# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_capability_seam.py
# │ Module: runtime/core/tests/test_capability_seam
# │ Role: Product serving port and fail-closed direct Plugin binding tests (REA-001).
# │
# │ 模块职责：产品服务端口、失败闭合绑定与兼容性隔离测试（REA-001）。
# └─────────────────────────────────────────────────────────────────────┘

import json

import pytest
from cyrene_plugin_runtime import DirectPayload, serve
from cyrene_plugin_runtime.client import (
    DirectPluginDeadlineExceeded,
    DirectPluginFailure,
    DirectPluginInvocationCancelled,
    DirectPluginProtocolError,
    DirectPluginTransportError,
)
from cy_exec.capability_seam import (
    EXECUTION_ENGINE_CAPABILITY,
    EXECUTION_ENGINE_INTERFACE_VERSION,
    EXECUTION_ENGINE_REQUIREMENT,
    ConfiguredExecutionEngineResolver,
    DirectPluginEngineProvider,
    DirectPluginExecutionEngineAdapter,
    ExecutionEngineBinding,
    ExecutionEngineCapabilityFactory,
    ExecutionEnginePort,
    ExecutionEngineRequirement,
    ServingPortFailure,
    ServingProfile,
    resolve_execution_engine_resolver,
)


def test_execution_engine_factory_resolves_direct_plugin_provider():
    resolver = ConfiguredExecutionEngineResolver(
        ExecutionEngineBinding(
            connection_ref="grpc://127.0.0.1:50051",
            provider_id="cyrene.engines.vllm",
        ),
        direct_client=object(),
    )
    factory = ExecutionEngineCapabilityFactory(resolver)

    assert isinstance(factory("cyrene.engines.vllm"), DirectPluginExecutionEngineAdapter)


def test_execution_engine_requirement_is_explicit_and_versioned():
    resolver = ConfiguredExecutionEngineResolver(
        ExecutionEngineBinding(
            connection_ref="grpc://127.0.0.1:50051",
            provider_id="cyrene.engines.vllm",
        ),
        direct_client=object(),
    )

    try:
        resolver.resolve(EXECUTION_ENGINE_REQUIREMENT.__class__(interface_version="2"))
    except ValueError as error:
        assert "execution.engine.v1" in str(error)
    else:
        raise AssertionError("incompatible serving capability must fail explicitly")


def test_direct_plugin_adapter_lifecycle_and_cancellation():
    class MockPluginClient:
        def __init__(self):
            self.calls = []

        def invoke(self, *, capability, interface_version, method, request, **kwargs):
            self.calls.append((capability, interface_version, method, request, kwargs))
            payload = json.loads(request.value.decode("utf-8"))
            assert capability == EXECUTION_ENGINE_CAPABILITY
            assert interface_version == EXECUTION_ENGINE_INTERFACE_VERSION
            assert request.type_url == (f"type.cyrene.io/{EXECUTION_ENGINE_CAPABILITY}.{method}.request")
            if method == "load_model":
                response = {
                    "status": "LOADED",
                    "model_path": payload["model_path"],
                    "engine": "cyrene.engines.vllm",
                }
            elif method == "execute_inference":
                response = {
                    "output_text": f"Generated tokens for {payload['prompt']}",
                    "latency_seconds": 0.02,
                    "engine": "cyrene.engines.vllm",
                }
            elif method == "unload_model":
                response = {
                    "status": "UNLOADED",
                    "engine": "cyrene.engines.vllm",
                }
            else:
                response = {
                    "engine_name": "vllm",
                    "runtime_available": False,
                    "is_loaded": True,
                }
            return DirectPayload(
                f"type.cyrene.io/{EXECUTION_ENGINE_CAPABILITY}.{method}.response",
                json.dumps(response).encode("utf-8"),
            )

    mock_client = MockPluginClient()
    binding = ExecutionEngineBinding(
        profile=ServingProfile.DIRECT_PLUGIN,
        connection_ref="grpc://127.0.0.1:50051",
        provider_id="cyrene.engines.vllm",
    )
    adapter = DirectPluginExecutionEngineAdapter(binding, client=mock_client)

    # Initial state
    # 中文:初始状态
    assert adapter.health_check() is False
    with pytest.raises(ServingPortFailure, match="Model is not loaded"):
        list(adapter.infer("test"))

    # Load model
    # 中文:加载模型
    adapter.load_model("/path/to/test-model")
    assert adapter.health_check() is True
    assert adapter.get_model_info()["is_loaded"] is True
    assert adapter.get_model_info()["engine"] == "cyrene.engines.vllm"

    # Inference streaming
    # 中文:推理流式输出
    tokens = list(adapter.infer("Hello"))
    assert len(tokens) == 1
    assert "Generated tokens for Hello" in tokens[0]

    # Cancellation fails closed cleanly
    # 中文:取消请求以干净的失败即拒绝方式处理
    with pytest.raises(ServingPortFailure, match="cancelled"):
        list(adapter.infer("Cancelled request", cancel_requested=True))

    # Unload model
    # 中文:卸载模型
    adapter.unload_model()
    assert adapter.health_check() is False
    assert adapter.get_model_info()["is_loaded"] is False
    assert [call[2] for call in mock_client.calls] == [
        "load_model",
        "get_engine_info",
        "get_engine_info",
        "execute_inference",
        "unload_model",
    ]


