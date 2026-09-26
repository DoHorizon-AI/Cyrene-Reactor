"""
Unit tests for Cyrene Reactor correlation propagation, error mapping, and logging.

中文:Cyrene Reactor 关联信息传播、错误映射和日志的单元测试。
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from cyrene_reactor_product.api import create_app
from cyrene_reactor_product.errors import map_reactor_error
from cyrene_reactor_product.logging import (
    format_cyrene_log,
    parse_w3c_traceparent,
    redact_attributes,
    sanitize_request_id,
)


def test_w3c_traceparent_parsing():
    valid = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    parsed = parse_w3c_traceparent(valid)
    assert parsed is not None
    trace_id, span_id = parsed
    assert trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert span_id == "00f067aa0ba902b7"

    # All zeros rejection
    # 中文:拒绝全零值。
    assert parse_w3c_traceparent("00-00000000000000000000000000000000-00f067aa0ba902b7-01") is None
    assert parse_w3c_traceparent("00-4bf92f3577b34da6a3ce929d0e0e4736-0000000000000000-01") is None
    assert parse_w3c_traceparent("invalid-traceparent") is None


def test_correlation_sanitization():
    dirty = "req-123\r\ninjection: attempt\x00"
    sanitized = sanitize_request_id(dirty)
    assert sanitized == "req-123injection:attempt"
    assert "\r" not in sanitized
    assert "\n" not in sanitized

    long_id = "X" * 300
    assert len(sanitize_request_id(long_id)) == 128


def test_redaction_preserves_token_usage_counters():
    attrs = {
        "api_key": "secret-api-key-12345",
        "token": "sensitive-token-abc",
        "password": "my-password",
        "tokens": 1500,
        "prompt_tokens": 500,
        "completion_tokens": 1000,
        "token_count": 1500,
        "safe_attr": "public-val",
    }
    redacted = redact_attributes(attrs)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["token"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["tokens"] == 1500
    assert redacted["prompt_tokens"] == 500
    assert redacted["completion_tokens"] == 1000
    assert redacted["token_count"] == 1500
    assert redacted["safe_attr"] == "public-val"


def test_reactor_error_mapping():
    mapped = map_reactor_error("REACTOR_DEPLOYMENT_NOT_FOUND")
    assert mapped["code"] == "PRODUCT.REACTOR.DEPLOYMENT_NOT_FOUND"
    assert mapped["recovery_action"] == "user_action_required"

    mapped_perm = map_reactor_error("REACTOR_PERMISSION_DENIED")
    assert mapped_perm["code"] == "PRODUCT.REACTOR.PERMISSION_DENIED"
    assert mapped_perm["recovery_action"] == "fix_configuration"

    mapped_unknown = map_reactor_error("CUSTOM_FOO_BAR")
    assert mapped_unknown["code"] == "PRODUCT.REACTOR.CUSTOM_FOO_BAR"
    assert mapped_unknown["recovery_action"] == "query_state_first"


def test_structured_log_formatting():
    log_line = format_cyrene_log(
        "INFO",
        "product.reactor.test_event",
        "Test reactor message",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        span_id="00f067aa0ba902b7",
        attributes={"deployment_id": "dep-123", "secret_key": "raw_secret"},
    )
    record = json.loads(log_line)
    assert record["schema_version"] == 1
    assert record["level"] == "INFO"
    assert record["service.name"] == "cyrene-reactor"
    assert record["event.name"] == "product.reactor.test_event"
    assert record["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert record["span_id"] == "00f067aa0ba902b7"
    assert record["attributes"]["deployment_id"] == "dep-123"
    assert record["attributes"]["secret_key"] == "[REDACTED]"


def test_api_traceparent_and_error_handling():
    with TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "reactor.db"
        app = create_app(database_path=db_path)
        client = TestClient(app)

        # Send request with W3C traceparent and x-request-id
        # 中文:发送包含 W3C traceparent 和 x-request-id 的请求。
        traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        req_id = "req-test-client-999"

        # Request unknown deployment to trigger 404 ProblemDetails
        # 中文:请求未知 Deployment,以触发 404 ProblemDetails。
        res = client.get(
            "/api/v1/deployments/00000000-0000-0000-0000-000000000001",
            headers={"traceparent": traceparent, "x-request-id": req_id},
        )

        assert res.status_code == 404
        assert "traceparent" in res.headers
        assert "4bf92f3577b34da6a3ce929d0e0e4736" in res.headers["traceparent"]
        assert res.headers["x-request-id"] == req_id

        problem = res.json()
        assert problem["code"] == "REACTOR_DEPLOYMENT_NOT_FOUND"
        assert problem.get("requestId") == req_id or problem.get("request_id") == req_id
        assert (
            problem.get("traceId") == "4bf92f3577b34da6a3ce929d0e0e4736"
            or problem.get("trace_id") == "4bf92f3577b34da6a3ce929d0e0e4736"
        )
        assert (
            problem.get("recoveryAction") == "user_action_required"
            or problem.get("recovery_action") == "user_action_required"
        )
