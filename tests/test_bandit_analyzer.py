"""
BanditAnalyzer单元测试
"""

import tempfile
import subprocess
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.tools.bandit_analyzer import BanditAnalyzer, BanditAnalysisError


class TestBanditAnalyzer:
    """BanditAnalyzer测试类"""

    def setup_method(self):
        """测试前的设置"""
        self.config_manager = Mock()
        self.config_manager.get_section.return_value = {
            'bandit': {
                'severity_level': 'medium',
                'config_file': '.bandit'
            }
        }
        self.analyzer = BanditAnalyzer(config_manager=self.config_manager)

    def test_init_default_config(self):
        """测试默认配置初始化"""
        analyzer = BanditAnalyzer()
        assert analyzer.severity_level == 'medium'
        assert analyzer.timeout == 60
        assert analyzer.default_config_file == '.bandit'

    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config_manager = Mock()
        config_manager.get_section.return_value = {
            'bandit': {
                'severity_level': 'high',
                'config_file': 'custom_bandit.conf'
            }
        }
        analyzer = BanditAnalyzer(config_manager=config_manager, timeout=120)
        assert analyzer.severity_level == 'high'
        assert analyzer.timeout == 120

    def test_build_bandit_command_basic(self):
        """测试构建基本bandit命令"""
        file_path = Path("test.py")
        cmd = self.analyzer._build_bandit_command(file_path)

        expected_parts = ["bandit", "-f", "json", "-ll", "-iii", "-q", "test.py"]
        for part in expected_parts:
            assert part in cmd

    def test_build_bandit_command_with_config_file(self):
        """测试带配置文件的bandit命令构建"""
        config_file = "custom_bandit.conf"
        analyzer = BanditAnalyzer(
            config_manager=self.config_manager,
            config_file=config_file
        )

        with patch('pathlib.Path.exists', return_value=True):
            file_path = Path("test.py")
            cmd = analyzer._build_bandit_command(file_path)

            assert "-c" in cmd
            assert config_file in cmd
            assert "test.py" in cmd

    def test_analyze_file_success(self, tmp_path):
        """测试成功分析文件"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        # 模拟bandit JSON输出
        mock_bandit_output = {
            "results": [
                {
                    "test_id": "B101",
                    "test_name": "hardcoded_password",
                    "issue_text": "Hardcoded password detected",
                    "issue_severity": "high",
                    "issue_confidence": "high",
                    "filename": str(test_file),
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

        mock_result = Mock()
        mock_result.stdout = json.dumps(mock_bandit_output)
        mock_result.stderr = ""
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            result = self.analyzer.analyze_file(test_file)

            assert result["file_path"] == str(test_file)
            assert len(result["vulnerabilities"]) == 1
            assert result["vulnerabilities"][0]["test_id"] == "B101"
            assert result["vulnerabilities"][0]["severity"] == "high"
            assert "Hardcoded password detected" in result["vulnerabilities"][0]["issue_text"]
            assert result["metrics"]["high_severity"] == 1

    def test_analyze_file_no_vulnerabilities(self, tmp_path):
        """测试分析没有安全漏洞的文件"""
        # 创建测试文件
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        # 模拟bandit没有发现漏洞的输出
        mock_bandit_output = {
            "results": [],
            "metrics": {
                "_totals": {
                    "loc": 10,
                    "nosec": 0,
                    "skipped_tests": 0,
                    "HIGH": 0,
                    "MEDIUM": 0,
                    "LOW": 0
                }
            }
        }

        mock_result = Mock()
        mock_result.stdout = json.dumps(mock_bandit_output)
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result):
            result = self.analyzer.analyze_file(test_file)

            assert result["file_path"] == str(test_file)
            assert len(result["vulnerabilities"]) == 0
            assert result["return_code"] == 0
            assert result["metrics"]["high_severity"] == 0

    def test_analyze_file_not_exists(self):
        """测试分析不存在的文件"""
        non_existent_file = Path("non_existent.py")

        with pytest.raises(BanditAnalysisError, match="File does not exist"):
            self.analyzer.analyze_file(non_existent_file)

    def test_analyze_file_not_python(self, tmp_path):
        """测试分析非Python文件"""
        non_python_file = tmp_path / "test.txt"
        non_python_file.write_text("This is not a Python file")

        with pytest.raises(BanditAnalysisError, match="File is not a Python file"):
            self.analyzer.analyze_file(non_python_file)

    def test_analyze_file_timeout(self, tmp_path):
        """测试分析超时"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("bandit", 60)):
            result = self.analyzer.analyze_file(test_file)

            assert result["file_path"] == str(test_file)
            assert result["error"] == "Analysis timeout"
            assert len(result["vulnerabilities"]) == 0
            assert "Analysis timed out" in result["messages"]

    def test_analyze_file_bandit_not_installed(self, tmp_path):
        """测试bandit未安装"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        with patch('subprocess.run', side_effect=FileNotFoundError("bandit not found")):
            with pytest.raises(BanditAnalysisError, match="Bandit is not installed"):
                self.analyzer.analyze_file(test_file)

    def test_parse_vulnerabilities(self):
        """测试解析漏洞信息"""
        bandit_result = {
            "results": [
                {
                    "test_id": "B101",
                    "test_name": "hardcoded_password",
                    "issue_text": "Hardcoded password detected",
                    "issue_severity": "high",
                    "issue_confidence": "high",
                    "filename": "test.py",
                    "line_number": 10,
                    "line_range": [10],
                    "code": "password = 'secret123'"
                },
                {
                    "test_id": "B201",
                    "test_name": "flask_debug_true",
                    "issue_text": "Flask app is running with debug enabled",
                    "issue_severity": "medium",
                    "issue_confidence": "medium",
                    "filename": "test.py",
                    "line_number": 15,
                    "line_range": [15],
                    "code": "app.run(debug=True)"
                }
            ]
        }

        vulnerabilities = self.analyzer._parse_vulnerabilities(bandit_result)

        assert len(vulnerabilities) == 2

        # 检查第一个漏洞
        vuln1 = vulnerabilities[0]
        assert vuln1["test_id"] == "B101"
        assert vuln1["test_name"] == "hardcoded_password"
        assert vuln1["severity"] == "high"
        assert vuln1["confidence"] == "high"
        assert vuln1["vulnerability_type"] == "credentials"
        assert vuln1["line_number"] == 10

        # 检查第二个漏洞
        vuln2 = vulnerabilities[1]
        assert vuln2["test_id"] == "B201"
        assert vuln2["severity"] == "medium"
        assert vuln2["vulnerability_type"] == "configuration_issues"

    def test_parse_metrics(self):
        """测试解析指标信息"""
        bandit_result = {
            "metrics": {
                "_totals": {
                    "loc": 100,
                    "nosec": 2,
                    "skipped_tests": 1,
                    "HIGH": 3,
                    "MEDIUM": 5,
                    "LOW": 10
                }
            }
        }

        metrics = self.analyzer._parse_metrics(bandit_result)

        assert metrics["loc"] == 100
        assert metrics["nosec"] == 2
        assert metrics["skipped_tests"] == 1
        assert metrics["high_severity"] == 3
        assert metrics["medium_severity"] == 5
        assert metrics["low_severity"] == 10

    def test_parse_text_output(self):
        """测试解析文本输出"""
        text_output = """
