"""
全局并发控制管理器
在LLM客户端层面统一管理所有LLM请求的并发控制
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..utils.logger import get_logger


@dataclass
class QueuedRequest:
    """队列中的请求"""

    request_id: str
    task_func: Callable
    args: tuple
    kwargs: dict
    created_at: float = field(default_factory=time.time)
    future: Optional[asyncio.Future] = None


class GlobalConcurrencyManager:
    """全局并发控制管理器"""

    def __init__(self, max_concurrent_requests: int = 5):
        """
        初始化并发管理器

        Args:
            max_concurrent_requests: 最大并发请求数
        """
        self.max_concurrent_requests = max_concurrent_requests
        self.logger = get_logger()

        # 并发控制信号量
        self._semaphore = asyncio.Semaphore(max_concurrent_requests)

        # 请求队列（按优先级排序）
        self._request_queue: List[QueuedRequest] = []
        self._queue_lock = asyncio.Lock()

        # 去重缓存（防止相同请求重复发送）
        self._request_cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5分钟缓存

        # 活跃请求跟踪
        self._active_requests: Dict[str, QueuedRequest] = {}

        # 统计信息
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cached_requests": 0,
            "queue_length": 0,
            "active_requests": 0,
        }

        self.logger.info(
            f"GlobalConcurrencyManager initialized with max_concurrent={max_concurrent_requests}"
        )

    def _generate_request_key(
        self, task_func: Callable, args: tuple, kwargs: dict
    ) -> str:
        """
        生成请求的唯一键（用于去重）

        Args:
            task_func: 任务函数
            args: 位置参数
            kwargs: 关键字参数

        Returns:
            请求的唯一键
        """
        # 提取关键参数生成哈希
        key_data = {
            "func_name": task_func.__name__,
            "args": str(args)[:200],  # 限制长度避免过长
            "kwargs": {
                k: str(v)[:100]
                for k, v in kwargs.items()
                if k in ["messages", "temperature", "max_tokens"]
            },
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def execute_request(self, task_func: Callable, *args, **kwargs) -> Any:
        """
        执行带并发控制的请求

        Args:
            task_func: 要执行的任务函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            任务执行结果
        """
        self.stats["total_requests"] += 1

        # 检查去重
        request_key = self._generate_request_key(task_func, args, kwargs)
        if self._check_duplicate(request_key):
            self.stats["cached_requests"] += 1
            self.logger.debug(
                f"Returning cached result for request key: {request_key[:8]}..."
            )
            return self._request_cache[request_key]["result"]

        # 创建请求对象
        request = QueuedRequest(
            request_id=f"{int(time.time() * 1000)}_{len(self._active_requests)}",
            task_func=task_func,
            args=args,
            kwargs=kwargs,
        )

        try:
            # 使用信号量控制并发
            async with self._semaphore:
                self.stats["active_requests"] += 1
                self._active_requests[request.request_id] = request

                self.logger.debug(
                    f"Executing request {request.request_id} (active: {len(self._active_requests)})"
                )

                # 执行任务
                start_time = time.time()
                result = await task_func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 缓存结果
                self._cache_result(request_key, result)

                self.stats["successful_requests"] += 1
                self.logger.debug(
                    f"Request {request.request_id} completed in {execution_time:.2f}s"
                )

                return result

        except Exception as e:
            self.stats["failed_requests"] += 1
            self.logger.error(f"Request {request.request_id} failed: {e}")
            raise

        finally:
            # 清理活跃请求
            if request.request_id in self._active_requests:
                del self._active_requests[request.request_id]
            self.stats["active_requests"] = len(self._active_requests)

    def _check_duplicate(self, request_key: str) -> bool:
        """
        检查是否为重复请求

        Args:
            request_key: 请求键

        Returns:
            是否为重复请求
        """
        if request_key in self._request_cache:
            cache_entry = self._request_cache[request_key]
            # 检查缓存是否过期
            if time.time() - cache_entry["timestamp"] < self._cache_ttl:
                return True
            else:
                # 清理过期缓存
                del self._request_cache[request_key]
        return False

    def _cache_result(self, request_key: str, result: Any):
        """
        缓存请求结果

        Args:
            request_key: 请求键
            result: 结果
        """
        self._request_cache[request_key] = {"result": result, "timestamp": time.time()}

        # 清理过期缓存
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._request_cache.items()
            if current_time - entry["timestamp"] > self._cache_ttl
        ]
        for key in expired_keys:
            del self._request_cache[key]

    async def execute_batch(self, requests: List[tuple]) -> List[Any]:
        """
        批量执行请求（保持并发控制）

        Args:
            requests: 请求列表，每个元素为 (task_func, args, kwargs)

        Returns:
            结果列表
        """
        tasks = []
        for task_func, args, kwargs in requests:
            task = self.execute_request(task_func, *args, **kwargs)
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        stats.update(
            {
                "max_concurrent_requests": self.max_concurrent_requests,
                "available_permits": self._semaphore._value,
                "cache_size": len(self._request_cache),
                "active_request_ids": list(self._active_requests.keys()),
            }
        )
        return stats

    async def clear_cache(self):
        """清空缓存"""
        self._request_cache.clear()
        self.logger.info("Request cache cleared")

    async def update_max_concurrent(self, new_max: int):
        """
        更新最大并发数

        Args:
            new_max: 新的最大并发数
        """
        old_max = self.max_concurrent_requests
        self.max_concurrent_requests = new_max

        # 调整信号量
        if new_max > old_max:
            # 增加许可
            additional_permits = new_max - old_max
            for _ in range(additional_permits):
                self._semaphore.release()
        elif new_max < old_max:
            # 减少许可（不能减少当前已使用的许可）
            permits_to_remove = min(old_max - new_max, self._semaphore._value)
            for _ in range(permits_to_remove):
                try:
                    self._semaphore.acquire_nowait()
                except:
                    break

        self.logger.info(f"Max concurrent requests updated: {old_max} -> {new_max}")


# 全局并发管理器实例
_global_concurrency_manager: Optional[GlobalConcurrencyManager] = None


def get_global_concurrency_manager(max_concurrent: int = 5) -> GlobalConcurrencyManager:
    """
    获取全局并发管理器实例

    Args:
        max_concurrent: 最大并发数（仅在首次创建时使用）

    Returns:
        GlobalConcurrencyManager: 全局并发管理器实例
    """
    global _global_concurrency_manager

    if _global_concurrency_manager is None:
        _global_concurrency_manager = GlobalConcurrencyManager(max_concurrent)

    return _global_concurrency_manager


async def close_global_concurrency_manager():
    """关闭全局并发管理器"""
    global _global_concurrency_manager

    if _global_concurrency_manager:
        await _global_concurrency_manager.clear_cache()
        _global_concurrency_manager = None
