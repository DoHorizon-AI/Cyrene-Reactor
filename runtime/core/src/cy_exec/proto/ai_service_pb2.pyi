from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class StreamMetadata(_message.Message):
    __slots__ = ("trace_id", "tenant", "player_id", "locale", "extra")
    class ExtraEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    PLAYER_ID_FIELD_NUMBER: _ClassVar[int]
    LOCALE_FIELD_NUMBER: _ClassVar[int]
    EXTRA_FIELD_NUMBER: _ClassVar[int]
    trace_id: str
    tenant: str
    player_id: str
    locale: str
    extra: _containers.ScalarMap[str, str]
    def __init__(self, trace_id: _Optional[str] = ..., tenant: _Optional[str] = ..., player_id: _Optional[str] = ..., locale: _Optional[str] = ..., extra: _Optional[_Mapping[str, str]] = ...) -> None: ...

class GenerationParameters(_message.Message):
    __slots__ = ("max_new_tokens", "temperature", "top_p", "repetition_penalty")
    MAX_NEW_TOKENS_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    TOP_P_FIELD_NUMBER: _ClassVar[int]
    REPETITION_PENALTY_FIELD_NUMBER: _ClassVar[int]
    max_new_tokens: int
    temperature: float
    top_p: float
    repetition_penalty: float
    def __init__(self, max_new_tokens: _Optional[int] = ..., temperature: _Optional[float] = ..., top_p: _Optional[float] = ..., repetition_penalty: _Optional[float] = ...) -> None: ...

class StreamPredictRequest(_message.Message):
    __slots__ = ("model_id", "prompt", "adapter", "priority", "generation", "metadata", "worker_hint")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    ADAPTER_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    GENERATION_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    WORKER_HINT_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    prompt: str
    adapter: str
    priority: int
    generation: GenerationParameters
    metadata: StreamMetadata
    worker_hint: str
    def __init__(self, model_id: _Optional[str] = ..., prompt: _Optional[str] = ..., adapter: _Optional[str] = ..., priority: _Optional[int] = ..., generation: _Optional[_Union[GenerationParameters, _Mapping]] = ..., metadata: _Optional[_Union[StreamMetadata, _Mapping]] = ..., worker_hint: _Optional[str] = ...) -> None: ...

class StreamPredictResponse(_message.Message):
    __slots__ = ("trace_id", "chunk", "end_of_stream", "index", "ttft_ms", "tokens_per_sec")
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    END_OF_STREAM_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    TTFT_MS_FIELD_NUMBER: _ClassVar[int]
    TOKENS_PER_SEC_FIELD_NUMBER: _ClassVar[int]
    trace_id: str
    chunk: str
    end_of_stream: bool
    index: int
    ttft_ms: float
    tokens_per_sec: float
    def __init__(self, trace_id: _Optional[str] = ..., chunk: _Optional[str] = ..., end_of_stream: _Optional[bool] = ..., index: _Optional[int] = ..., ttft_ms: _Optional[float] = ..., tokens_per_sec: _Optional[float] = ...) -> None: ...

class ControlMessage(_message.Message):
    __slots__ = ("trace_id", "command", "payload")
    class PayloadEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    trace_id: str
    command: str
    payload: _containers.ScalarMap[str, str]
    def __init__(self, trace_id: _Optional[str] = ..., command: _Optional[str] = ..., payload: _Optional[_Mapping[str, str]] = ...) -> None: ...

class WorkerHealthRequest(_message.Message):
    __slots__ = ("trace_id",)
    TRACE_ID_FIELD_NUMBER: _ClassVar[int]
    trace_id: str
    def __init__(self, trace_id: _Optional[str] = ...) -> None: ...

class WorkerHealthResponse(_message.Message):
    __slots__ = ("healthy", "metrics")
    class MetricsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    METRICS_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    metrics: _containers.ScalarMap[str, str]
    def __init__(self, healthy: _Optional[bool] = ..., metrics: _Optional[_Mapping[str, str]] = ...) -> None: ...
