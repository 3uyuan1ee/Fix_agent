"""
测试深度分析执行流程
"""

import pytest
import tempfile
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from src.tools.deep_analyzer import DeepAnalyzer, DeepAnalysisRequest, DeepAnalysisResult
from src.tools.deep_report_generator import DeepAnalysisReportGenerator


class TestDeepAnalysisFlow:
    """测试深度分析执行流程"""

    @pytest.fixture
    def temp_project_dir(self):
        """临时项目目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            # 创建测试Python文件
            (project_dir / "example.py").write_text("""
import os
import subprocess
import json

class DataProcessor:
    def __init__(self):
        self.data = []
        self.processed_count = 0

    def process_data(self, input_data):
        # 硬编码的SQL查询 - 安全问题
        query = f"SELECT * FROM users WHERE id = {input_data['user_id']}"

        # 使用eval的危险操作
        eval(f"print('Processing {input_data}')")

        # 性能问题：循环内重复连接数据库
        results = []
        for item in self.data:
            # 每次循环都建立新连接
            conn = self._create_database_connection()
            result = conn.execute(query)
            results.append(result)
            self.processed_count += 1

        return results

    def _create_database_connection(self):
        # 模拟数据库连接
        return MockConnection()

class MockConnection:
    def execute(self, query):
        return []

def main():
    processor = DataProcessor()

    # 处理用户输入
    user_input = {"user_id": 123, "data": "test"}
    results = processor.process_data(user_input)

    # 输出结果（未使用返回值）
    print(f"Processed {len(results)} items")

if __name__ == "__main__":
    main()
            """)

            # 创建简单的Python文件
            (project_dir / "simple.py").write_text("""
def hello_world():
    print("Hello, World!")
    return True

def add_numbers(a, b):
    return a + b

