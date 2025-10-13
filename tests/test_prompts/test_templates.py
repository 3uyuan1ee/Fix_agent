"""
测试具体的Prompt模板
"""

import pytest
from src.prompts.base import PromptCategory, PromptType
from src.prompts.templates import (
    StaticAnalysisTemplate, DeepAnalysisTemplate, RepairSuggestionTemplate
)


class TestStaticAnalysisTemplate:
    """测试静态分析模板"""

    def test_get_system_prompt(self):
        """测试获取系统提示"""
        template = StaticAnalysisTemplate.get_system_prompt()

        assert template.name == "static_analysis_system"
        assert template.category == PromptCategory.STATIC_ANALYSIS
        assert template.prompt_type == PromptType.SYSTEM
        assert "软件缺陷检测专家" in template.template
        assert "静态分析工具" in template.template
        assert template.description == "静态分析系统提示"
        assert "static_analysis" in template.tags
        assert "security" in template.tags

    def test_get_analysis_prompt(self):
        """测试获取分析提示"""
        template = StaticAnalysisTemplate.get_analysis_prompt()

        assert template.name == "static_analysis_main"
        assert template.category == PromptCategory.STATIC_ANALYSIS
        assert template.prompt_type == PromptType.USER
        assert "project_name" in template.parameters
        assert "language" in template.parameters
        assert "tool_name" in template.parameters
        assert "issues" in template.parameters
        assert "项目名称" in template.parameters["project_name"]
        assert "编程语言" in template.parameters["language"]
        assert "分析工具名称" in template.parameters["tool_name"]
        assert "问题列表" in template.parameters["issues"]

    def test_get_analysis_prompt_has_conditionals(self):
        """测试分析提示包含条件语句"""
        template = StaticAnalysisTemplate.get_analysis_prompt()

        # 检查条件语法
        assert "{{#if summary}}" in template.template
        assert "{{/if}}" in template.template
        assert "{{#each issues}}" in template.template
        assert "{{/each}}" in template.template

    def test_get_summary_prompt(self):
        """测试获取总结提示"""
        template = StaticAnalysisTemplate.get_summary_prompt()

        assert template.name == "static_analysis_summary"
        assert template.category == PromptCategory.STATIC_ANALYSIS
        assert template.prompt_type == PromptType.USER
        assert "total_defects" in template.parameters
        assert "critical_defects" in template.parameters
        assert "top_defects" in template.parameters
        assert "overall_assessment" in template.parameters

    def test_analysis_prompt_parameters_completeness(self):
        """测试分析提示参数完整性"""
        template = StaticAnalysisTemplate.get_analysis_prompt()

        required_params = [
            "project_name", "language", "lines_of_code", "tool_name",
            "issues"
        ]

        for param in required_params:
            assert param in template.parameters

    def test_template_structure(self):
        """测试模板结构"""
        template = StaticAnalysisTemplate.get_analysis_prompt()

        # 检查模板是否包含必要的部分
        assert "项目信息" in template.template
        assert "分析结果概览" in template.template
        assert "详细问题列表" in template.template
        assert "请提供以下分析" in template.template


