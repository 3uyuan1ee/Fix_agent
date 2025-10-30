"""
工作流用户交互数据结构
支持工作流中各用户决策点的数据结构
"""

import uuid
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..utils.logger import get_logger


class DecisionType(Enum):
    """决策类型枚举"""
    APPROVE = "approve"      # 批准
    MODIFY = "modify"        # 修改
    REJECT = "reject"        # 拒绝
    SUCCESS = "success"      # 成功
    FAILED = "failed"        # 失败
    SKIP = "skip"           # 跳过


class InteractionNodeType(Enum):
    """交互节点类型"""
    USER_REVIEW = "user_review"          # 节点D: 用户审查
    USER_DECISION = "user_decision"      # 节点E: 用户决策
    VERIFICATION_DECISION = "verification_decision"  # 节点I: 用户验证决策
    CONTINUE_DECISION = "continue_decision"  # 节点L: 继续决策


@dataclass
class BaseUserDecision:
    """用户决策基类"""
    decision_id: str
    node_type: InteractionNodeType
    decision_type: DecisionType
    user_id: Optional[str] = None
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "decision_id": self.decision_id,
            "node_type": self.node_type.value,
            "decision_type": self.decision_type.value,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "reasoning": self.reasoning,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseUserDecision':
        """从字典创建实例"""
        data["node_type"] = InteractionNodeType(data["node_type"])
        data["decision_type"] = DecisionType(data["decision_type"])
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


@dataclass
class UserReviewDecision(BaseUserDecision):
    """节点D: 用户审查决策"""
    suggestion_id: str
    problem_id: str = ""
    user_comments: str = ""
    modified_suggestion: Optional[Dict[str, Any]] = None
    review_confidence: float = 0.0  # 0.0-1.0
    review_time_spent: int = 0  # 秒

    def __post_init__(self):
        if not hasattr(self, 'node_type'):
            self.node_type = InteractionNodeType.USER_REVIEW
        if not hasattr(self, 'decision_id'):
            self.decision_id = f"review_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "suggestion_id": self.suggestion_id,
            "problem_id": self.problem_id,
            "user_comments": self.user_comments,
            "modified_suggestion": self.modified_suggestion,
            "review_confidence": self.review_confidence,
            "review_time_spent": self.review_time_spent
        })
        return base_dict


@dataclass
class UserFixDecision(BaseUserDecision):
    """节点E: 用户修复决策"""
    suggestion_id: str
    problem_id: str = ""
    modifications: Optional[Dict[str, Any]] = None
    alternative_approach: Optional[str] = None
    risk_acceptance: bool = False
    decision_certainty: float = 0.0  # 0.0-1.0

    def __post_init__(self):
        if not hasattr(self, 'node_type'):
            self.node_type = InteractionNodeType.USER_DECISION
        if not hasattr(self, 'decision_id'):
            self.decision_id = f"fix_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "suggestion_id": self.suggestion_id,
            "problem_id": self.problem_id,
            "modifications": self.modifications,
            "alternative_approach": self.alternative_approach,
            "risk_acceptance": self.risk_acceptance,
            "decision_certainty": self.decision_certainty
        })
        return base_dict


@dataclass
class UserVerificationDecision(BaseUserDecision):
    """节点I: 用户验证决策"""
    fix_id: str
    problem_id: str = ""
    verification_method: str = ""  # "manual", "automated", "testing"
    test_results: Optional[Dict[str, Any]] = None
    performance_impact: Optional[Dict[str, Any]] = None
    confidence_level: float = 0.0  # 0.0-1.0
    would_recommend: bool = False

    def __post_init__(self):
        if not hasattr(self, 'node_type'):
            self.node_type = InteractionNodeType.VERIFICATION_DECISION
        if not hasattr(self, 'decision_id'):
            self.decision_id = f"verify_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "fix_id": self.fix_id,
            "problem_id": self.problem_id,
            "verification_method": self.verification_method,
            "test_results": self.test_results,
            "performance_impact": self.performance_impact,
            "confidence_level": self.confidence_level,
            "would_recommend": self.would_recommend
        })
        return base_dict


