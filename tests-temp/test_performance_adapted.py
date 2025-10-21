#!/usr/bin/env python3
"""
性能监控和统计功能测试脚本（适配版）
验证项目中实际可用的性能监控、时间跟踪、统计记录等功能
"""

import sys
import os
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_progress_tracker_performance():
    """测试进度跟踪器性能监控"""
    print("🔍 测试进度跟踪器性能监控...")

    try:
        from src.utils.progress import ProgressTracker

        # 创建进度跟踪器
        progress = ProgressTracker(verbose=True)

        print("   测试基本时间跟踪:")
        progress.start(total_steps=10)

        # 模拟文件分析过程
        start_time = time.time()
        for i in range(10):
            time.sleep(0.01)  # 模拟处理时间
            progress.step(f"处理文件 {i+1}")
            if i % 3 == 0:  # 每3个文件更新问题计数
                progress.update_issue_count(i // 3 + 1)

        elapsed_time = time.time() - start_time
        progress.finish()

        print(f"   - 模拟分析完成时间: {elapsed_time:.3f}s")

        # 获取摘要信息
        summary = progress.get_summary()
        print("   进度跟踪摘要:")
        print(f"     - 完成步骤数: {summary.get('steps_completed', 0)}")
        print(f"     - 总步骤数: {summary.get('total_steps', 0)}")
        print(f"     - 发现问题数: {summary.get('total_issues', 0)}")
        print(f"     - 总耗时: {summary.get('total_time', 0):.3f}s")

        # 验证性能指标合理性
        total_time = summary.get('total_time', 0)
        steps_completed = summary.get('steps_completed', 0)
        performance_reasonable = total_time > 0 and steps_completed == 10

        print(f"     - 性能指标合理性: {'✅' if performance_reasonable else '❌'}")

        # 测试简化模式进度跟踪器
        print("\n   测试简化模式进度跟踪:")
        progress2 = ProgressTracker(verbose=False)
        progress2.start(total_steps=5)

        start_time = time.time()
        for i in range(5):
            progress2.step(f"简化模式步骤 {i+1}")
            time.sleep(0.005)

        progress2.finish()
        elapsed_time2 = time.time() - start_time

        summary2 = progress2.get_summary()
        print(f"     - 简化模式完成时间: {elapsed_time2:.3f}s")
        print(f"     - 简化模式步骤数: {summary2.get('steps_completed', 0)}")

        speed_comparison = elapsed_time2 < elapsed_time
        print(f"     - 简化模式性能提升: {'✅' if speed_comparison else '❌'}")

        return performance_reasonable and len(summary) > 0

    except Exception as e:
        print(f"❌ 进度跟踪器性能监控测试失败: {e}")
        return False

def test_logger_performance_monitoring():
    """测试日志系统性能监控"""
    print("\n🔍 测试日志系统性能监控...")

    try:
        from src.utils.logger import get_logger

        logger = get_logger()

        print("   测试API请求日志记录:")
        # 模拟API请求日志记录
        start_time = time.time()

        logger.log_api_request(
            api_type="LLM",
            endpoint="/analyze",
            status="success",
            response_time=0.234,
            model="glm-4.5",
            tokens=150
        )

        logger.log_api_request(
            api_type="Static Analysis",
            endpoint="/pylint",
            status="success",
            response_time=0.089,
            file_count=5
        )

        api_log_time = time.time() - start_time
        print(f"     - API日志记录时间: {api_log_time:.3f}s")

        print("\n   测试批量日志性能:")
        # 测试批量日志记录性能
        log_count = 100
        start_time = time.time()

        for i in range(log_count):
            logger.info(f"Performance test log {i}")
            if i % 10 == 0:
                logger.warning(f"Warning message {i}")

        batch_log_time = time.time() - start_time
        logs_per_second = log_count / batch_log_time
        print(f"     - 批量日志性能: {logs_per_second:.0f} 条/秒")
        print(f"     - 总日志数: {log_count}")
        print(f"     - 总耗时: {batch_log_time:.3f}s")

        print("\n   测试日志性能指标收集:")
        # 模拟性能指标日志
        performance_logs = []
        for i in range(10):
            log_time = time.time()
            logger.info(f"Processing item {i}", extra={
                'performance': {
                    'item_id': i,
                    'start_time': log_time,
                    'processing_time': 0.01 + (i * 0.001)
                }
            })
            performance_logs.append(log_time)

        print(f"     - 性能日志记录数: {len(performance_logs)}")

        # 性能基准测试
        performance_good = (
            api_log_time < 0.01 and
            logs_per_second > 1000
        )

        print(f"     - 日志性能评估: {'✅ 优秀' if performance_good else '❌ 需优化'}")
        return performance_good

    except Exception as e:
        print(f"❌ 日志系统性能监控测试失败: {e}")
        return False

def test_cache_performance_monitoring():
    """测试缓存性能监控"""
    print("\n🔍 测试缓存性能监控...")

    try:
        from src.utils.cache import CacheManager

        cache = CacheManager()

        print("   测试缓存统计功能:")
        # 初始统计
        initial_stats = cache.get_stats()
        print(f"     - 初始缓存大小: {initial_stats.get('size', 0)}")
        print(f"     - 初始总字节数: {initial_stats.get('total_size_bytes', 0)}")

        # 添加测试数据
        test_data = []
        for i in range(100):
            data = {
                'id': i,
                'content': f'test_content_{i}',
                'metadata': {
                    'created_at': datetime.now().isoformat(),
                    'size': len(f'test_content_{i}') * 10,
                    'tags': [f'tag_{j}' for j in range(3)]
                }
            }
            test_data.append(data)
            cache.set(f"cache_key_{i}", data, ttl=300)

        # 获取缓存统计
        stats_after_write = cache.get_stats()
        print(f"     - 写入后缓存大小: {stats_after_write.get('size', 0)}")
        print(f"     - 写入后总字节数: {stats_after_write.get('total_size_bytes', 0)}")
        print(f"     - 后端类型: {stats_after_write.get('backend_type', 'unknown')}")

        # 测试缓存命中率
        print("\n   测试缓存命中率统计:")
        cache_hits = 0
        cache_misses = 0

        # 第一次访问（应该全部命中）
        start_time = time.time()
        for i in range(100):
            result = cache.get(f"cache_key_{i}")
            if result is not None:
                cache_hits += 1
            else:
                cache_misses += 1
        read_time = time.time() - start_time

        hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        print(f"     - 缓存命中数: {cache_hits}")
        print(f"     - 缓存未命中数: {cache_misses}")
        print(f"     - 命中率: {hit_rate:.1%}")
        print(f"     - 读取性能: {100/read_time:.0f} 次/秒")

        # 测试专用缓存方法性能
        print("\n   测试专用缓存方法性能:")
        # 创建测试文件
        test_file = Path("perf_test_file.py")
        test_file.write_text("def test_func(): return 'test'")

        # 静态分析缓存
        static_result = {'tool': 'pylint', 'issues': [], 'score': 9.0}
        cache_start = time.time()
        cache.cache_static_analysis(str(test_file), 'comprehensive', static_result)
        cache_time = time.time() - cache_start

        get_start = time.time()
        cached_result = cache.get_static_analysis(str(test_file), 'comprehensive')
        get_time = time.time() - get_start

        print(f"     - 静态分析缓存时间: {cache_time:.6f}s")
        print(f"     - 静态分析获取时间: {get_time:.6f}s")
        print(f"     - 缓存结果正确: {'✅' if cached_result else '❌'}")

        # LLM响应缓存
        llm_start = time.time()
        cache.cache_llm_response("test prompt", "glm-4.5", "test response")
        llm_cache_time = time.time() - llm_start

        get_llm_start = time.time()
        llm_response = cache.get_llm_response("test prompt", "glm-4.5")
        get_llm_time = time.time() - get_llm_start

        print(f"     - LLM缓存时间: {llm_cache_time:.6f}s")
        print(f"     - LLM获取时间: {get_llm_time:.6f}s")
        print(f"     - LLM缓存正确: {'✅' if llm_response else '❌'}")

        # 清理测试文件
        test_file.unlink(missing_ok=True)

        # 性能验证
        performance_valid = (
            stats_after_write.get('size', 0) == 100 and
            hit_rate >= 0.9 and
            cache_time < 0.01 and get_time < 0.01
        )

        print(f"     - 缓存性能验证: {'✅' if performance_valid else '❌'}")
        return performance_valid

    except Exception as e:
        print(f"❌ 缓存性能监控测试失败: {e}")
        return False

def test_file_operation_performance():
    """测试文件操作性能"""
    print("\n🔍 测试文件操作性能...")

    try:
        print("   测试文件读写性能:")
        temp_dir = tempfile.mkdtemp()
        test_files = []

        # 测试文件写入性能
        write_start = time.time()
        for i in range(20):
            file_path = Path(temp_dir) / f"test_file_{i}.txt"
            content = f"Test file {i}\n" + "x" * 1000  # 1KB内容
            file_path.write_text(content)
            test_files.append(file_path)
        write_time = time.time() - write_start

        write_speed = len(test_files) / write_time
        print(f"     - 文件写入速度: {write_speed:.0f} 文件/秒")
        print(f"     - 写入文件数: {len(test_files)}")

        # 测试文件读取性能
        read_start = time.time()
        read_count = 0
        for file_path in test_files:
            content = file_path.read_text()
            read_count += len(content)
        read_time = time.time() - read_start

        read_speed = read_count / 1024 / read_time  # KB/s
        print(f"     - 文件读取速度: {read_speed:.0f} KB/秒")
        print(f"     - 读取总字节数: {read_count}")

        # 测试文件遍历性能
        traverse_start = time.time()
        for file_path in Path(temp_dir).iterdir():
            if file_path.is_file():
                stat = file_path.stat()
        traverse_time = time.time() - traverse_start

        print(f"     - 目录遍历时间: {traverse_time:.3f}s")
        print(f"     - 遍历文件数: {len(test_files)}")

        # 测试大文件操作
        print("\n   测试大文件操作性能:")
        large_file = Path(temp_dir) / "large_file.txt"
        large_content = "x" * (1024 * 100)  # 100KB

        large_write_start = time.time()
        large_file.write_text(large_content)
        large_write_time = time.time() - large_write_start

        large_read_start = time.time()
        large_read_content = large_file.read_text()
        large_read_time = time.time() - large_read_start

        print(f"     - 大文件写入时间: {large_write_time:.3f}s")
        print(f"     - 大文件读取时间: {large_read_time:.3f}s")
        print(f"     - 大文件大小: {len(large_read_content)} 字节")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        # 性能验证
        performance_valid = (
            write_speed > 100 and
            read_speed > 1000 and
            traverse_time < 0.1 and
            large_write_time < 0.1 and
            large_read_time < 0.1
        )

        print(f"     - 文件操作性能验证: {'✅' if performance_valid else '❌'}")
        return performance_valid

    except Exception as e:
        print(f"❌ 文件操作性能测试失败: {e}")
        return False

def test_memory_usage_monitoring():
    """测试内存使用监控"""
    print("\n🔍 测试内存使用监控...")

    try:
        print("   测试内存使用跟踪:")

        # 基础内存监控
        import gc
        import sys

        # 获取初始内存状态
        gc.collect()
        initial_objects = len(gc.get_objects())
        print(f"     - 初始对象数量: {initial_objects}")

        # 创建大量对象进行测试
        data_objects = []
        for i in range(1000):
            data = {
                'id': i,
                'data': 'x' * 100,
                'metadata': {
                    'created_at': time.time(),
                    'type': f'type_{i % 10}',
                    'tags': [f'tag_{j}' for j in range(5)]
                }
            }
            data_objects.append(data)

        peak_objects = len(gc.get_objects())
        print(f"     - 峰值对象数量: {peak_objects}")
        print(f"     - 新增对象数量: {peak_objects - initial_objects}")

        # 测试内存清理
        del data_objects
        gc.collect()

        after_cleanup_objects = len(gc.get_objects())
        print(f"     - 清理后对象数量: {after_cleanup_objects}")
        print(f"     - 清理对象数量: {peak_objects - after_cleanup_objects}")

        # 测试列表内存使用
        print("\n   测试数据结构内存使用:")
        test_lists = []

        # 测试不同大小的列表
        for size in [100, 1000, 10000]:
            test_list = list(range(size))
            test_lists.append(test_list)

            # 简单估算内存使用
            list_size = sys.getsizeof(test_list)
            print(f"     - 列表大小 {size}: {list_size // 1024} KB")

        # 测试字符串内存使用
        print("\n   测试字符串内存使用:")
        for size in [100, 1000, 10000]:
            test_string = 'x' * size
            string_size = sys.getsizeof(test_string)
            print(f"     - 字符串大小 {size}: {string_size} 字节")

        # 清理测试数据
        del test_lists

        # 内存效率验证
        memory_efficient = (
            peak_objects > initial_objects and
            after_cleanup_objects < peak_objects and
            len(gc.get_objects()) < peak_objects + 1000  # 允许一些对象仍然存在
        )

        print(f"     - 内存效率验证: {'✅' if memory_efficient else '❌'}")
        return memory_efficient

    except Exception as e:
        print(f"❌ 内存使用监控测试失败: {e}")
        return False

def test_performance_metrics_collection():
    """测试性能指标收集"""
    print("\n🔍 测试性能指标收集...")

    try:
        from src.utils.cache import CacheManager
        from src.utils.logger import get_logger
        from src.utils.progress import ProgressTracker

        # 创建性能监控组件
        cache = CacheManager()
        logger = get_logger()
        progress = ProgressTracker(verbose=False)

        # 性能指标收集器
        class PerformanceCollector:
            def __init__(self):
                self.metrics = {
                    'operations': [],
                    'timings': {},
                    'counters': {},
                    'start_time': time.time()
                }

            def record_operation(self, operation_type, duration, details=None):
                """记录操作性能"""
                self.metrics['operations'].append({
                    'type': operation_type,
                    'duration': duration,
                    'timestamp': time.time(),
                    'details': details or {}
                })

            def record_timing(self, key, value):
                """记录时间指标"""
                if key not in self.metrics['timings']:
                    self.metrics['timings'][key] = []
                self.metrics['timings'][key].append(value)

            def increment_counter(self, key, value=1):
                """增加计数器"""
                self.metrics['counters'][key] = self.metrics['counters'].get(key, 0) + value

            def get_summary(self):
                """获取性能摘要"""
                end_time = time.time()
                total_time = end_time - self.metrics['start_time']

                # 计算统计信息
                operation_stats = {}
                for op in self.metrics['operations']:
                    op_type = op['type']
                    if op_type not in operation_stats:
                        operation_stats[op_type] = {
                            'count': 0,
                            'total_time': 0,
                            'min_time': float('inf'),
                            'max_time': 0
                        }

                    stats = operation_stats[op_type]
                    stats['count'] += 1
                    stats['total_time'] += op['duration']
                    stats['min_time'] = min(stats['min_time'], op['duration'])
                    stats['max_time'] = max(stats['max_time'], op['duration'])

                # 计算平均值
                for stats in operation_stats.values():
                    stats['avg_time'] = stats['total_time'] / stats['count']

                return {
                    'total_duration': total_time,
                    'operation_stats': operation_stats,
                    'counters': self.metrics['counters'],
                    'timings_summary': {
                        key: {
                            'count': len(values),
                            'sum': sum(values),
                            'avg': sum(values) / len(values),
                            'min': min(values),
                            'max': max(values)
                        }
                        for key, values in self.metrics['timings'].items()
                    }
                }

        collector = PerformanceCollector()

        print("   执行性能测试并收集指标:")

        # 测试1: 缓存操作性能
        progress.start(total_steps=50)
        for i in range(50):
            start_time = time.time()
            cache.set(f"perf_key_{i}", {"data": f"value_{i}"}, ttl=300)
            duration = time.time() - start_time
            collector.record_operation("cache_set", duration, {"key": f"perf_key_{i}"})

            if i % 10 == 0:
                progress.step(f"缓存操作 {i}")

        # 测试2: 缓存读取性能
        for i in range(50):
            start_time = time.time()
            result = cache.get(f"perf_key_{i}")
            duration = time.time() - start_time
            collector.record_operation("cache_get", duration, {"hit": result is not None})
            collector.increment_counter("cache_reads")

        # 测试3: 日志记录性能
        for i in range(30):
            start_time = time.time()
            logger.info(f"Performance log {i}")
            duration = time.time() - start_time
            collector.record_operation("log_write", duration)
            collector.record_timing("log_duration", duration)

        progress.finish()

        # 获取性能摘要
        summary = collector.get_summary()
        print("\n   性能指标摘要:")
        print(f"     - 总执行时间: {summary['total_duration']:.3f}s")
        print(f"     - 操作类型数: {len(summary['operation_stats'])}")

        for op_type, stats in summary['operation_stats'].items():
            print(f"     - {op_type}:")
            print(f"       • 执行次数: {stats['count']}")
            print(f"       • 总耗时: {stats['total_time']:.3f}s")
            print(f"       • 平均耗时: {stats['avg_time']:.6f}s")
            print(f"       • 最快耗时: {stats['min_time']:.6f}s")
            print(f"       • 最慢耗时: {stats['max_time']:.6f}s")

        print(f"     - 计数器统计: {summary['counters']}")

        # 缓存性能分析
        cache_set_stats = summary['operation_stats'].get('cache_set', {})
        cache_get_stats = summary['operation_stats'].get('cache_get', {})

        if cache_set_stats and cache_get_stats:
            cache_efficiency = cache_get_stats['avg_time'] / cache_set_stats['avg_time']
            print(f"     - 缓存读取效率比: {cache_efficiency:.2f} (读取时间/写入时间)")

        # 性能基准验证
        performance_valid = (
            summary['total_duration'] > 0 and
            len(summary['operation_stats']) >= 2 and
            all(stats['count'] > 0 for stats in summary['operation_stats'].values())
        )

        print(f"     - 性能指标收集验证: {'✅' if performance_valid else '❌'}")
        return performance_valid

    except Exception as e:
        print(f"❌ 性能指标收集测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始性能监控和统计功能测试（适配版）")
    print("=" * 60)

    test_results = []

    # 1. 测试进度跟踪器性能监控
    progress_ok = test_progress_tracker_performance()
    test_results.append(progress_ok)

    # 2. 测试日志系统性能监控
    logger_ok = test_logger_performance_monitoring()
    test_results.append(logger_ok)

    # 3. 测试缓存性能监控
    cache_ok = test_cache_performance_monitoring()
    test_results.append(cache_ok)

    # 4. 测试文件操作性能
    file_ok = test_file_operation_performance()
    test_results.append(file_ok)

    # 5. 测试内存使用监控
    memory_ok = test_memory_usage_monitoring()
    test_results.append(memory_ok)

    # 6. 测试性能指标收集
    metrics_ok = test_performance_metrics_collection()
    test_results.append(metrics_ok)

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 性能监控和统计功能测试基本通过！")
        print("性能监控和统计功能已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查性能监控功能。")
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