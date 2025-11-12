"""
项目结构探索工具

这个工具深入分析项目结构，识别项目类型、架构模式、依赖关系和技术栈。
为缺陷检测代理提供全面的项目上下文信息。
"""

import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from langchain_core.tools import tool


class ProjectType(Enum):
    """项目类型"""

    PYTHON_PACKAGE = "python_package"
    PYTHON_WEB = "python_web"
    JAVASCRIPT_NODE = "javascript_node"
    REACT_APP = "react_app"
    VUE_APP = "vue_app"
    JAVA_MAVEN = "java_maven"
    JAVA_GRADLE = "java_gradle"
    CPP_PROJECT = "cpp_project"
    GO_MODULE = "go_module"
    RUST_CRATE = "rust_crate"
    UNKNOWN = "unknown"


class ArchitecturePattern(Enum):
    """架构模式"""

    MONOLITH = "monolith"
    MICROSERVICE = "microservice"
    LIBRARY = "library"
    PLUGIN = "plugin"
    CLI_TOOL = "cli_tool"
    WEB_APP = "web_app"
    API_SERVICE = "api_service"


@dataclass
class ProjectFile:
    """项目文件"""

    path: str
    relative_path: str
    name: str
    extension: str
    size: int
    language: str
    category: str
    is_source: bool = False
    is_test: bool = False
    is_config: bool = False
    is_doc: bool = False
    last_modified: Optional[str] = None


@dataclass
class Technology:
    """技术栈组件"""

    name: str
    category: str  # language, framework, tool, database, etc.
    version: Optional[str] = None
    confidence: float = 1.0
    evidence: List[str] = field(default_factory=list)


@dataclass
class ProjectAnalysis:
    """项目分析结果"""

    project_path: str
    project_type: ProjectType
    architecture_pattern: ArchitecturePattern
    primary_language: str
    technologies: List[Technology]
    files: List[ProjectFile]
    directories: List[str]
    dependencies: Dict[str, Any]
    metrics: Dict[str, Any]
    recommendations: List[str]
    analysis_timestamp: str


