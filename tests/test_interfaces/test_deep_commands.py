#!/usr/bin/env python3
"""
深度分析命令模块单元测试
测试`analyze deep`命令的功能
"""

import unittest
import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.interfaces.deep_commands import (
    DeepAnalysisCommand, ConversationManager, ProgressIndicator,
    ConversationMessage, DeepAnalysisResult
)
from src.interfaces.cli import CLIArgumentParser, CLIArguments
from src.interfaces.main import CLIMainApplication


class TestConversationMessage(unittest.TestCase):
    """对话消息测试"""

    def test_conversation_message_creation(self):
        """测试对话消息创建"""
        msg = ConversationMessage(
            role="user",
            content="测试消息"
        )

        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "测试消息")
        self.assertIsInstance(msg.timestamp, datetime)
        self.assertEqual(msg.metadata, {})

    def test_conversation_message_with_metadata(self):
        """测试带元数据的对话消息创建"""
        metadata = {"file": "test.py", "line": 10}
        msg = ConversationMessage(
            role="assistant",
            content="分析结果",
            metadata=metadata
        )

        self.assertEqual(msg.role, "assistant")
        self.assertEqual(msg.content, "分析结果")
        self.assertEqual(msg.metadata, metadata)


class TestConversationManager(unittest.TestCase):
    """对话管理器测试"""

    def setUp(self):
        """测试前准备"""
        self.target = "/test/path"
        self.manager = ConversationManager(self.target)

    def test_conversation_manager_initialization(self):
        """测试对话管理器初始化"""
        self.assertEqual(self.manager.target, self.target)
        self.assertEqual(len(self.manager.conversation), 0)
        self.assertIsNone(self.manager.session)
        self.assertIsInstance(self.manager.start_time, float)

    def test_add_message(self):
        """测试添加消息"""
        self.manager.add_message("user", "用户输入")

        self.assertEqual(len(self.manager.conversation), 1)
        msg = self.manager.conversation[0]
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "用户输入")

    def test_get_conversation_history(self):
        """测试获取对话历史"""
        self.manager.add_message("user", "用户输入")
        self.manager.add_message("assistant", "AI回复")

        history = self.manager.get_conversation_history()

        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["role"], "assistant")
        self.assertIn("timestamp", history[0])
        self.assertIn("metadata", history[0])

    def test_export_conversation(self):
        """测试导出对话"""
        self.manager.add_message("user", "用户输入")
        self.manager.add_message("assistant", "AI回复")

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_file = f.name

        try:
            success = self.manager.export_conversation(temp_file)
            self.assertTrue(success)

            # 验证导出文件内容
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.assertEqual(data["target"], self.target)
            self.assertEqual(data["message_count"], 2)
            self.assertEqual(len(data["conversation"]), 2)
            self.assertIn("start_time", data)
            self.assertIn("export_time", data)

        finally:
            os.unlink(temp_file)

    def test_export_conversation_failure(self):
        """测试导出对话失败"""
        # 尝试导出到无效路径
        invalid_path = "/invalid/path/file.json"
        success = self.manager.export_conversation(invalid_path)
        self.assertFalse(success)


class TestProgressIndicator(unittest.TestCase):
    """进度指示器测试"""

    def test_progress_indicator_initialization(self):
        """测试进度指示器初始化"""
        indicator = ProgressIndicator()
        self.assertFalse(indicator.is_running)
        self.assertIsNone(indicator._thread)

    def test_start_stop_progress(self):
        """测试开始和停止进度"""
        indicator = ProgressIndicator()

        indicator.start("测试消息")
        self.assertTrue(indicator.is_running)

        indicator.stop()
        self.assertFalse(indicator.is_running)

    def test_multiple_start_calls(self):
        """测试多次开始调用"""
        indicator = ProgressIndicator()

        indicator.start("测试消息")
        indicator.start("另一个消息")  # 应该被忽略

        self.assertTrue(indicator.is_running)

        indicator.stop()
        self.assertFalse(indicator.is_running)


class TestDeepAnalysisCommand(unittest.TestCase):
    """深度分析命令测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        # 创建测试Python文件
        self.test_file = self.temp_dir_path / "test.py"
        self.test_file.write_text("""
def test_function():
    x = 1
    y = 2
    return x + y

