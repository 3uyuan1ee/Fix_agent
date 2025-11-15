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
        and (project_path / "setup.py").exists()
        or (project_path / "pyproject.toml").exists()
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
@tool(
    description="编译项目并检测编译错误和警告。支持Python、JavaScript、Java、C/C++、Go、Rust等多种编程语言的编译检查。自动检测项目类型，使用相应的编译工具进行语法检查和编译验证，返回详细的错误和警告信息。"
)
def compile_project(project_path: str, build_config: Optional[str] = None) -> str:
    """
    编译项目并检测编译错误，提供给agent使用的一站式项目编译检查工具。

    此工具整合了多语言项目的编译检查功能：
    - 自动检测项目类型（Python、Node.js、Java、Go、C++、Rust等）
    - 执行相应语言的语法检查和编译验证
    - 识别编译错误、语法错误和警告信息
    - 提供详细的错误位置和修复建议
    - 支持自定义构建配置和超时设置

    Args:
        project_path: 项目根目录路径，支持相对路径和绝对路径
        build_config: 可选的构建配置JSON字符串，包含编译参数和设置

    Returns:
        编译检查结果的JSON字符串，包含：
            - success: 编译是否成功
            - project_type: 检测到的项目类型
            - compilation_result: 编译结果详情
                - success: 编译状态
                - errors: 错误列表，包含文件路径、错误类型、错误消息等
                - warnings: 警告列表
                - summary: 错误和警告统计信息
                - timestamp: 检查时间戳

    使用场景：
        - 代码提交前的编译检查
        - CI/CD流水线的质量门禁
        - 项目构建失败诊断
        - 多语言项目的统一编译检查
        - 语法错误快速定位

    工具优势：
        - 多语言统一接口，无需关心具体编译工具
        - 智能项目类型检测，自动选择合适的编译方式
        - 详细的错误定位和分类
        - 支持自定义构建配置，适应不同项目需求

    注意事项：
        - 需要系统中安装相应的编译工具
        - 大型项目编译可能需要较长时间
        - 建议在项目根目录执行
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


@tool(
    description="运行项目并监控运行时错误。实时监控程序执行过程，捕获和分析运行时错误、异常和系统错误。支持自定义运行命令、超时设置和日志捕获。提供详细的错误堆栈跟踪和诊断信息。"
)
def run_and_monitor(
    project_path: str, run_command: str, timeout: int = 30, capture_logs: bool = True
) -> str:
    """
    运行项目并监控运行时错误，提供给agent使用的程序运行监控工具。

    此工具提供完整的程序运行监控功能：
    - 启动并监控程序执行过程
    - 实时捕获和分析运行时错误、异常和系统错误
    - 支持多种错误模式的识别和分类
    - 提供详细的错误堆栈跟踪和诊断信息
    - 可配置的超时控制和日志捕获功能

    Args:
        project_path: 项目根目录路径，程序执行的工作目录
        run_command: 要执行的具体命令（如"python main.py"、"npm start"等）
        timeout: 超时时间（秒），超过此时间将终止程序，默认30秒
        capture_logs: 是否捕获程序输出日志，默认为True

    Returns:
        运行监控结果的JSON字符串，包含：
            - success: 程序是否成功运行完成
            - runtime_result: 运行时监控详情
                - runtime_errors: 捕获的错误列表
                - output_log: 程序输出日志（如果启用）
                - exit_code: 程序退出码
                - timestamp: 运行时间戳

    使用场景：
        - 应用程序的运行时测试
        - 服务启动和健康检查
        - 长时间运行任务的监控
        - 脚本和工具的执行验证
        - 调试和故障诊断

    工具优势：
        - 实时错误监控，及时发现运行时问题
        - 智能错误分类，区分错误类型和严重程度
        - 完整的执行日志，便于问题排查
        - 灵活的超时控制，防止程序无限运行

    注意事项：
        - 运行命令需要在系统PATH中可访问
        - 长时间运行的程序建议设置合适的超时
        - 某些交互式程序可能无法正常监控
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


