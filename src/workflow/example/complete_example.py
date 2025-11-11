"""
完整的可视化功能示例

展示增强版agent的所有可视化能力
"""

import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_base_agent import VisualizationConfig, create_enhanced_research_agent
from langchain_openai import ChatOpenAI


def main():
    """主示例函数"""
    print("🎭 增强版Agent完整功能示例")
    print("=" * 60)

    # 创建一个功能完整的增强版研究代理
    researcher = create_enhanced_research_agent(
        name="demo-enhanced-agent",
        description="演示用增强版研究代理",
        # 定制系统提示，鼓励展示思考过程
        system_prompt="""你是一个智能研究助手，具有强大的分析和展示能力。在执行任务时，请：

        1. **展示思考过程**：详细说明你的分析思路和决策逻辑
        2. **创建执行计划**：使用todo列表来分解复杂任务
        3. **说明工具选择**：解释为什么选择特定的工具或方法
        4. **跟踪执行进度**：清楚地显示每个步骤的完成情况
        5. **总结分析结果**：提供清晰的结论和建议

        请让用户能够清楚地看到你的完整工作流程。""",
        # 模型配置
        model=ChatOpenAI(
            temperature=0.5,
            model="glm-4.5-air",
            openai_api_key="4a5b3138f1b447d18ae48b1ece88a7e9.QXy6uJ1RYIoisDG4",
            openai_api_base="https://open.bigmodel.cn/api/paas/v4/",
        ),
        # 完整的可视化配置
        visualization_config=VisualizationConfig(
            show_thinking=True,  # 显示思考过程
            show_tool_calls=True,  # 显示工具调用
            show_todo_updates=True,  # 显示Todo更新
            show_timing=True,  # 显示执行时间
            show_subagent_calls=True,  # 显示子代理调用
            max_message_length=300,  # 详细显示内容
            colors={  # 自定义图标
                "thinking": "🧠",
                "tool_call": "🔧",
                "tool_result": "✅",
                "todo": "📝",
                "subagent": "🤖",
                "error": "⚠️",
                "success": "🎉",
                "info": "ℹ️",
            },
        ),
    )

    # 构建代理
    print("🔧 构建增强版代理...")
    researcher.build()
    print("✅ 代理构建完成")

    # 显示代理信息
    info = researcher.get_info()
    print(f"\n📋 代理详细信息:")
    print(f"  名称: {info['name']}")
    print(f"  类型: {info['type']}")
    print(f"  描述: {info['description']}")
    print(f"  模型: {info['model']}")
    print(f"  工具数量: {info['tools_count']}")
    print(f"  子代理数量: {info['subagents_count']}")
    print(f"  中间件数量: {info['middleware_count']}")
    print(f"  可视化状态: {'👁️ 启用' if info['visualization_enabled'] else '🔒 禁用'}")
    print(f"  调试模式: {'🐛 开启' if info['debug'] else '✅ 关闭'}")

    # 执行一个复杂的任务来展示所有可视化功能
    task = """请完成一个关于"人工智能在医疗健康领域的应用"的深度研究报告：

    研究要求：
    1. 分析当前AI在医疗诊断中的主要技术（如图像识别、自然语言处理等）
    2. 调研具体的成功应用案例和实际效果
    3. 分析AI医疗面临的技术挑战和伦理问题
    4. 评估未来5年的发展趋势和机遇
    5. 提供医疗行业采用AI的建议和实施路径

    请创建详细的研究计划，并逐步展示你的研究过程和分析结果。"""

    print(f"\n🎯 执行复杂研究任务:")
    print(f"   {task[:100]}...")

    # 执行任务（这将展示完整的可视化过程）
    print("\n" + "=" * 60)
    print("🚀 开始执行任务（展示完整可视化过程）")
    print("=" * 60)

    try:
        result = researcher.invoke({"messages": [{"role": "user", "content": task}]})

        # 获取和分析执行日志
        execution_log = researcher.get_execution_log()
        if execution_log and "execution_summary" in execution_log:
            summary = execution_log["execution_summary"]

            print("\n" + "=" * 60)
            print("📊 执行统计分析")
            print("=" * 60)

            print(f"📈 总体统计:")
            print(f"  总执行步骤: {summary.get('total_steps', 0)}")
            print(f"  工具调用次数: {summary.get('tool_calls', 0)}")
            print(f"  Todo更新次数: {summary.get('todo_updates', 0)}")
            print(f"  子代理调用次数: {summary.get('subagent_calls', 0)}")
            print(f"  总执行时间: {summary.get('total_time', 0):.2f}秒")

            # 分析步骤类型分布
            steps = summary.get("steps", [])
            if steps:
                step_types = {}
                for step in steps:
                    step_type = step.get("type", "unknown")
                    step_types[step_type] = step_types.get(step_type, 0) + 1

                print(f"\n🔍 步骤类型分析:")
                for step_type, count in step_types.items():
                    icons = {
                        "thinking": "🧠 思考过程",
                        "tool_call": "🔧 工具调用",
                        "tool_result": "✅ 工具结果",
                        "todo_update": "📝 Todo更新",
                        "subagent_call": "🤖 子代理调用",
                        "error": "⚠️ 错误处理",
                    }
                    label = icons.get(step_type, f"📋 {step_type}")
                    print(f"  {label}: {count} 次")

        # 显示结果摘要
        if isinstance(result, dict) and "messages" in result:
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                if hasattr(last_message, "content") and last_message.content:
                    content = last_message.content
                    print(f"\n📝 研究结果摘要:")
                    print(f"   {content[:300]}...")

        print("\n" + "=" * 60)
        print("🎉 任务执行完成！")
        print("=" * 60)

        print(f"\n✨ 可视化功能展示总结:")
        print(f"  🧠 思考过程可视化 - 清楚展示AI的推理逻辑")
        print(f"  🔧 工具调用可视化 - 详细记录每个操作步骤")
        print(f"  📝 Todo管理可视化 - 实时跟踪任务进度")
        print(f"  🤖 子代理协调可视化 - 展示多代理协作过程")
        print(f"  ⚠️ 错误处理可视化 - 清楚显示问题解决方案")
        print(f"  ⏱️ 执行时间统计 - 性能监控和优化")

    except Exception as e:
        print(f"❌ 任务执行过程中出现错误: {e}")
        print("这可能是因为任务过于复杂或资源限制")

    print(f"\n📚 更多信息:")
    print(f"  📖 查看文档: VISUALIZATION_SUMMARY.md")
    print(f"  📋 使用指南: USAGE_GUIDE.md")
    print(f"  🧪 更多示例: simple_demo.py, visualization_demo.py")

    print(f"\n🚀 开始使用增强版agent，享受完全透明的AI执行体验！")


if __name__ == "__main__":
    main()
