#!/usr/bin/env python3
"""
阶段A协调器 - Phase 1-4: 静态分析与AI分析结合用户决策进行文件选择
整合完整的文件选择流程，为AI修复工作流准备选定的文件
"""

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from ..utils.path_resolver import get_path_resolver

# 导入阶段A相关组件
from .multilang_static_analyzer import MultilangStaticAnalyzer, StaticAnalysisResult


# 提供基本的类定义以确保系统可用
@dataclass
class AggregatedAnalysisResult:
    """聚合分析结果"""

    files: List[Dict[str, Any]] = field(default_factory=list)
    total_issues: int = 0
    issues_by_severity: Dict[str, int] = field(default_factory=dict)
    issues_by_type: Dict[str, int] = field(default_factory=dict)


@dataclass
class UserDecisionResult:
    """用户决策结果"""

    selected_files: List[str] = field(default_factory=list)
    decision_type: str = ""
    confidence: float = 0.0


# 尝试导入各组件，分别处理导入失败
logger = get_logger()

# 导入静态分析聚合器
try:
    from .static_analysis_aggregator import StaticAnalysisAggregator
except ImportError as e:
    logger.warning(f"静态分析聚合器导入失败: {e}")

    class StaticAnalysisAggregator:
        def aggregate_results(self, results):
            return AggregatedAnalysisResult()


# 导入AI文件选择器（这是关键组件，必须导入成功）
try:
    from .ai_file_selector import AIFileSelectionResult, AIFileSelector
except ImportError as e:
    logger.error(f"AI文件选择器导入失败: {e}")
    raise ImportError(f"AI文件选择器是必需组件，无法导入: {e}")

# 导入用户决策收集器
try:
    from .user_decision_collector import UserDecisionCollector
except ImportError as e:
    logger.warning(f"用户决策收集器导入失败: {e}")

    class UserDecisionCollector:
        def collect_decisions(self, file_selections, **kwargs):
            return UserDecisionResult()


@dataclass
class PhaseAResult:
    """阶段A执行结果"""

    project_path: str
    static_analysis_results: List[StaticAnalysisResult] = field(default_factory=list)
    aggregated_results: Dict[str, Any] = field(default_factory=dict)
    ai_file_selections: AIFileSelectionResult = field(
        default_factory=AIFileSelectionResult
    )
    user_decisions: Dict[str, Any] = field(default_factory=dict)
    final_selected_files: List[str] = field(default_factory=list)
    phase_a_summary: Dict[str, Any] = field(default_factory=dict)
    execution_success: bool = True
    execution_time: float = 0.0
    error_message: str = ""
    execution_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "project_path": self.project_path,
            "static_analysis_results": [
                result.to_dict() if hasattr(result, "to_dict") else str(result)
                for result in self.static_analysis_results
            ],
            "aggregated_results": self.aggregated_results,
            "ai_file_selections": (
                self.ai_file_selections.to_dict()
                if hasattr(self.ai_file_selections, "to_dict")
                else str(self.ai_file_selections)
            ),
            "user_decisions": self.user_decisions,
            "final_selected_files": self.final_selected_files,
            "phase_a_summary": self.phase_a_summary,
            "execution_success": self.execution_success,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "execution_timestamp": self.execution_timestamp,
            "total_files_selected": len(self.final_selected_files),
        }


@dataclass
class ProjectContext:
    """项目上下文信息"""

    project_path: str
    project_name: str
    total_files: int
    programming_languages: Dict[str, int] = field(default_factory=dict)
    project_structure: Dict[str, Any] = field(default_factory=dict)
    analysis_scope: str = "full"  # full, incremental, custom
    user_requirements: str = ""
    analysis_focus: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "total_files": self.total_files,
            "programming_languages": self.programming_languages,
            "project_structure": self.project_structure,
            "analysis_scope": self.analysis_scope,
            "user_requirements": self.user_requirements,
            "analysis_focus": self.analysis_focus,
        }


