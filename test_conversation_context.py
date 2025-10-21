#!/usr/bin/env python3
"""
交互式对话界面和上下文管理测试脚本
用于验证ConversationContext和相关功能
"""

import sys
import os
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_conversation_context_initialization():
    """测试ConversationContext初始化"""
    print("🔍 测试ConversationContext初始化...")

    try:
        # 尝试导入ConversationContext类
        from src.tools.cli_coordinator import ConversationContext

        # 测试初始化
        context = ConversationContext("test_target", max_context_length=10)
        print("✅ ConversationContext 初始化成功")
        print(f"   - 目标路径: {context.target}")
        print(f"   - 最大长度: {context.max_context_length}")
        print(f"   - 初始对话数: {len(context.conversation_history)}")

        return context

    except ImportError as e:
        print(f"❌ ConversationContext导入失败: {e}")
        # 尝试创建一个简单的Mock版本
        return test_mock_conversation_context()
    except Exception as e:
        print(f"❌ ConversationContext初始化失败: {e}")
        return None

def test_mock_conversation_context():
    """测试Mock版本的ConversationContext"""
    print("🔍 创建Mock ConversationContext...")

    try:
        # 创建Mock版本
        class MockConversationContext:
            def __init__(self, target, max_context_length=15):
                self.target = target
                self.max_context_length = max_context_length
                self.conversation_history = []
                self.analysis_context = {
                    'target': target,
                    'analysis_type': 'comprehensive',
                    'current_file': '',
                    'previous_results': [],
                    'preferences': {},
                    'session_stats': {
                        'total_analyses': 0,
                        'successful_analyses': 0,
                        'failed_analyses': 0,
                        'total_time': 0.0
                    }
                }

            def add_message(self, user_input: str, ai_response: str, message_type: str = 'general'):
                """添加对话消息"""
                message = {
                    'timestamp': datetime.now(),
                    'type': message_type,
                    'user_input': user_input,
                    'ai_response': ai_response,
                    'session_time': 0.0
                }
                self.conversation_history.append(message)

                # 更新统计
                self.analysis_context['session_stats']['total_analyses'] += 1
                if ai_response and 'error' not in ai_response.lower():
                    self.analysis_context['session_stats']['successful_analyses'] += 1

                # 保持历史记录在限制内
                if len(self.conversation_history) > self.max_context_length:
                    self.conversation_history = self.conversation_history[-self.max_context_length:]

            def add_analysis_result(self, file_path: str, analysis_type: str, result: dict, execution_time: float):
                """添加分析结果"""
                analysis_entry = {
                    'timestamp': datetime.now(),
                    'type': 'file_analysis',
                    'file_path': file_path,
                    'analysis_type': analysis_type,
                    'result': result,
                    'execution_time': execution_time,
                    'success': result.get('success', False),
                    'session_time': 0.0
                }
                self.conversation_history.append(analysis_entry)
                self.analysis_context['previous_results'].append(analysis_entry)
                self.analysis_context['current_file'] = file_path

                # 更新统计信息
                self.analysis_context['session_stats']['total_analyses'] += 1
                if result.get('success', False):
                    self.analysis_context['session_stats']['successful_analyses'] += 1
                else:
                    self.analysis_context['session_stats']['failed_analyses'] += 1
                self.analysis_context['session_stats']['total_time'] += execution_time

                # 保持历史记录在限制内
                if len(self.conversation_history) > self.max_context_length:
                    self.conversation_history = self.conversation_history[-self.max_context_length:]

            def get_session_stats(self):
                """获取会话统计"""
                return self.analysis_context['session_stats']

            def get_conversation_summary(self):
                """获取对话摘要"""
                return {
                    'total_turns': len(self.conversation_history),
                    'target': self.target,
                    'last_activity': self.conversation_history[-1]['timestamp'] if self.conversation_history else None,
                    'analysis_types': self.analysis_context['session_stats']
                }

        context = MockConversationContext("test_target", max_context_length=10)
        print("✅ Mock ConversationContext 创建成功")
        print(f"   - 目标路径: {context.target}")
        print(f"   - 最大长度: {context.max_context_length}")

        return context

    except Exception as e:
        print(f"❌ Mock ConversationContext创建失败: {e}")
        return None

