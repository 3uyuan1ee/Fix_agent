"""
多语言代码分析工具模块
包含Python、JavaScript/TypeScript、Java、C/C++、Go、Rust等语言的代码分析工具
提供统一的接口和可扩展的架构
"""

import json
import re
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from langchain_core.tools import tool


@dataclass
class AnalysisIssue:
    """代码分析问题"""

    tool_name: str
    issue_type: str  # error, warning, info, convention
    severity: str  # high, medium, low
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    rule_id: Optional[str] = None
    category: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class AnalysisResult:
    """代码分析结果"""

    file_path: str
    language: str
    tool_name: str
    success: bool
    issues: List[AnalysisIssue]
    score: float = 0.0  # 0-100的质量评分
    execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        issue_counts = {
            "error": len([i for i in self.issues if i.issue_type == "error"]),
            "warning": len([i for i in self.issues if i.issue_type == "warning"]),
            "info": len([i for i in self.issues if i.issue_type == "info"]),
            "convention": len([i for i in self.issues if i.issue_type == "convention"]),
        }

        severity_counts = {
            "high": len([i for i in self.issues if i.severity == "high"]),
            "medium": len([i for i in self.issues if i.severity == "medium"]),
            "low": len([i for i in self.issues if i.severity == "low"]),
        }

        return {
            "file_path": self.file_path,
            "language": self.language,
            "tool_name": self.tool_name,
            "total_issues": len(self.issues),
            "issue_counts": issue_counts,
            "severity_counts": severity_counts,
            "quality_score": self.score,
            "has_issues": len(self.issues) > 0,
            "has_errors": issue_counts["error"] > 0,
            "success": self.success,
            "error": self.error,
        }


class BaseCodeAnalyzer(ABC):
    """代码分析器基类"""

    def __init__(self, timeout: int = 30, **kwargs):
        self.timeout = timeout
        self.config = kwargs

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """获取支持的文件扩展名"""
        pass

    @abstractmethod
    def get_language(self) -> str:
        """获取分析的语言"""
        pass

    @abstractmethod
    def get_tool_name(self) -> str:
        """获取工具名称"""
        pass

    @abstractmethod
    def _check_tool_availability(self) -> bool:
        """检查工具是否可用"""
        pass

    @abstractmethod
    def _build_command(self, file_path: Path) -> List[str]:
        """构建分析命令"""
        pass

    @abstractmethod
    def _parse_output(
        self, stdout: str, stderr: str, returncode: int, file_path: Path
    ) -> List[AnalysisIssue]:
        """解析工具输出"""
        pass

    def can_analyze(self, file_path: Union[str, Path]) -> bool:
        """检查是否可以分析指定文件"""
        file_path = Path(file_path)  # 确保转换为Path对象
        return (
            file_path.exists()
            and file_path.suffix in self.get_supported_extensions()
            and self._check_tool_availability()
        )

    def analyze(self, file_path: Union[str, Path]) -> AnalysisResult:
        """分析文件"""
        import time

        start_time = time.time()

        file_path = Path(file_path)

        if not self.can_analyze(file_path):
            return AnalysisResult(
                file_path=str(file_path),
                language=self.get_language(),
                tool_name=self.get_tool_name(),
                success=False,
                issues=[],
                error=f"Cannot analyze file: {file_path}",
            )

        try:
            # 执行分析命令
            cmd = self._build_command(file_path)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=file_path.parent,
            )

            # 解析输出
            issues = self._parse_output(
                result.stdout, result.stderr, result.returncode, file_path
            )

            # 计算质量评分
            score = self._calculate_score(issues)

            execution_time = time.time() - start_time

            return AnalysisResult(
                file_path=str(file_path),
                language=self.get_language(),
                tool_name=self.get_tool_name(),
                success=True,
                issues=issues,
                score=score,
                execution_time=execution_time,
                metadata={"returncode": result.returncode},
            )

        except subprocess.TimeoutExpired:
            return AnalysisResult(
                file_path=str(file_path),
                language=self.get_language(),
                tool_name=self.get_tool_name(),
                success=False,
                issues=[],
                error="Analysis timeout",
            )
        except FileNotFoundError:
            return AnalysisResult(
                file_path=str(file_path),
                language=self.get_language(),
                tool_name=self.get_tool_name(),
                success=False,
                issues=[],
                error=f"Tool '{self.get_tool_name()}' is not installed",
            )
        except Exception as e:
            return AnalysisResult(
                file_path=str(file_path),
                language=self.get_language(),
                tool_name=self.get_tool_name(),
                success=False,
                issues=[],
                error=f"Analysis failed: {e}",
            )

    def _calculate_score(self, issues: List[AnalysisIssue]) -> float:
        """计算质量评分"""
        if not issues:
            return 100.0

        # 根据问题严重程度扣分
        penalty = 0
        for issue in issues:
            if issue.severity == "high":
                penalty += 10
            elif issue.severity == "medium":
                penalty += 5
            elif issue.severity == "low":
                penalty += 1

        return max(0.0, 100.0 - penalty)


