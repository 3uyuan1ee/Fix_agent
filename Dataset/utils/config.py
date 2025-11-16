"""
简化的配置管理模块

提供基本的配置加载和管理功能。
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """简化的配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = Path(config_path or "./config.json")
        self.config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """加载配置"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = self._get_default_config()
                self.save()
        except Exception:
            self.config = self._get_default_config()

        return self.config

    def save(self) -> bool:
        """保存配置"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        if not self.config:
            self.load()

        keys = key.split('.')
        value = self.config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def _get_default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            "agent": {
                "model": "gpt-4",
                "api_key": "",
                "api_base": "https://api.openai.com/v1/",
                "temperature": 0.1,
                "max_tokens": 4000
            },
            "evaluation": {
                "default_timeout": 300,
                "max_workers": 4,
                "enable_caching": True
            }
        }


# 全局配置实例
config = Config()