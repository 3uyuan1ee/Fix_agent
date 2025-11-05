"""
智能文件选择算法模块
实现基于启发式的文件选择算法
"""

import ast
import os
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ..tools.file_operations import FileOperations
from ..utils.config import get_config_manager
from ..utils.logger import get_logger


@dataclass
class FileInfo:
    """文件信息数据结构"""

    path: str
    name: str
    extension: str
    size: int
    modified_time: float
    content: str = ""
    imports: Set[str] = field(default_factory=set)
    score: float = 0.0
    relevance: float = 0.0
    priority: int = 1
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)


@dataclass
class SelectionCriteria:
    """文件选择标准"""

    keywords: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    include_patterns: List[str] = field(default_factory=list)
    extensions: List[str] = field(default_factory=list)
    max_files: int = 100
    min_relevance: float = 0.1
    prioritize_recent: bool = True
    prioritize_dependencies: bool = True


class FileSelector:
    """智能文件选择器"""

    def __init__(self, config_manager=None):
        """
        初始化文件选择器

        Args:
            config_manager: 配置管理器实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()
        self.file_ops = FileOperations(self.config_manager)

        # 选择器配置
        self.config = self.config_manager.get_section("file_selector", {})

        # 文件相关性权重
        self.keyword_weight = self.config.get("keyword_weight", 0.4)
        self.dependency_weight = self.config.get("dependency_weight", 0.3)
        self.recency_weight = self.config.get("recency_weight", 0.2)
        self.extension_weight = self.config.get("extension_weight", 0.1)

        # 支持的文件扩展名和权重
        self.extension_weights = {
            ".py": 1.0,  # Python文件
            ".js": 0.9,  # JavaScript
            ".ts": 0.9,  # TypeScript
            ".java": 0.8,  # Java
            ".cpp": 0.8,  # C++
            ".c": 0.7,  # C
            ".h": 0.6,  # Header文件
            ".hpp": 0.6,  # C++ Header
            ".go": 0.8,  # Go
            ".rs": 0.8,  # Rust
            ".php": 0.7,  # PHP
            ".rb": 0.7,  # Ruby
            ".cs": 0.8,  # C#
            ".swift": 0.8,  # Swift
            ".kt": 0.8,  # Kotlin
            ".html": 0.5,  # HTML
            ".css": 0.5,  # CSS
            ".json": 0.4,  # JSON
            ".xml": 0.4,  # XML
            ".yaml": 0.4,  # YAML
            ".yml": 0.4,  # YAML
            ".md": 0.3,  # Markdown
            ".txt": 0.2,  # Text
        }

        # 常见文件模式的重要性权重
        self.file_pattern_weights = {
            # 核心文件
            r"^(main|index|app|application)\.": 1.0,
            r"^(__init__|setup|requirements)\.": 0.9,
            r"^(config|configuration)\.": 0.8,
            # 重要模块
            r".*core.*": 0.8,
            r".*utils.*": 0.7,
            r".*helper.*": 0.7,
            r".*service.*": 0.8,
            r".*controller.*": 0.8,
            r".*model.*": 0.8,
            r".*view.*": 0.7,
            # 测试文件
            r".*test.*": 0.6,
            r".*spec.*": 0.6,
            # 配置文件
            r".*\.(conf|cfg|ini)$": 0.7,
            r".*\.(env|dotenv)$": 0.8,
        }

        self.logger.info("FileSelector initialized")

    def select_files(
        self, directory: str, criteria: SelectionCriteria
    ) -> List[FileInfo]:
        """
        智能选择文件

        Args:
            directory: 目标目录
            criteria: 选择标准

        Returns:
            选择的文件信息列表
        """
        self.logger.info(f"Starting intelligent file selection in: {directory}")

        # 扫描所有文件
        all_files = self._scan_files(directory, criteria)
        self.logger.debug(f"Found {len(all_files)} files total")

        if not all_files:
            return []

        # 分析依赖关系
        dependency_graph = self._analyze_dependencies(all_files)
        self.logger.debug(f"Analyzed dependencies for {len(dependency_graph)} files")

        # 计算文件相关性分数
        scored_files = self._calculate_relevance_scores(
            all_files, criteria, dependency_graph
        )
        self.logger.debug(f"Calculated relevance scores for {len(scored_files)} files")

        # 按分数排序
        sorted_files = sorted(
            scored_files, key=lambda f: (f.relevance, f.modified_time), reverse=True
        )

        # 应用数量限制
        selected_files = sorted_files[: criteria.max_files]

        self.logger.info(
            f"Selected {len(selected_files)} files out of {len(all_files)}"
        )
        return selected_files

    def _scan_files(
        self, directory: str, criteria: SelectionCriteria
    ) -> List[FileInfo]:
        """扫描文件并收集基础信息"""
        files = []

        try:
            # 获取所有匹配扩展名的文件
            file_paths = self.file_ops.scan_directory(
                directory=directory,
                recursive=True,
                extensions=criteria.extensions or list(self.extension_weights.keys()),
                exclude_patterns=criteria.exclude_patterns,
            )

            for file_path in file_paths:
                try:
                    file_info = self.file_ops.get_file_info(file_path)

                    # 读取文件内容用于分析
                    if file_info["size"] < 1024 * 1024:  # 只读取小于1MB的文件
                        content = self.file_ops.read_file(file_path)
                    else:
                        content = ""

                    file_obj = FileInfo(
                        path=file_info["path"],
                        name=file_info["name"],
                        extension=file_info["extension"] or "",
                        size=file_info["size"],
                        modified_time=file_info["modified_time"],
                        content=content,
                    )

                    files.append(file_obj)

                except Exception as e:
                    self.logger.warning(f"Failed to process file {file_path}: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Failed to scan directory {directory}: {e}")
            return []

        return files

    def _analyze_dependencies(self, files: List[FileInfo]) -> Dict[str, Set[str]]:
        """分析文件依赖关系"""
        dependency_graph = defaultdict(set)

        for file_info in files:
            if file_info.extension != ".py":
                continue  # 目前只分析Python文件的依赖

            try:
                # 解析AST提取import
                tree = ast.parse(file_info.content, filename=file_info.path)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            dependency_graph[file_info.path].add(alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            dependency_graph[file_info.path].add(node.module)
                            for alias in node.names:
                                if alias.name != "*":
                                    dependency_graph[file_info.path].add(
                                        f"{node.module}.{alias.name}"
                                    )

                # 更新文件的依赖集合
                file_info.imports = dependency_graph[file_info.path]

            except SyntaxError as e:
                self.logger.debug(f"Syntax error in {file_info.path}: {e}")
            except Exception as e:
                self.logger.warning(
                    f"Failed to analyze dependencies for {file_info.path}: {e}"
                )

        # 构建反向依赖关系（哪些文件依赖于当前文件）
        for file_path, imports in dependency_graph.items():
            for imported_module in imports:
                for other_file in files:
                    if (
                        imported_module in other_file.path
                        or other_file.name == f"{imported_module}.py"
                    ):
                        other_file.dependents.add(file_path)

        return dict(dependency_graph)

    def _calculate_relevance_scores(
        self,
        files: List[FileInfo],
        criteria: SelectionCriteria,
        dependency_graph: Dict[str, Set[str]],
    ) -> List[FileInfo]:
        """计算文件相关性分数"""
        current_time = time.time()

        for file_info in files:
            score = 0.0

            # 1. 关键词匹配分数
            keyword_score = self._calculate_keyword_score(file_info, criteria.keywords)
            score += keyword_score * self.keyword_weight

            # 2. 文件名模式分数
            pattern_score = self._calculate_pattern_score(file_info)
            score += pattern_score * self.extension_weight

            # 3. 依赖关系分数
            if criteria.prioritize_dependencies:
                dependency_score = self._calculate_dependency_score(
                    file_info, dependency_graph, files
                )
                score += dependency_score * self.dependency_weight

            # 4. 修改时间分数
            if criteria.prioritize_recent:
                recency_score = self._calculate_recency_score(file_info, current_time)
                score += recency_score * self.recency_weight

            # 5. 文件扩展名权重
            extension_score = self.extension_weights.get(file_info.extension, 0.1)
            score += extension_score * self.extension_weight

            file_info.relevance = score

        # 过滤低相关性文件
        relevant_files = [f for f in files if f.relevance >= criteria.min_relevance]

        return relevant_files

    def _calculate_keyword_score(
        self, file_info: FileInfo, keywords: List[str]
    ) -> float:
        """计算关键词匹配分数"""
        if not keywords:
            return 0.0

        score = 0.0
        file_path_lower = file_info.path.lower()
        file_name_lower = file_info.name.lower()
        content_lower = file_info.content.lower()

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 文件路径匹配（权重最高）
            if keyword_lower in file_path_lower:
                score += 1.0

            # 文件名匹配
            if keyword_lower in file_name_lower:
                score += 0.8

            # 内容匹配（权重较低，但可以多次累加）
            content_matches = content_lower.count(keyword_lower)
            if content_matches > 0:
                score += min(content_matches * 0.1, 0.5)

        return min(score, 2.0)  # 限制最高分数

    def _calculate_pattern_score(self, file_info: FileInfo) -> float:
        """计算文件名模式分数"""
        score = 0.0
        file_name = file_info.name

        for pattern, weight in self.file_pattern_weights.items():
            if re.match(pattern, file_name, re.IGNORECASE):
                score += weight

        return min(score, 1.0)

    def _calculate_dependency_score(
        self,
        file_info: FileInfo,
        dependency_graph: Dict[str, Set[str]],
        all_files: List[FileInfo],
    ) -> float:
        """计算依赖关系分数"""
        score = 0.0
        file_path_set = {f.path for f in all_files}

        # 被依赖数量（有多少其他文件依赖当前文件）
        dependents_in_project = len(file_info.dependents & file_path_set)
        score += min(dependents_in_project * 0.2, 1.0)

        # 导入的模块数量
        if file_info.imports:
            imports_in_project = len(file_info.imports & file_path_set)
            score += min(imports_in_project * 0.1, 0.5)

        # 核心文件加分
        core_files = ["main.py", "app.py", "__init__.py", "setup.py"]
        if any(core in file_info.name for core in core_files):
            score += 0.5

        return min(score, 2.0)

    def _calculate_recency_score(
        self, file_info: FileInfo, current_time: float
    ) -> float:
        """计算修改时间分数"""
        # 计算文件修改时间与当前时间的差异（天）
        time_diff_days = (current_time - file_info.modified_time) / (24 * 60 * 60)

        # 最近的文件得分更高
        if time_diff_days < 1:  # 今天修改
            return 1.0
        elif time_diff_days < 7:  # 一周内修改
            return 0.8
        elif time_diff_days < 30:  # 一个月内修改
            return 0.6
        elif time_diff_days < 90:  # 三个月内修改
            return 0.4
        else:  # 更早修改
            return 0.2

    def get_file_statistics(self, files: List[FileInfo]) -> Dict[str, Any]:
        """获取文件统计信息"""
        if not files:
            return {}

        stats = {
            "total_files": len(files),
            "total_size": sum(f.size for f in files),
            "extensions": defaultdict(int),
            "avg_relevance": sum(f.relevance for f in files) / len(files),
            "most_recent": max(f.modified_time for f in files),
            "oldest": min(f.modified_time for f in files),
            "high_relevance_files": len([f for f in files if f.relevance > 0.7]),
            "files_with_dependencies": len([f for f in files if f.imports]),
        }

        # 统计扩展名分布
        for file_info in files:
            stats["extensions"][file_info.extension] += 1

        return dict(stats)

    def export_selection_results(
        self, files: List[FileInfo], output_format: str = "json"
    ) -> str:
        """导出选择结果"""
        results = {
            "selected_files": [],
            "statistics": self.get_file_statistics(files),
            "selection_time": time.time(),
        }

        for file_info in files:
            results["selected_files"].append(
                {
                    "path": file_info.path,
                    "name": file_info.name,
                    "extension": file_info.extension,
                    "size": file_info.size,
                    "modified_time": file_info.modified_time,
                    "relevance": file_info.relevance,
                    "imports": list(file_info.imports),
                    "dependents": list(file_info.dependents),
                }
            )

        if output_format.lower() == "json":
            import json

            return json.dumps(results, indent=2, ensure_ascii=False)
        elif output_format.lower() == "yaml":
            import yaml

            return yaml.dump(results, default_flow_style=False, allow_unicode=True)
        else:
            return str(results)

    def suggest_related_files(
        self,
        selected_files: List[FileInfo],
        all_files: List[FileInfo],
        max_suggestions: int = 10,
    ) -> List[FileInfo]:
        """建议相关文件"""
        if not selected_files:
            return []

        suggestions = []
        selected_paths = {f.path for f in selected_files}

        # 基于依赖关系建议
        for selected_file in selected_files:
            for dependency in selected_file.imports:
                for candidate_file in all_files:
                    if (
                        candidate_file.path not in selected_paths
                        and dependency in candidate_file.path
                        and candidate_file not in suggestions
                    ):
                        suggestions.append(candidate_file)

        # 基于文件名相似性建议
        for selected_file in selected_files:
            base_name = (
                selected_file.name.replace(".py", "")
                .replace("_test", "")
                .replace("test_", "")
            )
            for candidate_file in all_files:
                if (
                    candidate_file.path not in selected_paths
                    and candidate_file not in suggestions
                    and base_name in candidate_file.name
                ):
                    suggestions.append(candidate_file)

        # 按相关性排序并限制数量
        suggestions.sort(key=lambda f: f.relevance, reverse=True)
        return suggestions[:max_suggestions]
