"""
DeepAgents Base Agent Framework

基于软件工程设计思想的DeepAgents基类框架，提供：
- 单一职责的专门化代理类型
- 可扩展的工具和中间件系统
- 灵活的配置和依赖管理
- 统一的创建和管理接口
"""

import logging
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from deepagents import CompiledSubAgent, SubAgent, create_deep_agent
from deepagents.backends.protocol import BackendFactory, BackendProtocol
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.cache.base import BaseCache
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer


class AgentType(Enum):
    """代理类型枚举"""

    RESEARCHER = "researcher"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    COORDINATOR = "coordinator"
    REVIEWER = "reviewer"
    CUSTOM = "custom"


@dataclass
class AgentConfig:
    """代理配置数据类"""

    name: str
    agent_type: AgentType
    description: str
    system_prompt: str

    # 模型配置
    model: Optional[Union[str, BaseChatModel]] = None
    temperature: float = 0.1
    max_tokens: int = 20000

    # 工具和中间件
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]] = field(
        default_factory=list
    )
    middleware: List[Any] = field(default_factory=list)
    subagents: List[Union[SubAgent, CompiledSubAgent]] = field(default_factory=list)

    # 存储和缓存
    backend: Optional[Union[BackendProtocol, BackendFactory]] = None
    store: Optional[BaseStore] = None
    checkpointer: Optional[Checkpointer] = None
    cache: Optional[BaseCache] = None

    # 人机交互
    interrupt_on: Optional[Dict[str, Any]] = None

    # 其他配置
    debug: bool = False
    recursion_limit: int = 1000


