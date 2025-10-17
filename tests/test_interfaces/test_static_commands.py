#!/usr/bin/env python3
"""
静态分析命令模块单元测试
测试`analyze static`命令的功能
"""

import unittest
import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.interfaces.static_commands import (
    StaticAnalysisCommand, StaticAnalysisResult, ProgressTracker
)
from src.interfaces.cli import CLIArgumentParser, CLIArguments
from src.interfaces.main import CLIMainApplication


class TestProgressTracker(unittest.TestCase):
    """进度跟踪器测试"""

    def test_progress_tracker_initialization(self):
        """测试进度跟踪器初始化"""
        tracker = ProgressTracker(10)
        self.assertEqual(tracker.total_files, 10)
        self.assertEqual(tracker.processed_files, 0)
        self.assertEqual(tracker.current_tool, "")
        self.assertIsNotNone(tracker.start_time)

    def test_progress_update(self):
        """测试进度更新"""
        tracker = ProgressTracker(5)

        # 更新文件处理数量
        tracker.update(processed_files=2)
        self.assertEqual(tracker.processed_files, 2)

        # 更新当前工具
        tracker.update(current_tool="pylint")
        self.assertEqual(tracker.current_tool, "pylint")

        # 同时更新
        tracker.update(processed_files=1, current_tool="bandit")
        self.assertEqual(tracker.processed_files, 3)
        self.assertEqual(tracker.current_tool, "bandit")

    def test_progress_info(self):
        """测试进度信息获取"""
        tracker = ProgressTracker(4)

        # 初始状态
        info = tracker.get_progress_info()
        self.assertEqual(info["processed_files"], 0)
        self.assertEqual(info["total_files"], 4)
        self.assertEqual(info["percentage"], 0)

        # 处理一些文件后
        tracker.update(2, "test_tool")
        info = tracker.get_progress_info()
        self.assertEqual(info["processed_files"], 2)
        self.assertEqual(info["total_files"], 4)
        self.assertEqual(info["percentage"], 50)
        self.assertEqual(info["current_tool"], "test_tool")
        self.assertGreater(info["elapsed_time"], 0)


