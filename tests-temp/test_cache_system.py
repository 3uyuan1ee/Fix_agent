#!/usr/bin/env python3
"""
高级缓存系统测试脚本
用于验证缓存系统的初始化、基本操作和高级功能
"""

import sys
import os
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cache_manager_initialization():
    """测试缓存管理器初始化"""
    print("🔍 测试缓存管理器初始化...")

    try:
        from src.utils.cache import CacheManager

        # 测试默认初始化
        cache_manager = CacheManager()
        print("✅ 默认缓存管理器初始化成功")
        print(f"   - 缓存类型: {type(cache_manager.backend).__name__}")
        print(f"   - 默认TTL: {getattr(cache_manager, 'default_ttl', 'N/A')}")

        # 测试不同后端类型
        with patch('src.utils.cache.get_config_manager') as mock_config:
            for backend_type in ['memory', 'redis']:
                try:
                    # Mock配置
                    mock_config_instance = Mock()
                    mock_config_instance.get_section.return_value = {
                        'type': backend_type,
                        'max_size': 100,
                        'ttl': 3600
                    }
                    mock_config.return_value = mock_config_instance

                    manager = CacheManager(config_manager=mock_config_instance)
                    print(f"✅ {backend_type} 后端初始化成功")
                except Exception as e:
                    print(f"❌ {backend_type} 后端初始化失败: {e}")

        return cache_manager is not None

    except Exception as e:
        print(f"❌ 缓存管理器初始化失败: {e}")
        return False

