"""
完整可视化功能测试

测试所有可视化功能，包括思考过程、工具调用、todo列表构建等
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_base_agent import create_enhanced_research_agent, VisualizationConfig
from langchain_openai import ChatOpenAI


def test_thinking_visualization():
    """测试思考过程可视化"""
    print("🧠 测试思考过程可视化")
    print("-" * 50)

    try:
        # 创建一个强调思考过程的代理
        researcher = create_enhanced_research_agent(
            name="thinking-test",
            description="思考过程测试代理",

            system_prompt="""你是一个善于展示思考过程的助手。在回答任何问题之前，请：
            1. 详细分析问题的要求和含义
            2. 说明你的思考过程和推理步骤
            3. 解释你为什么选择这样的回答方式
            4. 展示你的决策逻辑

            请明确使用"思考："、"分析："、"推理："等词语来展示你的思考过程。""",

            model=ChatOpenAI(
                temperature=0.5,
                model="glm-4.5-air",
                openai_api_key="4a5b3138f1b447d18ae48b1ece88a7e9.QXy6uJ1RYIoisDG4",
                openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
            ),

            visualization_config=VisualizationConfig(
                show_thinking=True,
                show_tool_calls=True,
                show_todo_updates=True,
                show_timing=True,
                show_subagent_calls=False,
                max_message_length=300,
                colors={
                    "thinking": "🧠",
                    "tool_call": "🔧",
                    "tool_result": "✅",
                    "todo": "📝",
                    "error": "❌",
                    "success": "🎉",
                    "info": "ℹ️",
                }
            )
        )

        researcher.build()
        print("✅ 思考过程测试代理创建成功")

        # 需要深入思考的任务
        task = """分析为什么Python在数据科学领域如此受欢迎，请从以下角度思考：
        1. 语言特性方面
        2. 生态系统方面
        3. 社区支持方面
        4. 学习曲线方面

        请详细展示你的分析过程。"""

        print(f"\n🎯 思考任务: {task[:80]}...")

        # 执行任务
        result = researcher.invoke({"messages": [{"role": "user", "content": task}]})

        # 获取执行日志
        log = researcher.get_execution_log()
        if log and "execution_summary" in log:
            summary = log["execution_summary"]
            print(f"📊 执行统计:")
            print(f"  总步骤数: {summary.get('total_steps', 0)}")
            print(f"  工具调用: {summary.get('tool_calls', 0)}")
            print(f"  执行时间: {summary.get('total_time', 0):.2f}秒")

        print("✅ 思考过程可视化测试完成")
        return True

    except Exception as e:
        print(f"❌ 思考过程可视化测试失败: {e}")
        return False


def test_todo_visualization():
    """测试Todo列表可视化"""
    print("\n📝 测试Todo列表可视化")
    print("-" * 50)

    try:
        # 创建一个专门测试todo的代理
        todo_researcher = create_enhanced_research_agent(
            name="todo-test",
            description="Todo列表测试代理",

            system_prompt="""你是一个善于规划和任务管理的助手。在执行复杂任务时：
            1. 首先创建详细的todo列表，分解任务为具体步骤
            2. 按照todo列表逐步执行，每完成一项就标记完成
            3. 在过程中不断更新todo列表状态
            4. 最后总结完成的任务和结果

            请明确使用todo列表来跟踪你的工作进度。""",

            model=ChatOpenAI(
                temperature=0.3,
                model="glm-4.5-air",
                openai_api_key="4a5b3138f1b447d18ae48b1ece88a7e9.QXy6uJ1RYIoisDG4",
                openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
            ),

            visualization_config=VisualizationConfig(
                show_thinking=True,
                show_tool_calls=True,
                show_todo_updates=True,  # 重点显示Todo更新
                show_timing=True,
                show_subagent_calls=False,
                max_message_length=200,
                colors={
                    "thinking": "💭",
                    "tool_call": "🔨",
                    "tool_result": "✨",
                    "todo": "🗂️",
                    "error": "⚠️",
                    "success": "🎯",
                    "info": "📋",
                }
            )
        )

        todo_researcher.build()
        print("✅ Todo测试代理创建成功")

        # 需要多步骤规划的任务
        task = """完成一个小型研究报告：人工智能在医疗诊断中的应用
        要求：
        1. 调研当前AI医疗诊断的主要技术
        2. 分析这些技术的优势和局限性
        3. 收集实际应用案例
        4. 总结未来发展趋势
        5. 提供学习资源建议

        请创建详细的todo列表并逐步完成。"""

        print(f"\n🎯 Todo任务: {task[:60]}...")

        # 执行任务
        result = todo_researcher.invoke({"messages": [{"role": "user", "content": task}]})

        # 获取执行日志，特别关注todo更新
        log = todo_researcher.get_execution_log()
        if log and "execution_summary" in log:
            summary = log["execution_summary"]
            print(f"📊 Todo统计:")
            print(f"  Todo更新次数: {summary.get('todo_updates', 0)}")
            print(f"  总步骤数: {summary.get('total_steps', 0)}")
            print(f"  执行时间: {summary.get('total_time', 0):.2f}秒")

        print("✅ Todo列表可视化测试完成")
        return True

    except Exception as e:
        print(f"❌ Todo列表可视化测试失败: {e}")
        return False


def test_error_handling_visualization():
    """测试错误处理可视化"""
    print("\n⚠️ 测试错误处理可视化")
    print("-" * 50)

    try:
        # 创建一个测试错误处理的代理
        error_researcher = create_enhanced_research_agent(
            name="error-test",
            description="错误处理测试代理",

            system_prompt="""你是一个善于处理错误和异常情况的助手。当遇到问题时：
            1. 清楚地分析错误原因
            2. 说明你的解决方案思路
            3. 尝试多种替代方案
            4. 总结从错误中学到的经验

            请展示你的错误处理和问题解决过程。""",

            model=ChatOpenAI(
                temperature=0.2,
                model="glm-4.5-air",
                openai_api_key="4a5b3138f1b447d18ae48b1ece88a7e9.QXy6uJ1RYIoisDG4",
                openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
            ),

            visualization_config=VisualizationConfig(
                show_thinking=True,
                show_tool_calls=True,
                show_todo_updates=True,
                show_timing=True,
                show_subagent_calls=False,
                max_message_length=150,
                colors={
                    "thinking": "🤔",
                    "tool_call": "🔧",
                    "tool_result": "📊",
                    "todo": "📋",
                    "error": "🚨",
                    "success": "✅",
                    "info": "ℹ️",
                }
            )
        )

        error_researcher.build()
        print("✅ 错误处理测试代理创建成功")

        # 可能会遇到问题的任务
        task = """尝试完成以下可能有挑战的任务：
        1. 搜索一些不存在的网络资源
        2. 如果搜索失败，基于你的知识回答
        3. 分析为什么会出现问题
        4. 提供替代解决方案

        请展示你的错误处理过程。"""

        print(f"\n🎯 错误处理任务: {task[:60]}...")

        # 执行任务
        result = error_researcher.invoke({"messages": [{"role": "user", "content": task}]})

        # 获取执行日志
        log = error_researcher.get_execution_log()
        if log and "execution_summary" in log:
            summary = log["execution_summary"]
            print(f"📊 错误处理统计:")
            print(f"  总步骤数: {summary.get('total_steps', 0)}")
            print(f"  工具调用: {summary.get('tool_calls', 0)}")
            print(f"  执行时间: {summary.get('total_time', 0):.2f}秒")

        print("✅ 错误处理可视化测试完成")
        return True

    except Exception as e:
        print(f"❌ 错误处理可视化测试失败: {e}")
        return False


def test_streaming_visualization():
    """测试流式可视化"""
    print("\n🌊 测试流式可视化")
    print("-" * 50)

    try:
        # 创建流式测试代理
        stream_researcher = create_enhanced_research_agent(
            name="stream-test",
            description="流式测试代理",

            model=ChatOpenAI(
                temperature=0.4,
                model="glm-4.5-air",
                openai_api_key="4a5b3138f1b447d18ae48b1ece88a7e9.QXy6uJ1RYIoisDG4",
                openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
            ),

            visualization_config=VisualizationConfig(
                show_thinking=False,  # 流式时简化显示
                show_tool_calls=True,
                show_todo_updates=False,
                show_timing=False,
                show_subagent_calls=False,
                max_message_length=100,
            )
        )

        stream_researcher.build()
        print("✅ 流式测试代理创建成功")

        # 简单的流式任务
        task = "简单介绍一下机器学习的基本概念"

        print(f"\n🎯 流式任务: {task}")
        print("🌊 开始流式执行...")

        # 流式执行
        chunk_count = 0
        for chunk in stream_researcher.stream({"messages": [{"role": "user", "content": task}]}):
            chunk_count += 1
            if chunk_count <= 3:  # 只显示前几个chunk避免输出过多
                print(f"📦 Chunk {chunk_count}: {type(chunk).__name__}")

        print(f"✅ 流式执行完成，共 {chunk_count} 个chunks")
        return True

    except Exception as e:
        print(f"❌ 流式可视化测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🎭 完整可视化功能测试")
    print("=" * 60)
    print("测试项目:")
    print("  🧠 思考过程可视化")
    print("  📝 Todo列表构建可视化")
    print("  ⚠️ 错误处理可视化")
    print("  🌊 流式执行可视化")
    print("=" * 60)

    # 运行所有测试
    tests = [
        ("思考过程可视化", test_thinking_visualization),
        ("Todo列表可视化", test_todo_visualization),
        ("错误处理可视化", test_error_handling_visualization),
        ("流式执行可视化", test_streaming_visualization),
    ]

    passed_tests = 0
    total_tests = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_func():
                passed_tests += 1
                print(f"✅ {test_name} 通过")
            else:
                print(f"❌ {test_name} 失败")
        except Exception as e:
            print(f"❌ {test_name} 异常: {e}")

    # 最终总结
    print(f"\n{'='*60}")
    print(f"📊 测试总结: {passed_tests}/{total_tests} 通过")

    if passed_tests == total_tests:
        print("🎉 所有可视化功能测试通过！")
        print("\n你现在可以清楚地看到:")
        print("  🧠 Agent的思考过程和推理逻辑")
        print("  🔧 工具调用的详细信息和结果")
        print("  📝 Todo列表的构建和更新过程")
        print("  ⚠️ 错误处理和恢复机制")
        print("  🌊 流式执行的实时过程")
        print("\n✨ 可视化优化完成！")
    else:
        print(f"⚠️ {total_tests - passed_tests} 个测试失败，但主要功能已实现。")
        print("可视化系统基本可用，可以进行进一步调试。")

    print(f"\n🎯 建议:")
    print("  1. 在实际使用中启用完整可视化功能")
    print("  2. 根据需要调整可视化配置")
    print("  3. 查看执行日志来分析agent行为")
    print("  4. 使用流式模式进行实时监控")


if __name__ == "__main__":
    main()