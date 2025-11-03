#!/usr/bin/env python3
"""
问题状态检查器 - T018.1
检查是否还有待处理的问题，判断修复工作流是否继续或结束
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
from .workflow_flow_state_manager import WorkflowSession
from .workflow_data_types import AIDetectedProblem
from .workflow_user_interaction_types import UserDecision
from .workflow_flow_state_manager import WorkflowNode, WorkflowFlowStateManager

logger = get_logger()


@dataclass
class ProblemStatusSummary:
    """问题状态摘要"""
    total_problems: int
    solved_problems: int
    skipped_problems: int
    failed_problems: int
    remaining_problems: int
    problems_requiring_intervention: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_problems": self.total_problems,
            "solved_problems": self.solved_problems,
            "skipped_problems": self.skipped_problems,
            "failed_problems": self.failed_problems,
            "remaining_problems": self.remaining_problems,
            "problems_requiring_intervention": self.problems_requiring_intervention
        }


@dataclass
class WorkflowProgressReport:
    """工作流进度报告"""
    report_id: str
    session_id: str
    check_timestamp: datetime
    status_summary: ProblemStatusSummary
    workflow_statistics: Dict[str, Any]
    remaining_work: List[Dict[str, Any]]
    recommendations: List[str]
    next_action: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "report_id": self.report_id,
            "session_id": self.session_id,
            "check_timestamp": self.check_timestamp.isoformat(),
            "status_summary": self.status_summary.to_dict(),
            "workflow_statistics": self.workflow_statistics,
            "remaining_work": self.remaining_work,
            "recommendations": self.recommendations,
            "next_action": self.next_action
        }


class WorkflowDecision(Enum):
    """工作流决策"""
    CONTINUE_ANALYSIS = "continue_analysis"    # 继续分析
    COMPLETE_WORKFLOW = "complete_workflow"    # 完成工作流
    REQUIRE_INTERVENTION = "require_intervention"  # 需要干预


class ProblemStatusChecker:
    """问题状态检查器 - T018.1

    工作流位置: 节点L，检查是否还有待处理的问题
    核心功能: 判断修复工作流是否继续或结束
    用户协作: 为用户提供清晰的工作流状态信息
    """

    def __init__(self, config_manager=None):
        """初始化问题状态检查器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.state_manager = WorkflowFlowStateManager()

        # 获取配置
        self.config = self.config_manager.get_config("project_analysis", {})

        # 检查报告存储目录
        self.reports_dir = Path(self.config.get("status_check_reports_dir", ".fix_backups/status_reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def check_problem_status(self, session_id: str) -> Dict[str, Any]:
        """
        检查问题状态

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 检查结果
        """
        try:
            self.logger.info(f"检查问题状态: 会话={session_id}")

            # 获取会话信息
            session = self.state_manager.get_session(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 统计问题状态
            status_summary = self._calculate_status_summary(session)

            # 生成工作流统计
            workflow_statistics = self._generate_workflow_statistics(session)

            # 分析剩余工作
            remaining_work = self._analyze_remaining_work(session)

            # 生成建议
            recommendations = self._generate_recommendations(status_summary, workflow_statistics)

            # 确定下一步行动
            next_action = self._determine_next_action(status_summary, remaining_work)

            # 创建进度报告
            progress_report = WorkflowProgressReport(
                report_id=str(uuid.uuid4()),
                session_id=session_id,
                check_timestamp=datetime.now(),
                status_summary=status_summary,
                workflow_statistics=workflow_statistics,
                remaining_work=remaining_work,
                recommendations=recommendations,
                next_action=next_action
            )

            # 保存进度报告
            self._save_progress_report(progress_report)

            # 转换到相应节点
            if next_action == WorkflowDecision.CONTINUE_ANALYSIS.value:
                target_node = WorkflowNode.PROBLEM_DETECTION
                transition_message = "继续处理剩余问题"
            elif next_action == WorkflowDecision.COMPLETE_WORKFLOW.value:
                target_node = WorkflowNode.WORKFLOW_COMPLETE
                transition_message = "所有问题已处理完成"
            else:
                target_node = WorkflowNode.WORKFLOW_COMPLETE
                transition_message = "工作流完成，需要人工审查"

            self.state_manager.transition_to(
                session_id,
                target_node,
                transition_message
            )

            # 生成检查结果
            result = {
                "success": True,
                "session_id": session_id,
                "status_summary": status_summary.to_dict(),
                "next_action": next_action,
                "next_node": target_node.value,
                "remaining_problems": status_summary.remaining_problems,
                "workflow_complete": status_summary.remaining_problems == 0,
                "progress_report_id": progress_report.report_id,
                "message": f"问题状态检查完成: {transition_message}"
            }

            self.logger.info(f"问题状态检查完成: {result}")
            return result

        except Exception as e:
            self.logger.error(f"检查问题状态失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "检查问题状态失败"
            }

    def _calculate_status_summary(self, session: WorkflowSession) -> ProblemStatusSummary:
        """计算问题状态摘要"""
        try:
            # 总问题数
            total_problems = len(session.detected_problems)

            # 已解决问题数
            solved_problems = len(getattr(session, 'solved_problems', []))

            # 跳过问题数
            skipped_problems = len(getattr(session, 'skip_history', []))

            # 失败问题数（需要重新分析但超过重试次数的）
            failed_problems = 0
            if hasattr(session, 'reanalysis_history'):
                for issue_id, history in session.reanalysis_history.items():
                    if history.get('retry_count', 0) >= self.config.get("max_retry_attempts", 3):
                        failed_problems += 1

            # 待处理问题数
            remaining_problems = len(session.pending_problems)

            # 需要人工干预的问题数
            problems_requiring_intervention = 0
            for issue_id, status in session.problem_processing_status.items():
                if status in ["requires_human_intervention", "unknown"]:
                    problems_requiring_intervention += 1

            return ProblemStatusSummary(
                total_problems=total_problems,
                solved_problems=solved_problems,
                skipped_problems=skipped_problems,
                failed_problems=failed_problems,
                remaining_problems=remaining_problems,
                problems_requiring_intervention=problems_requiring_intervention
            )

        except Exception as e:
            self.logger.error(f"计算状态摘要失败: {e}")
            return ProblemStatusSummary(
                total_problems=0,
                solved_problems=0,
                skipped_problems=0,
                failed_problems=0,
                remaining_problems=0,
                problems_requiring_intervention=0
            )

    def _generate_workflow_statistics(self, session: WorkflowSession) -> Dict[str, Any]:
        """生成工作流统计"""
        try:
            statistics = {
                "session_duration": self._calculate_session_duration(session),
                "workflow_nodes_visited": self._get_visited_nodes(session),
                "total_fix_attempts": len(getattr(session, 'fix_suggestions', [])),
                "verification_decisions": len(getattr(session, 'verification_decisions', [])),
                "reanalysis_triggered": len(getattr(session, 'reanalysis_history', {})),
                "average_time_per_problem": self._calculate_average_time_per_problem(session)
            }

            # 成功率统计
            total_processed = statistics["total_fix_attempts"]
            if total_processed > 0:
                statistics["success_rate"] = len(getattr(session, 'solved_problems', [])) / total_processed
                statistics["skip_rate"] = len(getattr(session, 'skip_history', [])) / total_processed
            else:
                statistics["success_rate"] = 0.0
                statistics["skip_rate"] = 0.0

            return statistics

        except Exception as e:
            self.logger.error(f"生成工作流统计失败: {e}")
            return {}

    def _calculate_session_duration(self, session: WorkflowSession) -> float:
        """计算会话持续时间（秒）"""
        try:
            if hasattr(session, 'created_at') and session.created_at:
                duration = datetime.now() - session.created_at
                return duration.total_seconds()
            return 0.0
        except Exception:
            return 0.0

    def _get_visited_nodes(self, session: WorkflowSession) -> List[str]:
        """获取访问过的节点"""
        try:
            if hasattr(session, 'state_history'):
                return [transition.get("to_node") for transition in session.state_history]
            return []
        except Exception:
            return []

    def _calculate_average_time_per_problem(self, session: WorkflowSession) -> float:
        """计算每个问题的平均处理时间"""
        try:
            duration = self._calculate_session_duration(session)
            total_problems = len(session.detected_problems)
            return duration / total_problems if total_problems > 0 else 0.0
        except Exception:
            return 0.0

    def _analyze_remaining_work(self, session: WorkflowSession) -> List[Dict[str, Any]]:
        """分析剩余工作"""
        try:
            remaining_work = []

            for issue_id in session.pending_problems:
                problem = self._get_problem_by_id(session, issue_id)
                if problem:
                    work_item = {
                        "issue_id": issue_id,
                        "file_path": problem.file_path,
                        "line": problem.line,
                        "problem_type": problem.issue_type.value,
                        "severity": problem.severity.value,
                        "priority": self._calculate_problem_priority(problem),
                        "estimated_complexity": self._estimate_complexity(problem)
                    }
                    remaining_work.append(work_item)

            # 按优先级排序
            remaining_work.sort(key=lambda x: x["priority"], reverse=True)

            return remaining_work

        except Exception as e:
            self.logger.error(f"分析剩余工作失败: {e}")
            return []

    def _get_problem_by_id(self, session: WorkflowSession, issue_id: str) -> Optional[AIDetectedProblem]:
        """根据ID获取问题信息"""
        for problem in session.detected_problems:
            if problem.issue_id == issue_id:
                return problem
        return None

    def _calculate_problem_priority(self, problem: AIDetectedProblem) -> float:
        """计算问题优先级"""
        severity_weights = {
            "error": 1.0,
            "warning": 0.7,
            "info": 0.4
        }

        base_priority = severity_weights.get(problem.severity.value, 0.5)

        # 根据问题类型调整优先级
        if problem.issue_type.value == "security":
            base_priority += 0.2
        elif problem.issue_type.value == "performance":
            base_priority += 0.1

        return min(1.0, base_priority)

    def _estimate_complexity(self, problem: AIDetectedProblem) -> str:
        """估计问题复杂度"""
        # 基于问题类型和严重程度估计复杂度
        if problem.severity.value == "error":
            return "high"
        elif problem.issue_type.value in ["security", "performance"]:
            return "medium"
        else:
            return "low"

    def _generate_recommendations(
        self,
        status_summary: ProblemStatusSummary,
        workflow_statistics: Dict[str, Any]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于剩余问题数的建议
        if status_summary.remaining_problems == 0:
            recommendations.append("所有问题已处理完成，建议生成最终报告")
        elif status_summary.remaining_problems <= 3:
            recommendations.append("剩余问题较少，建议继续完成")
        else:
            recommendations.append("剩余问题较多，建议优先处理高优先级问题")

        # 基于成功率的建议
        success_rate = workflow_statistics.get("success_rate", 0.0)
        if success_rate < 0.5:
            recommendations.append("成功率较低，建议调整分析策略")
        elif success_rate > 0.8:
            recommendations.append("成功率很高，继续保持当前策略")

        # 基于失败问题的建议
        if status_summary.failed_problems > 0:
            recommendations.append(f"有 {status_summary.failed_problems} 个问题需要人工干预")

        # 基于跳过问题的建议
        if status_summary.skipped_problems > 0:
            recommendations.append(f"有 {status_summary.skipped_problems} 个问题被跳过，建议后续复查")

        return recommendations if recommendations else ["继续执行当前工作流程"]

    def _determine_next_action(
        self,
        status_summary: ProblemStatusSummary,
        remaining_work: List[Dict[str, Any]]
    ) -> str:
        """确定下一步行动"""
        # 如果没有剩余问题，完成工作流
        if status_summary.remaining_problems == 0:
            return WorkflowDecision.COMPLETE_WORKFLOW.value

        # 如果有需要人工干预的问题，建议完成工作流
        if status_summary.problems_requiring_intervention > 0:
            return WorkflowDecision.REQUIRE_INTERVENTION.value

        # 如果剩余问题都是低优先级，可以考虑完成工作流
        high_priority_remaining = [
            work for work in remaining_work
            if work["priority"] > 0.7
        ]
        if not high_priority_remaining:
            return WorkflowDecision.COMPLETE_WORKFLOW.value

        # 否则继续分析
        return WorkflowDecision.CONTINUE_ANALYSIS.value

    def _save_progress_report(self, report: WorkflowProgressReport) -> None:
        """保存进度报告"""
        try:
            report_file = self.reports_dir / f"progress_report_{report.session_id}_{report.check_timestamp.strftime('%Y%m%d_%H%M%S')}.json"

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"进度报告已保存: {report.report_id}")

        except Exception as e:
            self.logger.error(f"保存进度报告失败: {e}")

    def get_status_check_history(self, session_id: str) -> List[WorkflowProgressReport]:
        """
        获取状态检查历史

        Args:
            session_id: 会话ID

        Returns:
            List[WorkflowProgressReport]: 状态检查历史
        """
        try:
            reports = []

            # 扫描进度报告文件
            pattern = f"progress_report_{session_id}_*.json"
            for report_file in self.reports_dir.glob(pattern):
                with open(report_file, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                    report = self._reconstruct_progress_report(report_data)
                    if report:
                        reports.append(report)

            return sorted(reports, key=lambda r: r.check_timestamp, reverse=True)

        except Exception as e:
            self.logger.error(f"获取状态检查历史失败: {e}")
            return []

    def _reconstruct_progress_report(self, report_data: Dict[str, Any]) -> Optional[WorkflowProgressReport]:
        """从字典数据重构进度报告"""
        try:
            # 重构状态摘要
            summary_data = report_data["status_summary"]
            status_summary = ProblemStatusSummary(
                total_problems=summary_data["total_problems"],
                solved_problems=summary_data["solved_problems"],
                skipped_problems=summary_data["skipped_problems"],
                failed_problems=summary_data["failed_problems"],
                remaining_problems=summary_data["remaining_problems"],
                problems_requiring_intervention=summary_data["problems_requiring_intervention"]
            )

            return WorkflowProgressReport(
                report_id=report_data["report_id"],
                session_id=report_data["session_id"],
                check_timestamp=datetime.fromisoformat(report_data["check_timestamp"]),
                status_summary=status_summary,
                workflow_statistics=report_data["workflow_statistics"],
                remaining_work=report_data["remaining_work"],
                recommendations=report_data["recommendations"],
                next_action=report_data["next_action"]
            )
        except Exception as e:
            self.logger.error(f"重构进度报告失败: {e}")
            return None

    def generate_final_status_summary(self, session_id: str) -> Dict[str, Any]:
        """
        生成最终状态摘要

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 最终状态摘要
        """
        try:
            # 获取最新的进度报告
            reports = self.get_status_check_history(session_id)
            if not reports:
                return {"error": "无进度报告可分析"}

            latest_report = reports[0]
            session = self.state_manager.get_session(session_id)

            # 生成最终摘要
            final_summary = {
                "session_id": session_id,
                "completion_timestamp": datetime.now().isoformat(),
                "final_status": latest_report.status_summary.to_dict(),
                "workflow_performance": latest_report.workflow_statistics,
                "session_outcome": self._determine_session_outcome(latest_report),
                "key_achievements": self._identify_key_achievements(latest_report),
                "remaining_concerns": self._identify_remaining_concerns(latest_report),
                "recommendations_for_future": self._generate_future_recommendations(latest_report)
            }

            return final_summary

        except Exception as e:
            self.logger.error(f"生成最终状态摘要失败: {e}")
            return {"error": str(e)}

    def _determine_session_outcome(self, report: WorkflowProgressReport) -> str:
        """确定会话结果"""
        total = report.status_summary.total_problems
        solved = report.status_summary.solved_problems
        skipped = report.status_summary.skipped_problems

        if total == 0:
            return "no_issues_found"
        elif solved == total:
            return "all_issues_resolved"
        elif solved + skipped == total:
            return "all_issues_processed"
        elif solved > total / 2:
            return "majority_resolved"
        else:
            return "partial_progress"

    def _identify_key_achievements(self, report: WorkflowProgressReport) -> List[str]:
        """识别关键成就"""
        achievements = []

        if report.status_summary.solved_problems > 0:
            achievements.append(f"成功解决了 {report.status_summary.solved_problems} 个问题")

        success_rate = report.workflow_statistics.get("success_rate", 0)
        if success_rate > 0.8:
            achievements.append("修复成功率高，质量表现优秀")

        if report.status_summary.remaining_problems == 0:
            achievements.append("完成了所有问题的处理")

        return achievements if achievements else ["工作流程正常执行"]

    def _identify_remaining_concerns(self, report: WorkflowProgressReport) -> List[str]:
        """识别剩余关切点"""
        concerns = []

        if report.status_summary.remaining_problems > 0:
            concerns.append(f"仍有 {report.status_summary.remaining_problems} 个问题待处理")

        if report.status_summary.failed_problems > 0:
            concerns.append(f"有 {report.status_summary.failed_problems} 个问题处理失败")

        if report.status_summary.problems_requiring_intervention > 0:
            concerns.append("有问题需要人工干预")

        return concerns if concerns else ["无明显关切点"]

    def _generate_future_recommendations(self, report: WorkflowProgressReport) -> List[str]:
        """生成未来建议"""
        recommendations = []

        # 基于成功率建议
        success_rate = report.workflow_statistics.get("success_rate", 0)
        if success_rate < 0.5:
            recommendations.append("建议改进问题识别和修复策略")
        elif success_rate > 0.8:
            recommendations.append("建议保持当前高质量的处理策略")

        # 基于剩余工作建议
        if report.status_summary.remaining_problems > 0:
            recommendations.append("建议继续处理剩余问题或安排人工审查")

        # 基于性能建议
        avg_time = report.workflow_statistics.get("average_time_per_problem", 0)
        if avg_time > 300:  # 超过5分钟
            recommendations.append("建议优化处理流程，提高效率")

        return recommendations if recommendations else ["继续使用当前工作流程"]