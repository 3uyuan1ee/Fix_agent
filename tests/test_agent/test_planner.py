"""
测试任务规划器
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch

from src.agent.planner import (
    TaskPlanner, AnalysisMode, UserRequest, Task, ExecutionPlan
)


class TestTaskPlanner:
    """测试任务规划器"""

    @pytest.fixture
    def planner(self):
        """规划器fixture"""
        # 创建临时配置
        config_data = {'planner': {'max_files': 100}}

        with patch('src.agent.planner.get_config_manager') as mock_config:
            mock_config.return_value.get_section.return_value = config_data
            return TaskPlanner()

    def test_initialization(self, planner):
        """测试初始化"""
        assert planner is not None
        assert hasattr(planner, 'logger')
        assert hasattr(planner, 'config_manager')
        assert isinstance(planner.static_keywords, list)
        assert isinstance(planner.deep_keywords, list)
        assert isinstance(planner.fix_keywords, list)

    def test_parse_user_request_static_mode(self, planner):
        """测试解析静态分析模式用户请求"""
        user_input = "static analysis for security issues"
        current_path = "/test/path"

        request = planner.parse_user_request(user_input, current_path)

        assert isinstance(request, UserRequest)
        assert request.raw_input == user_input
        assert request.mode == AnalysisMode.STATIC
        assert "security" in request.keywords
        assert request.intent != ""

    def test_parse_user_request_deep_mode(self, planner):
        """测试解析深度分析模式用户请求"""
        user_input = "deep comprehensive analysis of performance"
        current_path = "/test/path"

        request = planner.parse_user_request(user_input, current_path)

        assert request.mode == AnalysisMode.DEEP
        assert "performance" in request.keywords

    def test_parse_user_request_fix_mode(self, planner):
        """测试解析修复模式用户请求"""
        user_input = "fix the bugs in code"
        current_path = "/test/path"

        request = planner.parse_user_request(user_input, current_path)

        assert request.mode == AnalysisMode.FIX
        assert "bug" in request.keywords

    def test_parse_user_request_with_path(self, planner):
        """测试解析包含路径的用户请求"""
        user_input = "analyze code in /path/to/project"
        current_path = "/test/path"

        request = planner.parse_user_request(user_input, current_path)

        assert "/path/to/project" in request.target_path or request.target_path != current_path

    def test_parse_user_request_with_options(self, planner):
        """测试解析包含选项的用户请求"""
        user_input = "analyze --verbose --max-files=50 --auto-fix"
        current_path = "/test/path"

        request = planner.parse_user_request(user_input, current_path)

        assert request.options.get("verbose") is True
        assert request.options.get("max-files") == 50
        assert request.options.get("auto-fix") is True

    def test_parse_user_request_with_relative_path(self, planner):
        """测试解析相对路径"""
        user_input = "analyze ./src"
        current_path = "/test/path"

        request = planner.parse_user_request(user_input, current_path)

        assert "src" in request.target_path

    def test_create_execution_plan_static_mode(self, planner):
        """测试创建静态分析执行计划"""
        request = UserRequest(
            raw_input="static analysis",
            mode=AnalysisMode.STATIC,
            target_path="/test/path"
        )

        plan = planner.create_execution_plan(request)

        assert isinstance(plan, ExecutionPlan)
        assert plan.mode == AnalysisMode.STATIC
        assert plan.target_path == "/test/path"
        assert isinstance(plan.tasks, list)
        assert plan.plan_id.startswith("plan_")
        assert plan.metadata['user_request'] == "static analysis"

    def test_create_execution_plan_deep_mode(self, planner):
        """测试创建深度分析执行计划"""
        request = UserRequest(
            raw_input="deep analysis",
            mode=AnalysisMode.DEEP,
            target_path="/test/path"
        )

        plan = planner.create_execution_plan(request)

        assert isinstance(plan, ExecutionPlan)
        assert plan.mode == AnalysisMode.DEEP
        assert isinstance(plan.tasks, list)

    def test_create_execution_plan_fix_mode(self, planner):
        """测试创建修复执行计划"""
        request = UserRequest(
            raw_input="fix issues",
            mode=AnalysisMode.FIX,
            target_path="/test/path"
        )

        plan = planner.create_execution_plan(request)

        assert isinstance(plan, ExecutionPlan)
        assert plan.mode == AnalysisMode.FIX
        assert isinstance(plan.tasks, list)

    def test_validate_plan_valid(self, planner):
        """测试验证有效计划"""
        # 使用临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            tasks = [
                Task(task_id="task1", task_type="scan", description="Scan files"),
                Task(task_id="task2", task_type="analyze", description="Analyze results", dependencies=["task1"])
            ]
            plan = ExecutionPlan(
                plan_id="test_plan",
                mode=AnalysisMode.STATIC,
                target_path=temp_dir,
                tasks=tasks
            )

            is_valid, errors = planner.validate_plan(plan)

            assert is_valid is True
            assert len(errors) == 0

    def test_validate_plan_invalid_path(self, planner):
        """测试验证无效路径的计划"""
        tasks = [Task(task_id="task1", task_type="scan", description="Scan files")]
        plan = ExecutionPlan(
            plan_id="test_plan",
            mode=AnalysisMode.STATIC,
            target_path="/nonexistent/path",
            tasks=tasks
        )

        is_valid, errors = planner.validate_plan(plan)

        assert is_valid is False
        assert len(errors) > 0
        assert any("does not exist" in error for error in errors)

    def test_validate_plan_no_tasks(self, planner):
        """测试验证无任务的计划"""
        plan = ExecutionPlan(
            plan_id="test_plan",
            mode=AnalysisMode.STATIC,
            target_path="/test",
            tasks=[]
        )

        is_valid, errors = planner.validate_plan(plan)

        assert is_valid is False
        assert any("No tasks" in error for error in errors)

    def test_validate_plan_invalid_dependency(self, planner):
        """测试验证无效依赖的计划"""
        tasks = [
            Task(task_id="task1", task_type="scan", description="Scan files", dependencies=["nonexistent"])
        ]
        plan = ExecutionPlan(
            plan_id="test_plan",
            mode=AnalysisMode.STATIC,
            target_path="/test",
            tasks=tasks
        )

        is_valid, errors = planner.validate_plan(plan)

        assert is_valid is False
        assert any("depends on non-existent task" in error for error in errors)

    def test_validate_plan_invalid_priority(self, planner):
        """测试验证无效优先级的计划"""
        tasks = [
            Task(task_id="task1", task_type="scan", description="Scan files", priority=0)
        ]
        plan = ExecutionPlan(
            plan_id="test_plan",
            mode=AnalysisMode.STATIC,
            target_path="/test",
            tasks=tasks
        )

        is_valid, errors = planner.validate_plan(plan)

        assert is_valid is False
        assert any("invalid priority" in error for error in errors)

    def test_detect_analysis_mode_static(self, planner):
        """测试检测静态分析模式"""
        mode = planner._detect_analysis_mode("static analysis please")
        assert mode == AnalysisMode.STATIC

        mode = planner._detect_analysis_mode("quick check")
        assert mode == AnalysisMode.STATIC

        mode = planner._detect_analysis_mode("基础分析")
        assert mode == AnalysisMode.STATIC

    def test_detect_analysis_mode_deep(self, planner):
        """测试检测深度分析模式"""
        mode = planner._detect_analysis_mode("deep analysis needed")
        assert mode == AnalysisMode.DEEP

        mode = planner._detect_analysis_mode("comprehensive review")
        assert mode == AnalysisMode.DEEP

        mode = planner._detect_analysis_mode("详细检查")
        assert mode == AnalysisMode.DEEP

    def test_detect_analysis_mode_fix(self, planner):
        """测试检测修复模式"""
        mode = planner._detect_analysis_mode("fix the issues")
        assert mode == AnalysisMode.FIX

        mode = planner._detect_analysis_mode("repair this code")
        assert mode == AnalysisMode.FIX

        mode = planner._detect_analysis_mode("修复问题")
        assert mode == AnalysisMode.FIX

    def test_extract_target_path_unix(self, planner):
        """测试提取Unix路径"""
        path = planner._extract_target_path("analyze /home/user/project", "/current")
        assert "/home/user/project" in path

    def test_extract_target_path_windows(self, planner):
        """测试提取Windows路径"""
        path = planner._extract_target_path("analyze C:\\Users\\user\\project", "/current")
        assert "C:" in path

    def test_extract_target_path_relative(self, planner):
        """测试提取相对路径"""
        path = planner._extract_target_path("analyze ./src", "/current")
        assert "src" in path

    def test_extract_options(self, planner):
        """测试提取选项"""
        options = planner._extract_options("analyze --verbose --max-files=100 --debug=false")

        assert options.get("verbose") is True
        assert options.get("max-files") == 100
        assert options.get("debug") is False

    def test_extract_keywords(self, planner):
        """测试提取关键词"""
        keywords = planner._extract_keywords("check security and performance issues")

        assert "security" in keywords
        assert "performance" in keywords

        keywords = planner._extract_keywords("检查安全漏洞")
        assert "安全" in keywords
        assert "漏洞" in keywords

    def test_analyze_intent_static_security(self, planner):
        """测试分析静态安全分析意图"""
        intent = planner._analyze_intent("static security analysis", AnalysisMode.STATIC)
        assert "安全" in intent or "security" in intent.lower()

    def test_analyze_intent_static_style(self, planner):
        """测试分析代码风格检查意图"""
        intent = planner._analyze_intent("static style check", AnalysisMode.STATIC)
        assert "风格" in intent or "style" in intent.lower()

    def test_analyze_intent_deep_performance(self, planner):
        """测试分析性能优化意图"""
        intent = planner._analyze_intent("deep performance analysis", AnalysisMode.DEEP)
        assert "性能" in intent or "performance" in intent.lower()

    def test_get_supported_modes(self, planner):
        """测试获取支持的模式"""
        modes = planner.get_supported_modes()
        assert "static" in modes
        assert "deep" in modes
        assert "fix" in modes

    def test_get_mode_description(self, planner):
        """测试获取模式描述"""
        desc = planner.get_mode_description("static")
        assert "静态分析" in desc

        desc = planner.get_mode_description("deep")
        assert "深度分析" in desc

        desc = planner.get_mode_description("fix")
        assert "修复" in desc

    def test_task_dataclass(self):
        """测试Task数据类"""
        task = Task(
            task_id="test_task",
            task_type="scan",
            description="Test scan task",
            priority=2,
            dependencies=["task1"],
            parameters={"option": "value"}
        )

        assert task.task_id == "test_task"
        assert task.task_type == "scan"
        assert task.description == "Test scan task"
        assert task.priority == 2
        assert task.dependencies == ["task1"]
        assert task.parameters["option"] == "value"
        assert task.status == "pending"

    def test_user_request_dataclass(self):
        """测试UserRequest数据类"""
        request = UserRequest(
            raw_input="test input",
            mode=AnalysisMode.STATIC,
            target_path="/test",
            keywords=["test"],
            intent="test intent"
        )

        assert request.raw_input == "test input"
        assert request.mode == AnalysisMode.STATIC
        assert request.target_path == "/test"
        assert request.keywords == ["test"]
        assert request.intent == "test intent"

    def test_execution_plan_dataclass(self):
        """测试ExecutionPlan数据类"""
        tasks = [Task(task_id="task1", task_type="scan", description="Test task")]
        plan = ExecutionPlan(
            plan_id="test_plan",
            mode=AnalysisMode.STATIC,
            target_path="/tmp/test",
            tasks=tasks,
            metadata={"test": "value"}
        )

        assert plan.plan_id == "test_plan"
        assert plan.mode == AnalysisMode.STATIC
        assert plan.target_path == "/tmp/test"
        assert len(plan.tasks) == 1
        assert plan.metadata["test"] == "value"
        assert plan.created_at > 0