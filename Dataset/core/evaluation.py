"""
评估框架 - 核心评估逻辑

提供标准化的数据集评估框架，支持SWE-bench和BugsInPy等数据集。
"""

import asyncio
import json
import os
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# 使用多层导入策略
try:
    from ..data_types import (EvaluationResult, EvaluationSummary,
                              EvaluationTask)
    from .agent import AgentRequest, AgentResponse, DatasetAgent
except ImportError:
    try:
        from core.agent import AgentRequest, AgentResponse, DatasetAgent
        from data_types import (EvaluationResult, EvaluationSummary,
                                EvaluationTask)
    except ImportError:
        try:
            from Dataset.core.agent import (AgentRequest, AgentResponse,
                                            DatasetAgent)
            from Dataset.data_types import (EvaluationResult,
                                            EvaluationSummary, EvaluationTask)
        except ImportError:
            # 最后尝试：添加路径后导入
            import sys
            from pathlib import Path

            current_dir = Path(__file__).parent
            root_dir = current_dir.parent
            if str(current_dir) not in sys.path:
                sys.path.insert(0, str(current_dir))
            if str(root_dir) not in sys.path:
                sys.path.insert(0, str(root_dir))
            from agent import AgentRequest, AgentResponse, DatasetAgent

            from ..data_types import (EvaluationResult, EvaluationSummary,
                                      EvaluationTask)


