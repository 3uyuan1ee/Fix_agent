"""/command和bash执行的命令处理器。"""

import importlib.resources
import os
import subprocess
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.memory import InMemorySaver

from ..agents.agent import get_current_assistant_id
from ..config.config import COLORS, DEEP_AGENTS_ASCII, console
from ..ui.dynamicCli import typewriter
from ..ui.ui import TokenTracker, show_interactive_help
from .memory_commands import (MemoryManager, handle_memory_backup,
                              handle_memory_clear, handle_memory_edit,
                              handle_memory_export, handle_memory_import,
                              handle_memory_restore, handle_memory_search,
                              handle_memory_stats, show_memory_menu,
                              view_agent_memory)


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
        typewriter.slide_in_text(
            "Fresh start! Screen cleared and conversation reset.", style="agent"
        )
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

    if command_name in ["sys", "system", "info"]:
        return handle_system_info_command(command_args)

    if command_name in ["services", "svc"]:
        return handle_services_command(command_args)

    if command_name == "memory":
        return handle_memory_command(agent, command_args)

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
        typewriter.print_with_random_speed("Configuration Options:", "primary")
        typewriter.print_fast(
            """""
            Configuration Options:
            1. Edit .env file in external editor
            2. Show current .env content
            3. Create backup
            4. Restore from backup
            5. Cancel
            """
            "",
            "warning",
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
    """Find .env file by searching package directory first, then current directory and parent directories."""

    # 首先检查包目录下的.env文件
    try:
        import Fix_agent
        package_dir = Path(Fix_agent.__file__).parent
        env_file = package_dir / ".env"
        if env_file.exists():
            return env_file
    except ImportError:
        pass

    # 备用：搜索当前目录和父目录
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

    # 在包目录下保存.env文件
    try:
        import Fix_agent
        package_dir = Path(Fix_agent.__file__).parent
    except ImportError:
        # 如果无法导入包，使用当前目录
        package_dir = Path.cwd()

    env_path = package_dir / ".env"

    # 先尝试当前目录的模板，再尝试包目录的模板
    template_content = None
    if template_path.exists():
        try:
            template_content = template_path.read_text(encoding="utf-8")
        except Exception:
            pass

    if template_content is None:
        # 备用方案：从包安装目录获取模板内容
        template_content = get_env_template_content_from_package()
        if template_content is None:
            typewriter.error_shake("❌ .env.template file not found")
            typewriter.info("Cannot create .env file without template")
            return True

    try:
        # Write template content to .env file
        env_path.write_text(template_content, encoding="utf-8")
        typewriter.success(f"✅ Created .env file from template: {env_path}")
        typewriter.info("Please edit the file and add your API keys")
        return True
    except Exception as e:
        typewriter.error_shake(f"❌ Failed to create .env file: {e}")
        return True


def get_env_template_content_from_package() -> Optional[str]:
    """从包安装目录读取.env.template文件内容"""
    try:
        # 尝试使用importlib.resources读取包数据
        with importlib.resources.open_text(".", ".env.template") as f:
            return f.read()
    except Exception:
        try:
            # 备用方案：尝试从包根目录读取
            import Fix_agent
            package_dir = Path(Fix_agent.__file__).parent
            template_path = package_dir / ".env.template"
            if template_path.exists():
                return template_path.read_text(encoding="utf-8")
        except Exception:
            pass

    # 如果以上方法都失败，返回内置的默认模板
    return get_default_env_template()


def get_default_env_template() -> str:
    """返回默认的.env模板内容"""
    return """# Fix Agent 环境配置模板
# 填入你的实际配置后将文件名改为.env

# =============================================================================
# 网络搜索配置 (可选)
# =============================================================================
# Tavily API Key - 用于网络搜索功能
# 获取地址: https://tavily.com
# TAVILY_API_KEY=your_tavily_api_key_here

# =============================================================================
# Anthropic Claude 配置
# =============================================================================
# Anthropic API Key
# 获取地址: https://console.anthropic.com
# ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Anthropic 模型名称
# 可选值: claude-sonnet-4-5-20250929, claude-sonnet-4-5-20250402, claude-opus-4-20250229
# ANTHROPIC_MODEL_NAME=claude-sonnet-4-5-20250929

# =============================================================================
# OpenAI 兼容模型配置
# =============================================================================
# OpenAI API Key
# 获取地址: https://platform.openai.com
# OPENAI_API_KEY=your_openai_api_key_here

# OpenAI 模型名称
# 可选值: gpt-4, gpt-4-turbo, gpt-5-mini, gpt-3.5-turbo
# OPENAI_MODEL=gpt-4

# =============================================================================
# 通用模型配置 (适用于所有模型)
# =============================================================================
# 模型温度参数 - 控制输出的随机性 (0.0-2.0)
MODEL_TEMPERATURE=0.3

# 最大输出token数
MODEL_MAX_TOKENS=50000

# 最大重试次数
MODEL_MAX_RETRIES=3

# =============================================================================
# 系统配置
# =============================================================================
# 调试模式 - 显示详细的调试信息
# DEBUG=false

# 人机交互模式 - 是否需要用户确认工具调用
# HUMAN_IN_LOOP=true

# 持久化存储 - 是否保存会话记忆
# PERSISTENT_STORAGE=false
"""


def display_env_status(env_path: Path) -> bool:
    """Display current .env configuration status."""
    try:
        import dotenv

        config = dotenv.dotenv_values(env_path)

        console.print(
            "[bold]Current Configuration Status:[/bold]", style=COLORS["primary"]
        )

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
            typewriter.error_shake(
                f"Invalid choice. Please enter one of: {', '.join(valid_choices)}"
            )
        except (EOFError, KeyboardInterrupt):
            return "5"  # Default to cancel


def edit_env_file(env_path: Path) -> bool:
    """Edit .env file in external editor."""
    try:
        import platform

        # 跨平台编辑器选择
        if platform.system() == "Windows":
            editor = os.environ.get("EDITOR", "notepad")
        else:
            editor = os.environ.get("EDITOR", "nano")

        typewriter.info(f"Opening {env_path} in {editor}...")

        # Windows特殊处理
        if platform.system() == "Windows" and editor == "notepad":
            result = subprocess.run(["notepad", str(env_path)], check=True)
        else:
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
    except FileNotFoundError:
        typewriter.error_shake(
            f"❌ Editor '{editor}' not found. Please set EDITOR environment variable."
        )
        typewriter.info(
            "Windows users can set EDITOR=notepad or EDITOR=path/to/your/editor"
        )
        return True
    except Exception as e:
        typewriter.error_shake(f"❌ Error opening editor: {e}")
        return True


def show_env_content(env_path: Path) -> bool:
    """Show .env file content with sensitive values masked."""
    try:
        console.print(f"[bold]Content of {env_path}:[/bold]", style=COLORS["primary"])
        console.print()

        with open(env_path, "r") as f:
            lines = f.readlines()

        for i, line in enumerate(lines, 1):
            line = line.rstrip()
            if line.strip() and not line.strip().startswith("#"):
                # Mask API keys
                if "API_KEY" in line.upper() and "=" in line:
                    key, value = line.split("=", 1)
                    if value.strip():
                        # Show first few characters and mask the rest
                        masked_value = (
                            value[:8] + "*" * (len(value) - 8)
                            if len(value) > 8
                            else "*" * len(value)
                        )
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
        choice = get_user_choice(
            "Choose backup to restore (1-5): ",
            [str(i) for i in range(1, min(len(backup_files), 5) + 1)] + ["cancel"],
        )

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

        # Display directory contents (cross-platform)
        try:
            console.print()
            console.print("[dim]Directory contents:[/dim]")

            # 使用Python内置功能，避免依赖系统命令
            import platform

            if platform.system() == "Windows":
                # Windows: 使用dir命令
                result = subprocess.run(
                    ["cmd", "/c", "dir"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=current_dir,
                )
            else:
                # Unix/Linux: 使用ls -la
                result = subprocess.run(
                    ["ls", "-la"],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=current_dir,
                )
            console.print(result.stdout, style=COLORS["dim"], markup=False)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception):
            # Fallback: 使用Python内置os.listdir
            try:
                items = []
                for item in sorted(os.listdir(current_dir)):
                    item_path = current_dir / item
                    if item_path.is_dir():
                        items.append(f"📁 {item}/")
                    else:
                        items.append(f"📄 {item}")

                for item in items:
                    console.print(f"  {item}", style=COLORS["dim"])
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
    """Execute a command with cross-platform shell support. Returns True if handled."""
    cmd = command.strip().lstrip("!")

    if not cmd:
        return True

    try:
        console.print()

        import platform

        # 检测是否为PowerShell命令
        is_powershell = cmd.startswith("pwsh ") or cmd.startswith("powershell ")

        if platform.system() == "Windows":
            if is_powershell:
                console.print(f"[dim]PS> {cmd}[/dim]")
                # 使用PowerShell执行
                result = subprocess.run(
                    ["powershell", "-Command", cmd],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=Path.cwd(),
                )
            else:
                console.print(f"[dim]C:> {cmd}[/dim]")
                # 使用cmd执行
                result = subprocess.run(
                    cmd,
                    check=False,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=Path.cwd(),
                )
        else:
            console.print(f"[dim]$ {cmd}[/dim]")
            # Unix/Linux系统
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
    except FileNotFoundError as e:
        if platform.system() == "Windows":
            console.print(
                f"[red]Command not found. Try using 'powershell {cmd}' or ensure the command is in PATH[/red]"
            )
        else:
            console.print(f"[red]Command not found: {e}[/red]")
        console.print()
        return True
    except Exception as e:
        console.print(f"[red]Error executing command: {e}[/red]")
        console.print()
        return True


def get_system_info() -> dict:
    """获取系统信息，包括WSL检测."""
    import platform
    import subprocess

    info = {
        "system": platform.system(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "wsl": False,
        "powershell_available": False,
    }

    # WSL检测
    if platform.system() == "Linux":
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
                if "microsoft" in version_info or "wsl" in version_info:
                    info["wsl"] = True
        except:
            pass

    # PowerShell可用性检测
    if platform.system() == "Windows":
        try:
            result = subprocess.run(
                ["powershell", "-Command", "Get-Host"], capture_output=True, timeout=5
            )
            info["powershell_available"] = result.returncode == 0
        except:
            try:
                result = subprocess.run(
                    ["pwsh", "-Command", "Get-Host"], capture_output=True, timeout=5
                )
                info["powershell_available"] = result.returncode == 0
            except:
                pass

    return info


def handle_system_info_command(args: list[str]) -> bool:
    """显示系统信息，包括WSL和PowerShell状态."""
    try:
        info = get_system_info()

        console.print("[bold]🖥️  System Information:[/bold]", style=COLORS["primary"])
        console.print()

        # 基本信息
        console.print(
            f"[dim]Operating System:[/dim] {info['system']} {info['version']}"
        )
        console.print(f"[dim]Architecture:[/dim] {info['machine']}")
        console.print(f"[dim]Processor:[/dim] {info['processor']}")
        console.print(f"[dim]Python Version:[/dim] {info['python_version']}")

        # 特殊功能状态
        console.print()
        console.print("[bold]Special Features:[/bold]", style=COLORS["primary"])

        if info["wsl"]:
            console.print(
                f"🐧 WSL: [green]Enabled[/green] (Windows Subsystem for Linux)"
            )
        else:
            console.print(f"🐧 WSL: [dim]Not detected[/dim]")

        if info["powershell_available"]:
            console.print(f"💻 PowerShell: [green]Available[/green]")
        else:
            console.print(f"💻 PowerShell: [red]Not available[/red]")

        # 平台特定提示
        console.print()
        console.print(
            "[bold]Platform-Specific Features:[/bold]", style=COLORS["primary"]
        )

        if info["system"] == "Windows":
            console.print(
                "🔧 Use 'pwsh' or 'powershell' prefix for PowerShell commands"
            )
            console.print("🔧 Use '/services' to view Windows services")
            console.print("🔧 Default editor: notepad")
        elif info["wsl"]:
            console.print("🐧 Running in WSL - Windows integration available")
            console.print("🔧 Can access Windows files via /mnt/c/")
        else:
            console.print("🐧 Unix/Linux environment detected")
            console.print("🔧 Default editor: nano")

        console.print()
        return True

    except Exception as e:
        typewriter.error_shake(f"❌ Error getting system info: {e}")
        return True


def handle_services_command(args: list[str]) -> bool:
    """处理Windows服务管理命令."""
    import platform

    if platform.system() != "Windows":
        typewriter.error_shake("❌ Services command is only available on Windows")
        typewriter.info("Use 'systemctl' or 'service' commands on Linux")
        return True

    try:
        if not args:
            # 显示帮助信息
            console.print(
                "[bold]🔧 Windows Services Management:[/bold]", style=COLORS["primary"]
            )
            console.print()
            typewriter.print_fast("Available commands:", "primary")
            console.print("  /services list           - List running services")
            console.print("  /services search <name>  - Search for a service")
            console.print("  /services status <name>  - Get service status")
            console.print("  /services start <name>   - Start a service")
            console.print("  /services stop <name>    - Stop a service")
            console.print("  /services restart <name> - Restart a service")
            console.print()
            return True

        subcommand = args[0].lower()

        if subcommand == "list":
            return list_windows_services()
        elif subcommand == "search" and len(args) > 1:
            return search_windows_service(args[1])
        elif subcommand == "status" and len(args) > 1:
            return get_service_status(args[1])
        elif subcommand in ["start", "stop", "restart"] and len(args) > 1:
            return manage_windows_service(subcommand, args[1])
        else:
            typewriter.error_shake("❌ Invalid services command")
            typewriter.info("Use '/services' for help")
            return True

    except Exception as e:
        typewriter.error_shake(f"❌ Error managing services: {e}")
        return True


def list_windows_services() -> bool:
    """列出Windows服务."""
    try:
        console.print("[dim]Fetching Windows services...[/dim]")

        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-Service | Select-Object Name, Status, DisplayName | Format-Table -AutoSize",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            console.print(result.stdout, style=COLORS["dim"], markup=False)
        else:
            console.print("[red]Failed to retrieve services list[/red]")
            console.print(result.stderr, style="red")

        console.print()
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out[/red]")
        return True
    except Exception as e:
        console.print(f"[red]Error listing services: {e}[/red]")
        return True


def search_windows_service(service_name: str) -> bool:
    """搜索Windows服务."""
    try:
        console.print(f"[dim]Searching for service: {service_name}[/dim]")

        ps_command = f'Get-Service "*{service_name}*" | Select-Object Name, Status, DisplayName | Format-Table -AutoSize'

        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            if result.stdout.strip():
                console.print(result.stdout, style=COLORS["dim"], markup=False)
            else:
                console.print(f"[dim]No services found matching: {service_name}[/dim]")
        else:
            console.print(f"[red]Error searching for service: {service_name}[/red]")

        console.print()
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Search timed out[/red]")
        return True
    except Exception as e:
        console.print(f"[red]Error searching service: {e}[/red]")
        return True


def get_service_status(service_name: str) -> bool:
    """获取Windows服务状态."""
    try:
        console.print(f"[dim]Getting status for service: {service_name}[/dim]")

        ps_command = f'Get-Service -Name "*{service_name}*" | Select-Object Name, Status, DisplayName, StartType | Format-Table -AutoSize'

        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0:
            console.print(result.stdout, style=COLORS["dim"], markup=False)
        else:
            console.print(
                f"[red]Service '{service_name}' not found or error occurred[/red]"
            )
            console.print(result.stderr, style="red")

        console.print()
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out[/red]")
        return True
    except Exception as e:
        console.print(f"[red]Error getting service status: {e}[/red]")
        return True


def manage_windows_service(action: str, service_name: str) -> bool:
    """管理Windows服务（启动/停止/重启）."""
    try:
        # 确认操作
        console.print(f"[yellow]About to {action} service: {service_name}[/yellow]")
        console.print("[dim]This may require administrator privileges[/dim]")

        choice = input("Continue? (y/N): ").strip().lower()
        if choice != "y" and choice != "yes":
            typewriter.info("Operation cancelled")
            return True

        # PowerShell命令映射
        actions = {
            "start": "Start-Service",
            "stop": "Stop-Service",
            "restart": "Restart-Service",
        }

        ps_command = f'Try {{ {actions[action]} -Name "*{service_name}*" -ErrorAction Stop; Write-Host "Service {action}ed successfully" -ForegroundColor Green }} Catch {{ Write-Host "Error: $_" -ForegroundColor Red }}'

        console.print(f"[dim]Executing: {action} service...[/dim]")

        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=30,
        )

        console.print(
            result.stdout,
            style="green" if "successfully" in result.stdout.lower() else "red",
        )
        if result.stderr:
            console.print(result.stderr, style="red")

        console.print()
        return True

    except subprocess.TimeoutExpired:
        console.print("[red]Operation timed out[/red]")
        return True
    except Exception as e:
        console.print(f"[red]Error managing service: {e}[/red]")
        return True


def handle_memory_command(agent, args: list[str]) -> bool:
    """Handle /memory command for agent memory management.

    Args:
        agent: The AI agent instance
        args: Command arguments

    Returns:
        True if command was handled
    """
    try:
        # 获取助手ID
        assistant_id = get_current_assistant_id()

        # 创建记忆管理器
        memory_manager = MemoryManager(assistant_id=assistant_id)

        # 如果没有参数，显示记忆概览
        if not args:
            view_agent_memory(memory_manager)
            return True

        # 解析子命令
        subcommand = args[0].lower()
        subcommand_args = args[1:] if len(args) > 1 else []

        if subcommand in ["help", "h", "?"]:
            show_memory_menu()
            return True

        elif subcommand == "edit":
            return handle_memory_edit(memory_manager, subcommand_args)

        elif subcommand in ["view", "show", "list"]:
            view_agent_memory(memory_manager)
            return True

        elif subcommand == "search":
            if len(subcommand_args) < 1:
                typewriter.error_shake("❌ 请提供搜索关键词")
                typewriter.info("用法: /memory search <关键词> [type]")
                return True
            query = subcommand_args[0]
            memory_type = subcommand_args[1] if len(subcommand_args) > 1 else "all"
            return handle_memory_search(
                memory_manager,
                [query, memory_type] if memory_type != "all" else [query],
            )

        elif subcommand == "export":
            return handle_memory_export(memory_manager, subcommand_args)

        elif subcommand == "import":
            if len(subcommand_args) < 1:
                typewriter.error_shake("❌ 请提供导入文件路径")
                typewriter.info("用法: /memory import <文件路径>")
                return True
            return handle_memory_import(memory_manager, subcommand_args)

        elif subcommand == "backup":
            return handle_memory_backup(memory_manager, subcommand_args)

        elif subcommand == "restore":
            return handle_memory_restore(memory_manager, subcommand_args)

        elif subcommand == "clean":
            return handle_memory_clear(memory_manager, subcommand_args)

        elif subcommand == "stats":
            return handle_memory_stats(memory_manager, [])

        elif subcommand == "files":
            # 显示记忆文件列表
            memory_files = memory_manager.list_memory_files()
            if memory_files:
                console.print("[bold]📄 记忆文件列表:[/bold]", style=COLORS["primary"])
                for file_info in memory_files:
                    icon = "📁" if file_info["type"] == "directory" else "📄"
                    console.print(f"  {icon} {file_info['name']}")
                    if file_info.get("size"):
                        console.print(f"    [dim]大小: {file_info['size']}[/dim]")
                    if file_info.get("modified"):
                        console.print(f"    [dim]修改: {file_info['modified']}[/dim]")
            else:
                typewriter.info("💭 没有找到记忆文件")
            return True

        else:
            typewriter.error_shake(f"❌ 未知的记忆子命令: {subcommand}")
            show_memory_menu()
            return True

    except Exception as e:
        typewriter.error_shake(f"❌ 记忆管理错误: {e}")
        return True
