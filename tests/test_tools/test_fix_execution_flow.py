"""
测试修复执行流程
"""

import pytest
import tempfile
import asyncio
import json
import time
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock, Mock

from src.tools.fix_generator import FixGenerator, FixRequest, FixResult, FixSuggestion
from src.tools.backup_manager import BackupManager, BackupResult
from src.tools.diff_viewer import DiffViewer, DiffResult
from src.tools.fix_confirmation import FixConfirmationManager, ConfirmationRequest, ConfirmationResponse, ConfirmationStatus
from src.tools.fix_executor import FixExecutor, ExecutionResult, ExecutionStatus
from src.tools.fix_coordinator import FixCoordinator, FixAnalysisRequest, FixProcessResult


class TestFixExecutionFlow:
    """测试修复执行流程"""

    @pytest.fixture
    def temp_project_dir(self):
        """临时项目目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            # 创建包含问题的Python文件
            (project_dir / "vulnerable_code.py").write_text("""
import os
import subprocess

# 硬编码密码
PASSWORD = "hardcoded_password_123"

def get_user_data(user_id):
    # SQL注入漏洞
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query

def execute_command(command):
    # 命令注入漏洞
    return subprocess.run(command, shell=True, capture_output=True)

class DataProcessor:
    def __init__(self):
        self.data = []

    def load_data(self, source):
        # 不安全的反序列化
        import pickle
        with open(source, 'rb') as f:
            self.data = pickle.load(f)
""")

            # 创建简单的Python文件
            (project_dir / "simple_code.py").write_text("""
def add_numbers(a, b):
    return a + b

def greet(name):
    return f"Hello, {name}!"

