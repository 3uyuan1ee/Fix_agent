"""
项目动态分析工具

这个工具动态分析项目的运行状态、性能指标、资源使用情况，
为缺陷检测和修复提供运行时上下文信息。
"""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool


@dataclass
class ProcessInfo:
    """进程信息"""

    pid: int
    name: str
    command: str
    status: str
    cpu_percent: float
    memory_mb: float
    parent_pid: int
    create_time: str


@dataclass
class HealthCheck:
    """健康检查结果"""

    service_name: str
    status: str  # healthy, unhealthy, unknown
    response_time_ms: float
    error_message: Optional[str] = None
    url: Optional[str] = None


@dataclass
class PerformanceMetric:
    """性能指标"""

    name: str
    value: float
    unit: str
    timestamp: str
    category: str


@dataclass
class DynamicAnalysis:
    """动态分析结果"""

    project_path: str
    timestamp: str
    processes: List[ProcessInfo]
    health_checks: List[HealthCheck]
    performance_metrics: List[PerformanceMetric]
    dependencies: Dict[str, Any]
    runtime_environment: Dict[str, str]
    issues: List[Dict[str, Any]]
    recommendations: List[str]


class ProjectDynamicAnalyzer:
    """项目动态分析器"""

    def __init__(self):
        self.python_available = self._check_python()
        self.node_available = self._check_node()
        self.docker_available = self._check_docker()

    def _check_python(self) -> bool:
        """检查Python环境"""
        try:
            subprocess.run(["python", "--version"], capture_output=True, timeout=10)
            return True
        except:
            return False

    def _check_node(self) -> bool:
        """检查Node.js环境"""
        try:
            subprocess.run(["node", "--version"], capture_output=True, timeout=10)
            return True
        except:
            return False

    def _check_docker(self) -> bool:
        """检查Docker环境"""
        try:
            subprocess.run(["docker", "--version"], capture_output=True, timeout=10)
            return True
        except:
            return False

    def analyze_project_dynamics(self, project_path: str) -> DynamicAnalysis:
        """分析项目动态状态"""
        project_path = Path(project_path).resolve()

        processes = self._analyze_processes(project_path)
        health_checks = self._check_health(project_path)
        performance_metrics = self._measure_performance(project_path)
        dependencies = self._analyze_dependencies(project_path)
        runtime_env = self._get_runtime_environment(project_path)
        issues = self._detect_issues(project_path, processes, health_checks)
        recommendations = self._generate_recommendations(issues, performance_metrics)

        return DynamicAnalysis(
            project_path=str(project_path),
            timestamp=datetime.now().isoformat(),
            processes=processes,
            health_checks=health_checks,
            performance_metrics=performance_metrics,
            dependencies=dependencies,
            runtime_environment=runtime_env,
            issues=issues,
            recommendations=recommendations,
        )

    def _analyze_processes(self, project_path: Path) -> List[ProcessInfo]:
        """分析进程状态"""
        processes = []
        try:
            project_name = project_path.name.lower()
            project_path_str = str(project_path)

            # 跨平台进程分析
            if os.name == "nt":  # Windows系统
                processes = self._analyze_windows_processes(project_path)
            else:  # Unix/Linux/macOS
                processes = self._analyze_unix_processes(project_path)

            # 检查特定类型的项目进程（Python/Node等）
            if self._is_python_project(project_path):
                python_processes = self._check_python_processes(project_path)
                processes.extend(python_processes)

            if self._is_node_project(project_path):
                node_processes = self._check_node_processes(project_path)
                processes.extend(node_processes)

        except Exception as e:
            # 进程分析失败不影响主要功能
            pass

        return processes

    def _analyze_unix_processes(self, project_path: Path) -> List[ProcessInfo]:
        """Unix/Linux/macOS系统进程分析"""
        processes = []
        try:
            # 尝试使用ps命令
            result = subprocess.run(
                ["ps", "aux"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                for line in result.stdout.splitlines()[1:]:  # 跳过标题行
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        cmd = " ".join(parts[10:])
                        pid = int(parts[1])

                        if (
                            project_name in cmd.lower()
                            or project_path_str in cmd
                            or self._is_project_related_process(cmd, project_path)
                        ):

                            try:
                                cpu_usage = (
                                    float(parts[2])
                                    if parts[2].replace(".", "").isdigit()
                                    else 0.0
                                )
                                memory_kb = (
                                    float(parts[5])
                                    if parts[5].replace(".", "").isdigit()
                                    else 0.0
                                )
                                memory_mb = memory_kb / 1024
                            except (ValueError, IndexError):
                                cpu_usage = 0.0
                                memory_mb = 0.0

                            processes.append(
                                ProcessInfo(
                                    pid=pid,
                                    name=cmd.split()[0] if cmd else "unknown",
                                    command=cmd,
                                    status="running",
                                    cpu_percent=cpu_usage,
                                    memory_mb=memory_mb,
                                    parent_pid=(
                                        int(parts[2])
                                        if len(parts) > 2 and parts[2].isdigit()
                                        else 0
                                    ),
                                    create_time=datetime.now().isoformat(),
                                )
                            )

        except Exception:
            pass

        # 如果ps命令失败，尝试使用其他方法
        if not processes:
            processes = self._check_project_specific_processes(project_path)

        return processes

    def _analyze_windows_processes(self, project_path: Path) -> List[ProcessInfo]:
        """Windows系统进程分析"""
        processes = []
        try:
            # 使用tasklist命令
            result = subprocess.run(
                ["tasklist", "/fo", "csv"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                import csv
                import io

                csv_reader = csv.DictReader(io.StringIO(result.stdout))
                for row in csv_reader:
                    try:
                        cmd = row.get("Image Name", "")
                        pid = int(row.get("PID", "0"))
                        if cmd and pid > 0:
                            cmd_lower = cmd.lower()
                            if (
                                project_name in cmd_lower
                                or project_path_str in cmd_lower
                                or self._is_project_related_process(cmd, project_path)
                            ):

                                # 获取CPU和内存使用情况
                                cpu_usage = 0.0
                                memory_mb = 0.0
                                try:
                                    cpu_usage = float(row.get("% CPU", "0"))
                                    memory_kb = float(
                                        row.get("Mem Usage", "0").replace(" K", "")
                                    )
                                    if "K" in row.get("Mem Usage", ""):
                                        memory_mb = memory_kb
                                    else:
                                        memory_mb = memory_kb / 1024
                                except (ValueError, AttributeError):
                                    pass

                                processes.append(
                                    ProcessInfo(
                                        pid=pid,
                                        name=cmd.split("\\")[0] if "\\" in cmd else cmd,
                                        command=cmd,
                                        status="running",
                                        cpu_percent=cpu_usage,
                                        memory_mb=memory_mb,
                                        parent_pid=0,
                                        create_time=datetime.now().isoformat(),
                                    )
                                )

                    except (ValueError, KeyError):
                        continue

        except Exception:
            pass

        return processes

    def _check_project_specific_processes(
        self, project_path: Path
    ) -> List[ProcessInfo]:
        """检查项目特定的进程"""
        processes = []

        # 通用项目进程检查
        project_related_patterns = [
            [
                "python",
                "node",
                "npm",
                "yarn",
                "java",
                "mvn",
                "gradle",
                "go",
                "cargo",
                "docker",
            ],
            ["manage.py", "app.py", "server.py", "main.py", "index.js", "app.js"],
            ["webpack", "vite", "next", "react-scripts", "angular"],
        ]

        for pattern in project_related_patterns:
            try:
                if os.name == "nt":
                    # Windows: tasklist
                    result = subprocess.run(
                        ["tasklist", "/fo", "csv", "/fi", f'imagename eq "{pattern}"'],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                else:
                    # Unix/macOS: pgrep
                    result = subprocess.run(
                        ["pgrep", "-f", pattern],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                if result.returncode == 0:
                    self._parse_process_output(result.stdout, processes, project_path)

            except Exception:
                continue

        return processes

    def _is_project_related_process(self, command: str, project_path: Path) -> bool:
        """检查进程是否与项目相关"""
        command_lower = command.lower()
        project_str = str(project_path).lower()

        # 检查命令中是否包含项目路径
        if project_str in command_lower:
            return True

        # 检查常见的开发服务器进程
        dev_server_patterns = [
            "python manage.py runserver",  # Django
            "uvicorn",  # FastAPI/FastAPI
            "gunicorn",
            "npm start",
            "npm run dev",
            "yarn start",
            "yarn dev",
            "webpack-dev-server",
            "react-scripts start",
            "ng serve",  # Angular CLI
            "gradle bootRun",
            "mvn spring-boot:run",
            "docker-compose up",
        ]

        return any(pattern in command_lower for pattern in dev_server_patterns)

    def _check_python_processes(self, project_path: Path) -> List[ProcessInfo]:
        """检查Python相关进程"""
        processes = []
        try:
            # 检查是否有Django开发服务器
            manage_py = project_path / "manage.py"
            if manage_py.exists():
                result = subprocess.run(
                    ["pgrep", "-f", "manage.py runserver"],
                    capture_output=True,
                    text=True,
                )
                if result.stdout.strip():
                    for line in result.stdout.strip().split("\n"):
                        try:
                            pid = int(line)
                            processes.append(
                                ProcessInfo(
                                    pid=pid,
                                    name="manage.py",
                                    command="python manage.py runserver",
                                    status="running",
                                    cpu_percent=0.0,
                                    memory_mb=0.0,
                                    parent_pid=0,
                                    create_time=datetime.now().isoformat(),
                                )
                            )
                        except ValueError:
                            continue

        except Exception:
            pass

        return processes

    def _is_python_project(self, project_path: Path) -> bool:
        """检查是否为Python项目"""
        python_indicators = [
            "setup.py",
            "requirements.txt",
            "pyproject.toml",
            "Pipfile",
        ]
        return any(
            (project_path / indicator).exists() for indicator in python_indicators
        )

    def _check_health(self, project_path: Path) -> List[HealthCheck]:
        """检查服务健康状态"""
        health_checks = []

        # 检查Python项目健康
        if self._is_python_project(project_path):
            python_health = self._check_python_health(project_path)
            health_checks.extend(python_health)

        # 检查Node.js项目健康
        if self._is_node_project(project_path):
            node_health = self._check_node_health(project_path)
            health_checks.extend(node_health)

        return health_checks

    def _is_node_project(self, project_path: Path) -> bool:
        """检查是否为Node.js项目"""
        return (project_path / "package.json").exists()

    def _check_python_health(self, project_path: Path) -> List[HealthCheck]:
        """检查Python项目健康"""
        checks = []

        # 检查虚拟环境
        venv_indicators = [".venv", "venv", "env"]
        venv_exists = any(
            (project_path / indicator).exists() for indicator in venv_indicators
        )

        checks.append(
            HealthCheck(
                service_name="virtual_environment",
                status="healthy" if venv_exists else "warning",
                response_time_ms=0,
                error_message=None if venv_exists else "Virtual environment not found",
            )
        )

        # 检查依赖
        deps_files = ["requirements.txt", "pyproject.toml", "Pipfile"]
        deps_exist = any((project_path / f).exists() for f in deps_files)

        checks.append(
            HealthCheck(
                service_name="dependencies",
                status="healthy" if deps_exist else "warning",
                response_time_ms=0,
                error_message=None if deps_exist else "Dependency file not found",
            )
        )

        return checks

    def _check_node_health(self, project_path: Path) -> List[HealthCheck]:
        """检查Node.js项目健康"""
        checks = []

        # 检查package.json
        package_json = project_path / "package.json"
        if package_json.exists():
            try:
                import json

                with open(package_json, "r") as f:
                    package_data = json.load(f)

                # 检查是否有scripts
                scripts = package_data.get("scripts", {})
                has_scripts = bool(scripts)

                checks.append(
                    HealthCheck(
                        service_name="package.json",
                        status="healthy",
                        response_time_ms=0,
                        error_message=None,
                    )
                )

                # 检查是否有node_modules
                node_modules = project_path / "node_modules"
                node_modules_exists = node_modules.exists()

                checks.append(
                    HealthCheck(
                        service_name="node_modules",
                        status="healthy" if node_modules_exists else "warning",
                        response_time_ms=0,
                        error_message=(
                            None
                            if node_modules_exists
                            else "Dependencies not installed"
                        ),
                    )
                )

            except Exception:
                checks.append(
                    HealthCheck(
                        service_name="package.json",
                        status="unhealthy",
                        response_time_ms=0,
                        error_message="Invalid package.json format",
                    )
                )

        return checks

    def _measure_performance(self, project_path: Path) -> List[PerformanceMetric]:
        """测量性能指标"""
        metrics = []

        # 系统资源使用情况
        try:
            if os.name != "nt":  # Unix-like系统
                # CPU使用率
                cpu_result = subprocess.run(
                    ["top", "-bn1"], capture_output=True, text=True
                )
                if cpu_result.returncode == 0:
                    # 简单的CPU使用率解析
                    cpu_line = [
                        line for line in cpu_result.stdout.split("\n") if "%Cpu" in line
                    ]
                    if cpu_line:
                        cpu_usage = float(cpu_line[0].split()[1])
                        metrics.append(
                            PerformanceMetric(
                                name="system_cpu_usage",
                                value=cpu_usage,
                                unit="percent",
                                timestamp=datetime.now().isoformat(),
                                category="system",
                            )
                        )

                # 内存使用
                mem_result = subprocess.run(
                    ["free", "-m"], capture_output=True, text=True
                )
                if mem_result.returncode == 0:
                    lines = mem_result.stdout.split("\n")
                    for line in lines:
                        if "Mem:" in line:
                            parts = line.split()
                            total_mem = float(parts[1])
                            used_mem = float(parts[2])
                            usage_percent = (used_mem / total_mem) * 100
                            metrics.append(
                                PerformanceMetric(
                                    name="memory_usage",
                                    value=usage_percent,
                                    unit="percent",
                                    timestamp=datetime.now().isoformat(),
                                    category="system",
                                )
                            )
                            break

        except Exception:
            pass

        # 项目文件统计
        try:
            file_count = 0
            total_size = 0
            for root, dirs, files in os.walk(project_path):
                file_count += len(files)
                for file in files:
                    try:
                        total_size += os.path.getsize(os.path.join(root, file))
                    except OSError:
                        continue

            metrics.append(
                PerformanceMetric(
                    name="project_file_count",
                    value=file_count,
                    unit="files",
                    timestamp=datetime.now().isoformat(),
                    category="project",
                )
            )

            metrics.append(
                PerformanceMetric(
                    name="project_size",
                    value=total_size / (1024 * 1024),  # Convert to MB
                    unit="MB",
                    timestamp=datetime.now().isoformat(),
                    category="project",
                )
            )

        except Exception:
            pass

        return metrics

    def _analyze_dependencies(self, project_path: Path) -> Dict[str, Any]:
        """分析依赖关系"""
        dependencies = {}

        # Python依赖
        if self._is_python_project(project_path):
            python_deps = self._analyze_python_dependencies(project_path)
            dependencies["python"] = python_deps

        # Node.js依赖
        if self._is_node_project(project_path):
            node_deps = self._analyze_node_dependencies(project_path)
            dependencies["nodejs"] = node_deps

        return dependencies

    def _analyze_python_dependencies(self, project_path: Path) -> Dict[str, Any]:
        """分析Python依赖"""
        dep_info = {
            "has_venv": False,
            "dependency_files": [],
            "total_dependencies": 0,
            "outdated_dependencies": [],
        }

        venv_indicators = [".venv", "venv", "env"]
        dep_info["has_venv"] = any(
            (project_path / indicator).exists() for indicator in venv_indicators
        )

        dep_files = ["requirements.txt", "pyproject.toml", "Pipfile"]
        for dep_file in dep_files:
            file_path = project_path / dep_file
            if file_path.exists():
                dep_info["dependency_files"].append(dep_file)

                if dep_file == "requirements.txt":
                    try:
                        with open(file_path, "r") as f:
                            deps = f.read().strip().split("\n")
                            dep_info["total_dependencies"] = len(
                                [d for d in deps if d.strip() and not d.startswith("#")]
                            )
                    except Exception:
                        pass

        return dep_info

    def _analyze_node_dependencies(self, project_path: Path) -> Dict[str, Any]:
        """分析Node.js依赖"""
        dep_info = {
            "has_node_modules": False,
            "dependency_files": [],
            "total_dependencies": 0,
            "outdated_dependencies": [],
        }

        package_json = project_path / "package.json"
        if package_json.exists():
            try:
                import json

                with open(package_json, "r") as f:
                    data = json.load(f)

                node_modules = project_path / "node_modules"
                dep_info["has_node_modules"] = node_modules.exists()

                dependencies = data.get("dependencies", {})
                dev_dependencies = data.get("devDependencies", {})
                dep_info["total_dependencies"] = len(dependencies) + len(
                    dev_dependencies
                )

                # 记录依赖文件
                dep_info["dependency_files"].append("package.json")

                if dependencies:
                    dep_info["dependencies"] = list(dependencies.keys())
                if dev_dependencies:
                    dep_info["dev_dependencies"] = list(dev_dependencies.keys())

            except Exception:
                pass

        return dep_info

    def _get_runtime_environment(self, project_path: Path) -> Dict[str, str]:
        """获取运行时环境信息"""
        env_info = {
            "python_version": self._get_python_version(),
            "node_version": self._get_node_version(),
            "operating_system": os.name,
            "architecture": os.uname().machine if hasattr(os, "uname") else "unknown",
            "shell": os.environ.get("SHELL", "unknown"),
            "pwd": str(Path.cwd()),
            "path_separator": os.pathsep,
            "encoding": "utf-8",
        }

        # 项目特定的环境变量
        project_env_vars = [
            "VIRTUAL_ENV",
            "CONDA_DEFAULT_ENV",
            "NODE_ENV",
            "DJANGO_SETTINGS_MODULE",
            "FLASK_ENV",
            "FLASK_CONFIG",
        ]

        for var in project_env_vars:
            if var in os.environ:
                env_info[f"env_{var.lower()}"] = os.environ[var]

        return env_info

    def _get_python_version(self) -> str:
        """获取Python版本"""
        try:
            import sys

            return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        except:
            return "unknown"

    def _get_node_version(self) -> str:
        """获取Node.js版本"""
        try:
            result = subprocess.run(
                ["node", "--version"], capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() if result.returncode == 0 else "not installed"
        except:
            return "not installed"

    def _detect_issues(
        self,
        project_path: Path,
        processes: List[ProcessInfo],
        health_checks: List[HealthCheck],
    ) -> List[Dict[str, Any]]:
        """检测问题"""
        issues = []

        # 检查是否有开发服务器在运行
        dev_server_running = any(
            any(
                server in proc.command.lower()
                for server in ["runserver", "dev", "start"]
            )
            for proc in processes
        )

        # 检查健康检查结果
        unhealthy_services = [
            check for check in health_checks if check.status == "unhealthy"
        ]
        warning_services = [
            check for check in health_checks if check.status == "warning"
        ]

        if unhealthy_services:
            issues.append(
                {
                    "type": "unhealthy_services",
                    "severity": "high",
                    "count": len(unhealthy_services),
                    "services": [s.service_name for s in unhealthy_services],
                }
            )

        if warning_services:
            issues.append(
                {
                    "type": "service_warnings",
                    "severity": "medium",
                    "count": len(warning_services),
                    "services": [s.service_name for s in warning_services],
                }
            )

        # 检查资源使用
        high_memory_processes = [
            proc for proc in processes if proc.memory_mb > 1000  # 超过1GB
        ]

        if high_memory_processes:
            issues.append(
                {
                    "type": "high_memory_usage",
                    "severity": "medium",
                    "count": len(high_memory_processes),
                    "processes": [
                        {"pid": p.pid, "name": p.name, "memory_mb": p.memory_mb}
                        for p in high_memory_processes
                    ],
                }
            )

        # 检查是否缺乏开发环境
        if self._is_python_project(project_path) and not dev_server_running:
            issues.append(
                {
                    "type": "no_development_server",
                    "severity": "info",
                    "message": "No Python development server running",
                }
            )

        return issues

    def _generate_recommendations(
        self, issues: List[Dict[str, Any]], metrics: List[PerformanceMetric]
    ) -> List[str]:
        """生成建议"""
        recommendations = []

        if not issues:
            recommendations.append("项目状态良好，无问题检测到")

        for issue in issues:
            if issue["type"] == "unhealthy_services":
                recommendations.append(
                    f"发现 {issue['count']} 个不健康的服务，建议检查服务配置"
                )

            elif issue["type"] == "high_memory_usage":
                recommendations.append(
                    f"发现 {issue['count']} 个高内存使用进程，建议优化或重启"
                )

            elif issue["type"] == "no_development_server":
                recommendations.append("建议启动开发服务器进行测试")

        # 基于性能指标的建议
        memory_metrics = [m for m in metrics if m.name == "memory_usage"]
        if memory_metrics and memory_metrics[0].value > 80:
            recommendations.append("内存使用率较高，建议优化内存使用或增加内存")

        return recommendations


# 创建工具函数
@tool(
    "analyze_project_dynamics",
    description="动态分析项目运行状态，包括进程、健康检查、性能指标等",
)
def analyze_project_dynamics(project_path: str) -> str:
    """
    分析项目动态状态

    Args:
        project_path: 项目根目录路径

    Returns:
        动态分析结果的JSON字符串
    """
    try:
        analyzer = ProjectDynamicAnalyzer()
        analysis = analyzer.analyze_project_dynamics(project_path)

        result_data = {
            "project_path": analysis.project_path,
            "timestamp": analysis.timestamp,
            "processes": [
                {
                    "pid": proc.pid,
                    "name": proc.name,
                    "command": proc.command,
                    "status": proc.status,
                    "cpu_percent": proc.cpu_percent,
                    "memory_mb": proc.memory_mb,
                    "parent_pid": proc.parent_pid,
                }
                for proc in analysis.processes
            ],
            "health_checks": [
                {
                    "service_name": check.service_name,
                    "status": check.status,
                    "response_time_ms": check.response_time_ms,
                    "error_message": check.error_message,
                    "url": check.url,
                }
                for check in analysis.health_checks
            ],
            "performance_metrics": [
                {
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "timestamp": metric.timestamp,
                    "category": metric.category,
                }
                for metric in analysis.performance_metrics
            ],
            "dependencies": analysis.dependencies,
            "runtime_environment": analysis.runtime_environment,
            "issues": analysis.issues,
            "recommendations": analysis.recommendations,
            "summary": {
                "total_processes": len(analysis.processes),
                "running_processes": len(
                    [p for p in analysis.processes if p.status == "running"]
                ),
                "health_checks_count": len(analysis.health_checks),
                "issues_count": len(analysis.issues),
                "metrics_count": len(analysis.performance_metrics),
            },
        }

        return json.dumps(result_data, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"动态分析失败: {str(e)}",
                "project_path": project_path,
            },
            indent=2,
            ensure_ascii=False,
        )


@tool("check_service_health", description="检查项目服务健康状态")
def check_service_health(
    project_path: str, service_urls: Optional[List[str]] = None
) -> str:
    """
    检查服务健康状态

    Args:
        project_path: 项目根目录路径
        service_urls: 要检查的服务URL列表

    Returns:
        健康检查结果的JSON字符串
    """
    try:
        import time

        import requests

        project_dir = Path(project_path)
        if not project_dir.exists():
            return json.dumps(
                {"success": False, "error": f"项目路径不存在: {project_path}"},
                indent=2,
                ensure_ascii=False,
            )

        health_results = []

        # 默认检查的URL
        default_urls = [
            "http://localhost:8000",  # Python/Django
            "http://localhost:3000",  # Node.js
            "http://localhost:5000",  # Flask/FastAPI
            "http://localhost:8080",  # Java
            "http://localhost:9000",  # 其他服务
        ]

        urls_to_check = service_urls or default_urls
        analyzer = ProjectDynamicAnalyzer()

        # 获取项目中定义的服务
        if analyzer._is_python_project(project_dir):
            # 检查Django管理命令
            manage_py = project_dir / "manage.py"
            if manage_py.exists():
                try:
                    result = subprocess.run(
                        ["python", str(manage_py), "check"],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        cwd=project_dir,
                    )

                    health_results.append(
                        {
                            "service": "django_check",
                            "status": (
                                "healthy" if result.returncode == 0 else "unhealthy"
                            ),
                            "response_time_ms": 0,
                            "details": (
                                result.stdout
                                if result.returncode == 0
                                else result.stderr
                            ),
                        }
                    )
                except Exception as e:
                    health_results.append(
                        {
                            "service": "django_check",
                            "status": "error",
                            "response_time_ms": 0,
                            "error": str(e),
                        }
                    )

        # 检查HTTP端点
        for url in urls_to_check:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=10)
                response_time = (time.time() - start_time) * 1000

                health_results.append(
                    {
                        "service": url,
                        "status": (
                            "healthy" if response.status_code == 200 else "unhealthy"
                        ),
                        "response_time_ms": response_time,
                        "http_status": response.status_code,
                        "details": f"HTTP {response.status_code}",
                    }
                )

            except requests.exceptions.Timeout:
                health_results.append(
                    {
                        "service": url,
                        "status": "timeout",
                        "response_time_ms": 10000,
                        "error": "Request timeout",
                    }
                )
            except requests.exceptions.ConnectionError:
                health_results.append(
                    {
                        "service": url,
                        "status": "connection_error",
                        "response_time_ms": 0,
                        "error": "Connection refused",
                    }
                )
            except Exception as e:
                health_results.append(
                    {
                        "service": url,
                        "status": "error",
                        "response_time_ms": 0,
                        "error": str(e),
                    }
                )

        return json.dumps(
            {
                "success": True,
                "project_path": str(project_dir),
                "health_checks": health_results,
                "summary": {
                    "total_checks": len(health_results),
                    "healthy_count": len(
                        [c for c in health_results if c["status"] == "healthy"]
                    ),
                    "unhealthy_count": len(
                        [c for c in health_results if c["status"] == "unhealthy"]
                    ),
                    "error_count": len(
                        [
                            c
                            for c in health_results
                            if c["status"] in ["error", "timeout", "connection_error"]
                        ]
                    ),
                },
            },
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"健康检查失败: {str(e)}",
                "project_path": project_path,
            },
            indent=2,
            ensure_ascii=False,
        )


if __name__ == "__main__":
    # 测试用例
    print("测试项目动态分析:")
    result = analyze_project_dynamics(".")
    print(result)
