"""
Prompt管理系统模块
提供针对不同任务的prompt模板管理功能
"""

from .base import BasePromptRenderer, PromptCategory, PromptTemplate, PromptType
from .manager import PromptManager
from .renderer import (
    AdvancedPromptRenderer,
    ConditionalPromptRenderer,
    TemplateFunctionRenderer,
)
from .templates import (
    DeepAnalysisTemplate,
    RepairSuggestionTemplate,
    StaticAnalysisTemplate,
)

__all__ = [
    "PromptTemplate",
    "PromptCategory",
    "PromptType",
    "BasePromptRenderer",
    "AdvancedPromptRenderer",
    "ConditionalPromptRenderer",
    "TemplateFunctionRenderer",
    "PromptManager",
    "StaticAnalysisTemplate",
    "DeepAnalysisTemplate",
    "RepairSuggestionTemplate",
]
