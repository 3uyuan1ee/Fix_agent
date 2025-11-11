"""
应用主模块
负责应用程序的初始化和启动
"""

from typing import Optional

from .agent_factory import AgentFactory
from .cli import CLIManager
from .config import ConfigManager


class DeepAgentsApp:
    """DeepAgents应用程序主类"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        初始化应用程序

        Args:
            config_manager: 配置管理器实例，如果为None则使用默认配置
        """
        self.config_manager = config_manager or ConfigManager()
        self.agent_factory = AgentFactory(self.config_manager)
        self.cli_manager = CLIManager(self.config_manager)

    def start_interactive_mode(self) -> None:
        """启动交互式模式"""
        try:
            self.cli_manager.start_interactive_session()
        except KeyboardInterrupt:
            print("\n应用程序被用户中断")
        except Exception as e:
            print(f"应用程序运行出错: {e}")
            raise

    def create_agent(self):
        """创建代理实例"""
        return self.agent_factory.create_interactive_agent()

    def get_config(self):
        """获取配置信息"""
        return self.config_manager

    def run(self, mode: str = "interactive") -> None:
        """
        运行应用程序

        Args:
            mode: 运行模式，目前支持 "interactive"
        """
        if mode.lower() == "interactive":
            self.start_interactive_mode()
        else:
            raise ValueError(f"不支持的运行模式: {mode}")


class AppFactory:
    """应用程序工厂"""

    @staticmethod
    def create_app(config_manager: Optional[ConfigManager] = None) -> DeepAgentsApp:
        """创建应用程序实例"""
        return DeepAgentsApp(config_manager)

    @staticmethod
    def create_default_app() -> DeepAgentsApp:
        """创建使用默认配置的应用程序实例"""
        return DeepAgentsApp()
