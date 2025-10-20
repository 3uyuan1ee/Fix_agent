#!/usr/bin/env python3
"""
CLI分析协调器
为CLI命令行接口提供简化的分析协调功能
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..utils.logger import get_logger
from ..utils.progress import ProgressTracker
from .static_coordinator import StaticAnalysisCoordinator


class ConversationContext:
    """对话上下文管理器"""

    def __init__(self, target: str, max_context_length: int = 10):
        """
        初始化对话上下文

        Args:
            target: 分析目标
            max_context_length: 最大上下文长度（轮对话）
        """
        self.target = target
        self.max_context_length = max_context_length
        self.session_start = self._get_current_time()
        self.conversation_history = []
        self.analysis_context = {
            'target': target,
            'analysis_type': 'comprehensive',
            'current_file': None,
            'previous_results': [],
            'preferences': {},
            'user_patterns': {},
            'session_stats': {
                'total_analyses': 0,
                'successful_analyses': 0,
                'failed_analyses': 0,
                'total_time': 0.0
            }
        }

    def add_message(self, user_input: str, ai_response: str, message_type: str = 'general'):
        """添加对话消息"""
        message = {
            'timestamp': self._get_current_time(),
            'type': message_type,
            'user_input': user_input,
            'ai_response': ai_response,
            'session_time': self._get_session_duration()
        }

        self.conversation_history.append(message)
        self._trim_context()

    def add_analysis_result(self, file_path: str, analysis_type: str, result: dict, execution_time: float):
        """添加分析结果"""
        analysis_entry = {
            'timestamp': self._get_current_time(),
            'type': 'file_analysis',
            'file_path': file_path,
            'analysis_type': analysis_type,
            'result': result,
            'execution_time': execution_time,
            'success': result.get('success', False),
            'session_time': self._get_session_duration()
        }

        self.conversation_history.append(analysis_entry)
        self.analysis_context['previous_results'].append(analysis_entry)
        self.analysis_context['current_file'] = file_path

        # 更新统计信息
        self.analysis_context['session_stats']['total_analyses'] += 1
        if result.get('success', False):
            self.analysis_context['session_stats']['successful_analyses'] += 1
        else:
            self.analysis_context['session_stats']['failed_analyses'] += 1
        self.analysis_context['session_stats']['total_time'] += execution_time

        self._trim_context()

    def set_analysis_type(self, analysis_type: str):
        """设置分析类型"""
        self.analysis_context['analysis_type'] = analysis_type
        # 记录用户偏好
        if 'analysis_type' not in self.analysis_context['user_patterns']:
            self.analysis_context['user_patterns']['analysis_type'] = {}
        if analysis_type not in self.analysis_context['user_patterns']['analysis_type']:
            self.analysis_context['user_patterns']['analysis_type'][analysis_type] = 0
        self.analysis_context['user_patterns']['analysis_type'][analysis_type] += 1

    def set_preference(self, key: str, value: any):
        """设置用户偏好"""
        self.analysis_context['preferences'][key] = value

    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        history = self.conversation_history
        if not history:
            return "这是我们的第一次对话"

        recent_analyses = [entry for entry in history[-5:] if entry.get('type') == 'file_analysis']
        if recent_analyses:
            last_file = recent_analyses[-1].get('file_path', 'unknown')
            last_type = recent_analyses[-1].get('analysis_type', 'unknown')
            return f"最近分析了 {Path(last_file).name} (类型: {last_type})"

        recent_messages = history[-3:]
        if recent_messages:
            return f"我们最近讨论了 {len(recent_messages)} 个话题"

        return f"我们已经进行了 {len(history)} 轮对话"

    def get_recent_context(self, num_entries: int = 3) -> list:
        """获取最近的上下文"""
        return self.conversation_history[-num_entries:]

    def get_file_analysis_history(self, file_path: str = None) -> list:
        """获取文件分析历史"""
        analyses = [entry for entry in self.conversation_history if entry.get('type') == 'file_analysis']

        if file_path:
            analyses = [entry for entry in analyses if file_path in entry.get('file_path', '')]

        return analyses

    def get_session_stats(self) -> dict:
        """获取会话统计"""
        stats = self.analysis_context['session_stats'].copy()
        stats.update({
            'session_duration': self._get_session_duration(),
            'total_messages': len(self.conversation_history),
            'files_analyzed': len(set(entry.get('file_path', '') for entry in self.conversation_history if entry.get('type') == 'file_analysis')),
            'most_used_analysis_type': self._get_most_used_analysis_type()
        })
        return stats

    def _trim_context(self):
        """修剪上下文以保持在最大长度内"""
        if len(self.conversation_history) > self.max_context_length:
            # 保留重要的分析结果
            important_entries = []
            regular_entries = []

            for entry in self.conversation_history:
                if entry.get('type') == 'file_analysis' and entry.get('success', False):
                    important_entries.append(entry)
                else:
                    regular_entries.append(entry)

            # 优先保留重要的分析结果
            self.conversation_history = important_entries + regular_entries[-(self.max_context_length - len(important_entries)):]

    def _get_most_used_analysis_type(self) -> str:
        """获取最常用的分析类型"""
        patterns = self.analysis_context['user_patterns'].get('analysis_type', {})
        if patterns:
            return max(patterns.items(), key=lambda x: x[1])[0]
        return 'comprehensive'

    def _get_session_duration(self) -> float:
        """获取会话持续时间（秒）"""
        from datetime import datetime
        start_time = datetime.strptime(self.session_start, "%Y-%m-%d %H:%M:%S")
        current_time = datetime.now()
        return (current_time - start_time).total_seconds()

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'target': self.target,
            'session_start': self.session_start,
            'conversation_history': self.conversation_history,
            'analysis_context': self.analysis_context,
            'max_context_length': self.max_context_length
        }


@dataclass
class CLIStaticCoordinator:
    """CLI静态分析协调器"""

    def __init__(self, tools: Optional[List[str]] = None, format: str = "simple",
                 output_file: Optional[str] = None, dry_run: bool = False,
                 progress: Optional[ProgressTracker] = None):
        """
        初始化CLI静态分析协调器

        Args:
            tools: 指定的工具列表
            format: 输出格式
            output_file: 输出文件路径
            dry_run: 是否为试运行
            progress: 进度跟踪器
        """
        self.tools = tools or ['ast', 'pylint', 'flake8']
        self.format = format
        self.output_file = output_file
        self.dry_run = dry_run
        self.progress = progress or ProgressTracker()
        self.logger = get_logger()

        # 创建静态分析协调器
        self.coordinator = StaticAnalysisCoordinator()
        if tools:
            self.coordinator.set_enabled_tools(tools)

    def analyze(self, target: str) -> Dict[str, Any]:
        """
        执行静态分析

        Args:
            target: 目标路径

        Returns:
            分析结果字典
        """
        try:
            if self.dry_run:
                print(f"🔍 [试运行] 将分析: {target}")
                return {
                    'dry_run': True,
                    'target': target,
                    'tools': self.tools,
                    'format': self.format
                }

            target_path = Path(target)

            if not target_path.exists():
                print(f"❌ 错误: 目标路径不存在: {target}")
                return {'error': f"Target path does not exist: {target}"}

            # 收集文件
            files = self._collect_files(target_path)
            if not files:
                print(f"⚠️  警告: 在 {target} 中未找到Python文件")
                return {
                    'target': target,
                    'files_analyzed': 0,
                    'total_issues': 0,
                    'files': []
                }

            # 开始分析
            self.progress.start(len(files))
            self.progress.update_file_count(0)

            all_results = []
            total_issues = 0

            for i, file_path in enumerate(files):
                self.progress.show_file_progress(file_path, i, len(files))

                try:
                    result = self.coordinator.analyze_file(file_path)
                    all_results.append(result)
                    total_issues += len(result.issues)
                    self.progress.update_issue_count(total_issues)

                    # 显示实时进度
                    if self.progress.verbose:
                        for issue in result.issues[:5]:  # 只显示前5个问题
                            print(f"  📍 {result.file_path}:{issue.line} - {issue.message}")

                except Exception as e:
                    self.logger.error(f"Failed to analyze {file_path}: {e}")
                    if self.progress.verbose:
                        print(f"  ❌ 分析失败: {e}")

            self.progress.finish()
            self.progress.update_file_count(len(files))

            # 生成报告
            report = self._generate_report(all_results, target)

            # 保存结果
            if self.output_file:
                self._save_report(report, self.output_file)

            return report

        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            print(f"❌ 分析失败: {e}")
            return {'error': str(e)}

    def _collect_files(self, target_path: Path) -> List[str]:
        """收集Python文件"""
        files = []

        if target_path.is_file():
            if target_path.suffix == '.py':
                files.append(str(target_path))
        elif target_path.is_dir():
            # 递归收集Python文件
            for py_file in target_path.rglob("*.py"):
                files.append(str(py_file))

        # 排序文件
        files.sort()
        return files

    def _generate_report(self, results: List[Any], target: str) -> Dict[str, Any]:
        """生成分析报告"""
        total_issues = sum(len(result.issues) for result in results)

        report = {
            'target': target,
            'files_analyzed': len(results),
            'total_issues': total_issues,
            'format': self.format,
            'tools_used': self.tools,
            'files': [],
            'summary': {
                'total_files': len(results),
                'total_issues': total_issues,
                'severity_distribution': {},
                'tool_distribution': {}
            },
            'execution_time': sum(getattr(result, 'execution_time', 0) for result in results)
        }

        # 统计严重程度和工具分布
        for result in results:
            for issue in result.issues:
                severity = issue.severity.value
                tool = issue.tool_name

                if severity not in report['summary']['severity_distribution']:
                    report['summary']['severity_distribution'][severity] = 0
                if tool not in report['summary']['tool_distribution']:
                    report['summary']['tool_distribution'][tool] = 0

                report['summary']['severity_distribution'][severity] += 1
                report['summary']['tool_distribution'][tool] += 1

        # 添加文件详情
        for result in results:
            file_info = {
                'file_path': result.file_path,
                'issues_count': len(result.issues),
                'execution_time': result.execution_time,
                'summary': result.summary
            }

            # 根据输出格式添加详细信息
            if self.format in ['detailed', 'json']:
                file_info['issues'] = [
                    {
                        'tool': issue.tool_name,
                        'line': issue.line,
                        'column': issue.column,
                        'severity': issue.severity.value,
                        'message': issue.message,
                        'type': issue.issue_type,
                        'code': issue.code
                    }
                    for issue in result.issues
                ]

            report['files'].append(file_info)

        return report

    def _save_report(self, report: Dict[str, Any], output_file: str):
        """保存报告到文件"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_file.endswith('.json'):
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
            elif output_file.endswith('.md'):
                self._save_markdown_report(report, output_path)
            else:
                # 简单文本格式
                with open(output_path, 'w', encoding='utf-8') as f:
                    self._save_text_report(report, f)

        except Exception as e:
            self.logger.error(f"Failed to save report: {e}")
            print(f"❌ 保存报告失败: {e}")


    def _save_text_report(self, report: Dict[str, Any], file):
        """保存文本格式报告"""
        file.write(f"静态分析报告\n")
        file.write("=" * 50 + "\n")
        file.write(f"目标: {report['target']}\n")
        file.write(f"分析文件数: {report['files_analyzed']}\n")
        file.write(f"发现问题数: {report['total_issues']}\n")
        file.write(f"执行时间: {report['execution_time']:.2f}秒\n")
        file.write(f"使用工具: {', '.join(report['tools_used'])}\n\n")

        if report['files']:
            file.write("文件详情:\n")
            file.write("-" * 30 + "\n")
            for file_info in report['files']:
                file.write(f"文件: {file_info['file_path']}\n")
                file.write(f"问题数: {file_info['issues_count']}\n")
                file.write(f"执行时间: {file_info['execution_time']:.2f}秒\n")
                file.write("-" * 30 + "\n")

    def _save_markdown_report(self, report: Dict[str, Any], file):
        """保存Markdown格式报告"""
        file.write("# 静态分析报告\n\n")
        file.write(f"**目标路径**: `{report['target']}`\n")
        file.write(f"**分析文件数**: {report['files_analyzed']}\n")
        file.write(f"**发现问题数**: {report['total_issues']}\n")
        file.write(f"**执行时间**: {report['execution_time']:.2f}秒\n")
        file.write(f"**使用工具**: {', '.join(report['tools_used'])}\n\n")

        # 严重程度分布
        if report['summary']['severity_distribution']:
            file.write("## 问题严重程度分布\n\n")
            file.write("| 严重程度 | 数量 |\n")
            file.write("|----------|------|\n")
            for severity, count in report['summary']['severity_distribution'].items():
                file.write(f"| {severity} | {count} |\n")
            file.write("\n")

        # 工具分布
        if report['summary']['tool_distribution']:
            file.write("## 工具发现问题分布\n\n")
            file.write("| 工具 | 发现问题数 |\n")
            file.write("|------|------------|\n")
            for tool, count in report['summary']['tool_distribution'].items():
                file.write(f"| {tool} | {count} |\n")
            file.write("\n")

        # 文件详情
        if report['files']:
            file.write("## 文件分析详情\n\n")
            for file_info in report['files']:
                file.write(f"### {file_info['file_path']}\n\n")
                file.write(f"- **问题数**: {file_info['issues_count']}\n")
                file.write(f"- **执行时间**: {file_info['execution_time']:.2f}秒\n")

                if 'issues' in file_info and file_info['issues']:
                    file.write("- **问题列表**:\n")
                    for issue in file_info['issues'][:10]:  # 只显示前10个问题
                        file.write(f"  - **{issue['tool']}**: [{issue['severity']}] {issue['message']}\n")
                        file.write(f"    - 位置: 第{issue['line']}行\n")
                    if len(file_info['issues']) > 10:
                        file.write(f"  - ... 还有 {len(file_info['issues']) - 10} 个问题\n")

                file.write("\n")


