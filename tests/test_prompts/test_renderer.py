"""
测试Prompt渲染器
"""

import pytest
from src.prompts.base import PromptTemplate, PromptCategory, PromptType
from src.prompts.renderer import (
    AdvancedPromptRenderer, ConditionalPromptRenderer, TemplateFunctionRenderer
)


class TestAdvancedPromptRenderer:
    """测试高级渲染器"""

    @pytest.fixture
    def renderer(self):
        """渲染器fixture"""
        return AdvancedPromptRenderer()

    @pytest.fixture
    def template(self):
        """模板fixture"""
        return PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}! Age: {{age}}.",
            description="Test template"
        )

    def test_render_basic_parameters(self, renderer, template):
        """测试基本参数渲染"""
        parameters = {"name": "Alice", "age": 25}
        result = renderer.render(template, parameters)

        assert result.success is True
        assert result.content == "Hello Alice! Age: 25."

    def test_render_complex_types(self, renderer):
        """测试复杂类型参数渲染"""
        template = PromptTemplate(
            name="complex_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="User: {{user}}\nSkills:\n{{skills}}",
            description="Complex template"
        )
        parameters = {
            "user": {"name": "Alice", "age": 25},
            "skills": ["Python", "Java", "SQL"]
        }
        result = renderer.render(template, parameters)

        assert result.success is True
        assert "name: Alice" in result.content
        assert "age: 25" in result.content
        assert "- Python" in result.content
        assert "- Java" in result.content
        assert "- SQL" in result.content

    def test_render_boolean_parameters(self, renderer):
        """测试布尔类型参数渲染"""
        template = PromptTemplate(
            name="bool_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Active: {{active}}, Verified: {{verified}}",
            description="Boolean template"
        )
        parameters = {"active": True, "verified": False}
        result = renderer.render(template, parameters)

        assert result.success is True
        assert result.content == "Active: true, Verified: false"

    def test_render_missing_parameters_strict_mode(self, renderer):
        """测试严格模式下缺失参数"""
        renderer.strict_mode = True
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}!"
        )
        result = renderer.render(template, {})

        assert result.success is False
        assert "Missing required parameters" in result.error_message

    def test_render_missing_parameters_non_strict_mode(self, renderer):
        """测试非严格模式下缺失参数"""
        renderer.strict_mode = False
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}!"
        )
        result = renderer.render(template, {})

        assert result.success is True  # 非严格模式下成功，但保留占位符
        assert result.content == "Hello {{name}}!"  # 原始占位符被保留
        assert len(result.missing_parameters) > 0  # 记录缺失参数

    def test_postprocess_content(self, renderer):
        """测试内容后处理"""
        template = PromptTemplate(
            name="multiline_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Line 1\n\n\n\nLine 2\n\nLine 3",
            description="Multiline template"
        )
        result = renderer.render(template, {})

        assert result.success is True
        # 应该清理多余的空行
        assert result.content == "Line 1\n\nLine 2\n\nLine 3"

    def test_custom_delimiters(self, renderer):
        """测试自定义分隔符"""
        renderer.delimiter_start = "[["
        renderer.delimiter_end = "]]"
        template = PromptTemplate(
            name="custom_delim_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello [[name]]!",
            description="Custom delimiter template"
        )
        result = renderer.render(template, {"name": "Alice"})

        assert result.success is True
        assert result.content == "Hello Alice!"

    def test_validate_template_mismatched_delimiters(self, renderer):
        """测试模板验证不匹配分隔符"""
        template = PromptTemplate(
            name="mismatched_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}! Age: [[age]]",
            description="Mismatched delimiter template"
        )
        errors = renderer.validate_template(template)
        assert len(errors) > 0
        assert any("Mismatched delimiters" in error for error in errors)


