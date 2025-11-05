"""
Mock LLM提供者，用于测试和演示
"""

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict

from .base import LLMConfig, LLMProvider, LLMRequest, LLMResponse


class MockLLMProvider(LLMProvider):
    """Mock LLM提供者"""

    def __init__(self, config: LLMConfig):
        super().__init__(config)

    @property
    def provider_name(self) -> str:
        """提供者名称"""
        return "mock"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """完成文本生成请求"""
        # 模拟网络延迟
        await asyncio.sleep(0.5 + len(request.messages) * 0.1)

        # 构造模拟响应
        user_messages = [msg for msg in request.messages if msg.role.value == "user"]
        last_user_message = user_messages[-1].content if user_messages else "分析代码"

        # 根据用户输入内容生成相应的响应
        if "分析" in last_user_message and "config" in last_user_message.lower():
            content = """{
    "summary": "这是一个配置管理模块，负责处理系统配置的加载、验证和管理",
    "issues": [
        {
            "type": "improvement",
            "line": 15,
            "message": "建议添加配置项的详细说明文档",
            "severity": "low"
        },
        {
            "type": "security",
            "line": 42,
            "message": "配置文件中包含敏感信息，建议使用环境变量",
            "severity": "medium"
        }
    ],
    "recommendations": [
        "为所有配置项添加类型注解",
        "使用环境变量存储敏感信息",
        "添加配置验证功能",
        "实现配置热重载机制"
    ],
    "strengths": [
        "模块结构清晰",
        "支持多种配置源",
        "错误处理完善"
    ],
    "overall_score": 8.2,
    "complexity_analysis": {
        "cyclomatic_complexity": 12,
        "cognitive_complexity": 8,
        "maintainability_index": 85
    }
}"""
        elif "测试" in last_user_message:
            content = """{
    "summary": "代码测试覆盖充分，包含单元测试和集成测试",
    "issues": [
        {
            "type": "coverage",
            "line": 25,
            "message": "部分分支的测试覆盖率可以进一步提升",
            "severity": "low"
        }
    ],
    "recommendations": [
        "增加边界条件测试",
        "添加性能测试用例",
        "考虑使用测试覆盖率工具"
    ],
    "strengths": [
        "测试结构完整",
        "Mock使用恰当",
        "测试覆盖了主要功能"
    ],
    "overall_score": 9.0
}"""
        else:
            content = """{
    "summary": "代码结构良好，实现了基本的功能需求",
    "issues": [
        {
            "type": "suggestion",
            "line": 10,
            "message": "建议添加更多的注释和文档",
            "severity": "low"
        }
    ],
    "recommendations": [
        "完善代码注释",
        "添加类型注解",
        "考虑添加错误处理机制"
    ],
    "strengths": [
        "代码结构清晰",
        "实现了核心功能"
    ],
    "overall_score": 8.5
}"""

        return LLMResponse(
            request_id=request.request_id,
            provider=self.provider_name,
            model=self.config.model,
            content=content,
            finish_reason="stop",
            usage={
                "prompt_tokens": sum(len(msg.content) for msg in request.messages) // 4,
                "completion_tokens": len(content) // 4,
                "total_tokens": (
                    sum(len(msg.content) for msg in request.messages) + len(content)
                )
                // 4,
            },
            created_at=time.time(),
            response_time=0.5 + len(request.messages) * 0.1,
        )

    async def stream_complete(
        self, request: LLMRequest
    ) -> AsyncGenerator[LLMResponse, None]:
        """流式完成文本生成请求"""
        # 模拟流式响应
        full_response = await self.complete(request)

        # 分块返回响应
        words = full_response.content.split()
        chunk_content = ""

        for word in words:
            chunk_content += word + " "
            yield LLMResponse(
                request_id=request.request_id,
                provider=self.provider_name,
                model=self.config.model,
                content=chunk_content.strip(),
                delta=word + " ",
                is_stream=True,
                is_complete=False,
            )
            await asyncio.sleep(0.05)

        # 最后返回完整响应
        yield LLMResponse(
            request_id=request.request_id,
            provider=self.provider_name,
            model=self.config.model,
            content=full_response.content,
            finish_reason="stop",
            is_stream=False,
            is_complete=True,
            usage=full_response.usage,
        )

    def validate_request(self, request: LLMRequest) -> None:
        """验证请求"""
        if not request.messages:
            raise ValueError("Messages are required")

        if any(not msg.content for msg in request.messages):
            raise ValueError("Message content cannot be empty")
