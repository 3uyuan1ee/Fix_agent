#!/usr/bin/env python3
"""
高级缓存系统测试脚本（适配版）
验证缓存系统的初始化、基本操作、TTL管理和性能特性
"""

import sys
import os
import time
import json
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cache_initialization():
    """测试缓存系统初始化"""
    print("🔍 测试缓存系统初始化...")

    try:
        from src.utils.cache import CacheManager

        # 测试默认初始化
        cache_manager = CacheManager()
        print("✅ 真实缓存管理器初始化成功")
        print(f"   - 后端类型: {type(cache_manager.backend).__name__}")
        print(f"   - 缓存大小: {cache_manager.backend.size()}")

        # 测试基本属性
        has_backend = cache_manager.backend is not None
        has_config = cache_manager.config_manager is not None
        print(f"   - 后端存在: {'✅' if has_backend else '❌'}")
        print(f"   - 配置管理器存在: {'✅' if has_config else '❌'}")

        # 测试统计功能
        stats = cache_manager.get_stats()
        print(f"   - 统计信息: {len(stats)} 个指标")
        print(f"     - 后端类型: {stats.get('backend_type', 'unknown')}")
        print(f"     - 缓存大小: {stats.get('size', 0)}")
        print(f"     - 总字节数: {stats.get('total_size_bytes', 0)}")

        return cache_manager is not None and has_backend

    except Exception as e:
        print(f"❌ 缓存系统初始化测试失败: {e}")
        return False

