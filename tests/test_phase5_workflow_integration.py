#!/usr/bin/env python3
"""
Phase 5 工作流集成测试
测试完整的B→C→D→E→F/G→H→I→J/K→L→B/M工作流程
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json

from src.tools.workflow_flow_state_manager import WorkflowFlowStateManager, WorkflowNode, WorkflowSession
from src.tools.problem_skip_processor import ProblemSkipProcessor, SkipReason
from src.tools.verification_static_analyzer import VerificationStaticAnalyzer
from src.tools.ai_dynamic_analysis_caller import AIDynamicAnalysisCaller
from src.tools.fix_verification_aggregator import FixVerificationAggregator
from src.tools.verification_result_displayer import VerificationResultDisplayer, DisplayFormat
from src.tools.user_verification_decision_processor import UserVerificationDecisionProcessor, VerificationDecisionType
from src.tools.problem_solution_processor import ProblemSolutionProcessor
from src.tools.reatalysis_trigger import ReanalysisTrigger
from src.tools.problem_status_checker import ProblemStatusChecker
from src.tools.workflow_completion_processor import WorkflowCompletionProcessor
from src.tools.project_analysis_types import AIDetectedProblem, AIFixSuggestion, StaticAnalysisResult, Issue, IssueSeverity, IssueType


class TestPhase5WorkflowIntegration:
    """Phase 5 工作流集成测试类"""

    def __init__(self):
        """初始化测试环境"""
        self.temp_dir = None
        self.state_manager = None
        self.test_session = None

    def setup_test_environment(self):
        """设置测试环境"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp(prefix="phase5_test_")

        # 初始化各个组件
        self.state_manager = WorkflowFlowStateManager()

        # 创建测试会话
        self.test_session = self._create_test_session()

        # 保存会话并添加到活跃会话
        self.state_manager.active_sessions[self.test_session.session_id] = self.test_session

        # 设置工作流状态到节点G（跳过问题）
        self.test_session.current_node = WorkflowNode.SKIP_PROBLEM

    def cleanup_test_environment(self):
        """清理测试环境"""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def _create_test_session(self) -> WorkflowSession:
        """创建测试会话"""
        session = WorkflowSession(
            session_id="test_session_001",
            project_path="/test/project",
            selected_files=["test_file.py"],
            created_at=datetime.now()
        )

        # 添加测试问题
        from src.tools.workflow_data_types import ProblemType, SeverityLevel, FixType
        test_problem = AIDetectedProblem(
            problem_id="issue_001",
            file_path="test_file.py",
            line_number=25,
            problem_type=ProblemType.SECURITY,
            severity=SeverityLevel.HIGH,
            description="SQL注入漏洞风险",
            code_snippet="query = f'SELECT * FROM users WHERE id = {user_id}'",
            confidence=0.9,
            reasoning="使用字符串格式化构建SQL查询存在注入风险"
        )
        session.problems_detected = [test_problem.to_dict()]
        session.pending_problems = ["issue_001"]

        # 添加测试修复建议
        test_suggestion = AIFixSuggestion(
            suggestion_id="suggestion_001",
            problem_id="issue_001",
            file_path="test_file.py",
            line_number=25,
            original_code="query = f'SELECT * FROM users WHERE id = {user_id}'",
            suggested_code="query = 'SELECT * FROM users WHERE id = %s'",
            explanation="使用参数化查询防止SQL注入",
            reasoning="参数化查询是防止SQL注入的标准做法",
            confidence=0.95,
            side_effects=["需要确保数据库连接器支持参数化查询"]
        )
        session.fix_suggestions = [test_suggestion.to_dict()]

        return session

    def test_node_g_problem_skip_processor(self):
        """测试节点G: 问题跳过处理器"""
        print("\n=== 测试节点G: 问题跳过处理器 ===")

        skip_processor = ProblemSkipProcessor()
        # 使用测试的状态管理器
        skip_processor.state_manager = self.state_manager

        # 测试跳过决策处理
        result = skip_processor.process_skip_decision(
            session_id=self.test_session.session_id,
            issue_id="issue_001",
            skip_reason=SkipReason.FALSE_POSITIVE,
            user_comment="这是误报，实际代码是安全的"
        )

        assert result["success"], "跳过处理应该成功"
        assert result["next_node"] == "CHECK_REMAINING", "应该转换到检查剩余问题节点"

        # 验证会话状态更新
        updated_session = self.state_manager.get_session(self.test_session.session_id)
        assert "issue_001" not in updated_session.pending_problems, "问题应该从待处理列表中移除"

        print("✅ 节点G测试通过")

    def test_node_h_verification_components(self):
        """测试节点H: 修复验证组件"""
        print("\n=== 测试节点H: 修复验证组件 ===")

        # 创建测试用的静态分析结果
        original_analysis = StaticAnalysisResult(
            file_path="test_file.py",
            issues=[
                Issue(
                    issue_id="issue_001",
                    file_path="test_file.py",
                    line=25,
                    issue_type=IssueType.SECURITY,
                    severity=IssueSeverity.ERROR,
                    message="SQL注入漏洞风险",
                    code_snippet="query = f'SELECT * FROM users WHERE id = {user_id}'"
                )
            ],
            execution_time=2.5,
            summary={"total_issues": 1},
            success=True
        )

        # 测试静态验证分析器
        print("  测试T014.1: 验证静态分析执行器")
        static_analyzer = VerificationStaticAnalyzer()

        # 注意：这里由于实际文件不存在，会创建空的结果
        verification_report = static_analyzer.verify_fix_with_static_analysis(
            session_id=self.test_session.session_id,
            suggestion_id="suggestion_001",
            original_analysis=original_analysis,
            modified_file_path="test_file.py"
        )

        assert verification_report is not None, "验证报告不应该为空"
        print("  ✅ T014.1测试通过")

        # 测试AI动态分析调用器
        print("  测试T014.2: AI动态分析调用器")
        ai_caller = AIDynamicAnalysisCaller()

        # 由于需要实际的AI调用，这里创建模拟结果
        ai_result = ai_caller.perform_ai_dynamic_analysis(
            session_id=self.test_session.session_id,
            suggestion_id="suggestion_001",
            original_problem={
                "issue_type": "security",
                "severity": "error",
                "description": "SQL注入漏洞风险"
            },
            fix_suggestion={
                "file_path": "test_file.py",
                "suggested_code": "query = 'SELECT * FROM users WHERE id = %s'",
                "explanation": "使用参数化查询防止SQL注入"
            },
            static_verification_report=verification_report,
            before_code="query = f'SELECT * FROM users WHERE id = {user_id}'",
            after_code="query = 'SELECT * FROM users WHERE id = %s'"
        )

        assert ai_result is not None, "AI分析结果不应该为空"
        print("  ✅ T014.2测试通过")

        # 测试修复验证结果聚合器
        print("  测试T014.3: 修复验证结果聚合器")
        aggregator = FixVerificationAggregator()

        comprehensive_report = aggregator.aggregate_verification_results(
            session_id=self.test_session.session_id,
            suggestion_id="suggestion_001",
            static_verification_report=verification_report,
            ai_dynamic_analysis_result=ai_result
        )

        assert comprehensive_report is not None, "综合验证报告不应该为空"
        assert comprehensive_report.verification_summary is not None, "验证摘要不应该为空"
        print("  ✅ T014.3测试通过")

        print("✅ 节点H测试通过")

    def test_node_i_user_verification_decision(self):
        """测试节点I: 用户验证决策"""
        print("\n=== 测试节点I: 用户验证决策 ===")

        # 测试验证结果展示器
        print("  测试T015.1: 验证结果展示器")
        displayer = VerificationResultDisplayer()

        # 创建模拟的综合验证报告
        from src.tools.fix_verification_aggregator import ComprehensiveVerificationReport, VerificationMetrics, VerificationSummary

        mock_report = ComprehensiveVerificationReport(
            report_id="report_001",
            session_id=self.test_session.session_id,
            suggestion_id="suggestion_001",
            file_path="test_file.py",
            verification_timestamp=datetime.now(),
            static_verification=None,  # 简化测试
            ai_dynamic_analysis=None,   # 简化测试
            verification_metrics=VerificationMetrics(
                fix_success_rate=0.9,
                new_issues_count=0,
                quality_improvement_score=0.8,
                security_impact_score=0.9,
                performance_impact_score=0.8,
                overall_verification_score=0.85
            ),
            verification_summary=VerificationSummary(
                session_id=self.test_session.session_id,
                suggestion_id="suggestion_001",
                file_path="test_file.py",
                verification_status="SUCCESS",
                problem_resolved=True,
                introduced_new_issues=False,
                quality_improved=True,
                recommended_action="ACCEPT_FIX",
                confidence_level=0.9
            ),
            detailed_findings=[],
            improvement_recommendations=["建议添加单元测试"],
            risk_assessment={"overall_risk_level": "low", "risk_factors": []}
        )

        display_data = displayer.display_verification_results(
            comprehensive_report=mock_report,
            display_format=DisplayFormat.SUMMARY
        )

        assert display_data is not None, "展示数据不应该为空"
        assert display_data.summary_overview is not None, "摘要概览不应该为空"
        print("  ✅ T015.1测试通过")

        # 测试用户验证决策处理器
        print("  测试T015.2: 用户验证决策处理器")
        decision_processor = UserVerificationDecisionProcessor()
        # 使用测试的状态管理器
        decision_processor.state_manager = self.state_manager

        # 重新创建测试会话，设置到正确的工作流状态
        self.test_session = self._create_test_session()
        self.test_session.current_node = WorkflowNode.VERIFICATION_DECISION
        self.state_manager.active_sessions[self.test_session.session_id] = self.test_session

        result = decision_processor.process_user_verification_decision(
            session_id=self.test_session.session_id,
            suggestion_id="suggestion_001",
            decision_type=VerificationDecisionType.SUCCESS,
            decision_reason="修复验证通过，问题已解决",
            user_comments="修复效果很好",
            confidence_level=0.95
        )

        assert result["success"], "验证决策处理应该成功"
        assert result["next_node"] == "problem_solved", "应该转换到问题解决节点"
        print("  ✅ T015.2测试通过")

        print("✅ 节点I测试通过")

    def test_node_jk_solution_and_reanalysis(self):
        """测试节点J/K: 问题解决/重新分析"""
        print("\n=== 测试节点J/K: 问题解决/重新分析 ===")

        # 重新创建测试会话，设置到正确的工作流状态
        self.test_session = self._create_test_session()
        self.test_session.current_node = WorkflowNode.PROBLEM_SOLVED
        self.state_manager.active_sessions[self.test_session.session_id] = self.test_session

        # 测试问题解决处理器
        print("  测试T016.1: 问题解决处理器")
        solution_processor = ProblemSolutionProcessor()
        # 使用测试的状态管理器
        solution_processor.state_manager = self.state_manager

        result = solution_processor.process_problem_solution(
            session_id=self.test_session.session_id,
            issue_id="issue_001",
            suggestion_id="suggestion_001",
            user_satisfaction="非常满意"
        )

        assert result["success"], "问题解决处理应该成功"
        assert result["next_node"] == "CHECK_REMAINING", "应该转换到检查剩余问题节点"
        print("  ✅ T016.1测试通过")

        # 重置会话状态以测试重新分析
        self.test_session.pending_problems = ["issue_001"]
        self.test_session.problem_processing_status = {}
        self.state_manager.save_session(self.test_session)

        # 测试重新分析触发器
        print("  测试T017.1: 重新分析触发器")
        reanalysis_trigger = ReanalysisTrigger()
        # 使用测试的状态管理器
        reanalysis_trigger.state_manager = self.state_manager

        result = reanalysis_trigger.trigger_reanalysis(
            session_id=self.test_session.session_id,
            issue_id="issue_001",
            failed_suggestion_id="suggestion_001",
            failure_reason="验证失败：修复未解决问题",
            user_feedback="修复方案不正确"
        )

        assert result["success"], "重新分析触发应该成功"
        assert result["next_node"] == "PROBLEM_DETECTION", "应该转换回问题检测节点"
        assert result["retry_count"] == 1, "重试次数应该是1"
        print("  ✅ T017.1测试通过")

        print("✅ 节点J/K测试通过")

    def test_node_l_status_checker(self):
        """测试节点L: 问题状态检查器"""
        print("\n=== 测试节点L: 问题状态检查器 ===")

        status_checker = ProblemStatusChecker()
        # 使用测试的状态管理器
        status_checker.state_manager = self.state_manager

        # 测试有剩余问题的情况
        self.test_session.pending_problems = ["issue_001"]
        self.state_manager.save_session(self.test_session)

        result = status_checker.check_problem_status(self.test_session.session_id)

        assert result["success"], "状态检查应该成功"
        assert result["remaining_problems"] > 0, "应该有剩余问题"
        assert result["workflow_complete"] is False, "工作流不应该完成"
        print("  ✅ 有剩余问题的情况测试通过")

        # 测试无剩余问题的情况
        self.test_session.pending_problems = []
        self.state_manager.save_session(self.test_session)

        result = status_checker.check_problem_status(self.test_session.session_id)

        assert result["success"], "状态检查应该成功"
        assert result["remaining_problems"] == 0, "不应该有剩余问题"
        assert result["workflow_complete"] is True, "工作流应该完成"
        print("  ✅ 无剩余问题的情况测试通过")

        print("✅ 节点L测试通过")

    def test_node_m_completion_processor(self):
        """测试节点M: 工作流完成处理器"""
        print("\n=== 测试节点M: 工作流完成处理器 ===")

        completion_processor = WorkflowCompletionProcessor()
        # 使用测试的状态管理器
        completion_processor.state_manager = self.state_manager

        # 设置一些已解决的问题
        self.test_session.solved_problems = ["solution_issue_001"]
        self.test_session.skip_history = ["skip_issue_002"]
        self.state_manager.save_session(self.test_session)

        result = completion_processor.process_workflow_completion(self.test_session.session_id)

        assert result["success"], "工作流完成处理应该成功"
        assert result["completion_status"] is not None, "完成状态不应该为空"
        assert result["statistics"]["total_problems"] >= 0, "统计数据应该有效"

        # 验证报告生成
        report = completion_processor.get_completion_report(self.test_session.session_id)
        assert report is not None, "应该能获取到完成报告"

        print("✅ 节点M测试通过")

    def test_complete_workflow_simulation(self):
        """测试完整工作流模拟"""
        print("\n=== 测试完整工作流模拟 ===")

        # 重置测试会话
        self.test_session = self._create_test_session()
        self.state_manager.save_session(self.test_session)

        workflow_steps = []

        try:
            # 模拟工作流执行
            print("  开始模拟工作流 B→C→D→E→F→H→I→J→L→M")

            # 步骤1: 问题检测 (B) - 模拟已存在
            print("  B. 问题检测完成")
            workflow_steps.append("PROBLEM_DETECTION")

            # 步骤2: 修复建议生成 (C) - 模拟已存在
            print("  C. 修复建议生成完成")
            workflow_steps.append("FIX_SUGGESTION")

            # 步骤3: 用户审查 (D) - 模拟用户批准
            print("  D. 用户审查完成（批准）")
            workflow_steps.append("USER_REVIEW")

            # 步骤4: 自动修复 (F) - 模拟执行成功
            print("  F. 自动修复完成")
            workflow_steps.append("AUTO_FIX")

            # 步骤5: 修复验证 (H) - 模拟验证成功
            print("  H. 修复验证完成")
            workflow_steps.append("FIX_VERIFICATION")

            # 步骤6: 用户验证决策 (I) - 模拟用户确认成功
            print("  I. 用户验证决策（成功）")
            workflow_steps.append("USER_VERIFICATION_DECISION")

            # 步骤7: 问题解决 (J) - 标记问题已解决
            solution_processor = ProblemSolutionProcessor()
            solution_processor.process_problem_solution(
                session_id=self.test_session.session_id,
                issue_id="issue_001",
                suggestion_id="suggestion_001"
            )
            print("  J. 问题解决完成")
            workflow_steps.append("PROBLEM_SOLVED")

            # 步骤8: 检查剩余问题 (L) - 无剩余问题
            status_checker = ProblemStatusChecker()
            status_result = status_checker.check_problem_status(self.test_session.session_id)
            print("  L. 检查剩余问题完成")
            workflow_steps.append("CHECK_REMAINING")

            # 步骤9: 工作流完成 (M) - 生成完成报告
            completion_processor = WorkflowCompletionProcessor()
            completion_result = completion_processor.process_workflow_completion(self.test_session.session_id)
            print("  M. 工作流完成")
            workflow_steps.append("WORKFLOW_COMPLETE")

            # 验证工作流完成
            assert completion_result["success"], "工作流完成应该成功"
            assert completion_result["statistics"]["solved_problems"] > 0, "应该有解决的问题"

            print(f"\n  ✅ 完整工作流模拟成功！")
            print(f"  执行步骤: {' → '.join(workflow_steps)}")
            print(f"  最终状态: {completion_result['completion_status']}")

        except Exception as e:
            print(f"  ❌ 工作流模拟失败: {e}")
            raise

    def run_all_tests(self):
        """运行所有测试"""
        print("开始 Phase 5 工作流集成测试...")
        print("=" * 60)

        try:
            self.setup_test_environment()

            self.test_node_g_problem_skip_processor()
            self.test_node_h_verification_components()
            self.test_node_i_user_verification_decision()
            self.test_node_jk_solution_and_reanalysis()
            self.test_node_l_status_checker()
            self.test_node_m_completion_processor()
            self.test_complete_workflow_simulation()

            print("\n" + "=" * 60)
            print("🎉 所有 Phase 5 工作流集成测试通过！")
            print("✅ 节点G: 问题跳过处理器 - 正常")
            print("✅ 节点H: 修复验证 - 正常")
            print("✅ 节点I: 用户验证决策 - 正常")
            print("✅ 节点J/K: 问题解决/重新分析 - 正常")
            print("✅ 节点L: 问题状态检查器 - 正常")
            print("✅ 节点M: 工作流完成处理器 - 正常")
            print("✅ 完整工作流流程 - 正常")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()

        finally:
            self.cleanup_test_environment()


def main():
    """主函数 - 运行测试"""
    print("Phase 5 工作流集成测试")
    print("测试 B→C→D→E→F/G→H→I→J/K→L→B/M 完整工作流程")
    print()

    tester = TestPhase5WorkflowIntegration()
    tester.run_all_tests()


if __name__ == "__main__":
    main()