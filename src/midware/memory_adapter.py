"""记忆中间件适配器"""

from typing import TYPE_CHECKING, Optional

from .agent_memory import AgentMemoryMiddleware
from .layered_memory import LayeredMemoryMiddleware

if TYPE_CHECKING:
    from deepagents.backends.protocol import BackendProtocol


def create_memory_middleware(
    *,
    backend: "BackendProtocol",
    memory_path: str = "/memories/",
    mode: str = "layered",  # "legacy", "layered", "hybrid"
    working_memory_size: int = 10,
    enable_semantic_memory: bool = True,
    enable_episodic_memory: bool = True,
    **kwargs,
):
    """创建记忆中间件的工厂函数

    Args:
        backend: 后端存储
        memory_path: 记忆路径
        mode: 记忆模式
            - "legacy": 使用原有的AgentMemoryMiddleware
            - "layered": 使用新的LayeredMemoryMiddleware
            - "hybrid": 混合模式，同时使用两者
        working_memory_size: 工作记忆大小
        enable_semantic_memory: 启用语义记忆
        enable_episodic_memory: 启用情节记忆
        **kwargs: 其他参数

    Returns:
        适当的记忆中间件实例或中间件列表
    """
    if mode == "legacy":
        # 使用原有的AgentMemoryMiddleware
        return AgentMemoryMiddleware(backend=backend, memory_path=memory_path, **kwargs)

    elif mode == "layered":
        # 使用新的LayeredMemoryMiddleware
        return LayeredMemoryMiddleware(
            backend=backend,
            memory_path=memory_path,
            working_memory_size=working_memory_size,
            enable_semantic_memory=enable_semantic_memory,
            enable_episodic_memory=enable_episodic_memory,
            **kwargs,
        )

    elif mode == "hybrid":
        # 混合模式：先使用原有记忆，再叠加分层记忆
        legacy_middleware = AgentMemoryMiddleware(
            backend=backend, memory_path=memory_path, **kwargs
        )

        layered_middleware = LayeredMemoryMiddleware(
            backend=backend,
            memory_path=memory_path,
            working_memory_size=working_memory_size,
            enable_semantic_memory=enable_semantic_memory,
            enable_episodic_memory=enable_episodic_memory,
            legacy_mode=True,  # 启用兼容模式
            **kwargs,
        )

        return [layered_middleware, legacy_middleware]

    else:
        raise ValueError(
            f"Unknown memory mode: {mode}. Use 'legacy', 'layered', or 'hybrid'."
        )


class MemoryMiddlewareFactory:
    """记忆中间件工厂类"""

    @staticmethod
    def create_legacy_memory(
        backend: "BackendProtocol", memory_path: str = "/memories/", **kwargs
    ) -> AgentMemoryMiddleware:
        """创建传统的记忆中间件"""
        return create_memory_middleware(
            backend=backend, memory_path=memory_path, mode="legacy", **kwargs
        )

    @staticmethod
    def create_layered_memory(
        backend: "BackendProtocol",
        memory_path: str = "/memories/",
        working_memory_size: int = 10,
        enable_semantic_memory: bool = True,
        enable_episodic_memory: bool = True,
        **kwargs,
    ) -> LayeredMemoryMiddleware:
        """创建分层记忆中间件"""
        return create_memory_middleware(
            backend=backend,
            memory_path=memory_path,
            mode="layered",
            working_memory_size=working_memory_size,
            enable_semantic_memory=enable_semantic_memory,
            enable_episodic_memory=enable_episodic_memory,
            **kwargs,
        )

    @staticmethod
    def create_hybrid_memory(
        backend: "BackendProtocol",
        memory_path: str = "/memories/",
        working_memory_size: int = 10,
        enable_semantic_memory: bool = True,
        enable_episodic_memory: bool = True,
        **kwargs,
    ) -> list:
        """创建混合记忆中间件"""
        return create_memory_middleware(
            backend=backend,
            memory_path=memory_path,
            mode="hybrid",
            working_memory_size=working_memory_size,
            enable_semantic_memory=enable_semantic_memory,
            enable_episodic_memory=enable_episodic_memory,
            **kwargs,
        )

    @staticmethod
    def auto_upgrade_memory(
        backend: "BackendProtocol",
        memory_path: str = "/memories/",
        enable_layered: bool = None,
        **kwargs,
    ):
        """自动选择最佳记忆配置

        Args:
            backend: 后端存储
            memory_path: 记忆路径
            enable_layered: 是否启用分层记忆，None表示自动检测
            **kwargs: 其他参数

        Returns:
        """
        if enable_layered is None:
            # 自动检测：如果原有agent.md存在，使用混合模式
            try:
                agent_data = backend.read("/agent.md")
                if agent_data and agent_data.strip():
                    # 有现有记忆，使用混合模式
                    return MemoryMiddlewareFactory.create_hybrid_memory(
                        backend=backend, memory_path=memory_path, **kwargs
                    )
                else:
                    # 无现有记忆，使用分层模式
                    return MemoryMiddlewareFactory.create_layered_memory(
                        backend=backend, memory_path=memory_path, **kwargs
                    )
            except:
                # 读取失败，使用分层模式
                return MemoryMiddlewareFactory.create_layered_memory(
                    backend=backend, memory_path=memory_path, **kwargs
                )
        else:
            # 根据参数选择
            if enable_layered:
                return MemoryMiddlewareFactory.create_layered_memory(
                    backend=backend, memory_path=memory_path, **kwargs
                )
            else:
                return MemoryMiddlewareFactory.create_legacy_memory(
                    backend=backend, memory_path=memory_path, **kwargs
                )


# 向后兼容的导入
def get_memory_middleware(**kwargs):
    """向后兼容的记忆中间件获取函数"""
    return MemoryMiddlewareFactory.auto_upgrade_memory(**kwargs)
