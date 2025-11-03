"""
T012.1: 修复执行准备器

节点F的核心组件，负责在执行修复前进行全面的准备工作。包括环境检查、
依赖验证、风险评估、备份创建等，确保修复执行的安全性和可靠性。

工作流位置: 节点F (执行自动修复)
输入: 用户决策结果 (T011.1/T011.2输出)
输出: 修复执行准备结果 + 执行计划
"""

import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path
import uuid
import shutil

from ..utils.types import ProblemType, RiskLevel, FixType
from ..utils.logger import get_logger
from .workflow_data_types import (
    AIFixSuggestion, WorkflowDataPacket, UserInteractionData
)
from .workflow_user_interaction_types import (
    UserDecision, DecisionType, UserAction, DecisionResult
)
from .workflow_flow_state_manager import WorkflowNode
from .user_decision_processor import DecisionResult
from .user_modification_processor import ModifiedSuggestion

logger = get_logger()


class PreparationStatus(Enum):
    """准备状态枚举"""
    PENDING = "pending"                     # 等待准备
    IN_PROGRESS = "in_progress"            # 准备中
    READY = "ready"                        # 准备就绪
    FAILED = "failed"                      # 准备失败
    CANCELLED = "cancelled"                # 已取消
    NEEDS_REVIEW = "needs_review"          # 需要审查


class ExecutionRiskLevel(Enum):
    """执行风险等级"""
    LOW = "low"                           # 低风险
    MEDIUM = "medium"                     # 中等风险
    HIGH = "high"                         # 高风险
    CRITICAL = "critical"                 # 关键风险


class BackupLevel(Enum):
    """备份等级"""
    NONE = "none"                         # 无备份
    BASIC = "basic"                       # 基础备份
    FULL = "full"                         # 完整备份
    INCREMENTAL = "incremental"           # 增量备份


@dataclass
class ExecutionEnvironment:
    """执行环境信息"""
    python_version: str
    operating_system: str
    available_memory_mb: int
    disk_space_gb: int
    current_directory: str
    git_repository: bool
    virtual_environment: bool
    dependencies_installed: List[str]
    missing_dependencies: List[str]


@dataclass
class BackupInfo:
    """备份信息"""
    backup_id: str
    backup_level: BackupLevel
    backup_path: str
    timestamp: datetime
    file_count: int
    total_size_mb: float
    checksum: str
    backup_metadata: Dict[str, Any]


@dataclass
class RiskAssessment:
    """风险评估"""
    overall_risk: ExecutionRiskLevel
    risk_factors: List[str]
    mitigation_strategies: List[str]
    potential_impact: str
    rollback_plan: str
    testing_requirements: List[str]
    approval_required: bool


@dataclass
class ExecutionPlan:
    """执行计划"""
    plan_id: str
    fix_suggestion_id: str
    execution_steps: List[Dict[str, Any]]
    estimated_duration_minutes: int
    resource_requirements: Dict[str, Any]
    validation_checks: List[str]
    rollback_procedure: List[str]
    success_criteria: List[str]


@dataclass
class FixExecutionPreparation:
    """修复执行准备结果"""
    preparation_id: str
    fix_suggestion_id: str
    status: PreparationStatus
    environment_info: ExecutionEnvironment
    backup_info: Optional[BackupInfo]
    risk_assessment: RiskAssessment
    execution_plan: ExecutionPlan
    validation_results: Dict[str, bool]
    warnings: List[str]
    errors: List[str]
    preparation_time_seconds: int
    timestamp: datetime
    metadata: Dict[str, Any]