def test_direct_plugin_adapter_uses_plugins_owned_grpc_wire():
    class TypedResult:
        def __init__(self, value, type_url):
            self.value = value
            self.type_url = type_url

    class RuntimePlugin:
        capabilities = (EXECUTION_ENGINE_CAPABILITY,)

        def on_invoke(self, capability, method, payload, *, request_type_url, **_kwargs):
            assert capability == EXECUTION_ENGINE_CAPABILITY
            assert request_type_url == f"type.cyrene.io/{capability}.{method}.request"
            request = json.loads(payload.decode("utf-8"))
            if method == "load_model":
                response = {
                    "status": "LOADED",
                    "model_path": request["model_path"],
                    "engine": "wire-fixture",
                }
            elif method == "execute_inference":
                response = {
                    "output_text": f"wire:{request['prompt']}",
                    "latency_seconds": 0.01,
                    "engine": "wire-fixture",
                }
            elif method == "get_engine_info":
                response = {
                    "engine_name": "wire-fixture",
                    "runtime_available": False,
                    "is_loaded": True,
                }
            else:
                response = {"status": "UNLOADED", "engine": "wire-fixture"}
            return True, TypedResult(
                json.dumps(response).encode("utf-8"),
                f"type.cyrene.io/{capability}.{method}.response",
            )

    server, connection_ref = serve(
        RuntimePlugin(), EXECUTION_ENGINE_CAPABILITY, EXECUTION_ENGINE_INTERFACE_VERSION, "127.0.0.1:0"
    )
    provider = DirectPluginEngineProvider(
        ExecutionEngineBinding(
            profile=ServingProfile.DIRECT_PLUGIN,
            connection_ref=connection_ref,
            provider_id="wire-fixture",
        )
    )
    engine = provider.create("wire-fixture")
    try:
        engine.load_model("/models/wire-fixture")
        assert list(engine.infer("hello")) == ["wire:hello"]
        assert engine.get_model_info()["engine_name"] == "wire-fixture"
    finally:
        engine.unload_model()
        server.stop(grace=None).wait()


def test_direct_plugin_binding_fails_closed_without_in_tree_fallback():
    """A connection failure remains a Product port failure without local fallback.

        中文:连接失败仍作为 Product 端口故障返回,不回退到本地实现。"""

    class FailingClient:
        def invoke(self, **_kwargs):
            raise DirectPluginTransportError("UNAVAILABLE", "Remote engine service unavailable")

    binding = ExecutionEngineBinding(
        profile=ServingProfile.DIRECT_PLUGIN,
        connection_ref="grpc://127.0.0.1:59999",
        provider_id="cyrene.engines.vllm",
    )
    resolver = ConfiguredExecutionEngineResolver(
        binding=binding,
        direct_client=FailingClient(),
    )
    factory = ExecutionEngineCapabilityFactory(resolver)
    engine = factory("cyrene.engines.vllm")

    # When remote endpoint fails, it must raise ServingPortFailure
    # 中文:远程端点失败时必须抛出 ServingPortFailure
    with pytest.raises(ServingPortFailure, match="Remote engine service unavailable"):
        engine.load_model("/models/meta-llama")

def test_direct_plugin_requires_connection_ref_or_client():
    binding = ExecutionEngineBinding(
        profile=ServingProfile.DIRECT_PLUGIN,
        connection_ref=None,
    )
    resolver = ConfiguredExecutionEngineResolver(binding=binding)
    with pytest.raises(ServingPortFailure, match="SERVING_BINDING_REQUIRED"):
        resolver.resolve(EXECUTION_ENGINE_REQUIREMENT)


def test_resolve_execution_engine_resolver_environment(monkeypatch):
    # Default profile -> DIRECT_PLUGIN and fail closed until a connection is configured.
    # 中文:默认配置为 DIRECT_PLUGIN;配置连接前按失败即拒绝处理。
    monkeypatch.delenv("CYRENE_SERVING_PROFILE", raising=False)
    monkeypatch.delenv("CYRENE_SERVING_CONNECTION_REF", raising=False)
    default_res = resolve_execution_engine_resolver()
    assert isinstance(default_res, ConfiguredExecutionEngineResolver)
    with pytest.raises(ServingPortFailure, match="SERVING_BINDING_REQUIRED"):
        default_res.resolve(EXECUTION_ENGINE_REQUIREMENT)

    # DIRECT_PLUGIN via environment variable
    # 中文:通过环境变量设置 DIRECT_PLUGIN
    monkeypatch.setenv("CYRENE_SERVING_PROFILE", "DIRECT_PLUGIN")
    monkeypatch.setenv("CYRENE_SERVING_CONNECTION_REF", "grpc://127.0.0.1:50051")
    monkeypatch.setenv("CYRENE_SERVING_PROVIDER_ID", "cyrene.engines.vllm")
    direct_res = resolve_execution_engine_resolver()
    assert isinstance(direct_res, ConfiguredExecutionEngineResolver)
    provider = direct_res.resolve(EXECUTION_ENGINE_REQUIREMENT)
    assert isinstance(provider, DirectPluginEngineProvider)

    # Removed compatibility profiles are rejected instead of selecting local code.
    # 中文:已移除的兼容配置会被拒绝,不会选择本地代码。
    monkeypatch.setenv("CYRENE_SERVING_PROFILE", "LOCAL_ENGINE")
    monkeypatch.delenv("CYRENE_SERVING_CONNECTION_REF", raising=False)
    with pytest.raises(ServingPortFailure, match="SERVING_PROFILE_UNSUPPORTED"):
        resolve_execution_engine_resolver()


