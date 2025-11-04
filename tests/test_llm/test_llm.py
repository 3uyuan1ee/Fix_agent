#!/usr/bin/env python3
"""
测试LLM客户端是否能正常工作
"""

import sys
import os

# 确保能正确导入模块
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 导入LLM客户端
try:
    from src.llm.client import LLMClient
except ImportError:
    print("❌ 无法导入LLM客户端")
    sys.exit(1)

def test_llm():
    print("测试LLM客户端...")

    try:
        # 创建LLM客户端
        client = LLMClient()
        print("✅ LLM客户端创建成功")

        # 测试调用
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": "你是一个代码分析专家"},
                {"role": "user", "content": "请分析这个文件：main.py，选择需要修复的问题，返回JSON格式"}
            ],
            temperature=0.3,
            max_tokens=1000
        )

        print(f"LLM响应: {response}")

        if response.get("success", False):
            print("✅ LLM调用成功")
            print(f"内容: {response.get('content', '')[:200]}...")
        else:
            print(f"❌ LLM调用失败: {response.get('error_message', '未知错误')}")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm()