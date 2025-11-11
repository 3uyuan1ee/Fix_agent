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

from ..config.config import (
    COLORS,
    config,
    console,
    get_default_coding_instructions,
    get_system_prompt,
)
from ..midware.agent_memory import AgentMemoryMiddleware


def list_agents():
    """List all available agents."""
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
    """Reset an agent to default or copy from another agent."""
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


def create_agent_with_config(model, assistant_id: str, tools: list):
    """Create and configure an agent with the specified model and tools using our custom architecture."""
    shell_middleware = ResumableShellToolMiddleware(
        workspace_root=os.getcwd(), execution_policy=HostExecutionPolicy()
    )

    # For long-term memory, point to ~/.deepagents/AGENT_NAME/ with /memories/ prefix
    agent_dir = Path.home() / ".deepagents" / assistant_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_md = agent_dir / "agent.md"
    if not agent_md.exists():
        source_content = get_default_coding_instructions()
        agent_md.write_text(source_content)

    # Long-term backend - rooted at agent directory
    # This handles both /memories/ files and /agent.md
    long_term_backend = FilesystemBackend(root_dir=agent_dir, virtual_mode=True)

    # Composite backend: current working directory for default, agent directory for /memories/
    backend = CompositeBackend(
        default=FilesystemBackend(), routes={"/memories/": long_term_backend}
    )

    # Use the same backend for agent memory middleware
    agent_middleware = [
        AgentMemoryMiddleware(backend=long_term_backend, memory_path="/memories/"),
        shell_middleware,
    ]

    # 创建子代理配置
    defect_analyzer_subagent = {
        "name": "defect-analyzer",
        "description": "专门负责分析代码缺陷，包括语法错误、逻辑问题、性能问题和安全隐患",
        "system_prompt": """你是一个专业的代码缺陷分析专家。你的任务是：

1. **语法分析**：检查代码中的语法错误、类型错误、导入错误
2. **逻辑分析**：识别潜在的逻辑漏洞、边界条件处理、空指针异常
3. **性能分析**：发现性能瓶颈、资源泄漏、算法优化机会
4. **安全分析**：检查SQL注入、XSS、权限绕过、敏感信息泄露
5. **代码质量**：评估代码可读性、维护性、设计模式使用

分析完成后，输出详细的缺陷报告，包括：
- 缺陷类型和严重程度
- 具体位置（文件名:行号）
- 缺陷描述和影响
- 修复建议

只进行分析，不要修改代码。""",
        "debug": True,
    }

    # 代码修复代理
    code_fixer_subagent = {
        "name": "code-fixer",
        "description": "专门负责修复代码缺陷，基于缺陷分析报告进行代码修改",
        "system_prompt": """你是一个专业的代码修复专家。你的任务是：

1. **修复语法错误**：修正编译错误、类型不匹配、导入问题
2. **修复逻辑缺陷**：处理边界条件、空指针、异常处理
3. **性能优化**：改进算法、减少资源消耗、优化数据结构
4. **安全加固**：修补安全漏洞、加强输入验证、权限控制
5. **代码重构**：提高代码质量、改善设计、增强可维护性

修复原则：
- 保持代码原有功能不变
- 最小化修改范围
- 添加必要的注释说明
- 确保修复后代码更健壮
- 遵循最佳实践和编码规范

每次修复前说明修复策略，修复后说明改动内容。""",
        "debug": True,
    }

    # 修复验证代理
    fix_validator_subagent = {
        "name": "fix-validator",
        "description": "专门负责验证代码修复的有效性，确保缺陷被正确修复且无新问题",
        "system_prompt": """你是一个专业的代码修复验证专家。你的任务是：

1. **功能验证**：确认修复后代码功能正常，原有行为保持
2. **缺陷验证**：验证原缺陷确实被修复，不会重现
3. **回归测试**：检查修复是否引入新的缺陷或副作用
4. **性能验证**：确认修复没有导致性能退化
5. **安全验证**：确保修复没有引入新的安全风险

验证方法：
- 静态代码分析
- 边界条件测试
- 异常情况模拟
- 性能基准对比
- 安全扫描检查

输出验证报告，包括：
- 修复有效性评估
- 测试结果详情
- 发现的新问题（如有）
- 最终质量评级

如果发现问题，给出具体改进建议。""",
        "debug": True,
    }

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
