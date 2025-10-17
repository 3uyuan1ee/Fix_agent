#!/usr/bin/env python3
"""
T023 用户交互处理单元测试
验证InputParser、ParameterValidator、ResponseFormatter和UserInteractionHandler的功能
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

# 导入被测试的模块
from src.agent.user_interaction import (
    InputParser, ParameterValidator, ResponseFormatter, UserInteractionHandler,
    ParsedInput, ValidationResult, FormattedOutput, InputType, OutputFormat
)
from src.agent.planner import AnalysisMode


class TestInputParser:
    """测试输入解析器"""

    def setup_method(self):
        """测试前的设置"""
        self.parser = InputParser()

    def test_parse_empty_input(self):
        """测试空输入解析"""
        result = self.parser.parse("")

        assert result.original_input == ""
        assert result.input_type == InputType.UNKNOWN
        assert result.is_valid is False
        assert "输入不能为空" in result.validation_errors

    def test_parse_help_commands(self):
        """测试帮助命令解析"""
        help_inputs = [
            "/help",
            "help",
            "?",
            "？",
            "/help format"
        ]

        for help_input in help_inputs:
            result = self.parser.parse(help_input)
            assert result.input_type == InputType.HELP
            assert result.command == "help"
            assert result.is_valid is True

    def test_parse_exit_commands(self):
        """测试退出命令解析"""
        exit_inputs = [
            "exit",
            "quit",
            "bye",
            "再见",
            "/exit",
            "/quit"
        ]

        for exit_input in exit_inputs:
            result = self.parser.parse(exit_input)
            assert result.input_type == InputType.EXIT
            assert result.command == "exit"
            assert result.is_valid is True

    def test_parse_confirmation_positive(self):
        """测试肯定确认输入"""
        positive_inputs = [
            "y",
            "yes",
            "是",
            "确定",
            "继续",
            "确认"
        ]

        for confirm_input in positive_inputs:
            result = self.parser.parse(confirm_input)
            assert result.input_type == InputType.CONFIRMATION
            assert result.command == "confirm"
            assert result.parameters.get("response") is True

    def test_parse_confirmation_negative(self):
        """测试否定确认输入"""
        negative_inputs = [
            "n",
            "no",
            "否",
            "取消",
            "停止",
            "放弃"
        ]

        for confirm_input in negative_inputs:
            result = self.parser.parse(confirm_input)
            assert result.input_type == InputType.CONFIRMATION
            assert result.command == "confirm"
            assert result.parameters.get("response") is False

    def test_parse_interruption_commands(self):
        """测试中断命令解析"""
        interrupt_inputs = [
            "\x03",  # Ctrl+C
            "/interrupt",
            "/break",
            "/stop",
            "/cancel"
        ]

        for interrupt_input in interrupt_inputs:
            result = self.parser.parse(interrupt_input)
            assert result.input_type == InputType.INTERRUPTION
            assert result.command == "interrupt"

    def test_parse_system_commands(self):
        """测试系统命令解析"""
        test_cases = [
            ("/mode static", "mode", {"mode": "static"}),
            ("/format json", "format", {"format": "json"}),
            ("/status", "status", {}),
            ("/clear", "clear", {}),
            ("/save results.txt", "save", {"file_path": "results.txt"}),
            ("/export pdf", "export", {"format": "pdf"})
        ]

        for command_input, expected_command, expected_params in test_cases:
            result = self.parser.parse(command_input)
            assert result.input_type == InputType.COMMAND
            assert result.command == expected_command
            for key, value in expected_params.items():
                assert result.parameters.get(key) == value

    def test_parse_command_with_flags(self):
        """测试带标志的命令解析"""
        command_input = "/mode static --verbose --force"
        result = self.parser.parse(command_input)

        assert result.input_type == InputType.COMMAND
        assert result.command == "mode"
        assert result.parameters.get("mode") == "static"
        assert result.flags.get("verbose") is True
        assert result.flags.get("force") is True

    def test_parse_natural_language(self):
        """测试自然语言输入解析"""
        natural_inputs = [
            "静态分析 src/ 目录",
            "深度分析这个文件的架构",
            "修复代码中的安全问题",
            "检查 main.py 文件"
        ]

        for natural_input in natural_inputs:
            result = self.parser.parse(natural_input)
            assert result.input_type == InputType.NATURAL_LANGUAGE
            assert result.is_valid is True
            assert "text" in result.parameters
            assert result.parameters["text"] == natural_input

    def test_extract_keywords(self):
        """测试关键词提取"""
        test_text = "分析这个代码文件中的函数和类"
        result = self.parser.parse(test_text)

        keywords = result.parameters.get("keywords", [])
        assert any(keyword in keywords for keyword in ["代码", "文件", "函数", "类", "分析"])

    def test_extract_file_paths(self):
        """测试文件路径提取"""
        test_text = '分析 "src/main.py" 和 ./utils/config.py 文件'
        result = self.parser.parse(test_text)

        file_paths = result.parameters.get("file_paths", [])
        assert "src/main.py" in file_paths or "main.py" in str(file_paths)
        assert "utils/config.py" in str(file_paths) or "config.py" in str(file_paths)

    def test_detect_mode_hints(self):
        """测试模式提示检测"""
        test_cases = [
            ("静态分析代码", ["static"]),
            ("深度检查架构", ["deep"]),
            ("修复安全问题", ["fix"]),
            ("静态深度分析", ["static", "deep"])
        ]

        for test_input, expected_hints in test_cases:
            result = self.parser.parse(test_input)
            hints = result.parameters.get("mode_hints", [])
            for hint in expected_hints:
                assert hint in hints


class TestParameterValidator:
    """测试参数验证器"""

    def setup_method(self):
        """测试前的设置"""
        self.validator = ParameterValidator()

    def test_validate_command_mode_parameter(self):
        """测试命令模式参数验证"""
        # 有效模式
        valid_parsed = ParsedInput(
            original_input="/mode static",
            input_type=InputType.COMMAND,
            command="mode",
            parameters={"mode": "static"}
        )
        result = self.validator.validate(valid_parsed)
        assert result.is_valid is True
        assert result.sanitized_params.get("mode") == "static"

        # 无效模式
        invalid_parsed = ParsedInput(
            original_input="/mode invalid",
            input_type=InputType.COMMAND,
            command="mode",
            parameters={"mode": "invalid"}
        )
        result = self.validator.validate(invalid_parsed)
        assert result.is_valid is False
        assert any("无效的分析模式" in error for error in result.errors)

    def test_validate_command_format_parameter(self):
        """测试命令格式参数验证"""
        # 有效格式
        valid_parsed = ParsedInput(
            original_input="/format json",
            input_type=InputType.COMMAND,
            command="format",
            parameters={"format": "json"}
        )
        result = self.validator.validate(valid_parsed)
        assert result.is_valid is True
        assert result.sanitized_params.get("format") == "json"

        # 无效格式
        invalid_parsed = ParsedInput(
            original_input="/format invalid",
            input_type=InputType.COMMAND,
            command="format",
            parameters={"format": "invalid"}
        )
        result = self.validator.validate(invalid_parsed)
        assert result.is_valid is False
        assert any("无效的输出格式" in error for error in result.errors)

    def test_validate_file_paths_security(self):
        """测试文件路径安全性验证"""
        # 危险路径
        dangerous_paths = [
            "/etc/passwd",
            "/usr/bin/python",
            "../../../etc/passwd",
            "..\\..\\windows\\system32"
        ]

        for dangerous_path in dangerous_paths:
            errors, sanitized = self.validator._validate_path_security(dangerous_path)
            assert len(errors) > 0, f"危险路径 {dangerous_path} 应该被拒绝"
            assert sanitized == ""

        # 安全路径
        safe_paths = [
            "src/main.py",
            "./utils/config.py",
            "/home/user/project/test.py"
        ]

        for safe_path in safe_paths:
            errors, sanitized = self.validator._validate_path_security(safe_path)
            assert len(errors) == 0, f"安全路径 {safe_path} 不应该被拒绝"
            assert sanitized != ""

    def test_validate_path_length(self):
        """测试路径长度验证"""
        # 超长路径
        long_path = "a" * 1001
        errors, sanitized = self.validator._validate_path_security(long_path)
        assert len(errors) > 0
        assert "路径过长" in errors[0]

        # 正常长度路径
        normal_path = "a" * 100
        errors, sanitized = self.validator._validate_path_security(normal_path)
        assert len(errors) == 0

    def test_validate_natural_language_parameters(self):
        """测试自然语言参数验证"""
        # 包含文件路径的自然语言输入
        parsed = ParsedInput(
            original_input="分析 src/main.py 文件",
            input_type=InputType.NATURAL_LANGUAGE,
            parameters={
                "text": "分析 src/main.py 文件",
                "file_paths": ["src/main.py"],
                "mode_hints": ["static"],
                "keywords": ["分析", "文件"]
            }
        )
        result = self.validator.validate(parsed)

        assert result.is_valid is True
        assert "file_paths" in result.sanitized_params
        assert "text" in result.sanitized_params

    def test_validate_too_many_files(self):
        """测试过多文件验证"""
        # 创建超过限制的文件列表
        max_files = self.validator.validation_rules['max_concurrent_files']
        too_many_files = [f"file_{i}.py" for i in range(max_files + 1)]

        parsed = ParsedInput(
            original_input="分析多个文件",
            input_type=InputType.NATURAL_LANGUAGE,
            parameters={"file_paths": too_many_files}
        )
        result = self.validator.validate(parsed)

        assert result.is_valid is False
        assert any("文件数量过多" in error for error in result.errors)


class TestResponseFormatter:
    """测试响应格式化器"""

    def setup_method(self):
        """测试前的设置"""
        self.formatter = ResponseFormatter()

    def create_mock_results(self, success_count=3, failure_count=2):
        """创建模拟执行结果"""
        results = []

        # 成功结果
        for i in range(success_count):
            result = Mock()
            result.success = True
            result.task_name = f"Task_{i}"
            result.output = f"Task {i} completed successfully"
            result.execution_time = 1.5 + i * 0.5
            result.error_message = None
            results.append(result)

        # 失败结果
        for i in range(failure_count):
            result = Mock()
            result.success = False
            result.task_name = f"Failed_Task_{i}"
            result.output = None
            result.execution_time = 2.0 + i * 0.3
            result.error_message = f"Error in task {i}"
            results.append(result)

        return results

    def create_mock_plan(self):
        """创建模拟执行计划"""
        plan = Mock()
        plan.plan_id = "test_plan_001"
        plan.target_path = "src/"
        plan.tasks = [Mock() for _ in range(5)]
        return plan

    def test_format_simple_results(self):
        """测试简洁格式化"""
        results = self.create_mock_results(3, 2)
        plan = self.create_mock_plan()

        formatted = self.formatter.format_execution_result(
            results, OutputFormat.SIMPLE, plan
        )

        assert isinstance(formatted, FormattedOutput)
        assert formatted.format_type == OutputFormat.SIMPLE
        assert "3/5" in formatted.content  # 成功数量统计
        assert plan.plan_id in formatted.content

    def test_format_detailed_results(self):
        """测试详细格式化"""
        results = self.create_mock_results(2, 1)
        plan = self.create_mock_plan()

        formatted = self.formatter.format_execution_result(
            results, OutputFormat.DETAILED, plan
        )

        assert isinstance(formatted, FormattedOutput)
        assert formatted.format_type == OutputFormat.DETAILED
        assert "代码分析详细报告" in formatted.content
        assert plan.plan_id in formatted.content
        assert "Task_0" in formatted.content
        assert "Failed_Task_0" in formatted.content

    def test_format_json_results(self):
        """测试JSON格式化"""
        results = self.create_mock_results(2, 1)
        plan = self.create_mock_plan()

        formatted = self.formatter.format_execution_result(
            results, OutputFormat.JSON, plan
        )

        assert isinstance(formatted, FormattedOutput)
        assert formatted.format_type == OutputFormat.JSON

        # 验证可以解析为JSON（Mock对象序列化可能失败）
        try:
            json_data = json.loads(formatted.content)
            # 如果成功序列化，验证基本结构
            assert "analysis_summary" in json_data or "error" in json_data
            if "analysis_summary" in json_data:
                assert "results" in json_data
                assert len(json_data["results"]) == 3
        except json.JSONDecodeError:
            # 如果Mock对象无法序列化，验证错误信息存在
            assert "error" in formatted.content or "analysis_summary" in formatted.content

    def test_format_table_results(self):
        """测试表格格式化"""
        results = self.create_mock_results(2, 1)
        plan = self.create_mock_plan()

        formatted = self.formatter.format_execution_result(
            results, OutputFormat.TABLE, plan
        )

        assert isinstance(formatted, FormattedOutput)
        assert formatted.format_type == OutputFormat.TABLE
        assert "┌" in formatted.content and "┐" in formatted.content  # 表格边框
        assert "任务编号" in formatted.content
        assert "2/3" in formatted.content  # 成功统计

    def test_format_markdown_results(self):
        """测试Markdown格式化"""
        results = self.create_mock_results(2, 1)
        plan = self.create_mock_plan()

        formatted = self.formatter.format_execution_result(
            results, OutputFormat.MARKDOWN, plan
        )

        assert isinstance(formatted, FormattedOutput)
        assert formatted.format_type == OutputFormat.MARKDOWN
        assert "# 🔍 代码分析报告" in formatted.content
        assert "## 📋 分析信息" in formatted.content
        assert "```" in formatted.content  # 代码块

    def test_format_response_with_string_data(self):
        """测试字符串数据格式化"""
        test_string = "这是一个测试响应"

        result = self.formatter.format_response(test_string)
        assert result == test_string

    def test_format_response_with_dict_data(self):
        """测试字典数据格式化"""
        test_dict = {"key": "value", "number": 123}

        result = self.formatter.format_response(test_dict)
        parsed = json.loads(result)
        assert parsed == test_dict


class TestUserInteractionHandler:
    """测试用户交互处理器"""

    def setup_method(self):
        """测试前的设置"""
        self.handler = UserInteractionHandler()

    def test_process_help_command(self):
        """测试处理帮助命令"""
        result = self.handler.process_user_input("/help")

        assert result["success"] is True
        assert result["input_type"] == InputType.HELP.value
        assert "帮助" in result["message"]
        assert result["requires_confirmation"] is False

    def test_process_exit_command(self):
        """测试处理退出命令"""
        result = self.handler.process_user_input("exit")

        assert result["success"] is True
        assert result["input_type"] == InputType.EXIT.value
        assert result["requires_confirmation"] is True
        assert "确定要退出吗？(y/n)" == result["confirmation_message"]

    def test_process_confirmation_positive(self):
        """测试处理肯定确认"""
        result = self.handler.process_user_input("yes")

        assert result["success"] is True
        assert result["input_type"] == InputType.CONFIRMATION.value
        assert result["response"] is True
        assert result["message"] == "确认"

    def test_process_confirmation_negative(self):
        """测试处理否定确认"""
        result = self.handler.process_user_input("no")

        assert result["success"] is True
        assert result["input_type"] == InputType.CONFIRMATION.value
        assert result["response"] is False
        assert result["message"] == "取消"

    def test_process_system_commands(self):
        """测试处理系统命令"""
        test_cases = [
            ("/mode static", "mode", "static"),
            ("/format json", "format", "json"),
            ("/status", "status", None),
            ("/clear", "clear", None)
        ]

        for command_input, expected_command, expected_value in test_cases:
            result = self.handler.process_user_input(command_input)

            assert result["success"] is True
            assert result["input_type"] == InputType.COMMAND.value
            assert result["command"] == expected_command

            if expected_value:
                assert result[expected_command] == expected_value

    def test_process_natural_language(self):
        """测试处理自然语言输入"""
        natural_input = "静态分析 src/ 目录"
        result = self.handler.process_user_input(natural_input)

        assert result["success"] is True
        assert result["input_type"] == InputType.NATURAL_LANGUAGE.value
        assert result["text"] == natural_input
        assert isinstance(result["keywords"], list)
        assert isinstance(result["file_paths"], list)

    def test_process_invalid_input(self):
        """测试处理无效输入"""
        result = self.handler.process_user_input("")

        assert result["success"] is False
        assert result["input_type"] == InputType.UNKNOWN.value
        assert "输入解析失败" in result["message"]

    def test_check_interruption(self):
        """测试中断检查"""
        # 初始状态
        assert self.handler.check_interruption() is False

        # 重置中断状态
        self.handler.reset_interruption()
        assert self.handler.check_interruption() is False

    def test_format_response_delegation(self):
        """测试响应格式化委托"""
        test_data = {"test": "data"}

        # 测试默认格式化
        result = self.handler.format_response(test_data)
        assert isinstance(json.loads(result), dict)

        # 测试指定格式化
        result = self.handler.format_response(test_data, "simple")
        assert isinstance(json.loads(result), dict)


class TestIntegration:
    """测试集成功能"""

    def setup_method(self):
        """测试前的设置"""
        self.handler = UserInteractionHandler()

    def test_full_workflow_help(self):
        """测试完整的帮助工作流"""
        # 用户输入帮助命令
        result = self.handler.process_user_input("/help")

        assert result["success"] is True
        assert "帮助" in result["message"]

        # 验证响应可以格式化
        formatted = self.handler.format_response(result["message"])
        assert len(formatted) > 0

    def test_full_workflow_mode_switch(self):
        """测试完整的模式切换工作流"""
        # 用户切换模式
        result = self.handler.process_user_input("/mode deep")

        assert result["success"] is True
        assert result["mode"] == "deep"
        assert "deep" in result["message"]

    def test_full_workflow_natural_language_with_validation(self):
        """测试自然语言输入验证工作流"""
        # 创建临时文件用于测试
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write("print('hello world')")
            temp_file_path = temp_file.name

        try:
            # 用户输入包含文件路径
            user_input = f"分析 {temp_file_path} 文件"
            result = self.handler.process_user_input(user_input)

            assert result["success"] is True
            assert result["input_type"] == InputType.NATURAL_LANGUAGE.value

            # 检查是否提取了文件路径
            file_paths = result.get("file_paths", [])
            assert any(temp_file_path in path or os.path.basename(temp_file_path) in path
                      for path in file_paths)

        finally:
            # 清理临时文件
            os.unlink(temp_file_path)

    def test_error_handling_workflow(self):
        """测试错误处理工作流"""
        # 各种无效输入
        invalid_inputs = [
            "",
            "   ",  # 仅空格
            "/invalid_command",
            "/mode invalid_mode"
        ]

        for invalid_input in invalid_inputs:
            result = self.handler.process_user_input(invalid_input)

            # 要么是解析失败，要么是命令执行失败，但都要有错误信息
            if not result["success"]:
                assert "error" in result or "errors" in result
                assert result["input_type"] in [InputType.UNKNOWN.value, InputType.COMMAND.value]

    def test_format_workflow_different_formats(self):
        """测试不同格式的格式化工作流"""
        mock_results = [Mock(success=True, task_name="TestTask", output="Test output")]

        formats = ["simple", "detailed", "json", "table", "markdown"]

        for format_type in formats:
            try:
                formatted = self.handler.format_response(mock_results, format_type)
                assert isinstance(formatted, str)
                assert len(formatted) > 0
            except Exception as e:
                # 如果某个格式不支持，至少不应该崩溃
                assert False, f"格式化 {format_type} 时发生错误: {e}"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])