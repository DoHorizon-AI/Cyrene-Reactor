"""""
server.py
# [gRPC 服务] 实现 Protobuf 中定义的服务：StreamPredict 与控制信道
# 说明：负责接受网关的双向流、调度推理任务、并与内存管理器协调。
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/core/server.py
# │ Module: runtime/core/src/cy_exec/core/server
# │ Role: Reactor Product coordinator for Plugin engines, bounded requests, health, and serving protocols.
# │
# │ 模块职责：Reactor Product 协调器——连接插件引擎并管理有界请求、健康检查与服务协议。
# └─────────────────────────────────────────────────────────────────────┘


from __future__ import annotations

import os
import queue
import threading
import time
from typing import Callable, Dict, Generator, List, Optional

import logging

from ..engines.abstract_engine import BaseEngine
from .memory_manager import ModelResidencyRegistry
from .task_scheduler import SchedulerBusy, TaskScheduler
from .telemetry import Telemetry

InferenceEngineFactory = Callable[[str], BaseEngine]


LOGGER = logging.getLogger("cy_llm.worker.server")


# ════════════════════════════════════════════════════════════════════════
# 🔧 CLASS: InferenceServer
#
#   Coordinates model loading, bounded request scheduling, streaming output,
#   health state, and graceful shutdown for the core serving worker.
#
#   协调核心服务工作器的模型加载、有界请求调度、流式输出、健康状态与优雅关闭。
#
# ════════════════════════════════════════════════════════════════════════
class InferenceServer:

	# 说明：该类作为推理服务的协调层，负责：
	# - 通过插件按需加载模型，并记录已加载句柄
	# - 将推理请求提交到本地调度器以限制并发
	# - 在推理过程中收集 Telemetry 指标并以队列方式流式返回生成文本

	def __init__(
		self,
		engine_factory: InferenceEngineFactory,
		scheduler: Optional[TaskScheduler] = None,
		telemetry: Optional[Telemetry] = None,
		residency: Optional[ModelResidencyRegistry] = None,
	) -> None:
		self._engine_factory = engine_factory
		self._scheduler = scheduler or TaskScheduler()
		self._telemetry = telemetry or Telemetry()
		self._residency = residency or ModelResidencyRegistry()
		self._model_lock: Dict[str, threading.Lock] = {}
		self._is_shutting_down: bool = False

	def _load_model(
		self,
		model_id: str,
		engine: BaseEngine,
		model_path: str,
		adapter_path: Optional[str],
		base_kwargs: Optional[dict],
		progress_callback: Optional[Callable[[str], None]] = None,
	) -> None:
		"""Delegate one model load attempt to the selected Plugin endpoint."""
		load_msg = f"正在通过插件加载模型 {model_id}..."
		LOGGER.info(load_msg)
		if progress_callback:
			progress_callback(load_msg)
		engine.load_model(model_path, adapter_path, **dict(base_kwargs or {}))

	def ensure_model(
		self,
		model_id: str,
		*,
		model_path: str,
		adapter_path: Optional[str] = None,
		provider_id: str,
		engine_kwargs: Optional[Dict] = None,
		progress_callback: Optional[Callable[[str], None]] = None,
	) -> BaseEngine:
		if self._is_shutting_down:
			raise RuntimeError("Server is shutting down.")

		# 如果内存管理器中已有加载的模型，直接返回
		engine = self._residency.get_loaded_model(model_id)
		if engine is not None:
			return engine

		if model_path == "/path/to/model" and os.getenv("CY_LLM_ALLOW_PLACEHOLDER_MODEL") != "true":
			raise ValueError("Placeholder model path")

        # 使用 per-model 锁防止并发重复加载同一模型
		lock = self._model_lock.setdefault(model_id, threading.Lock())
		with lock:
			# 再次检查，避免竞争条件下重复加载
			engine = self._residency.get_loaded_model(model_id)
			if engine is not None:
				return engine

			# Resolve the Plugins-owned provider and delegate model loading.
			if progress_callback:
				progress_callback(f"正在连接插件提供者 {provider_id}...")
			engine = self._engine_factory(provider_id)

			# Product does not rewrite engine settings after a capability failure.
			try:
				self._load_model(
					model_id,
					engine,
					model_path,
					adapter_path,
					engine_kwargs or {},
					progress_callback=progress_callback,
				)
			except Exception:
				try:
					engine.unload_model()
				except Exception:
					pass
				raise

			if progress_callback:
				progress_callback("模型加载完成，准备开始推理...")
			self._residency.register_model(model_id, engine)
			return engine

	def stream_predict(
		self,
		*,
		model_id: str,
		prompt: str,
		model_path: str,
		adapter_path: Optional[str] = None,
		provider_id: str,
		generation_kwargs: Optional[Dict] = None,
		engine_kwargs: Optional[Dict] = None,
		priority: int = 0,
		grpc_context: Optional[grpc.ServicerContext] = None,
		progress_callback: Optional[Callable[[str], None]] = None,
	) -> Generator[str, None, None]:
		if self._is_shutting_down:
			raise RuntimeError("Server is shutting down.")

		# 参数检查：prompt 不能为空
		if not prompt.strip():
			raise ValueError("Prompt must not be empty.")
		if len(prompt) > 50000:
			raise ValueError("Prompt too long (max 50000 chars).")

		gen_kwargs = dict(generation_kwargs or {})

		response_queue: queue.Queue[str] = queue.Queue()
		sentinel = "__CY_LLM_STREAM_END__"
		error_holder: List[Exception] = []

		# 进度队列：用于模型加载过程中的进度信息
		progress_queue: queue.Queue[str] = queue.Queue()
		progress_sentinel = "__CY_LLM_PROGRESS_END__"

		# 检查模型是否已加载
		model_loaded = self._residency.get_loaded_model(model_id) is not None

		# 如果模型未加载，先发送加载开始消息
		if not model_loaded:
			progress_queue.put("__CY_LLM_LOADING_START__")

		# 进度回调函数：将加载进度信息放入进度队列
		def progress_callback(message: str) -> None:
			progress_queue.put(f"__CY_LLM_LOADING__{message}__")

		# 工作函数：由调度器在后台线程调用，负责实际的推理并把结果放入队列
		def _task() -> None:
			start = time.time()
			self._telemetry.track_request_start()
			total_tokens = 0
			try:
				# 确保模型已加载（可能会触发加载）
				engine = self.ensure_model(
					model_id,
					model_path=model_path,
					adapter_path=adapter_path,
					provider_id=provider_id,
					engine_kwargs=engine_kwargs,
					progress_callback=progress_callback if not model_loaded else None,
				)
				# 模型加载完成，发送加载结束消息
				if not model_loaded:
					progress_queue.put(progress_sentinel)
				# 调用引擎的 infer，流式读取生成数据并入队
				for chunk in engine.infer(prompt, **gen_kwargs):
					response_queue.put(str(chunk))
					total_tokens += 1
				# 成功完成一次请求
				self._telemetry.track_request_end(time.time() - start, success=True)
				self._telemetry.track_token_generated(total_tokens)
				response_queue.put(sentinel)
			except Exception as exc:  # noqa: BLE001
				# 发生异常时记录并通知外层处理
				self._telemetry.track_request_end(time.time() - start, success=False)
				error_holder.append(exc)
				if not model_loaded:
					progress_queue.put(progress_sentinel)
				response_queue.put(sentinel)

		try:
			self._scheduler.submit(_task, priority=priority)
		except SchedulerBusy as exc:  # noqa: PERF203
			raise RuntimeError("Server is overloaded, please retry later.") from exc

		# 先处理加载进度信息
		progress_done = model_loaded  # 如果模型已加载，跳过进度处理
		if not model_loaded:
			yield "[模型加载] 开始加载模型，这可能需要几分钟，请耐心等待...\n"

		while not progress_done:
			try:
				# 使用超时避免阻塞
				progress_item = progress_queue.get(timeout=0.1)
				if progress_item == progress_sentinel:
					progress_done = True
				elif progress_item.startswith("__CY_LLM_LOADING__"):
					# 提取进度消息并输出
					message = progress_item.replace("__CY_LLM_LOADING__", "").rstrip("__")
					yield f"[模型加载] {message}\n"
			except queue.Empty:
				# 检查是否有错误
				if error_holder:
					break
				# 继续等待进度信息
				pass
			# 检查是否有错误
			if error_holder:
				# 确保处理完所有进度消息
				while True:
					try:
						progress_item = progress_queue.get_nowait()
						if progress_item == progress_sentinel:
							progress_done = True
							break
						elif progress_item.startswith("__CY_LLM_LOADING__"):
							message = progress_item.replace("__CY_LLM_LOADING__", "").rstrip("__")
							yield f"[模型加载] {message}\n"
					except queue.Empty:
						break
				break

		# 然后处理推理结果
		while True:
			item: str = response_queue.get()
			if item == sentinel:
				break
			yield item

		if error_holder:
			raise RuntimeError("Inference failed") from error_holder[0]

	def unload_model(self, model_id: str) -> None:
		lock = self._model_lock.setdefault(model_id, threading.Lock())
		with lock:
			engine = self._residency.get_loaded_model(model_id)
			if engine is None:
				return
			engine.unload_model()
			self._residency.unregister_model(model_id)

	async def async_unload_model(self, model_id: str) -> None:
		"""异步卸载模型（在线程池中执行）"""
		import asyncio
		loop = asyncio.get_running_loop()
		await loop.run_in_executor(None, self.unload_model, model_id)

	async def async_stream_predict(
		self,
		*,
		model_id: str,
		prompt: str,
		model_path: str,
		adapter_path: Optional[str] = None,
		provider_id: str,
		generation_kwargs: Optional[Dict] = None,
		engine_kwargs: Optional[Dict] = None,
		priority: int = 0,
	):
		"""
		异步流式推理。

		将同步的 stream_predict 包装为异步生成器，
		允许在异步上下文中使用。
		"""
		import asyncio

		loop = asyncio.get_running_loop()
		response_queue: queue.Queue[str] = queue.Queue()
		sentinel = "__CY_LLM_STREAM_END__"
		error_holder: List[Exception] = []

		def _sync_generate():
			try:
				for chunk in self.stream_predict(
					model_id=model_id,
					prompt=prompt,
					model_path=model_path,
					adapter_path=adapter_path,
					provider_id=provider_id,
					generation_kwargs=generation_kwargs,
					engine_kwargs=engine_kwargs,
					priority=priority,
				):
					response_queue.put(chunk)
			except Exception as e:
				error_holder.append(e)
			finally:
				response_queue.put(sentinel)

		# 在线程池中运行同步生成
		loop.run_in_executor(None, _sync_generate)

		# 异步轮询队列
		while True:
			# 非阻塞获取，配合 sleep 让出控制权
			try:
				item: str = response_queue.get_nowait()
				if item == sentinel:
					break
				yield item
			except queue.Empty:
				await asyncio.sleep(0.001)  # 1ms 轮询间隔

		if error_holder:
			raise RuntimeError("Inference failed") from error_holder[0]

	def shutdown(self) -> None:
		self._is_shutting_down = True
		self._scheduler.shutdown()
		for model_id in sorted(self._residency.get_loaded_models()):
			try:
				self.unload_model(model_id)
			except Exception:
				pass

	def get_loaded_models(self) -> List[str]:
		"""Return model identities known to the Product coordinator."""
		return self._residency.get_loaded_models()

	@property
	def telemetry(self) -> Telemetry:
		"""Return this server's canonical request telemetry."""
		return self._telemetry

	def health_check(self) -> bool:
		"""Return whether the Product coordinator accepts new work."""
		return not self._is_shutting_down

	def get_memory_usage(self) -> Dict:
		"""Return aggregate memory observations reported through engine ports."""
		return self._residency.memory_observation()
