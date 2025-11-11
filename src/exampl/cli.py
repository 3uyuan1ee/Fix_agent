"""
交互式CLI模块
负责处理用户交互和命令行界面
"""

import os
import readline
import sys
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .agent_factory import AgentFactory
from .config import ConfigManager


class BaseCLI(ABC):
    """CLI基类"""

    @abstractmethod
    def start(self) -> None:
        """启动CLI的抽象方法"""
        pass

    @abstractmethod
    def stop(self) -> None:
        """停止CLI的抽象方法"""
        pass


class InteractiveCLI(BaseCLI):
    """交互式CLI实现"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.agent_factory = AgentFactory(self.config_manager)
        self.agent = None
        self.running = False

    def _setup_workspace(self) -> None:
        """设置工作目录"""
        workspace_dir = self.agent_factory.get_workspace_directory()
        if os.path.exists(workspace_dir):
            os.chdir(workspace_dir)
            print(f"工作目录已设置为: {workspace_dir}")
        else:
            print(f"警告: 工作目录不存在: {workspace_dir}")

    def _initialize_agent(self) -> None:
        """初始化代理"""
        try:
            self.agent = self.agent_factory.create_interactive_agent()
            print("✅ 代理初始化成功")
        except Exception as e:
            print(f"❌ 代理初始化失败: {e}")
            raise

    def _display_welcome(self) -> None:
        """显示欢迎信息"""
        print("\n" + "=" * 50)
        print("🤖 DeepAgents Interactive CLI")
        print("Type 'quit', 'exit' or 'q' to end session")
        print("Type 'help' for available commands")
        print("=" * 50)

    def _process_user_input(self, user_input: str) -> bool:
        """处理用户输入"""
        user_input = user_input.strip()

        # 处理退出命令
        if user_input.lower() in ["quit", "exit", "q"]:
            print("\n👋 Goodbye!")
            return False

        # 处理帮助命令
        if user_input.lower() in ["help", "h", "?"]:
            self._show_help()
            return True

        # 处理空输入
        if not user_input:
            return True

        # 处理代理请求
        return self._handle_agent_request(user_input)

    def _show_help(self) -> None:
        """显示帮助信息"""
        help_text = """
📚 可用命令:
  help, h, ?          - 显示此帮助信息
  quit, exit, q       - 退出程序
  clear, cls          - 清空屏幕

💡 使用提示:
  - 直接输入您的问题或任务
  - 可以要求代理分析代码、修复缺陷等
  - 支持文件路径和代码片段
        """
        print(help_text)

    def _handle_agent_request(self, user_input: str) -> bool:
        """处理代理请求"""
        if not self.agent:
            print("❌ 代理未初始化")
            return True

        try:
            print("\n🤔 开始思考...")
            print("-" * 50)

            # 尝试使用流式输出
            try:
                for chunk in self.agent.stream(
                    {"messages": [{"role": "user", "content": user_input}]}
                ):
                    if chunk:
                        print(chunk, end="", flush=True)
                print("\n")
            except Exception as stream_error:
                # 如果流式输出失败，回退到普通调用
                print(f"⚠️ 流式输出失败，使用普通模式: {stream_error}")
                response = self.agent.invoke(
                    {"messages": [{"role": "user", "content": user_input}]}
                )
                print(f"\n📋 最终结果:\n{response}")

        except Exception as e:
            print(f"❌ 处理请求时出错: {e}")

        print("-" * 50)
        return True

    def _handle_interrupt(self) -> None:
        """处理中断信号"""
        print("\n\n⚠️ 会话被中断")
        self.stop()

    def start(self) -> None:
        """启动交互式CLI"""
        try:
            self._setup_workspace()
            self._initialize_agent()
            self._display_welcome()
            self.running = True

            while self.running:
                try:
                    user_input = input("\n🤖 > ")
                    should_continue = self._process_user_input(user_input)
                    if not should_continue:
                        break

                except KeyboardInterrupt:
                    self._handle_interrupt()
                    break
                except EOFError:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ 发生错误: {e}")
                    continue

        except Exception as e:
            print(f"❌ CLI启动失败: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """停止CLI"""
        self.running = False
        print("🔄 清理资源...")


class CLIManager:
    """CLI管理器"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.cli = InteractiveCLI(self.config_manager)

    def start_interactive_session(self) -> None:
        """启动交互式会话"""
        self.cli.start()

    def create_custom_cli(self, cli_type: str = "interactive") -> BaseCLI:
        """创建自定义CLI"""
        if cli_type.lower() == "interactive":
            return InteractiveCLI(self.config_manager)
        else:
            raise ValueError(f"不支持的CLI类型: {cli_type}")
