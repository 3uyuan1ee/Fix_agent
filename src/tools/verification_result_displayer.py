#!/usr/bin/env python3
"""
验证结果展示器 - T015.1
以用户友好的方式展示修复验证结果
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from .ai_dynamic_analysis_caller import AIDynamicAnalysisResult
from .fix_verification_aggregator import (
    ComprehensiveVerificationReport,
    RecommendedAction,
    VerificationStatus,
)
from .verification_static_analyzer import StaticVerificationReport

logger = get_logger()


@dataclass
class VerificationDisplayData:
    """验证展示数据"""

    display_id: str
    session_id: str
    suggestion_id: str
    file_path: str
    summary_overview: Dict[str, Any]
    fix_effectiveness: Dict[str, Any]
    quality_impact: Dict[str, Any]
    new_issues_analysis: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    recommendations: List[str]
    detailed_metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "display_id": self.display_id,
            "session_id": self.session_id,
            "suggestion_id": self.suggestion_id,
            "file_path": self.file_path,
            "summary_overview": self.summary_overview,
            "fix_effectiveness": self.fix_effectiveness,
            "quality_impact": self.quality_impact,
            "new_issues_analysis": self.new_issues_analysis,
            "risk_assessment": self.risk_assessment,
            "recommendations": self.recommendations,
            "detailed_metrics": self.detailed_metrics,
        }


class DisplayFormat(Enum):
    """展示格式"""

    SUMMARY = "summary"  # 摘要格式
    DETAILED = "detailed"  # 详细格式
    TECHNICAL = "technical"  # 技术格式
    QUICK_OVERVIEW = "quick_overview"  # 快速概览
    COMPARISON = "comparison"  # 对比格式


class VerificationResultDisplayer:
    """验证结果展示器 - T015.1

    工作流位置: 节点I核心，向用户展示修复验证结果
    核心功能: 以用户友好的方式展示修复验证结果
    用户协作: 为用户提供清晰的验证结果信息
    """

    def __init__(self, config_manager=None):
        """初始化验证结果展示器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        self.config = self.config_manager.get("project_analysis", {})

        # 展示配置
        self.display_config = self.config.get(
            "verification_display",
            {
                "default_format": "summary",
                "show_code_snippets": True,
                "show_metrics_charts": False,
                "max_recommendations": 10,
                "color_coding": True,
            },
        )

    def display_verification_results(
        self,
        comprehensive_report: ComprehensiveVerificationReport,
        display_format: DisplayFormat = None,
    ) -> VerificationDisplayData:
        """
        展示验证结果

        Args:
            comprehensive_report: 综合验证报告
            display_format: 展示格式

        Returns:
            VerificationDisplayData: 格式化的展示数据
        """
        try:
            self.logger.info(
                f"开始展示验证结果: 建议={comprehensive_report.suggestion_id}"
            )

            # 确定展示格式
            format_type = display_format or DisplayFormat(
                self.display_config["default_format"]
            )

            # 构建展示数据
            display_data = VerificationDisplayData(
                display_id=str(datetime.now().timestamp()),
                session_id=comprehensive_report.session_id,
                suggestion_id=comprehensive_report.suggestion_id,
                file_path=comprehensive_report.file_path,
                summary_overview=self._build_summary_overview(comprehensive_report),
                fix_effectiveness=self._build_fix_effectiveness(comprehensive_report),
                quality_impact=self._build_quality_impact(comprehensive_report),
                new_issues_analysis=self._build_new_issues_analysis(
                    comprehensive_report
                ),
                risk_assessment=self._build_risk_assessment_display(
                    comprehensive_report
                ),
                recommendations=self._build_recommendations_display(
                    comprehensive_report
                ),
                detailed_metrics=self._build_detailed_metrics(comprehensive_report),
            )

            # 根据格式调整展示内容
            if format_type == DisplayFormat.SUMMARY:
                display_data = self._format_for_summary(display_data)
            elif format_type == DisplayFormat.DETAILED:
                display_data = self._format_for_detailed(display_data)
            elif format_type == DisplayFormat.TECHNICAL:
                display_data = self._format_for_technical(display_data)
            elif format_type == DisplayFormat.QUICK_OVERVIEW:
                display_data = self._format_for_quick_overview(display_data)
            elif format_type == DisplayFormat.COMPARISON:
                display_data = self._format_for_comparison(display_data)

            self.logger.info(f"验证结果展示完成: 格式={format_type.value}")
            return display_data

        except Exception as e:
            self.logger.error(f"展示验证结果失败: {e}")
            raise

    def _build_summary_overview(
        self, report: ComprehensiveVerificationReport
    ) -> Dict[str, Any]:
        """构建摘要概览"""
        summary = report.verification_summary

        return {
            "verification_status": self._format_status_with_icon(
                summary.verification_status
            ),
            "problem_resolved": self._format_boolean_with_icon(
                summary.problem_resolved
            ),
            "quality_improved": self._format_boolean_with_icon(
                summary.quality_improved
            ),
            "new_issues_introduced": self._format_boolean_with_icon(
                summary.introduced_new_issues, invert=True
            ),
            "recommended_action": self._format_recommended_action(
                summary.recommended_action
            ),
            "confidence_level": f"{summary.confidence_level:.1%}",
            "file_path": report.file_path,
            "verification_time": report.verification_timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }

    def _build_fix_effectiveness(
        self, report: ComprehensiveVerificationReport
    ) -> Dict[str, Any]:
        """构建修复效果信息"""
        metrics = report.verification_metrics
        ai_analysis = report.ai_dynamic_analysis

        # 处理AI分析为None的情况
        if ai_analysis is None:
            ai_analysis = type(
                "MockAIAnalysis",
                (),
                {
                    "problem_resolution_status": "unknown",
                    "fix_effectiveness_score": 0.5,
                },
            )()

        return {
            "fix_success_rate": {
                "value": f"{metrics.fix_success_rate:.1%}",
                "description": "修复成功率",
                "trend": "up" if metrics.fix_success_rate > 0.7 else "down",
            },
            "problem_resolution_status": {
                "value": ai_analysis.problem_resolution_status,
                "description": "问题解决状态",
                "translation": self._translate_resolution_status(
                    ai_analysis.problem_resolution_status
                ),
            },
            "ai_effectiveness_score": {
                "value": f"{ai_analysis.fix_effectiveness_score:.2f}",
                "description": "AI评估有效性分数",
                "level": self._get_score_level(ai_analysis.fix_effectiveness_score),
            },
            "static_analysis_score": {
                "value": (
                    f"{report.static_verification.overall_quality_score:.2f}"
                    if report.static_verification
                    else "N/A"
                ),
                "description": "静态分析质量分数",
                "level": (
                    self._get_score_level(
                        report.static_verification.overall_quality_score
                    )
                    if report.static_verification
                    else "unknown"
                ),
            },
        }

    def _build_quality_impact(
        self, report: ComprehensiveVerificationReport
    ) -> Dict[str, Any]:
        """构建质量影响信息"""
        ai_analysis = report.ai_dynamic_analysis
        metrics = report.verification_metrics

        # 处理AI分析为None的情况
        if ai_analysis is None:
            quality_impact = {}
        else:
            quality_impact = ai_analysis.code_quality_impact

        impact_display = {}
        for aspect, impact in quality_impact.items():
            impact_display[aspect] = {
                "value": impact,
                "icon": self._get_impact_icon(impact),
                "description": self._get_aspect_description(aspect),
            }

        # 添加综合质量分数
        impact_display["overall_score"] = {
            "value": f"{metrics.quality_improvement_score:.2f}",
            "description": "综合质量改进分数",
            "level": self._get_score_level(metrics.quality_improvement_score),
            "change": self._calculate_quality_change(metrics.quality_improvement_score),
        }

        return impact_display

    def _build_new_issues_analysis(
        self, report: ComprehensiveVerificationReport
    ) -> Dict[str, Any]:
        """构建新问题分析"""
        static_report = report.static_verification
        ai_analysis = report.ai_dynamic_analysis

        # 处理静态验证为None的情况
        if static_report is None:
            static_new_issues = []
            static_new_count = 0
        else:
            # 静态分析发现的新问题
            static_new_issues = [
                issue.to_dict()
                for issue in static_report.verification_issues
                if issue.is_new_issue
            ]
            static_new_count = static_report.new_issues_count

        # AI分析发现的新问题 - 处理AI分析为None的情况
        ai_new_issues = ai_analysis.new_issues_detected if ai_analysis else []

        return {
            "total_new_issues": static_new_count + len(ai_new_issues),
            "static_analysis_issues": {
                "count": len(static_new_issues),
                "issues": static_new_issues[:5],  # 只显示前5个
                "has_more": len(static_new_issues) > 5,
            },
            "ai_detected_issues": {
                "count": len(ai_new_issues),
                "issues": ai_new_issues[:5],  # 只显示前5个
                "has_more": len(ai_new_issues) > 5,
            },
            "severity_distribution": self._analyze_issue_severity(
                static_new_issues + ai_new_issues
            ),
            "recommendation": self._get_new_issues_recommendation(
                static_new_count + len(ai_new_issues)
            ),
        }

    def _build_risk_assessment_display(
        self, report: ComprehensiveVerificationReport
    ) -> Dict[str, Any]:
        """构建风险评估展示"""
        risk_assessment = report.risk_assessment

        return {
            "overall_risk_level": {
                "level": risk_assessment["overall_risk_level"],
                "icon": self._get_risk_icon(risk_assessment["overall_risk_level"]),
                "color": self._get_risk_color(risk_assessment["overall_risk_level"]),
            },
            "risk_factors": risk_assessment["risk_factors"],
            "mitigation_strategies": risk_assessment.get("mitigation_strategies", []),
            "risk_score": self._calculate_risk_score(risk_assessment),
        }

    def _build_recommendations_display(
        self, report: ComprehensiveVerificationReport
    ) -> List[str]:
        """构建建议展示"""
        recommendations = report.improvement_recommendations

        # 限制建议数量
        max_recommendations = self.display_config["max_recommendations"]
        if len(recommendations) > max_recommendations:
            recommendations = recommendations[:max_recommendations] + [
                f"... 还有 {len(recommendations) - max_recommendations} 条建议"
            ]

        return recommendations

    def _build_detailed_metrics(
        self, report: ComprehensiveVerificationReport
    ) -> Dict[str, Any]:
        """构建详细指标"""
        metrics = report.verification_metrics
        ai_analysis = report.ai_dynamic_analysis

        # 处理AI分析为None的情况
        if ai_analysis is None:
            ai_analysis = type(
                "MockAIAnalysis",
                (),
                {
                    "confidence_score": 0.5,
                    "new_issues_detected": [],
                    "recommendations": [],
                },
            )()

        # 处理静态验证为None的情况
        if report.static_verification is None:
            static_metrics = {
                "original_issues_count": 0,
                "fixed_issues_count": 0,
                "remaining_issues_count": 0,
                "new_issues_count": 0,
            }
        else:
            static_metrics = {
                "original_issues_count": len(
                    report.static_verification.fix_comparison.original_issues
                ),
                "fixed_issues_count": len(
                    report.static_verification.fix_comparison.fixed_issues
                ),
                "remaining_issues_count": len(
                    report.static_verification.fix_comparison.remaining_issues
                ),
                "new_issues_count": report.static_verification.new_issues_count,
            }

        return {
            "verification_metrics": {
                "fix_success_rate": metrics.fix_success_rate,
                "quality_improvement_score": metrics.quality_improvement_score,
                "security_impact_score": metrics.security_impact_score,
                "performance_impact_score": metrics.performance_impact_score,
                "overall_verification_score": metrics.overall_verification_score,
            },
            "static_analysis_metrics": static_metrics,
            "ai_analysis_metrics": {
                "confidence_score": ai_analysis.confidence_score,
                "new_issues_detected_count": len(ai_analysis.new_issues_detected),
                "recommendations_count": len(ai_analysis.recommendations),
            },
        }

    def _format_for_summary(
        self, display_data: VerificationDisplayData
    ) -> VerificationDisplayData:
        """格式化为摘要格式"""
        # 保留关键信息，简化详细内容
        display_data.detailed_metrics = {}
        display_data.new_issues_analysis = {
            "total_new_issues": display_data.new_issues_analysis["total_new_issues"],
            "recommendation": display_data.new_issues_analysis["recommendation"],
        }
        return display_data

    def _format_for_detailed(
        self, display_data: VerificationDisplayData
    ) -> VerificationDisplayData:
        """格式化为详细格式"""
        # 保持完整信息，添加更多细节
        return display_data

    def _format_for_technical(
        self, display_data: VerificationDisplayData
    ) -> VerificationDisplayData:
        """格式化为技术格式"""
        # 强调技术指标和数据
        display_data.summary_overview.pop("verification_time", None)
        display_data.risk_assessment.pop("mitigation_strategies", None)
        return display_data

    def _format_for_quick_overview(
        self, display_data: VerificationDisplayData
    ) -> VerificationDisplayData:
        """格式化为快速概览"""
        # 只保留最关键的信息
        quick_data = VerificationDisplayData(
            display_id=display_data.display_id,
            session_id=display_data.session_id,
            suggestion_id=display_data.suggestion_id,
            file_path=display_data.file_path,
            summary_overview=display_data.summary_overview,
            fix_effectiveness={
                k: v
                for k, v in display_data.fix_effectiveness.items()
                if k in ["fix_success_rate", "problem_resolution_status"]
            },
            quality_impact={},
            new_issues_analysis={
                "total_new_issues": display_data.new_issues_analysis["total_new_issues"]
            },
            risk_assessment={
                "overall_risk_level": display_data.risk_assessment["overall_risk_level"]
            },
            recommendations=display_data.recommendations[:3],
            detailed_metrics={},
        )
        return quick_data

    def _format_for_comparison(
        self, display_data: VerificationDisplayData
    ) -> VerificationDisplayData:
        """格式化为对比格式"""
        # 强调修复前后的对比
        display_data.fix_effectiveness["before_after_comparison"] = {
            "before_issues": len(
                display_data.detailed_metrics.get("static_analysis_metrics", {}).get(
                    "original_issues_count", []
                )
            ),
            "after_issues": display_data.detailed_metrics.get(
                "static_analysis_metrics", {}
            ).get("remaining_issues_count", 0),
            "improvement_percentage": "计算改进百分比",
        }
        return display_data

    # 辅助方法
    def _format_status_with_icon(self, status: str) -> str:
        """格式化状态并添加图标"""
        icons = {
            "SUCCESS": "✅ 成功",
            "PARTIAL_SUCCESS": "⚠️ 部分成功",
            "FAILED": "❌ 失败",
            "REGRESSED": "📉 回退",
            "UNCERTAIN": "❓ 不确定",
        }
        return icons.get(status, f"❓ {status}")

    def _format_boolean_with_icon(self, value: bool, invert: bool = False) -> str:
        """格式化布尔值并添加图标"""
        actual_value = not value if invert else value
        return "✅ 是" if actual_value else "❌ 否"

    def _format_recommended_action(self, action: str) -> str:
        """格式化推荐行动"""
        actions = {
            "ACCEPT_FIX": "✅ 接受修复",
            "REJECT_FIX": "❌ 拒绝修复",
            "IMPROVE_FIX": "🔧 改进修复",
            "MANUAL_REVIEW": "👁️ 人工审查",
            "RETRY_ANALYSIS": "🔄 重新分析",
        }
        return actions.get(action, f"❓ {action}")

    def _translate_resolution_status(self, status: str) -> str:
        """翻译问题解决状态"""
        translations = {
            "fully_resolved": "完全解决",
            "partially_resolved": "部分解决",
            "not_resolved": "未解决",
            "regressed": "出现回退",
        }
        return translations.get(status, status)

    def _get_score_level(self, score: float) -> str:
        """获取分数等级"""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        else:
            return "poor"

    def _get_impact_icon(self, impact: str) -> str:
        """获取影响图标"""
        icons = {
            "improved": "📈",
            "unchanged": "➡️",
            "degraded": "📉",
            "positive": "✅",
            "negative": "❌",
            "minimal": "🔍",
            "moderate": "⚠️",
            "significant": "🔥",
        }
        return icons.get(impact, "❓")

    def _get_aspect_description(self, aspect: str) -> str:
        """获取方面描述"""
        descriptions = {
            "readability": "可读性",
            "maintainability": "可维护性",
            "complexity": "复杂度",
            "documentation": "文档",
            "security": "安全性",
            "performance": "性能",
        }
        return descriptions.get(aspect, aspect)

    def _calculate_quality_change(self, score: float) -> str:
        """计算质量变化"""
        if score > 0.7:
            return "显著改进"
        elif score > 0.5:
            return "有所改进"
        elif score > 0.3:
            return "轻微改进"
        else:
            return "无明显改进"

    def _analyze_issue_severity(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """分析问题严重程度分布"""
        severity_count = {"error": 0, "warning": 0, "info": 0, "unknown": 0}
        for issue in issues:
            severity = issue.get("severity", "unknown")
            if severity in severity_count:
                severity_count[severity] += 1
            else:
                severity_count["unknown"] += 1
        return severity_count

    def _get_new_issues_recommendation(self, count: int) -> str:
        """获取新问题建议"""
        if count == 0:
            return "✅ 很好！没有引入新问题"
        elif count <= 2:
            return "⚠️ 引入了少量新问题，建议关注"
        elif count <= 5:
            return "🔍 引入了一些新问题，建议审查"
        else:
            return "❌ 引入了较多新问题，建议重新评估修复方案"

    def _get_risk_icon(self, risk_level: str) -> str:
        """获取风险图标"""
        icons = {"low": "🟢", "medium": "🟡", "high": "🔴", "unknown": "⚪"}
        return icons.get(risk_level, "⚪")

    def _get_risk_color(self, risk_level: str) -> str:
        """获取风险颜色"""
        colors = {
            "low": "#28a745",
            "medium": "#ffc107",
            "high": "#dc3545",
            "unknown": "#6c757d",
        }
        return colors.get(risk_level, "#6c757d")

    def _calculate_risk_score(self, risk_assessment: Dict[str, Any]) -> float:
        """计算风险分数"""
        risk_levels = {"low": 0.2, "medium": 0.5, "high": 0.8, "unknown": 0.5}
        base_score = risk_levels.get(risk_assessment["overall_risk_level"], 0.5)

        # 根据风险因素数量调整分数
        factor_count = len(risk_assessment.get("risk_factors", []))
        adjusted_score = min(1.0, base_score + (factor_count * 0.1))

        return adjusted_score

    def generate_display_html(self, display_data: VerificationDisplayData) -> str:
        """
        生成HTML格式的展示内容

        Args:
            display_data: 展示数据

        Returns:
            str: HTML格式的展示内容
        """
        try:
            html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>修复验证结果</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f8f9fa; padding: 20px; border-radius: 5px; }
        .section { margin: 20px 0; padding: 15px; border: 1px solid #dee2e6; border-radius: 5px; }
        .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #e9ecef; border-radius: 3px; }
        .success { color: #28a745; }
        .warning { color: #ffc107; }
        .danger { color: #dc3545; }
        .recommendation { background-color: #d1ecf1; padding: 10px; margin: 5px 0; border-radius: 3px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>修复验证结果报告</h1>
        <p><strong>文件:</strong> {file_path}</p>
        <p><strong>验证时间:</strong> {verification_time}</p>
    </div>

    <div class="section">
        <h2>概览</h2>
        {summary_overview}
    </div>

    <div class="section">
        <h2>修复效果</h2>
        {fix_effectiveness}
    </div>

    <div class="section">
        <h2>质量影响</h2>
        {quality_impact}
    </div>

    <div class="section">
        <h2>新问题分析</h2>
        {new_issues_analysis}
    </div>

    <div class="section">
        <h2>风险评估</h2>
        {risk_assessment}
    </div>

    <div class="section">
        <h2>改进建议</h2>
        {recommendations}
    </div>
</body>
</html>
            """

            # 填充模板数据
            html_content = html_template.format(
                file_path=display_data.file_path,
                verification_time=display_data.summary_overview.get(
                    "verification_time", "未知"
                ),
                summary_overview=self._format_dict_to_html(
                    display_data.summary_overview
                ),
                fix_effectiveness=self._format_dict_to_html(
                    display_data.fix_effectiveness
                ),
                quality_impact=self._format_dict_to_html(display_data.quality_impact),
                new_issues_analysis=self._format_dict_to_html(
                    display_data.new_issues_analysis
                ),
                risk_assessment=self._format_dict_to_html(display_data.risk_assessment),
                recommendations=self._format_list_to_html(display_data.recommendations),
            )

            return html_content

        except Exception as e:
            self.logger.error(f"生成HTML展示失败: {e}")
            return f"<html><body><h1>生成展示内容失败: {e}</h1></body></html>"

    def _format_dict_to_html(self, data: Dict[str, Any]) -> str:
        """将字典转换为HTML格式"""
        html_parts = []
        for key, value in data.items():
            if isinstance(value, dict):
                html_parts.append(f"<p><strong>{key}:</strong></p>")
                html_parts.append(f"<ul>{self._format_dict_items(value)}</ul>")
            else:
                html_parts.append(f"<p><strong>{key}:</strong> {value}</p>")
        return "".join(html_parts)

    def _format_dict_items(self, data: Dict[str, Any]) -> str:
        """格式化字典项目为HTML列表"""
        items = []
        for key, value in data.items():
            items.append(f"<li><strong>{key}:</strong> {value}</li>")
        return "".join(items)

    def _format_list_to_html(self, data: List[str]) -> str:
        """将列表转换为HTML格式"""
        items = [f"<li>{item}</li>" for item in data]
        return f"<ul>{''.join(items)}</ul>" if items else "<p>无建议</p>"