class CLIInteractiveCoordinator:
    """CLI交互式分析协调器"""

    def __init__(self, mode: str = 'deep', output_file: Optional[str] = None,
                 progress: Optional[ProgressTracker] = None, max_context_length: int = 15):
        """
        初始化CLI交互式协调器

        Args:
            mode: 分析模式 (deep/fix)
            output_file: 输出文件路径
            progress: 进度跟踪器
            max_context_length: 最大上下文长度
        """
        self.mode = mode
        self.output_file = output_file
        self.progress = progress or ProgressTracker(verbose=True)
        self.logger = get_logger()
        self.max_context_length = max_context_length
        self.conversation_context = None

    def run_interactive(self, target: str) -> Dict[str, Any]:
        """运行交互式分析"""
        if self.mode == 'deep':
            return self._run_deep_analysis(target)
        elif self.mode == 'fix':
            return self._run_fix_analysis(target)
        else:
            raise ValueError(f"Unsupported interactive mode: {self.mode}")

    def _run_deep_analysis(self, target: str) -> Dict[str, Any]:
        """运行深度分析"""
        from .deep_analyzer import DeepAnalyzer, DeepAnalysisRequest
        import asyncio
        import time
        from threading import Thread
        import sys

        # 增强的启动界面
        self._show_enhanced_startup_banner(target)

        try:
            # 显示初始化进度
            self._show_initialization_progress()

            # 初始化对话上下文管理器
            self.conversation_context = ConversationContext(target, self.max_context_length)

            analyzer = DeepAnalyzer()

            # 显示会话信息
            self._show_enhanced_session_info(self.conversation_context, analyzer)
            print()

            # 交互式对话循环
            while True:
                try:
                    user_input = input("🤖 AI分析助手> ").strip()

                    if not user_input:
                        continue

                    # 处理退出命令
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("👋 退出深度分析模式")
                        break

                    # 处理帮助命令
                    elif user_input.lower() == 'help':
                        self._show_deep_analysis_help()
                        continue

                    # 处理类型设置命令
                    elif user_input.lower().startswith('type '):
                        new_type = user_input[5:].strip()
                        try:
                            supported_types = analyzer.get_supported_analysis_types()
                        except:
                            supported_types = ['comprehensive', 'security', 'performance', 'architecture', 'code_review', 'refactoring']

                        if new_type in supported_types:
                            self.conversation_context.set_analysis_type(new_type)
                            print(f"✅ 分析类型已设置为: {new_type}")
                            print(f"💾 已记录您的偏好设置")
                        else:
                            print(f"❌ 不支持的分析类型: {new_type}")
                            print(f"支持的类型: {', '.join(supported_types)}")
                        continue

                    # 处理分析命令
                    elif user_input.lower().startswith('analyze '):
                        file_path = user_input[8:].strip()
                        result = self._analyze_file_interactive_with_context(analyzer, file_path)
                        continue

                    # 处理总结命令
                    elif user_input.lower() == 'summary':
                        self._show_analysis_summary(analysis_context)
                        continue

                    # 处理导出命令
                    elif user_input.lower().startswith('export '):
                        export_file = user_input[7:].strip()
                        self._export_conversation_with_context(export_file)
                        continue

                    # 处理普通对话输入
                    else:
                        print(f"💭 正在处理您的问题: {user_input}")
                        print("🔍 AI正在思考...")

                        # 使用上下文感知的对话处理
                        response = self._generate_contextual_response(user_input)
                        print(f"🤖 AI: {response}")

                        # 记录对话历史到上下文管理器
                        self.conversation_context.add_message(user_input, response, 'general')

                except KeyboardInterrupt:
                    print("\n👋 使用Ctrl+C退出深度分析模式")
                    break
                except EOFError:
                    print("\n👋 到达输入末尾，退出深度分析模式")
                    break

            # 生成最终结果
            result = {
                'mode': 'deep',
                'target': target,
                'status': 'completed',
                'conversation_history': conversation_history,
                'analysis_context': analysis_context,
                'files_analyzed': len(analysis_context['previous_results']),
                'total_execution_time': sum(r.get('execution_time', 0) for r in analysis_context['previous_results'])
            }

            # 保存结果到文件
            if self.output_file:
                self._save_deep_analysis_result(result, self.output_file)

            print("✅ 深度分析完成")
            return result

        except Exception as e:
            self.logger.error(f"Deep analysis failed: {e}")
            print(f"❌ 深度分析失败: {e}")
            return {'error': str(e)}

    def _run_fix_analysis(self, target: str) -> Dict[str, Any]:
        """运行修复分析"""
        from .fix_coordinator import FixCoordinator, FixAnalysisRequest
        from .static_coordinator import StaticAnalysisCoordinator
        import asyncio

        print(f"🔧 开始修复分析: {target}")
        print("=" * 60)
        print("💡 提示: 输入 'quit' 或 'exit' 退出修复模式")
        print("💡 提示: 输入 'help' 查看可用命令")
        print("💡 提示: 输入 'scan' 扫描文件问题")
        print("💡 提示: 输入 'fix <file_path>' 修复指定文件")
        print("💡 提示: 输入 'batch fix' 批量修复")
        print()

        try:
            # 初始化协调器
            static_coordinator = StaticAnalysisCoordinator()
            fix_coordinator = FixCoordinator()

            # 修复会话状态
            fix_session = {
                'target': target,
                'scanned_files': [],
                'identified_issues': {},
                'fix_history': [],
                'current_file': None,
                'auto_confirm': False
            }

            print(f"📁 目标路径: {target}")
            print(f"🔧 修复模式: 手动确认 (可使用 'auto confirm' 切换)")
            print()

            # 交互式修复循环
            while True:
                try:
                    user_input = input("🔧 修复助手> ").strip()

                    if not user_input:
                        continue

                    # 处理退出命令
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("👋 退出修复模式")
                        break

                    # 处理帮助命令
                    elif user_input.lower() == 'help':
                        self._show_fix_analysis_help()
                        continue

                    # 处理扫描命令
                    elif user_input.lower() == 'scan':
                        self._scan_files_for_issues(static_coordinator, target, fix_session)
                        continue

                    # 处理自动确认切换
                    elif user_input.lower() == 'auto confirm':
                        fix_session['auto_confirm'] = not fix_session['auto_confirm']
                        status = "启用" if fix_session['auto_confirm'] else "禁用"
                        print(f"✅ 自动确认已{status}")
                        continue

                    # 处理修复命令
                    elif user_input.lower().startswith('fix '):
                        file_path = user_input[4:].strip()
                        result = self._fix_file_interactive(fix_coordinator, file_path, fix_session)
                        if result:
                            fix_session['fix_history'].append(result)
                        continue

                    # 处理批量修复命令
                    elif user_input.lower() == 'batch fix':
                        result = self._batch_fix_interactive(fix_coordinator, fix_session)
                        if result:
                            fix_session['fix_history'].extend(result.get('process_results', []))
                        continue

                    # 处理状态命令
                    elif user_input.lower() == 'status':
                        self._show_fix_status(fix_session)
                        continue

                    # 处理历史命令
                    elif user_input.lower() == 'history':
                        self._show_fix_history(fix_session)
                        continue

                    # 处理导出命令
                    elif user_input.lower().startswith('export '):
                        export_file = user_input[7:].strip()
                        self._export_fix_session(fix_session, export_file)
                        continue

                    # 处理普通对话输入
                    else:
                        print(f"💭 正在处理您的问题: {user_input}")
                        response = self._generate_fix_response(user_input, fix_session)
                        print(f"🤖 修复助手: {response}")

                except KeyboardInterrupt:
                    print("\n👋 使用Ctrl+C退出修复模式")
                    break
                except EOFError:
                    print("\n👋 到达输入末尾，退出修复模式")
                    break

            # 生成最终结果
            result = {
                'mode': 'fix',
                'target': target,
                'status': 'completed',
                'fix_session': fix_session,
                'files_scanned': len(fix_session['scanned_files']),
                'total_issues_found': sum(len(issues) for issues in fix_session['identified_issues'].values()),
                'fixes_attempted': len(fix_session['fix_history']),
                'successful_fixes': len([f for f in fix_session['fix_history'] if f.get('success', False)])
            }

            # 保存结果到文件
            if self.output_file:
                self._save_fix_analysis_result(result, self.output_file)

            print("✅ 修复分析完成")
            return result

        except Exception as e:
            self.logger.error(f"Fix analysis failed: {e}")
            print(f"❌ 修复分析失败: {e}")
            return {'error': str(e)}

    def _show_deep_analysis_help(self):
        """显示深度分析帮助信息"""
        print("\n📖 深度分析帮助")
        print("-" * 40)
        print("可用命令:")
        print("  help                    - 显示此帮助信息")
        print("  analyze <file_path>     - 分析指定文件")
        print("  type <analysis_type>    - 设置分析类型")
        print("  summary                 - 显示分析总结")
        print("  export <filename>       - 导出对话历史")
        print("  quit/exit/q             - 退出分析")
        print("\n分析类型:")
        print("  comprehensive           - 综合分析")
        print("  security                - 安全分析")
        print("  performance             - 性能分析")
        print("  architecture            - 架构分析")
        print("  code_review             - 代码审查")
        print("  refactoring             - 重构建议")
        print("\n示例:")
        print("  analyze src/main.py")
        print("  type security")
        print("  export conversation.json")
        print()

    def _analyze_file_interactive_with_context(self, analyzer, file_path: str) -> dict:
        """使用上下文管理器的交互式文件分析"""
        from pathlib import Path
        import asyncio
        import time

        try:
            # 检查文件是否存在
            full_path = Path(self.conversation_context.target) / file_path
            if not full_path.exists():
                full_path = Path(file_path)  # 尝试绝对路径

            if not full_path.exists():
                print(f"❌ 文件不存在: {file_path}")
                print("💡 请检查文件路径是否正确")

                # 记录失败尝试到上下文
                self.conversation_context.add_message(
                    f"analyze {file_path}",
                    f"分析失败: 文件不存在",
                    'file_analysis'
                )
                return None

            # 显示文件信息
            file_name = full_path.name
            file_size = self._format_file_size(full_path.stat().st_size)

            print(f"\n🔍 准备分析文件: {file_name}")
            print(f"📄 文件大小: {file_size}")
            print(f"📊 分析类型: {self.conversation_context.analysis_context['analysis_type']}")
            print(f"🕐 开始时间: {self._get_current_time()}")

            # 显示上下文信息
            context_summary = self.conversation_context.get_context_summary()
            print(f"💭 上下文: {context_summary}")
            print("-" * 50)

            # 显示分析进度
            self._show_analyzing_animation("AI正在深度分析代码结构")

            start_time = time.time()

            # 创建分析请求（包含上下文）
            request = DeepAnalysisRequest(
                file_path=str(full_path),
                analysis_type=self.conversation_context.analysis_context['analysis_type'],
                context=self.conversation_context.analysis_context
            )

            # 执行异步分析
            result = asyncio.run(analyzer.analyze_file(request))

            execution_time = time.time() - start_time

            # 显示分析结果横幅
            self._show_analysis_result_banner(result.success, file_name)

            if result.success:
                print(f"\n🎉 分析成功完成！")
                print(f"⏱️ 执行时间: {execution_time:.2f}秒")

                if hasattr(result, 'model_used') and result.model_used:
                    print(f"🤖 使用模型: {result.model_used}")

                print(f"📊 分析类型: {self.conversation_context.analysis_context['analysis_type']}")
                print("-" * 50)

                # 显示分析结果摘要
                if result.structured_analysis and result.structured_analysis.get('structured'):
                    self._show_enhanced_structured_result(result.structured_analysis)
                else:
                    # 显示文本结果的摘要
                    self._show_text_result_preview(result.content)

                # 添加到上下文管理器
                self.conversation_context.add_analysis_result(
                    str(full_path),
                    self.conversation_context.analysis_context['analysis_type'],
                    result.to_dict(),
                    execution_time
                )

                print(f"\n💡 提示: 使用 'summary' 查看会话总结")
                print(f"💡 提示: 使用 'export <filename>' 导出对话历史")

                return result.to_dict()
            else:
                print(f"\n❌ 分析失败")
                error_msg = getattr(result, 'error', '未知错误')
                print(f"🔴 错误信息: {error_msg}")
                print(f"⏱️ 耗时: {execution_time:.2f}秒")

                # 记录失败的分析到上下文
                self.conversation_context.add_analysis_result(
                    str(full_path),
                    self.conversation_context.analysis_context['analysis_type'],
                    {'success': False, 'error': error_msg},
                    execution_time
                )

                print(f"\n💡 建议:")
                print(f"  • 检查文件是否为有效的Python代码")
                print(f"  • 确认网络连接正常")
                print(f"  • 尝试更换分析类型")

                return None

        except Exception as e:
            print(f"\n❌ 分析过程中出现异常")
            print(f"🔴 异常信息: {e}")
            self.logger.error(f"Interactive analysis failed: {e}")

            # 记录异常到上下文
            self.conversation_context.add_message(
                f"analyze {file_path}",
                f"分析异常: {e}",
                'file_analysis'
            )

            print(f"\n💡 故障排除:")
            print(f"  • 检查文件路径是否正确")
            print(f"  • 确认文件权限可读")
            print(f"  • 检查系统资源是否充足")

            return None

    def _analyze_file_interactive(self, analyzer, file_path: str, context: dict, history: list) -> dict:
        """交互式文件分析"""
        from pathlib import Path
        import asyncio
        import time

        try:
            # 检查文件是否存在
            full_path = Path(context['target']) / file_path
            if not full_path.exists():
                full_path = Path(file_path)  # 尝试绝对路径

            if not full_path.exists():
                print(f"❌ 文件不存在: {file_path}")
                print("💡 请检查文件路径是否正确")
                return None

            # 显示文件信息
            file_name = full_path.name
            file_size = self._format_file_size(full_path.stat().st_size)

            print(f"\n🔍 准备分析文件: {file_name}")
            print(f"📄 文件大小: {file_size}")
            print(f"📊 分析类型: {context['analysis_type']}")
            print(f"🕐 开始时间: {self._get_current_time()}")
            print("-" * 50)

            # 显示分析进度
            self._show_analyzing_animation("AI正在深度分析代码结构")

            start_time = time.time()

            # 创建分析请求
            request = DeepAnalysisRequest(
                file_path=str(full_path),
                analysis_type=context['analysis_type'],
                context=context
            )

            # 执行异步分析
            result = asyncio.run(analyzer.analyze_file(request))

            execution_time = time.time() - start_time

            # 显示分析结果横幅
            self._show_analysis_result_banner(result.success, file_name)

            if result.success:
                print(f"\n🎉 分析成功完成！")
                print(f"⏱️ 执行时间: {execution_time:.2f}秒")

                if hasattr(result, 'model_used') and result.model_used:
                    print(f"🤖 使用模型: {result.model_used}")

                print(f"📊 分析类型: {context['analysis_type']}")
                print("-" * 50)

                # 显示分析结果摘要
                if result.structured_analysis and result.structured_analysis.get('structured'):
                    self._show_enhanced_structured_result(result.structured_analysis)
                else:
                    # 显示文本结果的摘要
                    self._show_text_result_preview(result.content)

                # 更新上下文
                context['current_file'] = str(full_path)
                context['previous_results'].append({
                    'file_path': str(full_path),
                    'analysis_type': context['analysis_type'],
                    'execution_time': execution_time,
                    'success': True,
                    'timestamp': self._get_current_time()
                })

                # 记录到对话历史
                history.append({
                    'timestamp': self._get_current_time(),
                    'type': 'file_analysis',
                    'file_path': str(full_path),
                    'analysis_type': context['analysis_type'],
                    'result': result.to_dict(),
                    'execution_time': execution_time
                })

                print(f"\n💡 提示: 使用 'summary' 查看会话总结")
                print(f"💡 提示: 使用 'export <filename>' 导出对话历史")

                return result.to_dict()
            else:
                print(f"\n❌ 分析失败")
                error_msg = getattr(result, 'error', '未知错误')
                print(f"🔴 错误信息: {error_msg}")
                print(f"⏱️ 耗时: {execution_time:.2f}秒")

                # 记录失败的分析
                history.append({
                    'timestamp': self._get_current_time(),
                    'type': 'file_analysis',
                    'file_path': str(full_path),
                    'analysis_type': context['analysis_type'],
                    'success': False,
                    'error': error_msg,
                    'execution_time': execution_time
                })

                print(f"\n💡 建议:")
                print(f"  • 检查文件是否为有效的Python代码")
                print(f"  • 确认网络连接正常")
                print(f"  • 尝试更换分析类型")

                return None

        except Exception as e:
            print(f"\n❌ 分析过程中出现异常")
            print(f"🔴 异常信息: {e}")
            self.logger.error(f"Interactive analysis failed: {e}")

            print(f"\n💡 故障排除:")
            print(f"  • 检查文件路径是否正确")
            print(f"  • 确认文件权限可读")
            print(f"  • 检查系统资源是否充足")

            return None

    def _show_enhanced_structured_result(self, structured_result: dict):
        """显示增强的结构化分析结果"""
        print("\n📊 结构化分析结果:")
        print("🎯" * 35)
        print()

        # 显示摘要
        if 'summary' in structured_result:
            print(f"📝 分析摘要:")
            print(f"   {structured_result['summary']}")
            print()

        # 显示代码质量评分
        if 'quality_score' in structured_result:
            score = structured_result['quality_score']
            emoji = self._get_score_emoji(score)
            print(f"📈 代码质量评分: {emoji} {score}/10")
            print(f"   {self._get_score_description(score)}")
            print()

        # 显示复杂度分析
        if 'complexity' in structured_result:
            complexity = structured_result['complexity']
            print(f"🔀 复杂度分析:")
            print(f"   圈复杂度: {complexity.get('cyclomatic', 'N/A')}")
            print(f"   认知复杂度: {complexity.get('cognitive', 'N/A')}")
            print(f"   复杂度等级: {self._get_complexity_level(complexity.get('cyclomatic', 0))}")
            print()

        # 显示问题分析
        if 'issues' in structured_result and structured_result['issues']:
            issues = structured_result['issues']
            print(f"🔍 发现问题 ({len(issues)}个):")
            print("-" * 40)

            # 按严重程度分组
            severity_groups = {}
            for issue in issues:
                severity = issue.get('severity', 'info')
                if severity not in severity_groups:
                    severity_groups[severity] = []
                severity_groups[severity].append(issue)

            for severity in ['error', 'warning', 'info']:
                if severity in severity_groups:
                    emoji = {'error': '🔴', 'warning': '🟡', 'info': '🔵'}[severity]
                    print(f"\n{emoji} {severity.upper()}级别问题 ({len(severity_groups[severity])}个):")

                    for i, issue in enumerate(severity_groups[severity][:5], 1):
                        message = issue.get('message', 'No message')
                        line = issue.get('line', 'N/A')
                        print(f"  {i}. 第{line}行: {message}")

                        if issue.get('suggestion'):
                            print(f"     💡 建议: {issue['suggestion']}")

                    if len(severity_groups[severity]) > 5:
                        print(f"     ... 还有 {len(severity_groups[severity]) - 5} 个{severity}级别问题")

        # 显示改进建议
        if 'recommendations' in structured_result and structured_result['recommendations']:
            recommendations = structured_result['recommendations']
            print(f"\n💡 改进建议 ({len(recommendations)}条):")
            print("-" * 40)

            for i, rec in enumerate(recommendations[:5], 1):
                priority = rec.get('priority', 'medium')
                priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
                print(f"  {i}. {priority_emoji} {rec.get('text', rec)}")

                if rec.get('effort'):
                    effort = rec.get('effort')
                    print(f"     实施难度: {effort}")

            if len(recommendations) > 5:
                print(f"     ... 还有 {len(recommendations) - 5} 条建议")

        print()

    def _show_text_result_preview(self, content: str):
        """显示文本结果预览"""
        print(f"\n📋 AI分析结果:")
        print("-" * 50)

        if not content:
            print("⚠️ 分析结果为空")
            return

        # 显示前500字符的预览
        preview_length = 500
        if len(content) <= preview_length:
            print(content)
        else:
            preview = content[:preview_length]
            print(preview)
            print(f"\n... (还有 {len(content) - preview_length} 字符，详见完整报告)")

        print("-" * 50)

    def _get_score_emoji(self, score: float) -> str:
        """根据评分获取emoji"""
        if score >= 8.5:
            return "🟢"
        elif score >= 7.0:
            return "🟡"
        elif score >= 5.0:
            return "🟠"
        else:
            return "🔴"

    def _get_score_description(self, score: float) -> str:
        """获取评分描述"""
        if score >= 9.0:
            return "优秀 - 代码质量非常高"
        elif score >= 8.0:
            return "良好 - 代码质量较高"
        elif score >= 7.0:
            return "中等 - 代码质量一般"
        elif score >= 6.0:
            return "较差 - 需要一些改进"
        else:
            return "很差 - 需要重大改进"

    def _get_complexity_level(self, complexity: int) -> str:
        """获取复杂度等级"""
        if complexity <= 5:
            return "简单"
        elif complexity <= 10:
            return "中等"
        elif complexity <= 15:
            return "复杂"
        else:
            return "非常复杂"

    def _show_structured_result(self, structured_result: dict):
        """显示结构化分析结果（保留原方法兼容性）"""
        self._show_enhanced_structured_result(structured_result)

    def _show_analysis_summary(self, context: dict):
        """显示分析总结"""
        print("\n📊 分析总结")
        print("=" * 40)
        print(f"📁 目标路径: {context['target']}")
        print(f"🔍 当前分析类型: {context['analysis_type']}")
        print(f"📄 已分析文件: {len(context['previous_results'])}")

        if context['previous_results']:
            total_time = sum(r.get('execution_time', 0) for r in context['previous_results'])
            successful_files = len([r for r in context['previous_results'] if r.get('success', False)])
            print(f"✅ 成功分析: {successful_files}/{len(context['previous_results'])} 文件")
            print(f"⏱️ 总耗时: {total_time:.2f}秒")

            # 显示文件列表
            print("\n📋 已分析文件列表:")
            for i, result in enumerate(context['previous_results'], 1):
                file_path = result.get('file_path', 'Unknown')
                success = result.get('success', False)
                status = "✅" if success else "❌"
                print(f"  {i}. {status} {Path(file_path).name}")

        print()

    def _export_conversation(self, history: list, export_file: str):
        """导出对话历史"""
        try:
            export_path = Path(export_file)
            if not export_path.suffix:
                export_path = export_path.with_suffix('.json')

            export_data = {
                'export_time': self._get_current_time(),
                'total_entries': len(history),
                'conversation_history': history
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 对话历史已导出到: {export_path}")

        except Exception as e:
            print(f"❌ 导出失败: {e}")

    def _generate_contextual_response(self, user_input: str) -> str:
        """生成上下文感知的对话响应"""
        user_lower = user_input.lower()

        # 获取上下文信息
        context_summary = self.conversation_context.get_context_summary()
        recent_context = self.conversation_context.get_recent_context(3)
        session_stats = self.conversation_context.get_session_stats()

        # 检查是否在询问分析相关的问题
        if any(keyword in user_lower for keyword in ['如何分析', '怎么分析', '分析什么', '如何使用']):
            current_type = self.conversation_context.analysis_context['analysis_type']
            return f"您可以使用 'analyze <文件路径>' 命令来分析指定文件。当前分析类型是 {current_type}，可以使用 'type <类型>' 命令更改。{context_summary}"

        # 检查是否在询问进度相关的问题
        elif any(keyword in user_lower for keyword in ['进度', '如何了', '状态', '统计']):
            if session_stats['total_analyses'] > 0:
                success_rate = (session_stats['successful_analyses'] / session_stats['total_analyses']) * 100
                return f"会话统计: 已分析 {session_stats['files_analyzed']} 个文件，成功率 {success_rate:.1f}%，总耗时 {session_stats['total_time']:.1f}秒。{context_summary}"
            else:
                return f"还没有开始分析。使用 'analyze <文件路径>' 命令开始分析文件。"

        # 检查是否在询问文件相关的问题
        elif any(keyword in user_lower for keyword in ['文件', '代码', 'project', '刚才']):
            if session_stats['total_analyses'] > 0:
                most_used_type = session_stats['most_used_analysis_type']
                return f"我们已经分析了 {session_stats['files_analyzed']} 个文件，最常用的分析类型是 {most_used_type}。{context_summary}"
            else:
                return "还没有分析任何文件。使用 'analyze <文件路径>' 命令开始分析。"

        # 检查是否在询问类型相关的问题
        elif any(keyword in user_lower for keyword in ['类型', 'type', '分析类型', '哪种分析']):
            current_type = self.conversation_context.analysis_context['analysis_type']
            most_used_type = session_stats['most_used_analysis_type']
            return f"当前分析类型是 {current_type}，您最常用的类型是 {most_used_type}。支持的类型包括: comprehensive, security, performance, architecture, code_review, refactoring。"

        # 检查是否在询问历史相关的问题
        elif any(keyword in user_lower for keyword in ['历史', '记录', '之前', '刚才说什么']):
            if recent_context:
                last_entry = recent_context[-1]
                if last_entry.get('type') == 'file_analysis':
                    file_name = Path(last_entry.get('file_path', 'unknown')).name
                    return f"最近我们分析了 {file_name}。使用 'summary' 查看完整会话总结。"
                else:
                    return f"我们刚才讨论了: {last_entry.get('user_input', '某个话题')}"
            else:
                return "这是我们对话的开始。使用 'analyze <文件路径>' 开始分析文件。"

        # 检查是否在询问建议相关的问题
        elif any(keyword in user_lower for keyword in ['建议', '推荐', '应该', '下一步']):
            if session_stats['total_analyses'] > 0:
                return f"基于您的分析历史，建议您: 1) 继续分析其他重要文件 2) 尝试不同的分析类型 3) 使用 'summary' 查看会话总结 4) 使用 'export' 保存对话历史。{context_summary}"
            else:
                return "建议您先分析一些关键文件，比如主程序文件或核心模块。使用 'analyze <文件路径>' 开始。"

        # 检查感谢或结束相关的话题
        elif any(keyword in user_lower for keyword in ['谢谢', '感谢', '好的', '可以', '明白了']):
            return "不客气！如果您需要更多帮助，随时告诉我。我可以帮您分析代码、解答问题或提供建议。"

        # 默认响应（包含上下文信息）
        else:
            return f"我是AI代码分析助手，可以帮助您进行深度代码分析。{context_summary} 输入 'help' 查看可用命令，或直接使用 'analyze <文件路径>' 开始分析文件。"

    def _export_conversation_with_context(self, export_file: str):
        """使用上下文管理器导出对话历史"""
        try:
            export_path = Path(export_file)

            # 根据文件扩展名确定导出格式
            if not export_path.suffix:
                # 默认导出为JSON
                export_path = export_path.with_suffix('.json')
                format_type = 'json'
            else:
                format_type = export_path.suffix.lower().lstrip('.')

            # 支持的导出格式
            if format_type not in ['json', 'md', 'markdown', 'txt', 'html']:
                print(f"❌ 不支持的导出格式: {format_type}")
                print("💡 支持的格式: json, md/markdown, txt, html")
                return

            # 确保目录存在
            export_path.parent.mkdir(parents=True, exist_ok=True)

            # 根据格式调用相应的导出方法
            if format_type == 'json':
                self._export_as_json(export_path)
            elif format_type in ['md', 'markdown']:
                self._export_as_markdown(export_path)
            elif format_type == 'txt':
                self._export_as_text(export_path)
            elif format_type == 'html':
                self._export_as_html(export_path)

            print(f"✅ 对话历史已导出到: {export_path}")
            print(f"📊 导出格式: {format_type.upper()}")
            print(f"📝 记录数量: {len(self.conversation_context.conversation_history)} 条")

        except Exception as e:
            print(f"❌ 导出失败: {e}")
            self.logger.error(f"Export failed: {e}")

    def _export_as_json(self, export_path: Path):
        """导出为JSON格式"""
        export_data = {
            'export_info': {
                'export_time': self._get_current_time(),
                'target': self.conversation_context.target,
                'total_entries': len(self.conversation_context.conversation_history),
                'session_duration': self.conversation_context._get_session_duration(),
                'version': '2.0',
                'format': 'json'
            },
            'session_stats': self.conversation_context.get_session_stats(),
            'analysis_context': self.conversation_context.analysis_context,
            'conversation_history': self.conversation_context.conversation_history,
            'user_preferences': self.conversation_context.analysis_context['preferences'],
            'user_patterns': self.conversation_context.analysis_context['user_patterns'],
            'metadata': {
                'generator': 'AIDefectDetector Deep Analysis',
                'platform': 'CLI Interactive Mode',
                'max_context_length': self.conversation_context.max_context_length
            }
        }

        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    def _export_as_markdown(self, export_path: Path):
        """导出为Markdown格式"""
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write("# AI深度分析对话历史\n\n")

            # 导出信息
            f.write("## 导出信息\n\n")
            f.write(f"- **导出时间**: {self._get_current_time()}\n")
            f.write(f"- **分析目标**: `{self.conversation_context.target}`\n")
            f.write(f"- **会话时长**: {self._format_duration(self.conversation_context._get_session_duration())}\n")
            f.write(f"- **对话记录**: {len(self.conversation_context.conversation_history)} 条\n\n")

            # 会话统计
            stats = self.conversation_context.get_session_stats()
            f.write("## 会话统计\n\n")
            f.write(f"- **分析文件数**: {stats['files_analyzed']}\n")
            f.write(f"- **成功分析**: {stats['successful_analyses']}\n")
            f.write(f"- **失败分析**: {stats['failed_analyses']}\n")
            f.write(f"- **总耗时**: {stats['total_time']:.2f}秒\n")
            f.write(f"- **最常用类型**: {stats['most_used_analysis_type']}\n\n")

            # 对话历史
            f.write("## 对话历史\n\n")

            for i, entry in enumerate(self.conversation_context.conversation_history, 1):
                f.write(f"### 对话 {i} - {entry.get('timestamp', 'N/A')}\n\n")

                if entry.get('type') == 'file_analysis':
                    file_path = entry.get('file_path', 'Unknown')
                    analysis_type = entry.get('analysis_type', 'Unknown')
                    success = entry.get('success', False)
                    exec_time = entry.get('execution_time', 0)

                    f.write(f"**类型**: 文件分析\n")
                    f.write(f"**文件**: `{file_path}`\n")
                    f.write(f"**分析类型**: {analysis_type}\n")
                    f.write(f"**结果**: {'✅ 成功' if success else '❌ 失败'}\n")
                    f.write(f"**耗时**: {exec_time:.2f}秒\n\n")

                    if entry.get('result') and entry['result'].get('success'):
                        result = entry['result']
                        if result.get('content'):
                            content = result['content']
                            preview = content[:300] + "..." if len(content) > 300 else content
                            f.write("**分析结果预览**:\n")
                            f.write("```\n")
                            f.write(preview)
                            f.write("\n```\n\n")

                    if entry.get('result') and not entry['result'].get('success'):
                        error_msg = entry['result'].get('error', '未知错误')
                        f.write(f"**错误信息**: {error_msg}\n\n")

                else:
                    # 普通对话
                    user_input = entry.get('user_input', '')
                    ai_response = entry.get('ai_response', '')

                    f.write("**用户**: ")
                    f.write(f"{user_input}\n\n")
                    f.write("**AI**: ")
                    f.write(f"{ai_response}\n\n")

                f.write("---\n\n")

    def _export_as_text(self, export_path: Path):
        """导出为纯文本格式"""
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write("AI深度分析对话历史\n")
            f.write("=" * 50 + "\n\n")

            # 导出信息
            f.write("导出信息:\n")
            f.write(f"  导出时间: {self._get_current_time()}\n")
            f.write(f"  分析目标: {self.conversation_context.target}\n")
            f.write(f"  会话时长: {self._format_duration(self.conversation_context._get_session_duration())}\n")
            f.write(f"  对话记录: {len(self.conversation_context.conversation_history)} 条\n\n")

            # 会话统计
            stats = self.conversation_context.get_session_stats()
            f.write("会话统计:\n")
            f.write(f"  分析文件数: {stats['files_analyzed']}\n")
            f.write(f"  成功分析: {stats['successful_analyses']}\n")
            f.write(f"  失败分析: {stats['failed_analyses']}\n")
            f.write(f"  总耗时: {stats['total_time']:.2f}秒\n")
            f.write(f"  最常用类型: {stats['most_used_analysis_type']}\n\n")

            # 对话历史
            f.write("对话历史:\n")
            f.write("-" * 50 + "\n\n")

            for i, entry in enumerate(self.conversation_context.conversation_history, 1):
                f.write(f"[{i}] {entry.get('timestamp', 'N/A')}\n")

                if entry.get('type') == 'file_analysis':
                    f.write(f"  类型: 文件分析\n")
                    f.write(f"  文件: {entry.get('file_path', 'Unknown')}\n")
                    f.write(f"  分析类型: {entry.get('analysis_type', 'Unknown')}\n")
                    f.write(f"  结果: {'成功' if entry.get('success', False) else '失败'}\n")
                    f.write(f"  耗时: {entry.get('execution_time', 0):.2f}秒\n")
                else:
                    f.write(f"  用户: {entry.get('user_input', '')}\n")
                    f.write(f"  AI: {entry.get('ai_response', '')}\n")

                f.write("\n")

    def _export_as_html(self, export_path: Path):
        """导出为HTML格式"""
        html_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI深度分析对话历史</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #007bff; margin-top: 30px; }}
        h3 {{ color: #495057; margin-top: 25px; }}
        .stats {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .conversation {{ margin: 20px 0; }}
        .message {{ padding: 15px; margin: 10px 0; border-radius: 8px; }}
        .user {{ background: #e3f2fd; border-left: 4px solid #2196f3; }}
        .ai {{ background: #f3e5f5; border-left: 4px solid #9c27b0; }}
        .analysis {{ background: #e8f5e8; border-left: 4px solid #4caf50; }}
        .file-info {{ background: #fff3cd; padding: 10px; border-radius: 5px; margin: 10px 0; }}
        .success {{ color: #28a745; }}
        .failure {{ color: #dc3545; }}
        code {{ background: #f1f1f1; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 AI深度分析对话历史</h1>

        <div class="stats">
            <h2>📊 会话统计</h2>
            <p><strong>导出时间</strong>: {export_time}</p>
            <p><strong>分析目标</strong>: <code>{target}</code></p>
            <p><strong>会话时长</strong>: {session_duration}</p>
            <p><strong>对话记录</strong>: {total_entries} 条</p>
            <p><strong>分析文件数</strong>: {files_analyzed}</p>
            <p><strong>成功分析</strong>: {successful_analyses}</p>
            <p><strong>失败分析</strong>: {failed_analyses}</p>
            <p><strong>总耗时</strong>: {total_time:.2f}秒</p>
        </div>

        <div class="conversation">
            <h2>💬 对话历史</h2>
            {conversation_content}
        </div>
    </div>
</body>
</html>"""

        # 生成对话内容
        conversation_html = ""
        for i, entry in enumerate(self.conversation_context.conversation_history, 1):
            timestamp = entry.get('timestamp', 'N/A')

            if entry.get('type') == 'file_analysis':
                file_path = entry.get('file_path', 'Unknown')
                analysis_type = entry.get('analysis_type', 'Unknown')
                success = entry.get('success', False)
                exec_time = entry.get('execution_time', 0)

                conversation_html += f"""
                <div class="message analysis">
                    <h3>📊 文件分析 #{i} <span class="timestamp">({timestamp})</span></h3>
                    <div class="file-info">
                        <p><strong>文件</strong>: <code>{file_path}</code></p>
                        <p><strong>分析类型</strong>: {analysis_type}</p>
                        <p><strong>结果</strong>: <span class="{'success' if success else 'failure'}">{'✅ 成功' if success else '❌ 失败'}</span></p>
                        <p><strong>耗时</strong>: {exec_time:.2f}秒</p>
                    </div>
                </div>"""

                if entry.get('result') and entry['result'].get('success'):
                    result = entry['result']
                    if result.get('content'):
                        content = result['content'][:500] + "..." if len(result['content']) > 500 else result['content']
                        conversation_html += f"""
                        <div class="message ai">
                            <p><strong>AI分析结果</strong>:</p>
                            <pre>{content}</pre>
                        </div>"""

            else:
                user_input = entry.get('user_input', '')
                ai_response = entry.get('ai_response', '')

                conversation_html += f"""
                <div class="conversation">
                    <div class="message user">
                        <p><strong>用户</strong> <span class="timestamp">({timestamp})</span>:</p>
                        <p>{user_input}</p>
                    </div>
                    <div class="message ai">
                        <p><strong>AI助手</strong>:</p>
                        <p>{ai_response}</p>
                    </div>
                </div>"""

        # 填充模板
        stats = self.conversation_context.get_session_stats()
        html_content = html_template.format(
            export_time=self._get_current_time(),
            target=self.conversation_context.target,
            session_duration=self._format_duration(self.conversation_context._get_session_duration()),
            total_entries=len(self.conversation_context.conversation_history),
            files_analyzed=stats['files_analyzed'],
            successful_analyses=stats['successful_analyses'],
            failed_analyses=stats['failed_analyses'],
            total_time=stats['total_time'],
            conversation_content=conversation_html
        )

        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def _format_duration(self, seconds: float) -> str:
        """格式化时长显示"""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分钟"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}小时"

    def _generate_conversational_response(self, user_input: str, context: dict) -> str:
        """生成对话响应（保留原方法兼容性）"""
        return self._generate_contextual_response(user_input)

    def _save_deep_analysis_result(self, result: dict, output_file: str):
        """保存深度分析结果"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_file.endswith('.json'):
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            elif output_file.endswith('.md'):
                self._save_deep_analysis_markdown(result, output_path)
            else:
                # 简单文本格式
                with open(output_path, 'w', encoding='utf-8') as f:
                    self._save_deep_analysis_text(result, f)

            print(f"📄 分析结果已保存到: {output_path}")

        except Exception as e:
            print(f"❌ 保存结果失败: {e}")

    def _save_deep_analysis_text(self, result: dict, file):
        """保存深度分析文本结果"""
        file.write(f"深度分析报告\n")
        file.write("=" * 50 + "\n")
        file.write(f"目标路径: {result['target']}\n")
        file.write(f"分析模式: {result['mode']}\n")
        file.write(f"分析文件数: {result['files_analyzed']}\n")
        file.write(f"总执行时间: {result['total_execution_time']:.2f}秒\n")
        file.write(f"对话轮次: {len(result.get('conversation_history', []))}\n\n")

        if result.get('conversation_history'):
            file.write("对话历史:\n")
            file.write("-" * 30 + "\n")
            for i, entry in enumerate(result['conversation_history'], 1):
                file.write(f"[{entry.get('timestamp', 'N/A')}]\n")
                if entry.get('type') == 'file_analysis':
                    file.write(f"分析文件: {entry.get('file_path', 'Unknown')}\n")
                    file.write(f"分析类型: {entry.get('analysis_type', 'Unknown')}\n")
                    file.write(f"结果: {'成功' if entry.get('result', {}).get('success') else '失败'}\n")
                else:
                    file.write(f"用户: {entry.get('user_input', 'N/A')}\n")
                    file.write(f"AI: {entry.get('ai_response', 'N/A')}\n")
                file.write("-" * 30 + "\n")

    def _save_deep_analysis_markdown(self, result: dict, file_path: Path):
        """保存深度分析Markdown结果"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 深度分析报告\n\n")
            f.write(f"**目标路径**: `{result['target']}`\n")
            f.write(f"**分析模式**: {result['mode']}\n")
            f.write(f"**分析文件数**: {result['files_analyzed']}\n")
            f.write(f"**总执行时间**: {result['total_execution_time']:.2f}秒\n")
            f.write(f"**对话轮次**: {len(result.get('conversation_history', []))}\n\n")

            if result.get('conversation_history'):
                f.write("## 对话历史\n\n")
                for i, entry in enumerate(result['conversation_history'], 1):
                    f.write(f"### 对话 {i} - {entry.get('timestamp', 'N/A')}\n\n")
                    if entry.get('type') == 'file_analysis':
                        f.write(f"**文件**: `{entry.get('file_path', 'Unknown')}`\n")
                        f.write(f"**分析类型**: {entry.get('analysis_type', 'Unknown')}\n")
                        f.write(f"**结果**: {'✅ 成功' if entry.get('result', {}).get('success') else '❌ 失败'}\n")
                        if entry.get('result', {}).get('content'):
                            content = entry['result']['content']
                            preview = content[:200] + "..." if len(content) > 200 else content
                            f.write(f"**内容预览**:\n```\n{preview}\n```\n")
                    else:
                        f.write(f"**用户**: {entry.get('user_input', 'N/A')}\n")
                        f.write(f"**AI**: {entry.get('ai_response', 'N/A')}\n")
                    f.write("\n")

    def _show_enhanced_startup_banner(self, target: str):
        """显示增强的启动横幅"""
        from pathlib import Path
        import os

        # 清屏（可选）
        if os.name == 'posix':  # Unix/Linux/macOS
            os.system('clear')
        else:  # Windows
            os.system('cls')

        print("\n" + "="*70)
        print("🧠 AI深度分析助手 - 交互式对话模式".center(70))
        print("="*70)
        print()

        # 显示目标信息
        target_path = Path(target)
        print(f"📁 分析目标: {target_path.resolve()}")
        print(f"📊 目标类型: {'文件' if target_path.is_file() else '目录'}")

        if target_path.is_file():
            print(f"📄 文件大小: {self._format_file_size(target_path.stat().st_size)}")
        elif target_path.is_dir():
            # 统计Python文件数量
            try:
                py_files = list(target_path.rglob("*.py"))
                print(f"🐍 Python文件: {len(py_files)} 个")
            except:
                print("🐍 Python文件: 无法统计")

        print(f"🕐 启动时间: {self._get_current_time()}")
        print()

    def _show_initialization_progress(self):
        """显示初始化进度"""
        import sys
        import time

        steps = [
            "🔧 初始化AI模型...",
            "🔗 连接到分析服务...",
            "📚 加载知识库...",
            "🎯 配置分析引擎...",
            "✅ 系统就绪！"
        ]

        print("🚀 系统初始化中:")
        for i, step in enumerate(steps, 1):
            # 显示进度条
            progress_bar = self._create_progress_bar(i, len(steps), width=30)
            print(f"  [{progress_bar}] {step}", end='\r')
            sys.stdout.flush()
            time.sleep(0.3)  # 模拟处理时间

        print()  # 换行
        print()

    def _create_progress_bar(self, current: int, total: int, width: int = 40) -> str:
        """创建进度条"""
        filled = int(width * current / total)
        bar = '█' * filled + '░' * (width - filled)
        return bar

    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def _show_enhanced_session_info(self, context: ConversationContext, analyzer):
        """显示增强的会话信息"""
        from pathlib import Path

        print("📊 会话配置信息:")
        print("-" * 50)
        print(f"  🎯 默认分析类型: {context.analysis_context['analysis_type']}")
        print(f"  📁 分析目标: {context.target}")
        print(f"  💬 对话模式: 智能上下文感知")
        print(f"  🧠 上下文容量: {context.max_context_length} 轮对话")
        print(f"  💾 自动保存: 启用")

        if self.output_file:
            print(f"  📄 输出文件: {Path(self.output_file).name}")
        else:
            print(f"  📄 输出文件: 自动生成时间戳文件")

        try:
            supported_types = analyzer.get_supported_analysis_types()
            print(f"  🔧 支持的分析类型: {', '.join(supported_types)}")
        except:
            print(f"  🔧 支持的分析类型: comprehensive, security, performance, architecture, code_review, refactoring")

        print(f"  🕐 会话开始: {context.session_start}")
        print()

    def _show_session_info(self, context: dict, analyzer):
        """显示会话信息（保留原方法兼容性）"""
        # 将旧格式转换为新的ConversationContext格式
        temp_context = ConversationContext(context.get('target', 'unknown'))
        temp_context.analysis_context = context
        self._show_enhanced_session_info(temp_context, analyzer)

    def _show_analyzing_animation(self, message: str = "AI正在分析"):
        """显示分析动画"""
        import sys
        import time
        from threading import Thread

        def animate():
            chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            for char in chars:
                sys.stdout.write(f'\r{char} {message}...')
                sys.stdout.flush()
                time.sleep(0.1)

        # 在实际实现中，这里应该启动动画线程
        # 为了简化，我们只显示静态消息
        print(f"⏳ {message}...")

    def _show_analysis_result_banner(self, success: bool, file_name: str = ""):
        """显示分析结果横幅"""
        if success:
            print(f"\n✅ 分析完成: {file_name}")
            print("🎉" * 20)
        else:
            print(f"\n❌ 分析失败: {file_name}")
            print("💥" * 20)

    def _get_current_time(self) -> str:
        """获取当前时间字符串"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _show_fix_analysis_help(self):
        """显示修复分析帮助信息"""
        print("\n📖 修复分析帮助")
        print("-" * 40)
        print("可用命令:")
        print("  help                    - 显示此帮助信息")
        print("  scan                    - 扫描目标路径中的问题")
        print("  fix <file_path>         - 修复指定文件")
        print("  batch fix               - 批量修复所有文件")
        print("  auto confirm            - 切换自动确认模式")
        print("  status                  - 显示当前状态")
        print("  history                 - 显示修复历史")
        print("  export <filename>       - 导出修复会话")
        print("  quit/exit/q             - 退出修复模式")
        print("\n修复流程:")
        print("  1. 使用 'scan' 扫描文件问题")
        print("  2. 使用 'fix <file>' 修复指定文件")
        print("  3. 或者使用 'batch fix' 批量修复")
        print("  4. 使用 'auto confirm' 启用自动确认")
        print("  5. 使用 'history' 查看修复历史")
        print("\n示例:")
        print("  scan")
        print("  fix src/main.py")
        print("  batch fix")
        print("  export fix_session.json")
        print()

    def _scan_files_for_issues(self, static_coordinator, target: str, session: dict):
        """扫描文件问题"""
        from pathlib import Path

        print(f"🔍 开始扫描: {target}")
        print("⏳ 正在分析文件...")

        try:
            target_path = Path(target)
            if not target_path.exists():
                print(f"❌ 目标路径不存在: {target}")
                return

            # 收集Python文件
            python_files = []
            if target_path.is_file() and target_path.suffix == '.py':
                python_files.append(str(target_path))
            elif target_path.is_dir():
                python_files.extend([str(f) for f in target_path.rglob("*.py")])

            if not python_files:
                print("⚠️ 未找到Python文件")
                return

            print(f"📁 找到 {len(python_files)} 个Python文件")

            # 扫描问题
            session['scanned_files'] = python_files
            session['identified_issues'] = {}
            total_issues = 0

            for i, file_path in enumerate(python_files, 1):
                print(f"🔍 [{i}/{len(python_files)}] 扫描: {Path(file_path).name}")

                try:
                    result = static_coordinator.analyze_file(file_path)
                    issues = result.issues if result.issues else []

                    if issues:
                        session['identified_issues'][file_path] = [issue.to_dict() for issue in issues]
                        total_issues += len(issues)
                        print(f"  发现 {len(issues)} 个问题")
                    else:
                        print(f"  ✅ 无问题")

                except Exception as e:
                    print(f"  ❌ 扫描失败: {e}")

            print(f"\n📊 扫描完成:")
            print(f"  📄 扫描文件: {len(python_files)}")
            print(f"  🔍 有问题文件: {len(session['identified_issues'])}")
            print(f"  ⚠️ 总问题数: {total_issues}")

            if session['identified_issues']:
                print(f"\n📋 问题文件列表:")
                for file_path, issues in list(session['identified_issues'].items())[:5]:  # 只显示前5个
                    print(f"  📄 {Path(file_path).name}: {len(issues)} 个问题")
                if len(session['identified_issues']) > 5:
                    print(f"  ... 还有 {len(session['identified_issues']) - 5} 个文件")

        except Exception as e:
            print(f"❌ 扫描失败: {e}")
            self.logger.error(f"Scan failed: {e}")

    def _fix_file_interactive(self, fix_coordinator, file_path: str, session: dict) -> dict:
        """交互式文件修复"""
        from pathlib import Path
        import asyncio

        try:
            # 检查文件路径
            full_path = Path(session['target']) / file_path
            if not full_path.exists():
                full_path = Path(file_path)  # 尝试绝对路径

            if not full_path.exists():
                print(f"❌ 文件不存在: {file_path}")
                return None

            # 获取问题列表
            file_key = str(full_path)
            if file_key not in session['identified_issues']:
                print(f"⚠️ 文件 {file_path} 没有扫描到问题，使用 'scan' 先扫描")
                return None

            issues = session['identified_issues'][file_key]
            print(f"🔧 开始修复文件: {full_path}")
            print(f"📋 发现问题: {len(issues)} 个")

            # 显示问题摘要
            for i, issue in enumerate(issues[:3], 1):
                message = issue.get('message', 'No message')
                line = issue.get('line', 'N/A')
                severity = issue.get('severity', 'unknown')
                print(f"  {i}. [{severity}] 第{line}行: {message}")
            if len(issues) > 3:
                print(f"  ... 还有 {len(issues) - 3} 个问题")

            # 创建修复请求
            request = FixAnalysisRequest(
                file_path=str(full_path),
                issues=issues,
                analysis_type="security",
                confirmation_required=not session['auto_confirm'],
                backup_enabled=True,
                auto_fix=session['auto_confirm']
            )

            print("⏳ AI正在生成修复方案...")

            # 执行修复
            result = asyncio.run(fix_coordinator.process_fix_request(request))

            if result.success:
                print(f"✅ 修复完成 (耗时: {result.total_time:.2f}秒)")
                print(f"🔧 完成阶段: {', '.join(result.stages_completed)}")

                if result.execution_result:
                    applied_fixes = len(result.execution_result.applied_suggestions)
                    print(f"📝 应用修复: {applied_fixes} 个")

                return result.to_dict()
            else:
                print(f"❌ 修复失败: {result.error_message}")
                return result.to_dict() if result else None

        except Exception as e:
            print(f"❌ 修复过程中出错: {e}")
            self.logger.error(f"Interactive fix failed: {e}")
            return None

    def _batch_fix_interactive(self, fix_coordinator, session: dict) -> dict:
        """批量修复交互"""
        import asyncio

        if not session['identified_issues']:
            print("⚠️ 没有扫描到问题，请先使用 'scan' 命令")
            return None

        total_files = len(session['identified_issues'])
        total_issues = sum(len(issues) for issues in session['identified_issues'].values())

        print(f"🔧 准备批量修复:")
        print(f"📁 文件数量: {total_files}")
        print(f"⚠️ 问题总数: {total_issues}")
        print(f"🔧 自动确认: {'启用' if session['auto_confirm'] else '禁用'}")

        if not session['auto_confirm']:
            print("\n⚠️ 批量修复将修改多个文件，建议先启用 'auto confirm'")
            choice = input("是否继续? (y/n): ").strip().lower()
            if choice not in ['y', 'yes']:
                print("❌ 取消批量修复")
                return None

        print("\n⏳ 开始批量修复...")

        try:
            # 创建批量修复请求
            requests = []
            for file_path, issues in session['identified_issues'].items():
                request = FixAnalysisRequest(
                    file_path=file_path,
                    issues=issues,
                    analysis_type="security",
                    confirmation_required=not session['auto_confirm'],
                    backup_enabled=True,
                    auto_fix=session['auto_confirm']
                )
                requests.append(request)

            # 执行批量修复
            result = fix_coordinator.process_batch_fix_requests(requests)

            # 显示结果
            print(f"\n📊 批量修复完成:")
            print(f"✅ 成功文件: {result.successful_files}/{result.total_files}")
            print(f"⏱️ 总耗时: {result.total_time:.2f}秒")
            print(f"📝 摘要: {result.summary}")

            if result.process_results:
                print(f"\n📋 详细结果:")
                for process_result in result.process_results[:5]:  # 只显示前5个
                    file_name = Path(process_result.file_path).name
                    status = "✅" if process_result.success else "❌"
                    print(f"  {status} {file_name} ({process_result.total_time:.2f}s)")
                if len(result.process_results) > 5:
                    print(f"  ... 还有 {len(result.process_results) - 5} 个文件")

            return result.__dict__ if hasattr(result, '__dict__') else {'batch_result': str(result)}

        except Exception as e:
            print(f"❌ 批量修复失败: {e}")
            self.logger.error(f"Batch fix failed: {e}")
            return None

    def _show_fix_status(self, session: dict):
        """显示修复状态"""
        print("\n📊 修复会话状态")
        print("=" * 40)
        print(f"📁 目标路径: {session['target']}")
        print(f"🔍 已扫描文件: {len(session['scanned_files'])}")
        print(f"⚠️ 发现问题文件: {len(session['identified_issues'])}")
        print(f"🔧 修复尝试: {len(session['fix_history'])}")
        print(f"✅ 成功修复: {len([f for f in session['fix_history'] if f.get('success', False)])}")
        print(f"🤖 自动确认: {'启用' if session['auto_confirm'] else '禁用'}")

        if session['identified_issues']:
            total_issues = sum(len(issues) for issues in session['identified_issues'].values())
            print(f"\n📋 问题统计:")
            print(f"  🔍 总问题数: {total_issues}")
            print(f"  📁 有问题文件: {len(session['identified_issues'])}")

            # 显示文件列表
            print(f"\n📄 待修复文件:")
            for file_path, issues in list(session['identified_issues'].items())[:5]:
                if not any(f.get('file_path') == file_path for f in session['fix_history']):
                    file_name = Path(file_path).name
                    print(f"  🔧 {file_name}: {len(issues)} 个问题")
            if len(session['identified_issues']) > 5:
                print(f"  ... 还有 {len(session['identified_issues']) - 5} 个文件")

        print()

    def _show_fix_history(self, session: dict):
        """显示修复历史"""
        print("\n📜 修复历史")
        print("=" * 40)

        if not session['fix_history']:
            print("📝 暂无修复记录")
            print()

        for i, fix_record in enumerate(session['fix_history'], 1):
            file_name = Path(fix_record.get('file_path', 'Unknown')).name
            success = fix_record.get('success', False)
            time_taken = fix_record.get('total_time', 0)
            stages = fix_record.get('stages_completed', [])

            print(f"{i}. {'✅' if success else '❌'} {file_name}")
            print(f"   耗时: {time_taken:.2f}秒")
            print(f"   阶段: {', '.join(stages)}")

            if not success and fix_record.get('error_message'):
                print(f"   错误: {fix_record['error_message']}")

            print()

    def _export_fix_session(self, session: dict, export_file: str):
        """导出修复会话"""
        try:
            export_path = Path(export_file)
            if not export_path.suffix:
                export_path = export_path.with_suffix('.json')

            export_data = {
                'export_time': self._get_current_time(),
                'session': session,
                'summary': {
                    'target': session['target'],
                    'files_scanned': len(session['scanned_files']),
                    'issues_found': sum(len(issues) for issues in session['identified_issues'].values()),
                    'fixes_attempted': len(session['fix_history']),
                    'successful_fixes': len([f for f in session['fix_history'] if f.get('success', False)])
                }
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"✅ 修复会话已导出到: {export_path}")

        except Exception as e:
            print(f"❌ 导出失败: {e}")

    def _generate_fix_response(self, user_input: str, session: dict) -> str:
        """生成修复响应"""
        user_lower = user_input.lower()

        # 检查是否在询问修复相关的问题
        if any(keyword in user_lower for keyword in ['如何修复', '怎么修复', '修复什么']):
            if session['identified_issues']:
                return f"发现了 {len(session['identified_issues'])} 个文件有问题。使用 'fix <文件路径>' 修复指定文件，或 'batch fix' 批量修复。"
            else:
                return "还没有扫描到问题。请先使用 'scan' 命令扫描文件。"

        # 检查是否在询问状态相关的问题
        elif any(keyword in user_lower for keyword in ['状态', '进度', '如何了']):
            scanned = len(session['scanned_files'])
            issues = len(session['identified_issues'])
            fixed = len([f for f in session['fix_history'] if f.get('success', False)])
            return f"已扫描 {scanned} 个文件，发现 {issues} 个文件有问题，成功修复 {fixed} 个文件。"

        # 检查是否在询问自动确认相关的问题
        elif any(keyword in user_lower for keyword in ['自动', 'auto', '确认']):
            status = "启用" if session['auto_confirm'] else "禁用"
            return f"自动确认当前{status}。使用 'auto confirm' 命令可以切换状态。"

        # 默认响应
        else:
            return "我是AI代码修复助手，可以帮助您扫描和修复代码问题。输入 'help' 查看可用命令，或使用 'scan' 开始扫描问题。"

    def _save_fix_analysis_result(self, result: dict, output_file: str):
        """保存修复分析结果"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if output_file.endswith('.json'):
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            elif output_file.endswith('.md'):
                self._save_fix_analysis_markdown(result, output_path)
            else:
                # 简单文本格式
                with open(output_path, 'w', encoding='utf-8') as f:
                    self._save_fix_analysis_text(result, f)

            print(f"📄 修复结果已保存到: {output_path}")

        except Exception as e:
            print(f"❌ 保存结果失败: {e}")

    def _save_fix_analysis_text(self, result: dict, file):
        """保存修复分析文本结果"""
        file.write(f"修复分析报告\n")
        file.write("=" * 50 + "\n")
        file.write(f"目标路径: {result['target']}\n")
        file.write(f"分析模式: {result['mode']}\n")
        file.write(f"扫描文件数: {result['files_scanned']}\n")
        file.write(f"发现问题数: {result['total_issues_found']}\n")
        file.write(f"修复尝试数: {result['fixes_attempted']}\n")
        file.write(f"成功修复数: {result['successful_fixes']}\n\n")

        session = result.get('fix_session', {})
        if session.get('fix_history'):
            file.write("修复历史:\n")
            file.write("-" * 30 + "\n")
            for i, fix_record in enumerate(session['fix_history'], 1):
                file_path = fix_record.get('file_path', 'Unknown')
                success = fix_record.get('success', False)
                file.write(f"{i}. {'✅' if success else '❌'} {Path(file_path).name}\n")
                file.write(f"   状态: {'成功' if success else '失败'}\n")
                if not success and fix_record.get('error_message'):
                    file.write(f"   错误: {fix_record['error_message']}\n")
                file.write("-" * 30 + "\n")

    def _save_fix_analysis_markdown(self, result: dict, file_path: Path):
        """保存修复分析Markdown结果"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("# 修复分析报告\n\n")
            f.write(f"**目标路径**: `{result['target']}`\n")
            f.write(f"**分析模式**: {result['mode']}\n")
            f.write(f"**扫描文件数**: {result['files_scanned']}\n")
            f.write(f"**发现问题数**: {result['total_issues_found']}\n")
            f.write(f"**修复尝试数**: {result['fixes_attempted']}\n")
            f.write(f"**成功修复数**: {result['successful_fixes']}\n\n")

            session = result.get('fix_session', {})

            # 问题统计
            if session.get('identified_issues'):
                f.write("## 发现问题统计\n\n")
                f.write("| 文件 | 问题数 |\n")
                f.write("|------|--------|\n")
                for file_path, issues in session['identified_issues'].items():
                    file_name = Path(file_path).name
                    f.write(f"| `{file_name}` | {len(issues)} |\n")
                f.write("\n")

            # 修复历史
            if session.get('fix_history'):
                f.write("## 修复历史\n\n")
                for i, fix_record in enumerate(session['fix_history'], 1):
                    file_name = Path(fix_record.get('file_path', 'Unknown')).name
                    success = fix_record.get('success', False)
                    status_icon = "✅" if success else "❌"

                    f.write(f"### {i}. {status_icon} {file_name}\n\n")
                    f.write(f"- **状态**: {'成功' if success else '失败'}\n")
                    f.write(f"- **耗时**: {fix_record.get('total_time', 0):.2f}秒\n")
                    f.write(f"- **完成阶段**: {', '.join(fix_record.get('stages_completed', []))}\n")

                    if not success and fix_record.get('error_message'):
                        f.write(f"- **错误**: {fix_record['error_message']}\n")

                    f.write("\n")