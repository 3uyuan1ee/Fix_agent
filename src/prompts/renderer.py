"""
Prompt渲染器实现
"""

import time
import re
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass

from .base import PromptTemplate, PromptRenderResult, PromptRenderer


class AdvancedPromptRenderer(PromptRenderer):
    """高级Prompt渲染器，支持更多功能"""

    def __init__(self,
                 delimiter_start: str = "{{",
                 delimiter_end: str = "}}",
                 strict_mode: bool = True):
        """
        初始化渲染器

        Args:
            delimiter_start: 参数开始分隔符
            delimiter_end: 参数结束分隔符
            strict_mode: 严格模式，未定义参数是否报错
        """
        self.delimiter_start = delimiter_start
        self.delimiter_end = delimiter_end
        self.strict_mode = strict_mode

    def render(self, template: PromptTemplate, parameters: Dict[str, Any]) -> PromptRenderResult:
        """
        渲染模板

        Args:
            template: Prompt模板
            parameters: 参数值

        Returns:
            渲染结果
        """
        start_time = time.time()

        try:
            # 验证必需参数
            missing_params = template.validate_parameters(parameters)
            if missing_params and self.strict_mode:
                return PromptRenderResult(
                    content="",
                    template_name=template.name,
                    parameters_used={},
                    success=False,
                    error_message=f"Missing required parameters: {', '.join(missing_params)}",
                    missing_parameters=missing_params
                )

            # 预处理参数
            processed_params = self._preprocess_parameters(parameters)

            # 执行渲染
            content = self._render_content(template.template, processed_params)

            # 后处理
            content = self._postprocess_content(content)

            render_time = time.time() - start_time

            return PromptRenderResult(
                content=content,
                template_name=template.name,
                parameters_used=processed_params,
                render_time=render_time,
                success=True,
                missing_parameters=missing_params
            )

        except Exception as e:
            return PromptRenderResult(
                content="",
                template_name=template.name,
                parameters_used={},
                success=False,
                error_message=str(e)
            )

    def _preprocess_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """预处理参数"""
        processed = {}

        for key, value in parameters.items():
            # 处理复杂类型的参数
            if isinstance(value, (dict, list)):
                processed[key] = self._format_complex_value(value)
            elif isinstance(value, bool):
                processed[key] = str(value).lower()
            else:
                processed[key] = str(value)

        return processed

    def _format_complex_value(self, value: Union[dict, list]) -> str:
        """格式化复杂类型的值"""
        if isinstance(value, dict):
            return "\n".join([f"{k}: {v}" for k, v in value.items()])
        elif isinstance(value, list):
            return "\n".join([f"- {item}" for item in value])
        else:
            return str(value)

    def _render_content(self, template: str, parameters: Dict[str, Any]) -> str:
        """渲染模板内容"""
        content = template

        # 构建正则表达式模式
        pattern = re.escape(self.delimiter_start) + r'(\w+)' + re.escape(self.delimiter_end)

        def replace_match(match):
            param_name = match.group(1)
            if param_name in parameters:
                return str(parameters[param_name])
            elif self.strict_mode:
                raise ValueError(f"Undefined parameter: {param_name}")
            else:
                return match.group(0)  # 保留原始占位符

        # 替换所有参数
        content = re.sub(pattern, replace_match, content)

        return content

    def _postprocess_content(self, content: str) -> str:
        """后处理内容"""
        # 清理多余的空行
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)

        # 清理首尾空白
        content = content.strip()

        return content

    def validate_template(self, template: PromptTemplate) -> List[str]:
        """
        验证模板

        Args:
            template: Prompt模板

        Returns:
            验证错误列表
        """
        errors = []

        # 基础验证
        if not template.name:
            errors.append("Template name cannot be empty")

        if not template.template:
            errors.append("Template content cannot be empty")

        # 参数格式验证
        pattern = re.escape(self.delimiter_start) + r'([^}{]*)' + re.escape(self.delimiter_end)
        matches = re.findall(pattern, template.template)

        for match in matches:
            if not re.match(r'^[a-zA-Z_]\w*$', match):
                errors.append(f"Invalid parameter name: '{match}'. Must start with letter or underscore and contain only alphanumeric characters and underscores.")

        # 检查未闭合的占位符
        open_count = template.template.count(self.delimiter_start)
        close_count = template.template.count(self.delimiter_end)
        if open_count != close_count:
            errors.append(f"Mismatched delimiters: {open_count} opening, {close_count} closing")

        return errors


