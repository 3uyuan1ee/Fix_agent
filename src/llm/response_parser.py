"""
LLM API响应解析器
专门用于解析LLM返回的JSON格式分析结果
"""

import json
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum

from ..utils.logger import get_logger


class ParseResult(Enum):
    """解析结果状态"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class ParsedAnalysis:
    """解析后的分析结果"""
    status: ParseResult
    defects: List[Dict[str, Any]]
    summary: Dict[str, Any]
    raw_response: str
    parse_errors: List[str]
    metadata: Dict[str, Any]


class LLMResponseParser:
    """LLM响应解析器"""

    def __init__(self):
        """初始化解析器"""
        self.logger = get_logger()

    def parse_analysis_response(self, response: str) -> ParsedAnalysis:
        """
        解析LLM分析响应

        Args:
            response: LLM返回的原始响应

        Returns:
            解析后的分析结果
        """
        self.logger.debug("开始解析LLM分析响应")

        # 初始化结果
        result = ParsedAnalysis(
            status=ParseResult.FAILED,
            defects=[],
            summary={},
            raw_response=response,
            parse_errors=[],
            metadata={}
        )

        try:
            # 清理和预处理响应
            cleaned_response = self._clean_response(response)
            result.metadata["original_length"] = len(response)
            result.metadata["cleaned_length"] = len(cleaned_response)

            # 尝试多种解析策略
            parsed_data = self._try_multiple_parse_strategies(cleaned_response)

            if parsed_data:
                result.defects, result.summary = self._extract_defects_and_summary(parsed_data)
                result.status = ParseResult.SUCCESS
                self.logger.info(f"成功解析LLM响应，发现{len(result.defects)}个缺陷")

            else:
                # 尝试从文本中提取信息
                result.defects, result.summary = self._extract_from_text(cleaned_response)
                if result.defects:
                    result.status = ParseResult.PARTIAL
                    self.logger.warning(f"部分解析成功，从文本中提取到{len(result.defects)}个缺陷")
                else:
                    result.parse_errors.append("无法解析JSON格式，也未找到文本格式的缺陷信息")

        except Exception as e:
            error_msg = f"解析过程中发生错误: {str(e)}"
            self.logger.error(error_msg)
            result.parse_errors.append(error_msg)

        # 生成统计信息
        self._generate_statistics(result)

        return result

    def _clean_response(self, response: str) -> str:
        """
        清理响应文本

        Args:
            response: 原始响应

        Returns:
            清理后的响应
        """
        if not response:
            return ""

        # 移除多余的空白字符
        cleaned = response.strip()

        # 移除常见的LLM响应前缀/后缀
        prefixes_to_remove = [
            "以下是分析结果：",
            "分析结果如下：",
            "Here are the analysis results:",
            "The analysis results are:",
            "```json",
            "```",
            '"',
            "'"
        ]

        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()

        for suffix in prefixes_to_remove:
            if cleaned.endswith(suffix):
                cleaned = cleaned[:-len(suffix)].strip()

        return cleaned

    def _try_multiple_parse_strategies(self, response: str) -> Optional[Dict[str, Any]]:
        """
        尝试多种解析策略

        Args:
            response: 清理后的响应

        Returns:
            解析后的数据，如果失败返回None
        """
        strategies = [
            self._parse_direct_json,
            self._parse_nested_json,
            self._parse_partial_json,
            self._parse_markdown_json,
            self._parse_structured_text
        ]

        for i, strategy in enumerate(strategies):
            try:
                self.logger.debug(f"尝试解析策略 {i+1}/{len(strategies)}")
                result = strategy(response)
                if result:
                    self.logger.debug(f"策略 {i+1} 成功")
                    return result
            except Exception as e:
                self.logger.debug(f"策略 {i+1} 失败: {str(e)}")
                continue

        return None

    def _parse_direct_json(self, response: str) -> Optional[Dict[str, Any]]:
        """直接解析JSON"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return None

    def _parse_nested_json(self, response: str) -> Optional[Dict[str, Any]]:
        """解析嵌套JSON"""
        # 尝试找到JSON对象
        json_pattern = r'\{[\s\S]*\}'
        matches = re.findall(json_pattern, response)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        # 尝试找到JSON数组
        array_pattern = r'\[[\s\S]*\]'
        matches = re.findall(array_pattern, response)

        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue

        return None

    def _parse_partial_json(self, response: str) -> Optional[Dict[str, Any]]:
        """解析部分JSON（修复常见错误）"""
        # 尝试修复常见的JSON错误
        fixed_response = response

        # 修复缺少的逗号
        fixed_response = re.sub(r'}\s*{\s*', '}, {', fixed_response)
        fixed_response = re.sub(r']\s*\[\s*', '], [', fixed_response)

        # 修复缺少的引号
        fixed_response = re.sub(r'(\w+):', r'"\1":', fixed_response)

        # 移除注释（如果存在）
        fixed_response = re.sub(r'//.*?\n', '', fixed_response)
        fixed_response = re.sub(r'/\*.*?\*/', '', fixed_response, flags=re.DOTALL)

        try:
            return json.loads(fixed_response)
        except json.JSONDecodeError:
            return None

    def _parse_markdown_json(self, response: str) -> Optional[Dict[str, Any]]:
        """解析Markdown代码块中的JSON"""
        # 查找 ```json 和 ``` 之间的内容
        pattern = r'```(?:json)?\s*\n?([\s\S]*?)\n?```'
        matches = re.findall(pattern, response, re.IGNORECASE)

        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue

        return None

    def _parse_structured_text(self, response: str) -> Optional[Dict[str, Any]]:
        """解析结构化文本（转换为JSON格式）"""
        # 这里可以实现更复杂的文本解析逻辑
        # 目前返回None，表示不支持
        return None

    def _extract_defects_and_summary(self, data: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        从解析的数据中提取缺陷和摘要

        Args:
            data: 解析后的数据

        Returns:
            (缺陷列表, 摘要字典)
        """
        defects = []
        summary = {}

        # 尝试多种可能的字段名
        defects_fields = ["defects", "issues", "problems", "errors", "vulnerabilities"]
        summary_fields = ["summary", "overview", "stats", "statistics"]

        # 提取缺陷
        for field in defects_fields:
            if field in data and isinstance(data[field], list):
                defects = self._normalize_defects(data[field])
                break

        # 提取摘要
        for field in summary_fields:
            if field in data and isinstance(data[field], dict):
                summary = data[field]
                break

        # 如果没有找到摘要，尝试生成一个
        if not summary:
            summary = self._generate_summary(defects, data)

        return defects, summary

    def _normalize_defects(self, raw_defects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        标准化缺陷格式

        Args:
            raw_defects: 原始缺陷列表

        Returns:
            标准化后的缺陷列表
        """
        normalized = []

        for defect in raw_defects:
            if not isinstance(defect, dict):
                continue

            normalized_defect = {
                "id": defect.get("id", ""),
                "type": defect.get("type", defect.get("category", "unknown")),
                "severity": self._normalize_severity(defect.get("severity", "medium")),
                "title": defect.get("title", defect.get("name", defect.get("message", ""))),
                "description": defect.get("description", defect.get("details", "")),
                "location": self._normalize_location(defect.get("location", defect.get("position", {}))),
                "fix_suggestion": defect.get("fix_suggestion", defect.get("suggestion", defect.get("fix", ""))),
                "code_snippet": defect.get("code_snippet", defect.get("code", "")),
                "confidence": defect.get("confidence", "medium"),
                "cwe_id": defect.get("cwe_id", defect.get("cwe", "")),
                "cvss_score": defect.get("cvss_score", defect.get("cvss", None)),
                "metadata": {}
            }

            # 保留额外的字段作为元数据
            for key, value in defect.items():
                if key not in normalized_defect and key != "metadata":
                    normalized_defect["metadata"][key] = value

            normalized.append(normalized_defect)

        return normalized

    def _normalize_severity(self, severity: str) -> str:
        """标准化严重程度"""
        severity_mapping = {
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
            "info": "info",
            "information": "info",
            "warning": "medium",
            "error": "high",
            "danger": "critical",
            "安全": "high",
            "警告": "medium",
            "提示": "info"
        }

        return severity_mapping.get(severity.lower(), "medium")

    def _normalize_location(self, location: Union[Dict, str, None]) -> Dict[str, Any]:
        """标准化位置信息"""
        if isinstance(location, dict):
            return {
                "file": location.get("file", location.get("filename", "")),
                "line": location.get("line", location.get("line_number", 0)),
                "column": location.get("column", location.get("col", 0)),
                "function": location.get("function", location.get("method", "")),
                "class": location.get("class", "")
            }
        elif isinstance(location, str):
            # 尝试从字符串中解析位置信息
            # 格式可能为: "filename.py:line:column" 或 "filename.py:line"
            match = re.match(r'^([^:]+):(\d+)(?::(\d+))?$', location)
            if match:
                return {
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3) or 0),
                    "function": "",
                    "class": ""
                }

        return {"file": "", "line": 0, "column": 0, "function": "", "class": ""}

    def _generate_summary(self, defects: List[Dict[str, Any]], data: Dict[str, Any]) -> Dict[str, Any]:
        """生成摘要信息"""
        summary = {
            "total_defects": len(defects),
            "severity_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            "type_distribution": {},
            "files_affected": set(),
            "analysis_time": data.get("timestamp", ""),
            "analyzer": data.get("analyzer", "LLM"),
            "recommendations": []
        }

        for defect in defects:
            # 统计严重程度分布
            severity = defect.get("severity", "medium")
            if severity in summary["severity_distribution"]:
                summary["severity_distribution"][severity] += 1

            # 统计类型分布
            defect_type = defect.get("type", "unknown")
            summary["type_distribution"][defect_type] = summary["type_distribution"].get(defect_type, 0) + 1

            # 统计影响的文件
            location = defect.get("location", {})
            file_path = location.get("file", "")
            if file_path:
                summary["files_affected"].add(file_path)

        # 转换set为list
        summary["files_affected"] = list(summary["files_affected"])

        # 生成建议
        if summary["severity_distribution"]["critical"] > 0:
            summary["recommendations"].append("发现严重缺陷，建议立即修复")
        if summary["severity_distribution"]["high"] > 0:
            summary["recommendations"].append("发现高风险缺陷，建议优先处理")

        return summary

    def _extract_from_text(self, response: str) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        从文本中提取缺陷信息

        Args:
            response: 响应文本

        Returns:
            (缺陷列表, 摘要字典)
        """
        defects = []

        # 尝试匹配文本中的缺陷描述
        # 这里可以实现更复杂的文本模式匹配
        lines = response.split('\n')

        current_defect = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检查是否包含缺陷关键词
            defect_keywords = ["缺陷", "问题", "错误", "漏洞", "vulnerability", "bug", "issue", "error"]
            if any(keyword in line.lower() for keyword in defect_keywords):
                if current_defect:
                    defects.append(current_defect)
                current_defect = {
                    "title": line,
                    "description": "",
                    "type": "text_extracted",
                    "severity": "medium"
                }
            elif current_defect:
                current_defect["description"] += line + " "

        if current_defect:
            defects.append(current_defect)

        summary = self._generate_summary(defects, {"source": "text_extraction"})

        return defects, summary

    def _generate_statistics(self, result: ParsedAnalysis) -> None:
        """生成统计信息"""
        stats = {
            "parse_status": result.status.value,
            "defects_count": len(result.defects),
            "parse_errors_count": len(result.parse_errors),
            "response_length": len(result.raw_response),
            "has_critical_issues": any(d.get("severity") == "critical" for d in result.defects),
            "has_high_issues": any(d.get("severity") == "high" for d in result.defects)
        }

        result.metadata["statistics"] = stats

    def validate_parsed_result(self, result: ParsedAnalysis) -> Dict[str, Any]:
        """
        验证解析结果

        Args:
            result: 解析结果

        Returns:
            验证报告
        """
        validation = {
            "is_valid": True,
            "warnings": [],
            "errors": []
        }

        # 检查是否有缺陷
        if not result.defects and result.status != ParseResult.SUCCESS:
            validation["warnings"].append("未发现缺陷信息")

        # 检查缺陷格式
        for i, defect in enumerate(result.defects):
            if not defect.get("title"):
                validation["warnings"].append(f"缺陷 {i+1} 缺少标题")
            if not defect.get("description"):
                validation["warnings"].append(f"缺陷 {i+1} 缺少描述")
            if not defect.get("location", {}).get("file"):
                validation["warnings"].append(f"缺陷 {i+1} 缺少文件位置信息")

        # 检查解析错误
        if result.parse_errors:
            validation["errors"].extend(result.parse_errors)
            validation["is_valid"] = False

        return validation