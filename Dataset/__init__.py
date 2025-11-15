"""
Fix Agent 数据集评估模块

这个模块提供了独立的数据集评估框架，用于在SWE-bench和BugsInPy等标准数据集上评估Fix Agent的性能。
完全独立于主项目的交互式界面，专为自动化评估设计。

主要组件：
- DatasetAgent: 独立的agent实现
- DatasetLoader: 数据集加载器
- EvaluationFramework: 评估框架
- MetricsCalculator: 指标计算器
"""

__version__ = "1.0.0"
__author__ = "Fix Agent Team"

from .core.agent import DatasetAgent
from .core.evaluation import EvaluationFramework
from .loaders.bugs_in_py import BugsInPyLoader
from .loaders.swe_bench import SWEBenchLoader
from .utils.metrics import MetricsCalculator

__all__ = [
    "DatasetAgent",
    "EvaluationFramework",
    "SWEBenchLoader",
    "BugsInPyLoader",
    "MetricsCalculator",
]
