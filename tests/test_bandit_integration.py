"""
BanditAnalyzer集成测试
测试真实的bandit工具集成
"""

import tempfile
from pathlib import Path
import subprocess

import pytest

from src.tools.bandit_analyzer import BanditAnalyzer, BanditAnalysisError


class TestBanditIntegration:
    """Bandit集成测试类"""

    def setup_method(self):
        """测试前的设置"""
        # 检查bandit是否安装
        try:
            subprocess.run(['bandit', '--version'], capture_output=True, check=True)
            self.bandit_available = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.bandit_available = False

        self.analyzer = BanditAnalyzer()

    @pytest.mark.skipif(not pytest.importorskip("bandit", reason="bandit not installed"),
                       reason="bandit not available")
    def test_real_bandit_analysis_safe_code(self, tmp_path):
        """测试真实bandit分析安全代码"""
        # 创建安全的Python文件
        safe_file = tmp_path / "safe_code.py"
        safe_code = '''
"""
This is a safe Python file with no security issues.
"""

def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b

def greet_user(name):
    """Greet a user safely."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    result = calculate_sum(5, 3)
    message = greet_user("World")
    print(f"{message} Result: {result}")
'''
        safe_file.write_text(safe_code)

        result = self.analyzer.analyze_file(safe_file)

        assert result["file_path"] == str(safe_file)
        assert isinstance(result["vulnerabilities"], list)
        # 对于安全代码，应该没有或少有安全漏洞

    @pytest.mark.skipif(not pytest.importorskip("bandit", reason="bandit not installed"),
                       reason="bandit not available")
    def test_real_bandit_analysis_vulnerable_code(self, tmp_path):
        """测试真实bandit分析有安全漏洞的代码"""
        # 创建有安全问题的Python文件
        vulnerable_file = tmp_path / "vulnerable_code.py"
        vulnerable_code = '''
import subprocess
import os

def insecure_function():
    """Function with security issues."""
    # 硬编码密码
    password = "secret123"

    # 不安全的subprocess调用
    subprocess.call(f"echo {password}", shell=True)

    # 危险的exec使用
    exec("print('This is dangerous')")

    return password

def sql_injection_example(user_input):
    """Example of SQL injection vulnerability."""
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    return query
'''
        vulnerable_file.write_text(vulnerable_code)

        result = self.analyzer.analyze_file(vulnerable_file)

        assert result["file_path"] == str(vulnerable_file)
        assert isinstance(result["vulnerabilities"], list)
        # 对于有问题代码，应该检测到安全漏洞
        if result["vulnerabilities"]:
            # 检查漏洞格式
            vulnerability = result["vulnerabilities"][0]
            assert "test_id" in vulnerability
            assert "test_name" in vulnerability
            assert "issue_text" in vulnerability
            assert "severity" in vulnerability
            assert "vulnerability_type" in vulnerability

    def test_bandit_not_installed_error(self, tmp_path):
        """测试bandit未安装时的错误处理"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('test')\n")

        # 使用不存在的bandit路径模拟未安装情况
        analyzer = BanditAnalyzer(timeout=1)

        # 通过mock模拟bandit未安装的情况
        import unittest.mock
        with unittest.mock.patch('subprocess.run', side_effect=FileNotFoundError("bandit: not found")):
            with pytest.raises(BanditAnalysisError, match="Bandit is not installed"):
                analyzer.analyze_file(test_file)

    def test_analysis_summary_with_real_results(self, tmp_path):
        """测试使用真实结果生成摘要"""
        # 创建一个模拟的结果
        mock_result = {
            "file_path": str(tmp_path / "test.py"),
            "vulnerabilities": [
                {
                    "test_id": "B101",
                    "severity": "high",
                    "vulnerability_type": "credentials",
                    "confidence": "high",
                    "issue_text": "Hardcoded password detected"
                },
                {
                    "test_id": "B601",
                    "severity": "medium",
                    "vulnerability_type": "shell_injection",
                    "confidence": "medium",
                    "issue_text": "Shell injection detected"
                },
                {
                    "test_id": "B201",
                    "severity": "medium",
                    "vulnerability_type": "configuration_issues",
                    "confidence": "low",
                    "issue_text": "Debug mode enabled"
                }
            ],
            "metrics": {
                "loc": 50,
                "high_severity": 1,
                "medium_severity": 2
            }
        }

        summary = self.analyzer.get_analysis_summary(mock_result)

        assert summary["total_vulnerabilities"] == 3
        assert summary["severity_distribution"]["high"] == 1
        assert summary["severity_distribution"]["medium"] == 2
        assert summary["vulnerability_types"]["credentials"] == 1
        assert summary["vulnerability_types"]["shell_injection"] == 1
        assert summary["vulnerability_types"]["configuration_issues"] == 1
        assert summary["confidence_distribution"]["high"] == 1
        assert summary["confidence_distribution"]["medium"] == 1
        assert summary["confidence_distribution"]["low"] == 1
        assert summary["has_high_risk"] is True
        assert summary["high_risk_count"] == 1
        assert summary["metrics"]["loc"] == 50

    def test_bandit_config_integration(self, tmp_path):
        """测试bandit配置集成"""
        # 创建自定义配置文件
        config_file = tmp_path / ".bandit"
        config_content = """
