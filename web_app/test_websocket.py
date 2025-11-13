#!/usr/bin/env python3
"""WebSocket测试客户端"""

import asyncio
import websockets
import json
import uuid

async def test_websocket():
    """测试WebSocket连接和消息发送"""
    session_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/{session_id}"

    print(f"🔗 连接到WebSocket: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket连接成功")

            # 发送测试消息
            test_message = {
                "type": "message",
                "content": "你好，这是一个测试消息！",
                "session_id": session_id
            }

            print(f"📤 发送消息: {test_message['content']}")
            await websocket.send(json.dumps(test_message))

            # 接收响应
            print("⏳ 等待AI响应...")
            response_count = 0
            async for message in websocket:
                data = json.loads(message)
                print(f"📥 收到响应: {data}")
                response_count += 1

                # 限制接收的消息数量
                if response_count >= 3:
                    break

            print("✅ 测试完成")

    except Exception as e:
        print(f"❌ WebSocket测试失败: {e}")

if __name__ == "__main__":
    print("🚀 开始WebSocket测试")
    asyncio.run(test_websocket())