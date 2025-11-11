"""
DeepAgents Base Agent 使用示例

展示如何使用基类框架创建和运行不同类型的代理
"""

import os

from base_agent import (
    AgentConfig,
    AgentType,
    CoordinatorAgent,
    DeveloperAgent,
    ResearchAgent,
    create_coordinator_agent,
    create_developer_agent,
    create_research_agent,
)
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

# 加载环境变量
load_dotenv()


def example_research_agent():
    """研究代理使用示例"""
    print("=" * 50)
    print("研究代理示例")
    print("=" * 50)

    # 方法1: 使用便利函数创建
    researcher = create_research_agent(
        name="ai-researcher",
        description="AI技术研究专家",
        system_prompt="你是AI技术专家，专门研究最新的AI发展趋势和技术细节",
        model=ChatAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=os.environ.get("ANTHROPIC_BASE_URL"),
            model_name=os.environ.get("ANTHROPIC_MODEL_NAME"),
            temperature=0.1,
            max_tokens=1000,
        ),
    )

    # 构建代理
    researcher.build()

    # 显示代理信息
    print("代理信息:", researcher.get_info())

    # 执行查询
    try:
        result = researcher.invoke(
            {"messages": [{"role": "user", "content": "研究一下LangGraph的最新发展"}]}
        )
        print("查询结果:", result)
    except Exception as e:
        print(f"执行失败: {e}")


def example_developer_agent():
    """开发代理使用示例"""
    print("\n" + "=" * 50)
    print("开发代理示例")
    print("=" * 50)

    # 方法2: 使用配置创建
    config = AgentConfig(
        name="code-developer",
        agent_type=AgentType.DEVELOPER,
        description="Python代码开发专家",
        system_prompt="你是Python开发专家，能够分析代码、发现问题并提供改进建议",
        model=ChatAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=os.environ.get("ANTHROPIC_BASE_URL"),
            model_name=os.environ.get("ANTHROPIC_MODEL_NAME"),
            temperature=0.1,
        ),
        debug=True,
    )

    developer = DeveloperAgent(config)
    developer.build()

    print("代理信息:", developer.get_info())

    try:
        result = developer.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "分析以下Python代码的质量：def add(a,b):return a+b",
                    }
                ]
            }
        )
        print("代码分析结果:", result)
    except Exception as e:
        print(f"执行失败: {e}")


def example_coordinator_agent():
    """协调代理使用示例"""
    print("\n" + "=" * 50)
    print("协调代理示例")
    print("=" * 50)

    # 创建子代理
    research_subagent = {
        "name": "research-subagent",
        "description": "负责信息收集的子代理",
        "system_prompt": "你是研究员，负责收集相关信息",
        "tools": [],  # 会自动添加搜索工具
    }

    code_subagent = {
        "name": "code-subagent",
        "description": "负责代码开发的子代理",
        "system_prompt": "你是开发工程师，负责代码实现",
        "tools": [],  # 会自动添加代码分析工具
    }

    # 创建协调代理
    coordinator = create_coordinator_agent(
        name="project-coordinator",
        description="项目协调管理器",
        system_prompt="你是项目经理，负责协调不同专家完成任务",
        subagents=[research_subagent, code_subagent],
        model=ChatAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=os.environ.get("ANTHROPIC_BASE_URL"),
            model_name=os.environ.get("ANTHROPIC_MODEL_NAME"),
            temperature=0.1,
        ),
    )

    coordinator.build()

    print("代理信息:", coordinator.get_info())

    try:
        result = coordinator.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "协调研究代理研究Python，然后让代码代理写一个Python脚本",
                    }
                ]
            }
        )
        print("协调结果:", result)
    except Exception as e:
        print(f"执行失败: {e}")


def example_stream_execution():
    """流式执行示例"""
    print("\n" + "=" * 50)
    print("流式执行示例")
    print("=" * 50)

    researcher = create_research_agent(
        name="stream-researcher",
        description="流式研究代理",
        model=ChatAnthropic(
            api_key=os.environ["ANTHROPIC_API_KEY"],
            base_url=os.environ.get("ANTHROPIC_BASE_URL"),
            model_name=os.environ.get("ANTHROPIC_MODEL_NAME"),
            temperature=0.1,
        ),
    )

    researcher.build()

    try:
        print("开始流式执行...")
        for chunk in researcher.stream(
            {"messages": [{"role": "user", "content": "简单介绍一下deepagents"}]}
        ):
            print("流式输出:", chunk)
            print("-" * 20)
    except Exception as e:
        print(f"流式执行失败: {e}")


def main():
    """主函数 - 运行所有示例"""
    print("DeepAgents Base Agent 使用示例")
    print("注意：确保环境变量已正确设置")

    # 检查必要的环境变量
    required_vars = ["ANTHROPIC_API_KEY"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        print(f"错误：缺少环境变量: {', '.join(missing_vars)}")
        return

    # 运行示例
    try:
        example_research_agent()
        example_developer_agent()
        example_coordinator_agent()
        example_stream_execution()
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        print(f"示例执行出错: {e}")


if __name__ == "__main__":
    main()
