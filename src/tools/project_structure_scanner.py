"""
项目结构扫描器 - T004.1
为AI分析提供基础数据的项目结构扫描工具
"""

import mimetypes
import os
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..utils.logger import get_logger

try:
    from .project_analysis_types import FileCategory, ProgrammingLanguage
except ImportError:
    # 如果project_analysis_types不可用，定义基本类型
    from enum import Enum

    class ProgrammingLanguage(Enum):
        PYTHON = "python"
        JAVASCRIPT = "javascript"
        TYPESCRIPT = "typescript"
        JAVA = "java"
        GO = "go"
        CPP = "cpp"
        CSHARP = "csharp"
        RUST = "rust"
        PHP = "php"
        RUBY = "ruby"
        SWIFT = "swift"
        KOTLIN = "kotlin"
        SCALA = "scala"
        HTML = "html"
        CSS = "css"
        JSON = "json"
        YAML = "yaml"
        XML = "xml"
        MARKDOWN = "markdown"
        SHELL = "shell"
        SQL = "sql"
        DOCKER = "docker"
        CONFIG = "config"
        OTHER = "other"

    class FileCategory(Enum):
        SOURCE_CODE = "source_code"
        CONFIG = "config"
        DOCUMENTATION = "documentation"
        TEST = "test"
        BUILD = "build"
        ASSET = "asset"
        OTHER = "other"


@dataclass
class ProjectStructure:
    """项目结构数据"""

    project_path: str
    total_files: int = 0
    total_directories: int = 0
    total_lines: int = 0
    file_extensions: Dict[str, int] = field(default_factory=dict)
    language_distribution: Dict[str, int] = field(default_factory=dict)
    category_distribution: Dict[str, int] = field(default_factory=dict)
    directory_tree: Dict[str, Any] = field(default_factory=dict)
    large_files: List[Dict[str, Any]] = field(default_factory=list)
    binary_files: List[str] = field(default_factory=list)
    scan_time: float = 0.0
    scan_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "project_path": self.project_path,
            "total_files": self.total_files,
            "total_directories": self.total_directories,
            "total_lines": self.total_lines,
            "file_extensions": self.file_extensions,
            "language_distribution": self.language_distribution,
            "category_distribution": self.category_distribution,
            "directory_tree": self.directory_tree,
            "large_files": self.large_files,
            "binary_files": self.binary_files,
            "scan_time": self.scan_time,
            "scan_timestamp": self.scan_timestamp,
        }


