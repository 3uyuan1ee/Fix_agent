"""
DeepAgents 包
提供代码缺陷分析和修复的AI代理系统

使用示例:
```python
from workflow.agents import GLMAgentApp, quick_start

# 快速启动
quick_start()

# 或者使用面向对象接口
app = GLMAgentApp()
app.start()
```
"""

from .agent_factory import AgentFactory, MainAgentFactory, SubAgentFactory
from .app import AppFactory, DeepAgentsApp
from .cli import CLIManager, InteractiveCLI
from .config import AgentConfig, ConfigManager, LLMConfig, WorkspaceConfig
from .glm import (
    GLMAgentApp,
    create_interactive_agent,
    interactive_cli,
    main,
    quick_start,
)

__version__ = "1.0.0"
__author__ = "DeepAgents Team"

# 导出主要接口
__all__ = [
    # 配置相关
    "ConfigManager",
    "LLMConfig",
    "WorkspaceConfig",
    "AgentConfig",
    # 工厂相关
    "AgentFactory",
    "MainAgentFactory",
    "SubAgentFactory",
    # CLI相关
    "InteractiveCLI",
    "CLIManager",
    # 应用相关
    "DeepAgentsApp",
    "AppFactory",
    "GLMAgentApp",
    # 兼容性接口
    "create_interactive_agent",
    "interactive_cli",
    "main",
    "quick_start",
]
