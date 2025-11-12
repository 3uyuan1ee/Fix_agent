"""CLI的配置、常量和模型创建。"""

import os
import sys
from pathlib import Path

import dotenv
from rich.console import Console
from ..prompt.prompt_template import system_prompt

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

def get_project_version():
    """Get project version from pyproject.toml."""
    try:
        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
                for line in content.split('\n'):
                    if line.strip().startswith('version = '):
                        return line.split('=')[1].strip().strip('"\'')
        return "0.1.0"  # Default version
    except Exception:
        return "0.1.0"


def get_ascii_banner():
    """Generate dynamic ASCII banner with working directory and version."""
    cwd = str(Path.cwd())
    version = get_project_version()

    return f"""
\033[38;2;13;148;136m ███████╗██╗██╗  ██╗    \033[0m
\033[38;2;13;148;136m ██╔════╝██║╚██╗██╔╝    \033[0m
\033[38;2;13;148;136m █████╗  ██║ ╚███╔╝     \033[0m
\033[38;2;13;148;136m ██╔══╝  ██║ ██╔██╗     \033[0m
\033[38;2;13;148;136m ██║     ██║██╔╝ ██╗    \033[0m
\033[38;2;13;148;136m ╚═╝     ╚═╝╚═╝  ╚═╝    \033[0m

\033[1;38;2;30;64;175m  █████╗  ██████╗ ███████╗ ██████╗ ███╗   ██╗████████╗\033[0m
\033[1;38;2;30;64;175m ██╔══██╗██╔════╝ ██╔════╝██╔════╝ ████╗  ██║╚══██╔══╝\033[0m
\033[1;38;2;30;64;175m ███████║██║  ███╗█████╗  ██║  ███╗██╔██╗ ██║   ██║   \033[0m
\033[1;38;2;30;64;175m ██╔══██║██║   ██║██╔══╝  ██║   ██║██║╚██╗██║   ██║   \033[0m
\033[1;38;2;30;64;175m ██║  ██║╚██████╔╝███████╗╚██████╔╝██║ ╚████║   ██║   \033[0m
\033[1;38;2;30;64;175m ╚═╝  ╚═╝ ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   \033[0m

\033[1;38;2;5;150;105m FIX  AGENT  v{version}\033[0m
\033[38;2;5;150;105m Working directory: {cwd}\033[0m
"""

# ASCII art banner function
DEEP_AGENTS_ASCII = get_ascii_banner()

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

    return system_prompt
