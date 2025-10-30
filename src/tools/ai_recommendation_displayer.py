"""
AI建议展示器 - T006.1
以用户友好的方式展示AI文件选择建议
"""

import os
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict, Counter

from ..utils.logger import get_logger
try:
    from ..tools.ai_file_selector import FileSelectionResult, AIFileSelectionResult
    from ..tools.project_structure_scanner import ProjectStructure
except ImportError:
    # 如果相关模块不可用，定义基本类型
    @dataclass
    class FileSelectionResult:
        file_path: str
        priority: str
        reason: str
        confidence: float
        key_issues: List[str] = field(default_factory=list)
        selection_score: float = 0.0

        def to_dict(self) -> Dict[str, Any]:
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
        selected_files: List[FileSelectionResult] = field(default_factory=list)
        selection_summary: Dict[str, Any] = field(default_factory=dict)
        execution_success: bool = True
        execution_time: float = 0.0
        error_message: str = ""
        ai_response_raw: str = ""
        token_usage: Dict[str, int] = field(default_factory=dict)
        execution_timestamp: str = ""

    @dataclass
    class ProjectStructure:
        project_path: str
        total_files: int = 0
        total_directories: int = 0
        total_lines: int = 0
        file_extensions: Dict[str, int] = field(default_factory=dict)
        language_distribution: Dict[str, int] = field(default_factory=dict)
        category_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class DisplayFile:
    """展示用的文件信息"""
    file_path: str
    display_name: str
    relative_path: str
    file_size: int = 0
    line_count: int = 0
    language: str = ""
    file_type: str = ""
    priority: str = "medium"
    confidence: float = 0.0
    selection_score: float = 0.0
    reason: str = ""
    key_issues: List[str] = field(default_factory=list)
    preview_content: Optional[str] = None
    issue_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "display_name": self.display_name,
            "relative_path": self.relative_path,
            "file_size": self.file_size,
            "line_count": self.line_count,
            "language": self.language,
            "file_type": self.file_type,
            "priority": self.priority,
            "confidence": self.confidence,
            "selection_score": self.selection_score,
            "reason": self.reason,
            "key_issues": self.key_issues,
            "preview_content": self.preview_content,
            "issue_summary": self.issue_summary
        }


@dataclass
class DisplayStatistics:
    """展示统计信息"""
    total_files: int = 0
    high_priority_count: int = 0
    medium_priority_count: int = 0
    low_priority_count: int = 0
    average_confidence: float = 0.0
    average_selection_score: float = 0.0
    language_distribution: Dict[str, int] = field(default_factory=dict)
    confidence_distribution: Dict[str, int] = field(default_factory=dict)
    selection_reason_categories: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_files": self.total_files,
            "priority_distribution": {
                "high": self.high_priority_count,
                "medium": self.medium_priority_count,
                "low": self.low_priority_count
            },
            "average_confidence": self.confidence,
            "average_selection_score": self.average_selection_score,
            "language_distribution": self.language_distribution,
            "confidence_distribution": self.confidence_distribution,
            "selection_reason_categories": self.selection_reason_categories
        }


@dataclass
class AIRecommendationDisplay:
    """AI建议展示数据"""
    display_files: List[DisplayFile] = field(default_factory=list)
    statistics: DisplayStatistics = field(default_factory=DisplayStatistics)
    metadata: Dict[str, Any] = field(default_factory=dict)
    display_options: Dict[str, Any] = field(default_factory=dict)
    generation_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "display_files": [file.to_dict() for file in self.display_files],
            "statistics": self.statistics.to_dict(),
            "metadata": self.metadata,
            "display_options": self.display_options,
            "generation_timestamp": self.generation_timestamp,
            "total_displayed": len(self.display_files)
        }


