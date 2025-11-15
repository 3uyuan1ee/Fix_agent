"""
独立的数据集评估Agent

这个Agent专门为数据集评估设计，复用原项目的tools和中间件，但不依赖交互式界面。
"""

import asyncio
import json
import os
import shutil
# 复用原项目的核心组件
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 获取项目根目录
project_root = Path(__file__).parent.parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# 导入独立配置
from .agent_config import (get_evaluation_subagents,
                           get_evaluation_system_prompt)

# 尝试导入工具和中间件
tools_available = True
middleware_available = True

try:
    from tools.tools import get_all_tools
except ImportError as e:
    print(f"[DatasetAgent] 工具导入警告: {e}")
    print("[DatasetAgent] 将使用模拟工具进行测试")
    tools_available = False

# 中间件导入（可选，因为它们可能也有相对导入问题）
try:
    from midware.context_enhancement import ContextEnhancementMiddleware
    from midware.layered_memory import LayeredMemoryMiddleware
    from midware.logging import LoggingMiddleware
    from midware.performance_monitor import PerformanceMonitorMiddleware
    from midware.security import SecurityMiddleware
except ImportError as e:
    print(f"[DatasetAgent] 中间件导入警告: {e}")
    print("[DatasetAgent] 将使用简化模式运行")
    middleware_available = False

# DeepAgents导入
try:
    from deepagents import create_deep_agent
    from deepagents.backends import CompositeBackend
    from deepagents.backends.filesystem import FilesystemBackend
    from deepagents.middleware.resumable_shell import \
        ResumableShellToolMiddleware
    from langchain.agents.middleware import HostExecutionPolicy
    from langgraph.checkpoint.memory import InMemorySaver
except ImportError as e:
    print(f"[DatasetAgent] DeepAgents导入错误: {e}")
    raise


@dataclass
class AgentRequest:
    """Agent请求数据结构"""

    task_id: str
    problem_description: str
    failing_tests: List[str]
    workspace_path: str
    repo_info: Optional[Dict[str, Any]] = None
    timeout: int = 300
    mode: str = "automated"  # automated: 自动模式, interactive: 交互模式


@dataclass
class AgentResponse:
    """Agent响应数据结构"""

    task_id: str
    success: bool
    message: str
    fixed_files: List[str]
    execution_time: float
    intermediate_steps: List[Dict[str, Any]]
    test_results: Dict[str, Any]
    error: Optional[str] = None
    metadata: Dict[str, Any] = None