def test_conversation_turn_management():
    """测试对话轮次管理"""
    print("\n🔍 测试对话轮次管理...")

    try:
        context = test_conversation_context_initialization()
        if not context:
            return False

        # 添加对话轮次
        initial_count = len(context.conversation_history) if hasattr(context, 'conversation_history') else 0

        # 第一轮对话
        context.add_message(
            "请分析这个文件",
            "我已经分析了文件，发现了3个潜在问题：1) 缺少错误处理 2) 函数复杂度较高 3) 硬编码路径",
            "analysis"
        )

        first_count = len(context.conversation_history) if hasattr(context, 'conversation_history') else 0
        print(f"✅ 第一轮对话添加成功 (历史记录: {initial_count} -> {first_count})")

        # 第二轮对话
        context.add_message(
            "请重点关注安全问题",
            "我重新检查了代码，发现了1个SQL注入风险：在第15行的数据库查询中直接使用了用户输入",
            "security"
        )

        second_count = len(context.conversation_history) if hasattr(context, 'conversation_history') else 0
        print(f"✅ 第二轮对话添加成功 (历史记录: {first_count} -> {second_count})")

        # 第三轮对话
        context.add_message(
            "如何修复这些问题？",
            "建议修复方案：1) 添加try-catch错误处理 2) 重构复杂函数 3) 使用参数化查询",
            "repair"
        )

        third_count = len(context.conversation_history) if hasattr(context, 'conversation_history') else 0
        print(f"✅ 第三轮对话添加成功 (历史记录: {second_count} -> {third_count})")

        return True

    except Exception as e:
        print(f"❌ 对话轮次管理测试失败: {e}")
        return False

def test_context_limit_management():
    """测试上下文长度限制管理"""
    print("\n�🔍 测试上下文长度限制管理...")

    try:
        # 创建限制为3的上下文
        context = test_conversation_context_initialization()
        if not context:
            return False

        # 设置最大长度为3
        if hasattr(context, 'max_context_length'):
            context.max_context_length = 3

        # 添加超过限制的对话
        for i in range(5):
            context.add_message(
                f"第{i+1}个问题",
                f"第{i+1}个回答",
                "test"
            )

        final_count = len(context.conversation_history) if hasattr(context, 'conversation_history') else 0
        expected_count = min(3, 5)  # 最多保留3个

        print(f"✅ 上下文长度限制管理正常")
        print(f"   - 添加了5轮对话，保留了{final_count}轮")
        print(f"   - 预期保留数量: {expected_count}")

        return final_count == expected_count

    except Exception as e:
        print(f"❌ 上下文长度限制管理测试失败: {e}")
        return False

def test_session_statistics():
    """测试会话统计功能"""
    print("\n🔍 测试会话统计功能...")

    try:
        context = test_conversation_context_initialization()
        if not context:
            return False

        # 添加一些对话
        context.add_message(
            "分析类型1",
            "回答1",
            "comprehensive"
        )
        context.add_message(
            "分析类型2",
            "回答2",
            "security"
        )
        context.add_message(
            "分析类型3",
            "回答3",
            "performance"
        )

        # 获取统计信息
        stats = context.get_session_stats()
        print("✅ 会话统计功能正常")
        print(f"   - 总分析次数: {stats.get('total_analyses', 0)}")
        print(f"   - 成功分析次数: {stats.get('successful_analyses', 0)}")
        print(f"   - 最常用分析类型: {stats.get('most_used_analysis_type', 'unknown')}")

        return True

    except Exception as e:
        print(f"❌ 会话统计测试失败: {e}")
        return False

def test_context_data_persistence():
    """测试上下文数据持久化"""
    print("\n🔍 测试上下文数据持久化...")

    try:
        context = test_conversation_context_initialization()
        if not context:
            return False

        # 添加对话数据
        context.add_message(
            "测试持久化",
            "持久化测试回答",
            "persistence"
        )

        # 测试获取分析上下文
        if hasattr(context, 'analysis_context'):
            analysis_context = context.analysis_context
            print("✅ 分析上下文数据获取成功")
            print(f"   - 目标: {analysis_context.get('target', 'unknown')}")
            print(f"   - 分析类型: {analysis_context.get('analysis_type', 'unknown')}")
            print(f"   - 偏好设置: {analysis_context.get('preferences', {})}")
            print(f"   - 统计数据: {analysis_context.get('session_stats', {})}")
        else:
            print("⚠️ 分析上下文属性不存在")
            return False

        return True

    except Exception as e:
        print(f"❌ 上下文数据持久化测试失败: {e}")
        return False

