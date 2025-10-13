"""
Bandit安全分析工具模块
集成bandit工具，实现安全漏洞检测
"""

import json
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from ..utils.logger import get_logger
from ..utils.config import get_config_manager


class BanditAnalysisError(Exception):
    """Bandit分析异常"""
    pass


class BanditAnalyzer:
    """Bandit安全分析器"""

    def __init__(self, config_manager=None, config_file: Optional[str] = None, timeout: int = 60):
        """
        初始化Bandit分析器

        Args:
            config_manager: 配置管理器实例
            config_file: 自定义bandit配置文件路径
            timeout: 分析超时时间（秒）
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.config_file = config_file
        self.timeout = timeout

        # 获取配置
        static_config = self.config_manager.get_section('static_analysis')
        bandit_config = static_config.get('bandit', {})

        # 配置参数
        self.severity_level = bandit_config.get('severity_level', 'medium')
        self.default_config_file = '.bandit'

        # 严重程度映射
        self.severity_mapping = {
            'low': 'low',
            'medium': 'medium',
            'high': 'high'
        }

        # 安全漏洞类型映射
        self.vulnerability_types = {
            # 注入类漏洞
            'hardcoded_password': 'credentials',
            'hardcoded-password': 'credentials',
            'hardcoded_sql_string': 'sql_injection',
            'hardcoded-sql-string': 'sql_injection',
            'hardcoded_temp_file': 'file_injection',
            'hardcoded-temp-file': 'file_injection',
            'subprocess_shell': 'shell_injection',
            'subprocess-shell': 'shell_injection',
            'shell_injection': 'shell_injection',
            'shell-injection': 'shell_injection',
            'sql_injection': 'sql_injection',
            'sql-injection': 'sql_injection',

            # 文件操作漏洞
            'tmp_path_symlink': 'file_security',
            'tmp-path-symlink': 'file_security',
            'bad_file_permissions': 'file_permissions',
            'bad-file-permissions': 'file_permissions',
            'tmp_file_access': 'file_access',
            'tmp-file-access': 'file_access',

            # 密码学问题
            'weak_crypto': 'weak_cryptography',
            'weak-crypto': 'weak_cryptography',
            'insecure_hash': 'weak_cryptography',
            'insecure-hash': 'weak_cryptography',
            'insecure_crypto': 'weak_cryptography',
            'insecure-crypto': 'weak_cryptography',

            # 网络安全
            'ssl_insecure_version': 'ssl_issues',
            'ssl-insecure-version': 'ssl_issues',
            'ssl_no_hostname': 'ssl_issues',
            'ssl-no-hostname': 'ssl_issues',
            'ssl_insecure_protocol': 'ssl_issues',
            'ssl-insecure-protocol': 'ssl_issues',

            # 输入验证
            'assert_used': 'input_validation',
            'assert-used': 'input_validation',
            'try_except_pass': 'exception_handling',
            'try-except-pass': 'exception_handling',
            'except_pass': 'exception_handling',
            'except-pass': 'exception_handling',

            # 配置问题
            'import_config': 'configuration_issues',
            'import-config': 'configuration_issues',
            'exec_used': 'code_injection',
            'exec-used': 'code_injection',
            'eval_used': 'code_injection',
            'eval-used': 'code_injection',
            'flask_debug_true': 'configuration_issues',
            'flask-debug-true': 'configuration_issues',

            # 默认分类
            'default': 'security_issue'
        }

    def analyze_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        分析Python文件的安全漏洞

        Args:
            file_path: 文件路径

        Returns:
            分析结果字典

        Raises:
            BanditAnalysisError: 文件分析失败
        """
        file_path = Path(file_path)

        # 检查文件是否存在
        if not file_path.exists():
            raise BanditAnalysisError(f"File does not exist: {file_path}")

        # 检查是否为Python文件
        if file_path.suffix != ".py":
            raise BanditAnalysisError(f"File is not a Python file: {file_path}")

        try:
            # 构建bandit命令
            cmd = self._build_bandit_command(file_path)

            # 执行bandit
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=file_path.parent
            )

            # 解析结果
            analysis_result = self._parse_bandit_output(result.stdout, result.stderr, result.returncode, file_path)

            self.logger.debug(f"Bandit analysis completed: {file_path}")
            return analysis_result

        except subprocess.TimeoutExpired:
            self.logger.warning(f"Bandit analysis timeout for {file_path}")
            return {
                "file_path": str(file_path),
                "error": "Analysis timeout",
                "vulnerabilities": [],
                "messages": ["Analysis timed out"],
                "metrics": {}
            }

        except FileNotFoundError as e:
            if "bandit" in str(e).lower():
                raise BanditAnalysisError("Bandit is not installed. Please install it with: pip install bandit")
            else:
                raise BanditAnalysisError(f"File not found: {e}")

        except Exception as e:
            raise BanditAnalysisError(f"Bandit analysis failed: {e}")

    def _build_bandit_command(self, file_path: Path) -> List[str]:
        """构建bandit命令"""
        cmd = ["bandit"]

        # 输出格式为JSON
        cmd.extend(["-f", "json"])

        # 设置严重程度级别
        cmd.extend(["-ll"])  # 显示低级别及以上
        cmd.extend(["-iii"])  # 显示置信度信息

        # 使用配置文件
        config_file = self.config_file or self.default_config_file
        if config_file and Path(config_file).exists():
            cmd.extend(["-c", config_file])

        # 不显示进度条
        cmd.append("-q")

        # 添加文件路径
        cmd.append(str(file_path))

        return cmd

    def _parse_bandit_output(self, stdout: str, stderr: str, returncode: int, file_path: Path) -> Dict[str, Any]:
        """解析bandit输出"""
        result = {
            "file_path": str(file_path),
            "vulnerabilities": [],
            "messages": [],
            "metrics": {},
            "return_code": returncode
        }

        # 尝试解析JSON输出
        if stdout.strip():
            try:
                bandit_result = json.loads(stdout)
                result["vulnerabilities"] = self._parse_vulnerabilities(bandit_result)
                result["metrics"] = self._parse_metrics(bandit_result)
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试解析文本输出
                vulnerabilities = self._parse_text_output(stdout, file_path)
                result["vulnerabilities"].extend(vulnerabilities)

        # 解析stderr输出
        if stderr.strip():
            # 尝试从stderr解析JSON
            try:
                bandit_result = json.loads(stderr)
                vulnerabilities = self._parse_vulnerabilities(bandit_result)
                result["vulnerabilities"].extend(vulnerabilities)
            except json.JSONDecodeError:
                # 如果不是JSON，则作为错误消息处理
                if "No issues identified" not in stderr:
                    result["messages"].append(f"Bandit stderr: {stderr.strip()}")

        # 如果返回码非0且没有发现漏洞，可能是配置错误
        if returncode != 0 and not result["vulnerabilities"] and not result["messages"]:
            result["messages"].append(f"Bandit exited with code {returncode}")

        return result

    def _parse_vulnerabilities(self, bandit_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析bandit JSON结果中的漏洞信息"""
        vulnerabilities = []

        results = bandit_result.get('results', [])
        for item in results:
            vulnerability = {
                "test_id": item.get("test_id", ""),
                "test_name": item.get("test_name", ""),
                "issue_text": item.get("issue_text", ""),
                "issue_severity": item.get("issue_severity", "").lower(),
                "issue_confidence": item.get("issue_confidence", "").lower(),
                "file_path": item.get("filename", ""),
                "line_number": item.get("line_number", 0),
                "line_range": item.get("line_range", []),
                "test_id": item.get("test_id", ""),
                "code": item.get("code", ""),
                "vulnerability_type": self._get_vulnerability_type(item.get("test_name", "")),
                "severity": self._normalize_severity(item.get("issue_severity", "")),
                "confidence": self._normalize_confidence(item.get("issue_confidence", ""))
            }

            vulnerabilities.append(vulnerability)

        return vulnerabilities

    def _parse_metrics(self, bandit_result: Dict[str, Any]) -> Dict[str, Any]:
        """解析bandit的指标信息"""
        metrics = bandit_result.get('metrics', {})

        # 提取关键指标
        return {
            "loc": metrics.get("_totals", {}).get("loc", 0),
            "nosec": metrics.get("_totals", {}).get("nosec", 0),
            "skipped_tests": metrics.get("_totals", {}).get("skipped_tests", 0),
            "high_severity": metrics.get("_totals", {}).get("HIGH", 0),
            "medium_severity": metrics.get("_totals", {}).get("MEDIUM", 0),
            "low_severity": metrics.get("_totals", {}).get("LOW", 0),
            "total_issues": metrics.get("_totals", {}).get("UNDEFINED", 0)
        }

    def _parse_text_output(self, output: str, file_path: Path) -> List[Dict[str, Any]]:
        """解析bandit文本输出"""
        vulnerabilities = []
        lines = output.strip().split('\n')

        current_vuln = None
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 匹配问题标题行
            # 例如: >> Issue: [B101:hardcoded_password] Hardcoded password detected
            title_match = re.match(r'>> Issue: \[([^\]]+)\] (.+)', line)
            if title_match:
                # 如果之前有漏洞，先添加到列表
                if current_vuln:
                    vulnerabilities.append(current_vuln)

                test_info, issue_text = title_match.groups()
                if ":" in test_info:
                    test_id, test_name = test_info.split(":", 1)
                else:
                    test_id = test_info
                    test_name = test_info

                current_vuln = {
                    "test_id": test_id,
                    "test_name": test_name,
                    "issue_text": issue_text,
                    "file_path": str(file_path),
                    "vulnerability_type": self._get_vulnerability_type(test_name),
                    "code": []
                }
                continue

            # 匹配位置信息
            # 例如:   Severity: Medium   Confidence: High
            if current_vuln and "Severity:" in line:
                severity_match = re.search(r'Severity:\s*(\w+)', line)
                confidence_match = re.search(r'Confidence:\s*(\w+)', line)

                if severity_match:
                    current_vuln["severity"] = self._normalize_severity(severity_match.group(1))
                if confidence_match:
                    current_vuln["confidence"] = self._normalize_confidence(confidence_match.group(1))
                continue

            # 匹配文件位置
            # 例如:   Location: examples/test.py:5
            if current_vuln and "Location:" in line:
                location_match = re.search(r'Location:\s*([^:]+):(\d+)', line)
                if location_match:
                    current_vuln["line_number"] = int(location_match.group(2))
                continue

            # 匹配代码行
            # 例如:   4       password = "secret123"
            if current_vuln and re.match(r'^\s*\d+\s+', line):
                current_vuln["code"].append(line)
                continue

        # 添加最后一个漏洞
        if current_vuln:
            vulnerabilities.append(current_vuln)

        return vulnerabilities

    def _get_vulnerability_type(self, test_name: str) -> str:
        """根据测试名称获取漏洞类型"""
        test_name_lower = test_name.lower()

        for key, value in self.vulnerability_types.items():
            if key in test_name_lower:
                return value

        return self.vulnerability_types['default']

    def _normalize_severity(self, severity: str) -> str:
        """标准化严重程度"""
        severity = severity.lower().strip()
        return self.severity_mapping.get(severity, 'unknown')

    def _normalize_confidence(self, confidence: str) -> str:
        """标准化置信度"""
        confidence = confidence.lower().strip()
        return confidence

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
            "total_vulnerabilities": len(result["vulnerabilities"]),
            "severity_distribution": {},
            "vulnerability_types": {},
            "confidence_distribution": {},
            "has_high_risk": False,
            "high_risk_count": 0,
            "metrics": result.get("metrics", {})
        }

        # 统计漏洞分布
        for vuln in result["vulnerabilities"]:
            severity = vuln.get("severity", "unknown")
            vuln_type = vuln.get("vulnerability_type", "unknown")
            confidence = vuln.get("confidence", "unknown")

            # 严重程度统计
            summary["severity_distribution"][severity] = summary["severity_distribution"].get(severity, 0) + 1

            # 漏洞类型统计
            summary["vulnerability_types"][vuln_type] = summary["vulnerability_types"].get(vuln_type, 0) + 1

            # 置信度统计
            summary["confidence_distribution"][confidence] = summary["confidence_distribution"].get(confidence, 0) + 1

            # 高风险检查
            if severity == "high":
                summary["has_high_risk"] = True
                summary["high_risk_count"] += 1

        # 添加消息
        if result.get("messages"):
            summary["messages"] = result["messages"]

        return summary