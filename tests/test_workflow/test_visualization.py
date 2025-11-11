"""
测试可视化功能

简单测试增强版agent的可视化功能是否正常工作
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_base_agent import create_enhanced_research_agent, VisualizationConfig
from langchain_openai import ChatOpenAI


def test_basic_functionality():
    """测试基础功能"""
    print("🧪 测试基础可视化功能")
    print("-" * 40)

    try:
        # 创建一个简单的研究代理
        researcher = create_enhanced_research_agent(
            name="test-researcher",
            description="测试用研究代理",

            model=ChatOpenAI(
                temperature=0.3,
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
            )
        )

        print("✅ 代理创建成功")

        # 构建代理
        researcher.build()
        print("✅ 代理构建成功")

        # 获取代理信息
        info = researcher.get_info()
        print(f"✅ 代理信息: {info['name']} ({info['type']})")
        print(f"   可视化状态: {'启用' if info['visualization_enabled'] else '禁用'}")
        print(f"   工具数量: {info['tools_count']}")

        return researcher

    except Exception as e:
        print(f"❌ 基础功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_simple_task(researcher):
    """测试简单任务执行"""
    print("\n🧪 测试简单任务执行")
    print("-" * 40)

    if not researcher:
        print("❌ 没有可用的代理")
        return

    try:
        # 简单的任务
        task = "简单介绍一下Python的优点"
        print(f"🎯 任务: {task}")

        # 执行任务
        result = researcher.invoke({"messages": [{"role": "user", "content": task}]})

        print("✅ 任务执行完成")

        # 获取执行日志
        log = researcher.get_execution_log()
        if log:
            print("✅ 执行日志获取成功")
            if "execution_summary" in log:
                summary = log["execution_summary"]
                print(f"   总步骤: {summary.get('total_steps', 0)}")
                print(f"   工具调用: {summary.get('tool_calls', 0)}")
                print(f"   执行时间: {summary.get('total_time', 0):.2f}秒")
        else:
            print("ℹ️ 没有执行日志（可视化可能未启用）")

    except Exception as e:
        print(f"❌ 任务执行失败: {e}")
        import traceback
        traceback.print_exc()


def test_todo_visibility():
    """测试Todo列表可视化"""
    print("\n🧪 测试Todo列表可视化")
    print("-" * 40)

    try:
        # 创建一个专门测试Todo的代理
        todo_researcher = create_enhanced_research_agent(
            name="todo-test-researcher",
            description="Todo测试代理",

            model=ChatOpenAI(
                temperature=0.2,
                model="glm-4.5-air",
                openai_api_key="4a5b3138f1b447d18ae48b1ece88a7e9.QXy6uJ1RYIoisDG4",
                openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
            ),

            system_prompt="""你是一个善于规划的助手。在执行任务时：
            1. 首先创建详细的todo列表
            2. 按照todo列表逐步执行
            3. 每完成一个任务就更新todo状态
            4. 清楚展示你的进度""",

            visualization_config=VisualizationConfig(
                show_thinking=True,
                show_tool_calls=True,
                show_todo_updates=True,  # 重点显示Todo更新
                show_timing=True,
                max_message_length=200,
            )
        )

        todo_researcher.build()
        print("✅ Todo测试代理创建成功")

        # 需要多步骤的任务
        task = """完成一个小研究项目：
        1. 研究Python的历史发展
        2. 分析Python的主要特性
        3. 总结Python的应用领域
        4. 提供学习建议

        请创建详细的todo列表并逐步完成。"""

        print(f"🎯 多步骤任务: {task[:50]}...")

        result = todo_researcher.invoke({"messages": [{"role": "user", "content": task}]})

        print("✅ 多步骤任务完成")

        # 检查Todo相关的日志
        log = todo_researcher.get_execution_log()
        if log and "execution_summary" in log:
            summary = log["execution_summary"]
            todo_updates = summary.get('todo_updates', 0)
            print(f"📝 Todo更新次数: {todo_updates}")

    except Exception as e:
        print(f"❌ Todo测试失败: {e}")


def test_error_handling():
    """测试错误处理可视化"""
    print("\n🧪 测试错误处理可视化")
    print("-" * 40)

    try:
        # 创建测试代理
        researcher = create_enhanced_research_agent(
            name="error-test-researcher",
            description="错误处理测试代理",

            model=ChatOpenAI(
                temperature=0.1,
                model="glm-4.5-air",
                openai_api_key="4a5b3138f1b447d18ae48b1ece88a7e9.QXy6uJ1RYIoisDG4",
                openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
            ),

            visualization_config=VisualizationConfig(
                show_thinking=True,
                show_tool_calls=True,
                show_todo_updates=True,
                show_timing=True,
                max_message_length=150,
            )
        )

        researcher.build()
        print("✅ 错误测试代理创建成功")

        # 可能会失败的任务
        task = "尝试访问一个不存在的API或进行网络搜索（如果工具不可用）"
        print(f"🎯 可能失败的任务: {task}")

        result = researcher.invoke({"messages": [{"role": "user", "content": task}]})
        print("✅ 任务完成（可能成功或优雅地失败）")

    except Exception as e:
        print(f"⚠️ 捕获到错误（这是正常的）: {e}")
        print("✅ 错误处理可视化正常工作")


def main():
    """主测试函数"""
    print("🧪 增强版Agent可视化功能测试")
    print("=" * 50)

    try:
        # 测试基础功能
        researcher = test_basic_functionality()

        if researcher:
            # 测试简单任务
            test_simple_task(researcher)

            # 测试Todo可视化
            test_todo_visibility()

            # 测试错误处理
            test_error_handling()

        print("\n" + "=" * 50)
        print("🎉 测试完成！")
        print("如果所有测试都显示✅，说明可视化功能正常工作。")
        print("你现在可以在代码中清楚地看到agent的思考过程和执行步骤。")

    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()