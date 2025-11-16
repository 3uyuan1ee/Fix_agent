"""首次使用环境配置向导 - 基于 /config 命令设计模式"""

import importlib.resources
import os
import platform
import sys
from pathlib import Path
from typing import Dict, Optional

from rich.panel import Panel

from ..config.config import COLORS, console
from ..ui.dynamicCli import typewriter


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


def detect_platform() -> str:
    """检测当前操作系统平台 - 参考 /config 命令设计"""
    return platform.system()


def get_user_choice(prompt: str, valid_choices: list[str]) -> str:
    """获取用户选择 - 复用 /config 命令的函数"""
    from rich.prompt import Prompt

    while True:
        try:
            choice = Prompt.ask(prompt, choices=valid_choices, default=valid_choices[0])
            return choice
        except KeyboardInterrupt:
            typewriter.info("\n操作已取消")
            return valid_choices[-1]  # 返回最后一个选项（通常是取消）


def show_platform_specific_instructions():
    """显示平台特定的环境变量设置说明"""
    system = detect_platform()

    if system == "Windows":
        instructions = """
[bold cyan]Windows 环境变量设置方法：[/bold cyan]

[bold]方法1: 命令行 (临时设置，重启后失效)[/bold]
[dim]CMD:[/dim]
set OPENAI_API_KEY=your_api_key_here
set ANTHROPIC_API_KEY=your_claude_key_here

[dim]PowerShell:[/dim]
$env:OPENAI_API_KEY="your_api_key_here"
$env:ANTHROPIC_API_KEY="your_claude_key_here"

[bold]方法2: 系统环境变量 (永久设置)[/bold]
1. 按 [yellow]Win + R[/yellow]，输入 [yellow]sysdm.cpl[/yellow]
2. 点击"高级"选项卡 → "环境变量"
3. 在"用户变量"中点击"新建"
4. 添加以下变量：
   • 变量名: [cyan]OPENAI_API_KEY[/cyan]
   • 变量值: [cyan]你的OpenAI密钥[/cyan]
   • 变量名: [cyan]ANTHROPIC_API_KEY[/cyan]
   • 变量值: [cyan]你的Claude密钥[/cyan]

[bold]方法3: 创建 .env 文件 (推荐)[/bold]
在当前目录创建 .env 文件，内容：
OPENAI_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_claude_key_here
        """
    else:
        instructions = """
[bold cyan]macOS/Linux 环境变量设置方法：[/bold cyan]

[bold]方法1: 命令行 (临时设置)[/bold]
export OPENAI_API_KEY=your_api_key_here
export ANTHROPIC_API_KEY=your_claude_key_here

[bold]方法2: Shell 配置文件 (永久设置)[/bold]
[dim]Bash ([yellow]~/.bashrc[/yellow]):[/dim]
echo 'export OPENAI_API_KEY=your_api_key_here' >> ~/.bashrc
echo 'export ANTHROPIC_API_KEY=your_claude_key_here' >> ~/.bashrc
source ~/.bashrc

[dim]Zsh ([yellow]~/.zshrc[/yellow]):[/dim]
echo 'export OPENAI_API_KEY=your_api_key_here' >> ~/.zshrc
echo 'export ANTHROPIC_API_KEY=your_claude_key_here' >> ~/.zshrc
source ~/.zshrc

[bold]方法3: 创建 .env 文件 (推荐)[/bold]
在当前目录创建 .env 文件，内容：
OPENAI_API_KEY=your_api_key_here
ANTHROPIC_API_KEY=your_claude_key_here
        """

    console.print()
    console.print(
        Panel(
            instructions.strip(),
            title="[bold blue]🔧 环境变量设置指南[/bold blue]",
            border_style="blue",
        )
    )


def create_interactive_env() -> bool:
    """交互式创建 .env 文件 - 基于 .env.template"""
    try:
        template_path = Path.cwd() / ".env.template"

        # 在包目录下保存.env文件
        try:
            import Fix_agent
            package_dir = Path(Fix_agent.__file__).parent
        except ImportError:
            # 如果无法导入包，使用当前目录
            package_dir = Path.cwd()

        env_path = package_dir / ".env"

        # 读取模板内容 - 先尝试当前目录，再尝试包目录
        if template_path.exists():
            template_content = template_path.read_text(encoding="utf-8")
        else:
            # 备用方案：从包安装目录读取
            template_content = get_env_template_content_from_package()
            if template_content is None:
                typewriter.error_shake("❌ .env.template 文件未找到")
                return False

        console.print()
        typewriter.print_with_random_speed(
            "🚀 欢迎使用 Fix_agent 环境配置向导", "primary"
        )
        console.print()

        system = detect_platform()
        typewriter.info(f"检测到系统: {system}")
        console.print()

        # 显示配置选项 - 参考 /config 命令的界面设计
        typewriter.print_with_random_speed("请选择配置方式:", "primary")
        typewriter.print_fast(
            """
            配置选项:
            1. 交互式配置 (推荐) - 逐步引导填写API密钥
            2. 从模板创建 - 复制模板文件手动编辑
            3. 显示设置指南 - 查看详细配置说明
            4. 取消
            """,
            "warning",
        )
        console.print()

        # 获取用户选择 - 使用与 /config 相同的函数
        choice = get_user_choice("请选择选项 (1-4): ", ["1", "2", "3", "4"])

        if choice == "1":
            return interactive_setup(template_content, env_path)
        elif choice == "2":
            return create_from_template(template_path, env_path)
        elif choice == "3":
            show_platform_specific_instructions()
            typewriter.info("配置完成后请重新运行 fix-agent")
            return False
        elif choice == "4":
            typewriter.info("配置已取消")
            return False

    except Exception as e:
        typewriter.error_shake(f"❌ 配置过程中出现错误: {e}")
        return False


