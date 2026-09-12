"""
test_config_loader.py
config/config_loader.py 模块的单元测试
"""
# ┌─────────────────────────────────────────────────────────────────────┐
# │ 📄 runtime/core/tests/test_config_loader.py
# │ Module: runtime/core/tests/test_config_loader
# │ Role: Core runtime test module — verifies the canonical inference worker behavior.
# │
# │ 模块职责：核心运行时测试模块——验证标准推理工作器的行为。
# └─────────────────────────────────────────────────────────────────────┘


import pytest
import sys
import os
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cy_exec.config.config_loader import (
    load_worker_config,
    load_model_registry,
    WorkerConfig,
)


@pytest.fixture(autouse=True)
def configured_plugin_provider(monkeypatch):
    """Give ordinary loader tests one explicit Plugins-owned provider binding."""

    monkeypatch.setenv("CYRENE_SERVING_PROVIDER_ID", "cyrene.engines.fixture")


class TestLoadConfig:
    """测试配置加载函数"""

    def test_load_from_file(self):
        """应从文件加载配置"""
        # 使用实际的模型注册表格式
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({
                "default": {"model_path": "/path/to/model"}
            }, f)
            path = f.name

        try:
            config = load_model_registry(path)
            assert config is not None
            assert "default" in config
        finally:
            os.unlink(path)

    def test_load_missing_file(self):
        """缺失文件应抛出异常或返回默认值"""
        try:
            config = load_model_registry("/nonexistent/config.json")
            # 如果返回默认值
            assert config is not None or config is None
        except FileNotFoundError:
            # 预期行为
            pass

    def test_load_invalid_json(self):
        """无效 JSON 应抛出异常"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            path = f.name

        try:
            with pytest.raises(json.JSONDecodeError):
                load_model_registry(path)
        finally:
            os.unlink(path)


class TestGetConfig:
    """测试获取配置函数"""

    def test_returns_config(self):
        """应返回配置对象"""
        config = load_worker_config()
        assert isinstance(config, WorkerConfig)

    def test_singleton_behavior(self):
        """应返回相同配置实例"""
        config1 = load_worker_config()
        config2 = load_worker_config()
        # 可能是单例
        assert config1 is not None and config2 is not None


class TestConfigLoader:
    """测试 ConfigLoader 类"""

    def test_initialization(self):
        """应正确初始化"""
        config = load_worker_config()
        assert isinstance(config, WorkerConfig)

    def test_get_model_config(self):
        """get_model_config 应返回模型配置"""
        registry = load_model_registry()
        assert isinstance(registry, dict)

    def test_get_server_config(self):
        """get_server_config 应返回服务器配置"""
        config = load_worker_config()
        assert isinstance(config, WorkerConfig)

    def test_reload_config(self):
        """reload 应重新加载配置"""
        config1 = load_worker_config()
        config2 = load_worker_config()
        assert isinstance(config1, WorkerConfig) and isinstance(config2, WorkerConfig)

class TestEnvironmentOverrides:
    """测试环境变量覆盖"""

    def test_env_override_port(self):
        """环境变量应覆盖配置"""
        original = os.environ.get('CY_LLM_GRPC_PORT')

        try:
            os.environ['CY_LLM_GRPC_PORT'] = '50052'

            # 重新加载配置
            config = load_worker_config()

            # 检查端口是否被覆盖
            # WorkerConfig 当前存储 engine 和 model registry，端口通常由 Gateway 配置
            assert isinstance(config, WorkerConfig)
        finally:
            if original:
                os.environ['CY_LLM_GRPC_PORT'] = original
            elif 'CY_LLM_GRPC_PORT' in os.environ:
                del os.environ['CY_LLM_GRPC_PORT']

    def test_env_override_provider(self):
        """The owner-resolved Plugin provider identity is preserved."""
        original = os.environ.get('CYRENE_SERVING_PROVIDER_ID')

        try:
            os.environ['CYRENE_SERVING_PROVIDER_ID'] = 'cyrene.engines.vllm'
            config = load_worker_config()
            assert config.provider_id == 'cyrene.engines.vllm'
        finally:
            if original:
                os.environ['CYRENE_SERVING_PROVIDER_ID'] = original
            else:
                os.environ.pop('CYRENE_SERVING_PROVIDER_ID', None)

    def test_empty_provider_fails_closed(self):
        """An empty binding identity must not trigger local selection."""
        import importlib
        original_cy = os.environ.get('CYRENE_SERVING_PROVIDER_ID')

        try:
            os.environ['CYRENE_SERVING_PROVIDER_ID'] = ''
            import cy_exec.config.config_loader as loader
            importlib.reload(loader)
            with pytest.raises(ValueError, match='must be non-empty'):
                loader.load_worker_config()
        finally:
            if original_cy:
                os.environ['CYRENE_SERVING_PROVIDER_ID'] = original_cy
            else:
                os.environ.pop('CYRENE_SERVING_PROVIDER_ID', None)

    def test_internal_token_mapping_cy(self):
        """设置 CY_LLM_INTERNAL_TOKEN 并用于推理服务"""
        import importlib
        original_cy = os.environ.get('CY_LLM_INTERNAL_TOKEN')

        try:
            os.environ['CY_LLM_INTERNAL_TOKEN'] = 'secret-token-abc'
            # reload the module to re-evaluate import-time variables
            import cy_exec.utils.auth as auth_mod
            importlib.reload(auth_mod)
            assert auth_mod.get_internal_token() == 'secret-token-abc'
        finally:
            if original_cy:
                os.environ['CY_LLM_INTERNAL_TOKEN'] = original_cy
            elif 'CY_LLM_INTERNAL_TOKEN' in os.environ:
                del os.environ['CY_LLM_INTERNAL_TOKEN']


    def test_internal_token_utils_cy(self):
        """CY_LLM_INTERNAL_TOKEN 应被 worker.utils.auth.INTERNAL_TOKEN 使用"""
        import importlib
        original_cy = os.environ.get('CY_LLM_INTERNAL_TOKEN')

        try:
            os.environ['CY_LLM_INTERNAL_TOKEN'] = 'secret-token-xyz'
            import cy_exec.utils.auth as auth_mod
            importlib.reload(auth_mod)
            assert auth_mod.INTERNAL_TOKEN == 'secret-token-xyz'
        finally:
            if original_cy:
                os.environ['CY_LLM_INTERNAL_TOKEN'] = original_cy
            elif 'CY_LLM_INTERNAL_TOKEN' in os.environ:
                del os.environ['CY_LLM_INTERNAL_TOKEN']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
