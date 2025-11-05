"""
修复流程协调器
协调整个分析修复执行流程
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..llm.client import LLMClient
from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from .backup_manager import BackupManager, BackupResult
from .diff_viewer import DiffResult, DiffViewer
from .fix_confirmation import (
    ConfirmationRequest,
    ConfirmationResponse,
    ConfirmationSession,
    FixConfirmationManager,
)
from .fix_executor import BatchExecutionResult, ExecutionResult, FixExecutor
from .fix_generator import FixGenerator, FixRequest, FixResult


@dataclass
class FixAnalysisRequest:
    """修复分析请求"""

    file_path: str
    issues: List[Dict[str, Any]]
    analysis_type: str = "security"
    user_instructions: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    auto_fix: bool = False
    backup_enabled: bool = True
    confirmation_required: bool = True


@dataclass
class FixProcessResult:
    """修复流程结果"""

    process_id: str
    file_path: str
    success: bool
    stages_completed: List[str] = field(default_factory=list)
    fix_result: Optional[FixResult] = field(default_factory=None)
    backup_result: Optional[BackupResult] = field(default_factory=None)
    diff_result: Optional[DiffResult] = field(default_factory=None)
    confirmation_response: Optional[ConfirmationResponse] = field(default_factory=None)
    execution_result: Optional[ExecutionResult] = field(default_factory=None)
    total_time: float = 0.0
    error_message: Optional[str] = None
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "process_id": self.process_id,
            "file_path": self.file_path,
            "success": self.success,
            "stages_completed": self.stages_completed,
            "total_time": self.total_time,
            "error_message": self.error_message,
            "summary": self.summary,
            "has_fix_result": self.fix_result is not None,
            "has_backup": self.backup_result is not None,
            "has_diff": self.diff_result is not None,
            "has_confirmation": self.confirmation_response is not None,
            "has_execution": self.execution_result is not None,
        }


@dataclass
class BatchFixProcessResult:
    """批量修复流程结果"""

    batch_id: str
    total_files: int
    successful_files: int
    failed_files: int
    process_results: List[FixProcessResult] = field(default_factory=list)
    total_time: float = 0.0
    start_time: str = ""
    end_time: str = ""
    confirmation_session: Optional[ConfirmationSession] = field(default_factory=None)
    batch_execution_result: Optional[BatchExecutionResult] = field(default_factory=None)
    summary: str = ""


class FixCoordinator:
    """修复流程协调器"""

    def __init__(self, config_manager=None, llm_client: Optional[LLMClient] = None):
        """
        初始化修复流程协调器

        Args:
            config_manager: 配置管理器实例
            llm_client: LLM客户端实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        try:
            self.config = self.config_manager.get_section("fix_coordinator")
        except:
            self.config = {}

        self.parallel_processing = self.config.get("parallel_processing", False)
        self.max_parallel_files = self.config.get("max_parallel_files", 3)
        self.generate_reports = self.config.get("generate_reports", True)
        self.report_output_dir = Path(
            self.config.get("report_output_dir", "./fix_reports")
        )

        # 初始化组件
        self.fix_generator = FixGenerator(config_manager, llm_client)
        self.backup_manager = BackupManager(config_manager)
        self.diff_viewer = DiffViewer(config_manager)
        self.confirmation_manager = FixConfirmationManager(config_manager)
        self.fix_executor = FixExecutor(config_manager)

        # 创建报告目录
        self.report_output_dir.mkdir(exist_ok=True)

        self.logger.info("FixCoordinator initialized")

    async def process_fix_request(
        self, request: FixAnalysisRequest
    ) -> FixProcessResult:
        """
        处理单个文件修复请求

        Args:
            request: 修复分析请求

        Returns:
            修复流程结果
        """
        import uuid

        process_id = str(uuid.uuid4())
        start_time = time.time()

        self.logger.info(f"Starting fix process {process_id} for {request.file_path}")

        result = FixProcessResult(
            process_id=process_id, file_path=request.file_path, success=False
        )

        try:
            # 阶段1: 生成修复建议
            self.logger.info(f"Stage 1: Generating fixes for {request.file_path}")
            fix_request = await self._create_fix_request(request)
            fix_result = await self.fix_generator.generate_fixes(fix_request)
            result.fix_result = fix_result
            result.stages_completed.append("fix_generation")

            if not fix_result.success:
                result.error_message = f"Fix generation failed: {fix_result.error}"
                return result

            # 阶段2: 创建备份
            if request.backup_enabled:
                self.logger.info(f"Stage 2: Creating backup for {request.file_path}")
                backup_result = self.backup_manager.create_backup(
                    request.file_path, reason="pre_fix", fix_request_id=process_id
                )
                result.backup_result = backup_result
                result.stages_completed.append("backup_creation")

                if not backup_result.success:
                    self.logger.warning(
                        f"Backup creation failed: {backup_result.error}"
                    )
                    # 继续处理，但记录警告

            # 阶段3: 生成代码差异
            self.logger.info(f"Stage 3: Generating diff for {request.file_path}")
            diff_result = self.diff_viewer.generate_diff(
                request.file_path,
                fix_request.original_content,
                fix_result.complete_fixed_content,
            )
            result.diff_result = diff_result
            result.stages_completed.append("diff_generation")

            # 阶段4: 用户确认
            if request.confirmation_required and not request.auto_fix:
                self.logger.info(
                    f"Stage 4: Requesting confirmation for {request.file_path}"
                )
                confirmation_response = self.confirmation_manager.request_confirmation(
                    process_id,
                    request.file_path,
                    fix_result,
                    diff_result,
                    result.backup_result.backup_id if result.backup_result else "",
                )
                result.confirmation_response = confirmation_response
                result.stages_completed.append("user_confirmation")

                # 检查确认结果
                if confirmation_response.status.value in ["rejected", "cancelled"]:
                    result.error_message = (
                        f"Fix rejected by user: {confirmation_response.user_message}"
                    )
                    return result
            else:
                # 自动确认
                from .fix_confirmation import ConfirmationStatus

                confirmation_response = ConfirmationResponse(
                    fix_id=process_id,
                    status=ConfirmationStatus.APPROVED,
                    user_message="Auto-approved",
                )
                result.confirmation_response = confirmation_response
                result.stages_completed.append("auto_confirmation")

            # 阶段5: 执行修复
            self.logger.info(f"Stage 5: Executing fix for {request.file_path}")
            execution_result = await self.fix_executor.execute_fix(
                process_id,
                request.file_path,
                fix_result,
                confirmation_response,
                result.backup_result.backup_id if result.backup_result else None,
            )
            result.execution_result = execution_result
            result.stages_completed.append("fix_execution")

            if execution_result.success:
                result.success = True
                result.summary = f"Fix completed successfully for {request.file_path}"
                self.logger.info(f"Fix process {process_id} completed successfully")
            else:
                result.error_message = (
                    f"Fix execution failed: {execution_result.error_message}"
                )
                self.logger.error(
                    f"Fix process {process_id} failed: {execution_result.error_message}"
                )

        except Exception as e:
            result.error_message = f"Fix process error: {e}"
            self.logger.error(f"Fix process {process_id} failed: {e}")

        result.total_time = time.time() - start_time

        # 生成报告（如果启用）
        if self.generate_reports:
            self._generate_process_report(result)

        return result

    def process_batch_fix_requests(
        self, requests: List[FixAnalysisRequest]
    ) -> BatchFixProcessResult:
        """
        处理批量修复请求

        Args:
            requests: 修复分析请求列表

        Returns:
            批量修复流程结果
        """
        import uuid

        batch_id = str(uuid.uuid4())
        start_time = time.time()

        self.logger.info(
            f"Starting batch fix process {batch_id} for {len(requests)} files"
        )

        batch_result = BatchFixProcessResult(
            batch_id=batch_id,
            total_files=len(requests),
            start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        try:
            if self.parallel_processing and len(requests) > 1:
                # 并行处理
                batch_result.process_results = asyncio.run(
                    self._process_requests_parallel(requests)
                )
            else:
                # 串行处理
                batch_result.process_results = []
                for request in requests:
                    result = asyncio.run(self.process_fix_request(request))
                    batch_result.process_results.append(result)

                    # 如果某个文件处理失败严重，询问是否继续
                    if (
                        not result.success
                        and result.execution_result
                        and result.execution_result.status.value not in ["rolled_back"]
                    ):
                        if not self._ask_continue_on_batch_failure(
                            request.file_path, result.error_message
                        ):
                            self.logger.info(
                                f"Batch process cancelled due to failure in {request.file_path}"
                            )
                            break

            # 统计结果
            batch_result.successful_files = len(
                [r for r in batch_result.process_results if r.success]
            )
            batch_result.failed_files = (
                batch_result.total_files - batch_result.successful_files
            )

            # 生成批量报告
            if self.generate_reports:
                self._generate_batch_report(batch_result)

        except Exception as e:
            self.logger.error(f"Batch fix process {batch_id} failed: {e}")

        batch_result.total_time = time.time() - start_time
        batch_result.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
        batch_result.summary = self._generate_batch_summary(batch_result)

        self.logger.info(
            f"Batch fix process {batch_id} completed: {batch_result.summary}"
        )

        return batch_result

    async def _create_fix_request(self, request: FixAnalysisRequest) -> FixRequest:
        """创建修复请求"""
        file_path = Path(request.file_path)
        original_content = file_path.read_text(encoding="utf-8")

        return FixRequest(
            file_path=request.file_path,
            issues=request.issues,
            original_content=original_content,
            analysis_type=request.analysis_type,
            user_instructions=request.user_instructions,
            context=request.context,
        )

    async def _process_requests_parallel(
        self, requests: List[FixAnalysisRequest]
    ) -> List[FixProcessResult]:
        """并行处理请求"""
        # 分批处理
        batch_size = self.max_parallel_files
        all_results = []

        for i in range(0, len(requests), batch_size):
            batch = requests[i : i + batch_size]
            self.logger.info(
                f"Processing batch {i//batch_size + 1}: {len(batch)} files"
            )

            # 并发执行
            tasks = [self.process_fix_request(request) for request in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理异常
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    # 创建失败结果
                    error_result = FixProcessResult(
                        process_id=f"error_{i}_{j}",
                        file_path=batch[j].file_path,
                        success=False,
                        error_message=str(result),
                        stages_completed=[],
                    )
                    all_results.append(error_result)
                else:
                    all_results.append(result)

        return all_results

    def _generate_process_report(self, result: FixProcessResult):
        """生成单文件处理报告"""
        try:
            report_lines = [
                f"修复处理报告 - {result.file_path}",
                f"=" * 60,
                f"处理ID: {result.process_id}",
                f"处理时间: {result.total_time:.2f}秒",
                f"成功状态: {'成功' if result.success else '失败'}",
                f"完成的阶段: {', '.join(result.stages_completed)}",
                "",
            ]

            if result.error_message:
                report_lines.extend([f"错误信息: {result.error_message}", ""])

            if result.fix_result:
                report_lines.extend(
                    [
                        f"修复建议数: {len(result.fix_result.suggestions)}",
                        f"使用模型: {result.fix_result.model_used}",
                        f"Token使用: {result.fix_result.token_usage.get('total_tokens', 0)}",
                        "",
                    ]
                )

            if result.backup_result:
                report_lines.extend(
                    [
                        f"备份ID: {result.backup_result.backup_id}",
                        f"备份文件: {result.backup_result.backup_path}",
                        "",
                    ]
                )

            if result.diff_result:
                report_lines.extend(
                    [
                        f"差异摘要: {result.diff_result.summary}",
                        f"变更统计: {result.diff_result.stats}",
                        "",
                    ]
                )

            if result.confirmation_response:
                report_lines.extend(
                    [
                        f"确认状态: {result.confirmation_response.status.value}",
                        f"用户消息: {result.confirmation_response.user_message}",
                        "",
                    ]
                )

            if result.execution_result:
                report_lines.extend(
                    [
                        f"执行状态: {result.execution_result.status.value}",
                        f"应用的修复数: {len(result.execution_result.applied_suggestions)}",
                        "",
                    ]
                )

            # 写入报告文件
            report_file = self.report_output_dir / f"fix_report_{result.process_id}.txt"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))

            self.logger.info(f"Process report generated: {report_file}")

        except Exception as e:
            self.logger.error(f"Failed to generate process report: {e}")

    def _generate_batch_report(self, batch_result: BatchFixProcessResult):
        """生成批量处理报告"""
        try:
            report_lines = [
                f"批量修复处理报告",
                f"=" * 60,
                f"批次ID: {batch_result.batch_id}",
                f"开始时间: {batch_result.start_time}",
                f"结束时间: {batch_result.end_time}",
                f"总处理时间: {batch_result.total_time:.2f}秒",
                f"总文件数: {batch_result.total_files}",
                f"成功文件数: {batch_result.successful_files}",
                f"失败文件数: {batch_result.failed_files}",
                f"成功率: {batch_result.successful_files/batch_result.total_files:.1%}",
                "",
            ]

            # 详细结果
            report_lines.append("详细处理结果:")
            report_lines.append("-" * 40)

            for i, result in enumerate(batch_result.process_results, 1):
                status_icon = "✅" if result.success else "❌"
                report_lines.append(f"{i}. {status_icon} {result.file_path}")
                report_lines.append(f"   处理时间: {result.total_time:.2f}秒")
                report_lines.append(
                    f"   完成阶段: {', '.join(result.stages_completed)}"
                )
                if result.error_message:
                    report_lines.append(f"   错误: {result.error_message}")
                report_lines.append("")

            # 统计信息
            if batch_result.process_results:
                successful_results = [
                    r for r in batch_result.process_results if r.success
                ]
                if successful_results:
                    avg_time = sum(r.total_time for r in successful_results) / len(
                        successful_results
                    )
                    report_lines.extend(
                        [
                            "统计信息:",
                            f"  平均处理时间: {avg_time:.2f}秒",
                            f"  总修复建议数: {sum(len(r.fix_result.suggestions) for r in successful_results if r.fix_result)}",
                            f"  总备份数: {sum(1 for r in successful_results if r.backup_result and r.backup_result.success)}",
                            "",
                        ]
                    )

            # 写入报告文件
            report_file = (
                self.report_output_dir / f"batch_fix_report_{batch_result.batch_id}.txt"
            )
            with open(report_file, "w", encoding="utf-8") as f:
                f.write("\n".join(report_lines))

            self.logger.info(f"Batch report generated: {report_file}")

        except Exception as e:
            self.logger.error(f"Failed to generate batch report: {e}")

    def _ask_continue_on_batch_failure(
        self, file_path: str, error_message: str
    ) -> bool:
        """询问是否在批量处理失败时继续"""
        try:
            print(f"\n批量处理失败: {file_path}")
            print(f"错误信息: {error_message}")
            choice = input("是否继续处理其他文件? (y/n): ").strip().lower()
            return choice in ["y", "yes"]
        except (KeyboardInterrupt, EOFError):
            return False

    def _generate_batch_summary(self, batch_result: BatchFixProcessResult) -> str:
        """生成批量处理摘要"""
        if batch_result.successful_files == batch_result.total_files:
            return f"所有文件修复成功 (耗时: {batch_result.total_time:.2f}秒)"
        elif batch_result.successful_files > 0:
            return f"{batch_result.successful_files}/{batch_result.total_files} 文件修复成功 (耗时: {batch_result.total_time:.2f}秒)"
        else:
            return f"所有文件修复失败 (耗时: {batch_result.total_time:.2f}秒)"

    def get_process_statistics(
        self, process_results: List[FixProcessResult]
    ) -> Dict[str, Any]:
        """获取处理统计信息"""
        try:
            total_files = len(process_results)
            successful_files = len([r for r in process_results if r.success])
            failed_files = total_files - successful_files

            total_time = sum(r.total_time for r in process_results)
            avg_time = total_time / total_files if total_files > 0 else 0

            # 阶段完成统计
            stage_stats = {}
            for result in process_results:
                for stage in result.stages_completed:
                    stage_stats[stage] = stage_stats.get(stage, 0) + 1

            # 错误统计
            error_stats = {}
            for result in process_results:
                if result.error_message:
                    error_type = result.error_message.split(":")[0]
                    error_stats[error_type] = error_stats.get(error_type, 0) + 1

            return {
                "total_files": total_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "success_rate": (
                    successful_files / total_files if total_files > 0 else 0
                ),
                "total_time": total_time,
                "average_time": avg_time,
                "stage_completion_stats": stage_stats,
                "error_distribution": error_stats,
            }

        except Exception as e:
            self.logger.error(f"Failed to get process statistics: {e}")
            return {}

    def set_confirmation_callback(self, callback):
        """设置确认回调函数"""
        self.confirmation_manager.set_confirmation_callback(callback)

    def get_supported_analysis_types(self) -> List[str]:
        """获取支持的分析类型"""
        return self.fix_generator.get_supported_fix_types()

    def validate_fix_request(self, request: FixAnalysisRequest) -> Tuple[bool, str]:
        """验证修复请求"""
        try:
            # 检查文件路径
            if not Path(request.file_path).exists():
                return False, f"File does not exist: {request.file_path}"

            # 检查问题列表
            if not request.issues:
                return False, "No issues provided for fix"

            # 检查分析类型
            if request.analysis_type not in self.get_supported_analysis_types():
                return False, f"Unsupported analysis type: {request.analysis_type}"

            return True, "Request is valid"

        except Exception as e:
            return False, f"Validation error: {e}"
