"""
多语言静态分析执行器 - T004.2
执行多语言静态分析，发现代码质量问题
"""

import os
import subprocess
import json
import time
from typing import Dict, List, Any, Optional, Set, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from ..utils.logger import get_logger
try:
    from .project_analysis_types import ProgrammingLanguage, SeverityLevel
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

    class SeverityLevel(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"


@dataclass
class StaticAnalysisIssue:
    """静态分析问题"""
    tool_name: str
    file_path: str
    line_number: int
    column_number: Optional[int]
    severity: SeverityLevel
    message: str
    rule_id: str
    category: str
    source_code: Optional[str] = None
    end_line_number: Optional[int] = None
    confidence: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tool_name": self.tool_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "severity": self.severity.value,
            "message": self.message,
            "rule_id": self.rule_id,
            "category": self.category,
            "source_code": self.source_code,
            "end_line_number": self.end_line_number,
            "confidence": self.confidence
        }


@dataclass
class StaticAnalysisResult:
    """静态分析结果"""
    language: ProgrammingLanguage
    tool_name: str
    issues: List[StaticAnalysisIssue] = field(default_factory=list)
    execution_time: float = 0.0
    success: bool = True
    error_message: str = ""
    execution_timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "language": self.language.value,
            "tool_name": self.tool_name,
            "issues": [issue.to_dict() for issue in self.issues],
            "execution_time": self.execution_time,
            "success": self.success,
            "error_message": self.error_message,
            "execution_timestamp": self.execution_timestamp,
            "issue_count": len(self.issues),
            "severity_counts": self._get_severity_counts()
        }

    def _get_severity_counts(self) -> Dict[str, int]:
        """获取各严重程度的问题数量"""
        counts = {level.value: 0 for level in SeverityLevel}
        for issue in self.issues:
            counts[issue.severity.value] += 1
        return counts


