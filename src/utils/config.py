"""
配置管理模块
实现配置读取和管理功能，支持YAML配置文件和环境变量覆盖
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from string import Template


class ConfigException(Exception):
    """配置异常"""
    pass


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = "config"):
        """
        初始化配置管理器

        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = self._find_project_root() / Path(config_dir)
        self.default_config = None
        self.user_config = None
        self._config = None

    def _find_project_root(self) -> Path:
        """
        查找项目根目录

        Returns:
            项目根目录路径
        """
        # 从当前文件开始向上查找项目根目录
        current_path = Path(__file__).parent

        # 查找包含 config/default.yaml 的目录
        while current_path.parent != current_path:
            potential_root = current_path.parent
            if (potential_root / "config" / "default.yaml").exists():
                return potential_root
            current_path = potential_root

        # 如果没找到，尝试从当前工作目录查找
        current_dir = Path.cwd()
        while current_dir.parent != current_dir:
            if (current_dir / "config" / "default.yaml").exists():
                return current_dir
            current_dir = current_dir.parent

        # 最后的备选方案：假设当前目录就是项目根目录
        return Path.cwd()

    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件

        Returns:
            合并后的配置字典

        Raises:
            ConfigException: 配置加载失败
        """
        try:
            # 加载默认配置
            default_config_path = self.config_dir / "default.yaml"
            if not default_config_path.exists():
                raise ConfigException(f"默认配置文件不存在: {default_config_path}")

            with open(default_config_path, 'r', encoding='utf-8') as f:
                self.default_config = yaml.safe_load(f)

            # 加载用户配置
            user_config_path = self.config_dir / "user_config.yaml"
            self.user_config = {}
            if user_config_path.exists():
                with open(user_config_path, 'r', encoding='utf-8') as f:
                    self.user_config = yaml.safe_load(f) or {}

            # 合并配置
            self._config = self._merge_configs(self.default_config, self.user_config)

            # 处理环境变量替换
            self._config = self._substitute_env_vars(self._config)

            return self._config

        except yaml.YAMLError as e:
            raise ConfigException(f"YAML解析错误: {e}")
        except Exception as e:
            raise ConfigException(f"配置加载失败: {e}")

    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并默认配置和用户配置

        Args:
            default: 默认配置
            user: 用户配置

        Returns:
            合并后的配置
        """
        result = default.copy()

        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _substitute_env_vars(self, config: Any) -> Any:
        """
        递归替换配置中的环境变量

        Args:
            config: 配置对象

        Returns:
            替换环境变量后的配置
        """
        if isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith("${") and config.endswith("}"):
            # 提取环境变量名
            env_var = config[2:-1]
            # 支持默认值，格式: ${VAR_NAME:default_value}
            if ":" in env_var:
                var_name, default_value = env_var.split(":", 1)
                return os.getenv(var_name.strip(), default_value)
            else:
                return os.getenv(env_var.strip(), "")
        else:
            return config

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'app.name'
            default: 默认值

        Returns:
            配置值

        Raises:
            ConfigException: 配置未加载
        """
        if self._config is None:
            raise ConfigException("配置未加载，请先调用 load_config()")

        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取配置段

        Args:
            section: 配置段名称

        Returns:
            配置段字典
        """
        return self.get(section, {})

    def reload_config(self) -> Dict[str, Any]:
        """
        重新加载配置

        Returns:
            重新加载的配置
        """
        return self.load_config()

    def validate_config(self) -> bool:
        """
        验证配置的完整性

        Returns:
            配置是否有效
        """
        required_sections = ['app', 'logging', 'llm', 'static_analysis']

        for section in required_sections:
            if section not in self._config:
                raise ConfigException(f"缺少必需的配置段: {section}")

        # 验证LLM配置
        llm_config = self.get_section('llm')
        default_provider = llm_config.get('default_provider')
        provider_config = llm_config.get(default_provider, {})

        api_key = provider_config.get('api_key', '')
        if not api_key or api_key.strip() == '':
            # 检查环境变量
            env_var = f"{default_provider.upper()}_API_KEY"
            if not os.getenv(env_var):
                raise ConfigException("未配置LLM API密钥")

        return True


# 全局配置管理器实例
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """
    获取全局配置管理器实例

    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load_config()
    return _config_manager


def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值的便捷函数

    Args:
        key: 配置键
        default: 默认值

    Returns:
        配置值
    """
    return get_config_manager().get(key, default)


def get_section_config(section: str) -> Dict[str, Any]:
    """
    获取配置段的便捷函数

    Args:
        section: 配置段名称

    Returns:
        配置段字典
    """
    return get_config_manager().get_section(section)