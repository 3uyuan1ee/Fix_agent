#!/usr/bin/env python3
"""
T022 模式切换和路由单元测试
验证ModeRecognizer和RequestRouter的功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional

# 导入被测试的模块
from src.agent.mode_router import (
    ModeRecognizer, RequestRouter, RouteRequest, RouteResult,
    AnalysisMode
)
from src.agent.orchestrator import Session, SessionState, MessageRole as OrchestratorMessageRole
from src.agent.planner import UserRequest, Task, ExecutionPlan


class TestModeRecognizer:
    """测试模式识别器"""

    def setup_method(self):
        """测试前的设置"""
        self.recognizer = ModeRecognizer()

    def test_recognize_static_analysis_mode(self):
        """测试识别静态分析模式"""
        test_cases = [
            ("静态分析 src/ 目录", AnalysisMode.STATIC),
            ("对 utils.py 进行代码扫描", AnalysisMode.STATIC),
            ("使用pylint检查代码质量", AnalysisMode.STATIC),
            ("运行静态代码分析工具", AnalysisMode.STATIC),
            ("代码风格检查", AnalysisMode.STATIC),
            ("安全漏洞扫描", AnalysisMode.STATIC)
        ]

        for user_input, expected_mode in test_cases:
            mode, confidence = self.recognizer.recognize_mode(user_input)

            assert mode == expected_mode, f"输入 '{user_input}' 应识别为 {expected_mode.value}"
            assert confidence > 0.5, f"输入 '{user_input}' 置信度过低: {confidence}"

    def test_recognize_deep_analysis_mode(self):
        """测试识别深度分析模式"""
        test_cases = [
            ("深度分析这个文件的架构", AnalysisMode.DEEP),
            ("详细解释这段代码的设计思路", AnalysisMode.DEEP),
            ("分析项目的整体架构设计", AnalysisMode.DEEP),
            ("解释这个模块的实现原理", AnalysisMode.DEEP),
            ("代码逻辑分析", AnalysisMode.DEEP),
            ("架构设计评审", AnalysisMode.DEEP)
        ]

        for user_input, expected_mode in test_cases:
            mode, confidence = self.recognizer.recognize_mode(user_input)

            assert mode == expected_mode, f"输入 '{user_input}' 应识别为 {expected_mode.value}"
            assert confidence > 0.5, f"输入 '{user_input}' 置信度过低: {confidence}"

    def test_recognize_fix_mode(self):
        """测试识别修复模式"""
        test_cases = [
            ("修复 src/utils/config.py 中的bug", AnalysisMode.FIX),
            ("解决代码中的安全问题", AnalysisMode.FIX),
            ("修复这个函数的逻辑错误", AnalysisMode.FIX),
            ("改正代码缺陷", AnalysisMode.FIX),
            ("处理异常情况", AnalysisMode.FIX),
            ("优化这段代码", AnalysisMode.FIX)
        ]

        for user_input, expected_mode in test_cases:
            mode, confidence = self.recognizer.recognize_mode(user_input)

            assert mode == expected_mode, f"输入 '{user_input}' 应识别为 {expected_mode.value}"
            assert confidence > 0.5, f"输入 '{user_input}' 置信度过低: {confidence}"

    def test_command_pattern_recognition(self):
        """测试命令模式识别"""
        test_cases = [
            ("/static 分析 src/", AnalysisMode.STATIC),
            ("/deep 分析架构", AnalysisMode.DEEP),
            ("/fix 修复bug", AnalysisMode.FIX),
            ("/analyze 扫描代码", AnalysisMode.STATIC),
            ("/review 深度检查", AnalysisMode.DEEP),
            ("/repair 解决问题", AnalysisMode.FIX)
        ]

        for user_input, expected_mode in test_cases:
            mode, confidence = self.recognizer.recognize_mode(user_input)

            assert mode == expected_mode, f"命令 '{user_input}' 应识别为 {expected_mode.value}"
            assert confidence > 0.9, f"命令 '{user_input}' 置信度应很高: {confidence}"

    def test_force_mode_override(self):
        """测试强制模式覆盖"""
        user_input = "静态分析代码"  # 正常应识别为STATIC

        # 强制设为深度分析
        mode, confidence = self.recognizer.recognize_mode(
            user_input,
            force_mode=AnalysisMode.DEEP
        )

        assert mode == AnalysisMode.DEEP
        assert confidence == 1.0

    def test_context_based_recognition(self):
        """测试基于上下文的识别"""
        # 创建模拟会话
        session = Mock(spec=Session)
        session.messages = []
        session.current_request = Mock()
        session.current_request.mode = AnalysisMode.STATIC

        # 添加相关消息历史
        for role, content in [
            (OrchestratorMessageRole.USER, "我想进行静态分析"),
            (OrchestratorMessageRole.ASSISTANT, "好的，我来帮您进行静态分析"),
            (OrchestratorMessageRole.USER, "继续分析")
        ]:
            message = Mock()
            message.role = role
            message.content = content
            session.messages.append(message)

        mode, confidence = self.recognizer.recognize_mode(
            "继续分析",
            session=session
        )

        # 应识别为静态分析（基于上下文）
        assert mode == AnalysisMode.STATIC
        assert confidence > 0.5

    def test_low_confidence_fallback(self):
        """测试低置信度回退"""
        # 模糊的输入
        ambiguous_input = "帮我看看这个文件"

        mode, confidence = self.recognizer.recognize_mode(ambiguous_input)

        # 置信度应该较低
        assert confidence < 0.5
        # 但仍应给出某种模式（默认回退）
        assert mode in [AnalysisMode.STATIC, AnalysisMode.DEEP, AnalysisMode.FIX]

    def test_invalid_input_handling(self):
        """测试无效输入处理"""
        invalid_inputs = [
            "",  # 空字符串
            "   ",  # 只有空格
            "hello",  # 英文无意义输入
        ]

        for invalid_input in invalid_inputs:
            mode, confidence = self.recognizer.recognize_mode(invalid_input)

            # 应该回退到静态分析模式
            assert mode == AnalysisMode.STATIC
            # 置信度应该很低
            assert confidence <= 0.3

    def test_get_mode_keywords(self):
        """测试获取模式关键词"""
        static_keywords = self.recognizer.get_mode_keywords(AnalysisMode.STATIC)
        deep_keywords = self.recognizer.get_mode_keywords(AnalysisMode.DEEP)
        fix_keywords = self.recognizer.get_mode_keywords(AnalysisMode.FIX)

        # 验证关键词不为空
        assert len(static_keywords) > 0
        assert len(deep_keywords) > 0
        assert len(fix_keywords) > 0

        # 验证关键词类型
        assert all(isinstance(k, str) for k in static_keywords)
        assert all(isinstance(k, str) for k in deep_keywords)
        assert all(isinstance(k, str) for k in fix_keywords)

        # 验证预期关键词存在
        assert "静态" in static_keywords
        assert "深度" in deep_keywords
        assert "修复" in fix_keywords


class TestRequestRouter:
    """测试请求路由器"""

    def setup_method(self):
        """测试前的设置"""
        # 创建模拟组件
        self.mock_orchestrator = Mock()
        self.mock_task_planner = Mock()
        self.mock_execution_engine = Mock()

        # 创建路由器
        self.router = RequestRouter(
            orchestrator=self.mock_orchestrator,
            task_planner=self.mock_task_planner,
            execution_engine=self.mock_execution_engine
        )

    def test_route_static_analysis_direct(self):
        """测试静态分析模式直接路由"""
        # 创建路由请求
        request = RouteRequest(
            user_input="静态分析 src/ 目录",
            session=None,
            context={"target_path": "src/"},
            options={}
        )

        # 模拟任务规划器返回
        mock_plan = Mock(spec=ExecutionPlan)
        mock_plan.plan_id = "plan_001"
        mock_plan.tasks = [
            Mock(spec=Task),
            Mock(spec=Task)
        ]
        self.mock_task_planner.create_execution_plan.return_value = mock_plan

        # 模拟执行引擎返回
        mock_result = Mock()
        mock_result.success = True
        mock_result.output = "静态分析完成"
        self.mock_execution_engine.execute_plan.return_value = mock_result

        # 执行路由
        result = self.router.route_request(request)

        # 验证结果
        assert isinstance(result, RouteResult)
        assert result.success is True
        assert result.execution_method == "direct"
        assert result.response_message == "静态分析完成"
        assert result.execution_plan.plan_id == "plan_001"

        # 验证调用
        self.mock_task_planner.create_execution_plan.assert_called_once()
        self.mock_execution_engine.execute_plan.assert_called_once_with(mock_plan)

    def test_route_deep_analysis_interactive(self):
        """测试深度分析模式交互路由"""
        # 创建模拟会话
        session = Mock(spec=Session)
        session.session_id = "session_001"

        # 创建路由请求
        request = RouteRequest(
            user_input="深度分析这个文件的架构",
            session=session,
            context={"target_file": "src/utils/config.py"},
            options={}
        )

        # 执行路由
        result = self.router.route_request(request)

        # 验证结果
        assert isinstance(result, RouteResult)
        assert result.success is True
        assert result.strategy == RouteStrategy.INTERACTIVE
        assert "对话交互" in result.response
        assert result.requires_user_input is True

        # 验证会话状态转换
        session.transition_state.assert_called_once()

        # 验证添加系统消息
        session.add_message.assert_called()

    def test_route_fix_mode_confirmation(self):
        """测试修复模式确认路由"""
        # 创建模拟会话
        session = Mock(spec=Session)
        session.session_id = "session_002"

        # 创建路由请求
        request = RouteRequest(
            user_input="修复 src/utils/config.py 中的安全问题",
            session=session,
            context={"issue_type": "security"},
            options={}
        )

        # 执行路由
        result = self.router.route_request(request)

        # 验证结果
        assert isinstance(result, RouteResult)
        assert result.success is True
        assert result.strategy == RouteStrategy.CONFIRMATION
        assert "确认" in result.response
        assert result.requires_confirmation is True

        # 验证添加确认消息
        session.add_message.assert_called()
        assert any("确认" in str(call) for call in session.add_message.call_args_list)

    def test_route_with_session_context(self):
        """测试带会话上下文的路由"""
        # 创建模拟会话，当前为静态分析模式
        session = Mock(spec=Session)
        session.session_id = "session_003"
        session.current_request = Mock()
        session.current_request.mode = AnalysisMode.STATIC

        # 创建路由请求
        request = RouteRequest(
            user_input="继续分析",
            session=session,
            context={},
            options={}
        )

        # 模拟执行结果
        mock_plan = Mock(spec=ExecutionPlan)
        mock_plan.plan_id = "plan_002"
        self.mock_task_planner.create_execution_plan.return_value = mock_plan

        mock_result = Mock()
        mock_result.success = True
        mock_result.output = "继续静态分析完成"
        self.mock_execution_engine.execute_plan.return_value = mock_result

        # 执行路由
        result = self.router.route_request(request)

        # 验证使用了会话上下文
        assert result.success is True
        assert result.strategy == RouteStrategy.DIRECT
        assert result.context.get("continued_mode") == AnalysisMode.STATIC.value

    def test_route_error_handling(self):
        """测试路由错误处理"""
        # 创建路由请求
        request = RouteRequest(
            user_input="无效输入",
            session=None,
            context={},
            options={}
        )

        # 模拟规划器抛出异常
        self.mock_task_planner.create_execution_plan.side_effect = Exception("规划失败")

        # 执行路由
        result = self.router.route_request(request)

        # 验证错误处理
        assert isinstance(result, RouteResult)
        assert result.success is False
        assert "规划失败" in result.error_message
        assert result.error_type == "execution_plan_failed"

    def test_route_with_force_mode(self):
        """测试强制模式路由"""
        # 创建路由请求，强制使用深度分析模式
        request = RouteRequest(
            user_input="静态分析代码",  # 正常应识别为静态
            session=None,
            context={},
            options={"force_mode": AnalysisMode.DEEP}
        )

        # 执行路由
        result = self.router.route_request(request)

        # 验证使用了强制模式
        assert isinstance(result, RouteResult)
        assert result.success is True
        assert result.strategy == RouteStrategy.INTERACTIVE  # 深度分析使用交互策略
        assert result.detected_mode == AnalysisMode.DEEP

    def test_update_route_statistics(self):
        """测试路由统计更新"""
        # 创建路由请求
        request = RouteRequest(
            user_input="测试请求",
            session=None,
            context={},
            options={}
        )

        # 模拟成功路由
        mock_plan = Mock(spec=ExecutionPlan)
        self.mock_task_planner.create_execution_plan.return_value = mock_plan
        mock_result = Mock()
        mock_result.success = True
        self.mock_execution_engine.execute_plan.return_value = mock_result

        # 执行多次路由
        for i in range(5):
            result = self.router.route_request(request)
            assert result.success is True

        # 验证统计信息
        stats = self.router.get_route_statistics()
        assert stats["total_routes"] == 5
        assert stats["successful_routes"] == 5
        assert stats["success_rate"] == 1.0
        assert "routes_by_strategy" in stats
        assert "routes_by_mode" in stats

    def test_get_supported_modes(self):
        """测试获取支持的模式"""
        supported_modes = self.router.get_supported_modes()

        assert len(supported_modes) == 3
        assert AnalysisMode.STATIC in supported_modes
        assert AnalysisMode.DEEP in supported_modes
        assert AnalysisMode.FIX in supported_modes

        # 验证返回的模式信息
        for mode_info in supported_modes:
            assert "mode" in mode_info
            assert "description" in mode_info
            assert "strategy" in mode_info

    def test_validate_route_request(self):
        """测试路由请求验证"""
        # 有效请求
        valid_request = RouteRequest(
            user_input="测试请求",
            session=None,
            context={},
            options={}
        )

        assert self.router._validate_route_request(valid_request) is True

        # 无效请求（空用户输入）
        invalid_request = RouteRequest(
            user_input="",
            session=None,
            context={},
            options={}
        )

        assert self.router._validate_route_request(invalid_request) is False


class TestRouteRequestAndResult:
    """测试路由请求和结果数据类"""

    def test_route_request_creation(self):
        """测试路由请求创建"""
        request = RouteRequest(
            user_input="测试输入",
            session=None,
            context={"key": "value"},
            options={"option1": True}
        )

        assert request.user_input == "测试输入"
        assert request.session is None
        assert request.context == {"key": "value"}
        assert request.options == {"option1": True}
        assert request.timestamp is not None

    def test_route_result_creation(self):
        """测试路由结果创建"""
        result = RouteResult(
            success=True,
            strategy=RouteStrategy.DIRECT,
            response="执行成功",
            detected_mode=AnalysisMode.STATIC,
            execution_plan_id="plan_001"
        )

        assert result.success is True
        assert result.strategy == RouteStrategy.DIRECT
        assert result.response == "执行成功"
        assert result.detected_mode == AnalysisMode.STATIC
        assert result.execution_plan_id == "plan_001"
        assert result.timestamp is not None
        assert result.error_message is None
        assert result.error_type is None

    def test_route_result_error(self):
        """测试路由结果错误"""
        result = RouteResult(
            success=False,
            strategy=RouteStrategy.DIRECT,
            response="执行失败",
            error_message="模拟错误",
            error_type="test_error"
        )

        assert result.success is False
        assert result.error_message == "模拟错误"
        assert result.error_type == "test_error"
        assert result.execution_plan_id is None


class TestIntegrationScenarios:
    """测试集成场景"""

    def setup_method(self):
        """测试前的设置"""
        self.mock_orchestrator = Mock()
        self.mock_task_planner = Mock()
        self.mock_execution_engine = Mock()

        self.router = RequestRouter(
            orchestrator=self.mock_orchestrator,
            task_planner=self.mock_task_planner,
            execution_engine=self.mock_execution_engine
        )

    def test_static_analysis_workflow(self):
        """测试完整的静态分析工作流"""
        # 模拟用户请求静态分析
        request = RouteRequest(
            user_input="/static 分析 src/ 目录",
            session=None,
            context={"target_path": "src/"},
            options={}
        )

        # 模拟执行计划
        mock_plan = Mock(spec=ExecutionPlan)
        mock_plan.plan_id = "static_plan_001"
        mock_plan.tasks = [Mock() for _ in range(3)]  # 3个任务

        self.mock_task_planner.create_execution_plan.return_value = mock_plan

        # 模拟执行结果
        mock_result = Mock()
        mock_result.success = True
        mock_result.output = "静态分析完成，发现3个问题"
        mock_result.task_results = [Mock() for _ in range(3)]

        self.mock_execution_engine.execute_plan.return_value = mock_result

        # 执行路由
        result = self.router.route_request(request)

        # 验证完整工作流
        assert result.success is True
        assert result.strategy == RouteStrategy.DIRECT
        assert result.detected_mode == AnalysisMode.STATIC
        assert "静态分析完成" in result.response

        # 验证调用顺序
        self.mock_task_planner.create_execution_plan.assert_called_once()
        self.mock_execution_engine.execute_plan.assert_called_once_with(mock_plan)

    def test_deep_analysis_workflow(self):
        """测试完整的深度分析工作流"""
        # 创建模拟会话
        session = Mock(spec=Session)
        session.session_id = "deep_session_001"

        request = RouteRequest(
            user_input="深度分析项目的架构设计",
            session=session,
            context={"analysis_type": "architecture"},
            options={}
        )

        # 执行路由
        result = self.router.route_request(request)

        # 验证深度分析工作流
        assert result.success is True
        assert result.strategy == RouteStrategy.INTERACTIVE
        assert result.detected_mode == AnalysisMode.DEEP
        assert result.requires_user_input is True

        # 验证会话状态被设置
        session.transition_state.assert_called_once()

        # 验证系统消息被添加
        session.add_message.assert_called()

    def test_fix_mode_workflow(self):
        """测试完整的修复模式工作流"""
        # 创建模拟会话
        session = Mock(spec=Session)
        session.session_id = "fix_session_001"

        request = RouteRequest(
            user_input="修复安全漏洞",
            session=session,
            context={"issue_type": "security", "target_file": "src/auth.py"},
            options={}
        )

        # 执行路由
        result = self.router.route_request(request)

        # 验证修复模式工作流
        assert result.success is True
        assert result.strategy == RouteStrategy.CONFIRMATION
        assert result.detected_mode == AnalysisMode.FIX
        assert result.requires_confirmation is True

        # 验证确认消息被添加
        session.add_message.assert_called()

    def test_mode_continuity_workflow(self):
        """测试模式连续性工作流"""
        # 创建会话，已有静态分析上下文
        session = Mock(spec=Session)
        session.session_id = "continuity_session_001"
        session.current_request = Mock()
        session.current_request.mode = AnalysisMode.STATIC

        # 第一次请求
        first_request = RouteRequest(
            user_input="静态分析 src/utils",
            session=session,
            context={},
            options={}
        )

        mock_plan = Mock(spec=ExecutionPlan)
        mock_plan.plan_id = "plan_001"
        self.mock_task_planner.create_execution_plan.return_value = mock_plan

        mock_result = Mock()
        mock_result.success = True
        mock_result.output = "第一次分析完成"
        self.mock_execution_engine.execute_plan.return_value = mock_result

        first_result = self.router.route_request(first_request)
        assert first_result.success is True

        # 第二次请求（继续相同模式）
        second_request = RouteRequest(
            user_input="继续分析",
            session=session,
            context={},
            options={}
        )

        mock_plan.plan_id = "plan_002"
        mock_result.output = "继续分析完成"

        second_result = self.router.route_request(second_request)

        # 验证模式连续性
        assert second_result.success is True
        assert second_result.context.get("continued_mode") == AnalysisMode.STATIC.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])