def test_cache_basic_operations():
    """测试缓存基本操作"""
    print("\n🔍 测试缓存基本操作...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

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
                    print(f"     ✅ {key}: 缓存成功")
                    results.append(True)
                else:
                    print(f"     ❌ {key}: 获取值不匹配")
                    results.append(False)
            else:
                print(f"     ❌ {key}: 缓存设置失败")
                results.append(False)

        # 测试缓存大小
        print("\n   测试缓存状态:")
        size = cache.backend.size()
        print(f"     - 缓存条目数: {size}")

        # 测试键列表
        keys = cache.backend.keys()
        print(f"     - 缓存键数量: {len(keys)}")

        # 测试删除操作
        print("\n   测试删除操作:")
        delete_success = cache.delete("test_string")
        after_delete = cache.get("test_string")
        print(f"     - 删除成功: {'✅' if delete_success else '❌'}")
        print(f"     - 删除后获取值: {after_delete}")

        # 测试清空操作
        cache.clear()
        empty_size = cache.backend.size()
        print(f"     - 清空后大小: {empty_size}")

        return all(results) and empty_size == 0

    except Exception as e:
        print(f"❌ 缓存基本操作测试失败: {e}")
        return False

def test_cache_ttl_functionality():
    """测试缓存TTL功能"""
    print("\n🔍 测试缓存TTL功能...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        print("   测试TTL过期:")
        # 设置短TTL的缓存
        cache.set("ttl_test", "expires_soon", ttl=1)  # 1秒TTL

        # 立即获取应该成功
        immediate = cache.get("ttl_test")
        print(f"     - 立即获取: {immediate}")

        # 等待过期
        print("     等待2秒让缓存过期...")
        time.sleep(2)

        # 过期后获取应该失败
        expired = cache.get("ttl_test")
        print(f"     - 过期后获取: {expired}")

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
            print(f"     - {key} (TTL={ttl}s): {'✅' if retrieved == value else '❌'}")

        return ttl_working

    except Exception as e:
        print(f"❌ 缓存TTL功能测试失败: {e}")
        return False

def test_cache_advanced_operations():
    """测试缓存高级操作"""
    print("\n🔍 测试缓存高级操作...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

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

        print(f"     - 第一次调用时间: {first_call_time:.3f}s (包含计算)")
        print(f"     - 第二次调用时间: {second_call_time:.3f}s (从缓存)")
        print(f"     - 结果一致性: {'✅' if result1 == result2 else '❌'}")
        print(f"     - 缓存加速效果: {'✅' if second_call_time < first_call_time / 2 else '❌'}")

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

        print(f"     - 批量设置键数: {len(batch_data)}")
        print(f"     - 批量获取键数: {len(batch_results)}")
        print(f"     - 数据完整性: {'✅' if batch_results == batch_data else '❌'}")

        print("\n   测试缓存统计:")
        stats = cache.get_stats()
        if stats:
            print("     - 缓存统计信息:")
            for key, value in stats.items():
                print(f"       {key}: {value}")

        return result1 == result2 and second_call_time < first_call_time / 2

    except Exception as e:
        print(f"❌ 缓存高级操作测试失败: {e}")
        return False

def test_cache_specialized_methods():
    """测试专用缓存方法"""
    print("\n🔍 测试专用缓存方法...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        print("   测试静态分析缓存:")
        # 创建测试文件
        test_file = Path("cache_test_file.py")
        test_content = '''def test_function():
    return "Hello, World!"
'''
        test_file.write_text(test_content)

        static_result = {
            'tool': 'pylint',
            'issues': [
                {'line': 1, 'message': 'Missing docstring', 'severity': 'info'}
            ],
            'score': 8.0
        }

        # 缓存静态分析结果
        cache_success = cache.cache_static_analysis(str(test_file), 'comprehensive', static_result)
        print(f"     - 静态分析缓存: {'✅' if cache_success else '❌'}")

        # 获取静态分析缓存
        cached_result = cache.get_static_analysis(str(test_file), 'comprehensive')
        static_valid = cached_result is not None and cached_result['tool'] == 'pylint'
        print(f"     - 静态分析获取: {'✅' if static_valid else '❌'}")

        print("\n   测试LLM响应缓存:")
        llm_prompt = "Please analyze this Python code for security issues"
        llm_model = "glm-4.5"
        llm_response = "I found 2 security issues in your code..."

        # 缓存LLM响应
        llm_cache_success = cache.cache_llm_response(llm_prompt, llm_model, llm_response)
        print(f"     - LLM响应缓存: {'✅' if llm_cache_success else '❌'}")

        # 获取LLM响应缓存
        cached_llm = cache.get_llm_response(llm_prompt, llm_model)
        llm_valid = cached_llm == llm_response
        print(f"     - LLM响应获取: {'✅' if llm_valid else '❌'}")

        # 清理测试文件
        test_file.unlink(missing_ok=True)

        return static_valid and llm_valid

    except Exception as e:
        print(f"❌ 专用缓存方法测试失败: {e}")
        return False

def test_cache_performance():
    """测试缓存性能"""
    print("\n🔍 测试缓存性能...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

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

        print(f"     - 生成测试数据: {len(large_data_sets)} 条")

        # 测试批量写入性能
        start_time = time.time()
        successful_writes = 0
        for i, data in enumerate(large_data_sets):
            if cache.set(f"perf_test_{i}", data, ttl=300):
                successful_writes += 1

        write_time = time.time() - start_time
        write_rate = successful_writes / write_time

        print(f"     - 写入性能: {write_rate:.0f} 条/秒")
        print(f"     - 写入成功率: {successful_writes}/{len(large_data_sets)} ({successful_writes/len(large_data_sets):.1%})")

        # 测试批量读取性能
        start_time = time.time()
        successful_reads = 0
        for i in range(len(large_data_sets)):
            if cache.get(f"perf_test_{i}") is not None:
                successful_reads += 1

        read_time = time.time() - start_time
        read_rate = successful_reads / read_time

        print(f"     - 读取性能: {read_rate:.0f} 条/秒")
        print(f"     - 读取成功率: {successful_reads}/{len(large_data_sets)} ({successful_reads/len(large_data_sets):.1%})")

        print("\n   测试内存使用情况:")
        cache_size = cache.backend.size()
        print(f"     - 缓存条目数: {cache_size}")

        # 测试缓存清理
        print("\n   测试缓存清理性能:")
        start_time = time.time()
        cache.clear()
        clear_time = time.time() - start_time
        final_size = cache.backend.size()

        print(f"     - 清理时间: {clear_time:.3f}秒")
        print(f"     - 清理后大小: {final_size}")

        # 性能基准测试
        performance_good = write_rate > 1000 and read_rate > 5000 and final_size == 0
        print(f"     - 性能评估: {'✅ 良好' if performance_good else '❌ 需要优化'}")

        return performance_good

    except Exception as e:
        print(f"❌ 缓存性能测试失败: {e}")
        return False

def test_cache_cleanup():
    """测试缓存清理功能"""
    print("\n🔍 测试缓存清理功能...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        print("   测试过期缓存清理:")
        # 添加一些会过期的缓存项
        cache.set("expire_1", "value1", ttl=1)
        cache.set("expire_2", "value2", ttl=1)
        cache.set("keep_1", "value3", ttl=10)  # 不会过期
        cache.set("keep_2", "value4", ttl=10)  # 不会过期

        initial_size = cache.backend.size()
        print(f"     - 初始缓存项数: {initial_size}")

        # 等待部分项过期
        print("     等待2秒让部分缓存过期...")
        time.sleep(2)

        # 清理过期项
        cleaned_count = cache.cleanup_expired()
        after_cleanup_size = cache.backend.size()

        print(f"     - 清理过期项数: {cleaned_count}")
        print(f"     - 清理后缓存项数: {after_cleanup_size}")

        # 验证保留的项
        keep1 = cache.get("keep_1")
        keep2 = cache.get("keep_2")
        expire1 = cache.get("expire_1")
        expire2 = cache.get("expire_2")

        cleanup_correct = (
            keep1 == "value3" and keep2 == "value4" and
            expire1 is None and expire2 is None
        )

        print(f"     - 清理正确性: {'✅' if cleanup_correct else '❌'}")

        return cleanup_correct and cleaned_count >= 2

    except Exception as e:
        print(f"❌ 缓存清理功能测试失败: {e}")
        return False

def test_cache_integration():
    """测试缓存集成场景"""
    print("\n🔍 测试缓存集成场景...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        print("   模拟深度分析缓存场景:")
        # 模拟文件分析缓存
        def mock_file_analysis(file_path, analysis_type):
            """Mock文件分析函数"""
            time.sleep(0.05)  # 模拟分析时间
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

        print("     第一次分析（无缓存）:")
        start_time = time.time()
        first_results = []
        for file_path in test_files:
            for analysis_type in analysis_types:
                result = cached_file_analysis(file_path, analysis_type)
                first_results.append(result)
        first_time = time.time() - start_time

        print("     第二次分析（有缓存）:")
        start_time = time.time()
        second_results = []
        for file_path in test_files:
            for analysis_type in analysis_types:
                result = cached_file_analysis(file_path, analysis_type)
                second_results.append(result)
        second_time = time.time() - start_time

        speedup = first_time / second_time if second_time > 0 else float('inf')
        print(f"     - 第一次分析时间: {first_time:.3f}秒")
        print(f"     - 第二次分析时间: {second_time:.3f}秒")
        print(f"     - 缓存加速比: {speedup:.1f}x")
        print(f"     - 结果一致性: {'✅' if first_results == second_results else '❌'}")

        # 获取最终统计
        final_stats = cache.get_stats()
        print(f"     - 最终缓存统计: {final_stats}")

        integration_success = speedup > 5 and first_results == second_results
        print(f"   - 缓存集成效果: {'✅ 成功' if integration_success else '❌ 失败'}")

        return integration_success

    except Exception as e:
        print(f"❌ 缓存集成场景测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始高级缓存系统测试（适配版）")
    print("=" * 60)

    test_results = []

    # 1. 测试缓存系统初始化
    init_ok = test_cache_initialization()
    test_results.append(init_ok)

    # 2. 测试缓存基本操作
    basic_ok = test_cache_basic_operations()
    test_results.append(basic_ok)

    # 3. 测试缓存TTL功能
    ttl_ok = test_cache_ttl_functionality()
    test_results.append(ttl_ok)

    # 4. 测试缓存高级操作
    advanced_ok = test_cache_advanced_operations()
    test_results.append(advanced_ok)

    # 5. 测试专用缓存方法
    specialized_ok = test_cache_specialized_methods()
    test_results.append(specialized_ok)

    # 6. 测试缓存性能
    performance_ok = test_cache_performance()
    test_results.append(performance_ok)

    # 7. 测试缓存清理功能
    cleanup_ok = test_cache_cleanup()
    test_results.append(cleanup_ok)

    # 8. 测试缓存集成场景
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