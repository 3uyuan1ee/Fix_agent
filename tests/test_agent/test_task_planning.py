"""
测试任务规划逻辑
"""

import pytest
import tempfile
from pathlib import Path

from src.agent.planner import (
    TaskPlanner, AnalysisMode, UserRequest, Task, ExecutionPlan
)


class TestTaskPlanning:
    """测试任务规划逻辑"""

    @pytest.fixture
    def planner(self):
        """任务规划器fixture"""
        return TaskPlanner()

    @pytest.fixture
    def temp_project_dir(self):
        """临时项目目录fixture"""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "test_project"
            project_dir.mkdir()

            # 创建一些测试文件
            (project_dir / "main.py").write_text("def main(): pass")
            (project_dir / "utils.py").write_text("def helper(): pass")
            (project_dir / "config.py").write_text("DEBUG = True")

            # 创建子目录
            (project_dir / "module").mkdir()
            (project_dir / "module" / "processor.py").write_text("class Processor: pass")

            yield str(project_dir)

    def test_static_analysis_tasks_creation(self, planner, temp_project_dir):
        """测试静态分析任务创建"""
        request = UserRequest(
            raw_input="static analysis",
            mode=AnalysisMode.STATIC,
            target_path=temp_project_dir,
            keywords=["test"],
            options={"max_files": 50}
        )

        plan = planner.create_execution_plan(request)

        # 验证计划基本信息
        assert isinstance(plan, ExecutionPlan)
        assert plan.mode == AnalysisMode.STATIC
        assert plan.target_path == temp_project_dir
        assert len(plan.tasks) > 0

        # 验证任务序列
        task_ids = [task.task_id for task in plan.tasks]
        expected_tasks = [
            "static_file_selection",
            "static_ast_analysis",
            "static_pylint_analysis",
            "static_flake8_analysis",
            "static_bandit_analysis",
            "static_report_generation"
        ]

        for expected_task in expected_tasks:
            assert expected_task in task_ids, f"Expected task {expected_task} not found"

        # 验证任务依赖关系
        report_task = next(task for task in plan.tasks if task.task_id == "static_report_generation")
        expected_deps = {"static_ast_analysis", "static_pylint_analysis",
                        "static_flake8_analysis", "static_bandit_analysis"}
        assert set(report_task.dependencies) == expected_deps

    def test_deep_analysis_tasks_creation(self, planner, temp_project_dir):
        """测试深度分析任务创建"""
        request = UserRequest(
            raw_input="deep analysis for performance optimization",
            mode=AnalysisMode.DEEP,
            target_path=temp_project_dir,
            keywords=["performance", "optimize"],
            options={"max_files": 20, "model": "gpt-4"}
        )

        plan = planner.create_execution_plan(request)

        # 验证计划基本信息
        assert isinstance(plan, ExecutionPlan)
        assert plan.mode == AnalysisMode.DEEP
        assert len(plan.tasks) > 0

        # 验证任务序列
        task_ids = [task.task_id for task in plan.tasks]
        expected_tasks = [
            "deep_file_selection",
            "deep_content_analysis",
            "deep_llm_preparation",
            "deep_llm_analysis",
            "deep_result_formatting"
        ]

        for expected_task in expected_tasks:
            assert expected_task in task_ids, f"Expected task {expected_task} not found"

        # 验证LLM分析参数
        llm_task = next(task for task in plan.tasks if task.task_id == "deep_llm_analysis")
        assert llm_task.parameters["model"] == "gpt-4"
        assert llm_task.parameters["temperature"] == 0.3

        # 验证分析类型确定
        prep_task = next(task for task in plan.tasks if task.task_id == "deep_llm_preparation")
        assert prep_task.parameters["analysis_type"] == "performance"

    def test_fix_analysis_tasks_creation(self, planner, temp_project_dir):
        """测试修复分析任务创建"""
        request = UserRequest(
            raw_input="fix security issues",
            mode=AnalysisMode.FIX,
            target_path=temp_project_dir,
            keywords=["security", "vulnerability"],
            options={"severity": "high", "batch": True}
        )

        plan = planner.create_execution_plan(request)

        # 验证计划基本信息
        assert isinstance(plan, ExecutionPlan)
        assert plan.mode == AnalysisMode.FIX
        assert len(plan.tasks) > 0

        # 验证任务序列
        task_ids = [task.task_id for task in plan.tasks]
        expected_tasks = [
            "fix_problem_detection",
            "fix_problem_classification",
            "fix_suggestion_generation",
            "fix_user_confirmation",
            "fix_execution",
            "fix_report_generation"
        ]

        for expected_task in expected_tasks:
            assert expected_task in task_ids, f"Expected task {expected_task} not found"

        # 验证修复参数
        detection_task = next(task for task in plan.tasks if task.task_id == "fix_problem_detection")
        assert detection_task.parameters["severity_threshold"] == "high"

        confirmation_task = next(task for task in plan.tasks if task.task_id == "fix_user_confirmation")
        assert confirmation_task.parameters["allow_batch_confirmation"] == True

    def test_task_priorities(self, planner, temp_project_dir):
        """测试任务优先级设置"""
        request = UserRequest(
            raw_input="static analysis",
            mode=AnalysisMode.STATIC,
            target_path=temp_project_dir
        )

        plan = planner.create_execution_plan(request)

        # 验证优先级递增
        priorities = [task.priority for task in plan.tasks]
        assert priorities == sorted(priorities), "Task priorities should be in ascending order"

        # 验证具体优先级值
        file_selection_task = next(task for task in plan.tasks if task.task_id == "static_file_selection")
        assert file_selection_task.priority == 1

        report_task = next(task for task in plan.tasks if task.task_id == "static_report_generation")
        assert report_task.priority == 4

    def test_task_dependencies_validation(self, planner, temp_project_dir):
        """测试任务依赖关系验证"""
        request = UserRequest(
            raw_input="deep analysis",
            mode=AnalysisMode.DEEP,
            target_path=temp_project_dir
        )

        plan = planner.create_execution_plan(request)

        # 验证所有依赖的任务都存在
        task_ids = {task.task_id for task in plan.tasks}
        for task in plan.tasks:
            for dep in task.dependencies:
                assert dep in task_ids, f"Task {task.task_id} depends on non-existent task {dep}"

        # 验证没有循环依赖
        for task in plan.tasks:
            assert task.task_id not in task.dependencies, f"Task {task.task_id} cannot depend on itself"

    def test_custom_options_integration(self, planner, temp_project_dir):
        """测试自定义选项集成"""
        request = UserRequest(
            raw_input="static analysis with custom settings",
            mode=AnalysisMode.STATIC,
            target_path=temp_project_dir,
            options={
                "max_files": 30,
                "pylint_disable": ["C0111", "R0903"],
                "max_line_length": 120,
                "security_level": "high",
                "output_format": "yaml"
            }
        )

        plan = planner.create_execution_plan(request)

        # 验证自定义选项被正确传递到任务参数中
        file_selection_task = next(task for task in plan.tasks if task.task_id == "static_file_selection")
        assert file_selection_task.parameters["max_files"] == 30

        pylint_task = next(task for task in plan.tasks if task.task_id == "static_pylint_analysis")
        assert pylint_task.parameters["disable_rules"] == ["C0111", "R0903"]

        flake8_task = next(task for task in plan.tasks if task.task_id == "static_flake8_analysis")
        assert flake8_task.parameters["max_line_length"] == 120

        bandit_task = next(task for task in plan.tasks if task.task_id == "static_bandit_analysis")
        assert bandit_task.parameters["severity_level"] == "high"

        report_task = next(task for task in plan.tasks if task.task_id == "static_report_generation")
        assert report_task.parameters["output_format"] == "yaml"

    def test_analysis_type_determination(self, planner):
        """测试分析类型确定逻辑"""
        # 测试架构分析
        request = UserRequest(
            raw_input="analyze architecture",
            mode=AnalysisMode.DEEP,
            keywords=["architecture"],
            intent="架构分析"
        )
        analysis_type = planner._determine_analysis_type(request)
        assert analysis_type == "architecture"

        # 测试性能分析
        request = UserRequest(
            raw_input="optimize performance",
            mode=AnalysisMode.DEEP,
            keywords=["performance"],
            intent="性能优化分析"
        )
        analysis_type = planner._determine_analysis_type(request)
        assert analysis_type == "performance"

        # 测试安全分析
        request = UserRequest(
            raw_input="security check",
            mode=AnalysisMode.DEEP,
            keywords=["security"],
            intent="安全漏洞扫描"
        )
        analysis_type = planner._determine_analysis_type(request)
        assert analysis_type == "security"

        # 测试默认综合分析
        request = UserRequest(
            raw_input="general analysis",
            mode=AnalysisMode.DEEP,
            keywords=["general"],
            intent="通用分析"
        )
        analysis_type = planner._determine_analysis_type(request)
        assert analysis_type == "comprehensive"

    def test_plan_validation_with_tasks(self, planner, temp_project_dir):
        """测试包含任务的计划验证"""
        request = UserRequest(
            raw_input="static analysis",
            mode=AnalysisMode.STATIC,
            target_path=temp_project_dir
        )

        plan = planner.create_execution_plan(request)

        # 验证计划有效性
        is_valid, errors = planner.validate_plan(plan, allow_empty_tasks=False)
        assert is_valid, f"Plan should be valid but got errors: {errors}"
        assert len(errors) == 0

    def test_task_types(self, planner, temp_project_dir):
        """测试任务类型设置"""
        request = UserRequest(
            raw_input="static analysis",
            mode=AnalysisMode.STATIC,
            target_path=temp_project_dir
        )

        plan = planner.create_execution_plan(request)

        # 验证任务类型
        expected_types = {
            "static_file_selection": "file_selection",
            "static_ast_analysis": "ast_analysis",
            "static_pylint_analysis": "pylint_analysis",
            "static_flake8_analysis": "flake8_analysis",
            "static_bandit_analysis": "bandit_analysis",
            "static_report_generation": "report_generation"
        }

        for task in plan.tasks:
            assert task.task_type == expected_types[task.task_id], \
                f"Task {task.task_id} has incorrect type: {task.task_type}"

    def test_plan_metadata(self, planner, temp_project_dir):
        """测试计划元数据"""
        request = UserRequest(
            raw_input="deep analysis with custom options",
            mode=AnalysisMode.DEEP,
            target_path=temp_project_dir,
            keywords=["performance", "optimize"],
            intent="性能优化分析",
            options={"model": "gpt-4", "temperature": 0.5}
        )

        plan = planner.create_execution_plan(request)

        # 验证元数据
        assert "user_request" in plan.metadata
        assert "keywords" in plan.metadata
        assert "intent" in plan.metadata
        assert "options" in plan.metadata

        assert plan.metadata["user_request"] == request.raw_input
        assert plan.metadata["keywords"] == request.keywords
        assert plan.metadata["intent"] == request.intent
        assert plan.metadata["options"] == request.options

    def test_all_modes_task_generation(self, planner, temp_project_dir):
        """测试所有模式的任务生成"""
        modes = [AnalysisMode.STATIC, AnalysisMode.DEEP, AnalysisMode.FIX]

        for mode in modes:
            request = UserRequest(
                raw_input=f"test {mode.value} analysis",
                mode=mode,
                target_path=temp_project_dir
            )

            plan = planner.create_execution_plan(request)

            # 验证每种模式都能生成任务
            assert len(plan.tasks) > 0, f"Mode {mode.value} should generate tasks"
            assert plan.mode == mode, f"Plan mode should be {mode.value}"

            # 验证任务ID的唯一性
            task_ids = [task.task_id for task in plan.tasks]
            assert len(task_ids) == len(set(task_ids)), "Task IDs should be unique"

    def test_empty_request_handling(self, planner, temp_project_dir):
        """测试空请求处理"""
        request = UserRequest(
            raw_input="",
            mode=AnalysisMode.STATIC,
            target_path=temp_project_dir,
            keywords=[],
            options={}
        )

        plan = planner.create_execution_plan(request)

        # 即使是空请求，也应该能生成基础任务
        assert len(plan.tasks) > 0
        assert plan.metadata["user_request"] == ""
        assert plan.metadata["keywords"] == []
        assert plan.metadata["options"] == {}