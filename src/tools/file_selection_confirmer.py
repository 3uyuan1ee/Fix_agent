"""
文件选择确认器 - T007.1
固化用户最终决策，为Phase 5修复工作流准备输入
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logger import get_logger

try:
    from ..tools.ai_file_selector import FileSelectionResult
    from ..tools.project_structure_scanner import ProjectStructure
    from ..tools.user_decision_collector import UserDecisionResult, UserDecisionSession
except ImportError:
    # 如果相关模块不可用，定义基本类型
    @dataclass
    class UserDecisionResult:
        session_id: str
        final_selected_files: List[Dict[str, Any]] = field(default_factory=list)
        rejected_files: List[str] = field(default_factory=list)
        added_files: List[str] = field(default_factory=list)
        decision_summary: Dict[str, Any] = field(default_factory=dict)
        user_feedback: Dict[str, Any] = field(default_factory=dict)
        execution_success: bool = True
        error_message: str = ""

    @dataclass
    class UserDecisionSession:
        session_id: str
        initial_files: List[str] = field(default_factory=list)
        current_selection: List[str] = field(default_factory=list)
        session_start_time: str = ""

    @dataclass
    class FileSelectionResult:
        file_path: str
        priority: str
        reason: str
        confidence: float
        key_issues: List[str] = field(default_factory=list)
        selection_score: float = 0.0


@dataclass
class ConfirmedFileSelection:
    """确认的文件选择"""

    file_path: str
    relative_path: str
    language: str
    priority: str
    confidence: float
    selection_score: float
    reason: str
    key_issues: List[str] = field(default_factory=list)
    file_metadata: Dict[str, Any] = field(default_factory=dict)
    analysis_priority: int = 0  # 分析优先级（数字越大优先级越高）
    estimated_complexity: str = ""  # 预估复杂度
    expected_fixes: int = 0  # 预期修复数量

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "relative_path": self.relative_path,
            "language": self.language,
            "priority": self.priority,
            "confidence": self.confidence,
            "selection_score": self.selection_score,
            "reason": self.reason,
            "key_issues": self.key_issues,
            "file_metadata": self.file_metadata,
            "analysis_priority": self.analysis_priority,
            "estimated_complexity": self.expected_complexity,
            "expected_fixes": self.expected_fixes,
        }


@dataclass
class WorkloadEstimate:
    """工作量估算"""

    total_files: int = 0
    estimated_hours: float = 0.0
    estimated_fixes: int = 0
    complexity_distribution: Dict[str, int] = field(default_factory=dict)
    language_distribution: Dict[str, int] = field(default_factory=dict)
    priority_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_files": self.total_files,
            "estimated_hours": round(self.estimated_hours, 2),
            "estimated_fixes": self.estimated_fixes,
            "complexity_distribution": self.complexity_distribution,
            "language_distribution": self.language_distribution,
            "priority_distribution": self.priority_distribution,
        }


@dataclass
class FileSelectionConfirmation:
    """文件选择确认结果"""

    confirmation_id: str
    project_path: str
    confirmed_files: List[ConfirmedFileSelection] = field(default_factory=list)
    workload_estimate: WorkloadEstimate = field(default_factory=WorkloadEstimate)
    confirmation_summary: Dict[str, Any] = field(default_factory=dict)
    phase5_input_data: Dict[str, Any] = field(default_factory=dict)
    export_data: Dict[str, Any] = field(default_factory=dict)
    confirmation_timestamp: str = ""
    user_signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "confirmation_id": self.confirmation_id,
            "project_path": self.project_path,
            "confirmed_files": [file.to_dict() for file in self.confirmed_files],
            "workload_estimate": self.workload_estimate.to_dict(),
            "confirmation_summary": self.confirmation_summary,
            "phase5_input_data": self.phase5_input_data,
            "export_data": self.export_data,
            "confirmation_timestamp": self.confirmation_timestamp,
            "user_signature": self.user_signature,
            "total_confirmed": len(self.confirmed_files),
        }


class FileSelectionConfirmer:
    """文件选择确认器"""

    def __init__(self, backup_dir: str = ".fix_backups"):
        self.backup_dir = backup_dir
        self.logger = get_logger()

        # 复杂度估算参数
        self.complexity_factors = {
            "base_time_per_file": 0.5,  # 每个文件基础时间（小时）
            "time_per_issue": 0.1,  # 每个问题时间（小时）
            "language_multiplier": {  # 语言复杂度乘数
                "python": 1.0,
                "javascript": 1.1,
                "typescript": 1.2,
                "java": 1.3,
                "go": 1.0,
                "cpp": 1.4,
                "c": 1.3,
                "csharp": 1.2,
                "rust": 1.3,
                "php": 1.1,
                "ruby": 1.0,
            },
            "priority_multiplier": {  # 优先级乘数
                "high": 1.5,
                "medium": 1.0,
                "low": 0.7,
            },
        }

        # 确保备份目录存在
        os.makedirs(self.backup_dir, exist_ok=True)

    def confirm_selection(
        self,
        user_decision_result: UserDecisionResult,
        project_path: str,
        user_signature: Optional[str] = None,
        additional_options: Optional[Dict[str, Any]] = None,
    ) -> FileSelectionConfirmation:
        """
        确认文件选择

        Args:
            user_decision_result: 用户决策结果
            project_path: 项目路径
            user_signature: 用户签名/确认
            additional_options: 额外选项

        Returns:
            FileSelectionConfirmation: 确认结果
        """
        self.logger.info("开始确认文件选择")

        if not user_decision_result.execution_success:
            raise ValueError(f"用户决策执行失败: {user_decision_result.error_message}")

        # 生成确认ID
        confirmation_id = self._generate_confirmation_id()

        confirmation = FileSelectionConfirmation(
            confirmation_id=confirmation_id,
            project_path=os.path.abspath(project_path),
            confirmation_timestamp=datetime.now().isoformat(),
            user_signature=user_signature,
        )

        try:
            # 转换确认的文件
            confirmation.confirmed_files = self._convert_to_confirmed_files(
                user_decision_result.final_selected_files, project_path
            )

            # 估算工作量
            confirmation.workload_estimate = self._estimate_workload(
                confirmation.confirmed_files
            )

            # 生成确认摘要
            confirmation.confirmation_summary = self._generate_confirmation_summary(
                confirmation, user_decision_result
            )

            # 准备Phase 5输入数据
            confirmation.phase5_input_data = self._prepare_phase5_input(confirmation)

            # 准备导出数据
            confirmation.export_data = self._prepare_export_data(
                confirmation, additional_options or {}
            )

            # 保存确认结果
            self._save_confirmation(confirmation)

            self.logger.info(
                f"文件选择确认完成: {confirmation_id}, "
                f"确认 {len(confirmation.confirmed_files)} 个文件"
            )

        except Exception as e:
            self.logger.error(f"文件选择确认失败: {e}")
            raise

        return confirmation

    def _convert_to_confirmed_files(
        self, final_selected_files: List[Dict[str, Any]], project_path: str
    ) -> List[ConfirmedFileSelection]:
        """转换为确认的文件选择"""
        confirmed_files = []

        for file_data in final_selected_files:
            file_path = file_data.get("file_path", "")
            if not file_path or not os.path.exists(file_path):
                self.logger.warning(f"文件不存在，跳过: {file_path}")
                continue

            # 创建确认文件选择
            confirmed_file = ConfirmedFileSelection(
                file_path=file_path,
                relative_path=os.path.relpath(file_path, project_path),
                language=file_data.get("language", "unknown"),
                priority=file_data.get("priority", "medium"),
                confidence=file_data.get("confidence", 0.5),
                selection_score=file_data.get("selection_score", 0.0),
                reason=file_data.get("reason", ""),
                key_issues=file_data.get("key_issues", []),
            )

            # 收集文件元数据
            confirmed_file.file_metadata = self._collect_file_metadata(file_path)

            # 计算分析优先级
            confirmed_file.analysis_priority = self._calculate_analysis_priority(
                confirmed_file
            )

            # 估算复杂度
            confirmed_file.estimated_complexity = self._estimate_file_complexity(
                confirmed_file
            )

            # 预期修复数量
            confirmed_file.expected_fixes = len(confirmed_file.key_issues)

            confirmed_files.append(confirmed_file)

        return confirmed_files

    def _collect_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """收集文件元数据"""
        metadata = {}

        try:
            # 基本文件信息
            stat_info = os.stat(file_path)
            metadata.update(
                {
                    "file_size": stat_info.st_size,
                    "last_modified": datetime.fromtimestamp(
                        stat_info.st_mtime
                    ).isoformat(),
                    "is_readable": os.access(file_path, os.R_OK),
                    "is_writable": os.access(file_path, os.W_OK),
                }
            )

            # 文件行数
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)
                    metadata["line_count"] = line_count
            except Exception:
                metadata["line_count"] = 0

            # 文件扩展名
            _, ext = os.path.splitext(file_path)
            metadata["file_extension"] = ext.lower()

            # 文件类型
            if os.path.isfile(file_path):
                metadata["file_type"] = "file"
            elif os.path.isdir(file_path):
                metadata["file_type"] = "directory"
            else:
                metadata["file_type"] = "other"

        except Exception as e:
            self.logger.debug(f"收集文件元数据失败 {file_path}: {e}")

        return metadata

    def _calculate_analysis_priority(
        self, confirmed_file: ConfirmedFileSelection
    ) -> int:
        """计算分析优先级"""
        priority = 0

        # 基于选择分数
        priority += int(confirmed_file.selection_score * 10)

        # 基于优先级
        priority_weights = {"high": 30, "medium": 20, "low": 10}
        priority += priority_weights.get(confirmed_file.priority, 20)

        # 基于置信度
        priority += int(confirmed_file.confidence * 20)

        # 基于关键问题数量
        priority += len(confirmed_file.key_issues) * 5

        # 基于文件大小（大文件可能有更多问题）
        file_size = confirmed_file.file_metadata.get("file_size", 0)
        if file_size > 100000:  # 100KB
            priority += 10
        elif file_size > 10000:  # 10KB
            priority += 5

        return priority

    def _estimate_file_complexity(self, confirmed_file: ConfirmedFileSelection) -> str:
        """估算文件复杂度"""
        complexity_score = 0

        # 基于选择分数
        complexity_score += confirmed_file.selection_score

        # 基于问题数量
        complexity_score += len(confirmed_file.key_issues) * 2

        # 基于文件行数
        line_count = confirmed_file.file_metadata.get("line_count", 0)
        if line_count > 500:
            complexity_score += 10
        elif line_count > 200:
            complexity_score += 5
        elif line_count > 100:
            complexity_score += 2

        # 基于语言复杂度
        language_multipliers = {
            "python": 1.0,
            "javascript": 1.1,
            "typescript": 1.2,
            "java": 1.3,
            "go": 1.0,
            "cpp": 1.4,
            "c": 1.3,
            "csharp": 1.2,
            "rust": 1.3,
            "php": 1.1,
            "ruby": 1.0,
        }
        lang_multiplier = language_multipliers.get(confirmed_file.language, 1.0)
        complexity_score *= lang_multiplier

        # 转换为复杂度等级
        if complexity_score >= 15:
            return "高"
        elif complexity_score >= 8:
            return "中"
        else:
            return "低"

    def _estimate_workload(
        self, confirmed_files: List[ConfirmedFileSelection]
    ) -> WorkloadEstimate:
        """估算工作量"""
        estimate = WorkloadEstimate()
        estimate.total_files = len(confirmed_files)

        total_hours = 0
        total_fixes = 0

        complexity_dist = {"低": 0, "中": 0, "高": 0}
        language_dist = {}
        priority_dist = {"high": 0, "medium": 0, "low": 0}

        for confirmed_file in confirmed_files:
            # 计算单个文件的工作量
            file_hours = self.complexity_factors["base_time_per_file"]

            # 基于问题数量
            file_hours += (
                len(confirmed_file.key_issues)
                * self.complexity_factors["time_per_issue"]
            )

            # 基于语言的乘数
            lang_multiplier = self.complexity_factors["language_multiplier"].get(
                confirmed_file.language, 1.0
            )
            file_hours *= lang_multiplier

            # 基于优先级的乘数
            priority_multiplier = self.complexity_factors["priority_multiplier"].get(
                confirmed_file.priority, 1.0
            )
            file_hours *= priority_multiplier

            total_hours += file_hours
            total_fixes += confirmed_file.expected_fixes

            # 统计分布
            complexity_dist[confirmed_file.estimated_complexity] += 1
            language_dist[confirmed_file.language] = (
                language_dist.get(confirmed_file.language, 0) + 1
            )
            priority_dist[confirmed_file.priority] += 1

        estimate.estimated_hours = total_hours
        estimate.estimated_fixes = total_fixes
        estimate.complexity_distribution = complexity_dist
        estimate.language_distribution = language_dist
        estimate.priority_distribution = priority_dist

        return estimate

    def _generate_confirmation_summary(
        self,
        confirmation: FileSelectionConfirmation,
        user_decision_result: UserDecisionResult,
    ) -> Dict[str, Any]:
        """生成确认摘要"""
        summary = {
            "confirmation_id": confirmation.confirmation_id,
            "project_path": confirmation.project_path,
            "confirmation_timestamp": confirmation.confirmation_timestamp,
            "user_signature": confirmation.user_signature,
            "files_summary": {
                "total_confirmed": len(confirmation.confirmed_files),
                "initial_selected": len(user_decision_result.final_selected_files),
                "rejected_count": len(user_decision_result.rejected_files),
                "added_count": len(user_decision_result.added_files),
            },
            "workload_summary": {
                "estimated_hours": confirmation.workload_estimate.estimated_hours,
                "estimated_fixes": confirmation.workload_estimate.estimated_fixes,
                "avg_time_per_file": (
                    round(
                        confirmation.workload_estimate.estimated_hours
                        / len(confirmation.confirmed_files),
                        2,
                    )
                    if confirmation.confirmed_files
                    else 0
                ),
            },
            "quality_metrics": {
                "average_confidence": (
                    round(
                        sum(f.confidence for f in confirmation.confirmed_files)
                        / len(confirmation.confirmed_files),
                        2,
                    )
                    if confirmation.confirmed_files
                    else 0
                ),
                "average_selection_score": (
                    round(
                        sum(f.selection_score for f in confirmation.confirmed_files)
                        / len(confirmation.confirmed_files),
                        2,
                    )
                    if confirmation.confirmed_files
                    else 0
                ),
                "high_priority_ratio": (
                    round(
                        len(
                            [
                                f
                                for f in confirmation.confirmed_files
                                if f.priority == "high"
                            ]
                        )
                        / len(confirmation.confirmed_files),
                        2,
                    )
                    if confirmation.confirmed_files
                    else 0
                ),
            },
            "decision_statistics": user_decision_result.decision_summary,
        }

        return summary

    def _prepare_phase5_input(
        self, confirmation: FileSelectionConfirmation
    ) -> Dict[str, Any]:
        """准备Phase 5输入数据"""
        phase5_input = {
            "phase_info": {
                "phase": "5",
                "name": "AI修复工作流",
                "description": "基于严格工作流图的完整修复闭环",
                "workflow_nodes": [
                    "B",
                    "C",
                    "D",
                    "E",
                    "F/G",
                    "H",
                    "I",
                    "J/K",
                    "L",
                    "B/M",
                ],
            },
            "project_context": {
                "project_path": confirmation.project_path,
                "confirmation_id": confirmation.confirmation_id,
                "confirmation_timestamp": confirmation.confirmation_timestamp,
            },
            "selected_files": [],
            "execution_plan": {
                "total_files": len(confirmation.confirmed_files),
                "estimated_duration_hours": confirmation.workload_estimate.estimated_hours,
                "workflow_type": "sequential",  # 按优先级顺序执行
                "error_handling": "continue_on_error",  # 遇到错误继续处理其他文件
                "backup_enabled": True,
            },
            "workflow_config": {
                "enable_user_interaction": True,
                "require_confirmation_at_critical_steps": True,
                "auto_retry_failed_fixes": True,
                "max_retry_attempts": 3,
            },
        }

        # 按分析优先级排序文件
        sorted_files = sorted(
            confirmation.confirmed_files,
            key=lambda x: x.analysis_priority,
            reverse=True,
        )

        # 转换为Phase 5格式
        for confirmed_file in sorted_files:
            phase5_file = {
                "file_path": confirmed_file.file_path,
                "relative_path": confirmed_file.relative_path,
                "language": confirmed_file.language,
                "priority": confirmed_file.priority,
                "analysis_priority": confirmed_file.analysis_priority,
                "key_issues": confirmed_file.key_issues,
                "estimated_complexity": confirmed_file.estimated_complexity,
                "expected_fixes": confirmed_file.expected_fixes,
                "ai_selection_reason": confirmed_file.reason,
                "file_metadata": confirmed_file.file_metadata,
                "workflow_state": {
                    "current_node": None,  # Phase 5开始时为null
                    "problem_detection_status": "pending",
                    "fix_suggestion_status": "pending",
                    "user_review_status": "pending",
                    "fix_execution_status": "pending",
                    "verification_status": "pending",
                },
            }
            phase5_input["selected_files"].append(phase5_file)

        return phase5_input

    def _prepare_export_data(
        self, confirmation: FileSelectionConfirmation, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """准备导出数据"""
        export_formats = options.get("formats", ["json"])
        export_data = {}

        # JSON格式（默认）
        if "json" in export_formats:
            export_data["json"] = confirmation.to_dict()

        # CSV格式
        if "csv" in export_formats:
            export_data["csv"] = self._export_to_csv(confirmation)

        # 简化格式（用于快速查看）
        if "summary" in export_formats:
            export_data["summary"] = {
                "confirmation_id": confirmation.confirmation_id,
                "total_files": len(confirmation.confirmed_files),
                "estimated_hours": confirmation.workload_estimate.estimated_hours,
                "files": [
                    {
                        "file_path": f.relative_path,
                        "priority": f.priority,
                        "complexity": f.estimated_complexity,
                        "issues": len(f.key_issues),
                    }
                    for f in confirmation.confirmed_files
                ],
            }

        return export_data

    def _export_to_csv(
        self, confirmation: FileSelectionConfirmation
    ) -> List[Dict[str, Any]]:
        """导出为CSV格式"""
        csv_data = []

        # 添加标题行
        csv_data.append(
            {
                "file_path": "文件路径",
                "relative_path": "相对路径",
                "language": "语言",
                "priority": "优先级",
                "confidence": "置信度",
                "selection_score": "选择分数",
                "complexity": "复杂度",
                "expected_fixes": "预期修复数",
                "key_issues": "关键问题",
                "reason": "选择理由",
            }
        )

        # 添加数据行
        for confirmed_file in confirmation.confirmed_files:
            csv_data.append(
                {
                    "file_path": confirmed_file.file_path,
                    "relative_path": confirmed_file.relative_path,
                    "language": confirmed_file.language,
                    "priority": confirmed_file.priority,
                    "confidence": confirmed_file.confidence,
                    "selection_score": confirmed_file.selection_score,
                    "complexity": confirmed_file.estimated_complexity,
                    "expected_fixes": confirmed_file.expected_fixes,
                    "key_issues": "; ".join(confirmed_file.key_issues),
                    "reason": confirmed_file.reason,
                }
            )

        return csv_data

    def _save_confirmation(self, confirmation: FileSelectionConfirmation) -> None:
        """保存确认结果"""
        try:
            # 创建确认文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"file_selection_confirmation_{confirmation.confirmation_id}_{timestamp}.json"
            filepath = os.path.join(self.backup_dir, filename)

            # 保存完整确认数据
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(confirmation.to_dict(), f, ensure_ascii=False, indent=2)

            self.logger.info(f"文件选择确认已保存: {filepath}")

            # 同时保存Phase 5输入数据
            phase5_filename = (
                f"phase5_input_{confirmation.confirmation_id}_{timestamp}.json"
            )
            phase5_filepath = os.path.join(self.backup_dir, phase5_filename)

            with open(phase5_filepath, "w", encoding="utf-8") as f:
                json.dump(
                    confirmation.phase5_input_data, f, ensure_ascii=False, indent=2
                )

            self.logger.info(f"Phase 5输入数据已保存: {phase5_filepath}")

        except Exception as e:
            self.logger.error(f"保存确认结果失败: {e}")

    def _generate_confirmation_id(self) -> str:
        """生成确认ID"""
        import uuid

        return f"confirm_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

    def load_confirmation(
        self, confirmation_id: str
    ) -> Optional[FileSelectionConfirmation]:
        """加载已保存的确认结果"""
        try:
            # 查找确认文件
            for filename in os.listdir(self.backup_dir):
                if filename.startswith(
                    f"file_selection_confirmation_{confirmation_id}_"
                ) and filename.endswith(".json"):
                    filepath = os.path.join(self.backup_dir, filename)

                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    # 重建确认对象
                    confirmation = self._rebuild_confirmation_from_data(data)
                    self.logger.info(f"已加载确认结果: {confirmation_id}")
                    return confirmation

        except Exception as e:
            self.logger.error(f"加载确认结果失败 {confirmation_id}: {e}")

        return None

    def _rebuild_confirmation_from_data(
        self, data: Dict[str, Any]
    ) -> FileSelectionConfirmation:
        """从数据重建确认对象"""
        # 这里简化实现，实际应该完整重建所有对象
        confirmation = FileSelectionConfirmation(
            confirmation_id=data["confirmation_id"],
            project_path=data["project_path"],
            confirmation_timestamp=data["confirmation_timestamp"],
            user_signature=data.get("user_signature"),
        )

        # TODO: 完整重建confirmed_files等其他字段

        return confirmation


# 便捷函数
def confirm_file_selection(
    user_decision_result: UserDecisionResult,
    project_path: str,
    backup_dir: str = ".fix_backups",
    export_formats: List[str] = None,
) -> Dict[str, Any]:
    """
    便捷的文件选择确认函数

    Args:
        user_decision_result: 用户决策结果
        project_path: 项目路径
        backup_dir: 备份目录
        export_formats: 导出格式列表

    Returns:
        Dict[str, Any]: 确认结果
    """
    confirmer = FileSelectionConfirmer(backup_dir)

    options = {"formats": export_formats or ["json", "summary"]}

    confirmation = confirmer.confirm_selection(
        user_decision_result=user_decision_result,
        project_path=project_path,
        additional_options=options,
    )

    return confirmation.to_dict()