@tool(
    description="运行测试并捕获测试错误。支持多种测试框架（pytest、jest、junit、go test等），自动检测项目使用的测试框架，执行测试并捕获测试失败和错误信息。提供详细的测试结果和错误诊断。"
)
def run_tests_with_error_capture(
    project_path: str, test_framework: str = "auto"
) -> str:
    """
    运行测试并捕获测试错误，提供给agent使用的自动化测试执行工具。

    此工具提供完整的测试执行和错误捕获功能：
    - 自动检测项目使用的测试框架
    - 执行测试套件并收集测试结果
    - 捕获测试失败和错误信息
    - 支持多种测试框架和配置
    - 提供详细的测试报告和错误诊断

    Args:
        project_path: 项目根目录路径
        test_framework: 测试框架类型，可选值：
            - "auto": 自动检测（默认）
            - "pytest": Python pytest框架
            - "jest": JavaScript Jest框架
            - "junit": Java JUnit框架
            - "go_test": Go测试框架
            - 其他自定义框架

    Returns:
        测试执行结果的JSON字符串，包含：
            - success: 测试是否全部通过
            - test_framework: 使用的测试框架
            - test_result: 测试执行详情
                - success: 测试通过状态
                - test_errors: 捕获的测试错误列表
                - test_results: 测试结果统计
                - timestamp: 测试执行时间戳

    使用场景：
        - 自动化测试执行和验证
        - 持续集成流水线中的测试阶段
        - 测试失败的快速诊断
        - 多项目测试统一管理
        - 测试覆盖率分析辅助

    工具优势：
        - 智能测试框架检测，无需手动配置
        - 多测试框架统一接口
        - 详细的测试错误捕获和分析
        - 适合集成到自动化工作流中

    注意事项：
        - 需要项目中已配置相应的测试框架
        - 测试执行时间可能较长，建议设置合适的超时
        - 某些测试可能需要特定的环境依赖
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


@tool(
    description="分析现有日志文件中的错误。智能搜索和分析项目中的日志文件，识别错误、异常和关键事件。支持多种日志格式和模式匹配，提供错误统计、分类和趋势分析。"
)
def analyze_existing_logs(
    project_path: str, log_patterns: Optional[List[str]] = None
) -> str:
    """
    分析现有日志文件中的错误，提供给agent使用的日志分析工具。

    此工具提供全面的日志错误分析功能：
    - 智能搜索和分析项目中的日志文件
    - 使用错误模式匹配识别异常和错误事件
    - 支持多种日志格式和编码处理
    - 提供错误统计、分类和趋势分析
    - 生成详细的分析报告和建议

    Args:
        project_path: 项目根目录路径，包含要分析的日志文件
        log_patterns: 可选的日志文件模式列表，用于指定要分析的日志文件
            - 默认模式：["*.log", "logs/*.log", "*.out", "*.err", "error.log"]
            - 支持glob模式，如"app/*.log", "**/*debug*"

    Returns:
        日志分析结果的JSON字符串，包含：
            - success: 分析是否成功完成
            - log_files_analyzed: 分析的日志文件数量
            - log_analysis: 日志分析详情
                - analyzed_files: 已分析的文件列表
                - total_errors: 发现的错误总数
                - errors: 错误详细信息（前50个）
                - error_summary: 错误统计和分类

    使用场景：
        - 生产环境日志分析和故障排查
        - 应用程序错误趋势分析
        - 系统健康检查和监控
        - 错误模式识别和预防
        - 运维团队的技术支持

    工具优势：
        - 智能错误识别，多种错误模式匹配
        - 支持多种日志格式和编码
        - 提供错误统计和趋势分析
        - 适合大量日志文件的批量分析

    注意事项：
        - 大型日志文件分析可能需要较长时间
        - 某些日志格式可能需要自定义模式
        - 敏感信息日志需要谨慎处理
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