class JavaScriptTypeScriptAnalyzer(BaseCodeAnalyzer):
    """JavaScript/TypeScript代码分析器"""

    def get_supported_extensions(self) -> List[str]:
        return [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]

    def get_language(self) -> str:
        return "javascript/typescript"

    def get_tool_name(self) -> str:
        return "eslint"

    def _check_tool_availability(self) -> bool:
        try:
            subprocess.run(["eslint", "--version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _build_command(self, file_path: Path) -> List[str]:
        cmd = [
            "eslint",
            "--format",
            "json",
            "--no-eslintrc",  # 不使用项目配置
            "--env",
            "browser,es2021,node",
            "--parser-options",
            '{"ecmaVersion": "latest", "sourceType": "module"}',
            str(file_path),
        ]
        return cmd

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int, file_path: Path
    ) -> List[AnalysisIssue]:
        issues = []

        try:
            # 解析ESLint JSON输出
            if stdout:
                results = json.loads(stdout)
                for result in results:
                    if result.get("filePath") == str(file_path):
                        for message in result.get("messages", []):
                            issue = AnalysisIssue(
                                tool_name="eslint",
                                issue_type=message.get(
                                    "severity", 1
                                ),  # 1=error, 2=warning
                                severity=(
                                    "high" if message.get("severity") == 1 else "medium"
                                ),
                                message=message.get("message", ""),
                                line=message.get("line"),
                                column=message.get("column"),
                                rule_id=message.get("ruleId"),
                                category="code_style",
                            )
                            issues.append(issue)
        except json.JSONDecodeError:
            # 如果JSON解析失败，尝试从stderr提取信息
            if stderr:
                for line in stderr.split("\n"):
                    if line.strip() and ":" in line:
                        # 简单的错误信息解析
                        parts = line.split(":")
                        if len(parts) >= 3:
                            try:
                                line_num = int(parts[1].strip())
                                issue = AnalysisIssue(
                                    tool_name="eslint",
                                    issue_type="error",
                                    severity="medium",
                                    message=":".join(parts[2:]).strip(),
                                    line=line_num,
                                    category="syntax_error",
                                )
                                issues.append(issue)
                            except ValueError:
                                continue

        return issues


class JavaAnalyzer(BaseCodeAnalyzer):
    """Java代码分析器"""

    def __init__(self, tool: str = "spotbugs", timeout: int = 60, **kwargs):
        super().__init__(timeout, **kwargs)
        self.tool = tool.lower()

    def get_supported_extensions(self) -> List[str]:
        return [".java"]

    def get_language(self) -> str:
        return "java"

    def get_tool_name(self) -> str:
        return self.tool

    def _check_tool_availability(self) -> bool:
        tools = {
            "spotbugs": ["spotbugs", "-textui", "-version"],
            "pmd": ["pmd", "--version"],
            "checkstyle": ["checkstyle", "-version"],
        }

        cmd = tools.get(self.tool)
        if not cmd:
            return False

        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _build_command(self, file_path: Path) -> List[str]:
        if self.tool == "spotbugs":
            return ["spotbugs", "-textui", "-xml:withMessages", str(file_path)]
        elif self.tool == "pmd":
            return [
                "pmd",
                "-d",
                str(file_path),
                "-f",
                "json",
                "-r",
                "rulesets/java/quickstart.xml",
            ]
        elif self.tool == "checkstyle":
            return [
                "checkstyle",
                "-f",
                "json",
                "-c",
                "/google_checks.xml",  # 使用Google风格指南
                str(file_path),
            ]
        else:
            raise ValueError(f"Unsupported tool: {self.tool}")

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int, file_path: Path
    ) -> List[AnalysisIssue]:
        issues = []

        if self.tool == "pmd" and stdout:
            try:
                data = json.loads(stdout)
                for violation in data.get("files", []):
                    if violation.get("filename") == str(file_path):
                        for v in violation.get("violations", []):
                            issue = AnalysisIssue(
                                tool_name="pmd",
                                issue_type="warning",
                                severity="medium",
                                message=v.get("message", ""),
                                line=v.get("beginline"),
                                column=v.get("begincolumn"),
                                rule_id=v.get("rule"),
                                category=v.get("ruleset", ""),
                            )
                            issues.append(issue)
            except json.JSONDecodeError:
                pass

        elif self.tool == "checkstyle" and stdout:
            try:
                data = json.loads(stdout)
                for file_data in data.get("files", []):
                    if file_data.get("name") == str(file_path):
                        for error in file_data.get("errors", []):
                            issue = AnalysisIssue(
                                tool_name="checkstyle",
                                issue_type="warning",
                                severity="low",
                                message=error.get("message", ""),
                                line=error.get("line"),
                                column=error.get("column"),
                                rule_id=error.get("source"),
                                category="style",
                            )
                            issues.append(issue)
            except json.JSONDecodeError:
                pass

        # 通用错误处理
        if stderr and not issues:
            for line in stderr.split("\n"):
                if "ERROR" in line or "WARNING" in line:
                    issue = AnalysisIssue(
                        tool_name=self.tool,
                        issue_type="warning",
                        severity="medium",
                        message=line.strip(),
                        category="general",
                    )
                    issues.append(issue)

        return issues


