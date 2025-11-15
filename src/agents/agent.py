"""CLI的agent管理和创建。"""

import os
import shutil
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.middleware.resumable_shell import ResumableShellToolMiddleware
from langchain.agents.middleware import HostExecutionPolicy
from langgraph.checkpoint.memory import InMemorySaver

from ..config.config import (COLORS, config, console,
                             get_default_coding_instructions,
                             get_system_prompt)
from ..config.subagent import (code_fixer_subagent, defect_analyzer_subagent,
                               fix_validator_subagent)
from ..midware.agent_memory import AgentMemoryMiddleware
from ..midware.context_enhancement import ContextEnhancementMiddleware
from ..midware.layered_memory import LayeredMemoryMiddleware
from ..midware.logging import LoggingMiddleware
from ..midware.memory_adapter import MemoryMiddlewareFactory
from ..midware.performance_monitor import PerformanceMonitorMiddleware
from ..midware.security import SecurityMiddleware


def list_agents():
    """列出所有可用的agents"""
    agents_dir = Path.home() / ".deepagents"

    if not agents_dir.exists() or not any(agents_dir.iterdir()):
        console.print("[yellow]No agents found.[/yellow]")
        console.print(
            "[dim]Agents will be created in ~/.deepagents/ when you first use them.[/dim]",
            style=COLORS["dim"],
        )
        return

    console.print("\n[bold]Available Agents:[/bold]\n", style=COLORS["primary"])

    for agent_path in sorted(agents_dir.iterdir()):
        if agent_path.is_dir():
            agent_name = agent_path.name
            agent_md = agent_path / "agent.md"

            if agent_md.exists():
                console.print(f"  • [bold]{agent_name}[/bold]", style=COLORS["primary"])
                console.print(f"    {agent_path}", style=COLORS["dim"])
            else:
                console.print(
                    f"  • [bold]{agent_name}[/bold] [dim](incomplete)[/dim]",
                    style=COLORS["tool"],
                )
                console.print(f"    {agent_path}", style=COLORS["dim"])

    console.print()


def reset_agent(agent_name: str, source_agent: str = None):
    """重置agent或复制另一个agent"""
    agents_dir = Path.home() / ".deepagents"
    agent_dir = agents_dir / agent_name

    if source_agent:
        source_dir = agents_dir / source_agent
        source_md = source_dir / "agent.md"

        if not source_md.exists():
            console.print(
                f"[bold red]Error:[/bold red] Source agent '{source_agent}' not found or has no agent.md"
            )
            return

        source_content = source_md.read_text()
        action_desc = f"contents of agent '{source_agent}'"
    else:
        source_content = get_default_coding_instructions()
        action_desc = "default"

    if agent_dir.exists():
        shutil.rmtree(agent_dir)
        console.print(
            f"Removed existing agent directory: {agent_dir}", style=COLORS["tool"]
        )

    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_md = agent_dir / "agent.md"
    agent_md.write_text(source_content)

    console.print(
        f"✓ Agent '{agent_name}' reset to {action_desc}", style=COLORS["primary"]
    )
    console.print(f"Location: {agent_dir}\n", style=COLORS["dim"])


