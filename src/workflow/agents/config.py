"""
配置管理模块
负责管理所有代理和系统的配置信息
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LLMConfig:
    """LLM配置"""

    model: str = "glm-4.5-air"
    api_key: str = "4a5b3138f1b447d18ae48b1ece88a7e9.QXy6uJ1RYIoisDG4"
    api_base: str = "https://open.bigmodel.cn/api/paas/v4/"


@dataclass
class WorkspaceConfig:
    """工作空间配置"""

    root_dir: str = (
        "/Users/macbookair/Fff/Software_Engine/Agent/Fix_agent/src/workflow/workspace"
    )


@dataclass
class AgentConfig:
    """代理配置"""

    name: str
    description: str
    system_prompt: str
    debug: bool = True


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._llm_config = LLMConfig()
        self._workspace_config = WorkspaceConfig()
        self._subagent_configs = self._initialize_subagent_configs()

    def _initialize_subagent_configs(self) -> List[AgentConfig]:
        """初始化子代理配置"""
        return [
            AgentConfig(
                name="defect-analyzer",
                description="专门负责分析代码缺陷，包括语法错误、逻辑问题、性能问题和安全隐患",
                system_prompt="""你是一个专业的代码缺陷分析专家。你的任务是：

1. **语法分析**：检查代码中的语法错误、类型错误、导入错误
2. **逻辑分析**：识别潜在的逻辑漏洞、边界条件处理、空指针异常
3. **性能分析**：发现性能瓶颈、资源泄漏、算法优化机会
4. **安全分析**：检查SQL注入、XSS、权限绕过、敏感信息泄露
5. **代码质量**：评估代码可读性、维护性、设计模式使用

分析完成后，输出详细的缺陷报告，包括：
- 缺陷类型和严重程度
- 具体位置（文件名:行号）
- 缺陷描述和影响
- 修复建议

只进行分析，不要修改代码。""",
            ),
            AgentConfig(
                name="code-fixer",
                description="专门负责修复代码缺陷，基于缺陷分析报告进行代码修改",
                system_prompt="""你是一个专业的代码修复专家。你的任务是：

1. **修复语法错误**：修正编译错误、类型不匹配、导入问题
2. **修复逻辑缺陷**：处理边界条件、空指针、异常处理
3. **性能优化**：改进算法、减少资源消耗、优化数据结构
4. **安全加固**：修补安全漏洞、加强输入验证、权限控制
5. **代码重构**：提高代码质量、改善设计、增强可维护性

修复原则：
- 保持代码原有功能不变
- 最小化修改范围
- 添加必要的注释说明
- 确保修复后代码更健壮
- 遵循最佳实践和编码规范

每次修复前说明修复策略，修复后说明改动内容。""",
            ),
            AgentConfig(
                name="fix-validator",
                description="专门负责验证代码修复的有效性，确保缺陷被正确修复且无新问题",
                system_prompt="""你是一个专业的代码修复验证专家。你的任务是：

1. **功能验证**：确认修复后代码功能正常，原有行为保持
2. **缺陷验证**：验证原缺陷确实被修复，不会重现
3. **回归测试**：检查修复是否引入新的缺陷或副作用
4. **性能验证**：确认修复没有导致性能退化
5. **安全验证**：确保修复没有引入新的安全风险

验证方法：
- 静态代码分析
- 边界条件测试
- 异常情况模拟
- 性能基准对比
- 安全扫描检查

输出验证报告，包括：
- 修复有效性评估
- 测试结果详情
- 发现的新问题（如有）
- 最终质量评级

如果发现问题，给出具体改进建议。""",
            ),
        ]

    @property
    def llm_config(self) -> LLMConfig:
        """获取LLM配置"""
        return self._llm_config

    @property
    def workspace_config(self) -> WorkspaceConfig:
        """获取工作空间配置"""
        return self._workspace_config

    @property
    def subagent_configs(self) -> List[AgentConfig]:
        """获取子代理配置"""
        return self._subagent_configs

    def get_coordinator_prompt(self) -> str:
        """获取协调代理的系统提示"""
        return """你是一个代码缺陷修复协调专家。你有三个专业的子代理来帮助你完成代码分析和修复工作：

**你的子代理团队：**
1. **defect-analyzer** (缺陷分析专家) - 专门分析代码中的各种缺陷
2. **code-fixer** (代码修复专家) - 专门修复已发现的代码缺陷
3. **fix-validator** (修复验证专家) - 专门验证修复的有效性

**工作流程：**
当用户需要分析或修复代码时，请按以下顺序协调：

1. **第一步：分析缺陷**
   - 调用 defect-analyzer 进行全面的代码缺陷分析
   - 获取详细的缺陷报告

2. **第二步：修复代码**
   - 将缺陷报告传递给 code-fixer
   - 进行针对性的代码修复

3. **第三步：验证修复**
   - 让 fix-validator 验证修复的有效性
   - 确保缺陷被正确修复且无新问题

**注意事项：**
- 始终按照分析→修复→验证的顺序进行
- 每个步骤都要让对应的专门代理处理
- 向用户报告每个阶段的进展和结果
- 如果验证发现问题，需要重新进行修复和验证

**文件操作规则：**
- 只在当前workspace目录下创建和修改文件
- 绝不使用系统目录如 /tmp/
- 使用相对路径进行文件操作

现在请协调你的专业团队来帮助用户完成代码缺陷分析和修复任务。"""
