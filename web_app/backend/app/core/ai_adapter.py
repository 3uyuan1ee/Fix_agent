"""AI model adapter that wraps the CLI's AI logic for web use."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, AsyncGenerator

# 导入应用配置
from .config import settings

# 添加CLI项目路径到Python路径
# 从 backend/app/core/ai_adapter.py 到 Fix Agent/src 的路径是向上5级
cli_root = Path(__file__).parent.parent.parent.parent.parent / "src"
if cli_root.exists():
    sys.path.insert(0, str(cli_root))
    # 同时添加Fix Agent根目录到路径，以便相对导入正常工作
    fix_agent_root = cli_root.parent
    sys.path.insert(0, str(fix_agent_root))
    print(f"✅ CLI root added to path: {cli_root}")
    print(f"✅ Fix Agent root added to path: {fix_agent_root}")
else:
    print(f"❌ CLI root not found at: {cli_root}")
    # 尝试不同的路径
    alt_paths = [
        Path(__file__).parent.parent.parent.parent / "src",  # 向上4级
        Path(__file__).parent.parent.parent / "src",  # 向上3级
    ]
    for alt_path in alt_paths:
        if alt_path.exists():
            sys.path.insert(0, str(alt_path))
            print(f"✅ CLI root found at alternative path: {alt_path}")
            break

# 延迟导入CLI模块
def _import_cli_modules():
    """Import CLI modules safely."""
    try:
        from src.agents.agent import create_agent_with_config
        from src.config.config import create_model
        from src.tools.tools import get_all_tools
        from src.midware.agent_memory import AgentMemoryMiddleware
        from src.midware.performance_monitor import PerformanceMonitorMiddleware
        from deepagents.backends.filesystem import FilesystemBackend
        from deepagents.backends.composite import CompositeBackend
        from deepagents.middleware.resumable_shell import ResumableShellToolMiddleware
        from langchain.agents.middleware import HostExecutionPolicy
        from langgraph.checkpoint.memory import InMemorySaver

        return {
            'create_agent_with_config': create_agent_with_config,
            'create_model': create_model,
            'get_all_tools': get_all_tools,
            'AgentMemoryMiddleware': AgentMemoryMiddleware,
            'PerformanceMonitorMiddleware': PerformanceMonitorMiddleware,
            'FilesystemBackend': FilesystemBackend,
            'CompositeBackend': CompositeBackend,
            'ResumableShellToolMiddleware': ResumableShellToolMiddleware,
            'HostExecutionPolicy': HostExecutionPolicy,
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
        workspace_root = Path(settings.workspace_root)
        self.session_dir = workspace_root / "sessions" / session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # 记忆目录
        self.memory_dir = workspace_root / "memories" / session_id
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 流式处理状态
        self.pending_text = ""  # 累积的文本缓冲
        self.tool_call_buffers = {}  # 工具调用缓冲区
        self.last_chunk_time = 0  # 最后发送chunk的时间
        self.chunk_timeout = 0.5  # chunk超时时间（秒）- 增加超时时间
        self.is_thinking = False  # AI思考状态
        self.sent_thinking = False  # 是否已发送思考状态

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

            print(f"✅ AI Agent initialized for session {self.session_id}")

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
                execution_policy=cli_modules['HostExecutionPolicy']()
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

            # 性能监控中间件（可选）
            performance_middleware = None
            try:
                performance_middleware = cli_modules['PerformanceMonitorMiddleware'](
                    backend=long_term_backend,
                    metrics_path="/performance/",
                    enable_system_monitoring=True,
                    max_records=1000
                )
            except Exception as e:
                print(f"Warning: Performance monitoring middleware disabled: {e}")

            # 构建中间件列表
            middleware_list = [memory_middleware, shell_middleware]
            if performance_middleware:
                middleware_list.insert(0, performance_middleware)  # 性能监控放在最外层

            return middleware_list
        except Exception as e:
            print(f"Failed to create middleware: {e}")
            return []

    async def stream_response(self, message: str, file_references: List[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
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

            # 流结束时，强制刷新所有剩余的文本
            final_chunks = self.flush_pending_text(final=True)
            for final_chunk in final_chunks:
                yield final_chunk

        except Exception as e:
            print(f"Error in AI streaming: {e}")
            # 即使出错也要尝试刷新缓冲的文本
            error_chunks = self.flush_pending_text(final=True)
            for chunk in error_chunks:
                yield chunk

            yield {
                "type": "error",
                "content": f"AI响应错误: {str(e)}",
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
        """Process streaming chunk from AI agent with CLI-style buffering."""
        import time

        if not isinstance(chunk, tuple) or len(chunk) != 3:
            return None

        namespace, stream_mode, data = chunk
        current_time = time.time()
        results = []

        if stream_mode == "messages":
            if isinstance(data, tuple) and len(data) == 2:
                message, metadata = data

                # 发送思考状态（如果还没有发送）
                if not self.sent_thinking and self.pending_text == "":
                    self.is_thinking = True
                    self.sent_thinking = True
                    return {
                        "type": "status",
                        "content": "AI正在思考...",
                        "session_id": self.session_id,
                        "metadata": {"state": "thinking"}
                    }

                # 处理AI消息
                if hasattr(message, 'content_blocks'):
                    for block in message.content_blocks:
                        if block.get("type") == "text":
                            # 累积文本到缓冲区
                            text_content = block.get("text", "")
                            if text_content:
                                self.pending_text += text_content
                                self.last_chunk_time = current_time
                                self.is_thinking = False  # 有文本内容，说明不在思考

                        elif block.get("type") == "tool_call_chunk":
                            # 处理工具调用块
                            tool_name = block.get("name")
                            tool_args = block.get("args", {})
                            tool_call_id = block.get("id", "default")

                            # 缓冲工具调用数据
                            if tool_call_id not in self.tool_call_buffers:
                                self.tool_call_buffers[tool_call_id] = {
                                    "name": tool_name,
                                    "args": "",
                                    "complete": False
                                }

                            buffer = self.tool_call_buffers[tool_call_id]
                            if tool_args:
                                buffer["args"] += tool_args

                            # 检查工具调用是否完成
                            if block.get("complete", False):
                                buffer["complete"] = True
                                results.append({
                                    "type": "tool_call",
                                    "tool": buffer["name"],
                                    "args": buffer["args"],
                                    "session_id": self.session_id,
                                    "tool_call_id": tool_call_id,
                                    "complete": True
                                })
                                del self.tool_call_buffers[tool_call_id]

        elif stream_mode == "updates":
            # 处理更新消息（包括HITL中断）
            if isinstance(data, dict):
                if "__interrupt__" in data:
                    # HITL批准请求
                    interrupt_data = data["__interrupt__"]
                    if interrupt_data and interrupt_data.get("action_requests"):
                        results.append({
                            "type": "approval_request",
                            "approval_data": interrupt_data,
                            "session_id": self.session_id
                        })

                elif "todos" in data:
                    # 待办事项更新
                    results.append({
                        "type": "todos",
                        "todos": data["todos"],
                        "session_id": self.session_id
                    })

        # 更智能的文本发送策略
        should_flush_text = False
        if self.pending_text:
            # 检查多个条件
            time_elapsed = current_time - self.last_chunk_time
            text_length = len(self.pending_text)

            # 条件1：时间超过阈值
            if time_elapsed > self.chunk_timeout:
                should_flush_text = True

            # 条件2：文本长度足够且包含完整句子
            elif text_length > 20 and self._has_complete_sentence(self.pending_text):
                should_flush_text = True

            # 条件3：文本很长（超过100字符）
            elif text_length > 100:
                should_flush_text = True

        if should_flush_text:
            text_to_send = self.pending_text.rstrip()
            if text_to_send:
                results.append({
                    "type": "message",
                    "content": text_to_send,
                    "session_id": self.session_id,
                    "is_stream": True
                })
                self.pending_text = ""
                self.last_chunk_time = current_time

        # 返回结果（优先返回工具调用和状态，然后是文本）
        if results:
            # 重新排序，优先级：状态 > 工具调用 > 其他 > 文本
            status_messages = [r for r in results if r.get("type") == "status"]
            tool_messages = [r for r in results if r.get("type") == "tool_call"]
            other_messages = [r for r in results if r.get("type") not in ["status", "tool_call", "message"]]
            text_messages = [r for r in results if r.get("type") == "message"]

            if status_messages:
                return status_messages[0]
            elif tool_messages:
                return tool_messages[0]
            elif other_messages:
                return other_messages[0]
            elif text_messages:
                return text_messages[0]

        return None

    def _has_complete_sentence(self, text: str) -> bool:
        """检查文本是否包含完整的句子。"""
        # 检查是否以句子结束符结尾
        end_chars = ['.', '!', '?', '\n']
        return any(text.strip().endswith(char) for char in end_chars) and len(text.strip()) > 10

    def flush_pending_text(self, final: bool = False):
        """强制刷新累积的文本缓冲区。"""
        results = []
        if self.pending_text and (final or self.pending_text.strip()):
            text_to_send = self.pending_text.rstrip()
            if text_to_send:
                results.append({
                    "type": "message",
                    "content": text_to_send,
                    "session_id": self.session_id,
                    "is_stream": not final
                })
                self.pending_text = ""

        # 流结束时重置思考状态
        if final:
            self.sent_thinking = False
            self.is_thinking = False

        return results

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