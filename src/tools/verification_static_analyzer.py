#!/usr/bin/env python3
"""
验证静态分析执行器 - T014.1
对修复后的代码执行静态分析，检查问题解决情况
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .workflow_flow_state_manager import WorkflowSession
from .workflow_data_types import AIFixSuggestion
from .project_analysis_types import StaticAnalysisResult
from .static_coordinator import StaticAnalysisCoordinator
from .project_analysis_types import StaticAnalysisResult, Issue, IssueSeverity, IssueType

logger = get_logger()


@dataclass
class VerificationIssue:
    """验证中发现的问题"""
    issue_id: str
    file_path: str
    line: int
    issue_type: str
    severity: str
    message: str
    code_snippet: str
    tool_name: str
    is_new_issue: bool  # 是否为新问题
    is_original_fixed: bool  # 是否修复了原问题

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "issue_id": self.issue_id,
            "file_path": self.file_path,
            "line": self.line,
            "issue_type": self.issue_type,
            "severity": self.severity,
            "message": self.message,
            "code_snippet": self.code_snippet,
            "tool_name": self.tool_name,
            "is_new_issue": self.is_new_issue,
            "is_original_fixed": self.is_original_fixed
        }


@dataclass
class FixComparison:
    """修复前后对比"""
    original_issues: List[Issue]
    current_issues: List[Issue]
    fixed_issues: List[str]  # 已修复的问题ID列表
    remaining_issues: List[str]  # 仍然存在的问题ID列表
    new_issues: List[Issue]  # 新引入的问题

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "original_issues": [issue.to_dict() for issue in self.original_issues],
            "current_issues": [issue.to_dict() for issue in self.current_issues],
            "fixed_issues": self.fixed_issues,
            "remaining_issues": self.remaining_issues,
            "new_issues": [issue.to_dict() for issue in self.new_issues]
        }


@dataclass
class StaticVerificationReport:
    """静态验证报告"""
    verification_id: str
    session_id: str
    suggestion_id: str
    file_path: str
    verification_timestamp: datetime
    fix_comparison: FixComparison
    verification_issues: List[VerificationIssue]
    success_rate: float
    new_issues_count: int
    overall_quality_score: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "verification_id": self.verification_id,
            "session_id": self.session_id,
            "suggestion_id": self.suggestion_id,
            "file_path": self.file_path,
            "verification_timestamp": self.verification_timestamp.isoformat(),
            "fix_comparison": self.fix_comparison.to_dict(),
            "verification_issues": [issue.to_dict() for issue in self.verification_issues],
            "success_rate": self.success_rate,
            "new_issues_count": self.new_issues_count,
            "overall_quality_score": self.overall_quality_score
        }


class VerificationStatus(Enum):
    """验证状态"""
    SUCCESS = "success"           # 修复成功
    PARTIAL_SUCCESS = "partial_success"  # 部分成功
    FAILED = "failed"            # 修复失败
    REGRESSED = "regressed"      # 出现回退


class VerificationStaticAnalyzer:
    """验证静态分析执行器 - T014.1

    工作流位置: 节点H第一步，对修复后的代码执行静态分析
    核心功能: 运用静态分析工具分析修复后的代码质量
    AI集成: 为AI动态分析提供修复后的静态分析结果
    """

    def __init__(self, config_manager=None):
        """初始化验证静态分析执行器"""
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        self.config = self.config_manager.get("project_analysis", {})
        self.static_coordinator = StaticAnalysisCoordinator()

        # 验证结果存储目录
        self.verification_dir = Path(self.config.get("verification_dir", ".fix_backups/verifications"))
        self.verification_dir.mkdir(parents=True, exist_ok=True)

    def verify_fix_with_static_analysis(
        self,
        session_id: str,
        suggestion_id: str,
        original_analysis: StaticAnalysisResult,
        modified_file_path: str
    ) -> StaticVerificationReport:
        """
        使用静态分析验证修复效果

        Args:
            session_id: 会话ID
            suggestion_id: 修复建议ID
            original_analysis: 修复前的静态分析结果
            modified_file_path: 修改后的文件路径

        Returns:
            StaticVerificationReport: 静态验证报告
        """
        try:
            self.logger.info(f"开始静态分析验证: 会话={session_id}, 文件={modified_file_path}")

            # 1. 对修复后的文件执行静态分析
            current_analysis = self._analyze_modified_file(modified_file_path)

            # 2. 对比修复前后的分析结果
            fix_comparison = self._compare_analysis_results(
                original_analysis, current_analysis, suggestion_id
            )

            # 3. 生成验证问题列表
            verification_issues = self._generate_verification_issues(
                fix_comparison, current_analysis
            )

            # 4. 计算成功率和质量分数
            success_rate = self._calculate_success_rate(fix_comparison)
            quality_score = self._calculate_quality_score(verification_issues)
            new_issues_count = len(fix_comparison.new_issues)

            # 5. 创建验证报告
            verification_report = StaticVerificationReport(
                verification_id=str(uuid.uuid4()),
                session_id=session_id,
                suggestion_id=suggestion_id,
                file_path=modified_file_path,
                verification_timestamp=datetime.now(),
                fix_comparison=fix_comparison,
                verification_issues=verification_issues,
                success_rate=success_rate,
                new_issues_count=new_issues_count,
                overall_quality_score=quality_score
            )

            # 6. 保存验证报告
            self._save_verification_report(verification_report)

            self.logger.info(f"静态分析验证完成: 成功率={success_rate:.2%}, 新问题={new_issues_count}")
            return verification_report

        except Exception as e:
            self.logger.error(f"静态分析验证失败: {e}")
            raise

    def _analyze_modified_file(self, file_path: str) -> StaticAnalysisResult:
        """分析修改后的文件"""
        try:
            # 使用静态分析协调器分析文件
            result = self.static_coordinator.analyze_file(file_path)

            if not result.success:
                raise RuntimeError(f"静态分析失败: {result.error}")

            return result

        except Exception as e:
            self.logger.error(f"分析修改后文件失败: {e}")
            # 创建一个空的分析结果作为后备
            return StaticAnalysisResult(
                file_path=file_path,
                issues=[],
                execution_time=0.0,
                summary={"error": str(e)},
                success=False
            )

    def _compare_analysis_results(
        self,
        original: StaticAnalysisResult,
        current: StaticAnalysisResult,
        suggestion_id: str
    ) -> FixComparison:
        """对比修复前后的分析结果"""
        original_issues = original.issues if hasattr(original, 'issues') else []
        current_issues = current.issues if hasattr(current, 'issues') else []

        # 找出修复的问题
        fixed_issues = []
        remaining_issues = []

        # 创建当前问题的集合用于快速查找
        current_issue_signatures = set()
        for issue in current_issues:
            signature = self._create_issue_signature(issue)
            current_issue_signatures.add(signature)

        # 检查原始问题是否已修复
        for original_issue in original_issues:
            original_signature = self._create_issue_signature(original_issue)
            if original_signature in current_issue_signatures:
                remaining_issues.append(original_issue.issue_id)
            else:
                fixed_issues.append(original_issue.issue_id)

        # 找出新引入的问题
        new_issues = []
        original_issue_signatures = set()
        for issue in original_issues:
            signature = self._create_issue_signature(issue)
            original_issue_signatures.add(signature)

        for current_issue in current_issues:
            current_signature = self._create_issue_signature(current_issue)
            if current_signature not in original_issue_signatures:
                new_issues.append(current_issue)

        return FixComparison(
            original_issues=original_issues,
            current_issues=current_issues,
            fixed_issues=fixed_issues,
            remaining_issues=remaining_issues,
            new_issues=new_issues
        )

    def _create_issue_signature(self, issue: Issue) -> str:
        """创建问题签名用于比较"""
        # 使用文件路径、行号、类型和消息创建签名
        return f"{issue.file_path}:{issue.line}:{issue.issue_type.value}:{issue.message[:100]}"

    def _generate_verification_issues(
        self,
        fix_comparison: FixComparison,
        current_analysis: StaticAnalysisResult
    ) -> List[VerificationIssue]:
        """生成验证问题列表"""
        verification_issues = []

        # 为新引入的问题创建验证记录
        for new_issue in fix_comparison.new_issues:
            verification_issue = VerificationIssue(
                issue_id=new_issue.issue_id,
                file_path=new_issue.file_path,
                line=new_issue.line,
                issue_type=new_issue.issue_type.value,
                severity=new_issue.severity.value,
                message=new_issue.message,
                code_snippet=new_issue.code_snippet or "",
                tool_name=getattr(new_issue, 'tool_name', 'unknown'),
                is_new_issue=True,
                is_original_fixed=False
            )
            verification_issues.append(verification_issue)

        # 为仍然存在的问题创建验证记录
        for remaining_issue_id in fix_comparison.remaining_issues:
            # 找到对应的问题
            for issue in fix_comparison.current_issues:
                if issue.issue_id == remaining_issue_id:
                    verification_issue = VerificationIssue(
                        issue_id=issue.issue_id,
                        file_path=issue.file_path,
                        line=issue.line,
                        issue_type=issue.issue_type.value,
                        severity=issue.severity.value,
                        message=issue.message,
                        code_snippet=issue.code_snippet or "",
                        tool_name=getattr(issue, 'tool_name', 'unknown'),
                        is_new_issue=False,
                        is_original_fixed=False
                    )
                    verification_issues.append(verification_issue)
                    break

        return verification_issues

    def _calculate_success_rate(self, fix_comparison: FixComparison) -> float:
        """计算修复成功率"""
        total_original_issues = len(fix_comparison.original_issues)
        if total_original_issues == 0:
            return 1.0

        fixed_count = len(fix_comparison.fixed_issues)
        return fixed_count / total_original_issues

    def _calculate_quality_score(self, verification_issues: List[VerificationIssue]) -> float:
        """计算整体质量分数"""
        if not verification_issues:
            return 1.0

        # 根据问题严重程度计算分数
        severity_weights = {
            "error": 0.1,
            "warning": 0.3,
            "info": 0.6
        }

        total_score = 0.0
        for issue in verification_issues:
            weight = severity_weights.get(issue.severity, 0.5)
            if issue.is_new_issue:
                weight *= 0.5  # 新问题扣分更多
            total_score += weight

        max_possible_score = len(verification_issues)
        if max_possible_score == 0:
            return 1.0

        return max(0.0, total_score / max_possible_score)

    def _save_verification_report(self, report: StaticVerificationReport) -> None:
        """保存验证报告"""
        try:
            report_file = self.verification_dir / f"verification_{report.session_id}_{report.suggestion_id}.json"

            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

            self.logger.info(f"验证报告已保存: {report_file}")

        except Exception as e:
            self.logger.error(f"保存验证报告失败: {e}")

    def batch_verify_fixes(
        self,
        session_id: str,
        verification_tasks: List[Dict[str, Any]]
    ) -> List[StaticVerificationReport]:
        """
        批量验证修复效果

        Args:
            session_id: 会话ID
            verification_tasks: 验证任务列表，每个包含suggestion_id, original_analysis, file_path

        Returns:
            List[StaticVerificationReport]: 验证报告列表
        """
        try:
            self.logger.info(f"开始批量验证修复: 会话={session_id}, 任务数={len(verification_tasks)}")

            reports = []
            for task in verification_tasks:
                try:
                    report = self.verify_fix_with_static_analysis(
                        session_id=session_id,
                        suggestion_id=task["suggestion_id"],
                        original_analysis=task["original_analysis"],
                        modified_file_path=task["file_path"]
                    )
                    reports.append(report)

                except Exception as e:
                    self.logger.error(f"批量验证单个任务失败: {e}")
                    # 创建一个失败报告
                    failure_report = StaticVerificationReport(
                        verification_id=str(uuid.uuid4()),
                        session_id=session_id,
                        suggestion_id=task["suggestion_id"],
                        file_path=task["file_path"],
                        verification_timestamp=datetime.now(),
                        fix_comparison=FixComparison([], [], [], [], []),
                        verification_issues=[],
                        success_rate=0.0,
                        new_issues_count=0,
                        overall_quality_score=0.0
                    )
                    reports.append(failure_report)

            self.logger.info(f"批量验证完成: 成功={len(reports)}")
            return reports

        except Exception as e:
            self.logger.error(f"批量验证失败: {e}")
            return []

    def get_verification_report(self, session_id: str, suggestion_id: str) -> Optional[StaticVerificationReport]:
        """
        获取验证报告

        Args:
            session_id: 会话ID
            suggestion_id: 修复建议ID

        Returns:
            Optional[StaticVerificationReport]: 验证报告
        """
        try:
            report_file = self.verification_dir / f"verification_{session_id}_{suggestion_id}.json"

            if not report_file.exists():
                return None

            with open(report_file, 'r', encoding='utf-8') as f:
                report_data = json.load(f)

            # 重新构建报告对象
            return self._reconstruct_report(report_data)

        except Exception as e:
            self.logger.error(f"获取验证报告失败: {e}")
            return None

    def _reconstruct_report(self, report_data: Dict[str, Any]) -> StaticVerificationReport:
        """从字典数据重构验证报告"""
        # 重构FixComparison
        fix_comparison_data = report_data["fix_comparison"]
        original_issues = [Issue.from_dict(data) for data in fix_comparison_data["original_issues"]]
        current_issues = [Issue.from_dict(data) for data in fix_comparison_data["current_issues"]]
        new_issues = [Issue.from_dict(data) for data in fix_comparison_data["new_issues"]]

        fix_comparison = FixComparison(
            original_issues=original_issues,
            current_issues=current_issues,
            fixed_issues=fix_comparison_data["fixed_issues"],
            remaining_issues=fix_comparison_data["remaining_issues"],
            new_issues=new_issues
        )

        # 重构VerificationIssue列表
        verification_issues = []
        for issue_data in report_data["verification_issues"]:
            verification_issue = VerificationIssue(
                issue_id=issue_data["issue_id"],
                file_path=issue_data["file_path"],
                line=issue_data["line"],
                issue_type=issue_data["issue_type"],
                severity=issue_data["severity"],
                message=issue_data["message"],
                code_snippet=issue_data["code_snippet"],
                tool_name=issue_data["tool_name"],
                is_new_issue=issue_data["is_new_issue"],
                is_original_fixed=issue_data["is_original_fixed"]
            )
            verification_issues.append(verification_issue)

        # 重构完整报告
        return StaticVerificationReport(
            verification_id=report_data["verification_id"],
            session_id=report_data["session_id"],
            suggestion_id=report_data["suggestion_id"],
            file_path=report_data["file_path"],
            verification_timestamp=datetime.fromisoformat(report_data["verification_timestamp"]),
            fix_comparison=fix_comparison,
            verification_issues=verification_issues,
            success_rate=report_data["success_rate"],
            new_issues_count=report_data["new_issues_count"],
            overall_quality_score=report_data["overall_quality_score"]
        )