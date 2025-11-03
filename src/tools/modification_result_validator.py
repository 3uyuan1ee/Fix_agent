"""
T012.3: 修改结果验证器

节点F的辅助组件，负责验证代码修改的结果。包括功能验证、性能测试、
回归测试等，确保修改达到预期效果且没有引入新问题。

工作流位置: 节点F (执行自动修复) - 验证功能
输入: 代码修改执行结果 (T012.2输出)
输出: 修改验证结果 + 验证报告
"""

import json
import subprocess
import time
import statistics
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
from pathlib import Path
import uuid

from ..utils.types import ProblemType, RiskLevel, FixType
from ..utils.logger import get_logger
from .workflow_data_types import AIFixSuggestion, WorkflowDataPacket
from .workflow_user_interaction_types import UserAction, DecisionResult
from .workflow_flow_state_manager import WorkflowNode
from .code_auto_modifier_executor import ExecutionResult, ExecutionStatus, FileModification
from .fix_execution_preparer import FixExecutionPreparation

logger = get_logger()


class ValidationLevel(Enum):
    """验证等级枚举"""
    BASIC = "basic"                       # 基础验证
    STANDARD = "standard"                 # 标准验证
    COMPREHENSIVE = "comprehensive"       # 全面验证
    THOROUGH = "thorough"                 # 彻底验证


class ValidationStatus(Enum):
    """验证状态枚举"""
    PENDING = "pending"                   # 等待验证
    IN_PROGRESS = "in_progress"          # 验证中
    PASSED = "passed"                    # 验证通过
    FAILED = "failed"                    # 验证失败
    WARNING = "warning"                  # 验证通过但有警告
    CANCELLED = "cancelled"              # 已取消
    SKIPPED = "skipped"                  # 已跳过


class TestType(Enum):
    """测试类型枚举"""
    SYNTAX = "syntax"                    # 语法测试
    IMPORT = "import"                    # 导入测试
    FUNCTIONAL = "functional"            # 功能测试
    PERFORMANCE = "performance"          # 性能测试
    REGRESSION = "regression"            # 回归测试
    INTEGRATION = "integration"          # 集成测试
    SECURITY = "security"                # 安全测试


@dataclass
class TestCase:
    """测试用例"""
    test_id: str
    test_type: TestType
    name: str
    description: str
    command: str
    expected_result: str
    timeout_seconds: int
    critical: bool


@dataclass
class TestResult:
    """测试结果"""
    test_id: str
    test_type: TestType
    status: ValidationStatus
    execution_time_seconds: float
    output: str
    error: str
    passed: bool
    warnings: List[str]


@dataclass
class ValidationResult:
    """验证结果"""
    validation_id: str
    execution_id: str
    overall_status: ValidationStatus
    validation_level: ValidationLevel
    test_results: List[TestResult]
    performance_metrics: Dict[str, float]
    quality_metrics: Dict[str, float]
    issues_found: List[Dict[str, Any]]
    recommendations: List[str]
    validation_time_seconds: int
    success_rate: float
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class ValidationReport:
    """验证报告"""
    report_id: str
    validation_result: ValidationResult
    summary: str
    detailed_findings: List[str]
    impact_assessment: str
    next_steps: List[str]
    approval_required: bool
    confidence_score: float


