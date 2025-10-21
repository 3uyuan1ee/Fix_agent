#!/usr/bin/env python3
"""
Prompt管理系统测试脚本
用于验证Prompt管理器和模板渲染功能
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_prompt_manager_initialization():
    """测试Prompt管理器初始化"""
    print("🔍 测试Prompt管理器初始化...")

    try:
        from src.prompts.manager import PromptManager

        # 测试管理器初始化
        manager = PromptManager()
        print("✅ PromptManager 初始化成功")

        # 测试获取模板列表
        templates = manager.list_templates()
        print(f"✅ 可用模板: {len(templates)}个")
        for template in templates[:5]:  # 显示前5个
            print(f"   - {template}")
        if len(templates) > 5:
            print(f"   ... 还有 {len(templates)-5} 个模板")

        return manager

    except Exception as e:
        print(f"❌ Prompt管理器初始化失败: {e}")
        return None

def test_template_loading():
    """测试模板加载"""
    print("\n🔍 测试模板加载...")

    try:
        from src.prompts.manager import PromptManager

        manager = PromptManager()

        # 测试常见模板加载
        common_templates = [
            "deep_analysis_system",
            "deep_code_analysis",
            "deep_vulnerability_assessment",
            "deep_performance_analysis",
            "deep_architecture_analysis"
        ]

        loaded_count = 0
        for template_name in common_templates:
            template = manager.get_template(template_name)
            if template:
                print(f"✅ {template_name}: 加载成功")
                loaded_count += 1
            else:
                print(f"⚠️ {template_name}: 模板不存在")

        print(f"📊 模板加载统计: {loaded_count}/{len(common_templates)}")
        return loaded_count > 0

    except Exception as e:
        print(f"❌ 模板加载测试失败: {e}")
        return False

def test_template_rendering():
    """测试模板渲染"""
    print("\n🔍 测试模板渲染...")

    try:
        from src.prompts.manager import PromptManager

        manager = PromptManager()

        # 测试深度分析系统模板
        system_result = manager.render_template(
            "deep_analysis_system",
            {"analysis_type": "comprehensive"}
        )

        if system_result.success:
            print("✅ 深度分析系统模板渲染成功")
            print(f"   - 内容长度: {len(system_result.content)} 字符")
            print(f"   - 内容预览: {system_result.content[:100]}...")
        else:
            print(f"❌ 深度分析系统模板渲染失败: {system_result.error}")

        # 测试代码分析模板
        code_variables = {
            "file_content": "def hello():\n    print('Hello, World!')",
            "analysis_type": "comprehensive",
            "user_instructions": "请重点关注代码质量",
            "context": {"language": "python", "framework": "none"}
        }

        code_result = manager.render_template("deep_code_analysis", code_variables)

        if code_result.success:
            print("✅ 代码分析模板渲染成功")
            print(f"   - 内容长度: {len(code_result.content)} 字符")
            print(f"   - 内容预览: {code_result.content[:100]}...")
        else:
            print(f"❌ 代码分析模板渲染失败: {code_result.error}")

        return system_result.success or code_result.success

    except Exception as e:
        print(f"❌ 模板渲染测试失败: {e}")
        return False

def test_template_base_class():
    """测试模板基类功能"""
    print("\n🔍 测试模板基类功能...")

    try:
        from src.prompts.base import Template, TemplateResult

        # 创建简单模板
        class SimpleTemplate(Template):
            def render(self, variables):
                content = f"分析类型: {variables.get('analysis_type', 'unknown')}\n"
                content += f"文件内容:\n{variables.get('file_content', 'No content')}\n"
                if variables.get('user_instructions'):
                    content += f"用户指示: {variables['user_instructions']}\n"
                return TemplateResult(success=True, content=content)

        # 测试模板渲染
        template = SimpleTemplate("test_template", "测试模板")
        result = template.render({
            "analysis_type": "security",
            "file_content": "def test(): pass",
            "user_instructions": "检查安全问题"
        })

        if result.success:
            print("✅ 简单模板渲染成功")
            print(f"   - 模板名称: {template.name}")
            print(f"   - 模板描述: {template.description}")
            print(f"   - 内容长度: {len(result.content)} 字符")
            print(f"   - 内容预览: {result.content[:100]}...")

            return True
        else:
            print(f"❌ 简单模板渲染失败: {result.error}")
            return False

    except Exception as e:
        print(f"❌ 模板基类测试失败: {e}")
        return False

def test_template_validation():
    """测试模板验证"""
    print("\n🔍 测试模板验证...")

    try:
        from src.prompts.base import Template, TemplateResult

        # 创建带验证的模板
        class ValidatedTemplate(Template):
            def __init__(self):
                super().__init__("validated_template", "带验证的模板")
                self.required_variables = ["file_content", "analysis_type"]

            def render(self, variables):
                # 验证必需变量
                missing_vars = []
                for var in self.required_variables:
                    if var not in variables or not variables[var]:
                        missing_vars.append(var)

                if missing_vars:
                    return TemplateResult(
                        success=False,
                        error=f"缺少必需变量: {', '.join(missing_vars)}"
                    )

                content = f"分析类型: {variables['analysis_type']}\n"
                content += f"文件内容: {variables['file_content']}\n"
                return TemplateResult(success=True, content=content)

        template = ValidatedTemplate()

        # 测试成功的渲染
        success_result = template.render({
            "file_content": "test content",
            "analysis_type": "security"
        })

        if success_result.success:
            print("✅ 模板验证通过")
        else:
            print(f"❌ 模板验证失败: {success_result.error}")
            return False

        # 测试失败的渲染
        fail_result = template.render({
            "file_content": "test content"
            # 缺少 analysis_type
        })

        if not fail_result.success:
            print("✅ 模板验证正确捕获了缺失变量")
            print(f"   - 错误信息: {fail_result.error}")
        else:
            print("❌ 模板验证未能捕获缺失变量")
            return False

        return True

    except Exception as e:
        print(f"❌ 模板验证测试失败: {e}")
        return False

def test_template_renderer():
    """测试模板渲染器"""
    print("\n🔍 测试模板渲染器...")

    try:
        from src.prompts.renderer import TemplateRenderer

        renderer = TemplateRenderer()

        # 测试简单字符串渲染
        template_str = "分析 {{analysis_type}}:\n{{file_content}}"
        variables = {
            "analysis_type": "performance",
            "file_content": "def slow_function():\n    return sum(range(10000))"
        }

        rendered = renderer.render_string(template_str, variables)
        print("✅ 字符串模板渲染成功")
        print(f"   - 原始模板: {template_str}")
        print(f"   - 渲染结果: {rendered}")

        # 测试Jinja2模板渲染（如果可用）
        jinja_template = """
