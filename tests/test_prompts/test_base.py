"""
测试Prompt基础类和数据结构
"""

import pytest
from src.prompts.base import (
    PromptTemplate, PromptCategory, PromptType, PromptRenderResult,
    BasePromptRenderer
)


class TestPromptCategory:
    """测试Prompt类别枚举"""

    def test_category_values(self):
        """测试类别枚举值"""
        assert PromptCategory.STATIC_ANALYSIS.value == "static_analysis"
        assert PromptCategory.DEEP_ANALYSIS.value == "deep_analysis"
        assert PromptCategory.REPAIR_SUGGESTION.value == "repair_suggestion"


class TestPromptType:
    """测试Prompt类型枚举"""

    def test_type_values(self):
        """测试类型枚举值"""
        assert PromptType.SYSTEM.value == "system"
        assert PromptType.USER.value == "user"
        assert PromptType.ASSISTANT.value == "assistant"
        assert PromptType.FUNCTION.value == "function"


class TestPromptTemplate:
    """测试Prompt模板数据类"""

    def test_template_creation(self):
        """测试模板创建"""
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}!",
            description="Test template"
        )
        assert template.name == "test_template"
        assert template.category == PromptCategory.STATIC_ANALYSIS
        assert template.prompt_type == PromptType.USER
        assert template.template == "Hello {{name}}!"
        assert template.description == "Test template"

    def test_template_parameter_extraction(self):
        """测试参数提取"""
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}! You are {{age}} years old."
        )
        expected_params = {"name": "Parameter 'name' to be replaced", "age": "Parameter 'age' to be replaced"}
        assert template.parameters == expected_params

    def test_template_no_parameters(self):
        """测试无参数模板"""
        template = PromptTemplate(
            name="simple_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello world!"
        )
        assert template.parameters == {}
        assert not template.has_parameters()

    def test_template_validation_success(self):
        """测试参数验证成功"""
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}!"
        )
        missing_params = template.validate_parameters({"name": "Alice"})
        assert missing_params == []

    def test_template_validation_missing_params(self):
        """测试参数验证缺失参数"""
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}! You are {{age}} years old."
        )
        missing_params = template.validate_parameters({"name": "Alice"})
        assert missing_params == ["age"]

    def test_template_get_required_parameters(self):
        """测试获取必需参数"""
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}! You are {{age}} years old."
        )
        required_params = template.get_required_parameters()
        assert set(required_params) == {"name", "age"}

    def test_template_to_dict(self):
        """测试模板转换为字典"""
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}!",
            description="Test template",
            version="1.0",
            tags=["test", "demo"]
        )
        template_dict = template.to_dict()
        assert template_dict["name"] == "test_template"
        assert template_dict["category"] == "static_analysis"
        assert template_dict["prompt_type"] == "user"
        assert template_dict["template"] == "Hello {{name}}!"
        assert template_dict["description"] == "Test template"
        assert template_dict["version"] == "1.0"
        assert template_dict["tags"] == ["test", "demo"]

    def test_template_from_dict(self):
        """测试从字典创建模板"""
        data = {
            "name": "test_template",
            "category": "static_analysis",
            "prompt_type": "user",
            "template": "Hello {{name}}!",
            "description": "Test template",
            "version": "1.0"
        }
        template = PromptTemplate.from_dict(data)
        assert template.name == "test_template"
        assert template.category == PromptCategory.STATIC_ANALYSIS
        assert template.prompt_type == PromptType.USER
        assert template.template == "Hello {{name}}!"
        assert template.description == "Test template"
        assert template.version == "1.0"

    def test_template_empty_content_error(self):
        """测试空内容模板错误"""
        with pytest.raises(ValueError, match="Template content cannot be empty"):
            PromptTemplate(
                name="empty_template",
                category=PromptCategory.STATIC_ANALYSIS,
                prompt_type=PromptType.USER,
                template=""
            )


class TestPromptRenderResult:
    """测试Prompt渲染结果"""

    def test_render_result_creation(self):
        """测试渲染结果创建"""
        result = PromptRenderResult(
            content="Hello Alice!",
            template_name="test_template",
            parameters_used={"name": "Alice"},
            render_time=0.1
        )
        assert result.content == "Hello Alice!"
        assert result.template_name == "test_template"
        assert result.parameters_used == {"name": "Alice"}
        assert result.render_time == 0.1
        assert result.success is True

    def test_render_result_failure(self):
        """测试渲染结果失败"""
        result = PromptRenderResult(
            content="",
            template_name="test_template",
            parameters_used={},
            success=False,
            error_message="Missing parameter: name",
            missing_parameters=["name"]
        )
        assert result.content == ""
        assert result.success is False
        assert result.error_message == "Missing parameter: name"
        assert result.missing_parameters == ["name"]

    def test_render_result_to_dict(self):
        """测试渲染结果转换为字典"""
        result = PromptRenderResult(
            content="Hello Alice!",
            template_name="test_template",
            parameters_used={"name": "Alice"},
            render_time=0.1
        )
        result_dict = result.to_dict()
        assert result_dict["content"] == "Hello Alice!"
        assert result_dict["template_name"] == "test_template"
        assert result_dict["parameters_used"] == {"name": "Alice"}
        assert result_dict["render_time"] == 0.1
        assert result_dict["success"] is True


class TestBasePromptRenderer:
    """测试基础Prompt渲染器"""

    @pytest.fixture
    def renderer(self):
        """渲染器fixture"""
        return BasePromptRenderer()

    @pytest.fixture
    def template(self):
        """模板fixture"""
        return PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}! You are {{age}} years old.",
            description="Test template"
        )

    def test_render_success(self, renderer, template):
        """测试渲染成功"""
        parameters = {"name": "Alice", "age": 25}
        result = renderer.render(template, parameters)

        assert result.success is True
        assert result.content == "Hello Alice! You are 25 years old."
        assert result.template_name == "test_template"
        assert result.parameters_used == {"name": "Alice", "age": 25}

    def test_render_missing_parameter(self, renderer, template):
        """测试渲染缺失参数"""
        parameters = {"name": "Alice"}  # 缺少age参数
        result = renderer.render(template, parameters)

        assert result.success is False
        assert "Missing required parameters" in result.error_message
        assert result.missing_parameters == ["age"]

    def test_render_extra_parameters(self, renderer, template):
        """测试渲染额外参数"""
        parameters = {"name": "Alice", "age": 25, "city": "Beijing"}  # 多余参数
        result = renderer.render(template, parameters)

        assert result.success is True
        assert result.parameters_used == {"name": "Alice", "age": 25}

    def test_render_empty_template(self, renderer):
        """测试渲染空模板"""
        template = PromptTemplate(
            name="empty_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="No parameters here."
        )
        result = renderer.render(template, {})

        assert result.success is True
        assert result.content == "No parameters here."

    def test_validate_template_success(self, renderer, template):
        """测试模板验证成功"""
        errors = renderer.validate_template(template)
        assert errors == []

    def test_validate_template_empty_name(self, renderer):
        """测试模板验证空名称"""
        template = PromptTemplate(
            name="",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}!"
        )
        errors = renderer.validate_template(template)
        assert "Template name cannot be empty" in errors

    def test_validate_template_invalid_parameter(self, renderer):
        """测试模板验证无效参数"""
        template = PromptTemplate(
            name="test_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name with spaces}}!"
        )
        errors = renderer.validate_template(template)
        assert any("Invalid parameter name" in error for error in errors)