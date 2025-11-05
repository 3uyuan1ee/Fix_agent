#!/usr/bin/env python3
"""
重新分析触发器 - T017.1
处理修复失败后的重新分析，触发对失败问题的重新分析流程
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from .workflow_data_types import AIDetectedProblem, AIFixSuggestion
from .workflow_flow_state_manager import (
    WorkflowFlowStateManager,
    WorkflowNode,
    WorkflowSession,
)
from .workflow_user_interaction_types import UserDecision

logger = get_logger()


@dataclass
class ReanalysisContext:
    """重新分析上下文"""

    reanalysis_id: str
    session_id: str
    original_issue_id: str
    failed_suggestion_id: str
    failure_reason: str
    failure_analysis: Dict[str, Any]
    previous_attempts: List[Dict[str, Any]]
    adjusted_strategy: Dict[str, Any]
    reanalysis_timestamp: datetime
    retry_count: int

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "reanalysis_id": self.reanalysis_id,
            "session_id": self.session_id,
            "original_issue_id": self.original_issue_id,
            "failed_suggestion_id": self.failed_suggestion_id,
            "failure_reason": self.failure_reason,
            "failure_analysis": self.failure_analysis,
            "previous_attempts": self.previous_attempts,
            "adjusted_strategy": self.adjusted_strategy,
            "reanalysis_timestamp": self.reanalysis_timestamp.isoformat(),
            "retry_count": self.retry_count,
        }


@dataclass
class FailureAnalysis:
    """失败分析结果"""

    analysis_id: str
    issue_id: str
    suggestion_id: str
    failure_patterns: List[str]
    root_causes: List[str]
    learnings: List[str]
    recommended_adjustments: Dict[str, Any]
    confidence_score: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "analysis_id": self.analysis_id,
            "issue_id": self.issue_id,
            "suggestion_id": self.suggestion_id,
            "failure_patterns": self.failure_patterns,
            "root_causes": self.root_causes,
            "learnings": self.learnings,
            "recommended_adjustments": self.recommended_adjustments,
            "confidence_score": self.confidence_score,
        }


class ReanalysisStrategy(Enum):
    """重新分析策略"""

    SAME_APPROACH = "same_approach"  # 相同方法
    ALTERNATIVE_APPROACH = "alternative_approach"  # 替代方法
    MORE_CONTEXT = "more_context"  # 更多上下文
    DIFFERENT_AI_MODEL = "different_ai_model"  # 不同AI模型
    HUMAN_INTERVENTION = "human_intervention"  # 人工干预


class ReanalysisTrigger:
    """重新分析触发器 - T017.1

    工作流位置: 节点K，处理修复失败后的重新分析
    核心功能: 触发对失败问题的重新分析流程
    AI集成: 支持AI从失败中学习和改进
    """

    def __init__(self, config_manager=None):
        """初始化重新分析触发器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.state_manager = WorkflowFlowStateManager()

        # 获取配置
        self.config = self.config_manager.get_config("project_analysis", {})

        # 重新分析配置
        self.max_retry_attempts = self.config.get("max_retry_attempts", 3)
        self.reanalysis_dir = Path(
            self.config.get("reanalysis_dir", ".fix_backups/reanalysis")
        )
        self.reanalysis_dir.mkdir(parents=True, exist_ok=True)

    def trigger_reanalysis(
        self,
        session_id: str,
        issue_id: str,
        failed_suggestion_id: str,
        failure_reason: str,
        verification_results: Optional[Dict[str, Any]] = None,
        user_feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        触发重新分析

        Args:
            session_id: 会话ID
            issue_id: 问题ID
            failed_suggestion_id: 失败的修复建议ID
            failure_reason: 失败原因
            verification_results: 验证结果
            user_feedback: 用户反馈

        Returns:
            Dict[str, Any]: 触发结果
        """
        try:
            self.logger.info(f"触发重新分析: 会话={session_id}, 问题={issue_id}")

            # 获取会话信息
            session = self.state_manager.get_session(session_id)
            if not session:
                raise ValueError(f"会话不存在: {session_id}")

            # 检查重试次数限制
            current_retry_count = self._get_retry_count(session, issue_id)
            if current_retry_count >= self.max_retry_attempts:
                return self._handle_max_retries_exceeded(session, issue_id)

            # 分析失败原因
            failure_analysis = self._analyze_failure(
                session=session,
                issue_id=issue_id,
                suggestion_id=failed_suggestion_id,
                failure_reason=failure_reason,
                verification_results=verification_results,
                user_feedback=user_feedback,
            )

            # 获取历史尝试记录
            previous_attempts = self._get_previous_attempts(session, issue_id)

            # 调整分析策略
            adjusted_strategy = self._adjust_analysis_strategy(
                failure_analysis=failure_analysis,
                previous_attempts=previous_attempts,
                retry_count=current_retry_count,
            )

            # 创建重新分析上下文
            reanalysis_context = self._create_reanalysis_context(
                session_id=session_id,
                issue_id=issue_id,
                failed_suggestion_id=failed_suggestion_id,
                failure_reason=failure_reason,
                failure_analysis=failure_analysis,
                previous_attempts=previous_attempts,
                adjusted_strategy=adjusted_strategy,
                retry_count=current_retry_count + 1,
            )

            # 保存重新分析上下文
            self._save_reanalysis_context(reanalysis_context)

            # 更新会话状态
            self._update_session_for_reanalysis(session, reanalysis_context)

            # 转换到节点B（重新问题检测）
            self.state_manager.transition_to(
                session_id,
                WorkflowNode.PROBLEM_DETECTION,
                f"触发重新分析: {issue_id} (第{current_retry_count + 1}次尝试)",
            )

            # 生成触发结果
            result = {
                "success": True,
                "reanalysis_id": reanalysis_context.reanalysis_id,
                "issue_id": issue_id,
                "retry_count": current_retry_count + 1,
                "adjusted_strategy": adjusted_strategy,
                "next_node": "PROBLEM_DETECTION",
                "failure_analysis": failure_analysis.to_dict(),
                "message": f"已触发问题 {issue_id} 的重新分析",
            }

            self.logger.info(f"重新分析触发完成: {result}")
            return result

        except Exception as e:
            self.logger.error(f"触发重新分析失败: {e}")
            return {"success": False, "error": str(e), "message": "触发重新分析失败"}

    def _get_retry_count(self, session: WorkflowSession, issue_id: str) -> int:
        """获取重试次数"""
        if not hasattr(session, "reanalysis_history"):
            session.reanalysis_history = {}

        return session.reanalysis_history.get(issue_id, {}).get("retry_count", 0)

    def _analyze_failure(
        self,
        session: WorkflowSession,
        issue_id: str,
        suggestion_id: str,
        failure_reason: str,
        verification_results: Optional[Dict[str, Any]],
        user_feedback: Optional[str],
    ) -> FailureAnalysis:
        """分析失败原因"""
        try:
            # 获取问题信息
            problem = self._get_problem_by_id(session, issue_id)
            if not problem:
                raise ValueError(f"问题不存在: {issue_id}")

            # 获取失败的修复建议
            failed_suggestion = self._get_fix_suggestion_by_id(session, suggestion_id)
            if not failed_suggestion:
                raise ValueError(f"修复建议不存在: {suggestion_id}")

            # 分析失败模式
            failure_patterns = self._identify_failure_patterns(
                failure_reason, verification_results, user_feedback
            )

            # 分析根本原因
            root_causes = self._identify_root_causes(
                problem, failed_suggestion, failure_patterns
            )

            # 提取学习要点
            learnings = self._extract_learnings(failure_patterns, root_causes)

            # 推荐调整方案
            recommended_adjustments = self._recommend_adjustments(
                failure_patterns, root_causes, learnings
            )

            # 计算置信度
            confidence_score = self._calculate_analysis_confidence(
                failure_patterns, root_causes, verification_results
            )

            return FailureAnalysis(
                analysis_id=str(uuid.uuid4()),
                issue_id=issue_id,
                suggestion_id=suggestion_id,
                failure_patterns=failure_patterns,
                root_causes=root_causes,
                learnings=learnings,
                recommended_adjustments=recommended_adjustments,
                confidence_score=confidence_score,
            )

        except Exception as e:
            self.logger.error(f"分析失败原因失败: {e}")
            # 返回默认分析
            return FailureAnalysis(
                analysis_id=str(uuid.uuid4()),
                issue_id=issue_id,
                suggestion_id=suggestion_id,
                failure_patterns=["analysis_failed"],
                root_causes=["unknown_error"],
                learnings=["需要更多调试信息"],
                recommended_adjustments={"strategy": "manual_review"},
                confidence_score=0.1,
            )

    def _get_problem_by_id(
        self, session: WorkflowSession, issue_id: str
    ) -> Optional[AIDetectedProblem]:
        """根据ID获取问题信息"""
        for problem in session.detected_problems:
            if problem.issue_id == issue_id:
                return problem
        return None

    def _get_fix_suggestion_by_id(
        self, session: WorkflowSession, suggestion_id: str
    ) -> Optional[AIFixSuggestion]:
        """根据ID获取修复建议信息"""
        for suggestion in session.fix_suggestions:
            if suggestion.suggestion_id == suggestion_id:
                return suggestion
        return None

    def _identify_failure_patterns(
        self,
        failure_reason: str,
        verification_results: Optional[Dict[str, Any]],
        user_feedback: Optional[str],
    ) -> List[str]:
        """识别失败模式"""
        patterns = []

        # 基于失败原因的模式
        if "语法" in failure_reason.lower() or "syntax" in failure_reason.lower():
            patterns.append("syntax_error")
        if "逻辑" in failure_reason.lower() or "logic" in failure_reason.lower():
            patterns.append("logic_error")
        if (
            "验证失败" in failure_reason.lower()
            or "verification_failed" in failure_reason.lower()
        ):
            patterns.append("verification_failure")
        if (
            "引入新问题" in failure_reason.lower()
            or "new_issues" in failure_reason.lower()
        ):
            patterns.append("regression")

        # 基于验证结果的模式
        if verification_results:
            if verification_results.get("new_issues_count", 0) > 0:
                patterns.append("introduced_new_issues")
            if verification_results.get("fix_success_rate", 0) < 0.5:
                patterns.append("low_success_rate")

        # 基于用户反馈的模式
        if user_feedback:
            if (
                "不正确" in user_feedback.lower()
                or "incorrect" in user_feedback.lower()
            ):
                patterns.append("incorrect_fix")
            if (
                "不完整" in user_feedback.lower()
                or "incomplete" in user_feedback.lower()
            ):
                patterns.append("incomplete_fix")

        return patterns if patterns else ["unknown_pattern"]

    def _identify_root_causes(
        self,
        problem: AIDetectedProblem,
        suggestion: AIFixSuggestion,
        failure_patterns: List[str],
    ) -> List[str]:
        """识别根本原因"""
        causes = []

        # 基于失败模式的根本原因分析
        for pattern in failure_patterns:
            if pattern == "syntax_error":
                causes.append("AI生成的代码存在语法错误")
            elif pattern == "logic_error":
                causes.append("AI对问题逻辑理解有误")
            elif pattern == "verification_failure":
                causes.append("修复方案未能通过验证")
            elif pattern == "regression":
                causes.append("修复引入了新的问题")
            elif pattern == "incorrect_fix":
                causes.append("修复方案不正确或不合适")
            elif pattern == "incomplete_fix":
                causes.append("修复方案不完整，遗漏了重要方面")

        # 基于问题复杂度的分析
        if problem.severity.value == "error":
            causes.append("问题复杂度过高，超出AI处理能力")

        # 基于修复建议的分析
        if not suggestion.suggested_code or len(suggestion.suggested_code.strip()) == 0:
            causes.append("AI未能生成有效的修复代码")

        return causes if causes else ["unknown_cause"]

    def _extract_learnings(
        self, failure_patterns: List[str], root_causes: List[str]
    ) -> List[str]:
        """提取学习要点"""
        learnings = []

        for pattern in failure_patterns:
            if pattern == "syntax_error":
                learnings.append("需要增强AI代码生成后的语法验证")
            elif pattern == "logic_error":
                learnings.append("需要改进AI对问题逻辑的理解能力")
            elif pattern == "regression":
                learnings.append("需要加强修复方案的副作用分析")

        for cause in root_causes:
            if "复杂" in cause:
                learnings.append("对于复杂问题，可能需要分解处理或人工介入")
            elif "理解" in cause:
                learnings.append("需要提供更多上下文信息给AI")

        return learnings if learnings else ["需要进一步分析失败原因"]

    def _recommend_adjustments(
        self, failure_patterns: List[str], root_causes: List[str], learnings: List[str]
    ) -> Dict[str, Any]:
        """推荐调整方案"""
        adjustments = {
            "strategy": ReanalysisStrategy.ALTERNATIVE_APPROACH.value,
            "context_enhancement": [],
            "parameter_adjustments": {},
            "quality_checks": [],
        }

        # 基于失败模式调整策略
        if "syntax_error" in failure_patterns:
            adjustments["strategy"] = ReanalysisStrategy.MORE_CONTEXT.value
            adjustments["context_enhancement"].append("add_surrounding_code")
            adjustments["quality_checks"].append("syntax_validation")

        if "logic_error" in failure_patterns:
            adjustments["strategy"] = ReanalysisStrategy.DIFFERENT_AI_MODEL.value
            adjustments["parameter_adjustments"]["temperature"] = 0.1
            adjustments["context_enhancement"].append("add_detailed_requirements")

        if "regression" in failure_patterns:
            adjustments["strategy"] = ReanalysisStrategy.HUMAN_INTERVENTION.value
            adjustments["quality_checks"].append("comprehensive_testing")

        # 基于根本原因调整
        for cause in root_causes:
            if "复杂" in cause:
                adjustments["strategy"] = ReanalysisStrategy.MORE_CONTEXT.value
                adjustments["context_enhancement"].append("break_down_problem")

        return adjustments

    def _calculate_analysis_confidence(
        self,
        failure_patterns: List[str],
        root_causes: List[str],
        verification_results: Optional[Dict[str, Any]],
    ) -> float:
        """计算分析置信度"""
        base_confidence = 0.5

        # 基于失败模式的置信度调整
        if len(failure_patterns) > 0 and "unknown" not in failure_patterns[0]:
            base_confidence += 0.2

        # 基于根本原因的置信度调整
        if len(root_causes) > 0 and "unknown" not in root_causes[0]:
            base_confidence += 0.2

        # 基于验证结果的置信度调整
        if verification_results:
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def _get_previous_attempts(
        self, session: WorkflowSession, issue_id: str
    ) -> List[Dict[str, Any]]:
        """获取历史尝试记录"""
        if not hasattr(session, "reanalysis_history"):
            return []

        history = session.reanalysis_history.get(issue_id, {})
        return history.get("attempts", [])

    def _adjust_analysis_strategy(
        self,
        failure_analysis: FailureAnalysis,
        previous_attempts: List[Dict[str, Any]],
        retry_count: int,
    ) -> Dict[str, Any]:
        """调整分析策略"""
        base_strategy = failure_analysis.recommended_adjustments.copy()

        # 基于重试次数调整
        if retry_count >= 2:
            base_strategy["strategy"] = ReanalysisStrategy.HUMAN_INTERVENTION.value
            base_strategy["escalation_required"] = True

        # 基于历史尝试调整
        if previous_attempts:
            used_strategies = [attempt.get("strategy") for attempt in previous_attempts]
            if base_strategy["strategy"] in used_strategies:
                # 尝试不同的策略
                if ReanalysisStrategy.MORE_CONTEXT.value not in used_strategies:
                    base_strategy["strategy"] = ReanalysisStrategy.MORE_CONTEXT.value
                elif ReanalysisStrategy.DIFFERENT_AI_MODEL.value not in used_strategies:
                    base_strategy["strategy"] = (
                        ReanalysisStrategy.DIFFERENT_AI_MODEL.value
                    )
                else:
                    base_strategy["strategy"] = (
                        ReanalysisStrategy.HUMAN_INTERVENTION.value
                    )

        # 添加重试计数信息
        base_strategy["retry_count"] = retry_count
        base_strategy["max_retries"] = self.max_retry_attempts

        return base_strategy

    def _create_reanalysis_context(
        self,
        session_id: str,
        issue_id: str,
        failed_suggestion_id: str,
        failure_reason: str,
        failure_analysis: FailureAnalysis,
        previous_attempts: List[Dict[str, Any]],
        adjusted_strategy: Dict[str, Any],
        retry_count: int,
    ) -> ReanalysisContext:
        """创建重新分析上下文"""
        return ReanalysisContext(
            reanalysis_id=str(uuid.uuid4()),
            session_id=session_id,
            original_issue_id=issue_id,
            failed_suggestion_id=failed_suggestion_id,
            failure_reason=failure_reason,
            failure_analysis=failure_analysis.to_dict(),
            previous_attempts=previous_attempts,
            adjusted_strategy=adjusted_strategy,
            reanalysis_timestamp=datetime.now(),
            retry_count=retry_count,
        )

    def _save_reanalysis_context(self, context: ReanalysisContext) -> None:
        """保存重新分析上下文"""
        try:
            context_file = (
                self.reanalysis_dir
                / f"reanalysis_{context.session_id}_{context.original_issue_id}_{context.retry_count}.json"
            )

            with open(context_file, "w", encoding="utf-8") as f:
                json.dump(context.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"重新分析上下文已保存: {context.reanalysis_id}")

        except Exception as e:
            self.logger.error(f"保存重新分析上下文失败: {e}")

    def _update_session_for_reanalysis(
        self, session: WorkflowSession, context: ReanalysisContext
    ) -> None:
        """更新会话状态以支持重新分析"""
        # 初始化重新分析历史
        if not hasattr(session, "reanalysis_history"):
            session.reanalysis_history = {}

        # 更新特定问题的历史
        if context.original_issue_id not in session.reanalysis_history:
            session.reanalysis_history[context.original_issue_id] = {
                "retry_count": 0,
                "attempts": [],
                "last_reanalysis": None,
            }

        history = session.reanalysis_history[context.original_issue_id]
        history["retry_count"] = context.retry_count
        history["last_reanalysis"] = context.reanalysis_id
        history["attempts"].append(
            {
                "reanalysis_id": context.reanalysis_id,
                "timestamp": context.reanalysis_timestamp.isoformat(),
                "strategy": context.adjusted_strategy.get("strategy"),
                "failure_reason": context.failure_reason,
            }
        )

        # 保存会话状态
        self.state_manager.save_session(session)

    def _handle_max_retries_exceeded(
        self, session: WorkflowSession, issue_id: str
    ) -> Dict[str, Any]:
        """处理超过最大重试次数的情况"""
        try:
            # 标记问题为需要人工干预
            session.problem_processing_status[issue_id] = "requires_human_intervention"
            self.state_manager.save_session(session)

            # 转换到节点L（检查剩余问题）
            self.state_manager.transition_to(
                session.session_id,
                WorkflowNode.CHECK_REMAINING,
                f"问题 {issue_id} 超过最大重试次数，需要人工干预",
            )

            return {
                "success": False,
                "max_retries_exceeded": True,
                "issue_id": issue_id,
                "next_node": "CHECK_REMAINING",
                "message": f"问题 {issue_id} 已达到最大重试次数，需要人工干预",
            }

        except Exception as e:
            self.logger.error(f"处理最大重试次数超限失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "处理最大重试次数超限失败",
            }

    def get_reanalysis_history(
        self, session_id: str, issue_id: str = None
    ) -> Dict[str, Any]:
        """
        获取重新分析历史

        Args:
            session_id: 会话ID
            issue_id: 问题ID（可选）

        Returns:
            Dict[str, Any]: 重新分析历史
        """
        try:
            session = self.state_manager.get_session(session_id)
            if not session:
                return {"error": f"会话不存在: {session_id}"}

            if not hasattr(session, "reanalysis_history"):
                return {"message": "无重新分析历史"}

            if issue_id:
                # 返回特定问题的历史
                return session.reanalysis_history.get(
                    issue_id, {"message": "该问题无重新分析历史"}
                )
            else:
                # 返回所有问题的历史
                return session.reanalysis_history

        except Exception as e:
            self.logger.error(f"获取重新分析历史失败: {e}")
            return {"error": str(e)}