class TestClass:
    def method(self):
        pass
        """)

        # 创建深度分析命令处理器
        self.deep_cmd = DeepAnalysisCommand()

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_deep_analysis_command_initialization(self):
        """测试深度分析命令初始化"""
        cmd = DeepAnalysisCommand()
        self.assertIsNotNone(cmd.config)
        self.assertIsNotNone(cmd.orchestrator)
        self.assertIsNotNone(cmd.progress)

    def test_validate_target_file(self):
        """测试验证目标文件"""
        # 测试Python文件
        self.assertTrue(self.deep_cmd._validate_target(self.test_file))

        # 测试非Python文件
        non_py_file = self.temp_dir_path / "test.txt"
        non_py_file.write_text("text content")
        self.assertFalse(self.deep_cmd._validate_target(non_py_file))

    def test_validate_target_directory(self):
        """测试验证目标目录"""
        # 包含Python文件的目录
        self.assertTrue(self.deep_cmd._validate_target(self.temp_dir_path))

        # 空目录
        empty_dir = self.temp_dir_path / "empty"
        empty_dir.mkdir()
        self.assertFalse(self.deep_cmd._validate_target(empty_dir))

    def test_validate_target_nonexistent(self):
        """测试验证不存在的目标"""
        nonexistent_path = Path("/nonexistent/path")
        self.assertFalse(self.deep_cmd._validate_target(nonexistent_path))

    @patch('src.interfaces.deep_commands.AgentOrchestrator')
    def test_execute_deep_analysis_file_not_found(self, mock_orchestrator_class):
        """测试执行深度分析 - 文件不存在"""
        cmd = DeepAnalysisCommand()

        with self.assertRaises(FileNotFoundError):
            cmd.execute_deep_analysis(
                target="/nonexistent/file.py",
                quiet=True
            )

    @patch('src.interfaces.deep_commands.AgentOrchestrator')
    def test_execute_deep_analysis_invalid_target(self, mock_orchestrator_class):
        """测试执行深度分析 - 无效目标"""
        cmd = DeepAnalysisCommand()

        # 创建非Python文件
        non_py_file = self.temp_dir_path / "test.txt"
        non_py_file.write_text("text content")

        result = cmd.execute_deep_analysis(
            target=str(non_py_file),
            quiet=True
        )

        self.assertFalse(result.success)
        self.assertIn("不是有效的Python文件", result.analysis_summary)

    @patch('src.interfaces.deep_commands.AgentOrchestrator')
    def test_execute_deep_analysis_success(self, mock_orchestrator_class):
        """测试执行深度分析 - 成功情况"""
        # 模拟编排器
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # 模拟会话
        mock_session = Mock()
        mock_orchestrator.create_session.return_value = mock_session

        # 模拟分析结果
        mock_orchestrator.process_user_input.return_value = {
            "success": True,
            "message": "分析完成，未发现明显问题"
        }

        cmd = DeepAnalysisCommand()

        # 模拟用户输入退出
        with patch('builtins.input', side_effect=['/exit']):
            result = cmd.execute_deep_analysis(
                target=str(self.test_file),
                quiet=True
            )

        self.assertTrue(result.success)
        self.assertEqual(result.target, str(self.test_file))
        self.assertIsInstance(result.conversation, list)
        self.assertGreater(result.execution_time, 0)

    @patch('src.interfaces.deep_commands.AgentOrchestrator')
    def test_generate_summary(self, mock_orchestrator_class):
        """测试生成分析摘要"""
        manager = ConversationManager("/test/path")

        # 添加对话消息
        manager.add_message("user", "请分析代码")
        manager.add_message("assistant", "分析发现了3个问题和2个建议")

        summary = self.deep_cmd._generate_summary(manager)

        self.assertIn("对话轮次", summary)
        self.assertIn("1", summary)  # 对话轮次应该是1（AI回复数量）

    def test_show_help(self):
        """测试显示帮助"""
        with patch('builtins.print') as mock_print:
            self.deep_cmd._show_help(quiet=False)

            # 验证print被调用
            self.assertTrue(mock_print.called)
            # 检查帮助内容
            printed_args = [call.args[0] for call in mock_print.call_args_list]
            help_text = ''.join(printed_args)
            self.assertIn("深度分析模式帮助", help_text)
            self.assertIn("/help", help_text)
            self.assertIn("/exit", help_text)

    def test_show_history(self):
        """测试显示对话历史"""
        manager = ConversationManager("/test/path")
        manager.add_message("user", "用户输入")
        manager.add_message("assistant", "AI回复")

        with patch('builtins.print') as mock_print:
            self.deep_cmd._show_history(manager, quiet=False)

            # 验证print被调用
            self.assertTrue(mock_print.called)
            # 检查历史内容
            printed_args = [call.args[0] for call in mock_print.call_args_list]
            history_text = ''.join(printed_args)
            self.assertIn("对话历史", history_text)
            self.assertIn("用户输入", history_text)
            self.assertIn("AI回复", history_text)

    def test_handle_special_command_exit(self):
        """测试处理特殊命令 - 退出"""
        manager = ConversationManager("/test/path")

        result = self.deep_cmd._handle_special_command("/exit", manager, quiet=False)
        self.assertTrue(result)

    def test_handle_special_command_help(self):
        """测试处理特殊命令 - 帮助"""
        manager = ConversationManager("/test/path")

        with patch('builtins.print'):
            result = self.deep_cmd._handle_special_command("/help", manager, quiet=False)

        self.assertFalse(result)  # 帮助命令不会导致退出

    def test_handle_special_command_unknown(self):
        """测试处理特殊命令 - 未知命令"""
        manager = ConversationManager("/test/path")

        with patch('builtins.print'):
            result = self.deep_cmd._handle_special_command("/unknown", manager, quiet=False)

        self.assertFalse(result)  # 未知命令不会导致退出


class TestCLIDeepCommand(unittest.TestCase):
    """CLI深度分析命令测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        # 创建测试Python文件
        self.test_file = self.temp_dir_path / "test.py"
        self.test_file.write_text("def test(): pass")

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_parse_analyze_deep_command(self):
        """测试解析analyze deep命令"""
        parser = CLIArgumentParser()

        args = parser.parse_args(['analyze', 'deep', str(self.test_file)], validate_paths=False)

        self.assertEqual(args.command, 'analyze')
        self.assertEqual(args.analyze_command, 'deep')
        self.assertEqual(args.sub_target, str(self.test_file))

    def test_parse_analyze_deep_with_options(self):
        """测试解析analyze deep命令带选项"""
        parser = CLIArgumentParser()

        args = parser.parse_args([
            'analyze', 'deep', str(self.test_file),
            '--output', 'conversation.json',
            '--verbose'
        ], validate_paths=False)

        self.assertEqual(args.command, 'analyze')
        self.assertEqual(args.analyze_command, 'deep')
        self.assertEqual(args.sub_target, str(self.test_file))
        self.assertEqual(args.sub_output, 'conversation.json')
        self.assertTrue(args.sub_verbose)

    @patch('src.interfaces.main.DeepAnalysisCommand')
    def test_handle_deep_analysis_command(self, mock_deep_cmd_class):
        """测试处理深度分析命令"""
        # 模拟深度分析命令
        mock_deep_cmd = Mock()
        mock_deep_cmd_class.return_value = mock_deep_cmd

        # 模拟分析结果
        mock_result = Mock()
        mock_result.success = True
        mock_deep_cmd.execute_deep_analysis.return_value = mock_result

        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='deep',
            sub_target=str(self.test_file),
            sub_output=None,
            sub_verbose=False,
            sub_quiet=False
        )

        exit_code = app._handle_deep_analysis_command()

        self.assertEqual(exit_code, 0)
        mock_deep_cmd.execute_deep_analysis.assert_called_once()

    def test_handle_deep_analysis_missing_target(self):
        """测试处理深度分析命令 - 缺少目标"""
        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='deep',
            sub_target=None
        )

        with patch('builtins.print') as mock_print:
            exit_code = app._handle_deep_analysis_command()
            self.assertEqual(exit_code, 1)
            mock_print.assert_called_with("❌ 深度分析需要指定目标路径")

    @patch('src.interfaces.main.DeepAnalysisCommand')
    def test_handle_deep_analysis_failure(self, mock_deep_cmd_class):
        """测试处理深度分析命令 - 执行失败"""
        # 模拟深度分析命令
        mock_deep_cmd = Mock()
        mock_deep_cmd_class.return_value = mock_deep_cmd

        # 模拟分析失败
        mock_deep_cmd.execute_deep_analysis.side_effect = Exception("分析失败")

        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='deep',
            sub_target=str(self.test_file),
            sub_verbose=False
        )

        with patch('builtins.print'):
            exit_code = app._handle_deep_analysis_command()
            self.assertEqual(exit_code, 1)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        # 创建测试项目
        (self.temp_dir_path / "main.py").write_text("""
def main():
    print("Hello, World!")
    x = 1
    return x

if __name__ == "__main__":
    main()
        """)

        (self.temp_dir_path / "utils.py").write_text("""
def helper():
    pass

class UtilClass:
    def method(self):
        return True
        """)

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.interfaces.main.DeepAnalysisCommand')
    def test_full_analyze_deep_workflow(self, mock_deep_cmd_class):
        """测试完整的analyze deep工作流"""
        # 模拟深度分析命令
        mock_deep_cmd = Mock()
        mock_deep_cmd_class.return_value = mock_deep_cmd

        # 模拟分析结果
        mock_result = DeepAnalysisResult(
            success=True,
            target=str(self.temp_dir_path),
            conversation=[],
            analysis_summary="深度分析完成",
            execution_time=1.5
        )
        mock_deep_cmd.execute_deep_analysis.return_value = mock_result

        app = CLIMainApplication()

        # 测试完整命令行解析和执行
        exit_code = app.run([
            'analyze', 'deep', str(self.temp_dir_path),
            '--verbose'
        ])

        self.assertEqual(exit_code, 0)
        mock_deep_cmd.execute_deep_analysis.assert_called_once()

    def test_cli_help_for_analyze_command(self):
        """测试analyze命令帮助信息"""
        parser = CLIArgumentParser()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            try:
                parser.parser.parse_args(['analyze', '--help'])
            except SystemExit:
                pass

            help_text = mock_stdout.getvalue()
            self.assertIn('analyze', help_text)
            self.assertIn('deep', help_text)


if __name__ == '__main__':
    unittest.main()