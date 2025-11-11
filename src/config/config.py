"""CLI的配置、常量和模型创建。"""

import os
import sys
from pathlib import Path

import dotenv
from rich.console import Console

dotenv.load_dotenv()

# Color scheme with deep green and deep blue
COLORS = {
    "primary": "#0d9488",  # 深蓝绿色
    "secondary": "#1e40af",  # 深蓝色
    "accent": "#059669",  # 深绿色
    "dim": "#475569",
    "user": "#f8fafc",
    "agent": "#0d9488",
    "thinking": "#0891b2",
    "tool": "#d97706",
    "warning": "#eab308",  # 黄色用于警告
    "success": "#22c55e",  # 绿色用于成功
    "info": "#3b82f6",  # 蓝色用于信息
}

# ASCII art banner - Defect FUcKeR in deep green and blue style
DEEP_AGENTS_ASCII = """
\033[38;2;13;148;136m ██████╗ ███████╗███████╗███████╗ ██████╗████████╗\033[0m
\033[38;2;13;148;136m ██╔══██╗██╔════╝██╔════╝██╔════╝██╔════╝╚══██╔══╝\033[0m
\033[38;2;13;148;136m ██║  ██║█████╗  █████╗  █████╗  ██║        ██║   \033[0m
\033[38;2;13;148;136m ██║  ██║██╔══╝  ██╔══╝  ██╔══╝  ██║        ██║   \033[0m
\033[38;2;13;148;136m ██████╔╝███████╗██║     ███████╗╚██████╗   ██║   \033[0m
\033[38;2;13;148;136m ╚═════╝ ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   \033[0m

\033[38;2;30;64;175m ███████╗██╗   ██╗ ██████╗██╗  ██╗███████╗██████╗ \033[0m
\033[38;2;30;64;175m ██╔════╝██║   ██║██╔════╝██║ ██╔╝██╔════╝██╔══██╗\033[0m
\033[38;2;30;64;175m █████╗  ██║   ██║██║     █████╔╝ █████╗  ██████╔╝\033[0m
\033[38;2;30;64;175m ██╔══╝  ██║   ██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗\033[0m
\033[38;2;30;64;175m ██║     ╚██████╔╝╚██████╗██║  ██╗███████╗██║  ██║\033[0m
\033[38;2;30;64;175m ╚═╝      ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝\033[0m

\033[38;2;5;150;105m ╔═══════════════════════════════════════════════════╗\033[0m
\033[38;2;5;150;105m ║                DEFECT  FUCKER                     ║\033[0m
\033[38;2;5;150;105m ╚═══════════════════════════════════════════════════╝\033[0m
"""
# Interactive commands
COMMANDS = {
    "clear": "Clear screen and reset conversation",
    "help": "Show help information",
    "tokens": "Show token usage for current session",
    "quit": "Exit the CLI",
    "exit": "Exit the CLI",
}

# Common bash commands for autocomplete
COMMON_BASH_COMMANDS = {
    "ls": "List directory contents",
    "ls -la": "List all files with details",
    "cd": "Change directory",
    "pwd": "Print working directory",
    "cat": "Display file contents",
    "grep": "Search text patterns",
    "find": "Find files",
    "mkdir": "Make directory",
    "rm": "Remove file",
    "cp": "Copy file",
    "mv": "Move/rename file",
    "echo": "Print text",
    "touch": "Create empty file",
    "head": "Show first lines",
    "tail": "Show last lines",
    "wc": "Count lines/words",
    "chmod": "Change permissions",
}

# Maximum argument length for display
MAX_ARG_LENGTH = 150

# Agent configuration
config = {"recursion_limit": 1000}

# Rich console instance
console = Console(highlight=False)


class SessionState:
    """Holds mutable session state (auto-approve mode, etc)."""

    def __init__(self, auto_approve: bool = False):
        self.auto_approve = auto_approve

    def toggle_auto_approve(self) -> bool:
        """Toggle auto-approve and return new state."""
        self.auto_approve = not self.auto_approve
        return self.auto_approve


def get_default_coding_instructions() -> str:
    """Get the default coding agent instructions.

    These are the immutable base instructions that cannot be modified by the agent.
    Long-term memory (agent.md) is handled separately by the middleware.
    """
    default_prompt_path = Path(__file__).parent / "default_agent_prompt.md"
    return default_prompt_path.read_text()


