#!/usr/bin/env python3
"""
静态分析命令模块
实现`analyze static`命令的处理逻辑
"""

import sys
import time
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from ..utils.logger import get_logger
from ..utils.config import ConfigManager
from ..agent.orchestrator import AgentOrchestrator
from ..agent.planner import AnalysisMode
from ..agent.user_interaction import ResponseFormatter, OutputFormat

logger = get_logger()


@dataclass
class StaticAnalysisResult:
    """静态分析结果数据类"""
    success: bool
    total_files: int
    analyzed_files: int
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues_by_type: Dict[str, int]
    tool_results: Dict[str, Any]
    execution_time: float
    summary: str


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, total_files: int):
        self.total_files = total_files
        self.processed_files = 0
        self.current_tool = ""
        self.start_time = time.time()
        self._lock = threading.Lock()

    def update(self, processed_files: int = None, current_tool: str = ""):
        """更新进度"""
        with self._lock:
            # 只更新文件数量（如果明确提供了processed_files参数）
            if processed_files is not None and processed_files > 0:
                self.processed_files += processed_files
            # 更新当前工具（如果提供了current_tool参数）
            if current_tool:
                self.current_tool = current_tool

    def get_progress_info(self) -> Dict[str, Any]:
        """获取进度信息"""
        with self._lock:
            elapsed = time.time() - self.start_time
            percentage = (self.processed_files / self.total_files * 100) if self.total_files > 0 else 0

            return {
                "processed_files": self.processed_files,
                "total_files": self.total_files,
                "percentage": percentage,
                "current_tool": self.current_tool,
                "elapsed_time": elapsed,
                "estimated_remaining": (elapsed / self.processed_files * (self.total_files - self.processed_files)) if self.processed_files > 0 else 0
            }


