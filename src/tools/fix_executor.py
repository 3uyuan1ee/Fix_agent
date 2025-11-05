"""
修复执行引擎
负责根据用户确认执行实际的代码修复操作
"""

import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.config import get_config_manager
from ..utils.logger import get_logger
from .backup_manager import BackupManager, BackupResult
from .diff_viewer import DiffResult, DiffViewer
from .fix_confirmation import ConfirmationResponse, ConfirmationStatus
from .fix_generator import FixResult, FixSuggestion


class ExecutionStatus(Enum):
    """执行状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ExecutionResult:
    """执行结果"""

    fix_id: str
    file_path: str
    status: ExecutionStatus
    success: bool
    backup_id: str
    original_content: str
    fixed_content: str
    applied_suggestions: List[FixSuggestion] = field(default_factory=list)
    execution_time: float = 0.0
    error_message: Optional[str] = None
    rollback_successful: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "fix_id": self.fix_id,
            "file_path": self.file_path,
            "status": self.status.value,
            "success": self.success,
            "backup_id": self.backup_id,
            "execution_time": self.execution_time,
            "error_message": self.error_message,
            "rollback_successful": self.rollback_successful,
            "applied_suggestions_count": len(self.applied_suggestions),
            "metadata": self.metadata,
        }


@dataclass
class BatchExecutionResult:
    """批量执行结果"""

    batch_id: str
    total_files: int
    successful_files: int
    failed_files: int
    rolled_back_files: int
    execution_results: List[ExecutionResult] = field(default_factory=list)
    total_execution_time: float = 0.0
    start_time: str = ""
    end_time: str = ""
    summary: str = ""


class FixExecutor:
    """修复执行引擎"""

    def __init__(self, config_manager=None):
        """
        初始化修复执行引擎

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 初始化组件
        self.backup_manager = BackupManager(config_manager)
        self.diff_viewer = DiffViewer(config_manager)

        # 获取配置
        try:
            self.config = self.config_manager.get_section("fix_executor")
        except:
            self.config = {}

        self.create_backup_before_fix = self.config.get(
            "create_backup_before_fix", True
        )
        self.validate_syntax_after_fix = self.config.get(
            "validate_syntax_after_fix", True
        )
        self.auto_rollback_on_error = self.config.get("auto_rollback_on_error", True)
        self.use_temp_file_for_write = self.config.get("use_temp_file_for_write", True)
        self.preserve_permissions = self.config.get("preserve_permissions", True)

        self.logger.info("FixExecutor initialized")

    async def execute_fix(
        self,
        fix_id: str,
        file_path: str,
        fix_result: FixResult,
        confirmation_response: ConfirmationResponse,
        backup_id: Optional[str] = None,
    ) -> ExecutionResult:
        """
        执行单个文件修复

        Args:
            fix_id: 修复ID
            file_path: 文件路径
            fix_result: 修复结果
            confirmation_response: 确认响应
            backup_id: 备份ID

        Returns:
            执行结果
        """
        start_time = time.time()

        self.logger.info(f"Executing fix {fix_id} for {file_path}")

        result = ExecutionResult(
            fix_id=fix_id,
            file_path=file_path,
            status=ExecutionStatus.PENDING,
            success=False,
            backup_id=backup_id or "",
            original_content="",
            fixed_content="",
        )

        try:
            file_path = Path(file_path)

            # 1. 读取原始内容
            if not file_path.exists():
                result.error_message = f"File does not exist: {file_path}"
                result.status = ExecutionStatus.FAILED
                return result

            result.original_content = file_path.read_text(encoding="utf-8")

            # 2. 创建备份（如果需要且尚未创建）
            if self.create_backup_before_fix and not backup_id:
                backup_result = self.backup_manager.create_backup(
                    str(file_path), reason="pre_fix_execution", fix_request_id=fix_id
                )
                if backup_result.success:
                    result.backup_id = backup_result.backup_id
                    self.logger.info(f"Created backup: {backup_result.backup_id}")
                else:
                    self.logger.warning(
                        f"Failed to create backup: {backup_result.error}"
                    )

            # 3. 根据确认响应确定要应用的修复
            applied_suggestions = self._select_suggestions_to_apply(
                fix_result.suggestions, confirmation_response
            )
            result.applied_suggestions = applied_suggestions

            if not applied_suggestions:
                self.logger.info(f"No suggestions to apply for fix {fix_id}")
                result.status = ExecutionStatus.COMPLETED
                result.success = True
                return result

            # 4. 生成修复后的内容
            fixed_content = self._apply_fixes(
                result.original_content, applied_suggestions, confirmation_response
            )
            result.fixed_content = fixed_content

            # 5. 验证修复后内容
            if self.validate_syntax_after_fix:
                if not self._validate_syntax(fixed_content, str(file_path)):
                    result.error_message = "Fixed code contains syntax errors"
                    result.status = ExecutionStatus.FAILED
                    return result

            # 6. 写入修复后的文件
            self._write_fixed_file(file_path, fixed_content, result.original_content)

            # 7. 验证修复结果
            if not self._verify_fix_result(
                file_path, result.original_content, fixed_content
            ):
                result.error_message = "Fix verification failed"
                if self.auto_rollback_on_error:
                    self._rollback_fix(file_path, result.original_content)
                    result.rollback_successful = True
                    result.status = ExecutionStatus.ROLLED_BACK
                else:
                    result.status = ExecutionStatus.FAILED
                return result

            # 8. 成功完成
            result.status = ExecutionStatus.COMPLETED
            result.success = True
            result.metadata = {
                "applied_suggestions_count": len(applied_suggestions),
                "total_suggestions_count": len(fix_result.suggestions),
                "file_size": len(fixed_content),
                "backup_created": bool(result.backup_id),
                "syntax_validated": self.validate_syntax_after_fix,
            }

            self.logger.info(f"Fix {fix_id} executed successfully for {file_path}")

        except Exception as e:
            result.error_message = str(e)
            result.status = ExecutionStatus.FAILED
            self.logger.error(f"Fix execution failed for {file_path}: {e}")

            # 自动回滚
            if self.auto_rollback_on_error and result.original_content:
                try:
                    self._rollback_fix(file_path, result.original_content)
                    result.rollback_successful = True
                    result.status = ExecutionStatus.ROLLED_BACK
                    self.logger.info(f"Auto-rollback completed for {file_path}")
                except Exception as rollback_error:
                    self.logger.error(
                        f"Auto-rollback failed for {file_path}: {rollback_error}"
                    )

        result.execution_time = time.time() - start_time
        return result

    def execute_batch_fixes(
        self,
        fix_requests: List[
            Tuple[str, str, FixResult, ConfirmationResponse, Optional[str]]
        ],
    ) -> BatchExecutionResult:
        """
        批量执行修复

        Args:
            fix_requests: 修复请求列表 (fix_id, file_path, fix_result, confirmation_response, backup_id)

        Returns:
            批量执行结果
        """
        import asyncio
        import uuid

        start_time = time.time()
        batch_id = str(uuid.uuid4())

        self.logger.info(
            f"Starting batch fix execution {batch_id} for {len(fix_requests)} files"
        )

        batch_result = BatchExecutionResult(
            batch_id=batch_id,
            total_files=len(fix_requests),
            start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

        try:
            # 逐个执行修复（避免并发问题）
            for (
                fix_id,
                file_path,
                fix_result,
                confirmation_response,
                backup_id,
            ) in fix_requests:
                self.logger.info(f"Executing fix {fix_id} for {file_path}")

                # 同步执行单个修复
                execution_result = asyncio.run(
                    self.execute_fix(
                        fix_id, file_path, fix_result, confirmation_response, backup_id
                    )
                )

                batch_result.execution_results.append(execution_result)

                # 更新统计
                if execution_result.success:
                    batch_result.successful_files += 1
                else:
                    batch_result.failed_files += 1
                    if execution_result.status == ExecutionStatus.ROLLED_BACK:
                        batch_result.rolled_back_files += 1

                # 如果某个修复失败严重，询问是否继续
                if (
                    not execution_result.success
                    and execution_result.status != ExecutionStatus.ROLLED_BACK
                ):
                    if not self._ask_continue_on_failure(
                        file_path, execution_result.error_message
                    ):
                        self.logger.info(
                            f"Batch execution cancelled due to failure in {file_path}"
                        )
                        break

        except Exception as e:
            self.logger.error(f"Batch fix execution failed: {e}")

        # 完成批量执行
        batch_result.total_execution_time = time.time() - start_time
        batch_result.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
        batch_result.summary = self._generate_batch_summary(batch_result)

        self.logger.info(
            f"Batch fix execution {batch_id} completed: {batch_result.summary}"
        )

        return batch_result

    def rollback_fix(self, file_path: str, backup_id: str) -> bool:
        """
        回滚修复

        Args:
            file_path: 文件路径
            backup_id: 备份ID

        Returns:
            是否回滚成功
        """
        try:
            self.logger.info(
                f"Rolling back fix for {file_path} using backup {backup_id}"
            )

            success = self.backup_manager.restore_backup(backup_id, str(file_path))

            if success:
                self.logger.info(f"Rollback successful for {file_path}")
            else:
                self.logger.error(f"Rollback failed for {file_path}")

            return success

        except Exception as e:
            self.logger.error(f"Error during rollback for {file_path}: {e}")
            return False

    def rollback_batch_fixes(
        self, execution_results: List[ExecutionResult]
    ) -> Dict[str, bool]:
        """
        批量回滚修复

        Args:
            execution_results: 执行结果列表

        Returns:
            回滚结果字典 {file_path: success}
        """
        self.logger.info(f"Starting batch rollback for {len(execution_results)} files")

        rollback_results = {}

        for result in execution_results:
            if result.success and result.backup_id:
                success = self.rollback_fix(result.file_path, result.backup_id)
                rollback_results[result.file_path] = success
            else:
                rollback_results[result.file_path] = True  # 无需回滚

        successful_rollbacks = sum(
            1 for success in rollback_results.values() if success
        )
        self.logger.info(
            f"Batch rollback completed: {successful_rollbacks}/{len(execution_results)} successful"
        )

        return rollback_results

    def _select_suggestions_to_apply(
        self,
        suggestions: List[FixSuggestion],
        confirmation_response: ConfirmationResponse,
    ) -> List[FixSuggestion]:
        """选择要应用的修复建议"""
        if confirmation_response.status == ConfirmationStatus.APPROVED:
            # 批准所有建议
            return suggestions.copy()
        elif confirmation_response.status == ConfirmationStatus.PARTIAL:
            # 部分批准，使用选中的建议
            selected_indices = confirmation_response.selected_suggestions
            return [
                suggestions[i] for i in selected_indices if 0 <= i < len(suggestions)
            ]
        else:
            # 拒绝或取消，不应用任何建议
            return []

    def _apply_fixes(
        self,
        original_content: str,
        suggestions: List[FixSuggestion],
        confirmation_response: ConfirmationResponse,
    ) -> str:
        """应用修复建议"""
        if not suggestions:
            return original_content

        try:
            # 如果有完整的修复内容，优先使用
            if (
                confirmation_response.metadata
                and "complete_fixed_content" in confirmation_response.metadata
            ):
                return confirmation_response.metadata["complete_fixed_content"]

            # 否则应用选中的建议
            lines = original_content.split("\n")

            # 按行号排序，从后往前应用（避免行号偏移）
            sorted_suggestions = sorted(
                [s for s in suggestions if s.location.get("line") and s.fixed_code],
                key=lambda x: x.location["line"],
                reverse=True,
            )

            for suggestion in sorted_suggestions:
                line_num = suggestion.location["line"] - 1  # 转换为0-based索引

                if 0 <= line_num < len(lines):
                    # 替换指定行
                    if "\n" in suggestion.fixed_code:
                        # 多行修复
                        fixed_lines = suggestion.fixed_code.split("\n")
                        lines[line_num : line_num + 1] = fixed_lines
                    else:
                        # 单行修复
                        lines[line_num] = suggestion.fixed_code

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"Error applying fixes: {e}")
            return original_content

    def _validate_syntax(self, content: str, file_path: str) -> bool:
        """验证语法"""
        try:
            compile(content, file_path, "exec")
            return True
        except SyntaxError as e:
            self.logger.warning(f"Syntax error in fixed code: {e}")
            return False
        except Exception as e:
            self.logger.warning(f"Error validating syntax: {e}")
            return False

    def _write_fixed_file(
        self, file_path: Path, fixed_content: str, original_content: str
    ):
        """写入修复后的文件"""
        try:
            if self.use_temp_file_for_write:
                # 使用临时文件写入
                temp_file = file_path.with_suffix(file_path.suffix + ".tmp")
                temp_file.write_text(fixed_content, encoding="utf-8")

                # 验证临时文件
                if temp_file.read_text(encoding="utf-8") == fixed_content:
                    # 替换原文件
                    if self.preserve_permissions:
                        # 保留权限
                        shutil.copystat(file_path, temp_file)
                    shutil.move(str(temp_file), str(file_path))
                else:
                    raise IOError("Temporary file verification failed")
            else:
                # 直接写入
                file_path.write_text(fixed_content, encoding="utf-8")

            self.logger.debug(f"Fixed file written: {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to write fixed file {file_path}: {e}")
            raise

    def _verify_fix_result(
        self, file_path: Path, original_content: str, fixed_content: str
    ) -> bool:
        """验证修复结果"""
        try:
            # 读取写入的文件内容
            written_content = file_path.read_text(encoding="utf-8")

            # 验证内容是否匹配
            if written_content != fixed_content:
                self.logger.error(f"Content mismatch in {file_path}")
                return False

            # 验证文件不为空（如果原文件不为空）
            if original_content and not written_content.strip():
                self.logger.warning(f"Fixed file is empty: {file_path}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error verifying fix result for {file_path}: {e}")
            return False

    def _rollback_fix(self, file_path: Path, original_content: str):
        """回滚修复"""
        try:
            file_path.write_text(original_content, encoding="utf-8")
            self.logger.info(f"File rolled back: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to rollback file {file_path}: {e}")
            raise

    def _ask_continue_on_failure(self, file_path: str, error_message: str) -> bool:
        """询问是否在失败时继续"""
        try:
            print(f"\n修复失败: {file_path}")
            print(f"错误信息: {error_message}")
            choice = input("是否继续处理其他文件? (y/n): ").strip().lower()
            return choice in ["y", "yes"]
        except (KeyboardInterrupt, EOFError):
            return False

    def _generate_batch_summary(self, batch_result: BatchExecutionResult) -> str:
        """生成批量执行摘要"""
        parts = []

        if batch_result.successful_files > 0:
            parts.append(f"{batch_result.successful_files} 成功")
        if batch_result.failed_files > 0:
            parts.append(f"{batch_result.failed_files} 失败")
        if batch_result.rolled_back_files > 0:
            parts.append(f"{batch_result.rolled_back_files} 已回滚")

        if not parts:
            return "无文件处理"

        return f"批量修复完成: {', '.join(parts)} (总耗时: {batch_result.total_execution_time:.2f}秒)"

    def get_execution_statistics(
        self, execution_results: List[ExecutionResult]
    ) -> Dict[str, Any]:
        """获取执行统计信息"""
        try:
            total_files = len(execution_results)
            successful_files = len([r for r in execution_results if r.success])
            failed_files = total_files - successful_files
            rolled_back_files = len(
                [
                    r
                    for r in execution_results
                    if r.status == ExecutionStatus.ROLLED_BACK
                ]
            )

            total_time = sum(r.execution_time for r in execution_results)
            avg_time = total_time / total_files if total_files > 0 else 0

            # 按状态统计
            status_counts = {}
            for result in execution_results:
                status = result.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

            # 按错误类型统计
            error_counts = {}
            for result in execution_results:
                if result.error_message:
                    error_type = result.error_message.split(":")[0]
                    error_counts[error_type] = error_counts.get(error_type, 0) + 1

            return {
                "total_files": total_files,
                "successful_files": successful_files,
                "failed_files": failed_files,
                "rolled_back_files": rolled_back_files,
                "success_rate": (
                    successful_files / total_files if total_files > 0 else 0
                ),
                "total_execution_time": total_time,
                "average_execution_time": avg_time,
                "status_distribution": status_counts,
                "error_distribution": error_counts,
            }

        except Exception as e:
            self.logger.error(f"Failed to get execution statistics: {e}")
            return {}
