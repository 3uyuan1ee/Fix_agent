#!/usr/bin/env python3
"""
问题跳过处理器 - 节点G
处理用户选择跳过的问题，记录跳过原因并继续处理后续问题
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
from .workflow_data_types import AIDetectedProblem
from .workflow_user_interaction_types import UserDecision, DecisionType
from .workflow_flow_state_manager import WorkflowNode, WorkflowFlowStateManager

logger = get_logger()


@dataclass
class SkipRecord:
    """问题跳过记录"""
    skip_id: str
    issue_id: str
    file_path: str
    line_number: int
    problem_type: str
    severity: str
    skip_reason: str
    user_comment: Optional[str]
    skip_timestamp: datetime
    session_id: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "skip_id": self.skip_id,
            "issue_id": self.issue_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "problem_type": self.problem_type,
            "severity": self.severity,
            "skip_reason": self.skip_reason,
            "user_comment": self.user_comment,
            "skip_timestamp": self.skip_timestamp.isoformat(),
            "session_id": self.session_id
        }


@dataclass
class SkipStatistics:
    """跳过统计信息"""
    total_skipped: int
    skip_by_reason: Dict[str, int]
    skip_by_type: Dict[str, int]
    skip_by_severity: Dict[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_skipped": self.total_skipped,
            "skip_by_reason": self.skip_by_reason,
            "skip_by_type": self.skip_by_type,
            "skip_by_severity": self.skip_by_severity
        }


class SkipReason(Enum):
    """跳过原因枚举"""
    FALSE_POSITIVE = "false_positive"          # 误报
    LOW_PRIORITY = "low_priority"             # 优先级低
    COMPLEX_TO_FIX = "complex_to_fix"         # 修复复杂
    REQUIRE_MORE_CONTEXT = "require_more_context"  # 需要更多上下文
    USER_PREFERENCE = "user_preference"       # 用户偏好
    OUT_OF_SCOPE = "out_of_scope"             # 超出范围
    TEMPORARY_SKIP = "temporary_skip"         # 临时跳过
    OTHER = "other"                           # 其他原因


class ProblemSkipProcessor:
    """问题跳过处理器 - 节点G

    工作流位置: 节点G，处理用户选择跳过的问题
    核心功能: 记录跳过的问题并继续处理后续问题
    用户协作: 尊重用户跳过问题的决策
    """

    def __init__(self, config_manager=None):
        """初始化问题跳过处理器"""
        self.config_manager = config_manager or get_config_manager()
        self.state_manager = WorkflowFlowStateManager()
        self.logger = get_logger()

        # 获取配置
        self.config = self.config_manager.get("project_analysis", {})
        self.skip_records_dir = Path(self.config.get("skip_records_dir", ".fix_backups/skip_records"))
        self.skip_records_dir.mkdir(parents=True, exist_ok=True)

    def process_skip_decision(
        self,
        session_id: str,
        issue_id: str,
        skip_reason: SkipReason,
        user_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理用户的跳过决策

        Args:
            session_id: 工作流会话ID
            issue_id: 问题ID
            skip_reason: 跳过原因
            user_comment: 用户评论

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            self.logger.info(f"处理问题跳过决策: 会话={session_id}, 问题={issue_id}, 原因={skip_reason.value}")

            # 获取会话信息
            session = self.state_manager.get_session(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 获取问题信息
            problem = self._get_problem_by_id(session, issue_id)
            if not problem:
                raise ValueError(f"问题不存在: {issue_id}")

            # 创建跳过记录
            skip_record = self._create_skip_record(
                session=session,
                problem=problem,
                skip_reason=skip_reason,
                user_comment=user_comment
            )

            # 保存跳过记录
            self._save_skip_record(skip_record)

            # 从待处理列表中移除问题
            self._remove_problem_from_pending(session, issue_id)

            # 更新会话状态
            session.problem_processing_status[issue_id] = "skipped"
            session.skip_history.append(skip_record.skip_id)

            # 保存会话状态
            self.state_manager.save_session(session)

            # 转换到节点L（检查剩余问题）
            self.state_manager.transition_to(
                session_id,
                WorkflowNode.CHECK_REMAINING,
                f"问题已跳过: {issue_id}"
            )

            # 生成处理结果
            result = {
                "success": True,
                "skip_id": skip_record.skip_id,
                "issue_id": issue_id,
                "skip_reason": skip_reason.value,
                "user_comment": user_comment,
                "next_node": "CHECK_REMAINING",
                "message": f"问题 {issue_id} 已跳过，将继续检查剩余问题"
            }

            self.logger.info(f"问题跳过处理完成: {result}")
            return result

        except Exception as e:
            self.logger.error(f"处理问题跳过失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "处理问题跳过失败"
            }

    def _get_problem_by_id(self, session: WorkflowSession, issue_id: str) -> Optional[AIDetectedProblem]:
        """根据ID获取问题信息"""
        # 先从detected_problems列表中查找
        for problem_dict in session.problems_detected:
            if problem_dict.get("problem_id") == issue_id:
                # 转换为AIDetectedProblem对象
                from .workflow_data_types import AIDetectedProblem
                try:
                    return AIDetectedProblem.from_dict(problem_dict)
                except:
                    # 如果转换失败，创建一个基本的对象
                    return AIDetectedProblem(
                        problem_id=problem_dict.get("problem_id", issue_id),
                        file_path=problem_dict.get("file_path", ""),
                        line_number=problem_dict.get("line_number", 0),
                        problem_type=problem_dict.get("problem_type", "SECURITY"),
                        severity=problem_dict.get("severity", "HIGH"),
                        description=problem_dict.get("description", ""),
                        code_snippet=problem_dict.get("code_snippet", ""),
                        confidence=problem_dict.get("confidence", 0.5),
                        reasoning=problem_dict.get("reasoning", "")
                    )

        # 如果没找到，再从detected_problems列表中查找
        for problem in session.detected_problems:
            if problem.problem_id == issue_id:
                return problem
        return None

    def _create_skip_record(
        self,
        session: WorkflowSession,
        problem: AIDetectedProblem,
        skip_reason: SkipReason,
        user_comment: Optional[str]
    ) -> SkipRecord:
        """创建跳过记录"""
        return SkipRecord(
            skip_id=str(uuid.uuid4()),
            issue_id=problem.problem_id,
            file_path=problem.file_path,
            line_number=problem.line_number,
            problem_type=problem.problem_type.value,
            severity=problem.severity.value,
            skip_reason=skip_reason.value,
            user_comment=user_comment,
            skip_timestamp=datetime.now(),
            session_id=session.session_id
        )

    def _save_skip_record(self, skip_record: SkipRecord) -> None:
        """保存跳过记录到文件"""
        try:
            skip_file = self.skip_records_dir / f"skip_{skip_record.session_id}.json"

            # 读取现有记录
            existing_records = []
            if skip_file.exists():
                with open(skip_file, 'r', encoding='utf-8') as f:
                    existing_records = json.load(f)

            # 添加新记录
            existing_records.append(skip_record.to_dict())

            # 保存记录
            with open(skip_file, 'w', encoding='utf-8') as f:
                json.dump(existing_records, f, indent=2, ensure_ascii=False)

            self.logger.info(f"跳过记录已保存: {skip_record.skip_id}")

        except Exception as e:
            self.logger.error(f"保存跳过记录失败: {e}")
            raise

    def _remove_problem_from_pending(self, session: WorkflowSession, issue_id: str) -> None:
        """从待处理问题列表中移除问题"""
        # 从检测到的问题列表中移除
        session.detected_problems = [
            problem for problem in session.detected_problems
            if problem.problem_id != issue_id
        ]

        # 从待处理问题列表中移除
        if issue_id in session.pending_problems:
            session.pending_problems.remove(issue_id)

        self.logger.info(f"问题已从待处理列表移除: {issue_id}")

    def get_skip_statistics(self, session_id: str) -> SkipStatistics:
        """
        获取会话的跳过统计信息

        Args:
            session_id: 会话ID

        Returns:
            SkipStatistics: 跳过统计信息
        """
        try:
            session = self.state_manager.get_session(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 读取跳过记录
            skip_file = self.skip_records_dir / f"skip_{session_id}.json"
            skip_records = []

            if skip_file.exists():
                with open(skip_file, 'r', encoding='utf-8') as f:
                    skip_records = json.load(f)

            # 统计跳过原因
            skip_by_reason = {}
            skip_by_type = {}
            skip_by_severity = {}

            for record in skip_records:
                # 按原因统计
                reason = record.get("skip_reason", "unknown")
                skip_by_reason[reason] = skip_by_reason.get(reason, 0) + 1

                # 按问题类型统计
                problem_type = record.get("problem_type", "unknown")
                skip_by_type[problem_type] = skip_by_type.get(problem_type, 0) + 1

                # 按严重程度统计
                severity = record.get("severity", "unknown")
                skip_by_severity[severity] = skip_by_severity.get(severity, 0) + 1

            return SkipStatistics(
                total_skipped=len(skip_records),
                skip_by_reason=skip_by_reason,
                skip_by_type=skip_by_type,
                skip_by_severity=skip_by_severity
            )

        except Exception as e:
            self.logger.error(f"获取跳过统计失败: {e}")
            return SkipStatistics(
                total_skipped=0,
                skip_by_reason={},
                skip_by_type={},
                skip_by_severity={}
            )

    def get_skip_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取会话的跳过历史记录

        Args:
            session_id: 会话ID

        Returns:
            List[Dict[str, Any]]: 跳过历史记录
        """
        try:
            skip_file = self.skip_records_dir / f"skip_{session_id}.json"

            if not skip_file.exists():
                return []

            with open(skip_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        except Exception as e:
            self.logger.error(f"获取跳过历史失败: {e}")
            return []

    def get_available_skip_reasons(self) -> List[Dict[str, str]]:
        """
        获取可用的跳过原因列表

        Returns:
            List[Dict[str, str]]: 跳过原因列表
        """
        return [
            {"value": reason.value, "label": self._get_skip_reason_label(reason)}
            for reason in SkipReason
        ]

    def _get_skip_reason_label(self, reason: SkipReason) -> str:
        """获取跳过原因的显示标签"""
        labels = {
            SkipReason.FALSE_POSITIVE: "误报问题",
            SkipReason.LOW_PRIORITY: "优先级较低",
            SkipReason.COMPLEX_TO_FIX: "修复过于复杂",
            SkipReason.REQUIRE_MORE_CONTEXT: "需要更多上下文",
            SkipReason.USER_PREFERENCE: "用户偏好",
            SkipReason.OUT_OF_SCOPE: "超出分析范围",
            SkipReason.TEMPORARY_SKIP: "临时跳过",
            SkipReason.OTHER: "其他原因"
        }
        return labels.get(reason, reason.value)

    def batch_skip_problems(
        self,
        session_id: str,
        issue_ids: List[str],
        skip_reason: SkipReason,
        user_comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量跳过问题

        Args:
            session_id: 会话ID
            issue_ids: 问题ID列表
            skip_reason: 跳过原因
            user_comment: 用户评论

        Returns:
            Dict[str, Any]: 批量处理结果
        """
        try:
            self.logger.info(f"开始批量跳过问题: 会话={session_id}, 数量={len(issue_ids)}")

            results = {
                "success_count": 0,
                "failed_count": 0,
                "results": [],
                "total_issues": len(issue_ids)
            }

            for issue_id in issue_ids:
                try:
                    result = self.process_skip_decision(
                        session_id=session_id,
                        issue_id=issue_id,
                        skip_reason=skip_reason,
                        user_comment=user_comment
                    )

                    results["results"].append({
                        "issue_id": issue_id,
                        "success": result.get("success", False),
                        "message": result.get("message", "")
                    })

                    if result.get("success"):
                        results["success_count"] += 1
                    else:
                        results["failed_count"] += 1

                except Exception as e:
                    self.logger.error(f"批量跳过单个问题失败 {issue_id}: {e}")
                    results["results"].append({
                        "issue_id": issue_id,
                        "success": False,
                        "message": str(e)
                    })
                    results["failed_count"] += 1

            self.logger.info(f"批量跳过完成: 成功={results['success_count']}, 失败={results['failed_count']}")
            return results

        except Exception as e:
            self.logger.error(f"批量跳过问题失败: {e}")
            return {
                "success_count": 0,
                "failed_count": len(issue_ids),
                "results": [],
                "total_issues": len(issue_ids),
                "error": str(e)
            }