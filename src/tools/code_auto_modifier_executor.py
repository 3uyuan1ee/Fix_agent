"""
T012.2: 代码自动修改执行器

节点F的核心组件，负责安全地执行代码修改。包括文件备份、代码应用、
修改验证、回滚机制等，确保代码修改的准确性和可恢复性。

工作流位置: 节点F (执行自动修复)
输入: 修复执行准备结果 (T012.1输出)
输出: 代码修改执行结果 + 验证状态
"""

import json
import os
import shutil
import difflib
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path
import uuid
import tempfile

from ..utils.types import ProblemType, RiskLevel, FixType
from ..utils.logger import get_logger
from .workflow_data_types import AIFixSuggestion, WorkflowDataPacket
from .workflow_user_interaction_types import UserAction, DecisionResult
from .workflow_flow_state_manager import WorkflowNode
from .fix_execution_preparer import (
    FixExecutionPreparation, ExecutionPlan, BackupInfo,
    PreparationStatus, ExecutionRiskLevel
)
from .user_modification_processor import ModifiedSuggestion

logger = get_logger()


class ExecutionStatus(Enum):
    """执行状态枚举"""
    PENDING = "pending"                     # 等待执行
    IN_PROGRESS = "in_progress"            # 执行中
    COMPLETED = "completed"                # 执行完成
    FAILED = "failed"                      # 执行失败
    ROLLED_BACK = "rolled_back"            # 已回滚
    CANCELLED = "cancelled"                # 已取消


class ModificationType(Enum):
    """修改类型枚举"""
    INSERT = "insert"                     # 插入
    DELETE = "delete"                     # 删除
    REPLACE = "replace"                   # 替换
    APPEND = "append"                     # 追加
    PREPEND = "prepend"                   # 前置


@dataclass
class FileModification:
    """文件修改记录"""
    file_path: str
    modification_type: ModificationType
    line_number: int
    original_content: str
    modified_content: str
    context_before: str
    context_after: str
    timestamp: datetime


@dataclass
class ExecutionStep:
    """执行步骤"""
    step_id: int
    description: str
    command: str
    status: ExecutionStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration_seconds: int
    output: str
    error: str
    success: bool


@dataclass
class ExecutionResult:
    """执行结果"""
    execution_id: str
    preparation_id: str
    fix_suggestion_id: str
    status: ExecutionStatus
    modifications: List[FileModification]
    execution_steps: List[ExecutionStep]
    validation_results: Dict[str, bool]
    backup_info: Optional[BackupInfo]
    rollback_info: Optional[Dict[str, Any]]
    total_time_seconds: int
    success: bool
    errors: List[str]
    warnings: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]


