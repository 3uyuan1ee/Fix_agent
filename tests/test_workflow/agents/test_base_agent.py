"""
DeepAgents Base Agent 测试用例

测试基类框架的核心功能和各种代理类型
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# 添加项目路径到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_agent import (
    AgentConfig,
    AgentType,
    BaseAgent,
    CoordinatorAgent,
    DeveloperAgent,
    ResearchAgent,
    create_coordinator_agent,
    create_developer_agent,
    create_research_agent,
)


class TestAgentConfig(unittest.TestCase):
    """测试AgentConfig配置类"""

    def test_agent_config_creation(self):
        """测试配置创建"""
        config = AgentConfig(
            name="test-agent",
            agent_type=AgentType.RESEARCHER,
            description="测试代理",
            system_prompt="测试提示",
        )

        self.assertEqual(config.name, "test-agent")
        self.assertEqual(config.agent_type, AgentType.RESEARCHER)
        self.assertEqual(config.description, "测试代理")
        self.assertEqual(config.system_prompt, "测试提示")
        self.assertEqual(config.temperature, 0.1)
        self.assertEqual(config.max_tokens, 20000)

    def test_agent_config_custom_values(self):
        """测试自定义配置值"""
        config = AgentConfig(
            name="custom-agent",
            agent_type=AgentType.DEVELOPER,
            description="自定义代理",
            system_prompt="自定义提示",
            temperature=0.5,
            max_tokens=1000,
            debug=True,
        )

        self.assertEqual(config.temperature, 0.5)
        self.assertEqual(config.max_tokens, 1000)
        self.assertTrue(config.debug)


class TestBaseAgent(unittest.TestCase):
    """测试BaseAgent基类"""

    def setUp(self):
        """设置测试环境"""
        self.config = AgentConfig(
            name="test-base-agent",
            agent_type=AgentType.CUSTOM,
            description="测试基类代理",
            system_prompt="测试基类提示",
        )

    def test_base_agent_initialization(self):
        """测试基类初始化"""

        class TestAgent(BaseAgent):
            def _build_custom(self):
                pass

        agent = TestAgent(self.config)
        self.assertEqual(agent.config, self.config)
        self.assertIsNotNone(agent._logger)
        self.assertIsNone(agent._agent)

    def test_base_agent_build_without_custom_build(self):
        """测试未实现_build_custom的代理"""

        class IncompleteAgent(BaseAgent):
            pass

        # 应该在实例化时就失败，因为抽象方法未实现
        with self.assertRaises(TypeError):
            agent = IncompleteAgent(self.config)

    @patch("base_agent.create_deep_agent")
    def test_base_agent_build_success(self, mock_create_deep_agent):
        """测试代理构建成功"""

        class TestAgent(BaseAgent):
            def _build_custom(self):
                pass

        # 创建mock对象链 - create_deep_agent返回的对象需要支持with_config方法
        mock_intermediate_agent = Mock()  # create_deep_agent返回的对象
        mock_final_agent = Mock()  # with_config返回的最终对象
        mock_intermediate_agent.with_config.return_value = mock_final_agent
        mock_create_deep_agent.return_value = mock_intermediate_agent

        agent = TestAgent(self.config)
        result = agent.build()

        self.assertEqual(result, agent)
        self.assertEqual(agent._agent, mock_final_agent)
        mock_create_deep_agent.assert_called_once()
        mock_intermediate_agent.with_config.assert_called_once_with(
            {"recursion_limit": 1000}
        )

    def test_base_agent_not_built_error(self):
        """测试未构建代理的错误"""

        class TestAgent(BaseAgent):
            def _build_custom(self):
                pass

        agent = TestAgent(self.config)
        with self.assertRaises(RuntimeError) as context:
            _ = agent.agent

        self.assertIn("代理未初始化", str(context.exception))

    @patch("base_agent.create_deep_agent")
    def test_base_agent_invoke_success(self, mock_create_deep_agent):
        """测试代理执行成功"""

        class TestAgent(BaseAgent):
            def _build_custom(self):
                pass

        mock_result = {"result": "success"}
        mock_final_agent = Mock()
        mock_final_agent.invoke.return_value = mock_result

        mock_with_config = Mock(return_value=mock_final_agent)
        mock_create_deep_agent.return_value = mock_with_config

        agent = TestAgent(self.config)
        agent.build()

        input_data = {"messages": [{"role": "user", "content": "test"}]}
        result = agent.invoke(input_data)

        self.assertEqual(result, mock_result)
        mock_final_agent.invoke.assert_called_once_with(input_data)

    def test_base_agent_get_info(self):
        """测试获取代理信息"""

        class TestAgent(BaseAgent):
            def _build_custom(self):
                pass

        agent = TestAgent(self.config)
        info = agent.get_info()

        self.assertEqual(info["name"], "test-base-agent")
        self.assertEqual(info["type"], AgentType.CUSTOM.value)
        self.assertEqual(info["description"], "测试基类代理")
        self.assertEqual(info["tools_count"], 0)
        self.assertEqual(info["subagents_count"], 0)

    def test_base_agent_str_representation(self):
        """测试字符串表示"""

        class TestAgent(BaseAgent):
            def _build_custom(self):
                pass

        agent = TestAgent(self.config)
        str_repr = str(agent)

        self.assertIn("TestAgent", str_repr)
        self.assertIn("test-base-agent", str_repr)
        self.assertIn("custom", str_repr)


class TestResearchAgent(unittest.TestCase):
    """测试ResearchAgent研究代理"""

    @patch("base_agent.create_deep_agent")
    @patch("base_agent.ResearchAgent._build_custom")
    def test_research_agent_custom_build(
        self, mock_build_custom, mock_create_deep_agent
    ):
        """测试研究代理的定制构建"""
        mock_final_agent = Mock()
        mock_with_config = Mock(return_value=mock_final_agent)
        mock_create_deep_agent.return_value = mock_with_config

        agent = ResearchAgent.create(name="test-researcher", description="测试研究代理")

        agent.build()
        self.assertEqual(agent._agent, mock_final_agent)
        mock_build_custom.assert_called_once()

    def test_research_agent_create_method(self):
        """测试研究代理的创建方法"""
        agent = ResearchAgent.create(
            name="test-researcher",
            description="测试研究代理",
            system_prompt="自定义研究提示",
        )

        self.assertEqual(agent.config.name, "test-researcher")
        self.assertEqual(agent.config.agent_type, AgentType.RESEARCHER)
        self.assertEqual(agent.config.system_prompt, "自定义研究提示")


class TestDeveloperAgent(unittest.TestCase):
    """测试DeveloperAgent开发代理"""

    @patch("base_agent.create_deep_agent")
    @patch("base_agent.DeveloperAgent._build_custom")
    def test_developer_agent_custom_build(
        self, mock_build_custom, mock_create_deep_agent
    ):
        """测试开发代理的定制构建"""
        mock_final_agent = Mock()
        mock_with_config = Mock(return_value=mock_final_agent)
        mock_create_deep_agent.return_value = mock_with_config

        agent = DeveloperAgent.create(name="test-developer", description="测试开发代理")

        agent.build()
        self.assertEqual(agent._agent, mock_final_agent)
        mock_build_custom.assert_called_once()


class TestCoordinatorAgent(unittest.TestCase):
    """测试CoordinatorAgent协调代理"""

    def test_coordinator_agent_with_subagents(self):
        """测试带子代理的协调代理"""
        subagent = {
            "name": "test-subagent",
            "description": "测试子代理",
            "system_prompt": "测试子代理提示",
        }

        agent = CoordinatorAgent.create(
            name="test-coordinator", description="测试协调代理", subagents=[subagent]
        )

        self.assertEqual(len(agent.config.subagents), 1)
        self.assertEqual(agent.config.subagents[0]["name"], "test-subagent")

    def test_coordinator_agent_without_subagents_warning(self):
        """测试没有子代理的协调代理警告"""
        import logging

        with patch("logging.getLogger") as mock_logger:
            mock_logger_instance = Mock()
            mock_logger.return_value = mock_logger_instance

            agent = CoordinatorAgent.create(
                name="test-coordinator", description="测试协调代理"
            )

            agent._build_custom()
            mock_logger_instance.warning.assert_called_with("协调代理没有配置子代理")


class TestConvenienceFunctions(unittest.TestCase):
    """测试便利函数"""

    def test_create_research_agent_function(self):
        """测试创建研究代理便利函数"""
        agent = create_research_agent(
            name="func-researcher", description="函数创建的研究代理"
        )

        self.assertIsInstance(agent, ResearchAgent)
        self.assertEqual(agent.config.name, "func-researcher")
        self.assertEqual(agent.config.agent_type, AgentType.RESEARCHER)

    def test_create_developer_agent_function(self):
        """测试创建开发代理便利函数"""
        agent = create_developer_agent(
            name="func-developer", description="函数创建的开发代理"
        )

        self.assertIsInstance(agent, DeveloperAgent)
        self.assertEqual(agent.config.name, "func-developer")
        self.assertEqual(agent.config.agent_type, AgentType.DEVELOPER)

    def test_create_coordinator_agent_function(self):
        """测试创建协调代理便利函数"""
        agent = create_coordinator_agent(
            name="func-coordinator", description="函数创建的协调代理"
        )

        self.assertIsInstance(agent, CoordinatorAgent)
        self.assertEqual(agent.config.name, "func-coordinator")
        self.assertEqual(agent.config.agent_type, AgentType.COORDINATOR)


class TestAgentType(unittest.TestCase):
    """测试AgentType枚举"""

    def test_agent_type_values(self):
        """测试代理类型值"""
        self.assertEqual(AgentType.RESEARCHER.value, "researcher")
        self.assertEqual(AgentType.DEVELOPER.value, "developer")
        self.assertEqual(AgentType.ANALYST.value, "analyst")
        self.assertEqual(AgentType.COORDINATOR.value, "coordinator")
        self.assertEqual(AgentType.REVIEWER.value, "reviewer")
        self.assertEqual(AgentType.CUSTOM.value, "custom")

    def test_agent_type_uniqueness(self):
        """测试代理类型唯一性"""
        values = [agent_type.value for agent_type in AgentType]
        self.assertEqual(len(values), len(set(values)))


if __name__ == "__main__":
    # 配置日志以避免测试输出中的日志信息
    import logging

    logging.getLogger().setLevel(logging.CRITICAL)

    # 运行测试
    unittest.main(verbosity=2)