>> Issue: [B101:hardcoded_password] Hardcoded password detected
   Severity: High   Confidence: High
   Location: test.py:10
   10       password = "secret123"
   11
>> Issue: [B201:flask_debug_true] Flask app is running with debug enabled
   Severity: Medium   Confidence: Medium
   Location: test.py:15
   15       app.run(debug=True)
        """

        file_path = Path("test.py")
        vulnerabilities = self.analyzer._parse_text_output(text_output, file_path)

        assert len(vulnerabilities) == 2

        # 检查第一个漏洞
        vuln1 = vulnerabilities[0]
        assert vuln1["test_id"] == "B101"
        assert vuln1["test_name"] == "hardcoded_password"
        assert vuln1["severity"] == "high"
        assert vuln1["confidence"] == "high"
        assert vuln1["line_number"] == 10
        assert vuln1["vulnerability_type"] == "credentials"

        # 检查第二个漏洞
        vuln2 = vulnerabilities[1]
        assert vuln2["test_id"] == "B201"
        assert vuln2["severity"] == "medium"
        assert vuln2["confidence"] == "medium"

    def test_get_vulnerability_type(self):
        """测试获取漏洞类型"""
        assert self.analyzer._get_vulnerability_type("hardcoded_password") == "credentials"
        assert self.analyzer._get_vulnerability_type("hardcoded_sql_string") == "sql_injection"
        assert self.analyzer._get_vulnerability_type("subprocess_shell") == "shell_injection"
        assert self.analyzer._get_vulnerability_type("weak_crypto") == "weak_cryptography"
        assert self.analyzer._get_vulnerability_type("ssl_insecure_version") == "ssl_issues"
        assert self.analyzer._get_vulnerability_type("unknown_test") == "security_issue"

    def test_normalize_severity(self):
        """测试标准化严重程度"""
        assert self.analyzer._normalize_severity("HIGH") == "high"
        assert self.analyzer._normalize_severity("MEDIUM") == "medium"
        assert self.analyzer._normalize_severity("LOW") == "low"
        assert self.analyzer._normalize_severity("unknown") == "unknown"

    def test_normalize_confidence(self):
        """测试标准化置信度"""
        assert self.analyzer._normalize_confidence("HIGH") == "high"
        assert self.analyzer._normalize_confidence("MEDIUM") == "medium"
        assert self.analyzer._normalize_confidence("LOW") == "low"

    def test_get_analysis_summary(self):
        """测试获取分析摘要"""
        result = {
            "file_path": "test.py",
            "vulnerabilities": [
                {
                    "severity": "high",
                    "vulnerability_type": "credentials",
                    "confidence": "high"
                },
                {
                    "severity": "medium",
                    "vulnerability_type": "sql_injection",
                    "confidence": "medium"
                },
                {
                    "severity": "high",
                    "vulnerability_type": "credentials",
                    "confidence": "low"
                }
            ],
            "metrics": {
                "loc": 100,
                "high_severity": 2,
                "medium_severity": 1
            },
            "messages": ["Some warning message"]
        }

        summary = self.analyzer.get_analysis_summary(result)

        assert summary["file_path"] == "test.py"
        assert summary["total_vulnerabilities"] == 3
        assert summary["severity_distribution"]["high"] == 2
        assert summary["severity_distribution"]["medium"] == 1
        assert summary["vulnerability_types"]["credentials"] == 2
        assert summary["vulnerability_types"]["sql_injection"] == 1
        assert summary["confidence_distribution"]["high"] == 1
        assert summary["confidence_distribution"]["medium"] == 1
        assert summary["confidence_distribution"]["low"] == 1
        assert summary["has_high_risk"] is True
        assert summary["high_risk_count"] == 2
        assert summary["metrics"]["loc"] == 100
        assert summary["messages"] == ["Some warning message"]

    def test_get_analysis_summary_no_vulnerabilities(self):
        """测试获取没有漏洞的分析摘要"""
        result = {
            "file_path": "test.py",
            "vulnerabilities": [],
            "metrics": {
                "loc": 50,
                "high_severity": 0,
                "medium_severity": 0
            }
        }

        summary = self.analyzer.get_analysis_summary(result)

        assert summary["total_vulnerabilities"] == 0
        assert summary["severity_distribution"] == {}
        assert summary["vulnerability_types"] == {}
        assert summary["confidence_distribution"] == {}
        assert summary["has_high_risk"] is False
        assert summary["high_risk_count"] == 0

    def test_parse_bandit_output_with_stderr(self, tmp_path):
        """测试解析包含stderr的输出"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        # 模拟bandit输出到stderr
        mock_bandit_output = {
            "results": [
                {
                    "test_id": "B101",
                    "test_name": "hardcoded_password",
                    "issue_text": "Hardcoded password detected",
                    "issue_severity": "high",
                    "issue_confidence": "high",
                    "filename": str(test_file),
                    "line_number": 5,
                    "line_range": [5],
                    "code": "password = 'secret123'"
                }
            ],
            "metrics": {}
        }

        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = json.dumps(mock_bandit_output)
        mock_result.returncode = 1

        with patch('subprocess.run', return_value=mock_result):
            result = self.analyzer.analyze_file(test_file)

            assert len(result["vulnerabilities"]) == 1
            assert result["vulnerabilities"][0]["test_id"] == "B101"

    def test_parse_bandit_output_json_decode_error(self, tmp_path):
        """测试JSON解析错误的处理"""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')\n")

        # 模拟无效的JSON输出
        mock_result = Mock()
        mock_result.stdout = "invalid json output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        with patch('subprocess.run', return_value=mock_result):
            result = self.analyzer.analyze_file(test_file)

            assert result["file_path"] == str(test_file)
            assert len(result["vulnerabilities"]) == 0