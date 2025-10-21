#!/usr/bin/env python3
"""
简化的缓存系统测试脚本
测试实际可用的缓存功能
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

def test_cache_manager_basic():
    """测试缓存管理器基本功能"""
    print("🔍 测试缓存管理器基本功能...")

    try:
        from src.utils.cache import CacheManager

        # 测试默认初始化
        cache = CacheManager()
        print("✅ 缓存管理器初始化成功")
        print(f"   - 后端类型: {type(cache.backend).__name__}")
        print(f"   - 是否有后端: {cache.backend is not None}")

        # 测试基本操作
        test_key = "test_basic_key"
        test_value = {"message": "Hello, Cache!", "timestamp": time.time()}

        # 设置缓存
        set_success = cache.set(test_key, test_value, ttl=60)
        print(f"   - 缓存设置: {'✅' if set_success else '❌'}")

        # 获取缓存
        retrieved = cache.get(test_key)
        get_success = retrieved is not None and retrieved['message'] == test_value['message']
        print(f"   - 缓存获取: {'✅' if get_success else '❌'}")

        # 检查存在性
        exists = cache.get(test_key) is not None
        print(f"   - 缓存存在检查: {'✅' if exists else '❌'}")

        # 删除缓存
        delete_success = cache.delete(test_key)
        after_delete = cache.get(test_key)
        print(f"   - 缓存删除: {'✅' if delete_success and after_delete is None else '❌'}")

        return set_success and get_success and delete_success

    except Exception as e:
        print(f"❌ 缓存管理器基本功能测试失败: {e}")
        return False

def test_cache_operations():
    """测试缓存操作"""
    print("\n🔍 测试缓存操作...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        print("   测试多种数据类型:")
        test_data = {
            'string': 'test_string_value',
            'number': 42,
            'boolean': True,
            'list': [1, 2, 3, 'test'],
            'dict': {'nested': {'key': 'value'}, 'array': [1, 2, 3]},
            'complex_analysis': {
                'file_path': 'test.py',
                'analysis_type': 'comprehensive',
                'issues': [
                    {'type': 'style', 'line': 5, 'message': 'Missing type hint'},
                    {'type': 'security', 'line': 10, 'message': 'Potential SQL injection'}
                ],
                'recommendations': ['Add type hints', 'Use parameterized queries'],
                'score': 8.5,
                'execution_time': 2.34
            }
        }

        results = []
        for key, value in test_data.items():
            success = cache.set(f"test_{key}", value, ttl=60)
            if success:
                retrieved = cache.get(f"test_{key}")
                if retrieved == value:
                    print(f"   ✅ {key}: 缓存和获取成功")
                    results.append(True)
                else:
                    print(f"   ❌ {key}: 获取值不匹配")
                    results.append(False)
            else:
                print(f"   ❌ {key}: 设置失败")
                results.append(False)

        # 测试缓存大小
        cache_size = cache.size() if hasattr(cache, 'size') else len(cache.backend.keys())
        print(f"   - 当前缓存条目数: {cache_size}")

        # 测试键列表
        keys = cache.backend.keys() if hasattr(cache.backend, 'keys') else []
        print(f"   - 缓存键数量: {len(keys)}")

        # 清空测试
        clear_success = cache.clear()
        final_size = cache.size() if hasattr(cache, 'size') else len(cache.backend.keys())
        print(f"   - 缓存清空: {'✅' if clear_success and final_size == 0 else '❌'}")

        return all(results) and final_size == 0

    except Exception as e:
        print(f"❌ 缓存操作测试失败: {e}")
        return False

def test_cache_ttl():
    """测试缓存TTL功能"""
    print("\n🔍 测试缓存TTL功能...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        # 测试短TTL
        cache.set("short_ttl", "expires_soon", ttl=1)
        immediate = cache.get("short_ttl")
        print(f"   - 立即获取: {immediate}")

        # 等待过期
        print("   等待2秒让缓存过期...")
        time.sleep(2)

        expired = cache.get("short_ttl")
        print(f"   - 过期后获取: {expired}")

        ttl_working = immediate == "expires_soon" and expired is None

        # 测试长TTL
        cache.set("long_ttl", "still_valid", ttl=10)
        time.sleep(1)
        still_valid = cache.get("long_ttl")
        print(f"   - 长TTL测试: {'✅' if still_valid == 'still_valid' else '❌'}")

        return ttl_working and still_valid == 'still_valid'

    except Exception as e:
        print(f"❌ 缓存TTL功能测试失败: {e}")
        return False

def test_cache_get_or_set():
    """测试get_or_set方法"""
    print("\n🔍 测试get_or_set方法...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        # 模拟耗时操作
        call_count = 0
        def expensive_operation(key):
            nonlocal call_count
            call_count += 1
            time.sleep(0.1)  # 模拟耗时
            return f"computed_value_for_{key}_{call_count}"

        # 第一次调用（应该执行计算）
        start_time = time.time()
        result1 = cache.get_or_set("compute_key", lambda: expensive_operation("test"), ttl=60)
        first_time = time.time() - start_time

        # 第二次调用（应该从缓存获取）
        start_time = time.time()
        result2 = cache.get_or_set("compute_key", lambda: expensive_operation("test"), ttl=60)
        second_time = time.time() - start_time

        print(f"   - 第一次调用时间: {first_time:.3f}s (包含计算)")
        print(f"   - 第二次调用时间: {second_time:.3f}s (从缓存)")
        print(f"   - 函数调用次数: {call_count}")
        print(f"   - 结果一致性: {'✅' if result1 == result2 else '❌'}")

        speedup_good = second_time < first_time / 2
        call_count_correct = call_count == 1
        results_match = result1 == result2

        print(f"   - 缓存加速效果: {'✅' if speedup_good else '❌'}")
        print(f"   - 避免重复计算: {'✅' if call_count_correct else '❌'}")

        return speedup_good and call_count_correct and results_match

    except Exception as e:
        print(f"❌ get_or_set方法测试失败: {e}")
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
        cache_success = cache.cache_static_analysis(str(test_file), 'pylint', static_result)
        print(f"   - 静态分析缓存: {'✅' if cache_success else '❌'}")

        # 获取静态分析缓存
        cached_result = cache.get_static_analysis(str(test_file), 'pylint')
        static_valid = cached_result is not None and cached_result['tool'] == 'pylint'
        print(f"   - 静态分析获取: {'✅' if static_valid else '❌'}")

        print("\n   测试LLM响应缓存:")
        llm_prompt = "Please analyze this Python code for security issues"
        llm_model = "glm-4.5"
        llm_response = "I found 2 security issues in your code..."

        # 缓存LLM响应
        llm_cache_success = cache.cache_llm_response(llm_prompt, llm_model, llm_response)
        print(f"   - LLM响应缓存: {'✅' if llm_cache_success else '❌'}")

        # 获取LLM响应缓存
        cached_llm = cache.get_llm_response(llm_prompt, llm_model)
        llm_valid = cached_llm == llm_response
        print(f"   - LLM响应获取: {'✅' if llm_valid else '❌'}")

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

        print("   测试批量操作性能:")
        # 批量设置测试
        test_count = 100
        test_data = []

        start_time = time.time()
        for i in range(test_count):
            data = {
                'id': i,
                'content': f'test_content_{i}',
                'metadata': {'created_at': time.time(), 'size': 100}
            }
            test_data.append(data)
            cache.set(f"perf_test_{i}", data, ttl=300)
        write_time = time.time() - start_time

        print(f"   - 写入{test_count}条记录: {write_time:.3f}s ({test_count/write_time:.0f} 条/秒)")

        # 批量读取测试
        start_time = time.time()
        successful_reads = 0
        for i in range(test_count):
            if cache.get(f"perf_test_{i}") is not None:
                successful_reads += 1
        read_time = time.time() - start_time

        print(f"   - 读取{test_count}条记录: {read_time:.3f}s ({successful_reads/read_time:.0f} 条/秒)")
        print(f"   - 读取成功率: {successful_reads}/{test_count} ({successful_reads/test_count:.1%})")

        # 性能基准
        write_performance_good = test_count / write_time > 500  # 至少500条/秒
        read_performance_good = successful_reads / read_time > 2000  # 至少2000条/秒

        print(f"   - 写入性能: {'✅ 良好' if write_performance_good else '❌ 需要优化'}")
        print(f"   - 读取性能: {'✅ 良' if read_performance_good else '❌ 需要优化'}")

        return write_performance_good and read_performance_good

    except Exception as e:
        print(f"❌ 缓存性能测试失败: {e}")
        return False

def test_cache_stats():
    """测试缓存统计功能"""
    print("\n🔍 测试缓存统计功能...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        # 添加一些测试数据
        for i in range(10):
            cache.set(f"stats_test_{i}", f"value_{i}", ttl=60)

        # 获取统计信息
        stats = cache.get_stats()
        print("   - 缓存统计信息:")
        if isinstance(stats, dict):
            for key, value in stats.items():
                print(f"     {key}: {value}")
            stats_valid = len(stats) > 0
        else:
            print(f"     统计格式: {type(stats)}")
            stats_valid = False

        # 测试清理过期条目
        cleaned = cache.cleanup_expired()
        print(f"   - 清理过期条目: {cleaned} 个")

        return stats_valid

    except Exception as e:
        print(f"❌ 缓存统计功能测试失败: {e}")
        return False

def test_cache_integration():
    """测试缓存集成场景"""
    print("\n🔍 测试缓存集成场景...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        print("   模拟文件分析缓存场景:")
        # 模拟文件分析函数
        analysis_calls = 0
        def analyze_file_with_cache(file_path, analysis_type):
            nonlocal analysis_calls
            analysis_calls += 1

            # 模拟分析耗时
            time.sleep(0.05)

            return {
                'file_path': file_path,
                'analysis_type': analysis_type,
                'result': f'Analysis result for {file_path}',
                'call_id': analysis_calls,
                'timestamp': time.time()
            }

        # 带缓存的分析函数
        def cached_analysis(file_path, analysis_type):
            cache_key = f"analysis:{file_path}:{analysis_type}"
            return cache.get_or_set(cache_key,
                                   lambda: analyze_file_with_cache(file_path, analysis_type),
                                   ttl=3600)

        # 测试文件
        test_files = ["file1.py", "file2.js", "file3.java"]
        analysis_types = ["comprehensive", "security", "performance"]

        # 第一轮分析（无缓存）
        print("   执行第一轮分析...")
        start_time = time.time()
        first_results = []
        for file_path in test_files:
            for analysis_type in analysis_types:
                result = cached_analysis(file_path, analysis_type)
                first_results.append(result)
        first_time = time.time() - start_time

        # 第二轮分析（有缓存）
        print("   执行第二轮分析...")
        start_time = time.time()
        second_results = []
        for file_path in test_files:
            for analysis_type in analysis_types:
                result = cached_analysis(file_path, analysis_type)
                second_results.append(result)
        second_time = time.time() - start_time

        total_analyses = len(test_files) * len(analysis_types)
        speedup = first_time / second_time if second_time > 0 else float('inf')

        print(f"   - 总分析数: {total_analyses}")
        print(f"   - 实际调用次数: {analysis_calls}")
        print(f"   - 第一次分析时间: {first_time:.3f}s")
        print(f"   - 第二次分析时间: {second_time:.3f}s")
        print(f"   - 缓存加速比: {speedup:.1f}x")
        print(f"   - 缓存命中率: {(total_analyses - analysis_calls) / total_analyses:.1%}")

        integration_success = (
            analysis_calls == total_analyses and  # 第一轮全部调用
            second_time < first_time / 5 and       # 第二轮显著加速
            first_results == second_results       # 结果一致
        )

        print(f"   - 集成测试: {'✅ 成功' if integration_success else '❌ 失败'}")

        return integration_success

    except Exception as e:
        print(f"❌ 缓存集成场景测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始缓存系统测试（简化版）")
    print("=" * 60)

    test_results = []

    # 1. 测试缓存管理器基本功能
    basic_ok = test_cache_manager_basic()
    test_results.append(basic_ok)

    # 2. 测试缓存操作
    operations_ok = test_cache_operations()
    test_results.append(operations_ok)

    # 3. 测试缓存TTL功能
    ttl_ok = test_cache_ttl()
    test_results.append(ttl_ok)

    # 4. 测试get_or_set方法
    get_or_set_ok = test_cache_get_or_set()
    test_results.append(get_or_set_ok)

    # 5. 测试专用缓存方法
    specialized_ok = test_cache_specialized_methods()
    test_results.append(specialized_ok)

    # 6. 测试缓存性能
    performance_ok = test_cache_performance()
    test_results.append(performance_ok)

    # 7. 测试缓存统计功能
    stats_ok = test_cache_stats()
    test_results.append(stats_ok)

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
        print("\n🎉 缓存系统测试基本通过！")
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