"""
代理工厂模块
负责创建和配置各种类型的代理
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langchain_openai import ChatOpenAI

from .config import AgentConfig, ConfigManager, WorkspaceConfig


class BaseAgentFactory(ABC):
    """代理工厂基类"""

    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    @abstractmethod
    def create_agent(self, **kwargs) -> Any:
        """创建代理的抽象方法"""
        pass


class SubAgentFactory(BaseAgentFactory):
    """子代理工厂"""

    def create_agent(self, agent_config: AgentConfig) -> Dict[str, Any]:
        """创建子代理配置"""
        return {
            "name": agent_config.name,
            "description": agent_config.description,
            "system_prompt": agent_config.system_prompt,
            "debug": agent_config.debug,
        }

    def create_all_subagents(self) -> List[Dict[str, Any]]:
        """创建所有子代理"""
        subagents = []
        for config in self.config_manager.subagent_configs:
            subagent = self.create_agent(config)
            subagents.append(subagent)
        return subagents


class MainAgentFactory(BaseAgentFactory):
    """主代理工厂"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__(config_manager)
        self.subagent_factory = SubAgentFactory(config_manager)

    def create_llm(self) -> ChatOpenAI:
        """创建LLM实例"""
        llm_config = self.config_manager.llm_config
        return ChatOpenAI(
            model=llm_config.model,
            openai_api_key=llm_config.api_key,
            openai_api_base=llm_config.api_base,
        )

    def create_backend(self) -> FilesystemBackend:
        """创建文件系统后端"""
        workspace_config = self.config_manager.workspace_config
        return FilesystemBackend(root_dir=workspace_config.root_dir)

    def create_agent(self, model: Optional[ChatOpenAI] = None) -> Any:
        """创建主协调代理"""
        if model is None:
            model = self.create_llm()

        backend = self.create_backend()
        subagents = self.subagent_factory.create_all_subagents()
        coordinator_prompt = self.config_manager.get_coordinator_prompt()

        return create_deep_agent(
            model=model,
            debug=True,
            system_prompt=coordinator_prompt,
            backend=backend,
            subagents=subagents,
        )


class AgentFactory:
    """代理工厂统一入口"""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.main_agent_factory = MainAgentFactory(self.config_manager)
        self.subagent_factory = SubAgentFactory(self.config_manager)

    def create_interactive_agent(self, model: Optional[ChatOpenAI] = None) -> Any:
        """创建交互式代理"""
        return self.main_agent_factory.create_agent(model)

    def create_llm(self) -> ChatOpenAI:
        """创建LLM实例"""
        return self.main_agent_factory.create_llm()

    def create_subagent_configs(self) -> List[Dict[str, Any]]:
        """获取子代理配置列表"""
        return self.subagent_factory.create_all_subagents()

    def get_workspace_directory(self) -> str:
        """获取工作空间目录"""
        return self.config_manager.workspace_config.root_dir
