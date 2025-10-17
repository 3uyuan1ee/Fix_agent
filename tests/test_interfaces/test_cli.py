#!/usr/bin/env python3
"""
CLI模块单元测试
测试CLI参数解析器、帮助功能和主应用程序
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json
from io import StringIO

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.interfaces.cli import CLIArgumentParser, CLIArguments, CLIHelper
from src.interfaces.main import CLIMainApplication


class TestCLIArgumentParser(unittest.TestCase):
    """CLI参数解析器测试"""

    def setUp(self):
        """测试前准备"""
        self.parser = CLIArgumentParser()

    def test_parse_basic_args(self):
        """测试基本参数解析"""
        args = self.parser.parse_args(['--mode', 'static', '--target', 'src/'])

        self.assertEqual(args.mode, 'static')
        self.assertEqual(args.target, 'src/')
        self.assertFalse(args.verbose)
        self.assertFalse(args.quiet)

    def test_parse_verbose_args(self):
        """测试详细模式参数"""
        args = self.parser.parse_args(['--verbose', '--mode', 'deep'], validate_paths=False)

        self.assertTrue(args.verbose)
        self.assertEqual(args.mode, 'deep')

    def test_parse_quiet_args(self):
        """测试静默模式参数"""
        args = self.parser.parse_args(['--quiet', '--mode', 'static'], validate_paths=False)

        self.assertTrue(args.quiet)
        self.assertFalse(args.verbose)

    def test_parse_with_output_format(self):
        """测试输出格式参数"""
        args = self.parser.parse_args(['--format', 'json', '--output', 'result.json'])

        self.assertEqual(args.format, 'json')
        self.assertEqual(args.output, 'result.json')

    def test_parse_batch_mode(self):
        """测试批处理模式"""
        args = self.parser.parse_args(['--batch', 'commands.txt'], validate_paths=False)

        self.assertEqual(args.batch_file, 'commands.txt')
        self.assertFalse(args.interactive)

    def test_parse_static_tools(self):
        """测试静态工具指定"""
        args = self.parser.parse_args(['--static-tools', 'pylint', 'bandit', 'mypy'])

        self.assertEqual(args.static_tools, ['pylint', 'bandit', 'mypy'])

    def test_parse_fix_mode_options(self):
        """测试修复模式选项"""
        args = self.parser.parse_args(['--mode', 'fix', '--no-confirm'], validate_paths=False)

        self.assertEqual(args.mode, 'fix')
        self.assertFalse(args.fix_confirm)

    
    def test_mutually_exclusive_args_validation(self):
        """测试互斥参数验证"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--verbose', '--quiet'])

    def test_target_required_with_mode(self):
        """测试模式需要目标参数"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--mode', 'static'])

    def test_export_requires_output(self):
        """测试导出需要输出参数"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--export', 'pdf'])

    def test_dry_run_parsing(self):
        """测试模拟运行参数"""
        args = self.parser.parse_args(['--dry-run', '--mode', 'static', '--target', 'src/'])

        self.assertTrue(args.dry_run)

    def test_config_file_parsing(self):
        """测试配置文件参数"""
        args = self.parser.parse_args(['--config', 'custom.yaml'])

        self.assertEqual(args.config, 'custom.yaml')

    def test_cache_control_parsing(self):
        """测试缓存控制参数"""
        args = self.parser.parse_args(['--no-cache'])

        self.assertFalse(args.enable_cache)

    def test_logging_control_parsing(self):
        """测试日志控制参数"""
        args = self.parser.parse_args(['--no-logging'])

        self.assertFalse(args.enable_logging)


class TestCLIHelper(unittest.TestCase):
    """CLI帮助工具测试"""

    def test_suggest_command(self):
        """测试命令建议"""
        available_commands = ['analyze', 'help', 'exit', 'status']

        # 测试完全匹配
        suggestions = CLIHelper.suggest_command('analyze', available_commands)
        self.assertIn('analyze', suggestions)

        # 测试模糊匹配
        suggestions = CLIHelper.suggest_command('anlz', available_commands)
        self.assertIn('analyze', suggestions)

        # 测试无匹配
        suggestions = CLIHelper.suggest_command('unknown', available_commands)
        self.assertEqual(len(suggestions), 0)

    def test_validate_path(self):
        """测试路径验证"""
        # 测试存在的路径
        valid_path = __file__  # 当前测试文件
        self.assertTrue(CLIHelper.validate_path(valid_path))

        # 测试不存在的路径
        invalid_path = '/nonexistent/path/file.py'
        self.assertFalse(CLIHelper.validate_path(invalid_path))

    def test_format_error_message(self):
        """测试错误消息格式化"""
        message = CLIHelper.format_error_message("参数错误", "无效的目标路径")
        expected = "❌ 参数错误: 无效的目标路径"
        self.assertEqual(message, expected)


