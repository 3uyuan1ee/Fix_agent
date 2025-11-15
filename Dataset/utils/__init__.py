"""
工具模块 - 评估相关的工具和实用函数
"""

# 尝试导入完整版本，失败则使用简化版本
try:
    from .metrics import MetricsCalculator
    from .visualization import EvaluationVisualizer
    _full_version = True
    print("[Utils] 使用完整版工具（需要matplotlib等依赖）")
except ImportError:
    from .metrics_simple import MetricsCalculator
    from .visualization_simple import EvaluationVisualizer
    _full_version = False
    print("[Utils] 使用简化版工具（无外部依赖）")

from .config import EvaluationConfig, ConfigManager

__all__ = [
    "MetricsCalculator",
    "EvaluationVisualizer",
    "EvaluationConfig",
    "ConfigManager",
    "_full_version"  # 导出版本标识
]