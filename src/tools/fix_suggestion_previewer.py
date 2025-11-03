"""
T010.2: 修复建议预览器

节点D的辅助组件，提供修复建议的预览功能，支持用户在正式审查前快速浏览
和筛选修复建议。提供多种预览模式和过滤选项。

工作流位置: 节点D (用户审查) - 预览功能
输入: 格式化的修复建议展示数据 (T010.1输出)
输出: 预览数据和用户选择结果
"""

import json
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import re
from pathlib import Path

from ..utils.types import ProblemType, RiskLevel, FixType
from ..utils.logger import get_logger
from .workflow_data_types import AIFixSuggestion, WorkflowDataPacket
from .workflow_user_interaction_types import UserDecision, DecisionType, UserAction
from .fix_suggestion_displayer import SuggestionDisplayData, DisplayFormat, DisplaySection

logger = get_logger()


class PreviewMode(Enum):
    """预览模式枚举"""
    QUICK_OVERVIEW = "quick_overview"    # 快速概览
    DETAILED_PREVIEW = "detailed_preview" # 详细预览
    COMPACT_VIEW = "compact_view"        # 紧凑视图
    CARD_VIEW = "card_view"             # 卡片视图
    LIST_VIEW = "list_view"             # 列表视图


class FilterCriteria(Enum):
    """过滤条件枚举"""
    BY_PROBLEM_TYPE = "by_problem_type"
    BY_RISK_LEVEL = "by_risk_level"
    BY_CONFIDENCE = "by_confidence"
    BY_QUALITY_SCORE = "by_quality_score"
    BY_FILE_PATH = "by_file_path"
    BY_COMPLEXITY = "by_complexity"
    BY_FIX_TYPE = "by_fix_type"


class SortCriteria(Enum):
    """排序条件枚举"""
    BY_QUALITY_SCORE = "by_quality_score"
    BY_RISK_LEVEL = "by_risk_level"
    BY_CONFIDENCE = "by_confidence"
    BY_FILE_NAME = "by_file_name"
    BY_LINE_NUMBER = "by_line_number"
    BY_PROBLEM_SEVERITY = "by_problem_severity"


@dataclass
class PreviewConfiguration:
    """预览配置"""
    mode: PreviewMode = PreviewMode.QUICK_OVERVIEW
    max_items_per_page: int = 10
    enable_filtering: bool = True
    enable_sorting: bool = True
    enable_grouping: bool = True
    show_quality_indicators: bool = True
    show_code_snippets: bool = True
    show_risk_indicators: bool = True
    show_alternatives_count: bool = True
    language: str = "zh"


@dataclass
class PreviewFilter:
    """预览过滤器"""
    criteria: FilterCriteria
    values: List[Any]
    operator: str = "in"  # in, not_in, gt, lt, eq, contains


@dataclass
class PreviewSort:
    """预览排序器"""
    criteria: SortCriteria
    ascending: bool = True


@dataclass
class PreviewGroup:
    """预览分组器"""
    criteria: str  # 分组条件
    groups: Dict[str, List[SuggestionDisplayData]]


@dataclass
class PreviewPage:
    """预览页面"""
    page_number: int
    total_pages: int
    items: List[SuggestionDisplayData]
    has_next: bool
    has_previous: bool
    page_size: int


@dataclass
class PreviewStatistics:
    """预览统计信息"""
    total_suggestions: int
    quality_distribution: Dict[str, int]
    risk_distribution: Dict[str, int]
    type_distribution: Dict[str, int]
    file_distribution: Dict[str, int]
    confidence_distribution: Dict[str, int]


@dataclass
class PreviewResult:
    """预览结果"""
    mode: PreviewMode
    config: PreviewConfiguration
    statistics: PreviewStatistics
    pages: List[PreviewPage]
    current_page: int
    filters: List[PreviewFilter]
    sort_config: Optional[PreviewSort]
    groups: Optional[PreviewGroup]
    selected_items: List[str]
    rejected_items: List[str]


