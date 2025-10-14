"""
测试LLM响应解析器
"""

import pytest
import json
from src.llm.response_parser import LLMResponseParser, ParsedAnalysis, ParseResult


class TestLLMResponseParser:
    """测试LLM响应解析器"""

    @pytest.fixture
    def parser(self):
        """解析器fixture"""
        return LLMResponseParser()

    def test_perfect_json_response(self, parser):
        """测试完美的JSON响应"""
        response = json.dumps({
            "defects": [
                {
                    "id": "defect_1",
                    "type": "sql_injection",
                    "severity": "high",
                    "title": "SQL注入漏洞",
                    "description": "代码中存在SQL注入漏洞",
                    "location": {
                        "file": "app.py",
                        "line": 45,
                        "column": 10
                    },
                    "fix_suggestion": "使用参数化查询"
                }
            ],
            "summary": {
                "total_defects": 1,
                "severity_distribution": {"high": 1}
            }
        })

        result = parser.parse_analysis_response(response)

        assert result.status == ParseResult.SUCCESS
        assert len(result.defects) == 1
        assert result.defects[0]["id"] == "defect_1"
        assert result.defects[0]["severity"] == "high"
        assert result.defects[0]["location"]["file"] == "app.py"
        assert result.defects[0]["location"]["line"] == 45
        assert result.summary["total_defects"] == 1

    def test_nested_json_response(self, parser):
        """测试嵌套JSON响应"""
        response = '''
        以下是分析结果：

        {
            "defects": [
                {
                    "type": "buffer_overflow",
                    "severity": "critical",
                    "title": "缓冲区溢出",
                    "location": {"file": "buffer.c", "line": 23}
                }
            ],
            "summary": {"total_defects": 1}
        }

        分析完成。
        '''

        result = parser.parse_analysis_response(response)

        assert result.status == ParseResult.SUCCESS
        assert len(result.defects) == 1
        assert result.defects[0]["severity"] == "critical"
        assert result.defects[0]["type"] == "buffer_overflow"

    def test_markdown_json_response(self, parser):
        """测试Markdown格式的JSON响应"""
        response = '''
        # 安全分析报告

        ```json
        {
            "defects": [
                {
                    "type": "xss",
                    "severity": "medium",
                    "title": "跨站脚本攻击",
                    "location": {"file": "web.html", "line": 15}
                }
            ],
            "summary": {"total_defects": 1}
        }
        ```
        '''

        result = parser.parse_analysis_response(response)

        assert result.status == ParseResult.SUCCESS
        assert len(result.defects) == 1
        assert result.defects[0]["type"] == "xss"

    def test_partial_json_with_errors(self, parser):
        """测试有错误的JSON响应"""
        response = '''
        {
            "defects": [
                {
                    type: "hardcoded_password",
                    severity: "high",
                    title: "硬编码密码",
                    location: {file: "config.py", line: 12}
                }
            ],
            summary: {total_defects: 1}
        }
        '''

        result = parser.parse_analysis_response(response)

        # 应该能够部分解析成功
        assert result.status in [ParseResult.SUCCESS, ParseResult.PARTIAL]
        if result.defects:
            assert len(result.defects) >= 1

    def test_defect_normalization(self, parser):
        """测试缺陷标准化"""
        response = json.dumps({
            "defects": [
                {
                    "id": "test_1",
                    "type": "测试类型",
                    "severity": "安全",
                    "name": "测试缺陷",
                    "details": "这是一个测试缺陷",
                    "position": {"filename": "test.py", "line_number": 10},
                    "suggestion": "修复建议"
                }
            ]
        })

        result = parser.parse_analysis_response(response)

        assert result.status == ParseResult.SUCCESS
        defect = result.defects[0]

        # 检查字段标准化
        assert defect["id"] == "test_1"
        assert defect["type"] == "测试类型"
        assert defect["severity"] == "high"  # "安全" -> "high"
        assert defect["title"] == "测试缺陷"
        assert defect["description"] == "这是一个测试缺陷"
        assert defect["location"]["file"] == "test.py"
        assert defect["location"]["line"] == 10
        assert defect["fix_suggestion"] == "修复建议"

    def test_text_extraction_fallback(self, parser):
        """测试文本提取回退机制"""
        response = '''
        分析发现以下问题：

        1. SQL注入漏洞 - 代码中存在SQL注入风险
           建议使用参数化查询来修复

        2. 硬编码密码 - 配置文件中包含硬编码密码
           建议使用环境变量或配置管理系统
        '''

        result = parser.parse_analysis_response(response)

        # 应该能够从文本中提取一些信息
        assert result.status in [ParseResult.PARTIAL, ParseResult.FAILED]
        if result.status == ParseResult.PARTIAL:
            assert len(result.defects) >= 1

    def test_empty_response(self, parser):
        """测试空响应"""
        result = parser.parse_analysis_response("")

        assert result.status == ParseResult.FAILED
        assert len(result.defects) == 0
        assert len(result.parse_errors) > 0

    def test_malformed_json_response(self, parser):
        """测试格式错误的JSON响应"""
        response = '''
        {
            "defects": [
                {
                    "type": "test",
                    "severity": "medium"
            ]
        }
        '''

        result = parser.parse_analysis_response(response)

        assert result.status == ParseResult.FAILED
        assert len(result.parse_errors) > 0

    def test_severity_normalization(self, parser):
        """测试严重程度标准化"""
        test_cases = [
            ("critical", "critical"),
            ("CRITICAL", "critical"),
            ("high", "high"),
            ("HIGH", "high"),
            ("medium", "medium"),
            ("MEDIUM", "medium"),
            ("low", "low"),
            ("warning", "medium"),
            ("error", "high"),
            ("安全", "high"),
            ("警告", "medium"),
            ("提示", "info"),
            ("unknown", "medium")
        ]

        for input_severity, expected in test_cases:
            response = json.dumps({
                "defects": [{
                    "type": "test",
                    "severity": input_severity,
                    "title": "测试"
                }]
            })

            result = parser.parse_analysis_response(response)
            assert result.status == ParseResult.SUCCESS
            assert result.defects[0]["severity"] == expected

    def test_location_normalization(self, parser):
        """测试位置信息标准化"""
        test_cases = [
            ({"file": "test.py", "line": 10, "col": 5}, {"file": "test.py", "line": 10, "column": 5}),
            ({"filename": "test.py", "line_number": 10}, {"file": "test.py", "line": 10, "column": 0}),
            ("test.py:10:5", {"file": "test.py", "line": 10, "column": 5}),
            ("test.py:10", {"file": "test.py", "line": 10, "column": 0}),
            (None, {"file": "", "line": 0, "column": 0})
        ]

        for input_location, expected in test_cases:
            response = json.dumps({
                "defects": [{
                    "type": "test",
                    "severity": "medium",
                    "title": "测试",
                    "location": input_location
                }]
            })

            result = parser.parse_analysis_response(response)
            assert result.status == ParseResult.SUCCESS

            location = result.defects[0]["location"]
            assert location["file"] == expected["file"]
            assert location["line"] == expected["line"]
            assert location["column"] == expected["column"]

    def test_summary_generation(self, parser):
        """测试摘要生成"""
        response = json.dumps({
            "defects": [
                {"type": "sql_injection", "severity": "critical", "title": "SQL注入"},
                {"type": "xss", "severity": "high", "title": "XSS漏洞"},
                {"type": "hardcoded_password", "severity": "medium", "title": "硬编码密码"},
                {"type": "info_leak", "severity": "low", "title": "信息泄露"}
            ]
        })

        result = parser.parse_analysis_response(response)

        assert result.status == ParseResult.SUCCESS
        assert result.summary["total_defects"] == 4
        assert result.summary["severity_distribution"]["critical"] == 1
        assert result.summary["severity_distribution"]["high"] == 1
        assert result.summary["severity_distribution"]["medium"] == 1
        assert result.summary["severity_distribution"]["low"] == 1
        assert len(result.summary["recommendations"]) >= 1

    def test_validation(self, parser):
        """测试结果验证"""
        # 测试有效结果
        valid_response = json.dumps({
            "defects": [
                {
                    "type": "test",
                    "severity": "medium",
                    "title": "测试缺陷",
                    "description": "测试描述",
                    "location": {"file": "test.py", "line": 10}
                }
            ]
        })

        result = parser.parse_analysis_response(valid_response)
        validation = parser.validate_parsed_result(result)

        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0

        # 测试无效结果
        invalid_response = json.dumps({
            "defects": [
                {
                    "type": "test",
                    "severity": "medium"
                    # 缺少title、description等字段
                }
            ]
        })

        result = parser.parse_analysis_response(invalid_response)
        validation = parser.validate_parsed_result(result)

        # 应该有警告，但仍然认为是有效的
        assert len(validation["warnings"]) > 0

    def test_statistics_generation(self, parser):
        """测试统计信息生成"""
        response = json.dumps({
            "defects": [
                {"type": "test", "severity": "critical", "title": "严重缺陷"},
                {"type": "test2", "severity": "high", "title": "高风险缺陷"}
            ]
        })

        result = parser.parse_analysis_response(response)
        stats = result.metadata.get("statistics", {})

        assert stats["parse_status"] == ParseResult.SUCCESS.value
        assert stats["defects_count"] == 2
        assert stats["has_critical_issues"] is True
        assert stats["has_high_issues"] is True
        assert stats["response_length"] > 0

    def test_metadata_preservation(self, parser):
        """测试元数据保留"""
        response = json.dumps({
            "defects": [
                {
                    "type": "test",
                    "severity": "medium",
                    "title": "测试",
                    "custom_field": "自定义值",
                    "extra_info": {"key": "value"}
                }
            ]
        })

        result = parser.parse_analysis_response(response)
        defect = result.defects[0]

        assert "custom_field" in defect["metadata"]
        assert defect["metadata"]["custom_field"] == "自定义值"
        assert "extra_info" in defect["metadata"]
        assert defect["metadata"]["extra_info"]["key"] == "value"