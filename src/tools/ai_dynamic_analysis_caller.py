#!/usr/bin/env python3
"""
AI动态分析调用器 - T014.2
调用AI对修复效果进行深度分析和验证
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..llm.client import LLMClient
from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from .project_analysis_types import StaticAnalysisResult
from .verification_static_analyzer import FixComparison, StaticVerificationReport
from .workflow_data_types import AIFixSuggestion
from .workflow_flow_state_manager import WorkflowSession

logger = get_logger()


@dataclass
class AIDynamicAnalysisContext:
    """AI动态分析上下文"""

    context_id: str
    session_id: str
    suggestion_id: str
    file_path: str
    original_problem: Dict[str, Any]
    fix_suggestion: Dict[str, Any]
    static_verification: Dict[str, Any]
    before_after_code: Dict[str, str]  # 修复前后的代码
    analysis_focus: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "context_id": self.context_id,
            "session_id": self.session_id,
            "suggestion_id": self.suggestion_id,
            "file_path": self.file_path,
            "original_problem": self.original_problem,
            "fix_suggestion": self.fix_suggestion,
            "static_verification": self.static_verification,
            "before_after_code": self.before_after_code,
            "analysis_focus": self.analysis_focus,
        }


@dataclass
class AIDynamicAnalysisResult:
    """AI动态分析结果"""

    analysis_id: str
    context_id: str
    analysis_timestamp: datetime
    fix_effectiveness_score: float  # 修复有效性分数 (0-1)
    problem_resolution_status: (
        str  # 问题解决状态 (fully_resolved, partially_resolved, not_resolved)
    )
    new_issues_detected: List[Dict[str, Any]]  # 新发现的问题
    code_quality_impact: Dict[str, Any]  # 代码质量影响分析
    side_effects_analysis: Dict[str, Any]  # 副作用分析
    recommendations: List[str]  # 建议
    confidence_score: float  # 置信度分数
    reasoning: str  # 分析推理过程

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "analysis_id": self.analysis_id,
            "context_id": self.context_id,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "fix_effectiveness_score": self.fix_effectiveness_score,
            "problem_resolution_status": self.problem_resolution_status,
            "new_issues_detected": self.new_issues_detected,
            "code_quality_impact": self.code_quality_impact,
            "side_effects_analysis": self.side_effects_analysis,
            "recommendations": self.recommendations,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
        }


class ProblemResolutionStatus(Enum):
    """问题解决状态"""

    FULLY_RESOLVED = "fully_resolved"  # 完全解决
    PARTIALLY_RESOLVED = "partially_resolved"  # 部分解决
    NOT_RESOLVED = "not_resolved"  # 未解决
    REGRESSED = "regressed"  # 出现回退


class AIDynamicAnalysisCaller:
    """AI动态分析调用器 - T014.2

    工作流位置: 节点H核心，将修复后的代码返回AI进行动态分析
    核心功能: 调用AI对修复效果进行深度分析和验证
    AI集成: 利用AI的智能分析能力验证修复效果
    """

    def __init__(self, config_manager=None):
        """初始化AI动态分析调用器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        self.config = self.config_manager.get("project_analysis", {})
        self.llm_config = self.config.get("ai_analysis", {})

        # 初始化LLM客户端
        self.llm_client = LLMClient()

        # 分析结果存储目录
        self.analysis_dir = Path(
            self.config.get("ai_analysis_dir", ".fix_backups/ai_analysis")
        )
        self.analysis_dir.mkdir(parents=True, exist_ok=True)

        # 预设的分析重点
        self.default_analysis_focus = [
            "correctness",  # 正确性
            "performance",  # 性能
            "security",  # 安全性
            "maintainability",  # 可维护性
            "side_effects",  # 副作用
        ]

    def perform_ai_dynamic_analysis(
        self,
        session_id: str,
        suggestion_id: str,
        original_problem: Dict[str, Any],
        fix_suggestion: Dict[str, Any],
        static_verification_report: StaticVerificationReport,
        before_code: str,
        after_code: str,
        custom_focus: Optional[List[str]] = None,
    ) -> AIDynamicAnalysisResult:
        """
        执行AI动态分析

        Args:
            session_id: 会话ID
            suggestion_id: 修复建议ID
            original_problem: 原始问题信息
            fix_suggestion: 修复建议信息
            static_verification_report: 静态验证报告
            before_code: 修复前代码
            after_code: 修复后代码
            custom_focus: 自定义分析重点

        Returns:
            AIDynamicAnalysisResult: AI动态分析结果
        """
        try:
            self.logger.info(f"开始AI动态分析: 会话={session_id}, 建议={suggestion_id}")

            # 1. 构建分析上下文
            context = self._build_analysis_context(
                session_id=session_id,
                suggestion_id=suggestion_id,
                original_problem=original_problem,
                fix_suggestion=fix_suggestion,
                static_verification_report=static_verification_report,
                before_code=before_code,
                after_code=after_code,
                custom_focus=custom_focus,
            )

            # 2. 构建AI分析提示词
            prompt = self._build_dynamic_analysis_prompt(context)

            # 3. 调用AI执行分析
            ai_response = self._call_ai_for_analysis(prompt)

            # 4. 解析AI响应
            analysis_result = self._parse_ai_response(ai_response, context)

            # 5. 验证分析结果
            validated_result = self._validate_analysis_result(analysis_result, context)

            # 6. 保存分析结果
            self._save_analysis_result(validated_result)

            self.logger.info(
                f"AI动态分析完成: 有效性={validated_result.fix_effectiveness_score:.2f}"
            )
            return validated_result

        except Exception as e:
            self.logger.error(f"AI动态分析失败: {e}")
            # 返回失败结果
            return self._create_failure_result(session_id, suggestion_id, str(e))

    def _build_analysis_context(
        self,
        session_id: str,
        suggestion_id: str,
        original_problem: Dict[str, Any],
        fix_suggestion: Dict[str, Any],
        static_verification_report: StaticVerificationReport,
        before_code: str,
        after_code: str,
        custom_focus: Optional[List[str]],
    ) -> AIDynamicAnalysisContext:
        """构建AI动态分析上下文"""
        context_id = str(uuid.uuid4())
        analysis_focus = custom_focus or self.default_analysis_focus

        # 准备静态验证数据
        static_verification_data = {
            "success_rate": static_verification_report.success_rate,
            "new_issues_count": static_verification_report.new_issues_count,
            "fixed_issues": static_verification_report.fix_comparison.fixed_issues,
            "remaining_issues": static_verification_report.fix_comparison.remaining_issues,
            "overall_quality_score": static_verification_report.overall_quality_score,
        }

        return AIDynamicAnalysisContext(
            context_id=context_id,
            session_id=session_id,
            suggestion_id=suggestion_id,
            file_path=fix_suggestion.get("file_path", ""),
            original_problem=original_problem,
            fix_suggestion=fix_suggestion,
            static_verification=static_verification_data,
            before_after_code={"before": before_code, "after": after_code},
            analysis_focus=analysis_focus,
        )

    def _build_dynamic_analysis_prompt(self, context: AIDynamicAnalysisContext) -> str:
        """构建AI动态分析提示词"""
        prompt = f"""
你是一个专业的代码质量分析师。请对以下代码修复进行深度动态分析验证。

## 分析任务
分析修复后的代码效果，评估修复的有效性、安全性、性能影响和潜在的副作用。

## 原始问题信息
- 文件: {context.file_path}
- 问题类型: {context.original_problem.get('issue_type', 'unknown')}
- 严重程度: {context.original_problem.get('severity', 'unknown')}
- 问题描述: {context.original_problem.get('description', 'No description')}
- 代码位置: 第{context.original_problem.get('line', 'unknown')}行

## 修复建议
- 修复代码: {context.fix_suggestion.get('suggested_code', 'No code provided')}
- 修复说明: {context.fix_suggestion.get('explanation', 'No explanation')}
- 修复推理: {context.fix_suggestion.get('reasoning', 'No reasoning')}

## 修复前后代码对比
```diff
{self._generate_diff(context.before_after_code['before'], context.before_after_code['after'])}
```

## 静态分析验证结果
- 修复成功率: {context.static_verification['success_rate']:.2%}
- 新问题数量: {context.static_verification['new_issues_count']}
- 整体质量分数: {context.static_verification['overall_quality_score']:.2f}
- 已修复问题: {len(context.static_verification['fixed_issues'])}个
- 仍存在问题: {len(context.static_verification['remaining_issues'])}个

## 分析重点
{', '.join(context.analysis_focus)}

## 输出要求
请以JSON格式返回分析结果，包含以下字段：

{{
  "fix_effectiveness_score": 0.95,  // 修复有效性分数 (0-1)
  "problem_resolution_status": "fully_resolved",  // 问题解决状态
  "new_issues_detected": [        // 新发现的问题列表
    {{
      "issue_type": "performance",
      "severity": "medium",
      "description": "修复引入了轻微的性能开销",
      "location": "line 45-47",
      "confidence": 0.8
    }}
  ],
  "code_quality_impact": {{
    "readability": "improved",     // 可读性影响
    "maintainability": "improved", // 可维护性影响
    "complexity": "reduced",       // 复杂度影响
    "documentation": "unchanged"   // 文档影响
  }},
  "side_effects_analysis": {{
    "potential_breaking_changes": false,
    "affected_components": ["user_service"],
    "performance_impact": "minimal",
    "security_implications": "none"
  }},
  "recommendations": [            // 改进建议
    "建议添加单元测试验证修复效果",
    "考虑添加错误处理逻辑"
  ],
  "confidence_score": 0.9,        // 分析置信度
  "reasoning": "详细的推理分析过程..." // 分析推理过程
}}

问题解决状态可选值: "fully_resolved", "partially_resolved", "not_resolved", "regressed"

请进行深入分析，给出客观、准确的评估结果。
"""
        return prompt

    def _generate_diff(self, before_code: str, after_code: str) -> str:
        """生成代码差异"""
        try:
            # 简单的差异生成逻辑
            before_lines = before_code.split("\n")
            after_lines = after_code.split("\n")

            diff_lines = []
            max_lines = max(len(before_lines), len(after_lines))

            for i in range(max_lines):
                before_line = before_lines[i] if i < len(before_lines) else ""
                after_line = after_lines[i] if i < len(after_lines) else ""

                if before_line != after_line:
                    if before_line and after_line:
                        diff_lines.append(f"- {before_line}")
                        diff_lines.append(f"+ {after_line}")
                    elif before_line:
                        diff_lines.append(f"- {before_line}")
                    elif after_line:
                        diff_lines.append(f"+ {after_line}")

            return "\n".join(diff_lines) if diff_lines else "无显著变化"

        except Exception as e:
            self.logger.warning(f"生成代码差异失败: {e}")
            return "无法生成差异"

    def _call_ai_for_analysis(self, prompt: str) -> str:
        """调用AI执行分析"""
        try:
            # 使用LLM客户端调用AI
            response = self.llm_client.generate_response(
                prompt=prompt, max_tokens=4000, temperature=0.3
            )
            return response

        except Exception as e:
            self.logger.error(f"调用AI分析失败: {e}")
            raise RuntimeError(f"AI分析调用失败: {e}")

    def _parse_ai_response(
        self, ai_response: str, context: AIDynamicAnalysisContext
    ) -> AIDynamicAnalysisResult:
        """解析AI响应"""
        try:
            # 尝试解析JSON响应
            if ai_response.strip().startswith("{"):
                response_data = json.loads(ai_response)
            else:
                # 如果不是纯JSON，尝试提取JSON部分
                start_idx = ai_response.find("{")
                end_idx = ai_response.rfind("}") + 1
                if start_idx != -1 and end_idx != -1:
                    json_str = ai_response[start_idx:end_idx]
                    response_data = json.loads(json_str)
                else:
                    raise ValueError("无法从AI响应中提取JSON数据")

            # 创建分析结果对象
            return AIDynamicAnalysisResult(
                analysis_id=str(uuid.uuid4()),
                context_id=context.context_id,
                analysis_timestamp=datetime.now(),
                fix_effectiveness_score=response_data.get(
                    "fix_effectiveness_score", 0.0
                ),
                problem_resolution_status=response_data.get(
                    "problem_resolution_status", "not_resolved"
                ),
                new_issues_detected=response_data.get("new_issues_detected", []),
                code_quality_impact=response_data.get("code_quality_impact", {}),
                side_effects_analysis=response_data.get("side_effects_analysis", {}),
                recommendations=response_data.get("recommendations", []),
                confidence_score=response_data.get("confidence_score", 0.0),
                reasoning=response_data.get("reasoning", "No reasoning provided"),
            )

        except json.JSONDecodeError as e:
            self.logger.error(f"解析AI响应JSON失败: {e}")
            # 创建基于文本分析的默认结果
            return self._create_fallback_result(context, ai_response)

        except Exception as e:
            self.logger.error(f"解析AI响应失败: {e}")
            raise

    def _create_fallback_result(
        self, context: AIDynamicAnalysisContext, ai_response: str
    ) -> AIDynamicAnalysisResult:
        """创建基于文本分析的后备结果"""
        # 简单的关键词分析
        effectiveness_score = 0.5  # 默认分数
        resolution_status = "partially_resolved"

        response_lower = ai_response.lower()
        if (
            "成功" in response_lower
            or "有效" in response_lower
            or "resolved" in response_lower
        ):
            effectiveness_score = 0.8
            resolution_status = "fully_resolved"
        elif (
            "失败" in response_lower
            or "无效" in response_lower
            or "not resolved" in response_lower
        ):
            effectiveness_score = 0.2
            resolution_status = "not_resolved"

        return AIDynamicAnalysisResult(
            analysis_id=str(uuid.uuid4()),
            context_id=context.context_id,
            analysis_timestamp=datetime.now(),
            fix_effectiveness_score=effectiveness_score,
            problem_resolution_status=resolution_status,
            new_issues_detected=[],
            code_quality_impact={},
            side_effects_analysis={},
            recommendations=["建议进行更详细的人工分析"],
            confidence_score=0.3,
            reasoning=f"基于AI响应文本的简化分析: {ai_response[:200]}...",
        )

    def _validate_analysis_result(
        self, result: AIDynamicAnalysisResult, context: AIDynamicAnalysisContext
    ) -> AIDynamicAnalysisResult:
        """验证分析结果"""
        # 验证分数范围
        result.fix_effectiveness_score = max(
            0.0, min(1.0, result.fix_effectiveness_score)
        )
        result.confidence_score = max(0.0, min(1.0, result.confidence_score))

        # 验证解决状态
        valid_statuses = [status.value for status in ProblemResolutionStatus]
        if result.problem_resolution_status not in valid_statuses:
            result.problem_resolution_status = "partially_resolved"

        # 验证新问题数据结构
        validated_new_issues = []
        for issue in result.new_issues_detected:
            if isinstance(issue, dict) and "description" in issue:
                validated_new_issues.append(issue)
        result.new_issues_detected = validated_new_issues

        return result

    def _save_analysis_result(self, result: AIDynamicAnalysisResult) -> None:
        """保存分析结果"""
        try:
            result_file = self.analysis_dir / f"ai_analysis_{result.context_id}.json"

            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"AI分析结果已保存: {result_file}")

        except Exception as e:
            self.logger.error(f"保存AI分析结果失败: {e}")

    def _create_failure_result(
        self, session_id: str, suggestion_id: str, error_message: str
    ) -> AIDynamicAnalysisResult:
        """创建失败结果"""
        return AIDynamicAnalysisResult(
            analysis_id=str(uuid.uuid4()),
            context_id=f"failure_{uuid.uuid4()}",
            analysis_timestamp=datetime.now(),
            fix_effectiveness_score=0.0,
            problem_resolution_status="not_resolved",
            new_issues_detected=[],
            code_quality_impact={},
            side_effects_analysis={},
            recommendations=[f"分析失败: {error_message}"],
            confidence_score=0.0,
            reasoning=f"AI动态分析执行失败: {error_message}",
        )

    def get_analysis_result(self, context_id: str) -> Optional[AIDynamicAnalysisResult]:
        """
        获取AI分析结果

        Args:
            context_id: 分析上下文ID

        Returns:
            Optional[AIDynamicAnalysisResult]: AI分析结果
        """
        try:
            result_file = self.analysis_dir / f"ai_analysis_{context_id}.json"

            if not result_file.exists():
                return None

            with open(result_file, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            # 重构分析结果对象
            return AIDynamicAnalysisResult(
                analysis_id=result_data["analysis_id"],
                context_id=result_data["context_id"],
                analysis_timestamp=datetime.fromisoformat(
                    result_data["analysis_timestamp"]
                ),
                fix_effectiveness_score=result_data["fix_effectiveness_score"],
                problem_resolution_status=result_data["problem_resolution_status"],
                new_issues_detected=result_data["new_issues_detected"],
                code_quality_impact=result_data["code_quality_impact"],
                side_effects_analysis=result_data["side_effects_analysis"],
                recommendations=result_data["recommendations"],
                confidence_score=result_data["confidence_score"],
                reasoning=result_data["reasoning"],
            )

        except Exception as e:
            self.logger.error(f"获取AI分析结果失败: {e}")
            return None

    def batch_analyze_fixes(
        self, analysis_tasks: List[Dict[str, Any]]
    ) -> List[AIDynamicAnalysisResult]:
        """
        批量执行AI动态分析

        Args:
            analysis_tasks: 分析任务列表

        Returns:
            List[AIDynamicAnalysisResult]: 分析结果列表
        """
        try:
            self.logger.info(f"开始批量AI动态分析: 任务数={len(analysis_tasks)}")

            results = []
            for task in analysis_tasks:
                try:
                    result = self.perform_ai_dynamic_analysis(**task)
                    results.append(result)

                except Exception as e:
                    self.logger.error(f"批量分析单个任务失败: {e}")
                    failure_result = self._create_failure_result(
                        task.get("session_id", "unknown"),
                        task.get("suggestion_id", "unknown"),
                        str(e),
                    )
                    results.append(failure_result)

            self.logger.info(f"批量AI动态分析完成: 成功={len(results)}")
            return results

        except Exception as e:
            self.logger.error(f"批量AI动态分析失败: {e}")
            return []