class TestDeepAnalysisTemplate:
    """测试深度分析模板"""

    def test_get_system_prompt(self):
        """测试获取系统提示"""
        template = DeepAnalysisTemplate.get_system_prompt()

        assert template.name == "deep_analysis_system"
        assert template.category == PromptCategory.DEEP_ANALYSIS
        assert template.prompt_type == PromptType.SYSTEM
        assert "软件架构师" in template.template
        assert "安全专家" in template.template
        assert "安全漏洞" in template.template
        assert "性能瓶颈" in template.template
        assert "架构缺陷" in template.template

    def test_get_code_analysis_prompt(self):
        """测试获取代码分析提示"""
        template = DeepAnalysisTemplate.get_code_analysis_prompt()

        assert template.name == "deep_code_analysis"
        assert template.category == PromptCategory.DEEP_ANALYSIS
        assert template.prompt_type == PromptType.USER
        assert "file_path" in template.parameters
        assert "function_name" in template.parameters
        assert "language" in template.parameters
        assert "code_content" in template.parameters

    def test_code_analysis_prompt_analysis_sections(self):
        """测试代码分析提示包含分析部分"""
        template = DeepAnalysisTemplate.get_code_analysis_prompt()

        # 检查各个分析部分
        assert "安全性分析" in template.template
        assert "性能分析" in template.template
        assert "架构分析" in template.template
        assert "业务逻辑分析" in template.template
        assert "代码质量分析" in template.template

    def test_get_vulnerability_assessment_prompt(self):
        """测试获取漏洞评估提示"""
        template = DeepAnalysisTemplate.get_vulnerability_assessment_prompt()

        assert template.name == "vulnerability_assessment"
        assert template.category == PromptCategory.DEEP_ANALYSIS
        assert template.prompt_type == PromptType.USER
        assert "vulnerability_type" in template.parameters
        assert "severity_level" in template.parameters
        assert "affected_components" in template.parameters
        assert "location" in template.parameters

    def test_vulnerability_assessment_prompt_sections(self):
        """测试漏洞评估提示包含评估部分"""
        template = DeepAnalysisTemplate.get_vulnerability_assessment_prompt()

        # 检查各个评估部分
        assert "漏洞机理" in template.template
        assert "影响评估" in template.template
        assert "利用风险评估" in template.template
        assert "修复建议" in template.template
        assert "预防措施" in template.template

    def test_vulnerability_assessment_attack_scenarios(self):
        """测试漏洞评估攻击场景处理"""
        template = DeepAnalysisTemplate.get_vulnerability_assessment_prompt()

        # 检查攻击场景的循环处理
        assert "{{#each attack_scenarios}}" in template.template
        assert "{{/each}}" in template.template

    def test_deep_analysis_template_tags(self):
        """测试深度分析模板标签"""
        system_template = DeepAnalysisTemplate.get_system_prompt()
        analysis_template = DeepAnalysisTemplate.get_code_analysis_prompt()
        vulnerability_template = DeepAnalysisTemplate.get_vulnerability_assessment_prompt()

        # 检查标签
        for template in [system_template, analysis_template, vulnerability_template]:
            assert "deep_analysis" in template.tags
            assert "security" in template.tags


class TestRepairSuggestionTemplate:
    """测试修复建议模板"""

    def test_get_system_prompt(self):
        """测试获取系统提示"""
        template = RepairSuggestionTemplate.get_system_prompt()

        assert template.name == "repair_suggestion_system"
        assert template.category == PromptCategory.REPAIR_SUGGESTION
        assert template.prompt_type == PromptType.SYSTEM
        assert "经验丰富的软件工程师" in template.template
        assert "代码修复和优化" in template.template
        assert "最佳实践" in template.template

    def test_get_fix_suggestion_prompt(self):
        """测试获取修复建议提示"""
        template = RepairSuggestionTemplate.get_fix_suggestion_prompt()

        assert template.name == "defect_fix_suggestion"
        assert template.category == PromptCategory.REPAIR_SUGGESTION
        assert template.prompt_type == PromptType.USER
        assert "defect_type" in template.parameters
        assert "severity" in template.parameters
        assert "file_path" in template.parameters
        assert "line_number" in template.parameters
        assert "description" in template.parameters
        assert "problematic_code" in template.parameters
        assert "context_code" in template.parameters

    def test_fix_suggestion_prompt_structure(self):
        """测试修复建议提示结构"""
        template = RepairSuggestionTemplate.get_fix_suggestion_prompt()

        # 检查各个建议部分
        assert "问题分析" in template.template
        assert "修复方案" in template.template
        assert "实施建议" in template.template
        assert "预防措施" in template.template

    def test_fix_suggestion_multiple_solutions(self):
        """测试修复建议多方案支持"""
        template = RepairSuggestionTemplate.get_fix_suggestion_prompt()

        # 检查多方案的条件处理
        assert "{{#if multiple_solutions}}" in template.template
        assert "{{/if}}" in template.template
        assert "方案一：推荐方案" in template.template
        assert "方案二：替代方案" in template.template

    def test_get_refactoring_suggestion_prompt(self):
        """测试获取重构建议提示"""
        template = RepairSuggestionTemplate.get_refactoring_suggestion_prompt()

        assert template.name == "code_refactoring_suggestion"
        assert template.category == PromptCategory.REPAIR_SUGGESTION
        assert template.prompt_type == PromptType.USER
        assert "current_code" in template.parameters
        assert "complexity" in template.parameters
        assert "readability_score" in template.parameters
        assert "maintainability_score" in template.parameters

    def test_refactoring_suggestion_structure(self):
        """测试重构建议提示结构"""
        template = RepairSuggestionTemplate.get_refactoring_suggestion_prompt()

        # 检查重构步骤
        assert "重构目标" in template.template
        assert "重构方案" in template.template
        assert "步骤1：" in template.template
        assert "步骤2：" in template.template
        assert "重构效果" in template.template
        assert "风险评估" in template.template

    def test_refactoring_additional_steps(self):
        """测试重构建议额外步骤"""
        template = RepairSuggestionTemplate.get_refactoring_suggestion_prompt()

        # 检查额外步骤的循环处理
        assert "{{#each additional_steps}}" in template.template
        assert "{{/each}}" in template.template

    def test_repair_suggestion_template_tags(self):
        """测试修复建议模板标签"""
        system_template = RepairSuggestionTemplate.get_system_prompt()
        fix_template = RepairSuggestionTemplate.get_fix_suggestion_prompt()
        refactor_template = RepairSuggestionTemplate.get_refactoring_suggestion_prompt()

        # 检查标签
        for template in [system_template, fix_template, refactor_template]:
            assert "repair" in template.tags or "refactoring" in template.tags
            assert "code_fix" in template.tags or "code_quality" in template.tags

    def test_template_parameters_completeness(self):
        """测试模板参数完整性"""
        fix_template = RepairSuggestionTemplate.get_fix_suggestion_prompt()

        # 检查必需参数
        required_params = [
            "defect_type", "severity", "file_path", "line_number",
            "description", "language", "problematic_code", "context_code"
        ]

        for param in required_params:
            assert param in fix_template.parameters