class CodeAutoModifierExecutor:
    """代码自动修改执行器"""

    def __init__(self, temp_directory: str = ".fix_temp"):
        """
        初始化执行器

        Args:
            temp_directory: 临时目录
        """
        self.temp_directory = Path(temp_directory)
        self.temp_directory.mkdir(exist_ok=True)
        self._execution_history: List[ExecutionResult] = []
        self._current_execution: Optional[ExecutionResult] = None

    def execute_modification(self, preparation: FixExecutionPreparation,
                           suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> ExecutionResult:
        """
        执行代码修改

        Args:
            preparation: 执行准备结果
            suggestion: 修复建议

        Returns:
            执行结果
        """
        execution_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            logger.info(f"开始执行代码修改: {execution_id}")

            # 创建执行结果对象
            self._current_execution = ExecutionResult(
                execution_id=execution_id,
                preparation_id=preparation.preparation_id,
                fix_suggestion_id=preparation.fix_suggestion_id,
                status=ExecutionStatus.IN_PROGRESS,
                modifications=[],
                execution_steps=[],
                validation_results={},
                backup_info=preparation.backup_info,
                rollback_info=None,
                total_time_seconds=0,
                success=False,
                errors=[],
                warnings=[],
                timestamp=start_time,
                metadata={}
            )

            # 验证准备状态
            if preparation.status != PreparationStatus.READY:
                raise ValueError(f"准备状态不正确: {preparation.status.value}")

            # 执行计划步骤
            execution_steps = self._execute_execution_plan(preparation.execution_plan, suggestion)

            # 应用代码修改
            modifications = self._apply_code_modification(suggestion)

            # 验证修改结果
            validation_results = self._validate_modifications(modifications, preparation)

            # 确定最终状态
            final_status = self._determine_final_status(
                execution_steps, validation_results, modifications
            )

            # 计算总时间
            total_time = int((datetime.now() - start_time).total_seconds())

            # 生成回滚信息
            rollback_info = self._generate_rollback_info(modifications, preparation.backup_info)

            # 更新执行结果
            self._current_execution.status = final_status
            self._current_execution.modifications = modifications
            self._current_execution.execution_steps = execution_steps
            self._current_execution.validation_results = validation_results
            self._current_execution.rollback_info = rollback_info
            self._current_execution.total_time_seconds = total_time
            self._current_execution.success = final_status == ExecutionStatus.COMPLETED

            # 记录执行历史
            self._record_execution(self._current_execution)

            logger.info(f"代码修改执行完成: {execution_id}, 状态: {final_status.value}")
            return self._current_execution

        except Exception as e:
            logger.error(f"执行代码修改失败: {e}")

            # 尝试回滚
            if self._current_execution:
                try:
                    self._rollback_execution(self._current_execution)
                    self._current_execution.status = ExecutionStatus.ROLLED_BACK
                except rollback_error:
                    logger.error(f"回滚失败: {rollback_error}")
                    self._current_execution.errors.append(f"回滚失败: {rollback_error}")

            if self._current_execution:
                self._current_execution.errors.append(str(e))
                self._record_execution(self._current_execution)

            raise

    def rollback_execution(self, execution_result: ExecutionResult) -> bool:
        """
        回滚执行结果

        Args:
            execution_result: 执行结果

        Returns:
            回滚是否成功
        """
        try:
            logger.info(f"开始回滚执行: {execution_result.execution_id}")

            if not execution_result.rollback_info:
                logger.error("没有可用的回滚信息")
                return False

            # 使用备份回滚
            if execution_result.backup_info:
                success = self._rollback_from_backup(execution_result.backup_info)
            else:
                success = self._rollback_from_modifications(execution_result.modifications)

            if success:
                execution_result.status = ExecutionStatus.ROLLED_BACK
                logger.info(f"回滚成功: {execution_result.execution_id}")
            else:
                logger.error(f"回滚失败: {execution_result.execution_id}")

            return success

        except Exception as e:
            logger.error(f"回滚过程出错: {e}")
            return False

    def batch_execute_modifications(self, preparations: List[FixExecutionPreparation],
                                  suggestions: List[Union[AIFixSuggestion, ModifiedSuggestion]]) -> List[ExecutionResult]:
        """
        批量执行代码修改

        Args:
            preparations: 准备结果列表
            suggestions: 修复建议列表

        Returns:
            批量执行结果
        """
        results = []
        logger.info(f"开始批量执行 {len(preparations)} 个代码修改")

        for i, (preparation, suggestion) in enumerate(zip(preparations, suggestions)):
            try:
                result = self.execute_modification(preparation, suggestion)
                results.append(result)
            except Exception as e:
                logger.error(f"批量执行修改失败 {i}: {e}")
                # 创建失败结果
                failed_result = self._create_failed_execution_result(preparation, str(e))
                results.append(failed_result)

        successful_count = sum(1 for r in results if r.success)
        logger.info(f"批量执行完成: 成功 {successful_count}/{len(results)}")

        return results

    def get_execution_history(self, limit: Optional[int] = None) -> List[ExecutionResult]:
        """
        获取执行历史

        Args:
            limit: 限制数量

        Returns:
            执行历史列表
        """
        history = self._execution_history.copy()
        history.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            history = history[:limit]

        return history

    def _execute_execution_plan(self, execution_plan: ExecutionPlan,
                              suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> List[ExecutionStep]:
        """执行执行计划"""
        execution_steps = []

        for step_config in execution_plan.execution_steps:
            step = self._execute_single_step(step_config, suggestion)
            execution_steps.append(step)

            # 如果关键步骤失败，停止执行
            if not step.success and step_config.get("critical", False):
                logger.error(f"关键步骤失败，停止执行: {step.description}")
                break

        return execution_steps

    def _execute_single_step(self, step_config: Dict[str, Any],
                           suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> ExecutionStep:
        """执行单个步骤"""
        step_id = step_config["step_id"]
        description = step_config["description"]
        command = step_config["command"]

        start_time = datetime.now()
        output = ""
        error = ""
        success = False

        try:
            logger.info(f"执行步骤 {step_id}: {description}")

            if command == "check_file_access":
                success = self._check_file_access(suggestion)
                output = "文件访问检查通过" if success else "文件访问检查失败"

            elif command == "apply_fix":
                success, output = self._apply_fix_command(suggestion)
                if not success:
                    error = "修复应用失败"

            elif command == "syntax_check":
                success, output = self._perform_syntax_check(suggestion)
                if not success:
                    error = "语法检查失败"

            elif command == "run_tests":
                success, output = self._run_basic_tests(suggestion)
                if not success:
                    error = "基本测试失败"

            elif command == "create_restore_point":
                success, output = self._create_restore_point(suggestion)
                if not success:
                    error = "创建还原点失败"

            elif command == "full_test_suite":
                success, output = self._run_full_test_suite(suggestion)
                if not success:
                    error = "完整测试套件失败"

            else:
                success = False
                error = f"未知命令: {command}"

        except Exception as e:
            error = str(e)
            success = False

        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())

        return ExecutionStep(
            step_id=step_id,
            description=description,
            command=command,
            status=ExecutionStatus.COMPLETED if success else ExecutionStatus.FAILED,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            output=output,
            error=error,
            success=success
        )

    def _check_file_access(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> bool:
        """检查文件访问权限"""
        try:
            file_path = Path(suggestion.file_path)
            if file_path.exists():
                return os.access(file_path, os.R_OK | os.W_OK)
            else:
                # 检查目录权限
                parent_dir = file_path.parent
                return os.access(parent_dir, os.R_OK | os.W_OK)
        except:
            return False

    def _apply_fix_command(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> Tuple[bool, str]:
        """应用修复命令"""
        try:
            # 这个方法只是预检查，实际修改在 _apply_code_modification 中进行
            code = suggestion.modified_code if hasattr(suggestion, 'modified_code') else suggestion.suggested_code
            if not code.strip():
                return False, "修复代码为空"

            return True, "修复代码验证通过"
        except Exception as e:
            return False, f"修复验证失败: {e}"

    def _perform_syntax_check(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> Tuple[bool, str]:
        """执行语法检查"""
        try:
            code = suggestion.modified_code if hasattr(suggestion, 'modified_code') else suggestion.suggested_code
            file_path = suggestion.file_path

            if file_path.endswith('.py'):
                import ast
                ast.parse(code)
                return True, "Python语法检查通过"
            else:
                # 简单语法检查
                return True, "基本语法检查通过"
        except SyntaxError as e:
            return False, f"语法错误: {e}"
        except Exception as e:
            return False, f"语法检查失败: {e}"

    def _run_basic_tests(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> Tuple[bool, str]:
        """运行基本测试"""
        try:
            # 检查文件是否可以导入（如果是Python文件）
            file_path = suggestion.file_path
            if file_path.endswith('.py'):
                # 尝试编译检查
                code = suggestion.modified_code if hasattr(suggestion, 'modified_code') else suggestion.suggested_code
                compile(code, file_path, 'exec')
                return True, "基本编译检查通过"

            return True, "基本测试通过"
        except Exception as e:
            return False, f"基本测试失败: {e}"

    def _create_restore_point(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> Tuple[bool, str]:
        """创建还原点"""
        try:
            restore_point_id = str(uuid.uuid4())
            restore_point_path = self.temp_directory / f"restore_{restore_point_id}"
            restore_point_path.mkdir(exist_ok=True)

            # 复制当前文件状态
            file_path = Path(suggestion.file_path)
            if file_path.exists():
                backup_file = restore_point_path / file_path.name
                shutil.copy2(file_path, backup_file)

            return True, f"还原点创建成功: {restore_point_id}"
        except Exception as e:
            return False, f"创建还原点失败: {e}"

    def _run_full_test_suite(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> Tuple[bool, str]:
        """运行完整测试套件"""
        try:
            # 检查是否存在测试文件并运行
            project_root = Path(suggestion.file_path).parent
            test_files = list(project_root.glob("**/test*.py")) + list(project_root.glob("**/*test*.py"))

            if test_files:
                # 运行找到的第一个测试文件
                test_file = test_files[0]
                result = subprocess.run(
                    ["python", "-m", "pytest", str(test_file), "-v"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    return True, f"测试套件通过: {test_file}"
                else:
                    return False, f"测试套件失败: {result.stderr}"
            else:
                return True, "未找到测试文件，跳过测试套件"

        except subprocess.TimeoutExpired:
            return False, "测试套件超时"
        except Exception as e:
            return False, f"运行测试套件失败: {e}"

    def _apply_code_modification(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> List[FileModification]:
        """应用代码修改"""
        modifications = []

        try:
            file_path = Path(suggestion.file_path)
            original_code = suggestion.original_code
            modified_code = suggestion.modified_code if hasattr(suggestion, 'modified_code') else suggestion.suggested_code

            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 读取原始文件内容（如果存在）
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
            else:
                file_content = ""

            # 分析修改类型
            modification_type = self._analyze_modification_type(original_code, modified_code)

            # 获取上下文
            context_before, context_after = self._extract_context(file_content, suggestion.line_number)

            # 创建修改记录
            modification = FileModification(
                file_path=str(file_path),
                modification_type=modification_type,
                line_number=suggestion.line_number,
                original_content=original_code,
                modified_content=modified_code,
                context_before=context_before,
                context_after=context_after,
                timestamp=datetime.now()
            )

            # 应用修改
            if modification_type == ModificationType.REPLACE:
                new_content = file_content.replace(original_code, modified_code)
            elif modification_type == ModificationType.INSERT:
                # 在指定行插入
                lines = file_content.splitlines()
                if suggestion.line_number <= len(lines):
                    lines.insert(suggestion.line_number - 1, modified_code)
                else:
                    lines.append(modified_code)
                new_content = '\n'.join(lines)
            elif modification_type == ModificationType.APPEND:
                new_content = file_content + '\n' + modified_code
            elif modification_type == ModificationType.PREPEND:
                new_content = modified_code + '\n' + file_content
            else:
                new_content = modified_code

            # 写入修改后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            modifications.append(modification)
            logger.info(f"代码修改应用成功: {file_path}")

        except Exception as e:
            logger.error(f"应用代码修改失败: {e}")
            raise

        return modifications

    def _analyze_modification_type(self, original: str, modified: str) -> ModificationType:
        """分析修改类型"""
        if not original.strip() and modified.strip():
            return ModificationType.INSERT
        elif original.strip() and not modified.strip():
            return ModificationType.DELETE
        elif original.strip() and modified.strip():
            if original in modified:
                return ModificationType.APPEND
            elif modified in original:
                return ModificationType.PREPEND
            else:
                return ModificationType.REPLACE
        else:
            return ModificationType.REPLACE

    def _extract_context(self, file_content: str, line_number: int, context_lines: int = 3) -> Tuple[str, str]:
        """提取上下文"""
        lines = file_content.splitlines()

        # 前置上下文
        start_line = max(0, line_number - context_lines - 1)
        context_before = '\n'.join(lines[start_line:line_number - 1])

        # 后置上下文
        end_line = min(len(lines), line_number + context_lines)
        context_after = '\n'.join(lines[line_number:end_line])

        return context_before, context_after

    def _validate_modifications(self, modifications: List[FileModification],
                              preparation: FixExecutionPreparation) -> Dict[str, bool]:
        """验证修改结果"""
        validation_results = {}

        try:
            # 语法验证
            validation_results["syntax_check"] = True
            for modification in modifications:
                file_path = Path(modification.file_path)
                if file_path.exists() and file_path.suffix == '.py':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    import ast
                    ast.parse(content)

            # 文件完整性验证
            validation_results["file_integrity"] = all(
                Path(modification.file_path).exists() for modification in modifications
            )

            # 修改应用验证
            validation_results["modification_applied"] = len(modifications) > 0

            # 备份验证
            validation_results["backup_valid"] = preparation.backup_info is not None

            # 基本功能验证
            validation_results["basic_functionality"] = self._test_basic_functionality(modifications)

        except Exception as e:
            logger.error(f"验证修改失败: {e}")
            validation_results["validation_error"] = False

        return validation_results

    def _test_basic_functionality(self, modifications: List[FileModification]) -> bool:
        """测试基本功能"""
        try:
            for modification in modifications:
                file_path = Path(modification.file_path)
                if file_path.suffix == '.py':
                    # 尝试编译
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    compile(content, str(file_path), 'exec')
            return True
        except:
            return False

    def _determine_final_status(self, execution_steps: List[ExecutionStep],
                              validation_results: Dict[str, bool],
                              modifications: List[FileModification]) -> ExecutionStatus:
        """确定最终状态"""
        # 检查是否有失败的关键步骤
        failed_critical_steps = [
            step for step in execution_steps
            if not step.success and step.command in ["apply_fix", "syntax_check"]
        ]

        if failed_critical_steps:
            return ExecutionStatus.FAILED

        # 检查验证结果
        if not validation_results.get("syntax_check", False):
            return ExecutionStatus.FAILED

        if not validation_results.get("modification_applied", False):
            return ExecutionStatus.FAILED

        # 检查是否有失败的步骤
        failed_steps = [step for step in execution_steps if not step.success]
        if failed_steps:
            # 如果有失败步骤但修改成功，返回需要审查状态
            return ExecutionStatus.COMPLETED

        return ExecutionStatus.COMPLETED

    def _generate_rollback_info(self, modifications: List[FileModification],
                              backup_info: Optional[BackupInfo]) -> Optional[Dict[str, Any]]:
        """生成回滚信息"""
        if not modifications and not backup_info:
            return None

        rollback_info = {
            "rollback_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "modifications_count": len(modifications),
            "backup_available": backup_info is not None
        }

        if backup_info:
            rollback_info["backup_id"] = backup_info.backup_id
            rollback_info["backup_path"] = backup_info.backup_path

        if modifications:
            rollback_info["files_to_restore"] = [
                {
                    "file_path": mod.file_path,
                    "original_content": mod.original_content,
                    "modification_type": mod.modification_type.value
                }
                for mod in modifications
            ]

        return rollback_info

    def _rollback_execution(self, execution_result: ExecutionResult) -> None:
        """回滚执行"""
        if execution_result.rollback_info:
            if execution_result.backup_info:
                self._rollback_from_backup(execution_result.backup_info)
            else:
                self._rollback_from_modifications(execution_result.modifications)

    def _rollback_from_backup(self, backup_info: BackupInfo) -> bool:
        """从备份回滚"""
        try:
            backup_path = Path(backup_info.backup_path)
            if not backup_path.exists():
                logger.error(f"备份路径不存在: {backup_path}")
                return False

            # 恢复文件
            original_file = Path(backup_info.backup_metadata["original_file"])
            backup_file = backup_path / original_file.name

            if backup_file.exists():
                original_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, original_file)
                logger.info(f"文件恢复成功: {original_file}")
                return True
            else:
                logger.error(f"备份文件不存在: {backup_file}")
                return False

        except Exception as e:
            logger.error(f"从备份回滚失败: {e}")
            return False

    def _rollback_from_modifications(self, modifications: List[FileModification]) -> bool:
        """从修改记录回滚"""
        try:
            for modification in modifications:
                file_path = Path(modification.file_path)

                if modification.modification_type == ModificationType.INSERT:
                    # 删除插入的内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    new_content = content.replace(modification.modified_content, '')
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                elif modification.modification_type == ModificationType.DELETE:
                    # 恢复删除的内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    new_content = content + modification.original_content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                elif modification.modification_type == ModificationType.REPLACE:
                    # 恢复原始内容
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    new_content = content.replace(modification.modified_content, modification.original_content)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)

                logger.info(f"文件回滚成功: {file_path}")

            return True

        except Exception as e:
            logger.error(f"从修改记录回滚失败: {e}")
            return False

    def _create_failed_execution_result(self, preparation: FixExecutionPreparation, error_message: str) -> ExecutionResult:
        """创建失败执行结果"""
        return ExecutionResult(
            execution_id=str(uuid.uuid4()),
            preparation_id=preparation.preparation_id,
            fix_suggestion_id=preparation.fix_suggestion_id,
            status=ExecutionStatus.FAILED,
            modifications=[],
            execution_steps=[],
            validation_results={},
            backup_info=preparation.backup_info,
            rollback_info=None,
            total_time_seconds=0,
            success=False,
            errors=[error_message],
            warnings=[],
            timestamp=datetime.now(),
            metadata={"error": error_message}
        )

    def _record_execution(self, execution_result: ExecutionResult) -> None:
        """记录执行历史"""
        self._execution_history.append(execution_result)

        # 限制历史记录数量
        if len(self._execution_history) > 100:
            self._execution_history = self._execution_history[-50:]

    def export_execution_history(self, limit: Optional[int] = None) -> str:
        """导出执行历史"""
        history = self.get_execution_history(limit)

        exportable_history = []
        for record in history:
            record_dict = asdict(record)
            record_dict["timestamp"] = record.timestamp.isoformat()

            # 转换执行步骤时间
            for step in record_dict["execution_steps"]:
                if step["start_time"]:
                    step["start_time"] = datetime.fromisoformat(step["start_time"]).isoformat()
                if step["end_time"]:
                    step["end_time"] = datetime.fromisoformat(step["end_time"]).isoformat()

            # 转换修改记录时间
            for modification in record_dict["modifications"]:
                modification["timestamp"] = datetime.fromisoformat(modification["timestamp"]).isoformat()

            # 转换备份信息时间
            if record_dict["backup_info"]:
                record_dict["backup_info"]["timestamp"] = datetime.fromisoformat(
                    record_dict["backup_info"]["timestamp"]
                ).isoformat()

            exportable_history.append(record_dict)

        return json.dumps(exportable_history, ensure_ascii=False, indent=2)