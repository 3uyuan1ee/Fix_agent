"""
缺陷聚合和智能分类工具

这个工具专门处理多个静态分析工具的输出，进行智能聚合、去重、分类和优先级排序。
它充分利用LLM的语义理解能力，提供比简单规则匹配更智能的缺陷分析。
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool


@dataclass
class DefectCluster:
    """缺陷聚类"""

    cluster_id: str
    defects: List[Dict[str, Any]]
    root_cause: str
    severity: str
    priority: str
    fix_complexity: str
    affected_files: List[str]
    confidence: float
    suggested_fix_type: str


class DefectAggregator:
    """智能缺陷聚合器"""

    def __init__(self):
        self.similarity_threshold = 0.8
        self.severity_weights = {
            "error": 4.0,
            "warning": 2.0,
            "info": 1.0,
            "convention": 0.5,
        }
        self.complexity_patterns = {
            "simple": ["unused", "missing", "format", "style", "whitespace"],
            "medium": ["undefined", "type", "import", "scope"],
            "complex": [
                "logic",
                "algorithm",
                "architecture",
                "security",
                "performance",
            ],
        }

    def aggregate_defects(self, raw_defects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        聚合和智能分类缺陷

        Args:
            raw_defects: 原始缺陷列表

        Returns:
            聚合后的缺陷分析结果
        """
        if not raw_defects:
            return {
                "total_defects": 0,
                "clusters": [],
                "summary": self._create_empty_summary(),
                "recommendations": ["未发现代码缺陷，代码质量良好！"],
            }

        # 步骤1: 去重相似缺陷
        deduplicated_defects = self._deduplicate_defects(raw_defects)

        # 步骤2: 智能聚类
        clusters = self._cluster_defects(deduplicated_defects)

        # 步骤3: 计算优先级和影响分析
        prioritized_clusters = self._prioritize_clusters(clusters)

        # 步骤4: 生成智能建议
        recommendations = self._generate_smart_recommendations(prioritized_clusters)

        # 步骤5: 创建摘要
        summary = self._create_summary(prioritized_clusters, deduplicated_defects)

        return {
            "total_defects": len(deduplicated_defects),
            "original_count": len(raw_defects),
            "deduplication_rate": (
                (len(raw_defects) - len(deduplicated_defects)) / len(raw_defects)
                if raw_defects
                else 0
            ),
            "clusters": prioritized_clusters,
            "summary": summary,
            "recommendations": recommendations,
            "metadata": {
                "aggregation_timestamp": datetime.now().isoformat(),
                "clustering_method": "semantic_similarity",
                "confidence_threshold": self.similarity_threshold,
            },
        }

    def _deduplicate_defects(
        self, defects: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """去重相似的缺陷"""
        unique_defects = []

        for defect in defects:
            is_duplicate = False

            for existing in unique_defects:
                similarity = self._calculate_similarity(defect, existing)
                if similarity > self.similarity_threshold:
                    # 合并缺陷信息，保留更详细的那个
                    if self._is_more_detailed(defect, existing):
                        unique_defects.remove(existing)
                        unique_defects.append(defect)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_defects.append(defect)

        return unique_defects

    def _cluster_defects(self, defects: List[Dict[str, Any]]) -> List[DefectCluster]:
        """将缺陷智能聚类"""
        clusters = []
        assigned_defects = set()

        for i, defect in enumerate(defects):
            if i in assigned_defects:
                continue

            # 创建新聚类
            cluster_defects = [defect]
            assigned_defects.add(i)

            # 查找相似缺陷
            for j, other_defect in enumerate(defects[i + 1 :], i + 1):
                if j in assigned_defects:
                    continue

                if self._should_cluster_together(defect, other_defect):
                    cluster_defects.append(other_defect)
                    assigned_defects.add(j)

            # 创建聚类对象
            cluster = self._create_cluster(cluster_defects, len(clusters))
            clusters.append(cluster)

        return clusters

    def _calculate_similarity(
        self, defect1: Dict[str, Any], defect2: Dict[str, Any]
    ) -> float:
        """计算两个缺陷的相似度"""
        similarity = 0.0

        # 文件相似度 (权重: 0.2)
        if defect1.get("file") == defect2.get("file"):
            similarity += 0.2
            # 行号相近 (权重: 0.1)
            line1 = defect1.get("line", 0)
            line2 = defect2.get("line", 0)
            if abs(line1 - line2) <= 5:
                similarity += 0.1

        # 消息语义相似度 (权重: 0.5)
        msg1 = defect1.get("message", "").lower()
        msg2 = defect2.get("message", "").lower()
        message_similarity = self._calculate_text_similarity(msg1, msg2)
        similarity += message_similarity * 0.5

        # 类别相似度 (权重: 0.1)
        if defect1.get("category") == defect2.get("category"):
            similarity += 0.1

        # 规则相似度 (权重: 0.1)
        rule1 = defect1.get("rule_id", "")
        rule2 = defect2.get("rule_id", "")
        if rule1 and rule2:
            if rule1 == rule2:
                similarity += 0.1
            elif self._rules_are_related(rule1, rule2):
                similarity += 0.05

        return min(similarity, 1.0)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        if not text1 or not text2:
            return 0.0

        # 简单的关键词匹配
        words1 = set(text1.split())
        words2 = set(text2.split())

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        if not union:
            return 0.0

        return len(intersection) / len(union)

    def _should_cluster_together(
        self, defect1: Dict[str, Any], defect2: Dict[str, Any]
    ) -> bool:
        """判断两个缺陷是否应该聚在一起"""
        similarity = self._calculate_similarity(defect1, defect2)
        return similarity > self.similarity_threshold

    def _is_more_detailed(
        self, defect1: Dict[str, Any], defect2: Dict[str, Any]
    ) -> bool:
        """判断哪个缺陷信息更详细"""
        score1 = len(defect1.get("message", "")) + (
            1 if defect1.get("suggestion") else 0
        )
        score2 = len(defect2.get("message", "")) + (
            1 if defect2.get("suggestion") else 0
        )
        return score1 > score2

    def _create_cluster(
        self, defects: List[Dict[str, Any]], cluster_id: int
    ) -> DefectCluster:
        """创建缺陷聚类"""
        # 分析根原因
        root_cause = self._analyze_root_cause(defects)

        # 确定严重程度
        severity = self._determine_cluster_severity(defects)

        # 计算优先级
        priority = self._calculate_priority(defects, severity)

        # 评估修复复杂度
        complexity = self._assess_fix_complexity(defects)

        # 获取受影响文件
        affected_files = list(set(d.get("file", "") for d in defects))

        # 计算置信度
        confidence = self._calculate_cluster_confidence(defects)

        # 建议修复类型
        fix_type = self._suggest_fix_type(defects, complexity)

        return DefectCluster(
            cluster_id=f"cluster_{cluster_id:03d}",
            defects=defects,
            root_cause=root_cause,
            severity=severity,
            priority=priority,
            fix_complexity=complexity,
            affected_files=affected_files,
            confidence=confidence,
            suggested_fix_type=fix_type,
        )

    def _analyze_root_cause(self, defects: List[Dict[str, Any]]) -> str:
        """分析缺陷的根本原因"""
        # 使用简单的规则来识别常见模式
        messages = [d.get("message", "").lower() for d in defects]
        categories = [d.get("category", "") for d in defects]

        # 检查常见根原因模式
        if any("undef" in msg or "name '" in msg for msg in messages):
            return "变量或函数未定义"
        elif any("import" in msg or "module" in msg for msg in messages):
            return "导入或模块问题"
        elif any("type" in msg or "typing" in msg for msg in messages):
            return "类型相关错误"
        elif any("unused" in msg for msg in messages):
            return "未使用的代码"
        elif any("format" in msg or "style" in msg for msg in messages):
            return "代码格式和风格问题"
        elif any("security" in cat for cat in categories):
            return "安全相关问题"
        elif any("performance" in cat for cat in categories):
            return "性能相关问题"
        else:
            return "代码质量问题"

    def _determine_cluster_severity(self, defects: List[Dict[str, Any]]) -> str:
        """确定聚类的严重程度"""
        severity_scores = {"error": 4, "warning": 2, "info": 1, "convention": 0.5}

        total_score = sum(
            severity_scores.get(d.get("severity", "info"), 1) for d in defects
        )
        avg_score = total_score / len(defects)

        if avg_score >= 3.5:
            return "critical"
        elif avg_score >= 2.5:
            return "high"
        elif avg_score >= 1.5:
            return "medium"
        else:
            return "low"

    def _calculate_priority(self, defects: List[Dict[str, Any]], severity: str) -> str:
        """计算修复优先级"""
        base_priority = {"critical": 4, "high": 3, "medium": 2, "low": 1}

        # 考虑缺陷数量和影响范围
        score = base_priority.get(severity, 1)

        # 缺陷数量影响
        if len(defects) > 5:
            score += 1
        elif len(defects) > 2:
            score += 0.5

        # 影响文件数量
        affected_files = len(set(d.get("file", "") for d in defects))
        if affected_files > 3:
            score += 0.5

        # 转换为优先级
        if score >= 4.5:
            return "critical"
        elif score >= 3.5:
            return "high"
        elif score >= 2.5:
            return "medium"
        else:
            return "low"

    def _assess_fix_complexity(self, defects: List[Dict[str, Any]]) -> str:
        """评估修复复杂度"""
        messages = [d.get("message", "").lower() for d in defects]

        # 检查复杂度模式
        complexity_score = 0

        for pattern, weight in self.complexity_patterns.items():
            matches = sum(1 for msg in messages if any(p in msg for p in pattern))
            if pattern == "simple":
                complexity_score -= matches * 0.1
            elif pattern == "medium":
                complexity_score += matches * 0.2
            elif pattern == "complex":
                complexity_score += matches * 0.5

        if complexity_score <= -0.3:
            return "simple"
        elif complexity_score <= 0.3:
            return "medium"
        else:
            return "complex"

    def _calculate_cluster_confidence(self, defects: List[Dict[str, Any]]) -> float:
        """计算聚类的置信度"""
        # 基于缺陷的一致性计算置信度
        if len(defects) <= 1:
            return 1.0

        # 检查缺陷的一致性
        severities = [d.get("severity", "") for d in defects]
        categories = [d.get("category", "") for d in defects]

        severity_consistency = len(set(severities)) / len(severities)
        category_consistency = len(set(categories)) / len(categories)

        # 一致性越高，置信度越高
        consistency = 1.0 - (severity_consistency + category_consistency) / 2

        # 考虑聚类大小
        size_factor = min(len(defects) / 5.0, 1.0)

        return min(consistency * 0.7 + size_factor * 0.3, 1.0)

    def _suggest_fix_type(self, defects: List[Dict[str, Any]], complexity: str) -> str:
        """建议修复类型"""
        if complexity == "simple":
            return "auto_fix"
        elif complexity == "medium":
            return "assisted_fix"
        else:
            return "manual_fix"

    def _rules_are_related(self, rule1: str, rule2: str) -> bool:
        """判断两个规则是否相关"""
        # 简单的规则相关性检查
        if not rule1 or not rule2:
            return False

        # 提取规则前缀
        prefix1 = re.split(r"[\d_]", rule1)[0] if rule1 else ""
        prefix2 = re.split(r"[\d_]", rule2)[0] if rule2 else ""

        return prefix1 == prefix2 and len(prefix1) > 2

    def _prioritize_clusters(
        self, clusters: List[DefectCluster]
    ) -> List[Dict[str, Any]]:
        """对聚类进行优先级排序"""
        # 转换为字典格式并排序
        cluster_dicts = []
        for cluster in clusters:
            cluster_dict = {
                "cluster_id": cluster.cluster_id,
                "root_cause": cluster.root_cause,
                "severity": cluster.severity,
                "priority": cluster.priority,
                "fix_complexity": cluster.fix_complexity,
                "affected_files": cluster.affected_files,
                "defect_count": len(cluster.defects),
                "confidence": cluster.confidence,
                "suggested_fix_type": cluster.suggested_fix_type,
                "defects": cluster.defects,
            }
            cluster_dicts.append(cluster_dict)

        # 按优先级排序
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        cluster_dicts.sort(
            key=lambda x: (
                priority_order.get(x["priority"], 0),
                x["defect_count"],
                -x["confidence"],
            ),
            reverse=True,
        )

        return cluster_dicts

    def _generate_smart_recommendations(
        self, clusters: List[Dict[str, Any]]
    ) -> List[str]:
        """生成智能修复建议"""
        recommendations = []

        # 统计信息
        total_clusters = len(clusters)
        critical_clusters = sum(1 for c in clusters if c["priority"] == "critical")
        simple_fixes = sum(1 for c in clusters if c["fix_complexity"] == "simple")

        # 生成总体建议
        if critical_clusters > 0:
            recommendations.append(
                f"发现 {critical_clusters} 个严重问题聚类，建议优先处理，可能影响系统稳定性"
            )

        if simple_fixes > 0:
            recommendations.append(
                f"有 {simple_fixes} 个简单修复聚类，可以自动修复以快速提升代码质量"
            )

        # 针对高影响聚类生成建议
        high_impact_clusters = [c for c in clusters if len(c["affected_files"]) > 1]
        if high_impact_clusters:
            recommendations.append(
                f"有 {len(high_impact_clusters)} 个跨文件问题聚类，建议制定系统性修复方案"
            )

        # 根据根因分布生成建议
        root_causes = {}
        for cluster in clusters:
            cause = cluster["root_cause"]
            root_causes[cause] = root_causes.get(cause, 0) + 1

        if "导入或模块问题" in root_causes:
            recommendations.append("检测到导入相关问题，建议检查项目依赖和模块结构")

        if "未使用的代码" in root_causes:
            recommendations.append("存在未使用代码，建议进行代码清理以提高可维护性")

        return recommendations

    def _create_summary(
        self, clusters: List[Dict[str, Any]], defects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """创建摘要统计"""
        summary = {
            "total_clusters": len(clusters),
            "total_defects": len(defects),
            "by_priority": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_complexity": {"simple": 0, "medium": 0, "complex": 0},
            "by_fix_type": {"auto_fix": 0, "assisted_fix": 0, "manual_fix": 0},
            "affected_files": set(),
            "avg_confidence": 0.0,
            "top_clusters": [],
        }

        total_confidence = 0

        for cluster in clusters:
            # 统计优先级
            summary["by_priority"][cluster["priority"]] += 1

            # 统计复杂度
            summary["by_complexity"][cluster["fix_complexity"]] += 1

            # 统计修复类型
            summary["by_fix_type"][cluster["suggested_fix_type"]] += 1

            # 统计受影响文件
            summary["affected_files"].update(cluster["affected_files"])

            # 累计置信度
            total_confidence += cluster["confidence"]

        summary["affected_files"] = len(summary["affected_files"])
        summary["avg_confidence"] = total_confidence / len(clusters) if clusters else 0

        # 获取Top 3聚类
        summary["top_clusters"] = [
            {
                "cluster_id": c["cluster_id"],
                "root_cause": c["root_cause"],
                "priority": c["priority"],
                "defect_count": c["defect_count"],
                "affected_files": len(c["affected_files"]),
            }
            for c in clusters[:3]
        ]

        return summary

    def _create_empty_summary(self) -> Dict[str, Any]:
        """创建空摘要"""
        return {
            "total_clusters": 0,
            "total_defects": 0,
            "by_priority": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_complexity": {"simple": 0, "medium": 0, "complex": 0},
            "by_fix_type": {"auto_fix": 0, "assisted_fix": 0, "manual_fix": 0},
            "affected_files": 0,
            "avg_confidence": 0.0,
            "top_clusters": [],
        }


# 创建工具函数
@tool(
    description="智能聚合和分类代码缺陷，提供去重、聚类和优先级排序。能够识别重复缺陷、进行语义相似度聚类、分析根因、评估修复复杂度，并提供智能修复建议。支持多种输入格式，输出包含聚类结果、优先级排序和修复建议的综合报告。"
)
def aggregate_defects_tool(defects_json: str) -> str:
    """
    智能聚合和分析代码缺陷，提供给agent使用的缺陷分析工具。

    此工具能够处理来自不同代码分析工具的原始缺陷输出，通过智能算法：
    - 去除重复和相似的缺陷报告
    - 基于语义相似度对缺陷进行聚类
    - 分析缺陷的根本原因
    - 评估修复的复杂度和优先级
    - 提供针对性的修复建议

    Args:
        defects_json: 原始缺陷列表的JSON字符串。支持多种格式：
            - 直接缺陷列表: [{"file": "test.py", "line": 10, "message": "..."}]
            - 带结构的结果: {"defects_found": [...]} 或 {"result": {"defects": [...]}}

    Returns:
        聚合分析结果的JSON字符串，包含：
            - total_defects: 缺陷总数
            - deduplication_rate: 去重率
            - clusters: 缺陷聚类列表，每个聚类包含相似缺陷
            - priority_ranking: 优先级排序的缺陷列表
            - recommendations: 修复建议和行动计划
            - root_cause_analysis: 根因分析结果
            - execution_plan: 执行计划建议

    使用场景：
        - 在代码修复前整理和分析大量的缺陷报告
        - 识别需要优先处理的关键问题
        - 了解项目中常见的缺陷模式
        - 制定代码质量改进计划
    """
    try:
        data = json.loads(defects_json)

        # 支持多种输入格式
        if isinstance(data, dict):
            if "analysis_results" in data:
                # 来自DetectionAgent的格式
                defects = data["analysis_results"]["analysis"]["defects_found"]
            elif "defects_found" in data:
                # 直接的缺陷列表
                defects = data["defects_found"]
            else:
                # 尝试其他可能的字段
                defects = data.get("defects", [])
        elif isinstance(data, list):
            # 直接的缺陷列表
            defects = data
        else:
            return json.dumps(
                {"success": False, "error": "无效的输入格式，期望JSON对象或数组"}
            )

        if not defects:
            return json.dumps(
                {
                    "success": True,
                    "result": {"total_defects": 0, "message": "未发现缺陷需要处理"},
                }
            )

        # 执行聚合
        aggregator = DefectAggregator()
        result = aggregator.aggregate_defects(defects)

        return json.dumps(
            {"success": True, "result": result}, indent=2, ensure_ascii=False
        )

    except json.JSONDecodeError as e:
        return json.dumps({"success": False, "error": f"JSON解析错误: {str(e)}"})
    except Exception as e:
        return json.dumps({"success": False, "error": f"缺陷聚合失败: {str(e)}"})


@tool(description="分析代码缺陷模式，识别重复出现的问题类型")
def analyze_defect_patterns(defects_json: str) -> str:
    """
    分析缺陷模式

    Args:
        defects_json: 缺陷列表的JSON字符串

    Returns:
        模式分析结果的JSON字符串
    """
    try:
        data = json.loads(defects_json)

        # 提取缺陷列表
        if isinstance(data, dict) and "result" in data:
            defects = data["result"].get(
                "defects_found", data["result"].get("defects", [])
            )
        elif isinstance(data, dict):
            defects = data.get("defects_found", data.get("defects", []))
        else:
            defects = data if isinstance(data, list) else []

        if not defects:
            return json.dumps(
                {"success": True, "patterns": [], "message": "无缺陷数据用于模式分析"}
            )

        # 分析模式
        patterns = {
            "by_category": {},
            "by_file": {},
            "by_rule": {},
            "by_severity": {},
            "recurring_messages": {},
            "fix_suggestions": {},
        }

        for defect in defects:
            # 按类别统计
            category = defect.get("category", "unknown")
            if category not in patterns["by_category"]:
                patterns["by_category"][category] = []
            patterns["by_category"][category].append(defect)

            # 按文件统计
            file_path = defect.get("file", "unknown")
            if file_path not in patterns["by_file"]:
                patterns["by_file"][file_path] = []
            patterns["by_file"][file_path].append(defect)

            # 按规则统计
            rule_id = defect.get("rule_id", "unknown")
            if rule_id not in patterns["by_rule"]:
                patterns["by_rule"][rule_id] = []
            patterns["by_rule"][rule_id].append(defect)

            # 按严重程度统计
            severity = defect.get("severity", "unknown")
            if severity not in patterns["by_severity"]:
                patterns["by_severity"][severity] = []
            patterns["by_severity"][severity].append(defect)

            # 分析重复消息模式
            message = defect.get("message", "")
            if message:
                # 提取关键词
                keywords = re.findall(r"\b\w+\b", message.lower())
                for keyword in keywords:
                    if len(keyword) > 3:  # 只考虑较长的关键词
                        if keyword not in patterns["recurring_messages"]:
                            patterns["recurring_messages"][keyword] = []
                        patterns["recurring_messages"][keyword].append(defect)

        # 生成模式洞察
        insights = []

        # 找出最常见的类别
        top_categories = sorted(
            [(cat, len(defects)) for cat, defects in patterns["by_category"].items()],
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        if top_categories:
            insights.append(
                f"主要问题类型: {', '.join([f'{cat}({count})' for cat, count in top_categories])}"
            )

        # 找出问题最多的文件
        top_files = sorted(
            [(file, len(defects)) for file, defects in patterns["by_file"].items()],
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        if top_files:
            insights.append(
                f"问题最多的文件: {', '.join([f'{file}({count})' for file, count in top_files])}"
            )

        # 找出最常见的规则违反
        top_rules = sorted(
            [
                (rule, len(defects))
                for rule, defects in patterns["by_rule"].items()
                if rule != "unknown"
            ],
            key=lambda x: x[1],
            reverse=True,
        )[:3]

        if top_rules:
            insights.append(
                f"最常见的规则违反: {', '.join([f'{rule}({count})' for rule, count in top_rules])}"
            )

        return json.dumps(
            {
                "success": True,
                "patterns": patterns,
                "insights": insights,
                "statistics": {
                    "total_defects": len(defects),
                    "unique_files": len(patterns["by_file"]),
                    "unique_categories": len(patterns["by_category"]),
                    "unique_rules": len(patterns["by_rule"]),
                },
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps({"success": False, "error": f"模式分析失败: {str(e)}"})


if __name__ == "__main__":
    # 测试用例
    test_defects = [
        {
            "file": "test.py",
            "line": 10,
            "severity": "warning",
            "category": "style",
            "message": "unused variable 'x'",
            "rule_id": "W0612",
        },
        {
            "file": "test.py",
            "line": 15,
            "severity": "warning",
            "category": "style",
            "message": "unused import 'os'",
            "rule_id": "W0611",
        },
    ]

    print("测试缺陷聚合:")
    result = aggregate_defects_tool(json.dumps(test_defects))
    print(result)