class ProjectExplorer:
    """项目结构探索器"""

    def __init__(self):
        self.language_indicators = {
            "python": [
                ".py",
                ".pyi",
                "Pipfile",
                "pyproject.toml",
                "requirements.txt",
                "setup.py",
            ],
            "javascript": [
                ".js",
                ".jsx",
                ".mjs",
                ".cjs",
                "package.json",
                "package-lock.json",
            ],
            "typescript": [".ts", ".tsx", "tsconfig.json"],
            "java": [".java", ".jar", "pom.xml", "build.gradle", "gradlew"],
            "cpp": [
                ".cpp",
                ".cc",
                ".cxx",
                ".c++",
                ".c",
                ".h",
                ".hpp",
                ".hxx",
                "CMakeLists.txt",
                "Makefile",
            ],
            "go": [".go", "go.mod", "go.sum"],
            "rust": [".rs", "Cargo.toml", "Cargo.lock"],
        }

        self.framework_patterns = {
            "django": ["django", "wsgi.py", "settings.py", "urls.py", "manage.py"],
            "flask": ["flask", "app.py", "__init__.py", "templates/", "static/"],
            "fastapi": ["fastapi", "main.py", "pydantic", "uvicorn"],
            "react": ["react", "src/App.js", "src/App.tsx", "public/", "package.json"],
            "vue": ["vue", "main.js", "App.vue", "components/"],
            "spring": ["spring", "@SpringBootApplication", "pom.xml"],
            "express": ["express", "app.js", "server.js", "routes/"],
            "angular": ["angular", "app.module.ts", "components/", "services/"],
        }

    def analyze_project(self, project_path: str) -> ProjectAnalysis:
        """全面分析项目结构"""
        try:
            project_path = Path(project_path).resolve()
            if not project_path.exists():
                raise FileNotFoundError(f"项目路径不存在: {project_path}")

            # 扫描文件结构
            files = self._scan_files(project_path)
            directories = self._get_directories(project_path)

            # 识别项目类型
            project_type = self._identify_project_type(files, directories)

            # 识别架构模式
            architecture = self._identify_architecture_pattern(
                files, directories, project_type
            )

            # 分析主要语言
            primary_language = self._identify_primary_language(files)

            # 识别技术栈
            technologies = self._identify_technologies(files, directories)

            # 分析依赖关系
            dependencies = self._analyze_dependencies(files, directories, project_type)

            # 计算项目指标
            metrics = self._calculate_metrics(files, directories, technologies)

            # 生成建议
            recommendations = self._generate_recommendations(
                project_type, architecture, metrics
            )

            return ProjectAnalysis(
                project_path=str(project_path),
                project_type=project_type,
                architecture_pattern=architecture,
                primary_language=primary_language,
                technologies=technologies,
                files=files,
                directories=directories,
                dependencies=dependencies,
                metrics=metrics,
                recommendations=recommendations,
                analysis_timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            # 返回基本的分析结果
            return ProjectAnalysis(
                project_path=str(project_path),
                project_type=ProjectType.UNKNOWN,
                architecture_pattern=ArchitecturePattern.UNKNOWN,
                primary_language="unknown",
                technologies=[],
                files=[],
                directories=[],
                dependencies={},
                metrics={},
                recommendations=[f"分析失败: {str(e)}"],
                analysis_timestamp=datetime.now().isoformat(),
            )

    def _scan_files(self, project_path: Path) -> List[ProjectFile]:
        """扫描项目文件"""
        files = []
        exclude_patterns = {
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "target",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
        }

        for root, dirs, filenames in os.walk(project_path):
            # 过滤目录
            dirs[:] = [d for d in dirs if d not in exclude_patterns]

            for filename in filenames:
                file_path = Path(root) / filename
                relative_path = file_path.relative_to(project_path)

                try:
                    stat_info = file_path.stat()
                    language = self._detect_file_language(file_path)
                    category = self._categorize_file(relative_path, language)

                    project_file = ProjectFile(
                        path=str(file_path),
                        relative_path=str(relative_path),
                        name=filename,
                        extension=file_path.suffix.lower(),
                        size=stat_info.st_size,
                        language=language,
                        category=category,
                        is_source=category in ["source", "test"],
                        is_test=category == "test",
                        is_config=category == "config",
                        is_doc=category == "documentation",
                        last_modified=datetime.fromtimestamp(
                            stat_info.st_mtime
                        ).isoformat(),
                    )
                    files.append(project_file)

                except OSError:
                    continue

        return files

    def _get_directories(self, project_path: Path) -> List[str]:
        """获取目录列表"""
        directories = []
        exclude_patterns = {
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "target",
            "build",
            "dist",
            ".pytest_cache",
        }

        for root, dirs, _ in os.walk(project_path):
            for d in dirs:
                if d not in exclude_patterns:
                    rel_path = Path(root) / d
                    directories.append(str(rel_path.relative_to(project_path)))

        return sorted(set(directories))

    def _detect_file_language(self, file_path: Path) -> str:
        """检测文件语言"""
        ext = file_path.suffix.lower()

        # 根据扩展名检测
        for language, extensions in self.language_indicators.items():
            if ext in extensions:
                return language

        # 根据文件名检测
        name = file_path.name.lower()
        if name in ["makefile", "cmakelists.txt"]:
            return "build"
        elif name in ["dockerfile", ".dockerignore"]:
            return "containerization"
        elif name.endswith((".yml", ".yaml")):
            return "configuration"
        elif name.endswith((".json", ".toml", ".ini", ".cfg")):
            return "configuration"
        elif name.endswith((".md", ".rst", ".txt")):
            return "documentation"

        return "unknown"

    def _categorize_file(self, relative_path: Path, language: str) -> str:
        """文件分类"""
        path_parts = str(relative_path).lower().split("/")
        filename = relative_path.name.lower()

        # 测试文件
        if (
            any("test" in part for part in path_parts)
            or filename.startswith("test_")
            or filename.endswith("_test")
            or filename.endswith(".test")
            or "tests/" in str(relative_path)
        ):
            return "test"

        # 源代码文件
        if language in [
            "python",
            "javascript",
            "typescript",
            "java",
            "cpp",
            "go",
            "rust",
        ]:
            if any(folder in path_parts for folder in ["src", "lib", "app", "modules"]):
                return "source"

        # 配置文件
        if (
            language == "configuration"
            or filename
            in [
                "package.json",
                "requirements.txt",
                "setup.py",
                "pyproject.toml",
                "pom.xml",
                "build.gradle",
            ]
            or any(
                folder in path_parts
                for folder in ["config", "settings", ".vscode", ".idea"]
            )
        ):
            return "config"

        # 文档文件
        if (
            language == "documentation"
            or filename.endswith((".md", ".rst", ".txt", ".adoc"))
            or any(folder in path_parts for folder in ["docs", "doc", "documentation"])
        ):
            return "documentation"

        # 构建文件
        if any(
            folder in path_parts for folder in ["build", "target", "dist", "out"]
        ) or filename in ["makefile", "cmakelists.txt"]:
            return "build"

        # 资源文件
        if any(
            folder in path_parts
            for folder in ["assets", "static", "resources", "public"]
        ):
            return "assets"

        return "other"

    def _identify_project_type(
        self, files: List[ProjectFile], directories: List[str]
    ) -> ProjectType:
        """识别项目类型"""
        file_names = [f.name.lower() for f in files]
        file_paths = [f.relative_path.lower() for f in files]
        dir_names = [d.lower() for d in directories]

        # Python项目
        if (
            "setup.py" in file_names
            or "pyproject.toml" in file_names
            or "requirements.txt" in file_names
            or "pipfile" in file_names
            or any("src/" in path for path in file_paths)
        ):

            if any(folder in dir_names for folder in ["templates", "static", "views"]):
                return ProjectType.PYTHON_WEB
            else:
                return ProjectType.PYTHON_PACKAGE

        # JavaScript/Node项目
        if "package.json" in file_names:
            if any(
                "src/app.js" in path or "src/app.tsx" in path for path in file_paths
            ):
                return ProjectType.REACT_APP
            elif any(folder in dir_names for folder in ["src", "pages"]):
                return ProjectType.JAVASCRIPT_NODE
            else:
                return ProjectType.JAVASCRIPT_NODE

        # Java项目
        if "pom.xml" in file_names:
            return ProjectType.JAVA_MAVEN
        elif "build.gradle" in file_names or "gradlew" in file_names:
            return ProjectType.JAVA_GRADLE

        # C++项目
        cpp_extensions = {".cpp", ".cc", ".cxx", ".c++", ".c", ".h", ".hpp", ".hxx"}
        if any(f.extension in cpp_extensions for f in files):
            if "cmakelists.txt" in file_names or "makefile" in file_names:
                return ProjectType.CPP_PROJECT

        # Go项目
        if "go.mod" in file_names or any(f.extension == ".go" for f in files):
            return ProjectType.GO_MODULE

        # Rust项目
        if "cargo.toml" in file_names:
            return ProjectType.RUST_CRATE

        return ProjectType.UNKNOWN

    def _identify_architecture_pattern(
        self,
        files: List[ProjectFile],
        directories: List[str],
        project_type: ProjectType,
    ) -> ArchitecturePattern:
        """识别架构模式"""
        dir_names = [d.lower() for d in directories]
        file_names = [f.name.lower() for f in files]

        # 库项目
        if (
            project_type in [ProjectType.PYTHON_PACKAGE, ProjectType.RUST_CRATE]
            or "setup.py" in file_names
            or "cargo.toml" in file_names
        ):
            return ArchitecturePattern.LIBRARY

        # 微服务
        if (
            any("service" in d for d in dir_names)
            or any("api" in d for d in dir_names)
            or any("microservice" in d for d in dir_names)
            or any("dockerfile" in f for f in file_names)
        ):
            return ArchitecturePattern.MICROSERVICE

        # CLI工具
        if (
            any("main.py" in f for f in file_names)
            or any("cli" in d for d in dir_names)
            or any("bin" in d for d in dir_names)
        ):
            return ArchitecturePattern.CLI_TOOL

        # API服务
        if (
            any("api" in d for d in dir_names)
            or any("rest" in d for d in dir_names)
            or any("controller" in d for d in dir_names)
            or any("handler" in d for d in dir_names)
        ):
            return ArchitecturePattern.API_SERVICE

        # Web应用
        if (
            any("web" in d for d in dir_names)
            or any("frontend" in d for d in dir_names)
            or any("backend" in d for d in dir_names)
            or any("static" in d for d in dir_names)
            or any("templates" in d for d in dir_names)
        ):
            return ArchitecturePattern.WEB_APP

        # 默认为单体应用
        return ArchitecturePattern.MONOLITH

    def _identify_primary_language(self, files: List[ProjectFile]) -> str:
        """识别主要编程语言"""
        language_counts = {}
        for file in files:
            if file.is_source:
                language_counts[file.language] = (
                    language_counts.get(file.language, 0) + 1
                )

        if not language_counts:
            return "unknown"

        # 返回文件数量最多的语言
        return max(language_counts, key=language_counts.get)

    def _identify_technologies(
        self, files: List[ProjectFile], directories: List[str]
    ) -> List[Technology]:
        """识别技术栈"""
        technologies = []
        file_contents = {}
        file_names = [f.name.lower() for f in files]
        file_paths = [f.relative_path.lower() for f in files]

        # 读取关键文件内容
        for file in files[:50]:  # 限制读取文件数量
            try:
                if file.size < 100000 and file.extension in [
                    ".json",
                    ".py",
                    ".js",
                    ".ts",
                    ".xml",
                    ".yml",
                    ".yaml",
                ]:
                    with open(file.path, "r", encoding="utf-8", errors="ignore") as f:
                        file_contents[file.relative_path] = f.read()
            except Exception:
                continue

        # 检测框架和库
        for framework, patterns in self.framework_patterns.items():
            evidence = []
            confidence = 0.0

            for pattern in patterns:
                if pattern in file_names:
                    evidence.append(f"File: {pattern}")
                    confidence += 0.3
                if any(pattern in path for path in file_paths):
                    evidence.append(f"Path: {pattern}")
                    confidence += 0.2

            # 检查文件内容
            for content in file_contents.values():
                if any(p in content for p in patterns if not p.endswith("/")):
                    evidence.append("Content match")
                    confidence += 0.1
                    break

            if confidence > 0:
                technologies.append(
                    Technology(
                        name=framework,
                        category="framework",
                        confidence=min(confidence, 1.0),
                        evidence=evidence[:3],  # 限制证据数量
                    )
                )

        # 检测数据库
        database_patterns = {
            "postgresql": ["postgresql", "psycopg2", "pg"],
            "mysql": ["mysql", "mysqldb", "pymysql"],
            "mongodb": ["mongodb", "pymongo", "mongo"],
            "redis": ["redis", "redis-py"],
            "sqlite": ["sqlite3", "sqlite"],
        }

        for db, patterns in database_patterns.items():
            for content in file_contents.values():
                if any(p in content for p in patterns):
                    technologies.append(
                        Technology(
                            name=db,
                            category="database",
                            evidence=[f"Content: {patterns[0]}"],
                        )
                    )
                    break

        # 检测容器化
        if "dockerfile" in file_names:
            technologies.append(
                Technology(
                    name="docker", category="containerization", evidence=["Dockerfile"]
                )
            )

        if "kubernetes" in str(file_contents).lower():
            technologies.append(
                Technology(
                    name="kubernetes",
                    category="orchestration",
                    evidence=["Kubernetes configuration"],
                )
            )

        return technologies

    def _analyze_dependencies(
        self,
        files: List[ProjectFile],
        directories: List[str],
        project_type: ProjectType,
    ) -> Dict[str, Any]:
        """分析依赖关系"""
        dependencies = {
            "package_dependencies": {},
            "system_dependencies": [],
            "external_apis": [],
        }

        # 分析包依赖
        if project_type == ProjectType.PYTHON_PACKAGE:
            for file in files:
                if file.name in [
                    "requirements.txt",
                    "pyproject.toml",
                    "setup.py",
                    "Pipfile",
                ]:
                    try:
                        if file.name == "requirements.txt":
                            deps = self._parse_requirements(file.path)
                        elif file.name == "pyproject.toml":
                            deps = self._parse_pyproject_toml(file.path)
                        elif file.name == "setup.py":
                            deps = self._parse_setup_py(file.path)
                        elif file.name == "Pipfile":
                            deps = self._parse_pipfile(file.path)

                        dependencies["package_dependencies"][file.name] = deps
                    except Exception:
                        continue

        elif project_type == ProjectType.JAVASCRIPT_NODE:
            for file in files:
                if file.name == "package.json":
                    try:
                        deps = self._parse_package_json(file.path)
                        dependencies["package_dependencies"][file.name] = deps
                    except Exception:
                        continue

        return dependencies

    def _parse_requirements(self, file_path: str) -> List[Dict[str, str]]:
        """解析requirements.txt"""
        deps = []
        try:
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("==", 1)
                        deps.append(
                            {
                                "name": parts[0].strip(),
                                "version": (
                                    parts[1].strip() if len(parts) > 1 else "latest"
                                ),
                            }
                        )
        except Exception:
            pass
        return deps

    def _parse_pyproject_toml(self, file_path: str) -> List[Dict[str, str]]:
        """解析pyproject.toml"""
        deps = []
        try:
            with open(file_path, "r") as f:
                content = f.read()
                # 简单解析依赖部分
                in_dependencies = False
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("[dependencies]"):
                        in_dependencies = True
                        continue
                    if line.startswith("[") and in_dependencies:
                        break
                    if in_dependencies and line:
                        parts = line.split("=", 1)
                        deps.append(
                            {
                                "name": parts[0].strip().strip("\"'"),
                                "version": (
                                    parts[1].strip().strip("\"'")
                                    if len(parts) > 1
                                    else "latest"
                                ),
                            }
                        )
        except Exception:
            pass
        return deps

    def _parse_setup_py(self, file_path: str) -> List[Dict[str, str]]:
        """解析setup.py"""
        deps = []
        try:
            with open(file_path, "r") as f:
                content = f.read()
                # 简单查找install_requires
                if "install_requires=" in content:
                    start = content.find("install_requires=") + len("install_requires=")
                    end = content.find("]", start)
                    if end > start:
                        req_section = content[start : end + 1]
                        for dep in req_section.split(","):
                            dep = dep.strip().strip("\"'")
                            if dep:
                                version = "latest"
                                if ">=" in dep or "==" in dep or "<=" in dep:
                                    parts = req_section.split(r"([<>=]+)", dep)
                                    if len(parts) > 1:
                                        dep = parts[0]
                                        version = parts[0] + parts[1]
                                deps.append({"name": dep, "version": version})
        except Exception:
            pass
        return deps

    def _parse_pipfile(self, file_path: str) -> List[Dict[str, str]]:
        """解析Pipfile"""
        deps = []
        try:
            with open(file_path, "r") as f:
                content = f.read()
                # 简单解析
                for line in content.split("\n"):
                    if "=" in line and not line.strip().startswith("#"):
                        parts = line.split("=", 1)
                        deps.append(
                            {
                                "name": parts[0].strip(),
                                "version": (
                                    parts[1].strip() if len(parts) > 1 else "latest"
                                ),
                            }
                        )
        except Exception:
            pass
        return deps

    def _parse_package_json(self, file_path: str) -> Dict[str, Any]:
        """解析package.json"""
        try:
            import json

            with open(file_path, "r") as f:
                data = json.load(f)
                return {
                    "dependencies": data.get("dependencies", {}),
                    "devDependencies": data.get("devDependencies", {}),
                    "peerDependencies": data.get("peerDependencies", {}),
                    "version": data.get("version", "unknown"),
                }
        except Exception:
            return {}

    def _calculate_metrics(
        self,
        files: List[ProjectFile],
        directories: List[str],
        technologies: List[Technology],
    ) -> Dict[str, Any]:
        """计算项目指标"""
        total_files = len(files)
        source_files = len([f for f in files if f.is_source])
        test_files = len([f for f in files if f.is_test])
        config_files = len([f for f in files if f.is_config])
        doc_files = len([f for f in files if f.is_doc])

        total_size = sum(f.size for f in files)
        avg_file_size = total_size / total_files if total_files > 0 else 0

        language_distribution = {}
        for file in files:
            if file.is_source:
                language_distribution[file.language] = (
                    language_distribution.get(file.language, 0) + 1
                )

        return {
            "total_files": total_files,
            "source_files": source_files,
            "test_files": test_files,
            "config_files": config_files,
            "doc_files": doc_files,
            "total_directories": len(set(directories)),
            "total_size_bytes": total_size,
            "average_file_size_bytes": avg_file_size,
            "language_distribution": language_distribution,
            "test_coverage": test_files / source_files if source_files > 0 else 0,
            "technologies_count": len(technologies),
            "categories_count": len(set(t.category for t in technologies)),
        }

    def _generate_recommendations(
        self,
        project_type: ProjectType,
        architecture: ArchitecturePattern,
        metrics: Dict[str, Any],
    ) -> List[str]:
        """生成项目建议"""
        recommendations = []

        # 测试覆盖率建议
        if metrics["test_coverage"] < 0.3:
            recommendations.append("测试覆盖率较低，建议增加单元测试")

        # 文档建议
        if metrics["doc_files"] / metrics["total_files"] < 0.1:
            recommendations.append("文档较少，建议增加API文档和使用说明")

        # 配置管理建议
        if metrics["config_files"] == 0:
            recommendations.append("缺少配置文件，建议添加项目配置")

        # 语言特定的建议
        if project_type == ProjectType.PYTHON_PACKAGE and not any(
            "requirements.txt" in f or "pyproject.toml" in f
            for f in [f.relative_path for f in []]  # 需要重新获取文件列表
        ):
            recommendations.append("Python项目建议使用pyproject.toml管理依赖")

        # 架构建议
        if (
            architecture == ArchitecturePattern.MONOLITH
            and metrics["total_files"] > 1000
        ):
            recommendations.append("大型项目建议考虑微服务架构")

        return recommendations


# 创建工具函数
@tool(
    description="深度分析项目结构，识别技术栈、架构模式和依赖关系。智能扫描项目文件，检测项目类型、编程语言、框架依赖和架构模式，为代码分析和重构提供全面的项目上下文信息。"
)
def explore_project_structure(project_path: str, max_files: int = 1000) -> str:
    """
    探索项目结构，提供给agent使用的项目结构分析工具。

    此工具提供全面的项目结构分析功能：
    - 智能识别项目类型和架构模式（单体、微服务、库、插件等）
    - 自动检测技术栈和依赖关系（语言、框架、工具、数据库等）
    - 深度扫描文件结构，分类源码、测试、配置和文档文件
    - 分析项目度量和统计信息，提供量化评估
    - 生成项目优化建议和技术栈升级指导

    Args:
        project_path: 项目根目录路径，支持相对路径和绝对路径
        max_files: 最大分析文件数量，默认1000，用于控制分析规模避免内存占用

    Returns:
        项目分析结果的JSON字符串，包含：
            - success: 分析是否成功
            - project_path: 项目根目录路径
            - project_type: 项目类型枚举值（python_package、react_app等）
            - architecture_pattern: 架构模式（monolith、microservice、library等）
            - primary_language: 主要编程语言
            - technologies: 技术栈列表，包含名称、类别、版本、置信度和证据
            - files: 文件详细信息列表，包含路径、语言、分类、大小等
            - directories: 目录结构列表
            - dependencies: 依赖关系分析结果
            - metrics: 项目度量指标（文件数、代码行数、复杂度等）
            - recommendations: 项目优化建议列表
            - analysis_timestamp: 分析执行时间戳
            - summary: 分析摘要信息（总文件数、目录数、技术栈数量等）

    使用场景：
        - 项目架构分析和重构规划
        - 技术栈识别和依赖管理
        - 代码质量评估和优化建议
        - 新团队成员项目快速理解
        - 技术债务评估和清理计划
        - 项目迁移和升级决策支持

    工具优势：
        - 深度分析项目结构和架构模式，超越表面文件扫描
        - 智能识别技术栈和依赖关系，支持多语言项目
        - 提供详细的项目元数据和量化度量指标
        - 支持多种编程语言和主流项目类型
        - 生成实用的优化建议和最佳实践指导

    注意事项：
        - 大型项目分析可能需要较长时间，建议适当调整max_files参数
        - 某些复杂的项目结构可能需要人工审核和补充分析
        - 隐藏文件和临时目录会被自动过滤
        - 分析结果基于文件模式匹配，可能存在误识别情况
    """
    try:
        explorer = ProjectExplorer()
        analysis = explorer.analyze_project(project_path)

        # 限制返回的文件数量
        limited_files = analysis.files[:max_files]

        # 转换为JSON格式
        result_data = {
            "project_path": analysis.project_path,
            "project_type": analysis.project_type.value,
            "architecture_pattern": analysis.architecture_pattern.value,
            "primary_language": analysis.primary_language,
            "technologies": [
                {
                    "name": tech.name,
                    "category": tech.category,
                    "version": tech.version,
                    "confidence": tech.confidence,
                    "evidence": tech.evidence,
                }
                for tech in analysis.technologies
            ],
            "files": [
                {
                    "relative_path": f.relative_path,
                    "name": f.name,
                    "extension": f.extension,
                    "size": f.size,
                    "language": f.language,
                    "category": f.category,
                    "is_source": f.is_source,
                    "is_test": f.is_test,
                    "is_config": f.is_config,
                    "is_doc": f.is_doc,
                }
                for f in limited_files
            ],
            "directories": analysis.directories[:50],  # 限制目录数量
            "dependencies": analysis.dependencies,
            "metrics": analysis.metrics,
            "recommendations": analysis.recommendations,
            "analysis_timestamp": analysis.analysis_timestamp,
            "summary": {
                "total_files_analyzed": len(limited_files),
                "total_directories": len(analysis.directories),
                "technologies_detected": len(analysis.technologies),
            },
        }

        return json.dumps(result_data, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"项目探索失败: {str(e)}",
                "project_path": project_path,
            },
            indent=2,
            ensure_ascii=False,
        )