class PhaseACoordinator:
    """阶段A协调器 - Phase 1-4 完整流程整合

    阶段A包含四个子阶段：
    - Phase 1: 静态项目分析 (T004-T005)
    - Phase 2: AI项目分析 (T006-T008)
    - Phase 3: 用户决策与文件选择 (T009-T010)
    - Phase 4: 准备进入AI修复工作流
    """

    def __init__(self, config_manager=None):
        """初始化阶段A协调器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 初始化PathResolver
        self.path_resolver = get_path_resolver()

        # 获取配置
        self.config = self.config_manager.get("project_analysis", {})

        # 初始化各个组件
        self.static_analyzer = MultilangStaticAnalyzer()
        self.static_aggregator = StaticAnalysisAggregator()
        self.ai_file_selector = AIFileSelector()
        self.user_decision_collector = UserDecisionCollector()

        # 分析结果存储（使用PathResolver解析）
        results_dir_path = self.config.get(
            "analysis_results_dir", ".fix_backups/phase_a_results"
        )
        resolved_results_dir = self.path_resolver.resolve_path(results_dir_path)
        if not resolved_results_dir:
            # 如果解析失败，使用当前工作目录下的路径
            resolved_results_dir = Path.cwd() / results_dir_path
        self.results_dir = resolved_results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def execute_phase_a(
        self,
        project_path: str,
        user_requirements: str = "",
        analysis_focus: List[str] = None,
        interactive: bool = True,
        verbose: bool = False,
    ) -> PhaseAResult:
        """
        执行完整的阶段A流程

        Args:
            project_path: 项目路径
            user_requirements: 用户需求描述
            analysis_focus: 分析重点
            interactive: 是否启用交互模式
            verbose: 是否显示详细信息

        Returns:
            PhaseAResult: 阶段A执行结果
        """
        start_time = time.time()

        # 使用PathResolver解析项目路径
        resolved_project_path = self.path_resolver.resolve_path(project_path)
        if not resolved_project_path:
            raise FileNotFoundError(f"无法解析项目路径: {project_path}")

        project_path = resolved_project_path

        if not project_path.exists():
            raise FileNotFoundError(f"项目路径不存在: {project_path}")

        # 设置项目根目录到PathResolver
        self.path_resolver.set_project_root(project_path)

        if verbose:
            print(f"🚀 启动阶段A: 静态分析与AI分析结合用户决策进行文件选择")
            print(f"📁 项目路径: {project_path}")
            print(f"📋 用户需求: {user_requirements}")
            print("=" * 60)

        # 创建项目上下文
        project_context = self._create_project_context(
            project_path, user_requirements, analysis_focus or []
        )

        try:
            # Phase 1: 静态项目分析 (使用multilang_static_analyzer)
            if verbose:
                print("\n📍 Phase 1: 静态项目分析")
                print("   正在执行多语言静态分析...")

            static_results = self._execute_comprehensive_static_analysis(
                project_context, verbose
            )

            if verbose:
                total_issues = sum(
                    len(result.issues) if hasattr(result, "issues") else 0
                    for result in static_results
                )
                print(f"   ✅ 静态分析完成，发现 {total_issues} 个问题")

            # Phase 1.5: 项目运行和错误收集
            if verbose:
                print("\n📍 Phase 1.5: 项目运行分析")
                print("   正在尝试运行项目，收集运行时错误...")

            runtime_errors = self._execute_project_runtime_analysis(
                project_context, verbose
            )

            if verbose:
                print(f"   ✅ 运行分析完成，收集到 {len(runtime_errors)} 个运行时问题")

            # Phase 2: AI项目分析 (基于静态分析+运行错误+项目结构)
            if verbose:
                print("\n📍 Phase 2: AI文件智能筛选")
                print("   AI正在基于静态分析、运行错误和项目结构筛选重点文件...")

            ai_selections = self._execute_ai_intelligent_file_selection(
                project_context, static_results, runtime_errors, verbose
            )

            if verbose:
                print(
                    f"   ✅ AI筛选完成，建议重点分析 {len(ai_selections.selected_files) if hasattr(ai_selections, 'selected_files') else 0} 个文件"
                )

            # Phase 3: 用户决策与文件选择
            if verbose:
                print("\n📍 Phase 3: 用户审批确认")
                print("   请审核AI的文件筛选建议...")

            user_decisions = self._execute_user_approval_process(
                project_context,
                static_results,
                runtime_errors,
                ai_selections,
                interactive,
                verbose,
            )

            if verbose:
                print(
                    f"   ✅ 用户审批完成，最终确定 {len(user_decisions.get('final_files', []))} 个文件进行深度分析"
                )

            # Phase 4: 准备进入阶段B (AI深度问题分析)
            final_files = user_decisions.get("final_files", [])
            if not final_files and hasattr(ai_selections, "selected_files"):
                # 如果用户没有做出决策，使用AI的建议
                final_files = [file.file_path for file in ai_selections.selected_files]

            # 生成阶段A摘要
            phase_a_summary = self._generate_phase_a_summary(
                project_context,
                static_results,
                ai_selections,
                user_decisions,
                final_files,
            )

            execution_time = time.time() - start_time

            # 创建结果对象
            result = PhaseAResult(
                project_path=str(project_path),
                static_analysis_results=static_results,
                aggregated_results=(
                    static_results[0].to_dict()
                    if static_results and hasattr(static_results[0], "to_dict")
                    else {}
                ),
                ai_file_selections=ai_selections,
                user_decisions=user_decisions,
                final_selected_files=final_files,
                phase_a_summary=phase_a_summary,
                execution_success=True,
                execution_time=execution_time,
                execution_timestamp=datetime.now().isoformat(),
            )

            # 保存结果
            self._save_phase_a_result(result)

            if verbose:
                self._show_phase_a_summary(result)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"阶段A执行失败: {e}"
            self.logger.error(error_msg)

            if verbose:
                print(f"\n❌ {error_msg}")

            return PhaseAResult(
                project_path=str(project_path),
                execution_success=False,
                execution_time=execution_time,
                error_message=error_msg,
                execution_timestamp=datetime.now().isoformat(),
            )

    def _create_project_context(
        self, project_path: Path, user_requirements: str, analysis_focus: List[str]
    ) -> ProjectContext:
        """创建项目上下文"""
        # 扫描项目结构
        project_structure = self._scan_project_structure(project_path)
        programming_languages = self._detect_programming_languages(project_path)

        return ProjectContext(
            project_path=str(project_path),
            project_name=project_path.name,
            total_files=len(list(project_path.rglob("*"))),
            programming_languages=programming_languages,
            project_structure=project_structure,
            user_requirements=user_requirements,
            analysis_focus=analysis_focus,
        )

    def _scan_project_structure(self, project_path: Path) -> Dict[str, Any]:
        """扫描项目结构 - 生成完整的树状结构"""

        def build_tree_structure(root_path: Path, current_path: Path, max_depth: int = 3, current_depth: int = 0) -> Dict[str, Any]:
            """递归构建目录树结构"""
            if current_depth > max_depth:
                return {"type": "directory", "truncated": True, "children": {}}

            tree_node = {
                "type": "directory",
                "name": current_path.name,
                "path": str(current_path.relative_to(root_path)),
                "children": {},
                "file_count": 0,
                "subdir_count": 0,
                "depth": current_depth
            }

            try:
                items = []
                for item in current_path.iterdir():
                    # 跳过隐藏文件和特殊目录
                    if item.name.startswith(".") and item.name not in {".gitignore", ".dockerignore"}:
                        continue

                    if item.name in {"__pycache__", "node_modules", ".git", ".venv", "venv", "env"}:
                        continue

                    items.append(item)

                # 排序：目录在前，文件在后，然后按名称排序
                items.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

                for item in items:
                    rel_path = item.relative_to(root_path)

                    if item.is_file():
                        # 文件节点
                        file_info = {
                            "type": "file",
                            "name": item.name,
                            "path": str(rel_path),
                            "extension": item.suffix.lower(),
                            "size": item.stat().st_size if item.exists() else 0,
                            "language": self._detect_file_language(item.suffix.lower()),
                            "is_key_file": self._is_key_file(item.name.lower()),
                            "depth": current_depth + 1
                        }

                        # 读取文件内容的预览（仅对小文件）
                        if item.stat().st_size < 1024 * 10:  # 10KB以内的文件读取预览
                            try:
                                with open(item, 'r', encoding='utf-8', errors='ignore') as f:
                                    lines = f.readlines()
                                    file_info["preview_lines"] = len(lines)
                                    file_info["content_preview"] = "".join(lines[:5])  # 前5行预览
                            except Exception:
                                file_info["content_preview"] = ""

                        tree_node["children"][item.name] = file_info
                        tree_node["file_count"] += 1

                    elif item.is_dir():
                        # 递归处理子目录
                        child_tree = build_tree_structure(root_path, item, max_depth, current_depth + 1)
                        tree_node["children"][item.name] = child_tree
                        tree_node["subdir_count"] += 1
                        tree_node["file_count"] += child_tree.get("file_count", 0)
                        tree_node["subdir_count"] += child_tree.get("subdir_count", 0)

            except PermissionError:
                tree_node["error"] = "Permission denied"
            except Exception as e:
                tree_node["error"] = str(e)

            return tree_node

        # 构建完整的项目结构
        project_root = project_path
        tree_structure = build_tree_structure(project_root, project_root)

        # 统计信息
        total_files = 0
        total_dirs = 0
        files_by_extension = {}
        key_files = []
        language_distribution = {}

        def analyze_tree(node):
            nonlocal total_files, total_dirs, files_by_extension, key_files, language_distribution

            if node.get("type") == "file":
                total_files += 1
                ext = node.get("extension", "")
                if ext:
                    files_by_extension[ext] = files_by_extension.get(ext, 0) + 1

                lang = node.get("language", "")
                if lang:
                    language_distribution[lang] = language_distribution.get(lang, 0) + 1

                if node.get("is_key_file", False):
                    key_files.append(node.get("path", ""))

            elif node.get("type") == "directory":
                total_dirs += 1
                for child in node.get("children", {}).values():
                    analyze_tree(child)

        analyze_tree(tree_structure)

        # 生成完整的结构信息
        structure = {
            "tree": tree_structure,
            "statistics": {
                "total_files": total_files,
                "total_directories": total_dirs,
                "files_by_extension": files_by_extension,
                "key_files": key_files,
                "language_distribution": language_distribution,
                "project_depth": self._calculate_max_depth(tree_structure)
            },
            "metadata": {
                "project_name": project_path.name,
                "project_path": str(project_path),
                "scan_timestamp": datetime.now().isoformat(),
                "scanner_version": "1.0"
            }
        }

        return structure

    def _detect_file_language(self, extension: str) -> str:
        """根据文件扩展名检测编程语言"""
        language_map = {
            ".py": "python",
            ".js": "javascript", ".jsx": "javascript",
            ".ts": "typescript", ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp", ".h": "cpp", ".hpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".scala": "scala",
            ".html": "html", ".htm": "html",
            ".css": "css", ".scss": "css", ".sass": "css",
            ".json": "json",
            ".yaml": "yaml", ".yml": "yaml",
            ".xml": "xml",
            ".md": "markdown", ".markdown": "markdown",
            ".sh": "shell", ".bash": "shell", ".zsh": "shell",
            ".sql": "sql",
            ".dockerfile": "docker",
            ".toml": "toml",
            ".ini": "ini",
            ".cfg": "config",
            ".conf": "config"
        }
        return language_map.get(extension, "unknown")

    def _is_key_file(self, filename: str) -> bool:
        """判断是否为关键文件"""
        key_patterns = [
            "readme", "license", "changelog", "contributing", "install",
            "requirements", "package", "setup", "dockerfile", "makefile",
            "cmakelists", "build.gradle", "pom.xml", "go.mod", "cargo.toml",
            "gitignore", "dockerignore", "eslintrc", "prettierrc", "babelrc",
            "tsconfig", "webpack.config", "vite.config", "rollup.config",
            "main.py", "index.js", "app.py", "server.py", "client.py"
        ]
        return any(pattern in filename for pattern in key_patterns)

    def _calculate_max_depth(self, node: Dict[str, Any], current_depth: int = 0) -> int:
        """计算目录树的最大深度"""
        if node.get("type") == "file":
            return current_depth

        max_child_depth = current_depth
        for child in node.get("children", {}).values():
            child_depth = self._calculate_max_depth(child, current_depth + 1)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth

    def _detect_programming_languages(self, project_path: Path) -> Dict[str, int]:
        """检测项目使用的编程语言"""
        language_extensions = {
            "python": [".py"],
            "javascript": [".js", ".jsx", ".mjs"],
            "typescript": [".ts", ".tsx"],
            "java": [".java"],
            "go": [".go"],
            "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
            "csharp": [".cs"],
            "rust": [".rs"],
            "php": [".php"],
            "ruby": [".rb"],
            "html": [".html", ".htm"],
            "css": [".css", ".scss", ".sass"],
            "json": [".json"],
            "yaml": [".yaml", ".yml"],
            "markdown": [".md"],
        }

        language_counts = {}

        # 如果是单个文件，直接检测该文件的扩展名
        if project_path.is_file():
            ext = project_path.suffix.lower()
            for lang, extensions in language_extensions.items():
                if ext in extensions:
                    language_counts[lang] = 1
                    break
        else:
            # 如果是目录，遍历所有文件
            for file_path in project_path.rglob("*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    for lang, extensions in language_extensions.items():
                        if ext in extensions:
                            language_counts[lang] = language_counts.get(lang, 0) + 1
                            break

        return language_counts

    def _execute_static_analysis(
        self, project_context: ProjectContext, verbose: bool = False
    ) -> List[StaticAnalysisResult]:
        """执行静态项目分析 - Phase 1"""
        try:
            # 使用PathResolver解析项目路径
            resolved_project_path = self.path_resolver.resolve_path(
                project_context.project_path
            )
            if not resolved_project_path:
                self.logger.error(f"无法解析项目路径: {project_context.project_path}")
                return []

            project_path = resolved_project_path

            if project_path.is_file():
                # 如果是单个文件，获取文件所在目录
                static_results = self.static_analyzer.analyze_files(
                    [str(project_path)], verbose=verbose
                )
            else:
                # 如果是目录，分析整个项目
                static_results = self.static_analyzer.analyze_project(
                    str(project_path), verbose=verbose
                )

            # 转换为列表格式
            if isinstance(static_results, dict):
                static_results = list(static_results.values())

            return static_results if static_results else []

        except Exception as e:
            self.logger.error(f"静态分析执行失败: {e}")
            return []

    def _execute_ai_file_selection(
        self,
        project_context: ProjectContext,
        static_results: List[StaticAnalysisResult],
        verbose: bool = False,
    ) -> AIFileSelectionResult:
        """执行AI文件选择 - Phase 2"""
        try:
            # 使用AI文件选择器
            ai_selections = self.ai_file_selector.select_files(
                project_path=project_context.project_path,
                analysis_results=static_results,
                user_requirements=project_context.user_requirements,
                analysis_focus=project_context.analysis_focus,
            )

            return ai_selections

        except Exception as e:
            self.logger.error(f"AI文件选择失败: {e}")
            return AIFileSelectionResult()

    def _execute_user_decision_making(
        self,
        project_context: ProjectContext,
        static_results: List[StaticAnalysisResult],
        ai_selections: AIFileSelectionResult,
        interactive: bool = True,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """执行用户决策制定 - Phase 3"""
        try:
            if (
                interactive
                and hasattr(ai_selections, "selected_files")
                and ai_selections.selected_files
            ):
                # 使用用户决策收集器
                user_decisions = self.user_decision_collector.collect_decisions(
                    ai_selections=ai_selections,
                    project_context=project_context,
                    static_results=static_results,
                )
            else:
                # 非交互模式，使用AI的建议
                final_files = [
                    file.file_path
                    for file in getattr(ai_selections, "selected_files", [])
                ]
                user_decisions = {
                    "final_files": final_files,
                    "decision_type": "auto_accept",
                    "user_modifications": [],
                    "decision_summary": "自动接受AI建议",
                }

            return user_decisions

        except Exception as e:
            self.logger.error(f"用户决策制定失败: {e}")
            # 返回基本的决策结果
            final_files = [
                file.file_path for file in getattr(ai_selections, "selected_files", [])
            ]
            return {
                "final_files": final_files,
                "decision_type": "fallback",
                "error": str(e),
            }

    def _generate_phase_a_summary(
        self,
        project_context: ProjectContext,
        static_results: List[StaticAnalysisResult],
        ai_selections: AIFileSelectionResult,
        user_decisions: Dict[str, Any],
        final_files: List[str],
    ) -> Dict[str, Any]:
        """生成阶段A摘要"""
        total_issues = sum(
            len(result.issues) if hasattr(result, "issues") else 0
            for result in static_results
        )
        ai_selected_count = len(getattr(ai_selections, "selected_files", []))
        user_selected_count = len(final_files)

        return {
            "project_info": {
                "name": project_context.project_name,
                "path": project_context.project_path,
                "total_files": project_context.total_files,
                "languages": project_context.programming_languages,
            },
            "static_analysis_summary": {
                "total_issues": total_issues,
                "tools_used": len(static_results),
                "analysis_success": len(static_results) > 0,
            },
            "ai_selection_summary": {
                "ai_selected_files": ai_selected_count,
                "selection_confidence": getattr(
                    ai_selections, "selection_summary", {}
                ).get("confidence", 0.0),
                "selection_criteria": getattr(
                    ai_selections, "selection_summary", {}
                ).get("criteria", []),
            },
            "user_decision_summary": {
                "final_selected_files": user_selected_count,
                "decision_type": user_decisions.get("decision_type", "unknown"),
                "user_modifications": len(user_decisions.get("user_modifications", [])),
            },
            "phase_a_status": "completed",
            "ready_for_phase_b": user_selected_count > 0,
        }

    def _save_phase_a_result(self, result: PhaseAResult):
        """保存阶段A结果"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            result_file = self.results_dir / f"phase_a_result_{timestamp}.json"

            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(
                    result.to_dict(), f, indent=2, ensure_ascii=False, default=str
                )

            self.logger.info(f"阶段A结果已保存到: {result_file}")

        except Exception as e:
            self.logger.error(f"保存阶段A结果失败: {e}")

    def _show_phase_a_summary(self, result: PhaseAResult):
        """显示阶段A摘要"""
        print(f"\n🎉 阶段A执行完成!")
        print("=" * 60)

        summary = result.phase_a_summary

        print(f"📊 项目信息:")
        print(f"   • 项目名称: {summary['project_info']['name']}")
        print(f"   • 总文件数: {summary['project_info']['total_files']}")
        print(
            f"   • 编程语言: {', '.join(summary['project_info']['languages'].keys())}"
        )

        print(f"\n🔍 静态分析结果:")
        print(f"   • 发现问题: {summary['static_analysis_summary']['total_issues']} 个")
        print(f"   • 使用工具: {summary['static_analysis_summary']['tools_used']} 个")

        print(f"\n🤖 AI文件选择:")
        print(
            f"   • AI选择文件: {summary['ai_selection_summary']['ai_selected_files']} 个"
        )
        print(
            f"   • 选择置信度: {summary['ai_selection_summary']['selection_confidence']:.2f}"
        )

        print(f"\n👤 用户决策:")
        print(
            f"   • 最终选择文件: {summary['user_decision_summary']['final_selected_files']} 个"
        )
        print(f"   • 决策类型: {summary['user_decision_summary']['decision_type']}")

        print(f"\n📋 状态:")
        print(f"   • 阶段A状态: {summary['phase_a_status']}")
        print(
            f"   • 准备进入阶段B: {'✅ 是' if summary['ready_for_phase_b'] else '❌ 否'}"
        )

        if result.final_selected_files:
            print(f"\n📁 选中的文件:")
            for i, file_path in enumerate(
                result.final_selected_files[:10], 1
            ):  # 最多显示10个
                print(f"   {i}. {file_path}")
            if len(result.final_selected_files) > 10:
                print(f"   ... 还有 {len(result.final_selected_files) - 10} 个文件")

        print("=" * 60)

    def _execute_comprehensive_static_analysis(
        self, project_context: ProjectContext, verbose: bool = False
    ) -> List[StaticAnalysisResult]:
        """执行综合静态分析 - Phase 1 (使用multilang_static_analyzer)"""
        try:
            # 使用多语言静态分析器进行深度分析
            if verbose:
                print(f"   正在使用多语言静态分析器分析项目...")

            # 使用PathResolver解析项目路径
            resolved_project_path = self.path_resolver.resolve_path(
                project_context.project_path
            )
            if not resolved_project_path:
                self.logger.error(f"无法解析项目路径: {project_context.project_path}")
                return []

            project_path = resolved_project_path

            if project_path.is_file():
                # 如果是单个文件，获取文件所在目录
                static_results = self.static_analyzer.analyze_files(
                    [str(project_path)], verbose=verbose
                )
            else:
                # 如果是目录，分析整个项目
                static_results = self.static_analyzer.analyze_project(
                    str(project_path), verbose=verbose
                )

            # 转换为列表格式
            if isinstance(static_results, dict):
                static_results = list(static_results.values())

            if verbose and static_results:
                for result in static_results:
                    if hasattr(result, "issues"):
                        print(
                            f"   • {result.tool_name}: 发现 {len(result.issues)} 个问题"
                        )
                    else:
                        print(
                            f"   • {getattr(result, 'tool_name', 'Unknown tool')}: 分析完成"
                        )

            return static_results if static_results else []

        except Exception as e:
            self.logger.error(f"综合静态分析失败: {e}")
            if verbose:
                print(f"   ⚠️ 静态分析失败: {e}")
            return []

    def _execute_project_runtime_analysis(
        self, project_context: ProjectContext, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """执行多语言项目运行分析 - Phase 1.5"""
        try:
            runtime_errors = []
            project_path = Path(project_context.project_path)

            # 根据检测到的编程语言进行相应的运行分析
            languages = project_context.programming_languages

            if verbose:
                print(f"   检测到的编程语言: {', '.join(languages.keys())}")
                print(f"   开始多语言项目运行分析...")

            # Python项目运行分析
            if languages.get("python", 0) > 0:
                if verbose:
                    print("   📝 Python项目运行分析...")
                python_errors = self._analyze_python_project(project_path, verbose)
                runtime_errors.extend(python_errors)

            # JavaScript/Node.js项目运行分析
            if languages.get("javascript", 0) > 0 or languages.get("typescript", 0) > 0:
                if verbose:
                    print("   📝 JavaScript/TypeScript项目运行分析...")
                js_errors = self._analyze_javascript_project(project_path, verbose)
                runtime_errors.extend(js_errors)

            # Java项目运行分析
            if languages.get("java", 0) > 0:
                if verbose:
                    print("   📝 Java项目运行分析...")
                java_errors = self._analyze_java_project(project_path, verbose)
                runtime_errors.extend(java_errors)

            # Go项目运行分析
            if languages.get("go", 0) > 0:
                if verbose:
                    print("   📝 Go项目运行分析...")
                go_errors = self._analyze_go_project(project_path, verbose)
                runtime_errors.extend(go_errors)

            # C/C++项目运行分析
            if languages.get("cpp", 0) > 0:
                if verbose:
                    print("   📝 C/C++项目运行分析...")
                cpp_errors = self._analyze_cpp_project(project_path, verbose)
                runtime_errors.extend(cpp_errors)

            # Rust项目运行分析
            if languages.get("rust", 0) > 0:
                if verbose:
                    print("   📝 Rust项目运行分析...")
                rust_errors = self._analyze_rust_project(project_path, verbose)
                runtime_errors.extend(rust_errors)

            # PHP项目运行分析
            if languages.get("php", 0) > 0:
                if verbose:
                    print("   📝 PHP项目运行分析...")
                php_errors = self._analyze_php_project(project_path, verbose)
                runtime_errors.extend(php_errors)

            # Ruby项目运行分析
            if languages.get("ruby", 0) > 0:
                if verbose:
                    print("   📝 Ruby项目运行分析...")
                ruby_errors = self._analyze_ruby_project(project_path, verbose)
                runtime_errors.extend(ruby_errors)

            if verbose:
                print(f"   ✅ 多语言运行分析完成，共发现 {len(runtime_errors)} 个问题")

            return runtime_errors

        except Exception as e:
            self.logger.error(f"多语言项目运行分析失败: {e}")
            if verbose:
                print(f"   ⚠️ 运行分析失败: {e}")
            return []

    def _analyze_python_project(
        self, project_path: Path, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """分析Python项目"""
        runtime_errors = []

        # 查找主入口文件
        main_files = ["main.py", "app.py", "run.py", "index.py", "__main__.py"]

        for main_file in main_files:
            main_file_path = project_path / main_file
            if main_file_path.exists():
                if verbose:
                    print(f"      尝试运行: {main_file}")

                try:
                    import subprocess

                    result = subprocess.run(
                        ["python", str(main_file_path)],
                        capture_output=True,
                        text=True,
                        timeout=10,
                        cwd=project_path,
                    )

                    if result.stderr:
                        error_lines = result.stderr.strip().split("\n")
                        for line in error_lines:
                            if "Error" in line or "Exception" in line:
                                runtime_errors.append(
                                    {
                                        "file": main_file,
                                        "language": "python",
                                        "error_type": "runtime_error",
                                        "message": line.strip(),
                                        "full_output": result.stderr,
                                    }
                                )

                except subprocess.TimeoutExpired:
                    if verbose:
                        print(f"      ⚠️ {main_file} 运行超时")
                except Exception as e:
                    runtime_errors.append(
                        {
                            "file": main_file,
                            "language": "python",
                            "error_type": "execution_error",
                            "message": str(e),
                            "full_output": str(e),
                        }
                    )

                break

        # 检查Python语法错误
        for file_path in project_path.rglob("*.py"):
            if file_path.is_file() and not file_path.name.startswith("."):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code = f.read()
                    compile(code, str(file_path), "exec")
                except SyntaxError as e:
                    runtime_errors.append(
                        {
                            "file": str(file_path.relative_to(project_path)),
                            "language": "python",
                            "error_type": "syntax_error",
                            "message": f"第{e.lineno}行: {e.msg}",
                            "line_number": e.lineno,
                            "full_output": str(e),
                        }
                    )

        return runtime_errors

    def _analyze_javascript_project(
        self, project_path: Path, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """分析JavaScript/TypeScript项目"""
        runtime_errors = []

        # 检查package.json
        package_json = project_path / "package.json"
        if package_json.exists():
            try:
                import subprocess

                # 尝试npm检查
                result = subprocess.run(
                    ["npm", "install"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=project_path,
                )

                if result.returncode != 0:
                    runtime_errors.append(
                        {
                            "file": "package.json",
                            "language": "javascript",
                            "error_type": "dependency_error",
                            "message": "npm install失败",
                            "full_output": result.stderr,
                        }
                    )

                # 尝试运行脚本
                try:
                    with open(package_json, "r", encoding="utf-8") as f:
                        import json

                        package_data = json.load(f)

                    scripts = package_data.get("scripts", {})
                    if "start" in scripts:
                        if verbose:
                            print(f"      尝试运行: npm start")
                        result = subprocess.run(
                            ["npm", "start"],
                            capture_output=True,
                            text=True,
                            timeout=15,
                            cwd=project_path,
                        )
                        if result.returncode != 0:
                            runtime_errors.append(
                                {
                                    "file": "package.json",
                                    "language": "javascript",
                                    "error_type": "runtime_error",
                                    "message": "npm start失败",
                                    "full_output": result.stderr,
                                }
                            )

                except Exception as e:
                    runtime_errors.append(
                        {
                            "file": "package.json",
                            "language": "javascript",
                            "error_type": "config_error",
                            "message": f"package.json解析失败: {e}",
                            "full_output": str(e),
                        }
                    )

            except subprocess.TimeoutExpired:
                if verbose:
                    print("      ⚠️ npm操作超时")
            except FileNotFoundError:
                if verbose:
                    print("      ⚠️ npm未安装")

        return runtime_errors

    def _analyze_java_project(
        self, project_path: Path, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """分析Java项目"""
        runtime_errors = []

        try:
            import subprocess

            # 查找Java文件
            java_files = list(project_path.rglob("*.java"))

            if java_files:
                if verbose:
                    print(f"      找到 {len(java_files)} 个Java文件")

                # 尝试编译
                for java_file in java_files[:5]:  # 限制编译数量
                    try:
                        result = subprocess.run(
                            ["javac", str(java_file)],
                            capture_output=True,
                            text=True,
                            timeout=20,
                            cwd=project_path,
                        )

                        if result.returncode != 0:
                            runtime_errors.append(
                                {
                                    "file": str(java_file.relative_to(project_path)),
                                    "language": "java",
                                    "error_type": "compilation_error",
                                    "message": "编译失败",
                                    "full_output": result.stderr,
                                }
                            )

                    except subprocess.TimeoutExpired:
                        if verbose:
                            print(f"      ⚠️ {java_file.name} 编译超时")
                    except FileNotFoundError:
                        if verbose:
                            print("      ⚠️ javac未安装")
                        break

        except Exception as e:
            self.logger.error(f"Java项目分析失败: {e}")

        return runtime_errors

    def _analyze_go_project(
        self, project_path: Path, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """分析Go项目"""
        runtime_errors = []

        try:
            import subprocess

            # 查找main.go
            main_go = project_path / "main.go"
            if main_go.exists():
                if verbose:
                    print("      尝试编译Go项目")

                result = subprocess.run(
                    ["go", "build", "."],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    cwd=project_path,
                )

                if result.returncode != 0:
                    runtime_errors.append(
                        {
                            "file": "main.go",
                            "language": "go",
                            "error_type": "compilation_error",
                            "message": "Go编译失败",
                            "full_output": result.stderr,
                        }
                    )

            # 尝试go mod tidy
            go_mod = project_path / "go.mod"
            if go_mod.exists():
                result = subprocess.run(
                    ["go", "mod", "tidy"],
                    capture_output=True,
                    text=True,
                    timeout=15,
                    cwd=project_path,
                )
                if result.returncode != 0:
                    runtime_errors.append(
                        {
                            "file": "go.mod",
                            "language": "go",
                            "error_type": "dependency_error",
                            "message": "Go依赖管理失败",
                            "full_output": result.stderr,
                        }
                    )

        except subprocess.TimeoutExpired:
            if verbose:
                print("      ⚠️ Go操作超时")
        except FileNotFoundError:
            if verbose:
                print("      ⚠️ Go未安装")
        except Exception as e:
            self.logger.error(f"Go项目分析失败: {e}")

        return runtime_errors

    def _analyze_cpp_project(
        self, project_path: Path, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """分析C/C++项目"""
        runtime_errors = []

        try:
            import subprocess

            # 查找C/C++文件
            cpp_files = (
                list(project_path.rglob("*.cpp"))
                + list(project_path.rglob("*.cc"))
                + list(project_path.rglob("*.c"))
            )

            if cpp_files:
                if verbose:
                    print(f"      找到 {len(cpp_files)} 个C/C++文件")

                # 尝试编译第一个C++文件
                for cpp_file in cpp_files[:3]:
                    try:
                        result = subprocess.run(
                            ["g++", "-c", str(cpp_file)],
                            capture_output=True,
                            text=True,
                            timeout=20,
                            cwd=project_path,
                        )

                        if result.returncode != 0:
                            runtime_errors.append(
                                {
                                    "file": str(cpp_file.relative_to(project_path)),
                                    "language": "cpp",
                                    "error_type": "compilation_error",
                                    "message": "C++编译失败",
                                    "full_output": result.stderr,
                                }
                            )

                    except subprocess.TimeoutExpired:
                        if verbose:
                            print(f"      ⚠️ {cpp_file.name} 编译超时")
                    except FileNotFoundError:
                        if verbose:
                            print("      ⚠️ g++未安装")
                        break

        except Exception as e:
            self.logger.error(f"C/C++项目分析失败: {e}")

        return runtime_errors

    def _analyze_rust_project(
        self, project_path: Path, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """分析Rust项目"""
        runtime_errors = []

        try:
            import subprocess

            cargo_toml = project_path / "Cargo.toml"

            if cargo_toml.exists():
                if verbose:
                    print("      尝试编译Rust项目")

                result = subprocess.run(
                    ["cargo", "check"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=project_path,
                )

                if result.returncode != 0:
                    runtime_errors.append(
                        {
                            "file": "Cargo.toml",
                            "language": "rust",
                            "error_type": "compilation_error",
                            "message": "Rust编译检查失败",
                            "full_output": result.stderr,
                        }
                    )

        except subprocess.TimeoutExpired:
            if verbose:
                print("      ⚠️ Cargo操作超时")
        except FileNotFoundError:
            if verbose:
                print("      ⚠️ Cargo未安装")
        except Exception as e:
            self.logger.error(f"Rust项目分析失败: {e}")

        return runtime_errors

    def _analyze_php_project(
        self, project_path: Path, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """分析PHP项目"""
        runtime_errors = []

        try:
            import subprocess

            # 查找PHP文件
            php_files = list(project_path.rglob("*.php"))

            if php_files:
                if verbose:
                    print(f"      找到 {len(php_files)} 个PHP文件")

                # 尝试语法检查
                for php_file in php_files[:5]:
                    try:
                        result = subprocess.run(
                            ["php", "-l", str(php_file)],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            cwd=project_path,
                        )

                        if result.returncode != 0:
                            runtime_errors.append(
                                {
                                    "file": str(php_file.relative_to(project_path)),
                                    "language": "php",
                                    "error_type": "syntax_error",
                                    "message": "PHP语法错误",
                                    "full_output": result.stderr,
                                }
                            )

                    except subprocess.TimeoutExpired:
                        if verbose:
                            print(f"      ⚠️ {php_file.name} 语法检查超时")
                    except FileNotFoundError:
                        if verbose:
                            print("      ⚠️ PHP未安装")
                        break

        except Exception as e:
            self.logger.error(f"PHP项目分析失败: {e}")

        return runtime_errors

    def _analyze_ruby_project(
        self, project_path: Path, verbose: bool = False
    ) -> List[Dict[str, Any]]:
        """分析Ruby项目"""
        runtime_errors = []

        try:
            import subprocess

            # 查找Ruby文件
            ruby_files = list(project_path.rglob("*.rb"))

            if ruby_files:
                if verbose:
                    print(f"      找到 {len(ruby_files)} 个Ruby文件")

                # 尝试语法检查
                for ruby_file in ruby_files[:5]:
                    try:
                        result = subprocess.run(
                            ["ruby", "-c", str(ruby_file)],
                            capture_output=True,
                            text=True,
                            timeout=10,
                            cwd=project_path,
                        )

                        if result.returncode != 0:
                            runtime_errors.append(
                                {
                                    "file": str(ruby_file.relative_to(project_path)),
                                    "language": "ruby",
                                    "error_type": "syntax_error",
                                    "message": "Ruby语法错误",
                                    "full_output": result.stderr,
                                }
                            )

                    except subprocess.TimeoutExpired:
                        if verbose:
                            print(f"      ⚠️ {ruby_file.name} 语法检查超时")
                    except FileNotFoundError:
                        if verbose:
                            print("      ⚠️ Ruby未安装")
                        break

        except Exception as e:
            self.logger.error(f"Ruby项目分析失败: {e}")

        return runtime_errors

    def _execute_ai_intelligent_file_selection(
        self,
        project_context: ProjectContext,
        static_results: List[StaticAnalysisResult],
        runtime_errors: List[Dict[str, Any]],
        verbose: bool = False,
    ) -> AIFileSelectionResult:
        """执行AI智能文件筛选 - Phase 2"""
        try:
            # Phase 2.1: 收集用户见解和需求（在AI文件选择前）
            if verbose:
                print("   正在收集用户对项目的见解和疑问...")

            user_insights = self._collect_user_insights(project_context, verbose)

            # 将用户见解合并到项目上下文中
            if user_insights:
                project_context.user_requirements = (
                    self._merge_user_insights_with_requirements(
                        project_context.user_requirements, user_insights
                    )
                )
                if verbose:
                    print(f"   ✅ 已收集用户见解: {len(user_insights)} 个要点")

            # 准备AI分析的输入数据
            analysis_input = self._prepare_ai_analysis_input(
                project_context, static_results, runtime_errors
            )

            if verbose:
                print("   正在构建AI文件选择提示...")

            # 使用AI文件选择器进行智能筛选
            ai_selections = self.ai_file_selector.select_files(
                project_path=project_context.project_path,
                analysis_results=static_results,
                user_requirements=project_context.user_requirements,
                analysis_focus=project_context.analysis_focus,
                runtime_errors=runtime_errors,
                project_structure=project_context.project_structure,
            )

            return ai_selections

        except Exception as e:
            self.logger.error(f"AI智能文件筛选失败: {e}")
            if verbose:
                print(f"   ⚠️ AI文件筛选失败: {e}")
            return AIFileSelectionResult()

    def _prepare_ai_analysis_input(
        self,
        project_context: ProjectContext,
        static_results: List[StaticAnalysisResult],
        runtime_errors: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """准备AI分析的输入数据"""
        input_data = {
            "project_context": project_context.to_dict(),
            "static_analysis_summary": {},
            "runtime_errors": runtime_errors,
            "key_findings": [],
        }

        # 汇总静态分析结果
        total_issues = 0
        issues_by_file = {}
        for result in static_results:
            if hasattr(result, "issues") and result.issues:
                tool_name = getattr(result, "tool_name", "unknown")
                for issue in result.issues:
                    file_path = getattr(issue, "file_path", "unknown")
                    if file_path not in issues_by_file:
                        issues_by_file[file_path] = []
                    issues_by_file[file_path].append(
                        {
                            "tool": tool_name,
                            "severity": getattr(issue, "severity", "unknown"),
                            "message": getattr(issue, "message", ""),
                            "line": getattr(issue, "line_number", None),
                        }
                    )
                    total_issues += 1

        input_data["static_analysis_summary"] = {
            "total_issues": total_issues,
            "issues_by_file": issues_by_file,
            "tools_used": [getattr(r, "tool_name", "unknown") for r in static_results],
        }

        # 识别关键发现
        if runtime_errors:
            input_data["key_findings"].append("发现运行时错误")
        if total_issues > 10:
            input_data["key_findings"].append("存在大量代码质量问题")

        # 识别有问题的文件
        problematic_files = set()
        for error in runtime_errors:
            problematic_files.add(error.get("file", ""))
        for file_path in issues_by_file.keys():
            if len(issues_by_file[file_path]) > 3:
                problematic_files.add(file_path)

        input_data["problematic_files"] = list(problematic_files)

        return input_data

    def _execute_user_approval_process(
        self,
        project_context: ProjectContext,
        static_results: List[StaticAnalysisResult],
        runtime_errors: List[Dict[str, Any]],
        ai_selections: AIFileSelectionResult,
        interactive: bool = True,
        verbose: bool = False,
    ) -> Dict[str, Any]:
        """执行用户审批流程 - Phase 3"""
        try:
            if not interactive:
                # 非交互模式，直接使用AI建议
                final_files = [
                    file.file_path
                    for file in getattr(ai_selections, "selected_files", [])
                ]
                return {
                    "final_files": final_files,
                    "decision_type": "auto_accept",
                    "user_modifications": [],
                    "decision_summary": "自动接受AI建议",
                }

            if verbose:
                print("   显示AI筛选结果，等待用户审批...")

            # 显示分析摘要
            self._show_analysis_summary(project_context, static_results, runtime_errors)

            # 显示AI建议
            if (
                hasattr(ai_selections, "selected_files")
                and ai_selections.selected_files
            ):
                print(
                    f"\n🤖 AI建议重点分析以下 {len(ai_selections.selected_files)} 个文件:"
                )
                for i, file_selection in enumerate(ai_selections.selected_files, 1):
                    reason = getattr(file_selection, "reason", "无特定原因")
                    confidence = getattr(file_selection, "confidence", 0.0)
                    priority = getattr(file_selection, "priority", "medium")
                    print(f"   {i}. {file_selection.file_path}")
                    print(f"      优先级: {priority}, 置信度: {confidence:.2f}")
                    print(f"      原因: {reason}")

                # 获取用户决策
                return self._collect_user_approval(ai_selections, project_context)
            else:
                print("   ⚠️ AI未提供文件建议")
                return {
                    "final_files": [],
                    "decision_type": "no_suggestion",
                    "decision_summary": "AI未提供文件选择建议",
                }

        except Exception as e:
            self.logger.error(f"用户审批流程失败: {e}")
            if verbose:
                print(f"   ⚠️ 用户审批流程失败: {e}")
            return {"final_files": [], "decision_type": "error", "error": str(e)}

    def _show_analysis_summary(
        self,
        project_context: ProjectContext,
        static_results: List[StaticAnalysisResult],
        runtime_errors: List[Dict[str, Any]],
    ):
        """显示分析摘要"""
        print(f"\n📊 项目分析摘要:")
        print(f"   • 项目: {project_context.project_name}")
        print(
            f"   • 编程语言: {', '.join(project_context.programming_languages.keys())}"
        )

        total_issues = sum(
            len(getattr(result, "issues", [])) for result in static_results
        )
        print(f"   • 静态分析问题: {total_issues} 个")
        print(f"   • 运行时错误: {len(runtime_errors)} 个")

        if runtime_errors:
            print(f"\n⚠️ 发现的运行时问题:")
            for error in runtime_errors[:5]:  # 最多显示5个
                print(
                    f"   • {error.get('file', 'unknown')}: {error.get('message', '')[:80]}..."
                )

    def _collect_user_approval(
        self, ai_selections: AIFileSelectionResult, project_context: ProjectContext
    ) -> Dict[str, Any]:
        """收集用户审批决策"""
        try:
            print(f"\n🤔 请对AI的文件筛选建议进行决策:")
            print(f"1. 接受AI建议")
            print(f"2. 自定义选择")
            print(f"3. 查看更多详情")
            print(f"4. 重新筛选")

            while True:
                try:
                    choice = input("\n请输入选择 (1-4): ").strip()

                    if choice == "1":
                        # 接受AI建议
                        final_files = [
                            file.file_path for file in ai_selections.selected_files
                        ]
                        return {
                            "final_files": final_files,
                            "decision_type": "accept_ai_suggestion",
                            "user_modifications": [],
                            "decision_summary": f"用户接受AI建议，选择{len(final_files)}个文件",
                        }

                    elif choice == "2":
                        # 自定义选择
                        return self._custom_file_selection(
                            ai_selections, project_context
                        )

                    elif choice == "3":
                        # 查看更多详情
                        self._show_detailed_analysis(ai_selections)
                        continue

                    elif choice == "4":
                        # 重新筛选
                        return self._retry_ai_selection(ai_selections, project_context)

                    else:
                        print("❌ 无效选择，请重新输入")

                except KeyboardInterrupt:
                    print("\n👋 用户取消操作")
                    return {
                        "final_files": [],
                        "decision_type": "cancelled",
                        "decision_summary": "用户取消操作",
                    }

        except Exception as e:
            self.logger.error(f"收集用户审批失败: {e}")
            return {
                "final_files": [
                    file.file_path for file in ai_selections.selected_files
                ],
                "decision_type": "fallback",
                "error": str(e),
            }

    def _custom_file_selection(
        self, ai_selections: AIFileSelectionResult, project_context: ProjectContext
    ) -> Dict[str, Any]:
        """自定义文件选择"""
        print(f"\n📝 自定义文件选择:")
        print(f"AI建议的文件列表:")

        for i, file_selection in enumerate(ai_selections.selected_files, 1):
            print(f"   {i}. {file_selection.file_path}")

        while True:
            try:
                selection = input(
                    "\n请输入要选择的文件编号，用逗号分隔 (例如: 1,3,5): "
                ).strip()
                if not selection:
                    continue

                selected_indices = [int(x.strip()) for x in selection.split(",")]
                final_files = []

                for idx in selected_indices:
                    if 1 <= idx <= len(ai_selections.selected_files):
                        final_files.append(
                            ai_selections.selected_files[idx - 1].file_path
                        )
                    else:
                        print(f"⚠️ 跳过无效编号: {idx}")

                return {
                    "final_files": final_files,
                    "decision_type": "custom_selection",
                    "user_modifications": [f"选择了{len(final_files)}个文件"],
                    "decision_summary": f"用户自定义选择{len(final_files)}个文件",
                }

            except ValueError:
                print("❌ 输入格式错误，请输入数字编号，用逗号分隔")
            except KeyboardInterrupt:
                return {
                    "final_files": [],
                    "decision_type": "cancelled",
                    "decision_summary": "用户取消自定义选择",
                }

    def _show_detailed_analysis(self, ai_selections: AIFileSelectionResult):
        """显示详细分析信息"""
        print(f"\n📋 详细分析信息:")
        for file_selection in ai_selections.selected_files:
            print(f"\n📄 文件: {file_selection.file_path}")
            print(f"   优先级: {getattr(file_selection, 'priority', 'unknown')}")
            print(f"   置信度: {getattr(file_selection, 'confidence', 0.0):.2f}")
            print(f"   原因: {getattr(file_selection, 'reason', '无')}")

            key_issues = getattr(file_selection, "key_issues", [])
            if key_issues:
                print(f"   关键问题:")
                for issue in key_issues:
                    print(f"     • {issue}")

    def _retry_ai_selection(
        self, ai_selections: AIFileSelectionResult, project_context: ProjectContext
    ) -> Dict[str, Any]:
        """重新AI选择"""
        print(f"\n🔄 重新进行AI筛选...")
        # 这里可以重新调用AI选择，暂时使用原始结果
        final_files = [file.file_path for file in ai_selections.selected_files]
        return {
            "final_files": final_files,
            "decision_type": "retry_ai",
            "user_modifications": ["用户要求重新筛选"],
            "decision_summary": f"重新AI筛选，选择{len(final_files)}个文件",
        }

    def get_phase_a_result(self, result_id: str = None) -> Optional[PhaseAResult]:
        """获取阶段A结果"""
        try:
            if result_id:
                result_file = self.results_dir / f"phase_a_result_{result_id}.json"
            else:
                # 获取最新的结果
                result_files = list(self.results_dir.glob("phase_a_result_*.json"))
                if not result_files:
                    return None
                result_file = max(result_files, key=lambda f: f.stat().st_mtime)

            with open(result_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 从字典重建结果对象（简化版本）
            result = PhaseAResult(
                project_path=data.get("project_path", ""),
                final_selected_files=data.get("final_selected_files", []),
                phase_a_summary=data.get("phase_a_summary", {}),
                execution_success=data.get("execution_success", True),
                execution_time=data.get("execution_time", 0.0),
                error_message=data.get("error_message", ""),
                execution_timestamp=data.get("execution_timestamp", ""),
            )

            return result

        except Exception as e:
            self.logger.error(f"获取阶段A结果失败: {e}")
            return None

    def _collect_user_insights(
        self, project_context: ProjectContext, verbose: bool = False
    ) -> Dict[str, Any]:
        """收集用户对项目的见解和疑问"""
        user_insights = {}

        try:
            print(
                f"\n💭 为了更好地进行文件选择，请分享您对项目的见解:（若没有请回车跳过）"
            )
            print("=" * 50)

            # 1. 项目重点关注区域
            focus_area = input(
                "1. 您最关注项目的哪些方面？(安全/性能/代码质量/业务逻辑/其他): "
            ).strip()
            if focus_area:
                user_insights["focus_area"] = focus_area

            # 2. 主要担忧
            concerns = input(
                "2. 对项目有什么主要担忧或问题？(例如：内存泄漏、安全漏洞、性能瓶颈等): "
            ).strip()
            if concerns:
                user_insights["concerns"] = concerns

            # 3. 特定文件关注
            specific_files = input(
                "3. 有特定需要关注的文件或模块吗？(多个文件用逗号分隔): "
            ).strip()
            if specific_files:
                user_insights["specific_files"] = [
                    f.strip() for f in specific_files.split(",")
                ]

            # 4. 技术疑问
            questions = input(
                "4. 有什么技术疑问需要AI重点分析？(例如：某段代码的作用、潜在问题等): "
            ).strip()
            if questions:
                user_insights["technical_questions"] = questions

            # 5. 业务背景
            business_context = input(
                "5. 项目的业务背景或使用场景是什么？(可选): "
            ).strip()
            if business_context:
                user_insights["business_context"] = business_context

            # 6. 时间约束
            time_constraint = input(
                "6. 有什么时间约束或紧急程度吗？(低/中/高): "
            ).strip()
            if time_constraint:
                user_insights["time_constraint"] = time_constraint

            # 7. 质量标准
            quality_standard = input(
                "7. 对代码质量有什么特殊要求或标准吗？(可选): "
            ).strip()
            if quality_standard:
                user_insights["quality_standard"] = quality_standard

            # 8. 修复偏好
            fix_preference = input(
                "8. 希望AI提供什么样的修复建议？(保守/激进/最小改动): "
            ).strip()
            if fix_preference:
                user_insights["fix_preference"] = fix_preference

            if verbose and user_insights:
                print(f"\n✅ 已收集到 {len(user_insights)} 个方面的见解")
                for key, value in user_insights.items():
                    if isinstance(value, list):
                        print(f"   • {key}: {', '.join(value)}")
                    else:
                        print(f"   • {key}: {value}")

            return user_insights

        except KeyboardInterrupt:
            print("\n⚠️ 用户取消了输入收集")
            return {}
        except Exception as e:
            self.logger.error(f"收集用户见解失败: {e}")
            if verbose:
                print(f"   ⚠️ 收集用户见解时出错: {e}")
            return {}

    def _merge_user_insights_with_requirements(
        self, original_requirements: str, user_insights: Dict[str, Any]
    ) -> str:
        """将用户见解与原有需求合并"""
        try:
            # 构建用户见解文本
            insights_text = "\n\n用户补充见解和需求:\n"

            if "focus_area" in user_insights:
                insights_text += f"- 重点关注领域: {user_insights['focus_area']}\n"

            if "concerns" in user_insights:
                insights_text += f"- 主要担忧: {user_insights['concerns']}\n"

            if "specific_files" in user_insights:
                insights_text += (
                    f"- 特定关注文件: {', '.join(user_insights['specific_files'])}\n"
                )

            if "technical_questions" in user_insights:
                insights_text += f"- 技术疑问: {user_insights['technical_questions']}\n"

            if "business_context" in user_insights:
                insights_text += f"- 业务背景: {user_insights['business_context']}\n"

            if "time_constraint" in user_insights:
                insights_text += f"- 时间约束: {user_insights['time_constraint']}\n"

            if "quality_standard" in user_insights:
                insights_text += f"- 质量标准: {user_insights['quality_standard']}\n"

            if "fix_preference" in user_insights:
                insights_text += f"- 修复偏好: {user_insights['fix_preference']}\n"

            # 合并原有需求和用户见解
            if original_requirements:
                merged_requirements = original_requirements + insights_text
            else:
                merged_requirements = insights_text.strip()

            return merged_requirements

        except Exception as e:
            self.logger.error(f"合并用户见解失败: {e}")
            # 如果合并失败，返回原始需求
            return original_requirements
