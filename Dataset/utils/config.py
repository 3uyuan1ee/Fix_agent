"""
评估配置管理

提供配置文件的加载、验证和管理功能。
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

@dataclass
class EvaluationConfig:
    """评估配置类"""

    # Agent配置
    model: str = "gpt-4"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 4000

    # 评估配置
    default_timeout: int = 300
    max_workers: int = 4
    enable_caching: bool = True
    cache_dir: str = "./cache"
    auto_cleanup: bool = True

    # 数据集配置
    swe_bench_samples: int = 100
    bugs_in_py_samples: int = 50

    # 输出配置
    default_dir: str = "./evaluation_results"
    save_intermediate_results: bool = True
    generate_visualizations: bool = False
    save_agent_logs: bool = True

    # 性能配置
    enable_profiling: bool = False
    memory_limit_gb: int = 8
    monitor_system_resources: bool = True

    # 日志配置
    log_level: str = "INFO"
    log_file: str = "evaluation.log"

class ConfigManager:
    """配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = EvaluationConfig()

        if config_file and Path(config_file).exists():
            self.load_config(config_file)

    def load_config(self, config_file: str) -> bool:
        """
        加载配置文件

        Args:
            config_file: 配置文件路径

        Returns:
            bool: 是否加载成功
        """
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 更新配置
            self._update_config_from_dict(data)

            # 验证配置
            self.validate_config()

            print(f"[ConfigManager] 配置已从 {config_file} 加载")
            return True

        except Exception as e:
            print(f"[ConfigManager] 配置加载失败: {e}")
            return False

    def _update_config_from_dict(self, data: Dict[str, Any]):
        """从字典更新配置"""

        # Agent配置
        if 'agent' in data:
            agent_config = data['agent']
            for key in ['model', 'api_key', 'api_base', 'temperature', 'max_tokens']:
                if key in agent_config:
                    setattr(self.config, key, agent_config[key])

        # 评估配置
        if 'evaluation' in data:
            eval_config = data['evaluation']
            for key in ['default_timeout', 'max_workers', 'enable_caching', 'cache_dir', 'auto_cleanup']:
                if key in eval_config:
                    setattr(self.config, key, eval_config[key])

        # 数据集配置
        if 'dataset' in data:
            dataset_config = data['dataset']
            if 'swe_bench' in dataset_config:
                swe_config = dataset_config['swe_bench']
                if 'default_samples' in swe_config:
                    self.config.swe_bench_samples = swe_config['default_samples']

            if 'bugs_in_py' in dataset_config:
                bug_config = dataset_config['bugs_in_py']
                if 'default_samples' in bug_config:
                    self.config.bugs_in_py_samples = bug_config['default_samples']

        # 输出配置
        if 'output' in data:
            output_config = data['output']
            for key in ['default_dir', 'save_intermediate_results', 'generate_visualizations', 'save_agent_logs']:
                if key in output_config:
                    setattr(self.config, key, output_config[key])

        # 性能配置
        if 'performance' in data:
            perf_config = data['performance']
            for key in ['enable_profiling', 'memory_limit_gb', 'monitor_system_resources']:
                if key in perf_config:
                    setattr(self.config, key, perf_config[key])

        # 日志配置
        if 'logging' in data:
            log_config = data['logging']
            for key in ['level', 'file', 'format']:
                if key in log_config:
                    attr_name = f"log_{key}" if key != 'level' else 'log_level'
                    setattr(self.config, attr_name, log_config[key])

    def validate_config(self):
        """验证配置的有效性"""

        # 验证基本参数
        if self.config.max_workers < 1:
            raise ValueError("max_workers must be at least 1")

        if self.config.default_timeout < 30:
            raise ValueError("default_timeout must be at least 30 seconds")

        if self.config.temperature < 0 or self.config.temperature > 2:
            raise ValueError("temperature must be between 0 and 2")

        if self.config.max_tokens < 100:
            raise ValueError("max_tokens must be at least 100")

        # 验证路径
        Path(self.config.cache_dir).mkdir(parents=True, exist_ok=True)
        Path(self.config.default_dir).mkdir(parents=True, exist_ok=True)

    def get_agent_config(self) -> Dict[str, Any]:
        """获取Agent配置"""
        return {
            "model": self.config.model,
            "api_key": self.config.api_key or os.getenv("OPENAI_API_KEY"),
            "api_base": self.config.api_base or os.getenv("OPENAI_API_BASE"),
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens
        }

    def get_evaluation_config(self) -> Dict[str, Any]:
        """获取评估配置"""
        return {
            "default_timeout": self.config.default_timeout,
            "max_workers": self.config.max_workers,
            "enable_caching": self.config.enable_caching,
            "cache_dir": self.config.cache_dir,
            "auto_cleanup": self.config.auto_cleanup
        }

    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        return {
            "default_dir": self.config.default_dir,
            "save_intermediate_results": self.config.save_intermediate_results,
            "generate_visualizations": self.config.generate_visualizations,
            "save_agent_logs": self.config.save_agent_logs
        }

    def save_config(self, output_file: str):
        """保存配置到文件"""

        config_dict = {
            "agent": {
                "model": self.config.model,
                "api_key": self.config.api_key,
                "api_base": self.config.api_base,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            },
            "evaluation": {
                "default_timeout": self.config.default_timeout,
                "max_workers": self.config.max_workers,
                "enable_caching": self.config.enable_caching,
                "cache_dir": self.config.cache_dir,
                "auto_cleanup": self.config.auto_cleanup
            },
            "dataset": {
                "swe_bench": {
                    "default_samples": self.config.swe_bench_samples
                },
                "bugs_in_py": {
                    "default_samples": self.config.bugs_in_py_samples
                }
            },
            "output": {
                "default_dir": self.config.default_dir,
                "save_intermediate_results": self.config.save_intermediate_results,
                "generate_visualizations": self.config.generate_visualizations,
                "save_agent_logs": self.config.save_agent_logs
            },
            "performance": {
                "enable_profiling": self.config.enable_profiling,
                "memory_limit_gb": self.config.memory_limit_gb,
                "monitor_system_resources": self.config.monitor_system_resources
            },
            "logging": {
                "level": self.config.log_level,
                "file": self.config.log_file
            }
        }

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)

            print(f"[ConfigManager] 配置已保存到 {output_file}")

        except Exception as e:
            print(f"[ConfigManager] 配置保存失败: {e}")

    def update_config(self, **kwargs):
        """更新配置

        Args:
            **kwargs: 配置参数
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                print(f"[ConfigManager] 配置更新: {key} = {value}")
            else:
                print(f"[ConfigManager] 未知配置项: {key}")

    def print_config(self):
        """打印当前配置"""
        print(f"[ConfigManager] 当前配置:")
        print(f"  模型: {self.config.model}")
        print(f"  超时时间: {self.config.default_timeout}秒")
        print(f"  工作线程数: {self.config.max_workers}")
        print(f"  缓存目录: {self.config.cache_dir}")
        print(f"  输出目录: {self.config.default_dir}")
        print(f"  日志级别: {self.config.log_level}")

# 全局配置实例
_global_config = None

def get_config(config_file: Optional[str] = None) -> ConfigManager:
    """获取全局配置实例"""
    global _global_config

    if _global_config is None or config_file:
        _global_config = ConfigManager(config_file)

    return _global_config

def reset_config():
    """重置全局配置"""
    global _global_config
    _global_config = None