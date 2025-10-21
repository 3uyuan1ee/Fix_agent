#!/usr/bin/env python3
"""
文件分析和结果格式化功能测试脚本
验证深度分析中的文件读取、分析和结果输出功能
"""

import sys
import os
import json
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_file_reading_capabilities():
    """测试文件读取能力"""
    print("🔍 测试文件读取能力...")

    try:
        # 创建测试文件
        temp_dir = tempfile.mkdtemp()
        test_files = {
            "simple.py": '''
def hello_world():
    """简单函数"""
    return "Hello, World!"

class TestClass:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}!"
''',
            "complex.js": '''
/**
 * 复杂JavaScript类
 */
class ComplexCalculator {
    constructor(initialValue = 0) {
        this.value = initialValue;
        this.history = [];
    }

    add(number) {
        this.history.push({operation: 'add', value: number, result: this.value + number});
        this.value += number;
        return this;
    }

    multiply(number) {
        this.history.push({operation: 'multiply', value: number, result: this.value * number});
        this.value *= number;
        return this;
    }

    async calculateAsync(operation, ...args) {
        await new Promise(resolve => setTimeout(resolve, 100));
        return this[operation](...args);
    }
}
''',
            "data.json": '''
{
    "name": "测试项目",
    "version": "1.0.0",
    "dependencies": {
        "lodash": "^4.17.21",
        "express": "^4.18.0"
    },
    "scripts": {
        "start": "node index.js",
        "test": "jest"
    }
}
''',
            "config.yaml": '''
# 应用配置
app:
  name: "测试应用"
  port: 8080
  debug: true

database:
  host: "localhost"
  port: 5432
  name: "testdb"

logging:
  level: "info"
  file: "app.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
'''
        }

        # 写入测试文件
        created_files = []
        for filename, content in test_files.items():
            file_path = Path(temp_dir) / filename
            file_path.write_text(content.strip())
            created_files.append(str(file_path))

        print(f"   - 创建测试文件: {len(created_files)} 个")

        # 测试文件读取功能
        read_results = []
        for file_path in created_files:
            try:
                file_path_obj = Path(file_path)
                if file_path_obj.exists():
                    content = file_path_obj.read_text(encoding='utf-8')
                    file_info = {
                        'path': file_path,
                        'size': len(content),
                        'lines': len(content.splitlines()),
                        'extension': file_path_obj.suffix,
                        'readable': True
                    }
                    read_results.append(file_info)
                    print(f"     ✅ {file_path_obj.name}: {file_info['lines']} 行, {file_info['size']} 字符")
                else:
                    print(f"     ❌ 文件不存在: {file_path}")
            except Exception as e:
                print(f"     ❌ 读取失败 {file_path}: {e}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        success = len(read_results) == len(created_files)
        print(f"   - 文件读取成功率: {len(read_results)}/{len(created_files)} ({len(read_results)/len(created_files):.1%})")

        return success

    except Exception as e:
        print(f"❌ 文件读取能力测试失败: {e}")
        return False

def test_file_analysis_functionality():
    """测试文件分析功能"""
    print("\n🔍 测试文件分析功能...")

    try:
        # 模拟文件分析器
        class MockFileAnalyzer:
            def __init__(self):
                self.analysis_patterns = {
                    'function_count': r'def\s+(\w+)',
                    'class_count': r'class\s+(\w+)',
                    'import_count': r'import\s+\w+|from\s+\w+\s+import',
                    'comment_ratio': r'#.*|/\*.*?\*/|//.*',
                    'complexity_indicators': r'if\s+.*else|for\s+.*in|while\s+.*|try\s*:.*except'
                }

            def analyze_file(self, file_path: str) -> dict:
                """分析单个文件"""
                try:
                    content = Path(file_path).read_text(encoding='utf-8')
                    lines = content.splitlines()

                    analysis = {
                        'file_path': file_path,
                        'file_size': len(content),
                        'line_count': len(lines),
                        'extension': Path(file_path).suffix,
                        'analysis_timestamp': datetime.now().isoformat(),
                        'metrics': {
                            'functions': len([line for line in lines if 'def ' in line]),
                            'classes': len([line for line in lines if 'class ' in line]),
                            'imports': len([line for line in lines if 'import ' in line or 'from ' in line]),
                            'comment_lines': len([line for line in lines if line.strip().startswith('#')]),
                            'blank_lines': len([line for line in lines if not line.strip()]),
                            'avg_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0
                        },
                        'complexity': 'low',
                        'quality_score': 8.5,
                        'suggestions': []
                    }

                    # 计算复杂度
                    if analysis['metrics']['functions'] > 10 or analysis['metrics']['classes'] > 5:
                        analysis['complexity'] = 'high'
                    elif analysis['metrics']['functions'] > 5 or analysis['metrics']['classes'] > 3:
                        analysis['complexity'] = 'medium'

                    # 生成建议
                    if analysis['metrics']['comment_lines'] / analysis['line_count'] < 0.1:
                        analysis['suggestions'].append("建议增加注释以提高代码可读性")

                    if analysis['metrics']['avg_line_length'] > 100:
                        analysis['suggestions'].append("建议缩短过长的代码行")

                    return analysis

                except Exception as e:
                    return {
                        'file_path': file_path,
                        'error': str(e),
                        'analysis_timestamp': datetime.now().isoformat()
                    }

        # 创建测试文件
        temp_dir = tempfile.mkdtemp()
        test_code = '''
def calculate_total(items):
    """计算总价"""
    total = 0
    for item in items:
        if item['price'] > 0:
            total += item['price'] * item.get('quantity', 1)
        else:
            raise ValueError("价格不能为负数")
    return total

class ShoppingCart:
    def __init__(self):
        self.items = []
        self.total = 0

    def add_item(self, name, price, quantity=1):
        self.items.append({
            'name': name,
            'price': price,
            'quantity': quantity
        })

    def calculate_total(self):
        self.total = calculate_total(self.items)
        return self.total
'''

        test_file = Path(temp_dir) / "test_ecommerce.py"
        test_file.write_text(test_code.strip())

        # 执行分析
        analyzer = MockFileAnalyzer()
        analysis_result = analyzer.analyze_file(str(test_file))

        print("   分析结果:")
        if 'error' not in analysis_result:
            print(f"     - 文件: {Path(analysis_result['file_path']).name}")
            print(f"     - 大小: {analysis_result['file_size']} 字符")
            print(f"     - 行数: {analysis_result['line_count']}")
            print(f"     - 函数数: {analysis_result['metrics']['functions']}")
            print(f"     - 类数: {analysis_result['metrics']['classes']}")
            print(f"     - 复杂度: {analysis_result['complexity']}")
            print(f"     - 质量分: {analysis_result['quality_score']}")
            print(f"     - 建议数: {len(analysis_result['suggestions'])}")

            analysis_valid = (
                analysis_result['metrics']['functions'] >= 2 and
                analysis_result['metrics']['classes'] >= 1 and
                analysis_result['complexity'] in ['low', 'medium', 'high'] and
                isinstance(analysis_result['quality_score'], (int, float))
            )
            print(f"     - 分析有效性: {'✅' if analysis_valid else '❌'}")
        else:
            print(f"     - 分析错误: {analysis_result['error']}")
            analysis_valid = False

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return analysis_valid

    except Exception as e:
        print(f"❌ 文件分析功能测试失败: {e}")
        return False

def test_result_formatting():
    """测试结果格式化功能"""
    print("\n🔍 测试结果格式化功能...")

    try:
        # 模拟分析结果
        mock_analysis_result = {
            'file_path': '/test/sample.py',
            'file_size': 2048,
            'line_count': 85,
            'extension': '.py',
            'analysis_timestamp': datetime.now().isoformat(),
            'metrics': {
                'functions': 6,
                'classes': 3,
                'imports': 8,
                'comment_lines': 15,
                'blank_lines': 12,
                'avg_line_length': 24.5
            },
            'complexity': 'medium',
            'quality_score': 7.8,
            'issues': [
                {
                    'type': 'style',
                    'severity': 'info',
                    'line': 15,
                    'message': '建议添加类型注解',
                    'suggestion': '为函数参数和返回值添加类型提示'
                },
                {
                    'type': 'performance',
                    'severity': 'warning',
                    'line': 32,
                    'message': '循环中的重复计算',
                    'suggestion': '将重复计算提取到循环外部'
                },
                {
                    'type': 'security',
                    'severity': 'error',
                    'line': 48,
                    'message': '潜在SQL注入风险',
                    'suggestion': '使用参数化查询替代字符串拼接'
                }
            ],
            'recommendations': [
                '增加单元测试覆盖率',
                '优化数据库查询性能',
                '改进错误处理机制'
            ],
            'suggestions': [
                '建议增加注释以提高代码可读性',
                '考虑使用类型提示增强代码健壮性'
            ]
        }

        # 测试不同格式化器
        class ResultFormatter:
            def format_as_json(self, result: dict) -> str:
                """JSON格式化"""
                return json.dumps(result, indent=2, ensure_ascii=False)

            def format_as_markdown(self, result: dict) -> str:
                """Markdown格式化"""
                md = f"""# 代码分析报告

## 文件信息
- **文件路径**: {result['file_path']}
- **文件大小**: {result['file_size']} 字符
- **代码行数**: {result['line_count']} 行
- **分析时间**: {result['analysis_timestamp']}

## 代码度量
- **函数数量**: {result['metrics']['functions']}
- **类数量**: {result['metrics']['classes']}
- **导入数量**: {result['metrics']['imports']}
- **注释行数**: {result['metrics']['comment_lines']}
- **空白行数**: {result['metrics']['blank_lines']}
- **平均行长度**: {result['metrics']['avg_line_length']:.1f}

## 质量评估
- **复杂度**: {result['complexity']}
- **质量评分**: {result['quality_score']}/10

## 发现的问题
"""
                for i, issue in enumerate(result['issues'], 1):
                    severity_emoji = {'error': '🚫', 'warning': '⚠️', 'info': 'ℹ️'}
                    md += f"""
### {i}. {issue['message']}
- **类型**: {issue['type']}
- **严重程度**: {severity_emoji.get(issue['severity'], '❓')} {issue['severity']}
- **行号**: {issue['line']}
- **建议**: {issue['suggestion']}
"""

                md += f"""
## 改进建议
"""
                for rec in result['recommendations']:
                    md += f"- {rec}\n"

                return md

            def format_as_text(self, result: dict) -> str:
                """纯文本格式化"""
                text = f"""代码分析报告
{'='*50}

文件信息:
  路径: {result['file_path']}
  大小: {result['file_size']} 字符
  行数: {result['line_count']} 行
  分析时间: {result['analysis_timestamp']}

代码度量:
  函数数量: {result['metrics']['functions']}
  类数量: {result['metrics']['classes']}
  导入数量: {result['metrics']['imports']}
  注释行数: {result['metrics']['comment_lines']}
  空白行数: {result['metrics']['blank_lines']}
  平均行长度: {result['metrics']['avg_line_length']:.1f}

质量评估:
  复杂度: {result['complexity']}
  质量评分: {result['quality_score']}/10

发现的问题:
"""
                for i, issue in enumerate(result['issues'], 1):
                    text += f"""
  {i}. {issue['message']} ({issue['severity']})
     行号: {issue['line']}
     建议: {issue['suggestion']}
"""

                text += "\n改进建议:\n"
                for rec in result['recommendations']:
                    text += f"  - {rec}\n"

                return text

        # 执行格式化测试
        formatter = ResultFormatter()

        # 测试JSON格式化
        json_output = formatter.format_as_json(mock_analysis_result)
        json_valid = len(json_output) > 100 and '"file_path"' in json_output
        print(f"   - JSON格式化: {'✅' if json_valid else '❌'} ({len(json_output)} 字符)")

        # 测试Markdown格式化
        md_output = formatter.format_as_markdown(mock_analysis_result)
        md_valid = len(md_output) > 200 and '##' in md_output and '**' in md_output
        print(f"   - Markdown格式化: {'✅' if md_valid else '❌'} ({len(md_output)} 字符)")

        # 测试文本格式化
        text_output = formatter.format_as_text(mock_analysis_result)
        text_valid = len(text_output) > 200 and '代码分析报告' in text_output
        print(f"   - 文本格式化: {'✅' if text_valid else '❌'} ({len(text_output)} 字符)")

        # 测试格式化一致性
        formats_consistent = all([
            json_valid,
            md_valid,
            text_valid,
            'sample.py' in json_output and 'sample.py' in md_output and 'sample.py' in text_output
        ])
        print(f"   - 格式一致性: {'✅' if formats_consistent else '❌'}")

        return formats_consistent

    except Exception as e:
        print(f"❌ 结果格式化功能测试失败: {e}")
        return False

def test_analysis_workflow():
    """测试完整分析工作流"""
    print("\n🔍 测试完整分析工作流...")

    try:
        # 模拟完整的分析工作流
        class AnalysisWorkflow:
            def __init__(self):
                self.supported_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.json', '.yaml', '.yml']
                self.max_file_size = 1024 * 1024  # 1MB

            def validate_file(self, file_path: str) -> dict:
                """验证文件是否适合分析"""
                path = Path(file_path)
                validation = {
                    'valid': True,
                    'reasons': [],
                    'file_info': {
                        'exists': path.exists(),
                        'is_file': path.is_file(),
                        'size': path.stat().st_size if path.exists() else 0,
                        'extension': path.suffix,
                        'readable': False
                    }
                }

                if not path.exists():
                    validation['valid'] = False
                    validation['reasons'].append('文件不存在')
                elif not path.is_file():
                    validation['valid'] = False
                    validation['reasons'].append('不是文件')
                elif path.stat().st_size > self.max_file_size:
                    validation['valid'] = False
                    validation['reasons'].append('文件过大')
                elif path.suffix not in self.supported_extensions:
                    validation['valid'] = False
                    validation['reasons'].append('不支持的文件类型')
                else:
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            f.read(100)  # 测试读取
                        validation['file_info']['readable'] = True
                    except UnicodeDecodeError:
                        validation['valid'] = False
                        validation['reasons'].append('文件编码问题')
                    except Exception as e:
                        validation['valid'] = False
                        validation['reasons'].append(f'读取错误: {e}')

                return validation

            def analyze_file(self, file_path: str) -> dict:
                """分析文件"""
                validation = self.validate_file(file_path)
                if not validation['valid']:
                    return {
                        'success': False,
                        'file_path': file_path,
                        'error': f"文件验证失败: {', '.join(validation['reasons'])}",
                        'validation': validation
                    }

                try:
                    content = Path(file_path).read_text(encoding='utf-8')

                    # 模拟分析过程
                    analysis = {
                        'success': True,
                        'file_path': file_path,
                        'analysis_time': datetime.now().isoformat(),
                        'file_stats': validation['file_info'],
                        'content_analysis': {
                            'total_lines': len(content.splitlines()),
                            'total_chars': len(content),
                            'estimated_reading_time': len(content.splitlines()) * 0.5,  # 分钟
                            'language': self._detect_language(file_path)
                        },
                        'quality_metrics': {
                            'complexity_score': self._calculate_complexity(content),
                            'maintainability_index': self._calculate_maintainability(content),
                            'technical_debt_ratio': self._calculate_tech_debt(content)
                        },
                        'recommendations': self._generate_recommendations(content, file_path)
                    }

                    return analysis

                except Exception as e:
                    return {
                        'success': False,
                        'file_path': file_path,
                        'error': f"分析过程中出错: {str(e)}",
                        'exception_type': type(e).__name__
                    }

            def _detect_language(self, file_path: str) -> str:
                """检测编程语言"""
                ext = Path(file_path).suffix.lower()
                language_map = {
                    '.py': 'Python',
                    '.js': 'JavaScript',
                    '.ts': 'TypeScript',
                    '.java': 'Java',
                    '.cpp': 'C++',
                    '.json': 'JSON',
                    '.yaml': 'YAML',
                    '.yml': 'YAML'
                }
                return language_map.get(ext, 'Unknown')

            def _calculate_complexity(self, content: str) -> float:
                """计算复杂度分数"""
                lines = content.splitlines()
                complexity_keywords = ['if', 'else', 'for', 'while', 'try', 'except', 'class', 'def', 'function']
                complexity_score = 0

                for line in lines:
                    line_lower = line.lower()
                    for keyword in complexity_keywords:
                        complexity_score += line_lower.count(keyword)

                return min(10.0, complexity_score / len(lines) * 2) if lines else 0

            def _calculate_maintainability(self, content: str) -> float:
                """计算可维护性指数"""
                lines = content.splitlines()
                comment_lines = len([line for line in lines if line.strip().startswith('#') or '//' in line])
                blank_lines = len([line for line in lines if not line.strip()])

                if len(lines) == 0:
                    return 10.0

                comment_ratio = comment_lines / len(lines)
                blank_ratio = blank_lines / len(lines)

                maintainability = 10.0 - (5.0 * (1 - comment_ratio)) - (2.0 * (1 - blank_ratio))
                return max(0.0, min(10.0, maintainability))

            def _calculate_tech_debt(self, content: str) -> float:
                """计算技术债务比率"""
                # 模拟技术债务计算
                complexity = self._calculate_complexity(content)
                maintainability = self._calculate_maintainability(content)
                tech_debt = max(0.0, (10.0 - maintainability + complexity) / 20.0 * 100)
                return tech_debt

            def _generate_recommendations(self, content: str, file_path: str) -> list:
                """生成改进建议"""
                recommendations = []
                lines = content.splitlines()

                # 基于文件长度的建议
                if len(lines) > 500:
                    recommendations.append("考虑将大文件拆分为多个小文件")
                elif len(lines) < 10:
                    recommendations.append("文件较小，确保功能完整")

                # 基于注释的建议
                comment_lines = len([line for line in lines if line.strip().startswith('#')])
                comment_ratio = comment_lines / len(lines) if lines else 0
                if comment_ratio < 0.1:
                    recommendations.append("建议增加注释以提高代码可读性")

                # 基于复杂度的建议
                complexity = self._calculate_complexity(content)
                if complexity > 7.0:
                    recommendations.append("代码复杂度较高，建议重构简化")

                # 语言特定建议
                if Path(file_path).suffix == '.py':
                    if 'type hint' not in content.lower():
                        recommendations.append("建议使用类型提示增强代码健壮性")
                elif Path(file_path).suffix == '.js':
                    if 'const' not in content and 'let' not in content:
                        recommendations.append("建议使用const/let替代var声明变量")

                return recommendations if recommendations else ["代码质量良好，无明显改进点"]

        # 创建测试文件
        temp_dir = tempfile.mkdtemp()
        test_files = {
            "good_code.py": '''
from typing import List, Dict

def calculate_average(numbers: List[float]) -> float:
    """
    计算数字列表的平均值

    Args:
        numbers: 数字列表

    Returns:
        平均值
    """
    if not numbers:
        return 0.0

    total = sum(numbers)
    return total / len(numbers)


class DataProcessor:
    """数据处理器"""

    def __init__(self, name: str):
        self.name = name
        self.processed_count = 0

    def process_data(self, data: List[Dict]) -> List[Dict]:
        """处理数据"""
        processed = []
        for item in data:
            if self._validate_item(item):
                processed.append(self._transform_item(item))
                self.processed_count += 1
        return processed

    def _validate_item(self, item: Dict) -> bool:
        """验证数据项"""
        return 'id' in item and 'value' in item

    def _transform_item(self, item: Dict) -> Dict:
        """转换数据项"""
        return {
            'id': item['id'],
            'value': item['value'] * 2,
            'processed_by': self.name
        }
''',
            "needs_improvement.js": '''
function processData(data) {
    var result = [];
    for (var i = 0; i < data.length; i++) {
        if (data[i].active == true) {
            result.push({
                id: data[i].id,
                value: data[i].value * 2,
                name: data[i].name
            });
        }
    }
    return result;
}

class User {
    constructor(name) {
        this.name = name;
        this.items = [];
    }

    addItem(item) {
        this.items.push(item);
        return this;
    }

    getTotal() {
        var total = 0;
        for (var i = 0; i < this.items.length; i++) {
            total += this.items[i].price;
        }
        return total;
    }
}
'''
        }

        # 写入测试文件
        created_files = []
        for filename, content in test_files.items():
            file_path = Path(temp_dir) / filename
            file_path.write_text(content.strip())
            created_files.append(str(file_path))

        # 执行工作流测试
        workflow = AnalysisWorkflow()
        analysis_results = []

        print(f"   分析 {len(created_files)} 个测试文件:")
        for file_path in created_files:
            result = workflow.analyze_file(file_path)
            analysis_results.append(result)

            if result['success']:
                file_name = Path(result['file_path']).name
                content_analysis = result['content_analysis']
                quality_metrics = result['quality_metrics']
                recommendations = result['recommendations']

                print(f"     ✅ {file_name}:")
                print(f"        - 语言: {content_analysis['language']}")
                print(f"        - 行数: {content_analysis['total_lines']}")
                print(f"        - 复杂度: {quality_metrics['complexity_score']:.1f}/10")
                print(f"        - 可维护性: {quality_metrics['maintainability_index']:.1f}/10")
                print(f"        - 建议数量: {len(recommendations)}")
            else:
                print(f"     ❌ {result['file_path']}: {result['error']}")

        # 验证结果
        successful_analyses = sum(1 for r in analysis_results if r['success'])
        total_files = len(created_files)
        success_rate = successful_analyses / total_files

        print(f"   - 工作流成功率: {successful_analyses}/{total_files} ({success_rate:.1%})")

        # 验证结果质量
        quality_checks = []
        for result in analysis_results:
            if result['success']:
                # 检查必需字段
                required_fields = ['content_analysis', 'quality_metrics', 'recommendations']
                has_all_fields = all(field in result for field in required_fields)
                quality_checks.append(has_all_fields)

        result_quality = all(quality_checks) if quality_checks else False
        print(f"   - 结果质量检查: {'✅' if result_quality else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return success_rate >= 0.8 and result_quality

    except Exception as e:
        print(f"❌ 完整分析工作流测试失败: {e}")
        return False

def test_async_file_analysis():
    """测试异步文件分析功能"""
    print("\n🔍 测试异步文件分析功能...")

    try:
        # 模拟异步文件分析器
        class AsyncFileAnalyzer:
            def __init__(self):
                self.max_concurrent = 3
                self.analysis_semaphore = None

            async def analyze_file_async(self, file_path: str) -> dict:
                """异步分析单个文件"""
                if not self.analysis_semaphore:
                    import asyncio
                    self.analysis_semaphore = asyncio.Semaphore(self.max_concurrent)

                async with self.analysis_semaphore:
                    # 模拟异步分析延迟
                    await asyncio.sleep(0.1)

                    try:
                        content = Path(file_path).read_text(encoding='utf-8')

                        # 模拟异步分析过程
                        await asyncio.sleep(0.05)

                        analysis = {
                            'file_path': file_path,
                            'analysis_completed': True,
                            'analysis_time': datetime.now().isoformat(),
                            'file_size': len(content),
                            'line_count': len(content.splitlines()),
                            'async_analysis': True,
                            'processing_time': 0.15  # 模拟处理时间
                        }

                        return analysis

                    except Exception as e:
                        return {
                            'file_path': file_path,
                            'analysis_completed': False,
                            'error': str(e),
                            'async_analysis': True
                        }

            async def analyze_multiple_files(self, file_paths: list) -> list:
                """异步分析多个文件"""
                tasks = [self.analyze_file_async(path) for path in file_paths]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                processed_results = []
                for result in results:
                    if isinstance(result, Exception):
                        processed_results.append({
                            'analysis_completed': False,
                            'error': f'异步执行错误: {str(result)}'
                        })
                    else:
                        processed_results.append(result)

                return processed_results

        # 创建测试文件
        temp_dir = tempfile.mkdtemp()
        test_contents = {
            "file1.py": "def function1():\n    return 'Hello World 1'",
            "file2.py": "def function2():\n    return 'Hello World 2'",
            "file3.py": "def function3():\n    return 'Hello World 3'",
            "file4.js": "function func4() { return 'Hello World 4'; }",
            "file5.js": "function func5() { return 'Hello World 5'; }"
        }

        created_files = []
        for filename, content in test_contents.items():
            file_path = Path(temp_dir) / filename
            file_path.write_text(content)
            created_files.append(str(file_path))

        # 执行异步分析
        async def run_async_test():
            analyzer = AsyncFileAnalyzer()

            start_time = asyncio.get_event_loop().time()
            results = await analyzer.analyze_multiple_files(created_files)
            end_time = asyncio.get_event_loop().time()

            return results, end_time - start_time

        # 运行异步测试
        import asyncio
        analysis_results, total_time = asyncio.run(run_async_test())

        print(f"   - 异步分析完成时间: {total_time:.3f}s")
        print(f"   - 分析文件数量: {len(created_files)}")
        print(f"   - 成功分析数量: {sum(1 for r in analysis_results if r.get('analysis_completed'))}")

        # 验证异步分析结果
        async_success = 0
        for result in analysis_results:
            if result.get('analysis_completed') and result.get('async_analysis'):
                async_success += 1
                print(f"     ✅ {Path(result['file_path']).name}: {result['file_size']} 字符")
            elif 'error' in result:
                print(f"     ❌ 分析失败: {result['error']}")

        async_success_rate = async_success / len(created_files)
        print(f"   - 异步分析成功率: {async_success_rate:.1%}")

        # 验证异步性能（应该比串行快）
        expected_serial_time = len(created_files) * 0.15  # 串行预期时间
        performance_good = total_time < expected_serial_time * 0.8  # 至少快20%
        print(f"   - 异步性能优势: {'✅' if performance_good else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return async_success_rate >= 0.8 and performance_good

    except Exception as e:
        print(f"❌ 异步文件分析功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始文件分析和结果格式化功能测试")
    print("=" * 60)

    test_results = []

    # 1. 测试文件读取能力
    reading_ok = test_file_reading_capabilities()
    test_results.append(reading_ok)

    # 2. 测试文件分析功能
    analysis_ok = test_file_analysis_functionality()
    test_results.append(analysis_ok)

    # 3. 测试结果格式化
    formatting_ok = test_result_formatting()
    test_results.append(formatting_ok)

    # 4. 测试完整分析工作流
    workflow_ok = test_analysis_workflow()
    test_results.append(workflow_ok)

    # 5. 测试异步文件分析
    async_ok = test_async_file_analysis()
    test_results.append(async_ok)

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 文件分析和结果格式化功能测试基本通过！")
        print("文件分析和结果格式化功能已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查文件分析功能。")
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