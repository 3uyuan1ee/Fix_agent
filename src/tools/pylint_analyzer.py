"""
Pylint静态分析工具模块
集成pylint工具，实现代码质量检查
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.config import get_config_manager
from ..utils.logger import get_logger


class PylintAnalysisError(Exception):
    """Pylint分析异常"""

    pass


class PylintAnalyzer:
    """Pylint静态分析器"""

    def __init__(
        self, config_manager=None, config_file: Optional[str] = None, timeout: int = 30
    ):
        """
        初始化Pylint分析器

        Args:
            config_manager: 配置管理器实例
            config_file: 自定义pylint配置文件路径
            timeout: 分析超时时间（秒）
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.config_file = config_file
        self.timeout = timeout

        # 获取配置
        static_config = self.config_manager.get_section("static_analysis")
        pylint_config = static_config.get("pylint", {})

        # 默认禁用的代码检查
        self.disable_codes = pylint_config.get(
            "disable_codes", ["C0114", "C0115", "C0116"]
        )
        self.default_config_file = pylint_config.get("config_file", ".pylintrc")

    def analyze_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        分析Python文件

        Args:
            file_path: 文件路径

        Returns:
            分析结果字典

        Raises:
            PylintAnalysisError: 文件分析失败
        """
        file_path = Path(file_path)

        # 检查文件是否存在
        if not file_path.exists():
            raise PylintAnalysisError(f"File does not exist: {file_path}")

        # 检查是否为Python文件
        if file_path.suffix != ".py":
            raise PylintAnalysisError(f"File is not a Python file: {file_path}")

        try:
            # 构建pylint命令
            cmd = self._build_pylint_command(file_path)

            # 执行pylint
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=file_path.parent,
            )

            # 解析结果
            analysis_result = self._parse_pylint_output(
                result.stdout, result.stderr, result.returncode, file_path
            )

            self.logger.debug(f"Pylint analysis completed: {file_path}")
            return analysis_result

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Pylint analysis timeout for {file_path}")
            return {
                "file_path": str(file_path),
                "error": "Analysis timeout",
                "score": 0.0,
                "issues": [],
                "messages": ["Analysis timed out"],
            }

        except FileNotFoundError as e:
            if "pylint" in str(e).lower():
                raise PylintAnalysisError(
                    "Pylint is not installed. Please install it with: pip install pylint"
                )
            else:
                raise PylintAnalysisError(f"File not found: {e}")

        except Exception as e:
            raise PylintAnalysisError(f"Pylint analysis failed: {e}")

    def _build_pylint_command(self, file_path: Path) -> List[str]:
        """构建pylint命令"""
        cmd = ["pylint"]

        # 输出格式为JSON
        cmd.extend(["--output-format=json"])

        # 添加禁用的检查
        if self.disable_codes:
            cmd.append(f"--disable={','.join(self.disable_codes)}")

        # 使用配置文件
        config_file = self.config_file or self.default_config_file
        if config_file and Path(config_file).exists():
            cmd.append(f"--rcfile={config_file}")

        # 添加文件路径
        cmd.append(str(file_path))

        return cmd

    def _parse_pylint_output(
        self, stdout: str, stderr: str, returncode: int, file_path: Path
    ) -> Dict[str, Any]:
        """解析pylint输出"""
        result = {
            "file_path": str(file_path),
            "score": 0.0,
            "issues": [],
            "messages": [],
        }

        # Pylint的JSON输出和评分信息都在stdout中
        # 首先尝试从stdout解析评分
        score = self._extract_score(stdout)
        result["score"] = score

        # 尝试从stdout解析JSON
        json_issues = self._try_parse_json(stdout)
        if json_issues:
            result["issues"].extend(json_issues)

        # 尝试从stderr解析JSON（某些版本可能输出到stderr）
        if stderr.strip():
            json_issues = self._try_parse_json(stderr)
            if json_issues:
                result["issues"].extend(json_issues)
            else:
                # 如果不是JSON，则作为错误消息处理
                result["messages"].append(f"Pylint stderr: {stderr.strip()}")

        # 如果没有找到JSON格式的问题，尝试解析文本格式
        if not result["issues"]:
            text_issues = self._parse_text_output(stdout)
            result["issues"].extend(text_issues)

            if not text_issues:
                text_issues_stderr = self._parse_text_output(stderr)
                result["issues"].extend(text_issues_stderr)

        # 如果返回码非0且没有问题，可能是配置错误
        if returncode != 0 and not result["issues"]:
            result["messages"].append(f"Pylint exited with code {returncode}")

        return result

    def _try_parse_json(self, text: str) -> List[Dict[str, Any]]:
        """尝试解析JSON格式的输出"""
        try:
            # 首先尝试直接解析整个文本
            stripped = text.strip()
            if stripped.startswith("[") or stripped.startswith("{"):
                messages = json.loads(stripped)
                if isinstance(messages, list):
                    return self._normalize_issues(messages)
                elif isinstance(messages, dict) and "messages" in messages:
                    return self._normalize_issues(messages["messages"])

            # 如果不是以[或{开头，尝试查找JSON部分
            # 处理包含评分和JSON的混合输出
            lines = text.strip().split("\n")
            json_buffer = []
            in_json = False

            for line in lines:
                stripped_line = line.strip()

                if stripped_line.startswith("["):
                    # 找到JSON开始
                    in_json = True
                    json_buffer.append(stripped_line)
                elif in_json:
                    # 正在收集JSON内容
                    json_buffer.append(stripped_line)
                    if stripped_line.endswith("]") or stripped_line.endswith("}"):
                        # JSON结束，尝试解析
                        json_text = "\n".join(json_buffer)
                        try:
                            messages = json.loads(json_text)
                            if isinstance(messages, list):
                                return self._normalize_issues(messages)
                            elif isinstance(messages, dict) and "messages" in messages:
                                return self._normalize_issues(messages["messages"])
                        except json.JSONDecodeError:
                            # 如果解析失败，继续收集（可能是多行JSON）
                            continue
                        # 重置缓冲区继续查找
                        json_buffer = []
                        in_json = False
                elif stripped_line.startswith("{"):
                    # 单行JSON对象
                    in_json = True
                    json_buffer.append(stripped_line)
                    if stripped_line.endswith("]") or stripped_line.endswith("}"):
                        json_text = "\n".join(json_buffer)
                        messages = json.loads(json_text)
                        if isinstance(messages, list):
                            return self._normalize_issues(messages)
                        elif isinstance(messages, dict) and "messages" in messages:
                            return self._normalize_issues(messages["messages"])
                        json_buffer = []
                        in_json = False

        except (json.JSONDecodeError, ValueError) as e:
            # 调试输出
            import logging

            logging.debug(f"JSON parsing failed: {e}")
        return []

    def _extract_score(self, output: str) -> float:
        """从pylint输出中提取评分"""
        # 常见的评分格式
        score_patterns = [
            r"(\d+\.?\d*)/10",
            r"rated at (\d+\.?\d*)/10",
            r"Score:\s*(\d+\.?\d*)",
        ]

        for pattern in score_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue

        return 0.0

    def _normalize_issues(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """标准化问题格式"""
        normalized_issues = []

        for msg in messages:
            issue = {
                "type": msg.get("type", "unknown").lower(),
                "message": msg.get("message", ""),
                "message_id": msg.get("message-id", ""),
                "symbol": msg.get("symbol", ""),
                "module": msg.get("module", ""),
                "obj": msg.get("obj", ""),
                "line": msg.get("line", 0),
                "column": msg.get("column", 0),
                "path": msg.get("path", ""),
                "confidence": msg.get("confidence", "HIGH"),
            }

            # 映射严重程度
            severity_mapping = {
                "fatal": "error",
                "error": "error",
                "warning": "warning",
                "refactor": "info",
                "convention": "info",
                "info": "info",
            }
            issue["severity"] = severity_mapping.get(issue["type"], "info")

            normalized_issues.append(issue)

        return normalized_issues

    def _parse_text_output(self, output: str) -> List[Dict[str, Any]]:
        """解析文本格式的pylint输出"""
        issues = []
        lines = output.split("\n")

        for line in lines:
            # 尝试匹配标准的pylint输出格式
            # 格式: filename:line:column: message-type: message (message-id)
            match = re.match(
                r"^([^:]+):(\d+):(\d+):\s*([^:]+):\s*([^(]+)\s*\(([^)]+)\)", line
            )
            if match:
                filename, line_num, column, msg_type, message, msg_id = match.groups()
                issue = {
                    "type": msg_type.lower().strip(),
                    "message": message.strip(),
                    "message_id": msg_id.strip(),
                    "line": int(line_num),
                    "column": int(column),
                    "path": filename.strip(),
                    "severity": msg_type.lower().strip(),
                }
                issues.append(issue)

        return issues

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
            "score": result["score"],
            "total_issues": len(result["issues"]),
            "issue_types": {},
            "has_errors": False,
            "error_count": 0,
        }

        # 统计问题类型
        for issue in result["issues"]:
            severity = issue.get("severity", "info")
            summary["issue_types"][severity] = (
                summary["issue_types"].get(severity, 0) + 1
            )

            if severity == "error":
                summary["has_errors"] = True
                summary["error_count"] += 1

        # 添加消息
        if result.get("messages"):
            summary["messages"] = result["messages"]

        return summary