class CCppAnalyzer(BaseCodeAnalyzer):
    """C/C++代码分析器"""

    def __init__(self, tool: str = "clang", timeout: int = 60, **kwargs):
        super().__init__(timeout, **kwargs)
        self.tool = tool.lower()

    def get_supported_extensions(self) -> List[str]:
        return [".c", ".cpp", ".cc", ".cxx", ".c++", ".h", ".hpp", ".hxx"]

    def get_language(self) -> str:
        return "c/c++"

    def get_tool_name(self) -> str:
        return self.tool

    def _check_tool_availability(self) -> bool:
        tools = {"clang": ["clang", "--version"], "cppcheck": ["cppcheck", "--version"]}

        cmd = tools.get(self.tool)
        if not cmd:
            return False

        try:
            subprocess.run(cmd, capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _build_command(self, file_path: Path) -> List[str]:
        if self.tool == "clang":
            return [
                "clang",
                "--analyze",
                "-Xanalyzer",
                "-analyzer-output=text",
                str(file_path),
            ]
        elif self.tool == "cppcheck":
            return ["cppcheck", "--enable=all", "--xml", str(file_path)]
        else:
            raise ValueError(f"Unsupported tool: {self.tool}")

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int, file_path: Path
    ) -> List[AnalysisIssue]:
        issues = []

        if self.tool == "clang" and stderr:
            # Clang静态分析器输出在stderr中
            for line in stderr.split("\n"):
                if file_path.name in line and ("warning" in line or "error" in line):
                    # 解析clang输出格式
                    # 示例: main.c:10:5: warning: ...
                    match = re.search(
                        rf"{re.escape(file_path.name)}:(\d+):(\d+):\s*(\w+):\s*(.+)",
                        line,
                    )
                    if match:
                        line_num, col_num, severity, message = match.groups()
                        issue = AnalysisIssue(
                            tool_name="clang",
                            issue_type="error" if severity == "error" else "warning",
                            severity="high" if severity == "error" else "medium",
                            message=message.strip(),
                            line=int(line_num),
                            column=int(col_num),
                            category="static_analysis",
                        )
                        issues.append(issue)

        elif self.tool == "cppcheck" and stdout:
            # 简单的XML解析cppcheck输出
            import xml.etree.ElementTree as ET

            try:
                root = ET.fromstring(stdout)
                for error in root.findall(".//error"):
                    attrs = error.attrib
                    if attrs.get("file") == str(file_path):
                        issue = AnalysisIssue(
                            tool_name="cppcheck",
                            issue_type="warning",
                            severity=attrs.get("severity", "medium"),
                            message=attrs.get("msg", ""),
                            line=(
                                int(attrs.get("line", 0)) if attrs.get("line") else None
                            ),
                            rule_id=attrs.get("id"),
                            category=attrs.get("category", ""),
                        )
                        issues.append(issue)
            except ET.ParseError:
                # 如果XML解析失败，尝试文本解析
                for line in stdout.split("\n"):
                    if file_path.name in line and (
                        "error" in line or "warning" in line
                    ):
                        issue = AnalysisIssue(
                            tool_name="cppcheck",
                            issue_type="warning",
                            severity="medium",
                            message=line.strip(),
                            category="general",
                        )
                        issues.append(issue)

        return issues


