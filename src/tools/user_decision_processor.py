"""
T011.1: 用户决策处理器

节点E的核心组件，负责处理用户对修复建议的决策。支持多种决策类型，
包括接受、拒绝、修改建议等，并记录用户的决策历史和偏好。

工作流位置: 节点E (用户决策)
输入: 用户审查结果 (T010.1/T010.2输出) + 用户交互数据
输出: 用户决策结果 + 工作流状态转换数据
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

from ..utils.logger import get_logger
from ..utils.types import FixType, ProblemType, RiskLevel
from .fix_suggestion_displayer import SuggestionDisplayData
from .workflow_data_types import (
    AIFixSuggestion,
    UserInteractionData,
    WorkflowDataPacket,
)
from .workflow_flow_state_manager import WorkflowFlowStateManager, WorkflowNode
from .workflow_user_interaction_types import (
    DecisionContext,
    DecisionRationale,
    DecisionType,
    ReviewResult,
    UserAction,
    UserDecision,
    UserPreference,
)

logger = get_logger()


class DecisionOutcome(Enum):
    """决策结果枚举"""

    ACCEPT = "accept"  # 接受建议
    REJECT = "reject"  # 拒绝建议
    MODIFY = "modify"  # 修改建议
    SKIP = "skip"  # 跳过当前问题
    POSTPONE = "postpone"  # 延迟决策
    REQUEST_ALTERNATIVE = "request_alternative"  # 请求替代方案
    NEED_MORE_INFO = "need_more_info"  # 需要更多信息


class DecisionConfidence(Enum):
    """决策置信度枚举"""

    VERY_CONFIDENT = "very_confident"  # 非常确信
    CONFIDENT = "confident"  # 确信
    SOMEWHAT_CONFIDENT = "somewhat_confident"  # 比较确信
    UNCERTAIN = "uncertain"  # 不确定
    VERY_UNCERTAIN = "very_uncertain"  # 非常不确定


@dataclass
class DecisionInput:
    """决策输入"""

    suggestion_id: str
    user_action: UserAction
    review_result: Optional[ReviewResult] = None
    user_comment: str = ""
    confidence_level: DecisionConfidence = DecisionConfidence.CONFIDENT
    time_spent_seconds: int = 0
    additional_context: Dict[str, Any] = None

    def __post_init__(self):
        if self.additional_context is None:
            self.additional_context = {}


@dataclass
class DecisionResult:
    """决策结果"""

    decision_id: str
    suggestion_id: str
    outcome: DecisionOutcome
    confidence: DecisionConfidence
    rationale: DecisionRationale
    timestamp: datetime
    time_spent_seconds: int
    next_workflow_node: WorkflowNode
    metadata: Dict[str, Any]

    def __post_init__(self):
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class DecisionBatchResult:
    """批量决策结果"""

    batch_id: str
    decisions: List[DecisionResult]
    total_processed: int
    accepted_count: int
    rejected_count: int
    modified_count: int
    skipped_count: int
    postponed_count: int
    processing_time_seconds: int
    next_workflow_step: WorkflowNode


@dataclass
class DecisionStatistics:
    """决策统计信息"""

    total_decisions: int
    accept_rate: float
    reject_rate: float
    modify_rate: float
    skip_rate: float
    postpone_rate: float
    average_confidence: float
    average_time_per_decision: float
    decision_by_type: Dict[str, Dict[str, int]]
    confidence_distribution: Dict[str, int]


class UserDecisionProcessor:
    """用户决策处理器"""

    def __init__(self, workflow_manager: Optional[WorkflowFlowStateManager] = None):
        """
        初始化用户决策处理器

        Args:
            workflow_manager: 工作流状态管理器
        """
        self.workflow_manager = workflow_manager or WorkflowFlowStateManager()
        self._decision_history: List[DecisionResult] = []
        self._user_preferences: Dict[str, UserPreference] = {}
        self._decision_stats = self._init_decision_stats()

    def process_single_decision(
        self, decision_input: DecisionInput, display_data: SuggestionDisplayData
    ) -> DecisionResult:
        """
        处理单个用户决策

        Args:
            decision_input: 决策输入
            display_data: 展示数据

        Returns:
            决策结果
        """
        try:
            logger.info(f"处理用户决策: {decision_input.suggestion_id}")

            # 解析用户动作
            outcome = self._parse_user_action(decision_input.user_action)

            # 生成决策理由
            rationale = self._generate_decision_rationale(
                decision_input, display_data, outcome
            )

            # 确定下一个工作流节点
            next_node = self._determine_next_workflow_node(outcome)

            # 创建决策结果
            decision_result = DecisionResult(
                decision_id=str(uuid.uuid4()),
                suggestion_id=decision_input.suggestion_id,
                outcome=outcome,
                confidence=decision_input.confidence_level,
                rationale=rationale,
                timestamp=datetime.now(),
                time_spent_seconds=decision_input.time_spent_seconds,
                next_workflow_node=next_node,
                metadata={
                    "user_comment": decision_input.user_comment,
                    "additional_context": decision_input.additional_context,
                    "suggestion_quality": display_data.overall_quality_score,
                    "suggestion_risk": display_data.risk_level,
                },
            )

            # 记录决策
            self._record_decision(decision_result)

            # 更新用户偏好
            self._update_user_preferences(decision_result, display_data)

            # 更新统计信息
            self._update_statistics(decision_result)

            logger.info(f"用户决策处理完成: {decision_result.decision_id}")
            return decision_result

        except Exception as e:
            logger.error(f"处理用户决策失败: {e}")
            raise

    def process_batch_decisions(
        self,
        decision_inputs: List[DecisionInput],
        display_data_list: List[SuggestionDisplayData],
    ) -> DecisionBatchResult:
        """
        批量处理用户决策

        Args:
            decision_inputs: 决策输入列表
            display_data_list: 展示数据列表

        Returns:
            批量决策结果
        """
        batch_id = str(uuid.uuid4())
        start_time = datetime.now()
        decisions = []

        logger.info(f"开始批量处理 {len(decision_inputs)} 个决策")

        try:
            for decision_input, display_data in zip(decision_inputs, display_data_list):
                decision_result = self.process_single_decision(
                    decision_input, display_data
                )
                decisions.append(decision_result)

            # 统计决策结果
            stats = self._calculate_batch_statistics(decisions)

            # 确定下一个工作流步骤
            next_step = self._determine_batch_next_step(decisions)

            processing_time = int((datetime.now() - start_time).total_seconds())

            batch_result = DecisionBatchResult(
                batch_id=batch_id,
                decisions=decisions,
                total_processed=len(decisions),
                accepted_count=stats["accepted"],
                rejected_count=stats["rejected"],
                modified_count=stats["modified"],
                skipped_count=stats["skipped"],
                postponed_count=stats["postponed"],
                processing_time_seconds=processing_time,
                next_workflow_step=next_step,
            )

            logger.info(f"批量决策处理完成: {batch_result.batch_id}")
            return batch_result

        except Exception as e:
            logger.error(f"批量处理决策失败: {e}")
            raise

    def suggest_decision(
        self,
        display_data: SuggestionDisplayData,
        user_context: Optional[Dict[str, Any]] = None,
    ) -> DecisionOutcome:
        """
        基于历史偏好建议决策

        Args:
            display_data: 展示数据
            user_context: 用户上下文

        Returns:
            建议的决策结果
        """
        try:
            # 获取相关用户偏好
            preferences = self._get_relevant_preferences(display_data)

            # 计算建议得分
            accept_score = self._calculate_accept_score(display_data, preferences)
            reject_score = self._calculate_reject_score(display_data, preferences)
            modify_score = self._calculate_modify_score(display_data, preferences)

            # 选择最高得分的决策
            scores = {
                DecisionOutcome.ACCEPT: accept_score,
                DecisionOutcome.REJECT: reject_score,
                DecisionOutcome.MODIFY: modify_score,
            }

            suggested_outcome = max(scores, key=scores.get)

            logger.info(
                f"建议决策: {suggested_outcome.value} (得分: {scores[suggested_outcome]:.2f})"
            )
            return suggested_outcome

        except Exception as e:
            logger.warning(f"生成决策建议失败: {e}")
            return DecisionOutcome.NEED_MORE_INFO

    def get_decision_history(
        self, limit: Optional[int] = None, filter_by_type: Optional[ProblemType] = None
    ) -> List[DecisionResult]:
        """
        获取决策历史

        Args:
            limit: 限制数量
            filter_by_type: 按问题类型过滤

        Returns:
            决策历史列表
        """
        history = self._decision_history.copy()

        # 按类型过滤
        if filter_by_type:
            history = [
                decision
                for decision in history
                if decision.metadata.get("problem_type") == filter_by_type
            ]

        # 按时间倒序排列
        history.sort(key=lambda x: x.timestamp, reverse=True)

        # 限制数量
        if limit:
            history = history[:limit]

        return history

    def get_decision_statistics(self, days: Optional[int] = None) -> DecisionStatistics:
        """
        获取决策统计信息

        Args:
            days: 统计最近N天的数据

        Returns:
            决策统计信息
        """
        recent_decisions = self._decision_history.copy()

        # 按时间过滤
        if days:
            cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
            recent_decisions = [
                decision
                for decision in recent_decisions
                if decision.timestamp.timestamp() > cutoff_date
            ]

        if not recent_decisions:
            return DecisionStatistics(
                total_decisions=0,
                accept_rate=0.0,
                reject_rate=0.0,
                modify_rate=0.0,
                skip_rate=0.0,
                postpone_rate=0.0,
                average_confidence=0.0,
                average_time_per_decision=0.0,
                decision_by_type={},
                confidence_distribution={},
            )

        # 计算统计指标
        total = len(recent_decisions)
        outcome_counts = {}
        type_counts = {}
        confidence_counts = {}
        total_confidence = 0
        total_time = 0

        for decision in recent_decisions:
            # 决策结果统计
            outcome = decision.outcome.value
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

            # 问题类型统计
            problem_type = decision.metadata.get("problem_type", "未知")
            if problem_type not in type_counts:
                type_counts[problem_type] = {
                    "accept": 0,
                    "reject": 0,
                    "modify": 0,
                    "skip": 0,
                    "postpone": 0,
                    "other": 0,
                }
            type_counts[problem_type][outcome] = (
                type_counts[problem_type].get(outcome, 0) + 1
            )

            # 置信度统计
            confidence = decision.confidence.value
            confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1
            total_confidence += list(DecisionConfidence).index(decision.confidence) + 1

            # 时间统计
            total_time += decision.time_spent_seconds

        return DecisionStatistics(
            total_decisions=total,
            accept_rate=outcome_counts.get("accept", 0) / total,
            reject_rate=outcome_counts.get("reject", 0) / total,
            modify_rate=outcome_counts.get("modify", 0) / total,
            skip_rate=outcome_counts.get("skip", 0) / total,
            postpone_rate=outcome_counts.get("postpone", 0) / total,
            average_confidence=total_confidence / total,
            average_time_per_decision=total_time / total,
            decision_by_type=type_counts,
            confidence_distribution=confidence_counts,
        )

    def _parse_user_action(self, user_action: UserAction) -> DecisionOutcome:
        """解析用户动作为决策结果"""
        action_mapping = {
            UserAction.ACCEPT_FIX: DecisionOutcome.ACCEPT,
            UserAction.REJECT_FIX: DecisionOutcome.REJECT,
            UserAction.MODIFY_FIX: DecisionOutcome.MODIFY,
            UserAction.SKIP_PROBLEM: DecisionOutcome.SKIP,
            UserAction.POSTPONE_DECISION: DecisionOutcome.POSTPONE,
            UserAction.REQUEST_ALTERNATIVE: DecisionOutcome.REQUEST_ALTERNATIVE,
            UserAction.NEED_MORE_INFO: DecisionOutcome.NEED_MORE_INFO,
        }

        return action_mapping.get(user_action, DecisionOutcome.NEED_MORE_INFO)

    def _generate_decision_rationale(
        self,
        decision_input: DecisionInput,
        display_data: SuggestionDisplayData,
        outcome: DecisionOutcome,
    ) -> DecisionRationale:
        """生成决策理由"""
        primary_factors = []
        secondary_factors = []
        context_factors = []

        # 主要因素
        if outcome == DecisionOutcome.ACCEPT:
            if display_data.overall_quality_score >= 0.8:
                primary_factors.append("高质量修复建议")
            if display_data.risk_level in ["低风险", "可忽略风险"]:
                primary_factors.append("低风险修复")
            if display_data.confidence >= 0.8:
                primary_factors.append("高置信度建议")

        elif outcome == DecisionOutcome.REJECT:
            if display_data.overall_quality_score < 0.6:
                primary_factors.append("质量评分过低")
            if display_data.risk_level in ["高风险", "关键风险"]:
                primary_factors.append("风险过高")
            if decision_input.user_comment:
                primary_factors.append("用户明确拒绝")

        elif outcome == DecisionOutcome.MODIFY:
            if decision_input.user_comment:
                primary_factors.append("用户要求修改")
            primary_factors.append("建议可改进")

        # 次要因素
        if display_data.code_changes.change_summary:
            secondary_factors.append(
                f"代码变更: {display_data.code_changes.change_summary}"
            )

        if display_data.testing_requirements:
            secondary_factors.append("测试要求明确")

        # 上下文因素
        if decision_input.time_spent_seconds > 300:  # 5分钟
            context_factors.append("决策时间较长，可能需要更多信息")

        if decision_input.confidence_level in [
            DecisionConfidence.UNCERTAIN,
            DecisionConfidence.VERY_UNCERTAIN,
        ]:
            context_factors.append("用户决策不确定")

        return DecisionRationale(
            primary_factors=primary_factors,
            secondary_factors=secondary_factors,
            context_factors=context_factors,
            user_comment=decision_input.user_comment,
            confidence_explanation=self._explain_confidence(
                decision_input.confidence_level
            ),
        )

    def _explain_confidence(self, confidence: DecisionConfidence) -> str:
        """解释置信度"""
        explanations = {
            DecisionConfidence.VERY_CONFIDENT: "用户非常确信这个决策",
            DecisionConfidence.CONFIDENT: "用户确信这个决策",
            DecisionConfidence.SOMEWHAT_CONFIDENT: "用户比较确信这个决策",
            DecisionConfidence.UNCERTAIN: "用户对这个决策不太确定",
            DecisionConfidence.VERY_UNCERTAIN: "用户非常不确定这个决策",
        }
        return explanations.get(confidence, "置信度未知")

    def _determine_next_workflow_node(self, outcome: DecisionOutcome) -> WorkflowNode:
        """确定下一个工作流节点"""
        if outcome == DecisionOutcome.ACCEPT:
            return WorkflowNode.FIX_EXECUTION
        elif outcome == DecisionOutcome.REJECT:
            return WorkflowNode.SKIP_PROBLEM
        elif outcome == DecisionOutcome.MODIFY:
            return WorkflowNode.FIX_EXECUTION
        elif outcome == DecisionOutcome.SKIP:
            return WorkflowNode.SKIP_PROBLEM
        elif outcome == DecisionOutcome.POSTPONE:
            return WorkflowNode.PROBLEM_DETECTION
        elif outcome == DecisionOutcome.REQUEST_ALTERNATIVE:
            return WorkflowNode.FIX_SUGGESTION_GENERATION
        else:
            return WorkflowNode.USER_REVIEW

    def _record_decision(self, decision_result: DecisionResult) -> None:
        """记录决策"""
        self._decision_history.append(decision_result)

        # 限制历史记录数量
        if len(self._decision_history) > 1000:
            self._decision_history = self._decision_history[-500:]

    def _update_user_preferences(
        self, decision_result: DecisionResult, display_data: SuggestionDisplayData
    ) -> None:
        """更新用户偏好"""
        # 更新质量偏好
        if decision_result.outcome == DecisionOutcome.ACCEPT:
            quality_level = self._categorize_quality(display_data.overall_quality_score)
            self._update_preference("quality_preference", quality_level, 1.0)

        # 更新风险偏好
        if decision_result.outcome == DecisionOutcome.REJECT:
            if display_data.risk_level in ["高风险", "关键风险"]:
                self._update_preference("risk_tolerance", "conservative", 1.0)

        # 更新问题类型偏好
        problem_type = display_data.problem_type
        if decision_result.outcome == DecisionOutcome.ACCEPT:
            self._update_preference(f"accept_{problem_type}", True, 0.1)
        elif decision_result.outcome == DecisionOutcome.REJECT:
            self._update_preference(f"accept_{problem_type}", False, 0.1)

    def _update_preference(self, key: str, value: Any, weight: float) -> None:
        """更新单个偏好"""
        if key not in self._user_preferences:
            self._user_preferences[key] = UserPreference(
                preference_id=str(uuid.uuid4()),
                user_id="default",  # 实际应从配置获取
                preference_key=key,
                preference_value=value,
                confidence=weight,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        else:
            preference = self._user_preferences[key]
            preference.preference_value = value
            preference.confidence = min(1.0, preference.confidence + weight * 0.1)
            preference.updated_at = datetime.now()

    def _get_relevant_preferences(
        self, display_data: SuggestionDisplayData
    ) -> Dict[str, Any]:
        """获取相关用户偏好"""
        preferences = {}

        # 质量偏好
        quality_level = self._categorize_quality(display_data.overall_quality_score)
        preferences["quality_preference"] = self._user_preferences.get(
            "quality_preference"
        )

        # 风险偏好
        preferences["risk_tolerance"] = self._user_preferences.get("risk_tolerance")

        # 问题类型偏好
        problem_type = display_data.problem_type
        preferences[f"accept_{problem_type}"] = self._user_preferences.get(
            f"accept_{problem_type}"
        )

        return preferences

    def _calculate_accept_score(
        self, display_data: SuggestionDisplayData, preferences: Dict[str, Any]
    ) -> float:
        """计算接受得分"""
        score = 0.0

        # 质量得分
        score += display_data.overall_quality_score * 0.3

        # 置信度得分
        score += display_data.confidence * 0.2

        # 风险得分（风险越低得分越高）
        risk_score = self._risk_to_score(display_data.risk_level)
        score += risk_score * 0.2

        # 偏好得分
        if preferences.get("quality_preference"):
            score += 0.1

        if preferences.get(f"accept_{display_data.problem_type}"):
            score += 0.2

        return min(1.0, score)

    def _calculate_reject_score(
        self, display_data: SuggestionDisplayData, preferences: Dict[str, Any]
    ) -> float:
        """计算拒绝得分"""
        score = 0.0

        # 低质量得分
        if display_data.overall_quality_score < 0.6:
            score += (0.6 - display_data.overall_quality_score) * 0.4

        # 高风险得分
        risk_score = self._risk_to_reject_score(display_data.risk_level)
        score += risk_score * 0.3

        # 低置信度得分
        if display_data.confidence < 0.7:
            score += (0.7 - display_data.confidence) * 0.3

        return min(1.0, score)

    def _calculate_modify_score(
        self, display_data: SuggestionDisplayData, preferences: Dict[str, Any]
    ) -> float:
        """计算修改得分"""
        score = 0.0

        # 中等质量得分
        if 0.6 <= display_data.overall_quality_score <= 0.8:
            score += 0.3

        # 中等风险得分
        if display_data.risk_level in ["中等风险"]:
            score += 0.2

        # 有替代方案得分
        if display_data.alternatives:
            score += 0.2

        # 复杂度得分
        complexity = display_data.display_metadata.get("code_change_size", 0)
        if complexity > 5:
            score += 0.3

        return min(1.0, score)

    def _risk_to_score(self, risk_level: str) -> float:
        """风险等级转得分"""
        risk_scores = {
            "可忽略风险": 1.0,
            "NEGLIGIBLE": 1.0,
            "低风险": 0.8,
            "LOW": 0.8,
            "中等风险": 0.5,
            "MEDIUM": 0.5,
            "高风险": 0.2,
            "HIGH": 0.2,
            "关键风险": 0.0,
            "CRITICAL": 0.0,
        }
        return risk_scores.get(risk_level, 0.5)

    def _risk_to_reject_score(self, risk_level: str) -> float:
        """风险等级转拒绝得分"""
        reject_scores = {
            "可忽略风险": 0.0,
            "NEGLIGIBLE": 0.0,
            "低风险": 0.2,
            "LOW": 0.2,
            "中等风险": 0.5,
            "MEDIUM": 0.5,
            "高风险": 0.8,
            "HIGH": 0.8,
            "关键风险": 1.0,
            "CRITICAL": 1.0,
        }
        return reject_scores.get(risk_level, 0.5)

    def _categorize_quality(self, score: float) -> str:
        """分类质量等级"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.8:
            return "good"
        elif score >= 0.7:
            return "acceptable"
        else:
            return "poor"

    def _calculate_batch_statistics(
        self, decisions: List[DecisionResult]
    ) -> Dict[str, int]:
        """计算批量统计"""
        stats = {
            "accepted": 0,
            "rejected": 0,
            "modified": 0,
            "skipped": 0,
            "postponed": 0,
        }

        for decision in decisions:
            outcome = decision.outcome.value
            if outcome in stats:
                stats[outcome] += 1

        return stats

    def _determine_batch_next_step(
        self, decisions: List[DecisionResult]
    ) -> WorkflowNode:
        """确定批量处理的下一个工作流步骤"""
        if not decisions:
            return WorkflowNode.USER_REVIEW

        # 如果有接受或修改的决策，进入修复执行
        for decision in decisions:
            if decision.outcome in [DecisionOutcome.ACCEPT, DecisionOutcome.MODIFY]:
                return WorkflowNode.FIX_EXECUTION

        # 如果有拒绝或跳过的决策，进入跳过处理
        for decision in decisions:
            if decision.outcome in [DecisionOutcome.REJECT, DecisionOutcome.SKIP]:
                return WorkflowNode.SKIP_PROBLEM

        # 否则继续问题检测
        return WorkflowNode.PROBLEM_DETECTION

    def _update_statistics(self, decision_result: DecisionResult) -> None:
        """更新统计信息"""
        # 更新各种计数器
        pass

    def _init_decision_stats(self) -> Dict[str, Any]:
        """初始化决策统计"""
        return {
            "total_decisions": 0,
            "accept_count": 0,
            "reject_count": 0,
            "modify_count": 0,
            "skip_count": 0,
            "postpone_count": 0,
        }

    def export_decisions_to_json(self, decisions: List[DecisionResult]) -> str:
        """导出决策为JSON"""
        exportable_decisions = []
        for decision in decisions:
            decision_dict = asdict(decision)
            decision_dict["timestamp"] = decision.timestamp.isoformat()
            decision_dict["outcome"] = decision.outcome.value
            decision_dict["confidence"] = decision.confidence.value
            decision_dict["next_workflow_node"] = decision.next_workflow_node.value
            exportable_decisions.append(decision_dict)

        return json.dumps(exportable_decisions, ensure_ascii=False, indent=2)
