"""
修复确认管理器
负责处理用户确认界面和交互流程
"""

import sys
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .fix_generator import FixResult, FixSuggestion
from .diff_viewer import DiffViewer, DiffResult


class ConfirmationStatus(Enum):
    """确认状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


@dataclass
class ConfirmationRequest:
    """确认请求"""
    fix_id: str
    file_path: str
    fix_result: FixResult
    diff_result: DiffResult
    backup_id: str
    timestamp: str
    timeout_seconds: int = 300  # 5分钟超时
    auto_approve_safe: bool = False
    require_explicit_confirmation: bool = True


@dataclass
class ConfirmationResponse:
    """确认响应"""
    fix_id: str
    status: ConfirmationStatus
    selected_suggestions: List[int] = field(default_factory=list)  # 选中的建议索引
    user_message: str = ""
    response_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfirmationSession:
    """确认会话"""
    session_id: str
    requests: List[ConfirmationRequest] = field(default_factory=list)
    responses: List[ConfirmationResponse] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""
    total_files: int = 0
    approved_files: int = 0
    rejected_files: int = 0
    partial_files: int = 0


class FixConfirmationManager:
    """修复确认管理器"""

    def __init__(self, config_manager=None):
        """
        初始化确认管理器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 初始化差异查看器
        self.diff_viewer = DiffViewer(config_manager)

        # 获取配置
        try:
            self.config = self.config_manager.get_section('fix_confirmation')
        except:
            self.config = {}

        self.default_timeout = self.config.get('default_timeout', 300)
        self.auto_approve_safe = self.config.get('auto_approve_safe', False)
        self.show_diff_summary = self.config.get('show_diff_summary', True)
        self.interactive_mode = self.config.get('interactive_mode', True)
        self.batch_mode = self.config.get('batch_mode', False)

        # 确认回调函数
        self.confirmation_callback: Optional[Callable[[ConfirmationRequest], ConfirmationResponse]] = None

        self.logger.info("FixConfirmationManager initialized")

    def set_confirmation_callback(self, callback: Callable[[ConfirmationRequest], ConfirmationResponse]):
        """
        设置确认回调函数

        Args:
            callback: 确认回调函数
        """
        self.confirmation_callback = callback
        self.logger.info("Confirmation callback set")

    def request_confirmation(self, fix_id: str, file_path: str, fix_result: FixResult,
                           diff_result: DiffResult, backup_id: str,
                           timeout_seconds: Optional[int] = None) -> ConfirmationResponse:
        """
        请求用户确认

        Args:
            fix_id: 修复ID
            file_path: 文件路径
            fix_result: 修复结果
            diff_result: 差异结果
            backup_id: 备份ID
            timeout_seconds: 超时时间（秒）

        Returns:
            确认响应
        """
        start_time = time.time()

        self.logger.info(f"Requesting confirmation for fix {fix_id} on {file_path}")

        # 创建确认请求
        request = ConfirmationRequest(
            fix_id=fix_id,
            file_path=file_path,
            fix_result=fix_result,
            diff_result=diff_result,
            backup_id=backup_id,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            timeout_seconds=timeout_seconds or self.default_timeout,
            auto_approve_safe=self.auto_approve_safe,
            require_explicit_confirmation=not self.batch_mode
        )

        try:
            # 检查是否自动批准
            if self._should_auto_approve(request):
                response = ConfirmationResponse(
                    fix_id=fix_id,
                    status=ConfirmationStatus.APPROVED,
                    user_message="Auto-approved: all fixes are safe",
                    response_time=time.time() - start_time
                )
                self.logger.info(f"Fix {fix_id} auto-approved")
                return response

            # 使用回调函数或内置确认机制
            if self.confirmation_callback:
                response = self.confirmation_callback(request)
            else:
                response = self._interactive_confirmation(request)

            response.response_time = time.time() - start_time
            self.logger.info(f"Confirmation received for fix {fix_id}: {response.status.value}")

            return response

        except Exception as e:
            self.logger.error(f"Error during confirmation for fix {fix_id}: {e}")
            return ConfirmationResponse(
                fix_id=fix_id,
                status=ConfirmationStatus.CANCELLED,
                user_message=f"Confirmation error: {e}",
                response_time=time.time() - start_time
            )

    def batch_request_confirmation(self, requests: List[ConfirmationRequest]) -> List[ConfirmationResponse]:
        """
        批量请求确认

        Args:
            requests: 确认请求列表

        Returns:
            确认响应列表
        """
        self.logger.info(f"Processing batch confirmation for {len(requests)} fixes")

        responses = []

        if self.batch_mode:
            # 批量模式 - 一次性确认所有修复
            response = self._batch_confirmation(requests)
            responses.extend([response] * len(requests))
        else:
            # 逐个确认
            for request in requests:
                response = self.request_confirmation(
                    request.fix_id,
                    request.file_path,
                    request.fix_result,
                    request.diff_result,
                    request.backup_id,
                    request.timeout_seconds
                )
                responses.append(response)

                # 如果用户取消，停止后续确认
                if response.status == ConfirmationStatus.CANCELLED:
                    break

        return responses

    def create_confirmation_session(self, requests: List[ConfirmationRequest]) -> ConfirmationSession:
        """
        创建确认会话

        Args:
            requests: 确认请求列表

        Returns:
            确认会话
        """
        import uuid

        session = ConfirmationSession(
            session_id=str(uuid.uuid4()),
            requests=requests,
            start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            total_files=len(requests)
        )

        # 处理确认
        responses = self.batch_request_confirmation(requests)
        session.responses = responses

        # 统计结果
        for response in responses:
            if response.status == ConfirmationStatus.APPROVED:
                session.approved_files += 1
            elif response.status == ConfirmationStatus.REJECTED:
                session.rejected_files += 1
            elif response.status == ConfirmationStatus.PARTIAL:
                session.partial_files += 1

        session.end_time = time.strftime("%Y-%m-%d %H:%M:%S")

        self.logger.info(f"Confirmation session {session.session_id} completed: "
                        f"{session.approved_files} approved, {session.rejected_files} rejected, "
                        f"{session.partial_files} partial")

        return session

    def _should_auto_approve(self, request: ConfirmationRequest) -> bool:
        """判断是否应该自动批准"""
        if not request.auto_approve_safe:
            return False

            # 检查所有修复建议是否安全
        complexity = self.diff_viewer.analyze_change_complexity(request.diff_result)
        if complexity.get('complexity') == 'high':
            self.logger.warning(f"Fix {request.fix_id} contains high-complexity changes, requiring manual review")
            return False

        # 检查每个建议的置信度
        for suggestion in request.fix_result.suggestions:
            if suggestion.confidence < 0.8:
                self.logger.warning(f"Fix {request.fix_id} has low confidence suggestions, requiring manual review")
                return False

        return True

    def _interactive_confirmation(self, request: ConfirmationRequest) -> ConfirmationResponse:
        """交互式确认"""
        if not self.interactive_mode:
            # 非交互模式，默认批准
            return ConfirmationResponse(
                fix_id=request.fix_id,
                status=ConfirmationStatus.APPROVED,
                user_message="Auto-approved (non-interactive mode)"
            )

        # 显示修复摘要
        self._display_fix_summary(request)

        # 显示代码差异
        if self.show_diff_summary:
            self._display_diff_summary(request.diff_result)

        # 获取用户输入
        while True:
            try:
                choice = self._get_user_choice(request)

                if choice in ['y', 'yes', 'Y', 'YES']:
                    return ConfirmationResponse(
                        fix_id=request.fix_id,
                        status=ConfirmationStatus.APPROVED,
                        user_message="User approved all fixes"
                    )
                elif choice in ['n', 'no', 'N', 'NO']:
                    return ConfirmationResponse(
                        fix_id=request.fix_id,
                        status=ConfirmationStatus.REJECTED,
                        user_message="User rejected fixes"
                    )
                elif choice in ['p', 'partial', 'P', 'PARTIAL']:
                    selected = self._select_specific_suggestions(request)
                    return ConfirmationResponse(
                        fix_id=request.fix_id,
                        status=ConfirmationStatus.PARTIAL,
                        selected_suggestions=selected,
                        user_message=f"User approved selected fixes: {selected}"
                    )
                elif choice in ['d', 'details', 'D', 'DETAILS']:
                    self._display_detailed_fixes(request)
                elif choice in ['q', 'quit', 'Q', 'QUIT']:
                    return ConfirmationResponse(
                        fix_id=request.fix_id,
                        status=ConfirmationStatus.CANCELLED,
                        user_message="User cancelled"
                    )
                else:
                    print("无效选择，请重新输入")

            except KeyboardInterrupt:
                return ConfirmationResponse(
                    fix_id=request.fix_id,
                    status=ConfirmationStatus.CANCELLED,
                    user_message="User interrupted (Ctrl+C)"
                )
            except EOFError:
                return ConfirmationResponse(
                    fix_id=request.fix_id,
                    status=ConfirmationStatus.CANCELLED,
                    user_message="End of input"
                )

    def _batch_confirmation(self, requests: List[ConfirmationRequest]) -> ConfirmationResponse:
        """批量确认"""
        print(f"\n{'='*80}")
        print(f"批量修复确认 - 共 {len(requests)} 个文件")
        print(f"{'='*80}")

        # 显示所有文件摘要
        for i, request in enumerate(requests, 1):
            print(f"\n{i}. {request.file_path}")
            print(f"   修复建议数: {len(request.fix_result.suggestions)}")
            print(f"   差异: {request.diff_result.summary}")

            # 分析复杂度
            complexity = self.diff_viewer.analyze_change_complexity(request.diff_result)
            print(f"   复杂度: {complexity.get('complexity', 'unknown')}")

        print(f"\n{'='*80}")

        while True:
            try:
                print("\n批量修复选项:")
                print("  y/yes    - 批准所有修复")
                print("  n/no     - 拒绝所有修复")
                print("  d/details - 查看详细信息")
                print("  q/quit   - 取消操作")

                choice = input("\n请选择 (y/n/d/q): ").strip().lower()

                if choice in ['y', 'yes']:
                    return ConfirmationResponse(
                        fix_id="batch",
                        status=ConfirmationStatus.APPROVED,
                        user_message="User approved all batch fixes"
                    )
                elif choice in ['n', 'no']:
                    return ConfirmationResponse(
                        fix_id="batch",
                        status=ConfirmationStatus.REJECTED,
                        user_message="User rejected all batch fixes"
                    )
                elif choice in ['d', 'details']:
                    for request in requests:
                        self._display_detailed_fixes(request)
                        print("\n" + "-"*80)
                elif choice in ['q', 'quit']:
                    return ConfirmationResponse(
                        fix_id="batch",
                        status=ConfirmationStatus.CANCELLED,
                        user_message="User cancelled batch operation"
                    )
                else:
                    print("无效选择，请重新输入")

            except (KeyboardInterrupt, EOFError):
                return ConfirmationResponse(
                    fix_id="batch",
                    status=ConfirmationStatus.CANCELLED,
                    user_message="User cancelled"
                )

    def _display_fix_summary(self, request: ConfirmationRequest):
        """显示修复摘要"""
        print(f"\n{'='*80}")
        print(f"修复确认 - {request.file_path}")
        print(f"修复ID: {request.fix_id}")
        print(f"备份ID: {request.backup_id}")
        print(f"时间: {request.timestamp}")
        print(f"{'='*80}")

        # 显示修复统计
        stats = request.diff_result.stats
        print(f"变更统计:")
        print(f"  原始行数: {stats['old_lines']}")
        print(f"  修复后行数: {stats['new_lines']}")
        print(f"  新增: {stats['added']}")
        print(f"  删除: {stats['deleted']}")
        print(f"  修改: {stats['modified']}")

        # 显示修复建议摘要
        suggestions = request.fix_result.suggestions
        print(f"\n修复建议 ({len(suggestions)} 个):")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.issue_type} - {suggestion.description}")
            print(f"     严重程度: {suggestion.severity}, 置信度: {suggestion.confidence:.2f}")

    def _display_diff_summary(self, diff_result: DiffResult):
        """显示差异摘要"""
        print(f"\n代码差异摘要:")
        print(f"  {diff_result.summary}")

        # 分析复杂度
        complexity = self.diff_viewer.analyze_change_complexity(diff_result)
        print(f"  复杂度: {complexity.get('complexity', 'unknown')}")
        print(f"  变更比例: {complexity.get('change_ratio', 0):.1%}")

        if complexity.get('risk_factors'):
            print(f"  风险因素: {', '.join(complexity['risk_factors'])}")

        print(f"  建议: {complexity.get('recommendation', '')}")

    def _display_detailed_fixes(self, request: ConfirmationRequest):
        """显示详细修复信息"""
        print(f"\n详细修复信息 - {request.file_path}")
        print("-" * 80)

        suggestions = request.fix_result.suggestions
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n修复建议 {i}:")
            print(f"  类型: {suggestion.issue_type}")
            print(f"  描述: {suggestion.description}")
            if suggestion.location:
                print(f"  位置: 行 {suggestion.location.get('line', 'N/A')}")
            print(f"  严重程度: {suggestion.severity}")
            print(f"  置信度: {suggestion.confidence:.2f}")
            print(f"  标签: {', '.join(suggestion.tags)}")
            print(f"  说明: {suggestion.explanation}")

            print(f"\n  修复代码:")
            print("  ```python")
            for line in suggestion.fixed_code.split('\n'):
                print(f"  {line}")
            print("  ```")

        print("\n" + "="*80)

    def _select_specific_suggestions(self, request: ConfirmationRequest) -> List[int]:
        """选择特定修复建议"""
        suggestions = request.fix_result.suggestions
        if not suggestions:
            return []

        print(f"\n选择要应用的修复建议 (1-{len(suggestions)}):")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"  {i}. {suggestion.issue_type} - {suggestion.description}")

        while True:
            try:
                choice = input("请输入要应用的修复编号 (用逗号分隔，如: 1,3,5): ").strip()
                if not choice:
                    return []

                selected_indices = []
                for part in choice.split(','):
                    part = part.strip()
                    if '-' in part:
                        # 处理范围，如: 1-3
                        start, end = map(int, part.split('-'))
                        selected_indices.extend(range(start, end + 1))
                    else:
                        selected_indices.append(int(part))

                # 验证选择
                valid_indices = [i for i in selected_indices if 1 <= i <= len(suggestions)]
                if valid_indices:
                    print(f"已选择修复建议: {valid_indices}")
                    return [i - 1 for i in valid_indices]  # 转换为0-based索引
                else:
                    print("无效的选择，请重新输入")

            except (ValueError, KeyboardInterrupt, EOFError):
                print("输入无效，取消选择")
                return []

    def _get_user_choice(self, request: ConfirmationRequest) -> str:
        """获取用户选择"""
        print(f"\n修复选项:")
        print("  y/yes      - 批准所有修复")
        print("  n/no       - 拒绝所有修复")
        print("  p/partial  - 选择特定修复")
        print("  d/details  - 查看详细信息")
        print("  q/quit     - 取消操作")

        return input("\n请选择 (y/n/p/d/q): ").strip().lower()

    def generate_confirmation_report(self, session: ConfirmationSession) -> str:
        """生成确认报告"""
        report_lines = [
            f"修复确认报告",
            f"=" * 60,
            f"会话ID: {session.session_id}",
            f"开始时间: {session.start_time}",
            f"结束时间: {session.end_time}",
            f"总文件数: {session.total_files}",
            f"批准文件数: {session.approved_files}",
            f"拒绝文件数: {session.rejected_files}",
            f"部分批准文件数: {session.partial_files}",
            "",
            f"详细结果:",
            "-" * 40
        ]

        for i, (request, response) in enumerate(zip(session.requests, session.responses), 1):
            report_lines.extend([
                f"",
                f"{i}. {request.file_path}",
                f"   状态: {response.status.value}",
                f"   修复数: {len(request.fix_result.suggestions)}",
                f"   用户消息: {response.user_message}",
                f"   响应时间: {response.response_time:.2f}秒"
            ])

            if response.selected_suggestions:
                report_lines.append(f"   选择的修复: {response.selected_suggestions}")

        return "\n".join(report_lines)