class TestStaticAnalysisCommand(unittest.TestCase):
    """静态分析命令测试"""

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

        # 创建静态分析命令处理器
        self.static_cmd = StaticAnalysisCommand()

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_static_analysis_command_initialization(self):
        """测试静态分析命令初始化"""
        cmd = StaticAnalysisCommand()
        self.assertIsNotNone(cmd.config)
        self.assertIsNotNone(cmd.orchestrator)
        self.assertIsNotNone(cmd.formatter)

    def test_get_files_to_analyze_file(self):
        """测试获取要分析的文件 - 单个文件"""
        files = self.static_cmd._get_files_to_analyze(self.test_file)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], str(self.test_file))

    def test_get_files_to_analyze_directory(self):
        """测试获取要分析的文件 - 目录"""
        # 创建更多测试文件
        (self.temp_dir_path / "test2.py").write_text("print('hello')")
        (self.temp_dir_path / "test3.py").write_text("def func(): pass")

        files = self.static_cmd._get_files_to_analyze(self.temp_dir_path)
        self.assertEqual(len(files), 3)
        self.assertTrue(all(f.endswith('.py') for f in files))

    def test_should_skip_file(self):
        """测试文件跳过逻辑"""
        # 测试隐藏文件
        hidden_file = Path(self.temp_dir_path / ".hidden.py")
        self.assertTrue(self.static_cmd._should_skip_file(hidden_file))

        # 测试缓存目录
        cache_file = Path(self.temp_dir_path / "__pycache__" / "test.pyc")
        self.assertTrue(self.static_cmd._should_skip_file(cache_file))

        # 测试正常文件
        normal_file = Path(self.temp_dir_path / "normal.py")
        self.assertFalse(self.static_cmd._should_skip_file(normal_file))

    @patch('src.interfaces.static_commands.ConfigManager')
    def test_get_selected_tools(self, mock_config_manager):
        """测试获取选中的工具"""
        # 模拟配置
        mock_config = Mock()
        mock_config.get_section.return_value = {
            'tools': {
                'pylint': {'enabled': True},
                'bandit': {'enabled': True},
                'flake8': {'enabled': False},
                'mypy': {'enabled': True}
            }
        }
        mock_config_manager.return_value = mock_config

        cmd = StaticAnalysisCommand(mock_config)

        # 不指定工具，返回启用的工具
        tools = cmd._get_selected_tools(None)
        self.assertEqual(set(tools), {'bandit', 'pylint', 'mypy'})

        # 指定工具，过滤可用工具
        tools = cmd._get_selected_tools(['pylint', 'flake8', 'unknown_tool'])
        self.assertEqual(tools, ['pylint'])  # 只有pylint启用

    @patch('src.interfaces.static_commands.AgentOrchestrator')
    def test_run_tool_analysis(self, mock_orchestrator_class):
        """测试工具分析执行"""
        # 模拟编排器
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # 模拟会话
        mock_session = Mock()
        mock_orchestrator.create_session.return_value = mock_session

        # 模拟结果
        mock_orchestrator.process_user_input.return_value = {
            "success": True,
            "message": "分析完成",
            "issues": [
                {"severity": "warning", "type": "style", "message": "Line too long"}
            ]
        }

        cmd = StaticAnalysisCommand()
        result = cmd._run_tool_analysis(
            "pylint",
            [str(self.test_file)],
            ProgressTracker(1),
            False
        )

        self.assertTrue(result["success"])
        self.assertEqual(len(result["issues"]), 1)
        mock_orchestrator.create_session.assert_called_once()
        mock_orchestrator.close_session.assert_called_once()

    @patch('src.interfaces.static_commands.AgentOrchestrator')
    def test_execute_static_analysis_success(self, mock_orchestrator_class):
        """测试静态分析执行 - 成功情况"""
        # 模拟编排器
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # 模拟会话
        mock_session = Mock()
        mock_orchestrator.create_session.return_value = mock_session

        # 模拟分析结果
        mock_orchestrator.process_user_input.return_value = {
            "success": True,
            "message": "分析完成",
            "issues": [
                {"severity": "error", "type": "syntax"},
                {"severity": "warning", "type": "style"}
            ]
        }

        cmd = StaticAnalysisCommand()
        result = cmd.execute_static_analysis(
            target=str(self.test_file),
            tools=['pylint'],
            output_format="simple",
            verbose=False,
            quiet=True,
            dry_run=False
        )

        self.assertTrue(result.success)
        self.assertEqual(result.total_files, 1)
        self.assertEqual(result.analyzed_files, 1)
        self.assertEqual(result.total_issues, 2)

    def test_execute_static_analysis_dry_run(self):
        """测试静态分析执行 - 模拟运行"""
        cmd = StaticAnalysisCommand()
        result = cmd.execute_static_analysis(
            target=str(self.test_file),
            tools=['pylint'],
            output_format="simple",
            verbose=False,
            quiet=True,
            dry_run=True
        )

        self.assertTrue(result.success)
        self.assertEqual(result.total_files, 1)
        self.assertEqual(result.analyzed_files, 1)
        self.assertEqual(result.total_issues, 0)
        self.assertEqual(result.summary, "模拟运行完成")

    def test_execute_static_analysis_file_not_found(self):
        """测试静态分析执行 - 文件不存在"""
        cmd = StaticAnalysisCommand()

        with self.assertRaises(FileNotFoundError):
            cmd.execute_static_analysis(
                target="/nonexistent/file.py",
                tools=['pylint'],
                output_format="simple",
                verbose=False,
                quiet=True,
                dry_run=False
            )

    def test_process_analysis_results(self):
        """测试分析结果处理"""
        # 模拟分析结果
        analysis_results = {
            'pylint': {
                'success': True,
                'issues': [
                    {'severity': 'error', 'type': 'syntax'},
                    {'severity': 'warning', 'type': 'style'}
                ]
            },
            'bandit': {
                'success': True,
                'issues': [
                    {'severity': 'warning', 'type': 'security'}
                ]
            }
        }

        result = self.static_cmd._process_analysis_results(
            analysis_results,
            ['pylint', 'bandit'],
            2,
            1.5
        )

        self.assertTrue(result.success)
        self.assertEqual(result.total_files, 2)
        self.assertEqual(result.analyzed_files, 2)
        self.assertEqual(result.total_issues, 3)
        self.assertEqual(result.issues_by_severity['error'], 1)
        self.assertEqual(result.issues_by_severity['warning'], 2)
        self.assertEqual(result.execution_time, 1.5)

    @patch('builtins.open', create=True)
    def test_save_results_json(self, mock_open):
        """测试保存结果 - JSON格式"""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = StaticAnalysisResult(
            success=True,
            total_files=1,
            analyzed_files=1,
            total_issues=2,
            issues_by_severity={'error': 1, 'warning': 1},
            issues_by_type={'syntax': 1, 'style': 1},
            tool_results={},
            execution_time=1.0,
            summary="发现2个问题"
        )

        self.static_cmd._save_results(result, "output.json", "json")

        # 验证文件写入被调用
        self.assertTrue(mock_file.write.called)
        # 获取所有写入的内容，并连接成完整JSON
        all_written_data = ''.join(call_args[0][0] for call_args in mock_file.write.call_args_list)
        saved_data = json.loads(all_written_data)
        self.assertEqual(saved_data['success'], True)
        self.assertEqual(saved_data['statistics']['total_issues'], 2)

    @patch('builtins.open', create=True)
    def test_save_results_text(self, mock_open):
        """测试保存结果 - 文本格式"""
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = StaticAnalysisResult(
            success=True,
            total_files=1,
            analyzed_files=1,
            total_issues=2,
            issues_by_severity={'error': 1, 'warning': 1},
            issues_by_type={'syntax': 1, 'style': 1},
            tool_results={},
            execution_time=1.0,
            summary="发现2个问题"
        )

        self.static_cmd._save_results(result, "output.txt", "simple")

        # 验证文件写入被调用
        self.assertTrue(mock_file.write.called)
        # 检查所有写入的内容
        all_written_data = ''.join(call_args[0][0] for call_args in mock_file.write.call_args_list)
        self.assertIn("静态分析报告", all_written_data)
        self.assertIn("分析文件: 1/1", all_written_data)