@dataclass
class UserContinueDecision(BaseUserDecision):
    """节点L: 用户继续决策"""
    continue_reasoning: str = ""
    remaining_problems_count: int = 0
    estimated_remaining_time: int = 0  # 分钟
    satisfaction_level: float = 0.0  # 0.0-1.0
    suggestions_for_improvement: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not hasattr(self, 'node_type'):
            self.node_type = InteractionNodeType.CONTINUE_DECISION
        if not hasattr(self, 'decision_id'):
            self.decision_id = f"continue_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        base_dict = super().to_dict()
        base_dict.update({
            "continue_reasoning": self.continue_reasoning,
            "remaining_problems_count": self.remaining_problems_count,
            "estimated_remaining_time": self.estimated_remaining_time,
            "satisfaction_level": self.satisfaction_level,
            "suggestions_for_improvement": self.suggestions_for_improvement
        })
        return base_dict


@dataclass
class UserInteractionSession:
    """用户交互会话数据"""
    session_id: str
    user_id: Optional[str] = None
    project_path: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    decisions: List[BaseUserDecision] = field(default_factory=list)
    total_interaction_time: int = 0  # 秒
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_decision(self, decision: BaseUserDecision):
        """添加决策记录"""
        decision.session_id = self.session_id
        self.decisions.append(decision)

    def get_decisions_by_type(self, node_type: InteractionNodeType) -> List[BaseUserDecision]:
        """根据节点类型获取决策"""
        return [d for d in self.decisions if d.node_type == node_type]

    def get_decisions_by_decision_type(self, decision_type: DecisionType) -> List[BaseUserDecision]:
        """根据决策类型获取决策"""
        return [d for d in self.decisions if d.decision_type == decision_type]

    def calculate_interaction_statistics(self) -> Dict[str, Any]:
        """计算交互统计信息"""
        total_decisions = len(self.decisions)
        if total_decisions == 0:
            return {
                "total_decisions": 0,
                "decision_distribution": {},
                "average_confidence": 0.0,
                "total_time": 0
            }

        # 决策分布统计
        decision_distribution = {}
        for decision_type in DecisionType:
            count = len([d for d in self.decisions if d.decision_type == decision_type])
            decision_distribution[decision_type.value] = count

        # 平均置信度
        confidence_values = []
        for decision in self.decisions:
            if hasattr(decision, 'review_confidence'):
                confidence_values.append(decision.review_confidence)
            elif hasattr(decision, 'decision_certainty'):
                confidence_values.append(decision.decision_certainty)
            elif hasattr(decision, 'confidence_level'):
                confidence_values.append(decision.confidence_level)

        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0

        return {
            "total_decisions": total_decisions,
            "decision_distribution": decision_distribution,
            "average_confidence": avg_confidence,
            "total_time": self.total_interaction_time
        }

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "project_path": self.project_path,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "decisions": [d.to_dict() for d in self.decisions],
            "total_interaction_time": self.total_interaction_time,
            "metadata": self.metadata,
            "statistics": self.calculate_interaction_statistics()
        }


