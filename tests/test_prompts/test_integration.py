"""
Prompt管理系统集成测试
"""

import pytest
from src.prompts.manager import PromptManager
from src.prompts.base import PromptCategory, PromptType
from src.prompts.renderer import ConditionalPromptRenderer, TemplateFunctionRenderer


class TestPromptManagerIntegration:
    """Prompt管理器集成测试"""

    @pytest.fixture
    def manager(self):
        """管理器fixture"""
        return PromptManager()

    def test_complete_static_analysis_workflow(self, manager):
        """测试完整的静态分析工作流程"""
        # 1. 获取静态分析系统提示
        system_template = manager.get_template("static_analysis_system")
        assert system_template is not None
        assert system_template.prompt_type == PromptType.SYSTEM

        # 2. 获取静态分析主提示
        main_template = manager.get_template("static_analysis_main")
        assert main_template is not None
        assert main_template.prompt_type == PromptType.USER

        # 3. 准备分析数据
        analysis_data = {
            "project_name": "WebApp Project",
            "language": "Python",
            "lines_of_code": "5000",
            "tool_name": "pylint",
            "summary": {
                "total_issues": 15,
                "critical_issues": 3,
                "high_issues": 5,
                "medium_issues": 5,
                "low_issues": 2
            },
            "issues": [
                {
                    "type": "Import Error",
                    "severity": "Critical",
                    "file": "main.py",
                    "line": 5,
                    "description": "Module not found",
                    "code_snippet": "import non_existent_module",
                    "rule": "E0401"
                },
                {
                    "type": "Undefined Variable",
                    "severity": "High",
                    "file": "utils.py",
                    "line": 25,
                    "description": "Undefined variable 'user_data'",
                    "code_snippet": "print(user_data)",
                    "rule": "E0602"
                }
            ]
        }

        # 4. 渲染主分析提示
        result = manager.render_template("static_analysis_main", analysis_data)
        assert result.success is True
        assert "WebApp Project" in result.content
        assert "Python" in result.content
        assert "Import Error" in result.content
        assert "Undefined Variable" in result.content

        # 5. 获取并渲染总结提示
        summary_data = {
            "total_defects": 15,
            "critical_defects": 3,
            "high_defects": 5,
            "false_positives": 2,
            "top_defects": [
                {
                    "type": "Import Error",
                    "file": "main.py",
                    "line": 5,
                    "description": "Module not found"
                },
                {
                    "type": "Undefined Variable",
                    "file": "utils.py",
                    "line": 25,
                    "description": "Undefined variable"
                }
            ],
            "overall_assessment": "Overall code quality is moderate with several critical issues"
        }

        summary_result = manager.render_template("static_analysis_summary", summary_data)
        assert summary_result.success is True
        assert "15" in summary_result.content
        assert "Import Error" in summary_result.content

    def test_complete_deep_analysis_workflow(self, manager):
        """测试完整的深度分析工作流程"""
        # 1. 获取深度分析系统提示
        system_template = manager.get_template("deep_analysis_system")
        assert system_template is not None

        # 2. 准备代码分析数据
        code_data = {
            "file_path": "src/auth/user_manager.py",
            "function_name": "authenticate_user",
            "language": "Python",
            "code_lines": 45,
            "code_content": '''def authenticate_user(username, password):
    conn = get_db_connection()
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor = conn.execute(query)
    user = cursor.fetchone()
    conn.close()
    return user''',
            "dependencies": [
                {"name": "sqlite3", "version": "3.36.0"},
                {"name": "flask", "version": "2.0.1"}
            ],
            "usage_context": "Web application authentication endpoint"
        }

        # 3. 渲染代码分析提示
        result = manager.render_template("deep_code_analysis", code_data)
        assert result.success is True
        assert "user_manager.py" in result.content
        assert "authenticate_user" in result.content
        assert "Python" in result.content

    def test_complete_repair_suggestion_workflow(self, manager):
        """测试完整的修复建议工作流程"""
        # 1. 获取修复建议系统提示
        system_template = manager.get_template("repair_suggestion_system")
        assert system_template is not None

        # 2. 准备缺陷数据
        defect_data = {
            "defect_type": "SQL Injection",
            "severity": "Critical",
            "file_path": "src/auth/user_manager.py",
            "line_number": 15,
            "description": "SQL injection vulnerability in authentication query",
            "language": "Python",
            "problematic_code": '''query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"''',
            "context_code": '''def authenticate_user(username, password):
    conn = get_db_connection()
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor = conn.execute(query)
    user = cursor.fetchone()
    conn.close()
    return user''',
            "constraints": [
                {"type": "functional", "description": "Must maintain backward compatibility"},
                {"type": "performance", "description": "Should not impact query performance"}
            ],
            "multiple_solutions": False,
            "fix_code": '''query = "SELECT * FROM users WHERE username = ? AND password = ?"
cursor.execute(query, (username, password))''',
            "fix_explanation": "Use parameterized queries to prevent SQL injection"
        }

        # 3. 渲染修复建议提示
        result = manager.render_template("defect_fix_suggestion", defect_data)
        assert result.success is True
        assert "SQL Injection" in result.content
        assert "Critical" in result.content
        assert "user_manager.py" in result.content

    def test_conditional_renderer_integration(self, manager):
        """测试条件渲染器集成"""
        # 设置条件渲染器
        manager.set_renderer("conditional")

        # 准备带条件的数据
        data = {
            "show_details": True,
            "user_type": "admin",
            "permissions": ["read", "write", "delete"],
            "profile": {
                "name": "Alice",
                "role": "Administrator",
                "department": "IT"
            }
        }

        # 创建自定义模板测试条件渲染
        custom_template = manager.get_template("static_analysis_main")

        # 渲染模板
        result = manager.render_template("static_analysis_main", data)
        assert result.success is True

    def test_function_renderer_integration(self, manager):
        """测试函数渲染器集成"""
        # 设置函数渲染器
        manager.set_renderer("function")

        # 添加自定义函数
        def custom_function(text):
            return f"[CUSTOM]{text}[/CUSTOM]"

        manager.add_custom_renderer("function").add_function("custom", custom_function)
        manager.set_renderer("function")

        # 创建测试模板
        from src.prompts.base import PromptTemplate
        test_template = PromptTemplate(
            name="function_test",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="Processing: {{custom:text}} and {{upper:status}}",
            description="Function renderer test"
        )
        manager.register_template(test_template)

        # 渲染模板
        result = manager.render_template("function_test", {"text": "test", "status": "active"})
        assert result.success is True
        assert "[CUSTOM]test[/CUSTOM]" in result.content
        assert "ACTIVE" in result.content

    def test_template_search_and_render(self, manager):
        """测试模板搜索和渲染组合"""
        # 搜索安全相关模板
        security_templates = manager.search_templates("security")
        assert len(security_templates) > 0

        # 对找到的模板进行渲染测试
        for template in security_templates:
            if template.has_parameters():
                # 创建基本参数
                parameters = {}
                for param in template.get_required_parameters():
                    if param == "project_name":
                        parameters[param] = "Test Project"
                    elif param == "language":
                        parameters[param] = "Python"
                    else:
                        parameters[param] = f"test_{param}"

                # 尝试渲染
                result = manager.render_template(template.name, parameters)
                # 可能会失败，因为不同模板需要不同的参数结构

    def test_template_export_import_cycle(self, manager):
        """测试模板导出导入循环"""
        # 导出所有模板
        json_export = manager.export_templates(format="json")
        assert len(json_export) > 0

        # 创建新的管理器实例
        new_manager = PromptManager()

        # 清空内置模板（模拟只使用导入的模板）
        new_manager.templates.clear()

        # 导入模板
        imported_count = new_manager.import_templates(json_export, format="json", overwrite=True)
        assert imported_count > 0

        # 验证导入的模板
        assert len(new_manager.templates) > 0
        assert new_manager.get_template("static_analysis_system") is not None

    def test_error_handling_and_recovery(self, manager):
        """测试错误处理和恢复"""
        # 测试不存在的模板
        result = manager.render_template("nonexistent", {})
        assert not result.success
        assert "not found" in result.error_message

        # 测试参数不足
        result = manager.render_template("static_analysis_main", {})
        assert not result.success
        assert "Missing required parameters" in result.error_message
        assert len(result.missing_parameters) > 0

        # 测试模板验证错误
        errors = manager.validate_template("nonexistent")
        assert len(errors) > 0
        assert "not found" in errors[0]

    def test_performance_with_large_data(self, manager):
        """测试大数据量性能"""
        # 创建大量问题数据
        large_issues_list = []
        for i in range(100):
            large_issues_list.append({
                "type": f"Issue Type {i}",
                "severity": "Medium",
                "file": f"file_{i}.py",
                "line": i + 1,
                "description": f"Description for issue {i}",
                "code_snippet": f"code_line_{i}",
                "rule": f"E{4000 + i}"
            })

        large_data = {
            "project_name": "Large Project",
            "language": "Python",
            "lines_of_code": "100000",
            "tool_name": "comprehensive_tool",
            "summary": {
                "total_issues": len(large_issues_list),
                "critical_issues": 10,
                "high_issues": 20,
                "medium_issues": 40,
                "low_issues": 30
            },
            "issues": large_issues_list
        }

        # 测试渲染性能
        import time
        start_time = time.time()
        result = manager.render_template("static_analysis_main", large_data)
        render_time = time.time() - start_time

        assert result.success is True
        assert render_time < 5.0  # 应该在5秒内完成
        assert len(result.content) > 1000  # 内容应该很长

    def test_multilingual_template_support(self, manager):
        """测试多语言模板支持"""
        # 测试不同编程语言的模板渲染
        languages = ["Python", "JavaScript", "Java", "C++", "Go"]

        for lang in languages:
            data = {
                "project_name": f"{lang} Project",
                "language": lang,
                "lines_of_code": "1000",
                "tool_name": f"{lang.lower()}_linter",
                "summary": {
                    "total_issues": 5,
                    "critical_issues": 1,
                    "high_issues": 1,
                    "medium_issues": 2,
                    "low_issues": 1
                },
                "issues": [{
                    "type": "Style Issue",
                    "severity": "Medium",
                    "file": f"main.{lang.lower().replace('++', 'pp')}",
                    "line": 10,
                    "description": f"Code style issue in {lang}",
                    "code_snippet": f"sample {lang} code",
                    "rule": "S0001"
                }]
            }

            result = manager.render_template("static_analysis_main", data)
            assert result.success is True
            assert lang in result.content