class StaticAnalysisCommand:
    """静态分析命令处理器"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """初始化静态分析命令处理器"""
        self.config = config or ConfigManager()
        # 确保配置已加载
        if not hasattr(self.config, '_config') or self.config._config is None:
            try:
                self.config.load_config()
            except Exception:
                # 如果配置加载失败，使用默认配置
                self.config._config = {
                    'static_analysis': {
                        'tools': {
                            'pylint': {'enabled': True},
                            'bandit': {'enabled': True},
                            'flake8': {'enabled': True},
                            'mypy': {'enabled': True}
                        }
                    }
                }
        self.orchestrator = AgentOrchestrator()
        self.formatter = ResponseFormatter()

    def execute_static_analysis(
        self,
        target: str,
        tools: Optional[List[str]] = None,
        output_format: str = "simple",
        output_file: Optional[str] = None,
        verbose: bool = False,
        quiet: bool = False,
        dry_run: bool = False
    ) -> StaticAnalysisResult:
        """
        执行静态分析

        Args:
            target: 目标文件或目录路径
            tools: 指定的分析工具列表
            output_format: 输出格式
            output_file: 输出文件路径
            verbose: 详细模式
            quiet: 静默模式
            dry_run: 模拟运行

        Returns:
            StaticAnalysisResult: 分析结果
        """
        start_time = time.time()
        target_path = Path(target)

        if not target_path.exists():
            raise FileNotFoundError(f"目标路径不存在: {target}")

        # 1. 获取要分析的文件列表
        if not quiet:
            print(f"🔍 扫描目标路径: {target}")

        files_to_analyze = self._get_files_to_analyze(target_path)
        if not files_to_analyze:
            if not quiet:
                print("⚠️  未找到可分析的Python文件")
            return StaticAnalysisResult(
                success=False,
                total_files=0,
                analyzed_files=0,
                total_issues=0,
                issues_by_severity={},
                issues_by_type={},
                tool_results={},
                execution_time=0,
                summary="未找到可分析的Python文件"
            )

        if not quiet:
            print(f"📁 找到 {len(files_to_analyze)} 个Python文件")

        # 2. 确定要使用的工具
        selected_tools = self._get_selected_tools(tools)
        if not selected_tools:
            if not quiet:
                print("⚠️  没有可用的分析工具")
            return StaticAnalysisResult(
                success=False,
                total_files=len(files_to_analyze),
                analyzed_files=0,
                total_issues=0,
                issues_by_severity={},
                issues_by_type={},
                tool_results={},
                execution_time=0,
                summary="没有可用的分析工具"
            )

        if not quiet:
            print(f"🔧 使用工具: {', '.join(selected_tools)}")

        # 3. 模拟运行
        if dry_run:
            if not quiet:
                print("🏃 模拟运行模式 - 不会执行实际分析")
            return StaticAnalysisResult(
                success=True,
                total_files=len(files_to_analyze),
                analyzed_files=len(files_to_analyze),
                total_issues=0,
                issues_by_severity={},
                issues_by_type={},
                tool_results={tool: "dry_run" for tool in selected_tools},
                execution_time=0.1,
                summary="模拟运行完成"
            )

        # 4. 执行分析
        if not quiet:
            print("🚀 开始静态分析...")

        progress_tracker = ProgressTracker(len(files_to_analyze))

        # 显示进度
        if not quiet and not verbose:
            progress_thread = threading.Thread(
                target=self._show_progress,
                args=(progress_tracker,),
                daemon=True
            )
            progress_thread.start()

        # 执行分析
        analysis_results = self._run_analysis(
            files_to_analyze,
            selected_tools,
            progress_tracker,
            verbose
        )

        execution_time = time.time() - start_time

        # 5. 处理结果
        result = self._process_analysis_results(
            analysis_results,
            selected_tools,
            len(files_to_analyze),
            execution_time
        )

        # 6. 输出结果
        if not quiet:
            self._display_results(result, output_format, verbose)

        # 7. 保存到文件
        if output_file:
            self._save_results(result, output_file, output_format)

        return result

    def _get_files_to_analyze(self, target_path: Path) -> List[str]:
        """获取要分析的文件列表"""
        files = []

        if target_path.is_file():
            if target_path.suffix == '.py':
                files.append(str(target_path))
        elif target_path.is_dir():
            # 递归查找Python文件
            for py_file in target_path.rglob('*.py'):
                # 跳过隐藏文件和测试文件（根据配置）
                if not self._should_skip_file(py_file):
                    files.append(str(py_file))

        return sorted(files)

    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        # 跳过隐藏文件
        if file_path.name.startswith('.'):
            return True

        # 可以根据配置添加更多跳过规则
        skip_patterns = ['__pycache__', '.git', '.pytest_cache', 'venv', 'env']
        return any(pattern in str(file_path) for pattern in skip_patterns)

    def _get_selected_tools(self, requested_tools: Optional[List[str]]) -> List[str]:
        """获取选中的分析工具"""
        try:
            # 检查配置是否已加载
            if not hasattr(self.config, '_config') or self.config._config is None:
                # 使用默认工具配置
                enabled_tools = ['pylint', 'bandit', 'flake8', 'mypy']
            else:
                tools_config = self.config.get_section('static_analysis')

                # 适配实际配置文件格式
                if 'enabled_tools' in tools_config:
                    # 新格式：使用 enabled_tools 列表
                    enabled_tools = tools_config['enabled_tools']
                elif 'tools' in tools_config:
                    # 旧格式：使用 tools 字典
                    available_tools = tools_config['tools']
                    enabled_tools = [
                        name for name, config in available_tools.items()
                        if config.get('enabled', True)
                    ]
                else:
                    # 默认工具列表
                    enabled_tools = ['pylint', 'bandit', 'flake8', 'mypy']

            # 如果用户指定了工具，进行过滤
            if requested_tools:
                selected_tools = []
                for tool in requested_tools:
                    if tool in enabled_tools:
                        selected_tools.append(tool)
                    else:
                        logger.warning(f"工具 '{tool}' 不可用或未启用")
                return selected_tools

            return enabled_tools

        except Exception as e:
            logger.error(f"获取工具配置失败: {e}")
            # 返回默认工具列表
            return ['pylint', 'bandit', 'flake8', 'mypy']

    def _run_analysis(
        self,
        files: List[str],
        tools: List[str],
        progress_tracker: ProgressTracker,
        verbose: bool
    ) -> Dict[str, Any]:
        """运行分析"""
        results = {}

        for tool in tools:
            if verbose:
                print(f"  🔄 运行 {tool} 分析...")

            tool_results = self._run_tool_analysis(tool, files, progress_tracker, verbose)
            results[tool] = tool_results

        return results

    def _run_tool_analysis(
        self,
        tool: str,
        files: List[str],
        progress_tracker: ProgressTracker,
        verbose: bool
    ) -> Dict[str, Any]:
        """运行单个工具的分析"""
        progress_tracker.update(processed_files=0, current_tool=tool)

        # 创建临时会话
        session = self.orchestrator.create_session()

        try:
            # 构建分析命令
            command = f"{tool}分析 {' '.join(files[:5])}"  # 限制文件数量避免命令过长

            if verbose:
                print(f"    📝 分析命令: {command[:100]}...")

            # 执行分析
            result = self.orchestrator.process_user_input(session, command)

            progress_tracker.update(len(files))

            return {
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "data": result.get("data", {}),
                "issues": result.get("issues", [])
            }

        except Exception as e:
            logger.error(f"工具 {tool} 分析失败: {e}")
            return {
                "success": False,
                "message": f"分析失败: {e}",
                "data": {},
                "issues": []
            }
        finally:
            self.orchestrator.close_session(session)

    def _show_progress(self, progress_tracker: ProgressTracker):
        """显示进度信息"""
        import sys

        while progress_tracker.processed_files < progress_tracker.total_files:
            info = progress_tracker.get_progress_info()

            # 构建进度条
            bar_length = 30
            filled_length = int(bar_length * info['percentage'] / 100)
            bar = '█' * filled_length + '░' * (bar_length - filled_length)

            # 显示进度
            sys.stdout.write(f'\r🔄 分析进度: |{bar}| {info["percentage"]:.1f}% '
                           f'({info["processed_files"]}/{info["total_files"]}) '
                           f'工具: {info["current_tool"]} '
                           f'耗时: {info["elapsed_time"]:.1f}s')
            sys.stdout.flush()

            time.sleep(0.5)

        # 进度完成
        sys.stdout.write(f'\r✅ 分析完成! 总共分析了 {progress_tracker.total_files} 个文件\n')
        sys.stdout.flush()

    def _process_analysis_results(
        self,
        analysis_results: Dict[str, Any],
        tools: List[str],
        total_files: int,
        execution_time: float
    ) -> StaticAnalysisResult:
        """处理分析结果"""
        total_issues = 0
        issues_by_severity = {"error": 0, "warning": 0, "info": 0}
        issues_by_type = {}
        analyzed_files = 0

        for tool, result in analysis_results.items():
            if result.get("success", False):
                analyzed_files += 1
                issues = result.get("issues", [])

                for issue in issues:
                    total_issues += 1

                    # 按严重程度分类
                    severity = issue.get("severity", "info").lower()
                    if severity in issues_by_severity:
                        issues_by_severity[severity] += 1

                    # 按类型分类
                    issue_type = issue.get("type", "other")
                    issues_by_type[issue_type] = issues_by_type.get(issue_type, 0) + 1

        # 生成摘要
        summary_parts = []
        if total_issues > 0:
            summary_parts.append(f"发现 {total_issues} 个问题")
            if issues_by_severity["error"] > 0:
                summary_parts.append(f"{issues_by_severity['error']} 个错误")
            if issues_by_severity["warning"] > 0:
                summary_parts.append(f"{issues_by_severity['warning']} 个警告")
        else:
            summary_parts.append("未发现问题")

        summary = "，".join(summary_parts)

        return StaticAnalysisResult(
            success=True,
            total_files=total_files,
            analyzed_files=analyzed_files,
            total_issues=total_issues,
            issues_by_severity=issues_by_severity,
            issues_by_type=issues_by_type,
            tool_results=analysis_results,
            execution_time=execution_time,
            summary=summary
        )

    def _display_results(self, result: StaticAnalysisResult, output_format: str, verbose: bool):
        """显示分析结果"""
        if output_format == "simple":
            self._display_simple_results(result)
        elif output_format == "detailed":
            self._display_detailed_results(result, verbose)
        elif output_format == "json":
            self._display_json_results(result)
        elif output_format == "table":
            self._display_table_results(result)
        elif output_format == "markdown":
            self._display_markdown_results(result)

    def _display_simple_results(self, result: StaticAnalysisResult):
        """显示简洁结果"""
        print(f"\n📊 分析结果摘要:")
        print(f"   分析文件: {result.analyzed_files}/{result.total_files}")
        print(f"   执行时间: {result.execution_time:.2f}秒")
        print(f"   问题总数: {result.total_issues}")

        if result.issues_by_severity:
            print(f"   严重程度: 错误({result.issues_by_severity.get('error', 0)}) "
                  f"警告({result.issues_by_severity.get('warning', 0)}) "
                  f"信息({result.issues_by_severity.get('info', 0)})")

        print(f"   📝 {result.summary}")

    def _display_detailed_results(self, result: StaticAnalysisResult, verbose: bool):
        """显示详细结果"""
        self._display_simple_results(result)

        print(f"\n🔧 工具执行结果:")
        for tool, tool_result in result.tool_results.items():
            status = "✅" if tool_result.get("success", False) else "❌"
            message = tool_result.get("message", "")
            issues_count = len(tool_result.get("issues", []))
            print(f"   {status} {tool}: {issues_count} 个问题 - {message}")

        if result.issues_by_type and verbose:
            print(f"\n📈 问题类型分布:")
            for issue_type, count in result.issues_by_type.items():
                print(f"   {issue_type}: {count}")

    def _display_json_results(self, result: StaticAnalysisResult):
        """显示JSON结果"""
        result_dict = {
            "success": result.success,
            "summary": result.summary,
            "statistics": {
                "total_files": result.total_files,
                "analyzed_files": result.analyzed_files,
                "total_issues": result.total_issues,
                "execution_time": result.execution_time
            },
            "issues_by_severity": result.issues_by_severity,
            "issues_by_type": result.issues_by_type,
            "tool_results": result.tool_results
        }
        print(json.dumps(result_dict, indent=2, ensure_ascii=False))

    def _display_table_results(self, result: StaticAnalysisResult):
        """显示表格结果"""
        print(f"\n📊 静态分析结果表")
        print("=" * 60)
        print(f"{'项目':<15} {'数量':<10}")
        print("-" * 60)
        print(f"{'分析文件':<15} {result.analyzed_files:<10}")
        print(f"{'总文件数':<15} {result.total_files:<10}")
        print(f"{'发现问题':<15} {result.total_issues:<10}")
        print("=" * 60)

        if result.issues_by_severity:
            print(f"\n按严重程度分类:")
            print("-" * 60)
            for severity, count in result.issues_by_severity.items():
                print(f"{severity.capitalize():<15} {count:<10}")

    def _display_markdown_results(self, result: StaticAnalysisResult):
        """显示Markdown结果"""
        print(f"\n# 静态分析报告\n")
        print(f"## 摘要")
        print(f"- **分析文件**: {result.analyzed_files}/{result.total_files}")
        print(f"- **执行时间**: {result.execution_time:.2f}秒")
        print(f"- **发现问题**: {result.total_issues}")
        print(f"- **结果**: {result.summary}\n")

        if result.issues_by_severity:
            print(f"## 严重程度分布")
            for severity, count in result.issues_by_severity.items():
                print(f"- **{severity.capitalize()}**: {count}")

    def _save_results(self, result: StaticAnalysisResult, output_file: str, output_format: str):
        """保存结果到文件"""
        try:
            output_path = Path(output_file)

            # 确保输出目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                if output_format == 'json':
                    result_dict = {
                        "success": result.success,
                        "summary": result.summary,
                        "statistics": {
                            "total_files": result.total_files,
                            "analyzed_files": result.analyzed_files,
                            "total_issues": result.total_issues,
                            "execution_time": result.execution_time
                        },
                        "issues_by_severity": result.issues_by_severity,
                        "issues_by_type": result.issues_by_type,
                        "tool_results": result.tool_results
                    }
                    json.dump(result_dict, f, indent=2, ensure_ascii=False)
                else:
                    # 保存文本格式
                    f.write(f"静态分析报告\n")
                    f.write(f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"分析文件: {result.analyzed_files}/{result.total_files}\n")
                    f.write(f"执行时间: {result.execution_time:.2f}秒\n")
                    f.write(f"问题总数: {result.total_issues}\n")
                    f.write(f"摘要: {result.summary}\n")

                    if result.issues_by_severity:
                        f.write(f"\n严重程度分布:\n")
                        for severity, count in result.issues_by_severity.items():
                            f.write(f"  {severity}: {count}\n")

            print(f"📄 结果已保存到: {output_file}")

        except Exception as e:
            logger.error(f"保存结果失败: {e}")
            print(f"❌ 保存结果失败: {e}")