class TestCLIMainApplication(unittest.TestCase):
    """CLI主应用程序测试"""

    def setUp(self):
        """测试前准备"""
        self.app = CLIMainApplication()

    def test_initialization(self):
        """测试应用初始化"""
        self.assertIsNotNone(self.app.parser)
        self.assertIsNone(self.app.config)
        self.assertIsNone(self.app.orchestrator)
        self.assertIsNone(self.app.args)

    @patch('src.interfaces.main.AgentOrchestrator')
    @patch('src.interfaces.main.ConfigManager')
    def test_run_version_command(self, mock_config, mock_orchestrator):
        """测试版本命令"""
        exit_code = self.app.run(['--version'])
        self.assertEqual(exit_code, 0)

    @patch('src.interfaces.main.AgentOrchestrator')
    @patch('src.interfaces.main.ConfigManager')
    def test_run_list_tools_command(self, mock_config, mock_orchestrator):
        """测试列出工具命令"""
        exit_code = self.app.run(['--list-tools'])
        self.assertEqual(exit_code, 0)

    @patch('src.interfaces.main.AgentOrchestrator')
    @patch('src.interfaces.main.ConfigManager')
    def test_run_help_topics(self, mock_config, mock_orchestrator):
        """测试帮助主题"""
        exit_code = self.app.run(['modes'])
        self.assertEqual(exit_code, 0)

    def test_handle_special_commands_version(self):
        """测试特殊命令处理 - 版本"""
        self.app.args = CLIArguments(version=True)
        result = self.app._handle_special_commands()
        self.assertTrue(result)

    def test_handle_special_commands_list_tools(self):
        """测试特殊命令处理 - 列出工具"""
        self.app.args = CLIArguments(list_tools=True)
        result = self.app._handle_special_commands()
        self.assertTrue(result)

    def test_handle_special_commands_help_topic(self):
        """测试特殊命令处理 - 帮助主题"""
        # 这个测试需要mock特殊命令处理
        with patch.object(self.app.parser, 'print_help') as mock_help:
            self.app.args = CLIArguments()
            with patch.object(self.app, 'args') as mock_args:
                mock_args.unknown_args = ['modes']
                result = self.app._handle_special_commands()
                self.assertTrue(result)

    def test_handle_special_commands_none(self):
        """测试特殊命令处理 - 无特殊命令"""
        self.app.args = CLIArguments(mode='static', target='src/')
        result = self.app._handle_special_commands()
        self.assertFalse(result)

    @patch('src.interfaces.main.ConfigManager')
    def test_load_configuration_success(self, mock_config):
        """测试配置加载成功"""
        mock_config.return_value = Mock()
        self.app.args = CLIArguments()

        self.app._load_configuration()
        self.assertIsNotNone(self.app.config)

    @patch('src.interfaces.main.ConfigManager')
    def test_load_configuration_failure(self, mock_config):
        """测试配置加载失败"""
        mock_config.side_effect = Exception("配置文件不存在")
        self.app.args = CLIArguments()

        with self.assertRaises(Exception):
            self.app._load_configuration()

    @patch('src.interfaces.main.setup_logging')
    def test_setup_logging_verbose(self, mock_setup):
        """测试详细模式日志设置"""
        self.app.args = CLIArguments(verbose=True, enable_logging=True, quiet=False)
        self.app._setup_logging()
        mock_setup.assert_called_with(level="DEBUG")

    @patch('src.interfaces.main.setup_logging')
    def test_setup_logging_quiet(self, mock_setup):
        """测试静默模式日志设置"""
        self.app.args = CLIArguments(quiet=True)
        self.app._setup_logging()
        mock_setup.assert_called_with(level="ERROR")

    @patch('src.interfaces.main.setup_logging')
    def test_setup_logging_disabled(self, mock_setup):
        """测试禁用日志"""
        self.app.args = CLIArguments(enable_logging=False)
        self.app._setup_logging()
        mock_setup.assert_called_with(level="ERROR")

    @patch('src.interfaces.main.AgentOrchestrator')
    def test_initialize_orchestrator_success(self, mock_orchestrator_class):
        """测试编排器初始化成功"""
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        self.app.config = Mock()
        self.app.args = CLIArguments()

        self.app._initialize_orchestrator()
        self.assertIsNotNone(self.app.orchestrator)

    def test_apply_cli_overrides_mode(self):
        """测试CLI参数覆盖 - 模式"""
        mock_orchestrator = Mock()
        mock_config = Mock()

        self.app.orchestrator = mock_orchestrator
        self.app.config = mock_config
        self.app.args = CLIArguments(mode='static')

        self.app._apply_cli_overrides()
        # 验证没有抛出异常

    def test_apply_cli_overrides_tools(self):
        """测试CLI参数覆盖 - 工具"""
        mock_orchestrator = Mock()
        mock_config = Mock()
        mock_config.get_tools_config.return_value = {}

        self.app.orchestrator = mock_orchestrator
        self.app.config = mock_config
        self.app.args = CLIArguments(static_tools=['pylint', 'bandit'])

        self.app._apply_cli_overrides()
        # 验证没有抛出异常

    def test_apply_cli_overrides_llm(self):
        """测试CLI参数覆盖 - LLM模型"""
        mock_orchestrator = Mock()
        mock_config = Mock()
        mock_config.get_tools_config.return_value = {}

        self.app.orchestrator = mock_orchestrator
        self.app.config = mock_config
        self.app.args = CLIArguments(deep_model='gpt-4')

        self.app._apply_cli_overrides()
        # 验证没有抛出异常

    def test_apply_cli_overrides_cache(self):
        """测试CLI参数覆盖 - 缓存"""
        mock_orchestrator = Mock()
        mock_config = Mock()

        self.app.orchestrator = mock_orchestrator
        self.app.config = mock_config
        self.app.args = CLIArguments(enable_cache=False)

        self.app._apply_cli_overrides()
        # 验证没有抛出异常

    def test_determine_execution_mode_batch(self):
        """测试执行模式确定 - 批处理"""
        self.app.args = CLIArguments(batch_file='commands.txt')
        exit_code = self.app._execute_main_functionality()
        # 由于批处理文件不存在，应该返回错误码
        self.assertEqual(exit_code, 1)

    def test_determine_execution_mode_non_interactive(self):
        """测试执行模式确定 - 非交互式"""
        self.app.args = CLIArguments(interactive=False, target='src/', mode='static')
        # 由于编排器未初始化，应该返回错误码
        exit_code = self.app._execute_main_functionality()
        self.assertEqual(exit_code, 1)

    def test_determine_execution_mode_interactive(self):
        """测试执行模式确定 - 交互式"""
        self.app.args = CLIArguments()  # 默认交互模式
        # 由于编排器未初始化，应该返回错误码
        exit_code = self.app._execute_main_functionality()
        self.assertEqual(exit_code, 1)