class ModificationResultValidator:
    """修改结果验证器"""

    def __init__(self, test_timeout: int = 300):
        """
        初始化验证器

        Args:
            test_timeout: 测试超时时间（秒）
        """
        self.test_timeout = test_timeout
        self._validation_history: List[ValidationResult] = []
        self._test_generators = self._init_test_generators()

    def validate_modification(self, execution_result: ExecutionResult,
                            preparation: FixExecutionPreparation,
                            validation_level: ValidationLevel = ValidationLevel.STANDARD) -> ValidationResult:
        """
        验证修改结果

        Args:
            execution_result: 执行结果
            preparation: 执行准备
            validation_level: 验证等级

        Returns:
            验证结果
        """
        validation_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            logger.info(f"开始验证修改结果: {validation_id}")

            # 检查执行状态
            if execution_result.status != ExecutionStatus.COMPLETED:
                raise ValueError(f"执行状态不正确: {execution_result.status.value}")

            # 生成测试用例
            test_cases = self._generate_test_cases(
                execution_result, preparation, validation_level
            )

            # 执行测试
            test_results = self._execute_test_cases(test_cases, execution_result)

            # 收集性能指标
            performance_metrics = self._collect_performance_metrics(execution_result)

            # 收集质量指标
            quality_metrics = self._collect_quality_metrics(execution_result, test_results)

            # 识别问题
            issues_found = self._identify_issues(test_results, performance_metrics, quality_metrics)

            # 生成建议
            recommendations = self._generate_recommendations(
                issues_found, test_results, performance_metrics
            )

            # 计算成功率
            success_rate = self._calculate_success_rate(test_results)

            # 确定整体状态
            overall_status = self._determine_overall_status(
                test_results, issues_found, success_rate
            )

            validation_time = int((datetime.now() - start_time).total_seconds())

            validation_result = ValidationResult(
                validation_id=validation_id,
                execution_id=execution_result.execution_id,
                overall_status=overall_status,
                validation_level=validation_level,
                test_results=test_results,
                performance_metrics=performance_metrics,
                quality_metrics=quality_metrics,
                issues_found=issues_found,
                recommendations=recommendations,
                validation_time_seconds=validation_time,
                success_rate=success_rate,
                timestamp=datetime.now(),
                metadata={
                    "file_count": len(execution_result.modifications),
                    "test_count": len(test_cases),
                    "validation_level": validation_level.value
                }
            )

            # 记录验证历史
            self._record_validation(validation_result)

            logger.info(f"修改结果验证完成: {validation_id}, 状态: {overall_status.value}")
            return validation_result

        except Exception as e:
            logger.error(f"验证修改结果失败: {e}")
            raise

    def batch_validate_modifications(self, execution_results: List[ExecutionResult],
                                   preparations: List[FixExecutionPreparation],
                                   validation_level: ValidationLevel = ValidationLevel.STANDARD) -> List[ValidationResult]:
        """
        批量验证修改结果

        Args:
            execution_results: 执行结果列表
            preparations: 准备结果列表
            validation_level: 验证等级

        Returns:
            批量验证结果
        """
        results = []
        logger.info(f"开始批量验证 {len(execution_results)} 个修改结果")

        for execution_result, preparation in zip(execution_results, preparations):
            try:
                validation_result = self.validate_modification(
                    execution_result, preparation, validation_level
                )
                results.append(validation_result)
            except Exception as e:
                logger.error(f"批量验证失败: {e}")
                # 创建失败结果
                failed_result = self._create_failed_validation_result(execution_result, str(e))
                results.append(failed_result)

        successful_count = sum(1 for r in results if r.overall_status == ValidationStatus.PASSED)
        logger.info(f"批量验证完成: 成功 {successful_count}/{len(results)}")

        return results

    def generate_validation_report(self, validation_result: ValidationResult) -> ValidationReport:
        """
        生成验证报告

        Args:
            validation_result: 验证结果

        Returns:
            验证报告
        """
        report_id = str(uuid.uuid4())

        # 生成摘要
        summary = self._generate_summary(validation_result)

        # 生成详细发现
        detailed_findings = self._generate_detailed_findings(validation_result)

        # 影响评估
        impact_assessment = self._assess_impact(validation_result)

        # 下一步行动
        next_steps = self._determine_next_steps(validation_result)

        # 确定是否需要审批
        approval_required = self._determine_approval_required(validation_result)

        # 计算置信度
        confidence_score = self._calculate_confidence_score(validation_result)

        return ValidationReport(
            report_id=report_id,
            validation_result=validation_result,
            summary=summary,
            detailed_findings=detailed_findings,
            impact_assessment=impact_assessment,
            next_steps=next_steps,
            approval_required=approval_required,
            confidence_score=confidence_score
        )

    def get_validation_history(self, limit: Optional[int] = None) -> List[ValidationResult]:
        """
        获取验证历史

        Args:
            limit: 限制数量

        Returns:
            验证历史列表
        """
        history = self._validation_history.copy()
        history.sort(key=lambda x: x.timestamp, reverse=True)

        if limit:
            history = history[:limit]

        return history

    def _generate_test_cases(self, execution_result: ExecutionResult,
                           preparation: FixExecutionPreparation,
                           validation_level: ValidationLevel) -> List[TestCase]:
        """生成测试用例"""
        test_cases = []

        # 基础测试用例
        basic_tests = self._generate_basic_tests(execution_result)
        test_cases.extend(basic_tests)

        # 根据验证等级添加更多测试
        if validation_level in [ValidationLevel.STANDARD, ValidationLevel.COMPREHENSIVE, ValidationLevel.THOROUGH]:
            standard_tests = self._generate_standard_tests(execution_result, preparation)
            test_cases.extend(standard_tests)

        if validation_level in [ValidationLevel.COMPREHENSIVE, ValidationLevel.THOROUGH]:
            comprehensive_tests = self._generate_comprehensive_tests(execution_result, preparation)
            test_cases.extend(comprehensive_tests)

        if validation_level == ValidationLevel.THOROUGH:
            thorough_tests = self._generate_thorough_tests(execution_result, preparation)
            test_cases.extend(thorough_tests)

        return test_cases

    def _generate_basic_tests(self, execution_result: ExecutionResult) -> List[TestCase]:
        """生成基础测试"""
        test_cases = []

        for modification in execution_result.modifications:
            file_path = Path(modification.file_path)

            # 语法测试
            if file_path.suffix == '.py':
                test_cases.append(TestCase(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.SYNTAX,
                    name=f"语法检查 - {file_path.name}",
                    description=f"验证 {file_path} 的Python语法正确性",
                    command=f"python -m py_compile {file_path}",
                    expected_result="编译成功，无语法错误",
                    timeout_seconds=30,
                    critical=True
                ))

            # 导入测试
            if file_path.suffix == '.py':
                test_cases.append(TestCase(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.IMPORT,
                    name=f"导入测试 - {file_path.name}",
                    description=f"验证 {file_path} 可以正常导入",
                    command=f"python -c \"import {file_path.stem}\"",
                    expected_result="模块导入成功",
                    timeout_seconds=10,
                    critical=True
                ))

        return test_cases

    def _generate_standard_tests(self, execution_result: ExecutionResult,
                               preparation: FixExecutionPreparation) -> List[TestCase]:
        """生成标准测试"""
        test_cases = []

        # 功能测试
        project_root = Path(execution_result.modifications[0].file_path).parent if execution_result.modifications else Path.cwd()

        # 查找并运行测试文件
        test_files = list(project_root.glob("**/test*.py")) + list(project_root.glob("**/*test*.py"))

        for test_file in test_files[:3]:  # 限制测试文件数量
            test_cases.append(TestCase(
                test_id=str(uuid.uuid4()),
                test_type=TestType.FUNCTIONAL,
                name=f"功能测试 - {test_file.name}",
                description=f"运行 {test_file} 中的功能测试",
                command=f"python -m pytest {test_file} -v",
                expected_result="所有测试通过",
                timeout_seconds=120,
                critical=False
            ))

        return test_cases

    def _generate_comprehensive_tests(self, execution_result: ExecutionResult,
                                    preparation: FixExecutionPreparation) -> List[TestCase]:
        """生成全面测试"""
        test_cases = []

        # 性能测试
        for modification in execution_result.modifications:
            file_path = Path(modification.file_path)
            if file_path.suffix == '.py':
                test_cases.append(TestCase(
                    test_id=str(uuid.uuid4()),
                    test_type=TestType.PERFORMANCE,
                    name=f"性能测试 - {file_path.name}",
                    description=f"测试 {file_path} 的基本性能",
                    command=f"python -c \"import time; import {file_path.stem}; start = time.time(); # 基本性能测试; print(f'执行时间: {{time.time() - start:.3f}}秒')\"",
                    expected_result="性能测试完成",
                    timeout_seconds=60,
                    critical=False
                ))

        return test_cases

    def _generate_thorough_tests(self, execution_result: ExecutionResult,
                               preparation: FixExecutionPreparation) -> List[TestCase]:
        """生成彻底测试"""
        test_cases = []

        # 集成测试
        project_root = Path(execution_result.modifications[0].file_path).parent if execution_result.modifications else Path.cwd()
        setup_py = project_root / "setup.py"
        requirements_txt = project_root / "requirements.txt"

        if setup_py.exists():
            test_cases.append(TestCase(
                test_id=str(uuid.uuid4()),
                test_type=TestType.INTEGRATION,
                name="集成测试",
                description="验证项目整体集成",
                command=f"cd {project_root} && python setup.py check",
                expected_result="集成检查通过",
                timeout_seconds=180,
                critical=False
            ))

        return test_cases

    def _execute_test_cases(self, test_cases: List[TestCase],
                          execution_result: ExecutionResult) -> List[TestResult]:
        """执行测试用例"""
        test_results = []

        for test_case in test_cases:
            try:
                logger.info(f"执行测试: {test_case.name}")
                result = self._execute_single_test(test_case)
                test_results.append(result)
            except Exception as e:
                logger.error(f"测试执行失败: {test_case.name}, 错误: {e}")
                # 创建失败结果
                failed_result = TestResult(
                    test_id=test_case.test_id,
                    test_type=test_case.test_type,
                    status=ValidationStatus.FAILED,
                    execution_time_seconds=0.0,
                    output="",
                    error=str(e),
                    passed=False,
                    warnings=[f"测试执行异常: {e}"]
                )
                test_results.append(failed_result)

        return test_results

    def _execute_single_test(self, test_case: TestCase) -> TestResult:
        """执行单个测试"""
        start_time = time.time()
        output = ""
        error = ""
        warnings = []

        try:
            # 执行测试命令
            result = subprocess.run(
                test_case.command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=test_case.timeout_seconds,
                cwd=Path.cwd()
            )

            execution_time = time.time() - start_time

            if result.returncode == 0:
                status = ValidationStatus.PASSED
                passed = True
                output = result.stdout
            else:
                status = ValidationStatus.FAILED
                passed = False
                output = result.stdout
                error = result.stderr

            # 检查警告
            if "warning" in output.lower() or "warning" in error.lower():
                warnings.append("测试输出包含警告")
                if status == ValidationStatus.PASSED:
                    status = ValidationStatus.WARNING

            return TestResult(
                test_id=test_case.test_id,
                test_type=test_case.test_type,
                status=status,
                execution_time_seconds=execution_time,
                output=output,
                error=error,
                passed=passed,
                warnings=warnings
            )

        except subprocess.TimeoutExpired:
            execution_time = test_case.timeout_seconds
            return TestResult(
                test_id=test_case.test_id,
                test_type=test_case.test_type,
                status=ValidationStatus.FAILED,
                execution_time_seconds=execution_time,
                output="",
                error=f"测试超时 ({test_case.timeout_seconds}秒)",
                passed=False,
                warnings=["测试执行超时"]
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_id=test_case.test_id,
                test_type=test_case.test_type,
                status=ValidationStatus.FAILED,
                execution_time_seconds=execution_time,
                output="",
                error=str(e),
                passed=False,
                warnings=[f"测试执行异常: {e}"]
            )

    def _collect_performance_metrics(self, execution_result: ExecutionResult) -> Dict[str, float]:
        """收集性能指标"""
        metrics = {}

        try:
            # 基于执行结果的性能指标
            metrics["execution_time"] = execution_result.total_time_seconds
            metrics["modification_count"] = len(execution_result.modifications)
            metrics["success_rate"] = 1.0 if execution_result.success else 0.0

            # 文件大小指标
            if execution_result.modifications:
                total_size = 0
                for modification in execution_result.modifications:
                    file_path = Path(modification.file_path)
                    if file_path.exists():
                        total_size += file_path.stat().st_size
                metrics["total_file_size_bytes"] = total_size
                metrics["average_file_size_bytes"] = total_size / len(execution_result.modifications)

            # 代码复杂度指标
            metrics["code_complexity_score"] = self._calculate_code_complexity(execution_result)

        except Exception as e:
            logger.warning(f"收集性能指标失败: {e}")

        return metrics

    def _collect_quality_metrics(self, execution_result: ExecutionResult,
                               test_results: List[TestResult]) -> Dict[str, float]:
        """收集质量指标"""
        metrics = {}

        try:
            # 测试通过率
            if test_results:
                passed_tests = sum(1 for test in test_results if test.passed)
                metrics["test_pass_rate"] = passed_tests / len(test_results)

                # 平均执行时间
                execution_times = [test.execution_time_seconds for test in test_results]
                metrics["average_test_time"] = statistics.mean(execution_times) if execution_times else 0.0

                # 关键测试通过率
                critical_tests = [test for test in test_results if hasattr(TestCase, 'critical')]  # 这里需要调整
                if critical_tests:
                    passed_critical = sum(1 for test in critical_tests if test.passed)
                    metrics["critical_test_pass_rate"] = passed_critical / len(critical_tests)

            # 代码质量指标
            metrics["code_quality_score"] = self._calculate_code_quality(execution_result)
            metrics["maintainability_score"] = self._calculate_maintainability_score(execution_result)

        except Exception as e:
            logger.warning(f"收集质量指标失败: {e}")

        return metrics

    def _calculate_code_complexity(self, execution_result: ExecutionResult) -> float:
        """计算代码复杂度"""
        try:
            total_complexity = 0.0
            file_count = 0

            for modification in execution_result.modifications:
                if modification.file_path.endswith('.py'):
                    code = modification.modified_content
                    # 简单的复杂度计算：基于关键字数量
                    complexity_keywords = ['if', 'elif', 'for', 'while', 'try', 'except', 'with', 'def', 'class']
                    complexity = sum(code.count(keyword) for keyword in complexity_keywords)
                    total_complexity += complexity
                    file_count += 1

            return total_complexity / file_count if file_count > 0 else 0.0

        except:
            return 0.0

    def _calculate_code_quality(self, execution_result: ExecutionResult) -> float:
        """计算代码质量分数"""
        try:
            quality_scores = []

            for modification in execution_result.modifications:
                code = modification.modified_content
                score = 1.0

                # 基本质量检查
                if len(code.strip()) == 0:
                    score -= 0.5
                if code.count('#') / max(len(code.splitlines()), 1) < 0.1:  # 注释比例
                    score -= 0.1

                # 代码长度检查
                if len(code.splitlines()) > 100:
                    score -= 0.2

                quality_scores.append(max(0.0, score))

            return statistics.mean(quality_scores) if quality_scores else 0.0

        except:
            return 0.0

    def _calculate_maintainability_score(self, execution_result: ExecutionResult) -> float:
        """计算可维护性分数"""
        try:
            maintainability_scores = []

            for modification in execution_result.modifications:
                code = modification.modified_content
                score = 1.0

                # 函数长度检查
                functions = code.split('def ')[1:]  # 简单的函数分割
                for func in functions:
                    func_lines = func.split('\n')
                    if len(func_lines) > 50:
                        score -= 0.1

                # 类长度检查
                classes = code.split('class ')[1:]
                for cls in classes:
                    cls_lines = cls.split('\n')
                    if len(cls_lines) > 200:
                        score -= 0.1

                maintainability_scores.append(max(0.0, score))

            return statistics.mean(maintainability_scores) if maintainability_scores else 0.0

        except:
            return 0.0

    def _identify_issues(self, test_results: List[TestResult],
                        performance_metrics: Dict[str, float],
                        quality_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """识别问题"""
        issues = []

        # 测试失败问题
        failed_tests = [test for test in test_results if not test.passed]
        for test in failed_tests:
            issues.append({
                "type": "test_failure",
                "severity": "high" if test.test_type == TestType.SYNTAX else "medium",
                "description": f"测试失败: {test.test_id}",
                "details": test.error,
                "test_type": test.test_type.value,
                "critical": test.test_type == TestType.SYNTAX
            })

        # 性能问题
        if performance_metrics.get("execution_time", 0) > 300:  # 5分钟
            issues.append({
                "type": "performance",
                "severity": "medium",
                "description": "执行时间过长",
                "details": f"执行时间: {performance_metrics['execution_time']}秒"
            })

        # 质量问题
        if quality_metrics.get("code_quality_score", 1.0) < 0.7:
            issues.append({
                "type": "quality",
                "severity": "low",
                "description": "代码质量分数较低",
                "details": f"质量分数: {quality_metrics['code_quality_score']:.2f}"
            })

        return issues

    def _generate_recommendations(self, issues_found: List[Dict[str, Any]],
                                test_results: List[TestResult],
                                performance_metrics: Dict[str, float]) -> List[str]:
        """生成建议"""
        recommendations = []

        # 基于问题的建议
        critical_issues = [issue for issue in issues_found if issue.get("severity") == "high"]
        if critical_issues:
            recommendations.append("存在关键问题，建议立即修复后再进行验证")

        # 基于测试结果的建议
        failed_tests = [test for test in test_results if not test.passed]
        if failed_tests:
            recommendations.append(f"有 {len(failed_tests)} 个测试失败，建议检查相关代码")

        # 基于性能的建议
        if performance_metrics.get("execution_time", 0) > 300:
            recommendations.append("执行时间较长，建议优化代码或分批处理")

        # 基于覆盖率的建议
        if len(test_results) < 5:
            recommendations.append("测试覆盖率较低，建议增加更多测试用例")

        if not recommendations:
            recommendations.append("验证结果良好，修改看起来是成功的")

        return recommendations

    def _calculate_success_rate(self, test_results: List[TestResult]) -> float:
        """计算成功率"""
        if not test_results:
            return 0.0

        passed_tests = sum(1 for test in test_results if test.passed)
        return passed_tests / len(test_results)

    def _determine_overall_status(self, test_results: List[TestResult],
                                issues_found: List[Dict[str, Any]],
                                success_rate: float) -> ValidationStatus:
        """确定整体状态"""
        # 检查是否有关键测试失败
        critical_failures = [
            issue for issue in issues_found
            if issue.get("critical") or issue.get("severity") == "high"
        ]
        if critical_failures:
            return ValidationStatus.FAILED

        # 检查成功率
        if success_rate >= 0.9:
            return ValidationStatus.PASSED
        elif success_rate >= 0.7:
            return ValidationStatus.WARNING
        else:
            return ValidationStatus.FAILED

    def _generate_summary(self, validation_result: ValidationResult) -> str:
        """生成摘要"""
        passed_tests = sum(1 for test in validation_result.test_results if test.passed)
        total_tests = len(validation_result.test_results)

        summary = f"验证 {validation_result.validation_id} 完成。\n"
        summary += f"整体状态: {validation_result.overall_status.value}\n"
        summary += f"测试通过率: {passed_tests}/{total_tests} ({validation_result.success_rate:.1%})\n"
        summary += f"验证时间: {validation_result.validation_time_seconds}秒\n"
        summary += f"发现问题: {len(validation_result.issues_found)}个\n"

        if validation_result.issues_found:
            high_issues = [issue for issue in validation_result.issues_found if issue.get("severity") == "high"]
            if high_issues:
                summary += f"包含 {len(high_issues)} 个高优先级问题\n"

        return summary

    def _generate_detailed_findings(self, validation_result: ValidationResult) -> List[str]:
        """生成详细发现"""
        findings = []

        # 测试结果发现
        passed_tests = [test for test in validation_result.test_results if test.passed]
        failed_tests = [test for test in validation_result.test_results if not test.passed]

        if passed_tests:
            findings.append(f"✓ {len(passed_tests)} 个测试通过，包括 {', '.join(set(test.test_type.value for test in passed_tests))}")

        if failed_tests:
            findings.append(f"✗ {len(failed_tests)} 个测试失败:")
            for test in failed_tests[:5]:  # 限制显示数量
                findings.append(f"  - {test.test_type.value}: {test.error[:100]}...")

        # 性能发现
        if validation_result.performance_metrics:
            exec_time = validation_result.performance_metrics.get("execution_time", 0)
            if exec_time > 300:
                findings.append(f"⚠ 执行时间较长: {exec_time}秒")

        # 质量发现
        if validation_result.quality_metrics:
            quality_score = validation_result.quality_metrics.get("code_quality_score", 1.0)
            if quality_score < 0.7:
                findings.append(f"⚠ 代码质量分数较低: {quality_score:.2f}")

        return findings

    def _assess_impact(self, validation_result: ValidationResult) -> str:
        """评估影响"""
        if validation_result.overall_status == ValidationStatus.PASSED:
            return "修改验证通过，对系统有正面影响，修复了目标问题"
        elif validation_result.overall_status == ValidationStatus.WARNING:
            return "修改基本成功，但存在一些需要注意的问题，建议进一步优化"
        else:
            return "修改存在问题，可能对系统产生负面影响，建议修复问题后重新验证"

    def _determine_next_steps(self, validation_result: ValidationResult) -> List[str]:
        """确定下一步行动"""
        next_steps = []

        if validation_result.overall_status == ValidationStatus.PASSED:
            next_steps.append("✓ 可以继续后续工作流程")
            next_steps.append("✓ 建议部署到测试环境进一步验证")
        elif validation_result.overall_status == ValidationStatus.WARNING:
            next_steps.append("⚠ 建议修复警告问题")
            next_steps.append("⚠ 重新验证修改结果")
        else:
            next_steps.append("✗ 必须修复失败问题")
            next_steps.append("✗ 考虑回滚修改")
            next_steps.append("✗ 重新分析和修复")

        # 基于建议添加行动
        if validation_result.recommendations:
            next_steps.extend([f"建议: {rec}" for rec in validation_result.recommendations[:3]])

        return next_steps

    def _determine_approval_required(self, validation_result: ValidationResult) -> bool:
        """确定是否需要审批"""
        # 如果验证失败或有高优先级问题，需要审批
        if validation_result.overall_status == ValidationStatus.FAILED:
            return True

        high_issues = [
            issue for issue in validation_result.issues_found
            if issue.get("severity") == "high"
        ]
        if high_issues:
            return True

        # 如果成功率较低，需要审批
        if validation_result.success_rate < 0.8:
            return True

        return False

    def _calculate_confidence_score(self, validation_result: ValidationResult) -> float:
        """计算置信度分数"""
        score = 0.0

        # 基于成功率
        score += validation_result.success_rate * 0.4

        # 基于测试数量
        test_count_bonus = min(len(validation_result.test_results) / 10, 0.2)
        score += test_count_bonus

        # 基于质量指标
        quality_score = validation_result.quality_metrics.get("code_quality_score", 0.5)
        score += quality_score * 0.2

        # 基于问题数量
        issue_penalty = len(validation_result.issues_found) * 0.05
        score = max(0.0, score - issue_penalty)

        return min(1.0, score)

    def _init_test_generators(self) -> Dict[str, Callable]:
        """初始化测试生成器"""
        return {
            "basic": self._generate_basic_tests,
            "standard": self._generate_standard_tests,
            "comprehensive": self._generate_comprehensive_tests,
            "thorough": self._generate_thorough_tests
        }

    def _create_failed_validation_result(self, execution_result: ExecutionResult, error_message: str) -> ValidationResult:
        """创建失败验证结果"""
        return ValidationResult(
            validation_id=str(uuid.uuid4()),
            execution_id=execution_result.execution_id,
            overall_status=ValidationStatus.FAILED,
            validation_level=ValidationLevel.BASIC,
            test_results=[],
            performance_metrics={},
            quality_metrics={},
            issues_found=[{"type": "validation_error", "description": error_message}],
            recommendations=[],
            validation_time_seconds=0,
            success_rate=0.0,
            timestamp=datetime.now(),
            metadata={"error": error_message}
        )

    def _record_validation(self, validation_result: ValidationResult) -> None:
        """记录验证历史"""
        self._validation_history.append(validation_result)

        # 限制历史记录数量
        if len(self._validation_history) > 100:
            self._validation_history = self._validation_history[-50:]

    def export_validation_history(self, limit: Optional[int] = None) -> str:
        """导出验证历史"""
        history = self.get_validation_history(limit)

        exportable_history = []
        for record in history:
            record_dict = asdict(record)
            record_dict["timestamp"] = record.timestamp.isoformat()

            # 转换测试结果
            for test_result in record_dict["test_results"]:
                test_result["status"] = test_result["status"].value
                test_result["test_type"] = test_result["test_type"].value

            exportable_history.append(record_dict)

        return json.dumps(exportable_history, ensure_ascii=False, indent=2)