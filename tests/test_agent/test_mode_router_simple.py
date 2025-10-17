#!/usr/bin/env python3
"""
T022 模式切换和路由简化单元测试
验证ModeRecognizer的基本功能，避免循环导入问题
"""

import pytest
from unittest.mock import Mock
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 直接导入要测试的模块
from src.agent.mode_router import ModeRecognizer
from src.agent.planner import AnalysisMode


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
            ("安全漏洞扫描", AnalysisMode.STATIC),
            ("static analysis", AnalysisMode.STATIC),
            ("quick scan", AnalysisMode.STATIC)
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
            ("架构设计评审", AnalysisMode.DEEP),
            ("deep analysis", AnalysisMode.DEEP),
            ("detailed review", AnalysisMode.DEEP)
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
            ("优化这段代码", AnalysisMode.FIX),
            ("fix bug", AnalysisMode.FIX),
            ("repair issue", AnalysisMode.FIX)
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
            ("/repair 解决问题", AnalysisMode.FIX),
            ("static check", AnalysisMode.STATIC),
            ("deep analysis", AnalysisMode.DEEP),
            ("fix issue", AnalysisMode.FIX)
        ]

        for user_input, expected_mode in test_cases:
            mode, confidence = self.recognizer.recognize_mode(user_input)

            assert mode == expected_mode, f"命令 '{user_input}' 应识别为 {expected_mode.value}"
            assert confidence > 0.7, f"命令 '{user_input}' 置信度应较高: {confidence}"

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
        session = Mock()
        session.messages = []

        # 添加相关消息历史
        for role, content in [
            ("user", "我想进行静态检查"),
            ("assistant", "好的，我来帮您进行静态检查"),
            ("user", "继续检查")
        ]:
            message = Mock()
            message.role = role
            message.content = content
            session.messages.append(message)

        mode, confidence = self.recognizer.recognize_mode(
            "继续检查",
            session=session
        )

        # 应识别为静态分析（基于上下文）
        assert mode == AnalysisMode.STATIC
        assert confidence > 0.5

    def test_low_confidence_fallback(self):
        """测试低置信度回退"""
        # 模糊的输入
        ambiguous_inputs = [
            "帮我看看这个文件",
            "检查一下代码",
            "能帮我分析吗"
        ]

        for ambiguous_input in ambiguous_inputs:
            mode, confidence = self.recognizer.recognize_mode(ambiguous_input)

            # 应该给出某种模式
            assert mode in [AnalysisMode.STATIC, AnalysisMode.DEEP, AnalysisMode.FIX]
            # 置信度可能较低，但不应该为0
            assert confidence > 0

    def test_invalid_input_handling(self):
        """测试无效输入处理"""
        invalid_inputs = [
            "",  # 空字符串
            "   ",  # 只有空格
            "hello world",  # 英文无意义输入
            "123456"  # 只有数字
        ]

        for invalid_input in invalid_inputs:
            mode, confidence = self.recognizer.recognize_mode(invalid_input)

            # 应该回退到静态分析模式（默认）
            assert mode == AnalysisMode.STATIC
            # 置信度应该很低或为默认值
            assert 0.5 <= confidence <= 1.0

    def test_get_mode_suggestions(self):
        """测试获取模式建议"""
        user_input = "我想进行静态代码分析"

        suggestions = self.recognizer.get_mode_suggestions(user_input, top_n=3)

        assert len(suggestions) <= 3
        assert len(suggestions) > 0

        # 验证返回格式
        for mode, confidence in suggestions:
            assert mode in [AnalysisMode.STATIC, AnalysisMode.DEEP, AnalysisMode.FIX]
            assert 0 <= confidence <= 1

        # 验证排序（第一个应该置信度最高）
        if len(suggestions) > 1:
            for i in range(len(suggestions) - 1):
                assert suggestions[i][1] >= suggestions[i + 1][1]

    def test_different_confidence_levels(self):
        """测试不同置信度级别"""
        # 高置信度命令模式
        mode, confidence = self.recognizer.recognize_mode("/static 分析")
        assert confidence > 0.9

        # 中等置信度关键词模式
        mode, confidence = self.recognizer.recognize_mode("静态分析代码")
        assert confidence > 0.5

        # 低置信度模糊输入
        mode, confidence = self.recognizer.recognize_mode("看看代码")
        assert confidence <= 0.5

    def test_mixed_language_input(self):
        """测试混合语言输入"""
        test_cases = [
            ("static 静态分析", AnalysisMode.STATIC),
            ("deep 深度分析", AnalysisMode.DEEP),
            ("fix 修复问题", AnalysisMode.FIX),
            ("分析代码 static", AnalysisMode.STATIC),
            ("深度分析 deep", AnalysisMode.DEEP),
            ("修复 fix 代码", AnalysisMode.FIX)
        ]

        for user_input, expected_mode in test_cases:
            mode, confidence = self.recognizer.recognize_mode(user_input)

            assert mode == expected_mode, f"混合输入 '{user_input}' 应识别为 {expected_mode.value}"
            assert confidence > 0.5, f"混合输入 '{user_input}' 置信度过低: {confidence}"


class TestModeRecognizerIntegration:
    """测试模式识别器集成功能"""

    def setup_method(self):
        """测试前的设置"""
        self.recognizer = ModeRecognizer()

    def test_consistency_multiple_calls(self):
        """测试多次调用的一致性"""
        user_input = "静态分析 src/ 目录"

        # 多次调用相同输入
        results = []
        for _ in range(5):
            mode, confidence = self.recognizer.recognize_mode(user_input)
            results.append((mode, confidence))

        # 验证结果一致性
        first_mode, first_confidence = results[0]
        for mode, confidence in results[1:]:
            assert mode == first_mode
            # 浮点数可能有微小差异，但应该很接近
            assert abs(confidence - first_confidence) < 0.001

    def test_edge_cases(self):
        """测试边界情况"""
        edge_cases = [
            ("静", AnalysisMode.STATIC),  # 单字匹配
            ("修复", AnalysisMode.FIX),  # 精确匹配
            ("深度", AnalysisMode.DEEP),  # 精确匹配
            ("STATIC ANALYSIS", AnalysisMode.STATIC),  # 大写
            ("Deep Analysis", AnalysisMode.DEEP),  # 标题大小写
            ("Fix Bug", AnalysisMode.FIX),  # 标题大小写
        ]

        for user_input, expected_mode in edge_cases:
            mode, confidence = self.recognizer.recognize_mode(user_input)

            assert mode == expected_mode, f"边界输入 '{user_input}' 应识别为 {expected_mode.value}"
            assert confidence > 0, f"边界输入 '{user_input}' 应该有非零置信度"

    def test_performance_basic(self):
        """测试基本性能"""
        import time

        user_input = "对 src/ 目录进行静态代码分析，检查代码质量和安全漏洞"

        # 测试单次调用性能
        start_time = time.time()
        mode, confidence = self.recognizer.recognize_mode(user_input)
        single_call_time = time.time() - start_time

        # 单次调用应该很快（< 10ms）
        assert single_call_time < 0.01, f"单次调用耗时过长: {single_call_time:.3f}s"

        # 测试批量调用性能
        start_time = time.time()
        for _ in range(100):
            mode, confidence = self.recognizer.recognize_mode(user_input)
        batch_time = time.time() - start_time

        # 100次调用应该很快（< 1s）
        assert batch_time < 1.0, f"批量调用耗时过长: {batch_time:.3f}s"

        # 验证结果一致性
        assert mode == AnalysisMode.STATIC
        assert confidence > 0.5


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])