class TestConditionalPromptRenderer:
    """测试条件渲染器"""

    @pytest.fixture
    def renderer(self):
        """条件渲染器fixture"""
        return ConditionalPromptRenderer()

    def test_render_conditional_true(self, renderer):
        """测试条件为真时的渲染"""
        template = PromptTemplate(
            name="conditional_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="{{#if show_greeting}}Hello {{name}}!{{/if}}Welcome!",
            description="Conditional template"
        )
        parameters = {"show_greeting": True, "name": "Alice"}
        result = renderer.render(template, parameters)

        assert result.success is True
        assert "Hello Alice!" in result.content
        assert "Welcome!" in result.content

    def test_render_conditional_false(self, renderer):
        """测试条件为假时的渲染"""
        template = PromptTemplate(
            name="conditional_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="{{#if show_greeting}}Hello {{name}}!{{/if}}Welcome!",
            description="Conditional template"
        )
        parameters = {"show_greeting": False, "name": "Alice"}
        result = renderer.render(template, parameters)

        assert result.success is True
        assert "Hello Alice!" not in result.content
        assert result.content == "Welcome!"

    def test_render_multiple_conditionals(self, renderer):
        """测试多个条件渲染"""
        template = PromptTemplate(
            name="multi_conditional_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="{{#if is_admin}}Admin Panel{{/if}}{{#if is_user}}User Panel{{/if}}",
            description="Multiple conditional template"
        )

        # 测试管理员
        result = renderer.render(template, {"is_admin": True, "is_user": False})
        assert result.success is True
        assert result.content == "Admin Panel"

        # 测试用户
        result = renderer.render(template, {"is_admin": False, "is_user": True})
        assert result.success is True
        assert result.content == "User Panel"

        # 测试两者都是
        result = renderer.render(template, {"is_admin": True, "is_user": True})
        assert result.success is True
        assert result.content == "Admin PanelUser Panel"

    def test_render_nested_conditionals(self, renderer):
        """测试嵌套条件渲染"""
        template = PromptTemplate(
            name="nested_conditional_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="{{#if show_details}}{{#if has_name}}Name: {{name}}{{/if}}{{/if}}",
            description="Nested conditional template"
        )

        # 都为真
        result = renderer.render(template, {"show_details": True, "has_name": True, "name": "Alice"})
        assert result.success is True
        assert result.content == "Name: Alice"

        # 外层为假
        result = renderer.render(template, {"show_details": False, "has_name": True, "name": "Alice"})
        assert result.success is True
        assert result.content == ""

    def test_render_loop_simple(self, renderer):
        """测试简单循环渲染"""
        template = PromptTemplate(
            name="loop_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Items:\n{{#each items}}- {{this}}\n{{/each}}",
            description="Loop template"
        )
        parameters = {"items": ["Apple", "Banana", "Orange"]}
        result = renderer.render(template, parameters)

        assert result.success is True
        assert "- Apple" in result.content
        assert "- Banana" in result.content
        assert "- Orange" in result.content

    def test_render_loop_object(self, renderer):
        """测试对象循环渲染"""
        template = PromptTemplate(
            name="object_loop_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Users:\n{{#each users}}- {{name}} ({{age}})\n{{/each}}",
            description="Object loop template"
        )
        parameters = {
            "users": [
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 30}
            ]
        }
        result = renderer.render(template, parameters)

        assert result.success is True
        assert "- Alice (25)" in result.content
        assert "- Bob (30)" in result.content

    def test_render_empty_loop(self, renderer):
        """测试空循环渲染"""
        template = PromptTemplate(
            name="empty_loop_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Items:\n{{#each items}}- {{this}}\n{{/each}}No items found.",
            description="Empty loop template"
        )
        parameters = {"items": []}
        result = renderer.render(template, parameters)

        assert result.success is True
        assert result.content == "No items found."

    def test_render_conditional_and_loop_combined(self, renderer):
        """测试条件和循环组合渲染"""
        template = PromptTemplate(
            name="combined_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="{{#if show_list}}List:\n{{#each items}}- {{.}}\n{{/each}}{{/if}}",
            description="Combined template"
        )

        # 显示列表
        parameters = {"show_list": True, "items": ["A", "B", "C"]}
        result = renderer.render(template, parameters)
        assert result.success is True
        assert "List:" in result.content
        assert "- A" in result.content

        # 不显示列表
        parameters = {"show_list": False, "items": ["A", "B", "C"]}
        result = renderer.render(template, parameters)
        assert result.success is True
        assert result.content == ""


class TestTemplateFunctionRenderer:
    """测试模板函数渲染器"""

    @pytest.fixture
    def renderer(self):
        """函数渲染器fixture"""
        return TemplateFunctionRenderer()

    def test_render_upper_function(self, renderer):
        """测试大写函数"""
        template = PromptTemplate(
            name="upper_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{upper:name}}!",
            description="Upper function template"
        )
        result = renderer.render(template, {"name": "alice"})
        assert result.success is True
        assert result.content == "Hello ALICE!"

    def test_render_lower_function(self, renderer):
        """测试小写函数"""
        template = PromptTemplate(
            name="lower_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{lower:name}}!",
            description="Lower function template"
        )
        result = renderer.render(template, {"name": "ALICE"})
        assert result.success is True
        assert result.content == "Hello alice!"

    def test_render_capitalize_function(self, renderer):
        """测试首字母大写函数"""
        template = PromptTemplate(
            name="capitalize_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{capitalize:greeting}}!",
            description="Capitalize function template"
        )
        result = renderer.render(template, {"greeting": "world"})
        assert result.success is True
        assert result.content == "Hello World!"

    def test_render_title_function(self, renderer):
        """测试标题函数"""
        template = PromptTemplate(
            name="title_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="{{title:title}}",
            description="Title function template"
        )
        result = renderer.render(template, {"title": "hello world"})
        assert result.success is True
        assert result.content == "Hello World"

    def test_render_length_function(self, renderer):
        """测试长度函数"""
        template = PromptTemplate(
            name="length_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="String length: {{length:text}}",
            description="Length function template"
        )
        result = renderer.render(template, {"text": "hello"})
        assert result.success is True
        assert result.content == "String length: 5"

    def test_render_default_function(self, renderer):
        """测试默认值函数"""
        template = PromptTemplate(
            name="default_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Name: {{default:name}}",
            description="Default function template"
        )

        # 有值的情况
        result = renderer.render(template, {"name": "Alice"})
        assert result.success is True
        assert result.content == "Name: Alice"

        # 无值的情况
        result = renderer.render(template, {"name": ""})
        assert result.success is True
        assert result.content == "Name: "

    def test_render_default_function_with_custom_default(self, renderer):
        """测试带自定义默认值的默认函数"""
        template = PromptTemplate(
            name="default_custom_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Name: {{default:name}}",
            description="Default custom function template"
        )

        # 提供自定义默认值
        result = renderer.render(template, {"name": "", "name_default": "Guest"})
        assert result.success is True
        assert result.content == "Name: Guest"

    def test_add_custom_function(self, renderer):
        """测试添加自定义函数"""
        def reverse_function(text):
            return text[::-1]

        renderer.add_function("reverse", reverse_function)

        template = PromptTemplate(
            name="reverse_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Reversed: {{reverse:text}}",
            description="Custom function template"
        )
        result = renderer.render(template, {"text": "hello"})
        assert result.success is True
        assert result.content == "Reversed: olleh"

    def test_remove_function(self, renderer):
        """测试移除函数"""
        renderer.remove_function("upper")

        template = PromptTemplate(
            name="removed_function_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{upper:name}}!",
            description="Removed function template"
        )
        result = renderer.render(template, {"name": "alice"})
        assert result.success is True
        # 函数被移除，应该保持原样
        assert result.content == "Hello {{upper:name}}!"

    def test_render_function_error_handling(self, renderer):
        """测试函数错误处理"""
        def error_function(text):
            raise ValueError("Test error")

        renderer.add_function("error", error_function)

        template = PromptTemplate(
            name="error_function_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Result: {{error:text}}",
            description="Error function template"
        )
        result = renderer.render(template, {"text": "hello"})
        assert result.success is True
        # 错误时应该返回原值
        assert result.content == "Result: hello"

    def test_render_combined_functions_and_parameters(self, renderer):
        """测试函数和普通参数组合渲染"""
        template = PromptTemplate(
            name="combined_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{upper:name}}! You are {{age}} years old. Today is {{capitalize:day}}.",
            description="Combined function template"
        )
        parameters = {"name": "alice", "age": 25, "day": "monday"}
        result = renderer.render(template, parameters)

        assert result.success is True
        assert result.content == "Hello ALICE! You are 25 years old. Today is Monday."