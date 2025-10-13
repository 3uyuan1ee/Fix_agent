"""
配置管理模块单元测试
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path
from src.utils.config import ConfigManager, ConfigException


class TestConfigManager:
    """配置管理器测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_manager = ConfigManager(self.temp_dir)

        # 创建测试用的默认配置文件
        self.default_config = {
            'app': {
                'name': 'TestApp',
                'version': '1.0.0',
                'debug': False
            },
            'llm': {
                'default_provider': 'openai',
                'openai': {
                    'api_key': '${OPENAI_API_KEY:test-key}',
                    'model': 'gpt-4'
                }
            },
            'logging': {
                'level': 'INFO',
                'file_path': 'test.log'
            },
            'static_analysis': {
                'enabled_tools': ['ast', 'pylint']
            }
        }

        default_config_path = Path(self.temp_dir) / "default.yaml"
        with open(default_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.default_config, f)

    def test_load_default_config_success(self):
        """测试成功加载默认配置"""
        config = self.config_manager.load_config()

        assert config is not None
        assert config['app']['name'] == 'TestApp'
        assert config['app']['version'] == '1.0.0'
        assert config['llm']['default_provider'] == 'openai'

    def test_load_config_with_user_override(self):
        """测试用户配置覆盖默认配置"""
        # 创建用户配置文件
        user_config = {
            'app': {
                'debug': True,
                'new_setting': 'user_value'
            },
            'llm': {
                'default_provider': 'anthropic'
            }
        }

        user_config_path = Path(self.temp_dir) / "user_config.yaml"
        with open(user_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(user_config, f)

        config = self.config_manager.load_config()

        # 验证覆盖效果
        assert config['app']['name'] == 'TestApp'  # 保持默认值
        assert config['app']['debug'] is True      # 用户覆盖
        assert config['app']['new_setting'] == 'user_value'  # 用户新增
        assert config['llm']['default_provider'] == 'anthropic'  # 用户覆盖

    def test_env_var_substitution(self):
        """测试环境变量替换"""
        # 设置环境变量
        os.environ['TEST_API_KEY'] = 'env-api-key-value'

        try:
            # 创建包含环境变量的默认配置文件
            config_with_env = {
                'api': {
                    'key': '${TEST_API_KEY}',
                    'url': '${TEST_URL:http://default}'
                },
                'app': {
                    'name': 'TestApp'
                }
            }

            config_path = Path(self.temp_dir) / "default.yaml"
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_with_env, f)

            test_manager = ConfigManager(self.temp_dir)
            config = test_manager.load_config()

            assert config['api']['key'] == 'env-api-key-value'
            assert config['api']['url'] == 'http://default'

        finally:
            # 清理环境变量
            if 'TEST_API_KEY' in os.environ:
                del os.environ['TEST_API_KEY']

    def test_get_config_value_success(self):
        """测试成功获取配置值"""
        self.config_manager.load_config()

        # 测试简单键
        assert self.config_manager.get('app.name') == 'TestApp'
        assert self.config_manager.get('app.debug') is False

        # 测试嵌套键
        assert self.config_manager.get('llm.openai.model') == 'gpt-4'

        # 测试不存在的键
        assert self.config_manager.get('nonexistent.key') is None
        assert self.config_manager.get('nonexistent.key', 'default') == 'default'

    def test_get_section_config_success(self):
        """测试成功获取配置段"""
        self.config_manager.load_config()

        app_section = self.config_manager.get_section('app')
        assert app_section is not None
        assert app_section['name'] == 'TestApp'
        assert app_section['version'] == '1.0.0'

        llm_section = self.config_manager.get_section('llm')
        assert llm_section['default_provider'] == 'openai'

    def test_load_config_file_not_exists(self):
        """测试配置文件不存在的情况"""
        invalid_manager = ConfigManager('/nonexistent/path')

        with pytest.raises(ConfigException) as exc_info:
            invalid_manager.load_config()

        assert '默认配置文件不存在' in str(exc_info.value)

    def test_load_config_invalid_yaml(self):
        """测试无效YAML文件"""
        # 创建无效的YAML文件
        invalid_config_path = Path(self.temp_dir) / "default.yaml"
        with open(invalid_config_path, 'w', encoding='utf-8') as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ConfigException) as exc_info:
            self.config_manager.load_config()

        assert 'YAML解析错误' in str(exc_info.value)

    def test_get_config_before_load(self):
        """测试在加载配置前获取配置值"""
        with pytest.raises(ConfigException) as exc_info:
            self.config_manager.get('app.name')

        assert '配置未加载' in str(exc_info.value)

    def test_validate_config_success(self):
        """测试配置验证成功"""
        # 添加必需的配置段
        self.config_manager.load_config()

        # 临时设置环境变量以通过验证
        os.environ['OPENAI_API_KEY'] = 'test-key'

        try:
            is_valid = self.config_manager.validate_config()
            assert is_valid is True
        finally:
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']

    def test_validate_config_missing_section(self):
        """测试配置验证失败 - 缺少必需段"""
        # 创建不完整的配置
        incomplete_config = {
            'app': {'name': 'TestApp'}
            # 缺少必需的段
        }

        default_config_path = Path(self.temp_dir) / "default.yaml"
        with open(default_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(incomplete_config, f)

        self.config_manager.load_config()

        with pytest.raises(ConfigException) as exc_info:
            self.config_manager.validate_config()

        assert '缺少必需的配置段' in str(exc_info.value)

    def test_validate_config_missing_api_key(self):
        """测试配置验证失败 - 缺少API密钥"""
        # 创建没有API密钥的配置
        config_no_api_key = {
            'app': {'name': 'TestApp'},
            'llm': {
                'default_provider': 'openai',
                'openai': {
                    'api_key': '${OPENAI_API_KEY:}',  # 空默认值
                    'model': 'gpt-4'
                }
            },
            'logging': {'level': 'INFO'},
            'static_analysis': {'enabled_tools': ['ast']}
        }

        default_config_path = Path(self.temp_dir) / "default.yaml"
        with open(default_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_no_api_key, f)

        # 确保没有设置环境变量
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        if 'ANTHROPIC_API_KEY' in os.environ:
            del os.environ['ANTHROPIC_API_KEY']

        # 重新加载配置
        self.config_manager.load_config()

        with pytest.raises(ConfigException) as exc_info:
            self.config_manager.validate_config()

        assert '未配置LLM API密钥' in str(exc_info.value)

    def test_reload_config(self):
        """测试重新加载配置"""
        # 初始加载
        config1 = self.config_manager.load_config()
        assert config1['app']['name'] == 'TestApp'

        # 修改配置文件
        modified_config = self.default_config.copy()
        modified_config['app']['name'] = 'ModifiedApp'

        default_config_path = Path(self.temp_dir) / "default.yaml"
        with open(default_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(modified_config, f)

        # 重新加载
        config2 = self.config_manager.reload_config()
        assert config2['app']['name'] == 'ModifiedApp'