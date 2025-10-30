"""
AI文件选择提示词构建器 - T005.1
将项目分析结果转化为高效的AI提示词
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from ..utils.logger import get_logger
try:
    from ..tools.project_analysis_types import ProgrammingLanguage, FileCategory
    from ..tools.static_analysis_aggregator import ProjectAnalysisReport, FileAnalysisSummary
except ImportError:
    # 如果相关模块不可用，定义基本类型
    from enum import Enum

    class ProgrammingLanguage(Enum):
        PYTHON = "python"
        JAVASCRIPT = "javascript"
        TYPESCRIPT = "typescript"
        JAVA = "java"
        GO = "go"
        CPP = "cpp"
        CSHARP = "csharp"
        RUST = "rust"
        PHP = "php"
        RUBY = "ruby"
        SWIFT = "swift"
        KOTLIN = "kotlin"
        SCALA = "scala"
        HTML = "html"
        CSS = "css"
        JSON = "json"
        YAML = "yaml"
        XML = "xml"
        MARKDOWN = "markdown"
        SHELL = "shell"
        SQL = "sql"
        DOCKER = "docker"
        CONFIG = "config"
        OTHER = "other"

    class FileCategory(Enum):
        SOURCE_CODE = "source_code"
        CONFIG = "config"
        DOCUMENTATION = "documentation"
        TEST = "test"
        BUILD = "build"
        ASSET = "asset"
        OTHER = "other"

    @dataclass
    class FileAnalysisSummary:
        file_path: str
        language: ProgrammingLanguage
        total_issues: int = 0
        severity_counts: Dict[str, int] = field(default_factory=dict)
        category_counts: Dict[str, int] = field(default_factory=dict)
        issue_density: float = 0.0
        complexity_score: float = 0.0
        importance_score: float = 0.0
        tools_used: List[str] = field(default_factory=list)
        analysis_timestamp: str = ""


@dataclass
class FileSelectionCriteria:
    """文件选择标准"""
    max_files: int = 20
    max_total_issues: int = 500
    min_importance_score: float = 10.0
    include_test_files: bool = False
    preferred_languages: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    focus_categories: List[str] = field(default_factory=list)


@dataclass
class AIFileSelectionPrompt:
    """AI文件选择提示词"""
    system_prompt: str
    user_prompt: str
    context_data: Dict[str, Any]
    expected_output_format: Dict[str, Any]
    token_estimate: int = 0
    build_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "context_data": self.context_data,
            "expected_output_format": self.expected_output_format,
            "token_estimate": self.token_estimate,
            "build_timestamp": self.build_timestamp
        }


class AIFileSelectionPromptBuilder:
    """AI文件选择提示词构建器"""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        self.logger = get_logger()

        # 提示词模板
        self.system_prompt_template = """
你是一个专业的代码分析专家，负责从项目分析结果中选择需要重点关注和修复的文件。

你的任务是基于提供的项目分析数据，智能选择出最需要AI深度分析和修复的核心文件。

选择标准：
1. **问题密度高**: 每百行代码中问题数量较多的文件
2. **严重问题多**: 包含高严重程度（critical, high）问题的文件
3. **重要核心文件**: 项目中的主要业务逻辑文件、配置文件、入口文件
4. **影响面广**: 被其他文件依赖或引用较多的核心文件
5. **修复价值高**: 修复后能显著提升项目整体质量的文件

注意事项：
- 优先选择业务逻辑核心文件，避免测试文件（除非特别要求）
- 平衡不同类型文件：业务代码、配置文件、工具文件等
- 考虑文件之间的依赖关系
- 控制选择的文件数量在合理范围内
- 为每个选择的文件提供明确的选择理由

输出格式：
严格按照JSON格式输出，包含文件路径、优先级、选择理由和置信度。
"""

        self.user_prompt_template = """
# 项目分析任务：智能文件选择

## 项目概览
项目路径: {project_path}
总文件数: {total_files}
总问题数: {total_issues}
主要编程语言: {main_languages}
平均每文件问题数: {avg_issues_per_file}
高严重程度问题比例: {high_severity_ratio}%

## 分析重点
{analysis_focus}

## 高风险文件
以下文件已被识别为高风险，请优先考虑：
{high_risk_files}

## 文件分析数据
{file_analysis_data}

## 选择要求
1. 选择 {max_files} 个最需要AI深度分析和修复的文件
2. 最小重要性分数: {min_importance_score}
3. 优先考虑语言: {preferred_languages}
4. 关注问题类型: {focus_categories}
5. 排除模式: {exclude_patterns}

