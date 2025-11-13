#!/usr/bin/env python3
"""完整版Web应用测试脚本"""

import asyncio
import websockets
import json
import uuid
import requests
import time

BASE_URL = "http://localhost:8000"

def test_api():
    """测试REST API"""
    print("🔧 测试REST API...")

    # 健康检查
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ 健康检查通过")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return None

    # 创建会话
    try:
        response = requests.post(
            f"{BASE_URL}/api/sessions/",
            json={"title": "WebSocket Test Session"}
        )
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data["session_id"]
            print(f"✅ 会话创建成功: {session_id}")
            return session_id
        else:
            print(f"❌ 会话创建失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
    except Exception as e:
        print(f"❌ 会话创建异常: {e}")
        return None

async def test_websocket(session_id):
    """测试WebSocket连接"""
    print(f"🔗 测试WebSocket连接...")
    uri = f"ws://localhost:8000/ws/{session_id}"

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")

            # 等待欢迎消息
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(welcome_msg)
                print(f"📥 收到欢迎消息: {welcome_data.get('content', 'No content')}")
            except asyncio.TimeoutError:
                print("⚠️ 未收到欢迎消息（超时）")

            # 发送测试消息
            test_message = {
                "type": "chat",
                "content": "你好，这是一个WebSocket测试！",
                "session_id": session_id
            }

            print(f"📤 发送消息: {test_message['content']}")
            await websocket.send(json.dumps(test_message))

            # 接收响应
            print("⏳ 等待AI响应...")
            response_count = 0
            timeout_count = 0

            while response_count < 5 and timeout_count < 3:  # 最多接收5条消息，允许3次超时
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)

                    print(f"📥 收到响应 [{data.get('type', 'unknown')}]: {data.get('content', '')[:100]}...")
                    response_count += 1

                    # 如果收到完成状态，停止接收
                    if data.get("type") == "status" and data.get("metadata", {}).get("state") == "complete":
                        break

                except asyncio.TimeoutError:
                    timeout_count += 1
                    print(f"⏰ 响应超时 ({timeout_count}/3)")
                    if timeout_count >= 3:
                        break

            print(f"✅ WebSocket测试完成，收到 {response_count} 条响应")

    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")

async def main():
    """主测试函数"""
    print("🚀 开始完整版Web应用测试")
    print("=" * 50)

    # 测试API
    session_id = test_api()
    if not session_id:
        print("❌ API测试失败，退出")
        return

    # 测试WebSocket
    await test_websocket(session_id)

    print("\n" + "=" * 50)
    print("🎉 完整版测试完成！")
    print(f"🔗 API文档: {BASE_URL}/docs")
    print(f"🏥 健康检查: {BASE_URL}/health")

if __name__ == "__main__":
    asyncio.run(main())