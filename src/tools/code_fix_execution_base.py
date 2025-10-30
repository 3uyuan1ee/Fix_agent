"""
代码修复执行基础架构
提供节点F自动修复执行的安全基础
"""

import uuid
import hashlib
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import shutil
import difflib
import ast

from ..utils.logger import get_logger
from ..utils.config import get_config_manager


class FixExecutionError(Exception):
    """修复执行异常"""
    pass


class FixValidationError(Exception):
    """修复验证异常"""
    pass


@dataclass
class FixOperation:
    """修复操作数据结构"""
    operation_id: str
    file_path: str
    line_start: int
    line_end: int
    original_code: str
    fixed_code: str
    operation_type: str  # "replace", "insert", "delete"
    backup_path: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    applied: bool = False
    rollback_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "operation_id": self.operation_id,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "original_code": self.original_code,
            "fixed_code": self.fixed_code,
            "operation_type": self.operation_type,
            "backup_path": self.backup_path,
            "timestamp": self.timestamp.isoformat(),
            "applied": self.applied,
            "rollback_data": self.rollback_data
        }

    def calculate_hash(self) -> str:
        """计算操作的哈希值用于验证"""
        content = f"{self.file_path}:{self.line_start}-{self.line_end}:{self.original_code}:{self.fixed_code}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class FixExecutionResult:
    """修复执行结果"""
    operation_id: str
    success: bool
    error_message: str = ""
    execution_time: float = 0.0
    syntax_valid: bool = False
    backup_created: bool = False
    rollback_available: bool = False
    verification_details: Dict[str, Any] = field(default_factory=dict)