class TestCLIIntegration(unittest.TestCase):
    """CLI集成测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')

        # 创建测试配置文件
        with open(self.config_file, 'w') as f:
            f.write("""
test:
  enabled: true
  tools:
    - pylint
    - bandit
            """)

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_argument_parsing_workflow(self):
        """测试完整的参数解析工作流"""
        parser = CLIArgumentParser()

        # 测试复杂的参数组合
        args = parser.parse_args([
            '--mode', 'static',
            '--target', 'src/',
            '--verbose',
            '--format', 'json',
            '--output', 'result.json',
            '--static-tools', 'pylint', 'bandit',
            '--config', self.config_file
        ])

        self.assertIsInstance(args, CLIArguments)
        self.assertEqual(args.mode, 'static')
        self.assertEqual(args.target, 'src/')
        self.assertTrue(args.verbose)
        self.assertEqual(args.format, 'json')
        self.assertEqual(args.output, 'result.json')
        self.assertEqual(args.static_tools, ['pylint', 'bandit'])
        self.assertEqual(args.config, self.config_file)

    def test_error_handling_invalid_target(self):
        """测试错误处理 - 无效目标"""
        parser = CLIArgumentParser()

        with self.assertRaises(SystemExit):
            parser.parse_args(['--mode', 'static', '--target', '/nonexistent/'])

    def test_error_handling_invalid_batch_file(self):
        """测试错误处理 - 无效批处理文件"""
        parser = CLIArgumentParser()

        with self.assertRaises(SystemExit):
            parser.parse_args(['--batch', '/nonexistent/batch.txt'])

    def test_help_functionality(self):
        """测试帮助功能"""
        parser = CLIArgumentParser()

        # 测试主帮助不会抛出异常
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            try:
                parser.print_help()
            except SystemExit:
                pass

        # 测试主题帮助不会抛出异常
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            try:
                parser.print_help('modes')
            except SystemExit:
                pass

    def test_version_functionality(self):
        """测试版本功能"""
        parser = CLIArgumentParser()

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            try:
                parser.print_version()
            except SystemExit:
                pass

        output = mock_stdout.getvalue()
        self.assertIn('AI缺陷检测系统', output)
        self.assertIn('v', output)


class TestCLIErrorHandling(unittest.TestCase):
    """CLI错误处理测试"""

    def setUp(self):
        """测试前准备"""
        self.parser = CLIArgumentParser()

    def test_invalid_mode_argument(self):
        """测试无效模式参数"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--mode', 'invalid', '--target', 'src/'])

    def test_invalid_format_argument(self):
        """测试无效格式参数"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--format', 'invalid'])

    def test_invalid_export_argument(self):
        """测试无效导出参数"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--export', 'invalid'])

    def test_conflicting_verbose_quiet(self):
        """测试冲突的详细和静默参数"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--verbose', '--quiet'])

    def test_missing_target_with_mode(self):
        """测试缺少目标参数"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--mode', 'static'])

    def test_missing_output_with_export(self):
        """测试缺少输出参数"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(['--export', 'pdf'])


if __name__ == '__main__':
    unittest.main()