class AIRecommendationDisplayer:
    """AI建议展示器"""

    def __init__(self, project_root: str = "", max_preview_lines: int = 10):
        self.project_root = os.path.abspath(project_root) if project_root else ""
        self.max_preview_lines = max_preview_lines
        self.logger = get_logger()

        # 文件类型图标映射
        self.file_type_icons = {
            "python": "🐍",
            "javascript": "🟨",
            "typescript": "🔷",
            "java": "☕",
            "go": "🐹",
            "cpp": "⚙️",
            "c": "⚙️",
            "csharp": "🔷",
            "rust": "🦀",
            "php": "🐘",
            "ruby": "💎",
            "html": "🌐",
            "css": "🎨",
            "json": "📄",
            "yaml": "📄",
            "markdown": "📝",
            "config": "⚙️",
            "default": "📄"
        }

        # 优先级颜色映射
        self.priority_colors = {
            "high": "#ff4757",    # 红色
            "medium": "#ffa502",  # 橙色
            "low": "#2ed573"      # 绿色
        }

        # 语言扩展名映射
        self.language_extensions = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".cc": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".html": "html",
            ".htm": "html",
            ".css": "css",
            ".scss": "css",
            ".sass": "css",
            ".less": "css",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".markdown": "markdown",
            ".toml": "config",
            ".ini": "config",
            ".cfg": "config",
            ".conf": "config"
        }

    def create_display(self,
                       ai_selection_result: AIFileSelectionResult,
                       project_structure: Optional[ProjectStructure] = None,
                       display_options: Optional[Dict[str, Any]] = None) -> AIRecommendationDisplay:
        """
        创建AI建议展示

        Args:
            ai_selection_result: AI文件选择结果
            project_structure: 项目结构信息
            display_options: 展示选项

        Returns:
            AIRecommendationDisplay: 展示数据
        """
        self.logger.info("开始创建AI建议展示")

        if display_options is None:
            display_options = {}

        display = AIRecommendationDisplay(
            generation_timestamp=datetime.now().isoformat(),
            display_options=display_options
        )

        try:
            # 转换选择的文件为展示格式
            display.display_files = self._convert_to_display_files(
                ai_selection_result.selected_files, display_options
            )

            # 计算统计信息
            display.statistics = self._calculate_display_statistics(display.display_files)

            # 设置元数据
            display.metadata = self._create_metadata(ai_selection_result, project_structure)

            # 应用展示选项
            display = self._apply_display_options(display, display_options)

            self.logger.info(f"AI建议展示创建完成，共 {len(display.display_files)} 个文件")

        except Exception as e:
            self.logger.error(f"创建AI建议展示失败: {e}")
            raise

        return display

    def _convert_to_display_files(self,
                                 selected_files: List[FileSelectionResult],
                                 display_options: Dict[str, Any]) -> List[DisplayFile]:
        """转换选择的文件为展示格式"""
        display_files = []

        include_preview = display_options.get("include_preview", True)
        include_file_stats = display_options.get("include_file_stats", True)

        for file_result in selected_files:
            file_path = file_result.file_path

            # 创建展示文件
            display_file = DisplayFile(
                file_path=file_path,
                display_name=self._get_display_name(file_path),
                relative_path=self._get_relative_path(file_path),
                priority=file_result.priority,
                confidence=file_result.confidence,
                selection_score=file_result.selection_score,
                reason=file_result.reason,
                key_issues=file_result.key_issues
            )

            # 获取文件信息
            if include_file_stats:
                self._enrich_file_info(display_file)

            # 获取预览内容
            if include_preview:
                display_file.preview_content = self._get_file_preview(file_path)

            # 检测文件类型和语言
            display_file.language = self._detect_language(file_path)
            display_file.file_type = display_file.language

            # 生成问题摘要
            display_file.issue_summary = self._create_issue_summary(file_result)

            display_files.append(display_file)

        return display_files

    def _get_display_name(self, file_path: str) -> str:
        """获取显示名称"""
        import os
        return os.path.basename(file_path)

    def _get_relative_path(self, file_path: str) -> str:
        """获取相对路径"""
        if self.project_root and file_path.startswith(self.project_root):
            return os.path.relpath(file_path, self.project_root)
        return file_path

    def _enrich_file_info(self, display_file: DisplayFile) -> None:
        """丰富文件信息"""
        file_path = display_file.file_path

        try:
            # 获取文件大小
            if os.path.exists(file_path):
                display_file.file_size = os.path.getsize(file_path)

                # 获取行数
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        display_file.line_count = sum(1 for _ in f)
                except Exception:
                    display_file.line_count = 0

        except Exception as e:
            self.logger.debug(f"获取文件信息失败 {file_path}: {e}")

    def _get_file_preview(self, file_path: str) -> Optional[str]:
        """获取文件预览内容"""
        try:
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= self.max_preview_lines:
                        break
                    # 清理行尾空白和限制长度
                    cleaned_line = line.rstrip()[:200]
                    lines.append(f"{i+1:3d}: {cleaned_line}")

                if lines:
                    return "\n".join(lines)

        except Exception as e:
            self.logger.debug(f"获取文件预览失败 {file_path}: {e}")

        return None

    def _detect_language(self, file_path: str) -> str:
        """检测文件语言"""
        import os
        _, ext = os.path.splitext(file_path)
        return self.language_extensions.get(ext.lower(), "default")

    def _create_issue_summary(self, file_result: FileSelectionResult) -> Dict[str, Any]:
        """创建问题摘要"""
        return {
            "key_issues_count": len(file_result.key_issues),
            "key_issues": file_result.key_issues[:5],  # 最多显示5个关键问题
            "has_security_issues": any("安全" in issue.lower() or "security" in issue.lower()
                                     for issue in file_result.key_issues),
            "has_performance_issues": any("性能" in issue.lower() or "performance" in issue.lower()
                                        for issue in file_result.key_issues)
        }

    def _calculate_display_statistics(self, display_files: List[DisplayFile]) -> DisplayStatistics:
        """计算展示统计信息"""
        stats = DisplayStatistics()

        if not display_files:
            return stats

        stats.total_files = len(display_files)

        # 统计优先级分布
        for display_file in display_files:
            if display_file.priority == "high":
                stats.high_priority_count += 1
            elif display_file.priority == "medium":
                stats.medium_priority_count += 1
            else:
                stats.low_priority_count += 1

        # 计算平均置信度
        total_confidence = sum(f.confidence for f in display_files)
        stats.average_confidence = round(total_confidence / len(display_files), 2)

        # 计算平均选择分数
        total_score = sum(f.selection_score for f in display_files)
        stats.average_selection_score = round(total_score / len(display_files), 2)

        # 统计语言分布
        for display_file in display_files:
            lang = display_file.language
            stats.language_distribution[lang] = stats.language_distribution.get(lang, 0) + 1

        # 统计置信度分布
        confidence_ranges = {
            "high (0.8-1.0)": 0,
            "medium (0.5-0.8)": 0,
            "low (0.0-0.5)": 0
        }

        for display_file in display_files:
            conf = display_file.confidence
            if conf >= 0.8:
                confidence_ranges["high (0.8-1.0)"] += 1
            elif conf >= 0.5:
                confidence_ranges["medium (0.5-0.8)"] += 1
            else:
                confidence_ranges["low (0.0-0.5)"] += 1

        stats.confidence_distribution = confidence_ranges

        # 统计选择理由类别
        reason_categories = self._categorize_selection_reasons(display_files)
        stats.selection_reason_categories = reason_categories

        return stats

    def _categorize_selection_reasons(self, display_files: List[DisplayFile]) -> Dict[str, int]:
        """分类选择理由"""
        categories = defaultdict(int)

        reason_keywords = {
            "security": ["安全", "漏洞", "风险", "security", "vulnerability", "risk"],
            "performance": ["性能", "效率", "缓慢", "performance", "efficiency", "slow"],
            "quality": ["质量", "规范", "标准", "quality", "standard", "style"],
            "complexity": ["复杂", "难度", "维护", "complexity", "maintenance", "difficult"],
            "importance": ["重要", "核心", "关键", "important", "core", "critical", "main"],
            "issues": ["问题", "错误", "缺陷", "issues", "errors", "bugs", "defects"]
        }

        for display_file in display_files:
            reason_lower = display_file.reason.lower()
            categorized = False

            for category, keywords in reason_keywords.items():
                if any(keyword in reason_lower for keyword in keywords):
                    categories[category] += 1
                    categorized = True
                    break

            if not categorized:
                categories["other"] += 1

        return dict(categories)

    def _create_metadata(self,
                        ai_selection_result: AIFileSelectionResult,
                        project_structure: Optional[ProjectStructure]) -> Dict[str, Any]:
        """创建元数据"""
        metadata = {
            "ai_execution_info": {
                "execution_success": ai_selection_result.execution_success,
                "execution_time": ai_selection_result.execution_time,
                "execution_timestamp": ai_selection_result.execution_timestamp,
                "error_message": ai_selection_result.error_message
            },
            "selection_summary": ai_selection_result.selection_summary,
            "token_usage": ai_selection_result.token_usage
        }

        if project_structure:
            metadata["project_info"] = {
                "project_path": project_structure.project_path,
                "total_files": project_structure.total_files,
                "total_lines": project_structure.total_lines,
                "language_distribution": project_structure.language_distribution
            }

        return metadata

    def _apply_display_options(self,
                              display: AIRecommendationDisplay,
                              display_options: Dict[str, Any]) -> AIRecommendationDisplay:
        """应用展示选项"""
        # 排序选项
        sort_by = display_options.get("sort_by", "selection_score")
        sort_order = display_options.get("sort_order", "desc")

        if sort_by == "priority":
            priority_order = {"high": 3, "medium": 2, "low": 1}
            display.display_files.sort(
                key=lambda x: (priority_order.get(x.priority, 0), x.selection_score),
                reverse=(sort_order == "desc")
            )
        elif sort_by == "confidence":
            display.display_files.sort(
                key=lambda x: x.confidence,
                reverse=(sort_order == "desc")
            )
        elif sort_by == "file_name":
            display.display_files.sort(
                key=lambda x: x.display_name.lower(),
                reverse=(sort_order == "desc")
            )
        else:  # selection_score (default)
            display.display_files.sort(
                key=lambda x: x.selection_score,
                reverse=(sort_order == "desc")
            )

        # 过滤选项
        min_priority = display_options.get("min_priority")
        if min_priority:
            priority_order = {"high": 3, "medium": 2, "low": 1}
            min_level = priority_order.get(min_priority, 0)
            display.display_files = [
                f for f in display.display_files
                if priority_order.get(f.priority, 0) >= min_level
            ]

        min_confidence = display_options.get("min_confidence")
        if min_confidence is not None:
            display.display_files = [
                f for f in display.display_files
                if f.confidence >= min_confidence
            ]

        max_files = display_options.get("max_files")
        if max_files:
            display.display_files = display.display_files[:max_files]

        return display

    def format_for_console(self, display: AIRecommendationDisplay) -> str:
        """格式化为控制台输出"""
        lines = []

        # 标题
        lines.append("=" * 80)
        lines.append("🤖 AI文件选择建议")
        lines.append("=" * 80)
        lines.append("")

        # 统计信息
        stats = display.statistics
        lines.append("📊 选择统计:")
        lines.append(f"   总文件数: {stats.total_files}")
        lines.append(f"   优先级分布: 高({stats.high_priority_count}) 中({stats.medium_priority_count}) 低({stats.low_priority_count})")
        lines.append(f"   平均置信度: {stats.average_confidence:.2f}")
        lines.append(f"   平均选择分数: {stats.average_selection_score:.2f}")
        lines.append("")

        # 语言分布
        if stats.language_distribution:
            lines.append("🌍 语言分布:")
            for lang, count in sorted(stats.language_distribution.items(), key=lambda x: x[1], reverse=True):
                icon = self.file_type_icons.get(lang, self.file_type_icons["default"])
                lines.append(f"   {icon} {lang.capitalize()}: {count}")
            lines.append("")

        # 文件详情
        lines.append("📁 推荐文件详情:")
        lines.append("-" * 80)

        for i, display_file in enumerate(display.display_files, 1):
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[display_file.priority]
            lang_icon = self.file_type_icons.get(display_file.language, self.file_type_icons["default"])

            lines.append(f"{i:2d}. {priority_icon} {lang_icon} {display_file.display_name}")
            lines.append(f"    路径: {display_file.relative_path}")
            lines.append(f"    优先级: {display_file.priority} | 置信度: {display_file.confidence:.2f} | 分数: {display_file.selection_score:.1f}")

            if display_file.line_count > 0:
                lines.append(f"    信息: {display_file.line_count}行 | {display_file.file_size}字节")

            lines.append(f"    理由: {display_file.reason}")

            if display_file.key_issues:
                lines.append(f"    关键问题: {', '.join(display_file.key_issues[:3])}")

            # 显示预览（前几行）
            if display_file.preview_content:
                preview_lines = display_file.preview_content.split('\n')
                lines.append("    预览:")
                for line in preview_lines[:3]:  # 只显示前3行
                    lines.append(f"      {line}")
                if len(preview_lines) > 3:
                    lines.append("      ...")

            lines.append("")

        # 元数据
        if display.metadata.get("ai_execution_info"):
            exec_info = display.metadata["ai_execution_info"]
            lines.append("⚡ 执行信息:")
            lines.append(f"   执行时间: {exec_info['execution_time']:.2f}秒")
            lines.append(f"   执行状态: {'成功' if exec_info['execution_success'] else '失败'}")
            if exec_info.get("token_usage"):
                usage = exec_info["token_usage"]
                lines.append(f"   Token使用: {usage.get('total', 'N/A')}")

        lines.append("=" * 80)

        return "\n".join(lines)

    def format_for_web(self, display: AIRecommendationDisplay) -> Dict[str, Any]:
        """格式化为Web界面数据"""
        web_data = {
            "summary": {
                "total_files": display.statistics.total_files,
                "high_priority_count": display.statistics.high_priority_count,
                "medium_priority_count": display.statistics.medium_priority_count,
                "low_priority_count": display.statistics.low_priority_count,
                "average_confidence": display.statistics.average_confidence,
                "average_selection_score": display.statistics.average_selection_score
            },
            "charts": {
                "language_distribution": display.statistics.language_distribution,
                "confidence_distribution": display.statistics.confidence_distribution,
                "reason_categories": display.statistics.selection_reason_categories
            },
            "files": []
        }

        # 转换文件数据
        for display_file in display.display_files:
            file_data = display_file.to_dict()
            # 添加展示用的额外信息
            file_data["icon"] = self.file_type_icons.get(display_file.language, self.file_type_icons["default"])
            file_data["priority_color"] = self.priority_colors.get(display_file.priority, "#666666")
            file_data["priority_icon"] = {"high": "🔴", "medium": "🟡", "low": "🟢"}[display_file.priority]

            web_data["files"].append(file_data)

        # 添加元数据
        web_data["metadata"] = display.metadata
        web_data["generation_timestamp"] = display.generation_timestamp

        return web_data


# 便捷函数
def display_ai_recommendations(ai_selection_result: AIFileSelectionResult,
                             project_root: str = "",
                             format_type: str = "console",
                             display_options: Dict[str, Any] = None) -> Any:
    """
    便捷的AI建议展示函数

    Args:
        ai_selection_result: AI文件选择结果
        project_root: 项目根目录
        format_type: 输出格式 ("console", "web", "dict")
        display_options: 展示选项

    Returns:
        Any: 格式化后的展示数据
    """
    displayer = AIRecommendationDisplayer(project_root)
    display = displayer.create_display(ai_selection_result, display_options=display_options)

    if format_type == "console":
        return displayer.format_for_console(display)
    elif format_type == "web":
        return displayer.format_for_web(display)
    elif format_type == "dict":
        return display.to_dict()
    else:
        return display