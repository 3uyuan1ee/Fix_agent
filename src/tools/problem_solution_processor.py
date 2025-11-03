#!/usr/bin/env python3
"""
问题解决处理器 - T016.1
处理成功解决的问题，记录和标记已成功解决的问题
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
from .workflow_data_types import WorkflowSession, AIDetectedProblem, AIFixSuggestion
from .workflow_user_interaction_types import UserDecision
from .workflow_flow_state_manager import WorkflowNode, WorkflowFlowStateManager

logger = get_logger()


@dataclass
class ProblemSolution:
    """问题解决方案"""
    solution_id: str
    session_id: str
    issue_id: str
    file_path: str
    line_number: int
    problem_type: str
    severity: str
    suggestion_id: str
    fix_code: str
    fix_description: str
    solution_timestamp: datetime
    verification_status: str
    quality_score: float
    user_satisfaction: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "solution_id": self.solution_id,
            "session_id": self.session_id,
            "issue_id": self.issue_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "problem_type": self.problem_type,
            "severity": self.severity,
            "suggestion_id": self.suggestion_id,
            "fix_code": self.fix_code,
            "fix_description": self.fix_description,
            "solution_timestamp": self.solution_timestamp.isoformat(),
            "verification_status": self.verification_status,
            "quality_score": self.quality_score,
            "user_satisfaction": self.user_satisfaction
        }


@dataclass
class SolutionStatistics:
    """解决方案统计"""
    total_solved: int
    solved_by_type: Dict[str, int]
    solved_by_severity: Dict[str, int]
    average_quality_score: float
    solution_time_stats: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_solved": self.total_solved,
            "solved_by_type": self.solved_by_type,
            "solved_by_severity": self.solved_by_severity,
            "average_quality_score": self.average_quality_score,
            "solution_time_stats": self.solution_time_stats
        }


class ProblemSolutionProcessor:
    """问题解决处理器 - T016.1

    工作流位置: 节点J，处理成功解决的问题
    核心功能: 记录和标记已成功解决的问题
    用户协作: 为用户提供明确的问题解决确认
    """

    def __init__(self, config_manager=None):
        """初始化问题解决处理器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.state_manager = WorkflowFlowStateManager()

        # 获取配置
        self.config = self.config_manager.get_config("project_analysis", {})

        # 解决方案存储目录
        self.solutions_dir = Path(self.config.get("solutions_dir", ".fix_backups/solutions"))
        self.solutions_dir.mkdir(parents=True, exist_ok=True)

    def process_problem_solution(
        self,
        session_id: str,
        issue_id: str,
        suggestion_id: str,
        verification_report_id: Optional[str] = None,
        user_satisfaction: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理问题解决方案

        Args:
            session_id: 会话ID
            issue_id: 问题ID
            suggestion_id: 修复建议ID
            verification_report_id: 验证报告ID
            user_satisfaction: 用户满意度

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            self.logger.info(f"处理问题解决方案: 会话={session_id}, 问题={issue_id}")

            # 获取会话信息
            session = self.state_manager.get_session(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 获取问题信息
            problem = self._get_problem_by_id(session, issue_id)
            if not problem:
                raise ValueError(f"问题不存在: {issue_id}")

            # 获取修复建议信息
            fix_suggestion = self._get_fix_suggestion_by_id(session, suggestion_id)
            if not fix_suggestion:
                raise ValueError(f"修复建议不存在: {suggestion_id}")

            # 创建解决方案记录
            solution = self._create_solution_record(
                session=session,
                problem=problem,
                fix_suggestion=fix_suggestion,
                verification_report_id=verification_report_id,
                user_satisfaction=user_satisfaction
            )

            # 保存解决方案
            self._save_solution(solution)

            # 更新会话状态
            self._update_session_for_solution(session, solution)

            # 生成解决方案报告
            solution_report = self._generate_solution_report(solution)

            # 转换到节点L（检查剩余问题）
            self.state_manager.transition_to(
                session_id,
                WorkflowNode.CHECK_REMAINING,
                f"问题已解决: {issue_id}"
            )

            # 生成处理结果
            result = {
                "success": True,
                "solution_id": solution.solution_id,
                "issue_id": issue_id,
                "suggestion_id": suggestion_id,
                "next_node": "CHECK_REMAINING",
                "solution_report": solution_report,
                "message": f"问题 {issue_id} 已成功解决"
            }

            self.logger.info(f"问题解决处理完成: {result}")
            return result

        except Exception as e:
            self.logger.error(f"处理问题解决方案失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "处理问题解决方案失败"
            }

    def _get_problem_by_id(self, session: WorkflowSession, issue_id: str) -> Optional[AIDetectedProblem]:
        """根据ID获取问题信息"""
        for problem in session.detected_problems:
            if problem.issue_id == issue_id:
                return problem
        return None

    def _get_fix_suggestion_by_id(self, session: WorkflowSession, suggestion_id: str) -> Optional[AIFixSuggestion]:
        """根据ID获取修复建议信息"""
        for suggestion in session.fix_suggestions:
            if suggestion.suggestion_id == suggestion_id:
                return suggestion
        return None

    def _create_solution_record(
        self,
        session: WorkflowSession,
        problem: AIDetectedProblem,
        fix_suggestion: AIFixSuggestion,
        verification_report_id: Optional[str],
        user_satisfaction: Optional[str]
    ) -> ProblemSolution:
        """创建解决方案记录"""
        # 计算质量分数（可以从验证报告获取，这里使用默认值）
        quality_score = 0.8  # 默认质量分数

        return ProblemSolution(
            solution_id=str(uuid.uuid4()),
            session_id=session.session_id,
            issue_id=problem.issue_id,
            file_path=problem.file_path,
            line_number=problem.line,
            problem_type=problem.issue_type.value,
            severity=problem.severity.value,
            suggestion_id=fix_suggestion.suggestion_id,
            fix_code=fix_suggestion.suggested_code,
            fix_description=fix_suggestion.explanation,
            solution_timestamp=datetime.now(),
            verification_status="verified_success",
            quality_score=quality_score,
            user_satisfaction=user_satisfaction
        )

    def _save_solution(self, solution: ProblemSolution) -> None:
        """保存解决方案记录"""
        try:
            solution_file = self.solutions_dir / f"solution_{solution.session_id}_{solution.issue_id}.json"

            with open(solution_file, 'w', encoding='utf-8') as f:
                json.dump(solution.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"解决方案已保存: {solution.solution_id}")

        except Exception as e:
            self.logger.error(f"保存解决方案失败: {e}")
            raise

    def _update_session_for_solution(self, session: WorkflowSession, solution: ProblemSolution) -> None:
        """更新会话状态以反映问题解决"""
        # 从待处理问题列表中移除
        if solution.issue_id in session.pending_problems:
            session.pending_problems.remove(solution.issue_id)

        # 添加到已解决问题列表
        if not hasattr(session, 'solved_problems'):
            session.solved_problems = []
        session.solved_problems.append(solution.solution_id)

        # 更新问题处理状态
        session.problem_processing_status[solution.issue_id] = "solved"

        # 保存会话状态
        self.state_manager.save_session(session)

        self.logger.info(f"会话状态已更新: 问题 {solution.issue_id} 标记为已解决")

    def _generate_solution_report(self, solution: ProblemSolution) -> Dict[str, Any]:
        """生成解决方案报告"""
        return {
            "solution_id": solution.solution_id,
            "problem_summary": {
                "issue_id": solution.issue_id,
                "file_path": solution.file_path,
                "line_number": solution.line_number,
                "problem_type": solution.problem_type,
                "severity": solution.severity
            },
            "solution_details": {
                "suggestion_id": solution.suggestion_id,
                "fix_code": solution.fix_code,
                "fix_description": solution.fix_description,
                "quality_score": solution.quality_score
            },
            "solution_metadata": {
                "solution_timestamp": solution.solution_timestamp.isoformat(),
                "verification_status": solution.verification_status,
                "user_satisfaction": solution.user_satisfaction
            },
            "impact_assessment": {
                "problem_resolved": True,
                "code_improved": True,
                "risk_mitigated": solution.severity in ["error", "warning"]
            }
        }

    def batch_process_solutions(
        self,
        session_id: str,
        solution_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量处理解决方案

        Args:
            session_id: 会话ID
            solution_tasks: 解决方案任务列表

        Returns:
            Dict[str, Any]: 批量处理结果
        """
        try:
            self.logger.info(f"开始批量处理解决方案: 会话={session_id}, 任务数={len(solution_tasks)}")

            results = {
                "success_count": 0,
                "failed_count": 0,
                "results": [],
                "total_tasks": len(solution_tasks)
            }

            for task in solution_tasks:
                try:
                    result = self.process_problem_solution(session_id=session_id, **task)

                    results["results"].append({
                        "issue_id": task.get("issue_id"),
                        "success": result.get("success", False),
                        "message": result.get("message", "")
                    })

                    if result.get("success"):
                        results["success_count"] += 1
                    else:
                        results["failed_count"] += 1

                except Exception as e:
                    self.logger.error(f"批量处理单个解决方案失败: {e}")
                    results["results"].append({
                        "issue_id": task.get("issue_id"),
                        "success": False,
                        "message": str(e)
                    })
                    results["failed_count"] += 1

            self.logger.info(f"批量解决方案处理完成: 成功={results['success_count']}, 失败={results['failed_count']}")
            return results

        except Exception as e:
            self.logger.error(f"批量处理解决方案失败: {e}")
            return {
                "success_count": 0,
                "failed_count": len(solution_tasks),
                "results": [],
                "total_tasks": len(solution_tasks),
                "error": str(e)
            }

    def get_solution_statistics(self, session_id: str) -> SolutionStatistics:
        """
        获取会话的解决方案统计信息

        Args:
            session_id: 会话ID

        Returns:
            SolutionStatistics: 解决方案统计信息
        """
        try:
            session = self.state_manager.get_session(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 获取所有解决方案
            solutions = self._get_session_solutions(session_id)

            if not solutions:
                return SolutionStatistics(
                    total_solved=0,
                    solved_by_type={},
                    solved_by_severity={},
                    average_quality_score=0.0,
                    solution_time_stats={}
                )

            # 统计解决问题数量
            total_solved = len(solutions)

            # 按问题类型统计
            solved_by_type = {}
            for solution in solutions:
                problem_type = solution.problem_type
                solved_by_type[problem_type] = solved_by_type.get(problem_type, 0) + 1

            # 按严重程度统计
            solved_by_severity = {}
            for solution in solutions:
                severity = solution.severity
                solved_by_severity[severity] = solved_by_severity.get(severity, 0) + 1

            # 计算平均质量分数
            average_quality_score = sum(s.quality_score for s in solutions) / len(solutions)

            # 解决时间统计
            solution_times = [s.solution_timestamp for s in solutions]
            if solution_times:
                time_span = (max(solution_times) - min(solution_times)).total_seconds()
                solution_time_stats = {
                    "total_time_seconds": time_span,
                    "average_time_per_solution": time_span / len(solutions),
                    "solutions_per_hour": len(solutions) / (time_span / 3600) if time_span > 0 else 0
                }
            else:
                solution_time_stats = {}

            return SolutionStatistics(
                total_solved=total_solved,
                solved_by_type=solved_by_type,
                solved_by_severity=solved_by_severity,
                average_quality_score=average_quality_score,
                solution_time_stats=solution_time_stats
            )

        except Exception as e:
            self.logger.error(f"获取解决方案统计失败: {e}")
            return SolutionStatistics(
                total_solved=0,
                solved_by_type={},
                solved_by_severity={},
                average_quality_score=0.0,
                solution_time_stats={}
            )

    def _get_session_solutions(self, session_id: str) -> List[ProblemSolution]:
        """获取会话的所有解决方案"""
        try:
            solutions = []

            # 扫描解决方案文件
            pattern = f"solution_{session_id}_*.json"
            for solution_file in self.solutions_dir.glob(pattern):
                with open(solution_file, 'r', encoding='utf-8') as f:
                    solution_data = json.load(f)
                    solution = self._reconstruct_solution(solution_data)
                    if solution:
                        solutions.append(solution)

            return sorted(solutions, key=lambda s: s.solution_timestamp)

        except Exception as e:
            self.logger.error(f"获取会话解决方案失败: {e}")
            return []

    def _reconstruct_solution(self, solution_data: Dict[str, Any]) -> Optional[ProblemSolution]:
        """从字典数据重构解决方案"""
        try:
            return ProblemSolution(
                solution_id=solution_data["solution_id"],
                session_id=solution_data["session_id"],
                issue_id=solution_data["issue_id"],
                file_path=solution_data["file_path"],
                line_number=solution_data["line_number"],
                problem_type=solution_data["problem_type"],
                severity=solution_data["severity"],
                suggestion_id=solution_data["suggestion_id"],
                fix_code=solution_data["fix_code"],
                fix_description=solution_data["fix_description"],
                solution_timestamp=datetime.fromisoformat(solution_data["solution_timestamp"]),
                verification_status=solution_data["verification_status"],
                quality_score=solution_data["quality_score"],
                user_satisfaction=solution_data.get("user_satisfaction")
            )
        except Exception as e:
            self.logger.error(f"重构解决方案失败: {e}")
            return None

    def get_solution_details(self, session_id: str, issue_id: str) -> Optional[ProblemSolution]:
        """
        获取特定问题的解决方案详情

        Args:
            session_id: 会话ID
            issue_id: 问题ID

        Returns:
            Optional[ProblemSolution]: 解决方案详情
        """
        try:
            solution_file = self.solutions_dir / f"solution_{session_id}_{issue_id}.json"

            if not solution_file.exists():
                return None

            with open(solution_file, 'r', encoding='utf-8') as f:
                solution_data = json.load(f)

            return self._reconstruct_solution(solution_data)

        except Exception as e:
            self.logger.error(f"获取解决方案详情失败: {e}")
            return None

    def generate_solution_summary_report(self, session_id: str) -> Dict[str, Any]:
        """
        生成解决方案摘要报告

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 摘要报告
        """
        try:
            statistics = self.get_solution_statistics(session_id)
            solutions = self._get_session_solutions(session_id)

            # 生成摘要报告
            report = {
                "session_id": session_id,
                "report_timestamp": datetime.now().isoformat(),
                "executive_summary": {
                    "total_problems_solved": statistics.total_solved,
                    "success_rate": 1.0 if statistics.total_solved > 0 else 0.0,
                    "average_quality_score": statistics.average_quality_score
                },
                "problem_type_breakdown": statistics.solved_by_type,
                "severity_breakdown": statistics.solved_by_severity,
                "solution_efficiency": statistics.solution_time_stats,
                "recent_solutions": [
                    {
                        "solution_id": s.solution_id,
                        "issue_id": s.issue_id,
                        "file_path": s.file_path,
                        "problem_type": s.problem_type,
                        "solution_timestamp": s.solution_timestamp.isoformat()
                    }
                    for s in solutions[-5:]  # 最近5个解决方案
                ],
                "quality_distribution": self._analyze_quality_distribution(solutions),
                "recommendations": self._generate_solution_recommendations(statistics)
            }

            return report

        except Exception as e:
            self.logger.error(f"生成解决方案摘要报告失败: {e}")
            return {"error": str(e)}

    def _analyze_quality_distribution(self, solutions: List[ProblemSolution]) -> Dict[str, Any]:
        """分析质量分布"""
        if not solutions:
            return {}

        quality_scores = [s.quality_score for s in solutions]

        return {
            "min_score": min(quality_scores),
            "max_score": max(quality_scores),
            "average_score": sum(quality_scores) / len(quality_scores),
            "median_score": sorted(quality_scores)[len(quality_scores) // 2],
            "high_quality_count": len([s for s in solutions if s.quality_score >= 0.8]),
            "medium_quality_count": len([s for s in solutions if 0.6 <= s.quality_score < 0.8]),
            "low_quality_count": len([s for s in solutions if s.quality_score < 0.6])
        }

    def _generate_solution_recommendations(self, statistics: SolutionStatistics) -> List[str]:
        """生成解决方案建议"""
        recommendations = []

        if statistics.total_solved == 0:
            recommendations.append("尚未解决任何问题，建议分析问题识别和修复策略")
            return recommendations

        if statistics.average_quality_score < 0.7:
            recommendations.append("解决方案质量分数偏低，建议改进修复策略和验证流程")

        high_severity_count = statistics.solved_by_severity.get("error", 0)
        total_count = statistics.total_solved
        if high_severity_count / total_count > 0.5:
            recommendations.append("高严重程度问题占比较高，建议加强代码质量预防措施")

        solution_rate = statistics.solution_time_stats.get("solutions_per_hour", 0)
        if solution_rate < 1:
            recommendations.append("解决效率较低，建议优化工作流程和工具使用")

        if not recommendations:
            recommendations.append("解决方案质量良好，继续保持当前策略")

        return recommendations