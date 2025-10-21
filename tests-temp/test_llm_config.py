#!/usr/bin/env python3
"""
测试LLM配置和客户端是否正常工作
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_config_loading():
    """测试配置加载"""
    print("🔍 测试LLM配置加载...")

    try:
        from llm.config import LLMConfigManager

        # 创建配置管理器
        config_manager = LLMConfigManager()

        # 列出所有可用providers
        providers = config_manager.list_providers()
        print(f"   - 可用providers: {providers}")

        # 检查mock配置
        mock_config = config_manager.get_config('mock')
        if mock_config:
            print(f"   - Mock配置: ✅ {mock_config.provider} -> {mock_config.model}")
            return True
        else:
            print("   - Mock配置: ❌ 不存在")
            return False

    except Exception as e:
        print(f"   - 配置加载失败: ❌ {e}")
        return False

def test_client_initialization():
    """测试客户端初始化"""
    print("\n🔍 测试LLM客户端初始化...")

    try:
        from llm.client import LLMClient

        # 创建客户端
        client = LLMClient()

        # 检查可用的providers
        providers = client.get_provider_names()
        print(f"   - 客户端providers: {providers}")

        if 'mock' in providers:
            print("   - Mock provider: ✅ 可用")
            return True
        else:
            print("   - Mock provider: ❌ 不可用")
            return False

    except Exception as e:
        print(f"   - 客户端初始化失败: ❌ {e}")
        return False

def test_mock_provider():
    """测试Mock provider功能"""
    print("\n🔍 测试Mock provider功能...")

    try:
        from llm.client import LLMClient
        import asyncio

        # 创建客户端
        client = LLMClient()

        # 创建测试请求
        request = client.create_request(
            ["分析这个Python代码的质量"],
            max_tokens=100,
            temperature=0.3
        )

        # 测试异步调用
        async def run_test():
            response = await client.complete(request, provider="mock")
            return response

        response = asyncio.run(run_test())

        if response and response.content:
            print(f"   - Mock响应: ✅ {len(response.content)} 字符")
            print(f"   - 响应预览: {response.content[:100]}...")
            return True
        else:
            print("   - Mock响应: ❌ 空响应")
            return False

    except Exception as e:
        print(f"   - Mock provider测试失败: ❌ {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 LLM配置和客户端测试")
    print("=" * 50)

    test_results = []

    # 1. 测试配置加载
    config_ok = test_config_loading()
    test_results.append(config_ok)

    # 2. 测试客户端初始化
    client_ok = test_client_initialization()
    test_results.append(client_ok)

    # 3. 测试Mock provider
    mock_ok = test_mock_provider()
    test_results.append(mock_ok)

    # 输出结果
    print("\n" + "=" * 50)
    print("📊 测试结果:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed == total:
        print("\n🎉 所有测试通过！Mock LLM配置正常工作。")
        return 0
    else:
        print(f"\n⚠️ 有 {total-passed} 项测试失败，需要检查配置。")
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