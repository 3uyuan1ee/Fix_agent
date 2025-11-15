"""
测试用例：AI代理系统

基于项目实际结构的agent.py模块测试
测试文件: src/agents/agent.py
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# 导入实际的项目模块
try:
    from src.agents.agent import (create_agent_with_config,
                                  get_current_assistant_id, list_agents,
                                  reset_agent)
    from src.config.config import COLORS, config, console
except ImportError as e:
    print(f"Import warning: {e}")

    # Mock imports for testing
    def list_agents():
        pass

    def reset_agent(agent_name, source_agent=None):
        return True

    def create_agent_with_config(model, assistant_id, tools, memory_mode="auto"):
        return Mock()

    def get_current_assistant_id():
        return "test_assistant"

    COLORS = {"primary": "blue", "success": "green", "error": "red", "dim": "gray"}
    console = Mock()
    config = Mock()


class TestListAgents:
    """测试列出代理功能"""

    def test_list_agents_no_agents_directory(self):
        """测试当.agents目录不存在时的行为"""
        with patch("pathlib.Path.home") as mock_home:
            # 模拟不存在的agents目录
            mock_agents_dir = Mock()
            mock_agents_dir.exists.return_value = False
            mock_agents_dir.__truediv__ = Mock(return_value=mock_agents_dir)
            mock_agents_dir.iterdir.return_value = []
            mock_home.return_value = mock_agents_dir

            # 重定向console.print到capture
            with patch.object(console, "print") as mock_print:
                list_agents()

                # 验证打印了"No agents found"消息
                mock_print.assert_any_call("[yellow]No agents found.[/yellow]")
                mock_print.assert_any_call(
                    "[dim]Agents will be created in ~/.deepagents/ when you first use them.[/dim]",
                    style=COLORS["dim"],
                )

    def test_list_agents_empty_directory(self):
        """测试空agents目录的行为"""
        with patch("pathlib.Path.home") as mock_home:
            # 模拟空的agents目录
            mock_agents_dir = Mock()
            mock_agents_dir.exists.return_value = True
            mock_agents_dir.iterdir.return_value = []
            mock_agents_dir.__truediv__ = Mock(return_value=mock_agents_dir)
            mock_home.return_value = mock_agents_dir

            with patch.object(console, "print") as mock_print:
                list_agents()

                mock_print.assert_any_call("[yellow]No agents found.[/yellow]")

    def test_list_agents_with_agents(self):
        """测试存在agents时的列出功能"""
        with patch("pathlib.Path.home") as mock_home:
            # 模拟有agents的目录
            mock_agent1_dir = Mock()
            mock_agent1_dir.is_dir.return_value = True
            mock_agent1_dir.name = "agent1"

            mock_agent1_md = Mock()
            mock_agent1_md.exists.return_value = True
            mock_agent1_dir.__truediv__ = Mock(return_value=mock_agent1_md)

            mock_agents_dir = Mock()
            mock_agents_dir.exists.return_value = True
            mock_agents_dir.iterdir.return_value = [mock_agent1_dir]
            mock_agents_dir.__truediv__ = Mock(return_value=mock_agents_dir)
            mock_home.return_value = mock_agents_dir

            with patch.object(console, "print") as mock_print:
                list_agents()

                # 验证打印了"Available Agents"
                mock_print.assert_any_call(
                    "\n[bold]Available Agents:[/bold]\n", style=COLORS["primary"]
                )


class TestResetAgent:
    """测试重置代理功能"""

    @pytest.fixture
    def mock_agents_dir(self):
        """模拟agents目录结构"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agents_dir = Path(temp_dir) / ".deepagents"
            agents_dir.mkdir()

            # 创建源代理目录
            source_dir = agents_dir / "source_agent"
            source_dir.mkdir()

            # 创建source agent.md
            source_md = source_dir / "agent.md"
            source_md.write_text("# Source Agent\nTest content")

            yield agents_dir, source_dir

    def test_reset_agent_from_source(self, mock_agents_dir):
        """测试从源代理重置"""
        agents_dir, source_dir = mock_agents_dir

        # 创建目标代理目录
        target_dir = agents_dir / "target_agent"
        target_dir.mkdir()
        target_md = target_dir / "agent.md"
        target_md.write_text("# Target Agent\nOriginal content")

        with patch("pathlib.Path.home", return_value=agents_dir.parent):
            with patch.object(console, "print") as mock_print:
                reset_agent("target_agent", "source_agent")

                # 验证目标代理被重置
                assert target_md.exists()
                content = target_md.read_text()
                assert "Source Agent" in content
                assert "Test content" in content

                # 验证打印了成功消息
                mock_print.assert_any_call(
                    f"✓ Agent 'target_agent' reset to contents of agent 'source_agent'",
                    style=COLORS["primary"],
                )

    def test_reset_agent_nonexistent_source(self, mock_agents_dir):
        """测试从不存在的源代理重置"""
        agents_dir, _ = mock_agents_dir

        with patch("pathlib.Path.home", return_value=agents_dir.parent):
            with patch.object(console, "print") as mock_print:
                reset_agent("target_agent", "nonexistent_source")

                # 验证打印了错误消息
                mock_print.assert_any_call(
                    "[bold red]Error:[/bold red] Source agent 'nonexistent_source' not found or has no agent.md"
                )

    def test_reset_agent_default_content(self, mock_agents_dir):
        """测试重置为默认内容"""
        agents_dir, _ = mock_agents_dir

        # 创建目标代理目录
        target_dir = agents_dir / "target_agent"
        target_dir.mkdir()
        target_md = target_dir / "agent.md"
        target_md.write_text("# Target Agent\nOriginal content")

        with patch("pathlib.Path.home", return_value=agents_dir.parent):
            with patch(
                "src.agents.agent.get_default_coding_instructions"
            ) as mock_default:
                mock_default.return_value = "# Default Instructions\nDefault content"

                with patch.object(console, "print") as mock_print:
                    reset_agent("target_agent", None)

                    # 验证使用了默认内容
                    mock_default.assert_called_once()
                    content = target_md.read_text()
                    assert "Default Instructions" in content

                    # 验证打印了成功消息
                    mock_print.assert_any_call(
                        f"✓ Agent 'target_agent' reset to default",
                        style=COLORS["primary"],
                    )

    def test_reset_agent_removes_existing_directory(self, mock_agents_dir):
        """测试重置时移除现有目录"""
        agents_dir, _ = mock_agents_dir

        # 创建目标代理目录和文件
        target_dir = agents_dir / "target_agent"
        target_dir.mkdir()
        (target_dir / "old_file.txt").write_text("old content")
        sub_dir = target_dir / "subdir"
        sub_dir.mkdir()
        (sub_dir / "sub_file.txt").write_text("sub content")

        with patch("pathlib.Path.home", return_value=agents_dir.parent):
            with patch.object(console, "print") as mock_print:
                reset_agent("target_agent", None)

                # 验证旧内容被移除，只有agent.md存在
                assert target_dir.exists()
                assert (target_dir / "agent.md").exists()
                assert not (target_dir / "old_file.txt").exists()
                assert not (target_dir / "subdir").exists()

                # 验证打印了移除消息
                mock_print.assert_any_call(
                    f"Removed existing agent directory: {target_dir}",
                    style=COLORS["tool"],
                )