@dataclass
class UserPreferences:
    """用户偏好设置"""
    user_id: str
    auto_approve_safe_fixes: bool = False
    risk_tolerance_level: str = "medium"  # "low", "medium", "high"
    preferred_fix_types: List[str] = field(default_factory=list)
    notification_preferences: Dict[str, bool] = field(default_factory=dict)
    interaction_patterns: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_preference(self, key: str, value: Any):
        """更新偏好设置"""
        if hasattr(self, key):
            setattr(self, key, value)
            self.updated_at = datetime.now()
        else:
            self.interaction_patterns[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "user_id": self.user_id,
            "auto_approve_safe_fixes": self.auto_approve_safe_fixes,
            "risk_tolerance_level": self.risk_tolerance_level,
            "preferred_fix_types": self.preferred_fix_types,
            "notification_preferences": self.notification_preferences,
            "interaction_patterns": self.interaction_patterns,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class UserInteractionManager:
    """用户交互管理器"""

    def __init__(self):
        self.logger = get_logger()
        self.active_sessions: Dict[str, UserInteractionSession] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}

    def create_session(self, session_id: str, user_id: Optional[str] = None,
                      project_path: str = "") -> UserInteractionSession:
        """
        创建用户交互会话

        Args:
            session_id: 会话ID
            user_id: 用户ID
            project_path: 项目路径

        Returns:
            UserInteractionSession: 新创建的会话
        """
        session = UserInteractionSession(
            session_id=session_id,
            user_id=user_id,
            project_path=project_path
        )

        self.active_sessions[session_id] = session
        self.logger.info(f"创建用户交互会话: {session_id}, 用户: {user_id}")

        return session

    def add_decision(self, session_id: str, decision: BaseUserDecision) -> bool:
        """
        添加用户决策

        Args:
            session_id: 会话ID
            decision: 用户决策

        Returns:
            bool: 添加是否成功
        """
        if session_id not in self.active_sessions:
            self.logger.error(f"会话不存在: {session_id}")
            return False

        session = self.active_sessions[session_id]
        session.add_decision(decision)

        # 更新用户偏好（基于决策模式）
        if decision.user_id:
            self._update_user_preferences_from_decision(decision)

        self.logger.info(f"添加用户决策: {decision.decision_id}, 类型: {decision.decision_type.value}")
        return True

    def _update_user_preferences_from_decision(self, decision: BaseUserDecision):
        """基于用户决策更新偏好设置"""
        user_id = decision.user_id
        if not user_id:
            return

        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = UserPreferences(user_id=user_id)

        preferences = self.user_preferences[user_id]

        # 基于决策类型更新偏好
        if decision.decision_type == DecisionType.APPROVE:
            # 记录批准的决策模式
            if "approve_patterns" not in preferences.interaction_patterns:
                preferences.interaction_patterns["approve_patterns"] = []
            preferences.interaction_patterns["approve_patterns"].append({
                "node_type": decision.node_type.value,
                "timestamp": decision.timestamp.isoformat()
            })

        elif decision.decision_type == DecisionType.MODIFY:
            # 记录修改的决策模式
            if "modify_patterns" not in preferences.interaction_patterns:
                preferences.interaction_patterns["modify_patterns"] = []
            preferences.interaction_patterns["modify_patterns"].append({
                "node_type": decision.node_type.value,
                "timestamp": decision.timestamp.isoformat()
            })

        preferences.updated_at = datetime.now()

    def get_session(self, session_id: str) -> Optional[UserInteractionSession]:
        """获取用户交互会话"""
        return self.active_sessions.get(session_id)

    def get_user_preferences(self, user_id: str) -> Optional[UserPreferences]:
        """获取用户偏好设置"""
        return self.user_preferences.get(user_id)

    def set_user_preferences(self, preferences: UserPreferences):
        """设置用户偏好"""
        self.user_preferences[preferences.user_id] = preferences
        self.logger.info(f"更新用户偏好: {preferences.user_id}")

    def analyze_user_behavior(self, user_id: str) -> Optional[Dict[str, Any]]:
        """分析用户行为模式"""
        if user_id not in self.user_preferences:
            return None

        preferences = self.user_preferences[user_id]
        behavior_patterns = {}

        # 分析决策模式
        approve_patterns = preferences.interaction_patterns.get("approve_patterns", [])
        modify_patterns = preferences.interaction_patterns.get("modify_patterns", [])

        # 计算决策倾向
        total_decisions = len(approve_patterns) + len(modify_patterns)
        if total_decisions > 0:
            behavior_patterns["decision_tendency"] = {
                "approve_rate": len(approve_patterns) / total_decisions,
                "modify_rate": len(modify_patterns) / total_decisions
            }

        # 分析时间模式
        if approve_patterns:
            timestamps = [datetime.fromisoformat(p["timestamp"]) for p in approve_patterns]
            behavior_patterns["activity_patterns"] = {
                "most_active_hour": max([t.hour for t in timestamps]) if timestamps else None
            }

        return behavior_patterns

    def end_session(self, session_id: str) -> bool:
        """
        结束用户交互会话

        Args:
            session_id: 会话ID

        Returns:
            bool: 结束是否成功
        """
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        session.end_time = datetime.now()

        self.logger.info(f"结束用户交互会话: {session_id}")
        return True

    def cleanup_inactive_sessions(self, hours: int = 24) -> int:
        """
        清理不活跃的会话

        Args:
            hours: 不活跃小时数阈值

        Returns:
            int: 清理的会话数量
        """
        cutoff_time = datetime.now().timestamp() - (hours * 3600)
        cleaned_count = 0

        for session_id, session in list(self.active_sessions.items()):
            if session.start_time.timestamp() < cutoff_time:
                del self.active_sessions[session_id]
                cleaned_count += 1

        self.logger.info(f"清理了 {cleaned_count} 个不活跃用户会话")
        return cleaned_count