def interactive_setup(template_content: str, env_path: Path) -> bool:
    """交互式配置 - 参考 /config 命令的用户交互模式"""
    try:
        from rich.prompt import Prompt
        from rich.table import Table

        console.print()
        typewriter.print_with_random_speed("📝 开始交互式配置", "primary")
        console.print()

        # 收集 API 密钥
        config_values = {}

        # OpenAI 配置
        typewriter.print_with_random_speed("🤖 OpenAI API 配置", "cyan")
        if Prompt.ask("是否配置 OpenAI API?", choices=["y", "n"], default="y") == "y":
            api_key = Prompt.ask(
                "请输入 OpenAI API Key", password=True, show_default=False
            )
            if api_key.strip():
                config_values["OPENAI_API_KEY"] = api_key.strip()

                # 高级选项
                if (
                    Prompt.ask("是否配置高级选项?", choices=["y", "n"], default="n")
                    == "y"
                ):
                    base_url = Prompt.ask("API Base URL (可选)", default="")
                    if base_url.strip():
                        config_values["OPENAI_API_BASE"] = base_url.strip()

                    model = Prompt.ask(
                        "模型名称",
                        choices=["gpt-4", "gpt-4-turbo", "gpt-5-mini", "gpt-3.5-turbo","glm-4.5-air","glm-4.6"],
                        default="gpt-5-mini",
                    )
                    config_values["OPENAI_MODEL"] = model

        console.print()

        # Anthropic 配置
        typewriter.print_with_random_speed("🧠 Anthropic Claude 配置", "cyan")
        if (
            Prompt.ask("是否配置 Anthropic API?", choices=["y", "n"], default="y")
            == "y"
        ):
            api_key = Prompt.ask(
                "请输入 Anthropic API Key", password=True, show_default=False
            )
            if api_key.strip():
                config_values["ANTHROPIC_API_KEY"] = api_key.strip()

                # 高级选项
                if (
                    Prompt.ask("是否配置高级选项?", choices=["y", "n"], default="n")
                    == "y"
                ):
                    base_url = Prompt.ask("Base URL (可选)", default="")
                    if base_url.strip():
                        config_values["ANTHROPIC_BASE_URL"] = base_url.strip()

                    model = Prompt.ask(
                        "模型名称",
                        choices=[
                            "claude-sonnet-4-5-20250929",
                            "claude-3-opus-20240229",
                            "claude-3-sonnet-20240229",
                        ],
                        default="claude-sonnet-4-5-20250929",
                    )
                    config_values["ANTHROPIC_MODEL"] = model

        console.print()

        # Tavily 配置 (可选)
        typewriter.print_with_random_speed("🔍 Tavily 搜索 API 配置 (可选)", "cyan")
        if Prompt.ask("是否配置网络搜索功能?", choices=["y", "n"], default="n") == "y":
            api_key = Prompt.ask(
                "请输入 Tavily API Key", password=True, show_default=False
            )
            if api_key.strip():
                config_values["TAVILY_API_KEY"] = api_key.strip()

        # 生成 .env 文件内容
        env_content = generate_env_content(template_content, config_values)

        # 显示配置摘要
        console.print()
        typewriter.print_with_random_speed("📋 配置摘要", "primary")

        table = Table(title="已配置的 API")
        table.add_column("服务", style="cyan")
        table.add_column("状态", style="green")
        table.add_column("说明", style="dim")

        if "OPENAI_API_KEY" in config_values:
            table.add_row(
                "OpenAI",
                "✅ 已配置",
                f"模型: {config_values.get('OPENAI_MODEL', 'gpt-5-mini')}",
            )
        else:
            table.add_row("OpenAI", "❌ 未配置", "可后续添加")

        if "ANTHROPIC_API_KEY" in config_values:
            table.add_row(
                "Anthropic",
                "✅ 已配置",
                f"模型: {config_values.get('ANTHROPIC_MODEL', 'claude-sonnet-4-5-20250929')}",
            )
        else:
            table.add_row("Anthropic", "❌ 未配置", "可后续添加")

        if "TAVILY_API_KEY" in config_values:
            table.add_row("Tavily", "✅ 已配置", "网络搜索功能")
        else:
            table.add_row("Tavily", "❌ 未配置", "可选功能")

        console.print(table)

        # 确认保存
        console.print()
        if Prompt.ask("确认保存配置?", choices=["y", "n"], default="y") == "y":
            # 写入 .env 文件
            env_path.write_text(env_content, encoding="utf-8")
            typewriter.success(f"✅ 配置已保存到: {env_path}")

            # 显示下一步操作
            console.print()
            typewriter.print_with_random_speed("🎉 配置完成！", "primary")
            typewriter.info("重新运行 fix-agent 即可开始使用")
            console.print()

            # 使用说明
            next_steps = """
[bold cyan]下一步操作：[/bold cyan]

1. 重新启动 Fix_agent:
   [dim]Windows: fixagent 或 fix-agent[/dim]
   [dim]macOS/Linux: fixagent 或 python -m src.main[/dim]

2. 后续修改配置:
   • 运行 [cyan]/config[/cyan] 命令编辑配置
   • 直接编辑 .env 文件

3. 获取帮助:
   • 运行 [cyan]/help[/cyan] 查看所有命令
            """

            console.print(
                Panel(
                    next_steps.strip(),
                    title="[bold blue]📚 使用指南[/bold blue]",
                    border_style="blue",
                )
            )

            return True
        else:
            typewriter.info("配置已取消")
            return False

    except Exception as e:
        typewriter.error_shake(f"❌ 配置过程中出现错误: {e}")
        return False