class BaseStaticAnalyzer:
    """静态分析器基类"""

    def __init__(self, tool_name: str, language: ProgrammingLanguage):
        self.tool_name = tool_name
        self.language = language
        self.logger = get_logger()

    def analyze(self, file_path: str, **kwargs) -> StaticAnalysisResult:
        """
        执行静态分析

        Args:
            file_path: 要分析的文件路径
            **kwargs: 其他参数

        Returns:
            StaticAnalysisResult: 分析结果
        """
        raise NotImplementedError("子类必须实现analyze方法")

    def _run_command(self, cmd: List[str], timeout: int = 30) -> tuple[bool, str, str]:
        """
        运行外部命令

        Args:
            cmd: 命令列表
            timeout: 超时时间（秒）

        Returns:
            tuple: (成功标志, 标准输出, 标准错误)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=os.path.dirname(cmd[0]) if os.path.isfile(cmd[0]) else os.getcwd()
            )
            return True, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", f"命令执行超时: {' '.join(cmd)}"
        except FileNotFoundError:
            return False, "", f"命令未找到: {cmd[0]}"
        except Exception as e:
            return False, "", f"命令执行失败: {e}"

    def _normalize_severity(self, tool_severity: str) -> SeverityLevel:
        """
        标准化严重程度

        Args:
            tool_severity: 工具返回的严重程度

        Returns:
            SeverityLevel: 标准化的严重程度
        """
        severity_mapping = {
            # 通用映射
            'error': SeverityLevel.HIGH,
            'warning': SeverityLevel.MEDIUM,
            'info': SeverityLevel.LOW,
            'note': SeverityLevel.LOW,
            'fatal': SeverityLevel.CRITICAL,
            'critical': SeverityLevel.CRITICAL,
            'major': SeverityLevel.HIGH,
            'minor': SeverityLevel.LOW,

            # Pylint特定映射
            'F': SeverityLevel.CRITICAL,  # Fatal
            'E': SeverityLevel.HIGH,     # Error
            'W': SeverityLevel.MEDIUM,   # Warning
            'R': SeverityLevel.LOW,      # Refactor
            'C': SeverityLevel.LOW,      # Convention

            # Flake8特定映射
            'E': SeverityLevel.HIGH,     # Error
            'W': SeverityLevel.MEDIUM,   # Warning
            'F': SeverityLevel.CRITICAL, # Flake8 specific

            # Bandit特定映射
            'LOW': SeverityLevel.LOW,
            'MEDIUM': SeverityLevel.MEDIUM,
            'HIGH': SeverityLevel.HIGH,
        }

        return severity_mapping.get(tool_severity.upper(), SeverityLevel.LOW)


class PythonStaticAnalyzer(BaseStaticAnalyzer):
    """Python静态分析器"""

    def __init__(self):
        super().__init__("python_analyzer", ProgrammingLanguage.PYTHON)

    def analyze(self, file_path: str, tools: List[str] = None, **kwargs) -> StaticAnalysisResult:
        """
        执行Python静态分析

        Args:
            file_path: 要分析的Python文件路径
            tools: 要使用的工具列表，默认使用所有可用工具
            **kwargs: 其他参数

        Returns:
            StaticAnalysisResult: 分析结果
        """
        start_time = time.time()
        result = StaticAnalysisResult(
            language=self.language,
            tool_name="python_analyzer",
            execution_timestamp=datetime.now().isoformat()
        )

        if tools is None:
            tools = ['pylint', 'flake8', 'bandit']

        try:
            # 检查文件是否存在
            if not os.path.exists(file_path):
                result.success = False
                result.error_message = f"文件不存在: {file_path}"
                return result

            # 并行执行多个分析工具
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_tool = {}

                if 'pylint' in tools:
                    future_to_tool[executor.submit(self._run_pylint, file_path)] = 'pylint'
                if 'flake8' in tools:
                    future_to_tool[executor.submit(self._run_flake8, file_path)] = 'flake8'
                if 'bandit' in tools:
                    future_to_tool[executor.submit(self._run_bandit, file_path)] = 'bandit'

                for future in as_completed(future_to_tool):
                    tool_name = future_to_tool[future]
                    try:
                        tool_result = future.result(timeout=60)
                        result.issues.extend(tool_result.issues)
                        self.logger.info(f"{tool_name} 分析完成，发现 {len(tool_result.issues)} 个问题")
                    except Exception as e:
                        self.logger.error(f"{tool_name} 分析失败: {e}")

            result.execution_time = time.time() - start_time
            self.logger.info(f"Python静态分析完成，共发现 {len(result.issues)} 个问题")

        except Exception as e:
            result.success = False
            result.error_message = f"Python静态分析失败: {e}"
            self.logger.error(result.error_message)

        return result

    def _run_pylint(self, file_path: str) -> StaticAnalysisResult:
        """运行Pylint分析"""
        result = StaticAnalysisResult(
            language=self.language,
            tool_name="pylint"
        )

        cmd = ['pylint', '--output-format=json', file_path]
        success, stdout, stderr = self._run_command(cmd, timeout=60)

        if not success:
            result.success = False
            result.error_message = f"Pylint执行失败: {stderr}"
            return result

        try:
            pylint_issues = json.loads(stdout)
            for issue in pylint_issues:
                static_issue = StaticAnalysisIssue(
                    tool_name="pylint",
                    file_path=issue.get('path', file_path),
                    line_number=issue.get('line', 0),
                    column_number=issue.get('column'),
                    severity=self._normalize_severity(issue.get('type', '')),
                    message=issue.get('message', ''),
                    rule_id=issue.get('message-id', ''),
                    category=issue.get('type', ''),
                    source_code=issue.get('symbol', '')
                )
                result.issues.append(static_issue)

        except json.JSONDecodeError as e:
            result.success = False
            result.error_message = f"Pylint输出解析失败: {e}"

        return result

    def _run_flake8(self, file_path: str) -> StaticAnalysisResult:
        """运行Flake8分析"""
        result = StaticAnalysisResult(
            language=self.language,
            tool_name="flake8"
        )

        cmd = ['flake8', '--format=json', file_path]
        success, stdout, stderr = self._run_command(cmd, timeout=30)

        if not success:
            result.success = False
            result.error_message = f"Flake8执行失败: {stderr}"
            return result

        try:
            flake8_issues = json.loads(stdout)
            for issue in flake8_issues:
                static_issue = StaticAnalysisIssue(
                    tool_name="flake8",
                    file_path=issue.get('filename', file_path),
                    line_number=issue.get('line_number', 0),
                    column_number=issue.get('column_number'),
                    severity=self._normalize_severity(issue.get('code', '')[0]),
                    message=issue.get('text', ''),
                    rule_id=issue.get('code', ''),
                    category="style"
                )
                result.issues.append(static_issue)

        except json.JSONDecodeError:
            # 如果flake8不支持JSON格式，尝试解析普通输出
            result = self._parse_flake8_text_output(stdout, file_path)

        return result

    def _parse_flake8_text_output(self, output: str, file_path: str) -> StaticAnalysisResult:
        """解析Flake8文本输出"""
        result = StaticAnalysisResult(
            language=self.language,
            tool_name="flake8"
        )

        for line in output.strip().split('\n'):
            if line.strip():
                try:
                    # Flake8格式: filename:line:column: code message
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        static_issue = StaticAnalysisIssue(
                            tool_name="flake8",
                            file_path=parts[0].strip(),
                            line_number=int(parts[1].strip()),
                            column_number=int(parts[2].strip()),
                            severity=self._normalize_severity(parts[3].strip().split()[0][0]),
                            message=' '.join(parts[3].strip().split()[1:]),
                            rule_id=parts[3].strip().split()[0],
                            category="style"
                        )
                        result.issues.append(static_issue)
                except (ValueError, IndexError):
                    continue

        return result

    def _run_bandit(self, file_path: str) -> StaticAnalysisResult:
        """运行Bandit安全分析"""
        result = StaticAnalysisResult(
            language=self.language,
            tool_name="bandit"
        )

        cmd = ['bandit', '-f', 'json', file_path]
        success, stdout, stderr = self._run_command(cmd, timeout=60)

        if not success:
            result.success = False
            result.error_message = f"Bandit执行失败: {stderr}"
            return result

        try:
            bandit_output = json.loads(stdout)
            results = bandit_output.get('results', [])

            for issue in results:
                static_issue = StaticAnalysisIssue(
                    tool_name="bandit",
                    file_path=issue.get('filename', file_path),
                    line_number=issue.get('line_number', 0),
                    column_number=None,
                    severity=self._normalize_severity(issue.get('issue_severity', '')),
                    message=issue.get('issue_text', ''),
                    rule_id=issue.get('test_id', ''),
                    category=issue.get('issue_cwe', {}).get('id', 'security'),
                    confidence=issue.get('issue_confidence', '')
                )
                result.issues.append(static_issue)

        except json.JSONDecodeError as e:
            result.success = False
            result.error_message = f"Bandit输出解析失败: {e}"

        return result


class JavaScriptStaticAnalyzer(BaseStaticAnalyzer):
    """JavaScript/TypeScript静态分析器"""

    def __init__(self):
        super().__init__("javascript_analyzer", ProgrammingLanguage.JAVASCRIPT)

    def analyze(self, file_path: str, tools: List[str] = None, **kwargs) -> StaticAnalysisResult:
        """
        执行JavaScript/TypeScript静态分析

        Args:
            file_path: 要分析的JS/TS文件路径
            tools: 要使用的工具列表
            **kwargs: 其他参数

        Returns:
            StaticAnalysisResult: 分析结果
        """
        start_time = time.time()
        result = StaticAnalysisResult(
            language=self.language,
            tool_name="javascript_analyzer",
            execution_timestamp=datetime.now().isoformat()
        )

        if tools is None:
            tools = ['eslint']

        try:
            if not os.path.exists(file_path):
                result.success = False
                result.error_message = f"文件不存在: {file_path}"
                return result

            # 运行ESLint分析
            if 'eslint' in tools:
                eslint_result = self._run_eslint(file_path)
                result.issues.extend(eslint_result.issues)
                if not eslint_result.success:
                    self.logger.warning(f"ESLint分析失败: {eslint_result.error_message}")

            result.execution_time = time.time() - start_time
            self.logger.info(f"JavaScript静态分析完成，发现 {len(result.issues)} 个问题")

        except Exception as e:
            result.success = False
            result.error_message = f"JavaScript静态分析失败: {e}"
            self.logger.error(result.error_message)

        return result

    def _run_eslint(self, file_path: str) -> StaticAnalysisResult:
        """运行ESLint分析"""
        result = StaticAnalysisResult(
            language=self.language,
            tool_name="eslint"
        )

        # 尝试查找配置文件
        config_file = self._find_eslint_config(file_path)
        cmd = ['npx', 'eslint', '--format', 'json']

        if config_file:
            cmd.extend(['--config', config_file])

        cmd.append(file_path)

        success, stdout, stderr = self._run_command(cmd, timeout=60)

        if not success:
            result.success = False
            result.error_message = f"ESLint执行失败: {stderr}"
            return result

        try:
            eslint_output = json.loads(stdout)
            for file_result in eslint_output:
                for message in file_result.get('messages', []):
                    static_issue = StaticAnalysisIssue(
                        tool_name="eslint",
                        file_path=file_result.get('filePath', file_path),
                        line_number=message.get('line', 0),
                        column_number=message.get('column'),
                        severity=self._normalize_severity(message.get('severity', 1)),
                        message=message.get('message', ''),
                        rule_id=message.get('ruleId', ''),
                        category=message.get('ruleId', '').split('/')[0] if message.get('ruleId') else 'general'
                    )
                    result.issues.append(static_issue)

        except json.JSONDecodeError as e:
            result.success = False
            result.error_message = f"ESLint输出解析失败: {e}"

        return result

    def _find_eslint_config(self, file_path: str) -> Optional[str]:
        """查找ESLint配置文件"""
        directory = os.path.dirname(file_path)
        config_files = ['.eslintrc.js', '.eslintrc.json', '.eslintrc.yml', '.eslintrc.yaml']

        while directory and directory != '/':
            for config_file in config_files:
                config_path = os.path.join(directory, config_file)
                if os.path.exists(config_path):
                    return config_path
            directory = os.path.dirname(directory)

        return None

    def _normalize_severity(self, eslint_severity: Union[int, str]) -> SeverityLevel:
        """标准化ESLint严重程度"""
        # ESLint使用数字：1=warning, 2=error
        if isinstance(eslint_severity, int):
            return SeverityLevel.MEDIUM if eslint_severity == 1 else SeverityLevel.HIGH
        elif isinstance(eslint_severity, str):
            return super()._normalize_severity(eslint_severity)
        return SeverityLevel.LOW


class MultilangStaticAnalyzer:
    """多语言静态分析执行器"""

    def __init__(self, max_workers: int = 4, timeout_per_file: int = 120):
        self.max_workers = max_workers
        self.timeout_per_file = timeout_per_file
        self.logger = get_logger()

        # 初始化各语言分析器
        self.analyzers = {
            ProgrammingLanguage.PYTHON: PythonStaticAnalyzer(),
            ProgrammingLanguage.JAVASCRIPT: JavaScriptStaticAnalyzer(),
            # 可以继续添加其他语言的分析器
        }

        # 语言文件扩展名映射
        self.language_extensions = {
            ProgrammingLanguage.PYTHON: {'.py', '.pyw', '.pyi'},
            ProgrammingLanguage.JAVASCRIPT: {'.js', '.jsx', '.mjs', '.cjs'},
            ProgrammingLanguage.TYPESCRIPT: {'.ts', '.tsx'},
            ProgrammingLanguage.JAVA: {'.java'},
            ProgrammingLanguage.GO: {'.go'},
            ProgrammingLanguage.CPP: {'.cpp', '.cxx', '.cc', '.c', '.h', '.hpp', '.hxx'},
            ProgrammingLanguage.CSHARP: {'.cs'},
            ProgrammingLanguage.RUST: {'.rs'},
            ProgrammingLanguage.PHP: {'.php', '.phtml'},
            ProgrammingLanguage.RUBY: {'.rb', '.rbw'},
        }

    def analyze_files(self, file_paths: List[str], **kwargs) -> Dict[str, StaticAnalysisResult]:
        """
        批量分析文件

        Args:
            file_paths: 要分析的文件路径列表
            **kwargs: 其他参数

        Returns:
            Dict[str, StaticAnalysisResult]: 文件路径到分析结果的映射
        """
        results = {}

        # 按语言分组文件
        files_by_language = self._group_files_by_language(file_paths)

        # 并行分析各语言的文件
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {}

            for language, files in files_by_language.items():
                analyzer = self.analyzers.get(language)
                if analyzer:
                    for file_path in files:
                        future = executor.submit(
                            analyzer.analyze,
                            file_path,
                            timeout=self.timeout_per_file,
                            **kwargs
                        )
                        future_to_file[future] = file_path
                else:
                    self.logger.warning(f"暂不支持 {language.value} 语言的分析")
                    for file_path in files:
                        results[file_path] = StaticAnalysisResult(
                            language=language,
                            tool_name="unsupported",
                            success=False,
                            error_message=f"暂不支持 {language.value} 语言的分析"
                        )

            # 收集结果
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    result = future.result(timeout=self.timeout_per_file + 10)
                    results[file_path] = result
                    self.logger.info(f"文件 {file_path} 分析完成，发现 {len(result.issues)} 个问题")
                except Exception as e:
                    self.logger.error(f"文件 {file_path} 分析失败: {e}")
                    results[file_path] = StaticAnalysisResult(
                        language=self._detect_language(file_path) or ProgrammingLanguage.OTHER,
                        tool_name="analyzer_error",
                        success=False,
                        error_message=str(e)
                    )

        return results

    def _group_files_by_language(self, file_paths: List[str]) -> Dict[ProgrammingLanguage, List[str]]:
        """按语言分组文件"""
        grouped = {}

        for file_path in file_paths:
            language = self._detect_language(file_path)
            if language:
                if language not in grouped:
                    grouped[language] = []
                grouped[language].append(file_path)

        return grouped

    def _detect_language(self, file_path: str) -> Optional[ProgrammingLanguage]:
        """检测文件的语言"""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        for language, extensions in self.language_extensions.items():
            if ext in extensions:
                return language

        return None

    def get_analysis_summary(self, results: Dict[str, StaticAnalysisResult]) -> Dict[str, Any]:
        """
        获取分析结果摘要

        Args:
            results: 分析结果字典

        Returns:
            Dict[str, Any]: 分析摘要
        """
        total_files = len(results)
        total_issues = 0
        successful_analyses = 0
        failed_analyses = 0
        language_counts = {}
        severity_counts = {level.value: 0 for level in SeverityLevel}
        tool_usage = {}

        for file_path, result in results.items():
            if result.success:
                successful_analyses += 1
                total_issues += len(result.issues)

                # 统计语言
                lang = result.language.value
                language_counts[lang] = language_counts.get(lang, 0) + 1

                # 统计严重程度
                for issue in result.issues:
                    severity_counts[issue.severity.value] += 1

                # 统计工具使用
                tool = result.tool_name
                tool_usage[tool] = tool_usage.get(tool, 0) + 1
            else:
                failed_analyses += 1

        return {
            "summary": {
                "total_files": total_files,
                "successful_analyses": successful_analyses,
                "failed_analyses": failed_analyses,
                "total_issues": total_issues,
                "success_rate": round(successful_analyses / total_files * 100, 2) if total_files > 0 else 0
            },
            "language_distribution": language_counts,
            "severity_distribution": severity_counts,
            "tool_usage": tool_usage,
            "issue_density": round(total_issues / successful_analyses, 2) if successful_analyses > 0 else 0
        }


# 便捷函数
def analyze_multiple_files(file_paths: List[str],
                          max_workers: int = 4,
                          timeout_per_file: int = 120) -> Dict[str, Any]:
    """
    便捷的多文件静态分析函数

    Args:
        file_paths: 要分析的文件路径列表
        max_workers: 最大工作线程数
        timeout_per_file: 每个文件的超时时间

    Returns:
        Dict[str, Any]: 分析结果和摘要
    """
    analyzer = MultilangStaticAnalyzer(max_workers, timeout_per_file)
    results = analyzer.analyze_files(file_paths)
    summary = analyzer.get_analysis_summary(results)

    return {
        "results": {path: result.to_dict() for path, result in results.items()},
        "summary": summary
    }