class FixSuggestionPreviewer:
    """修复建议预览器"""

    def __init__(self, config: PreviewConfiguration = None):
        """
        初始化预览器

        Args:
            config: 预览配置
        """
        self.config = config or PreviewConfiguration()
        self._current_suggestions: List[SuggestionDisplayData] = []
        self._filters: List[PreviewFilter] = []
        self._sort_config: Optional[PreviewSort] = None
        self._groups: Optional[PreviewGroup] = None
        self._selected_items: List[str] = []
        self._rejected_items: List[str] = []

    def load_suggestions(self, suggestions: List[SuggestionDisplayData]) -> None:
        """
        加载修复建议

        Args:
            suggestions: 格式化的修复建议展示数据
        """
        self._current_suggestions = suggestions.copy()
        logger.info(f"加载了 {len(suggestions)} 个修复建议")

    def set_filter(self, filter_config: PreviewFilter) -> None:
        """
        设置过滤条件

        Args:
            filter_config: 过滤配置
        """
        # 移除相同条件的现有过滤器
        self._filters = [
            f for f in self._filters
            if f.criteria != filter_config.criteria
        ]
        self._filters.append(filter_config)
        logger.info(f"设置过滤器: {filter_config.criteria.value}")

    def clear_filters(self) -> None:
        """清除所有过滤器"""
        self._filters.clear()
        logger.info("清除所有过滤器")

    def set_sort(self, sort_config: PreviewSort) -> None:
        """
        设置排序条件

        Args:
            sort_config: 排序配置
        """
        self._sort_config = sort_config
        logger.info(f"设置排序: {sort_config.criteria.value}")

    def set_grouping(self, group_by: str) -> None:
        """
        设置分组条件

        Args:
            group_by: 分组条件
        """
        if group_by not in ["problem_type", "risk_level", "file_name", "quality_tier"]:
            raise ValueError(f"不支持的分组条件: {group_by}")

        self._groups = self._create_groups(group_by)
        logger.info(f"设置分组: {group_by}")

    def apply_filters_and_sort(self) -> List[SuggestionDisplayData]:
        """应用过滤和排序条件"""
        filtered_suggestions = self._current_suggestions.copy()

        # 应用过滤器
        for filter_config in self._filters:
            filtered_suggestions = self._apply_filter(filtered_suggestions, filter_config)

        # 应用排序
        if self._sort_config:
            filtered_suggestions = self._apply_sort(filtered_suggestions, self._sort_config)

        logger.info(f"过滤和排序后剩余 {len(filtered_suggestions)} 个建议")
        return filtered_suggestions

    def generate_preview(self, mode: Optional[PreviewMode] = None) -> PreviewResult:
        """
        生成预览结果

        Args:
            mode: 预览模式，如果为None则使用配置中的模式

        Returns:
            预览结果
        """
        preview_mode = mode or self.config.mode

        # 应用过滤和排序
        processed_suggestions = self.apply_filters_and_sort()

        # 生成统计信息
        statistics = self._generate_statistics(processed_suggestions)

        # 生成分页
        pages = self._generate_pages(processed_suggestions)

        result = PreviewResult(
            mode=preview_mode,
            config=self.config,
            statistics=statistics,
            pages=pages,
            current_page=1,
            filters=self._filters.copy(),
            sort_config=self._sort_config,
            groups=self._groups,
            selected_items=self._selected_items.copy(),
            rejected_items=self._rejected_items.copy()
        )

        logger.info(f"生成预览结果: {preview_mode.value}, 总页数: {len(pages)}")
        return result

    def get_page(self, page_number: int, suggestions: List[SuggestionDisplayData]) -> PreviewPage:
        """
        获取指定页面

        Args:
            page_number: 页码
            suggestions: 修复建议列表

        Returns:
            预览页面
        """
        total_items = len(suggestions)
        total_pages = (total_items + self.config.max_items_per_page - 1) // self.config.max_items_per_page

        if page_number < 1 or page_number > total_pages:
            raise ValueError(f"页码 {page_number} 超出范围 (1-{total_pages})")

        start_index = (page_number - 1) * self.config.max_items_per_page
        end_index = start_index + self.config.max_items_per_page

        page_items = suggestions[start_index:end_index]

        return PreviewPage(
            page_number=page_number,
            total_pages=total_pages,
            items=page_items,
            has_next=page_number < total_pages,
            has_previous=page_number > 1,
            page_size=len(page_items)
        )

    def select_item(self, suggestion_id: str) -> None:
        """
        选择修复建议

        Args:
            suggestion_id: 建议ID
        """
        if suggestion_id not in self._selected_items:
            self._selected_items.append(suggestion_id)
            # 从拒绝列表中移除
            if suggestion_id in self._rejected_items:
                self._rejected_items.remove(suggestion_id)
        logger.info(f"选择修复建议: {suggestion_id}")

    def reject_item(self, suggestion_id: str) -> None:
        """
        拒绝修复建议

        Args:
            suggestion_id: 建议ID
        """
        if suggestion_id not in self._rejected_items:
            self._rejected_items.append(suggestion_id)
            # 从选择列表中移除
            if suggestion_id in self._selected_items:
                self._selected_items.remove(suggestion_id)
        logger.info(f"拒绝修复建议: {suggestion_id}")

    def toggle_item_selection(self, suggestion_id: str) -> None:
        """
        切换修复建议选择状态

        Args:
            suggestion_id: 建议ID
        """
        if suggestion_id in self._selected_items:
            self.reject_item(suggestion_id)
        else:
            self.select_item(suggestion_id)

    def get_selected_items(self) -> List[SuggestionDisplayData]:
        """获取选择的修复建议"""
        return [
            suggestion for suggestion in self._current_suggestions
            if suggestion.suggestion_id in self._selected_items
        ]

    def get_rejected_items(self) -> List[SuggestionDisplayData]:
        """获取拒绝的修复建议"""
        return [
            suggestion for suggestion in self._current_suggestions
            if suggestion.suggestion_id in self._rejected_items
        ]

    def get_unprocessed_items(self) -> List[SuggestionDisplayData]:
        """获取未处理的修复建议"""
        processed_ids = self._selected_items + self._rejected_items
        return [
            suggestion for suggestion in self._current_suggestions
            if suggestion.suggestion_id not in processed_ids
        ]

    def _apply_filter(self, suggestions: List[SuggestionDisplayData],
                     filter_config: PreviewFilter) -> List[SuggestionDisplayData]:
        """应用单个过滤器"""
        filtered = []

        for suggestion in suggestions:
            if self._matches_filter(suggestion, filter_config):
                filtered.append(suggestion)

        return filtered

    def _matches_filter(self, suggestion: SuggestionDisplayData,
                       filter_config: PreviewFilter) -> bool:
        """检查建议是否匹配过滤器"""
        value = self._get_filter_value(suggestion, filter_config.criteria)

        if filter_config.operator == "in":
            return value in filter_config.values
        elif filter_config.operator == "not_in":
            return value not in filter_config.values
        elif filter_config.operator == "gt":
            return value > filter_config.values[0]
        elif filter_config.operator == "lt":
            return value < filter_config.values[0]
        elif filter_config.operator == "eq":
            return value == filter_config.values[0]
        elif filter_config.operator == "contains":
            return any(v in str(value).lower() for v in filter_config.values)
        else:
            return False

    def _get_filter_value(self, suggestion: SuggestionDisplayData,
                         criteria: FilterCriteria) -> Any:
        """获取过滤值"""
        if criteria == FilterCriteria.BY_PROBLEM_TYPE:
            return suggestion.problem_type
        elif criteria == FilterCriteria.BY_RISK_LEVEL:
            return suggestion.risk_level
        elif criteria == FilterCriteria.BY_CONFIDENCE:
            return suggestion.confidence
        elif criteria == FilterCriteria.BY_QUALITY_SCORE:
            return suggestion.overall_quality_score
        elif criteria == FilterCriteria.BY_FILE_PATH:
            return suggestion.file_info["file_path"]
        elif criteria == FilterCriteria.BY_COMPLEXITY:
            return suggestion.display_metadata["code_change_size"]
        elif criteria == FilterCriteria.BY_FIX_TYPE:
            return suggestion.context_info["fix_type"]
        else:
            return None

    def _apply_sort(self, suggestions: List[SuggestionDisplayData],
                   sort_config: PreviewSort) -> List[SuggestionDisplayData]:
        """应用排序"""
        return sorted(
            suggestions,
            key=self._get_sort_key(sort_config.criteria),
            reverse=not sort_config.ascending
        )

    def _get_sort_key(self, criteria: SortCriteria) -> Callable:
        """获取排序键函数"""
        if criteria == SortCriteria.BY_QUALITY_SCORE:
            return lambda x: x.overall_quality_score
        elif criteria == SortCriteria.BY_RISK_LEVEL:
            return lambda x: self._risk_level_to_number(x.risk_level)
        elif criteria == SortCriteria.BY_CONFIDENCE:
            return lambda x: x.confidence
        elif criteria == SortCriteria.BY_FILE_NAME:
            return lambda x: x.file_info["file_name"]
        elif criteria == SortCriteria.BY_LINE_NUMBER:
            return lambda x: x.code_changes.line_number
        elif criteria == SortCriteria.BY_PROBLEM_SEVERITY:
            return lambda x: self._severity_to_number(x.severity)
        else:
            return lambda x: x.suggestion_id

    def _risk_level_to_number(self, risk_level: str) -> int:
        """风险等级转数字"""
        risk_map = {
            "CRITICAL": 5, "HIGH": 4, "MEDIUM": 3, "LOW": 2, "NEGLIGIBLE": 1,
            "关键风险": 5, "高风险": 4, "中等风险": 3, "低风险": 2, "可忽略风险": 1
        }
        return risk_map.get(risk_level, 0)

    def _severity_to_number(self, severity: str) -> int:
        """严重程度转数字"""
        severity_map = {
            "严重": 5, "高": 4, "中": 3, "低": 2, "未知": 1
        }
        return severity_map.get(severity, 0)

    def _create_groups(self, group_by: str) -> PreviewGroup:
        """创建分组"""
        groups = {}

        for suggestion in self._current_suggestions:
            group_key = self._get_group_key(suggestion, group_by)

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(suggestion)

        return PreviewGroup(criteria=group_by, groups=groups)

    def _get_group_key(self, suggestion: SuggestionDisplayData, group_by: str) -> str:
        """获取分组键"""
        if group_by == "problem_type":
            return suggestion.problem_type
        elif group_by == "risk_level":
            return suggestion.risk_level
        elif group_by == "file_name":
            return suggestion.file_info["file_name"]
        elif group_by == "quality_tier":
            score = suggestion.overall_quality_score
            if score >= 0.9:
                return "优秀 (≥0.9)"
            elif score >= 0.8:
                return "良好 (0.8-0.9)"
            elif score >= 0.7:
                return "一般 (0.7-0.8)"
            else:
                return "需改进 (<0.7)"
        else:
            return "其他"

    def _generate_statistics(self, suggestions: List[SuggestionDisplayData]) -> PreviewStatistics:
        """生成统计信息"""
        total_suggestions = len(suggestions)

        # 质量分布
        quality_distribution = self._calculate_distribution(
            suggestions, "overall_quality_score",
            [(0.9, "优秀"), (0.8, "良好"), (0.7, "一般"), (0.0, "需改进")]
        )

        # 风险分布
        risk_distribution = {}
        for suggestion in suggestions:
            risk_level = suggestion.risk_level
            risk_distribution[risk_level] = risk_distribution.get(risk_level, 0) + 1

        # 类型分布
        type_distribution = {}
        for suggestion in suggestions:
            problem_type = suggestion.problem_type
            type_distribution[problem_type] = type_distribution.get(problem_type, 0) + 1

        # 文件分布
        file_distribution = {}
        for suggestion in suggestions:
            file_name = suggestion.file_info["file_name"]
            file_distribution[file_name] = file_distribution.get(file_name, 0) + 1

        # 置信度分布
        confidence_distribution = self._calculate_distribution(
            suggestions, "confidence",
            [(0.9, "极高"), (0.8, "高"), (0.7, "中等"), (0.0, "较低")]
        )

        return PreviewStatistics(
            total_suggestions=total_suggestions,
            quality_distribution=quality_distribution,
            risk_distribution=risk_distribution,
            type_distribution=type_distribution,
            file_distribution=file_distribution,
            confidence_distribution=confidence_distribution
        )

    def _calculate_distribution(self, suggestions: List[SuggestionDisplayData],
                               field: str, thresholds: List[Tuple[float, str]]) -> Dict[str, int]:
        """计算分布统计"""
        distribution = {name: 0 for _, name in thresholds}

        for suggestion in suggestions:
            value = getattr(suggestion, field, 0)
            for threshold, name in reversed(thresholds):
                if value >= threshold:
                    distribution[name] += 1
                    break

        return distribution

    def _generate_pages(self, suggestions: List[SuggestionDisplayData]) -> List[PreviewPage]:
        """生成分页"""
        pages = []
        total_pages = (len(suggestions) + self.config.max_items_per_page - 1) // self.config.max_items_per_page

        for page_num in range(1, total_pages + 1):
            page = self.get_page(page_num, suggestions)
            pages.append(page)

        return pages

    def export_preview_result(self, result: PreviewResult) -> Dict[str, Any]:
        """导出预览结果"""
        return {
            "mode": result.mode.value,
            "statistics": asdict(result.statistics),
            "total_pages": len(result.pages),
            "current_page": result.current_page,
            "filters": [asdict(f) for f in result.filters],
            "sort_config": asdict(result.sort_config) if result.sort_config else None,
            "selected_count": len(result.selected_items),
            "rejected_count": len(result.rejected_items)
        }

    def quick_filter_high_quality(self, min_score: float = 0.8) -> None:
        """快速过滤高质量建议"""
        filter_config = PreviewFilter(
            criteria=FilterCriteria.BY_QUALITY_SCORE,
            values=[min_score],
            operator="gt"
        )
        self.set_filter(filter_config)

    def quick_filter_low_risk(self, max_risk: str = "MEDIUM") -> None:
        """快速过滤低风险建议"""
        risk_levels = ["LOW", "NEGLIGIBLE", "低风险", "可忽略风险"]
        if max_risk in ["MEDIUM", "中等风险"]:
            risk_levels.extend(["MEDIUM", "中等风险"])

        filter_config = PreviewFilter(
            criteria=FilterCriteria.BY_RISK_LEVEL,
            values=risk_levels,
            operator="in"
        )
        self.set_filter(filter_config)

    def quick_sort_by_quality(self, descending: bool = True) -> None:
        """快速按质量排序"""
        sort_config = PreviewSort(
            criteria=SortCriteria.BY_QUALITY_SCORE,
            ascending=not descending
        )
        self.set_sort(sort_config)

    def reset_all(self) -> None:
        """重置所有设置"""
        self._filters.clear()
        self._sort_config = None
        self._groups = None
        self._selected_items.clear()
        self._rejected_items.clear()
        logger.info("重置所有预览设置")