class Calculator:
    def __init__(self):
        self.history = []

    def calculate(self, operation, a, b):
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
    def mock_llm_client(self):
        """Mock LLM客户端"""
        mock_client = AsyncMock()

        # 模拟修复响应
        mock_response = Mock()

        # 创建语法正确的完整修复文件内容
        complete_fixed_file = """import os
import subprocess

# Use environment variable for password
PASSWORD = os.environ.get('APP_PASSWORD')

def get_user_data(user_id):
    # SQL injection vulnerability fixed
    query = "SELECT * FROM users WHERE id = ?"
    return query

def execute_command(command):
    # Command injection vulnerability
    return subprocess.run(command, shell=True, capture_output=True)

class DataProcessor:
    def __init__(self):
        self.data = []

    def load_data(self, source):
        # Unsafe deserialization
        import pickle
        with open(source, 'rb') as f:
            self.data = pickle.load(f)"""

        # 转义换行符
        escaped_content = complete_fixed_file.replace('\n', '\\n')

        # 构建JSON结构
        response_data = {
            "fixes": [
                {
                    "issue_id": "fix_1",
                    "issue_type": "Hardcoded Credentials",
                    "description": "Hardcoded password found in source code",
                    "location": {"line": 5, "column": 1},
                    "severity": "high",
                    "fixed_code": "# Use environment variable for password\nPASSWORD = os.environ.get('APP_PASSWORD')",
                    "explanation": "Hardcoded passwords should be stored in environment variables",
                    "confidence": 0.95,
                    "tags": ["security", "credentials"]
                },
                {
                    "issue_id": "fix_2",
                    "issue_type": "SQL Injection",
                    "description": "SQL injection vulnerability in user input",
                    "location": {"line": 8, "column": 13},
                    "severity": "critical",
                    "fixed_code": "query = \"SELECT * FROM users WHERE id = ?\"",
                    "explanation": "Use parameterized queries to prevent SQL injection",
                    "confidence": 0.98,
                    "tags": ["security", "sql_injection"]
                }
            ],
            "complete_fixed_file": complete_fixed_file,
            "summary": "Fixed 2 security vulnerabilities: hardcoded credentials and SQL injection",
            "risk_assessment": "Low risk from these changes, both fixes improve security"
        }

        mock_response.content = json.dumps(response_data)
        mock_response.usage = {"total_tokens": 2500, "prompt_tokens": 1200, "completion_tokens": 1300}
        mock_response.model = "gpt-4"

        # 设置complete方法返回正确的响应
        mock_client.complete = AsyncMock(return_value=mock_response)

        return mock_client

    @pytest.fixture
    def fix_generator(self, mock_llm_client):
        """修复生成器fixture"""
        # 使用Mock对象避免初始化问题
        from unittest.mock import Mock
        mock_logger = Mock()
        mock_logger.info = Mock()
        mock_logger.error = Mock()
        mock_logger.warning = Mock()

        generator = FixGenerator.__new__(FixGenerator)
        generator.llm_client = mock_llm_client
        generator.prompt_manager = Mock()
        generator.prompt_manager.get_template.return_value = None
        generator.prompt_manager.render_template.return_value = Mock(success=False, content="")
        generator.config_manager = Mock()
        generator.config_manager.get_section.return_value = {}
        generator.default_model = "gpt-4"
        generator.default_temperature = 0.2
        generator.max_tokens = 6000
        generator.max_file_size = 50 * 1024
        generator.config = {}
        generator.logger = mock_logger

        # 绑定真实方法
        generator._validate_request = FixGenerator._validate_request.__get__(generator, FixGenerator)
        generator._construct_fix_prompt = FixGenerator._construct_fix_prompt.__get__(generator, FixGenerator)
        generator._get_default_fix_system_message = FixGenerator._get_default_fix_system_message.__get__(generator, FixGenerator)
        generator._construct_fix_user_message = FixGenerator._construct_fix_user_message.__get__(generator, FixGenerator)
        generator._format_issues_for_prompt = FixGenerator._format_issues_for_prompt.__get__(generator, FixGenerator)
        generator._parse_llm_response = FixGenerator._parse_llm_response.__get__(generator, FixGenerator)
        generator._parse_fix_suggestions = FixGenerator._parse_fix_suggestions.__get__(generator, FixGenerator)
        generator._parse_json_fixes = FixGenerator._parse_json_fixes.__get__(generator, FixGenerator)
        generator._generate_complete_fixed_content = FixGenerator._generate_complete_fixed_content.__get__(generator, FixGenerator)

        return generator

    @pytest.fixture
    def backup_manager(self):
        """备份管理器fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = Path(temp_dir) / "backups"
            backup_dir.mkdir()

            manager = BackupManager.__new__(BackupManager)
            manager.backup_dir = backup_dir
            manager.metadata_file = backup_dir / 'backup_metadata.json'
            manager.max_backups_per_file = 10
            manager.backup_retention_days = 30
            manager.compress_backups = True
            manager.metadata = {"backups": []}
            manager.logger = Mock()

            # 绑定真实方法
            manager._generate_backup_id = BackupManager._generate_backup_id.__get__(manager, BackupManager)
            manager._get_backup_path = BackupManager._get_backup_path.__get__(manager, BackupManager)
            manager._calculate_file_hash = BackupManager._calculate_file_hash.__get__(manager, BackupManager)
            manager._find_existing_backup = BackupManager._find_existing_backup.__get__(manager, BackupManager)
            manager._create_compressed_backup = BackupManager._create_compressed_backup.__get__(manager, BackupManager)
            manager._save_backup_metadata = BackupManager._save_backup_metadata.__get__(manager, BackupManager)
            manager._dict_to_metadata = BackupManager._dict_to_metadata.__get__(manager, BackupManager)
            manager._save_metadata_file = BackupManager._save_metadata_file.__get__(manager, BackupManager)
            manager._get_backup_metadata = BackupManager._get_backup_metadata.__get__(manager, BackupManager)

            return manager

    @pytest.fixture
    def diff_viewer(self):
        """差异查看器fixture"""
        viewer = DiffViewer.__new__(DiffViewer)
        viewer.context_lines = 3
        viewer.show_line_numbers = True
        viewer.highlight_syntax = True
        viewer.ignore_whitespace = False
        viewer.logger = Mock()

        # 绑定真实方法
        viewer._normalize_lines = DiffViewer._normalize_lines.__get__(viewer, DiffViewer)
        viewer._generate_diff_chunks = DiffViewer._generate_diff_chunks.__get__(viewer, DiffViewer)
        viewer._calculate_diff_stats = DiffViewer._calculate_diff_stats.__get__(viewer, DiffViewer)
        viewer._generate_summary = DiffViewer._generate_summary.__get__(viewer, DiffViewer)
        viewer._format_unified_diff_from_chunks = DiffViewer._format_unified_diff_from_chunks.__get__(viewer, DiffViewer)

        return viewer

    @pytest.fixture
    def fix_executor(self):
        """修复执行引擎fixture"""
        executor = FixExecutor.__new__(FixExecutor)
        executor.backup_manager = Mock()
        executor.diff_viewer = Mock()
        executor.create_backup_before_fix = True
        executor.validate_syntax_after_fix = True
        executor.auto_rollback_on_error = True
        executor.use_temp_file_for_write = True
        executor.preserve_permissions = True
        executor.logger = Mock()

        # 绑定真实方法
        executor._select_suggestions_to_apply = FixExecutor._select_suggestions_to_apply.__get__(executor, FixExecutor)
        executor._apply_fixes = FixExecutor._apply_fixes.__get__(executor, FixExecutor)
        executor._validate_syntax = FixExecutor._validate_syntax.__get__(executor, FixExecutor)
        executor._write_fixed_file = FixExecutor._write_fixed_file.__get__(executor, FixExecutor)
        executor._verify_fix_result = FixExecutor._verify_fix_result.__get__(executor, FixExecutor)
        executor._rollback_fix = FixExecutor._rollback_fix.__get__(executor, FixExecutor)
        executor.get_execution_statistics = FixExecutor.get_execution_statistics.__get__(executor, FixExecutor)

        return executor

    @pytest.fixture
    def fix_coordinator(self, mock_llm_client):
        """修复流程协调器fixture"""
        coordinator = FixCoordinator.__new__(FixCoordinator)
        coordinator.parallel_processing = False
        coordinator.max_parallel_files = 3
        coordinator.generate_reports = True
        coordinator.report_output_dir = Path("./test_reports")
        coordinator.report_output_dir.mkdir(exist_ok=True)
        coordinator.logger = Mock()

        # 创建mock组件
        coordinator.fix_generator = Mock()
        coordinator.backup_manager = Mock()
        coordinator.diff_viewer = Mock()
        coordinator.confirmation_manager = Mock()
        coordinator.fix_executor = Mock()

        # 绑定真实方法
        coordinator.validate_fix_request = FixCoordinator.validate_fix_request.__get__(coordinator, FixCoordinator)
        coordinator.get_process_statistics = FixCoordinator.get_process_statistics.__get__(coordinator, FixCoordinator)
        coordinator.get_supported_analysis_types = FixCoordinator.get_supported_analysis_types.__get__(coordinator, FixCoordinator)

        return coordinator

    # 测试修复生成器
    @pytest.mark.asyncio
    async def test_fix_generator_initialization(self, fix_generator):
        """测试修复生成器初始化"""
        assert fix_generator is not None
        assert hasattr(fix_generator, 'llm_client')
        assert hasattr(fix_generator, 'prompt_manager')
        assert hasattr(fix_generator, 'get_supported_fix_types')
        assert isinstance(fix_generator.get_supported_fix_types(), list)

    def test_fix_request_creation(self):
        """测试修复请求创建"""
        request = FixRequest(
            file_path="/test/file.py",
            issues=[{"type": "SQL Injection", "line": 10}],
            original_content="test content",
            analysis_type="security",
            user_instructions="Focus on security"
        )

        assert request.file_path == "/test/file.py"
        assert request.analysis_type == "security"
        assert request.issues[0]["type"] == "SQL Injection"
        assert request.user_instructions == "Focus on security"

    @pytest.mark.asyncio
    async def test_fix_validation(self, fix_generator, temp_project_dir):
        """测试修复请求验证"""
        # 测试有效请求
        file_path = Path(temp_project_dir) / "vulnerable_code.py"
        issues = [{"type": "SQL Injection", "line": 8}]
        original_content = file_path.read_text()

        request = FixRequest(
            file_path=str(file_path),
            issues=issues,
            original_content=original_content
        )

        is_valid = fix_generator._validate_request(request)
        assert is_valid is True

        # 测试无效请求 - 文件不存在
        invalid_request = FixRequest(
            file_path="/nonexistent/file.py",
            issues=issues,
            original_content="test"
        )

        is_valid = fix_generator._validate_request(invalid_request)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_fix_suggestions_parsing(self, fix_generator):
        """测试修复建议解析"""
        request = FixRequest(
            file_path="/test/file.py",
            issues=[{"type": "SQL Injection", "line": 10}],
            original_content="test content"
        )

        # 测试JSON格式响应
        json_response = """{
            "fixes": [
                {
                    "issue_id": "fix_1",
                    "issue_type": "SQL Injection",
                    "description": "SQL injection vulnerability",
                    "location": {"line": 10, "column": 5},
                    "severity": "high",
                    "fixed_code": "fixed code here",
                    "explanation": "explanation here",
                    "confidence": 0.95,
                    "tags": ["security", "sql"]
                }
            ]
        }"""

        suggestions = fix_generator._parse_fix_suggestions(json_response, request)
        assert len(suggestions) == 1
        assert suggestions[0].issue_type == "SQL Injection"
        assert suggestions[0].confidence == 0.95

    @pytest.mark.asyncio
    async def test_fix_generation(self, fix_generator, temp_project_dir):
        """测试修复生成"""
        file_path = Path(temp_project_dir) / "vulnerable_code.py"
        issues = [
            {"type": "Hardcoded Credentials", "line": 5, "severity": "high"},
            {"type": "SQL Injection", "line": 8, "severity": "critical"}
        ]
        original_content = file_path.read_text()

        request = FixRequest(
            file_path=str(file_path),
            issues=issues,
            original_content=original_content,
            analysis_type="security"
        )

        result = await fix_generator.generate_fixes(request)

        assert isinstance(result, FixResult)
        assert result.success is True
        assert result.file_path == str(file_path)
        assert len(result.suggestions) > 0
        assert result.complete_fixed_content != ""
        assert result.execution_time > 0

    # 测试备份管理器
    def test_backup_creation(self, backup_manager, temp_project_dir):
        """测试备份创建"""
        file_path = Path(temp_project_dir) / "vulnerable_code.py"

        result = backup_manager.create_backup(
            str(file_path),
            reason="test_backup",
            issues_fixed=["SQL Injection", "Hardcoded Credentials"]
        )

        assert isinstance(result, BackupResult)
        assert result.success is True
        assert result.backup_id != ""
        assert result.backup_path != ""
        assert result.file_size > 0
        assert result.metadata is not None
        assert result.metadata.reason == "test_backup"
        assert "SQL Injection" in result.metadata.issues_fixed

    def test_backup_restoration(self, backup_manager, temp_project_dir):
        """测试备份恢复"""
        file_path = Path(temp_project_dir) / "vulnerable_code.py"
        original_content = file_path.read_text()

        # 创建备份
        backup_result = backup_manager.create_backup(str(file_path), reason="test_restore")

        # 修改文件
        file_path.write_text("modified content")
        assert file_path.read_text() == "modified content"

        # 恢复备份
        success = backup_manager.restore_backup(backup_result.backup_id)
        assert success is True
        assert file_path.read_text() == original_content

    def test_backup_listing(self, backup_manager, temp_project_dir):
        """测试备份列表"""
        file_path = Path(temp_project_dir) / "vulnerable_code.py"

        # 创建多个备份
        backup1 = backup_manager.create_backup(str(file_path), reason="backup_1")
        backup2 = backup_manager.create_backup(str(file_path), reason="backup_2")

        # 列出备份
        backups = backup_manager.list_backups(str(file_path))

        assert len(backups) == 2
        assert backups[0].timestamp >= backups[1].timestamp  # 最新的在前
        assert backup1.backup_id in [b.backup_id for b in backups]
        assert backup2.backup_id in [b.backup_id for b in backups]

    # 测试差异查看器
    def test_diff_generation(self, diff_viewer):
        """测试差异生成"""
        old_content = """def old_function():
    print("old")
    return 1"""

        new_content = """def new_function():
    print("new")
    return 2"""

        result = diff_viewer.generate_diff("/test/file.py", old_content, new_content)

        assert isinstance(result, DiffResult)
        assert result.file_path == "/test/file.py"
        assert result.old_content == old_content
        assert result.new_content == new_content
        assert len(result.chunks) > 0
        assert result.stats['modified'] > 0
        assert result.summary != ""

    def test_unified_diff_format(self, diff_viewer):
        """测试统一格式差异"""
        old_content = "line 1\nline 2\nline 3"
        new_content = "line 1\nmodified line 2\nline 3"

        diff_text = diff_viewer.generate_unified_diff("/test/file.py", old_content, new_content)

        assert "--- a/file.py" in diff_text
        assert "+++ b/file.py" in diff_text
        assert "-line 2" in diff_text
        assert "+modified line 2" in diff_text

    def test_change_complexity_analysis(self, diff_viewer):
        """测试变更复杂度分析"""
        old_content = "def old(): pass"
        new_content = """def new():
    # Added comment
    x = 1 + 2
    return x"""

        result = diff_viewer.generate_diff("/test/file.py", old_content, new_content)
        complexity = diff_viewer.analyze_change_complexity(result)

        assert 'complexity' in complexity
        assert 'change_ratio' in complexity
        assert 'total_changes' in complexity
        assert 'recommendation' in complexity

    # 测试修复确认机制
    def test_confirmation_request_creation(self):
        """测试确认请求创建"""
        fix_result = FixResult(file_path="/test/file.py", success=True)
        diff_result = DiffResult(file_path="/test/file.py", old_content="old", new_content="new")

        request = ConfirmationRequest(
            fix_id="test_fix",
            file_path="/test/file.py",
            fix_result=fix_result,
            diff_result=diff_result,
            backup_id="backup_123",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        assert request.fix_id == "test_fix"
        assert request.file_path == "/test/file.py"
        assert request.backup_id == "backup_123"

    def test_confirmation_response_creation(self):
        """测试确认响应创建"""
        response = ConfirmationResponse(
            fix_id="test_fix",
            status=ConfirmationStatus.APPROVED,
            user_message="User approved"
        )

        assert response.fix_id == "test_fix"
        assert response.status == ConfirmationStatus.APPROVED
        assert response.user_message == "User approved"

    def test_auto_approval_decision(self):
        """测试自动批准决策"""
        manager = FixConfirmationManager()
        manager.auto_approve_safe = True

        # 创建安全的修复结果
        safe_suggestions = [
            FixSuggestion(
                issue_id="safe_1",
                issue_type="style",
                description="Minor style issue",
                location={},
                severity="low",
                fixed_code="fixed code",
                explanation="safe fix",
                confidence=0.9
            )
        ]

        fix_result = FixResult(file_path="/test/file.py", success=True, suggestions=safe_suggestions)
        diff_result = DiffResult(file_path="/test/file.py", old_content="old", new_content="new")

        request = ConfirmationRequest(
            fix_id="test_fix",
            file_path="/test/file.py",
            fix_result=fix_result,
            diff_result=diff_result,
            backup_id="backup_123",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            auto_approve_safe=True
        )

        should_approve = manager._should_auto_approve(request)
        assert should_approve is True

    # 测试修复执行引擎
    def test_execution_result_creation(self):
        """测试执行结果创建"""
        result = ExecutionResult(
            fix_id="test_fix",
            file_path="/test/file.py",
            status=ExecutionStatus.COMPLETED,
            success=True,
            backup_id="backup_123",
            original_content="old",
            fixed_content="new"
        )

        assert result.fix_id == "test_fix"
        assert result.status == ExecutionStatus.COMPLETED
        assert result.success is True

    def test_suggestion_selection(self, fix_executor):
        """测试修复建议选择"""
        suggestions = [
            FixSuggestion(issue_id="1", issue_type="type1", description="desc1", location={}, severity="high", fixed_code="fix1", explanation="exp1", confidence=0.9),
            FixSuggestion(issue_id="2", issue_type="type2", description="desc2", location={}, severity="medium", fixed_code="fix2", explanation="exp2", confidence=0.8),
            FixSuggestion(issue_id="3", issue_type="type3", description="desc3", location={}, severity="low", fixed_code="fix3", explanation="exp3", confidence=0.7)
        ]

        # 测试批准所有
        from src.tools.fix_confirmation import ConfirmationResponse, ConfirmationStatus
        response = ConfirmationResponse(fix_id="test", status=ConfirmationStatus.APPROVED)
        selected = fix_executor._select_suggestions_to_apply(suggestions, response)
        assert len(selected) == 3

        # 测试部分批准
        response = ConfirmationResponse(fix_id="test", status=ConfirmationStatus.PARTIAL, selected_suggestions=[0, 2])
        selected = fix_executor._select_suggestions_to_apply(suggestions, response)
        assert len(selected) == 2
        assert selected[0].issue_id == "1"
        assert selected[1].issue_id == "3"

    def test_syntax_validation(self, fix_executor):
        """测试语法验证"""
        # 有效代码
        valid_code = "def test():\n    return 1"
        assert fix_executor._validate_syntax(valid_code, "/test.py") is True

        # 无效代码 - 真正的语法错误
        invalid_code = "def test():\n    return 1\n    def unclosed_function():\n        if True:\n            print('hello'"
        assert fix_executor._validate_syntax(invalid_code, "/test.py") is False

    # 测试修复流程协调器
    @pytest.mark.asyncio
    async def test_fix_coordinator_request_validation(self, fix_coordinator, temp_project_dir):
        """测试修复请求验证"""
        file_path = Path(temp_project_dir) / "vulnerable_code.py"

        # 有效请求
        valid_request = FixAnalysisRequest(
            file_path=str(file_path),
            issues=[{"type": "SQL Injection", "line": 8}],
            analysis_type="security"
        )

        is_valid, message = fix_coordinator.validate_fix_request(valid_request)
        assert is_valid is True

        # 无效请求 - 文件不存在
        invalid_request = FixAnalysisRequest(
            file_path="/nonexistent/file.py",
            issues=[{"type": "SQL Injection"}],
            analysis_type="security"
        )

        is_valid, message = fix_coordinator.validate_fix_request(invalid_request)
        assert is_valid is False
        assert "does not exist" in message

    def test_fix_coordinator_statistics(self, fix_coordinator):
        """测试协调器统计"""
        # 创建模拟结果
        process_results = [
            FixProcessResult(
                process_id="1",
                file_path="/test/file1.py",
                success=True,
                total_time=1.5,
                stages_completed=["fix_generation", "backup_creation", "fix_execution"],
                fix_result=Mock(),
                backup_result=Mock(),
                diff_result=Mock(),
                confirmation_response=Mock(),
                execution_result=Mock(),
                summary="Test success"
            ),
            FixProcessResult(
                process_id="2",
                file_path="/test/file2.py",
                success=False,
                total_time=2.0,
                error_message="Test error",
                stages_completed=["fix_generation"],
                fix_result=Mock(),
                backup_result=Mock(),
                diff_result=Mock(),
                confirmation_response=Mock(),
                execution_result=Mock(),
                summary="Test failure"
            )
        ]

        stats = fix_coordinator.get_process_statistics(process_results)

        assert stats["total_files"] == 2
        assert stats["successful_files"] == 1
        assert stats["failed_files"] == 1
        assert stats["success_rate"] == 0.5
        assert stats["total_time"] == 3.5
        assert stats["stage_completion_stats"]["fix_generation"] == 2
        assert stats["stage_completion_stats"]["backup_creation"] == 1

    # 端到端集成测试
    @pytest.mark.asyncio
    async def test_end_to_end_fix_flow(self, fix_generator, backup_manager, diff_viewer,
                                        fix_executor, temp_project_dir):
        """测试端到端修复流程"""
        file_path = Path(temp_project_dir) / "vulnerable_code.py"
        original_content = file_path.read_text()

        # 1. 定义问题
        issues = [
            {"type": "Hardcoded Credentials", "line": 5, "severity": "high"},
            {"type": "SQL Injection", "line": 8, "severity": "critical"}
        ]

        # 2. 生成修复建议
        fix_request = FixRequest(
            file_path=str(file_path),
            issues=issues,
            original_content=original_content,
            analysis_type="security"
        )

        fix_result = await fix_generator.generate_fixes(fix_request)
        assert fix_result.success is True
        assert len(fix_result.suggestions) > 0

        # 3. 创建备份
        backup_result = backup_manager.create_backup(
            str(file_path),
            reason="end_to_end_test",
            fix_request_id="test_fix"
        )
        assert backup_result.success is True

        # 4. 生成差异
        diff_result = diff_viewer.generate_diff(
            str(file_path),
            original_content,
            fix_result.complete_fixed_content
        )
        assert len(diff_result.chunks) > 0

        # 5. 模拟用户确认
        from src.tools.fix_confirmation import ConfirmationResponse, ConfirmationStatus
        confirmation_response = ConfirmationResponse(
            fix_id="test_fix",
            status=ConfirmationStatus.APPROVED,
            user_message="Test approval"
        )

        # 6. 执行修复
        execution_result = await fix_executor.execute_fix(
            "test_fix",
            str(file_path),
            fix_result,
            confirmation_response,
            backup_result.backup_id
        )

        assert execution_result.success is True
        assert execution_result.status.value == "completed"

        # 7. 验证修复结果
        fixed_content = file_path.read_text()
        assert fixed_content != original_content
        assert os.environ.get('APP_PASSWORD') in fixed_content or "os.environ" in fixed_content

        # 8. 清理 - 恢复原始文件
        backup_manager.restore_backup(backup_result.backup_id)
        restored_content = file_path.read_text()
        assert restored_content == original_content

    def test_cleanup(self, fix_generator, backup_manager, diff_viewer, fix_executor):
        """测试清理"""
        # 大多数组件不需要特殊清理
        pass