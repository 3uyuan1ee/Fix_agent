"""
工作流状态管理器
严格按照工作流图实现状态转换管理: B→C→D→E→F/G→H→I→J/K→L→B/M
"""

import uuid
import time
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.config import get_config_manager


class WorkflowNode(Enum):
    """工作流节点枚举 - 严格按照工作流图"""
    PHASE_A_COMPLETE = "phase_a_complete"  # Phase 1-4完成
    PROBLEM_DETECTION = "problem_detection"  # 节点B: AI问题检测
    FIX_SUGGESTION = "fix_suggestion"  # 节点C: AI修复建议生成
    USER_REVIEW = "user_review"  # 节点D: 用户审查
    USER_DECISION = "user_decision"  # 节点E: 用户决策
    AUTO_FIX = "auto_fix"  # 节点F: 执行自动修复
    SKIP_PROBLEM = "skip_problem"  # 节点G: 跳过此问题
    FIX_VERIFICATION = "fix_verification"  # 节点H: 修复验证
    VERIFICATION_DECISION = "verification_decision"  # 节点I: 用户验证决策
    PROBLEM_SOLVED = "problem_solved"  # 节点J: 问题解决
    REANALYSIS = "reanalysis"  # 节点K: 重新分析
    CHECK_REMAINING = "check_remaining"  # 节点L: 检查剩余问题
    WORKFLOW_COMPLETE = "workflow_complete"  # 节点M: 工作流完成


class WorkflowTransitionError(Exception):
    """工作流转换异常"""
    pass


@dataclass
class WorkflowStateTransition:
    """工作流状态转换记录"""
    transition_id: str
    from_node: WorkflowNode
    to_node: WorkflowNode
    timestamp: datetime
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "transition_id": self.transition_id,
            "from_node": self.from_node.value,
            "to_node": self.to_node.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "metadata": self.metadata
        }


@dataclass
class WorkflowSession:
    """工作流会话数据"""
    session_id: str
    project_path: str
    selected_files: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 工作流状态
    current_node: WorkflowNode = WorkflowNode.PHASE_A_COMPLETE
    workflow_history: List[WorkflowStateTransition] = field(default_factory=list)

    # 会话数据
    problems_detected: List[Dict[str, Any]] = field(default_factory=list)
    current_problem_index: int = 0
    fix_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    applied_fixes: List[Dict[str, Any]] = field(default_factory=list)
    skipped_problems: List[str] = field(default_factory=list)
    solved_problems: List[str] = field(default_factory=list)

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now()

    def add_transition(self, from_node: WorkflowNode, to_node: WorkflowNode,
                      reason: str = "", metadata: Dict[str, Any] = None) -> WorkflowStateTransition:
        """添加状态转换记录"""
        transition = WorkflowStateTransition(
            transition_id=f"trans_{uuid.uuid4().hex[:8]}",
            from_node=from_node,
            to_node=to_node,
            timestamp=datetime.now(),
            reason=reason,
            metadata=metadata or {}
        )
        self.workflow_history.append(transition)
        self.current_node = to_node
        self.update_timestamp()
        return transition

    def get_next_problem(self) -> Optional[Dict[str, Any]]:
        """获取下一个待处理问题"""
        if self.current_problem_index < len(self.problems_detected):
            problem = self.problems_detected[self.current_problem_index]
            if problem.get("problem_id") not in self.skipped_problems + self.solved_problems:
                return problem
        return None

    def advance_to_next_problem(self) -> bool:
        """移动到下一个问题"""
        self.current_problem_index += 1
        return self.current_problem_index < len(self.problems_detected)

    def has_remaining_problems(self) -> bool:
        """检查是否还有待处理问题"""
        for problem in self.problems_detected[self.current_problem_index:]:
            if problem.get("problem_id") not in self.skipped_problems + self.solved_problems:
                return True
        return False


