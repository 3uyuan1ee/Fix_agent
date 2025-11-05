"""
工作流用户交互数据结构
支持工作流中各用户决策点的数据结构
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..utils.logger import get_logger


class DecisionType(Enum):
    """决策类型枚举"""

    APPROVE = "approve"  # 批准
    MODIFY = "modify"  # 修改
    REJECT = "reject"  # 拒绝
    SUCCESS = "success"  # 成功
    FAILED = "failed"  # 失败
    SKIP = "skip"  # 跳过


class InteractionNodeType(Enum):
    """交互节点类型"""

    USER_REVIEW = "user_review"  # 节点D: 用户审查
    USER_DECISION = "user_decision"  # 节点E: 用户决策
    VERIFICATION_DECISION = "verification_decision"  # 节点I: 用户验证决策
    CONTINUE_DECISION = "continue_decision"  # 节点L: 继续决策


# 简化的用户决策类型，用于测试
class UserDecision:
    """简化的用户决策类"""

    def __init__(
        self, decision_id: str, decision_type: DecisionType, session_id: str = ""
    ):
        self.decision_id = decision_id
        self.decision_type = decision_type
        self.session_id = session_id
        self.timestamp = datetime.now()
        self.reasoning = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "reasoning": self.reasoning,
        }


# 为了兼容性，添加空的决策类
class Decision:
    """兼容性决策类"""

    pass
