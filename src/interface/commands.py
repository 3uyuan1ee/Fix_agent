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

    if command_name == "config":
        return handle_config_command(command_args)

    # 使用震动效果显示未知命令错误
    typewriter.error_shake(f"Unknown command: /{cmd}")
    console.print("[dim]Type /help for available commands.[/dim]")
    console.print()
    return True

    return False


def handle_config_command(args: list[str]) -> bool:
    """Handle /config command to edit .env file.

    Args:
        args: Command arguments (currently unused)

    Returns:
        True if command was handled
    """
    # Find .env file in current directory and parent directories
    env_path = find_env_file()

    if not env_path:
        typewriter.error_shake("❌ .env file not found")
        typewriter.info("Creating a new .env file from template...")
        return create_env_from_template()

    # Check if file exists and is readable
    if not env_path.exists():
        typewriter.error_shake(f"❌ .env file not found: {env_path}")
        return True

    try:
        # Show current configuration status
        typewriter.info(f"📁 Environment file: {env_path}")
        console.print()

        # Load and display current .env content (without sensitive values)
        display_env_status(env_path)

        # Ask user what they want to do
        typewriter.print_with_random_speed("Configuration Options:","primary")
        typewriter.print_fast(
            """""
            Configuration Options:
            1. Edit .env file in external editor
            2. Show current .env content
            3. Create backup
            4. Restore from backup
            5. Cancel
            """""  ,
            "warning"
        )
        console.print()

        # Get user choice
        choice = get_user_choice("Choose an option (1-5): ", ["1", "2", "3", "4", "5"])

        if choice == "1":
            return edit_env_file(env_path)
        elif choice == "2":
            return show_env_content(env_path)
        elif choice == "3":
            return backup_env_file(env_path)
        elif choice == "4":
            return restore_env_file(env_path)
        elif choice == "5":
            typewriter.info("Cancelled configuration editing")
            return True

    except Exception as e:
        typewriter.error_shake(f"❌ Error accessing .env file: {e}")
        return True


def find_env_file() -> Path | None:
    """Find .env file by searching current directory and parent directories."""
    current_dir = Path.cwd()

    # Search up to 5 levels up
    for _ in range(5):
        env_file = current_dir / ".env"
        if env_file.exists():
            return env_file
        current_dir = current_dir.parent

        # Stop at home directory
        if current_dir == Path.home():
            break

    return None


def create_env_from_template() -> bool:
    """Create .env file from .env.template."""
    template_path = Path.cwd() / ".env.template"
    env_path = Path.cwd() / ".env"

    if not template_path.exists():
        typewriter.error_shake("❌ .env.template file not found")
        typewriter.info("Cannot create .env file without template")
        return True

    try:
        # Copy template to .env
        import shutil
        shutil.copy(template_path, env_path)
        typewriter.success(f" Created .env file from template: {env_path}")
        typewriter.info("Please edit the file and add your API keys")
        return True
    except Exception as e:
        typewriter.error_shake(f"❌ Failed to create .env file: {e}")
        return True


def display_env_status(env_path: Path) -> bool:
    """Display current .env configuration status."""
    try:
        import dotenv
        config = dotenv.dotenv_values(env_path)

        console.print("[bold]Current Configuration Status:[/bold]", style=COLORS["primary"])

        # Check API keys
        api_keys_status = []

        if config.get("OPENAI_API_KEY"):
            api_keys_status.append(("OpenAI", " Configured"))
        else:
            api_keys_status.append(("OpenAI", " Not configured"))

        if config.get("ANTHROPIC_API_KEY"):
            api_keys_status.append(("Anthropic", " Configured"))
        else:
            api_keys_status.append(("Anthropic", " Not configured"))

        if config.get("TAVILY_API_KEY"):
            api_keys_status.append(("Tavily Search", " Configured"))
        else:
            api_keys_status.append(("Tavily Search", " Not configured"))

        for service, status in api_keys_status:
            console.print(f"  {service}: {status}")

        console.print()
        return True

    except Exception as e:
        typewriter.error_shake(f" Error reading .env file: {e}")
        return True