class TestTemplateIntegration:
    """测试模板集成"""

    def test_all_templates_have_required_fields(self):
        """测试所有模板都有必需字段"""
        templates = [
            StaticAnalysisTemplate.get_system_prompt(),
            StaticAnalysisTemplate.get_analysis_prompt(),
            StaticAnalysisTemplate.get_summary_prompt(),
            DeepAnalysisTemplate.get_system_prompt(),
            DeepAnalysisTemplate.get_code_analysis_prompt(),
            DeepAnalysisTemplate.get_vulnerability_assessment_prompt(),
            RepairSuggestionTemplate.get_system_prompt(),
            RepairSuggestionTemplate.get_fix_suggestion_prompt(),
            RepairSuggestionTemplate.get_refactoring_suggestion_prompt()
        ]

        for template in templates:
            # 检查必需字段
            assert template.name, f"Template missing name: {template}"
            assert template.category, f"Template missing category: {template}"
            assert template.prompt_type, f"Template missing prompt_type: {template}"
            assert template.template, f"Template missing content: {template}"
            assert template.description, f"Template missing description: {template}"
            assert template.version, f"Template missing version: {template}"

    def test_template_categories_distribution(self):
        """测试模板类别分布"""
        static_templates = [
            StaticAnalysisTemplate.get_system_prompt(),
            StaticAnalysisTemplate.get_analysis_prompt(),
            StaticAnalysisTemplate.get_summary_prompt()
        ]

        deep_templates = [
            DeepAnalysisTemplate.get_system_prompt(),
            DeepAnalysisTemplate.get_code_analysis_prompt(),
            DeepAnalysisTemplate.get_vulnerability_assessment_prompt()
        ]

        repair_templates = [
            RepairSuggestionTemplate.get_system_prompt(),
            RepairSuggestionTemplate.get_fix_suggestion_prompt(),
            RepairSuggestionTemplate.get_refactoring_suggestion_prompt()
        ]

        # 检查类别
        for template in static_templates:
            assert template.category == PromptCategory.STATIC_ANALYSIS

        for template in deep_templates:
            assert template.category == PromptCategory.DEEP_ANALYSIS

        for template in repair_templates:
            assert template.category == PromptCategory.REPAIR_SUGGESTION

    def test_template_prompt_types_distribution(self):
        """测试模板类型分布"""
        system_prompts = [
            StaticAnalysisTemplate.get_system_prompt(),
            DeepAnalysisTemplate.get_system_prompt(),
            RepairSuggestionTemplate.get_system_prompt()
        ]

        user_prompts = [
            StaticAnalysisTemplate.get_analysis_prompt(),
            StaticAnalysisTemplate.get_summary_prompt(),
            DeepAnalysisTemplate.get_code_analysis_prompt(),
            DeepAnalysisTemplate.get_vulnerability_assessment_prompt(),
            RepairSuggestionTemplate.get_fix_suggestion_prompt(),
            RepairSuggestionTemplate.get_refactoring_suggestion_prompt()
        ]

        # 检查类型
        for template in system_prompts:
            assert template.prompt_type == PromptType.SYSTEM

        for template in user_prompts:
            assert template.prompt_type == PromptType.USER