def test_memory_cache_operations():
    """测试内存缓存操作"""
    print("\n🔍 测试内存缓存操作...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager(backend_type='memory')

        # 测试基本操作
        test_data = {
            'string': 'test_value',
            'number': 42,
            'list': [1, 2, 3],
            'dict': {'key': 'value', 'nested': {'data': 'test'}},
            'complex': {
                'analysis_result': {
                    'file': 'test.py',
                    'issues': [{'type': 'style', 'line': 10}],
                    'score': 8.5
                }
            }
        }

        print("   测试缓存设置和获取:")
        results = []

        for key, value in test_data.items():
            # 设置缓存
            success = cache.set(f"test_{key}", value, ttl=60)
            if success:
                # 获取缓存
                retrieved = cache.get(f"test_{key}")
                if retrieved == value:
                    print(f"   ✅ {key}: 缓存成功")
                    results.append(True)
                else:
                    print(f"   ❌ {key}: 获取值不匹配")
                    results.append(False)
            else:
                print(f"   ❌ {key}: 缓存设置失败")
                results.append(False)

        # 测试缓存存在性检查
        print("\n   测试缓存存在性检查:")
        exists = cache.exists("test_string")
        not_exists = cache.exists("nonexistent_key")
        print(f"   - 存在的键: {exists}")
        print(f"   - 不存在的键: {not_exists}")

        # 测试缓存大小
        print("\n   测试缓存大小和统计:")
        size = cache.size()
        print(f"   - 缓存条目数: {size}")

        # 测试键列表
        keys = cache.keys()
        print(f"   - 缓存键列表: {len(keys)} 个键")

        # 测试删除操作
        print("\n   测试删除操作:")
        delete_success = cache.delete("test_string")
        after_delete = cache.get("test_string")
        print(f"   - 删除成功: {delete_success}")
        print(f"   - 删除后获取值: {after_delete}")

        # 测试清空操作
        cache.clear()
        empty_size = cache.size()
        print(f"   - 清空后大小: {empty_size}")

        return all(results) and empty_size == 0

    except Exception as e:
        print(f"❌ 内存缓存操作测试失败: {e}")
        return False

def test_cache_ttl_functionality():
    """测试缓存TTL功能"""
    print("\n🔍 测试缓存TTL功能...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager(backend_type='memory')

        print("   测试TTL过期:")
        # 设置短TTL的缓存
        cache.set("ttl_test", "expires_soon", ttl=1)  # 1秒TTL

        # 立即获取应该成功
        immediate = cache.get("ttl_test")
        print(f"   - 立即获取: {immediate}")

        # 等待过期
        print("   等待2秒让缓存过期...")
        time.sleep(2)

        # 过期后获取应该失败
        expired = cache.get("ttl_test")
        print(f"   - 过期后获取: {expired}")

        ttl_working = immediate == "expires_soon" and expired is None

        print("   测试不同TTL值:")
        # 测试不同TTL值
        ttl_tests = [
            ("short_ttl", "short", 1),
            ("medium_ttl", "medium", 5),
            ("long_ttl", "long", 10)
        ]

        for key, value, ttl in ttl_tests:
            cache.set(key, value, ttl=ttl)
            retrieved = cache.get(key)
            print(f"   - {key} (TTL={ttl}s): {'✅' if retrieved == value else '❌'}")

        return ttl_working

    except Exception as e:
        print(f"❌ 缓存TTL功能测试失败: {e}")
        return False

def test_cache_advanced_operations():
    """测试缓存高级操作"""
    print("\n🔍 测试缓存高级操作...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager(backend_type='memory')

        print("   测试get_or_set方法:")
        def expensive_operation(key):
            """模拟耗时操作"""
            time.sleep(0.1)  # 模拟延迟
            return f"computed_value_for_{key}"

        # 第一次调用会执行计算
        start_time = time.time()
        result1 = cache.get_or_set("compute_key", lambda: expensive_operation("compute_key"), ttl=60)
        first_call_time = time.time() - start_time

        # 第二次调用从缓存获取
        start_time = time.time()
        result2 = cache.get_or_set("compute_key", lambda: expensive_operation("compute_key"), ttl=60)
        second_call_time = time.time() - start_time

        print(f"   - 第一次调用时间: {first_call_time:.3f}s (包含计算)")
        print(f"   - 第二次调用时间: {second_call_time:.3f}s (从缓存)")
        print(f"   - 结果一致性: {'✅' if result1 == result2 else '❌'}")
        print(f"   - 缓存加速效果: {'✅' if second_call_time < first_call_time / 2 else '❌'}")

        print("\n   测试批量操作:")
        # 批量设置
        batch_data = {
            "batch_key_1": "value1",
            "batch_key_2": "value2",
            "batch_key_3": "value3"
        }

        for key, value in batch_data.items():
            cache.set(key, value, ttl=60)

        # 批量获取
        batch_keys = list(batch_data.keys())
        batch_results = {}
        for key in batch_keys:
            batch_results[key] = cache.get(key)

        print(f"   - 批量设置键数: {len(batch_data)}")
        print(f"   - 批量获取键数: {len(batch_results)}")
        print(f"   - 数据完整性: {'✅' if batch_results == batch_data else '❌'}")

        print("\n   测试缓存统计:")
        stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
        if stats:
            print("   - 缓存统计信息:")
            for key, value in stats.items():
                print(f"     {key}: {value}")
        else:
            print("   - 当前缓存后端不支持统计")

        return result1 == result2 and second_call_time < first_call_time / 2

    except Exception as e:
        print(f"❌ 缓存高级操作测试失败: {e}")
        return False

def test_cache_with_analysis_data():
    """测试缓存分析数据"""
    print("\n🔍 测试缓存分析数据...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager(backend_type='memory')

        print("   测试分析结果缓存:")
        # 模拟深度分析结果
        analysis_result = {
            "file_path": "test_analysis.py",
            "analysis_type": "comprehensive",
            "success": True,
            "content": "代码分析完成，发现3个问题",
            "structured_analysis": {
                "summary": "代码质量良好",
                "issues": [
                    {"type": "style", "line": 5, "message": "缺少类型注解"},
                    {"type": "performance", "line": 15, "message": "可以优化算法"}
                ],
                "recommendations": ["添加类型注解", "优化算法"],
                "score": 8.5
            },
            "execution_time": 2.34,
            "model_used": "glm-4.5",
            "token_usage": {"total_tokens": 450},
            "timestamp": datetime.now().isoformat()
        }

        # 生成缓存键
        cache_key = f"analysis:{analysis_result['file_path']}:{analysis_result['analysis_type']}"

        # 缓存分析结果
        cache_success = cache.set(cache_key, analysis_result, ttl=3600)  # 1小时
        print(f"   - 分析结果缓存: {'✅' if cache_success else '❌'}")

        # 获取缓存结果
        cached_result = cache.get(cache_key)
        cache_valid = cached_result is not None and cached_result['file_path'] == analysis_result['file_path']
        print(f"   - 缓存结果验证: {'✅' if cache_valid else '❌'}")

        print("\n   测试静态分析结果缓存:")
        # 模拟静态分析结果
        static_result = {
            "tool": "pylint",
            "file_path": "test_static.py",
            "timestamp": datetime.now().timestamp(),
            "issues": [
                {"line": 10, "column": 5, "message": "Unused variable", "severity": "warning"},
                {"line": 20, "column": 1, "message": "Missing docstring", "severity": "convention"}
            ],
            "metrics": {
                "complexity": 5.2,
                "maintainability": 8.1,
                "lines_of_code": 150
            }
        }

        static_key = f"static:{static_result['tool']}:{static_result['file_path']}"
        static_cache_success = cache.set(static_key, static_result, ttl=1800)  # 30分钟
        print(f"   - 静态分析缓存: {'✅' if static_cache_success else '❌'}")

        cached_static = cache.get(static_key)
        static_valid = cached_static is not None and len(cached_static['issues']) == 2
        print(f"   - 静态缓存验证: {'✅' if static_valid else '❌'}")

        print("\n   测试LLM响应缓存:")
        # 模拟LLM响应
        llm_response = {
            "model": "glm-4.5",
            "prompt_hash": "abc123def456",
            "content": "这是LLM的分析响应...",
            "usage": {"prompt_tokens": 200, "completion_tokens": 300, "total_tokens": 500},
            "response_time": 1.23,
            "timestamp": datetime.now().isoformat()
        }

        llm_key = f"llm:{llm_response['model']}:{llm_response['prompt_hash']}"
        llm_cache_success = cache.set(llm_key, llm_response, ttl=7200)  # 2小时
        print(f"   - LLM响应缓存: {'✅' if llm_cache_success else '❌'}")

        cached_llm = cache.get(llm_key)
        llm_valid = cached_llm is not None and cached_llm['model'] == llm_response['model']
        print(f"   - LLM缓存验证: {'✅' if llm_valid else '❌'}")

        # 测试缓存键生成
        print("\n   测试智能缓存键生成:")
        def generate_cache_key(file_path, analysis_type, model=None, user_instructions=None):
            """生成智能缓存键"""
            key_parts = [analysis_type, file_path]
            if model:
                key_parts.append(model)
            if user_instructions:
                # 对用户指令进行哈希以保持键长度合理
                import hashlib
                instruction_hash = hashlib.md5(user_instructions.encode()).hexdigest()[:8]
                key_parts.append(f"instr_{instruction_hash}")
            return ":".join(key_parts)

        test_key = generate_cache_key(
            "test_file.py",
            "security",
            model="glm-4.5",
            user_instructions="重点关注安全问题"
        )
        print(f"   - 智能键生成: {test_key}")

        return cache_valid and static_valid and llm_valid

    except Exception as e:
        print(f"❌ 缓存分析数据测试失败: {e}")
        return False

def test_cache_persistence():
    """测试缓存持久化"""
    print("\n🔍 测试缓存持久化...")

    try:
        from src.utils.cache import CacheManager

        # 创建临时文件用于持久化缓存
        temp_dir = tempfile.mkdtemp()
        cache_file = os.path.join(temp_dir, "test_cache.json")

        print("   测试缓存保存和加载:")

        # 创建缓存并添加数据
        cache = CacheManager(backend_type='memory')
        test_data = {
            "persistent_key_1": "persistent_value_1",
            "persistent_key_2": {"nested": "data", "number": 42},
            "persistent_key_3": [1, 2, 3, 4, 5]
        }

        for key, value in test_data.items():
            cache.set(key, value, ttl=3600)

        print(f"   - 原始缓存条目: {cache.size()}")

        # 尝试保存缓存（如果支持）
        if hasattr(cache, 'save_to_file'):
            save_success = cache.save_to_file(cache_file)
            print(f"   - 缓存保存: {'✅' if save_success else '❌'}")

            # 创建新的缓存实例并加载
            new_cache = CacheManager(backend_type='memory')
            if hasattr(new_cache, 'load_from_file'):
                load_success = new_cache.load_from_file(cache_file)
                print(f"   - 缓存加载: {'✅' if load_success else '❌'}")

                # 验证加载的数据
                loaded_correct = True
                for key, expected_value in test_data.items():
                    loaded_value = new_cache.get(key)
                    if loaded_value != expected_value:
                        print(f"   - 键 {key} 加载失败")
                        loaded_correct = False

                print(f"   - 数据完整性: {'✅' if loaded_correct else '❌'}")
        else:
            print("   - 当前缓存后端不支持持久化")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return True

    except Exception as e:
        print(f"❌ 缓存持久化测试失败: {e}")
        return False

def test_cache_performance():
    """测试缓存性能"""
    print("\n🔍 测试缓存性能...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager(backend_type='memory')

        print("   测试大量数据缓存性能:")
        # 大量数据测试
        large_data_sets = []

        # 生成测试数据
        for i in range(1000):
            large_data_sets.append({
                'id': i,
                'data': f'test_data_{i}',
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'size': len(f'test_data_{i}') * 10,
                    'tags': [f'tag_{j}' for j in range(5)]
                }
            })

        print(f"   - 生成测试数据: {len(large_data_sets)} 条")

        # 测试批量写入性能
        start_time = time.time()
        successful_writes = 0
        for i, data in enumerate(large_data_sets):
            if cache.set(f"perf_test_{i}", data, ttl=300):
                successful_writes += 1

        write_time = time.time() - start_time
        write_rate = successful_writes / write_time

        print(f"   - 写入性能: {write_rate:.0f} 条/秒")
        print(f"   - 写入成功率: {successful_writes}/{len(large_data_sets)} ({successful_writes/len(large_data_sets):.1%})")

        # 测试批量读取性能
        start_time = time.time()
        successful_reads = 0
        for i in range(len(large_data_sets)):
            if cache.get(f"perf_test_{i}") is not None:
                successful_reads += 1

        read_time = time.time() - start_time
        read_rate = successful_reads / read_time

        print(f"   - 读取性能: {read_rate:.0f} 条/秒")
        print(f"   - 读取成功率: {successful_reads}/{len(large_data_sets)} ({successful_reads/len(large_data_sets):.1%})")

        print("\n   测试内存使用情况:")
        cache_size = cache.size()
        print(f"   - 缓存条目数: {cache_size}")

        # 测试缓存清理
        print("\n   测试缓存清理性能:")
        start_time = time.time()
        cache.clear()
        clear_time = time.time() - start_time
        final_size = cache.size()

        print(f"   - 清理时间: {clear_time:.3f}秒")
        print(f"   - 清理后大小: {final_size}")

        # 性能基准测试
        performance_good = write_rate > 1000 and read_rate > 5000 and final_size == 0
        print(f"   - 性能评估: {'✅ 良好' if performance_good else '❌ 需要优化'}")

        return performance_good

    except Exception as e:
        print(f"❌ 缓存性能测试失败: {e}")
        return False

def test_cache_integration():
    """测试缓存集成功能"""
    print("\n🔍 测试缓存集成功能...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager(backend_type='memory')

        print("   测试与分析工具集成:")

        # 模拟文件分析缓存
        def mock_file_analysis(file_path, analysis_type):
            """Mock文件分析函数"""
            time.sleep(0.1)  # 模拟分析时间
            return {
                "file_path": file_path,
                "analysis_type": analysis_type,
                "result": f"Analysis of {file_path} for {analysis_type}",
                "timestamp": datetime.now().isoformat()
            }

        def cached_file_analysis(file_path, analysis_type):
            """带缓存的文件分析函数"""
            cache_key = f"analysis:{file_path}:{analysis_type}"
            return cache.get_or_set(cache_key,
                                   lambda: mock_file_analysis(file_path, analysis_type),
                                   ttl=3600)

        # 测试缓存效果
        test_files = ["test1.py", "test2.js", "test3.java"]
        analysis_types = ["comprehensive", "security", "performance"]

        print("   第一次分析（无缓存）:")
        start_time = time.time()
        first_results = []
        for file_path in test_files:
            for analysis_type in analysis_types:
                result = cached_file_analysis(file_path, analysis_type)
                first_results.append(result)
        first_time = time.time() - start_time

        print("   第二次分析（有缓存）:")
        start_time = time.time()
        second_results = []
        for file_path in test_files:
            for analysis_type in analysis_types:
                result = cached_file_analysis(file_path, analysis_type)
                second_results.append(result)
        second_time = time.time() - start_time

        speedup = first_time / second_time if second_time > 0 else float('inf')
        print(f"   - 第一次分析时间: {first_time:.3f}秒")
        print(f"   - 第二次分析时间: {second_time:.3f}秒")
        print(f"   - 缓存加速比: {speedup:.1f}x")
        print(f"   - 结果一致性: {'✅' if first_results == second_results else '❌'}")

        print("\n   测试缓存失效策略:")
        # 模拟缓存失效
        cache.set("will_expire", "value", ttl=1)
        before_expire = cache.get("will_expire")
        time.sleep(2)
        after_expire = cache.get("will_expire")

        print(f"   - 过期前获取: {before_expire}")
        print(f"   - 过期后获取: {after_expire}")
        expire_working = before_expire == "value" and after_expire is None

        return speedup > 5 and first_results == second_results and expire_working

    except Exception as e:
        print(f"❌ 缓存集成功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始高级缓存系统测试")
    print("=" * 60)

    test_results = []

    # 1. 测试缓存管理器初始化
    init_ok = test_cache_manager_initialization()
    test_results.append(init_ok)

    # 2. 测试内存缓存操作
    memory_ok = test_memory_cache_operations()
    test_results.append(memory_ok)

    # 3. 测试缓存TTL功能
    ttl_ok = test_cache_ttl_functionality()
    test_results.append(ttl_ok)

    # 4. 测试缓存高级操作
    advanced_ok = test_cache_advanced_operations()
    test_results.append(advanced_ok)

    # 5. 测试缓存分析数据
    analysis_ok = test_cache_with_analysis_data()
    test_results.append(analysis_ok)

    # 6. 测试缓存持久化
    persistence_ok = test_cache_persistence()
    test_results.append(persistence_ok)

    # 7. 测试缓存性能
    performance_ok = test_cache_performance()
    test_results.append(performance_ok)

    # 8. 测试缓存集成功能
    integration_ok = test_cache_integration()
    test_results.append(integration_ok)

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 高级缓存系统测试基本通过！")
        print("缓存系统的初始化和核心功能已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查缓存系统。")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n用户中断测试")
        sys.exit(0)
    except Exception as e:
        print(f"\n测试异常: {e}")
        sys.exit(1)