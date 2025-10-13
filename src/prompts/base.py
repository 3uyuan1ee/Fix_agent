"""
Prompt模板基础类和数据结构
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import re


class PromptCategory(Enum):
    """Prompt模板类别"""
    STATIC_ANALYSIS = "static_analysis"
    DEEP_ANALYSIS = "deep_analysis"
    REPAIR_SUGGESTION = "repair_suggestion"
    CODE_GENERATION = "code_generation"
    TESTING = "testing"
    DOCUMENTATION = "documentation"


class PromptType(Enum):
    """Prompt模板类型"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


@dataclass
class PromptTemplate:
    """Prompt模板数据类"""
    name: str
    category: PromptCategory
    prompt_type: PromptType
    template: str
    description: str = ""
    parameters: Dict[str, str] = field(default_factory=dict)
    version: str = "1.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.template:
            raise ValueError("Template content cannot be empty")

        # 从模板中提取参数并与手动设置的参数合并
        extracted_params = self._extract_parameters()
        # 保留手动设置的参数描述，添加自动提取的新参数
        for param, description in extracted_params.items():
            if param not in self.parameters:
                self.parameters[param] = description

    def _extract_parameters(self) -> Dict[str, str]:
        """从模板中提取参数"""
        # 匹配 {{parameter}} 格式的参数，匹配所有有效的参数名
        pattern = r'\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}'
        matches = re.findall(pattern, self.template)

        parameters = {}
        for param in matches:
            parameters[param] = f"Parameter '{param}' to be replaced"

        return parameters

    def validate_parameters(self, values: Dict[str, Any]) -> List[str]:
        """
        验证参数是否完整

        Args:
            values: 参数值字典

        Returns:
            缺失的参数列表
        """
        missing_params = []
        for param in self.parameters:
            if param not in values:
                missing_params.append(param)
        return missing_params

    def get_required_parameters(self) -> List[str]:
        """获取必需参数列表"""
        return list(self.parameters.keys())

    def has_parameters(self) -> bool:
        """检查模板是否有参数"""
        return len(self.parameters) > 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "category": self.category.value,
            "prompt_type": self.prompt_type.value,
            "template": self.template,
            "description": self.description,
            "parameters": self.parameters,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """从字典创建模板"""
        # 转换枚举值
        if isinstance(data.get("category"), str):
            data["category"] = PromptCategory(data["category"])
        if isinstance(data.get("prompt_type"), str):
            data["prompt_type"] = PromptType(data["prompt_type"])

        return cls(**data)


@dataclass
class PromptRenderResult:
    """Prompt渲染结果"""
    content: str
    template_name: str
    parameters_used: Dict[str, Any]
    render_time: float = 0.0
    success: bool = True
    error_message: Optional[str] = None
    missing_parameters: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "content": self.content,
            "template_name": self.template_name,
            "parameters_used": self.parameters_used,
            "render_time": self.render_time,
            "success": self.success,
            "error_message": self.error_message,
            "missing_parameters": self.missing_parameters
        }


class PromptRenderer(ABC):
    """Prompt渲染器抽象基类"""

    @abstractmethod
    def render(self, template: PromptTemplate, parameters: Dict[str, Any]) -> PromptRenderResult:
        """
        渲染模板

        Args:
            template: Prompt模板
            parameters: 参数值

        Returns:
            渲染结果
        """
        pass

    @abstractmethod
    def validate_template(self, template: PromptTemplate) -> List[str]:
        """
        验证模板

        Args:
            template: Prompt模板

        Returns:
            验证错误列表
        """
        pass


class BasePromptRenderer(PromptRenderer):
    """基础Prompt渲染器实现"""

    def __init__(self):
        self.delimiter_start = "{{"
        self.delimiter_end = "}}"

    def render(self, template: PromptTemplate, parameters: Dict[str, Any]) -> PromptRenderResult:
        """
        渲染模板

        Args:
            template: Prompt模板
            parameters: 参数值

        Returns:
            渲染结果
        """
        import time
        start_time = time.time()

        try:
            # 验证参数
            missing_params = template.validate_parameters(parameters)
            if missing_params:
                return PromptRenderResult(
                    content="",
                    template_name=template.name,
                    parameters_used={},
                    success=False,
                    error_message=f"Missing required parameters: {', '.join(missing_params)}",
                    missing_parameters=missing_params
                )

            # 执行渲染
            content = template.template
            used_parameters = {}

            for param_name, param_value in parameters.items():
                if param_name in template.parameters:
                    placeholder = f"{self.delimiter_start}{param_name}{self.delimiter_end}"
                    content = content.replace(placeholder, str(param_value))
                    used_parameters[param_name] = param_value

            render_time = time.time() - start_time

            return PromptRenderResult(
                content=content,
                template_name=template.name,
                parameters_used=used_parameters,
                render_time=render_time,
                success=True
            )

        except Exception as e:
            return PromptRenderResult(
                content="",
                template_name=template.name,
                parameters_used={},
                success=False,
                error_message=str(e)
            )

    def validate_template(self, template: PromptTemplate) -> List[str]:
        """
        验证模板

        Args:
            template: Prompt模板

        Returns:
            验证错误列表
        """
        errors = []

        if not template.name:
            errors.append("Template name cannot be empty")

        if not template.template:
            errors.append("Template content cannot be empty")

        # 验证参数格式
        pattern = re.escape(self.delimiter_start) + r'([^}]+)' + re.escape(self.delimiter_end)
        matches = re.findall(pattern, template.template)

        for match in matches:
            if not re.match(r'^[a-zA-Z_]\w*$', match):
                errors.append(f"Invalid parameter name: '{match}'")

        return errors