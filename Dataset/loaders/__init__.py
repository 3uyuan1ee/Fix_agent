"""
数据集加载器模块

支持多种标准数据集的加载和预处理：
- SWE-bench: GitHub真实issue和PR数据集
- BugsInPy: Python项目bug修复数据集
- 其他可扩展的数据集格式
"""

from .swe_bench import SWEBenchLoader
from .bugs_in_py import BugsInPyLoader
from .base import BaseDatasetLoader

__all__ = [
    "BaseDatasetLoader",
    "SWEBenchLoader",
    "BugsInPyLoader"
]