def create_model():
    """Create the appropriate model based on available API keys.

    Returns:
        ChatModel instance (OpenAI or Anthropic)

    Raises:
        SystemExit if no API key is configured
    """
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if openai_key:
        from langchain_openai import ChatOpenAI

        model_name = os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        console.print(f"[dim]Using OpenAI model: {model_name}[/dim]")
        return ChatOpenAI(
            model=model_name,
            temperature=0.3,
        )
    if anthropic_key:
        from langchain_anthropic import ChatAnthropic

        model_name = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
        console.print(f"[dim]Using Anthropic model: {model_name}[/dim]")
        return ChatAnthropic(
            model_name=model_name,
            max_tokens=20000,
        )
    console.print("[bold red]Error:[/bold red] No API key configured.")
    console.print("\nPlease set one of the following environment variables:")
    console.print("  - OPENAI_API_KEY     (for OpenAI models like gpt-5-mini)")
    console.print("  - ANTHROPIC_API_KEY  (for Claude models)")
    console.print("\nExample:")
    console.print("  export OPENAI_API_KEY=your_api_key_here")
    console.print("\nOr add it to your .env file.")
    sys.exit(1)


def get_system_prompt():

    # 创建主协调代理的系统提示
    system_prompt = f"""### Current Working Directory

The filesystem backend is currently operating in: `{Path.cwd()}`

### Memory System Reminder

Your long-term memory is stored in /memories/ and persists across sessions.

**IMPORTANT - Check memories before answering:**
- When asked "what do you know about X?" → Run `ls /memories/` FIRST, then read relevant files
- When starting a task → Check if you have guides or examples in /memories/
- At the beginning of new sessions → Consider checking `ls /memories/` to see what context you have

Base your answers on saved knowledge (from /memories/) when available, supplemented by general knowledge.

### Human-in-the-Loop Tool Approval

Some tool calls require user approval before execution. When a tool call is rejected by the user:
1. Accept their decision immediately - do NOT retry the same command
2. Explain that you understand they rejected the action
3. Suggest an alternative approach or ask for clarification
4. Never attempt the exact same rejected command again

Respect the user's decisions and work with them collaboratively.

### Web Search Tool Usage

When you use the web_search tool:
1. The tool will return search results with titles, URLs, and content excerpts
2. You MUST read and process these results, then respond naturally to the user
3. NEVER show raw JSON or tool results directly to the user
4. Synthesize the information from multiple sources into a coherent answer
5. Cite your sources by mentioning page titles or URLs when relevant
6. If the search doesn't find what you need, explain what you found and ask clarifying questions

The user only sees your text responses - not tool results. Always provide a complete, natural language answer after using web_search.

### Todo List Management

When using the write_todos tool:
1. Keep the todo list MINIMAL - aim for 3-6 items maximum
2. Only create todos for complex, multi-step tasks that truly need tracking
3. Break down work into clear, actionable items without over-fragmenting
4. For simple tasks (1-2 steps), just do them directly without creating todos
5. When first creating a todo list for a task, ALWAYS ask the user if the plan looks good before starting work
   - Create the todos, let them render, then ask: "Does this plan look good?" or similar
   - Wait for the user's response before marking the first todo as in_progress
   - If they want changes, adjust the plan accordingly
6. Update todo status promptly as you complete each item

The todo list is a planning tool - use it judiciously to avoid overwhelming the user with excessive task tracking.
你是一个代码缺陷修复协调专家。你有三个专业的子代理来帮助你完成代码分析和修复工作：

**你的子代理团队：**
1. **defect-analyzer** (缺陷分析专家) - 专门分析代码中的各种缺陷
2. **code-fixer** (代码修复专家) - 专门修复已发现的代码缺陷
3. **fix-validator** (修复验证专家) - 专门验证修复的有效性

**工作流程：**
当用户需要分析或修复代码时，请按以下顺序协调：

1. **第一步：分析缺陷**
   - 调用 defect-analyzer 进行全面的代码缺陷分析
   - 获取详细的缺陷报告

2. **第二步：修复代码**
   - 将缺陷报告传递给 code-fixer
   - 进行针对性的代码修复

3. **第三步：验证修复**
   - 让 fix-validator 验证修复的有效性
   - 确保缺陷被正确修复且无新问题

**注意事项：**
- 始终按照分析→修复→验证的顺序进行
- 每个步骤都要让对应的专门代理处理
- 向用户报告每个阶段的进展和结果
- 如果验证发现问题，需要重新进行修复和验证

**文件操作规则：**
- 只在当前workspace目录下创建和修改文件
- 绝不使用系统目录如 /tmp/
- 使用相对路径进行文件操作

现在请协调你的专业团队来帮助用户完成代码缺陷分析和修复任务。"""

    return system_prompt
