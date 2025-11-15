"""分层记忆中间件 - 工作记忆、短期记忆、长期记忆"""

import json
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from deepagents.backends.protocol import BackendProtocol
from langchain.agents.middleware.types import (AgentMiddleware, AgentState,
                                               ModelRequest, ModelResponse)
from typing_extensions import NotRequired, TypedDict

from .agent_memory import LONGTERM_MEMORY_SYSTEM_PROMPT


@dataclass
class MemoryItem:
    """记忆项数据结构"""

    content: str
    timestamp: float
    importance: float = 1.0  # 重要性评分 0.0-1.0
    tags: List[str] = None
    access_count: int = 0
    last_accessed: float = 0.0

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.last_accessed == 0.0:
            self.last_accessed = self.timestamp


class LayeredMemoryState(AgentState):
    """分层记忆中间件的状态"""

    # 工作记忆
    working_memory: NotRequired[List[str]]  # 当前对话的临时信息
    working_memory_size: NotRequired[int]  # 工作记忆最大条目数

    # 短期记忆
    session_memory: NotRequired[Dict[str, Any]]  # 会话级别的上下文
    session_start_time: NotRequired[float]
    conversation_summary: NotRequired[str]

    # 长期记忆
    agent_memory: NotRequired[str]  # 原有的agent.md内容
    semantic_memory: NotRequired[List[Dict]]  # 语义化长期记忆
    episodic_memory: NotRequired[List[Dict]]  # 情节记忆

    # 配置
    memory_config: NotRequired[Dict[str, Any]]


class WorkingMemory:
    """工作记忆管理器 - 当前对话的临时信息"""

    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.items: deque = deque(maxlen=max_size)

    def add(self, content: str, importance: float = 1.0):
        """添加工作记忆项"""
        item = {"content": content, "timestamp": time.time(), "importance": importance}
        self.items.append(item)

    def get_context(self, max_items: int = 5) -> str:
        """获取工作记忆上下文"""
        recent_items = list(self.items)[-max_items:]
        if not recent_items:
            return ""

        context_parts = ["## 当前对话上下文（工作记忆）"]
        for i, item in enumerate(recent_items, 1):
            context_parts.append(f"{i}. {item['content']}")

        return "\n".join(context_parts)

    def clear(self):
        """清空工作记忆"""
        self.items.clear()


class SessionMemory:
    """短期记忆管理器 - 会话级别的上下文"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.start_time = time.time()
        self.conversation_summary = ""
        self.key_topics: List[str] = []
        self.user_preferences: Dict[str, Any] = {}
        self.interaction_count = 0

    def update_summary(self, new_content: str):
        """更新对话摘要"""
        self.conversation_summary = (
            f"{self.conversation_summary}\n{new_content}".strip()
        )
        self.interaction_count += 1

    def add_topic(self, topic: str):
        """添加关键话题"""
        if topic not in self.key_topics:
            self.key_topics.append(topic)

    def get_context(self) -> str:
        """获取会话上下文"""
        context_parts = ["## 会话上下文（短期记忆）"]
        context_parts.append(f"会话开始时间: {time.ctime(self.start_time)}")
        context_parts.append(f"交互次数: {self.interaction_count}")

        if self.key_topics:
            context_parts.append(f"关键话题: {', '.join(self.key_topics)}")

        if self.conversation_summary:
            context_parts.append(f"对话摘要: {self.conversation_summary}")

        return "\n".join(context_parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于存储"""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "conversation_summary": self.conversation_summary,
            "key_topics": self.key_topics,
            "user_preferences": self.user_preferences,
            "interaction_count": self.interaction_count,
        }

    def from_dict(self, data: Dict[str, Any]):
        """从字典恢复"""
        self.start_time = data.get("start_time", time.time())
        self.conversation_summary = data.get("conversation_summary", "")
        self.key_topics = data.get("key_topics", [])
        self.user_preferences = data.get("user_preferences", {})
        self.interaction_count = data.get("interaction_count", 0)


