"""
GLM模块 - 重构后的主入口文件
使用面向对象设计和软件工程最佳实践
"""

from .agent_factory import AgentFactory
from .app import AppFactory
from .cli import CLIManager
from .config import ConfigManager


# 保持向后兼容的函数接口
def create_interactive_agent(model=None):
    """
    创建交互式代理 - 保持向后兼容性

    Args:
        model: 可选的预配置模型

    Returns:
        配置好的代理实例
    """
    agent_factory = AgentFactory()
    return agent_factory.create_interactive_agent(model)


def interactive_cli():
    """
    启动交互式CLI - 保持向后兼容性
    """
    app = AppFactory.create_default_app()
    app.start_interactive_mode()


def main():
    """
    主函数 - 应用程序入口点
    """
    app = AppFactory.create_default_app()
    app.run("interactive")


# 新推荐的面向对象接口
class GLMAgentApp:
    """
    GLM代理应用类
    提供现代化的面向对象接口
    """

    def __init__(self, config_manager=None):
        self.app = AppFactory.create_app(config_manager)

    def start(self, mode="interactive"):
        """启动应用"""
        self.app.run(mode)

    def create_agent(self, model=None):
        """创建代理"""
        return self.app.create_agent()

    def get_config(self):
        """获取配置"""
        return self.app.get_config()


# 便捷函数
def quick_start():
    """快速启动应用"""
    app = GLMAgentApp()
    app.start()


if __name__ == "__main__":
    main()