class GoAnalyzer(BaseCodeAnalyzer):
    """Go代码分析器"""

    def __init__(self, tool: str = "vet", timeout: int = 30, **kwargs):
        super().__init__(timeout, **kwargs)
        self.tool = tool.lower()

    def get_supported_extensions(self) -> List[str]:
        return [".go"]

    def get_language(self) -> str:
        return "go"

    def get_tool_name(self) -> str:
        return self.tool

    def _check_tool_availability(self) -> bool:
        try:
            subprocess.run(["go", "version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _build_command(self, file_path: Path) -> List[str]:
        if self.tool == "vet":
            return ["go", "vet", str(file_path)]
        elif self.tool == "fmt":
            return ["go", "fmt", "-d", str(file_path)]
        elif self.tool == "staticcheck":
            return ["staticcheck", str(file_path)]
        else:
            raise ValueError(f"Unsupported tool: {self.tool}")

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int, file_path: Path
    ) -> List[AnalysisIssue]:
        issues = []

        # Go工具通常在stderr输出错误信息
        output = stderr if stderr else stdout

        for line in output.split("\n"):
            if line.strip() and file_path.name in line:
                # 解析Go输出格式
                # 示例: main.go:10:2: missing argument for conversion to int
                match = re.search(
                    rf"{re.escape(file_path.name)}:(\d+):(\d+):\s*(.+)", line
                )
                if match:
                    line_num, col_num, message = match.groups()
                    issue = AnalysisIssue(
                        tool_name=self.tool,
                        issue_type="warning",
                        severity="medium",
                        message=message.strip(),
                        line=int(line_num),
                        column=int(col_num),
                        category="go_analysis",
                    )
                    issues.append(issue)
                else:
                    # 如果无法解析行号，创建通用问题
                    issue = AnalysisIssue(
                        tool_name=self.tool,
                        issue_type="warning",
                        severity="medium",
                        message=line.strip(),
                        category="go_analysis",
                    )
                    issues.append(issue)

        return issues


class RustAnalyzer(BaseCodeAnalyzer):
    """Rust代码分析器"""

    def get_supported_extensions(self) -> List[str]:
        return [".rs"]

    def get_language(self) -> str:
        return "rust"

    def get_tool_name(self) -> str:
        return "clippy"

    def _check_tool_availability(self) -> bool:
        try:
            subprocess.run(
                ["cargo", "clippy", "--version"], capture_output=True, timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _build_command(self, file_path: Path) -> List[str]:
        # Rust分析通常在项目根目录运行
        return ["cargo", "clippy", "--message-format=json", "--", str(file_path)]

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int, file_path: Path
    ) -> List[AnalysisIssue]:
        issues = []

        # Clippy输出JSON格式的诊断信息
        for line in stdout.split("\n"):
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get("message", {}).get("file_name") == str(file_path):
                        msg = data["message"]
                        spans = msg.get("spans", [])
                        if spans:
                            span = spans[0]
                            issue = AnalysisIssue(
                                tool_name="clippy",
                                issue_type=msg.get("level", "warning"),
                                severity=(
                                    "high" if msg.get("level") == "error" else "medium"
                                ),
                                message=msg.get("message", ""),
                                line=span.get("line_start"),
                                column=span.get("column_start"),
                                category="rust_analysis",
                            )
                            issues.append(issue)
                except json.JSONDecodeError:
                    # 忽略非JSON行
                    continue

        # 如果没有找到JSON格式，尝试文本解析
        if not issues and stderr:
            for line in stderr.split("\n"):
                if file_path.name in line and ("warning" in line or "error" in line):
                    issue = AnalysisIssue(
                        tool_name="clippy",
                        issue_type="warning",
                        severity="medium",
                        message=line.strip(),
                        category="rust_analysis",
                    )
                    issues.append(issue)

        return issues


class PythonAnalyzer(BaseCodeAnalyzer):
    """Python代码分析器"""

    def __init__(self, tool: str = "pylint", timeout: int = 30, **kwargs):
        super().__init__(timeout, **kwargs)
        self.tool = tool.lower()

    def get_supported_extensions(self) -> List[str]:
        return [".py"]

    def get_language(self) -> str:
        return "python"

    def get_tool_name(self) -> str:
        return self.tool

    def _check_tool_availability(self) -> bool:
        if self.tool == "pylint":
            try:
                subprocess.run(["pylint", "--version"], capture_output=True, timeout=5)
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # pylint未安装，尝试降级到flake8
                try:
                    subprocess.run(
                        ["flake8", "--version"], capture_output=True, timeout=5
                    )
                    self.tool = "flake8"  # 降级到flake8
                    return True
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    # 如果flake8也未安装，使用Python内置的语法检查
                    self.tool = "python_builtin"
                    return True
        elif self.tool == "flake8":
            try:
                subprocess.run(["flake8", "--version"], capture_output=True, timeout=5)
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # flake8未安装，降级到Python内置检查
                self.tool = "python_builtin"
                return True
        elif self.tool == "mypy":
            try:
                subprocess.run(["mypy", "--version"], capture_output=True, timeout=5)
                return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # mypy未安装，降级到Python内置检查
                self.tool = "python_builtin"
                return True
        elif self.tool == "python_builtin":
            return True  # Python内置检查总是可用
        return False

    def _build_command(self, file_path: Path) -> List[str]:
        if self.tool == "pylint":
            return ["pylint", "--output-format=json", "--reports=no", str(file_path)]
        elif self.tool == "flake8":
            return ["flake8", "--format=json", str(file_path)]
        elif self.tool == "mypy":
            return ["mypy", "--show-error-codes", "--no-error-summary", str(file_path)]
        elif self.tool == "python_builtin":
            # 使用Python内置的语法检查
            return ["python", "-m", "py_compile", str(file_path)]
        else:
            raise ValueError(f"Unsupported tool: {self.tool}")

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int, file_path: Path
    ) -> List[AnalysisIssue]:
        issues = []

        if self.tool == "pylint" and stdout:
            try:
                pylint_issues = json.loads(stdout)
                for issue in pylint_issues:
                    if issue.get("path") == str(file_path):
                        analysis_issue = AnalysisIssue(
                            tool_name="pylint",
                            issue_type=issue.get("type", "warning"),
                            severity=(
                                "high" if issue.get("type") == "error" else "medium"
                            ),
                            message=issue.get("message", ""),
                            line=issue.get("line"),
                            column=issue.get("column"),
                            rule_id=issue.get("message-id"),
                            category="python_quality",
                        )
                        issues.append(analysis_issue)
            except json.JSONDecodeError:
                pass

        elif self.tool == "flake8" and stdout:
            # Flake8输出格式: {"filename": "...", "line": 1, "column": 1, "text": "...", "code": "E001"}
            try:
                flake8_issues = json.loads(stdout)
                if isinstance(flake8_issues, list):
                    for issue in flake8_issues:
                        if issue.get("filename") == str(file_path):
                            analysis_issue = AnalysisIssue(
                                tool_name="flake8",
                                issue_type="warning",
                                severity="medium",
                                message=issue.get("text", ""),
                                line=issue.get("line"),
                                column=issue.get("column"),
                                rule_id=issue.get("code"),
                                category="python_style",
                            )
                            issues.append(analysis_issue)
            except json.JSONDecodeError:
                # 尝试解析传统格式
                for line in stdout.split("\n"):
                    if line.strip() and file_path.name in line:
                        # 示例: test.py:1:1: E001 error message
                        match = re.search(
                            rf"{re.escape(file_path.name)}:(\d+):(\d+):\s*(\w+)\s+(.+)",
                            line,
                        )
                        if match:
                            line_num, col_num, code, message = match.groups()
                            analysis_issue = AnalysisIssue(
                                tool_name="flake8",
                                issue_type="warning",
                                severity="medium",
                                message=message.strip(),
                                line=int(line_num),
                                column=int(col_num),
                                rule_id=code,
                                category="python_style",
                            )
                            issues.append(analysis_issue)

        elif self.tool == "mypy" and stderr:
            # MyPy输出在stderr中
            for line in stderr.split("\n"):
                if line.strip() and file_path.name in line:
                    # 示例: test.py:1: error: Name 'x' is not defined
                    match = re.search(
                        rf"{re.escape(file_path.name)}:(\d+):\s*(\w+):\s*(.+)", line
                    )
                    if match:
                        line_num, severity, message = match.groups()
                        analysis_issue = AnalysisIssue(
                            tool_name="mypy",
                            issue_type="error" if severity == "error" else "warning",
                            severity="high" if severity == "error" else "medium",
                            message=message.strip(),
                            line=int(line_num),
                            category="python_typing",
                        )
                        issues.append(analysis_issue)

        return issues


