"""
静态分析工具执行协调器
统一管理和协调多个静态分析工具的执行
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from ..agent.execution_engine import ExecutionEngine, ExecutionResult, TaskStatus
from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from .ast_analyzer import ASTAnalyzer
from .bandit_analyzer import BanditAnalyzer
from .flake8_analyzer import Flake8Analyzer
from .pylint_analyzer import PylintAnalyzer


class SeverityLevel(Enum):
    """问题严重程度枚举"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    LOW = "low"


@dataclass
class AnalysisIssue:
    """分析问题数据结构"""

    tool_name: str
    file_path: str
    line: int
    column: int = 0
    message: str = ""
    severity: SeverityLevel = SeverityLevel.INFO
    issue_type: str = ""
    code: str = ""
    confidence: str = ""
    source_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tool_name": self.tool_name,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "message": self.message,
            "severity": self.severity.value,
            "issue_type": self.issue_type,
            "code": self.code,
            "confidence": self.confidence,
            "source_code": self.source_code,
        }


@dataclass
class StaticAnalysisResult:
    """静态分析结果数据结构"""

    file_path: str
    issues: List[AnalysisIssue] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    summary: Dict[str, Any] = field(default_factory=dict)

    def add_issue(self, issue: AnalysisIssue):
        """添加问题"""
        self.issues.append(issue)

    def get_issues_by_severity(self, severity: SeverityLevel) -> List[AnalysisIssue]:
        """根据严重程度获取问题"""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_tool(self, tool_name: str) -> List[AnalysisIssue]:
        """根据工具获取问题"""
        return [issue for issue in self.issues if issue.tool_name == tool_name]