请基于以上数据，选择最需要重点分析的文件，并输出JSON格式的结果。
"""

    def build_prompt(self,
                    project_report: Dict[str, Any],
                    criteria: Optional[FileSelectionCriteria] = None,
                    user_requirements: Optional[str] = None) -> AIFileSelectionPrompt:
        """
        构建AI文件选择提示词

        Args:
            project_report: 项目分析报告
            criteria: 文件选择标准
            user_requirements: 用户特定需求

        Returns:
            AIFileSelectionPrompt: 构建的提示词
        """
        if criteria is None:
            criteria = FileSelectionCriteria()

        self.logger.info("开始构建AI文件选择提示词")

        # 提取项目基本信息
        project_overview = project_report.get("project_overview", {})
        file_summaries = project_report.get("file_summaries", [])
        high_risk_files = project_report.get("high_risk_files", [])

        # 构建上下文数据
        context_data = self._build_context_data(
            project_overview, file_summaries, high_risk_files, criteria
        )

        # 构建系统提示词
        system_prompt = self._build_system_prompt(criteria)

        # 构建用户提示词
        user_prompt = self._build_user_prompt(
            project_overview, file_summaries, high_risk_files,
            criteria, user_requirements
        )

        # 定义期望输出格式
        expected_output_format = self._build_output_format()

        # 估算token数量
        token_estimate = self._estimate_tokens(
            system_prompt, user_prompt, context_data
        )

        prompt = AIFileSelectionPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            context_data=context_data,
            expected_output_format=expected_output_format,
            token_estimate=token_estimate,
            build_timestamp=datetime.now().isoformat()
        )

        self.logger.info(f"AI文件选择提示词构建完成，预估token数: {token_estimate}")

        return prompt

    def _build_context_data(self,
                           project_overview: Dict[str, Any],
                           file_summaries: List[Dict[str, Any]],
                           high_risk_files: List[str],
                           criteria: FileSelectionCriteria) -> Dict[str, Any]:
        """构建上下文数据"""
        # 过滤和排序文件摘要
        filtered_summaries = self._filter_file_summaries(file_summaries, criteria)

        # 限制文件数量以控制token使用
        max_files_for_context = min(50, len(filtered_summaries))
        top_summaries = sorted(
            filtered_summaries,
            key=lambda x: x.get("importance_score", 0),
            reverse=True
        )[:max_files_for_context]

        context_data = {
            "project_overview": project_overview,
            "high_risk_files": high_risk_files[:10],  # 限制高风险文件数量
            "file_summaries": top_summaries,
            "selection_criteria": {
                "max_files": criteria.max_files,
                "min_importance_score": criteria.min_importance_score,
                "preferred_languages": criteria.preferred_languages,
                "exclude_patterns": criteria.exclude_patterns,
                "focus_categories": criteria.focus_categories
            }
        }

        return context_data

    def _filter_file_summaries(self,
                              file_summaries: List[Dict[str, Any]],
                              criteria: FileSelectionCriteria) -> List[Dict[str, Any]]:
        """过滤文件摘要"""
        filtered = []

        for summary in file_summaries:
            file_path = summary.get("file_path", "")
            importance_score = summary.get("importance_score", 0)

            # 检查最小重要性分数
            if importance_score < criteria.min_importance_score:
                continue

            # 检查排除模式
            if self._should_exclude_file(file_path, criteria.exclude_patterns):
                continue

            # 检查测试文件
            if not criteria.include_test_files and self._is_test_file(file_path):
                continue

            # 检查语言偏好
            if criteria.preferred_languages:
                file_language = summary.get("language", "")
                if file_language not in criteria.preferred_languages:
                    continue

            filtered.append(summary)

        return filtered

    def _should_exclude_file(self, file_path: str, exclude_patterns: List[str]) -> bool:
        """检查文件是否应该被排除"""
        import re
        file_lower = file_path.lower()

        for pattern in exclude_patterns:
            if pattern.startswith('*'):
                # 后缀匹配
                if file_lower.endswith(pattern[1:].lower()):
                    return True
            elif pattern.endswith('*'):
                # 前缀匹配
                if file_lower.startswith(pattern[:-1].lower()):
                    return True
            else:
                # 正则表达式匹配
                try:
                    if re.search(pattern, file_path, re.IGNORECASE):
                        return True
                except re.error:
                    # 如果正则表达式无效，进行简单的字符串匹配
                    if pattern.lower() in file_lower:
                        return True

        return False

    def _is_test_file(self, file_path: str) -> bool:
        """检查是否为测试文件"""
        test_indicators = [
            '/test/', '/tests/', 'test_', '_test.', '.test.', '/spec/', '_spec.', '.spec.'
        ]

        file_lower = file_path.lower()
        return any(indicator in file_lower for indicator in test_indicators)

    def _build_system_prompt(self, criteria: FileSelectionCriteria) -> str:
        """构建系统提示词"""
        base_prompt = self.system_prompt_template.strip()

        # 添加特定标准
        criteria_section = f"""