class MultiLanguageAnalyzerFactory:
    """多语言代码分析器工厂"""

    _analyzers: Dict[str, Any] = {
        # Python
        "python": lambda **kwargs: PythonAnalyzer(**kwargs),
        "py": lambda **kwargs: PythonAnalyzer(**kwargs),
        "pylint": lambda **kwargs: PythonAnalyzer(tool="pylint", **kwargs),
        "flake8": lambda **kwargs: PythonAnalyzer(tool="flake8", **kwargs),
        "mypy": lambda **kwargs: PythonAnalyzer(tool="mypy", **kwargs),
        # JavaScript/TypeScript
        "javascript": JavaScriptTypeScriptAnalyzer,
        "typescript": JavaScriptTypeScriptAnalyzer,
        "js": JavaScriptTypeScriptAnalyzer,
        "ts": JavaScriptTypeScriptAnalyzer,
        # Java
        "java": lambda **kwargs: JavaAnalyzer(**kwargs),
        # C/C++
        "c": lambda **kwargs: CCppAnalyzer(tool="clang", **kwargs),
        "cpp": lambda **kwargs: CCppAnalyzer(tool="clang", **kwargs),
        "c++": lambda **kwargs: CCppAnalyzer(tool="clang", **kwargs),
        "clang": lambda **kwargs: CCppAnalyzer(tool="clang", **kwargs),
        "cppcheck": lambda **kwargs: CCppAnalyzer(tool="cppcheck", **kwargs),
        # Go
        "go": lambda **kwargs: GoAnalyzer(tool="vet", **kwargs),
        "golint": lambda **kwargs: GoAnalyzer(tool="vet", **kwargs),
        "govet": lambda **kwargs: GoAnalyzer(tool="vet", **kwargs),
        "staticcheck": lambda **kwargs: GoAnalyzer(tool="staticcheck", **kwargs),
        # Rust
        "rust": RustAnalyzer,
        "clippy": RustAnalyzer,
    }

    @classmethod
    def create_analyzer(cls, language: str, **kwargs) -> Optional[BaseCodeAnalyzer]:
        """创建指定语言的分析器"""
        language_key = language.lower()

        if language_key in cls._analyzers:
            analyzer_class = cls._analyzers[language_key]
            if callable(analyzer_class) and not isinstance(analyzer_class, type):
                return analyzer_class(**kwargs)
            else:
                return analyzer_class(**kwargs)

        return None

    @classmethod
    def detect_language_from_extension(cls, file_path: Path) -> Optional[str]:
        """根据文件扩展名检测语言"""
        extension_map = {
            # Python
            ".py": "python",
            # JavaScript/TypeScript
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".mjs": "javascript",
            ".cjs": "javascript",
            # Java
            ".java": "java",
            # C/C++
            ".c": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".c++": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".hxx": "cpp",
            # Go
            ".go": "go",
            # Rust
            ".rs": "rust",
        }

        return extension_map.get(file_path.suffix.lower())

    @classmethod
    def analyze_file(
        cls, file_path: Union[str, Path], language: Optional[str] = None, **kwargs
    ) -> Optional[AnalysisResult]:
        """分析文件，自动检测语言或使用指定语言"""
        file_path = Path(file_path)

        if not file_path.exists():
            return None

        # 检测语言
        if not language:
            language = cls.detect_language_from_extension(file_path)

        if not language:
            return None

        # 创建分析器并分析
        analyzer = cls.create_analyzer(language, **kwargs)
        if analyzer and analyzer.can_analyze(file_path):
            return analyzer.analyze(file_path)

        return None

    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """获取支持的语言列表"""
        return list(set(cls._analyzers.keys()))