class DatasetAgent:
    """
    独立的数据集评估Agent

    特点：
    - 不依赖交互式界面
    - 复用原项目的所有tools和中间件
    - 支持自动化的bug修复流程
    - 提供标准化的API接口
    """

    def __init__(
        self, agent_id: str = "dataset_eval_agent", config: Optional[Dict] = None
    ):
        self.agent_id = agent_id
        self.config = config or {}
        self.agent = None
        self.workspace_root = None
        self.temp_dirs = []  # 跟踪临时目录
        self._initialized = False

    async def initialize(self, workspace_root: str = None) -> bool:
        """
        初始化Agent

        Args:
            workspace_root: 工作空间根目录

        Returns:
            bool: 初始化是否成功
        """
        try:
            self.workspace_root = workspace_root or tempfile.mkdtemp(
                prefix="dataset_eval_"
            )
            self.temp_dirs.append(self.workspace_root)

            # 切换到工作目录
            original_cwd = os.getcwd()
            os.chdir(self.workspace_root)

            try:
                # 创建agent实例
                await self._create_agent()
                self._initialized = True

                print(f"[DatasetAgent] 初始化成功，工作空间: {self.workspace_root}")
                return True

            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)

        except Exception as e:
            print(f"[DatasetAgent] 初始化失败: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def _create_agent(self):
        """创建agent实例"""

        try:
            # 创建工具列表
            if tools_available:
                tools = get_all_tools().values()
                print(f"[DatasetAgent] 加载了 {len(tools)} 个工具")
            else:
                # 创建模拟工具用于测试
                tools = []
                print("[DatasetAgent] 使用模拟工具模式")

            # 创建shell中间件
            shell_middleware = ResumableShellToolMiddleware(
                workspace_root=self.workspace_root,
                execution_policy=HostExecutionPolicy(),
            )

            # 创建记忆后端
            agent_dir = Path(self.workspace_root) / "agent_data"
            agent_dir.mkdir(exist_ok=True)

            long_term_backend = FilesystemBackend(root_dir=agent_dir, virtual_mode=True)
            backend = CompositeBackend(
                default=FilesystemBackend(), routes={"/memories/": long_term_backend}
            )

            # 构建中间件管道（简化版，专为数据集评估优化）
            agent_middleware = []

            # 如果中间件可用，添加中间件
            if middleware_available:
                try:
                    # 性能监控中间件
                    performance_middleware = PerformanceMonitorMiddleware(
                        backend=long_term_backend,
                        metrics_path="/performance/",
                        enable_system_monitoring=True,
                        max_records=100,
                    )
                    agent_middleware.append(performance_middleware)
                    print("[DatasetAgent] 性能监控中间件已加载")
                except Exception as e:
                    print(f"[DatasetAgent] 性能监控中间件加载失败: {e}")

                try:
                    # 日志记录中间件
                    logging_middleware = LoggingMiddleware(
                        backend=long_term_backend,
                        session_id=self.agent_id,
                        log_path="/logs/",
                        enable_conversation_logging=True,
                        enable_tool_logging=True,
                        enable_performance_logging=True,
                        enable_error_logging=True,
                    )
                    agent_middleware.append(logging_middleware)
                    print("[DatasetAgent] 日志记录中间件已加载")
                except Exception as e:
                    print(f"[DatasetAgent] 日志记录中间件加载失败: {e}")

                try:
                    # 安全检查中间件（评估模式，适当放宽限制）
                    security_middleware = SecurityMiddleware(
                        backend=long_term_backend,
                        security_level="low",  # 评估模式使用较低安全级别
                        workspace_root=self.workspace_root,
                        enable_file_security=True,
                        enable_command_security=False,  # 禁用命令安全检查，允许编译和测试
                        enable_content_security=True,
                        allow_path_traversal=True,  # 允许路径遍历，便于项目文件操作
                        max_file_size=50 * 1024 * 1024,  # 50MB
                    )
                    agent_middleware.append(security_middleware)
                    print("[DatasetAgent] 安全检查中间件已加载")
                except Exception as e:
                    print(f"[DatasetAgent] 安全检查中间件加载失败: {e}")
            else:
                print("[DatasetAgent] 使用简化中间件模式")

            # shell工具中间件（最内层）
            agent_middleware.append(shell_middleware)

            # 创建子代理
            subagents = get_evaluation_subagents()
            print(f"[DatasetAgent] 加载了 {len(subagents)} 个子代理")

            # 创建agent（禁用交互式确认）
            system_prompt = get_evaluation_system_prompt()

            # 如果没有指定模型，使用默认配置
            model = self.config.get("model")
            if not model:
                print("[DatasetAgent] 警告：未指定模型，请确保在配置中设置model参数")

            self.agent = create_deep_agent(
                model=model,  # 需要在config中指定模型
                system_prompt=system_prompt,
                tools=list(tools),
                backend=backend,
                middleware=agent_middleware,
                subagents=subagents,
                interrupt_on={},  # 禁用所有交互式中断
            )

            self.agent.checkpointer = InMemorySaver()
            print("[DatasetAgent] Agent创建成功")

        except Exception as e:
            print(f"[DatasetAgent] Agent创建失败: {e}")
            import traceback

            traceback.print_exc()
            raise

    def _get_evaluation_system_prompt(self) -> str:
        """获取评估模式的系统提示"""

        return f"""### 数据集评估模式

你是一个专业的代码缺陷修复专家，正在参与标准数据集评估。

**当前模式：** 自动化评估模式（无需用户确认）

**工作流程：**
1. **缺陷分析** - 使用 defect-analyzer 子代理分析代码问题
2. **代码修复** - 使用 code-fixer 子代理修复发现的问题
3. **修复验证** - 使用 fix-validator 子代理验证修复效果

**重要原则：**
- 直接执行操作，不要询问用户确认
- 专注于修复指定的bug，不要进行额外的改进
- 保存所有修改的文件，便于后续测试验证
- 如果某个步骤失败，继续尝试其他方法

**输出格式：**
完成修复后，请提供：
1. 修复的文件列表
2. 每个文件的修改说明
3. 预期的修复效果

**工具使用：**
- compile_project: 编译项目检查语法错误
- run_and_monitor: 运行测试验证修复效果
- analyze_code_defects: 分析代码缺陷
- explore_project_structure: 了解项目结构

现在请按照上述流程处理收到的代码修复任务。
"""

    async def process_request(self, request: AgentRequest) -> AgentResponse:
        """
        处理修复请求

        Args:
            request: 修复请求

        Returns:
            AgentResponse: 修复结果
        """

        if not self._initialized:
            await self.initialize(request.workspace_path)

        start_time = time.time()

        try:
            # 构造标准化的请求提示
            prompt = self._build_evaluation_prompt(request)

            # 切换到工作目录
            original_cwd = os.getcwd()
            os.chdir(request.workspace_path)

            try:
                # 执行agent处理
                result = await self._execute_agent(prompt, request)

                execution_time = time.time() - start_time

                # 运行测试验证修复效果
                test_results = await self._run_validation_tests(request)

                return AgentResponse(
                    task_id=request.task_id,
                    success=result.get("success", False),
                    message=result.get("message", ""),
                    fixed_files=result.get("fixed_files", []),
                    execution_time=execution_time,
                    intermediate_steps=result.get("steps", []),
                    test_results=test_results,
                    metadata=result.get("metadata", {}),
                )

            finally:
                # 恢复原工作目录
                os.chdir(original_cwd)

        except Exception as e:
            return AgentResponse(
                task_id=request.task_id,
                success=False,
                message=f"处理失败: {str(e)}",
                fixed_files=[],
                execution_time=time.time() - start_time,
                intermediate_steps=[],
                test_results={},
                error=str(e),
            )

    def _build_evaluation_prompt(self, request: AgentRequest) -> str:
        """构造评估提示"""

        repo_info = request.repo_info or {}

        prompt = f"""请分析并修复以下代码问题：

**任务ID：** {request.task_id}

**问题描述：**
{request.problem_description}

**失败的测试用例：**
{chr(10).join(f"- {test}" for test in request.failing_tests) if request.failing_tests else "无具体测试用例"}

**项目信息：**
- 项目名称：{repo_info.get('name', '未知')}
- 主要语言：{repo_info.get('language', '未知')}
- 框架：{repo_info.get('framework', '无')}

**修复要求：**
1. 使用defect-analyzer分析代码缺陷
2. 使用code-fixer修复发现的问题
3. 使用fix-validator验证修复效果
4. 确保修复后所有失败的测试都能通过

**工作目录：** {request.workspace_path}

请按照上述步骤进行修复，并提供详细的修复报告。
"""

        return prompt

    async def _execute_agent(
        self, prompt: str, request: AgentRequest
    ) -> Dict[str, Any]:
        """执行agent处理"""

        try:
            # 使用异步方式调用agent
            # 这里需要根据实际的agent接口调整
            if hasattr(self.agent, "ainvoke"):
                result = await self.agent.ainvoke({"input": prompt})
            elif hasattr(self.agent, "invoke"):
                # 如果没有异步接口，使用同步接口
                result = self.agent.invoke({"input": prompt})
            else:
                raise Exception("Agent不支持invoke接口")

            # 解析结果
            return self._parse_agent_result(result)

        except Exception as e:
            return {
                "success": False,
                "message": f"Agent执行失败: {str(e)}",
                "fixed_files": [],
                "steps": [],
                "metadata": {"error": str(e)},
            }

    def _parse_agent_result(self, result) -> Dict[str, Any]:
        """解析agent结果"""

        # 根据实际的agent输出格式解析结果
        # 这里需要根据具体的agent实现调整

        try:
            if isinstance(result, dict):
                if "output" in result:
                    # 标准格式
                    output = result["output"]
                elif "response" in result:
                    output = result["response"]
                else:
                    output = str(result)
            else:
                output = str(result)

            # 尝试从输出中提取结构化信息
            fixed_files = self._extract_fixed_files(output)

            return {
                "success": True,
                "message": output,
                "fixed_files": fixed_files,
                "steps": [{"step": "agent_processing", "output": output}],
                "metadata": {"raw_output": output},
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"结果解析失败: {str(e)}",
                "fixed_files": [],
                "steps": [],
                "metadata": {"parse_error": str(e)},
            }

    def _extract_fixed_files(self, output: str) -> List[str]:
        """从输出中提取修复的文件列表"""

        # 这里需要根据实际的agent输出格式提取文件列表
        # 简化实现，实际可能需要更复杂的解析逻辑

        fixed_files = []

        # 简单的关键词匹配
        lines = output.split("\n")
        for line in lines:
            if any(
                keyword in line.lower()
                for keyword in ["fixed:", "modified:", "updated:", "changed:"]
            ):
                # 尝试提取文件路径
                words = line.split()
                for word in words:
                    if "." in word and any(
                        word.endswith(ext)
                        for ext in [".py", ".js", ".java", ".cpp", ".c"]
                    ):
                        fixed_files.append(word)

        return list(set(fixed_files))  # 去重

    async def _run_validation_tests(self, request: AgentRequest) -> Dict[str, Any]:
        """运行验证测试"""

        test_results = {
            "compilation": {"success": False, "output": ""},
            "unit_tests": {"success": False, "output": "", "passed": 0, "failed": 0},
            "specific_tests": {"success": False, "output": ""},
        }

        try:
            # 1. 编译检查
            test_results["compilation"] = await self._run_compilation_test()

            # 2. 运行具体的失败测试
            if request.failing_tests:
                test_results["specific_tests"] = await self._run_specific_tests(
                    request.failing_tests
                )

            # 3. 运行单元测试套件（如果有）
            test_results["unit_tests"] = await self._run_unit_tests()

        except Exception as e:
            test_results["error"] = str(e)

        return test_results

    async def _run_compilation_test(self) -> Dict[str, Any]:
        """运行编译测试"""

        try:
            # 使用compile_project工具
            from src.tools.error_detector import compile_project

            result = compile_project.invoke({"project_path": ".", "language": "auto"})

            return {
                "success": "成功" in result or "success" in result.lower(),
                "output": result,
            }

        except Exception as e:
            return {"success": False, "output": f"编译测试失败: {str(e)}"}

    async def _run_specific_tests(self, failing_tests: List[str]) -> Dict[str, Any]:
        """运行特定的测试"""

        try:
            # 使用run_and_monitor工具运行测试
            from src.tools.error_detector import run_and_monitor

            # 构造测试命令
            test_command = self._build_test_command(failing_tests)

            result = run_and_monitor.invoke({"command": test_command, "timeout": 60})

            return {
                "success": "passed" in result.lower() or "ok" in result.lower(),
                "output": result,
            }

        except Exception as e:
            return {"success": False, "output": f"特定测试失败: {str(e)}"}

    async def _run_unit_tests(self) -> Dict[str, Any]:
        """运行单元测试套件"""

        try:
            # 尝试不同的测试命令
            test_commands = [
                "python -m pytest . -v",
                "python -m unittest discover -v",
                "python setup.py test",
                "npm test",
                "make test",
            ]

            for cmd in test_commands:
                try:
                    from src.tools.error_detector import run_and_monitor

                    result = run_and_monitor.invoke({"command": cmd, "timeout": 120})

                    if "passed" in result.lower() or "ok" in result.lower():
                        return {"success": True, "output": result, "command": cmd}

                except:
                    continue

            return {"success": False, "output": "无法找到合适的测试命令"}

        except Exception as e:
            return {"success": False, "output": f"单元测试失败: {str(e)}"}

    def _build_test_command(self, failing_tests: List[str]) -> str:
        """构建测试命令"""

        # 根据项目类型和测试框架构建命令
        if any("test_" in test for test in failing_tests):
            # pytest格式
            return f"python -m pytest {' '.join(failing_tests)} -v"
        elif any("unittest" in test for test in failing_tests):
            # unittest格式
            return f"python -m unittest {' '.join(failing_tests)}"
        else:
            # 通用格式
            return f"python -m pytest {' '.join(failing_tests)} -v"

    async def cleanup(self):
        """清理资源"""

        # 清理临时目录
        for temp_dir in self.temp_dirs:
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"[DatasetAgent] 清理临时目录失败: {e}")

        self.temp_dirs.clear()
        self._initialized = False

    def __del__(self):
        """析构函数"""
        if hasattr(self, "temp_dirs"):
            for temp_dir in self.temp_dirs:
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass
