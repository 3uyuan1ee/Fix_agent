"""AI model adapter that wraps the CLI's AI logic for web use."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加CLI项目路径到Python路径
cli_root = Path(__file__).parent.parent.parent.parent / "src"
if cli_root.exists():
    sys.path.insert(0, str(cli_root))

# 延迟导入CLI模块
def _import_cli_modules():
    """Import CLI modules safely."""
    try:
        from agents.agent import create_agent_with_config
        from config.config import create_model
        from tools.tools import get_all_tools
        from midware.agent_memory import AgentMemoryMiddleware
        from deepagents.backends.filesystem import FilesystemBackend
        from deepagents.backends.composite import CompositeBackend
        from deepagents.middleware.resumable_shell import ResumableShellToolMiddleware
        from langgraph.checkpoint.memory import InMemorySaver

        return {
            'create_agent_with_config': create_agent_with_config,
            'create_model': create_model,
            'get_all_tools': get_all_tools,
            'AgentMemoryMiddleware': AgentMemoryMiddleware,
            'FilesystemBackend': FilesystemBackend,
            'CompositeBackend': CompositeBackend,
            'ResumableShellToolMiddleware': ResumableShellToolMiddleware,
            'InMemorySaver': InMemorySaver
        }
    except ImportError as e:
        print(f"Warning: CLI modules not available: {e}")
        return None

cli_modules = _import_cli_modules()


class AIAdapter:
    """Adapter class to bridge CLI AI logic with web interface."""

    def __init__(self, session_id: str, workspace_path: str):
        """Initialize AI adapter for a specific session.

        Args:
            session_id: Unique identifier for the web session
            workspace_path: Path to the user's workspace directory
        """
        self.session_id = session_id
        self.workspace_path = Path(workspace_path)
        self.agent = None
        self.checkpointer = None
        self.cli_available = cli_modules is not None

        # 创建会话专用目录
        self.session_dir = Path("workspaces") / "sessions" / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # 记忆目录
        self.memory_dir = Path("workspaces") / "memories" / session_id
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 只有在CLI模块可用时才初始化AI代理
        if self.cli_available:
            self._initialize_agent()

    def _initialize_agent(self):
        """Initialize the AI agent with CLI configuration."""
        if not self.cli_available:
            return

        try:
            # 创建模型（复用CLI逻辑）
            model = self._create_model_from_env()

            # 获取工具（复用CLI工具）
            tools = self._get_available_tools()

            # 创建中间件
            agent_middleware = self._create_middleware()

            # 创建代理
            self.agent = cli_modules['create_agent_with_config'](
                model=model,
                assistant_id=self.session_id,
                tools=tools
            )

            # 设置内存检查点
            self.checkpointer = cli_modules['InMemorySaver']()
            self.agent.checkpointer = self.checkpointer
        except Exception as e:
            print(f"Failed to initialize AI agent: {e}")
            self.cli_available = False

    def _create_model_from_env(self):
        """Create AI model from environment variables (CLI logic)."""
        if not self.cli_available:
            return None

        try:
            # 导入环境变量
            from dotenv import load_dotenv
            load_dotenv()

            # 复用CLI的模型创建逻辑
            return cli_modules['create_model']()
        except Exception as e:
            print(f"Failed to create model: {e}")
            return None

    def _get_available_tools(self) -> List[Any]:
        """Get list of available tools (CLI logic)."""
        if not self.cli_available:
            return []

        try:
            return list(cli_modules['get_all_tools']().values())
        except Exception as e:
            print(f"Failed to get tools: {e}")
            return []

    def _create_middleware(self) -> List:
        """Create middleware for the agent."""
        if not self.cli_available:
            return []

        try:
            # Shell中间件（限制在用户工作空间）
            shell_middleware = cli_modules['ResumableShellToolMiddleware'](
                workspace_root=str(self.workspace_path),
                execution_policy=None  # 使用默认策略
            )

            # 记忆后端
            long_term_backend = cli_modules['FilesystemBackend'](
                root_dir=self.memory_dir,
                virtual_mode=True
            )

            # 复合后端
            backend = cli_modules['CompositeBackend'](
                default=cli_modules['FilesystemBackend'](),
                routes={"/memories/": long_term_backend}
            )

            # 记忆中间件
            memory_middleware = cli_modules['AgentMemoryMiddleware'](
                backend=long_term_backend,
                memory_path="/memories/"
            )

            return [memory_middleware, shell_middleware]
        except Exception as e:
            print(f"Failed to create middleware: {e}")
            return []

    async def stream_response(self, message: str, file_references: List[str] = None):
        """Stream AI response for web interface.

        Args:
            message: User message
            file_references: List of file paths to include in context

        Yields:
            Dict containing streaming response chunks
        """
        # 如果CLI不可用，返回模拟响应
        if not self.cli_available or not self.agent:
            yield {
                "type": "message",
                "content": f"我收到了你的消息: '{message}'。这是一个模拟的AI响应。完整版本将集成CLI的AI代理功能。",
                "session_id": self.session_id
            }
            return

        # 构建完整输入（包含文件引用）
        full_input = self._build_input_with_files(message, file_references or [])

        # 配置
        config = {
            "configurable": {"thread_id": self.session_id},
            "metadata": {"session_id": self.session_id, "source": "web"},
        }

        try:
            # 流式响应
            for chunk in self.agent.stream(
                {"messages": [{"role": "user", "content": full_input}]},
                stream_mode=["messages", "updates"],
                subgraphs=True,
                config=config,
                durability="exit",
            ):
                # 处理流式数据块
                processed_chunk = self._process_stream_chunk(chunk)
                if processed_chunk:
                    yield processed_chunk

        except Exception as e:
            yield {
                "type": "error",
                "content": str(e),
                "session_id": self.session_id
            }

    def _build_input_with_files(self, message: str, file_paths: List[str]) -> str:
        """Build input message with file contents included."""
        if not file_paths:
            return message

        context_parts = [message, "\n\n## Referenced Files\n"]

        for file_path in file_paths:
            try:
                full_path = self.workspace_path / file_path
                if full_path.exists():
                    content = full_path.read_text(encoding='utf-8')
                    # 限制文件大小
                    if len(content) > 50000:
                        content = content[:50000] + "\n... (file truncated)"

                    context_parts.append(
                        f"\n### {full_path.name}\n"
                        f"Path: `{file_path}`\n"
                        f"```\n{content}\n```"
                    )
                else:
                    context_parts.append(
                        f"\n### {Path(file_path).name}\n"
                        f"[Error: File not found - {file_path}]"
                    )
            except Exception as e:
                context_parts.append(
                    f"\n### {Path(file_path).name}\n"
                    f"[Error reading file: {e}]"
                )

        return "\n".join(context_parts)

    def _process_stream_chunk(self, chunk) -> Optional[Dict]:
        """Process streaming chunk from AI agent."""
        if not isinstance(chunk, tuple) or len(chunk) != 3:
            return None

        namespace, stream_mode, data = chunk

        if stream_mode == "messages":
            if isinstance(data, tuple) and len(data) == 2:
                message, metadata = data

                # 处理AI消息
                if hasattr(message, 'content_blocks'):
                    for block in message.content_blocks:
                        if block.get("type") == "text":
                            return {
                                "type": "message",
                                "content": block.get("text", ""),
                                "session_id": self.session_id,
                                "metadata": metadata
                            }

                        elif block.get("type") == "tool_call_chunk":
                            return {
                                "type": "tool_call",
                                "tool": block.get("name"),
                                "args": block.get("args"),
                                "session_id": self.session_id
                            }

        elif stream_mode == "updates":
            if isinstance(data, dict) and "todos" in data:
                return {
                    "type": "todos",
                    "todos": data["todos"],
                    "session_id": self.session_id
                }

        return None

    def get_memory_files(self) -> List[str]:
        """Get list of memory files for this session."""
        memory_files = []
        if self.memory_dir.exists():
            for file_path in self.memory_dir.rglob("*"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self.memory_dir)
                    memory_files.append(str(relative_path))
        return memory_files

    def read_memory_file(self, file_path: str) -> str:
        """Read content from a memory file."""
        full_path = self.memory_dir / file_path
        if full_path.exists() and full_path.is_file():
            return full_path.read_text(encoding='utf-8')
        return ""

    def write_memory_file(self, file_path: str, content: str):
        """Write content to a memory file."""
        full_path = self.memory_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')