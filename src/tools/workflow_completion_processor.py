#!/usr/bin/env python3
"""
工作流完成处理器 - T019.1
处理工作流的完成，生成最终的修复工作流完成报告
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .workflow_flow_state_manager import WorkflowSession
from .workflow_data_types import AIDetectedProblem, AIFixSuggestion
from .workflow_user_interaction_types import UserDecision
from .workflow_flow_state_manager import WorkflowNode, WorkflowFlowStateManager

logger = get_logger()


@dataclass
class WorkflowExecutionSummary:
    """工作流执行摘要"""
    session_id: str
    start_time: datetime
    end_time: datetime
    total_duration: float  # 秒
    total_problems: int
    solved_problems: int
    skipped_problems: int
    failed_problems: int
    success_rate: float
    workflow_completion_status: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "total_duration": self.total_duration,
            "total_problems": self.total_problems,
            "solved_problems": self.solved_problems,
            "skipped_problems": self.skipped_problems,
            "failed_problems": self.failed_problems,
            "success_rate": self.success_rate,
            "workflow_completion_status": self.workflow_completion_status
        }


@dataclass
class ProblemAnalysisResult:
    """问题分析结果"""
    issue_id: str
    file_path: str
    line_number: int
    problem_type: str
    severity: str
    status: str  # solved, skipped, failed, pending
    solution_id: Optional[str]
    fix_attempts: int
    final_outcome: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "issue_id": self.issue_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "problem_type": self.problem_type,
            "severity": self.severity,
            "status": self.status,
            "solution_id": self.solution_id,
            "fix_attempts": self.fix_attempts,
            "final_outcome": self.final_outcome
        }


@dataclass
class WorkflowCompletionReport:
    """工作流完成报告"""
    report_id: str
    session_id: str
    generation_timestamp: datetime
    execution_summary: WorkflowExecutionSummary
    problem_results: List[ProblemAnalysisResult]
    quality_metrics: Dict[str, Any]
    user_interactions: Dict[str, Any]
    recommendations: List[str]
    improvement_suggestions: List[str]
    lessons_learned: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "generation_timestamp": self.generation_timestamp.isoformat(),
            "execution_summary": self.execution_summary.to_dict(),
            "problem_results": [result.to_dict() for result in self.problem_results],
            "quality_metrics": self.quality_metrics,
            "user_interactions": self.user_interactions,
            "recommendations": self.recommendations,
            "improvement_suggestions": self.improvement_suggestions,
            "lessons_learned": self.lessons_learned
        }


class CompletionStatus(Enum):
    """完成状态"""
    SUCCESS = "success"                   # 完全成功
    PARTIAL_SUCCESS = "partial_success"   # 部分成功
    COMPLETED_WITH_ISSUES = "completed_with_issues"  # 完成但有问题
    INCOMPLETE = "incomplete"             # 未完成
    FAILED = "failed"                     # 失败


class WorkflowCompletionProcessor:
    """工作流完成处理器 - T019.1

    工作流位置: 节点M，处理工作流的完成
    核心功能: 生成最终的修复工作流完成报告
    用户协作: 为用户提供完整的工作执行总结
    """

    def __init__(self, config_manager=None):
        """初始化工作流完成处理器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.state_manager = WorkflowFlowStateManager()

        # 获取配置
        self.config = self.config_manager.get("project_analysis", {})

        # 完成报告存储目录
        self.reports_dir = Path(self.config.get("completion_reports_dir", ".fix_backups/completion_reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def process_workflow_completion(self, session_id: str) -> Dict[str, Any]:
        """
        处理工作流完成

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            self.logger.info(f"处理工作流完成: 会话={session_id}")

            # 获取会话信息
            session = self.state_manager.get_session(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 生成执行摘要
            execution_summary = self._generate_execution_summary(session)

            # 分析所有问题结果
            problem_results = self._analyze_all_problems(session)

            # 计算质量指标
            quality_metrics = self._calculate_quality_metrics(session, execution_summary)

            # 分析用户交互
            user_interactions = self._analyze_user_interactions(session)

            # 生成建议和改进意见
            recommendations = self._generate_recommendations(execution_summary, quality_metrics)
            improvement_suggestions = self._generate_improvement_suggestions(session, quality_metrics)
            lessons_learned = self._extract_lessons_learned(session, execution_summary)

            # 创建完成报告
            completion_report = WorkflowCompletionReport(
                report_id=str(uuid.uuid4()),
                session_id=session_id,
                generation_timestamp=datetime.now(),
                execution_summary=execution_summary,
                problem_results=problem_results,
                quality_metrics=quality_metrics,
                user_interactions=user_interactions,
                recommendations=recommendations,
                improvement_suggestions=improvement_suggestions,
                lessons_learned=lessons_learned
            )

            # 保存完成报告
            self._save_completion_report(completion_report)

            # 生成用户友好的总结
            user_summary = self._generate_user_summary(completion_report)

            # 更新会话完成状态
            self._update_session_completion_status(session, completion_report)

            # 生成处理结果
            result = {
                "success": True,
                "session_id": session_id,
                "report_id": completion_report.report_id,
                "completion_status": execution_summary.workflow_completion_status,
                "execution_summary": execution_summary.to_dict(),
                "user_summary": user_summary,
                "statistics": {
                    "total_problems": execution_summary.total_problems,
                    "solved_problems": execution_summary.solved_problems,
                    "success_rate": execution_summary.success_rate,
                    "total_duration": execution_summary.total_duration
                },
                "message": f"工作流已完成: {execution_summary.workflow_completion_status}"
            }

            self.logger.info(f"工作流完成处理完成: {result}")
            return result

        except Exception as e:
            self.logger.error(f"处理工作流完成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "处理工作流完成失败"
            }

    def _generate_execution_summary(self, session: WorkflowSession) -> WorkflowExecutionSummary:
        """生成执行摘要"""
        try:
            # 获取时间信息
            start_time = getattr(session, 'created_at', datetime.now())
            end_time = datetime.now()
            total_duration = (end_time - start_time).total_seconds()

            # 统计问题数量
            total_problems = len(session.detected_problems)
            solved_problems = len(getattr(session, 'solved_problems', []))
            skipped_problems = len(getattr(session, 'skip_history', []))

            # 统计失败问题
            failed_problems = 0
            if hasattr(session, 'reanalysis_history'):
                for issue_id, history in session.reanalysis_history.items():
                    if history.get('retry_count', 0) >= self.config.get("max_retry_attempts", 3):
                        failed_problems += 1

            # 计算成功率
            success_rate = solved_problems / total_problems if total_problems > 0 else 0.0

            # 确定完成状态
            completion_status = self._determine_completion_status(
                total_problems, solved_problems, skipped_problems, failed_problems
            )

            return WorkflowExecutionSummary(
                session_id=session.session_id,
                start_time=start_time,
                end_time=end_time,
                total_duration=total_duration,
                total_problems=total_problems,
                solved_problems=solved_problems,
                skipped_problems=skipped_problems,
                failed_problems=failed_problems,
                success_rate=success_rate,
                workflow_completion_status=completion_status
            )

        except Exception as e:
            self.logger.error(f"生成执行摘要失败: {e}")
            # 返回默认摘要
            return WorkflowExecutionSummary(
                session_id=session.session_id,
                start_time=datetime.now(),
                end_time=datetime.now(),
                total_duration=0.0,
                total_problems=0,
                solved_problems=0,
                skipped_problems=0,
                failed_problems=0,
                success_rate=0.0,
                workflow_completion_status="FAILED"
            )

    def _determine_completion_status(
        self,
        total: int,
        solved: int,
        skipped: int,
        failed: int
    ) -> str:
        """确定完成状态"""
        if total == 0:
            return CompletionStatus.SUCCESS.value
        elif solved == total:
            return CompletionStatus.SUCCESS.value
        elif solved + skipped == total:
            return CompletionStatus.PARTIAL_SUCCESS.value
        elif solved + skipped + failed == total:
            return CompletionStatus.COMPLETED_WITH_ISSUES.value
        elif failed > total / 2:
            return CompletionStatus.FAILED.value
        else:
            return CompletionStatus.INCOMPLETE.value

    def _analyze_all_problems(self, session: WorkflowSession) -> List[ProblemAnalysisResult]:
        """分析所有问题结果"""
        try:
            problem_results = []

            for problem in session.detected_problems:
                # 确定问题状态
                status = self._determine_problem_status(session, problem.issue_id)

                # 获取解决方案ID
                solution_id = self._get_solution_id(session, problem.issue_id)

                # 计算修复尝试次数
                fix_attempts = self._count_fix_attempts(session, problem.issue_id)

                # 确定最终结果
                final_outcome = self._determine_final_outcome(status, fix_attempts)

                result = ProblemAnalysisResult(
                    issue_id=problem.issue_id,
                    file_path=problem.file_path,
                    line_number=problem.line,
                    problem_type=problem.issue_type.value,
                    severity=problem.severity.value,
                    status=status,
                    solution_id=solution_id,
                    fix_attempts=fix_attempts,
                    final_outcome=final_outcome
                )

                problem_results.append(result)

            return problem_results

        except Exception as e:
            self.logger.error(f"分析所有问题结果失败: {e}")
            return []

    def _determine_problem_status(self, session: WorkflowSession, issue_id: str) -> str:
        """确定问题状态"""
        # 检查是否已解决
        if hasattr(session, 'solved_problems') and issue_id in [s.split('_')[-1] for s in session.solved_problems]:
            return "solved"

        # 检查是否被跳过
        if hasattr(session, 'skip_history') and any(issue_id in skip for skip in session.skip_history):
            return "skipped"

        # 检查是否失败
        if hasattr(session, 'reanalysis_history') and issue_id in session.reanalysis_history:
            history = session.reanalysis_history[issue_id]
            if history.get('retry_count', 0) >= self.config.get("max_retry_attempts", 3):
                return "failed"

        # 检查是否仍在待处理
        if issue_id in session.pending_problems:
            return "pending"

        return "unknown"

    def _get_solution_id(self, session: WorkflowSession, issue_id: str) -> Optional[str]:
        """获取解决方案ID"""
        if hasattr(session, 'solved_problems'):
            for solution_id in session.solved_problems:
                if issue_id in solution_id:
                    return solution_id
        return None

    def _count_fix_attempts(self, session: WorkflowSession, issue_id: str) -> int:
        """计算修复尝试次数"""
        count = 0

        # 统计修复建议数量
        for suggestion in getattr(session, 'fix_suggestions', []):
            if hasattr(suggestion, 'issue_id') and suggestion.issue_id == issue_id:
                count += 1

        # 添加重新分析次数
        if hasattr(session, 'reanalysis_history') and issue_id in session.reanalysis_history:
            count += session.reanalysis_history[issue_id].get('retry_count', 0)

        return count

    def _determine_final_outcome(self, status: str, fix_attempts: int) -> str:
        """确定最终结果"""
        if status == "solved":
            return "成功解决"
        elif status == "skipped":
            return "用户跳过"
        elif status == "failed":
            return "修复失败"
        elif status == "pending":
            return "未处理"
        else:
            return f"状态未知 (尝试{fix_attempts}次)"

    def _calculate_quality_metrics(
        self,
        session: WorkflowSession,
        summary: WorkflowExecutionSummary
    ) -> Dict[str, Any]:
        """计算质量指标"""
        try:
            metrics = {
                "efficiency_metrics": {
                    "problems_per_hour": summary.total_problems / (summary.total_duration / 3600) if summary.total_duration > 0 else 0,
                    "average_time_per_problem": summary.total_duration / summary.total_problems if summary.total_problems > 0 else 0,
                    "workflow_efficiency": summary.success_rate
                },
                "quality_metrics": {
                    "resolution_quality": summary.solved_problems / max(1, summary.solved_problems + summary.failed_problems),
                    "completeness_rate": (summary.solved_problems + summary.skipped_problems) / max(1, summary.total_problems)
                },
                "user_satisfaction": {
                    "decision_consistency": self._calculate_decision_consistency(session),
                    "user_engagement": self._calculate_user_engagement(session)
                }
            }

            return metrics

        except Exception as e:
            self.logger.error(f"计算质量指标失败: {e}")
            return {}

    def _calculate_decision_consistency(self, session: WorkflowSession) -> float:
        """计算决策一致性"""
        try:
            total_decisions = 0
            consistent_decisions = 0

            # 这里可以实现更复杂的一致性分析逻辑
            # 暂时返回默认值
            return 0.8

        except Exception:
            return 0.5

    def _calculate_user_engagement(self, session: WorkflowSession) -> float:
        """计算用户参与度"""
        try:
            total_interactions = (
                len(getattr(session, 'user_decisions', [])) +
                len(getattr(session, 'verification_decisions', []))
            )
            total_problems = len(session.detected_problems)

            return min(1.0, total_interactions / max(1, total_problems))

        except Exception:
            return 0.5

    def _analyze_user_interactions(self, session: WorkflowSession) -> Dict[str, Any]:
        """分析用户交互"""
        try:
            interactions = {
                "total_decisions": len(getattr(session, 'user_decisions', [])),
                "verification_decisions": len(getattr(session, 'verification_decisions', [])),
                "skip_decisions": len(getattr(session, 'skip_history', [])),
                "decision_patterns": self._analyze_decision_patterns(session),
                "feedback_summary": self._summarize_user_feedback(session)
            }

            return interactions

        except Exception as e:
            self.logger.error(f"分析用户交互失败: {e}")
            return {}

    def _analyze_decision_patterns(self, session: WorkflowSession) -> Dict[str, Any]:
        """分析决策模式"""
        patterns = {
            "acceptance_rate": 0.0,
            "rejection_rate": 0.0,
            "modification_rate": 0.0,
            "skip_rate": 0.0
        }

        # 实现决策模式分析逻辑
        # 这里简化处理

        return patterns

    def _summarize_user_feedback(self, session: WorkflowSession) -> Dict[str, Any]:
        """总结用户反馈"""
        summary = {
            "positive_feedback_count": 0,
            "negative_feedback_count": 0,
            "common_themes": [],
            "overall_sentiment": "neutral"
        }

        # 实现反馈总结逻辑
        # 这里简化处理

        return summary

    def _generate_recommendations(
        self,
        summary: WorkflowExecutionSummary,
        metrics: Dict[str, Any]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于成功率的建议
        if summary.success_rate > 0.8:
            recommendations.append("工作流执行效果优秀，建议保持当前策略")
        elif summary.success_rate < 0.5:
            recommendations.append("建议改进问题识别和修复策略")
        else:
            recommendations.append("工作流执行效果良好，可考虑优化部分环节")

        # 基于效率的建议
        efficiency = metrics.get("efficiency_metrics", {})
        if efficiency.get("problems_per_hour", 0) < 2:
            recommendations.append("建议优化处理流程，提高效率")

        # 基于完成度的建议
        if summary.failed_problems > 0:
            recommendations.append(f"有 {summary.failed_problems} 个问题需要人工干预")

        if not recommendations:
            recommendations.append("工作流执行正常，建议继续使用")

        return recommendations

    def _generate_improvement_suggestions(
        self,
        session: WorkflowSession,
        metrics: Dict[str, Any]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 基于质量指标的改进建议
        quality = metrics.get("quality_metrics", {})
        if quality.get("resolution_quality", 1.0) < 0.7:
            suggestions.append("改进修复方案质量，减少失败率")

        if quality.get("completeness_rate", 1.0) < 0.8:
            suggestions.append("提高问题处理完整性")

        # 基于用户交互的改进建议
        user_satisfaction = metrics.get("user_satisfaction", {})
        if user_satisfaction.get("decision_consistency", 1.0) < 0.7:
            suggestions.append("改进AI建议的一致性和可靠性")

        return suggestions if suggestions else ["当前流程运行良好"]

    def _extract_lessons_learned(
        self,
        session: WorkflowSession,
        summary: WorkflowExecutionSummary
    ) -> List[str]:
        """提取经验教训"""
        lessons = []

        # 基于执行结果的经验教训
        if summary.success_rate > 0.8:
            lessons.append("当前AI驱动的工作流程能够有效解决大部分问题")
        else:
            lessons.append("需要改进问题识别或修复策略以提高成功率")

        if summary.skipped_problems > 0:
            lessons.append(f"用户跳过了 {summary.skipped_problems} 个问题，可能需要更好的问题筛选")

        if summary.failed_problems > 0:
            lessons.append("某些问题超出了自动处理能力，需要人工介入机制")

        # 基于持续时间的经验教训
        if summary.total_duration > 3600:  # 超过1小时
            lessons.append("大规模项目分析可能需要优化性能")

        return lessons if lessons else ["工作流程按预期执行"]

    def _save_completion_report(self, report: WorkflowCompletionReport) -> None:
        """保存完成报告"""
        try:
            report_file = self.reports_dir / f"completion_report_{report.session_id}_{report.generation_timestamp.strftime('%Y%m%d_%H%M%S')}.json"

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"工作流完成报告已保存: {report.report_id}")

        except Exception as e:
            self.logger.error(f"保存完成报告失败: {e}")

    def _generate_user_summary(self, report: WorkflowCompletionReport) -> Dict[str, Any]:
        """生成用户友好的总结"""
        try:
            summary = {
                "title": "AI修复工作流执行完成",
                "status": report.execution_summary.workflow_completion_status,
                "key_stats": {
                    "总问题数": report.execution_summary.total_problems,
                    "已解决问题": report.execution_summary.solved_problems,
                    "成功率": f"{report.execution_summary.success_rate:.1%}",
                    "执行时长": f"{report.execution_summary.total_duration:.1f}秒"
                },
                "status_description": self._get_status_description(report.execution_summary),
                "highlights": self._get_execution_highlights(report),
                "next_steps": self._get_next_steps(report)
            }

            return summary

        except Exception as e:
            self.logger.error(f"生成用户总结失败: {e}")
            return {"error": str(e)}

    def _get_status_description(self, summary: WorkflowExecutionSummary) -> str:
        """获取状态描述"""
        if summary.workflow_completion_status == "success":
            return "工作流执行成功，所有问题都得到了妥善处理"
        elif summary.workflow_completion_status == "partial_success":
            return "工作流部分成功，大部分问题已处理"
        elif summary.workflow_completion_status == "completed_with_issues":
            return "工作流已完成，但部分问题处理失败"
        elif summary.workflow_completion_status == "incomplete":
            return "工作流未完全完成，仍有问题待处理"
        else:
            return "工作流执行遇到问题"

    def _get_execution_highlights(self, report: WorkflowCompletionReport) -> List[str]:
        """获取执行亮点"""
        highlights = []

        if report.execution_summary.solved_problems > 0:
            highlights.append(f"成功解决了 {report.execution_summary.solved_problems} 个问题")

        if report.execution_summary.success_rate > 0.8:
            highlights.append("处理成功率高，质量表现优秀")

        if report.execution_summary.total_duration < 600:  # 10分钟内
            highlights.append("执行效率高，快速完成分析")

        return highlights if highlights else ["工作流程正常执行"]

    def _get_next_steps(self, report: WorkflowCompletionReport) -> List[str]:
        """获取后续步骤"""
        steps = []

        if report.execution_summary.remaining_problems > 0:
            steps.append("继续处理剩余问题")
        else:
            steps.append("所有问题已处理完成")

        steps.append("查看详细的执行报告")
        steps.append("根据建议进行代码优化")

        return steps

    def _update_session_completion_status(self, session: WorkflowSession, report: WorkflowCompletionReport) -> None:
        """更新会话完成状态"""
        try:
            session.completion_status = report.execution_summary.workflow_completion_status
            session.completion_timestamp = report.generation_timestamp
            session.completion_report_id = report.report_id

            self.state_manager.save_session(session)

        except Exception as e:
            self.logger.error(f"更新会话完成状态失败: {e}")

    def get_completion_report(self, session_id: str) -> Optional[WorkflowCompletionReport]:
        """
        获取完成报告

        Args:
            session_id: 会话ID

        Returns:
            Optional[WorkflowCompletionReport]: 完成报告
        """
        try:
            # 扫描完成报告文件
            pattern = f"completion_report_{session_id}_*.json"
            report_files = list(self.reports_dir.glob(pattern))

            if not report_files:
                return None

            # 获取最新的报告
            latest_file = max(report_files, key=lambda f: f.stat().st_mtime)
            with open(latest_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            return self._reconstruct_completion_report(report_data)

        except Exception as e:
            self.logger.error(f"获取完成报告失败: {e}")
            return None

    def _reconstruct_completion_report(self, report_data: Dict[str, Any]) -> WorkflowCompletionReport:
        """从字典数据重构完成报告"""
        try:
            # 重构执行摘要
            summary_data = report_data["execution_summary"]
            execution_summary = WorkflowExecutionSummary(
                session_id=summary_data["session_id"],
                start_time=datetime.fromisoformat(summary_data["start_time"]),
                end_time=datetime.fromisoformat(summary_data["end_time"]),
                total_duration=summary_data["total_duration"],
                total_problems=summary_data["total_problems"],
                solved_problems=summary_data["solved_problems"],
                skipped_problems=summary_data["skipped_problems"],
                failed_problems=summary_data["failed_problems"],
                success_rate=summary_data["success_rate"],
                workflow_completion_status=summary_data["workflow_completion_status"]
            )

            # 重构问题结果
            problem_results = []
            for result_data in report_data["problem_results"]:
                problem_results.append(ProblemAnalysisResult(
                    issue_id=result_data["issue_id"],
                    file_path=result_data["file_path"],
                    line_number=result_data["line_number"],
                    problem_type=result_data["problem_type"],
                    severity=result_data["severity"],
                    status=result_data["status"],
                    solution_id=result_data.get("solution_id"),
                    fix_attempts=result_data["fix_attempts"],
                    final_outcome=result_data["final_outcome"]
                ))

            return WorkflowCompletionReport(
                report_id=report_data["report_id"],
                session_id=report_data["session_id"],
                generation_timestamp=datetime.fromisoformat(report_data["generation_timestamp"]),
                execution_summary=execution_summary,
                problem_results=problem_results,
                quality_metrics=report_data["quality_metrics"],
                user_interactions=report_data["user_interactions"],
                recommendations=report_data["recommendations"],
                improvement_suggestions=report_data["improvement_suggestions"],
                lessons_learned=report_data["lessons_learned"]
            )

        except Exception as e:
            self.logger.error(f"重构完成报告失败: {e}")
            raise