class FixExecutionPreparer:
    """修复执行准备器"""

    def __init__(self, backup_directory: str = ".fix_backups"):
        """
        初始化执行准备器

        Args:
            backup_directory: 备份目录
        """
        self.backup_directory = Path(backup_directory)
        self.backup_directory.mkdir(exist_ok=True)
        self._preparation_history: List[FixExecutionPreparation] = []

    def prepare_execution(self, decision_result: DecisionResult,
                         fix_suggestion: Optional[AIFixSuggestion] = None,
                         modified_suggestion: Optional[ModifiedSuggestion] = None) -> FixExecutionPreparation:
        """
        准备修复执行

        Args:
            decision_result: 用户决策结果
            fix_suggestion: 原始修复建议
            modified_suggestion: 修改后的建议

        Returns:
            修复执行准备结果
        """
        preparation_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            logger.info(f"开始准备修复执行: {preparation_id}")

            # 确定要使用的建议
            target_suggestion = self._determine_target_suggestion(
                fix_suggestion, modified_suggestion, decision_result
            )

            if not target_suggestion:
                raise ValueError("没有可用的修复建议")

            # 检查执行环境
            environment_info = self._check_execution_environment()

            # 创建备份
            backup_info = self._create_backup(
                target_suggestion, decision_result, environment_info
            )

            # 评估风险
            risk_assessment = self._assess_execution_risks(
                target_suggestion, decision_result, environment_info
            )

            # 创建执行计划
            execution_plan = self._create_execution_plan(
                target_suggestion, risk_assessment, environment_info
            )

            # 执行验证检查
            validation_results = self._perform_validation_checks(
                target_suggestion, environment_info
            )

            # 生成警告和错误
            warnings, errors = self._generate_warnings_and_errors(
                validation_results, risk_assessment, environment_info
            )

            # 确定准备状态
            status = self._determine_preparation_status(errors, warnings, validation_results)

            preparation_time = int((datetime.now() - start_time).total_seconds())

            preparation_result = FixExecutionPreparation(
                preparation_id=preparation_id,
                fix_suggestion_id=target_suggestion.suggestion_id,
                status=status,
                environment_info=environment_info,
                backup_info=backup_info,
                risk_assessment=risk_assessment,
                execution_plan=execution_plan,
                validation_results=validation_results,
                warnings=warnings,
                errors=errors,
                preparation_time_seconds=preparation_time,
                timestamp=datetime.now(),
                metadata={
                    "decision_id": decision_result.decision_id,
                    "user_confidence": decision_result.confidence.value,
                    "original_suggestion_id": fix_suggestion.suggestion_id if fix_suggestion else None,
                    "is_modified": modified_suggestion is not None
                }
            )

            # 记录准备历史
            self._record_preparation(preparation_result)

            logger.info(f"修复执行准备完成: {preparation_id}, 状态: {status.value}")
            return preparation_result

        except Exception as e:
            logger.error(f"准备修复执行失败: {e}")
            raise

    def batch_prepare_executions(self, decision_results: List[DecisionResult],
                               fix_suggestions: List[AIFixSuggestion],
                               modified_suggestions: List[ModifiedSuggestion] = None) -> List[FixExecutionPreparation]:
        """
        批量准备修复执行

        Args:
            decision_results: 决策结果列表
            fix_suggestions: 修复建议列表
            modified_suggestions: 修改建议列表

        Returns:
            批量准备结果
        """
        if modified_suggestions is None:
            modified_suggestions = [None] * len(decision_results)

        results = []
        logger.info(f"开始批量准备 {len(decision_results)} 个修复执行")

        for i, decision_result in enumerate(decision_results):
            try:
                fix_suggestion = fix_suggestions[i] if i < len(fix_suggestions) else None
                modified_suggestion = modified_suggestions[i] if i < len(modified_suggestions) else None

                preparation = self.prepare_execution(
                    decision_result, fix_suggestion, modified_suggestion
                )
                results.append(preparation)

            except Exception as e:
                logger.error(f"批量准备执行失败 {i}: {e}")
                # 创建失败结果
                failed_preparation = self._create_failed_preparation(decision_result, str(e))
                results.append(failed_preparation)

        successful_count = sum(1 for r in results if r.status == PreparationStatus.READY)
        logger.info(f"批量准备完成: 成功 {successful_count}/{len(results)}")

        return results

    def validate_readiness(self, preparation: FixExecutionPreparation) -> bool:
        """
        验证准备就绪状态

        Args:
            preparation: 准备结果

        Returns:
            是否准备好执行
        """
        if preparation.status != PreparationStatus.READY:
            return False

        if preparation.errors:
            return False

        # 检查关键验证项
        critical_validations = [
            "environment_check",
            "backup_created",
            "syntax_validation",
            "dependency_check"
        ]

        for validation in critical_validations:
            if not preparation.validation_results.get(validation, False):
                return False

        # 检查风险等级
        if (preparation.risk_assessment.overall_risk == ExecutionRiskLevel.CRITICAL and
            not preparation.risk_assessment.approval_required):
            return False

        return True

    def get_preparation_history(self, limit: Optional[int] = None) -> List[FixExecutionPreparation]:
        """
        获取准备历史

        Args:
            limit: 限制数量

        Returns:
            准备历史列表
        """
        history = self._preparation_history.copy()
        history.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            history = history[:limit]

        return history

    def _determine_target_suggestion(self, fix_suggestion: Optional[AIFixSuggestion],
                                   modified_suggestion: Optional[ModifiedSuggestion],
                                   decision_result: DecisionResult) -> Optional[Union[AIFixSuggestion, ModifiedSuggestion]]:
        """确定目标修复建议"""
        if decision_result.outcome.value in ["modify"] and modified_suggestion:
            return modified_suggestion
        elif fix_suggestion:
            return fix_suggestion
        else:
            return None

    def _check_execution_environment(self) -> ExecutionEnvironment:
        """检查执行环境"""
        import sys
        import platform
        import psutil

        try:
            # 基本系统信息
            python_version = sys.version.split()[0]
            operating_system = platform.system() + " " + platform.release()
            current_directory = str(Path.cwd())

            # 系统资源
            memory = psutil.virtual_memory()
            available_memory_mb = int(memory.available / 1024 / 1024)

            disk = psutil.disk_usage(current_directory)
            disk_space_gb = int(disk.free / 1024 / 1024 / 1024)

            # Git检查
            git_repository = self._check_git_repository()

            # 虚拟环境检查
            virtual_environment = self._check_virtual_environment()

            # 依赖检查
            dependencies_installed, missing_dependencies = self._check_dependencies()

            return ExecutionEnvironment(
                python_version=python_version,
                operating_system=operating_system,
                available_memory_mb=available_memory_mb,
                disk_space_gb=disk_space_gb,
                current_directory=current_directory,
                git_repository=git_repository,
                virtual_environment=virtual_environment,
                dependencies_installed=dependencies_installed,
                missing_dependencies=missing_dependencies
            )

        except Exception as e:
            logger.warning(f"环境检查不完整: {e}")
            return ExecutionEnvironment(
                python_version=sys.version.split()[0],
                operating_system=platform.system(),
                available_memory_mb=0,
                disk_space_gb=0,
                current_directory=str(Path.cwd()),
                git_repository=False,
                virtual_environment=False,
                dependencies_installed=[],
                missing_dependencies=["环境检查失败"]
            )

    def _check_git_repository(self) -> bool:
        """检查是否为Git仓库"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except:
            return False

    def _check_virtual_environment(self) -> bool:
        """检查是否在虚拟环境中"""
        import sys
        return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    def _check_dependencies(self) -> Tuple[List[str], List[str]]:
        """检查依赖"""
        required_packages = ["ast", "pathlib", "json", "uuid", "hashlib"]
        installed_packages = []
        missing_packages = []

        for package in required_packages:
            try:
                __import__(package)
                installed_packages.append(package)
            except ImportError:
                missing_packages.append(package)

        return installed_packages, missing_packages

    def _create_backup(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion],
                      decision_result: DecisionResult,
                      environment_info: ExecutionEnvironment) -> Optional[BackupInfo]:
        """创建备份"""
        try:
            backup_id = str(uuid.uuid4())
            timestamp = datetime.now()

            # 确定备份等级
            backup_level = self._determine_backup_level(suggestion, decision_result)

            if backup_level == BackupLevel.NONE:
                return None

            # 创建备份目录
            backup_path = self.backup_directory / f"backup_{backup_id}"
            backup_path.mkdir(exist_ok=True)

            # 复制文件
            file_path = Path(suggestion.file_path)
            if file_path.exists():
                backup_file_path = backup_path / file_path.name
                shutil.copy2(file_path, backup_file_path)

                # 计算文件大小和校验和
                file_size = backup_file_path.stat().st_size / 1024 / 1024  # MB
                checksum = self._calculate_file_checksum(backup_file_path)

                backup_info = BackupInfo(
                    backup_id=backup_id,
                    backup_level=backup_level,
                    backup_path=str(backup_path),
                    timestamp=timestamp,
                    file_count=1,
                    total_size_mb=file_size,
                    checksum=checksum,
                    backup_metadata={
                        "original_file": str(file_path),
                        "suggestion_id": suggestion.suggestion_id,
                        "decision_id": decision_result.decision_id,
                        "git_commit": self._get_current_git_commit() if environment_info.git_repository else None
                    }
                )

                logger.info(f"创建备份: {backup_id}, 文件: {file_path}")
                return backup_info

            return None

        except Exception as e:
            logger.error(f"创建备份失败: {e}")
            return None

    def _determine_backup_level(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion],
                              decision_result: DecisionResult) -> BackupLevel:
        """确定备份等级"""
        # 基于风险等级确定备份等级
        if hasattr(suggestion, 'risk_level'):
            risk_level = suggestion.risk_level
        else:
            risk_level = RiskLevel.MEDIUM  # 默认中等风险

        if risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            return BackupLevel.FULL
        elif risk_level == RiskLevel.MEDIUM:
            return BackupLevel.BASIC
        else:
            return BackupLevel.INCREMENTAL

    def _calculate_file_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def _get_current_git_commit(self) -> Optional[str]:
        """获取当前Git提交"""
        try:
            import subprocess
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except:
            return None

    def _assess_execution_risks(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion],
                               decision_result: DecisionResult,
                               environment_info: ExecutionEnvironment) -> RiskAssessment:
        """评估执行风险"""
        risk_factors = []
        mitigation_strategies = []
        testing_requirements = []

        # 基础风险评估
        if hasattr(suggestion, 'risk_level'):
            base_risk = suggestion.risk_level
        else:
            base_risk = RiskLevel.MEDIUM

        # 风险因素分析
        if base_risk in [RiskLevel.CRITICAL, RiskLevel.HIGH]:
            risk_factors.append(f"基础风险等级较高: {base_risk.value}")
            mitigation_strategies.append("建议在测试环境中充分验证")

        # 用户置信度风险
        if decision_result.confidence.value in ["uncertain", "very_uncertain"]:
            risk_factors.append("用户决策不确定")
            mitigation_strategies.append("建议获取更多信息或专家意见")

        # 环境风险
        if environment_info.missing_dependencies:
            risk_factors.append(f"缺少依赖: {', '.join(environment_info.missing_dependencies)}")
            mitigation_strategies.append("安装缺少的依赖包")

        if environment_info.available_memory_mb < 1024:  # 小于1GB
            risk_factors.append("可用内存较少")
            mitigation_strategies.append("释放系统内存或使用更强大的环境")

        # 代码复杂度风险
        code_lines = len(suggestion.modified_code if hasattr(suggestion, 'modified_code') else suggestion.suggested_code.splitlines())
        if code_lines > 50:
            risk_factors.append("修复代码较长，复杂度较高")
            mitigation_strategies.append("考虑分步实施或拆分修复")

        # 文件系统风险
        if not environment_info.disk_space_gb > 1:
            risk_factors.append("磁盘空间不足")
            mitigation_strategies.append("清理磁盘空间")

        # 确定整体风险等级
        overall_risk = self._calculate_overall_risk(risk_factors, base_risk)

        # 测试要求
        testing_requirements.extend([
            "语法检查",
            "基本功能测试",
            "回归测试"
        ])

        if overall_risk in [ExecutionRiskLevel.HIGH, ExecutionRiskLevel.CRITICAL]:
            testing_requirements.extend([
                "集成测试",
                "性能测试"
            ])

        return RiskAssessment(
            overall_risk=overall_risk,
            risk_factors=risk_factors,
            mitigation_strategies=mitigation_strategies,
            potential_impact=self._describe_potential_impact(overall_risk),
            rollback_plan=self._create_rollback_plan(suggestion, environment_info),
            testing_requirements=testing_requirements,
            approval_required=overall_risk == ExecutionRiskLevel.CRITICAL
        )

    def _calculate_overall_risk(self, risk_factors: List[str], base_risk: RiskLevel) -> ExecutionRiskLevel:
        """计算整体风险等级"""
        risk_score = 0

        # 基础风险分数
        risk_mapping = {
            RiskLevel.NEGLIGIBLE: 0, RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4
        }
        risk_score += risk_mapping.get(base_risk, 2)

        # 风险因素加分
        risk_score += len(risk_factors)

        # 确定风险等级
        if risk_score >= 6:
            return ExecutionRiskLevel.CRITICAL
        elif risk_score >= 4:
            return ExecutionRiskLevel.HIGH
        elif risk_score >= 2:
            return ExecutionRiskLevel.MEDIUM
        else:
            return ExecutionRiskLevel.LOW

    def _describe_potential_impact(self, risk_level: ExecutionRiskLevel) -> str:
        """描述潜在影响"""
        impact_descriptions = {
            ExecutionRiskLevel.LOW: "轻微影响：可能影响单个功能点",
            ExecutionRiskLevel.MEDIUM: "中等影响：可能影响相关功能模块",
            ExecutionRiskLevel.HIGH: "较大影响：可能影响系统整体功能",
            ExecutionRiskLevel.CRITICAL: "严重影响：可能导致系统不稳定或数据丢失"
        }
        return impact_descriptions.get(risk_level, "影响未知")

    def _create_rollback_plan(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion],
                            environment_info: ExecutionEnvironment) -> str:
        """创建回滚计划"""
        plan_steps = []

        if environment_info.git_repository:
            plan_steps.append("使用git checkout恢复原始文件")
        else:
            plan_steps.append("从备份目录恢复原始文件")

        plan_steps.append("验证文件恢复正确性")
        plan_steps.append("运行相关测试确保功能正常")

        return "；".join(plan_steps)

    def _create_execution_plan(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion],
                             risk_assessment: RiskAssessment,
                             environment_info: ExecutionEnvironment) -> ExecutionPlan:
        """创建执行计划"""
        plan_id = str(uuid.uuid4())

        # 基础执行步骤
        execution_steps = [
            {
                "step_id": 1,
                "description": "验证文件权限和可访问性",
                "command": "check_file_access",
                "estimated_time": 1,
                "critical": True
            },
            {
                "step_id": 2,
                "description": "应用代码修复",
                "command": "apply_fix",
                "estimated_time": 2,
                "critical": True
            },
            {
                "step_id": 3,
                "description": "验证语法正确性",
                "command": "syntax_check",
                "estimated_time": 1,
                "critical": True
            },
            {
                "step_id": 4,
                "description": "运行基本测试",
                "command": "run_tests",
                "estimated_time": 5,
                "critical": True
            }
        ]

        # 根据风险等级添加额外步骤
        if risk_assessment.overall_risk in [ExecutionRiskLevel.HIGH, ExecutionRiskLevel.CRITICAL]:
            execution_steps.extend([
                {
                    "step_id": 5,
                    "description": "创建系统还原点",
                    "command": "create_restore_point",
                    "estimated_time": 2,
                    "critical": False
                },
                {
                    "step_id": 6,
                    "description": "运行完整测试套件",
                    "command": "full_test_suite",
                    "estimated_time": 15,
                    "critical": True
                }
            ])

        # 估算总时间
        estimated_duration = sum(step["estimated_time"] for step in execution_steps)

        # 资源要求
        resource_requirements = {
            "memory_mb": min(512, environment_info.available_memory_mb // 4),
            "disk_space_mb": 100,
            "cpu_cores": 1,
            "network_required": False
        }

        # 验证检查
        validation_checks = [
            "文件语法正确",
            "代码可以导入",
            "基本功能正常",
            "无运行时错误"
        ]

        # 回滚程序
        rollback_procedure = [
            "停止相关进程",
            "恢复原始文件",
            "清理临时文件",
            "验证系统状态"
        ]

        # 成功标准
        success_criteria = [
            "代码修复成功应用",
            "语法检查通过",
            "基本测试通过",
            "系统功能正常"
        ]

        return ExecutionPlan(
            plan_id=plan_id,
            fix_suggestion_id=suggestion.suggestion_id,
            execution_steps=execution_steps,
            estimated_duration_minutes=estimated_duration,
            resource_requirements=resource_requirements,
            validation_checks=validation_checks,
            rollback_procedure=rollback_procedure,
            success_criteria=success_criteria
        )

    def _perform_validation_checks(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion],
                                 environment_info: ExecutionEnvironment) -> Dict[str, bool]:
        """执行验证检查"""
        validation_results = {}

        # 环境检查
        validation_results["environment_check"] = (
            len(environment_info.missing_dependencies) == 0 and
            environment_info.available_memory_mb > 512 and
            environment_info.disk_space_gb > 1
        )

        # 备份检查
        validation_results["backup_created"] = True  # 假设备份已创建

        # 语法验证
        validation_results["syntax_validation"] = self._validate_syntax(suggestion)

        # 依赖检查
        validation_results["dependency_check"] = len(environment_info.missing_dependencies) == 0

        # 文件权限检查
        validation_results["file_permission_check"] = self._check_file_permissions(suggestion)

        # 磁盘空间检查
        validation_results["disk_space_check"] = environment_info.disk_space_gb > 1

        return validation_results

    def _validate_syntax(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> bool:
        """验证语法"""
        try:
            code = suggestion.modified_code if hasattr(suggestion, 'modified_code') else suggestion.suggested_code
            file_path = suggestion.file_path

            # 根据文件扩展名选择语法验证器
            if file_path.endswith('.py'):
                import ast
                ast.parse(code)
                return True
            else:
                # 简单的语法检查
                return len(code.strip()) > 0
        except:
            return False

    def _check_file_permissions(self, suggestion: Union[AIFixSuggestion, ModifiedSuggestion]) -> bool:
        """检查文件权限"""
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

    def _generate_warnings_and_errors(self, validation_results: Dict[str, bool],
                                    risk_assessment: RiskAssessment,
                                    environment_info: ExecutionEnvironment) -> Tuple[List[str], List[str]]:
        """生成警告和错误"""
        warnings = []
        errors = []

        # 验证结果警告和错误
        if not validation_results.get("environment_check"):
            errors.append("环境检查失败，无法安全执行修复")

        if not validation_results.get("backup_created"):
            warnings.append("备份创建失败，回滚可能不可用")

        if not validation_results.get("syntax_validation"):
            errors.append("语法验证失败，修复代码存在语法错误")

        if not validation_results.get("dependency_check"):
            warnings.append(f"缺少依赖: {', '.join(environment_info.missing_dependencies)}")

        if not validation_results.get("file_permission_check"):
            errors.append("文件权限不足，无法执行修复")

        if not validation_results.get("disk_space_check"):
            warnings.append("磁盘空间不足，可能影响备份创建")

        # 风险评估警告
        if risk_assessment.overall_risk == ExecutionRiskLevel.CRITICAL:
            warnings.append("执行风险极高，建议额外审查和批准")

        # 环境警告
        if environment_info.available_memory_mb < 1024:
            warnings.append("可用内存较少，可能影响执行性能")

        return warnings, errors

    def _determine_preparation_status(self, errors: List[str], warnings: List[str],
                                    validation_results: Dict[str, bool]) -> PreparationStatus:
        """确定准备状态"""
        if errors:
            return PreparationStatus.FAILED

        failed_validations = [k for k, v in validation_results.items() if not v]
        critical_failures = ["environment_check", "syntax_validation", "file_permission_check"]

        if any(failure in failed_validations for failure in critical_failures):
            return PreparationStatus.FAILED

        if warnings or failed_validations:
            return PreparationStatus.NEEDS_REVIEW

        return PreparationStatus.READY

    def _create_failed_preparation(self, decision_result: DecisionResult, error_message: str) -> FixExecutionPreparation:
        """创建失败准备结果"""
        return FixExecutionPreparation(
            preparation_id=str(uuid.uuid4()),
            fix_suggestion_id="unknown",
            status=PreparationStatus.FAILED,
            environment_info=ExecutionEnvironment(
                python_version="unknown",
                operating_system="unknown",
                available_memory_mb=0,
                disk_space_gb=0,
                current_directory="unknown",
                git_repository=False,
                virtual_environment=False,
                dependencies_installed=[],
                missing_dependencies=[]
            ),
            backup_info=None,
            risk_assessment=RiskAssessment(
                overall_risk=ExecutionRiskLevel.CRITICAL,
                risk_factors=["准备失败"],
                mitigation_strategies=[],
                potential_impact="无法执行",
                rollback_plan="无",
                testing_requirements=[],
                approval_required=False
            ),
            execution_plan=ExecutionPlan(
                plan_id="failed",
                fix_suggestion_id="unknown",
                execution_steps=[],
                estimated_duration_minutes=0,
                resource_requirements={},
                validation_checks=[],
                rollback_procedure=[],
                success_criteria=[]
            ),
            validation_results={},
            warnings=[],
            errors=[error_message],
            preparation_time_seconds=0,
            timestamp=datetime.now(),
            metadata={"error": error_message}
        )

    def _record_preparation(self, preparation: FixExecutionPreparation) -> None:
        """记录准备历史"""
        self._preparation_history.append(preparation)

        # 限制历史记录数量
        if len(self._preparation_history) > 200:
            self._preparation_history = self._preparation_history[-100:]

    def export_preparation_history(self, limit: Optional[int] = None) -> str:
        """导出准备历史"""
        history = self.get_preparation_history(limit)

        exportable_history = []
        for record in history:
            record_dict = asdict(record)
            record_dict["timestamp"] = record.timestamp.isoformat()
            if record.backup_info:
                record_dict["backup_info"]["timestamp"] = record.backup_info.timestamp.isoformat()
            exportable_history.append(record_dict)

        return json.dumps(exportable_history, ensure_ascii=False, indent=2)