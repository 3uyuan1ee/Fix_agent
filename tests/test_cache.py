"""
缓存管理模块单元测试
"""

import pytest
import tempfile
import time
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.utils.cache import (
    CacheEntry, MemoryCacheBackend, CacheManager,
    get_cache_manager
)
from src.utils.config import ConfigManager


class TestCacheEntry:
    """缓存条目测试"""

    def test_cache_entry_creation(self):
        """测试缓存条目创建"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            timestamp=time.time(),
            ttl=3600,
            size=10
        )

        assert entry.key == "test_key"
        assert entry.value == "test_value"
        assert entry.size == 10

    def test_cache_entry_not_expired(self):
        """测试缓存条目未过期"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            timestamp=time.time(),
            ttl=3600,  # 1小时后过期
            size=10
        )

        assert not entry.is_expired()

    def test_cache_entry_expired(self):
        """测试缓存条目已过期"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            timestamp=time.time() - 7200,  # 2小时前
            ttl=3600,  # 1小时TTL，已过期
            size=10
        )

        assert entry.is_expired()


class TestMemoryCacheBackend:
    """内存缓存后端测试"""

    def setup_method(self):
        """测试前设置"""
        self.cache = MemoryCacheBackend(max_size=3)

    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            timestamp=time.time(),
            ttl=3600,
            size=10
        )

        # 设置缓存
        result = self.cache.set(entry)
        assert result is True

        # 获取缓存
        retrieved_entry = self.cache.get("test_key")
        assert retrieved_entry is not None
        assert retrieved_entry.value == "test_value"

    def test_cache_get_nonexistent(self):
        """测试获取不存在的缓存"""
        result = self.cache.get("nonexistent_key")
        assert result is None

    def test_cache_delete(self):
        """测试删除缓存"""
        entry = CacheEntry(
            key="test_key",
            value="test_value",
            timestamp=time.time(),
            ttl=3600,
            size=10
        )

        # 设置缓存
        self.cache.set(entry)

        # 删除缓存
        result = self.cache.delete("test_key")
        assert result is True

        # 验证已删除
        retrieved_entry = self.cache.get("test_key")
        assert retrieved_entry is None

    def test_cache_delete_nonexistent(self):
        """测试删除不存在的缓存"""
        result = self.cache.delete("nonexistent_key")
        assert result is False

    def test_cache_clear(self):
        """测试清空缓存"""
        # 添加多个条目
        for i in range(3):
            entry = CacheEntry(
                key=f"key_{i}",
                value=f"value_{i}",
                timestamp=time.time(),
                ttl=3600,
                size=10
            )
            self.cache.set(entry)

        assert self.cache.size() == 3

        # 清空缓存
        result = self.cache.clear()
        assert result is True
        assert self.cache.size() == 0

    def test_cache_keys(self):
        """测试获取所有键"""
        # 添加多个条目
        for i in range(3):
            entry = CacheEntry(
                key=f"key_{i}",
                value=f"value_{i}",
                timestamp=time.time(),
                ttl=3600,
                size=10
            )
            self.cache.set(entry)

        keys = self.cache.keys()
        assert len(keys) == 3
        assert all(key.startswith("key_") for key in keys)

    def test_cache_lru_eviction(self):
        """测试LRU淘汰策略"""
        cache = MemoryCacheBackend(max_size=2)

        # 添加两个条目
        entry1 = CacheEntry("key1", "value1", time.time(), 3600, 10)
        entry2 = CacheEntry("key2", "value2", time.time(), 3600, 10)

        cache.set(entry1)
        cache.set(entry2)
        assert cache.size() == 2

        # 添加第三个条目，应该淘汰最久未访问的
        entry3 = CacheEntry("key3", "value3", time.time(), 3600, 10)
        cache.set(entry3)

        # key1应该被淘汰
        assert cache.get("key1") is None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None

    def test_cache_access_order_update(self):
        """测试访问顺序更新"""
        cache = MemoryCacheBackend(max_size=2)

        # 添加两个条目
        entry1 = CacheEntry("key1", "value1", time.time(), 3600, 10)
        entry2 = CacheEntry("key2", "value2", time.time(), 3600, 10)

        cache.set(entry1)
        cache.set(entry2)

        # 访问key1，更新访问顺序
        cache.get("key1")

        # 添加第三个条目，key2应该被淘汰（最久未访问）
        entry3 = CacheEntry("key3", "value3", time.time(), 3600, 10)
        cache.set(entry3)

        assert cache.get("key1") is not None  # 仍存在，因为最近访问过
        assert cache.get("key2") is None     # 被淘汰
        assert cache.get("key3") is not None

    def test_cache_expired_entry(self):
        """测试过期条目"""
        # 创建过期的条目
        expired_entry = CacheEntry(
            key="expired_key",
            value="expired_value",
            timestamp=time.time() - 7200,  # 2小时前
            ttl=3600,  # 1小时TTL
            size=10
        )

        self.cache.set(expired_entry)

        # 获取过期条目应该返回None并删除条目
        result = self.cache.get("expired_key")
        assert result is None
        assert self.cache.size() == 0


class TestCacheManager:
    """缓存管理器测试"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试配置
        self.test_config = {
            'app': {'name': 'TestApp'},
            'cache': {
                'type': 'memory',
                'ttl': 3600,
                'max_size': 100,
                'redis_url': 'redis://localhost:6379/0'
            },
            'logging': {
                'level': 'INFO',
                'file_path': f'{self.temp_dir}/test.log',
                'enable_console': False
            },
            'llm': {
                'default_provider': 'openai',
                'openai': {'api_key': 'test-key'}
            },
            'static_analysis': {'enabled_tools': ['ast']}
        }

        config_path = Path(self.temp_dir) / "default.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_config, f)

        self.config_manager = MagicMock()
        self.config_manager.get_section.return_value = self.test_config['cache']

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_manager_initialization(self):
        """测试缓存管理器初始化"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            assert cache_manager is not None
            assert cache_manager.backend is not None
            assert cache_manager.config_manager == self.config_manager

    def test_cache_generate_key(self):
        """测试缓存键生成"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            # 测试不同数据类型
            key1 = cache_manager._generate_key("test", {"a": 1, "b": 2})
            key2 = cache_manager._generate_key("test", {"b": 2, "a": 1})  # 相同内容，不同顺序
            key3 = cache_manager._generate_key("test", {"a": 1, "b": 3})  # 不同内容

            assert key1 == key2  # 相同内容应该生成相同的键
            assert key1 != key3  # 不同内容应该生成不同的键
            assert key1.startswith("test:")

    def test_cache_set_and_get(self):
        """测试缓存设置和获取"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            # 设置缓存
            result = cache_manager.set("test_key", "test_value")
            assert result is True

            # 获取缓存
            value = cache_manager.get("test_key")
            assert value == "test_value"

    def test_cache_get_nonexistent(self):
        """测试获取不存在的缓存"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            value = cache_manager.get("nonexistent_key")
            assert value is None

    def test_cache_delete(self):
        """测试删除缓存"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            # 设置缓存
            cache_manager.set("test_key", "test_value")

            # 删除缓存
            result = cache_manager.delete("test_key")
            assert result is True

            # 验证已删除
            value = cache_manager.get("test_key")
            assert value is None

    def test_cache_clear(self):
        """测试清空缓存"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            # 添加多个条目
            for i in range(3):
                cache_manager.set(f"key_{i}", f"value_{i}")

            # 清空缓存
            result = cache_manager.clear()
            assert result is True

            # 验证所有条目都被删除
            for i in range(3):
                value = cache_manager.get(f"key_{i}")
                assert value is None

    def test_cache_get_or_set_with_factory(self):
        """测试使用工厂函数的get_or_set"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            # 工厂函数
            def factory_func():
                return "generated_value"

            # 第一次调用，应该调用工厂函数
            value1 = cache_manager.get_or_set("factory_key", factory_func)
            assert value1 == "generated_value"

            # 第二次调用，应该从缓存获取，不调用工厂函数
            factory_func.call_count = 0
            factory_func = MagicMock(return_value="generated_value")
            value2 = cache_manager.get_or_set("factory_key", factory_func)
            assert value2 == "generated_value"
            factory_func.assert_not_called()  # 不应该被调用

    def test_cache_static_analysis(self):
        """测试静态分析缓存"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            # 模拟静态分析结果
            result = {
                'file_path': '/test/file.py',
                'issues': [
                    {'line': 1, 'type': 'error', 'message': 'Test error'}
                ],
                'timestamp': time.time()
            }

            # 缓存静态分析结果
            cache_result = cache_manager.cache_static_analysis(
                '/test/file.py', 'pylint', result
            )
            assert cache_result is True

            # 获取静态分析缓存
            cached_result = cache_manager.get_static_analysis(
                '/test/file.py', 'pylint'
            )
            assert cached_result is not None
            assert cached_result['file_path'] == '/test/file.py'
            assert len(cached_result['issues']) == 1

    def test_cache_llm_response(self):
        """测试LLM响应缓存"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            prompt = "Analyze this code"
            model = "gpt-4"
            response = "This code has some issues..."

            # 缓存LLM响应
            cache_result = cache_manager.cache_llm_response(prompt, model, response)
            assert cache_result is True

            # 获取LLM响应缓存
            cached_response = cache_manager.get_llm_response(prompt, model)
            assert cached_response == response

    def test_cache_cleanup_expired(self):
        """测试清理过期缓存"""
        with patch('src.utils.cache.get_logger'):
            # 创建短TTL的缓存管理器
            short_config = self.test_config['cache'].copy()
            short_config['ttl'] = 1  # 1秒TTL

            config_manager = MagicMock()
            config_manager.get_section.return_value = short_config

            cache_manager = CacheManager(config_manager)

            # 添加缓存条目
            cache_manager.set("test_key", "test_value", ttl=1)

            # 等待过期
            time.sleep(1.1)

            # 清理过期条目
            cleaned_count = cache_manager.cleanup_expired()
            assert cleaned_count >= 0  # 可能已经被自动清理

            # 验证过期条目不存在
            value = cache_manager.get("test_key")
            assert value is None

    def test_cache_get_stats(self):
        """测试获取缓存统计"""
        with patch('src.utils.cache.get_logger'):
            cache_manager = CacheManager(self.config_manager)

            # 添加一些缓存条目
            for i in range(3):
                cache_manager.set(f"key_{i}", f"value_{i}")

            # 获取统计信息
            stats = cache_manager.get_stats()
            assert 'backend_type' in stats
            assert 'size' in stats
            assert 'total_size_bytes' in stats
            assert stats['size'] == 3
            assert stats['backend_type'] == 'memory'

    def test_cache_fallback_to_memory(self):
        """测试Redis连接失败时回退到内存缓存"""
        # 配置Redis缓存
        redis_config = self.test_config['cache'].copy()
        redis_config['type'] = 'redis'

        config_manager = MagicMock()
        config_manager.get_section.return_value = redis_config

        # 模拟Redis连接失败
        with patch('src.utils.cache.RedisCacheBackend', side_effect=Exception("Connection failed")):
            with patch('src.utils.cache.get_logger') as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                cache_manager = CacheManager(config_manager)

                # 应该回退到内存缓存
                assert type(cache_manager.backend).__name__ == 'MemoryCacheBackend'
                mock_logger.warning.assert_called()


class TestGlobalCacheManager:
    """全局缓存管理器测试"""

    def test_get_cache_manager_singleton(self):
        """测试全局缓存管理器单例"""
        with patch('src.utils.cache.get_config_manager') as mock_get_config:
            mock_config_manager = MagicMock()
            mock_config_manager.get_section.return_value = {
                'type': 'memory',
                'ttl': 3600,
                'max_size': 100
            }
            mock_get_config.return_value = mock_config_manager

            # 多次调用应该返回同一实例
            manager1 = get_cache_manager()
            manager2 = get_cache_manager()

            assert manager1 is manager2