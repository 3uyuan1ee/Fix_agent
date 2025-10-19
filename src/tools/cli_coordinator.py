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
                 progress: Optional[ProgressTracker] = None):
        """
        初始化CLI交互式协调器

        Args:
            mode: 分析模式 (deep/fix)
            output_file: 输出文件路径
            progress: 进度跟踪器
        """
        self.mode = mode
        self.output_file = output_file
        self.progress = progress or ProgressTracker(verbose=True)
        self.logger = get_logger()

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

        print(f"🧠 开始深度分析: {target}")
        print("=" * 60)
        print("💡 提示: 输入 'quit' 或 'exit' 退出分析")
        print("💡 提示: 输入 'help' 查看可用命令")
        print("💡 提示: 输入 'analyze <file_path>' 分析指定文件")
        print("💡 提示: 输入 'type <analysis_type>' 设置分析类型")
        print()

        try:
            analyzer = DeepAnalyzer()
            conversation_history = []
            analysis_context = {
                'target': target,
                'analysis_type': 'comprehensive',
                'current_file': None,
                'previous_results': []
            }

            print(f"📁 目标路径: {target}")
            print(f"🔍 当前分析类型: {analysis_context['analysis_type']}")
            print(f"📊 支持的分析类型: {', '.join(analyzer.get_supported_analysis_types())}")
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
                        if new_type in analyzer.get_supported_analysis_types():
                            analysis_context['analysis_type'] = new_type
                            print(f"✅ 分析类型已设置为: {new_type}")
                        else:
                            print(f"❌ 不支持的分析类型: {new_type}")
                            print(f"支持的类型: {', '.join(analyzer.get_supported_analysis_types())}")
                        continue

                    # 处理分析命令
                    elif user_input.lower().startswith('analyze '):
                        file_path = user_input[8:].strip()
                        result = self._analyze_file_interactive(analyzer, file_path, analysis_context, conversation_history)
                        if result:
                            analysis_context['previous_results'].append(result)
                        continue

                    # 处理总结命令
                    elif user_input.lower() == 'summary':
                        self._show_analysis_summary(analysis_context)
                        continue

                    # 处理导出命令
                    elif user_input.lower().startswith('export '):
                        export_file = user_input[7:].strip()
                        self._export_conversation(conversation_history, export_file)
                        continue

                    # 处理普通对话输入
                    else:
                        print(f"💭 正在处理您的问题: {user_input}")
                        print("🔍 AI正在思考...")

                        # 这里可以添加更复杂的对话处理逻辑
                        # 暂时给出简单的回应
                        response = self._generate_conversational_response(user_input, analysis_context)
                        print(f"🤖 AI: {response}")

                        # 记录对话历史
                        conversation_history.append({
                            'timestamp': self._get_current_time(),
                            'user_input': user_input,
                            'ai_response': response
                        })

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

    def _analyze_file_interactive(self, analyzer, file_path: str, context: dict, history: list) -> dict:
        """交互式文件分析"""
        from pathlib import Path
        import asyncio

        try:
            # 检查文件是否存在
            full_path = Path(context['target']) / file_path
            if not full_path.exists():
                full_path = Path(file_path)  # 尝试绝对路径

            if not full_path.exists():
                print(f"❌ 文件不存在: {file_path}")
                return None

            print(f"🔍 开始分析文件: {full_path}")
            print(f"📊 分析类型: {context['analysis_type']}")
            print("⏳ AI正在深度分析...")

            # 创建分析请求
            request = DeepAnalysisRequest(
                file_path=str(full_path),
                analysis_type=context['analysis_type'],
                context=context
            )

            # 执行异步分析
            result = asyncio.run(analyzer.analyze_file(request))

            if result.success:
                print(f"✅ 分析完成 (耗时: {result.execution_time:.2f}秒)")
                print(f"🤖 使用模型: {result.model_used}")

                # 显示分析结果摘要
                if result.structured_analysis and result.structured_analysis.get('structured'):
                    self._show_structured_result(result.structured_analysis)
                else:
                    # 显示文本结果的摘要
                    content_preview = result.content[:300] + "..." if len(result.content) > 300 else result.content
                    print(f"📋 分析结果:")
                    print("-" * 20)
                    print(content_preview)
                    print("-" * 20)

                # 记录到对话历史
                history.append({
                    'timestamp': self._get_current_time(),
                    'type': 'file_analysis',
                    'file_path': str(full_path),
                    'analysis_type': context['analysis_type'],
                    'result': result.to_dict()
                })

                return result.to_dict()
            else:
                print(f"❌ 分析失败: {result.error}")
                return None

        except Exception as e:
            print(f"❌ 分析过程中出错: {e}")
            self.logger.error(f"Interactive analysis failed: {e}")
            return None

    def _show_structured_result(self, structured_result: dict):
        """显示结构化分析结果"""
        print("\n📊 结构化分析结果:")
        print("-" * 30)

        if 'summary' in structured_result:
            print(f"📝 摘要: {structured_result['summary']}")

        if 'issues' in structured_result and structured_result['issues']:
            print(f"\n🔍 发现问题 ({len(structured_result['issues'])}个):")
            for i, issue in enumerate(structured_result['issues'][:5], 1):  # 只显示前5个
                severity = issue.get('severity', 'unknown')
                message = issue.get('message', 'No message')
                line = issue.get('line', 'N/A')
                print(f"  {i}. [{severity}] 第{line}行: {message}")

            if len(structured_result['issues']) > 5:
                print(f"  ... 还有 {len(structured_result['issues']) - 5} 个问题")

        if 'recommendations' in structured_result and structured_result['recommendations']:
            print(f"\n💡 建议 ({len(structured_result['recommendations'])}条):")
            for i, rec in enumerate(structured_result['recommendations'][:3], 1):  # 只显示前3条
                print(f"  {i}. {rec}")

        print()

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

    def _generate_conversational_response(self, user_input: str, context: dict) -> str:
        """生成对话响应"""
        # 这里可以集成更复杂的LLM对话逻辑
        # 目前提供简单的规则响应

        user_lower = user_input.lower()

        # 检查是否在询问分析相关的问题
        if any(keyword in user_lower for keyword in ['如何分析', '怎么分析', '分析什么']):
            return f"您可以使用 'analyze <文件路径>' 命令来分析指定文件。当前分析类型是 {context['analysis_type']}，可以使用 'type <类型>' 命令更改。"

        # 检查是否在询问文件相关的问题
        elif any(keyword in user_lower for keyword in ['文件', '代码', 'project']):
            analyzed_count = len(context['previous_results'])
            if analyzed_count > 0:
                return f"我已经分析了 {analyzed_count} 个文件。使用 'summary' 命令查看详细信息，或者使用 'analyze <文件路径>' 分析更多文件。"
            else:
                return "还没有分析任何文件。使用 'analyze <文件路径>' 命令开始分析。"

        # 检查是否在询问类型相关的问题
        elif any(keyword in user_lower for keyword in ['类型', 'type', '分析类型']):
            return f"当前分析类型是 {context['analysis_type']}。支持的类型包括: comprehensive, security, performance, architecture, code_review, refactoring。"

        # 默认响应
        else:
            return "我是AI代码分析助手，可以帮助您进行深度代码分析。输入 'help' 查看可用命令，或直接使用 'analyze <文件路径>' 开始分析文件。"

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