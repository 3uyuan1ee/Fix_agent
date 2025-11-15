"""将代理特定的长期记忆加载到系统提示中的中间件。"""

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any

from ..prompt.prompt_template import LONGTERM_MEMORY_SYSTEM_PROMPT

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from deepagents.backends.protocol import BackendProtocol
from langchain.agents.middleware.types import (AgentMiddleware, AgentState,
                                               ModelRequest, ModelResponse)
from typing_extensions import NotRequired, TypedDict


class AgentMemoryState(AgentState):
    """代理记忆中间件的状态"""

    agent_memory: NotRequired[str | None]
    """代理的长期记忆内容"""


AGENT_MEMORY_FILE_PATH = "/agent.md"

DEFAULT_MEMORY_SNIPPET = """<agent_memory>
{agent_memory}
</agent_memory>
"""


class AgentMemoryMiddleware(AgentMiddleware):
    """用于加载代理特定长期记忆的中间件

    这个中间件从文件(agent.md)中加载代理的长期记忆，并将其注入到系统提示中。
    记忆在对话开始时加载一次，并存储在状态中。

    Args:
        backend: 用于加载代理记忆文件的后端。
        system_prompt_template: 用于将代理记忆注入系统提示的可选自定义模板。
            使用 {agent_memory} 作为占位符。默认为简单的节标题。

    Example:
        ```python
        from deepagents.middleware.agent_memory import AgentMemoryMiddleware
        from deepagents.memory.backends import FilesystemBackend
        from pathlib import Path

        # 设置指向代理目录的后端
        agent_dir = Path.home() / ".deepagents" / "my-agent"
        backend = FilesystemBackend(root_dir=agent_dir)

        # 创建中间件
        middleware = AgentMemoryMiddleware(backend=backend)
        ```
    """

    state_schema = AgentMemoryState

    def __init__(
        self,
        *,
        backend: BackendProtocol,
        memory_path: str,
        system_prompt_template: str | None = None,
    ) -> None:
        """初始化代理记忆中间件。

        Args:
            backend: 用于加载代理记忆文件的后端。
            memory_path: 记忆文件路径。
            system_prompt_template: 用于将代理记忆注入系统提示的可选自定义模板。
        """
        self.backend = backend
        self.memory_path = memory_path
        self.system_prompt_template = system_prompt_template or DEFAULT_MEMORY_SNIPPET

    def before_agent(
        self,
        state: AgentMemoryState,
        runtime,
    ) -> AgentMemoryState:
        """在代理执行前从文件加载代理记忆。

        Args:
            state: 当前代理状态。
            runtime: 运行时实例。

        Returns:
            填充 agent_memory 的更新状态。
        """
        # 仅在记忆尚未加载时加载
        if "agent_memory" not in state or state.get("agent_memory") is None:
            file_data = self.backend.read(AGENT_MEMORY_FILE_PATH)
            return {"agent_memory": file_data}

    async def abefore_agent(
        self,
        state: AgentMemoryState,
        runtime,
    ) -> AgentMemoryState:
        """（异步）在代理执行前从文件加载代理记忆。

        Args:
            state: 当前代理状态。
            runtime: 运行时实例。

        Returns:
            填充 agent_memory 的更新状态。
        """
        # 仅在记忆尚未加载时加载
        if "agent_memory" not in state or state.get("agent_memory") is None:
            file_data = self.backend.read(AGENT_MEMORY_FILE_PATH)
            return {"agent_memory": file_data}

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """将代理记忆注入到系统提示中

        Args:
            request: 正在处理的模型请求
            handler: 调用修改后请求的处理器函数

        Returns:
            来自处理器的模型响应
        """
        # 从状态中获取代理记忆
        agent_memory = request.state.get("agent_memory", "")

        memory_section = self.system_prompt_template.format(agent_memory=agent_memory)
        if request.system_prompt:
            request.system_prompt = memory_section + "\n\n" + request.system_prompt
        else:
            request.system_prompt = memory_section
        request.system_prompt = (
            request.system_prompt
            + "\n\n"
            + LONGTERM_MEMORY_SYSTEM_PROMPT.format(memory_path=self.memory_path)
        )

        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """（异步）将代理记忆注入到系统提示中

        Args:
            request: 正在处理的模型请求
            handler: 调用修改后请求的处理器函数

        Returns:
            来自处理器的模型响应
        """
        # 从状态中获取代理记忆
        agent_memory = request.state.get("agent_memory", "")

        memory_section = self.system_prompt_template.format(agent_memory=agent_memory)
        if request.system_prompt:
            request.system_prompt = memory_section + "\n\n" + request.system_prompt
        else:
            request.system_prompt = memory_section
        request.system_prompt = (
            request.system_prompt
            + "\n\n"
            + LONGTERM_MEMORY_SYSTEM_PROMPT.format(memory_path=self.memory_path)
        )

        return await handler(request)