class Calculator:
    def __init__(self):
        self.history = []

    def calculate(self, operation, a, b):
        result = 0
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        else:
            raise ValueError(f"Unsupported operation: {operation}")

        self.history.append(f"{operation}({a}, {b}) = {result}")
        return result
            """)

            yield str(project_dir)

    @pytest.fixture
    def deep_analyzer(self):
        """深度分析器fixture"""
        # 创建一个简单的Mock对象来替代AsyncMock的logger
        from unittest.mock import Mock
        mock_logger = Mock()
        mock_logger.info = Mock()
        mock_logger.error = Mock()
        mock_logger.warning = Mock()

        # 使用mock的LLM客户端来避免初始化问题
        mock_llm_client = AsyncMock()
        mock_llm_client.create_request = lambda messages, model, temperature, max_tokens: {
            'messages': messages,
            'model': model,
            'temperature': temperature,
            'max_tokens': max_tokens
        }

        # Mock DeepAnalyzer without real LLM client
        analyzer = DeepAnalyzer.__new__(DeepAnalyzer)
        analyzer.llm_client = mock_llm_client
        analyzer.prompt_manager = Mock()
        analyzer.prompt_manager.get_template.return_value = None
        analyzer.prompt_manager.render_template.return_value = Mock(success=False, content="")
        analyzer.config_manager = Mock()
        analyzer.config_manager.get_section.return_value = {}
        analyzer.default_model = "gpt-4"
        analyzer.default_temperature = 0.3
        analyzer.max_tokens = 4000
        analyzer.max_file_size = 100 * 1024
        analyzer.config = {}
        analyzer.logger = mock_logger

        return analyzer

    @pytest.fixture
    def report_generator(self):
        """报告生成器fixture"""
        return DeepAnalysisReportGenerator()

    @pytest.mark.asyncio
    async def test_deep_analyzer_initialization(self, deep_analyzer):
        """测试深度分析器初始化"""
        assert deep_analyzer is not None
        assert hasattr(deep_analyzer, 'llm_client')
        assert hasattr(deep_analyzer, 'prompt_manager')
        assert hasattr(deep_analyzer, 'get_supported_analysis_types')
        assert isinstance(deep_analyzer.get_supported_analysis_types(), list)

    def test_deep_analysis_request_creation(self):
        """测试深度分析请求创建"""
        request = DeepAnalysisRequest(
            file_path="/test/file.py",
            analysis_type="security",
            model="gpt-4",
            temperature=0.3,
            max_tokens=2000,
            user_instructions="Focus on security vulnerabilities"
        )

        assert request.file_path == "/test/file.py"
        assert request.analysis_type == "security"
        assert request.model == "gpt-4"
        assert request.temperature == 0.3
        assert request.max_tokens == 2000
        assert request.user_instructions == "Focus on security vulnerabilities"

    def test_file_content_reading(self, deep_analyzer, temp_project_dir):
        """测试文件内容读取"""
        # 重置_real_的_read_file_content方法
        deep_analyzer._read_file_content = DeepAnalyzer._read_file_content.__get__(deep_analyzer, DeepAnalyzer)

        # 测试正常文件读取
        file_path = Path(temp_project_dir) / "example.py"
        content = deep_analyzer._read_file_content(file_path)
        assert content is not None
        assert "DataProcessor" in content
        assert "import os" in content

        # 测试不存在的文件
        non_existent = Path(temp_project_dir) / "nonexistent.py"
        content = deep_analyzer._read_file_content(non_existent)
        assert content is None

        # 测试空文件
        empty_file = Path(temp_project_dir) / "empty.py"
        empty_file.write_text("")
        content = deep_analyzer._read_file_content(empty_file)
        assert content == ""

    def test_prompt_construction(self, deep_analyzer, temp_project_dir):
        """测试prompt构造"""
        # 重置_real_方法
        deep_analyzer._read_file_content = DeepAnalyzer._read_file_content.__get__(deep_analyzer, DeepAnalyzer)
        deep_analyzer._construct_prompt = DeepAnalyzer._construct_prompt.__get__(deep_analyzer, DeepAnalyzer)
        deep_analyzer._get_fallback_prompt = DeepAnalyzer._get_fallback_prompt.__get__(deep_analyzer, DeepAnalyzer)

        file_path = Path(temp_project_dir) / "example.py"
        file_content = deep_analyzer._read_file_content(file_path)

        request = DeepAnalysisRequest(
            file_path=str(file_path),
            analysis_type="security",
            user_instructions="Focus on SQL injection vulnerabilities"
        )

        messages = deep_analyzer._construct_prompt(file_content, request)

        assert isinstance(messages, list)
        assert len(messages) >= 2  # 至少system和user消息
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "DataProcessor" in messages[1]["content"]
        assert "security" in messages[1]["content"].lower()

    def test_llm_response_parsing(self, deep_analyzer):
        """测试LLM响应解析"""
        # 重置_real_方法
        deep_analyzer._parse_llm_response = DeepAnalyzer._parse_llm_response.__get__(deep_analyzer, DeepAnalyzer)

        # 测试JSON格式响应
        json_response = """{
            "findings": [
                {"type": "SQL Injection", "severity": "High", "line": 10},
                {"type": "Code Injection", "severity": "Critical", "line": 15}
            ],
            "recommendations": [
                {"description": "Use parameterized queries", "priority": "high"},
                {"description": "Avoid eval() function", "priority": "medium"}
            ],
            "overall_score": 7.5,
            "risk_level": "high"
        }"""

        parsed = deep_analyzer._parse_llm_response(json_response)
        assert "findings" in parsed
        assert "recommendations" in parsed
        assert parsed["overall_score"] == 7.5
        assert parsed["risk_level"] == "high"

        # 测试文本格式响应
        text_response = "Based on the code analysis, I found several security issues..."
        parsed = deep_analyzer._parse_llm_response(text_response)
        assert parsed["format"] == "text"
        assert "analysis_text" in parsed
        assert "summary" in parsed

        # 测试错误格式
        malformed_response = '{"findings": [invalid json'  # 无效JSON
        parsed = deep_analyzer._parse_llm_response(malformed_response)
        assert "parse_error" in parsed
        assert parsed["format"] == "text"

    @pytest.mark.asyncio
    async def test_mock_deep_analysis(self, deep_analyzer, temp_project_dir):
        """测试模拟深度分析"""
        file_path = Path(temp_project_dir) / "example.py"

        request = DeepAnalysisRequest(
            file_path=str(file_path),
            analysis_type="security"
        )

        # 模拟LLM响应
        mock_response = AsyncMock()
        mock_response.content = """{
            "findings": [
                {"type": "SQL Injection", "severity": "High", "line": 8, "description": "SQL injection vulnerability"},
                {"type": "Code Injection", "severity": "Critical", "line": 11, "description": "Use of eval() function"}
            ],
            "recommendations": [
                {"description": "Use parameterized queries", "priority": "high"},
                {"description": "Replace eval() with safer alternatives", "priority": "high"}
            ],
            "overall_score": 6.0,
            "risk_level": "high"
        }"""
        mock_response.usage = {"total_tokens": 1500, "prompt_tokens": 800, "completion_tokens": 700}
        mock_response.model = "gpt-4"

        with patch.object(deep_analyzer.llm_client, 'complete', return_value=mock_response):
            result = await deep_analyzer.analyze_file(request)

        assert isinstance(result, DeepAnalysisResult)
        assert result.success is True
        assert result.file_path == str(file_path)
        assert result.analysis_type == "security"
        assert result.execution_time > 0
        assert result.model_used == "gpt-4"
        assert result.structured_analysis["findings"][0]["type"] == "SQL Injection"

    def test_multiple_files_analysis(self, deep_analyzer, temp_project_dir):
        """测试多文件分析"""
        # 重置_real_方法
        deep_analyzer.analyze_files = DeepAnalyzer.analyze_files.__get__(deep_analyzer, DeepAnalyzer)

        files = [
            str(Path(temp_project_dir) / "example.py"),
            str(Path(temp_project_dir) / "simple.py")
        ]

        requests = [
            DeepAnalysisRequest(file_path=files[0], analysis_type="security"),
            DeepAnalysisRequest(file_path=files[1], analysis_type="performance")
        ]

        # 模拟LLM响应
        mock_response = AsyncMock()
        mock_response.content = "Mock analysis result"
        mock_response.usage = {"total_tokens": 1000}
        mock_response.model = "gpt-4"

        with patch.object(deep_analyzer.llm_client, 'complete', return_value=mock_response):
            results = deep_analyzer.analyze_files(requests)

        assert len(results) == 2
        assert all(isinstance(r, DeepAnalysisResult) for r in results)

    def test_supported_analysis_types(self, deep_analyzer):
        """测试支持的分析类型"""
        # 重置_real_方法
        deep_analyzer.get_supported_analysis_types = DeepAnalyzer.get_supported_analysis_types.__get__(deep_analyzer, DeepAnalyzer)

        types = deep_analyzer.get_supported_analysis_types()

        expected_types = [
            "comprehensive",
            "security",
            "performance",
            "architecture",
            "code_review",
            "refactoring"
        ]

        for expected_type in expected_types:
            assert expected_type in types

    def test_analysis_summary_generation(self, deep_analyzer):
        """测试分析摘要生成"""
        # 重置_real_方法
        deep_analyzer.get_analysis_summary = DeepAnalyzer.get_analysis_summary.__get__(deep_analyzer, DeepAnalyzer)

        # 创建模拟结果
        results = [
            DeepAnalysisResult(
                file_path="/test/file1.py",
                analysis_type="security",
                success=True,
                execution_time=1.5,
                model_used="gpt-4",
                token_usage={"total_tokens": 1000}
            ),
            DeepAnalysisResult(
                file_path="/test/file2.py",
                analysis_type="performance",
                success=True,
                execution_time=2.0,
                model_used="gpt-4",
                token_usage={"total_tokens": 1500}
            ),
            DeepAnalysisResult(
                file_path="/test/file3.py",
                analysis_type="architecture",
                success=False,
                error="API error",
                execution_time=0.0
            )
        ]

        summary = deep_analyzer.get_analysis_summary(results)

        assert summary["total_files"] == 3
        assert summary["successful_files"] == 2
        assert summary["failed_files"] == 1
        assert summary["success_rate"] == 2/3
        assert summary["total_execution_time"] == 3.5
        assert "security" in summary["analysis_types"]
        assert "performance" in summary["analysis_types"]

    def test_result_formatting_text(self, deep_analyzer):
        """测试文本格式化"""
        # 重置_real_方法
        deep_analyzer.format_analysis_result = DeepAnalyzer.format_analysis_result.__get__(deep_analyzer, DeepAnalyzer)
        deep_analyzer._format_as_text = DeepAnalyzer._format_as_text.__get__(deep_analyzer, DeepAnalyzer)

        result = DeepAnalysisResult(
            file_path="/test/example.py",
            analysis_type="security",
            success=True,
            content="This is a test analysis result.",
            structured_analysis={
                "findings": [{"type": "SQL Injection", "severity": "High"}],
                "overall_score": 7.0
            },
            execution_time=1.5,
            model_used="gpt-4"
        )

        formatted = deep_analyzer.format_analysis_result(result, "text")

        assert "深度分析报告" in formatted
        assert "/test/example.py" in formatted
        assert "security" in formatted
        assert "1.50秒" in formatted

    def test_result_formatting_json(self, deep_analyzer):
        """测试JSON格式化"""
        # 重置_real_方法
        deep_analyzer.format_analysis_result = DeepAnalyzer.format_analysis_result.__get__(deep_analyzer, DeepAnalyzer)

        result = DeepAnalysisResult(
            file_path="/test/example.py",
            analysis_type="security",
            success=True,
            content="Test content"
        )

        formatted = deep_analyzer.format_analysis_result(result, "json")

        parsed = json.loads(formatted)
        assert parsed["file_path"] == "/test/example.py"
        assert parsed["analysis_type"] == "security"
        assert parsed["success"] is True

    def test_result_formatting_markdown(self, deep_analyzer):
        """测试Markdown格式化"""
        # 重置_real_方法
        deep_analyzer.format_analysis_result = DeepAnalyzer.format_analysis_result.__get__(deep_analyzer, DeepAnalyzer)
        deep_analyzer._format_as_markdown = DeepAnalyzer._format_as_markdown.__get__(deep_analyzer, DeepAnalyzer)

        result = DeepAnalysisResult(
            file_path="/test/example.py",
            analysis_type="security",
            success=True,
            content="Test content"
        )

        formatted = deep_analyzer.format_analysis_result(result, "markdown")

        assert "# 深度分析报告" in formatted
        assert "**文件**" in formatted
        assert "/test/example.py" in formatted
        assert "✅ 成功" in formatted

    def test_report_generator_initialization(self, report_generator):
        """测试报告生成器初始化"""
        assert report_generator is not None
        assert hasattr(report_generator, 'generate_report')
        assert hasattr(report_generator, 'save_report')

    def test_report_generation(self, report_generator):
        """测试报告生成"""
        # 创建模拟结果
        results = [
            DeepAnalysisResult(
                file_path="/test/file1.py",
                analysis_type="security",
                success=True,
                content="Security analysis result",
                structured_analysis={
                    "findings": [{"type": "SQL Injection", "severity": "High"}],
                    "overall_score": 7.0,
                    "risk_level": "high"
                },
                execution_time=1.5,
                model_used="gpt-4"
            )
        ]

        report = report_generator.generate_report(results, "json")

        assert "metadata" in report
        assert "summary" in report
        assert "file_results" in report
        assert "analysis_insights" in report
        assert "recommendations" in report

        # 验证元数据
        assert report["metadata"]["total_files"] == 1
        assert report["metadata"]["successful_files"] == 1

        # 验证摘要
        assert report["summary"]["success_rate"] == 1.0

    def test_report_insights_generation(self, report_generator):
        """测试报告洞察生成"""
        # 创建多个有结构化分析的结果，确保issues字段存在
        results = [
            DeepAnalysisResult(
                file_path="/test/file1.py",
                analysis_type="security",
                success=True,
                content="Mock analysis content",  # 添加内容以满足条件
                structured_analysis={
                    "findings": [
                        {"type": "SQL Injection", "severity": "High"},
                        {"type": "XSS", "severity": "Medium"}
                    ],
                    "issues": [
                        {"type": "SQL Injection", "description": "SQL injection vulnerability"},
                        {"type": "SQL Injection", "description": "Another SQL injection issue"}
                    ],
                    "recommendations": [
                        {"category": "security", "priority": "high", "description": "Use parameterized queries"},
                        {"category": "performance", "priority": "medium", "description": "Optimize loops"}
                    ]
                }
            )
        ]

        report = report_generator.generate_report(results, "json")

        insights = report["analysis_insights"]
        assert "common_issues" in insights
        # 现在应该有SQL Injection问题的统计
        assert len(insights["common_issues"]) > 0
        assert insights["common_issues"][0]["type"] == "SQL Injection"

        # 验证安全关注点被提取
        recommendations = report["recommendations"]
        assert "security_improvements" in recommendations
        assert len(recommendations["security_improvements"]) > 0

    def test_report_saving(self, report_generator):
        """测试报告保存"""
        results = [
            DeepAnalysisResult(
                file_path="/test/file1.py",
                analysis_type="security",
                success=True,
                content="Test content"
            )
        ]

        report = report_generator.generate_report(results, "json")

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test_report.json"

            success = report_generator.save_report(report, str(output_path), "json")

            assert success is True
            assert output_path.exists()

            # 验证保存的文件内容
            with open(output_path, 'r', encoding='utf-8') as f:
                saved_report = json.load(f)

            assert "metadata" in saved_report
            assert saved_report["metadata"]["total_files"] == 1

    def test_end_to_end_flow(self, deep_analyzer, report_generator, temp_project_dir):
        """测试端到端流程"""
        files = [
            str(Path(temp_project_dir) / "example.py"),
            str(Path(temp_project_dir) / "simple.py")
        ]

        requests = [
            DeepAnalysisRequest(file_path=files[0], analysis_type="security"),
            DeepAnalysisRequest(file_path=files[1], analysis_type="performance")
        ]

        # 模拟LLM响应
        mock_response = AsyncMock()
        mock_response.content = """{
            "findings": [
                {"type": "SQL Injection", "severity": "High", "line": 8, "description": "SQL injection vulnerability in query construction"},
                {"type": "Performance Issue", "severity": "Medium", "line": 15, "description": "Inefficient database connection in loop"}
            ],
            "recommendations": [
                {"description": "Use parameterized queries for database operations", "priority": "high"},
                {"description": "Implement connection pooling for database access", "priority": "medium"}
            ],
            "overall_score": 6.5,
            "risk_level": "medium"
        }"""
        mock_response.usage = {"total_tokens": 2000, "prompt_tokens": 1000, "completion_tokens": 1000}
        mock_response.model = "gpt-4"

        # 1. 执行深度分析
        with patch.object(deep_analyzer.llm_client, 'complete', return_value=mock_response):
            results = deep_analyzer.analyze_files(requests)

        assert len(results) == 2
        assert all(isinstance(r, DeepAnalysisResult) for r in results)

        # 2. 生成报告
        report = report_generator.generate_report(results, "json")
        assert "summary" in report

        # 3. 验证报告内容
        assert report["metadata"]["total_files"] == 2
        assert report["summary"]["successful_files"] == 2

        # 4. 保存报告
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "end_to_end_report.json"
            success = report_generator.save_report(report, str(output_path))
            assert success is True
            assert output_path.exists()

    def test_error_handling(self, deep_analyzer):
        """测试错误处理"""
        # 重置_real_方法
        deep_analyzer._read_file_content = DeepAnalyzer._read_file_content.__get__(deep_analyzer, DeepAnalyzer)
        deep_analyzer.analyze_file = DeepAnalyzer.analyze_file.__get__(deep_analyzer, DeepAnalyzer)

        # 测试文件不存在的情况
        request = DeepAnalysisRequest(
            file_path="/nonexistent/file.py",
            analysis_type="security"
        )

        result = asyncio.run(deep_analyzer.analyze_file(request))
        assert result.success is False
        assert result.error is not None
        assert "nonexistent" in result.error.lower()

    def test_get_fallback_prompt(self, deep_analyzer, temp_project_dir):
        """测试fallback prompt"""
        # 重置_real_方法
        deep_analyzer._read_file_content = DeepAnalyzer._read_file_content.__get__(deep_analyzer, DeepAnalyzer)
        deep_analyzer._get_fallback_prompt = DeepAnalyzer._get_fallback_prompt.__get__(deep_analyzer, DeepAnalyzer)

        file_path = Path(temp_project_dir) / "example.py"
        file_content = deep_analyzer._read_file_content(file_path)

        request = DeepAnalysisRequest(
            file_path=str(file_path),
            analysis_type="unknown_type",  # 未知类型
            user_instructions="Special instructions"
        )

        prompt = deep_analyzer._get_fallback_prompt(file_content, request)
        assert prompt is not None
        assert file_content in prompt
        assert "unknown_type" in prompt
        assert "Special instructions" in prompt

    def cleanup(self, deep_analyzer):
        """测试清理"""
        # DeepAnalyzer目前不需要特殊清理
        pass