class EvaluationFramework:
    """
    评估框架主类

    特点：
    - 支持多数据集评估
    - 并行任务执行
    - 详细的错误分析
    - 灵活的配置选项
    - 实时进度报告
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agent = None
        self.results: List[EvaluationResult] = []
        self.temp_workspace = None
        self._setup_temp_workspace()

    def _setup_temp_workspace(self):
        """设置临时工作空间"""
        self.temp_workspace = tempfile.mkdtemp(prefix="dataset_eval_")
        print(f"[EvaluationFramework] 临时工作空间: {self.temp_workspace}")

    async def initialize(self) -> bool:
        """初始化评估框架"""
        try:
            # 创建DatasetAgent实例
            self.agent = DatasetAgent(
                agent_id="evaluation_agent", config=self.config.get("agent", {})
            )

            # 初始化agent
            success = await self.agent.initialize(self.temp_workspace)

            if success:
                print("[EvaluationFramework] 初始化成功")
            else:
                print("[EvaluationFramework] 初始化失败")

            return success

        except Exception as e:
            print(f"[EvaluationFramework] 初始化异常: {e}")
            import traceback

            traceback.print_exc()
            return False

    async def evaluate_dataset(
        self,
        tasks: List[EvaluationTask],
        max_workers: int = 4,
        progress_callback: Optional[callable] = None,
    ) -> EvaluationSummary:
        """
        评估数据集

        Args:
            tasks: 评估任务列表
            max_workers: 并行工作线程数
            progress_callback: 进度回调函数

        Returns:
            EvaluationSummary: 评估摘要
        """

        if not self.agent:
            raise RuntimeError("评估框架未初始化")

        print(f"[EvaluationFramework] 开始评估 {len(tasks)} 个任务")
        print(f"[EvaluationFramework] 并行工作线程数: {max_workers}")

        start_time = time.time()
        results = []

        # 为每个任务准备独立的工作空间
        task_workspaces = {}
        for task in tasks:
            task_workspace = Path(self.temp_workspace) / task.task_id
            task_workspace.mkdir(exist_ok=True)
            task_workspaces[task.task_id] = str(task_workspace)

        # 并行执行评估任务
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_task = {}
            for task in tasks:
                future = executor.submit(
                    self._evaluate_single_task_sync, task, task_workspaces[task.task_id]
                )
                future_to_task[future] = task

            # 收集结果
            for i, future in enumerate(as_completed(future_to_task), 1):
                task = future_to_task[future]

                try:
                    result = future.result(timeout=600)  # 10分钟超时
                    results.append(result)

                    # 进度回调
                    if progress_callback:
                        progress_callback(i, len(tasks), task, result)

                    # 实时进度报告
                    success = result.success
                    print(
                        f"[{i}/{len(tasks)}] 任务 {task.task_id}: {'成功' if success else '失败'}"
                    )

                except Exception as e:
                    print(f"[{i}/{len(tasks)}] 任务 {task.task_id}: 异常 - {str(e)}")

                    # 创建失败结果
                    error_result = EvaluationResult(
                        task_id=task.task_id,
                        dataset_name=task.dataset_name,
                        success=False,
                        execution_time=0,
                        agent_response=None,
                        test_results={},
                        error=str(e),
                    )
                    results.append(error_result)

        total_time = time.time() - start_time

        # 生成评估摘要
        summary = self._generate_summary(results, total_time)

        # 保存结果
        self._save_results(results, summary)

        print(f"[EvaluationFramework] 评估完成，成功率: {summary.success_rate:.2%}")

        return summary

    def _evaluate_single_task_sync(
        self, task: EvaluationTask, workspace_path: str
    ) -> EvaluationResult:
        """同步评估单个任务（在线程池中运行）"""

        start_time = time.time()

        try:
            # 设置项目环境
            self._setup_task_environment(task, workspace_path)

            # 运行初始测试（验证bug存在）
            initial_test_result = self._run_initial_tests(task, workspace_path)

            # 创建AgentRequest
            agent_request = AgentRequest(
                task_id=task.task_id,
                problem_description=task.problem_description,
                failing_tests=task.failing_tests,
                workspace_path=workspace_path,
                repo_info=task.repo_info,
                timeout=task.timeout,
                mode="automated",
            )

            # 执行agent修复（同步调用）
            import asyncio

            agent_response = asyncio.run(self.agent.process_request(agent_request))

            execution_time = time.time() - start_time

            # 运行修复后测试
            final_test_result = self._run_final_tests(task, workspace_path)

            # 判断修复是否成功
            success = self._determine_fix_success(
                initial_test_result, final_test_result, task.failing_tests
            )

            return EvaluationResult(
                task_id=task.task_id,
                dataset_name=task.dataset_name,
                success=success,
                execution_time=execution_time,
                agent_response=agent_response,
                test_results={
                    "initial": initial_test_result,
                    "final": final_test_result,
                },
                metadata={
                    "workspace": workspace_path,
                    "repo_name": task.repo_name,
                    "patch_available": task.patch_file is not None,
                },
            )

        except Exception as e:
            return EvaluationResult(
                task_id=task.task_id,
                dataset_name=task.dataset_name,
                success=False,
                execution_time=time.time() - start_time,
                agent_response=None,
                test_results={},
                error=str(e),
                metadata={"workspace": workspace_path},
            )

    def _setup_task_environment(self, task: EvaluationTask, workspace_path: str):
        """设置任务环境"""

        workspace = Path(workspace_path)

        # 如果指定了patch文件，应用patch
        if task.patch_file and Path(task.patch_file).exists():
            try:
                self._apply_patch(task.patch_file, workspace)
                print(f"[{task.task_id}] 应用patch文件: {task.patch_file}")
            except Exception as e:
                print(f"[{task.task_id}] 应用patch失败: {e}")

        # 运行设置命令
        if task.setup_commands:
            for cmd in task.setup_commands:
                try:
                    result = os.system(f"cd {workspace} && {cmd}")
                    if result != 0:
                        print(f"[{task.task_id}] 设置命令失败: {cmd}")
                except Exception as e:
                    print(f"[{task.task_id}] 设置命令异常: {cmd} - {e}")

    def _apply_patch(self, patch_file: str, workspace_path: Path):
        """应用patch文件"""

        try:
            import subprocess

            # 使用git apply应用patch
            result = subprocess.run(
                ["git", "apply", patch_file],
                cwd=workspace_path,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                # 如果git apply失败，尝试patch命令
                result = subprocess.run(
                    ["patch", "-p1", "-i", patch_file],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    raise Exception(f"Patch应用失败: {result.stderr}")

        except Exception as e:
            raise Exception(f"应用patch失败: {e}")

    def _run_initial_tests(
        self, task: EvaluationTask, workspace_path: str
    ) -> Dict[str, Any]:
        """运行初始测试"""

        try:
            # 使用指定的测试命令
            if task.test_command:
                return self._run_test_command(task.test_command, workspace_path)

            # 尝试运行失败的测试
            if task.failing_tests:
                test_cmd = self._build_test_command(task.failing_tests)
                return self._run_test_command(test_cmd, workspace_path)

            return {"success": True, "output": "无测试命令"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_final_tests(
        self, task: EvaluationTask, workspace_path: str
    ) -> Dict[str, Any]:
        """运行修复后测试"""

        try:
            # 使用相同的测试命令
            if task.test_command:
                return self._run_test_command(task.test_command, workspace_path)

            # 运行之前失败的测试
            if task.failing_tests:
                test_cmd = self._build_test_command(task.failing_tests)
                return self._run_test_command(test_cmd, workspace_path)

            return {"success": True, "output": "无测试命令"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_test_command(self, command: str, workspace_path: str) -> Dict[str, Any]:
        """运行测试命令"""

        try:
            import subprocess

            result = subprocess.run(
                command,
                shell=True,
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=120,  # 2分钟超时
            )

            output = result.stdout + result.stderr

            return {
                "success": result.returncode == 0,
                "output": output,
                "return_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "测试执行超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_test_command(self, failing_tests: List[str]) -> str:
        """构建测试命令"""

        if not failing_tests:
            return "python -m pytest . -v"

        # 根据测试名称判断测试框架
        if any("test_" in test for test in failing_tests):
            return f"python -m pytest {' '.join(failing_tests)} -v"
        else:
            return f"python -m pytest {' '.join(failing_tests)} -v"

    def _determine_fix_success(
        self,
        initial_result: Dict[str, Any],
        final_result: Dict[str, Any],
        failing_tests: List[str],
    ) -> bool:
        """判断修复是否成功"""

        # 如果初始测试成功，说明bug未重现
        if initial_result.get("success", False):
            return False

        # 如果最终测试成功，说明修复成功
        if final_result.get("success", False):
            return True

        # 检查输出中是否包含通过的测试
        final_output = final_result.get("output", "")
        if any(
            "passed" in final_output.lower() or "ok" in final_output.lower()
            for test in failing_tests
        ):
            return True

        return False

    def _generate_summary(
        self, results: List[EvaluationResult], total_time: float
    ) -> EvaluationSummary:
        """生成评估摘要"""

        # 基础统计
        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.success)
        failed_tasks = total_tasks - successful_tasks

        # 时间统计
        execution_times = [r.execution_time for r in results if r.execution_time > 0]
        avg_execution_time = (
            sum(execution_times) / len(execution_times) if execution_times else 0
        )

        # 错误分析
        error_analysis = self._analyze_errors(results)

        # 性能指标
        performance_metrics = self._calculate_performance_metrics(results)

        # 按数据集分组统计
        dataset_stats = {}
        for result in results:
            dataset = result.dataset_name
            if dataset not in dataset_stats:
                dataset_stats[dataset] = {"total": 0, "success": 0}
            dataset_stats[dataset]["total"] += 1
            if result.success:
                dataset_stats[dataset]["success"] += 1

        return EvaluationSummary(
            dataset_name=(
                "multiple" if len(dataset_stats) > 1 else list(dataset_stats.keys())[0]
            ),
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            success_rate=successful_tasks / total_tasks if total_tasks > 0 else 0,
            average_execution_time=avg_execution_time,
            total_execution_time=total_time,
            tasks_per_hour=total_tasks / (total_time / 3600) if total_time > 0 else 0,
            error_analysis=error_analysis,
            performance_metrics={
                **performance_metrics,
                "dataset_breakdown": dataset_stats,
            },
        )

    def _analyze_errors(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """分析错误模式"""

        error_counts = {}
        error_by_dataset = {}
        error_by_phase = {}

        for result in results:
            if not result.success:
                error_msg = result.error or "未知错误"
                error_counts[error_msg] = error_counts.get(error_msg, 0) + 1

                # 按数据集统计
                dataset = result.dataset_name
                if dataset not in error_by_dataset:
                    error_by_dataset[dataset] = {}
                error_by_dataset[dataset][error_msg] = (
                    error_by_dataset[dataset].get(error_msg, 0) + 1
                )

                # 按阶段统计
                if result.agent_response:
                    phase = "agent_execution"
                elif "test" in str(result.test_results).lower():
                    phase = "testing"
                else:
                    phase = "setup"

                error_by_phase[phase] = error_by_phase.get(phase, 0) + 1

        return {
            "total_errors": len([r for r in results if not r.success]),
            "error_types": error_counts,
            "error_by_dataset": error_by_dataset,
            "error_by_phase": error_by_phase,
            "most_common_errors": sorted(
                error_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

    def _calculate_performance_metrics(
        self, results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """计算性能指标"""

        execution_times = [r.execution_time for r in results if r.execution_time > 0]

        if not execution_times:
            return {}

        return {
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "median_execution_time": sorted(execution_times)[len(execution_times) // 2],
            "std_execution_time": (
                sum(
                    (t - sum(execution_times) / len(execution_times)) ** 2
                    for t in execution_times
                )
                / len(execution_times)
            )
            ** 0.5,
            "execution_time_distribution": {
                "under_30s": len([t for t in execution_times if t < 30]),
                "30s_to_60s": len([t for t in execution_times if 30 <= t < 60]),
                "60s_to_120s": len([t for t in execution_times if 60 <= t < 120]),
                "over_120s": len([t for t in execution_times if t >= 120]),
            },
        }

    def _save_results(
        self, results: List[EvaluationResult], summary: EvaluationSummary
    ):
        """保存评估结果"""

        # 创建输出目录
        output_dir = Path("evaluation_results")
        output_dir.mkdir(exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        results_file = output_dir / f"results_{timestamp}.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(result) for result in results],
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        # 保存摘要
        summary_file = output_dir / f"summary_{timestamp}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(asdict(summary), f, indent=2, ensure_ascii=False, default=str)

        print(f"[EvaluationFramework] 结果已保存:")
        print(f"  详细结果: {results_file}")
        print(f"  评估摘要: {summary_file}")

    async def cleanup(self):
        """清理资源"""

        # 清理agent
        if self.agent:
            await self.agent.cleanup()

        # 清理临时工作空间
        if self.temp_workspace and os.path.exists(self.temp_workspace):
            try:
                shutil.rmtree(self.temp_workspace)
                print(f"[EvaluationFramework] 清理临时工作空间: {self.temp_workspace}")
            except Exception as e:
                print(f"[EvaluationFramework] 清理失败: {e}")

    def __del__(self):
        """析构函数"""
        if (
            hasattr(self, "temp_workspace")
            and self.temp_workspace
            and os.path.exists(self.temp_workspace)
        ):
            try:
                shutil.rmtree(self.temp_workspace)
            except:
                pass