class BaseAgent(ABC):
    """
    DeepAgents基类

    提供所有代理通用的功能和接口，遵循软件工程最佳实践：
    - 单一职责：每个子类专注于特定领域
    - 开闭原则：可扩展，不可修改
    - 依赖注入：灵活的配置管理
    - 接口隔离：清晰的抽象层次
    """

    def __init__(self, config: AgentConfig):
        """
        初始化代理

        Args:
            config: 代理配置
        """
        self.config = config
        self._agent: Optional[CompiledStateGraph] = None
        self._logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger(f"{self.__class__.__name__}.{self.config.name}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO if not self.config.debug else logging.DEBUG)
        return logger

    @property
    def agent(self) -> CompiledStateGraph:
        """获取编译后的代理图"""
        if self._agent is None:
            raise RuntimeError("代理未初始化，请先调用build()方法")
        return self._agent

    def build(self) -> "BaseAgent":
        """
        构建代理

        Returns:
            self: 支持链式调用
        """
        try:
            self._logger.info(f"开始构建代理: {self.config.name}")

            # 子类定制化构建
            self._build_custom()

            # 创建核心代理
            self._agent = create_deep_agent(
                model=self.config.model,
                tools=self.config.tools,
                system_prompt=self.config.system_prompt,
                middleware=self.config.middleware,
                subagents=self.config.subagents,
                backend=self.config.backend,
                store=self.config.store,
                checkpointer=self.config.checkpointer,
                cache=self.config.cache,
                interrupt_on=self.config.interrupt_on,
                debug=self.config.debug,
                name=self.config.name,
            ).with_config({"recursion_limit": self.config.recursion_limit})

            self._logger.info(f"代理构建完成: {self.config.name}")
            return self

        except Exception as e:
            error_msg = f"构建代理失败: {str(e)}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    @abstractmethod
    def _build_custom(self) -> None:
        """
        子类定制化构建逻辑

        子类应该重写此方法来实现特定的构建逻辑，例如：
        - 添加专门的工具
        - 配置特定的中间件
        - 设置子代理
        """
        pass

    def invoke(self, input_data: Dict[str, Any]) -> Any:
        """执行代理"""
        try:
            self._logger.info(f"执行代理: {self.config.name}")
            result = self.agent.invoke(input_data)
            self._logger.info(f"代理执行完成: {self.config.name}")
            return result
        except Exception as e:
            error_msg = f"代理执行失败: {str(e)}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def stream(self, input_data: Dict[str, Any], **kwargs) -> Any:
        """流式执行代理"""
        try:
            self._logger.info(f"开始流式执行: {self.config.name}")
            for chunk in self.agent.stream(input_data, **kwargs):
                yield chunk
            self._logger.info(f"流式执行完成: {self.config.name}")
        except Exception as e:
            error_msg = f"流式执行失败: {str(e)}"
            self._logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def get_info(self) -> Dict[str, Any]:
        """获取代理信息"""
        return {
            "name": self.config.name,
            "type": self.config.agent_type.value,
            "description": self.config.description,
            "model": getattr(self.config.model, "model_name", str(self.config.model)),
            "tools_count": len(self.config.tools),
            "subagents_count": len(self.config.subagents),
            "middleware_count": len(self.config.middleware),
            "has_backend": self.config.backend is not None,
            "has_store": self.config.store is not None,
            "debug": self.config.debug,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.__class__.__name__}(name='{self.config.name}', type='{self.config.agent_type.value}')"


class ResearchAgent(BaseAgent):
    """研究代理 - 专门用于信息收集和分析"""

    def _build_custom(self) -> None:
        """研究代理的定制化构建"""
        # 添加网络搜索工具
        try:
            from src.workflow.tools.web_search import search_web

            def internet_search(query: str, max_results: int = 5):
                """网络搜索工具"""
                return search_web(
                    query=query, max_results=max_results, provider="tavily"
                )

            self.config.tools = list(self.config.tools) + [internet_search]
            self._logger.info("已添加网络搜索工具")
        except ImportError:
            self._logger.warning("无法导入web_search工具")

    @classmethod
    def create(cls, name: str, description: str, **kwargs) -> "ResearchAgent":
        """快速创建研究代理"""
        config = AgentConfig(
            name=name,
            agent_type=AgentType.RESEARCHER,
            description=description,
            system_prompt=kwargs.pop(
                "system_prompt", "你是专业的研究员，负责信息收集和分析"
            ),
            **kwargs,
        )
        return cls(config)


class DeveloperAgent(BaseAgent):
    """开发代理 - 专门用于软件开发任务"""

    def _build_custom(self) -> None:
        """开发代理的定制化构建"""
        # 添加代码分析工具
        try:
            from src.workflow.tools.multilang_code_analyzer import (
                MultiLanguageCodeAnalyzer,
            )

            analyzer = MultiLanguageCodeAnalyzer()
            self.config.tools = list(self.config.tools) + [
                analyzer.analyze_code,
                analyzer.detect_issues,
                analyzer.get_suggestions,
            ]
            self._logger.info("已添加代码分析工具")
        except ImportError:
            self._logger.warning("无法导入代码分析工具")

    @classmethod
    def create(cls, name: str, description: str, **kwargs) -> "DeveloperAgent":
        """快速创建开发代理"""
        config = AgentConfig(
            name=name,
            agent_type=AgentType.DEVELOPER,
            description=description,
            system_prompt=kwargs.pop("system_prompt", "你是专业的软件开发工程师"),
            **kwargs,
        )
        return cls(config)


class CoordinatorAgent(BaseAgent):
    """协调代理 - 专门用于多代理协调和任务分发"""

    def _build_custom(self) -> None:
        """协调代理的定制化构建"""
        if not self.config.subagents:
            self._logger.warning("协调代理没有配置子代理")

    @classmethod
    def create(cls, name: str, description: str, **kwargs) -> "CoordinatorAgent":
        """快速创建协调代理"""
        config = AgentConfig(
            name=name,
            agent_type=AgentType.COORDINATOR,
            description=description,
            system_prompt=kwargs.pop(
                "system_prompt", "你是项目协调员，负责任务分解和协调"
            ),
            **kwargs,
        )
        return cls(config)


# 便利函数
def create_research_agent(name: str, description: str, **kwargs) -> ResearchAgent:
    """创建研究代理的便利函数"""
    return ResearchAgent.create(name, description, **kwargs)


def create_developer_agent(name: str, description: str, **kwargs) -> DeveloperAgent:
    """创建开发代理的便利函数"""
    return DeveloperAgent.create(name, description, **kwargs)


def create_coordinator_agent(name: str, description: str, **kwargs) -> CoordinatorAgent:
    """创建协调代理的便利函数"""
    return CoordinatorAgent.create(name, description, **kwargs)