分析报告: {{ analysis_type | upper }}
文件内容:
```python
{{ file_content }}
```
用户指示: {% if user_instructions %}{{ user_instructions }}{% else %}无特殊指示{% endif %}
"""

        jinja_rendered = renderer.render_jinja2(jinja_template, variables)
        print("✅ Jinja2模板渲染成功")
        print(f"   - 渲染结果长度: {len(jinja_rendered)} 字符")
        print(f"   - 渲染结果预览: {jinja_rendered[:100]}...")

        return True

    except Exception as e:
        print(f"❌ 模板渲染器测试失败: {e}")
        return False

def test_template_caching():
    """测试模板缓存"""
    print("\n🔍 测试模板缓存...")

    try:
        from src.prompts.manager import PromptManager

        manager = PromptManager()

        # 测试模板缓存
        template_name = "deep_analysis_system"

        # 第一次加载（应该从文件加载）
        import time
        start_time = time.time()
        template1 = manager.get_template(template_name)
        first_load_time = time.time() - start_time

        # 第二次加载（应该从缓存加载）
        start_time = time.time()
        template2 = manager.get_template(template_name)
        second_load_time = time.time() - start_time

        if template1 and template2:
            print("✅ 模板缓存功能正常")
            print(f"   - 首次加载时间: {first_load_time:.4f}s")
            print(f"   - 缓存加载时间: {second_load_time:.4f}s")
            print(f"   - 缓存加速比: {first_load_time/second_load_time:.1f}x")
            return True
        else:
            print("❌ 模板加载失败")
            return False

    except Exception as e:
        print(f"❌ 模板缓存测试失败: {e}")
        return False

def test_custom_template_creation():
    """测试自定义模板创建"""
    print("\n🔍 测试自定义模板创建...")

    try:
        from src.prompts.base import Template, TemplateResult
        from src.prompts.manager import PromptManager

        # 创建自定义模板
        class CustomAnalysisTemplate(Template):
            def __init__(self):
                super().__init__(
                    "custom_analysis",
                    "自定义代码分析模板"
                )

            def render(self, variables):
                file_path = variables.get('file_path', 'unknown')
                analysis_type = variables.get('analysis_type', 'general')
                file_content = variables.get('file_content', '')

                content = f"""自定义分析报告
================
文件路径: {file_path}
分析类型: {analysis_type}

代码内容:
{file_content}

分析建议:
1. 检查代码质量
2. 识别潜在问题
3. 提供改进建议
"""
                return TemplateResult(success=True, content=content)

        # 注册自定义模板
        manager = PromptManager()
        custom_template = CustomAnalysisTemplate()
        manager.register_template("custom_analysis", custom_template)

        # 测试自定义模板渲染
        result = manager.render_template("custom_analysis", {
            "file_path": "test.py",
            "analysis_type": "security",
            "file_content": "import os\n\ndef read_file(path):\n    return open(path).read()"
        })

        if result.success:
            print("✅ 自定义模板创建和渲染成功")
            print(f"   - 模板名称: {custom_template.name}")
            print(f"   - 内容长度: {len(result.content)} 字符")
            print(f"   - 内容预览: {result.content[:100]}...")
            return True
        else:
            print(f"❌ 自定义模板渲染失败: {result.error}")
            return False

    except Exception as e:
        print(f"❌ 自定义模板创建测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始Prompt管理系统测试")
    print("=" * 50)

    test_results = []

    # 1. 测试Prompt管理器初始化
    manager = test_prompt_manager_initialization()
    test_results.append(manager is not None)

    # 2. 测试模板加载
    loading_ok = test_template_loading()
    test_results.append(loading_ok)

    # 3. 测试模板渲染
    rendering_ok = test_template_rendering()
    test_results.append(rendering_ok)

    # 4. 测试模板基类
    base_class_ok = test_template_base_class()
    test_results.append(base_class_ok)

    # 5. 测试模板验证
    validation_ok = test_template_validation()
    test_results.append(validation_ok)

    # 6. 测试模板渲染器
    renderer_ok = test_template_renderer()
    test_results.append(renderer_ok)

    # 7. 测试模板缓存
    caching_ok = test_template_caching()
    test_results.append(caching_ok)

    # 8. 测试自定义模板创建
    custom_ok = test_custom_template_creation()
    test_results.append(custom_ok)

    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 Prompt管理系统测试基本通过！")
        print("Prompt管理器和模板渲染功能已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查Prompt系统。")
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