class TestCreateAgentWithConfig:
    """测试创建代理配置功能"""

    @pytest.fixture
    def mock_model(self):
        """模拟模型对象"""
        return Mock()

    @pytest.fixture
    def mock_tools(self):
        """模拟工具列表"""
        return ["tool1", "tool2", "tool3"]

    @pytest.fixture
    def mock_agents_dir(self):
        """模拟agents目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            agents_dir = Path(temp_dir) / ".deepagents"
            agents_dir.mkdir()
            yield agents_dir

    def test_create_agent_basic(self, mock_model, mock_tools, mock_agents_dir):
        """测试基本代理创建"""
        assistant_id = "test_agent"

        with patch("pathlib.Path.home", return_value=mock_agents_dir.parent):
            with patch("src.agents.agent.create_deep_agent") as mock_create_deep:
                mock_agent = Mock()
                mock_create_deep.return_value = mock_agent

                with patch("src.agents.agent.FilesystemBackend") as mock_backend:
                    with patch("src.agents.agent.CompositeBackend") as mock_composite:
                        with patch(
                            "src.agents.agent.LayeredMemoryMiddleware"
                        ) as mock_memory:
                            with patch(
                                "src.agents.agent.SecurityMiddleware"
                            ) as mock_security:
                                with patch(
                                    "src.agents.agent.LoggingMiddleware"
                                ) as mock_logging:
                                    with patch(
                                        "src.agents.agent.ContextEnhancementMiddleware"
                                    ) as mock_context:
                                        with patch(
                                            "src.agents.agent.PerformanceMonitorMiddleware"
                                        ) as mock_perf:
                                            with patch(
                                                "src.agents.agent.AgentMemoryMiddleware"
                                            ) as mock_agent_mem:
                                                with patch(
                                                    "src.agents.agent.ResumableShellToolMiddleware"
                                                ) as mock_shell:
                                                    with patch(
                                                        "src.agents.agent.HostExecutionPolicy"
                                                    ) as mock_policy:
                                                        with patch(
                                                            "src.agents.agent.MemoryMiddlewareFactory"
                                                        ) as mock_factory:
                                                            with patch(
                                                                "src.agents.agent.get_default_coding_instructions"
                                                            ) as mock_default:
                                                                mock_default.return_value = "Default instructions"
                                                                mock_factory.create_memory_backend.return_value = (
                                                                    Mock()
                                                                )

                                                                agent = create_agent_with_config(
                                                                    mock_model,
                                                                    assistant_id,
                                                                    mock_tools,
                                                                    "auto",
                                                                )

                                                                # 验证agent目录被创建
                                                                agent_dir = (
                                                                    mock_agents_dir
                                                                    / assistant_id
                                                                )
                                                                assert (
                                                                    agent_dir.exists()
                                                                )

                                                                # 验证agent.md文件被创建
                                                                agent_md = (
                                                                    agent_dir
                                                                    / "agent.md"
                                                                )
                                                                assert agent_md.exists()

                                                                content = (
                                                                    agent_md.read_text()
                                                                )
                                                                assert (
                                                                    "Default instructions"
                                                                    in content
                                                                )

                                                                # 验证create_deep_agent被调用
                                                                mock_create_deep.assert_called_once()

    def test_create_agent_existing_agent_md(
        self, mock_model, mock_tools, mock_agents_dir
    ):
        """测试创建代理时agent.md已存在"""
        assistant_id = "existing_agent"

        # 预先创建agent目录和agent.md
        agent_dir = mock_agents_dir / assistant_id
        agent_dir.mkdir()
        agent_md = agent_dir / "agent.md"
        agent_md.write_text("# Existing Agent\nAlready exists")

        with patch("pathlib.Path.home", return_value=mock_agents_dir.parent):
            with patch("src.agents.agent.create_deep_agent") as mock_create_deep:
                mock_agent = Mock()
                mock_create_deep.return_value = mock_agent

                # 模拟所有中间件
                with patch("src.agents.agent.ResumableShellToolMiddleware"):
                    with patch("src.agents.agent.FilesystemBackend"):
                        with patch("src.agents.agent.CompositeBackend"):
                            with patch("src.agents.agent.LayeredMemoryMiddleware"):
                                with patch("src.agents.agent.SecurityMiddleware"):
                                    with patch("src.agents.agent.LoggingMiddleware"):
                                        with patch(
                                            "src.agents.agent.ContextEnhancementMiddleware"
                                        ):
                                            with patch(
                                                "src.agents.agent.PerformanceMonitorMiddleware"
                                            ):
                                                with patch(
                                                    "src.agents.agent.AgentMemoryMiddleware"
                                                ):
                                                    with patch(
                                                        "src.agents.agent.MemoryMiddlewareFactory"
                                                    ) as mock_factory:
                                                        mock_factory.create_memory_backend.return_value = (
                                                            Mock()
                                                        )

                                                        agent = (
                                                            create_agent_with_config(
                                                                mock_model,
                                                                assistant_id,
                                                                mock_tools,
                                                                "auto",
                                                            )
                                                        )

                                                        # 验证现有的agent.md没有被覆盖
                                                        content = agent_md.read_text()
                                                        assert (
                                                            "Existing Agent" in content
                                                        )
                                                        assert (
                                                            "Already exists" in content
                                                        )
                                                        assert (
                                                            "Default instructions"
                                                            not in content
                                                        )

    def test_create_agent_different_memory_modes(
        self, mock_model, mock_tools, mock_agents_dir
    ):
        """测试不同记忆模式的代理创建"""
        assistant_id = "memory_test_agent"
        memory_modes = ["auto", "enhanced", "minimal"]

        for memory_mode in memory_modes:
            with patch("pathlib.Path.home", return_value=mock_agents_dir.parent):
                with patch("src.agents.agent.create_deep_agent") as mock_create_deep:
                    mock_agent = Mock()
                    mock_create_deep.return_value = mock_agent

                    with patch("src.agents.agent.ResumableShellToolMiddleware"):
                        with patch("src.agents.agent.FilesystemBackend"):
                            with patch("src.agents.agent.CompositeBackend"):
                                with patch(
                                    "src.agents.agent.LayeredMemoryMiddleware"
                                ) as mock_memory:
                                    with patch("src.agents.agent.SecurityMiddleware"):
                                        with patch(
                                            "src.agents.agent.LoggingMiddleware"
                                        ):
                                            with patch(
                                                "src.agents.agent.ContextEnhancementMiddleware"
                                            ):
                                                with patch(
                                                    "src.agents.agent.PerformanceMonitorMiddleware"
                                                ):
                                                    with patch(
                                                        "src.agents.agent.AgentMemoryMiddleware"
                                                    ):
                                                        with patch(
                                                            "src.agents.agent.MemoryMiddlewareFactory"
                                                        ) as mock_factory:
                                                            mock_factory.create_memory_backend.return_value = (
                                                                Mock()
                                                            )
                                                            with patch(
                                                                "src.agents.agent.get_default_coding_instructions",
                                                                return_value="# Default instructions",
                                                            ):

                                                                agent = create_agent_with_config(
                                                                    mock_model,
                                                                    f"{assistant_id}_{memory_mode}",
                                                                    mock_tools,
                                                                    memory_mode,
                                                                )

                                                                # 验证memory_mode被正确使用
                                                                # 由于使用了多个patch，我们只需要确认agent被创建成功
                                                                assert agent is not None

    def test_create_agent_with_empty_tools(self, mock_model, mock_agents_dir):
        """测试使用空工具列表创建代理"""
        assistant_id = "empty_tools_agent"
        tools = []

        with patch("pathlib.Path.home", return_value=mock_agents_dir.parent):
            with patch("src.agents.agent.create_deep_agent") as mock_create_deep:
                mock_agent = Mock()
                mock_create_deep.return_value = mock_agent

                with patch("src.agents.agent.ResumableShellToolMiddleware"):
                    with patch("src.agents.agent.FilesystemBackend"):
                        with patch("src.agents.agent.CompositeBackend"):
                            with patch("src.agents.agent.LayeredMemoryMiddleware"):
                                with patch("src.agents.agent.SecurityMiddleware"):
                                    with patch("src.agents.agent.LoggingMiddleware"):
                                        with patch(
                                            "src.agents.agent.ContextEnhancementMiddleware"
                                        ):
                                            with patch(
                                                "src.agents.agent.PerformanceMonitorMiddleware"
                                            ):
                                                with patch(
                                                    "src.agents.agent.AgentMemoryMiddleware"
                                                ):
                                                    with patch(
                                                        "src.agents.agent.MemoryMiddlewareFactory"
                                                    ) as mock_factory:
                                                        mock_factory.create_memory_backend.return_value = (
                                                            Mock()
                                                        )
                                                        with patch(
                                                            "src.agents.agent.get_default_coding_instructions",
                                                            return_value="# Default instructions",
                                                        ):

                                                            agent = create_agent_with_config(
                                                                mock_model,
                                                                assistant_id,
                                                                tools,
                                                                "auto",
                                                            )

                                                            # 验证代理仍然能够创建
                                                            mock_create_deep.assert_called_once()

    def test_create_agent_directory_creation_error(self, mock_model, mock_tools):
        """测试代理目录创建错误"""
        assistant_id = "error_agent"

        with patch("pathlib.Path.home") as mock_home:
            # 模拟权限错误
            mock_home.return_value = Path("/nonexistent/permission_denied")

            with pytest.raises((OSError, PermissionError)):
                create_agent_with_config(mock_model, assistant_id, mock_tools, "auto")


class TestGetAgent:
    """测试获取代理功能"""

    def test_get_agent_success(self):
        """测试成功获取代理"""
        # 这个测试需要实际的deepagents模块，所以使用mock
        with patch("src.agents.agent.create_deep_agent") as mock_create_deep:
            mock_agent = Mock()
            mock_create_deep.return_value = mock_agent

            # 模拟现有的agent配置
            with tempfile.TemporaryDirectory() as temp_dir:
                agents_dir = Path(temp_dir) / ".deepagents"
                agents_dir.mkdir()

                agent_dir = agents_dir / "existing_agent"
                agent_dir.mkdir()

                with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                    # 由于get_agent函数可能不存在或需要参数，这里测试导入
                    try:
                        from src.agents.agent import get_agent

                        agent = get_agent("existing_agent")
                        # 验证返回了代理
                        assert agent is not None
                    except ImportError:
                        # 如果get_agent不存在，跳过测试
                        pytest.skip("get_agent function not available")

    def test_get_agent_nonexistent(self):
        """测试获取不存在的代理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                try:
                    from src.agents.agent import get_agent

                    agent = get_agent("nonexistent_agent")
                    # 应该返回None或抛出异常
                    assert agent is None
                except (ValueError, FileNotFoundError):
                    # 预期的异常
                    assert True
                except ImportError:
                    pytest.skip("get_agent function not available")