@pytest.mark.parametrize(
    ("error", "status", "retryable"),
    [
        (DirectPluginFailure(3, "cancelled"), 499, False),
        (DirectPluginFailure(6, "endpoint unavailable", retryable=True), 503, True),
        (DirectPluginFailure(4, "deadline", retryable=True), 504, True),
        (DirectPluginInvocationCancelled("CANCELLED", "cancelled"), 499, False),
        (DirectPluginDeadlineExceeded("DEADLINE_EXCEEDED", "deadline"), 504, True),
        (DirectPluginTransportError("UNAVAILABLE", "transport down"), 503, True),
        (DirectPluginProtocolError("missing result"), 502, False),
    ],
)
def test_direct_plugin_failures_map_to_stable_serving_port_failure(error, status, retryable):
    class FailingClient:
        def invoke(self, **_kwargs):
            raise error

    adapter = DirectPluginExecutionEngineAdapter(
        ExecutionEngineBinding(
            profile=ServingProfile.DIRECT_PLUGIN,
            connection_ref="grpc://127.0.0.1:50051",
        ),
        client=FailingClient(),
    )
    adapter._is_loaded = True
    with pytest.raises(ServingPortFailure) as captured:
        list(adapter.infer("hello"))
    assert captured.value.status == status
    assert captured.value.retryable is retryable


def test_untyped_direct_plugin_exception_is_stable_and_has_no_fallback():
    class BrokenClient:
        def invoke(self, **_kwargs):
            raise ConnectionError("socket closed")

    adapter = DirectPluginExecutionEngineAdapter(
        ExecutionEngineBinding(
            profile=ServingProfile.DIRECT_PLUGIN,
            connection_ref="grpc://127.0.0.1:50051",
        ),
        client=BrokenClient(),
    )
    adapter._is_loaded = True
    with pytest.raises(ServingPortFailure, match="direct Plugin invocation failed: socket closed") as captured:
        list(adapter.infer("hello"))
    assert captured.value.status == 503
    assert captured.value.retryable is True


def test_direct_plugin_response_type_url_corruption_fails_closed():
    class CorruptClient:
        def invoke(self, **_kwargs):
            return DirectPayload("type.cyrene.io/other.capability.response", b"{}")

    adapter = DirectPluginExecutionEngineAdapter(
        ExecutionEngineBinding(
            profile=ServingProfile.DIRECT_PLUGIN,
            connection_ref="grpc://127.0.0.1:50051",
        ),
        client=CorruptClient(),
    )
    adapter._is_loaded = True
    with pytest.raises(ServingPortFailure, match="unexpected response type URL"):
        list(adapter.infer("hello"))


def test_direct_plugin_engine_info_uses_generic_runtime_available_field():
    class LegacyInfoClient:
        def invoke(self, *, method, **_kwargs):
            assert method == "get_engine_info"
            return DirectPayload(
                "type.cyrene.io/execution.engine.v1.get_engine_info.response",
                json.dumps(
                    {
                        "engine_name": "fixture",
                        "legacy_runtime_flag": False,
                        "is_loaded": True,
                    }
                ).encode("utf-8"),
            )

    adapter = DirectPluginExecutionEngineAdapter(
        ExecutionEngineBinding(
            profile=ServingProfile.DIRECT_PLUGIN,
            connection_ref="grpc://127.0.0.1:50051",
        ),
        client=LegacyInfoClient(),
    )
    adapter._is_loaded = True
    with pytest.raises(ServingPortFailure, match="engine info response is malformed"):
        adapter.get_model_info()


def test_direct_plugin_connection_ref_uses_sdk_local_target_validation():
    provider = DirectPluginEngineProvider(
        ExecutionEngineBinding(
            profile=ServingProfile.DIRECT_PLUGIN,
            connection_ref="https://remote.example/plugin",
            provider_id="cyrene.engines.vllm",
        )
    )
    with pytest.raises(ServingPortFailure, match="SERVING_BINDING_INVALID"):
        provider.create("cyrene.engines.vllm")


def test_in_tree_concrete_engines_are_absent_rea002():
    """REA-002: Reactor must not ship concrete execution-engine modules.

        中文:REA-002:Reactor 不得随包发布具体执行引擎模块。"""
    from pathlib import Path

    engine_dir = Path(__file__).parents[1] / "src" / "cy_exec" / "engines"
    assert {path.name for path in engine_dir.glob("*.py")} == {
        "__init__.py",
        "abstract_engine.py",
    }