class WorkflowFlowStateManager:
    """严格遵循工作流图的状态管理器"""

    def __init__(self, storage_path: str = ".workflow_sessions"):
        """
        初始化工作流状态管理器

        Args:
            storage_path: 会话数据存储路径
        """
        self.logger = get_logger()
        self.config_manager = get_config_manager()
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)

        # 活跃会话
        self.active_sessions: Dict[str, WorkflowSession] = {}

        # 工作流转换规则 - 严格按照工作流图定义
        self.transition_rules = {
            WorkflowNode.PHASE_A_COMPLETE: [WorkflowNode.PROBLEM_DETECTION],
            WorkflowNode.PROBLEM_DETECTION: [WorkflowNode.FIX_SUGGESTION],
            WorkflowNode.FIX_SUGGESTION: [WorkflowNode.USER_REVIEW],
            WorkflowNode.USER_REVIEW: [WorkflowNode.USER_DECISION],
            WorkflowNode.USER_DECISION: [
                WorkflowNode.AUTO_FIX,      # 批准修复
                WorkflowNode.FIX_SUGGESTION, # 修改建议
                WorkflowNode.SKIP_PROBLEM   # 拒绝建议
            ],
            WorkflowNode.AUTO_FIX: [WorkflowNode.FIX_VERIFICATION],
            WorkflowNode.SKIP_PROBLEM: [WorkflowNode.CHECK_REMAINING],
            WorkflowNode.FIX_VERIFICATION: [WorkflowNode.VERIFICATION_DECISION],
            WorkflowNode.VERIFICATION_DECISION: [
                WorkflowNode.PROBLEM_SOLVED,  # 验证成功
                WorkflowNode.REANALYSIS       # 验证失败
            ],
            WorkflowNode.PROBLEM_SOLVED: [WorkflowNode.CHECK_REMAINING],
            WorkflowNode.REANALYSIS: [WorkflowNode.PROBLEM_DETECTION],
            WorkflowNode.CHECK_REMAINING: [
                WorkflowNode.PROBLEM_DETECTION,  # 还有问题
                WorkflowNode.WORKFLOW_COMPLETE   # 没有问题
            ],
            WorkflowNode.WORKFLOW_COMPLETE: []  # 终点状态
        }

    def create_session(self, project_path: str, selected_files: List[str]) -> WorkflowSession:
        """
        创建新的工作流会话

        Args:
            project_path: 项目路径
            selected_files: 选择的文件列表

        Returns:
            WorkflowSession: 新创建的会话
        """
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        session = WorkflowSession(
            session_id=session_id,
            project_path=str(project_path),
            selected_files=selected_files
        )

        self.active_sessions[session_id] = session
        self.logger.info(f"创建工作流会话: {session_id}, 项目: {project_path}")

        return session

    def transition_to(self, session_id: str, target_node: WorkflowNode,
                     reason: str = "", metadata: Dict[str, Any] = None) -> bool:
        """
        状态转换 - 严格按照工作流图逻辑

        Args:
            session_id: 会话ID
            target_node: 目标节点
            reason: 转换原因
            metadata: 转换元数据

        Returns:
            bool: 转换是否成功

        Raises:
            WorkflowTransitionError: 转换失败时抛出
        """
        if session_id not in self.active_sessions:
            raise WorkflowTransitionError(f"会话不存在: {session_id}")

        session = self.active_sessions[session_id]
        current_node = session.current_node

        # 检查转换是否合法
        if target_node not in self.transition_rules.get(current_node, []):
            raise WorkflowTransitionError(
                f"非法的状态转换: {current_node.value} → {target_node.value}. "
                f"允许的转换: {[n.value for n in self.transition_rules.get(current_node, [])]}"
            )

        # 特殊逻辑处理
        if not self._handle_special_transitions(session, current_node, target_node, metadata):
            return False

        # 执行转换
        transition = session.add_transition(current_node, target_node, reason, metadata)
        self.logger.info(f"状态转换: {current_node.value} → {target_node.value}, 会话: {session_id}")

        # 保存会话状态
        self._save_session(session)

        return True

    def _handle_special_transitions(self, session: WorkflowSession,
                                  from_node: WorkflowNode, to_node: WorkflowNode,
                                  metadata: Dict[str, Any] = None) -> bool:
        """
        处理特殊转换逻辑

        Args:
            session: 工作流会话
            from_node: 源节点
            to_node: 目标节点
            metadata: 元数据

        Returns:
            bool: 处理是否成功
        """
        if from_node == WorkflowNode.CHECK_REMAINING and to_node == WorkflowNode.PROBLEM_DETECTION:
            # 检查是否还有问题，如果没有则转换到WORKFLOW_COMPLETE
            if not session.has_remaining_problems():
                session.add_transition(WorkflowNode.CHECK_REMAINING,
                                    WorkflowNode.WORKFLOW_COMPLETE,
                                    "没有剩余问题，工作流完成")
                return False
            else:
                # 重置到下一个问题
                session.advance_to_next_problem()

        elif from_node == WorkflowNode.USER_DECISION and to_node == WorkflowNode.SKIP_PROBLEM:
            # 记录跳过的问题
            if metadata and "problem_id" in metadata:
                session.skipped_problems.append(metadata["problem_id"])

        elif from_node == WorkflowNode.VERIFICATION_DECISION and to_node == WorkflowNode.PROBLEM_SOLVED:
            # 记录解决的问题
            if metadata and "problem_id" in metadata:
                session.solved_problems.append(metadata["problem_id"])

        return True

    def get_next_possible_nodes(self, session_id: str) -> List[WorkflowNode]:
        """
        获取可能的下一个节点

        Args:
            session_id: 会话ID

        Returns:
            List[WorkflowNode]: 可能的下一个节点列表
        """
        if session_id not in self.active_sessions:
            return []

        session = self.active_sessions[session_id]
        current_node = session.current_node

        possible_nodes = self.transition_rules.get(current_node, []).copy()

        # 特殊处理CHECK_REMAINING节点
        if current_node == WorkflowNode.CHECK_REMAINING:
            if not session.has_remaining_problems():
                return [WorkflowNode.WORKFLOW_COMPLETE]
            else:
                return [WorkflowNode.PROBLEM_DETECTION]

        return possible_nodes

    def get_session(self, session_id: str) -> Optional[WorkflowSession]:
        """
        获取会话

        Args:
            session_id: 会话ID

        Returns:
            Optional[WorkflowSession]: 会话对象，如果不存在返回None
        """
        return self.active_sessions.get(session_id)

    def load_session(self, session_id: str) -> Optional[WorkflowSession]:
        """
        从存储加载会话

        Args:
            session_id: 会话ID

        Returns:
            Optional[WorkflowSession]: 加载的会话，如果失败返回None
        """
        try:
            session_file = self.storage_path / f"{session_id}.json"
            if not session_file.exists():
                return None

            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 重建会话对象
            session = WorkflowSession(
                session_id=data["session_id"],
                project_path=data["project_path"],
                selected_files=data["selected_files"],
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                current_node=WorkflowNode(data["current_node"]),
                problems_detected=data["problems_detected"],
                current_problem_index=data["current_problem_index"],
                fix_suggestions=data["fix_suggestions"],
                applied_fixes=data["applied_fixes"],
                skipped_problems=data["skipped_problems"],
                solved_problems=data["solved_problems"],
                metadata=data.get("metadata", {})
            )

            # 重建转换历史
            for trans_data in data["workflow_history"]:
                transition = WorkflowStateTransition(
                    transition_id=trans_data["transition_id"],
                    from_node=WorkflowNode(trans_data["from_node"]),
                    to_node=WorkflowNode(trans_data["to_node"]),
                    timestamp=datetime.fromisoformat(trans_data["timestamp"]),
                    reason=trans_data.get("reason", ""),
                    metadata=trans_data.get("metadata", {})
                )
                session.workflow_history.append(transition)

            self.active_sessions[session_id] = session
            self.logger.info(f"加载工作流会话: {session_id}")

            return session

        except Exception as e:
            self.logger.error(f"加载会话失败 {session_id}: {e}")
            return None

    def _save_session(self, session: WorkflowSession):
        """
        保存会话到存储

        Args:
            session: 会话对象
        """
        try:
            session_file = self.storage_path / f"{session.session_id}.json"

            data = {
                "session_id": session.session_id,
                "project_path": session.project_path,
                "selected_files": session.selected_files,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "current_node": session.current_node.value,
                "workflow_history": [trans.to_dict() for trans in session.workflow_history],
                "problems_detected": session.problems_detected,
                "current_problem_index": session.current_problem_index,
                "fix_suggestions": session.fix_suggestions,
                "applied_fixes": session.applied_fixes,
                "skipped_problems": session.skipped_problems,
                "solved_problems": session.solved_problems,
                "metadata": session.metadata
            }

            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"保存会话失败 {session.session_id}: {e}")

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 删除是否成功
        """
        try:
            # 从活跃会话中移除
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

            # 删除存储文件
            session_file = self.storage_path / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()

            self.logger.info(f"删除工作流会话: {session_id}")
            return True

        except Exception as e:
            self.logger.error(f"删除会话失败 {session_id}: {e}")
            return False

    def get_active_sessions(self) -> List[str]:
        """
        获取所有活跃会话ID

        Returns:
            List[str]: 活跃会话ID列表
        """
        return list(self.active_sessions.keys())

    def get_workflow_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取工作流摘要信息

        Args:
            session_id: 会话ID

        Returns:
            Optional[Dict[str, Any]]: 工作流摘要，如果会话不存在返回None
        """
        session = self.get_session(session_id)
        if not session:
            return None

        total_problems = len(session.problems_detected)
        solved_count = len(session.solved_problems)
        skipped_count = len(session.skipped_problems)

        return {
            "session_id": session_id,
            "project_path": session.project_path,
            "current_node": session.current_node.value,
            "total_problems": total_problems,
            "solved_problems": solved_count,
            "skipped_problems": skipped_count,
            "pending_problems": total_problems - solved_count - skipped_count,
            "progress_percentage": (solved_count / total_problems * 100) if total_problems > 0 else 0,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "next_possible_nodes": [node.value for node in self.get_next_possible_nodes(session_id)]
        }

    def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        清理旧的会话文件

        Args:
            days: 保留天数

        Returns:
            int: 清理的会话数量
        """
        cleaned_count = 0
        cutoff_time = datetime.now().timestamp() - (days * 24 * 3600)

        try:
            for session_file in self.storage_path.glob("*.json"):
                if session_file.stat().st_mtime < cutoff_time:
                    session_id = session_file.stem
                    if session_id in self.active_sessions:
                        del self.active_sessions[session_id]
                    session_file.unlink()
                    cleaned_count += 1

            self.logger.info(f"清理了 {cleaned_count} 个旧会话")

        except Exception as e:
            self.logger.error(f"清理旧会话失败: {e}")

        return cleaned_count