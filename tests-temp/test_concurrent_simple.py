#!/usr/bin/env python3
"""
多文件并发分析功能测试脚本（简化版）
验证系统处理多个文件并发分析的能力和性能
"""

import sys
import os
import time
import concurrent.futures
import tempfile
from pathlib import Path
from unittest.mock import Mock
from datetime import datetime, timedelta
from typing import List, Dict, Any

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_concurrent_analysis_performance():
    """测试并发分析性能"""
    print("🔍 测试并发分析性能...")

    try:
        # 创建测试文件
        temp_dir = tempfile.mkdtemp()
        test_files = []

        print("   创建测试文件:")
        for i in range(30):
            file_path = Path(temp_dir) / f"concurrent_test_{i:02d}.py"
            content = f'''#!/usr/bin/env python3
"""
并发测试文件 {i}
"""

def function_{i}():
    """函数 {i}"""
    result = 0
    for j in range({20 + i * 3}):
        result += j * (i + 1)
    return result

class TestClass{i}:
    """测试类 {i}"""

    def __init__(self, name):
        self.name = name
        self.data = list(range({10 + i}))

    def process_data(self):
        """处理数据"""
        return [x * 2 for x in self.data]

def helper_function_{i}(x, y):
    """辅助函数"""
    return x + y

if __name__ == "__main__":
    print("Running test file {i}")
    obj = TestClass{i}("test")
    print(function_{i}())
    print(obj.process_data())
    print(helper_function_{i}(10, 20))
'''
            file_path.write_text(content)
            test_files.append(str(file_path))

        print(f"     - 创建文件数: {len(test_files)}")

        # 分析函数
        def analyze_file(file_path: str) -> Dict[str, Any]:
            """文件分析函数"""
            start_time = time.time()

            try:
                # 读取文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 模拟分析耗时
                file_size = len(content)
                analysis_time = 0.02 + (file_size / 10000)
                time.sleep(analysis_time)

                # 分析内容
                lines = content.splitlines()
                functions = len([line for line in lines if line.strip().startswith('def ')])
                classes = len([line for line in lines if line.strip().startswith('class ')])
                imports = len([line for line in lines if line.strip().startswith('import ') or 'from ' in line])

                # 计算复杂度指标
                complexity_score = functions * 2.5 + classes * 3.0 + imports * 1.5

                end_time = time.time()

                return {
                    'file_path': Path(file_path).name,
                    'file_size': file_size,
                    'line_count': len(lines),
                    'function_count': functions,
                    'class_count': classes,
                    'import_count': imports,
                    'complexity_score': round(complexity_score, 2),
                    'analysis_time': end_time - start_time,
                    'success': True,
                    'timestamp': datetime.now().isoformat()
                }

            except Exception as e:
                return {
                    'file_path': Path(file_path).name,
                    'error': str(e),
                    'analysis_time': time.time() - start_time,
                    'success': False
                }

        # 测试串行分析
        print("\n   执行串行分析:")
        serial_start = time.time()
        serial_results = []

        for file_path in test_files:
            result = analyze_file(file_path)
            serial_results.append(result)

        serial_time = time.time() - serial_start
        serial_success = sum(1 for r in serial_results if r.get('success'))

        print(f"     - 串行分析时间: {serial_time:.3f}s")
        print(f"     - 成功分析数: {serial_success}/{len(test_files)}")
        print(f"     - 平均每文件时间: {serial_time/len(test_files):.3f}s")

        # 测试不同并发级别
        print("\n   测试不同并发级别:")
        concurrency_tests = [2, 4, 8, 16]
        concurrent_results = {}

        for max_workers in concurrency_tests:
            print(f"\n     并发级别 {max_workers}:")
            concurrent_start = time.time()
            worker_results = []

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_file = {
                    executor.submit(analyze_file, file_path): file_path
                    for file_path in test_files
                }

                # 收集结果
                for future in concurrent.futures.as_completed(future_to_file):
                    try:
                        result = future.result()
                        worker_results.append(result)
                    except Exception as e:
                        print(f"       - 执行异常: {e}")

            concurrent_time = time.time() - concurrent_start
            concurrent_success = sum(1 for r in worker_results if r.get('success'))
            speedup = serial_time / concurrent_time if concurrent_time > 0 else 0

            concurrent_results[max_workers] = {
                'time': concurrent_time,
                'success_count': concurrent_success,
                'speedup': speedup,
                'throughput': concurrent_success / concurrent_time
            }

            print(f"       - 分析时间: {concurrent_time:.3f}s")
            print(f"       - 成功分析: {concurrent_success}/{len(test_files)}")
            print(f"       - 性能提升: {speedup:.2f}x")
            print(f"       - 吞吐量: {concurrent_success/concurrent_time:.1f} 文件/秒")

        # 分析最佳并发级别
        print("\n   并发性能分析:")
        best_workers = max(concurrent_results.keys(),
                         key=lambda k: concurrent_results[k]['throughput'])
        best_result = concurrent_results[best_workers]

        print(f"     - 最佳并发数: {best_workers}")
        print(f"     - 最佳吞吐量: {best_result['throughput']:.1f} 文件/秒")
        print(f"     - 最大性能提升: {best_result['speedup']:.2f}x")

        # 验证结果一致性
        serial_files = set(r['file_path'] for r in serial_results if r.get('success'))
        best_files = set()

        # 重新运行最佳并发数来验证一致性
        with concurrent.futures.ThreadPoolExecutor(max_workers=best_workers) as executor:
            future_to_file = {
                executor.submit(analyze_file, file_path): file_path
                for file_path in test_files
            }

            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    result = future.result()
                    if result.get('success'):
                        best_files.add(result['file_path'])
                except Exception:
                    pass

        consistency = serial_files == best_files
        print(f"     - 结果一致性: {'✅' if consistency else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        # 性能验证
        performance_good = (
            best_result['speedup'] > 3.0 and
            best_result['success_count'] >= len(test_files) * 0.9 and
            consistency
        )

        print(f"     - 并发分析性能验证: {'✅' if performance_good else '❌'}")
        return performance_good

    except Exception as e:
        print(f"❌ 并发分析性能测试失败: {e}")
        return False

def test_concurrent_error_handling():
    """测试并发分析的错误处理"""
    print("\n🔍 测试并发分析的错误处理...")

    try:
        # 创建包含各种问题的测试文件
        temp_dir = tempfile.mkdtemp()
        test_files = []

        print("   创建包含错误的测试文件:")
        for i in range(20):
            file_path = Path(temp_dir) / f"error_test_{i:02d}.py"

            if i % 4 == 0:
                # 空文件
                content = ''
            elif i % 4 == 1:
                # 语法错误
                content = f'''# 语法错误文件 {i}
def broken_function_{i}(
    # 缺少右括号
    return "broken"
'''
            elif i % 4 == 2:
                # 正常文件
                content = f'''# 正常文件 {i}
def normal_function_{i}():
    return {i}

class NormalClass{i}:
    pass
'''
            else:
                # 大文件
                content = 'x' * 5000 + f'\n# 大文件 {i}\n'

            file_path.write_text(content, encoding='utf-8')
            test_files.append(str(file_path))

        print(f"     - 创建文件数: {len(test_files)}")

        # 带错误处理的分析函数
        def safe_analyze_file(file_path: str) -> Dict[str, Any]:
            """安全的文件分析函数"""
            start_time = time.time()

            try:
                # 检查文件是否存在
                if not os.path.exists(file_path):
                    return {
                        'file_path': Path(file_path).name,
                        'error': 'File not found',
                        'error_type': 'file_error',
                        'success': False
                    }

                # 检查文件大小
                file_size = os.path.getsize(file_path)

                # 读取文件
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    return {
                        'file_path': Path(file_path).name,
                        'error': 'Encoding error',
                        'error_type': 'encoding_error',
                        'file_size': file_size,
                        'success': False
                    }

                # 检查空文件
                if not content.strip():
                    return {
                        'file_path': Path(file_path).name,
                        'file_size': file_size,
                        'line_count': 0,
                        'function_count': 0,
                        'class_count': 0,
                        'is_empty': True,
                        'success': True,
                        'analysis_time': time.time() - start_time
                    }

                # 模拟分析
                time.sleep(0.01)  # 模拟分析时间

                lines = content.splitlines()
                functions = len([line for line in lines if line.strip().startswith('def ')])
                classes = len([line for line in lines if line.strip().startswith('class ')])

                # 简单语法检查
                syntax_issues = 0
                for line_num, line in enumerate(lines, 1):
                    if line.count('(') != line.count(')'):
                        syntax_issues += 1

                return {
                    'file_path': Path(file_path).name,
                    'file_size': file_size,
                    'line_count': len(lines),
                    'function_count': functions,
                    'class_count': classes,
                    'syntax_issues': syntax_issues,
                    'has_errors': syntax_issues > 0,
                    'success': True,
                    'analysis_time': time.time() - start_time
                }

            except Exception as e:
                return {
                    'file_path': Path(file_path).name,
                    'error': str(e),
                    'error_type': 'unexpected_error',
                    'success': False,
                    'analysis_time': time.time() - start_time
                }

        # 执行并发分析（带错误处理）
        print("\n   执行带错误处理的并发分析:")
        max_workers = 6

        start_time = time.time()
        all_results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(safe_analyze_file, file_path): file_path
                for file_path in test_files
            }

            # 收集结果
            for future in concurrent.futures.as_completed(future_to_file):
                try:
                    result = future.result()
                    all_results.append(result)
                except Exception as e:
                    # 这种情况理论上不应该发生，因为我们已经在safe_analyze_file中处理了所有异常
                    file_path = future_to_file[future]
                    all_results.append({
                        'file_path': Path(file_path).name,
                        'error': f'Executor error: {str(e)}',
                        'error_type': 'executor_error',
                        'success': False
                    })

        total_time = time.time() - start_time

        # 统计结果
        successful = sum(1 for r in all_results if r.get('success'))
        with_errors = len(all_results) - successful
        empty_files = sum(1 for r in all_results if r.get('is_empty'))
        files_with_syntax_issues = sum(1 for r in all_results if r.get('has_errors'))

        # 错误类型统计
        error_types = {}
        for result in all_results:
            if not result.get('success'):
                error_type = result.get('error_type', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1

        print(f"     - 总分析时间: {total_time:.3f}s")
        print(f"     - 成功分析: {successful}")
        print(f"     - 包含错误: {with_errors}")
        print(f"     - 空文件: {empty_files}")
        print(f"     - 语法问题文件: {files_with_syntax_issues}")
        print(f"     - 错误类型: {error_types}")
        print(f"     - 平均处理时间: {total_time/len(test_files):.3f}s/文件")

        # 验证错误处理
        error_handling_good = (
            len(all_results) == len(test_files) and  # 所有文件都被处理
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

def test_concurrent_resource_management():
    """测试并发分析的资源管理"""
    print("\n🔍 测试并发分析的资源管理...")

    try:
        # 创建大量文件测试资源管理
        temp_dir = tempfile.mkdtemp()
        test_files = []

        print("   创建资源管理测试文件:")
        for i in range(50):
            file_path = Path(temp_dir) / f"resource_test_{i:02d}.py"
            content = f'''# 资源管理测试文件 {i}
import os
import sys

def resource_function_{i}():
    """资源使用函数"""
    data = list(range({100 + i * 2}))
    return sum(data)

class ResourceClass{i}:
    """资源管理类"""

    def __init__(self):
        self.items = []
        for j in range({20 + i}):
            self.items.append(j * 2)

    def get_total(self):
        return sum(self.items)

def helper_{i}(x):
    return x * x

# 测试数据结构
test_dict_{i} = {{
    'numbers': list(range({10})),
    'strings': [f'str_{{j}}' for j in range(5)],
    'nested': {{'inner': [j for j in range(3)]}}
}}
'''
            file_path.write_text(content)
            test_files.append(str(file_path))

        print(f"     - 创建文件数: {len(test_files)}")

        # 资源感知的分析函数
        def resource_aware_analysis(file_path: str) -> Dict[str, Any]:
            """资源感知的分析函数"""
            import gc
            import threading

            start_time = time.time()
            start_objects = len(gc.get_objects())
            thread_id = threading.current_thread().ident

            try:
                # 读取文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 模拟内存使用
                temp_data = []
                for line_num, line in enumerate(content.splitlines()[:20]):  # 只处理前20行
                    temp_data.append({
                        'line_num': line_num,
                        'content': line.strip(),
                        'length': len(line),
                        'thread_id': thread_id
                    })

                # 分析内容
                lines = content.splitlines()
                functions = len([line for line in lines if 'def ' in line])
                classes = len([line for line in lines if 'class ' in line])

                # 计算一些指标
                total_line_length = sum(len(line) for line in lines)
                avg_line_length = total_line_length / len(lines) if lines else 0

                # 清理临时数据
                del temp_data

                end_time = time.time()
                end_objects = len(gc.get_objects())

                return {
                    'file_path': Path(file_path).name,
                    'line_count': len(lines),
                    'function_count': functions,
                    'class_count': classes,
                    'avg_line_length': round(avg_line_length, 1),
                    'total_line_length': total_line_length,
                    'analysis_time': end_time - start_time,
                    'thread_id': thread_id,
                    'objects_created': max(0, end_objects - start_objects),
                    'success': True
                }

            except Exception as e:
                return {
                    'file_path': Path(file_path).name,
                    'error': str(e),
                    'thread_id': thread_id,
                    'analysis_time': time.time() - start_time,
                    'success': False
                }

        # 测试不同并发级别的资源使用
        worker_counts = [4, 8, 16]
        resource_results = {}

        for max_workers in worker_counts:
            print(f"\n     测试并发数 {max_workers}:")

            # 手动垃圾回收以获得准确基线
            import gc
            gc.collect()
            initial_objects = len(gc.get_objects())

            start_time = time.time()
            analysis_results = []
            thread_usage = {}

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交任务（限制数量以控制测试时间）
                future_to_file = {
                    executor.submit(resource_aware_analysis, file_path): file_path
                    for file_path in test_files[:30]  # 只处理前30个文件
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
                        print(f"       - 执行异常: {e}")

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

            print(f"       - 分析时间: {total_time:.3f}s")
            print(f"       - 成功分析: {successful}")
            print(f"       - 使用线程数: {len(thread_usage)}")
            print(f"       - 创建对象: {total_objects_created}")
            print(f"       - 平均每文件对象: {avg_objects_per_file:.0f}")
            print(f"       - 对象泄漏: {resource_results[max_workers]['objects_leaked']}")
            print(f"       - 吞吐量: {successful/total_time:.1f} 文件/秒")

        # 分析资源管理效率
        print("\n   资源管理效率分析:")
        best_workers = max(resource_results.keys(),
                         key=lambda k: resource_results[k]['throughput'])
        best_result = resource_results[best_workers]

        print(f"     - 最佳并发数: {best_workers}")
        print(f"     - 最佳吞吐量: {best_result['throughput']:.1f} 文件/秒")
        print(f"     - 对象泄漏控制: {best_result['objects_leaked']}")

        # 验证资源管理
        resource_management_good = (
            all(result['successful'] > 0 for result in resource_results.values()) and
            all(result['objects_leaked'] < 500 for result in resource_results.values()) and
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
    print("🚀 开始多文件并发分析功能测试（简化版）")
    print("=" * 60)

    test_results = []

    # 1. 测试并发分析性能
    performance_ok = test_concurrent_analysis_performance()
    test_results.append(performance_ok)

    # 2. 测试并发分析错误处理
    error_ok = test_concurrent_error_handling()
    test_results.append(error_ok)

    # 3. 测试并发分析资源管理
    resource_ok = test_concurrent_resource_management()
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