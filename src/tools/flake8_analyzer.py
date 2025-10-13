"""
Flake8静态分析工具模块
集成flake8工具，实现代码风格检查
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from ..utils.logger import get_logger
from ..utils.config import get_config_manager


class Flake8AnalysisError(Exception):
    """Flake8分析异常"""
    pass


class Flake8Analyzer:
    """Flake8静态分析器"""

    def __init__(self, config_manager=None, config_file: Optional[str] = None, timeout: int = 30):
        """
        初始化Flake8分析器

        Args:
            config_manager: 配置管理器实例
            config_file: 自定义flake8配置文件路径
            timeout: 分析超时时间（秒）
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.config_file = config_file
        self.timeout = timeout

        # 获取配置
        static_config = self.config_manager.get_section('static_analysis')
        flake8_config = static_config.get('flake8', {})

        # 配置参数
        self.max_line_length = flake8_config.get('max_line_length', 88)
        self.ignore_codes = flake8_config.get('ignore_codes', ['E203', 'W503'])
        self.default_config_file = '.flake8'

    def analyze_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        分析Python文件

        Args:
            file_path: 文件路径

        Returns:
            分析结果字典

        Raises:
            Flake8AnalysisError: 文件分析失败
        """
        file_path = Path(file_path)

        # 检查文件是否存在
        if not file_path.exists():
            raise Flake8AnalysisError(f"File does not exist: {file_path}")

        # 检查是否为Python文件
        if file_path.suffix != ".py":
            raise Flake8AnalysisError(f"File is not a Python file: {file_path}")

        try:
            # 构建flake8命令
            cmd = self._build_flake8_command(file_path)

            # 执行flake8
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=file_path.parent
            )

            # 解析结果
            analysis_result = self._parse_flake8_output(result.stdout, result.stderr, result.returncode, file_path)

            self.logger.debug(f"Flake8 analysis completed: {file_path}")
            return analysis_result

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Flake8 analysis timeout for {file_path}")
            return {
                "file_path": str(file_path),
                "error": "Analysis timeout",
                "issues": [],
                "messages": ["Analysis timed out"]
            }

        except FileNotFoundError as e:
            if "flake8" in str(e).lower():
                raise Flake8AnalysisError("Flake8 is not installed. Please install it with: pip install flake8")
            else:
                raise Flake8AnalysisError(f"File not found: {e}")

        except Exception as e:
            raise Flake8AnalysisError(f"Flake8 analysis failed: {e}")

    def _build_flake8_command(self, file_path: Path) -> List[str]:
        """构建flake8命令"""
        cmd = ["flake8"]

        # 设置最大行长度
        cmd.append(f"--max-line-length={self.max_line_length}")

        # 添加忽略的错误代码
        if self.ignore_codes:
            cmd.append(f"--ignore={','.join(self.ignore_codes)}")

        # 使用配置文件
        config_file = self.config_file or self.default_config_file
        if config_file and Path(config_file).exists():
            cmd.append(f"--config={config_file}")

        # 添加文件路径
        cmd.append(str(file_path))

        return cmd

    def _parse_flake8_output(self, stdout: str, stderr: str, returncode: int, file_path: Path) -> Dict[str, Any]:
        """解析flake8输出"""
        result = {
            "file_path": str(file_path),
            "issues": [],
            "messages": [],
            "return_code": returncode
        }

        # 解析stdout中的问题
        if stdout.strip():
            issues = self._parse_flake8_issues(stdout, file_path)
            result["issues"].extend(issues)

        # 解析stderr中的问题（某些情况下可能输出到stderr）
        if stderr.strip():
            issues = self._parse_flake8_issues(stderr, file_path)
            result["issues"].extend(issues)

            # 如果没有解析到问题，则作为错误消息处理
            if not issues:
                result["messages"].append(f"Flake8 stderr: {stderr.strip()}")

        # 如果返回码非0且没有问题，可能是配置错误
        if returncode != 0 and not result["issues"]:
            result["messages"].append(f"Flake8 exited with code {returncode}")

        return result

    def _parse_flake8_issues(self, output: str, file_path: Path) -> List[Dict[str, Any]]:
        """解析flake8问题输出"""
        issues = []
        lines = output.strip().split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Flake8输出格式: filename:line:column: code message
            # 例如: example.py:10:5: E302 expected 2 blank lines, found 1
            match = re.match(r'^([^:]+):(\d+):(\d+):\s*([A-Z]\d+)\s+(.+)$', line)
            if match:
                filename, line_num, column, code, message = match.groups()

                # 确保文件路径匹配
                if Path(filename).name != file_path.name:
                    continue

                issue = {
                    "file_path": str(file_path),
                    "line": int(line_num),
                    "column": int(column),
                    "code": code,
                    "message": message.strip(),
                    "severity": self._get_severity_from_code(code),
                    "type": self._get_type_from_code(code)
                }
                issues.append(issue)

        return issues

    def _get_severity_from_code(self, code: str) -> str:
        """根据错误代码获取严重程度"""
        # E系列：错误
        if code.startswith('E'):
            return "error"
        # W系列：警告
        elif code.startswith('W'):
            return "warning"
        # F系列：致命错误
        elif code.startswith('F'):
            return "error"
        # C系列：约定
        elif code.startswith('C'):
            return "info"
        # N系列：命名
        elif code.startswith('N'):
            return "info"
        # 其他默认为警告
        else:
            return "warning"

    def _get_type_from_code(self, code: str) -> str:
        """根据错误代码获取问题类型"""
        if code.startswith('E'):
            return "style"
        elif code.startswith('W'):
            return "warning"
        elif code.startswith('F'):
            return "fatal"
        elif code.startswith('C'):
            return "convention"
        elif code.startswith('N'):
            return "naming"
        else:
            return "other"

    def get_analysis_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取分析摘要

        Args:
            result: 分析结果

        Returns:
            分析摘要字典
        """
        summary = {
            "file_path": result["file_path"],
            "total_issues": len(result["issues"]),
            "issue_types": {},
            "issue_codes": {},
            "has_errors": False,
            "error_count": 0,
            "return_code": result.get("return_code", 0)
        }

        # 统计问题类型和代码
        for issue in result["issues"]:
            severity = issue.get("severity", "warning")
            code = issue.get("code", "unknown")

            summary["issue_types"][severity] = summary["issue_types"].get(severity, 0) + 1
            summary["issue_codes"][code] = summary["issue_codes"].get(code, 0) + 1

            if severity == "error":
                summary["has_errors"] = True
                summary["error_count"] += 1

        # 添加消息
        if result.get("messages"):
            summary["messages"] = result["messages"]

        return summary