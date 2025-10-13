"""
测试Prompt管理器
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path

from src.prompts.manager import PromptManager
from src.prompts.base import PromptTemplate, PromptCategory, PromptType


class TestPromptManager:
    """测试Prompt管理器"""

    @pytest.fixture
    def manager(self):
        """管理器fixture"""
        return PromptManager()

    def test_init_loads_builtin_templates(self, manager):
        """测试初始化加载内置模板"""
        # 应该加载所有内置模板
        assert len(manager.templates) > 0

        # 检查是否有静态分析模板
        static_templates = manager.get_static_analysis_prompts()
        assert len(static_templates) >= 3

        # 检查是否有深度分析模板
        deep_templates = manager.get_deep_analysis_prompts()
        assert len(deep_templates) >= 3

        # 检查是否有修复建议模板
        repair_templates = manager.get_repair_suggestion_prompts()
        assert len(repair_templates) >= 3

    def test_register_template(self, manager):
        """测试注册模板"""
        custom_template = PromptTemplate(
            name="custom_template",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Hello {{name}}!",
            description="Custom test template"
        )

        manager.register_template(custom_template)
        assert "custom_template" in manager.templates
        retrieved = manager.get_template("custom_template")
        assert retrieved == custom_template

    def test_unregister_template(self, manager):
        """测试注销模板"""
        # 确保模板存在
        template = manager.get_template("static_analysis_main")
        assert template is not None

        # 注销模板
        result = manager.unregister_template("static_analysis_main")
        assert result is True
        assert manager.get_template("static_analysis_main") is None

        # 尝试注销不存在的模板
        result = manager.unregister_template("nonexistent")
        assert result is False

    def test_get_template(self, manager):
        """测试获取模板"""
        # 获取存在的模板
        template = manager.get_template("static_analysis_system")
        assert template is not None
        assert template.name == "static_analysis_system"

        # 获取不存在的模板
        template = manager.get_template("nonexistent")
        assert template is None

    def test_list_templates_all(self, manager):
        """测试列出所有模板"""
        all_templates = manager.list_templates()
        assert len(all_templates) > 0

        # 检查返回的都是模板对象
        for template in all_templates:
            assert isinstance(template, PromptTemplate)

    def test_list_templates_by_category(self, manager):
        """测试按类别列出模板"""
        static_templates = manager.list_templates(category=PromptCategory.STATIC_ANALYSIS)
        assert len(static_templates) >= 3

        for template in static_templates:
            assert template.category == PromptCategory.STATIC_ANALYSIS

    def test_list_templates_by_type(self, manager):
        """测试按类型列出模板"""
        user_templates = manager.list_templates(prompt_type=PromptType.USER)
        assert len(user_templates) > 0

        for template in user_templates:
            assert template.prompt_type == PromptType.USER

    def test_list_templates_by_tags(self, manager):
        """测试按标签列出模板"""
        security_templates = manager.list_templates(tags=["security"])
        assert len(security_templates) > 0

        for template in security_templates:
            assert "security" in template.tags

    def test_search_templates(self, manager):
        """测试搜索模板"""
        # 搜索包含"analysis"的模板
        results = manager.search_templates("analysis")
        assert len(results) > 0

        for template in results:
            keyword_found = (
                "analysis" in template.name.lower() or
                "analysis" in template.description.lower() or
                any("analysis" in tag.lower() for tag in template.tags)
            )
            assert keyword_found

    def test_search_templates_case_insensitive(self, manager):
        """测试搜索模板大小写不敏感"""
        results_lower = manager.search_templates("static")
        results_upper = manager.search_templates("STATIC")
        results_mixed = manager.search_templates("Static")

        # 应该返回相同的结果
        assert len(results_lower) == len(results_upper) == len(results_mixed)

    def test_render_template_success(self, manager):
        """测试渲染模板成功"""
        parameters = {
            "project_name": "Test Project",
            "language": "Python",
            "lines_of_code": "1000",
            "tool_name": "pylint",
            "summary": {
                "total_issues": 10,
                "critical_issues": 2,
                "high_issues": 3,
                "medium_issues": 3,
                "low_issues": 2
            },
            "issues": [
                {
                    "type": "Syntax Error",
                    "severity": "Critical",
                    "file": "main.py",
                    "line": 10,
                    "description": "Invalid syntax",
                    "code_snippet": "print('hello'",
                    "rule": "E0001"
                }
            ]
        }

        result = manager.render_template("static_analysis_main", parameters)

        assert result.success is True
        assert "Test Project" in result.content
        assert "Python" in result.content
        assert "pylint" in result.content
        assert result.template_name == "static_analysis_main"
        assert len(result.parameters_used) > 0

    def test_render_template_not_found(self, manager):
        """测试渲染不存在的模板"""
        result = manager.render_template("nonexistent_template", {})

        assert result.success is False
        assert "not found" in result.error_message

    def test_render_template_missing_parameters(self, manager):
        """测试渲染模板缺失参数"""
        result = manager.render_template("static_analysis_main", {})

        assert result.success is False
        assert "Missing required parameters" in result.error_message
        assert len(result.missing_parameters) > 0

    def test_validate_template_success(self, manager):
        """测试验证模板成功"""
        errors = manager.validate_template("static_analysis_system")
        assert errors == []

    def test_validate_template_not_found(self, manager):
        """测试验证不存在的模板"""
        errors = manager.validate_template("nonexistent_template")
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_set_renderer(self, manager):
        """测试设置渲染器"""
        # 设置条件渲染器
        manager.set_renderer("conditional")
        assert manager.current_renderer == "conditional"

        # 设置函数渲染器
        manager.set_renderer("function")
        assert manager.current_renderer == "function"

        # 尝试设置不存在的渲染器
        with pytest.raises(ValueError):
            manager.set_renderer("nonexistent")

    def test_add_custom_renderer(self, manager):
        """测试添加自定义渲染器"""
        from src.prompts.renderer import AdvancedPromptRenderer

        custom_renderer = AdvancedPromptRenderer()
        manager.add_custom_renderer("custom", custom_renderer)

        assert "custom" in manager.renderers
        manager.set_renderer("custom")
        assert manager.current_renderer == "custom"

    def test_get_template_parameters(self, manager):
        """测试获取模板参数"""
        parameters = manager.get_template_parameters("static_analysis_main")

        assert isinstance(parameters, dict)
        assert "project_name" in parameters
        assert "language" in parameters
        assert "issues" in parameters

    def test_get_template_parameters_not_found(self, manager):
        """测试获取不存在模板的参数"""
        parameters = manager.get_template_parameters("nonexistent")
        assert parameters == {}

    def test_export_templates_json(self, manager):
        """测试导出模板为JSON"""
        json_str = manager.export_templates(format="json")

        assert isinstance(json_str, str)
        data = json.loads(json_str)

        assert "templates" in data
        assert "metadata" in data
        assert len(data["templates"]) > 0
        assert data["metadata"]["total_count"] > 0

    def test_export_templates_yaml(self, manager):
        """测试导出模板为YAML"""
        yaml_str = manager.export_templates(format="yaml")

        assert isinstance(yaml_str, str)
        data = yaml.safe_load(yaml_str)

        assert "templates" in data
        assert "metadata" in data
        assert len(data["templates"]) > 0

    def test_export_templates_by_category(self, manager):
        """测试按类别导出模板"""
        json_str = manager.export_templates(
            format="json",
            category=PromptCategory.STATIC_ANALYSIS
        )

        data = json.loads(json_str)
        for template_data in data["templates"]:
            assert template_data["category"] == "static_analysis"

    def test_import_templates_json(self, manager):
        """测试导入JSON模板"""
        import_data = {
            "templates": [
                {
                    "name": "imported_template",
                    "category": "static_analysis",
                    "prompt_type": "user",
                    "template": "Imported template: {{param}}",
                    "description": "Imported test template",
                    "version": "1.0"
                }
            ]
        }

        json_str = json.dumps(import_data)
        imported_count = manager.import_templates(json_str, format="json")

        assert imported_count == 1
        template = manager.get_template("imported_template")
        assert template is not None
        assert template.template == "Imported template: {{param}}"

    def test_import_templates_yaml(self, manager):
        """测试导入YAML模板"""
        import_data = {
            "templates": [
                {
                    "name": "imported_yaml_template",
                    "category": "static_analysis",
                    "prompt_type": "user",
                    "template": "YAML imported template: {{param}}",
                    "description": "YAML imported test template",
                    "version": "1.0"
                }
            ]
        }

        yaml_str = yaml.dump(import_data)
        imported_count = manager.import_templates(yaml_str, format="yaml")

        assert imported_count == 1
        template = manager.get_template("imported_yaml_template")
        assert template is not None

    def test_import_templates_overwrite(self, manager):
        """测试导入模板覆盖"""
        # 先注册一个模板
        original_template = PromptTemplate(
            name="overwrite_test",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Original template",
            description="Original description"
        )
        manager.register_template(original_template)

        # 导入相同名称的模板，不覆盖
        import_data = {
            "templates": [
                {
                    "name": "overwrite_test",
                    "category": "static_analysis",
                    "prompt_type": "user",
                    "template": "New template",
                    "description": "New description",
                    "version": "1.0"
                }
            ]
        }

        json_str = json.dumps(import_data)
        imported_count = manager.import_templates(json_str, format="json", overwrite=False)

        assert imported_count == 0  # 不应该导入
        template = manager.get_template("overwrite_test")
        assert template.template == "Original template"

        # 导入相同名称的模板，覆盖
        imported_count = manager.import_templates(json_str, format="json", overwrite=True)

        assert imported_count == 1  # 应该导入
        template = manager.get_template("overwrite_test")
        assert template.template == "New template"

    def test_get_statistics(self, manager):
        """测试获取统计信息"""
        stats = manager.get_statistics()

        assert "total_templates" in stats
        assert "categories" in stats
        assert "types" in stats
        assert "top_tags" in stats
        assert "available_renderers" in stats
        assert "current_renderer" in stats

        assert stats["total_templates"] > 0
        assert len(stats["categories"]) > 0
        assert len(stats["types"]) > 0
        assert len(stats["available_renderers"]) > 0

    def test_convenience_methods(self, manager):
        """测试便捷方法"""
        # 测试便捷渲染方法
        parameters = {
            "project_name": "Test Project",
            "language": "Python",
            "lines_of_code": "1000",
            "tool_name": "pylint",
            "summary": {
                "total_issues": 10,
                "critical_issues": 2,
                "high_issues": 3,
                "medium_issues": 3,
                "low_issues": 2
            },
            "issues": []
        }

        # 测试静态分析渲染
        result = manager.render_static_analysis(parameters)
        assert result.success is True

        # 测试深度分析渲染
        deep_params = {
            "file_path": "test.py",
            "function_name": "test_func",
            "language": "Python",
            "code_lines": 20,
            "code_content": "def test_func(): pass"
        }
        result = manager.render_deep_analysis(deep_params)
        assert result.success is True

        # 测试修复建议渲染
        repair_params = {
            "defect_type": "Syntax Error",
            "severity": "Critical",
            "file_path": "test.py",
            "line_number": 10,
            "description": "Invalid syntax",
            "language": "Python",
            "problematic_code": "print('hello'",
            "context_code": "def main():\n    print('hello'"
        }
        result = manager.render_repair_suggestion(repair_params)
        assert result.success is True


class TestPromptManagerWithConfig:
    """测试带配置文件的Prompt管理器"""

    @pytest.fixture
    def config_file(self):
        """配置文件fixture"""
        config_data = {
            "templates": [
                {
                    "name": "config_template",
                    "category": "static_analysis",
                    "prompt_type": "user",
                    "template": "Config template: {{param}}",
                    "description": "Template from config file",
                    "version": "1.0",
                    "tags": ["config", "test"]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        yield temp_file
        Path(temp_file).unlink()  # 清理

    def test_init_with_config_file(self, config_file):
        """测试使用配置文件初始化"""
        manager = PromptManager(config_path=config_file)

        # 应该加载内置模板和配置文件中的模板
        assert len(manager.templates) > 0
        assert "config_template" in manager.templates

        config_template = manager.get_template("config_template")
        assert config_template.template == "Config template: {{param}}"
        assert "config" in config_template.tags
        assert "test" in config_template.tags

    def test_init_with_nonexistent_config_file(self):
        """测试使用不存在的配置文件初始化"""
        # 不应该抛出异常，只是记录警告
        manager = PromptManager(config_path="/nonexistent/file.json")
        # 应该只加载内置模板
        assert len(manager.templates) > 0
        assert len(manager.get_static_analysis_prompts()) >= 3

    @pytest.fixture
    def yaml_config_file(self):
        """YAML配置文件fixture"""
        config_data = {
            "templates": [
                {
                    "name": "yaml_config_template",
                    "category": "deep_analysis",
                    "prompt_type": "user",
                    "template": "YAML config template: {{param}}",
                    "description": "Template from YAML config file",
                    "version": "1.0",
                    "tags": ["yaml", "config"]
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            temp_file = f.name

        yield temp_file
        Path(temp_file).unlink()  # 清理

    def test_init_with_yaml_config_file(self, yaml_config_file):
        """测试使用YAML配置文件初始化"""
        manager = PromptManager(config_path=yaml_config_file)

        assert "yaml_config_template" in manager.templates
        template = manager.get_template("yaml_config_template")
        assert template.category == PromptCategory.DEEP_ANALYSIS
        assert template.template == "YAML config template: {{param}}"