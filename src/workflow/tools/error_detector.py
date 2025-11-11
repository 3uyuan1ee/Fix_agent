"""
项目错误检测工具

这个工具专门检测项目的编译错误、运行时错误和构建失败，
为deepagents提供实时的错误监控和分析能力。
"""

import json
import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool


@dataclass
class CompilationError:
    """编译错误信息"""

    file_path: str
    line_number: int
    column_number: int
    error_type: str
    error_message: str
    compiler: str
    severity: str  # error, warning
    raw_output: str


@dataclass
class RuntimeError:
    """运行时错误信息"""

    error_type: str
    error_message: str
    stack_trace: str
    file_path: Optional[str]
    line_number: Optional[int]
    timestamp: str
    process_name: str
    severity: str


@dataclass
class BuildError:
    """构建错误信息"""

    build_tool: str  # npm, maven, gradle, make, cmake, etc.
    phase: str  # compile, test, package, install
    error_message: str
    step: str
    exit_code: int
    logs: str


@dataclass
class ErrorSummary:
    """错误汇总"""

    total_errors: int
    total_warnings: int
    compilation_errors: int
    runtime_errors: int
    build_errors: int
    critical_errors: List[Dict[str, Any]]
    recommendations: List[str]


def _init_error_patterns() -> Dict[str, List[str]]:
    """初始化错误模式"""
    return {
        "python": [
            r"File \"(.+)\", line (\d+)",
            r"(\w+Error): (.+)",
            r"Traceback \(most recent call last\):",
            r"SyntaxError: (.+)",
            r"IndentationError: (.+)",
            r"NameError: name '(.+)' is not defined",
            r"TypeError: (.+)",
            r"AttributeError: (.+)",
        ],
        "javascript": [
            r"(.+):(\d+):(\d+): (.+)",
            r"TypeError: (.+)",
            r"ReferenceError: (.+) is not defined",
            r"SyntaxError: (.+)",
            r"Cannot read property '(.+)' of undefined",
            r"(.+) is not a function",
        ],
        "java": [
            r"(.+):(\d+): error: (.+)",
            r"(.+):(\d+): warning: (.+)",
            r"java\.lang\.(\w+): (.+)",
            r"Exception in thread \"(.+)\" (.+): (.+)",
            r"at (.+)\.([^:]+)\([^:]+:(\d+)\)",
        ],
        "cpp": [
            r"(.+):(\d+):(\d+): error: (.+)",
            r"(.+):(\d+):(\d+): warning: (.+)",
            r"undefined reference to",
            r"cannot find",
            r"fatal error: (.+): No such file or directory",
        ],
        "go": [
            r"(.+):(\d+):(\d+): (.+)",
            r"cannot find package",
            r"undefined: (.+)",
            r"syntax error: (.+)",
        ],
    }


def _parse_build_config(build_config: Optional[str]) -> Dict[str, Any]:
    """解析构建配置"""
    default_config = {
        "clean_build": False,
        "parallel_jobs": 4,
        "verbose": True,
        "stop_on_error": True,
        "environment": {},
    }

    if build_config:
        try:
            user_config = json.loads(build_config)
            default_config.update(user_config)
        except json.JSONDecodeError:
            pass

    return default_config


def _detect_project_type(project_path: Path) -> str:
    """检测项目类型"""
    if (project_path / "package.json").exists():
        return "nodejs"
    elif (project_path / "pom.xml").exists():
        return "java_maven"
    elif (project_path / "build.gradle").exists() or (
        project_path / "settings.gradle"
    ).exists():
        return "java_gradle"
    elif (project_path / "Cargo.toml").exists():
        return "rust"
    elif (project_path / "go.mod").exists():
        return "go"
    elif (
        list(project_path.glob("*.c"))
        or list(project_path.glob("*.cpp"))
        or (project_path / "Makefile").exists()
    ):
        return "cpp"
    elif (
        list(project_path.glob("*.py"))
        and (project_path / "setup.py" or project_path / "pyproject.toml").exists()
    ):
        return "python"
    else:
        return "unknown"


def _error_response(message: str) -> str:
    """创建错误响应"""
    return json.dumps(
        {"success": False, "error": message}, ensure_ascii=False, indent=2
    )


