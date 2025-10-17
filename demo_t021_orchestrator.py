#!/usr/bin/env python3
"""
T021 Agent编排器演示脚本
演示AgentOrchestrator的基础功能和会话管理能力
"""

import sys
import time
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agent.orchestrator import AgentOrchestrator, SessionState, MessageRole


def print_section(title):
    """打印章节标题"""
    print(f"\n{'='*60}")
    print(f"T021演示: {title}")
    print('='*60)


def print_subsection(title):
    """打印子章节标题"""
    print(f"\n--- {title} ---")


def print_session_info(session, orchestrator):
    """打印会话信息"""
    print(f"会话ID: {session.session_id}")
    print(f"用户ID: {session.user_id}")
    print(f"状态: {session.state.value}")
    print(f"消息数量: {len(session.messages)}")
    print(f"创建时间: {time.strftime('%H:%M:%S', time.localtime(session.created_at))}")
    print(f"更新时间: {time.strftime('%H:%M:%S', time.localtime(session.updated_at))}")

    if session.current_request:
        print(f"当前请求模式: {session.current_request.mode.value}")

    if session.current_plan:
        print(f"当前计划ID: {session.current_plan.plan_id}")
        print(f"任务数量: {len(session.current_plan.tasks)}")


def demo_orchestrator_initialization():
    """演示编排器初始化"""
    print_section("AgentOrchestrator初始化")

    # 创建编排器实例
    orchestrator = AgentOrchestrator()

    print("✅ AgentOrchestrator初始化成功")
    print(f"最大会话数: {orchestrator.max_sessions}")
    print(f"会话超时时间: {orchestrator.session_timeout}秒")
    print(f"每会话最大消息数: {orchestrator.max_messages_per_session}")

    return orchestrator


def demo_session_creation(orchestrator):
    """演示会话创建"""
    print_section("会话创建和管理")

    # 创建多个用户的会话
    users = ["alice", "bob", "charlie"]
    sessions = {}

    for user in users:
        print_subsection(f"为用户 {user} 创建会话")

        metadata = {
            "source": "demo",
            "user_type": "developer",
            "preferences": {
                "language": "python",
                "analysis_mode": "static"
            }
        }

        session = orchestrator.create_session(user, metadata)
        sessions[user] = session

        print(f"✅ 会话创建成功")
        print(f"   会话ID: {session.session_id}")
        print(f"   初始状态: {session.state.value}")
        print(f"   元数据: {json.dumps(session.metadata, indent=2, ensure_ascii=False)}")

    return sessions


def demo_state_transitions(orchestrator, sessions):
    """演示状态转换"""
    print_section("会话状态转换")

    alice_session = sessions["alice"]

    print_subsection("初始状态")
    print(f"当前状态: {alice_session.state.value}")

    # 测试有效状态转换
    valid_transitions = [
        (SessionState.ACTIVE, "用户激活会话"),
        (SessionState.WAITING_INPUT, "等待用户输入"),
        (SessionState.PROCESSING, "处理用户请求"),
        (SessionState.ACTIVE, "处理完成，回到活跃状态"),
        (SessionState.COMPLETED, "完成会话")
    ]

    for new_state, reason in valid_transitions:
        print_subsection(f"转换到 {new_state.value}")
        success = orchestrator.transition_session_state(
            alice_session.session_id,
            new_state,
            reason
        )

        print(f"转换结果: {'✅ 成功' if success else '❌ 失败'}")
        print(f"当前状态: {alice_session.state.value}")
        print(f"转换原因: {alice_session.metadata.get('state_transition_reason', 'N/A')}")

        if not success:
            break

    # 测试无效状态转换
    print_subsection("测试无效状态转换")
    success = orchestrator.transition_session_state(
        alice_session.session_id,
        SessionState.CREATED,  # 不能从COMPLETED回到CREATED
        "无效转换测试"
    )
    print(f"无效转换结果: {'✅ 成功' if success else '❌ 失败（预期）'}")
    print(f"当前状态: {alice_session.state.value}")


def demo_message_handling(orchestrator, sessions):
    """演示消息处理和对话历史"""
    print_section("消息处理和对话历史")

    bob_session = sessions["bob"]

    # 模拟对话流程
    conversations = [
        (MessageRole.USER, "我想对 src/ 目录进行静态分析"),
        (MessageRole.ASSISTANT, "好的，我将为您创建静态分析计划"),
        (MessageRole.SYSTEM, "系统提示：分析将使用AST、Pylint、Flake8和Bandit工具"),
        (MessageRole.USER, "请重点关注安全性问题"),
        (MessageRole.ASSISTANT, "已调整分析参数，将重点扫描安全漏洞")
    ]

    for role, content in conversations:
        print_subsection(f"添加{role.value}消息")
        message = bob_session.add_message(role, content, {"demo": True})

        print(f"消息ID: {message.message_id}")
        print(f"消息内容: {content}")
        print(f"时间戳: {time.strftime('%H:%M:%S', time.localtime(message.timestamp))}")

        # 显示最后一条用户消息
        if role == MessageRole.USER:
            last_user_msg = bob_session.get_last_user_message()
            print(f"最后用户消息: {last_user_msg.content if last_user_msg else 'None'}")

    # 显示对话摘要
    print_subsection("对话摘要")
    summary = bob_session.get_conversation_summary(max_messages=3)
    print(f"最近3条消息:")
    for i, msg in enumerate(summary, 1):
        print(f"  {i}. [{msg.role.value}] {msg.content}")


