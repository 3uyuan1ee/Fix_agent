#!/usr/bin/env python3
"""
分析修复命令模块
实现`analyze fix`命令的处理逻辑，提供修复建议和确认流程
"""

import difflib
import json
import shutil
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..agent.orchestrator import AgentOrchestrator
from ..utils.config import ConfigManager
from ..utils.logger import get_logger

logger = get_logger()


@dataclass
class FixSuggestion:
    """修复建议数据类"""

    file_path: str
    issue_type: str
    description: str
    line_number: int
    original_code: str
    fixed_code: str
    severity: str = "medium"  # low, medium, high, critical
    confidence: float = 0.8  # 0.0-1.0
    auto_applicable: bool = True


@dataclass
class FixResult:
    """修复结果数据类"""

    success: bool
    target: str
    suggestions: List[FixSuggestion]
    applied_fixes: List[FixSuggestion] = field(default_factory=list)
    failed_fixes: List[FixSuggestion] = field(default_factory=list)
    backup_files: Dict[str, str] = field(default_factory=dict)
    execution_time: float = 0.0
    total_issues: int = 0
    fixed_issues: int = 0


class CodeDiffer:
    """代码差异对比器"""

    @staticmethod
    def generate_diff(original: str, fixed: str, file_path: str) -> str:
        """
        生成代码差异对比

        Args:
            original: 原始代码
            fixed: 修复后代码
            file_path: 文件路径

        Returns:
            str: 差异对比文本
        """
        original_lines = original.splitlines(keepends=True)
        fixed_lines = fixed.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            fixed_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )

        return "".join(diff)


class FixManager:
    """修复管理器"""

    def __init__(self, backup_dir: Optional[str] = None):
        """
        初始化修复管理器

        Args:
            backup_dir: 备份目录路径
        """
        self.backup_dir = Path(backup_dir) if backup_dir else Path(".fix_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def create_backup(self, file_path: str) -> str:
        """
        创建文件备份

        Args:
            file_path: 原始文件路径

        Returns:
            str: 备份文件路径
        """
        with self._lock:
            source_path = Path(file_path)
            if not source_path.exists():
                raise FileNotFoundError(f"源文件不存在: {file_path}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
            backup_path = self.backup_dir / backup_name

            shutil.copy2(source_path, backup_path)
            logger.info(f"创建备份: {source_path} -> {backup_path}")

            return str(backup_path)

    def apply_fix(self, suggestion: FixSuggestion) -> bool:
        """
        应用修复建议

        Args:
            suggestion: 修复建议

        Returns:
            bool: 修复是否成功
        """
        try:
            file_path = Path(suggestion.file_path)
            if not file_path.exists():
                logger.error(f"文件不存在: {suggestion.file_path}")
                return False

            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.splitlines()

            # 验证行号
            if suggestion.line_number < 1 or suggestion.line_number > len(lines):
                logger.error(f"行号超出范围: {suggestion.line_number}")
                return False

            # 替换代码行
            lines[suggestion.line_number - 1] = suggestion.fixed_code

            # 写回文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            logger.info(
                f"成功应用修复: {suggestion.file_path}:{suggestion.line_number}"
            )
            return True

        except Exception as e:
            logger.error(f"应用修复失败: {e}")
            return False

    def restore_backup(self, backup_path: str, original_path: str) -> bool:
        """
        恢复备份文件

        Args:
            backup_path: 备份文件路径
            original_path: 原始文件路径

        Returns:
            bool: 恢复是否成功
        """
        try:
            shutil.copy2(backup_path, original_path)
            logger.info(f"恢复备份: {backup_path} -> {original_path}")
            return True
        except Exception as e:
            logger.error(f"恢复备份失败: {e}")
            return False


class FixAnalysisCommand:
    """分析修复命令处理器"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """
        初始化分析修复命令处理器

        Args:
            config: 配置管理器
        """
        self.config = config or ConfigManager()
        self.orchestrator = AgentOrchestrator()
        self.fix_manager = FixManager()

    def execute_fix_analysis(
        self,
        target: str,
        confirm_fixes: bool = True,
        verbose: bool = False,
        quiet: bool = False,
    ) -> FixResult:
        """
        执行分析修复

        Args:
            target: 目标文件或目录路径
            confirm_fixes: 是否确认修复操作
            verbose: 详细模式
            quiet: 静默模式

        Returns:
            FixResult: 修复结果
        """
        start_time = time.time()
        target_path = Path(target)

        if not target_path.exists():
            raise FileNotFoundError(f"目标路径不存在: {target}")

        # 验证目标路径
        if not self._validate_target(target_path):
            return FixResult(
                success=False, target=target, suggestions=[], execution_time=0
            )

        if not quiet:
            print(f"🔧 启动分析修复模式")
            print(f"📁 目标: {target}")
            if confirm_fixes:
                print(f"✅ 修复操作需要用户确认")
            else:
                print(f"⚡ 自动应用修复建议")
            print("=" * 60)

        # 创建会话
        session = self.orchestrator.create_session(user_id="fix_analysis_user")

        try:
            # 执行分析获取修复建议
            suggestions = self._analyze_and_generate_suggestions(
                target_path, session, quiet
            )

            if not suggestions:
                if not quiet:
                    print("✅ 未发现需要修复的问题")
                return FixResult(
                    success=True,
                    target=target,
                    suggestions=[],
                    execution_time=time.time() - start_time,
                    total_issues=0,
                )

            # 显示修复建议
            if not quiet:
                self._display_fix_suggestions(suggestions)

            # 应用修复
            applied_fixes = []
            failed_fixes = []
            backup_files = {}

            if confirm_fixes:
                # 交互式确认每个修复
                applied_fixes, failed_fixes, backup_files = (
                    self._apply_fixes_with_confirmation(suggestions, quiet, verbose)
                )
            else:
                # 自动应用所有修复
                applied_fixes, failed_fixes, backup_files = (
                    self._apply_fixes_automatically(suggestions, quiet, verbose)
                )

            # 计算执行时间
            execution_time = time.time() - start_time

            # 显示修复结果
            if not quiet:
                self._display_fix_results(applied_fixes, failed_fixes, execution_time)

            return FixResult(
                success=len(failed_fixes) == 0,
                target=target,
                suggestions=suggestions,
                applied_fixes=applied_fixes,
                failed_fixes=failed_fixes,
                backup_files=backup_files,
                execution_time=execution_time,
                total_issues=len(suggestions),
                fixed_issues=len(applied_fixes),
            )

        finally:
            self.orchestrator.close_session(session.session_id)

    def _validate_target(self, target_path: Path) -> bool:
        """
        验证目标路径

        Args:
            target_path: 目标路径

        Returns:
            bool: 是否为有效目标
        """
        if target_path.is_file():
            return target_path.suffix == ".py"
        elif target_path.is_dir():
            # 检查目录中是否包含Python文件
            return any(target_path.rglob("*.py"))
        return False

    def _analyze_and_generate_suggestions(
        self, target_path: Path, session, quiet: bool
    ) -> List[FixSuggestion]:
        """
        分析并生成修复建议

        Args:
            target_path: 目标路径
            session: 会话对象
            quiet: 静默模式

        Returns:
            List[FixSuggestion]: 修复建议列表
        """
        if not quiet:
            print("🔍 正在分析代码问题...")

        # 模拟分析过程，实际应该调用静态分析工具和LLM
        suggestions = self._generate_demo_suggestions(target_path)

        if not quiet:
            print(f"📋 发现 {len(suggestions)} 个可修复问题")

        return suggestions

    def _generate_demo_suggestions(self, target_path: Path) -> List[FixSuggestion]:
        """
        生成演示修复建议（实际应基于真实分析结果）

        Args:
            target_path: 目标路径

        Returns:
            List[FixSuggestion]: 修复建议列表
        """
        suggestions = []

        if target_path.is_file():
            suggestions.extend(self._analyze_file(target_path))
        else:
            for py_file in target_path.rglob("*.py"):
                suggestions.extend(self._analyze_file(py_file))

        return suggestions

    def _analyze_file(self, file_path: Path) -> List[FixSuggestion]:
        """
        分析单个文件并生成修复建议

        Args:
            file_path: 文件路径

        Returns:
            List[FixSuggestion]: 修复建议列表
        """
        suggestions = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                line_content = line.strip()

                # 检查常见问题
                if "import *" in line_content:
                    suggestions.append(
                        FixSuggestion(
                            file_path=str(file_path),
                            issue_type="style",
                            description="避免使用通配符导入",
                            line_number=i,
                            original_code=line_content,
                            fixed_code=line_content.replace(
                                "import *", "# TODO: 明确导入所需模块"
                            ),
                            severity="medium",
                            confidence=0.9,
                        )
                    )

                # 检查硬编码密码
                if (
                    "password" in line_content.lower()
                    and "=" in line_content
                    and not line_content.startswith("#")
                ):
                    suggestions.append(
                        FixSuggestion(
                            file_path=str(file_path),
                            issue_type="security",
                            description="硬编码密码存在安全风险",
                            line_number=i,
                            original_code=line_content,
                            fixed_code=line_content
                            + "  # TODO: 使用环境变量或配置文件",
                            severity="high",
                            confidence=0.8,
                        )
                    )

                # 检查未使用的导入
                if line_content.startswith("import ") or line_content.startswith(
                    "from "
                ):
                    # 简单演示，实际需要更复杂的分析
                    if "os" in line_content and i > len(lines) // 2:
                        suggestions.append(
                            FixSuggestion(
                                file_path=str(file_path),
                                issue_type="unused",
                                description="未使用的导入",
                                line_number=i,
                                original_code=line_content,
                                fixed_code="# " + line_content,
                                severity="low",
                                confidence=0.6,
                            )
                        )

        except Exception as e:
            logger.error(f"分析文件失败 {file_path}: {e}")

        return suggestions

    def _display_fix_suggestions(self, suggestions: List[FixSuggestion]):
        """
        显示修复建议

        Args:
            suggestions: 修复建议列表
        """
        print(f"\n🔧 修复建议 (共 {len(suggestions)} 个):")
        print("-" * 60)

        for i, suggestion in enumerate(suggestions, 1):
            severity_icon = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🟠",
                "critical": "🔴",
            }.get(suggestion.severity, "⚪")

            print(
                f"\n{i}. {severity_icon} [{suggestion.issue_type.upper()}] {suggestion.description}"
            )
            print(f"   📁 文件: {suggestion.file_path}:{suggestion.line_number}")
            print(
                f"   📊 严重程度: {suggestion.severity} | 置信度: {suggestion.confidence:.1f}"
            )

            # 显示代码差异
            diff = CodeDiffer.generate_diff(
                suggestion.original_code,
                suggestion.fixed_code,
                Path(suggestion.file_path).name,
            )
            if diff.strip():
                print("   📝 代码变更:")
                for line in diff.split("\n"):
                    if line.startswith("-"):
                        print(f"     \033[91m{line}\033[0m")  # 红色
                    elif line.startswith("+"):
                        print(f"     \033[92m{line}\033[0m")  # 绿色
                    elif line.startswith("@@"):
                        print(f"     \033[96m{line}\033[0m")  # 蓝色

        print("-" * 60)

    def _apply_fixes_with_confirmation(
        self, suggestions: List[FixSuggestion], quiet: bool, verbose: bool
    ) -> Tuple[List[FixSuggestion], List[FixSuggestion], Dict[str, str]]:
        """
        通过用户确认应用修复

        Args:
            suggestions: 修复建议列表
            quiet: 静默模式
            verbose: 详细模式

        Returns:
            Tuple[成功修复列表, 失败修复列表, 备份文件映射]
        """
        applied_fixes = []
        failed_fixes = []
        backup_files = {}

        print(f"\n🤔 确认修复操作 (共 {len(suggestions)} 个建议):")
        print("输入 'y' 确认当前修复, 'n' 跳过, 'a' 全部确认, 'q' 退出")

        for i, suggestion in enumerate(suggestions):
            try:
                # 获取用户确认
                if not quiet:
                    print(f"\n[{i+1}/{len(suggestions)}] {suggestion.description}")
                    print(f"文件: {suggestion.file_path}:{suggestion.line_number}")

                while True:
                    if not quiet:
                        response = input("确认修复? [y/n/a/q]: ").strip().lower()
                    else:
                        response = "n"  # 静默模式默认跳过

                    if response == "q":
                        print("👋 用户退出修复操作")
                        return applied_fixes, failed_fixes, backup_files
                    elif response == "a":
                        # 应用剩余所有修复
                        remaining_suggestions = suggestions[i:]
                        for remaining_suggestion in remaining_suggestions:
                            if self._apply_single_fix(
                                remaining_suggestion, backup_files, verbose
                            ):
                                applied_fixes.append(remaining_suggestion)
                            else:
                                failed_fixes.append(remaining_suggestion)
                        return applied_fixes, failed_fixes, backup_files
                    elif response == "y":
                        if self._apply_single_fix(suggestion, backup_files, verbose):
                            applied_fixes.append(suggestion)
                            if not quiet:
                                print("✅ 修复已应用")
                        else:
                            failed_fixes.append(suggestion)
                            if not quiet:
                                print("❌ 修复失败")
                        break
                    elif response == "n":
                        if not quiet:
                            print("⏭️ 跳过修复")
                        break
                    else:
                        print("无效输入，请输入 y/n/a/q")

            except KeyboardInterrupt:
                print("\n👋 用户中断操作")
                break

        return applied_fixes, failed_fixes, backup_files

    def _apply_fixes_automatically(
        self, suggestions: List[FixSuggestion], quiet: bool, verbose: bool
    ) -> Tuple[List[FixSuggestion], List[FixSuggestion], Dict[str, str]]:
        """
        自动应用修复

        Args:
            suggestions: 修复建议列表
            quiet: 静默模式
            verbose: 详细模式

        Returns:
            Tuple[成功修复列表, 失败修复列表, 备份文件映射]
        """
        applied_fixes = []
        failed_fixes = []
        backup_files = {}

        if not quiet:
            print(f"\n🚀 自动应用修复 (共 {len(suggestions)} 个建议):")

        for i, suggestion in enumerate(suggestions):
            if not quiet:
                print(f"[{i+1}/{len(suggestions)}] {suggestion.description}")

            if self._apply_single_fix(suggestion, backup_files, verbose):
                applied_fixes.append(suggestion)
                if not quiet:
                    print("  ✅ 修复已应用")
            else:
                failed_fixes.append(suggestion)
                if not quiet:
                    print("  ❌ 修复失败")

        return applied_fixes, failed_fixes, backup_files

    def _apply_single_fix(
        self, suggestion: FixSuggestion, backup_files: Dict[str, str], verbose: bool
    ) -> bool:
        """
        应用单个修复

        Args:
            suggestion: 修复建议
            backup_files: 备份文件映射
            verbose: 详细模式

        Returns:
            bool: 修复是否成功
        """
        try:
            # 创建备份
            if suggestion.file_path not in backup_files:
                backup_path = self.fix_manager.create_backup(suggestion.file_path)
                backup_files[suggestion.file_path] = backup_path

            # 应用修复
            success = self.fix_manager.apply_fix(suggestion)

            if verbose and success:
                print(f"    📝 已修复: {suggestion.file_path}:{suggestion.line_number}")

            return success

        except Exception as e:
            if verbose:
                print(f"    ❌ 修复失败: {e}")
            return False

    def _display_fix_results(
        self,
        applied_fixes: List[FixSuggestion],
        failed_fixes: List[FixSuggestion],
        execution_time: float,
    ):
        """
        显示修复结果

        Args:
            applied_fixes: 成功应用的修复
            failed_fixes: 失败的修复
            execution_time: 执行时间
        """
        print(f"\n🎯 修复执行完成 (耗时 {execution_time:.2f}秒)")
        print("=" * 60)

        print(f"✅ 成功修复: {len(applied_fixes)} 个")
        print(f"❌ 修复失败: {len(failed_fixes)} 个")

        if applied_fixes:
            print(f"\n✅ 成功修复的问题:")
            for fix in applied_fixes:
                print(f"  • {fix.description} ({fix.file_path}:{fix.line_number})")

        if failed_fixes:
            print(f"\n❌ 修复失败的问题:")
            for fix in failed_fixes:
                print(f"  • {fix.description} ({fix.file_path}:{fix.line_number})")

        print("=" * 60)
