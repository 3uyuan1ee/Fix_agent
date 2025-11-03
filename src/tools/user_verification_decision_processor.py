#!/usr/bin/env python3
"""
用户验证决策处理器 - T015.2
收集用户对验证结果的两种决策：成功、失败
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
from .workflow_user_interaction_types import UserDecision, DecisionType
from .workflow_flow_state_manager import WorkflowNode, WorkflowFlowStateManager
from .fix_verification_aggregator import ComprehensiveVerificationReport

logger = get_logger()


@dataclass
class UserVerificationDecision:
    """用户验证决策"""
    decision_id: str
    session_id: str
    suggestion_id: str
    decision_type: str  # "success" 或 "failure"
    decision_reason: str
    user_comments: Optional[str]
    confidence_level: float
    decision_timestamp: datetime
    verification_report_id: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "decision_id": self.decision_id,
            "session_id": self.session_id,
            "suggestion_id": self.suggestion_id,
            "decision_type": self.decision_type,
            "decision_reason": self.decision_reason,
            "user_comments": self.user_comments,
            "confidence_level": self.confidence_level,
            "decision_timestamp": self.decision_timestamp.isoformat(),
            "verification_report_id": self.verification_report_id
        }


@dataclass
class VerificationDecisionOptions:
    """验证决策选项"""
    success_option: Dict[str, Any]
    failure_option: Dict[str, Any]
    additional_options: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success_option": self.success_option,
            "failure_option": self.failure_option,
            "additional_options": self.additional_options
        }


class VerificationDecisionType(Enum):
    """验证决策类型"""
    SUCCESS = "success"       # 验证成功
    FAILURE = "failure"       # 验证失败


class UserVerificationDecisionProcessor:
    """用户验证决策处理器 - T015.2

    工作流位置: 节点I决策点，处理用户对验证结果的决策
    核心功能: 收集用户对验证结果的两种决策：成功、失败
    用户协作: 实现用户对修复验证的最终确认权
    """

    def __init__(self, config_manager=None):
        """初始化用户验证决策处理器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.state_manager = WorkflowFlowStateManager()

        # 获取配置
        self.config = self.config_manager.get("project_analysis", {})

        # 决策记录存储目录
        self.decisions_dir = Path(self.config.get("verification_decisions_dir", ".fix_backups/verification_decisions"))
        self.decisions_dir.mkdir(parents=True, exist_ok=True)

    def process_user_verification_decision(
        self,
        session_id: str,
        suggestion_id: str,
        decision_type: VerificationDecisionType,
        decision_reason: str,
        user_comments: Optional[str] = None,
        confidence_level: float = 0.8,
        verification_report_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理用户验证决策

        Args:
            session_id: 会话ID
            suggestion_id: 修复建议ID
            decision_type: 决策类型
            decision_reason: 决策原因
            user_comments: 用户评论
            confidence_level: 置信度水平
            verification_report_id: 验证报告ID

        Returns:
            Dict[str, Any]: 处理结果
        """
        try:
            self.logger.info(f"处理用户验证决策: 会话={session_id}, 决策={decision_type.value}")

            # 获取会话信息
            session = self.state_manager.get_session(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 创建用户决策记录
            verification_decision = self._create_verification_decision(
                session_id=session_id,
                suggestion_id=suggestion_id,
                decision_type=decision_type,
                decision_reason=decision_reason,
                user_comments=user_comments,
                confidence_level=confidence_level,
                verification_report_id=verification_report_id
            )

            # 保存决策记录
            self._save_verification_decision(verification_decision)

            # 更新会话状态
            session.verification_decisions.append(verification_decision.decision_id)
            session.problem_processing_status[suggestion_id] = decision_type.value

            # 保存会话状态
            self.state_manager.save_session(session)

            # 根据决策类型转换到相应节点
            next_node = self._determine_next_node(decision_type)
            transition_message = self._build_transition_message(decision_type, decision_reason)

            self.state_manager.transition_to(
                session_id,
                next_node,
                transition_message
            )

            # 生成处理结果
            result = {
                "success": True,
                "decision_id": verification_decision.decision_id,
                "decision_type": decision_type.value,
                "next_node": next_node.value,
                "transition_message": transition_message,
                "message": f"用户验证决策已处理: {decision_type.value}"
            }

            self.logger.info(f"用户验证决策处理完成: {result}")
            return result

        except Exception as e:
            self.logger.error(f"处理用户验证决策失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "处理用户验证决策失败"
            }

    def _create_verification_decision(
        self,
        session_id: str,
        suggestion_id: str,
        decision_type: VerificationDecisionType,
        decision_reason: str,
        user_comments: Optional[str],
        confidence_level: float,
        verification_report_id: Optional[str]
    ) -> UserVerificationDecision:
        """创建验证决策记录"""
        return UserVerificationDecision(
            decision_id=str(uuid.uuid4()),
            session_id=session_id,
            suggestion_id=suggestion_id,
            decision_type=decision_type.value,
            decision_reason=decision_reason,
            user_comments=user_comments,
            confidence_level=confidence_level,
            decision_timestamp=datetime.now(),
            verification_report_id=verification_report_id or f"report_{suggestion_id}"
        )

    def _save_verification_decision(self, decision: UserVerificationDecision) -> None:
        """保存验证决策记录"""
        try:
            decision_file = self.decisions_dir / f"decision_{decision.session_id}_{decision.suggestion_id}.json"

            with open(decision_file, 'w', encoding='utf-8') as f:
                json.dump(decision.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"验证决策记录已保存: {decision.decision_id}")

        except Exception as e:
            self.logger.error(f"保存验证决策记录失败: {e}")
            raise

    def _determine_next_node(self, decision_type: VerificationDecisionType) -> WorkflowNode:
        """确定下一个节点"""
        if decision_type == VerificationDecisionType.SUCCESS:
            return WorkflowNode.PROBLEM_SOLVED
        elif decision_type == VerificationDecisionType.FAILURE:
            return WorkflowNode.REANALYSIS
        else:
            return WorkflowNode.CHECK_REMAINING

    def _build_transition_message(self, decision_type: VerificationDecisionType, reason: str) -> str:
        """构建转换消息"""
        if decision_type == VerificationDecisionType.SUCCESS:
            return f"用户确认修复成功: {reason}"
        elif decision_type == VerificationDecisionType.FAILURE:
            return f"用户确认修复失败: {reason}，将重新分析"
        else:
            return f"用户验证决策: {decision_type.value} - {reason}"

    def get_verification_decision_options(
        self,
        verification_report: ComprehensiveVerificationReport
    ) -> VerificationDecisionOptions:
        """
        获取验证决策选项

        Args:
            verification_report: 综合验证报告

        Returns:
            VerificationDecisionOptions: 决策选项
        """
        try:
            # 基于验证报告生成决策选项
            success_option = {
                "value": "success",
                "label": "✅ 修复成功",
                "description": "确认修复已成功解决问题",
                "recommended": verification_report.verification_summary.problem_resolved,
                "reason": "问题已得到有效解决"
            }

            failure_option = {
                "value": "failure",
                "label": "❌ 修复失败",
                "description": "确认修复未能解决原始问题",
                "recommended": not verification_report.verification_summary.problem_resolved,
                "reason": "问题未得到解决或引入了新问题"
            }

            # 根据验证结果添加额外选项
            additional_options = []

            if verification_report.verification_summary.introduced_new_issues:
                additional_options.append({
                    "value": "success_with_concerns",
                    "label": "⚠️ 修复成功但有顾虑",
                    "description": "修复了问题但引入了新问题，需要进一步处理",
                    "recommended": False,
                    "reason": "修复有效但有副作用"
                })

            if verification_report.verification_summary.confidence_level < 0.6:
                additional_options.append({
                    "value": "uncertain",
                    "label": "❓ 结果不确定",
                    "description": "验证结果不够明确，需要进一步分析",
                    "recommended": False,
                    "reason": "置信度较低，需要更多信息"
                })

            return VerificationDecisionOptions(
                success_option=success_option,
                failure_option=failure_option,
                additional_options=additional_options
            )

        except Exception as e:
            self.logger.error(f"获取验证决策选项失败: {e}")
            # 返回默认选项
            return VerificationDecisionOptions(
                success_option={
                    "value": "success",
                    "label": "✅ 修复成功",
                    "description": "确认修复已成功解决问题",
                    "recommended": False,
                    "reason": "用户确认修复成功"
                },
                failure_option={
                    "value": "failure",
                    "label": "❌ 修复失败",
                    "description": "确认修复未能解决原始问题",
                    "recommended": False,
                    "reason": "用户确认修复失败"
                },
                additional_options=[]
            )

    def get_verification_decision_history(self, session_id: str) -> List[UserVerificationDecision]:
        """
        获取会话的验证决策历史

        Args:
            session_id: 会话ID

        Returns:
            List[UserVerificationDecision]: 验证决策历史
        """
        try:
            session = self.state_manager.get_session(session_id)
            if not session:
                return []

            decisions = []
            for decision_id in session.verification_decisions:
                decision = self._load_verification_decision(decision_id)
                if decision:
                    decisions.append(decision)

            return sorted(decisions, key=lambda d: d.decision_timestamp, reverse=True)

        except Exception as e:
            self.logger.error(f"获取验证决策历史失败: {e}")
            return []

    def _load_verification_decision(self, decision_id: str) -> Optional[UserVerificationDecision]:
        """加载验证决策记录"""
        try:
            # 查找对应的决策文件
            for decision_file in self.decisions_dir.glob("decision_*.json"):
                with open(decision_file, 'r', encoding='utf-8') as f:
                    decision_data = json.load(f)
                    if decision_data.get("decision_id") == decision_id:
                        return self._reconstruct_decision(decision_data)

            return None

        except Exception as e:
            self.logger.error(f"加载验证决策记录失败: {e}")
            return None

    def _reconstruct_decision(self, decision_data: Dict[str, Any]) -> UserVerificationDecision:
        """从字典数据重构验证决策"""
        return UserVerificationDecision(
            decision_id=decision_data["decision_id"],
            session_id=decision_data["session_id"],
            suggestion_id=decision_data["suggestion_id"],
            decision_type=decision_data["decision_type"],
            decision_reason=decision_data["decision_reason"],
            user_comments=decision_data.get("user_comments"),
            confidence_level=decision_data["confidence_level"],
            decision_timestamp=datetime.fromisoformat(decision_data["decision_timestamp"]),
            verification_report_id=decision_data["verification_report_id"]
        )

    def batch_process_verification_decisions(
        self,
        decisions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        批量处理验证决策

        Args:
            decisions: 决策列表，每个包含session_id, suggestion_id, decision_type等

        Returns:
            Dict[str, Any]: 批量处理结果
        """
        try:
            self.logger.info(f"开始批量处理验证决策: 数量={len(decisions)}")

            results = {
                "success_count": 0,
                "failed_count": 0,
                "results": [],
                "total_decisions": len(decisions)
            }

            for decision_data in decisions:
                try:
                    result = self.process_user_verification_decision(**decision_data)

                    results["results"].append({
                        "suggestion_id": decision_data.get("suggestion_id"),
                        "success": result.get("success", False),
                        "message": result.get("message", "")
                    })

                    if result.get("success"):
                        results["success_count"] += 1
                    else:
                        results["failed_count"] += 1

                except Exception as e:
                    self.logger.error(f"批量处理单个决策失败: {e}")
                    results["results"].append({
                        "suggestion_id": decision_data.get("suggestion_id"),
                        "success": False,
                        "message": str(e)
                    })
                    results["failed_count"] += 1

            self.logger.info(f"批量验证决策处理完成: 成功={results['success_count']}, 失败={results['failed_count']}")
            return results

        except Exception as e:
            self.logger.error(f"批量处理验证决策失败: {e}")
            return {
                "success_count": 0,
                "failed_count": len(decisions),
                "results": [],
                "total_decisions": len(decisions),
                "error": str(e)
            }

    def analyze_decision_patterns(self, session_id: str) -> Dict[str, Any]:
        """
        分析会话中的决策模式

        Args:
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 决策模式分析结果
        """
        try:
            decisions = self.get_verification_decision_history(session_id)
            if not decisions:
                return {"message": "无决策历史记录"}

            # 统计决策类型分布
            decision_counts = {"success": 0, "failure": 0}
            for decision in decisions:
                decision_type = decision.decision_type
                if decision_type in decision_counts:
                    decision_counts[decision_type] += 1

            # 计算平均置信度
            avg_confidence = sum(d.confidence_level for d in decisions) / len(decisions)

            # 分析常见决策原因
            reason_counts = {}
            for decision in decisions:
                reason = decision.decision_reason
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

            # 生成模式分析
            total_decisions = len(decisions)
            success_rate = decision_counts["success"] / total_decisions if total_decisions > 0 else 0

            return {
                "total_decisions": total_decisions,
                "decision_distribution": decision_counts,
                "success_rate": success_rate,
                "average_confidence": avg_confidence,
                "common_reasons": reason_counts,
                "decision_trend": self._analyze_decision_trend(decisions),
                "recommendations": self._generate_pattern_recommendations(success_rate, avg_confidence)
            }

        except Exception as e:
            self.logger.error(f"分析决策模式失败: {e}")
            return {"error": str(e)}

    def _analyze_decision_trend(self, decisions: List[UserVerificationDecision]) -> str:
        """分析决策趋势"""
        if len(decisions) < 3:
            return "数据不足"

        # 检查最近的决策趋势
        recent_decisions = decisions[:3]  # 最近3个决策
        success_count = sum(1 for d in recent_decisions if d.decision_type == "success")

        if success_count >= 2:
            return "近期倾向于确认成功"
        elif success_count == 1:
            return "近期决策较为平衡"
        else:
            return "近期倾向于确认失败"

    def _generate_pattern_recommendations(self, success_rate: float, avg_confidence: float) -> List[str]:
        """生成模式建议"""
        recommendations = []

        if success_rate < 0.5:
            recommendations.append("修复成功率较低，建议改进修复质量或重新评估问题")
        elif success_rate > 0.8:
            recommendations.append("修复成功率很高，继续保持当前策略")

        if avg_confidence < 0.6:
            recommendations.append("决策置信度较低，建议提供更详细的验证信息")
        elif avg_confidence > 0.8:
            recommendations.append("决策置信度很高，验证信息充分有效")

        if not recommendations:
            recommendations.append("决策模式正常，继续当前工作流程")

        return recommendations