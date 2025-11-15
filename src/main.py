"""DeepAgents的主入口点和CLI循环。"""

import argparse
import asyncio
import sys
from pathlib import Path

from .agents.agent import create_agent_with_config, list_agents, reset_agent
from .config.config import COLORS, SessionState, console, create_model
from .interface.commands import execute_bash_command, handle_command
from .interface.execution import execute_task
from .interface.input import create_prompt_session
# 导入tavily客户端（如果需要）
from .tools.network_tools import tavily_client
# 从统一的工具导出模块导入工具
from .tools.tools import (analyze_code_complexity, analyze_code_defects,
                          analyze_existing_logs, batch_format_professional,
                          compile_project, execute_test_suite_tool,
                          explore_project_structure, format_code_professional,
                          generate_validation_tests_tool, http_request,
                          run_and_monitor, run_tests_with_error_capture,
                          web_search)
from .ui.dynamicCli import typewriter
from .ui.ui import TokenTracker, show_help


def check_cli_dependencies():
    """检查CLI的可选依赖是否安装"""
    missing = []

    try:
        import rich
    except ImportError:
        missing.append("rich")

    try:
        import requests
    except ImportError:
        missing.append("requests")

    try:
        import dotenv
    except ImportError:
        missing.append("python-dotenv")

    try:
        import tavily
    except ImportError:
        missing.append("tavily-python")

    try:
        import prompt_toolkit
    except ImportError:
        missing.append("prompt-toolkit")

    if missing:
        print("\n❌ 缺少所需要的CLI依赖")
        print("\nThe following packages are required to use the deepagents CLI:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease install them with:")
        print("  pip install deepagents[cli]")
        print("\nOr install all dependencies:")
        print("  pip install 'deepagents[cli]'")
        sys.exit(1)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="DeepAgents - AI Coding Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all available agents")

    # Help command
    subparsers.add_parser("help", help="Show help information")

    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset an agent")
    reset_parser.add_argument("--agent", required=True, help="Name of agent to reset")
    reset_parser.add_argument(
        "--target", dest="source_agent", help="Copy prompt from another agent"
    )

    # Default interactive mode
    parser.add_argument(
        "--agent",
        default="agent",
        help="Agent identifier for separate memory stores (default: agent).",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve tool usage without prompting (disables human-in-the-loop)",
    )

    return parser.parse_args()


async def simple_cli(
    agent, assistant_id: str | None, session_state, baseline_tokens: int = 0
):
    """Main CLI循环"""
    console.clear()

    if tavily_client is None:
        console.print(
            "[yellow]⚠ Web search disabled:[/yellow] TAVILY_API_KEY not found.",
            style=COLORS["dim"],
        )
        console.print(
            "  To enable web search, set your Tavily API key:", style=COLORS["dim"]
        )
        console.print(
            "    export TAVILY_API_KEY=your_api_key_here", style=COLORS["dim"]
        )
        console.print(
            "  Or add it to your .env file. Get your key at: https://tavily.com",
            style=COLORS["dim"],
        )
        console.print()

    typewriter.welcome()

    console.print()

    if session_state.auto_approve:
        console.print(
            "  [yellow]⚡ Auto-approve: ON[/yellow] [dim](tools run without confirmation)[/dim]"
        )
        console.print()

    console.print(
        "  Tips: Enter to submit, Alt+Enter for newline, Ctrl+E for editor, Ctrl+T to toggle auto-approve, Ctrl+C to interrupt",
        style=f"dim {COLORS['dim']}",
    )
    console.print()

    # 创建提示词会话和token跟踪器
    session = create_prompt_session(assistant_id, session_state)
    token_tracker = TokenTracker()
    token_tracker.set_baseline(baseline_tokens)

    while True:
        try:
            user_input = await session.prompt_async()
            user_input = user_input.strip()
        except EOFError:
            break
        except KeyboardInterrupt:
            # Ctrl+C 提示符 - 推出程序
            typewriter.goodbye()
            break

        if not user_input:
            continue

        # 首先检查'/'命令
        if user_input.startswith("/"):
            result = handle_command(user_input, agent, token_tracker)
            if result == "exit":
                typewriter.goodbye()
                break
            if result:
                # 处理完指令，继续处理下一条
                continue

        # 检查bash命令 (!)
        if user_input.startswith("!"):
            execute_bash_command(user_input)
            continue

        # 处理常见的推出关键词
        if user_input.lower() in ["quit", "exit", "q"]:
            typewriter.goodbye()
            break

        execute_task(user_input, agent, assistant_id, session_state, token_tracker)


async def main(assistant_id: str, session_state):
    """主入口点"""
    # 创建模型 (检查 API keys)
    model = create_model()

    # 用可选的工具创建模型

    # 添加http请求工具
    tools = [http_request]

    # 检查tavily是否可用并添加
    if tavily_client is not None:
        tools.append(web_search)

    # 添加静态分析工具
    tools.append(analyze_code_defects)

    # 添加动态分析工具
    tools.append(compile_project)
    tools.append(run_and_monitor)
    tools.append(run_tests_with_error_capture)
    tools.append(analyze_existing_logs)

    # 添加项目探索工具
    tools.append(analyze_code_complexity)
    tools.append(explore_project_structure)

    # 添加代码格式化工具
    tools.append(format_code_professional)
    tools.append(batch_format_professional)

    # 添加智能测试工具
    tools.append(generate_validation_tests_tool)
    tools.append(execute_test_suite_tool)

    agent = create_agent_with_config(model, assistant_id, tools)

    # Calculate baseline token count for accurate token tracking
    from .agents.agent import get_system_prompt
    from .utils.token_utils import calculate_baseline_tokens

    agent_dir = Path.home() / ".deepagents" / assistant_id
    system_prompt = get_system_prompt()
    baseline_tokens = calculate_baseline_tokens(model, agent_dir, system_prompt)

    try:
        await simple_cli(agent, assistant_id, session_state, baseline_tokens)
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {e}\n")


def cli_main():
    """控制台脚本的入口点"""
    # 先检查依赖
    check_cli_dependencies()

    try:
        args = parse_args()

        if args.command == "help":
            show_help()
        elif args.command == "list":
            list_agents()
        elif args.command == "reset":
            reset_agent(args.agent, args.source_agent)
        else:
            # 根据args创建会话
            session_state = SessionState(auto_approve=args.auto_approve)

            # API key验证在create_model()中进行
            asyncio.run(main(args.agent, session_state))
    except KeyboardInterrupt:
        # Ctrl+C 安全退出 - suppress ugly traceback
        console.print("\n\n[yellow]Interrupted[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Fatal Error:[/bold red] {e}")
        console.print("[dim]Detailed error information:[/dim]")
        import traceback

        console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