class TestCLIAnalyzeCommand(unittest.TestCase):
    """CLI analyze命令测试"""

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

    def test_parse_analyze_static_command(self):
        """测试解析analyze static命令"""
        parser = CLIArgumentParser()

        args = parser.parse_args(['analyze', 'static', str(self.test_file)], validate_paths=False)

        self.assertEqual(args.command, 'analyze')
        self.assertEqual(args.analyze_command, 'static')
        self.assertEqual(args.sub_target, str(self.test_file))

    def test_parse_analyze_static_with_options(self):
        """测试解析analyze static命令带选项"""
        parser = CLIArgumentParser()

        args = parser.parse_args([
            'analyze', 'static', str(self.test_file),
            '--tools', 'pylint', 'bandit',
            '--format', 'detailed',
            '--output', 'result.json',
            '--verbose',
            '--dry-run'
        ], validate_paths=False)

        self.assertEqual(args.command, 'analyze')
        self.assertEqual(args.analyze_command, 'static')
        self.assertEqual(args.sub_target, str(self.test_file))
        self.assertEqual(args.sub_tools, ['pylint', 'bandit'])
        self.assertEqual(args.sub_format, 'detailed')
        self.assertEqual(args.sub_output, 'result.json')
        self.assertTrue(args.sub_verbose)
        self.assertTrue(args.sub_dry_run)

    @patch('src.interfaces.main.StaticAnalysisCommand')
    def test_handle_static_analysis_command(self, mock_static_cmd_class):
        """测试处理静态分析命令"""
        # 模拟静态分析命令
        mock_static_cmd = Mock()
        mock_static_cmd_class.return_value = mock_static_cmd

        # 模拟分析结果
        mock_result = Mock()
        mock_result.success = True
        mock_static_cmd.execute_static_analysis.return_value = mock_result

        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='static',
            sub_target=str(self.test_file),
            sub_tools=['pylint'],
            sub_format='simple',
            sub_output=None,
            sub_verbose=False,
            sub_quiet=False,
            sub_dry_run=False
        )

        exit_code = app._handle_static_analysis_command()

        self.assertEqual(exit_code, 0)
        mock_static_cmd.execute_static_analysis.assert_called_once()

    def test_handle_static_analysis_missing_target(self):
        """测试处理静态分析命令 - 缺少目标"""
        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='static',
            sub_target=None
        )

        with patch('builtins.print') as mock_print:
            exit_code = app._handle_static_analysis_command()
            self.assertEqual(exit_code, 1)
            mock_print.assert_called_with("❌ 静态分析需要指定目标路径")

    @patch('src.interfaces.main.StaticAnalysisCommand')
    def test_handle_static_analysis_failure(self, mock_static_cmd_class):
        """测试处理静态分析命令 - 执行失败"""
        # 模拟静态分析命令
        mock_static_cmd = Mock()
        mock_static_cmd_class.return_value = mock_static_cmd

        # 模拟分析失败
        mock_static_cmd.execute_static_analysis.side_effect = Exception("分析失败")

        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='static',
            sub_target=str(self.test_file),
            sub_verbose=False
        )

        with patch('builtins.print') as mock_print:
            exit_code = app._handle_static_analysis_command()
            self.assertEqual(exit_code, 1)

    def test_handle_analyze_command_deep_mode(self):
        """测试处理analyze命令 - 深度模式"""
        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='deep',
            sub_target=str(self.test_file)
        )

        with patch('builtins.print') as mock_print:
            exit_code = app._handle_analyze_command()
            self.assertEqual(exit_code, 1)
            mock_print.assert_called_with("❌ 深度分析模式正在开发中")

    def test_handle_analyze_command_fix_mode(self):
        """测试处理analyze命令 - 修复模式"""
        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='fix',
            sub_target=str(self.test_file)
        )

        with patch('builtins.print') as mock_print:
            exit_code = app._handle_analyze_command()
            self.assertEqual(exit_code, 1)
            mock_print.assert_called_with("❌ 分析修复模式正在开发中")

    def test_handle_analyze_command_unknown_mode(self):
        """测试处理analyze命令 - 未知模式"""
        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='unknown',
            sub_target=str(self.test_file)
        )

        with patch('builtins.print') as mock_print:
            exit_code = app._handle_analyze_command()
            self.assertEqual(exit_code, 1)
            mock_print.assert_called_with("❌ 未知的分析模式，使用 'aidetector analyze --help' 查看可用模式")


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

    @patch('src.interfaces.main.StaticAnalysisCommand')
    def test_full_analyze_static_workflow(self, mock_static_cmd_class):
        """测试完整的analyze static工作流"""
        # 模拟静态分析命令
        mock_static_cmd = Mock()
        mock_static_cmd_class.return_value = mock_static_cmd

        # 模拟分析结果
        mock_result = StaticAnalysisResult(
            success=True,
            total_files=2,
            analyzed_files=2,
            total_issues=0,
            issues_by_severity={},
            issues_by_type={},
            tool_results={},
            execution_time=0.5,
            summary="未发现问题"
        )
        mock_static_cmd.execute_static_analysis.return_value = mock_result

        app = CLIMainApplication()

        # 测试完整命令行解析和执行
        exit_code = app.run([
            'analyze', 'static', str(self.temp_dir_path),
            '--format', 'detailed',
            '--verbose'
        ])

        self.assertEqual(exit_code, 0)
        mock_static_cmd.execute_static_analysis.assert_called_once()

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
            self.assertIn('static', help_text)


if __name__ == '__main__':
    unittest.main()