def create_agent_with_config(
    model, assistant_id: str, tools: list, memory_mode: str = "auto"
):
    """使用自定义架构创建并配置具有指定模型和工具的代理"""
    shell_middleware = ResumableShellToolMiddleware(
        workspace_root=os.getcwd(), execution_policy=HostExecutionPolicy()
    )

    # 长期记忆目录, 指向 ~/.deepagents/AGENT_NAME/ with /memories/ prefix
    agent_dir = Path.home() / ".deepagents" / assistant_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_md = agent_dir / "agent.md"
    if not agent_md.exists():
        source_content = get_default_coding_instructions()
        agent_md.write_text(source_content)

    # 长期记忆后端 - rooted at agent directory
    # 处理 /memories/ files 和 /agent.md
    # virtual_mode放置路径遍历攻击
    long_term_backend = FilesystemBackend(root_dir=agent_dir, virtual_mode=True)

    # Composite backend: current working directory for default, agent directory for /memories/
    backend = CompositeBackend(
        default=FilesystemBackend(), routes={"/memories/": long_term_backend}
    )

    # 建中间件管道
    agent_middleware = []

    console.print("[bold blue]🏗️  正在构建中间件管道系统...[/bold blue]")

    # 第一层：全局监控（最外层）
    # 1. 性能监控中间件
    try:
        performance_middleware = PerformanceMonitorMiddleware(
            backend=long_term_backend,
            metrics_path="/performance/",
            enable_system_monitoring=True,
            max_records=1000,
        )
        agent_middleware.append(performance_middleware)
        console.print("[green]✓[/green] 性能监控中间件 (最外层)")
    except Exception as e:
        console.print(f"[yellow]⚠ 性能监控中间件失败: {e}[/yellow]")

    # 2. 日志记录中间件
    try:
        logging_middleware = LoggingMiddleware(
            backend=long_term_backend,
            session_id=assistant_id,
            log_path="/logs/",
            enable_conversation_logging=True,
            enable_tool_logging=True,
            enable_performance_logging=True,
            enable_error_logging=True,
        )
        agent_middleware.append(logging_middleware)
        console.print("[green]✓[/green] 日志记录中间件")
    except Exception as e:
        console.print(f"[yellow]⚠ 日志记录中间件失败: {e}[/yellow]")

    # 第二层：上下文增强
    # 3. 上下文增强中间件
    try:
        context_middleware = ContextEnhancementMiddleware(
            backend=long_term_backend,
            context_path="/context/",
            enable_project_analysis=True,
            enable_user_preferences=True,
            enable_conversation_enhancement=True,
            max_context_length=4000,
        )
        agent_middleware.append(context_middleware)
        console.print("[green]✓[/green] 上下文增强中间件")
    except Exception as e:
        console.print(f"[yellow]⚠ 上下文增强中间件失败: {e}[/yellow]")

    # 4. 分层记忆中间件（在上下文增强之后，框架之前）
    try:
        memory_middleware = MemoryMiddlewareFactory.auto_upgrade_memory(
            backend=long_term_backend,
            memory_path="/memories/",
            enable_layered=None,  # 自动检测
            working_memory_size=10,
            enable_semantic_memory=True,
            enable_episodic_memory=True,
        )

        if isinstance(memory_middleware, list):
            # 混合模式，返回多个中间件
            agent_middleware.extend(memory_middleware)
            console.print("[green]✓[/green] 分层记忆系统 (混合模式)")
        else:
            # 单个中间件
            agent_middleware.append(memory_middleware)
            if hasattr(memory_middleware, "__class__"):
                if isinstance(memory_middleware, LayeredMemoryMiddleware):
                    console.print("[green]✓[/green] 分层记忆系统")
                elif isinstance(memory_middleware, AgentMemoryMiddleware):
                    console.print("[green]✓[/green] 传统记忆系统")

    except Exception as e:
        # 如果分层记忆失败，回退到传统记忆
        console.print(f"[yellow]⚠ 记忆系统失败，使用传统模式: {e}[/yellow]")
        agent_middleware.append(
            AgentMemoryMiddleware(backend=long_term_backend, memory_path="/memories/")
        )

    # 第三层：框架默认中间件（会自动追加到这里）
    # 框架会自动添加：TodoList, Filesystem, SubAgent, Summarization, Caching, PatchToolCalls
    console.print(
        """[green]✓[/green] 任务管理,文件系统操作,子代理管理,对话摘要,提示缓存,工具调用补丁中间件"""
    )

    # 第四层：工具层（最内层）
    # 5. 安全检查中间件
    try:
        security_middleware = SecurityMiddleware(
            backend=long_term_backend,
            security_level="medium",
            workspace_root=os.getcwd(),
            enable_file_security=True,
            enable_command_security=True,
            enable_content_security=True,
            allow_path_traversal=False,
            max_file_size=10 * 1024 * 1024,  # 10MB
        )
        agent_middleware.append(security_middleware)
        console.print("[green]✓[/green] 安全检查中间件")
    except Exception as e:
        console.print(f"[yellow]⚠ 安全检查中间件失败: {e}[/yellow]")

    # 6. Shell工具中间件（最内层）
    agent_middleware.append(shell_middleware)
    console.print("[green]✓[/green] Shell工具中间件 (最内层)")

    console.print(
        f"[bold green]🎉 中间件管道构建完成！共 {len(agent_middleware)} 个中间件[/bold green]"
    )

    # 创建subagents
    subagents = [defect_analyzer_subagent, code_fixer_subagent, fix_validator_subagent]

    # Helper functions for formatting tool descriptions in HITL prompts
    def format_write_file_description(tool_call: dict) -> str:
        """Format write_file tool call for approval prompt."""
        args = tool_call.get("args", {})
        file_path = args.get("file_path", "unknown")
        content = args.get("content", "")

        action = "Overwrite" if os.path.exists(file_path) else "Create"
        line_count = len(content.splitlines())
        size = len(content.encode("utf-8"))

        return f"File: {file_path}\nAction: {action} file\nLines: {line_count} · Bytes: {size}"

    def format_edit_file_description(tool_call: dict) -> str:
        """Format edit_file tool call for approval prompt."""
        args = tool_call.get("args", {})
        file_path = args.get("file_path", "unknown")
        old_string = args.get("old_string", "")
        new_string = args.get("new_string", "")
        replace_all = bool(args.get("replace_all", False))

        delta = len(new_string) - len(old_string)

        return (
            f"File: {file_path}\n"
            f"Action: Replace text ({'all occurrences' if replace_all else 'single occurrence'})\n"
            f"Snippet delta: {delta:+} characters"
        )

    def format_web_search_description(tool_call: dict) -> str:
        """Format web_search tool call for approval prompt."""
        args = tool_call.get("args", {})
        query = args.get("query", "unknown")
        max_results = args.get("max_results", 5)

        return f"Query: {query}\nMax results: {max_results}\n\n⚠️  This will use Tavily API credits"

    def format_task_description(tool_call: dict) -> str:
        """Format task (subagent) tool call for approval prompt."""
        args = tool_call.get("args", {})
        description = args.get("description", "unknown")
        prompt = args.get("prompt", "")

        # Truncate prompt if too long
        prompt_preview = prompt[:300]
        if len(prompt) > 300:
            prompt_preview += "..."

        return (
            f"Task: {description}\n\n"
            f"Instructions to subagent:\n"
            f"{'─' * 40}\n"
            f"{prompt_preview}\n"
            f"{'─' * 40}\n\n"
            f"⚠️  Subagent will have access to file operations and shell commands"
        )

    # Configure human-in-the-loop for potentially destructive tools
    from langchain.agents.middleware import InterruptOnConfig

    shell_interrupt_config: InterruptOnConfig = {
        "allowed_decisions": ["approve", "reject"],
        "description": lambda tool_call, state, runtime: (
            f"Shell Command: {tool_call['args'].get('command', 'N/A')}\n"
            f"Working Directory: {os.getcwd()}"
        ),
    }

    write_file_interrupt_config: InterruptOnConfig = {
        "allowed_decisions": ["approve", "reject"],
        "description": lambda tool_call, state, runtime: format_write_file_description(
            tool_call
        ),
    }

    edit_file_interrupt_config: InterruptOnConfig = {
        "allowed_decisions": ["approve", "reject"],
        "description": lambda tool_call, state, runtime: format_edit_file_description(
            tool_call
        ),
    }

    web_search_interrupt_config: InterruptOnConfig = {
        "allowed_decisions": ["approve", "reject"],
        "description": lambda tool_call, state, runtime: format_web_search_description(
            tool_call
        ),
    }

    task_interrupt_config: InterruptOnConfig = {
        "allowed_decisions": ["approve", "reject"],
        "description": lambda tool_call, state, runtime: format_task_description(
            tool_call
        ),
    }

    agent = create_deep_agent(
        model=model,
        system_prompt=get_system_prompt(),
        tools=tools,
        backend=backend,
        middleware=agent_middleware,
        subagents=subagents,
        interrupt_on={
            "shell": shell_interrupt_config,
            "write_file": write_file_interrupt_config,
            "edit_file": edit_file_interrupt_config,
            "web_search": web_search_interrupt_config,
            "task": task_interrupt_config,
        },
    ).with_config(config)

    agent.checkpointer = InMemorySaver()

    return agent


def get_current_assistant_id() -> str:
    """获取当前助手ID。

    Returns:
        str: 当前助手ID，如果无法获取则返回默认值
    """
    try:
        # 尝试从环境变量获取
        if os.getenv("ASSISTANT_ID"):
            return os.getenv("ASSISTANT_ID")

        # 尝试从当前工作目录推断
        cwd = Path.cwd()

        # 如果在项目中，尝试使用项目名
        if (cwd / "pyproject.toml").exists():
            try:
                import toml

                pyproject = toml.load(cwd / "pyproject.toml")
                project_name = pyproject.get("project", {}).get("name")
                if project_name:
                    return project_name.replace("-", "_").replace(" ", "_")
            except:
                pass

        # 如果在Fix Agent目录中，使用特殊标识
        if "Fix Agent" in str(cwd) or "fix_agent" in str(cwd):
            return "fix_agent"

        # 使用目录名作为备用
        return cwd.name.replace(" ", "_").replace("-", "_")

    except Exception:
        # 最后的备用选项
        return "default_assistant"