class LongTermMemory:
    """长期记忆管理器 - 跨会话的持久化知识"""

    def __init__(self, backend: BackendProtocol, memory_path: str = "/memories/"):
        self.backend = backend
        self.memory_path = memory_path.rstrip("/") + "/"
        self.semantic_memory: List[Dict] = []  # 语义记忆（概念、规则、偏好）
        self.episodic_memory: List[Dict] = []  # 情节记忆（具体事件、对话）

    def load(self):
        """加载长期记忆"""
        try:
            # 加载语义记忆
            semantic_data = self.backend.read(f"{self.memory_path}semantic_memory.json")
            if semantic_data:
                self.semantic_memory = json.loads(semantic_data)
        except:
            self.semantic_memory = []

        try:
            # 加载情节记忆
            episodic_data = self.backend.read(f"{self.memory_path}episodic_memory.json")
            if episodic_data:
                self.episodic_memory = json.loads(episodic_data)
        except:
            self.episodic_memory = []

    def save(self):
        """保存长期记忆"""
        try:
            self.backend.write(
                f"{self.memory_path}semantic_memory.json",
                json.dumps(self.semantic_memory, ensure_ascii=False, indent=2),
            )
        except Exception as e:
            print(f"Warning: Failed to save semantic memory: {e}")

        try:
            self.backend.write(
                f"{self.memory_path}episodic_memory.json",
                json.dumps(self.episodic_memory, ensure_ascii=False, indent=2),
            )
        except Exception as e:
            print(f"Warning: Failed to save episodic memory: {e}")

    def add_semantic_memory(
        self, content: str, importance: float = 1.0, tags: List[str] = None
    ):
        """添加语义记忆"""
        memory_item = {
            "content": content,
            "timestamp": time.time(),
            "importance": importance,
            "tags": tags or [],
            "access_count": 0,
            "last_accessed": time.time(),
        }
        self.semantic_memory.append(memory_item)

        # 限制语义记忆大小，删除最不重要的项
        if len(self.semantic_memory) > 1000:
            self.semantic_memory.sort(
                key=lambda x: (x["importance"], x["access_count"])
            )
            self.semantic_memory = self.semantic_memory[-800:]

    def add_episodic_memory(
        self, content: str, importance: float = 0.8, tags: List[str] = None
    ):
        """添加情节记忆"""
        memory_item = {
            "content": content,
            "timestamp": time.time(),
            "importance": importance,
            "tags": tags or [],
            "access_count": 0,
            "last_accessed": time.time(),
        }
        self.episodic_memory.append(memory_item)

        # 限制情节记忆大小，保留最近的
        if len(self.episodic_memory) > 500:
            self.episodic_memory.sort(key=lambda x: x["timestamp"])
            self.episodic_memory = self.episodic_memory[-400:]

    def search_memory(
        self, query: str, memory_type: str = "all", limit: int = 5
    ) -> List[Dict]:
        """搜索记忆内容"""
        results = []

        if memory_type in ["semantic", "all"]:
            for item in self.semantic_memory:
                if query.lower() in item["content"].lower():
                    item["access_count"] += 1
                    item["last_accessed"] = time.time()
                    results.append({**item, "type": "semantic"})

        if memory_type in ["episodic", "all"]:
            for item in self.episodic_memory:
                if query.lower() in item["content"].lower():
                    item["access_count"] += 1
                    item["last_accessed"] = time.time()
                    results.append({**item, "type": "episodic"})

        # 按重要性和最近访问时间排序
        results.sort(key=lambda x: (x["importance"], x["last_accessed"]), reverse=True)
        return results[:limit]

    def get_context(self, max_items: int = 10) -> str:
        """获取相关长期记忆上下文"""
        if not self.semantic_memory and not self.episodic_memory:
            return ""

        context_parts = ["## 长期记忆（相关上下文）"]

        # 获取最重要的语义记忆
        semantic_items = sorted(
            self.semantic_memory,
            key=lambda x: (x["importance"], x["access_count"]),
            reverse=True,
        )[: max_items // 2]

        if semantic_items:
            context_parts.append("### 语义记忆（概念、规则、偏好）:")
            for item in semantic_items:
                context_parts.append(f"- {item['content']}")

        # 获取最近的情节记忆
        episodic_items = sorted(
            self.episodic_memory, key=lambda x: x["timestamp"], reverse=True
        )[: max_items // 2]

        if episodic_items:
            context_parts.append("### 情节记忆（重要事件、对话）:")
            for item in episodic_items:
                context_parts.append(f"- {item['content']}")

        return "\n".join(context_parts)


class LayeredMemoryMiddleware(AgentMiddleware):
    """分层记忆中间件

    提供三层记忆架构：
    - 工作记忆：当前对话的临时信息（快速访问）
    - 短期记忆：会话级别的上下文（会话持续）
    - 长期记忆：跨会话的持久化知识（永久存储）

    Args:
        backend: 用于持久化记忆的后端
        memory_path: 记忆存储路径
        working_memory_size: 工作记忆最大条目数
        enable_semantic_memory: 是否启用语义记忆
        enable_episodic_memory: 是否启用情节记忆
        auto_save_interval: 自动保存间隔（秒）
    """

    state_schema = LayeredMemoryState

    def __init__(
        self,
        *,
        backend: BackendProtocol,
        memory_path: str = "/memories/",
        working_memory_size: int = 10,
        enable_semantic_memory: bool = True,
        enable_episodic_memory: bool = True,
        auto_save_interval: int = 300,  # 5分钟
        legacy_mode: bool = False,  # 兼容模式
    ) -> None:
        """初始化分层记忆中间件"""
        self.backend = backend
        self.memory_path = memory_path
        self.working_memory_size = working_memory_size
        self.enable_semantic_memory = enable_semantic_memory
        self.enable_episodic_memory = enable_episodic_memory
        self.auto_save_interval = auto_save_interval
        self.legacy_mode = legacy_mode

        # 记忆管理器
        self.working_memory = WorkingMemory(max_size=working_memory_size)
        self.session_memory: Dict[str, SessionMemory] = {}
        self.long_term_memory = LongTermMemory(backend, memory_path)

        # 加载长期记忆
        if enable_semantic_memory or enable_episodic_memory:
            self.long_term_memory.load()

        # 最后保存时间
        self.last_save_time = time.time()

    def _get_session_id(self, state: LayeredMemoryState) -> str:
        """获取会话ID"""
        return state.get("session_id") or state.get("thread_id") or "default"

    def _extract_context_from_request(self, request: ModelRequest) -> str:
        """从请求中提取上下文信息"""
        content_parts = []

        # 提取用户输入
        if hasattr(request, "content") and request.content:
            content_parts.append(f"用户: {request.content}")
        elif hasattr(request, "messages") and request.messages:
            for msg in request.messages:
                if hasattr(msg, "content") and msg.content:
                    # 兼容LangChain Message对象和字典格式
                    if hasattr(msg, "type"):
                        role = (
                            "用户"
                            if msg.type == "human"
                            else "助手" if msg.type == "ai" else "未知"
                        )
                    elif hasattr(msg, "get"):
                        role = (
                            "用户"
                            if msg.get("role") == "user"
                            else "助手" if msg.get("role") == "assistant" else "未知"
                        )
                    else:
                        role = "未知"
                    content_parts.append(f"{role}: {msg.content}")

        return " | ".join(content_parts)

    def _extract_context_from_response(self, response: ModelResponse) -> str:
        """从响应中提取上下文信息"""
        content_parts = []

        if hasattr(response, "content") and response.content:
            content_parts.append(f"助手: {response.content}")
        elif hasattr(response, "messages") and response.messages:
            for msg in response.messages:
                if hasattr(msg, "content") and msg.content:
                    # 兼容LangChain Message对象和字典格式
                    if hasattr(msg, "type"):
                        role = (
                            "用户"
                            if msg.type == "human"
                            else "助手" if msg.type == "ai" else "未知"
                        )
                    elif hasattr(msg, "get"):
                        role = (
                            "用户"
                            if msg.get("role") == "user"
                            else "助手" if msg.get("role") == "assistant" else "未知"
                        )
                    else:
                        role = "未知"
                    content_parts.append(f"{role}: {msg.content}")

        return " | ".join(content_parts)

    def _update_working_memory(self, content: str, importance: float = 1.0):
        """更新工作记忆"""
        self.working_memory.add(content, importance)

    def _update_session_memory(self, session_id: str, content: str):
        """更新会话记忆"""
        if session_id not in self.session_memory:
            self.session_memory[session_id] = SessionMemory(session_id)

        session = self.session_memory[session_id]
        session.update_summary(content)

        # 提取关键词作为话题
        words = content.split()
        for word in words:
            if len(word) > 4 and word.isalpha():  # 简单的关键词提取
                session.add_topic(word.lower())

    def _update_long_term_memory(self, content: str, importance: float = 0.8):
        """更新长期记忆"""
        if not self.enable_semantic_memory and not self.enable_episodic_memory:
            return

        # 简单的重要性评估
        if "重要" in content or "关键" in content or "记住" in content:
            importance = min(1.0, importance + 0.3)

        # 判断记忆类型
        if any(keyword in content for keyword in ["我说", "用户说", "对话", "讨论"]):
            # 情节记忆
            if self.enable_episodic_memory:
                self.long_term_memory.add_episodic_memory(content, importance)
        else:
            # 语义记忆
            if self.enable_semantic_memory:
                self.long_term_memory.add_semantic_memory(content, importance)

    def _auto_save_if_needed(self):
        """如果需要，自动保存记忆"""
        current_time = time.time()
        if current_time - self.last_save_time > self.auto_save_interval:
            try:
                self.long_term_memory.save()
                self.last_save_time = current_time
            except Exception as e:
                print(f"Warning: Auto save failed: {e}")

    def before_agent(
        self,
        state: LayeredMemoryState,
        runtime,
    ) -> LayeredMemoryState:
        """在代理执行前初始化记忆系统"""
        session_id = self._get_session_id(state)

        # 初始化会话记忆
        if session_id not in self.session_memory:
            self.session_memory[session_id] = SessionMemory(session_id)

        # 设置记忆配置
        memory_config = {
            "working_memory_size": self.working_memory_size,
            "enable_semantic_memory": self.enable_semantic_memory,
            "enable_episodic_memory": self.enable_episodic_memory,
        }

        return {
            "memory_config": memory_config,
            "working_memory_size": self.working_memory_size,
            "session_memory": (
                self.session_memory[session_id].to_dict()
                if session_id in self.session_memory
                else {}
            ),
        }

    async def abefore_agent(
        self,
        state: LayeredMemoryState,
        runtime,
    ) -> LayeredMemoryState:
        """异步：在代理执行前初始化记忆系统"""
        return self.before_agent(state, runtime)

    def _build_memory_context(self, request: ModelRequest) -> str:
        """构建完整的记忆上下文"""
        session_id = self._get_session_id(request.state)
        context_parts = []

        # 工作记忆
        working_context = self.working_memory.get_context()
        if working_context:
            context_parts.append(working_context)

        # 会话记忆
        if session_id in self.session_memory:
            session_context = self.session_memory[session_id].get_context()
            if session_context:
                context_parts.append(session_context)

        # 长期记忆
        if self.enable_semantic_memory or self.enable_episodic_memory:
            long_term_context = self.long_term_memory.get_context()
            if long_term_context:
                context_parts.append(long_term_context)

        # 兼容模式：包含原有agent_memory
        if self.legacy_mode:
            agent_memory = request.state.get("agent_memory", "")
            if agent_memory:
                context_parts.append(f"## 原始记忆\n{agent_memory}")

        return "\n\n".join(context_parts)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """包装模型调用，注入分层记忆上下文"""

        # 提取请求上下文
        request_context = self._extract_context_from_request(request)
        if request_context:
            self._update_working_memory(request_context, importance=1.0)
            session_id = self._get_session_id(request.state)
            self._update_session_memory(session_id, request_context)

        # 构建记忆上下文
        memory_context = self._build_memory_context(request)

        # 注入记忆到系统提示
        if memory_context:
            if request.system_prompt:
                request.system_prompt = f"{memory_context}\n\n{request.system_prompt}"
            else:
                request.system_prompt = memory_context

            # 添加记忆系统提示
            request.system_prompt = (
                request.system_prompt
                + "\n\n"
                + LONGTERM_MEMORY_SYSTEM_PROMPT.format(memory_path=self.memory_path)
            )

        # 执行原始请求
        response = handler(request)

        # 提取响应上下文并更新记忆
        response_context = self._extract_context_from_response(response)
        if response_context:
            self._update_working_memory(response_context, importance=0.8)
            session_id = self._get_session_id(request.state)
            self._update_session_memory(session_id, response_context)
            self._update_long_term_memory(response_context, importance=0.7)

        # 自动保存
        self._auto_save_if_needed()

        return response

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步：包装模型调用，注入分层记忆上下文"""
        # 提取请求上下文
        request_context = self._extract_context_from_request(request)
        if request_context:
            self._update_working_memory(request_context, importance=1.0)
            session_id = self._get_session_id(request.state)
            self._update_session_memory(session_id, request_context)

        # 构建记忆上下文
        memory_context = self._build_memory_context(request)

        # 注入记忆到系统提示
        if memory_context:
            if request.system_prompt:
                request.system_prompt = f"{memory_context}\n\n{request.system_prompt}"
            else:
                request.system_prompt = memory_context

            # 添加记忆系统提示
            request.system_prompt = (
                request.system_prompt
                + "\n\n"
                + LONGTERM_MEMORY_SYSTEM_PROMPT.format(memory_path=self.memory_path)
            )

        # 执行原始请求
        response = await handler(request)

        # 提取响应上下文并更新记忆
        response_context = self._extract_context_from_response(response)
        if response_context:
            self._update_working_memory(response_context, importance=0.8)
            session_id = self._get_session_id(request.state)
            self._update_session_memory(session_id, response_context)
            self._update_long_term_memory(response_context, importance=0.7)

        # 自动保存
        self._auto_save_if_needed()

        return response

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            "working_memory": {
                "size": len(self.working_memory.items),
                "max_size": self.working_memory.max_size,
            },
            "session_memory": {
                "active_sessions": len(self.session_memory),
                "sessions": {
                    sid: {
                        "interaction_count": session.interaction_count,
                        "key_topics_count": len(session.key_topics),
                        "summary_length": len(session.conversation_summary),
                    }
                    for sid, session in self.session_memory.items()
                },
            },
            "long_term_memory": {
                "semantic_memory_count": len(self.long_term_memory.semantic_memory),
                "episodic_memory_count": len(self.long_term_memory.episodic_memory),
                "last_save_time": self.last_save_time,
            },
        }

    def search_memories(
        self, query: str, memory_type: str = "all", limit: int = 5
    ) -> List[Dict]:
        """搜索所有记忆层级"""
        return self.long_term_memory.search_memory(query, memory_type, limit)

    def clear_working_memory(self):
        """清空工作记忆"""
        self.working_memory.clear()

    def save_all_memories(self):
        """强制保存所有记忆"""
        try:
            self.long_term_memory.save()
            self.last_save_time = time.time()
        except Exception as e:
            print(f"Error saving memories: {e}")

    def cleanup(self):
        """清理资源"""
        self.save_all_memories()
