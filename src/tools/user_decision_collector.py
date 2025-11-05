"""
用户决策收集器 - T006.2
收集用户对AI建议的确认、修改或补充
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from ..utils.logger import get_logger

try:
    from ..tools.ai_file_selector import AIFileSelectionResult, FileSelectionResult
    from ..tools.ai_recommendation_displayer import AIRecommendationDisplay, DisplayFile
except ImportError:
    # 如果相关模块不可用，定义基本类型
    @dataclass
    class FileSelectionResult:
        file_path: str
        priority: str
        reason: str
        confidence: float
        key_issues: List[str] = field(default_factory=list)
        selection_score: float = 0.0

    @dataclass
    class DisplayFile:
        file_path: str
        display_name: str
        relative_path: str
        priority: str = "medium"
        confidence: float = 0.0
        selection_score: float = 0.0
        reason: str = ""
        key_issues: List[str] = field(default_factory=list)


class DecisionAction(Enum):
    """用户决策动作"""

    CONFIRM = "confirm"  # 确认AI建议
    REJECT = "reject"  # 拒绝AI建议
    MODIFY = "modify"  # 修改建议
    ADD_FILE = "add_file"  # 添加文件
    REMOVE_FILE = "remove_file"  # 移除文件
    CHANGE_PRIORITY = "change_priority"  # 修改优先级
    BATCH_OPERATION = "batch_operation"  # 批量操作


@dataclass
class UserDecision:
    """用户决策"""

    action: DecisionAction
    file_path: Optional[str] = None
    original_data: Optional[Dict[str, Any]] = None
    modified_data: Optional[Dict[str, Any]] = None
    reason: str = ""
    timestamp: str = ""
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "action": self.action.value,
            "file_path": self.file_path,
            "original_data": self.original_data,
            "modified_data": self.modified_data,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
        }


@dataclass
class BatchOperation:
    """批量操作"""

    operation_type: str  # "select_all", "deselect_all", "invert", "filter"
    criteria: Optional[Dict[str, Any]] = None
    affected_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "operation_type": self.operation_type,
            "criteria": self.criteria,
            "affected_files": self.affected_files,
        }


@dataclass
class UserDecisionSession:
    """用户决策会话"""

    session_id: str
    ai_recommendations: AIRecommendationDisplay
    initial_files: List[str] = field(default_factory=list)
    user_decisions: List[UserDecision] = field(default_factory=list)
    batch_operations: List[BatchOperation] = field(default_factory=list)
    current_selection: List[str] = field(default_factory=list)
    session_start_time: str = ""
    session_end_time: str = ""
    is_completed: bool = False
    completion_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "initial_files": self.initial_files,
            "user_decisions": [decision.to_dict() for decision in self.user_decisions],
            "batch_operations": [op.to_dict() for op in self.batch_operations],
            "current_selection": self.current_selection,
            "session_start_time": self.session_start_time,
            "session_end_time": self.session_end_time,
            "is_completed": self.is_completed,
            "completion_summary": self.completion_summary,
            "session_duration": self._calculate_duration(),
        }

    def _calculate_duration(self) -> float:
        """计算会话持续时间"""
        if not self.session_start_time or not self.session_end_time:
            return 0.0

        try:
            from datetime import datetime

            start = datetime.fromisoformat(self.session_start_time)
            end = datetime.fromisoformat(self.session_end_time)
            return (end - start).total_seconds()
        except Exception:
            return 0.0


@dataclass
class UserDecisionResult:
    """用户决策结果"""

    session_id: str
    final_selected_files: List[Dict[str, Any]] = field(default_factory=list)
    rejected_files: List[str] = field(default_factory=list)
    added_files: List[str] = field(default_factory=list)
    decision_summary: Dict[str, Any] = field(default_factory=dict)
    user_feedback: Dict[str, Any] = field(default_factory=dict)
    execution_success: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "final_selected_files": self.final_selected_files,
            "rejected_files": self.rejected_files,
            "added_files": self.added_files,
            "decision_summary": self.decision_summary,
            "user_feedback": self.user_feedback,
            "execution_success": self.execution_success,
            "error_message": self.error_message,
        }


class UserDecisionCollector:
    """用户决策收集器"""

    def __init__(self, session_timeout: int = 3600):
        self.session_timeout = session_timeout  # 会话超时时间（秒）
        self.active_sessions: Dict[str, UserDecisionSession] = {}
        self.logger = get_logger()

    def create_session(
        self,
        ai_recommendations: AIRecommendationDisplay,
        session_id: Optional[str] = None,
    ) -> UserDecisionSession:
        """
        创建用户决策会话

        Args:
            ai_recommendations: AI建议展示
            session_id: 会话ID，如果不提供则自动生成

        Returns:
            UserDecisionSession: 创建的会话
        """
        if session_id is None:
            session_id = self._generate_session_id()

        self.logger.info(f"创建用户决策会话: {session_id}")

        # 提取初始文件列表
        initial_files = [
            display_file.file_path for display_file in ai_recommendations.display_files
        ]

        session = UserDecisionSession(
            session_id=session_id,
            ai_recommendations=ai_recommendations,
            initial_files=initial_files.copy(),
            current_selection=initial_files.copy(),
            session_start_time=datetime.now().isoformat(),
        )

        self.active_sessions[session_id] = session

        self.logger.info(f"会话创建成功，初始选择 {len(initial_files)} 个文件")

        return session

    def add_decision(
        self,
        session_id: str,
        action: DecisionAction,
        file_path: Optional[str] = None,
        original_data: Optional[Dict[str, Any]] = None,
        modified_data: Optional[Dict[str, Any]] = None,
        reason: str = "",
        confidence: float = 1.0,
    ) -> bool:
        """
        添加用户决策

        Args:
            session_id: 会话ID
            action: 决策动作
            file_path: 相关文件路径
            original_data: 原始数据
            modified_data: 修改后的数据
            reason: 决策理由
            confidence: 决策置信度

        Returns:
            bool: 是否成功添加
        """
        session = self.active_sessions.get(session_id)
        if not session:
            self.logger.error(f"会话不存在: {session_id}")
            return False

        decision = UserDecision(
            action=action,
            file_path=file_path,
            original_data=original_data,
            modified_data=modified_data,
            reason=reason,
            timestamp=datetime.now().isoformat(),
            confidence=confidence,
        )

        # 处理决策
        success = self._process_decision(session, decision)

        if success:
            session.user_decisions.append(decision)
            self.logger.info(
                f"用户决策已添加: {action.value} - {file_path or '批量操作'}"
            )

        return success

    def _process_decision(
        self, session: UserDecisionSession, decision: UserDecision
    ) -> bool:
        """处理用户决策"""
        try:
            if decision.action == DecisionAction.CONFIRM:
                # 确认文件选择（无需操作，默认已选择）
                return True

            elif decision.action == DecisionAction.REJECT:
                # 拒绝文件选择
                if (
                    decision.file_path
                    and decision.file_path in session.current_selection
                ):
                    session.current_selection.remove(decision.file_path)
                return True

            elif decision.action == DecisionAction.ADD_FILE:
                # 添加新文件
                if (
                    decision.file_path
                    and decision.file_path not in session.current_selection
                ):
                    session.current_selection.append(decision.file_path)
                    if decision.file_path not in session.initial_files:
                        session.initial_files.append(decision.file_path)
                return True

            elif decision.action == DecisionAction.REMOVE_FILE:
                # 移除文件
                if (
                    decision.file_path
                    and decision.file_path in session.current_selection
                ):
                    session.current_selection.remove(decision.file_path)
                return True

            elif decision.action == DecisionAction.MODIFY:
                # 修改文件属性
                if decision.modified_data and decision.file_path:
                    return self._modify_file_in_session(
                        session, decision.file_path, decision.modified_data
                    )

            elif decision.action == DecisionAction.CHANGE_PRIORITY:
                # 修改优先级
                if decision.modified_data and decision.file_path:
                    return self._change_file_priority(
                        session, decision.file_path, decision.modified_data
                    )

            elif decision.action == DecisionAction.BATCH_OPERATION:
                # 批量操作
                if decision.modified_data:
                    return self._execute_batch_operation(
                        session, decision.modified_data
                    )

        except Exception as e:
            self.logger.error(f"处理用户决策失败: {e}")
            return False

        return True

    def _modify_file_in_session(
        self,
        session: UserDecisionSession,
        file_path: str,
        modified_data: Dict[str, Any],
    ) -> bool:
        """修改会话中的文件属性"""
        try:
            # 查找对应的显示文件
            for display_file in session.ai_recommendations.display_files:
                if display_file.file_path == file_path:
                    # 更新文件属性
                    if "priority" in modified_data:
                        display_file.priority = modified_data["priority"]
                    if "reason" in modified_data:
                        display_file.reason = modified_data["reason"]
                    if "confidence" in modified_data:
                        display_file.confidence = modified_data["confidence"]
                    return True

            # 如果没找到现有文件，可能需要添加新文件
            if file_path not in [
                f.file_path for f in session.ai_recommendations.display_files
            ]:
                # 这里可以创建新的DisplayFile并添加到列表中
                # 为了简化，暂时只更新选择列表
                return True

        except Exception as e:
            self.logger.error(f"修改文件属性失败 {file_path}: {e}")

        return False

    def _change_file_priority(
        self,
        session: UserDecisionSession,
        file_path: str,
        modified_data: Dict[str, Any],
    ) -> bool:
        """修改文件优先级"""
        new_priority = modified_data.get("priority")
        if new_priority not in ["high", "medium", "low"]:
            return False

        return self._modify_file_in_session(
            session, file_path, {"priority": new_priority}
        )

    def _execute_batch_operation(
        self, session: UserDecisionSession, operation_data: Dict[str, Any]
    ) -> bool:
        """执行批量操作"""
        operation_type = operation_data.get("operation_type")
        criteria = operation_data.get("criteria", {})

        batch_op = BatchOperation(operation_type=operation_type, criteria=criteria)

        if operation_type == "select_all":
            # 选择所有文件
            all_files = [f.file_path for f in session.ai_recommendations.display_files]
            session.current_selection = list(set(session.current_selection + all_files))
            batch_op.affected_files = all_files

        elif operation_type == "deselect_all":
            # 取消选择所有文件
            batch_op.affected_files = session.current_selection.copy()
            session.current_selection = []

        elif operation_type == "invert":
            # 反转选择
            all_files = [f.file_path for f in session.ai_recommendations.display_files]
            current_set = set(session.current_selection)
            inverted = [f for f in all_files if f not in current_set]
            session.current_selection = inverted
            batch_op.affected_files = all_files

        elif operation_type == "filter":
            # 根据条件过滤选择
            filtered_files = self._filter_files(
                session.ai_recommendations.display_files, criteria
            )
            session.current_selection = [f.file_path for f in filtered_files]
            batch_op.affected_files = [f.file_path for f in filtered_files]

        else:
            return False

        session.batch_operations.append(batch_op)
        return True

    def _filter_files(
        self, display_files: List[DisplayFile], criteria: Dict[str, Any]
    ) -> List[DisplayFile]:
        """根据条件过滤文件"""
        filtered = display_files

        # 按优先级过滤
        min_priority = criteria.get("min_priority")
        if min_priority:
            priority_order = {"high": 3, "medium": 2, "low": 1}
            min_level = priority_order.get(min_priority, 0)
            filtered = [
                f for f in filtered if priority_order.get(f.priority, 0) >= min_level
            ]

        # 按置信度过滤
        min_confidence = criteria.get("min_confidence")
        if min_confidence is not None:
            filtered = [f for f in filtered if f.confidence >= min_confidence]

        # 按语言过滤
        languages = criteria.get("languages")
        if languages:
            filtered = [f for f in filtered if f.language in languages]

        # 按关键词过滤
        keywords = criteria.get("keywords")
        if keywords:
            filtered = [
                f
                for f in filtered
                if any(
                    keyword.lower() in f.reason.lower()
                    or any(keyword.lower() in issue.lower() for issue in f.key_issues)
                    for keyword in keywords
                )
            ]

        return filtered

    def complete_session(
        self, session_id: str, user_feedback: Optional[Dict[str, Any]] = None
    ) -> UserDecisionResult:
        """
        完成用户决策会话

        Args:
            session_id: 会话ID
            user_feedback: 用户反馈

        Returns:
            UserDecisionResult: 最终决策结果
        """
        session = self.active_sessions.get(session_id)
        if not session:
            error_msg = f"会话不存在: {session_id}"
            self.logger.error(error_msg)
            return UserDecisionResult(
                session_id=session_id, execution_success=False, error_message=error_msg
            )

        self.logger.info(f"完成用户决策会话: {session_id}")

        session.session_end_time = datetime.now().isoformat()
        session.is_completed = True

        # 生成最终结果
        result = self._generate_final_result(session, user_feedback or {})

        # 更新会话完成摘要
        session.completion_summary = {
            "final_selection_count": len(result.final_selected_files),
            "total_decisions": len(session.user_decisions),
            "batch_operations": len(session.batch_operations),
            "session_duration": session._calculate_duration(),
        }

        # 从活跃会话中移除
        self.active_sessions.pop(session_id, None)

        return result

    def _generate_final_result(
        self, session: UserDecisionSession, user_feedback: Dict[str, Any]
    ) -> UserDecisionResult:
        """生成最终决策结果"""
        # 获取最终选择的文件
        final_selected_files = []
        selected_paths = set(session.current_selection)

        for display_file in session.ai_recommendations.display_files:
            if display_file.file_path in selected_paths:
                final_selected_files.append(
                    {
                        "file_path": display_file.file_path,
                        "display_name": display_file.display_name,
                        "relative_path": display_file.relative_path,
                        "priority": display_file.priority,
                        "confidence": display_file.confidence,
                        "selection_score": display_file.selection_score,
                        "reason": display_file.reason,
                        "key_issues": display_file.key_issues,
                        "language": display_file.language,
                    }
                )

        # 计算被拒绝的文件
        rejected_files = list(set(session.initial_files) - selected_paths)

        # 计算新增的文件
        added_files = list(selected_paths - set(session.initial_files))

        # 生成决策摘要
        decision_summary = self._generate_decision_summary(session)

        result = UserDecisionResult(
            session_id=session.session_id,
            final_selected_files=final_selected_files,
            rejected_files=rejected_files,
            added_files=added_files,
            decision_summary=decision_summary,
            user_feedback=user_feedback,
        )

        return result

    def _generate_decision_summary(
        self, session: UserDecisionSession
    ) -> Dict[str, Any]:
        """生成决策摘要"""
        summary = {
            "initial_count": len(session.initial_files),
            "final_count": len(session.current_selection),
            "decision_count": len(session.user_decisions),
            "batch_operation_count": len(session.batch_operations),
            "action_distribution": {},
            "priority_changes": {},
            "session_duration": session._calculate_duration(),
        }

        # 统计决策动作分布
        action_counts = {}
        for decision in session.user_decisions:
            action = decision.action.value
            action_counts[action] = action_counts.get(action, 0) + 1
        summary["action_distribution"] = action_counts

        # 统计优先级变化
        priority_changes = {}
        for decision in session.user_decisions:
            if (
                decision.action == DecisionAction.CHANGE_PRIORITY
                and decision.modified_data
            ):
                old_priority = (
                    decision.original_data.get("priority", "unknown")
                    if decision.original_data
                    else "unknown"
                )
                new_priority = decision.modified_data.get("priority", "unknown")
                change_key = f"{old_priority} -> {new_priority}"
                priority_changes[change_key] = priority_changes.get(change_key, 0) + 1
        summary["priority_changes"] = priority_changes

        return summary

    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "is_active": True,
            "is_completed": session.is_completed,
            "current_selection_count": len(session.current_selection),
            "decision_count": len(session.user_decisions),
            "session_duration": session._calculate_duration(),
            "initial_files_count": len(session.initial_files),
        }

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        current_time = datetime.now()
        expired_count = 0

        expired_sessions = []
        for session_id, session in self.active_sessions.items():
            try:
                start_time = datetime.fromisoformat(session.session_start_time)
                if (current_time - start_time).total_seconds() > self.session_timeout:
                    expired_sessions.append(session_id)
            except Exception:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            self.active_sessions.pop(session_id, None)
            expired_count += 1
            self.logger.info(f"清理过期会话: {session_id}")

        return expired_count

    def _generate_session_id(self) -> str:
        """生成会话ID"""
        import uuid

        return f"decision_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"


# 便捷函数
def collect_user_decisions(
    ai_recommendations: AIRecommendationDisplay,
    decisions: List[Dict[str, Any]],
    user_feedback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    便捷的用户决策收集函数

    Args:
        ai_recommendations: AI建议展示
        decisions: 用户决策列表
        user_feedback: 用户反馈

    Returns:
        Dict[str, Any]: 最终决策结果
    """
    collector = UserDecisionCollector()
    session = collector.create_session(ai_recommendations)

    # 添加所有决策
    for decision_data in decisions:
        action = DecisionAction(decision_data.get("action", "confirm"))
        collector.add_decision(
            session_id=session.session_id,
            action=action,
            file_path=decision_data.get("file_path"),
            original_data=decision_data.get("original_data"),
            modified_data=decision_data.get("modified_data"),
            reason=decision_data.get("reason", ""),
            confidence=decision_data.get("confidence", 1.0),
        )

    # 完成会话
    result = collector.complete_session(session.session_id, user_feedback)

    return result.to_dict()
