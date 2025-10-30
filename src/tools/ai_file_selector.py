"""
AI文件选择执行器 - T005.2
调用AI模型智能选择需要分析的核心文件
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import threading

from ..utils.logger import get_logger
try:
    from ..prompts.ai_file_selection_prompt_builder import AIFileSelectionPromptBuilder, FileSelectionCriteria
    from ..llm.unified_llm_client import UnifiedLLMClient
except ImportError:
    # 如果相关模块不可用，使用基本导入
    try:
        from ..prompts.ai_file_selection_prompt_builder import AIFileSelectionPromptBuilder, FileSelectionCriteria
    except ImportError:
        class AIFileSelectionPromptBuilder:
            def __init__(self, *args, **kwargs):
                pass

        class FileSelectionCriteria:
            def __init__(self, *args, **kwargs):
                pass

    try:
        from ..llm.unified_llm_client import UnifiedLLMClient
    except ImportError:
        # 如果unified_llm_client不可用，创建一个模拟客户端
        class UnifiedLLMClient:
            def __init__(self, *args, **kwargs):
                pass

            def chat_completion(self, *args, **kwargs):
                return {"content": '{"selected_files": []}', "success": True}


@dataclass
class FileSelectionResult:
    """文件选择结果"""
    file_path: str
    priority: str  # high, medium, low
    reason: str
    confidence: float  # 0.0-1.0
    key_issues: List[str] = field(default_factory=list)
    selection_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "priority": self.priority,
            "reason": self.reason,
            "confidence": self.confidence,
            "key_issues": self.key_issues,
            "selection_score": self.selection_score
        }


@dataclass
class AIFileSelectionResult:
    """AI文件选择执行结果"""
    selected_files: List[FileSelectionResult] = field(default_factory=list)
    selection_summary: Dict[str, Any] = field(default_factory=dict)
    execution_success: bool = True
    execution_time: float = 0.0
    error_message: str = ""
    ai_response_raw: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)
    execution_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "selected_files": [file.to_dict() for file in self.selected_files],
            "selection_summary": self.selection_summary,
            "execution_success": self.execution_success,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "ai_response_raw": self.ai_response_raw,
            "token_usage": self.token_usage,
            "execution_timestamp": self.execution_timestamp,
            "total_selected": len(self.selected_files)
        }


@dataclass
class SelectionStatistics:
    """选择统计信息"""
    total_selected: int = 0
    high_priority_count: int = 0
    medium_priority_count: int = 0
    low_priority_count: int = 0
    average_confidence: float = 0.0
    language_distribution: Dict[str, int] = field(default_factory=dict)
    reason_categories: Dict[str, int] = field(default_factory=dict)


class AIFileSelector:
    """AI文件选择执行器"""

    def __init__(self,
                 llm_client: Optional[Any] = None,
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        self.llm_client = llm_client
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = get_logger()

        # 初始化组件
        self.prompt_builder = AIFileSelectionPromptBuilder()

        # 优先级权重
        self.priority_weights = {
            "high": 3.0,
            "medium": 2.0,
            "low": 1.0
        }

    def select_files(self,
                    project_report: Dict[str, Any],
                    criteria: Optional[FileSelectionCriteria] = None,
                    user_requirements: Optional[str] = None) -> AIFileSelectionResult:
        """
        执行AI文件选择

        Args:
            project_report: 项目分析报告
            criteria: 文件选择标准
            user_requirements: 用户特定需求

        Returns:
            AIFileSelectionResult: AI选择结果
        """
        start_time = time.time()
        self.logger.info("开始执行AI文件选择")

        result = AIFileSelectionResult(
            execution_timestamp=datetime.now().isoformat()
        )

        try:
            # 构建提示词
            prompt = self.prompt_builder.build_prompt(
                project_report, criteria, user_requirements
            )

            # 如果token过多，优化提示词
            if prompt.token_estimate > 4000:
                self.logger.info(f"提示词token数过多({prompt.token_estimate})，进行优化")
                prompt = self.prompt_builder.optimize_prompt_for_tokens(prompt, 3500)

            # 调用AI模型
            ai_response = self._call_ai_with_retry(prompt)

            if not ai_response.get("success", False):
                result.execution_success = False
                result.error_message = ai_response.get("error_message", "AI调用失败")
                return result

            # 解析AI响应
            ai_content = ai_response.get("content", "")
            result.ai_response_raw = ai_content
            result.token_usage = ai_response.get("token_usage", {})

            # 解析选择结果
            selection_data = self._parse_ai_response(ai_content)
            if selection_data is None:
                result.execution_success = False
                result.error_message = "AI响应格式解析失败"
                return result

            # 处理选择结果
            selected_files = selection_data.get("selected_files", [])
            result.selected_files = self._process_selected_files(selected_files)

            # 生成选择摘要
            result.selection_summary = self._generate_selection_summary(
                result.selected_files, selection_data.get("selection_summary", {})
            )

            # 计算执行时间
            result.execution_time = time.time() - start_time

            self.logger.info(
                f"AI文件选择完成: 选择了 {len(result.selected_files)} 个文件, "
                f"耗时 {result.execution_time:.2f}秒"
            )

        except Exception as e:
            result.execution_success = False
            result.error_message = f"AI文件选择执行失败: {e}"
            result.execution_time = time.time() - start_time
            self.logger.error(result.error_message)

        return result

    def _call_ai_with_retry(self, prompt) -> Dict[str, Any]:
        """带重试的AI调用"""
        last_error = ""

        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"调用AI模型，尝试 {attempt + 1}/{self.max_retries}")

                if self.llm_client is None:
                    # 如果没有提供LLM客户端，尝试创建默认客户端
                    self.llm_client = self._create_default_llm_client()

                # 准备调用参数
                call_params = {
                    "messages": [
                        {"role": "system", "content": prompt.system_prompt},
                        {"role": "user", "content": prompt.user_prompt}
                    ],
                    "temperature": 0.3,  # 较低温度以获得更一致的结果
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"}  # 强制JSON响应
                }

                # 调用AI
                response = self.llm_client.chat_completion(**call_params)

                if response.get("success", False):
                    self.logger.info("AI调用成功")
                    return response
                else:
                    last_error = response.get("error_message", "未知错误")
                    self.logger.warning(f"AI调用失败: {last_error}")

            except Exception as e:
                last_error = str(e)
                self.logger.error(f"AI调用异常 (尝试 {attempt + 1}): {e}")

            # 如果不是最后一次尝试，等待重试
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (2 ** attempt))  # 指数退避

        self.logger.error(f"AI调用最终失败: {last_error}")
        return {
            "success": False,
            "error_message": f"AI调用失败，已重试 {self.max_retries} 次: {last_error}"
        }

    def _create_default_llm_client(self):
        """创建默认LLM客户端"""
        try:
            from ..llm.unified_llm_client import UnifiedLLMClient
            return UnifiedLLMClient()
        except Exception as e:
            self.logger.error(f"无法创建默认LLM客户端: {e}")
            raise

    def _parse_ai_response(self, ai_content: str) -> Optional[Dict[str, Any]]:
        """
        解析AI响应

        Args:
            ai_content: AI返回的内容

        Returns:
            Optional[Dict[str, Any]]: 解析后的数据
        """
        try:
            # 尝试直接解析JSON
            parsed_data = json.loads(ai_content)
            return self._validate_and_normalize_response(parsed_data)

        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            json_content = self._extract_json_from_response(ai_content)
            if json_content:
                try:
                    parsed_data = json.loads(json_content)
                    return self._validate_and_normalize_response(parsed_data)
                except json.JSONDecodeError as e:
                    self.logger.error(f"提取的JSON解析失败: {e}")

            self.logger.error("无法解析AI响应为JSON格式")
            return None

    def _extract_json_from_response(self, content: str) -> Optional[str]:
        """从响应中提取JSON内容"""
        import re

        # 尝试匹配JSON对象
        json_pattern = r'\{.*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)

        if matches:
            # 选择最长的匹配（通常是最完整的JSON）
            longest_match = max(matches, key=len)

            # 尝试验证是否为有效JSON
            try:
                json.loads(longest_match)
                return longest_match
            except json.JSONDecodeError:
                pass

        return None

    def _validate_and_normalize_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证和标准化响应数据"""
        normalized = {
            "selected_files": [],
            "selection_summary": {}
        }

        # 处理选择的文件
        selected_files = data.get("selected_files", [])
        if not isinstance(selected_files, list):
            self.logger.warning("selected_files不是列表格式")
            return normalized

        for file_data in selected_files:
            if not isinstance(file_data, dict):
                continue

            normalized_file = {
                "file_path": file_data.get("file_path", ""),
                "priority": file_data.get("priority", "medium"),
                "reason": file_data.get("reason", ""),
                "confidence": float(file_data.get("confidence", 0.5)),
                "key_issues": file_data.get("key_issues", [])
            }

            # 验证必需字段
            if not normalized_file["file_path"]:
                continue

            # 验证优先级
            if normalized_file["priority"] not in ["high", "medium", "low"]:
                normalized_file["priority"] = "medium"

            # 验证置信度范围
            normalized_file["confidence"] = max(0.0, min(1.0, normalized_file["confidence"]))

            normalized["selected_files"].append(normalized_file)

        # 处理选择摘要
        selection_summary = data.get("selection_summary", {})
        if isinstance(selection_summary, dict):
            normalized["selection_summary"] = {
                "total_selected": selection_summary.get("total_selected", len(normalized["selected_files"])),
                "selection_criteria_met": selection_summary.get("selection_criteria_met", True),
                "additional_notes": selection_summary.get("additional_notes", "")
            }
        else:
            normalized["selection_summary"] = {
                "total_selected": len(normalized["selected_files"]),
                "selection_criteria_met": True,
                "additional_notes": ""
            }

        return normalized

    def _process_selected_files(self, selected_files: List[Dict[str, Any]]) -> List[FileSelectionResult]:
        """处理选择的文件"""
        processed_files = []

        for file_data in selected_files:
            # 计算选择分数
            selection_score = self._calculate_selection_score(file_data)

            result = FileSelectionResult(
                file_path=file_data["file_path"],
                priority=file_data["priority"],
                reason=file_data["reason"],
                confidence=file_data["confidence"],
                key_issues=file_data.get("key_issues", []),
                selection_score=selection_score
            )

            processed_files.append(result)

        # 按选择分数排序
        processed_files.sort(key=lambda x: x.selection_score, reverse=True)

        return processed_files

    def _calculate_selection_score(self, file_data: Dict[str, Any]) -> float:
        """计算文件选择分数"""
        score = 0.0

        # 基于优先级的分数
        priority = file_data.get("priority", "medium")
        score += self.priority_weights.get(priority, 2.0)

        # 基于置信度的分数
        confidence = file_data.get("confidence", 0.5)
        score += confidence * 2.0

        # 基于关键问题数量的分数
        key_issues = file_data.get("key_issues", [])
        score += len(key_issues) * 0.5

        # 基于理由详细程度的分数
        reason = file_data.get("reason", "")
        reason_score = min(len(reason) / 50, 2.0)  # 最多2分
        score += reason_score

        return round(score, 2)

    def _generate_selection_summary(self,
                                  selected_files: List[FileSelectionResult],
                                  ai_summary: Dict[str, Any]) -> Dict[str, Any]:
        """生成选择摘要"""
        statistics = self._calculate_selection_statistics(selected_files)

        summary = {
            "total_selected": len(selected_files),
            "priority_distribution": {
                "high": statistics.high_priority_count,
                "medium": statistics.medium_priority_count,
                "low": statistics.low_priority_count
            },
            "average_confidence": round(statistics.average_confidence, 2),
            "average_selection_score": round(
                sum(f.selection_score for f in selected_files) / len(selected_files), 2
            ) if selected_files else 0.0,
            "language_distribution": statistics.language_distribution,
            "reason_categories": statistics.reason_categories,
            "top_selected_files": [
                {
                    "file_path": f.file_path,
                    "selection_score": f.selection_score,
                    "priority": f.priority,
                    "reason": f.reason[:100] + "..." if len(f.reason) > 100 else f.reason
                }
                for f in selected_files[:5]
            ],
            "ai_summary": ai_summary
        }

        return summary

    def _calculate_selection_statistics(self, selected_files: List[FileSelectionResult]) -> SelectionStatistics:
        """计算选择统计信息"""
        stats = SelectionStatistics()

        if not selected_files:
            return stats

        stats.total_selected = len(selected_files)

        # 统计优先级分布
        for file_result in selected_files:
            if file_result.priority == "high":
                stats.high_priority_count += 1
            elif file_result.priority == "medium":
                stats.medium_priority_count += 1
            else:
                stats.low_priority_count += 1

        # 计算平均置信度
        total_confidence = sum(f.confidence for f in selected_files)
        stats.average_confidence = total_confidence / len(selected_files)

        # 统计语言分布（从文件路径推断）
        language_extensions = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".go": "Go",
            ".cpp": "C++",
            ".c": "C",
            ".cs": "C#",
            ".rs": "Rust",
            ".php": "PHP",
            ".rb": "Ruby"
        }

        for file_result in selected_files:
            import os
            _, ext = os.path.splitext(file_result.file_path)
            language = language_extensions.get(ext.lower(), "Other")
            stats.language_distribution[language] = stats.language_distribution.get(language, 0) + 1

        # 统计理由类别
        reason_keywords = {
            "security": ["安全", "漏洞", "风险", "security", "vulnerability"],
            "performance": ["性能", "效率", "缓慢", "performance", "efficiency"],
            "quality": ["质量", "规范", "标准", "quality", "standard"],
            "complexity": ["复杂", "难度", "维护", "complexity", "maintenance"],
            "importance": ["重要", "核心", "关键", "important", "core", "critical"]
        }

        for file_result in selected_files:
            reason_lower = file_result.reason.lower()
            categorized = False

            for category, keywords in reason_keywords.items():
                if any(keyword in reason_lower for keyword in keywords):
                    stats.reason_categories[category] = stats.reason_categories.get(category, 0) + 1
                    categorized = True
                    break

            if not categorized:
                stats.reason_categories["other"] = stats.reason_categories.get("other", 0) + 1

        return stats

    def validate_selection_result(self,
                                 result: AIFileSelectionResult,
                                 criteria: FileSelectionCriteria) -> Dict[str, Any]:
        """
        验证选择结果

        Args:
            result: AI选择结果
            criteria: 选择标准

        Returns:
            Dict[str, Any]: 验证结果
        """
        validation = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "metrics": {}
        }

        # 检查执行成功
        if not result.execution_success:
            validation["is_valid"] = False
            validation["errors"].append(f"执行失败: {result.error_message}")
            return validation

        selected_files = result.selected_files

        # 检查文件数量
        if len(selected_files) == 0:
            validation["is_valid"] = False
            validation["errors"].append("没有选择任何文件")
        elif len(selected_files) > criteria.max_files:
            validation["warnings"].append(
                f"选择的文件数量({len(selected_files)})超过限制({criteria.max_files})"
            )

        # 检查文件路径有效性
        invalid_files = []
        for file_result in selected_files:
            if not file_result.file_path or not isinstance(file_result.file_path, str):
                invalid_files.append(file_result.file_path)

        if invalid_files:
            validation["warnings"].append(f"发现 {len(invalid_files)} 个无效文件路径")

        # 检查置信度分布
        low_confidence_files = [f for f in selected_files if f.confidence < 0.5]
        if len(low_confidence_files) > len(selected_files) * 0.5:
            validation["warnings"].append(
                f"超过50%的文件选择置信度较低({len(low_confidence_files)}/{len(selected_files)})"
            )

        # 计算指标
        validation["metrics"] = {
            "total_files": len(selected_files),
            "avg_confidence": round(sum(f.confidence for f in selected_files) / len(selected_files), 2) if selected_files else 0,
            "high_priority_ratio": round(
                len([f for f in selected_files if f.priority == "high"]) / len(selected_files), 2
            ) if selected_files else 0,
            "avg_selection_score": round(
                sum(f.selection_score for f in selected_files) / len(selected_files), 2
            ) if selected_files else 0
        }

        return validation


# 便捷函数
def select_files_with_ai(project_report: Dict[str, Any],
                        max_files: int = 20,
                        preferred_languages: List[str] = None,
                        focus_categories: List[str] = None,
                        user_requirements: str = None,
                        llm_client: Any = None) -> Dict[str, Any]:
    """
    便捷的AI文件选择函数

    Args:
        project_report: 项目分析报告
        max_files: 最大文件选择数量
        preferred_languages: 优先编程语言
        focus_categories: 关注问题类型
        user_requirements: 用户特殊需求
        llm_client: LLM客户端实例

    Returns:
        Dict[str, Any]: 选择结果和验证信息
    """
    criteria = FileSelectionCriteria(
        max_files=max_files,
        preferred_languages=preferred_languages or [],
        focus_categories=focus_categories or []
    )

    selector = AIFileSelector(llm_client)
    result = selector.select_files(project_report, criteria, user_requirements)
    validation = selector.validate_selection_result(result, criteria)

    return {
        "selection_result": result.to_dict(),
        "validation": validation
    }