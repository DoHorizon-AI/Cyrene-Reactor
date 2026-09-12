# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_proto_roundtrip.py
# │ Module: runtime/core/tests/test_proto_roundtrip
# │ Role: Core runtime test module — verifies the canonical inference worker behavior.
# │
# │ 模块职责：核心运行时测试模块——验证标准推理工作器的行为。
# └─────────────────────────────────────────────────────────────────────┘

from cy_exec.proto import (
    GenerationParameters,
    StreamMetadata,
    StreamPredictRequest,
)


def test_stream_predict_request_roundtrip() -> None:
    request = StreamPredictRequest(
        model_id="test-model",
        prompt="hello",
        generation=GenerationParameters(max_new_tokens=4, temperature=0.2),
        metadata=StreamMetadata(trace_id="trace-1", extra={"source": "test"}),
    )

    decoded = StreamPredictRequest.FromString(request.SerializeToString())

    assert decoded == request
    assert decoded.metadata.extra["source"] == "test"
