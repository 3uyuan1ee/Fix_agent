"""
测试LLM配置管理系统
"""

import pytest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.llm.config import LLMConfigManager
from src.llm.base import LLMConfig


class TestLLMConfigManager:
    """测试LLM配置管理器"""

    @pytest.fixture
    def temp_config_file(self):
        """临时配置文件fixture"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_data = {
                "providers": {
                    "openai": {
                        "provider": "openai",
                        "model": "gpt-4",
                        "api_key": "test-openai-key",
                        "temperature": 0.7,
                        "max_tokens": 2000
                    },
                    "anthropic": {
                        "provider": "anthropic",
                        "model": "claude-3-sonnet",
                        "api_key": "test-anthropic-key",
                        "temperature": 0.5
                    }
                }
            }
            yaml.dump(config_data, f)
            temp_file = f.name

        yield temp_file
        os.unlink(temp_file)

    @pytest.fixture
    def config_manager(self, temp_config_file):
        """配置管理器fixture"""
        return LLMConfigManager(config_file=temp_config_file)

    def test_init_with_config_file(self, config_manager):
        """测试使用配置文件初始化"""
        assert len(config_manager.configs) == 2
        assert "openai" in config_manager.configs
        assert "anthropic" in config_manager.configs

    def test_get_config_success(self, config_manager):
        """测试成功获取配置"""
        openai_config = config_manager.get_config("openai")
        assert openai_config is not None
        assert openai_config.provider == "openai"
        assert openai_config.model == "gpt-4"
        assert openai_config.api_key == "test-openai-key"

    def test_get_config_not_found(self, config_manager):
        """测试获取不存在的配置"""
        config = config_manager.get_config("nonexistent")
        assert config is None

    def test_get_config_case_insensitive(self, config_manager):
        """测试大小写不敏感的配置获取"""
        openai_config_upper = config_manager.get_config("OPENAI")
        openai_config_lower = config_manager.get_config("openai")
        assert openai_config_upper == openai_config_lower

    def test_list_providers(self, config_manager):
        """测试列出提供者"""
        providers = config_manager.list_providers()
        assert len(providers) == 2
        assert "openai" in providers
        assert "anthropic" in providers

    def test_add_config(self, config_manager):
        """测试添加配置"""
        new_config = LLMConfig(
            provider="custom",
            model="custom-model",
            api_key="custom-key"
        )
        config_manager.add_config("custom", new_config)

        assert len(config_manager.configs) == 3
        retrieved_config = config_manager.get_config("custom")
        assert retrieved_config.provider == "custom"
        assert retrieved_config.model == "custom-model"

    def test_add_config_invalid(self, config_manager):
        """测试添加无效配置"""
        invalid_config = LLMConfig(
            provider="",
            model="test",  # 缺少provider
            api_key="test"
        )
        with pytest.raises(ValueError, match="Provider is required"):
            config_manager.add_config("invalid", invalid_config)

    def test_remove_config_success(self, config_manager):
        """测试成功移除配置"""
        assert "openai" in config_manager.configs
        result = config_manager.remove_config("openai")
        assert result is True
        assert "openai" not in config_manager.configs

    def test_remove_config_not_found(self, config_manager):
        """测试移除不存在的配置"""
        result = config_manager.remove_config("nonexistent")
        assert result is False

    def test_update_config_success(self, config_manager):
        """测试成功更新配置"""
        updates = {
            "temperature": 0.9,
            "max_tokens": 3000
        }
        result = config_manager.update_config("openai", updates)
        assert result is True

        updated_config = config_manager.get_config("openai")
        assert updated_config.temperature == 0.9
        assert updated_config.max_tokens == 3000
        # 其他字段应该保持不变
        assert updated_config.model == "gpt-4"

    def test_update_config_not_found(self, config_manager):
        """测试更新不存在的配置"""
        updates = {"temperature": 0.9}
        result = config_manager.update_config("nonexistent", updates)
        assert result is False

    def test_update_config_invalid(self, config_manager):
        """测试更新为无效配置"""
        updates = {"temperature": 3.0}  # 无效值
        result = config_manager.update_config("openai", updates)
        assert result is False

        # 原配置应该保持不变
        original_config = config_manager.get_config("openai")
        assert original_config.temperature == 0.7

    def test_save_config(self, config_manager):
        """测试保存配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_file = f.name

        try:
            result = config_manager.save_config(temp_file)
            assert result is True

            # 验证文件内容
            with open(temp_file, 'r') as f:
                saved_data = yaml.safe_load(f)

            assert "providers" in saved_data
            assert len(saved_data["providers"]) == 2
            assert "openai" in saved_data["providers"]
            assert "anthropic" in saved_data["providers"]

        finally:
            os.unlink(temp_file)

    def test_get_provider_models(self, config_manager):
        """测试获取提供者模型列表"""
        openai_models = config_manager.get_provider_models("openai")
        assert isinstance(openai_models, list)
        assert len(openai_models) > 0
        assert "gpt-4" in openai_models

        anthropic_models = config_manager.get_provider_models("anthropic")
        assert isinstance(anthropic_models, list)
        assert len(anthropic_models) > 0
        assert "claude-3-sonnet-20240229" in anthropic_models

        # 不存在的提供者应该返回空列表
        unknown_models = config_manager.get_provider_models("unknown")
        assert unknown_models == []

    def test_validate_config_success(self, config_manager):
        """测试配置验证成功"""
        assert config_manager.validate_config("openai") is True
        assert config_manager.validate_config("anthropic") is True

    def test_validate_config_not_found(self, config_manager):
        """测试验证不存在的配置"""
        assert config_manager.validate_config("nonexistent") is False

    def test_get_default_provider(self, config_manager):
        """测试获取默认提供者"""
        default = config_manager.get_default_provider()
        assert default == "openai"  # openai优先级最高

    def test_get_default_provider_no_openai(self):
        """测试没有OpenAI时的默认提供者"""
        config_data = {
            "providers": {
                "anthropic": {
                    "provider": "anthropic",
                    "model": "claude-3-sonnet",
                    "api_key": "test-key"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config_manager = LLMConfigManager(config_file=temp_file)
            default = config_manager.get_default_provider()
            assert default == "anthropic"
        finally:
            os.unlink(temp_file)

    def test_export_config_yaml(self, config_manager):
        """测试导出YAML格式配置"""
        yaml_str = config_manager.export_config("yaml")
        assert "providers:" in yaml_str
        assert "openai:" in yaml_str
        assert "anthropic:" in yaml_str

        # 验证可以重新加载
        data = yaml.safe_load(yaml_str)
        assert "providers" in data
        assert len(data["providers"]) == 2

    def test_export_config_json(self, config_manager):
        """测试导出JSON格式配置"""
        json_str = config_manager.export_config("json")
        assert '"providers"' in json_str
        assert '"openai"' in json_str
        assert '"anthropic"' in json_str

        # 验证可以重新加载
        import json
        data = json.loads(json_str)
        assert "providers" in data
        assert len(data["providers"]) == 2

    def test_import_config_yaml(self, config_manager):
        """测试导入YAML格式配置"""
        yaml_str = """
providers:
  new_provider:
    provider: new
    model: new-model
    api_key: new-key
    temperature: 0.8
"""
        result = config_manager.import_config(yaml_str, "yaml")
        assert result is True
        assert "new_provider" in config_manager.configs

        new_config = config_manager.get_config("new_provider")
        assert new_config.provider == "new"
        assert new_config.model == "new-model"
        assert new_config.temperature == 0.8

    def test_import_config_json(self, config_manager):
        """测试导入JSON格式配置"""
        json_str = """
{
  "providers": {
    "json_provider": {
      "provider": "json",
      "model": "json-model",
      "api_key": "json-key",
      "temperature": 0.6
    }
  }
}
"""
        result = config_manager.import_config(json_str, "json")
        assert result is True
        assert "json_provider" in config_manager.configs

    def test_import_config_invalid(self, config_manager):
        """测试导入无效配置"""
        invalid_yaml = "invalid: yaml: content:"
        result = config_manager.import_config(invalid_yaml, "yaml")
        assert result is False

    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'env-openai-key',
        'OPENAI_MODEL': 'gpt-3.5-turbo',
        'ANTHROPIC_API_KEY': 'env-anthropic-key'
    })
    def test_load_from_environment(self):
        """测试从环境变量加载配置"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            # 空配置文件
            yaml.dump({"providers": {}}, f)
            temp_file = f.name

        try:
            config_manager = LLMConfigManager(config_file=temp_file)
            # 应该从环境变量加载OpenAI和Anthropic配置
            assert "openai" in config_manager.configs
            assert "anthropic" in config_manager.configs

            openai_config = config_manager.get_config("openai")
            assert openai_config.api_key == "env-openai-key"
            assert openai_config.model == "gpt-3.5-turbo"

            anthropic_config = config_manager.get_config("anthropic")
            assert anthropic_config.api_key == "env-anthropic-key"

        finally:
            os.unlink(temp_file)

    @patch.dict(os.environ, {
        'OPENAI_API_KEY': 'env-openai-key',
        'ANTHROPIC_API_KEY': 'env-anthropic-key'
    })
    def test_create_default_configs(self):
        """测试创建默认配置"""
        # 没有配置文件
        config_manager = LLMConfigManager(config_file="nonexistent.yaml")
        # 应该从环境变量创建默认配置
        assert "openai" in config_manager.configs
        assert "anthropic" in config_manager.configs

    def test_parse_config_file_data_invalid_provider(self):
        """测试解析配置文件数据中的无效提供者"""
        config_data = {
            "providers": {
                "invalid": {
                    "provider": "",  # 无效
                    "model": "test-model"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        try:
            config_manager = LLMConfigManager(config_file=temp_file)
            # 应该跳过无效配置，不会抛出异常
            assert len(config_manager.configs) == 0
        finally:
            os.unlink(temp_file)

    @patch('src.llm.config.get_config_manager')
    def test_load_from_global_config(self, mock_get_config_manager):
        """测试从全局配置加载"""
        mock_global_config = Mock()
        mock_global_config.get_section.return_value = {
            "providers": {
                "global_openai": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "api_key": "global-key"
                }
            }
        }
        mock_get_config_manager.return_value = mock_global_config

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"providers": {}}, f)
            temp_file = f.name

        try:
            config_manager = LLMConfigManager(config_file=temp_file)
            # 应该从全局配置加载
            assert "global_openai" in config_manager.configs
        finally:
            os.unlink(temp_file)