class ProjectStructureScanner:
    """项目结构扫描器"""

    def __init__(self, max_file_size_mb: int = 10, max_depth: int = 10):
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_depth = max_depth
        self.project_root_path = None  # 用于记录项目根路径，防止扫描到项目边界之外
        self.logger = get_logger()

        # 编程语言文件扩展名映射
        self.language_extensions = {
            ProgrammingLanguage.PYTHON: {".py", ".pyw", ".pyi", ".pyx", ".pyd"},
            ProgrammingLanguage.JAVASCRIPT: {".js", ".jsx", ".mjs", ".cjs"},
            ProgrammingLanguage.TYPESCRIPT: {".ts", ".tsx"},
            ProgrammingLanguage.JAVA: {".java", ".class", ".jar"},
            ProgrammingLanguage.GO: {".go"},
            ProgrammingLanguage.CPP: {
                ".cpp",
                ".cxx",
                ".cc",
                ".c",
                ".h",
                ".hpp",
                ".hxx",
            },
            ProgrammingLanguage.CSHARP: {".cs", ".csx"},
            ProgrammingLanguage.RUST: {".rs"},
            ProgrammingLanguage.PHP: {".php", ".phtml", ".php3", ".php4", ".php5"},
            ProgrammingLanguage.RUBY: {".rb", ".rbw"},
            ProgrammingLanguage.SWIFT: {".swift"},
            ProgrammingLanguage.KOTLIN: {".kt", ".kts"},
            ProgrammingLanguage.SCALA: {".scala", ".sc"},
            ProgrammingLanguage.HTML: {".html", ".htm", ".xhtml"},
            ProgrammingLanguage.CSS: {".css", ".scss", ".sass", ".less"},
            ProgrammingLanguage.JSON: {".json"},
            ProgrammingLanguage.YAML: {".yaml", ".yml"},
            ProgrammingLanguage.XML: {".xml", ".xsl", ".xslt"},
            ProgrammingLanguage.MARKDOWN: {".md", ".markdown"},
            ProgrammingLanguage.SHELL: {".sh", ".bash", ".zsh", ".fish", ".ps1"},
            ProgrammingLanguage.SQL: {".sql"},
            ProgrammingLanguage.DOCKER: {".dockerfile", "dockerfile"},
            ProgrammingLanguage.CONFIG: {
                ".ini",
                ".cfg",
                ".conf",
                ".toml",
                ".properties",
            },
        }

        # 文件类别映射
        self.category_extensions = {
            FileCategory.SOURCE_CODE: {
                ".py",
                ".js",
                ".ts",
                ".java",
                ".go",
                ".cpp",
                ".c",
                ".h",
                ".hpp",
                ".cs",
                ".rs",
                ".php",
                ".rb",
                ".swift",
                ".kt",
                ".scala",
                ".swift",
            },
            FileCategory.CONFIG: {
                ".yaml",
                ".yml",
                ".json",
                ".toml",
                ".ini",
                ".cfg",
                ".conf",
                ".xml",
                ".properties",
                ".env",
                ".dockerfile",
            },
            FileCategory.DOCUMENTATION: {
                ".md",
                ".markdown",
                ".rst",
                ".txt",
                ".doc",
                ".docx",
                ".pdf",
            },
            FileCategory.TEST: {
                ".test.js",
                ".test.ts",
                ".spec.js",
                ".spec.ts",
                "_test.py",
                "test_*.py",
                ".test.go",
                "_test.go",
            },
            FileCategory.BUILD: {
                "Makefile",
                "CMakeLists.txt",
                "build.gradle",
                "pom.xml",
                "package.json",
                "requirements.txt",
                "go.mod",
                "Cargo.toml",
            },
            FileCategory.ASSET: {
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".svg",
                ".ico",
                ".bmp",
                ".css",
                ".scss",
                ".sass",
                ".less",
            },
        }

        # 默认忽略的目录和文件
        self.ignore_patterns = {
            # 版本控制
            ".git",
            ".svn",
            ".hg",
            ".bzr",
            # 依赖目录
            "node_modules",
            "__pycache__",
            ".venv",
            "venv",
            "env",
            "target",
            "build",
            "dist",
            "out",
            ".next",
            ".nuxt",
            # IDE目录
            ".vscode",
            ".idea",
            ".eclipse",
            ".settings",
            # 临时文件
            ".tmp",
            ".temp",
            "*.tmp",
            "*.temp",
            ".cache",
            # 系统文件
            ".DS_Store",
            "Thumbs.db",
            ".DS_Store?",
            # 日志文件
            "*.log",
            ".logs",
            "logs",
            # 编译产物
            "*.pyc",
            "*.pyo",
            "*.class",
            "*.o",
            "*.so",
            "*.dylib",
            # 包管理器锁文件
            "package-lock.json",
            "yarn.lock",
            "poetry.lock",
            "Pipfile.lock",
        }

    def scan_project(self, project_path: str) -> ProjectStructure:
        """
        扫描项目结构

        Args:
            project_path: 项目根路径

        Returns:
            ProjectStructure: 项目结构数据
        """
        start_time = time.time()
        self.logger.info(f"开始扫描项目结构: {project_path}")

        # 转换为绝对路径并规范化
        project_path = os.path.abspath(project_path)
        self.project_root_path = project_path

        # 初始化项目结构对象
        structure = ProjectStructure(
            project_path=project_path,
            scan_timestamp=datetime.now().isoformat(),
        )

        # 检查项目路径是否存在
        if not os.path.exists(project_path):
            self.logger.error(f"项目路径不存在: {project_path}")
            raise ValueError(f"项目路径不存在: {project_path}")

        # 检查是否为目录
        if not os.path.isdir(project_path):
            self.logger.error(f"项目路径不是目录: {project_path}")
            raise ValueError(f"项目路径不是目录: {project_path}")

        # 执行扫描
        try:
            self._scan_directory_recursive(project_path, structure, current_depth=0)

            # 计算扫描时间
            structure.scan_time = time.time() - start_time

            # 生成目录树
            structure.directory_tree = self._build_directory_tree(project_path)

            self.logger.info(
                f"项目结构扫描完成: {structure.total_files}个文件, "
                f"{structure.total_directories}个目录, "
                f"耗时{structure.scan_time:.2f}秒"
            )

        except Exception as e:
            self.logger.error(f"项目结构扫描失败: {e}")
            raise

        return structure

    def _scan_directory_recursive(
        self, directory_path: str, structure: ProjectStructure, current_depth: int
    ) -> None:
        """
        递归扫描目录

        Args:
            directory_path: 当前目录路径
            structure: 项目结构对象
            current_depth: 当前深度
        """
        if current_depth > self.max_depth:
            self.logger.warning(
                f"达到最大扫描深度 {self.max_depth}，停止扫描: {directory_path}"
            )
            return

        # 检查是否超出项目边界
        if not self._is_within_project_bounds(directory_path):
            self.logger.warning(f"目录超出项目边界，停止扫描: {directory_path}")
            return

        try:
            for item in os.listdir(directory_path):
                item_path = os.path.join(directory_path, item)

                # 检查是否超出项目边界
                if not self._is_within_project_bounds(item_path):
                    self.logger.debug(f"路径超出项目边界，跳过: {item_path}")
                    continue

                # 检查是否应该忽略
                if self._should_ignore(item, item_path):
                    continue

                if os.path.isfile(item_path):
                    self._scan_file(item_path, structure)
                elif os.path.isdir(item_path):
                    structure.total_directories += 1
                    self._scan_directory_recursive(
                        item_path, structure, current_depth + 1
                    )

        except PermissionError:
            self.logger.warning(f"无权限访问目录: {directory_path}")
        except Exception as e:
            self.logger.error(f"扫描目录时出错 {directory_path}: {e}")

    def _scan_file(self, file_path: str, structure: ProjectStructure) -> None:
        """
        扫描单个文件

        Args:
            file_path: 文件路径
            structure: 项目结构对象
        """
        try:
            # 获取文件信息
            stat_info = os.stat(file_path)
            file_size = stat_info.st_size

            # 检查文件大小
            if file_size > self.max_file_size_bytes:
                structure.large_files.append(
                    {
                        "file_path": file_path,
                        "size_mb": file_size / (1024 * 1024),
                        "size_bytes": file_size,
                    }
                )
                self.logger.warning(
                    f"文件过大，跳过详细分析: {file_path} ({file_size / 1024 / 1024:.2f}MB)"
                )
                return

            # 获取文件扩展名
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()

            # 统计文件扩展名
            structure.file_extensions[ext] = structure.file_extensions.get(ext, 0) + 1

            # 判断是否为二进制文件
            if self._is_binary_file(file_path, ext):
                structure.binary_files.append(file_path)
                return

            # 识别编程语言
            language = self._identify_language(ext)
            if language:
                structure.language_distribution[language.value] = (
                    structure.language_distribution.get(language.value, 0) + 1
                )

            # 识别文件类别
            category = self._identify_category(file_path, ext)
            if category:
                structure.category_distribution[category.value] = (
                    structure.category_distribution.get(category.value, 0) + 1
                )

            # 统计代码行数（仅对文本文件）
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = sum(1 for _ in f)
                    structure.total_lines += lines
            except Exception as e:
                self.logger.debug(f"无法读取文件行数 {file_path}: {e}")

            structure.total_files += 1

        except Exception as e:
            self.logger.error(f"扫描文件时出错 {file_path}: {e}")

    def _should_ignore(self, item_name: str, item_path: str) -> bool:
        """
        检查是否应该忽略某个文件或目录

        Args:
            item_name: 项目名称
            item_path: 项目路径

        Returns:
            bool: 是否应该忽略
        """
        item_lower = item_name.lower()

        # 检查忽略模式
        for pattern in self.ignore_patterns:
            if pattern.startswith("*"):
                # 通配符模式
                if item_lower.endswith(pattern[1:]):
                    return True
            elif pattern.endswith("*"):
                # 前缀匹配
                if item_lower.startswith(pattern[:-1]):
                    return True
            else:
                # 精确匹配
                if item_lower == pattern:
                    return True

        # 检查隐藏文件（以.开头的文件）
        if item_name.startswith(".") and item_name not in {
            ".gitignore",
            ".dockerignore",
        }:
            return True

        return False

    def _is_within_project_bounds(self, path: str) -> bool:
        """
        检查路径是否在项目边界内

        Args:
            path: 要检查的路径

        Returns:
            bool: 是否在项目边界内
        """
        if not self.project_root_path:
            return True  # 如果项目根路径未设置，默认允许

        # 转换为绝对路径
        abs_path = os.path.abspath(path)
        abs_project_root = os.path.abspath(self.project_root_path)

        # 检查路径是否以项目根路径开头
        # 使用os.path.commonpath来正确处理路径比较
        common_path = os.path.commonpath([abs_project_root, abs_path])

        # 如果公共路径就是项目根路径，说明路径在项目内
        return common_path == abs_project_root

    def _is_binary_file(self, file_path: str, ext: str) -> bool:
        """
        判断是否为二进制文件

        Args:
            file_path: 文件路径
            ext: 文件扩展名

        Returns:
            bool: 是否为二进制文件
        """
        # 已知的二进制文件扩展名
        binary_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".bmp",
            ".webp",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".zip",
            ".tar",
            ".gz",
            ".rar",
            ".7z",
            ".dmg",
            ".exe",
            ".msi",
            ".so",
            ".dll",
            ".dylib",
            ".class",
            ".pyc",
            ".pyo",
            ".jar",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".wav",
            ".flac",
        }

        if ext in binary_extensions:
            return True

        # 使用mimetypes判断
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type and not mime_type.startswith("text/"):
            return True

        # 尝试读取文件前几个字节判断
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                if b"\x00" in chunk:  # 包含null字节通常是二进制文件
                    return True
        except Exception:
            return True  # 无法读取的文件默认当作二进制文件

        return False

    def _identify_language(self, ext: str) -> Optional[ProgrammingLanguage]:
        """
        根据文件扩展名识别编程语言

        Args:
            ext: 文件扩展名

        Returns:
            Optional[ProgrammingLanguage]: 编程语言枚举
        """
        for language, extensions in self.language_extensions.items():
            if ext in extensions:
                return language
        return None

    def _identify_category(self, file_path: str, ext: str) -> Optional[FileCategory]:
        """
        根据文件路径和扩展名识别文件类别

        Args:
            file_path: 文件路径
            ext: 文件扩展名

        Returns:
            Optional[FileCategory]: 文件类别枚举
        """
        file_name = os.path.basename(file_path).lower()

        # 特殊文件名判断
        if any(
            name in file_name
            for name in ["readme", "license", "changelog", "contributing"]
        ):
            return FileCategory.DOCUMENTATION

        if any(
            name in file_name for name in ["dockerfile", "makefile", "cmakelists.txt"]
        ):
            return FileCategory.BUILD

        if any(pattern in file_name for pattern in ["test", "spec"]):
            return FileCategory.TEST

        # 根据扩展名判断
        for category, extensions in self.category_extensions.items():
            if ext in extensions:
                return category

        return None

    def _build_directory_tree(
        self, project_path: str, max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        构建简化的目录树结构（用于展示）

        Args:
            project_path: 项目根路径
            max_depth: 最大深度

        Returns:
            Dict[str, Any]: 目录树结构
        """

        def build_tree_recursive(
            directory_path: str, current_depth: int
        ) -> Dict[str, Any]:
            if current_depth > max_depth:
                return {"type": "directory", "children": {}, "truncated": True}

            tree = {"type": "directory", "children": {}}

            try:
                items = []
                for item in os.listdir(directory_path):
                    item_path = os.path.join(directory_path, item)
                    if not self._should_ignore(item, item_path):
                        items.append((item, item_path))

                # 排序：目录在前，文件在后
                items.sort(key=lambda x: (not os.path.isdir(x[1]), x[0].lower()))

                for item_name, item_path in items:
                    if os.path.isdir(item_path):
                        tree["children"][item_name] = build_tree_recursive(
                            item_path, current_depth + 1
                        )
                    else:
                        tree["children"][item_name] = {
                            "type": "file",
                            "size": os.path.getsize(item_path),
                            "extension": os.path.splitext(item_name)[1].lower(),
                        }

            except PermissionError:
                tree["error"] = "Permission denied"
            except Exception as e:
                tree["error"] = str(e)

            return tree

        return build_tree_recursive(project_path, 0)

    def get_scan_summary(self, structure: ProjectStructure) -> Dict[str, Any]:
        """
        获取扫描结果摘要

        Args:
            structure: 项目结构数据

        Returns:
            Dict[str, Any]: 扫描摘要
        """
        # 主要编程语言
        main_languages = sorted(
            structure.language_distribution.items(), key=lambda x: x[1], reverse=True
        )[:5]

        # 主要文件类别
        main_categories = sorted(
            structure.category_distribution.items(), key=lambda x: x[1], reverse=True
        )

        # 文件大小统计
        total_size = sum(f["size_bytes"] for f in structure.large_files)

        return {
            "project_path": structure.project_path,
            "scan_summary": {
                "total_files": structure.total_files,
                "total_directories": structure.total_directories,
                "total_lines": structure.total_lines,
                "scan_time_seconds": round(structure.scan_time, 2),
            },
            "language_distribution": dict(main_languages),
            "category_distribution": dict(main_categories),
            "file_extensions": dict(
                sorted(
                    structure.file_extensions.items(), key=lambda x: x[1], reverse=True
                )[:10]
            ),
            "large_files_info": {
                "count": len(structure.large_files),
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "files": structure.large_files[:5],  # 只显示前5个大文件
            },
            "binary_files_count": len(structure.binary_files),
            "scan_timestamp": structure.scan_timestamp,
        }


# 便捷函数
def scan_project_structure(
    project_path: str, max_file_size_mb: int = 10, max_depth: int = 10
) -> Dict[str, Any]:
    """
    便捷的项目结构扫描函数

    Args:
        project_path: 项目根路径
        max_file_size_mb: 最大文件大小（MB）
        max_depth: 最大扫描深度

    Returns:
        Dict[str, Any]: 扫描结果摘要
    """
    scanner = ProjectStructureScanner(max_file_size_mb, max_depth)
    structure = scanner.scan_project(project_path)
    return scanner.get_scan_summary(structure)
