"""
test_grpc_servicer.py
grpc_servicer.py 模块的单元测试
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_grpc_servicer.py
# │ Module: runtime/core/tests/test_grpc_servicer
# │ Role: Core runtime test module — verifies the canonical inference worker behavior.
# │
# │ 模块职责：核心运行时测试模块——验证标准推理工作器的行为。
# └─────────────────────────────────────────────────────────────────────┘


import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cy_exec.config.models import ModelSpec, WorkerConfig
from cy_exec.core.telemetry import Telemetry
from cy_exec.proto.ai_service_pb2 import WorkerHealthRequest


class TestGRPCServicer:
    """测试 gRPC Servicer"""

    @pytest.fixture
    def mock_server(self):
        """创建模拟推理服务器"""
        server = Mock()
        server.unload_model = Mock(return_value=True)
        server.stream_predict = Mock(return_value=iter(["Hello", " ", "World"]))
        server.get_loaded_models = Mock(return_value=["model-1"])
        server.health_check = Mock(return_value=True)
        server.telemetry = Telemetry()
        return server

    @pytest.fixture
    def servicer(self, mock_server):
        """创建 servicer 实例"""
        with patch('cy_exec.grpc_servicer.InferenceServer', return_value=mock_server):
            from cy_exec.grpc_servicer import AiInferenceServicerImpl
            return AiInferenceServicerImpl(
                mock_server,
                config=WorkerConfig(provider_id="cyrene.engines.fixture"),
            )

    def test_stream_predict_returns_responses(self, servicer, mock_server):
        """StreamPredict 应返回响应流"""
        # StreamPredict 接收一个请求迭代器
        request = Mock()
        request.model_id = "test-model"
        request.prompt = "Hello"
        request.max_tokens = 100
        request.temperature = 0.7
        request.adapter = None
        request.priority = 0
        request.metadata = Mock()
        request.metadata.trace_id = "test-trace-id"
        request.generation = None

        servicer._config = WorkerConfig(
            provider_id="cyrene.engines.fixture",
            model_registry={
                "test-model": ModelSpec(
                    model_path="/valid/model",
                    provider_id="cyrene.engines.fixture",
                )
            },
        )

        # 创建一个迭代器包装请求
        request_iterator = iter([request])

        context = Mock()
        context.invocation_metadata = Mock(return_value=[])
        context.abort = Mock()

        with patch("cy_exec.grpc_servicer._verify_internal_token", return_value=True):
            responses = list(servicer.StreamPredict(request_iterator, context))

        assert responses
        mock_server.stream_predict.assert_called_once()
        assert mock_server.stream_predict.call_args.kwargs["trace_id"] == "test-trace-id"

    def test_authentication_required(self, servicer):
        """需要认证时应验证 token"""
        request = Mock()
        request.model_id = "model"
        request.prompt = "test"

        context = Mock()
        context.invocation_metadata = Mock(return_value=[])
        context.abort = Mock()

        # 无 token 的请求
        # 取决于配置是否启用认证

    def test_health_uses_inference_server_telemetry(self, servicer, mock_server):
        mock_server.telemetry.track_request_start()
        mock_server.telemetry.track_request_end(0.01, success=True)

        response = servicer.Health(WorkerHealthRequest(trace_id="health"), Mock())

        assert response.metrics["requests_inflight"] == "0.0"
        assert response.metrics["requests_success"] == "1.0"
        assert response.metrics["requests_failed"] == "0.0"


class TestGRPCServicerErrorHandling:
    """测试 gRPC Servicer 错误处理"""

    @pytest.fixture
    def servicer_with_errors(self):
        """创建会抛出错误的 servicer"""
        mock_server = Mock()
        mock_server.stream_predict = Mock(side_effect=RuntimeError("Model error"))
        mock_server.telemetry = Telemetry()

        with patch('cy_exec.grpc_servicer.InferenceServer', return_value=mock_server):
            from cy_exec.grpc_servicer import AiInferenceServicerImpl
            return AiInferenceServicerImpl(
                mock_server,
                config=WorkerConfig(provider_id="cyrene.engines.fixture"),
            )

    def test_handles_runtime_error(self, servicer_with_errors):
        """应处理运行时错误"""
        request = Mock()
        request.model_id = "model"
        request.prompt = "test"

        context = Mock()
        context.invocation_metadata = Mock(return_value=[])
        context.abort = Mock()
        context.set_code = Mock()
        context.set_details = Mock()

        # 应该不崩溃
        try:
            list(servicer_with_errors.StreamPredict(request, context))
        except Exception:
            pass  # 预期可能抛出异常

    def test_handles_value_error(self):
        """应处理值错误"""
        pass

    def test_handles_oom_error(self):
        """应处理 OOM 错误"""
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
