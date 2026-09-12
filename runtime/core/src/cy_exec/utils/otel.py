# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/src/cy_exec/utils/otel.py
# │ Module: runtime/core/src/cy_exec/utils/otel
# │ Role: Canonical Reactor inference runtime — manages engines, scheduling, health, and serving protocols.
# │
# │ 模块职责：Reactor 标准推理运行时——管理引擎、调度、健康检查与服务协议。
# └─────────────────────────────────────────────────────────────────────┘

from __future__ import annotations

import os


def init_tracing(service_name: str) -> None:
	endpoint = os.getenv("CY_LLM_OTEL_ENDPOINT", "")
	if not endpoint:
		return

	try:
		from opentelemetry import trace  # type: ignore
		from opentelemetry.sdk.resources import SERVICE_NAME, Resource  # type: ignore
		from opentelemetry.sdk.trace import TracerProvider  # type: ignore
		from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
		from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter  # type: ignore
	except ImportError:
		return

	resource = Resource(attributes={SERVICE_NAME: service_name})
	provider = TracerProvider(resource=resource)
	span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
	provider.add_span_processor(BatchSpanProcessor(span_exporter))
	trace.set_tracer_provider(provider)