class ConditionalPromptRenderer(AdvancedPromptRenderer):
    """支持条件渲染的Prompt渲染器"""

    def render(self, template: PromptTemplate, parameters: Dict[str, Any]) -> PromptRenderResult:
        """
        重写render方法以支持条件渲染的特殊参数验证逻辑
        """
        start_time = time.time()

        try:
            # 对于条件渲染器，只验证顶级参数，不验证循环内的参数
            missing_params = self._validate_top_level_parameters(template, parameters)
            if missing_params and self.strict_mode:
                return PromptRenderResult(
                    content="",
                    template_name=template.name,
                    parameters_used={},
                    success=False,
                    error_message=f"Missing required parameters: {', '.join(missing_params)}",
                    missing_parameters=missing_params
                )

            # 执行渲染，传入原始参数（不预处理，保持嵌套结构）
            content = self._render_content(template.template, parameters)

            # 后处理
            content = self._postprocess_content(content)

            render_time = time.time() - start_time

            # 记录使用的参数（原始参数）
            used_params = {}
            for param_name in parameters:
                used_params[param_name] = parameters[param_name]

            return PromptRenderResult(
                content=content,
                template_name=template.name,
                parameters_used=used_params,
                render_time=render_time,
                success=True,
                missing_parameters=missing_params
            )

        except Exception as e:
            return PromptRenderResult(
                content="",
                template_name=template.name,
                parameters_used={},
                success=False,
                error_message=str(e)
            )

    def _validate_top_level_parameters(self, template: PromptTemplate, parameters: Dict[str, Any]) -> List[str]:
        """只验证顶级参数，不包括循环内部的参数"""
        # 提取顶级参数（不在循环内部的参数）
        top_level_params = set()

        # 先移除循环块
        temp_content = re.sub(r'\{\{#each\s+\w+\}\}.*?\{\{/each\}', '', template.template, flags=re.DOTALL)

        # 再移除条件块
        temp_content = re.sub(r'\{\{#if\s+\w+\}\}.*?\{\{/if\}', '', temp_content, flags=re.DOTALL)

        # 提取剩余的参数
        pattern = re.escape(self.delimiter_start) + r'(\w+)' + re.escape(self.delimiter_end)
        matches = re.findall(pattern, temp_content)
        top_level_params.update(matches)

        # 检查缺失的参数
        missing_params = []
        for param in top_level_params:
            if param not in parameters:
                missing_params.append(param)

        return missing_params

    def _render_content(self, template: str, parameters: Dict[str, Any]) -> str:
        """支持条件渲染的内容渲染"""
        content = template

        # 处理条件块 {{#if condition}} ... {{/if}}
        content = self._render_conditionals(content, parameters)

        # 处理循环块 {{#each items}} ... {{/each}}
        content = self._render_loops(content, parameters)

        # 处理普通参数
        content = super()._render_content(content, parameters)

        return content

    def _render_conditionals(self, content: str, parameters: Dict[str, Any]) -> str:
        """渲染条件块"""
        pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}'

        def replace_conditional(match):
            param_name = match.group(1)
            conditional_content = match.group(2)

            if param_name in parameters and parameters[param_name]:
                # 递归渲染条件块内的内容
                return self._render_nested_content(conditional_content, parameters)
            else:
                return ""

        return re.sub(pattern, replace_conditional, content, flags=re.DOTALL)

    def _render_loops(self, content: str, parameters: Dict[str, Any]) -> str:
        """渲染循环块"""
        pattern = r'\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}'

        def replace_loop(match):
            param_name = match.group(1)
            loop_content = match.group(2)

            if param_name in parameters and isinstance(parameters[param_name], list):
                result = []
                for index, item in enumerate(parameters[param_name]):
                    # 简单的变量替换，支持对象属性、{{this}}、{{.}}和index
                    item_content = loop_content
                    if isinstance(item, dict):
                        # 替换对象属性
                        for key, value in item.items():
                            item_content = item_content.replace(f"{{{{{key}}}}}", str(value))
                        # 替换index相关
                        item_content = item_content.replace("{{index}}", str(index))
                        item_content = item_content.replace("{{index + 1}}", str(index + 1))
                    else:
                        item_content = item_content.replace("{{this}}", str(item))
                        item_content = item_content.replace("{{.}}", str(item))
                        item_content = item_content.replace("{{index}}", str(index))
                        item_content = item_content.replace("{{index + 1}}", str(index + 1))
                    result.append(item_content)
                return "\n".join(result)
            else:
                return ""

        return re.sub(pattern, replace_loop, content, flags=re.DOTALL)

    def _render_nested_content(self, content: str, parameters: Dict[str, Any]) -> str:
        """渲染嵌套内容，支持点号表示法"""
        result = content

        # 处理点号表示法的参数，如 {{summary.total_issues}}
        nested_pattern = r'\{\{(\w+(?:\.\w+)*)\}\}'

        def replace_nested(match):
            param_path = match.group(1)
            keys = param_path.split('.')

            value = parameters
            try:
                for key in keys:
                    value = value[key]
                return str(value)
            except (KeyError, TypeError):
                return match.group(0)  # 保留原始占位符

        result = re.sub(nested_pattern, replace_nested, result)

        # 处理普通参数
        simple_pattern = re.escape(self.delimiter_start) + r'(\w+)' + re.escape(self.delimiter_end)

        def replace_simple(match):
            param_name = match.group(1)
            if param_name in parameters:
                return str(parameters[param_name])
            else:
                return match.group(0)

        result = re.sub(simple_pattern, replace_simple, result)

        return result


class TemplateFunctionRenderer(AdvancedPromptRenderer):
    """支持模板函数的渲染器"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.functions = {
            'upper': str.upper,
            'lower': str.lower,
            'capitalize': str.capitalize,
            'title': str.title,
            'length': len,
            'default': self._default_function,
        }

    def _default_function(self, value: str, default: str = "") -> str:
        """默认值函数"""
        return value if value else default

    def _render_content(self, template: str, parameters: Dict[str, Any]) -> str:
        """支持函数调用的内容渲染"""
        content = template

        # 处理函数调用 {{function:param}}
        pattern = r'\{\{(\w+):(\w+)\}\}'

        def replace_function(match):
            func_name = match.group(1)
            param_name = match.group(2)

            if func_name in self.functions and param_name in parameters:
                func = self.functions[func_name]
                value = str(parameters[param_name])
                try:
                    if func_name == 'default':
                        # 特殊处理默认值函数
                        return func(value, parameters.get(f"{param_name}_default", ""))
                    else:
                        return str(func(value))
                except Exception:
                    return value
            else:
                return match.group(0)

        content = re.sub(pattern, replace_function, content)

        # 处理普通参数
        content = super()._render_content(content, parameters)

        return content

    def add_function(self, name: str, func):
        """添加自定义函数"""
        self.functions[name] = func

    def remove_function(self, name: str):
        """移除函数"""
        if name in self.functions:
            del self.functions[name]