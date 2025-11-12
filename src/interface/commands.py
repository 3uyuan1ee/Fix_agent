"""/command和bash执行的命令处理器。"""

import subprocess
import os
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver

from ..config.config import COLORS, DEEP_AGENTS_ASCII, console
from ..ui.ui import TokenTracker, show_interactive_help
from ..ui.dynamicCli import typewriter


def handle_command(command: str, agent, token_tracker: TokenTracker) -> str | bool:
    """Handle slash commands. Returns 'exit' to exit, True if handled, False to pass to agent."""
    cmd = command.lower().strip().lstrip("/")
    parts = cmd.split()
    command_name = parts[0] if parts else ""
    command_args = parts[1:] if len(parts) > 1 else []

    if cmd in ["quit", "exit", "q"]:
        return "exit"

    if command_name == "clear":
        # Reset agent conversation state
        agent.checkpointer = InMemorySaver()

        # Reset token tracking to baseline
        token_tracker.reset()

        # Clear screen and show fresh UI
        console.clear()
        console.print(DEEP_AGENTS_ASCII, style=f"bold {COLORS['primary']}")
        console.print()
        # 使用滑入动画显示重置消息
        typewriter.slide_in_text("Fresh start! Screen cleared and conversation reset.", style="agent")
        console.print()
        return True

    if command_name == "help":
        show_interactive_help()
        return True

    if command_name == "tokens":
        token_tracker.display_session()
        return True

    if command_name == "cd":
        return handle_cd_command(command_args)

    # 使用震动效果显示未知命令错误
    typewriter.error_shake(f"Unknown command: /{cmd}")
    console.print("[dim]Type /help for available commands.[/dim]")
    console.print()
    return True

    return False


def handle_cd_command(args: list[str]) -> bool:
    """Handle /cd command to change directory.
    
    Args:
        args: Command arguments, should contain path to change to
        
    Returns:
        True if command was handled
    """
    if not args:
        # No arguments provided - show current directory and usage
        current_dir = Path.cwd()
        typewriter.info(f"Current directory: {current_dir}")
        typewriter.info("Usage: /cd <path>  - Change to specified directory")
        typewriter.info("       /cd ..      - Go up one level")
        typewriter.info("       /cd ~       - Go to home directory")
        return True

    target_path_str = args[0]
    
    # Handle special paths
    if target_path_str == "~":
        target_path = Path.home()
    elif target_path_str == "..":
        target_path = Path.cwd().parent
    elif target_path_str.startswith("~"):
        # Handle paths like ~/Documents
        home_path = Path.home()
        target_path = home_path / target_path_str[2:]
    else:
        # Handle relative and absolute paths
        target_path = Path(target_path_str)

    # Security validation - prevent path traversal attacks
    if not is_path_safe(target_path):
        typewriter.error_shake(f"❌ Invalid or unsafe path: {target_path_str}")
        typewriter.info("Paths must be within the allowed directories.")
        return True

    try:
        # Resolve path to handle relative paths and check if it exists
        resolved_path = target_path.resolve()
        
        if not resolved_path.exists():
            typewriter.error_shake(f"❌ Directory does not exist: {target_path_str}")
            typewriter.info(f"Resolved path: {resolved_path}")
            return True
            
        if not resolved_path.is_dir():
            typewriter.error_shake(f"❌ Path is not a directory: {target_path_str}")
            typewriter.info(f"Resolved path: {resolved_path}")
            return True
            
        # Change working directory
        os.chdir(resolved_path)
        
        # Show success animation with new directory info
        current_dir = Path.cwd()
        typewriter.success(f" Changed directory to: {current_dir}")
        
        # Display directory contents (like ls -la)
        try:
            console.print()
            console.print("[dim]Directory contents:[/dim]")
            result = subprocess.run(
                ["ls", "-la"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=current_dir
            )
            console.print(result.stdout, style=COLORS["dim"], markup=False)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
            # Fallback to simple ls if ls -la fails
            try:
                result = subprocess.run(
                    ["ls"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=current_dir
                )
                console.print(result.stdout, style=COLORS["dim"], markup=False)
            except Exception:
                console.print("[dim]Unable to list directory contents[/dim]")
        console.print()
        
        return True
        
    except (OSError, ValueError) as e:
        typewriter.error_shake(f"❌ Error changing directory: {e}")
        typewriter.info(f"Target path: {target_path}")
        return True
    except Exception as e:
        typewriter.error_shake(f"❌ Unexpected error: {e}")
        return True


def is_path_safe(path: Path) -> bool:
    """Validate that a path is safe (no path traversal attempts).
    
    Args:
        path: Path to validate
        
    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Resolve path to get absolute path
        resolved_path = path.resolve()
        
        # Check for path traversal attempts
        # We'll allow paths within current working directory and home directory
        current_dir = Path.cwd().resolve()
        home_dir = Path.home().resolve()
        
        # Check if resolved path is within allowed directories
        is_within_current = str(resolved_path).startswith(str(current_dir))
        is_within_home = str(resolved_path).startswith(str(home_dir))
        
        # Allow paths within current directory or home directory
        return is_within_current or is_within_home
        
    except (OSError, ValueError):
        return False


def execute_bash_command(command: str) -> bool:
    """Execute a bash command and display output. Returns True if handled."""
    cmd = command.strip().lstrip("!")

    if not cmd:
        return True

    try:
        console.print()
        console.print(f"[dim]$ {cmd}[/dim]")

        # Execute the command
        result = subprocess.run(
            cmd,
            check=False,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path.cwd(),
        )

        # Display output
        if result.stdout:
            console.print(result.stdout, style=COLORS["dim"], markup=False)
        if result.stderr:
            console.print(result.stderr, style="red", markup=False)

        # Show return code if non-zero
        if result.returncode != 0:
            console.print(f"[dim]Exit code: {result.returncode}[/dim]")

        console.print()
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out after 30 seconds[/red]")
        console.print()
        return True
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")
        console.print()
        return True
