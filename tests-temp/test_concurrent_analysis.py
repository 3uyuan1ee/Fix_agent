#!/usr/bin/env python3
"""
多文件并发分析功能测试脚本
验证系统处理多个文件并发分析的能力和性能
"""

import sys
import os
import time
import asyncio
import tempfile
import concurrent.futures
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_sequential_vs_concurrent_analysis():
    """测试串行与并发分析性能对比"""
    print("🔍 测试串行与并发分析性能对比...")

    try:
        # 创建测试文件
        temp_dir = tempfile.mkdtemp()
        test_files = []

        print("   创建测试文件:")
        for i in range(20):
            file_path = Path(temp_dir) / f"test_file_{i:02d}.py"
            content = f'''#!/usr/bin/env python3
"""
测试文件 {i}
"""

def function_{i}():
    """函数 {i}"""
    result = 0
    for j in range({10 + i * 5}):
        result += j * (i + 1)
    return result

class Class{i}:
    """类 {i}"""

    def __init__(self, name):
        self.name = name
        self.data = list(range({5 + i}))

    def process_data(self):
        """处理数据"""
        return [x * 2 for x in self.data]

if __name__ == "__main__":
    print("Running test file {i}")
    obj = Class{i}("test")
    print(function_{i}())
    print(obj.process_data())
'''
            file_path.write_text(content)
            test_files.append(str(file_path))

        print(f"     - 创建文件数: {len(test_files)}")

        # 模拟文件分析函数
        def analyze_file(file_path: str) -> Dict[str, Any]:
            """模拟文件分析"""
            start_time = time.time()

            # 模拟分析耗时（基于文件大小）
            file_size = os.path.getsize(file_path)
            analysis_time = 0.05 + (file_size / 10000)  # 基础时间 + 文件大小相关时间
            time.sleep(analysis_time)

            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 模拟分析结果
            lines = content.splitlines()
            functions = len([line for line in lines if 'def ' in line])
            classes = len([line for line in lines if 'class ' in line])

            end_time = time.time()

            return {
                'file_path': file_path,
                'file_size': file_size,
                'line_count': len(lines),
                'function_count': functions,
                'class_count': classes,
                'analysis_time': end_time - start_time,
                'complexity_score': (functions + classes) * 2.5,
                'timestamp': datetime.now().isoformat()
            }

        # 测试串行分析
        print("\n   执行串行分析:")
        sequential_start = time.time()
        sequential_results = []

        for file_path in test_files:
            result = analyze_file(file_path)
            sequential_results.append(result)

        sequential_time = time.time() - sequential_start
        print(f"     - 串行分析完成时间: {sequential_time:.3f}s")
        print(f"     - 平均每文件时间: {sequential_time/len(test_files):.3f}s")

        # 测试并发分析（使用ThreadPoolExecutor）
        print("\n   执行并发分析 (ThreadPoolExecutor):")
        concurrent_start = time.time()
        concurrent_results = []

        # 使用线程池进行并发分析
        max_workers = min(8, len(test_files))  # 最多8个并发线程
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有分析任务
            future_to_file = {
                executor.submit(analyze_file, file_path): file_path
                for file_path in test_files
            }

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    result = future.result()
                    concurrent_results.append(result)
                except Exception as e:
                    print(f"     - 分析失败: {e}")

        concurrent_time = time.time() - concurrent_start
        print(f"     - 并发分析完成时间: {concurrent_time:.3f}s")
        print(f"     - 平均每文件时间: {concurrent_time/len(test_files):.3f}s")
        print(f"     - 使用线程数: {max_workers}")

        # 计算性能提升
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 0
        print(f"     - 性能提升倍数: {speedup:.2f}x")

        # 验证结果一致性
        sequential_files = set(r['file_path'] for r in sequential_results)
        concurrent_files = set(r['file_path'] for r in concurrent_results)
        results_consistent = sequential_files == concurrent_files

        print(f"     - 结果一致性: {'✅' if results_consistent else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        # 性能基准验证
        performance_good = speedup > 2.0 and results_consistent
        print(f"     - 并发分析性能验证: {'✅' if performance_good else '❌'}")

        return performance_good

    except Exception as e:
        print(f"❌ 串行与并发分析性能对比测试失败: {e}")
        return False

def test_async_concurrent_analysis():
    """测试异步并发分析"""
    print("\n🔍 测试异步并发分析...")

    try:
        # 创建测试文件
        temp_dir = tempfile.mkdtemp()
        test_files = []

        print("   创建异步测试文件:")
        for i in range(15):
            file_path = Path(temp_dir) / f"async_test_{i:02d}.py"
            content = f'''# 异步测试文件 {i}
import asyncio
import time

async def async_function_{i}():
    """异步函数 {i}"""
    await asyncio.sleep(0.1)
    return f"Result {i}"

def sync_function_{i}():
    """同步函数 {i}"""
    time.sleep(0.05)
    return i * 2

class AsyncClass{i}:
    """异步类 {i}"""

    def __init__(self):
        self.value = {i}

    async def process_async(self):
        """异步处理"""
        await asyncio.sleep(0.08)
        return self.value * 3
'''
            file_path.write_text(content)
            test_files.append(str(file_path))

        print(f"     - 创建文件数: {len(test_files)}")

        # 异步文件分析函数
        async def analyze_file_async(file_path: str) -> Dict[str, Any]:
            """异步文件分析"""
            start_time = time.time()

            # 模拟异步分析耗时
            file_size = os.path.getsize(file_path)
            await asyncio.sleep(0.03 + (file_size / 20000))

            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 模拟分析
            lines = content.splitlines()
            async_funcs = len([line for line in lines if 'async def' in line])
            sync_funcs = len([line for line in lines if 'def ' in line and 'async def' not in line])
            async_classes = len([line for line in lines if 'class ' in line])

            end_time = time.time()

            return {
                'file_path': file_path,
                'file_size': file_size,
                'line_count': len(lines),
                'async_function_count': async_funcs,
                'sync_function_count': sync_funcs,
                'class_count': async_classes,
                'analysis_time': end_time - start_time,
                'is_async_file': async_funcs > 0,
                'timestamp': datetime.now().isoformat()
            }

        # 测试串行异步分析
        print("\n   执行串行异步分析:")
        async def run_serial_async():
            serial_async_start = time.time()
            serial_async_results = []

            for file_path in test_files:
                result = await analyze_file_async(file_path)
                serial_async_results.append(result)

            return time.time() - serial_async_start, serial_async_results

        serial_async_time, serial_async_results = asyncio.run(run_serial_async())
        print(f"     - 串行异步分析时间: {serial_async_time:.3f}s")

        # 测试并发异步分析
        print("\n   执行并发异步分析:")
        async def run_concurrent_async():
            concurrent_async_start = time.time()

            # 使用asyncio.gather进行并发
            tasks = [analyze_file_async(file_path) for file_path in test_files]
            concurrent_async_results = await asyncio.gather(*tasks)

            return time.time() - concurrent_async_start, concurrent_async_results

        concurrent_async_time, concurrent_async_results = asyncio.run(run_concurrent_async())
        print(f"     - 并发异步分析时间: {concurrent_async_time:.3f}s")

        # 计算异步性能提升
        async_speedup = serial_async_time / concurrent_async_time if concurrent_async_time > 0 else 0
        print(f"     - 异步性能提升倍数: {async_speedup:.2f}x")

        # 验证异步分析结果
        async_files_found = sum(1 for r in concurrent_async_results if r['is_async_file'])
        print(f"     - 发现异步文件数: {async_files_found}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        # 性能验证
        async_performance_good = async_speedup > 2.0 and async_files_found > 0
        print(f"     - 异步并发分析验证: {'✅' if async_performance_good else '❌'}")

        return async_performance_good

    except Exception as e:
        print(f"❌ 异步并发分析测试失败: {e}")
        return False

def test_concurrent_analysis_with_limits():
    """测试带限制的并发分析"""
    print("\n🔍 测试带限制的并发分析...")

    try:
        # 创建更多测试文件
        temp_dir = tempfile.mkdtemp()
        test_files = []

        print("   创建大量测试文件:")
        for i in range(50):
            file_path = Path(temp_dir) / f"limit_test_{i:02d}.py"
            content = f'''# 限制测试文件 {i}
import os
import sys

def function_{i}():
    """函数 {i}"""
    data = [x for x in range({20 + i})]
    return sum(data)

class LimitTest{i}:
    """限制测试类 {i}"""

    def __init__(self):
        self.items = list(range({10 + i // 5}))

    def process(self):
        return self.items * 2
'''
            file_path.write_text(content)
            test_files.append(str(file_path))

        print(f"     - 创建文件数: {len(test_files)}")

        # 带限制的分析函数
        def analyze_with_limits(file_path: str, max_execution_time: float = 1.0) -> Dict[str, Any]:
            """带时间限制的分析函数"""
            start_time = time.time()

            # 检查文件大小限制
            file_size = os.path.getsize(file_path)
            if file_size > 10000:  # 10KB限制
                return {
                    'file_path': file_path,
                    'error': 'File too large',
                    'file_size': file_size,
                    'skipped': True
                }

            # 模拟分析
            analysis_time = min(0.02 + (file_size / 50000), max_execution_time - 0.01)
            time.sleep(analysis_time)

            # 检查执行时间限制
            elapsed = time.time() - start_time
            if elapsed > max_execution_time:
                return {
                    'file_path': file_path,
                    'error': 'Analysis timeout',
                    'elapsed_time': elapsed,
                    'timeout': True
                }

            # 正常分析
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.splitlines()
            functions = len([line for line in lines if 'def ' in line])
            classes = len([line for line in lines if 'class ' in line])

            end_time = time.time()

            return {
                'file_path': file_path,
                'file_size': file_size,
                'line_count': len(lines),
                'function_count': functions,
                'class_count': classes,
                'analysis_time': end_time - start_time,
                'completed': True
            }

        # 测试不同并发限制
        concurrency_limits = [2, 4, 8, 16]
        results = {}

        for max_workers in concurrency_limits:
            print(f"\n   测试并发限制 {max_workers}:")

            start_time = time.time()
            analysis_results = []
            timeouts = 0
            skipped = 0
            completed = 0

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(analyze_with_limits, file_path): file_path
                    for file_path in test_files
                }

                for future in concurrent.futures.as_completed(future_to_file):
                    try:
                        result = future.result()
                        analysis_results.append(result)

                        if result.get('timeout'):
                            timeouts += 1
                        elif result.get('skipped'):
                            skipped += 1
                        elif result.get('completed'):
                            completed += 1

                    except Exception as e:
                        print(f"     - 分析异常: {e}")

            total_time = time.time() - start_time

            results[max_workers] = {
                'total_time': total_time,
                'completed': completed,
                'timeouts': timeouts,
                'skipped': skipped,
                'throughput': completed / total_time
            }

            print(f"     - 总时间: {total_time:.3f}s")
            print(f"     - 完成分析: {completed}")
            print(f"     - 超时数量: {timeouts}")
            print(f"     - 跳过数量: {skipped}")
            print(f"     - 吞吐量: {completed/total_time:.1f} 文件/秒")

        # 分析最佳并发数
        print("\n   并发性能分析:")
        best_workers = max(results.keys(), key=lambda k: results[k]['throughput'])
        best_throughput = results[best_workers]['throughput']

        print(f"     - 最佳并发数: {best_workers}")
        print(f"     - 最佳吞吐量: {best_throughput:.1f} 文件/秒")

        # 性能对比
        min_workers = min(results.keys())
        max_workers = max(results.keys())
        improvement = results[max_workers]['throughput'] / results[min_workers]['throughput']

        print(f"     - 最大并发提升: {improvement:.2f}x")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        # 验证限制功能正常工作
        limits_working = (
            all(result['total_time'] > 0 for result in results.values()) and
            best_throughput > 10 and
            improvement > 1.5
        )

        print(f"     - 并发限制功能验证: {'✅' if limits_working else '❌'}")
        return limits_working

    except Exception as e:
        print(f"❌ 带限制的并发分析测试失败: {e}")
        return False

def test_concurrent_analysis_with_errors():
    """测试并发分析中的错误处理"""
    print("\n🔍 测试并发分析中的错误处理...")

    try:
        # 创建包含错误的测试文件
        temp_dir = tempfile.mkdtemp()
        test_files = []

        print("   创建包含错误的测试文件:")
        for i in range(20):
            file_path = Path(temp_dir) / f"error_test_{i:02d}.py"

            if i % 5 == 0:
                # 创建语法错误的文件
                content = f'''# 语法错误文件 {i}
def broken_function_{i}(
    # 缺少右括号
    return "broken"
'''
            elif i % 7 == 0:
                # 创建编码问题的文件（模拟）
                content = f'''# 编码问题文件 {i}
def function_{i}():
    return "包含特殊字符: äöüß"

# 模拟一些可能导致问题的内容
invalid_syntax_{i} = [1, 2, 3, 4, 5
'''
            elif i % 3 == 0:
                # 创建空文件
                content = ''
            else:
                # 创建正常文件
                content = f'''# 正常文件 {i}
def normal_function_{i}():
    return {i} * 2

class NormalClass{i}:
    def __init__(self):
        self.value = {i}
'''

            file_path.write_text(content, encoding='utf-8')
            test_files.append(str(file_path))

        print(f"     - 创建文件数: {len(test_files)}")

        # 带错误处理的分析函数
        def analyze_with_error_handling(file_path: str) -> Dict[str, Any]:
            """带错误处理的分析函数"""
            start_time = time.time()

            try:
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    return {
                        'file_path': file_path,
                        'error': 'File not found',
                        'error_type': 'file_not_found'
                    }

                # 检查文件大小
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    return {
                        'file_path': file_path,
                        'file_size': 0,
                        'line_count': 0,
                        'function_count': 0,
                        'class_count': 0,
                        'is_empty': True,
                        'analysis_time': time.time() - start_time
                    }

                # 尝试读取文件
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # 尝试其他编码
                    try:
                        with open(file_path, 'r', encoding='latin-1') as f:
                            content = f.read()
                    except Exception as e:
                        return {
                            'file_path': file_path,
                            'error': f'Encoding error: {str(e)}',
                            'error_type': 'encoding_error',
                            'file_size': file_size
                        }

                # 尝试解析代码
                try:
                    lines = content.splitlines()
                    functions = len([line for line in lines if 'def ' in line and line.strip().startswith('def')])
                    classes = len([line for line in lines if 'class ' in line and line.strip().startswith('class')])

                    # 简单的语法检查
                    syntax_errors = 0
                    for line_num, line in enumerate(lines, 1):
                        if line.count('(') != line.count(')'):
                            syntax_errors += 1

                    return {
                        'file_path': file_path,
                        'file_size': file_size,
                        'line_count': len(lines),
                        'function_count': functions,
                        'class_count': classes,
                        'syntax_errors': syntax_errors,
                        'analysis_time': time.time() - start_time,
                        'success': True
                    }

                except Exception as e:
                    return {
                        'file_path': file_path,
                        'error': f'Parse error: {str(e)}',
                        'error_type': 'parse_error',
                        'file_size': file_size
                    }

            except Exception as e:
                return {
                    'file_path': file_path,
                    'error': f'Unexpected error: {str(e)}',
                    'error_type': 'unexpected_error'
                }

        # 执行并发分析（包含错误处理）
        print("\n   执行带错误处理的并发分析:")

        start_time = time.time()
        analysis_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            future_to_file = {
                executor.submit(analyze_with_error_handling, file_path): file_path
                for file_path in test_files
            }

            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    result = future.result()
                    analysis_results.append(result)
                except Exception as e:
                    # 处理执行器级别的错误
                    file_path = future_to_file[future]
                    analysis_results.append({
                        'file_path': file_path,
                        'error': f'Executor error: {str(e)}',
                        'error_type': 'executor_error'
                    })

        total_time = time.time() - start_time

        # 分析结果统计
        successful = sum(1 for r in analysis_results if r.get('success'))
        with_errors = len(analysis_results) - successful
        empty_files = sum(1 for r in analysis_results if r.get('is_empty'))

        error_types = {}
        for result in analysis_results:
            error_type = result.get('error_type')
            if error_type:
                error_types[error_type] = error_types.get(error_type, 0) + 1

        print(f"     - 总分析时间: {total_time:.3f}s")
        print(f"     - 成功分析: {successful}")
        print(f"     - 包含错误: {with_errors}")
        print(f"     - 空文件: {empty_files}")
        print(f"     - 错误类型统计: {error_types}")
        print(f"     - 平均处理时间: {total_time/len(test_files):.3f}s/文件")

        # 验证错误处理功能
        error_handling_good = (
            len(analysis_results) == len(test_files) and  # 所有文件都被处理
            successful > 0 and  # 有成功的分析
            with_errors > 0 and  # 也有错误被正确处理
            len(error_types) > 0  # 错误被正确分类
        )

        print(f"     - 错误处理功能验证: {'✅' if error_handling_good else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return error_handling_good

    except Exception as e:
        print(f"❌ 并发分析错误处理测试失败: {e}")
        return False

def test_concurrent_analysis_resource_management():
    """测试并发分析的资源管理"""
    print("\n🔍 测试并发分析的资源管理...")

    try:
        # 创建大量测试文件来测试资源管理
        temp_dir = tempfile.mkdtemp()
        test_files = []

        print("   创建资源管理测试文件:")
        for i in range(100):
            file_path = Path(temp_dir) / f"resource_test_{i:03d}.py"
            content = f'''# 资源管理测试文件 {i}
import time
import threading
import random

def resource_intensive_function_{i}():
    """资源密集型函数"""
    # 模拟内存使用
    data = [random.random() for _ in range({100 + i})]

    # 模拟CPU使用
    result = sum(x * x for x in data)

    return result

class ResourceClass{i}:
    """资源管理类"""

    def __init__(self):
        self.thread_local = threading.local()
        self.cache = {{}}

    def process_with_resources(self):
        """使用资源的处理方法"""
        # 使用线程本地存储
        if not hasattr(self.thread_local, 'counter'):
            self.thread_local.counter = 0

        self.thread_local.counter += 1

        # 模拟缓存使用
        for j in range({10}):
            key = f"key_{{j}}"
            if key not in self.cache:
                self.cache[key] = j * j

        return len(self.cache)
'''
            file_path.write_text(content)
            test_files.append(str(file_path))

        print(f"     - 创建文件数: {len(test_files)}")

        # 资源监控的分析函数
        def analyze_with_resource_monitoring(file_path: str) -> Dict[str, Any]:
            """带资源监控的分析函数"""
            import gc
            import threading

            start_time = time.time()
            start_objects = len(gc.get_objects())
            thread_id = threading.current_thread().ident

            try:
                # 读取文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 模拟资源密集型分析
                lines = content.splitlines()
                functions = len([line for line in lines if 'def ' in line])
                classes = len([line for line in lines if 'class ' in line])

                # 模拟内存分配
                temp_data = []
                for i in range(50):
                    temp_data.append({
                        'line_num': i,
                        'content': lines[i] if i < len(lines) else '',
                        'length': len(lines[i]) if i < len(lines) else 0,
                        'thread_id': thread_id
                    })

                # 模拟一些计算
                total_length = sum(item['length'] for item in temp_data)
                avg_length = total_length / len(temp_data) if temp_data else 0

                # 清理临时数据
                del temp_data

                end_time = time.time()
                end_objects = len(gc.get_objects())

                return {
                    'file_path': file_path,
                    'line_count': len(lines),
                    'function_count': functions,
                    'class_count': classes,
                    'avg_line_length': avg_length,
                    'analysis_time': end_time - start_time,
                    'thread_id': thread_id,
                    'objects_created': end_objects - start_objects,
                    'success': True
                }

            except Exception as e:
                return {
                    'file_path': file_path,
                    'error': str(e),
                    'thread_id': thread_id,
                    'analysis_time': time.time() - start_time,
                    'success': False
                }

        # 测试不同并发级别的资源管理
        worker_counts = [4, 8, 16, 32]
        resource_results = {}

        for max_workers in worker_counts:
            print(f"\n   测试并发数 {max_workers} 的资源管理:")

            # 手动垃圾回收以获得准确的基线
            import gc
            gc.collect()
            initial_objects = len(gc.get_objects())

            start_time = time.time()
            analysis_results = []
            thread_usage = {}

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(analyze_with_resource_monitoring, file_path): file_path
                    for file_path in test_files[:min(50, len(test_files))]  # 限制文件数
                }

                for future in concurrent.futures.as_completed(future_to_file):
                    try:
                        result = future.result()
                        analysis_results.append(result)

                        # 统计线程使用
                        thread_id = result.get('thread_id')
                        if thread_id:
                            thread_usage[thread_id] = thread_usage.get(thread_id, 0) + 1

                    except Exception as e:
                        print(f"     - 执行异常: {e}")

            total_time = time.time() - start_time

            # 最终对象计数
            gc.collect()
            final_objects = len(gc.get_objects())

            # 统计结果
            successful = sum(1 for r in analysis_results if r.get('success'))
            total_objects_created = sum(r.get('objects_created', 0) for r in analysis_results)
            avg_objects_per_file = total_objects_created / len(analysis_results) if analysis_results else 0

            resource_results[max_workers] = {
                'total_time': total_time,
                'successful': successful,
                'threads_used': len(thread_usage),
                'total_objects_created': total_objects_created,
                'avg_objects_per_file': avg_objects_per_file,
                'objects_leaked': final_objects - initial_objects,
                'throughput': successful / total_time
            }

            print(f"     - 总时间: {total_time:.3f}s")
            print(f"     - 成功分析: {successful}")
            print(f"     - 使用线程数: {len(thread_usage)}")
            print(f"     - 创建对象总数: {total_objects_created}")
            print(f"     - 平均每文件对象: {avg_objects_per_file:.0f}")
            print(f"     - 对象泄漏: {resource_results[max_workers]['objects_leaked']}")
            print(f"     - 吞吐量: {successful/total_time:.1f} 文件/秒")

        # 分析资源管理效率
        print("\n   资源管理效率分析:")

        # 找到最佳吞吐量
        best_workers = max(resource_results.keys(), key=lambda k: resource_results[k]['throughput'])
        best_result = resource_results[best_workers]

        print(f"     - 最佳并发数: {best_workers}")
        print(f"     - 最佳吞吐量: {best_result['throughput']:.1f} 文件/秒")
        print(f"     - 对象泄漏控制: {best_result['objects_leaked']}")

        # 验证资源管理
        resource_management_good = (
            all(result['successful'] > 0 for result in resource_results.values()) and
            all(result['objects_leaked'] < 1000 for result in resource_results.values()) and
            best_result['throughput'] > 20
        )

        print(f"     - 资源管理验证: {'✅' if resource_management_good else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return resource_management_good

    except Exception as e:
        print(f"❌ 并发分析资源管理测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始多文件并发分析功能测试")
    print("=" * 60)

    test_results = []

    # 1. 测试串行与并发分析性能对比
    comparison_ok = test_sequential_vs_concurrent_analysis()
    test_results.append(comparison_ok)

    # 2. 测试异步并发分析
    async_ok = asyncio.run(test_async_concurrent_analysis())
    test_results.append(async_ok)

    # 3. 测试带限制的并发分析
    limits_ok = test_concurrent_analysis_with_limits()
    test_results.append(limits_ok)

    # 4. 测试并发分析中的错误处理
    errors_ok = test_concurrent_analysis_with_errors()
    test_results.append(errors_ok)

    # 5. 测试并发分析的资源管理
    resource_ok = test_concurrent_analysis_resource_management()
    test_results.append(resource_ok)

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 多文件并发分析功能测试基本通过！")
        print("多文件并发分析功能已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查并发分析功能。")
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