# 便捷函数，供deepagents调用
@tool(
    description="多语言代码分析工具，支持Python、JavaScript、Java、C/C++、Go、Rust等语言的静态代码分析"
)
def analyze_code_file(file_path: str, language: Optional[str] = None) -> str:
    """
    代码分析主函数，供deepagents调用

    Args:
        file_path: 文件路径
        language: 可选的语言标识符

    Returns:
        分析结果的JSON字符串
    """
    result = MultiLanguageAnalyzerFactory.analyze_file(file_path, language)

    if result:
        analysis_result = {
            "success": True,
            "result": result.get_summary(),
            "detailed_result": {
                "file_path": result.file_path,
                "language": result.language,
                "tool_name": result.tool_name,
                "issues": [
                    {
                        "tool": issue.tool_name,
                        "type": issue.issue_type,
                        "severity": issue.severity,
                        "message": issue.message,
                        "line": issue.line,
                        "column": issue.column,
                        "rule_id": issue.rule_id,
                        "category": issue.category,
                        "suggestion": issue.suggestion,
                    }
                    for issue in result.issues
                ],
                "score": result.score,
                "execution_time": result.execution_time,
                "metadata": result.metadata,
            },
        }
        return json.dumps(analysis_result, indent=2, ensure_ascii=False)
    else:
        error_result = {
            "success": False,
            "error": f"Cannot analyze file: {file_path}",
            "supported_languages": MultiLanguageAnalyzerFactory.get_supported_languages(),
        }
        return json.dumps(error_result, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # 命令行接口
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        language = sys.argv[2] if len(sys.argv) > 2 else None

        result = analyze_code_file(file_path, language)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("Usage: python multilang_code_analyzers.py <file_path> [language]")
        print(
            f"Supported languages: {MultiLanguageAnalyzerFactory.get_supported_languages()}"
        )
