import os
import random
import time
from typing import Literal

import requests
from anthropic import RateLimitError
from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.exceptions import LangChainException
from langchain_openai import ChatOpenAI

from src.workflow.tools.web_search import search_web

# 加载.env文件中的环境变量
load_dotenv()


def check_api_server_status(base_url):
    """检查API服务器状态"""
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=10)
        return response.status_code == 200
    except:
        return False


def invoke_with_retry(agent, messages, max_retries=3, initial_delay=1.0):
    """带重试机制的agent调用函数"""
    for attempt in range(max_retries):
        try:
            print(f"尝试调用agent (第{attempt + 1}次)...")
            result = agent.invoke(messages)
            print("调用成功!")
            return result

        except RateLimitError as e:
            if attempt == max_retries - 1:
                print(f"速率限制错误：已达到最大重试次数 {max_retries}")
                raise

            # 计算指数退避延迟，加上随机抖动
            delay = initial_delay * (2**attempt) + random.uniform(0, 1)
            print(f"遇到速率限制，等待 {delay:.2f} 秒后重试...")
            time.sleep(delay)

        except Exception as e:
            error_str = str(e)
            if (
                "502 Bad Gateway" in error_str
                or "InternalServerError" in type(e).__name__
            ):
                if attempt == max_retries - 1:
                    print(f"服务器错误：已达到最大重试次数 {max_retries}")
                    raise

                # 对于502错误，使用更长的延迟
                delay = initial_delay * (3**attempt) + random.uniform(2, 5)
                print(f"遇到服务器错误 (502 Bad Gateway)，等待 {delay:.2f} 秒后重试...")
                print("建议：检查API服务器是否正常运行")
                time.sleep(delay)
            else:
                print(f"发生其他错误: {type(e).__name__}: {e}")
                raise

    raise RuntimeError(f"在 {max_retries} 次重试后仍然失败")


# Web search tool using the improved web search service
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search using the improved web search service"""
    return search_web(
        query=query,
        max_results=max_results,
        topic=topic,
        include_raw_content=include_raw_content,
        provider="tavily",
    )


# System prompt to steer the agent to be an expert researcher
research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
"""

# 创建支持自定义端点的 Anthropic 模型
anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
anthropic_base_url = os.environ.get("ANTHROPIC_BASE_URL")
anthropic_model_name = os.environ.get("ANTHROPIC_MODEL_NAME")
model_config = {
    "api_key": anthropic_api_key,
    "model_name": anthropic_model_name,
    "base_url": anthropic_base_url,
}
print(f"Anthropic API Key: {model_config['api_key']}")
print(f"Anthropic Base URL: {model_config['base_url']}")
print(f"Anthropic Model Name: {model_config['model_name']}")

# 添加额外的模型配置以减少API调用频率
enhanced_config = model_config.copy()
enhanced_config.update(
    {
        "temperature": 0.1,  # 降低温度以减少重复调用的需要
        "max_tokens": 1000,  # 限制响应长度
        "timeout": 60,  # 设置超时时间
    }
)

model = ChatAnthropic(**enhanced_config)

# Create the deep agent
agent = create_deep_agent(
    model=model,
    tools=[internet_search],
    system_prompt=research_instructions,
)

# 在开始前检查API服务器状态
print("检查API服务器状态...")
if anthropic_base_url:
    server_status = check_api_server_status(anthropic_base_url)
    if server_status:
        print("✅ API服务器状态正常")
    else:
        print("⚠️  API服务器状态异常，可能出现连接问题")
        print("建议：检查网络连接或更换API服务器地址")
else:
    print("⚠️  未配置自定义API端点")

# 程序启动时添加延迟，避免连续请求
print("程序启动，等待2秒后开始...")
time.sleep(2)

# 使用重试机制调用agent
try:
    print("开始调用agent进行查询...")
    messages = {"messages": [{"role": "user", "content": "What is langgraph?"}]}
    result = invoke_with_retry(agent, messages)
    print("=" * 50)
    print("最终结果:")
    print(result)
    print("=" * 50)
except RateLimitError as e:
    print("=" * 50)
    print(f"最终失败: 速率限制错误 - {e}")
    print("建议：")
    print("1) 检查API密钥是否有效")
    print("2) 等待一段时间后重试")
    print("3) 考虑升级API计划以获得更高的速率限制")
    print("4) 检查是否有其他程序同时使用相同的API密钥")
    print("=" * 50)
except Exception as e:
    error_str = str(e)
    print("=" * 50)
    if "502 Bad Gateway" in error_str:
        print("最终失败: 502 Bad Gateway 错误")
        print("🚨 服务器网关错误，API服务器暂时无法响应")
        print("建议：")
        print("1) 检查API服务器是否正常运行")
        print("2) 稍后重试 (建议等待5-10分钟)")
        print("3) 联系API服务提供商")
        print("4) 尝试更换API端点地址")
        print(f"5) 当前使用端点: {anthropic_base_url}")
    else:
        print(f"最终失败: {type(e).__name__} - {e}")
        print("建议：")
        print("1) 检查环境变量配置是否正确")
        print("2) 检查网络连接是否正常")
        print("3) 检查所有依赖包是否正确安装")
    print("=" * 50)
