"""
Prompt模板管理器
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import asdict

from .base import PromptTemplate, PromptCategory, PromptType, PromptRenderResult
from .renderer import AdvancedPromptRenderer, ConditionalPromptRenderer, TemplateFunctionRenderer
from .templates import StaticAnalysisTemplate, DeepAnalysisTemplate, RepairSuggestionTemplate
from ..utils.logger import get_logger


class PromptManager:
    """Prompt模板管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化Prompt管理器

        Args:
            config_path: 配置文件路径
        """
        self.logger = get_logger()
        self.templates: Dict[str, PromptTemplate] = {}
        self.renderers = {
            "basic": AdvancedPromptRenderer(),
            "conditional": ConditionalPromptRenderer(),
            "function": TemplateFunctionRenderer()
        }
        self.current_renderer = "conditional"

        # 加载内置模板
        self._load_builtin_templates()

        # 从配置文件加载自定义模板
        if config_path:
            self._load_from_file(config_path)

    def _load_builtin_templates(self):
        """加载内置模板"""
        # 加载静态分析模板
        static_templates = [
            StaticAnalysisTemplate.get_system_prompt(),
            StaticAnalysisTemplate.get_analysis_prompt(),
            StaticAnalysisTemplate.get_summary_prompt()
        ]

        # 加载深度分析模板
        deep_templates = [
            DeepAnalysisTemplate.get_system_prompt(),
            DeepAnalysisTemplate.get_code_analysis_prompt(),
            DeepAnalysisTemplate.get_vulnerability_assessment_prompt()
        ]

        # 加载修复建议模板
        repair_templates = [
            RepairSuggestionTemplate.get_system_prompt(),
            RepairSuggestionTemplate.get_fix_suggestion_prompt(),
            RepairSuggestionTemplate.get_refactoring_suggestion_prompt()
        ]

        # 注册所有模板
        for template in static_templates + deep_templates + repair_templates:
            self.register_template(template)

        self.logger.info(f"Loaded {len(self.templates)} builtin prompt templates")

    def _load_from_file(self, config_path: str):
        """从配置文件加载模板"""
        config_file = Path(config_path)
        if not config_file.exists():
            self.logger.warning(f"Prompt config file not found: {config_path}")
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                if config_file.suffix.lower() in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            if 'templates' in data:
                for template_data in data['templates']:
                    try:
                        template = PromptTemplate.from_dict(template_data)
                        self.register_template(template)
                    except Exception as e:
                        self.logger.error(f"Failed to load template '{template_data.get('name', 'unknown')}': {e}")

            self.logger.info(f"Loaded templates from {config_path}")

        except Exception as e:
            self.logger.error(f"Failed to load prompt config file {config_path}: {e}")

    def register_template(self, template: PromptTemplate):
        """
        注册模板

        Args:
            template: Prompt模板
        """
        self.templates[template.name] = template
        self.logger.debug(f"Registered prompt template: {template.name}")

    def unregister_template(self, name: str) -> bool:
        """
        注销模板

        Args:
            name: 模板名称

        Returns:
            是否成功注销
        """
        if name in self.templates:
            del self.templates[name]
            self.logger.debug(f"Unregistered prompt template: {name}")
            return True
        return False

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """
        获取模板

        Args:
            name: 模板名称

        Returns:
            Prompt模板或None
        """
        return self.templates.get(name)

    def list_templates(self, category: Optional[PromptCategory] = None,
                      prompt_type: Optional[PromptType] = None,
                      tags: Optional[List[str]] = None) -> List[PromptTemplate]:
        """
        列出模板

        Args:
            category: 按类别过滤
            prompt_type: 按类型过滤
            tags: 按标签过滤

        Returns:
            模板列表
        """
        templates = list(self.templates.values())

        # 按类别过滤
        if category:
            templates = [t for t in templates if t.category == category]

        # 按类型过滤
        if prompt_type:
            templates = [t for t in templates if t.prompt_type == prompt_type]

        # 按标签过滤
        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]

        return templates

    def search_templates(self, keyword: str) -> List[PromptTemplate]:
        """
        搜索模板

        Args:
            keyword: 搜索关键词

        Returns:
            匹配的模板列表
        """
        keyword = keyword.lower()
        results = []

        for template in self.templates.values():
            if (keyword in template.name.lower() or
                keyword in template.description.lower() or
                any(keyword in tag.lower() for tag in template.tags)):
                results.append(template)

        return results

    def render_template(self, template_name: str, parameters: Dict[str, Any],
                       renderer_name: Optional[str] = None) -> PromptRenderResult:
        """
        渲染模板

        Args:
            template_name: 模板名称
            parameters: 参数值
            renderer_name: 渲染器名称

        Returns:
            渲染结果
        """
        template = self.get_template(template_name)
        if not template:
            return PromptRenderResult(
                content="",
                template_name=template_name,
                parameters_used={},
                success=False,
                error_message=f"Template '{template_name}' not found"
            )

        renderer_name = renderer_name or self.current_renderer
        renderer = self.renderers.get(renderer_name)
        if not renderer:
            return PromptRenderResult(
                content="",
                template_name=template_name,
                parameters_used={},
                success=False,
                error_message=f"Renderer '{renderer_name}' not found"
            )

        return renderer.render(template, parameters)

    def validate_template(self, template_name: str, renderer_name: Optional[str] = None) -> List[str]:
        """
        验证模板

        Args:
            template_name: 模板名称
            renderer_name: 渲染器名称

        Returns:
            验证错误列表
        """
        template = self.get_template(template_name)
        if not template:
            return [f"Template '{template_name}' not found"]

        renderer_name = renderer_name or self.current_renderer
        renderer = self.renderers.get(renderer_name)
        if not renderer:
            return [f"Renderer '{renderer_name}' not found"]

        return renderer.validate_template(template)

    def set_renderer(self, renderer_name: str):
        """
        设置默认渲染器

        Args:
            renderer_name: 渲染器名称
        """
        if renderer_name in self.renderers:
            self.current_renderer = renderer_name
            self.logger.info(f"Set default renderer to: {renderer_name}")
        else:
            raise ValueError(f"Renderer '{renderer_name}' not available")

    def add_custom_renderer(self, name: str, renderer):
        """
        添加自定义渲染器

        Args:
            name: 渲染器名称
            renderer: 渲染器实例
        """
        self.renderers[name] = renderer
        self.logger.info(f"Added custom renderer: {name}")

    def get_template_parameters(self, template_name: str) -> Dict[str, str]:
        """
        获取模板参数

        Args:
            template_name: 模板名称

        Returns:
            参数字典
        """
        template = self.get_template(template_name)
        if template:
            return template.parameters
        return {}

    def export_templates(self, format: str = "json", category: Optional[PromptCategory] = None) -> str:
        """
        导出模板

        Args:
            format: 导出格式 (json, yaml)
            category: 按类别过滤

        Returns:
            导出字符串
        """
        templates = self.list_templates(category=category)
        data = {
            "templates": [template.to_dict() for template in templates],
            "metadata": {
                "total_count": len(templates),
                "categories": list(set(t.category.value for t in templates)),
                "export_time": self._get_current_time()
            }
        }

        if format.lower() == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format.lower() == "yaml":
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def import_templates(self, config_str: str, format: str = "json",
                       overwrite: bool = False) -> int:
        """
        导入模板

        Args:
            config_str: 配置字符串
            format: 配置格式 (json, yaml)
            overwrite: 是否覆盖现有模板

        Returns:
            导入的模板数量
        """
        try:
            if format.lower() == "json":
                data = json.loads(config_str)
            else:
                data = yaml.safe_load(config_str)

            imported_count = 0
            if 'templates' in data:
                for template_data in data['templates']:
                    try:
                        template = PromptTemplate.from_dict(template_data)
                        if template.name in self.templates and not overwrite:
                            self.logger.warning(f"Template '{template.name}' already exists, skipping")
                            continue

                        self.register_template(template)
                        imported_count += 1
                    except Exception as e:
                        self.logger.error(f"Failed to import template '{template_data.get('name', 'unknown')}': {e}")

            self.logger.info(f"Imported {imported_count} templates")
            return imported_count

        except Exception as e:
            self.logger.error(f"Failed to import templates: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        category_counts = {}
        type_counts = {}
        tag_counts = {}

        for template in self.templates.values():
            # 统计类别
            category = template.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

            # 统计类型
            ptype = template.prompt_type.value
            type_counts[ptype] = type_counts.get(ptype, 0) + 1

            # 统计标签
            for tag in template.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "total_templates": len(self.templates),
            "categories": category_counts,
            "types": type_counts,
            "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            "available_renderers": list(self.renderers.keys()),
            "current_renderer": self.current_renderer
        }

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().isoformat()

    # 便捷方法
    def get_static_analysis_prompts(self) -> List[PromptTemplate]:
        """获取所有静态分析提示"""
        return self.list_templates(category=PromptCategory.STATIC_ANALYSIS)

    def get_deep_analysis_prompts(self) -> List[PromptTemplate]:
        """获取所有深度分析提示"""
        return self.list_templates(category=PromptCategory.DEEP_ANALYSIS)

    def get_repair_suggestion_prompts(self) -> List[PromptTemplate]:
        """获取所有修复建议提示"""
        return self.list_templates(category=PromptCategory.REPAIR_SUGGESTION)

    def render_static_analysis(self, parameters: Dict[str, Any]) -> PromptRenderResult:
        """渲染静态分析提示"""
        return self.render_template("static_analysis_main", parameters)

    def render_deep_analysis(self, parameters: Dict[str, Any]) -> PromptRenderResult:
        """渲染深度分析提示"""
        return self.render_template("deep_code_analysis", parameters)

    def render_repair_suggestion(self, parameters: Dict[str, Any]) -> PromptRenderResult:
        """渲染修复建议提示"""
        return self.render_template("defect_fix_suggestion", parameters)