\n## 特定选择标准
- 最大文件数量: {criteria.max_files}
- 最小重要性分数: {criteria.min_importance_score}
- 包含测试文件: {'是' if criteria.include_test_files else '否'}
- 优先语言: {', '.join(criteria.preferred_languages) if criteria.preferred_languages else '无'}
- 关注问题类型: {', '.join(criteria.focus_categories) if criteria.focus_categories else '全部'}
"""

        return base_prompt + criteria_section

    def _build_user_prompt(self,
                          project_overview: Dict[str, Any],
                          file_summaries: List[Dict[str, Any]],
                          high_risk_files: List[str],
                          criteria: FileSelectionCriteria,
                          user_requirements: Optional[str]) -> str:
        """构建用户提示词"""
        # 准备数据
        main_languages = project_overview.get("main_languages", {})
        analysis_summary = project_overview.get("analysis_summary", {})

        # 格式化高风险文件
        high_risk_section = ""
        if high_risk_files:
            high_risk_section = "\n".join([f"- {file}" for file in high_risk_files[:10]])
        else:
            high_risk_section = "无特别高风险文件"

        # 准备文件分析数据
        file_analysis_section = self._format_file_analysis_data(file_summaries, criteria)

        # 准备分析重点
        analysis_focus = self._build_analysis_focus(criteria, user_requirements)

        # 构建用户提示词
        user_prompt = self.user_prompt_template.format(
            project_path=project_overview.get("project_path", ""),
            total_files=project_overview.get("total_files", 0),
            total_issues=project_overview.get("total_issues", 0),
            main_languages=", ".join([f"{lang}({count})" for lang, count in main_languages.items()]),
            avg_issues_per_file=analysis_summary.get("avg_issues_per_file", 0),
            high_severity_ratio=f"{analysis_summary.get('high_severity_ratio', 0)*100:.1f}%",
            analysis_focus=analysis_focus,
            high_risk_files=high_risk_section,
            file_analysis_data=file_analysis_section,
            max_files=criteria.max_files,
            min_importance_score=criteria.min_importance_score,
            preferred_languages=", ".join(criteria.preferred_languages) if criteria.preferred_languages else "无",
            focus_categories=", ".join(criteria.focus_categories) if criteria.focus_categories else "全部",
            exclude_patterns=", ".join(criteria.exclude_patterns) if criteria.exclude_patterns else "无"
        )

        return user_prompt.strip()

    def _format_file_analysis_data(self,
                                  file_summaries: List[Dict[str, Any]],
                                  criteria: FileSelectionCriteria) -> str:
        """格式化文件分析数据"""
        if not file_summaries:
            return "无文件数据"

        # 限制显示的文件数量
        max_display = min(30, len(file_summaries))
        display_summaries = file_summaries[:max_display]

        data_lines = []
        data_lines.append("## 文件详细分析数据")
        data_lines.append("")

        for i, summary in enumerate(display_summaries, 1):
            file_path = summary.get("file_path", "")
            language = summary.get("language", "")
            total_issues = summary.get("total_issues", 0)
            importance_score = summary.get("importance_score", 0)
            issue_density = summary.get("issue_density", 0)

            # 获取严重程度分布
            severity_counts = summary.get("severity_counts", {})
            critical = severity_counts.get("critical", 0)
            high = severity_counts.get("high", 0)
            medium = severity_counts.get("medium", 0)
            low = severity_counts.get("low", 0)

            data_lines.append(f"### {i}. {file_path}")
            data_lines.append(f"- 语言: {language}")
            data_lines.append(f"- 问题总数: {total_issues}")
            data_lines.append(f"- 重要性分数: {importance_score:.1f}")
            data_lines.append(f"- 问题密度: {issue_density:.2f}/100行")
            data_lines.append(f"- 严重程度分布: 严重({critical}) 高({high}) 中({medium}) 低({low})")
            data_lines.append("")

        if len(file_summaries) > max_display:
            data_lines.append(f"... 还有 {len(file_summaries) - max_display} 个文件未显示")

        return "\n".join(data_lines)

    def _build_analysis_focus(self,
                            criteria: FileSelectionCriteria,
                            user_requirements: Optional[str]) -> str:
        """构建分析重点描述"""
        focus_items = []

        if criteria.focus_categories:
            focus_items.append(f"重点关注问题类型: {', '.join(criteria.focus_categories)}")

        if criteria.preferred_languages:
            focus_items.append(f"优先分析编程语言: {', '.join(criteria.preferred_languages)}")

        if user_requirements:
            focus_items.append(f"用户特殊要求: {user_requirements}")

        focus_items.append("平衡选择不同类型和重要性的文件")
        focus_items.append("考虑文件间的依赖关系和影响面")

        return "\n".join([f"- {item}" for item in focus_items])

    def _build_output_format(self) -> Dict[str, Any]:
        """构建期望输出格式"""
        return {
            "type": "json",
            "schema": {
                "type": "object",
                "properties": {
                    "selected_files": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {
                                    "type": "string",
                                    "description": "文件路径"
                                },
                                "priority": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"],
                                    "description": "优先级"
                                },
                                "reason": {
                                    "type": "string",
                                    "description": "选择理由"
                                },
                                "confidence": {
                                    "type": "number",
                                    "minimum": 0.0,
                                    "maximum": 1.0,
                                    "description": "置信度"
                                },
                                "key_issues": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "关键问题列表"
                                }
                            },
                            "required": ["file_path", "priority", "reason", "confidence"]
                        }
                    },
                    "selection_summary": {
                        "type": "object",
                        "properties": {
                            "total_selected": {"type": "number"},
                            "selection_criteria_met": {"type": "boolean"},
                            "additional_notes": {"type": "string"}
                        }
                    }
                },
                "required": ["selected_files"]
            }
        }

    def _estimate_tokens(self,
                        system_prompt: str,
                        user_prompt: str,
                        context_data: Dict[str, Any]) -> int:
        """估算token数量"""
        # 粗略估算：1个token约等于4个字符（英文）或1.5个汉字
        total_text = system_prompt + user_prompt + json.dumps(context_data, ensure_ascii=False)

        # 简单估算：中文按1字符=1token，英文按4字符=1token
        chinese_chars = len([c for c in total_text if ord(c) > 127])
        other_chars = len(total_text) - chinese_chars

        estimated_tokens = chinese_chars + (other_chars // 4)

        return estimated_tokens

    def optimize_prompt_for_tokens(self,
                                  prompt: AIFileSelectionPrompt,
                                  target_tokens: int) -> AIFileSelectionPrompt:
        """
        优化提示词以控制token数量

        Args:
            prompt: 原始提示词
            target_tokens: 目标token数量

        Returns:
            AIFileSelectionPrompt: 优化后的提示词
        """
        if prompt.token_estimate <= target_tokens:
            return prompt

        self.logger.info(f"优化提示词，当前token数: {prompt.token_estimate}, 目标: {target_tokens}")

        optimized_prompt = AIFileSelectionPrompt(
            system_prompt=prompt.system_prompt,
            user_prompt=prompt.user_prompt,
            context_data=self._optimize_context_data(prompt.context_data, target_tokens),
            expected_output_format=prompt.expected_output_format,
            token_estimate=0,  # 重新计算
            build_timestamp=prompt.build_timestamp
        )

        # 重新估算token数量
        optimized_prompt.token_estimate = self._estimate_tokens(
            optimized_prompt.system_prompt,
            optimized_prompt.user_prompt,
            optimized_prompt.context_data
        )

        self.logger.info(f"提示词优化完成，新token数: {optimized_prompt.token_estimate}")

        return optimized_prompt

    def _optimize_context_data(self,
                              context_data: Dict[str, Any],
                              target_tokens: int) -> Dict[str, Any]:
        """优化上下文数据"""
        optimized_data = context_data.copy()

        # 减少文件摘要数量
        file_summaries = optimized_data.get("file_summaries", [])
        if len(file_summaries) > 20:
            # 按重要性分数排序，保留最重要的文件
            sorted_summaries = sorted(
                file_summaries,
                key=lambda x: x.get("importance_score", 0),
                reverse=True
            )
            optimized_data["file_summaries"] = sorted_summaries[:20]

        # 减少高风险文件数量
        high_risk_files = optimized_data.get("high_risk_files", [])
        if len(high_risk_files) > 5:
            optimized_data["high_risk_files"] = high_risk_files[:5]

        return optimized_data


# 便捷函数
def build_file_selection_prompt(project_report: Dict[str, Any],
                              max_files: int = 20,
                              preferred_languages: List[str] = None,
                              focus_categories: List[str] = None,
                              user_requirements: str = None) -> Dict[str, Any]:
    """
    便捷的AI文件选择提示词构建函数

    Args:
        project_report: 项目分析报告
        max_files: 最大文件选择数量
        preferred_languages: 优先编程语言
        focus_categories: 关注问题类型
        user_requirements: 用户特殊需求

    Returns:
        Dict[str, Any]: 构建的提示词
    """
    criteria = FileSelectionCriteria(
        max_files=max_files,
        preferred_languages=preferred_languages or [],
        focus_categories=focus_categories or []
    )

    builder = AIFileSelectionPromptBuilder()
    prompt = builder.build_prompt(project_report, criteria, user_requirements)

    # 如果token过多，进行优化
    if prompt.token_estimate > 4000:
        prompt = builder.optimize_prompt_for_tokens(prompt, 3500)

    return prompt.to_dict()