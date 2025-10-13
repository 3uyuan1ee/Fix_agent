"""
缓存管理模块
实现分析结果缓存机制，支持内存和Redis缓存
"""

import json
import time
import hashlib
import threading
from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from dataclasses import dataclass
from pathlib import Path

from .config import get_config_manager
from .logger import get_logger


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    timestamp: float
    ttl: int
    size: int

    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() > (self.timestamp + self.ttl)


class CacheBackend(ABC):
    """缓存后端抽象基类"""

    @abstractmethod
    def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        pass

    @abstractmethod
    def set(self, entry: CacheEntry) -> bool:
        """设置缓存条目"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """清空缓存"""
        pass

    @abstractmethod
    def keys(self) -> List[str]:
        """获取所有键"""
        pass

    @abstractmethod
    def size(self) -> int:
        """获取缓存大小"""
        pass


class MemoryCacheBackend(CacheBackend):
    """内存缓存后端"""

    def __init__(self, max_size: int = 1000):
        """
        初始化内存缓存

        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._access_order: List[str] = []  # LRU访问顺序

    def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                # 更新访问顺序
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)

                # 检查是否过期
                if entry.is_expired():
                    self.delete(key)
                    return None
            return entry

    def set(self, entry: CacheEntry) -> bool:
        """设置缓存条目"""
        with self._lock:
            # 如果缓存已满，移除最久未访问的条目
            if len(self._cache) >= self.max_size and entry.key not in self._cache:
                self._evict_lru()

            # 添加或更新条目
            self._cache[entry.key] = entry

            # 更新访问顺序
            if entry.key in self._access_order:
                self._access_order.remove(entry.key)
            self._access_order.append(entry.key)

            return True

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False

    def clear(self) -> bool:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()
            return True

    def keys(self) -> List[str]:
        """获取所有键"""
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)

    def _evict_lru(self):
        """移除最久未访问的条目"""
        if self._access_order:
            lru_key = self._access_order.pop(0)
            if lru_key in self._cache:
                del self._cache[lru_key]


class RedisCacheBackend(CacheBackend):
    """Redis缓存后端"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        初始化Redis缓存

        Args:
            redis_url: Redis连接URL
        """
        try:
            import redis
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            # 测试连接
            self.redis_client.ping()
            self._connected = True
        except ImportError:
            raise ImportError("redis package is required for Redis cache backend")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def get(self, key: str) -> Optional[CacheEntry]:
        """获取缓存条目"""
        if not self._connected:
            return None

        try:
            data = self.redis_client.get(key)
            if data:
                entry_data = json.loads(data)
                entry = CacheEntry(**entry_data)
                if entry.is_expired():
                    self.delete(key)
                    return None
                return entry
            return None
        except Exception:
            return None

    def set(self, entry: CacheEntry) -> bool:
        """设置缓存条目"""
        if not self._connected:
            return False

        try:
            data = json.dumps({
                'key': entry.key,
                'value': entry.value,
                'timestamp': entry.timestamp,
                'ttl': entry.ttl,
                'size': entry.size
            })
            # 设置过期时间
            self.redis_client.setex(entry.key, entry.ttl, data)
            return True
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """删除缓存条目"""
        if not self._connected:
            return False

        try:
            return bool(self.redis_client.delete(key))
        except Exception:
            return False

    def clear(self) -> bool:
        """清空缓存"""
        if not self._connected:
            return False

        try:
            return bool(self.redis_client.flushdb())
        except Exception:
            return False

    def keys(self) -> List[str]:
        """获取所有键"""
        if not self._connected:
            return []

        try:
            keys = self.redis_client.keys()
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        except Exception:
            return []

    def size(self) -> int:
        """获取缓存大小"""
        if not self._connected:
            return 0

        try:
            return self.redis_client.dbsize()
        except Exception:
            return 0


