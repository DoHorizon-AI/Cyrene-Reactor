"""
test_server.py
core/server.py (InferenceServer) 模块的单元测试
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_server.py
# │ Module: runtime/core/tests/test_server
# │ Role: Core runtime test module — verifies the canonical inference worker behavior.
# │
# │ 模块职责：核心运行时测试模块——验证标准推理工作器的行为。
# └─────────────────────────────────────────────────────────────────────┘


import pytest
import sys
import os
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cy_exec.core.memory_manager import ModelResidencyRegistry
from cy_exec.core.server import InferenceServer


class TestInferenceServer:
    """测试推理服务器"""

    @pytest.fixture
    def mock_engine(self):
        """创建模拟引擎"""
        engine = Mock()
        engine.load_model = Mock()
        engine.unload_model = Mock()
        engine.infer = Mock(return_value=iter(["Hello", " ", "World"]))
        engine.get_memory_usage = Mock(return_value={"allocated_gb": 1.0, "total_gb": 24.0})
        return engine

    @pytest.fixture
    def server(self, mock_engine):
        """创建服务器实例"""
        return InferenceServer(
            engine_factory=Mock(return_value=mock_engine),
            residency=ModelResidencyRegistry(),
        )

    def test_initialization(self, server):
        """应正确初始化"""
        assert server is not None

    def test_ensure_model_delegates_to_plugin_engine(self, server, mock_engine):
        """Model loading delegates through the selected Plugin provider."""
        loaded = server.ensure_model(
            "test-model",
            model_path="/valid/model",
            provider_id="fixture.engine",
        )

        assert loaded is mock_engine
        mock_engine.load_model.assert_called_once_with("/valid/model", None)

    def test_unload_model(self, server, mock_engine):
        """unload_model 应调用引擎卸载"""
        server.ensure_model(
            "test-model",
            model_path="/valid/model",
            provider_id="fixture.engine",
        )
        server.unload_model("test-model")
        mock_engine.unload_model.assert_called_once_with()

    def test_stream_predict(self, server, mock_engine):
        """stream_predict 应返回生成器"""
        os.environ["CY_LLM_ALLOW_PLACEHOLDER_MODEL"] = "true"
        result = list(server.stream_predict(
            model_id="test-model",
            prompt="Hello",
            model_path="/valid/model",
            provider_id="fixture.engine",
        ))
        assert result[-3:] == ["Hello", " ", "World"]

    def test_stream_predict_unknown_model(self, server):
        """未知模型应抛出异常"""
        with patch.object(server, "ensure_model", side_effect=ValueError("unknown model")):
            with pytest.raises(RuntimeError):
                list(server.stream_predict(
                    model_id="unknown",
                    prompt="Hello",
                    model_path="/path/to/model",
                    provider_id="fixture.engine",
                ))

    def test_get_loaded_models(self, server):
        """get_loaded_models 应返回列表"""
        models = server.get_loaded_models()
        assert models == []

    def test_health_check(self, server):
        """health_check 应返回健康状态"""
        status = server.health_check()
        assert status is True

    def test_get_memory_usage(self, server, mock_engine):
        """get_memory_usage 应返回内存信息"""
        usage = server.get_memory_usage()
        assert isinstance(usage, dict)


class TestInferenceServerAsync:
    """测试异步推理服务器方法"""

    @pytest.fixture
    def mock_engine(self):
        engine = Mock()
        engine.load_model = Mock()
        engine.infer = Mock(return_value=iter(["a", "b"]))
        return engine

    @pytest.fixture
    def server(self, mock_engine):
        return InferenceServer(engine_factory=Mock(return_value=mock_engine))

    def test_async_stream_predict(self, server):
        """async_stream_predict 应异步返回 token"""
        import asyncio

        async def _run():
            with patch.object(server, "stream_predict", return_value=iter(["a", "b"])):
                items = []
                async for chunk in server.async_stream_predict(
                    model_id="model",
                    prompt="Hello",
                    model_path="/path/to/model",
                    provider_id="fixture.engine",
                ):
                    items.append(chunk)
                assert items == ["a", "b"]

        asyncio.run(_run())

    def test_async_unload_model(self, server):
        """async_unload_model 应异步卸载"""
        import asyncio

        async def _run():
            server.ensure_model(
                "model", model_path="/path", provider_id="fixture.engine"
            )
            await server.async_unload_model("model")

        asyncio.run(_run())


class TestInferenceServerLifecycle:
    """测试推理服务器生命周期与关闭安全"""

    @staticmethod
    def _isolated_server(engine_factory):
        residency = ModelResidencyRegistry()
        scheduler = Mock()
        server = InferenceServer(
            engine_factory=engine_factory,
            scheduler=scheduler,
            residency=residency,
        )
        return server, residency, scheduler

    def test_successful_unload_unregisters_engine_and_allows_fresh_reload(self):
        first_engine = MagicMock()
        second_engine = MagicMock()
        engine_factory = Mock(side_effect=[first_engine, second_engine])
        server, residency, _scheduler = self._isolated_server(engine_factory)

        assert server.ensure_model(
            "model", model_path="/valid/model", provider_id="fixture.engine"
        ) is first_engine
        assert server.get_loaded_models() == ["model"]

        server.unload_model("model")

        first_engine.unload_model.assert_called_once_with()
        assert residency.get_loaded_model("model") is None
        assert server.get_loaded_models() == []
        assert server.ensure_model(
            "model", model_path="/valid/model", provider_id="fixture.engine"
        ) is second_engine

    def test_failed_unload_preserves_loaded_state_for_retry(self):
        engine = MagicMock()
        engine.unload_model.side_effect = RuntimeError("device cleanup failed")
        engine_factory = Mock(return_value=engine)
        server, residency, _scheduler = self._isolated_server(engine_factory)
        server.ensure_model(
            "model", model_path="/valid/model", provider_id="fixture.engine"
        )

        with pytest.raises(RuntimeError, match="device cleanup failed"):
            server.unload_model("model")

        assert residency.get_loaded_model("model") is engine
        assert server.ensure_model(
            "model", model_path="/valid/model", provider_id="fixture.engine"
        ) is engine
        engine_factory.assert_called_once_with("fixture.engine")

    def test_shutdown_unloads_all_plugin_models(self):
        first_engine = MagicMock()
        second_engine = MagicMock()
        engine_factory = Mock(side_effect=[first_engine, second_engine])
        server, residency, scheduler = self._isolated_server(engine_factory)
        server.ensure_model(
            "first", model_path="/valid/first", provider_id="fixture.engine"
        )
        server.ensure_model(
            "second", model_path="/valid/second", provider_id="fixture.engine"
        )

        server.shutdown()

        scheduler.shutdown.assert_called_once_with()
        first_engine.unload_model.assert_called_once_with()
        second_engine.unload_model.assert_called_once_with()
        assert residency.get_loaded_models() == []
        assert server.get_loaded_models() == []

    def test_shutdown_transitions_and_rejection(self):
        server = InferenceServer(engine_factory=Mock())
        assert server.health_check() is True

        server.shutdown()
        assert server.health_check() is False

        with pytest.raises(RuntimeError, match="shutting down"):
            list(server.stream_predict(
                model_id="test-model",
                prompt="hello",
                model_path="/path",
                provider_id="fixture.engine",
            ))

        with pytest.raises(RuntimeError, match="shutting down"):
            server.ensure_model(
                model_id="test-model",
                model_path="/path",
                provider_id="fixture.engine",
            )

    def test_failed_load_calls_unload_model(self):
        mock_engine = MagicMock()
        mock_engine.load_model.side_effect = RuntimeError("CUDA OOM during weights load")

        server = InferenceServer(engine_factory=Mock(return_value=mock_engine))
        with pytest.raises(RuntimeError, match="CUDA OOM"):
            server.ensure_model(
                model_id="oom-model",
                model_path="/valid/path",
                provider_id="fixture.engine",
            )
        mock_engine.unload_model.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
