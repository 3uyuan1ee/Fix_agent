"""
LLM配置管理模块
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .base import LLMConfig
from .exceptions import LLMConfigError


class LLMConfigManager:
    """LLM配置管理器"""

    def __init__(self, config_manager=None, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_manager: 全局配置管理器
            config_file: 配置文件路径
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.config_file = config_file or "config/llm_config.yaml"

        # 加载配置
        self._load_config()

    def _load_config(self) -> None:
        """加载配置"""
        self.configs: Dict[str, LLMConfig] = {}

        # 尝试从配置文件加载
        config_path = Path(self.config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    self._parse_config_file_data(data)
                self.logger.info(f"Loaded LLM config from {config_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load LLM config file: {e}")

        # 尝试从环境变量加载
        self._load_from_environment()

        # 尝试从全局配置加载
        self._load_from_global_config()

        # 如果没有配置，创建默认配置
        if not self.configs:
            self._create_default_configs()

    def _parse_config_file_data(self, data: Dict[str, Any]) -> None:
        """解析配置文件数据"""
        if "providers" not in data:
            return

        for name, config_data in data["providers"].items():
            try:
                config = LLMConfig.from_dict(config_data)
                config.validate()
                self.configs[name] = config
                self.logger.debug(f"Loaded provider config: {name}")
            except Exception as e:
                self.logger.error(f"Failed to load provider config {name}: {e}")

    def _load_from_environment(self) -> None:
        """从环境变量加载配置"""
        # OpenAI配置
        if "OPENAI_API_KEY" in os.environ:
            openai_config = LLMConfig(
                provider="openai",
                model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                api_key=os.environ["OPENAI_API_KEY"],
                api_base=os.environ.get("OPENAI_API_BASE"),
                organization=os.environ.get("OPENAI_ORGANIZATION"),
                max_tokens=int(os.environ.get("OPENAI_MAX_TOKENS", "1000")),
                temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0.7"))
            )
            try:
                openai_config.validate()
                self.configs["openai"] = openai_config
                self.logger.info("Loaded OpenAI config from environment")
            except Exception as e:
                self.logger.error(f"Failed to load OpenAI config from environment: {e}")

        # Anthropic配置
        if "ANTHROPIC_API_KEY" in os.environ:
            anthropic_config = LLMConfig(
                provider="anthropic",
                model=os.environ.get("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
                api_key=os.environ["ANTHROPIC_API_KEY"],
                api_base=os.environ.get("ANTHROPIC_API_BASE"),
                max_tokens=int(os.environ.get("ANTHROPIC_MAX_TOKENS", "1000")),
                temperature=float(os.environ.get("ANTHROPIC_TEMPERATURE", "0.7"))
            )
            try:
                anthropic_config.validate()
                self.configs["anthropic"] = anthropic_config
                self.logger.info("Loaded Anthropic config from environment")
            except Exception as e:
                self.logger.error(f"Failed to load Anthropic config from environment: {e}")

        # 自定义提供者配置
        custom_providers = os.environ.get("LLM_PROVIDERS", "").split(",")
        for provider in custom_providers:
            provider = provider.strip()
            if not provider:
                continue

            key_prefix = f"{provider.upper()}_"
            api_key_env = f"{key_prefix}API_KEY"
            model_env = f"{key_prefix}MODEL"

            if api_key_env in os.environ:
                config = LLMConfig(
                    provider=provider.lower(),
                    model=os.environ.get(model_env, "default"),
                    api_key=os.environ[api_key_env],
                    api_base=os.environ.get(f"{key_prefix}API_BASE"),
                    max_tokens=int(os.environ.get(f"{key_prefix}MAX_TOKENS", "1000")),
                    temperature=float(os.environ.get(f"{key_prefix}TEMPERATURE", "0.7"))
                )
                try:
                    config.validate()
                    self.configs[provider.lower()] = config
                    self.logger.info(f"Loaded {provider} config from environment")
                except Exception as e:
                    self.logger.error(f"Failed to load {provider} config from environment: {e}")

    def _load_from_global_config(self) -> None:
        """从全局配置加载"""
        try:
            llm_config = self.config_manager.get_section('llm', {})
            if "providers" in llm_config:
                self._parse_config_file_data({"providers": llm_config["providers"]})
                self.logger.info("Loaded LLM config from global config")
        except Exception as e:
            self.logger.warning(f"Failed to load LLM config from global config: {e}")

    def _create_default_configs(self) -> None:
        """创建默认配置"""
        # 检查环境变量中是否有API密钥
        if "OPENAI_API_KEY" in os.environ:
            openai_config = LLMConfig(
                provider="openai",
                model="gpt-3.5-turbo",
                api_key=os.environ["OPENAI_API_KEY"]
            )
            try:
                openai_config.validate()
                self.configs["openai"] = openai_config
                self.logger.info("Created default OpenAI config")
            except Exception as e:
                self.logger.error(f"Failed to create default OpenAI config: {e}")

        if "ANTHROPIC_API_KEY" in os.environ:
            anthropic_config = LLMConfig(
                provider="anthropic",
                model="claude-3-sonnet-20240229",
                api_key=os.environ["ANTHROPIC_API_KEY"]
            )
            try:
                anthropic_config.validate()
                self.configs["anthropic"] = anthropic_config
                self.logger.info("Created default Anthropic config")
            except Exception as e:
                self.logger.error(f"Failed to create default Anthropic config: {e}")

    def get_config(self, provider: str) -> Optional[LLMConfig]:
        """
        获取提供者配置

        Args:
            provider: 提供者名称

        Returns:
            LLM配置或None
        """
        return self.configs.get(provider.lower())

    def list_providers(self) -> List[str]:
        """
        列出所有可用的提供者

        Returns:
            提供者名称列表
        """
        return list(self.configs.keys())

    def add_config(self, provider: str, config: LLMConfig) -> None:
        """
        添加提供者配置

        Args:
            provider: 提供者名称
            config: LLM配置
        """
        config.validate()
        self.configs[provider.lower()] = config
        self.logger.info(f"Added config for provider: {provider}")

    def remove_config(self, provider: str) -> bool:
        """
        移除提供者配置

        Args:
            provider: 提供者名称

        Returns:
            是否成功移除
        """
        if provider.lower() in self.configs:
            del self.configs[provider.lower()]
            self.logger.info(f"Removed config for provider: {provider}")
            return True
        return False

    def update_config(self, provider: str, updates: Dict[str, Any]) -> bool:
        """
        更新提供者配置

        Args:
            provider: 提供者名称
            updates: 更新的配置项

        Returns:
            是否成功更新
        """
        if provider.lower() not in self.configs:
            return False

        config = self.configs[provider.lower()]
        current_config = config.to_dict()
        current_config.update(updates)

        try:
            new_config = LLMConfig.from_dict(current_config)
            new_config.validate()
            self.configs[provider.lower()] = new_config
            self.logger.info(f"Updated config for provider: {provider}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update config for provider {provider}: {e}")
            return False

    def save_config(self, config_file: Optional[str] = None) -> bool:
        """
        保存配置到文件

        Args:
            config_file: 配置文件路径

        Returns:
            是否成功保存
        """
        config_file = config_file or self.config_file
        config_path = Path(config_file)

        try:
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # 准备配置数据
            data = {
                "providers": {
                    name: config.to_dict()
                    for name, config in self.configs.items()
                }
            }

            # 保存到文件
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

            self.logger.info(f"Saved LLM config to {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save config to {config_path}: {e}")
            return False

    def get_provider_models(self, provider: str) -> List[str]:
        """
        获取提供者支持的模型列表

        Args:
            provider: 提供者名称

        Returns:
            模型列表
        """
        # 这里可以扩展为从API获取可用模型
        # 目前返回一些常见的模型
        models = {
            "openai": [
                "gpt-4",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-4-32k",
                "text-davinci-003",
                "text-curie-001"
            ],
            "anthropic": [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2"
            ]
        }
        return models.get(provider.lower(), [])

    def validate_config(self, provider: str) -> bool:
        """
        验证提供者配置

        Args:
            provider: 提供者名称

        Returns:
            配置是否有效
        """
        config = self.get_config(provider)
        if not config:
            return False

        try:
            config.validate()
            return True
        except Exception:
            return False

    def get_default_provider(self) -> Optional[str]:
        """
        获取默认提供者

        Returns:
            默认提供者名称
        """
        # 优先级：openai > anthropic > 第一个可用的
        preferred_order = ["openai", "anthropic"]
        for provider in preferred_order:
            if provider in self.configs:
                return provider

        return next(iter(self.configs.keys())) if self.configs else None

    def export_config(self, format: str = "yaml") -> str:
        """
        导出配置

        Args:
            format: 导出格式 (yaml, json)

        Returns:
            配置字符串
        """
        data = {
            "providers": {
                name: config.to_dict()
                for name, config in self.configs.items()
            }
        }

        if format.lower() == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)

    def import_config(self, config_str: str, format: str = "yaml") -> bool:
        """
        导入配置

        Args:
            config_str: 配置字符串
            format: 配置格式 (yaml, json)

        Returns:
            是否成功导入
        """
        try:
            if format.lower() == "json":
                data = json.loads(config_str)
            else:
                data = yaml.safe_load(config_str)

            self._parse_config_file_data(data)
            self.logger.info(f"Imported {len(self.configs)} provider configs")
            return True
        except Exception as e:
            self.logger.error(f"Failed to import config: {e}")
            return False