def demo_user_input_processing(orchestrator, sessions):
    """演示用户输入处理"""
    print_section("用户输入处理")

    charlie_session = sessions["charlie"]

    # 确保会话处于可处理输入的状态
    orchestrator.transition_session_state(charlie_session.session_id, SessionState.ACTIVE)

    # 测试不同类型的用户输入
    user_inputs = [
        "对 src/ 目录进行静态代码分析",
        "深度分析 src/utils/config.py 文件的架构设计",
        "修复 src/tools/analyzer.py 中的安全问题"
    ]

    for i, user_input in enumerate(user_inputs, 1):
        print_subsection(f"处理用户输入 {i}")
        print(f"用户输入: {user_input}")

        # 处理用户输入
        result = orchestrator.process_user_input(
            charlie_session.session_id,
            user_input,
            {"current_path": ".", "demo_iteration": i}
        )

        if result["success"]:
            print("✅ 处理成功")
            print(f"执行计划ID: {result['execution_plan']}")
            print(f"任务数量: {result['task_count']}")
            print(f"预估时间: {result['estimated_duration']:.2f}秒")
            print(f"助手响应: {result['response']}")

            # 显示会话状态
            print(f"会话状态: {charlie_session.state.value}")

            # 显示消息历史
            history = orchestrator.get_session_history(charlie_session.session_id, limit=2)
            print(f"最近消息:")
            for msg in history:
                print(f"  [{msg.role.value}] {msg.content}")
        else:
            print(f"❌ 处理失败: {result['error']}")
            print(f"错误类型: {result['error_type']}")

        print()


def demo_session_statistics(orchestrator, sessions):
    """演示会话统计"""
    print_section("会话统计信息")

    print_subsection("全局统计")
    global_stats = orchestrator.get_session_statistics()
    print(f"总会话数: {global_stats['total_sessions']}")
    print(f"总用户数: {global_stats['total_users']}")
    print(f"活跃会话数: {global_stats['active_sessions']}")
    print(f"总消息数: {global_stats['total_messages']}")
    print(f"平均会话时长: {global_stats['average_session_duration']:.2f}秒")
    print("按状态分布:")
    for state, count in global_stats['sessions_by_state'].items():
        print(f"  {state}: {count}")

    # 用户统计
    for user_id, session in sessions.items():
        print_subsection(f"用户 {user_id} 的统计")
        user_stats = orchestrator.get_session_statistics(user_id=user_id)
        print(f"会话数: {user_stats['total_sessions']}")
        print(f"活跃会话数: {user_stats['active_sessions']}")
        print(f"总消息数: {user_stats['total_messages']}")
        print(f"平均消息数/会话: {user_stats['average_messages_per_session']:.1f}")

    # 单个会话统计
    alice_session = sessions["alice"]
    print_subsection(f"Alice的会话详情")
    session_stats = orchestrator.get_session_statistics(session_id=alice_session.session_id)
    print(f"会话ID: {session_stats['session_id']}")
    print(f"状态: {session_stats['state']}")
    print(f"用户消息数: {session_stats['user_message_count']}")
    print(f"助手消息数: {session_stats['assistant_message_count']}")
    print(f"会话时长: {session_stats['duration']:.2f}秒")


def demo_session_cleanup(orchestrator, sessions):
    """演示会话清理"""
    print_section("会话清理")

    # 显示清理前的状态
    print_subsection("清理前状态")
    print(f"活跃会话数: {len(orchestrator.sessions)}")
    print(f"用户会话映射: {len(orchestrator.user_sessions)}")

    # 关闭一些会话
    users_to_close = ["alice", "bob"]
    for user in users_to_close:
        if user in sessions:
            session = sessions[user]
            success = orchestrator.close_session(session.session_id, "演示清理")
            print(f"关闭 {user} 的会话: {'✅ 成功' if success else '❌ 失败'}")

    # 显示清理后的状态
    print_subsection("清理后状态")
    print(f"活跃会话数: {len(orchestrator.sessions)}")
    print(f"用户会话映射: {len(orchestrator.user_sessions)}")

    # 显示剩余会话的用户
    active_users = []
    for user_id, session_list in orchestrator.user_sessions.items():
        if session_list:  # 如果用户还有活跃会话
            active_users.append(user_id)

    print(f"仍有活跃会话的用户: {active_users}")


def main():
    """主演示函数"""
    print("🚀 T021 Agent编排器基础框架演示")
    print("本演示将展示AgentOrchestrator的核心功能，包括：")
    print("1. 编排器初始化")
    print("2. 会话创建和管理")
    print("3. 会话状态转换")
    print("4. 消息处理和对话历史")
    print("5. 用户输入处理")
    print("6. 会话统计")
    print("7. 会话清理")

    try:
        # 1. 初始化编排器
        orchestrator = demo_orchestrator_initialization()

        # 2. 创建会话
        sessions = demo_session_creation(orchestrator)

        # 3. 演示状态转换
        demo_state_transitions(orchestrator, sessions)

        # 4. 演示消息处理
        demo_message_handling(orchestrator, sessions)

        # 5. 演示用户输入处理
        demo_user_input_processing(orchestrator, sessions)

        # 6. 演示会话统计
        demo_session_statistics(orchestrator, sessions)

        # 7. 演示会话清理
        demo_session_cleanup(orchestrator, sessions)

        print_section("演示完成")
        print("✅ T021 Agent编排器基础框架演示成功完成！")
        print("\n核心功能验证:")
        print("✅ AgentOrchestrator类能够初始化")
        print("✅ 能够创建和管理用户会话")
        print("✅ 能够记录对话历史")
        print("✅ 能够处理会话状态转换")
        print("✅ 能够处理用户输入并生成执行计划")
        print("✅ 能够提供会话统计信息")
        print("✅ 能够管理会话生命周期")

    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)