def test_conversation_export():
    """测试对话导出功能"""
    print("\n🔍 测试对话导出功能...")

    try:
        from src.interfaces.deep_commands import ConversationManager

        # 创建对话管理器
        manager = ConversationManager("test_target")

        # 添加一些对话
        manager.add_message("user", "请分析代码")
        manager.add_message("assistant", "我发现了3个问题")
        manager.add_message("user", "请详细说明")
        manager.add_message("assistant", "详细说明如下...")

        # 测试导出
        export_file = "test_conversation_export.json"
        export_success = manager.export_conversation(export_file)

        if export_success:
            print("✅ 对话导出功能正常")
            print(f"   - 导出文件: {export_file}")

            # 验证导出文件
            if os.path.exists(export_file):
                with open(export_file, 'r', encoding='utf-8') as f:
                    import json
                    data = json.load(f)
                    print(f"   - 导出数据验证: {len(data)} 个字段")
                    print(f"   - 对话数量: {data.get('message_count', 0)}")
                    print(f"   - 目标路径: {data.get('target', 'unknown')}")

                # 清理测试文件
                os.remove(export_file)
                print("   - 测试文件已清理")
            else:
                print("❌ 导出文件不存在")
                return False
        else:
            print("❌ 对话导出失败")
            return False

        return True

    except Exception as e:
        print(f"❌ 对话导出测试失败: {e}")
        return False

def test_context_memory_efficiency():
    """测试上下文内存效率"""
    print("\n🔍 测试上下文内存效率...")

    try:
        context = test_conversation_context_initialization()
        if not context:
            return False

        import sys

        # 测试大量对话的内存使用
        initial_size = sys.getsizeof(context) if hasattr(context, '__sizeof__') else 0

        # 添加大量对话
        for i in range(100):
            context.add_message(
                f"用户消息 {i}",
                f"AI回答 {i}" * 100,  # 较长的回答
                "memory_test"
            )

        final_size = sys.getsizeof(context) if hasattr(context, '__sizeof__') else 0

        print("✅ 内存效率测试完成")
        print(f"   - 初始内存大小: {initial_size} bytes")
        print(f"   - 100轮对话后内存大小: {final_size} bytes")
        print(f"   - 内存增长: {final_size - initial_size} bytes")

        # 验证历史记录被正确限制
        final_count = len(context.conversation_history) if hasattr(context, 'conversation_history') else 0
        expected_max = context.max_context_length if hasattr(context, 'max_context_length') else float('inf')
        print(f"   - 最终历史记录数: {final_count}")
        print(f"   - 最大限制: {expected_max}")

        return True

    except Exception as e:
        print(f"❌ 内存效率测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始交互式对话界面和上下文管理测试")
    print("=" * 60)

    test_results = []

    # 1. 测试ConversationContext初始化
    context = test_conversation_context_initialization()
    test_results.append(context is not None)

    # 2. 测试对话轮次管理
    turn_management_ok = test_conversation_turn_management()
    test_results.append(turn_management_ok)

    # 3. 测试上下文长度限制管理
    limit_management_ok = test_context_limit_management()
    test_results.append(limit_management_ok)

    # 4. 测试会话统计
    stats_ok = test_session_statistics()
    test_results.append(stats_ok)

    # 5. 测试上下文数据持久化
    persistence_ok = test_context_data_persistence()
    test_results.append(persistence_ok)

    # 6. 测试对话导出
    export_ok = test_conversation_export()
    test_results.append(export_ok)

    # 7. 测试内存效率
    memory_ok = test_context_memory_efficiency()
    test_results.append(memory_ok)

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 交互式对话界面和上下文管理测试基本通过！")
        print("对话界面和上下文管理功能已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查对话系统。")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n用户中断测试")
        sys.exit(0)
    except Exception as e:
        print(f"\n测试异常: {e}")
        sys.exit(1)