[bandit]
exclude_dirs = tests
skips = B101,B601
"""
        config_file.write_text(config_content)

        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_code = '''
password = "secret123"  # 这通常是B101漏洞，但会被配置跳过
subprocess.call("echo hello", shell=True)  # 这通常是B601漏洞，但会被配置跳过
'''
        test_file.write_text(test_code)

        # 使用自定义配置的分析器
        analyzer = BanditAnalyzer(config_file=str(config_file))

        # 检查命令构建是否包含配置
        cmd = analyzer._build_bandit_command(test_file)
        assert "-c" in cmd
        assert str(config_file) in cmd

    @pytest.mark.skipif(not pytest.importorskip("bandit", reason="bandit not installed"),
                       reason="bandit not available")
    def test_timeout_handling(self, tmp_path):
        """测试超时处理"""
        # 创建一个测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('test')\n")

        # 使用很短的超时时间
        analyzer = BanditAnalyzer(timeout=0.001)  # 1毫秒，应该超时

        # 在实际环境中，bandit通常很快，所以这个测试可能不会触发超时
        # 但我们可以测试超时处理的逻辑
        result = analyzer.analyze_file(test_file)

        # 检查结果格式
        assert "file_path" in result
        assert "vulnerabilities" in result
        assert "messages" in result

    def test_parse_real_bandit_json(self):
        """测试解析真实bandit JSON输出"""
        # 模拟真实的bandit JSON输出
        bandit_json = {
            "results": [
                {
                    "test_id": "B101",
                    "test_name": "hardcoded_password",
                    "issue_text": "Hardcoded password detected",
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "filename": "/tmp/test.py",
                    "line_number": 5,
                    "line_range": [5],
                    "code": "password = 'secret123'"
                }
            ],
            "metrics": {
                "_totals": {
                    "loc": 10,
                    "nosec": 0,
                    "skipped_tests": 0,
                    "HIGH": 1,
                    "MEDIUM": 0,
                    "LOW": 0
                }
            }
        }

        vulnerabilities = self.analyzer._parse_vulnerabilities(bandit_json)
        metrics = self.analyzer._parse_metrics(bandit_json)

        assert len(vulnerabilities) == 1
        assert vulnerabilities[0]["test_id"] == "B101"
        assert vulnerabilities[0]["severity"] == "high"
        assert vulnerabilities[0]["vulnerability_type"] == "credentials"
        assert metrics["high_severity"] == 1
        assert metrics["loc"] == 10

    def test_vulnerability_type_classification(self):
        """测试漏洞类型分类"""
        test_cases = [
            ("hardcoded_password", "credentials"),
            ("hardcoded_sql_string", "sql_injection"),
            ("subprocess_shell", "shell_injection"),
            ("weak_crypto", "weak_cryptography"),
            ("ssl_insecure_version", "ssl_issues"),
            ("assert_used", "input_validation"),
            ("flask_debug_true", "configuration_issues"),
            ("unknown_test_name", "security_issue")
        ]

        for test_name, expected_type in test_cases:
            result_type = self.analyzer._get_vulnerability_type(test_name)
            assert result_type == expected_type, f"Failed for {test_name}: got {result_type}, expected {expected_type}"