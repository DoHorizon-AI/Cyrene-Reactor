"""Property tests migrated from the Pro structured logging tests."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/pro/tests/test_structured_logging_pbt.py
# │ Module: runtime/pro/tests/test_structured_logging_pbt
# │ Role: Optional Pro runtime test module — verifies enterprise serving extensions.
# │
# │ 模块职责：可选 Pro 运行时测试模块——验证企业级服务扩展。
# └─────────────────────────────────────────────────────────────────────┘


import json
import logging
import sys

from hypothesis import given, settings, strategies as st

from cy_exec_pro.utils.structured_logging import SensitiveDataRedactor, StructuredFormatter


@given(value=st.text(min_size=8, max_size=40))
@settings(max_examples=30, deadline=None)
def test_sensitive_fields_are_redacted(value):
    redacted = SensitiveDataRedactor().redact_dict({"password": value})
    assert redacted["password"] != value


@given(value=st.text(min_size=1, max_size=100))
@settings(max_examples=30, deadline=None)
def test_non_sensitive_fields_are_preserved(value):
    redacted = SensitiveDataRedactor().redact_dict({"request_id": value})
    assert redacted["request_id"] == value


@given(body=st.text(min_size=20, max_size=48, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"))
@settings(max_examples=30, deadline=None)
def test_bearer_tokens_are_redacted(body):
    text = f"Authorization: Bearer {body}"
    output = SensitiveDataRedactor().redact_api_keys(text)
    assert body not in output
    assert "..." in output or "***" in output


def test_nested_redaction_and_formatter_structure():
    redactor = SensitiveDataRedactor()
    data = {"user": {"password": "secret123", "request_id": "request-1"}}
    result = redactor.redact_dict(data)
    assert result["user"]["password"] != "secret123"
    assert result["user"]["request_id"] == "request-1"

    logger = logging.getLogger("structured-test")
    record = logger.makeRecord("structured-test", logging.INFO, __file__, 1, "hello", (), None)
    record.trace_id = "trace-123"
    formatted = json.loads(StructuredFormatter().format(record))
    assert formatted["message"] == "hello"
    assert formatted["trace_id"] == "trace-123"
    assert {"timestamp", "level", "logger", "message"} <= formatted.keys()


def test_exception_information_is_serialized():
    logger = logging.getLogger("structured-test")
    try:
        raise ValueError("test error")
    except ValueError:
        record = logger.makeRecord(
            "structured-test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info()
        )
    formatted = json.loads(StructuredFormatter().format(record))
    assert formatted["exception"]["type"] == "ValueError"
    assert "test error" in formatted["exception"]["message"]