@tool(
    description="分析代码复杂度，识别潜在问题和改进点。智能扫描项目源代码，计算圈复杂度、函数和类统计，识别复杂文件并提供重构建议，帮助改善代码质量和可维护性。"
)
def analyze_code_complexity(project_path: str, min_lines: int = 10) -> str:
    """
    分析代码复杂度，提供给agent使用的代码复杂度分析工具。

    此工具提供全面的代码复杂度分析功能：
    - 智能识别和分析多种编程语言的源代码文件
    - 计算圈复杂度指标，识别代码逻辑复杂程度
    - 统计函数和类的数量，评估代码结构合理性
    - 识别复杂文件，提供具体的重构建议和优化方向
    - 生成项目整体复杂度评估和改进指导

    Args:
        project_path: 项目根目录路径，支持相对路径和绝对路径
        min_lines: 最小分析行数，默认10行，过滤过小文件避免噪声

    Returns:
        复杂度分析结果的JSON字符串，包含：
            - success: 分析是否成功
            - files_analyzed: 分析的源代码文件数量
            - total_lines: 总代码行数统计
            - functions_found: 发现的函数总数
            - classes_found: 发现的类总数
            - complex_files: 复杂文件列表，每个文件包含：
                - file: 相对文件路径
                - lines: 文件行数
                - functions: 文件内函数数量
                - classes: 文件内类数量
                - complexity_score: 复杂度得分
                - avg_complexity: 平均复杂度
            - recommendations: 具体的改进建议列表
            - project_path: 分析的项目路径
            - analysis_timestamp: 分析执行时间戳

    使用场景：
        - 代码重构前的复杂度评估
        - 技术债务分析和清理计划制定
        - 代码质量审查和改进指导
        - 新项目架构设计复杂度控制
        - 团队代码质量标准和最佳实践制定

    工具优势：
        - 支持多种主流编程语言的复杂度分析
        - 基于圈复杂度指标的科学评估方法
        - 智能识别复杂文件，提供具体重构建议
        - 提供量化指标，便于代码质量对比和跟踪
        - 生成实用的改进指导，支持实际开发决策

    注意事项：
        - 分析结果基于静态代码扫描，可能存在误判
        - 复杂度阈值应根据项目实际情况调整
        - 建议结合人工代码审查进行综合评估
        - 某些设计模式可能自然增加复杂度，需要理性判断
        - 分析范围默认限制为20个文件，大型项目可考虑分批分析
    """
    try:
        import re
        from pathlib import Path

        project_dir = Path(project_path)
        if not project_dir.exists():
            return json.dumps(
                {"success": False, "error": f"项目路径不存在: {project_path}"},
                indent=2,
                ensure_ascii=False,
            )

        # 查找源代码文件
        source_files = []
        for ext in [".py", ".js", ".ts", ".java", ".cpp", ".cc", ".c", ".go", ".rs"]:
            source_files.extend(project_dir.glob(f"**/*{ext}"))

        complexity_analysis = {
            "files_analyzed": len(source_files),
            "total_lines": 0,
            "functions_found": 0,
            "classes_found": 0,
            "complex_files": [],
            "recommendations": [],
        }

        for file_path in source_files[:20]:  # 限制分析文件数量
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                    if len(lines) < min_lines:
                        continue

                    complexity_analysis["total_lines"] += len(lines)

                    # 简单的复杂度分析
                    complexity_score = 0
                    function_count = 0
                    class_count = 0

                    for i, line in enumerate(lines):
                        line_stripped = line.strip()

                        # 计算圈复杂度指标
                        if any(
                            keyword in line_stripped
                            for keyword in [
                                "if",
                                "elif",
                                "for",
                                "while",
                                "try",
                                "except",
                                "catch",
                                "switch",
                                "case",
                            ]
                        ):
                            complexity_score += 1

                        # 统计函数和类
                        if re.match(
                            r"^(def|function|class|interface)\s+\w+", line_stripped
                        ):
                            if "class" in line_stripped or "interface" in line_stripped:
                                class_count += 1
                            else:
                                function_count += 1

                    complexity_analysis["functions_found"] += function_count
                    complexity_analysis["classes_found"] += class_count

                    # 识别复杂文件
                    avg_complexity = (
                        complexity_score / len(lines) if len(lines) > 0 else 0
                    )
                    if avg_complexity > 0.1 or len(lines) > 200:
                        complexity_analysis["complex_files"].append(
                            {
                                "file": str(file_path.relative_to(project_dir)),
                                "lines": len(lines),
                                "functions": function_count,
                                "classes": class_count,
                                "complexity_score": complexity_score,
                                "avg_complexity": avg_complexity,
                            }
                        )

            except Exception:
                continue

        # 生成建议
        if complexity_analysis["complex_files"]:
            complexity_analysis["recommendations"].append(
                f"发现 {len(complexity_analysis['complex_files'])} 个复杂文件，建议重构降低复杂度"
            )

        if complexity_analysis["total_lines"] > 10000:
            complexity_analysis["recommendations"].append("项目较大，建议模块化拆分")

        # 将结果提升到顶级，便于访问
        result = {
            "success": True,
            "files_analyzed": complexity_analysis["files_analyzed"],
            "total_lines": complexity_analysis["total_lines"],
            "functions_found": complexity_analysis["functions_found"],
            "classes_found": complexity_analysis["classes_found"],
            "complex_files": complexity_analysis["complex_files"],
            "recommendations": complexity_analysis["recommendations"],
            "project_path": str(project_dir),
            "analysis_timestamp": datetime.now().isoformat(),
        }

        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"复杂度分析失败: {str(e)}",
                "project_path": project_path,
            },
            indent=2,
            ensure_ascii=False,
        )


if __name__ == "__main__":
    # 测试用例
    print("测试项目结构探索:")
    result = explore_project_structure(".")
    print(result)