def create_from_template(template_path: Path, env_path: Path) -> bool:
    """从模板创建 .env 文件 - 参考 /config 命令的模板复制功能"""
    try:
        # 获取模板内容 - 先尝试当前目录，再尝试包目录
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
                typewriter.error_shake("❌ 无法获取模板内容")
                return False

        # 写入模板内容到 .env 文件
        env_path.write_text(template_content, encoding="utf-8")
        typewriter.success(f"✅ 已从模板创建 .env 文件: {env_path}")

        system = detect_platform()
        editor = "notepad" if system == "Windows" else "nano"

        typewriter.info(f"请使用文本编辑器打开 {env_path} 并填入你的 API 密钥")
        typewriter.info(f"或在命令行运行: [cyan]{editor} {env_path}[/cyan]")

        console.print()
        typewriter.print_with_random_speed("💡 配置提示:", "primary")
        typewriter.info("• 至少需要配置 OPENAI_API_KEY 或 ANTHROPIC_API_KEY 中的一个")
        typewriter.info("• 删除配置项前的 # 号来启用该配置")
        typewriter.info("• 配置完成后重新运行 fix-agent")

        return True

    except Exception as e:
        typewriter.error_shake(f"❌ 创建文件时出错: {e}")
        return False


def generate_env_content(template_content: str, config_values: Dict[str, str]) -> str:
    """基于模板和用户配置生成 .env 文件内容"""
    lines = []
    lines.append("# Fix Agent 环境配置文件")
    lines.append("# 由首次配置向导自动生成")
    lines.append("")

    # 添加用户配置的 API 密钥
    if "OPENAI_API_KEY" in config_values:
        lines.append("# OpenAI 配置")
        lines.append(f"OPENAI_API_KEY={config_values['OPENAI_API_KEY']}")
        if "OPENAI_API_BASE" in config_values:
            lines.append(f"OPENAI_API_BASE={config_values['OPENAI_API_BASE']}")
        if "OPENAI_MODEL" in config_values:
            lines.append(f"OPENAI_MODEL={config_values['OPENAI_MODEL']}")
        lines.append("")

    if "ANTHROPIC_API_KEY" in config_values:
        lines.append("# Anthropic 配置")
        lines.append(f"ANTHROPIC_API_KEY={config_values['ANTHROPIC_API_KEY']}")
        if "ANTHROPIC_BASE_URL" in config_values:
            lines.append(f"ANTHROPIC_BASE_URL={config_values['ANTHROPIC_BASE_URL']}")
        if "ANTHROPIC_MODEL" in config_values:
            lines.append(f"ANTHROPIC_MODEL={config_values['ANTHROPIC_MODEL']}")
        lines.append("")

    if "TAVILY_API_KEY" in config_values:
        lines.append("# Tavily 搜索配置")
        lines.append(f"TAVILY_API_KEY={config_values['TAVILY_API_KEY']}")
        lines.append("")

    # 添加通用配置
    lines.append("# 通用配置")
    lines.append("MODEL_TEMPERATURE=0.3")
    lines.append("MODEL_MAX_TOKENS=50000")
    lines.append("MODEL_MAX_RETRIES=3")
    lines.append("")

    return "\n".join(lines)


def check_env_file_exists() -> bool:
    """检查 .env 文件是否存在"""
    # 首先检查包目录下的.env文件
    try:
        import Fix_agent
        package_dir = Path(Fix_agent.__file__).parent
        env_path = package_dir / ".env"
        if env_path.exists():
            return True
    except ImportError:
        pass

    # 备用：检查当前目录
    env_path = Path.cwd() / ".env"
    return env_path.exists()


def run_first_time_setup() -> bool:
    """运行首次配置向导"""
    if check_env_file_exists():
        return True  # 已有配置，跳过首次设置

    return create_interactive_env()