class CacheManager:
    """缓存管理器"""

    def __init__(self, config_manager=None):
        """
        初始化缓存管理器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()
        self.backend: Optional[CacheBackend] = None
        self._setup_backend()

    def _setup_backend(self):
        """设置缓存后端"""
        cache_config = self.config_manager.get_section('cache')
        cache_type = cache_config.get('type', 'memory')
        max_size = cache_config.get('max_size', 1000)

        try:
            if cache_type == 'redis':
                redis_url = cache_config.get('redis_url', 'redis://localhost:6379/0')
                self.backend = RedisCacheBackend(redis_url)
                self.logger.info(f"Redis cache backend initialized: {redis_url}")
            else:
                self.backend = MemoryCacheBackend(max_size)
                self.logger.info(f"Memory cache backend initialized, max_size: {max_size}")
        except Exception as e:
            self.logger.warning(f"Failed to initialize {cache_type} cache backend, falling back to memory: {e}")
            self.backend = MemoryCacheBackend(max_size)

    def _generate_key(self, prefix: str, data: Any) -> str:
        """
        生成缓存键

        Args:
            prefix: 键前缀
            data: 用于生成键的数据

        Returns:
            缓存键
        """
        # 将数据序列化为字符串
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)

        # 生成哈希
        hash_obj = hashlib.md5(data_str.encode())
        hash_hex = hash_obj.hexdigest()

        return f"{prefix}:{hash_hex}"

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值或None
        """
        if not self.backend:
            return None

        entry = self.backend.get(key)
        if entry:
            self.logger.debug(f"Cache hit: {key}")
            return entry.value
        else:
            self.logger.debug(f"Cache miss: {key}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间(秒)，None则使用默认TTL

        Returns:
            是否设置成功
        """
        if not self.backend:
            return False

        # 获取默认TTL
        if ttl is None:
            cache_config = self.config_manager.get_section('cache')
            ttl = cache_config.get('ttl', 3600)

        # 计算值大小
        try:
            value_size = len(json.dumps(value))
        except (TypeError, ValueError):
            value_size = len(str(value))

        # 创建缓存条目
        entry = CacheEntry(
            key=key,
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            size=value_size
        )

        result = self.backend.set(entry)
        if result:
            self.logger.debug(f"Cache set: {key} (TTL: {ttl}s, Size: {value_size})")
        else:
            self.logger.warning(f"Cache set failed: {key}")

        return result

    def delete(self, key: str) -> bool:
        """
        删除缓存条目

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        if not self.backend:
            return False

        result = self.backend.delete(key)
        if result:
            self.logger.debug(f"Cache deleted: {key}")
        return result

    def clear(self) -> bool:
        """
        清空缓存

        Returns:
            是否清空成功
        """
        if not self.backend:
            return False

        result = self.backend.clear()
        if result:
            self.logger.info("Cache cleared")
        return result

    def get_or_set(self, key: str, factory_func, ttl: Optional[int] = None) -> Any:
        """
        获取缓存值，如果不存在则调用工厂函数生成并缓存

        Args:
            key: 缓存键
            factory_func: 工厂函数，用于生成值
            ttl: 过期时间(秒)

        Returns:
            缓存值
        """
        # 尝试从缓存获取
        value = self.get(key)
        if value is not None:
            return value

        # 调用工厂函数生成值
        try:
            value = factory_func()
            # 缓存生成的值
            self.set(key, value, ttl)
            return value
        except Exception as e:
            self.logger.error(f"Factory function failed for key {key}: {e}")
            raise

    def cache_static_analysis(self, file_path: str, analysis_type: str,
                             result: Dict[str, Any]) -> bool:
        """
        缓存静态分析结果

        Args:
            file_path: 文件路径
            analysis_type: 分析类型
            result: 分析结果

        Returns:
            是否缓存成功
        """
        key = self._generate_key(f"static:{analysis_type}", {
            'file_path': file_path,
            'mtime': Path(file_path).stat().st_mtime if Path(file_path).exists() else 0
        })
        return self.set(key, result)

    def get_static_analysis(self, file_path: str,
                           analysis_type: str) -> Optional[Dict[str, Any]]:
        """
        获取静态分析缓存

        Args:
            file_path: 文件路径
            analysis_type: 分析类型

        Returns:
            分析结果或None
        """
        key = self._generate_key(f"static:{analysis_type}", {
            'file_path': file_path,
            'mtime': Path(file_path).stat().st_mtime if Path(file_path).exists() else 0
        })
        return self.get(key)

    def cache_llm_response(self, prompt: str, model: str,
                          response: str) -> bool:
        """
        缓存LLM响应

        Args:
            prompt: 提示词
            model: 模型名称
            response: 响应内容

        Returns:
            是否缓存成功
        """
        key = self._generate_key(f"llm:{model}", prompt)
        return self.set(key, response, ttl=86400)  # LLM响应缓存24小时

    def get_llm_response(self, prompt: str, model: str) -> Optional[str]:
        """
        获取LLM响应缓存

        Args:
            prompt: 提示词
            model: 模型名称

        Returns:
            缓存的响应或None
        """
        key = self._generate_key(f"llm:{model}", prompt)
        return self.get(key)

    def cleanup_expired(self) -> int:
        """
        清理过期的缓存条目

        Returns:
            清理的条目数量
        """
        if not self.backend:
            return 0

        cleaned_count = 0
        keys = self.backend.keys()

        for key in keys:
            entry = self.backend.get(key)
            if entry and entry.is_expired():
                self.backend.delete(key)
                cleaned_count += 1

        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} expired cache entries")

        return cleaned_count

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        if not self.backend:
            return {'backend_type': 'none', 'size': 0}

        keys = self.backend.keys()
        total_size = 0
        expired_count = 0

        for key in keys:
            entry = self.backend.get(key)
            if entry:
                total_size += entry.size
                if entry.is_expired():
                    expired_count += 1

        backend_type = type(self.backend).__name__.replace('CacheBackend', '').lower()

        return {
            'backend_type': backend_type,
            'size': len(keys),
            'total_size_bytes': total_size,
            'expired_entries': expired_count,
            'hit_rate': getattr(self, '_hit_count', 0) / max(getattr(self, '_access_count', 1), 1)
        }


# 全局缓存管理器实例
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    获取全局缓存管理器实例

    Returns:
        缓存管理器实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager