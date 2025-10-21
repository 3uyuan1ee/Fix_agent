#!/usr/bin/env python3
"""
深度分析功能测试脚本（Mock版本）
用于验证DeepAnalyzer的核心功能可用性，不需要真实API密钥
"""

import sys
import os
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

class MockLLMClient:
    """Mock LLM客户端"""
    def __init__(self):
        self.default_model = "glm-4.5"
        self.stats = {"total_requests": 0, "successful_requests": 0}

    def create_request(self, messages, **kwargs):
        """创建请求"""
        class MockRequest:
            def __init__(self):
                self.messages = messages
                self.model = kwargs.get('model', 'glm-4.5')
                self.temperature = kwargs.get('temperature', 0.3)
                self.max_tokens = kwargs.get('max_tokens', 4000)

        return MockRequest()

    async def complete(self, request):
        """完成请求"""
        self.stats["total_requests"] += 1
        self.stats["successful_requests"] += 1

        class MockResponse:
            def __init__(self):
                self.content = '''{
    "summary": "代码质量良好，结构清晰",
    "issues": [
        {
            "type": "suggestion",
            "line": 1,
            "message": "建议添加函数文档字符串"
        }
    ],
    "recommendations": [
        "添加详细的文档说明",
        "考虑添加类型注解",
        "添加错误处理机制"
    ],
    "overall_score": 8.5
}'''
                self.model = request.model
                self.provider = "mock"
                self.usage = {"total_tokens": 150}

        return MockResponse()

class MockPromptManager:
    """Mock Prompt管理器"""
    def get_template(self, template_name):
        """获取模板"""
        if template_name == "deep_analysis_system":
            return MockTemplate()
        return None

    def render_template(self, template_name, variables):
        """渲染模板"""
        class MockResult:
            def __init__(self):
                self.success = True
                self.content = f"请分析以下代码（{variables.get('analysis_type', 'comprehensive')}分析）：\n\n{variables.get('file_content', '')}"

        return MockResult()

class MockTemplate:
    """Mock模板"""
    def render(self, variables):
        return f"Mock rendered template with {variables}"

def test_deep_analyzer_initialization():
    """测试DeepAnalyzer初始化"""
    print("🔍 测试DeepAnalyzer初始化...")

    try:
        from src.tools.deep_analyzer import DeepAnalyzer, DeepAnalysisRequest, DeepAnalysisResult

        # Mock LLM客户端和Prompt管理器
        with patch('src.tools.deep_analyzer.LLMClient', MockLLMClient), \
             patch('src.tools.deep_analyzer.PromptManager', MockPromptManager):

            # 测试无参初始化
            analyzer = DeepAnalyzer()
            print("✅ DeepAnalyzer 默认初始化成功")

            # 测试获取支持的分析类型
            supported_types = analyzer.get_supported_analysis_types()
            print(f"✅ 支持的分析类型: {supported_types}")

            # 测试配置
            print(f"   - 默认模型: {analyzer.default_model}")
            print(f"   - 默认温度: {analyzer.default_temperature}")
            print(f"   - 最大tokens: {analyzer.max_tokens}")
            print(f"   - 最大文件大小: {analyzer.max_file_size} bytes")

            return analyzer

    except Exception as e:
        print(f"❌ DeepAnalyzer 初始化失败: {e}")
        return None

def test_deep_analysis_request_creation():
    """测试DeepAnalysisRequest创建"""
    print("\n🔍 测试DeepAnalysisRequest创建...")

    try:
        from src.tools.deep_analyzer import DeepAnalysisRequest

        # 创建请求对象
        request = DeepAnalysisRequest(
            file_path="test_file.py",
            analysis_type="comprehensive",
            temperature=0.3,
            max_tokens=4000,
            user_instructions="请分析这个代码的质量"
        )

        print("✅ DeepAnalysisRequest 创建成功")
        print(f"   - 文件路径: {request.file_path}")
        print(f"   - 分析类型: {request.analysis_type}")
        print(f"   - 温度: {request.temperature}")
        print(f"   - 最大tokens: {request.max_tokens}")
        print(f"   - 用户指令: {request.user_instructions}")

        return request

    except Exception as e:
        print(f"❌ DeepAnalysisRequest 创建失败: {e}")
        return None

def test_file_reading():
    """测试文件读取功能"""
    print("\n🔍 测试文件读取功能...")

    try:
        from src.tools.deep_analyzer import DeepAnalyzer

        # Mock LLM客户端和Prompt管理器
        with patch('src.tools.deep_analyzer.LLMClient', MockLLMClient), \
             patch('src.tools.deep_analyzer.PromptManager', MockPromptManager):

            analyzer = DeepAnalyzer()

            # 创建测试文件
            test_file = Path("test_sample.py")
            test_content = '''def calculate_fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def main():
    for i in range(10):
        print(f"F({i}) = {calculate_fibonacci(i)}")

if __name__ == "__main__":
    main()
'''

            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_content)

            # 测试读取文件
            content = analyzer._read_file_content(test_file)

            if content:
                print("✅ 文件读取成功")
                print(f"   - 文件大小: {len(content)} 字符")
                print(f"   - 内容预览: {content[:100]}...")

                # 清理测试文件
                test_file.unlink()
                return content
            else:
                print("❌ 文件读取失败")
                return None

    except Exception as e:
        print(f"❌ 文件读取测试失败: {e}")
        return None

def test_prompt_construction():
    """测试Prompt构造功能"""
    print("\n🔍 测试Prompt构造功能...")

    try:
        from src.tools.deep_analyzer import DeepAnalyzer, DeepAnalysisRequest

        # Mock LLM客户端和Prompt管理器
        with patch('src.tools.deep_analyzer.LLMClient', MockLLMClient), \
             patch('src.tools.deep_analyzer.PromptManager', MockPromptManager):

            analyzer = DeepAnalyzer()

            # 创建测试请求
            request = DeepAnalysisRequest(
                file_path="test_file.py",
                analysis_type="comprehensive",
                user_instructions="请重点关注代码的可读性和性能"
            )

            test_content = '''def hello_world():
    print("Hello, World!")
'''

            # 构造prompt
            messages = analyzer._construct_prompt(test_content, request)

            if messages:
                print("✅ Prompt构造成功")
                print(f"   - 消息数量: {len(messages)}")
                for i, msg in enumerate(messages):
                    print(f"   - 消息 {i+1}: {msg['role']} (长度: {len(msg['content'])})")
                    if i == 0:  # 系统消息
                        print(f"     内容预览: {msg['content'][:100]}...")

                return messages
            else:
                print("❌ Prompt构造失败")
                return None

    except Exception as e:
        print(f"❌ Prompt构造测试失败: {e}")
        return None

def test_response_parsing():
    """测试响应解析功能"""
    print("\n🔍 测试响应解析功能...")

    try:
        from src.tools.deep_analyzer import DeepAnalyzer

        # Mock LLM客户端和Prompt管理器
        with patch('src.tools.deep_analyzer.LLMClient', MockLLMClient), \
             patch('src.tools.deep_analyzer.PromptManager', MockPromptManager):

            analyzer = DeepAnalyzer()

            # 测试JSON格式响应
            json_response = '''{
    "summary": "代码质量良好，但有一些改进建议",
    "issues": [
        {
            "type": "style",
            "line": 2,
            "message": "建议添加类型注解"
        }
    ],
    "recommendations": [
        "添加类型注解",
        "添加错误处理"
    ]
}'''

            parsed = analyzer._parse_llm_response(json_response)
            print("✅ JSON响应解析成功")
            print(f"   - 解析格式: {parsed.get('format', 'unknown')}")
            print(f"   - 摘要: {parsed.get('summary', '')[:50]}...")

            # 测试文本格式响应
            text_response = """这是一个简单的代码分析报告：

1. 总体评估：代码结构清晰
2. 发现问题：无错误处理
3. 改进建议：添加异常处理机制

建议重构以提高代码健壮性。"""

            parsed_text = analyzer._parse_llm_response(text_response)
            print("✅ 文本响应解析成功")
            print(f"   - 解析格式: {parsed_text.get('format', 'unknown')}")
            print(f"   - 摘要: {parsed_text.get('summary', '')[:50]}...")

            return True

    except Exception as e:
        print(f"❌ 响应解析测试失败: {e}")
        return False