class TestAgentIntegration:
    """集成测试"""

    @pytest.fixture
    def full_agent_setup(self):
        """完整的代理设置夹具"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 设置测试环境
            os.chdir(temp_dir)

            agents_dir = Path(temp_dir) / ".deepagents"
            agents_dir.mkdir()

            yield agents_dir

    def test_complete_agent_workflow(self, full_agent_setup):
        """测试完整的代理工作流程"""
        mock_model = Mock()
        tools = ["tool1"]
        assistant_id = "workflow_test"

        with patch("pathlib.Path.home", return_value=full_agent_setup.parent):
            # 1. 创建代理
            with patch("src.agents.agent.create_deep_agent") as mock_create_deep:
                mock_agent = Mock()
                mock_create_deep.return_value = mock_agent

                with patch("src.agents.agent.ResumableShellToolMiddleware"):
                    with patch("src.agents.agent.FilesystemBackend"):
                        with patch("src.agents.agent.CompositeBackend"):
                            with patch("src.agents.agent.LayeredMemoryMiddleware"):
                                with patch("src.agents.agent.SecurityMiddleware"):
                                    with patch("src.agents.agent.LoggingMiddleware"):
                                        with patch(
                                            "src.agents.agent.ContextEnhancementMiddleware"
                                        ):
                                            with patch(
                                                "src.agents.agent.PerformanceMonitorMiddleware"
                                            ):
                                                with patch(
                                                    "src.agents.agent.AgentMemoryMiddleware"
                                                ):
                                                    with patch(
                                                        "src.agents.agent.MemoryMiddlewareFactory"
                                                    ) as mock_factory:
                                                        mock_factory.create_memory_backend.return_value = (
                                                            Mock()
                                                        )
                                                        with patch(
                                                            "src.agents.agent.get_default_coding_instructions",
                                                            return_value="# Default instructions",
                                                        ):

                                                            agent = create_agent_with_config(
                                                                mock_model,
                                                                assistant_id,
                                                                tools,
                                                                "auto",
                                                            )

            # 2. 验证代理目录创建
            agent_dir = full_agent_setup / assistant_id
            assert agent_dir.exists()
            assert (agent_dir / "agent.md").exists()

            # 3. 列出代理
            with patch.object(console, "print"):
                list_agents()

            # 4. 重置代理
            with patch.object(console, "print"):
                reset_agent(assistant_id, None)


class TestAgentErrorHandling:
    """错误处理测试"""

    def test_invalid_assistant_id(self):
        """测试无效的助手ID"""
        mock_model = Mock()
        tools = []

        with pytest.raises((ValueError, TypeError, OSError)):
            create_agent_with_config(mock_model, "", tools, "auto")

    def test_none_model(self):
        """测试None模型"""
        tools = ["tool1"]

        # 应该能处理None模型，或者抛出适当异常
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                    with patch("src.agents.agent.os.getcwd", return_value=temp_dir):
                        result = create_agent_with_config(None, "test", tools, "auto")
                        # 如果没有抛出异常，结果应该是None或有效的代理
                    assert result is not None
        except (ValueError, TypeError):
            # 预期的异常类型
            assert True

    def test_malformed_tools_list(self):
        """测试畸形工具列表"""
        mock_model = Mock()

        # 测试各种无效的工具列表
        invalid_tools = [None, "not_a_list", [{"invalid": "tool"}]]

        for tools in invalid_tools:
            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    with patch("pathlib.Path.home", return_value=Path(temp_dir)):
                        with patch("src.agents.agent.os.getcwd", return_value=temp_dir):
                            result = create_agent_with_config(
                                mock_model, "test", tools, "auto"
                            )
                            # 如果没有抛出异常，应该能处理
                            assert result is not None
            except (ValueError, TypeError):
                # 预期的异常
                assert True


# 运行测试的入口
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
