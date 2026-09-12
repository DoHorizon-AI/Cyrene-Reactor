"""JSON logging, context propagation, and sensitive-value redaction."""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/pro/src/cy_exec_pro/utils/structured_logging.py
# │ Module: runtime/pro/src/cy_exec_pro/utils/structured_logging
# │ Role: Optional Reactor Pro runtime — adds relay, hardware, cache, LoRA, and coordination extensions.
# │
# │ 模块职责：Reactor 可选 Pro 运行时——提供中继、硬件、缓存、LoRA 与协调扩展。
# └─────────────────────────────────────────────────────────────────────┘


from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class SensitiveDataRedactor:
    """Redact sensitive fields and common API-token forms."""

    SENSITIVE_FIELD_PATTERNS = [
        r".*password.*",
        r".*passwd.*",
        r".*secret.*",
        r".*token.*",
        r".*api[_-]?key.*",
        r".*auth.*",
        r".*credential.*",
        r".*private[_-]?key.*",
        r".*access[_-]?key.*",
    ]

    # Do not treat every long alphanumeric message or trace ID as a secret.
    # Field names above provide context for generic secret values.
    API_KEY_PATTERNS = [
        r"sk-[a-zA-Z0-9]{32,}",
        r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*",
    ]

    def __init__(self) -> None:
        self.sensitive_field_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SENSITIVE_FIELD_PATTERNS
        ]
        self.api_key_regex = [re.compile(pattern) for pattern in self.API_KEY_PATTERNS]

    def is_sensitive_field(self, field_name: str) -> bool:
        """Return whether a field name identifies sensitive data."""
        return any(regex.match(field_name) for regex in self.sensitive_field_regex)

    def redact_value(self, value: str) -> str:
        """Mask short values completely and preserve small outer slices."""
        if not isinstance(value, str):
            value = str(value)
        if len(value) <= 8:
            return "***"
        if len(value) <= 16:
            return f"{value[:2]}...{value[-2:]}"
        return f"{value[:4]}...{value[-4:]}"

    def redact_api_keys(self, text: str) -> str:
        """Mask API-key and Bearer-token patterns in free text."""
        for regex in self.api_key_regex:
            text = regex.sub(lambda match: self.redact_value(match.group(0)), text)
        return text

    def redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively redact sensitive dictionary values."""
        redacted: Dict[str, Any] = {}
        for key, value in data.items():
            if self.is_sensitive_field(key):
                redacted[key] = self.redact_value(str(value))
            elif isinstance(value, dict):
                redacted[key] = self.redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self.redact_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                redacted[key] = self.redact_api_keys(value)
            else:
                redacted[key] = value
        return redacted


class StructuredFormatter(logging.Formatter):
    """Format log records as JSON with optional redaction."""

    def __init__(self, redact_sensitive: bool = True) -> None:
        super().__init__()
        self.redactor = SensitiveDataRedactor() if redact_sensitive else None

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record to JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "trace_id"):
            log_data["trace_id"] = record.trace_id
        if record.pathname:
            log_data["source"] = {
                "file": Path(record.pathname).name,
                "line": record.lineno,
                "function": record.funcName,
            }
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        standard_fields = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
            "trace_id",
        }
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in standard_fields
        }
        if extra_fields:
            if self.redactor:
                extra_fields = self.redactor.redact_dict(extra_fields)
            log_data["extra"] = extra_fields
        if self.redactor:
            log_data = self.redactor.redact_dict(log_data)
        return json.dumps(log_data, ensure_ascii=False)


def setup_structured_logging(
    level: str = "INFO",
    json_format: bool = True,
    redact_sensitive: bool = True,
    log_file: Optional[str] = None,
) -> None:
    """Configure root logging handlers for console and optional file output."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    formatter: logging.Formatter
    if json_format:
        formatter = StructuredFormatter(redact_sensitive=redact_sensitive)
    else:
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def get_structured_logger(name: str) -> logging.Logger:
    """Return a named logger."""
    return logging.getLogger(name)


class LogContext:
    """Temporarily add context fields to all log records."""

    def __init__(self, logger: logging.Logger, **context: Any) -> None:
        self.logger = logger
        self.context = context
        self.old_factory: Optional[Any] = None

    def __enter__(self) -> "LogContext":
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
            assert self.old_factory is not None
            record = self.old_factory(*args, **kwargs)
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **context: Any,
) -> None:
    """Log one message with temporary context fields."""
    with LogContext(logger, **context):
        getattr(logger, level.lower())(message)


__all__ = [
    "LogContext",
    "SensitiveDataRedactor",
    "StructuredFormatter",
    "get_structured_logger",
    "log_with_context",
    "setup_structured_logging",
]