def test_result_formatting():
    """测试结果格式化功能"""
    print("\n🔍 测试结果格式化功能...")

    try:
        from src.tools.deep_analyzer import DeepAnalyzer, DeepAnalysisResult

        # Mock LLM客户端和Prompt管理器
        with patch('src.tools.deep_analyzer.LLMClient', MockLLMClient), \
             patch('src.tools.deep_analyzer.PromptManager', MockPromptManager):

            analyzer = DeepAnalyzer()

            # 创建测试结果
            result = DeepAnalysisResult(
                file_path="test_file.py",
                analysis_type="comprehensive",
                success=True,
                content="这是一个分析结果示例",
                structured_analysis={
                    "summary": "代码质量良好",
                    "issues": [],
                    "recommendations": ["添加文档"]
                },
                execution_time=1.23,
                model_used="glm-4.5",
                token_usage={"total_tokens": 500}
            )

            # 测试文本格式化
            text_output = analyzer.format_analysis_result(result, "text")
            print("✅ 文本格式化成功")
            print(f"   - 输出长度: {len(text_output)} 字符")
            print(f"   - 预览: {text_output[:100]}...")

            # 测试JSON格式化
            json_output = analyzer.format_analysis_result(result, "json")
            print("✅ JSON格式化成功")
            print(f"   - 输出长度: {len(json_output)} 字符")

            # 测试Markdown格式化
            md_output = analyzer.format_analysis_result(result, "markdown")
            print("✅ Markdown格式化成功")
            print(f"   - 输出长度: {len(md_output)} 字符")

            return True

    except Exception as e:
        print(f"❌ 结果格式化测试失败: {e}")
        return False

def test_file_analysis():
    """测试完整的文件分析流程"""
    print("\n🔍 测试完整的文件分析流程...")

    try:
        from src.tools.deep_analyzer import DeepAnalyzer, DeepAnalysisRequest
        import asyncio

        # Mock LLM客户端和Prompt管理器
        with patch('src.tools.deep_analyzer.LLMClient', MockLLMClient), \
             patch('src.tools.deep_analyzer.PromptManager', MockPromptManager):

            analyzer = DeepAnalyzer()

            # 创建测试文件
            test_file = Path("test_analysis_sample.py")
            test_content = '''def calculate_average(numbers):
    """计算数字列表的平均值"""
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

def find_duplicates(items):
    """查找列表中的重复项"""
    seen = set()
    duplicates = []
    for item in items:
        if item in seen:
            duplicates.append(item)
        seen.add(item)
    return duplicates

def main():
    numbers = [1, 2, 3, 4, 5, 2, 3]
    avg = calculate_average(numbers)
    dups = find_duplicates(numbers)
    print(f"平均值: {avg}")
    print(f"重复项: {dups}")

if __name__ == "__main__":
    main()
'''

            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_content)

            # 创建分析请求
            request = DeepAnalysisRequest(
                file_path=str(test_file),
                analysis_type="comprehensive",
                user_instructions="请重点关注代码质量和性能优化"
            )

            # 执行分析（使用asyncio运行异步函数）
            print("   开始分析...")

            async def run_analysis():
                return await analyzer.analyze_file(request)

            result = asyncio.run(run_analysis())

            if result.success:
                print("✅ 文件分析成功")
                print(f"   - 分析文件: {result.file_path}")
                print(f"   - 分析类型: {result.analysis_type}")
                print(f"   - 执行时间: {result.execution_time:.2f}秒")
                print(f"   - 使用模型: {result.model_used}")
                print(f"   - Token使用: {result.token_usage}")
                print(f"   - 内容长度: {len(result.content)} 字符")

                # 清理测试文件
                test_file.unlink()
                return result
            else:
                print(f"❌ 文件分析失败: {result.error}")
                test_file.unlink()
                return None

    except Exception as e:
        print(f"❌ 文件分析测试失败: {e}")
        return None

def main():
    """主测试函数"""
    print("🚀 开始DeepAnalyzer核心功能测试（Mock版本）")
    print("=" * 60)

    test_results = []

    # 1. 测试初始化
    analyzer = test_deep_analyzer_initialization()
    test_results.append(analyzer is not None)

    # 2. 测试请求创建
    request = test_deep_analysis_request_creation()
    test_results.append(request is not None)

    # 3. 测试文件读取
    content = test_file_reading()
    test_results.append(content is not None)

    # 4. 测试Prompt构造
    messages = test_prompt_construction()
    test_results.append(messages is not None)

    # 5. 测试响应解析
    parsing_ok = test_response_parsing()
    test_results.append(parsing_ok)

    # 6. 测试结果格式化
    formatting_ok = test_result_formatting()
    test_results.append(formatting_ok)

    # 7. 测试完整分析流程
    print("\n🔍 测试异步分析流程...")
    try:
        result = asyncio.run(test_file_analysis())
        test_results.append(result is not None)
    except Exception as e:
        print(f"❌ 异步分析流程测试失败: {e}")
        test_results.append(False)

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed == total:
        print("\n🎉 所有DeepAnalyzer核心功能测试通过！")
        print("深度分析基础功能已就绪，可以进行下一步测试。")
        return 0
    else:
        print(f"\n⚠️ 有 {total-passed} 项测试失败，需要检查相关功能。")
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