def get_user_choice(prompt: str, valid_choices: list[str]) -> str:
    """Get user choice with validation."""
    while True:
        try:
            choice = input(prompt).strip()
            if choice in valid_choices:
                return choice
            typewriter.error_shake(f"Invalid choice. Please enter one of: {', '.join(valid_choices)}")
        except (EOFError, KeyboardInterrupt):
            return "5"  # Default to cancel


def edit_env_file(env_path: Path) -> bool:
    """Edit .env file in external editor."""
    try:
        editor = os.environ.get("EDITOR", "nano")
        typewriter.info(f"Opening {env_path} in {editor}...")

        result = subprocess.run([editor, str(env_path)], check=True)
        typewriter.success(f"✅ Saved changes to {env_path}")

        # Reload environment variables
        import dotenv
        dotenv.load_dotenv(env_path, override=True)

        typewriter.info("🔄 Environment variables reloaded")
        return True

    except subprocess.CalledProcessError as e:
        typewriter.error_shake(f"❌ Editor exited with error: {e}")
        return True
    except Exception as e:
        typewriter.error_shake(f"❌ Error opening editor: {e}")
        return True


def show_env_content(env_path: Path) -> bool:
    """Show .env file content with sensitive values masked."""
    try:
        console.print(f"[bold]Content of {env_path}:[/bold]", style=COLORS["primary"])
        console.print()

        with open(env_path, 'r') as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            line = line.rstrip()
            if line.strip() and not line.strip().startswith("#"):
                # Mask API keys
                if "API_KEY" in line.upper() and "=" in line:
                    key, value = line.split("=", 1)
                    if value.strip():
                        # Show first few characters and mask the rest
                        masked_value = value[:8] + "*" * (len(value) - 8) if len(value) > 8 else "*" * len(value)
                        line = f"{key}={masked_value}"

            # Print line with line number
            console.print(f"[dim]{i:3d}:[/dim] {line}")

        console.print()
        return True

    except Exception as e:
        typewriter.error_shake(f"❌ Error reading .env file: {e}")
        return True


def backup_env_file(env_path: Path) -> bool:
    """Create backup of .env file."""
    try:
        import shutil
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = env_path.parent / f".env.backup.{timestamp}"

        shutil.copy2(env_path, backup_path)
        typewriter.success(f"✅ Backup created: {backup_path}")
        return True

    except Exception as e:
        typewriter.error_shake(f"❌ Failed to create backup: {e}")
        return True


def restore_env_file(env_path: Path) -> bool:
    """Restore .env file from backup."""
    try:
        # Find backup files
        import glob
        backup_pattern = env_path.parent / ".env.backup.*"
        backup_files = sorted(glob.glob(str(backup_pattern)), reverse=True)

        if not backup_files:
            typewriter.error_shake("❌ No backup files found")
            return True

        # List available backups
        console.print("[bold]Available backups:[/bold]", style=COLORS["primary"])
        for i, backup in enumerate(backup_files[:5], 1):  # Show latest 5
            backup_name = Path(backup).name
            timestamp = backup_name.split(".")[-1]
            console.print(f"  {i}. {backup_name}")

        # Get user choice
        choice = get_user_choice("Choose backup to restore (1-5): ", [str(i) for i in range(1, min(len(backup_files), 5) + 1)] + ["cancel"])

        if choice.lower() == "cancel":
            typewriter.info("Cancelled restore operation")
            return True

        # Restore selected backup
        selected_backup = backup_files[int(choice) - 1]
        import shutil
        shutil.copy2(selected_backup, env_path)

        typewriter.success(f"✅ Restored from: {Path(selected_backup).name}")

        # Reload environment variables
        import dotenv
        dotenv.load_dotenv(env_path, override=True)
        typewriter.info("🔄 Environment variables reloaded")

        return True

    except Exception as e:
        typewriter.error_shake(f"❌ Failed to restore backup: {e}")
        return True


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