class SafeCodeModifier:
    """安全的代码修改器"""

    def __init__(self, backup_dir: str = ".fix_backups"):
        """
        初始化安全代码修改器

        Args:
            backup_dir: 备份目录
        """
        self.logger = get_logger()
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.operation_history: List[FixOperation] = []

    def create_backup(self, file_path: str) -> str:
        """
        创建文件备份

        Args:
            file_path: 文件路径

        Returns:
            str: 备份文件路径

        Raises:
            FixExecutionError: 备份失败时抛出
        """
        try:
            source_path = Path(file_path)
            if not source_path.exists():
                raise FixExecutionError(f"源文件不存在: {file_path}")

            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
            backup_path = self.backup_dir / backup_name

            # 创建备份
            shutil.copy2(source_path, backup_path)

            self.logger.info(f"创建备份: {source_path} → {backup_path}")
            return str(backup_path)

        except Exception as e:
            raise FixExecutionError(f"创建备份失败: {e}")

    def apply_fix(self, operation: FixOperation) -> bool:
        """
        应用修复操作

        Args:
            operation: 修复操作

        Returns:
            bool: 应用是否成功

        Raises:
            FixExecutionError: 应用失败时抛出
        """
        try:
            file_path = Path(operation.file_path)
            if not file_path.exists():
                raise FixExecutionError(f"目标文件不存在: {operation.file_path}")

            # 创建备份
            if not operation.backup_path:
                operation.backup_path = self.create_backup(operation.file_path)

            # 读取原文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            # 验证行号范围
            if operation.line_start < 1 or operation.line_end > len(original_lines):
                raise FixExecutionError(
                    f"行号范围错误: {operation.line_start}-{operation.line_end}, "
                    f"文件总行数: {len(original_lines)}"
                )

            # 准备修复数据
            fixed_lines = operation.fixed_code.splitlines(keepends=True)
            original_lines_section = original_lines[operation.line_start-1:operation.line_end]

            # 保存回滚数据
            operation.rollback_data = {
                "original_lines": original_lines_section,
                "line_start": operation.line_start,
                "line_end": operation.line_end
            }

            # 应用修复
            new_lines = (
                original_lines[:operation.line_start-1] +
                fixed_lines +
                original_lines[operation.line_end:]
            )

            # 写入修复后的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            # 更新操作状态
            operation.applied = True
            self.operation_history.append(operation)

            self.logger.info(f"应用修复: {operation.operation_id}, 文件: {operation.file_path}")
            return True

        except Exception as e:
            self.logger.error(f"应用修复失败 {operation.operation_id}: {e}")
            raise FixExecutionError(f"应用修复失败: {e}")

    def rollback_fix(self, operation_id: str) -> bool:
        """
        回滚修复操作

        Args:
            operation_id: 操作ID

        Returns:
            bool: 回滚是否成功
        """
        try:
            # 查找操作
            operation = None
            for op in self.operation_history:
                if op.operation_id == operation_id:
                    operation = op
                    break

            if not operation:
                self.logger.error(f"未找到操作: {operation_id}")
                return False

            if not operation.applied or not operation.rollback_data:
                self.logger.error(f"操作无法回滚: {operation_id}")
                return False

            file_path = Path(operation.file_path)

            # 读取当前文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                current_lines = f.readlines()

            # 恢复原始内容
            rollback_data = operation.rollback_data
            new_lines = (
                current_lines[:rollback_data["line_start"]-1] +
                rollback_data["original_lines"] +
                current_lines[rollback_data["line_end"]:]
            )

            # 写入恢复的内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            # 更新操作状态
            operation.applied = False

            self.logger.info(f"回滚修复: {operation_id}, 文件: {operation.file_path}")
            return True

        except Exception as e:
            self.logger.error(f"回滚修复失败 {operation_id}: {e}")
            return False

    def verify_fix_syntax(self, file_path: str) -> bool:
        """
        验证修复后代码语法

        Args:
            file_path: 文件路径

        Returns:
            bool: 语法是否正确
        """
        try:
            file_path = Path(file_path)

            # 只验证Python文件
            if file_path.suffix != '.py':
                return True

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 使用AST验证语法
            ast.parse(content)
            return True

        except SyntaxError as e:
            self.logger.error(f"语法验证失败 {file_path}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"语法验证异常 {file_path}: {e}")
            return False

    def get_operation_history(self) -> List[FixOperation]:
        """
        获取操作历史

        Returns:
            List[FixOperation]: 操作历史列表
        """
        return self.operation_history.copy()

    def clear_history(self):
        """清空操作历史"""
        self.operation_history.clear()
        self.logger.info("清空修复操作历史")


class FixExecutionManager:
    """修复执行管理器"""

    def __init__(self, backup_dir: str = ".fix_backups"):
        """
        初始化修复执行管理器

        Args:
            backup_dir: 备份目录
        """
        self.logger = get_logger()
        self.config_manager = get_config_manager()
        self.code_modifier = SafeCodeModifier(backup_dir)
        self.execution_log: List[FixExecutionResult] = []

    def execute_ai_fix_suggestion(self, suggestion: Dict[str, Any]) -> FixExecutionResult:
        """
        执行AI修复建议

        Args:
            suggestion: AI修复建议

        Returns:
            FixExecutionResult: 执行结果
        """
        operation_id = f"fix_{uuid.uuid4().hex[:8]}"
        start_time = time.time()

        result = FixExecutionResult(operation_id=operation_id, success=False)

        try:
            # 解析修复建议
            file_path = suggestion.get("file_path")
            line_number = suggestion.get("line", 1)
            original_code = suggestion.get("original_code", "")
            fixed_code = suggestion.get("suggested_code", "")

            if not all([file_path, fixed_code]):
                raise FixExecutionError("修复建议缺少必要字段")

            # 确定操作类型
            operation_type = "replace"
            if not original_code.strip():
                operation_type = "insert"
            elif not fixed_code.strip():
                operation_type = "delete"

            # 创建修复操作
            operation = FixOperation(
                operation_id=operation_id,
                file_path=file_path,
                line_start=line_number,
                line_end=line_number if operation_type in ["insert", "delete"] else line_number,
                original_code=original_code,
                fixed_code=fixed_code,
                operation_type=operation_type
            )

            # 应用修复
            self.code_modifier.apply_fix(operation)
            result.backup_created = True
            result.rollback_available = True

            # 验证语法
            result.syntax_valid = self.code_modifier.verify_fix_syntax(file_path)
            if not result.syntax_valid:
                raise FixValidationError("修复后代码语法错误")

            # 执行成功
            result.success = True
            self.logger.info(f"成功执行修复: {operation_id}")

        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"执行修复失败 {operation_id}: {e}")

        finally:
            result.execution_time = time.time() - start_time
            self.execution_log.append(result)

        return result

    def batch_execute_fixes(self, suggestions: List[Dict[str, Any]]) -> List[FixExecutionResult]:
        """
        批量执行修复

        Args:
            suggestions: 修复建议列表

        Returns:
            List[FixExecutionResult]: 执行结果列表
        """
        results = []

        for suggestion in suggestions:
            try:
                result = self.execute_ai_fix_suggestion(suggestion)
                results.append(result)

                # 如果单个修复失败，可以选择停止或继续
                if not result.success:
                    self.logger.warning(f"批量修复中遇到失败: {result.operation_id}")

            except Exception as e:
                self.logger.error(f"批量修复异常: {e}")
                results.append(FixExecutionResult(
                    operation_id=f"batch_error_{uuid.uuid4().hex[:8]}",
                    success=False,
                    error_message=str(e)
                ))

        success_count = sum(1 for r in results if r.success)
        self.logger.info(f"批量修复完成: {success_count}/{len(results)} 成功")

        return results

    def rollback_last_fix(self) -> bool:
        """
        回滚最后一次修复

        Returns:
            bool: 回滚是否成功
        """
        if not self.code_modifier.operation_history:
            self.logger.warning("没有可回滚的修复操作")
            return False

        last_operation = self.code_modifier.operation_history[-1]
        return self.code_modifier.rollback_fix(last_operation.operation_id)

    def rollback_all_fixes(self) -> int:
        """
        回滚所有修复

        Returns:
            int: 回滚的操作数量
        """
        if not self.code_modifier.operation_history:
            return 0

        # 按相反顺序回滚
        operations = list(reversed(self.code_modifier.operation_history))
        rollback_count = 0

        for operation in operations:
            if self.code_modifier.rollback_fix(operation.operation_id):
                rollback_count += 1

        self.logger.info(f"回滚修复完成: {rollback_count}/{len(operations)} 个操作")
        return rollback_count

    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        获取执行统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        total_operations = len(self.execution_log)
        successful_operations = sum(1 for r in self.execution_log if r.success)
        failed_operations = total_operations - successful_operations

        total_time = sum(r.execution_time for r in self.execution_log)
        avg_time = total_time / total_operations if total_operations > 0 else 0

        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": failed_operations,
            "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "total_execution_time": total_time,
            "average_execution_time": avg_time,
            "pending_rollbacks": len(self.code_modifier.operation_history)
        }

    def clear_execution_log(self):
        """清空执行日志"""
        self.execution_log.clear()
        self.logger.info("清空修复执行日志")

    def export_execution_report(self, file_path: str) -> bool:
        """
        导出执行报告

        Args:
            file_path: 报告文件路径

        Returns:
            bool: 导出是否成功
        """
        try:
            report_data = {
                "generated_at": datetime.now().isoformat(),
                "statistics": self.get_execution_statistics(),
                "execution_log": [
                    {
                        "operation_id": r.operation_id,
                        "success": r.success,
                        "error_message": r.error_message,
                        "execution_time": r.execution_time,
                        "syntax_valid": r.syntax_valid,
                        "backup_created": r.backup_created
                    }
                    for r in self.execution_log
                ],
                "operation_history": [
                    op.to_dict() for op in self.code_modifier.operation_history
                ]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"导出执行报告: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"导出执行报告失败: {e}")
            return False