class StaticAnalysisCoordinator:
    """静态分析工具执行协调器"""

    def __init__(
        self, config_manager=None, execution_engine: Optional[ExecutionEngine] = None
    ):
        """
        初始化静态分析协调器

        Args:
            config_manager: 配置管理器实例
            execution_engine: 执行引擎实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 创建或使用现有的执行引擎
        self.execution_engine = execution_engine or ExecutionEngine(max_workers=4)

        # 初始化分析工具
        self.ast_analyzer = ASTAnalyzer(config_manager)
        self.pylint_analyzer = PylintAnalyzer(config_manager)
        self.flake8_analyzer = Flake8Analyzer(config_manager)
        self.bandit_analyzer = BanditAnalyzer(config_manager)

        # 注册工具到执行引擎
        self._register_tools()

        # 获取配置
        try:
            self.config = self.config_manager.get_section("static_analysis")
        except:
            self.config = {}
        self.enabled_tools = self.config.get(
            "enabled_tools", ["ast", "pylint", "flake8", "bandit"]
        )

        self.logger.info(
            f"StaticAnalysisCoordinator initialized with tools: {self.enabled_tools}"
        )

    def _register_tools(self):
        """注册所有静态分析工具到执行引擎"""
        # 注册AST分析器
        self.execution_engine.register_tool(
            name="ast_analysis",
            tool_class=self.ast_analyzer.analyze_file,
            description="AST语法分析工具",
            timeout=30.0,
        )

        # 注册Pylint分析器
        self.execution_engine.register_tool(
            name="pylint_analysis",
            tool_class=self.pylint_analyzer.analyze_file,
            description="Pylint代码质量检查工具",
            timeout=60.0,
        )

        # 注册Flake8分析器
        self.execution_engine.register_tool(
            name="flake8_analysis",
            tool_class=self.flake8_analyzer.analyze_file,
            description="Flake8代码风格检查工具",
            timeout=30.0,
        )

        # 注册Bandit分析器
        self.execution_engine.register_tool(
            name="bandit_analysis",
            tool_class=self.bandit_analyzer.analyze_file,
            description="Bandit安全漏洞检测工具",
            timeout=90.0,
        )

    def analyze_file(self, file_path: str) -> StaticAnalysisResult:
        """
        分析单个文件

        Args:
            file_path: 文件路径

        Returns:
            静态分析结果
        """
        start_time = time.time()

        self.logger.info(f"Starting static analysis for file: {file_path}")

        # 创建分析结果对象
        result = StaticAnalysisResult(file_path=file_path)

        # 构建分析任务
        tasks = []
        for tool_name in self.enabled_tools:
            if tool_name == "ast":
                tasks.append(
                    {
                        "task_id": f"ast_{file_path}",
                        "tool_name": "ast_analysis",
                        "parameters": {"file_path": file_path},
                    }
                )
            elif tool_name == "pylint":
                tasks.append(
                    {
                        "task_id": f"pylint_{file_path}",
                        "tool_name": "pylint_analysis",
                        "parameters": {"file_path": file_path},
                    }
                )
            elif tool_name == "flake8":
                tasks.append(
                    {
                        "task_id": f"flake8_{file_path}",
                        "tool_name": "flake8_analysis",
                        "parameters": {"file_path": file_path},
                    }
                )
            elif tool_name == "bandit":
                tasks.append(
                    {
                        "task_id": f"bandit_{file_path}",
                        "tool_name": "bandit_analysis",
                        "parameters": {"file_path": file_path},
                    }
                )

        # 执行分析任务
        execution_results = self.execution_engine.execute_tasks(tasks)

        # 处理执行结果
        for exec_result in execution_results:
            if exec_result.success:
                tool_name = exec_result.tool_name.replace("_analysis", "")
                result.tool_results[tool_name] = exec_result.data

                # 转换工具特定的结果为统一格式
                issues = self._convert_tool_result(tool_name, exec_result.data)
                result.issues.extend(issues)

                self.logger.debug(
                    f"Tool {tool_name} found {len(issues)} issues in {file_path}"
                )
            else:
                tool_name = exec_result.tool_name.replace("_analysis", "")
                self.logger.warning(
                    f"Tool {tool_name} failed for {file_path}: {exec_result.error}"
                )

        # 计算执行时间
        result.execution_time = time.time() - start_time

        # 生成摘要
        result.summary = self._generate_summary(result)

        self.logger.info(
            f"Static analysis completed for {file_path}: "
            f"{len(result.issues)} issues in {result.execution_time:.2f}s"
        )

        return result

    def analyze_files(self, file_paths: List[str]) -> List[StaticAnalysisResult]:
        """
        分析多个文件

        Args:
            file_paths: 文件路径列表

        Returns:
            静态分析结果列表
        """
        self.logger.info(f"Starting static analysis for {len(file_paths)} files")

        results = []
        for file_path in file_paths:
            try:
                result = self.analyze_file(file_path)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to analyze file {file_path}: {e}")
                # 创建失败结果
                failed_result = StaticAnalysisResult(
                    file_path=file_path, execution_time=0.0, summary={"error": str(e)}
                )
                results.append(failed_result)

        return results

    def _convert_tool_result(
        self, tool_name: str, tool_result: Dict[str, Any]
    ) -> List[AnalysisIssue]:
        """
        将工具特定结果转换为统一格式

        Args:
            tool_name: 工具名称
            tool_result: 工具分析结果

        Returns:
            统一格式的问题列表
        """
        issues = []

        if tool_name == "ast":
            issues = self._convert_ast_result(tool_result)
        elif tool_name == "pylint":
            issues = self._convert_pylint_result(tool_result)
        elif tool_name == "flake8":
            issues = self._convert_flake8_result(tool_result)
        elif tool_name == "bandit":
            issues = self._convert_bandit_result(tool_result)

        return issues

    def _convert_ast_result(self, ast_result: Dict[str, Any]) -> List[AnalysisIssue]:
        """转换AST分析结果"""
        issues = []

        # 转换语法错误
        for error in ast_result.get("errors", []):
            issue = AnalysisIssue(
                tool_name="ast",
                file_path=ast_result["file_path"],
                line=error.get("line", 0),
                column=error.get("column", 0),
                message=error.get("message", ""),
                severity=SeverityLevel.ERROR,
                issue_type="syntax_error",
                code="SYNTAX_ERROR",
            )
            issues.append(issue)

        # 转换复杂度警告
        for func in ast_result.get("functions", []):
            complexity = func.get("complexity", 1)
            if complexity > 10:  # 复杂度过高
                issue = AnalysisIssue(
                    tool_name="ast",
                    file_path=ast_result["file_path"],
                    line=func.get("line", 0),
                    message=f"Function '{func['name']}' has high cyclomatic complexity: {complexity}",
                    severity=SeverityLevel.WARNING,
                    issue_type="complexity",
                    code="HIGH_COMPLEXITY",
                )
                issues.append(issue)

        return issues

    def _convert_pylint_result(
        self, pylint_result: Dict[str, Any]
    ) -> List[AnalysisIssue]:
        """转换Pylint分析结果"""
        issues = []

        for issue_data in pylint_result.get("issues", []):
            severity_map = {
                "error": SeverityLevel.ERROR,
                "warning": SeverityLevel.WARNING,
                "info": SeverityLevel.INFO,
                "refactor": SeverityLevel.INFO,
                "convention": SeverityLevel.LOW,
            }

            severity = severity_map.get(
                issue_data.get("severity", "info"), SeverityLevel.INFO
            )

            issue = AnalysisIssue(
                tool_name="pylint",
                file_path=pylint_result["file_path"],
                line=issue_data.get("line", 0),
                column=issue_data.get("column", 0),
                message=issue_data.get("message", ""),
                severity=severity,
                issue_type=issue_data.get("type", "unknown"),
                code=issue_data.get("message_id", ""),
                confidence=issue_data.get("confidence", ""),
            )
            issues.append(issue)

        return issues

    def _convert_flake8_result(
        self, flake8_result: Dict[str, Any]
    ) -> List[AnalysisIssue]:
        """转换Flake8分析结果"""
        issues = []

        for issue_data in flake8_result.get("issues", []):
            severity_map = {
                "error": SeverityLevel.ERROR,
                "warning": SeverityLevel.WARNING,
                "info": SeverityLevel.INFO,
            }

            severity = severity_map.get(
                issue_data.get("severity", "warning"), SeverityLevel.WARNING
            )

            issue = AnalysisIssue(
                tool_name="flake8",
                file_path=flake8_result["file_path"],
                line=issue_data.get("line", 0),
                column=issue_data.get("column", 0),
                message=issue_data.get("message", ""),
                severity=severity,
                issue_type=issue_data.get("type", "style"),
                code=issue_data.get("code", ""),
            )
            issues.append(issue)

        return issues

    def _convert_bandit_result(
        self, bandit_result: Dict[str, Any]
    ) -> List[AnalysisIssue]:
        """转换Bandit分析结果"""
        issues = []

        for vuln_data in bandit_result.get("vulnerabilities", []):
            severity_map = {
                "high": SeverityLevel.ERROR,
                "medium": SeverityLevel.WARNING,
                "low": SeverityLevel.INFO,
            }

            severity = severity_map.get(
                vuln_data.get("severity", "low"), SeverityLevel.LOW
            )

            issue = AnalysisIssue(
                tool_name="bandit",
                file_path=bandit_result["file_path"],
                line=vuln_data.get("line_number", 0),
                column=0,
                message=vuln_data.get("issue_text", ""),
                severity=severity,
                issue_type=vuln_data.get("vulnerability_type", "security"),
                code=vuln_data.get("test_id", ""),
                confidence=vuln_data.get("confidence", ""),
            )
            issues.append(issue)

        return issues

    def _generate_summary(self, result: StaticAnalysisResult) -> Dict[str, Any]:
        """生成分析摘要"""
        summary = {
            "file_path": result.file_path,
            "total_issues": len(result.issues),
            "severity_distribution": {},
            "tool_distribution": {},
            "issue_types": {},
            "execution_time": result.execution_time,
        }

        # 统计严重程度分布
        for issue in result.issues:
            severity = issue.severity.value
            summary["severity_distribution"][severity] = (
                summary["severity_distribution"].get(severity, 0) + 1
            )

        # 统计工具分布
        for issue in result.issues:
            tool = issue.tool_name
            summary["tool_distribution"][tool] = (
                summary["tool_distribution"].get(tool, 0) + 1
            )

        # 统计问题类型
        for issue in result.issues:
            issue_type = issue.issue_type
            summary["issue_types"][issue_type] = (
                summary["issue_types"].get(issue_type, 0) + 1
            )

        return summary

    def get_enabled_tools(self) -> List[str]:
        """获取启用的工具列表"""
        return self.enabled_tools.copy()

    def set_enabled_tools(self, tools: List[str]):
        """设置启用的工具列表"""
        valid_tools = {"ast", "pylint", "flake8", "bandit"}
        self.enabled_tools = [tool for tool in tools if tool in valid_tools]
        self.logger.info(f"Updated enabled tools: {self.enabled_tools}")

    def cleanup(self):
        """清理资源"""
        if self.execution_engine:
            self.execution_engine.cleanup()
