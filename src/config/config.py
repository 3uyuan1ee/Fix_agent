"""CLI的配置、常量和模型创建。"""

import os
import sys
from pathlib import Path

import dotenv
from rich.console import Console
from ..prompt.prompt_template import system_prompt

dotenv.load_dotenv()

modelName= os.environ.get("OPENAI_MODEL", "DefaultModel")
baseUrl = os.environ.get("OPENAI_API_BASE",'defaultUrl')

# Color scheme with deep green and deep blue
COLORS = {
    "primary": "#00ffff",  # 青色 - 在深色和浅色背景下都清晰
    "secondary": "#0000ff",  # 蓝色 - 标准终端色彩
    "accent": "#00ff00",  # 绿色 - 明亮易识别
    "dim": "#808080",  # 灰色文本
    "user": "#ffffff",  # 白色 - 用户消息
    "agent": "#00ffff",  # 青色 - AI消息
    "thinking": "#ff00ff",  # 洋红色 - 思考状态
    "tool": "#ffff00",  # 黄色 - 工具调用
    "warning": "#ffff00",  # 黄色 - 警告信息
    "success": "#00ff00",  # 绿色 - 成功状态
    "info": "#0000ff",  # 蓝色 - 信息提示
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
\033[38;2;5;150;105m Using OpenAI model: {modelName}\033[0m
\033[38;2;5;150;105m Base URL: {baseUrl}\033[0m
"""

# ASCII art banner function
DEEP_AGENTS_ASCII = get_ascii_banner()

# Interactive commands
COMMANDS = {
    "clear": "Clear screen and reset conversation",
    "help": "Show help information",
    "tokens": "Show token usage for current session",
    "cd": "Change working directory",
    "config": "Edit .env configuration file",
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

# Rich console 实例
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

    # 获取通用配置
    temperature = float(os.environ.get("MODEL_TEMPERATURE", "0.3"))
    max_tokens = os.environ.get("MODEL_MAX_TOKENS")
    timeout = os.environ.get("MODEL_TIMEOUT")
    max_retries = int(os.environ.get("MODEL_MAX_RETRIES", "3"))

    if openai_key:
        from langchain_openai import ChatOpenAI

        # OpenAI特定配置
        openai_base_url = os.environ.get("OPENAI_API_BASE")
        model_name = os.environ.get("OPENAI_MODEL", "gpt-5-mini")

        # 构建模型参数
        model_kwargs = {
            "model": model_name,
            "temperature": temperature,
            "api_key": openai_key,
        }

        # 添加可选参数
        if openai_base_url:
            model_kwargs["base_url"] = openai_base_url
        if max_tokens:
            model_kwargs["max_tokens"] = int(max_tokens)
        if timeout:
            model_kwargs["timeout"] = float(timeout)
        if max_retries:
            model_kwargs["max_retries"] = max_retries

        return ChatOpenAI(**model_kwargs)

    if anthropic_key:
        from langchain_anthropic import ChatAnthropic

        # Anthropic特定配置
        anthropic_base_url = os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("ANTHROPIC_API_BASE")
        model_name = os.environ.get("ANTHROPIC_MODEL") or os.environ.get("ANTHROPIC_MODEL_NAME", "claude-sonnet-4-5-20250929")

        # 构建模型参数
        model_kwargs = {
            "model_name": model_name,
            "temperature": temperature,
            "api_key": anthropic_key,
        }

        # 添加可选参数
        if anthropic_base_url:
            model_kwargs["base_url"] = anthropic_base_url
        if max_tokens:
            model_kwargs["max_tokens"] = int(max_tokens)
        else:
            model_kwargs["max_tokens"] = 1000000  # Anthropic默认值
        if timeout:
            model_kwargs["timeout"] = float(timeout)
        if max_retries:
            model_kwargs["max_retries"] = max_retries

        console.print(f"[dim]Using Anthropic model: {model_name}[/dim]")
        if anthropic_base_url:
            console.print(f"[dim]Base URL: {anthropic_base_url}[/dim]")

        return ChatAnthropic(**model_kwargs)

    console.print("[bold red]Error:[/bold red] No API key configured.")
    console.print("\nPlease set one of the following environment variables:")
    console.print("  - OPENAI_API_KEY     (for OpenAI models like gpt-5-mini)")
    console.print("  - ANTHROPIC_API_KEY  (for Claude models)")
    console.print("\nOptional base URL configuration:")
    console.print("  - OPENAI_API_BASE    (for custom OpenAI-compatible endpoints)")
    console.print("  - ANTHROPIC_BASE_URL (for custom Anthropic endpoints)")
    console.print("\nExample:")
    console.print("  export OPENAI_API_KEY=your_api_key_here")
    console.print("  export OPENAI_API_BASE=https://your-custom-endpoint.com/v1")
    console.print("\nOr add it to your .env file.")
    sys.exit(1)


def get_system_prompt():

    return system_prompt
