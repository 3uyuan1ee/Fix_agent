#!/usr/bin/env python3
"""
分析修复命令模块单元测试
测试`analyze fix`命令的功能
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

from src.interfaces.fix_commands import (
    FixSuggestion, FixResult, CodeDiffer, FixManager, FixAnalysisCommand
)
from src.interfaces.cli import CLIArgumentParser, CLIArguments
from src.interfaces.main import CLIMainApplication


class TestFixSuggestion(unittest.TestCase):
    """修复建议测试"""

    def test_fix_suggestion_creation(self):
        """测试修复建议创建"""
        suggestion = FixSuggestion(
            file_path="test.py",
            issue_type="style",
            description="测试建议",
            line_number=10,
            original_code="original code",
            fixed_code="fixed code"
        )

        self.assertEqual(suggestion.file_path, "test.py")
        self.assertEqual(suggestion.issue_type, "style")
        self.assertEqual(suggestion.description, "测试建议")
        self.assertEqual(suggestion.line_number, 10)
        self.assertEqual(suggestion.original_code, "original code")
        self.assertEqual(suggestion.fixed_code, "fixed code")
        self.assertEqual(suggestion.severity, "medium")
        self.assertEqual(suggestion.confidence, 0.8)
        self.assertTrue(suggestion.auto_applicable)

    def test_fix_suggestion_with_custom_attributes(self):
        """测试自定义属性的修复建议"""
        suggestion = FixSuggestion(
            file_path="test.py",
            issue_type="security",
            description="安全问题",
            line_number=5,
            original_code="password = '123'",
            fixed_code="password = os.getenv('PASSWORD')",
            severity="high",
            confidence=0.9,
            auto_applicable=False
        )

        self.assertEqual(suggestion.severity, "high")
        self.assertEqual(suggestion.confidence, 0.9)
        self.assertFalse(suggestion.auto_applicable)


class TestFixResult(unittest.TestCase):
    """修复结果测试"""

    def test_fix_result_creation(self):
        """测试修复结果创建"""
        suggestions = [
            FixSuggestion("test.py", "style", "测试", 1, "old", "new")
        ]

        result = FixResult(
            success=True,
            target="test.py",
            suggestions=suggestions,
            applied_fixes=suggestions,
            execution_time=1.5,
            total_issues=1,
            fixed_issues=1
        )

        self.assertTrue(result.success)
        self.assertEqual(result.target, "test.py")
        self.assertEqual(len(result.suggestions), 1)
        self.assertEqual(len(result.applied_fixes), 1)
        self.assertEqual(result.execution_time, 1.5)
        self.assertEqual(result.total_issues, 1)
        self.assertEqual(result.fixed_issues, 1)


class TestCodeDiffer(unittest.TestCase):
    """代码差异对比器测试"""

    def test_generate_diff(self):
        """测试生成代码差异"""
        original = "def hello():\n    print('Hello')"
        fixed = "def hello():\n    print('Hello, World!')"

        diff = CodeDiffer.generate_diff(original, fixed, "test.py")

        self.assertIn("--- a/test.py", diff)
        self.assertIn("+++ b/test.py", diff)
        self.assertIn("-    print('Hello')", diff)
        self.assertIn("+    print('Hello, World!')", diff)

    def test_generate_diff_no_changes(self):
        """测试无变更的差异生成"""
        original = "def hello():\n    print('Hello')"
        fixed = "def hello():\n    print('Hello')"

        diff = CodeDiffer.generate_diff(original, fixed, "test.py")

        self.assertEqual(diff.strip(), "")

    def test_generate_diff_empty_content(self):
        """测试空内容差异生成"""
        original = ""
        fixed = "def hello():\n    pass"

        diff = CodeDiffer.generate_diff(original, fixed, "test.py")

        self.assertIn("+++ b/test.py", diff)
        self.assertIn("+def hello():", diff)


class TestFixManager(unittest.TestCase):
    """修复管理器测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.backup_dir = os.path.join(self.temp_dir, "backups")
        self.fix_manager = FixManager(self.backup_dir)

        # 创建测试文件
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write("def hello():\n    print('Hello')\n")

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fix_manager_initialization(self):
        """测试修复管理器初始化"""
        manager = FixManager()
        self.assertTrue(manager.backup_dir.exists())

        # 使用临时目录测试自定义备份目录
        custom_backup_dir = os.path.join(self.temp_dir, "custom_backup")
        custom_manager = FixManager(custom_backup_dir)
        self.assertEqual(str(custom_manager.backup_dir), custom_backup_dir)
        self.assertTrue(custom_manager.backup_dir.exists())

    def test_create_backup(self):
        """测试创建备份"""
        backup_path = self.fix_manager.create_backup(self.test_file)

        self.assertTrue(os.path.exists(backup_path))
        self.assertTrue(backup_path.startswith(self.backup_dir))
        self.assertIn("test_", os.path.basename(backup_path))

        # 验证备份内容
        with open(self.test_file, 'r', encoding='utf-8') as original:
            with open(backup_path, 'r', encoding='utf-8') as backup:
                self.assertEqual(original.read(), backup.read())

    def test_create_backup_file_not_found(self):
        """测试备份不存在的文件"""
        with self.assertRaises(FileNotFoundError):
            self.fix_manager.create_backup("/nonexistent/file.py")

    def test_apply_fix_success(self):
        """测试成功应用修复"""
        suggestion = FixSuggestion(
            file_path=self.test_file,
            issue_type="style",
            description="修复打印语句",
            line_number=2,
            original_code="    print('Hello')",
            fixed_code="    print('Hello, World!')"
        )

        result = self.fix_manager.apply_fix(suggestion)
        self.assertTrue(result)

        # 验证文件内容已修改
        with open(self.test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("print('Hello, World!')", content)
            self.assertNotIn("print('Hello')", content)

    def test_apply_fix_invalid_line_number(self):
        """测试无效行号的修复"""
        suggestion = FixSuggestion(
            file_path=self.test_file,
            issue_type="style",
            description="无效行号修复",
            line_number=999,  # 超出文件行数
            original_code="old",
            fixed_code="new"
        )

        result = self.fix_manager.apply_fix(suggestion)
        self.assertFalse(result)

    def test_apply_fix_file_not_found(self):
        """测试修复不存在的文件"""
        suggestion = FixSuggestion(
            file_path="/nonexistent/file.py",
            issue_type="style",
            description="修复不存在的文件",
            line_number=1,
            original_code="old",
            fixed_code="new"
        )

        result = self.fix_manager.apply_fix(suggestion)
        self.assertFalse(result)

    def test_restore_backup(self):
        """测试恢复备份"""
        # 创建备份
        backup_path = self.fix_manager.create_backup(self.test_file)

        # 修改原文件
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write("modified content")

        # 恢复备份
        result = self.fix_manager.restore_backup(backup_path, self.test_file)
        self.assertTrue(result)

        # 验证内容已恢复
        with open(self.test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("def hello():", content)
            self.assertNotIn("modified content", content)


class TestFixAnalysisCommand(unittest.TestCase):
    """分析修复命令测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        # 创建测试Python文件
        self.test_file = self.temp_dir_path / "test.py"
        self.test_file.write_text("""
import os
import sys

def test_function():
    password = "admin123"  # 硬编码密码
    import *  # 通配符导入
    print("Hello")
    return password
""")

        # 创建分析修复命令处理器
        self.fix_cmd = FixAnalysisCommand()

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fix_analysis_command_initialization(self):
        """测试分析修复命令初始化"""
        cmd = FixAnalysisCommand()
        self.assertIsNotNone(cmd.config)
        self.assertIsNotNone(cmd.orchestrator)
        self.assertIsNotNone(cmd.fix_manager)

    def test_validate_target_file(self):
        """测试验证目标文件"""
        # 测试Python文件
        self.assertTrue(self.fix_cmd._validate_target(self.test_file))

        # 测试非Python文件
        non_py_file = self.temp_dir_path / "test.txt"
        non_py_file.write_text("text content")
        self.assertFalse(self.fix_cmd._validate_target(non_py_file))

    def test_validate_target_directory(self):
        """测试验证目标目录"""
        # 包含Python文件的目录
        self.assertTrue(self.fix_cmd._validate_target(self.temp_dir_path))

        # 空目录
        empty_dir = self.temp_dir_path / "empty"
        empty_dir.mkdir()
        self.assertFalse(self.fix_cmd._validate_target(empty_dir))

    def test_validate_target_nonexistent(self):
        """测试验证不存在的目标"""
        nonexistent_path = Path("/nonexistent/path")
        self.assertFalse(self.fix_cmd._validate_target(nonexistent_path))

    def test_analyze_file(self):
        """测试分析文件"""
        suggestions = self.fix_cmd._analyze_file(self.test_file)

        # 应该找到硬编码密码和通配符导入问题
        self.assertGreater(len(suggestions), 0)

        issue_types = [s.issue_type for s in suggestions]
        self.assertIn("security", issue_types)
        self.assertIn("style", issue_types)

    def test_generate_demo_suggestions(self):
        """测试生成演示建议"""
        suggestions = self.fix_cmd._generate_demo_suggestions(self.test_file)

        self.assertGreater(len(suggestions), 0)
        for suggestion in suggestions:
            self.assertIsInstance(suggestion, FixSuggestion)
            self.assertEqual(suggestion.file_path, str(self.test_file))

    @patch('src.interfaces.fix_commands.AgentOrchestrator')
    def test_execute_fix_analysis_success(self, mock_orchestrator_class):
        """测试执行分析修复 - 成功情况"""
        # 模拟编排器
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # 模拟会话
        mock_session = Mock()
        mock_session.session_id = "test_session"
        mock_orchestrator.create_session.return_value = mock_session

        cmd = FixAnalysisCommand()

        # 模拟用户输入跳过所有修复
        with patch('builtins.input', return_value='n'):
            result = cmd.execute_fix_analysis(
                target=str(self.test_file),
                confirm_fixes=True,
                quiet=True
            )

        self.assertTrue(result.success)
        self.assertEqual(result.target, str(self.test_file))
        self.assertGreater(result.total_issues, 0)
        self.assertEqual(result.fixed_issues, 0)  # 跳过了所有修复

    @patch('src.interfaces.fix_commands.AgentOrchestrator')
    def test_execute_fix_analysis_file_not_found(self, mock_orchestrator_class):
        """测试执行分析修复 - 文件不存在"""
        cmd = FixAnalysisCommand()

        with self.assertRaises(FileNotFoundError):
            cmd.execute_fix_analysis(
                target="/nonexistent/file.py",
                confirm_fixes=True,
                quiet=True
            )

    @patch('src.interfaces.fix_commands.AgentOrchestrator')
    def test_execute_fix_analysis_invalid_target(self, mock_orchestrator_class):
        """测试执行分析修复 - 无效目标"""
        cmd = FixAnalysisCommand()

        # 创建非Python文件
        non_py_file = self.temp_dir_path / "test.txt"
        non_py_file.write_text("text content")

        result = cmd.execute_fix_analysis(
            target=str(non_py_file),
            confirm_fixes=True,
            quiet=True
        )

        self.assertFalse(result.success)

    def test_display_fix_suggestions(self):
        """测试显示修复建议"""
        suggestions = [
            FixSuggestion(
                file_path="test.py",
                issue_type="security",
                description="硬编码密码",
                line_number=5,
                original_code='password = "123"',
                fixed_code='password = os.getenv("PASSWORD")',
                severity="high"
            )
        ]

        # 捕获输出
        with patch('builtins.print') as mock_print:
            self.fix_cmd._display_fix_suggestions(suggestions)

            # 验证print被调用
            self.assertTrue(mock_print.called)

            # 检查输出内容
            printed_args = [str(call.args[0]) for call in mock_print.call_args_list]
            output_text = ''.join(printed_args)
            self.assertIn("修复建议", output_text)
            self.assertIn("硬编码密码", output_text)
            self.assertIn("test.py:5", output_text)


class TestCLIFixCommand(unittest.TestCase):
    """CLI修复命令测试"""

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

    def test_parse_analyze_fix_command(self):
        """测试解析analyze fix命令"""
        parser = CLIArgumentParser()

        args = parser.parse_args(['analyze', 'fix', str(self.test_file)], validate_paths=False)

        self.assertEqual(args.command, 'analyze')
        self.assertEqual(args.analyze_command, 'fix')
        self.assertEqual(args.sub_target, str(self.test_file))

    def test_parse_analyze_fix_with_options(self):
        """测试解析analyze fix命令带选项"""
        parser = CLIArgumentParser()

        args = parser.parse_args([
            'analyze', 'fix', str(self.test_file),
            '--no-confirm',
            '--verbose'
        ], validate_paths=False)

        self.assertEqual(args.command, 'analyze')
        self.assertEqual(args.analyze_command, 'fix')
        self.assertEqual(args.sub_target, str(self.test_file))
        self.assertTrue(args.sub_no_confirm)
        self.assertTrue(args.sub_verbose)

    @patch('src.interfaces.main.FixAnalysisCommand')
    def test_handle_fix_analysis_command(self, mock_fix_cmd_class):
        """测试处理分析修复命令"""
        # 模拟分析修复命令
        mock_fix_cmd = Mock()
        mock_fix_cmd_class.return_value = mock_fix_cmd

        # 模拟修复结果
        mock_result = Mock()
        mock_result.success = True
        mock_fix_cmd.execute_fix_analysis.return_value = mock_result

        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='fix',
            sub_target=str(self.test_file),
            sub_no_confirm=False,
            sub_verbose=False,
            sub_quiet=False
        )

        exit_code = app._handle_fix_analysis_command()

        self.assertEqual(exit_code, 0)
        mock_fix_cmd.execute_fix_analysis.assert_called_once()

    def test_handle_fix_analysis_missing_target(self):
        """测试处理分析修复命令 - 缺少目标"""
        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='fix',
            sub_target=None
        )

        with patch('builtins.print') as mock_print:
            exit_code = app._handle_fix_analysis_command()
            self.assertEqual(exit_code, 1)
            mock_print.assert_called_with("❌ 分析修复需要指定目标路径")

    @patch('src.interfaces.main.FixAnalysisCommand')
    def test_handle_fix_analysis_failure(self, mock_fix_cmd_class):
        """测试处理分析修复命令 - 执行失败"""
        # 模拟分析修复命令
        mock_fix_cmd = Mock()
        mock_fix_cmd_class.return_value = mock_fix_cmd

        # 模拟修复失败
        mock_fix_cmd.execute_fix_analysis.side_effect = Exception("修复失败")

        app = CLIMainApplication()
        app.args = CLIArguments(
            command='analyze',
            analyze_command='fix',
            sub_target=str(self.test_file),
            sub_verbose=False
        )

        with patch('builtins.print'):
            exit_code = app._handle_fix_analysis_command()
            self.assertEqual(exit_code, 1)


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_dir_path = Path(self.temp_dir)

        # 创建测试项目
        (self.temp_dir_path / "main.py").write_text("""
import os
from utils import *

def main():
    password = "admin123"
    print(password)
    return password
""")

        (self.temp_dir_path / "utils.py").write_text("""
import sys

def helper():
    unused_var = "not used"
    return True
""")

    def tearDown(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch('src.interfaces.main.FixAnalysisCommand')
    def test_full_analyze_fix_workflow(self, mock_fix_cmd_class):
        """测试完整的analyze fix工作流"""
        # 模拟分析修复命令
        mock_fix_cmd = Mock()
        mock_fix_cmd_class.return_value = mock_fix_cmd

        # 模拟修复结果
        mock_result = Mock()
        mock_result.success = True
        mock_result.fixed_issues = 2
        mock_result.total_issues = 3
        mock_result.execution_time = 1.5
        mock_fix_cmd.execute_fix_analysis.return_value = mock_result

        app = CLIMainApplication()

        # 测试完整命令行解析和执行
        exit_code = app.run([
            'analyze', 'fix', str(self.temp_dir_path),
            '--verbose'
        ])

        self.assertEqual(exit_code, 0)
        mock_fix_cmd.execute_fix_analysis.assert_called_once()

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
            self.assertIn('fix', help_text)


if __name__ == '__main__':
    unittest.main()