def _check_python_syntax(project_path: Path, config: Dict[str, Any]) -> Dict[str, List]:
    """检查Python语法错误"""
    errors = []
    warnings = []

    # 查找Python文件
    python_files = list(project_path.rglob("*.py"))

    for py_file in python_files:
        # 跳过虚拟环境和缓存目录
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue

        try:
            # 使用Python -m py_compile 检查语法
            result = subprocess.run(
                ["python", "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                errors.append(
                    {
                        "file_path": str(py_file),
                        "error_type": "syntax_error",
                        "error_message": result.stderr.strip(),
                        "severity": "error",
                        "compiler": "python",
                    }
                )

        except subprocess.TimeoutExpired:
            errors.append(
                {
                    "file_path": str(py_file),
                    "error_type": "timeout",
                    "error_message": "语法检查超时",
                    "severity": "warning",
                    "compiler": "python",
                }
            )
        except Exception as e:
            errors.append(
                {
                    "file_path": str(py_file),
                    "error_type": "check_failed",
                    "error_message": str(e),
                    "severity": "warning",
                    "compiler": "python",
                }
            )

    return {"errors": errors, "warnings": warnings}


def _compile_nodejs(project_path: Path, config: Dict[str, Any]) -> Dict[str, List]:
    """编译Node.js项目"""
    errors = []
    warnings = []

    try:
        # 检查TypeScript配置
        if (project_path / "tsconfig.json").exists():
            # TypeScript编译
            result = subprocess.run(
                ["npx", "tsc", "--noEmit"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                errors.extend(_parse_typescript_errors(result.stderr, "typescript"))
        else:
            # JavaScript语法检查（使用ESLint如果可用）
            if (project_path / ".eslintrc.js").exists() or (
                project_path / ".eslintrc.json"
            ).exists():
                result = subprocess.run(
                    ["npx", "eslint", ".", "--format", "json"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                if result.stdout:
                    lint_errors = _parse_eslint_output(result.stdout)
                    errors.extend(
                        [e for e in lint_errors if e.get("severity") == "error"]
                    )
                    warnings.extend(
                        [e for e in lint_errors if e.get("severity") == "warning"]
                    )

    except subprocess.TimeoutExpired:
        errors.append(
            {
                "error_type": "timeout",
                "error_message": "Node.js编译超时",
                "severity": "error",
                "compiler": "nodejs",
            }
        )

    return {"errors": errors, "warnings": warnings}


def _parse_typescript_errors(output: str, compiler: str) -> List[Dict[str, Any]]:
    """解析TypeScript错误"""
    errors = []

    # TypeScript错误格式: file(line,column): error TScode: message
    pattern = r"(.+)\((\d+),(\d+)\): error (TS\d+): (.+)"

    for match in re.finditer(pattern, output):
        file_path, line, column, error_code, message = match.groups()
        errors.append(
            {
                "file_path": file_path.strip(),
                "line_number": int(line),
                "column_number": int(column),
                "error_type": "typescript_error",
                "error_message": message.strip(),
                "error_code": error_code,
                "severity": "error",
                "compiler": compiler,
            }
        )

    return errors


def _parse_eslint_output(output: str) -> List[Dict[str, Any]]:
    """解析ESLint输出"""
    errors = []

    try:
        eslint_results = json.loads(output)

        for file_result in eslint_results:
            file_path = file_result.get("filePath", "")
            for message in file_result.get("messages", []):
                errors.append(
                    {
                        "file_path": file_path,
                        "line_number": message.get("line", 0),
                        "column_number": message.get("column", 0),
                        "error_type": "eslint_error",
                        "error_message": message.get("message", ""),
                        "rule": message.get("ruleId", ""),
                        "severity": (
                            "error" if message.get("severity", 0) == 2 else "warning"
                        ),
                        "compiler": "eslint",
                    }
                )
    except json.JSONDecodeError:
        # 如果无法解析JSON，按行处理
        for line in output.split("\n"):
            if line.strip():
                errors.append(
                    {
                        "error_type": "eslint_parse_error",
                        "error_message": line.strip(),
                        "severity": "warning",
                        "compiler": "eslint",
                    }
                )

    return errors


def _parse_runtime_errors(output: str, stream: str) -> List[Dict[str, Any]]:
    """解析运行时错误"""
    errors = []
    lines = output.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Python错误模式
        if "Traceback" in line:
            errors.append(
                {
                    "error_type": "exception",
                    "error_message": line,
                    "stream": stream,
                    "severity": "error",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # JavaScript错误模式
        elif "Error:" in line or "TypeError:" in line or "ReferenceError:" in line:
            errors.append(
                {
                    "error_type": "javascript_error",
                    "error_message": line,
                    "stream": stream,
                    "severity": "error",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        # 通用错误模式
        elif any(
            keyword in line.lower()
            for keyword in ["error", "failed", "exception", "fatal"]
        ):
            if "warning" not in line.lower():
                errors.append(
                    {
                        "error_type": "general_error",
                        "error_message": line,
                        "stream": stream,
                        "severity": "error",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

    return errors


# deepagents工具函数
@tool("compile_project", description="编译项目并检测编译错误和警告")
def compile_project(project_path: str, build_config: Optional[str] = None) -> str:
    """
    编译项目并检测编译错误

    Args:
        project_path: 项目路径
        build_config: 构建配置JSON字符串

    Returns:
        编译结果JSON字符串
    """
    try:
        project_path = Path(project_path)
        if not project_path.exists():
            return _error_response("项目路径不存在")

        # 解析构建配置
        config = _parse_build_config(build_config)

        # 检测项目类型
        project_type = _detect_project_type(project_path)

        # 执行编译
        compilation_errors = []
        compilation_warnings = []

        try:
            if project_type == "python":
                # Python语法检查
                result = _check_python_syntax(project_path, config)
                compilation_errors.extend(result.get("errors", []))
                compilation_warnings.extend(result.get("warnings", []))

            elif project_type == "nodejs":
                # Node.js编译/构建
                result = _compile_nodejs(project_path, config)
                compilation_errors.extend(result.get("errors", []))
                compilation_warnings.extend(result.get("warnings", []))

            elif project_type == "unknown":
                return _error_response(f"无法识别的项目类型: {project_path}")

        except subprocess.TimeoutExpired:
            compilation_errors.append(
                {
                    "error_type": "timeout",
                    "error_message": "编译超时",
                    "severity": "error",
                }
            )

        # 生成编译结果
        error_summary = ErrorSummary(
            total_errors=len(compilation_errors),
            total_warnings=len(compilation_warnings),
            compilation_errors=len(compilation_errors),
            runtime_errors=0,
            build_errors=0,
            critical_errors=[
                e for e in compilation_errors if e.get("severity") == "error"
            ],
            recommendations=[
                f"修复{len(compilation_errors)}个编译错误",
                f"处理{len(compilation_warnings)}个编译警告",
            ],
        )

        compilation_result = {
            "success": len(compilation_errors) == 0,
            "project_type": project_type,
            "errors": compilation_errors,
            "warnings": compilation_warnings,
            "summary": error_summary.__dict__,
            "timestamp": datetime.now().isoformat(),
        }

        return json.dumps(
            {
                "success": True,
                "project_type": project_type,
                "compilation_result": compilation_result,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"编译检测失败: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


@tool("run_and_monitor", description="运行项目并监控运行时错误")
def run_and_monitor(
    project_path: str, run_command: str, timeout: int = 30, capture_logs: bool = True
) -> str:
    """
    运行项目并监控运行时错误

    Args:
        project_path: 项目路径
        run_command: 运行命令
        timeout: 超时时间（秒）
        capture_logs: 是否捕获日志

    Returns:
        运行监控结果JSON字符串
    """
    try:
        project_path = Path(project_path)
        if not project_path.exists():
            return _error_response("项目路径不存在")

        # 启动进程并监控
        runtime_errors = []
        output_log = []

        try:
            # 启动进程
            process = subprocess.Popen(
                run_command.split(),
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            start_time = time.time()

            # 实时监控输出
            while True:
                # 检查超时
                if time.time() - start_time > timeout:
                    process.terminate()
                    break

                # 检查进程是否结束
                if process.poll() is not None:
                    break

                # 读取输出
                try:
                    stdout_line = process.stdout.readline()
                    stderr_line = process.stderr.readline()

                    if stdout_line:
                        if capture_logs:
                            output_log.append(f"STDOUT: {stdout_line.strip()}")
                        runtime_errors.extend(
                            _parse_runtime_errors(stdout_line, "stdout")
                        )

                    if stderr_line:
                        if capture_logs:
                            output_log.append(f"STDERR: {stderr_line.strip()}")
                        runtime_errors.extend(
                            _parse_runtime_errors(stderr_line, "stderr")
                        )

                except:
                    break

            # 获取剩余输出
            stdout, stderr = process.communicate(timeout=5)
            if stdout:
                if capture_logs:
                    output_log.append(f"STDOUT: {stdout}")
                runtime_errors.extend(_parse_runtime_errors(stdout, "stdout"))
            if stderr:
                if capture_logs:
                    output_log.append(f"STDERR: {stderr}")
                runtime_errors.extend(_parse_runtime_errors(stderr, "stderr"))

        except subprocess.TimeoutExpired:
            process.kill()
            runtime_errors.append(
                {
                    "error_type": "timeout",
                    "error_message": f"程序运行超时（{timeout}秒）",
                    "severity": "error",
                }
            )
        except Exception as e:
            runtime_errors.append(
                {
                    "error_type": "execution_failed",
                    "error_message": str(e),
                    "severity": "error",
                }
            )

        runtime_result = {
            "success": len(runtime_errors) == 0,
            "runtime_errors": runtime_errors,
            "output_log": output_log if capture_logs else None,
            "exit_code": process.returncode if "process" in locals() else None,
            "timestamp": datetime.now().isoformat(),
        }

        return json.dumps(
            {"success": True, "runtime_result": runtime_result},
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"运行时监控失败: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


@tool("run_tests_with_error_capture", description="运行测试并捕获测试错误")
def run_tests_with_error_capture(
    project_path: str, test_framework: str = "auto"
) -> str:
    """
    运行测试并捕获测试错误

    Args:
        project_path: 项目路径
        test_framework: 测试框架 (auto, pytest, jest, junit, go test, etc.)

    Returns:
        测试错误检测结果JSON字符串
    """
    try:
        project_path = Path(project_path)
        if not project_path.exists():
            return _error_response("项目路径不存在")

        # 检测测试框架
        if test_framework == "auto":
            if (project_path / "pytest.ini").exists() or (
                project_path / "pyproject.toml"
            ).exists():
                test_framework = "pytest"
            elif (project_path / "jest.config.js").exists() or (
                project_path / "jest.config.json"
            ).exists():
                test_framework = "jest"
            elif (project_path / "pom.xml").exists():
                test_framework = "junit"
            elif (project_path / "go.mod").exists():
                test_framework = "go_test"
            else:
                test_framework = "unknown"

        # 运行测试
        test_errors = []
        test_results = {}

        try:
            if test_framework == "pytest":
                result = subprocess.run(
                    ["python", "-m", "pytest", "-v", "--tb=short"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                # 简单的错误解析
                if result.returncode != 0:
                    test_errors.append(
                        {
                            "error_type": "pytest_failure",
                            "error_message": "测试失败",
                            "details": result.stderr,
                            "severity": "error",
                        }
                    )

            elif test_framework == "jest":
                result = subprocess.run(
                    ["npm", "test", "--", "--verbose"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode != 0:
                    test_errors.append(
                        {
                            "error_type": "jest_failure",
                            "error_message": "Jest测试失败",
                            "details": result.stderr,
                            "severity": "error",
                        }
                    )

        except subprocess.TimeoutExpired:
            test_errors.append(
                {
                    "error_type": "timeout",
                    "error_message": "测试执行超时",
                    "severity": "error",
                }
            )

        test_result = {
            "success": len(test_errors) == 0,
            "test_framework": test_framework,
            "test_errors": test_errors,
            "test_results": test_results,
            "timestamp": datetime.now().isoformat(),
        }

        return json.dumps(
            {
                "success": True,
                "test_framework": test_framework,
                "test_result": test_result,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"测试错误检测失败: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )


@tool("analyze_existing_logs", description="分析现有日志文件中的错误")
def analyze_existing_logs(
    project_path: str, log_patterns: Optional[List[str]] = None
) -> str:
    """
    分析现有日志文件中的错误

    Args:
        project_path: 项目路径
        log_patterns: 日志文件模式列表

    Returns:
        日志错误分析结果JSON字符串
    """
    try:
        project_path = Path(project_path)
        if not project_path.exists():
            return _error_response("项目路径不存在")

        # 查找日志文件
        if log_patterns is None:
            log_patterns = ["*.log", "logs/*.log", "*.out", "*.err", "error.log"]

        log_files = []
        for pattern in log_patterns:
            log_files.extend(project_path.glob(pattern))
            log_files.extend(project_path.rglob(pattern))

        log_files = list(set(log_files))  # 去重

        # 分析日志文件
        all_errors = []
        analyzed_files = []

        for log_file in log_files[:10]:  # 限制分析文件数量
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # 简单的错误搜索
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    line = line.strip()
                    if any(
                        keyword in line.lower()
                        for keyword in ["error", "failed", "exception", "fatal"]
                    ):
                        if "warning" not in line.lower():
                            all_errors.append(
                                {
                                    "file_path": str(log_file),
                                    "line_number": i + 1,
                                    "error_type": "log_error",
                                    "error_message": line,
                                    "severity": "error",
                                }
                            )

                analyzed_files.append(str(log_file))

            except Exception as e:
                all_errors.append(
                    {
                        "file_path": str(log_file),
                        "error_type": "log_analysis_failed",
                        "error_message": f"无法分析日志文件: {str(e)}",
                        "severity": "warning",
                    }
                )

        log_analysis = {
            "analyzed_files": analyzed_files,
            "total_errors": len(all_errors),
            "errors": all_errors[:50],  # 返回前50个错误
            "error_summary": {
                "total_errors": len(all_errors),
                "by_severity": {"error": len(all_errors)},
                "critical_errors": all_errors[:10],
            },
        }

        return json.dumps(
            {
                "success": True,
                "log_files_analyzed": len(log_files),
                "log_analysis": log_analysis,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"日志分析失败: {str(e)}"},
            ensure_ascii=False,
            indent=2,
        )
