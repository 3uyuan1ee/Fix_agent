#!/usr/bin/env python3
"""
修复验证结果聚合器 - T014.3
整合静态分析和AI动态分析结果，形成全面的修复验证报告
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .verification_static_analyzer import StaticVerificationReport
from .ai_dynamic_analysis_caller import AIDynamicAnalysisResult
from .workflow_flow_state_manager import WorkflowSession

logger = get_logger()


@dataclass
class VerificationMetrics:
    """验证指标"""
    fix_success_rate: float           # 修复成功率
    new_issues_count: int            # 新问题数量
    quality_improvement_score: float # 质量改进分数
    security_impact_score: float     # 安全影响分数
    performance_impact_score: float  # 性能影响分数
    overall_verification_score: float # 整体验证分数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "fix_success_rate": self.fix_success_rate,
            "new_issues_count": self.new_issues_count,
            "quality_improvement_score": self.quality_improvement_score,
            "security_impact_score": self.security_impact_score,
            "performance_impact_score": self.performance_impact_score,
            "overall_verification_score": self.overall_verification_score
        }


@dataclass
class VerificationSummary:
    """验证摘要"""
    session_id: str
    suggestion_id: str
    file_path: str
    verification_status: str        # 验证状态
    problem_resolved: bool          # 问题是否解决
    introduced_new_issues: bool     # 是否引入新问题
    quality_improved: bool          # 质量是否改进
    recommended_action: str         # 推荐行动
    confidence_level: float         # 置信度水平

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "suggestion_id": self.suggestion_id,
            "file_path": self.file_path,
            "verification_status": self.verification_status,
            "problem_resolved": self.problem_resolved,
            "introduced_new_issues": self.introduced_new_issues,
            "quality_improved": self.quality_improved,
            "recommended_action": self.recommended_action,
            "confidence_level": self.confidence_level
        }


@dataclass
class ComprehensiveVerificationReport:
    """综合验证报告"""
    report_id: str
    session_id: str
    suggestion_id: str
    file_path: str
    verification_timestamp: datetime
    static_verification: StaticVerificationReport
    ai_dynamic_analysis: AIDynamicAnalysisResult
    verification_metrics: VerificationMetrics
    verification_summary: VerificationSummary
    detailed_findings: List[Dict[str, Any]]
    improvement_recommendations: List[str]
    risk_assessment: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "suggestion_id": self.suggestion_id,
            "file_path": self.file_path,
            "verification_timestamp": self.verification_timestamp.isoformat(),
            "static_verification": self.static_verification.to_dict(),
            "ai_dynamic_analysis": self.ai_dynamic_analysis.to_dict(),
            "verification_metrics": self.verification_metrics.to_dict(),
            "verification_summary": self.verification_summary.to_dict(),
            "detailed_findings": self.detailed_findings,
            "improvement_recommendations": self.improvement_recommendations,
            "risk_assessment": self.risk_assessment
        }


class VerificationStatus(Enum):
    """验证状态"""
    SUCCESS = "success"                   # 验证成功
    PARTIAL_SUCCESS = "partial_success"   # 部分成功
    FAILED = "failed"                     # 验证失败
    REGRESSED = "regressed"               # 出现回退
    UNCERTAIN = "uncertain"               # 结果不确定


class RecommendedAction(Enum):
    """推荐行动"""
    ACCEPT_FIX = "accept_fix"             # 接受修复
    REJECT_FIX = "reject_fix"             # 拒绝修复
    IMPROVE_FIX = "improve_fix"           # 改进修复
    MANUAL_REVIEW = "manual_review"       # 人工审查
    RETRY_ANALYSIS = "retry_analysis"     # 重新分析


class FixVerificationAggregator:
    """修复验证结果聚合器 - T014.3

    工作流位置: 节点H第三步，聚合静态分析和AI动态分析结果
    核心功能: 整合多种验证结果，形成全面的修复验证报告
    AI集成: 综合AI分析和传统分析的验证结果
    """

    def __init__(self, config_manager=None):
        """初始化修复验证结果聚合器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        self.config = self.config_manager.get("project_analysis", {})

        # 验证报告存储目录
        self.reports_dir = Path(self.config.get("verification_reports_dir", ".fix_backups/verification_reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # 权重配置
        self.metric_weights = self.config.get("verification_weights", {
            "static_analysis": 0.6,
            "ai_analysis": 0.4
        })

    def aggregate_verification_results(
        self,
        session_id: str,
        suggestion_id: str,
        static_verification_report: StaticVerificationReport,
        ai_dynamic_analysis_result: AIDynamicAnalysisResult
    ) -> ComprehensiveVerificationReport:
        """
        聚合验证结果

        Args:
            session_id: 会话ID
            suggestion_id: 修复建议ID
            static_verification_report: 静态验证报告
            ai_dynamic_analysis_result: AI动态分析结果

        Returns:
            ComprehensiveVerificationReport: 综合验证报告
        """
        try:
            self.logger.info(f"开始聚合验证结果: 会话={session_id}, 建议={suggestion_id}")

            # 1. 计算验证指标
            verification_metrics = self._calculate_verification_metrics(
                static_verification_report, ai_dynamic_analysis_result
            )

            # 2. 生成验证摘要
            verification_summary = self._generate_verification_summary(
                session_id, suggestion_id, static_verification_report.file_path,
                verification_metrics, ai_dynamic_analysis_result
            )

            # 3. 生成详细发现
            detailed_findings = self._generate_detailed_findings(
                static_verification_report, ai_dynamic_analysis_result
            )

            # 4. 生成改进建议
            improvement_recommendations = self._generate_improvement_recommendations(
                verification_metrics, ai_dynamic_analysis_result
            )

            # 5. 生成风险评估
            risk_assessment = self._generate_risk_assessment(
                static_verification_report, ai_dynamic_analysis_result
            )

            # 6. 创建综合验证报告
            comprehensive_report = ComprehensiveVerificationReport(
                report_id=str(uuid.uuid4()),
                session_id=session_id,
                suggestion_id=suggestion_id,
                file_path=static_verification_report.file_path,
                verification_timestamp=datetime.now(),
                static_verification=static_verification_report,
                ai_dynamic_analysis=ai_dynamic_analysis_result,
                verification_metrics=verification_metrics,
                verification_summary=verification_summary,
                detailed_findings=detailed_findings,
                improvement_recommendations=improvement_recommendations,
                risk_assessment=risk_assessment
            )

            # 7. 保存综合报告
            self._save_comprehensive_report(comprehensive_report)

            self.logger.info(f"验证结果聚合完成: 状态={verification_summary.verification_status}")
            return comprehensive_report

        except Exception as e:
            self.logger.error(f"聚合验证结果失败: {e}")
            raise

    def _calculate_verification_metrics(
        self,
        static_report: StaticVerificationReport,
        ai_analysis: AIDynamicAnalysisResult
    ) -> VerificationMetrics:
        """计算验证指标"""
        try:
            # 修复成功率（基于静态分析）
            fix_success_rate = static_report.success_rate

            # 新问题数量（基于静态分析）
            new_issues_count = static_report.new_issues_count

            # 质量改进分数（综合静态和AI分析）
            quality_score_static = static_report.overall_quality_score
            quality_score_ai = ai_analysis.fix_effectiveness_score
            quality_improvement_score = (
                quality_score_static * self.metric_weights["static_analysis"] +
                quality_score_ai * self.metric_weights["ai_analysis"]
            )

            # 安全影响分数（基于AI分析）
            security_impact_score = self._calculate_security_impact_score(ai_analysis)

            # 性能影响分数（基于AI分析）
            performance_impact_score = self._calculate_performance_impact_score(ai_analysis)

            # 整体验证分数
            overall_verification_score = (
                fix_success_rate * 0.4 +
                (1.0 - min(1.0, new_issues_count / 5.0)) * 0.3 +  # 新问题扣分
                quality_improvement_score * 0.3
            )

            return VerificationMetrics(
                fix_success_rate=fix_success_rate,
                new_issues_count=new_issues_count,
                quality_improvement_score=quality_improvement_score,
                security_impact_score=security_impact_score,
                performance_impact_score=performance_impact_score,
                overall_verification_score=overall_verification_score
            )

        except Exception as e:
            self.logger.error(f"计算验证指标失败: {e}")
            # 返回默认指标
            return VerificationMetrics(
                fix_success_rate=0.0,
                new_issues_count=999,
                quality_improvement_score=0.0,
                security_impact_score=0.0,
                performance_impact_score=0.0,
                overall_verification_score=0.0
            )

    def _calculate_security_impact_score(self, ai_analysis: AIDynamicAnalysisResult) -> float:
        """计算安全影响分数"""
        try:
            # 检查AI分析中的安全相关信息
            side_effects = ai_analysis.side_effects_analysis
            security_implications = side_effects.get("security_implications", "none")

            if security_implications == "positive":
                return 1.0
            elif security_implications == "none":
                return 0.8
            elif security_implications == "minor":
                return 0.6
            elif security_implications == "moderate":
                return 0.4
            elif security_implications == "major":
                return 0.2
            else:
                return 0.5  # 默认值

        except Exception:
            return 0.5

    def _calculate_performance_impact_score(self, ai_analysis: AIDynamicAnalysisResult) -> float:
        """计算性能影响分数"""
        try:
            # 检查AI分析中的性能相关信息
            side_effects = ai_analysis.side_effects_analysis
            performance_impact = side_effects.get("performance_impact", "minimal")

            if performance_impact == "positive":
                return 1.0
            elif performance_impact == "minimal":
                return 0.9
            elif performance_impact == "moderate":
                return 0.7
            elif performance_impact == "significant":
                return 0.4
            elif performance_impact == "negative":
                return 0.2
            else:
                return 0.7  # 默认值

        except Exception:
            return 0.7

    def _generate_verification_summary(
        self,
        session_id: str,
        suggestion_id: str,
        file_path: str,
        metrics: VerificationMetrics,
        ai_analysis: AIDynamicAnalysisResult
    ) -> VerificationSummary:
        """生成验证摘要"""
        try:
            # 确定验证状态
            verification_status = self._determine_verification_status(metrics)

            # 确定问题是否解决
            problem_resolved = ai_analysis.problem_resolution_status in ["fully_resolved", "partially_resolved"]

            # 确定是否引入新问题
            introduced_new_issues = metrics.new_issues_count > 0

            # 确定质量是否改进
            quality_improved = metrics.quality_improvement_score > 0.6

            # 确定推荐行动
            recommended_action = self._determine_recommended_action(
                verification_status, problem_resolved, introduced_new_issues, metrics
            )

            # 计算置信度水平
            confidence_level = (
                ai_analysis.confidence_score * 0.7 +
                metrics.overall_verification_score * 0.3
            )

            return VerificationSummary(
                session_id=session_id,
                suggestion_id=suggestion_id,
                file_path=file_path,
                verification_status=verification_status,
                problem_resolved=problem_resolved,
                introduced_new_issues=introduced_new_issues,
                quality_improved=quality_improved,
                recommended_action=recommended_action,
                confidence_level=confidence_level
            )

        except Exception as e:
            self.logger.error(f"生成验证摘要失败: {e}")
            # 返回默认摘要
            return VerificationSummary(
                session_id=session_id,
                suggestion_id=suggestion_id,
                file_path=file_path,
                verification_status="UNCERTAIN",
                problem_resolved=False,
                introduced_new_issues=True,
                quality_improved=False,
                recommended_action="MANUAL_REVIEW",
                confidence_level=0.0
            )

    def _determine_verification_status(self, metrics: VerificationMetrics) -> str:
        """确定验证状态"""
        overall_score = metrics.overall_verification_score

        if overall_score >= 0.8:
            return "SUCCESS"
        elif overall_score >= 0.6:
            return "PARTIAL_SUCCESS"
        elif overall_score >= 0.4:
            return "UNCERTAIN"
        elif overall_score >= 0.2:
            return "FAILED"
        else:
            return "REGRESSED"

    def _determine_recommended_action(
        self,
        verification_status: str,
        problem_resolved: bool,
        introduced_new_issues: bool,
        metrics: VerificationMetrics
    ) -> str:
        """确定推荐行动"""
        # 基于验证状态的基本决策
        if verification_status == "SUCCESS" and problem_resolved and not introduced_new_issues:
            return "ACCEPT_FIX"
        elif verification_status == "REGRESSED":
            return "REJECT_FIX"
        elif verification_status == "FAILED":
            return "IMPROVE_FIX"
        elif verification_status in ["PARTIAL_SUCCESS", "UNCERTAIN"]:
            return "MANUAL_REVIEW"
        elif introduced_new_issues and metrics.new_issues_count > 3:
            return "REJECT_FIX"
        elif not problem_resolved:
            return "IMPROVE_FIX"
        else:
            return "MANUAL_REVIEW"

    def _generate_detailed_findings(
        self,
        static_report: StaticVerificationReport,
        ai_analysis: AIDynamicAnalysisResult
    ) -> List[Dict[str, Any]]:
        """生成详细发现"""
        findings = []

        try:
            # 静态分析发现
            if static_report.fix_comparison.fixed_issues:
                findings.append({
                    "type": "static_fixed_issues",
                    "description": f"成功修复 {len(static_report.fix_comparison.fixed_issues)} 个问题",
                    "details": static_report.fix_comparison.fixed_issues,
                    "severity": "positive"
                })

            if static_report.new_issues_count > 0:
                findings.append({
                    "type": "static_new_issues",
                    "description": f"引入 {static_report.new_issues_count} 个新问题",
                    "details": [issue.to_dict() for issue in static_report.verification_issues if issue.is_new_issue],
                    "severity": "warning"
                })

            # AI分析发现
            if ai_analysis.new_issues_detected:
                findings.append({
                    "type": "ai_detected_issues",
                    "description": f"AI发现 {len(ai_analysis.new_issues_detected)} 个潜在问题",
                    "details": ai_analysis.new_issues_detected,
                    "severity": "info"
                })

            # 质量影响分析
            quality_impact = ai_analysis.code_quality_impact
            improved_aspects = [k for k, v in quality_impact.items() if v == "improved"]
            if improved_aspects:
                findings.append({
                    "type": "quality_improvement",
                    "description": f"改进了 {', '.join(improved_aspects)} 方面",
                    "details": quality_impact,
                    "severity": "positive"
                })

            # 副作用分析
            side_effects = ai_analysis.side_effects_analysis
            if side_effects.get("potential_breaking_changes"):
                findings.append({
                    "type": "breaking_changes",
                    "description": "可能存在破坏性变更",
                    "details": side_effects,
                    "severity": "error"
                })

        except Exception as e:
            self.logger.error(f"生成详细发现失败: {e}")
            findings.append({
                "type": "error",
                "description": f"生成详细发现时发生错误: {e}",
                "details": {},
                "severity": "error"
            })

        return findings

    def _generate_improvement_recommendations(
        self,
        metrics: VerificationMetrics,
        ai_analysis: AIDynamicAnalysisResult
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []

        try:
            # 添加AI的建议
            recommendations.extend(ai_analysis.recommendations)

            # 基于指标添加建议
            if metrics.new_issues_count > 0:
                recommendations.append(f"建议修复引入的 {metrics.new_issues_count} 个新问题")

            if metrics.fix_success_rate < 0.8:
                recommendations.append("建议重新审视修复方案，提高修复成功率")

            if metrics.quality_improvement_score < 0.6:
                recommendations.append("建议进一步优化代码质量")

            if metrics.security_impact_score < 0.7:
                recommendations.append("建议进行安全审查和加固")

            if metrics.performance_impact_score < 0.7:
                recommendations.append("建议进行性能优化测试")

        except Exception as e:
            self.logger.error(f"生成改进建议失败: {e}")
            recommendations.append("建议进行人工审查以确定改进方向")

        return recommendations

    def _generate_risk_assessment(
        self,
        static_report: StaticVerificationReport,
        ai_analysis: AIDynamicAnalysisResult
    ) -> Dict[str, Any]:
        """生成风险评估"""
        risk_assessment = {
            "overall_risk_level": "low",
            "risk_factors": [],
            "mitigation_strategies": []
        }

        try:
            risk_score = 0.0

            # 新问题风险
            if static_report.new_issues_count > 0:
                risk_score += static_report.new_issues_count * 0.2
                risk_assessment["risk_factors"].append({
                    "factor": "new_issues",
                    "description": f"引入了 {static_report.new_issues_count} 个新问题",
                    "impact": "medium"
                })

            # 修复失败风险
            if static_report.success_rate < 0.5:
                risk_score += 0.4
                risk_assessment["risk_factors"].append({
                    "factor": "low_success_rate",
                    "description": "修复成功率较低",
                    "impact": "high"
                })

            # 副作用风险
            side_effects = ai_analysis.side_effects_analysis
            if side_effects.get("potential_breaking_changes"):
                risk_score += 0.5
                risk_assessment["risk_factors"].append({
                    "factor": "breaking_changes",
                    "description": "可能存在破坏性变更",
                    "impact": "high"
                })

            # 确定整体风险等级
            if risk_score >= 1.0:
                risk_assessment["overall_risk_level"] = "high"
            elif risk_score >= 0.5:
                risk_assessment["overall_risk_level"] = "medium"
            else:
                risk_assessment["overall_risk_level"] = "low"

            # 生成缓解策略
            if risk_assessment["overall_risk_level"] != "low":
                risk_assessment["mitigation_strategies"] = [
                    "进行充分的测试验证",
                    "准备回滚方案",
                    "逐步部署和监控"
                ]

        except Exception as e:
            self.logger.error(f"生成风险评估失败: {e}")
            risk_assessment["overall_risk_level"] = "unknown"
            risk_assessment["risk_factors"].append({
                "factor": "analysis_error",
                "description": f"风险评估时发生错误: {e}",
                "impact": "unknown"
            })

        return risk_assessment

    def _save_comprehensive_report(self, report: ComprehensiveVerificationReport) -> None:
        """保存综合验证报告"""
        try:
            report_file = self.reports_dir / f"comprehensive_verification_{report.session_id}_{report.suggestion_id}.json"

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"综合验证报告已保存: {report_file}")

        except Exception as e:
            self.logger.error(f"保存综合验证报告失败: {e}")

    def get_comprehensive_report(
        self,
        session_id: str,
        suggestion_id: str
    ) -> Optional[ComprehensiveVerificationReport]:
        """
        获取综合验证报告

        Args:
            session_id: 会话ID
            suggestion_id: 修复建议ID

        Returns:
            Optional[ComprehensiveVerificationReport]: 综合验证报告
        """
        try:
            report_file = self.reports_dir / f"comprehensive_verification_{session_id}_{suggestion_id}.json"

            if not report_file.exists():
                return None

            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            # 重构报告对象
            return self._reconstruct_comprehensive_report(report_data)

        except Exception as e:
            self.logger.error(f"获取综合验证报告失败: {e}")
            return None

    def _reconstruct_comprehensive_report(self, report_data: Dict[str, Any]) -> ComprehensiveVerificationReport:
        """从字典数据重构综合验证报告"""
        # 这里需要实现完整的重构逻辑
        # 由于涉及复杂的数据结构，简化处理
        try:
            return ComprehensiveVerificationReport(
                report_id=report_data["report_id"],
                session_id=report_data["session_id"],
                suggestion_id=report_data["suggestion_id"],
                file_path=report_data["file_path"],
                verification_timestamp=datetime.fromisoformat(report_data["verification_timestamp"]),
                static_verification=None,  # 需要完整重构
                ai_dynamic_analysis=None,  # 需要完整重构
                verification_metrics=None,  # 需要完整重构
                verification_summary=None,  # 需要完整重构
                detailed_findings=report_data.get("detailed_findings", []),
                improvement_recommendations=report_data.get("improvement_recommendations", []),
                risk_assessment=report_data.get("risk_assessment", {})
            )
        except Exception as e:
            self.logger.error(f"重构综合验证报告失败: {e}")
            raise