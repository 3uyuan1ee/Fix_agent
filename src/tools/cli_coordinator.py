#!/usr/bin/env python3
"""
CLI分析协调器
为CLI命令行接口提供简化的分析协调功能
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

from ..utils.logger import get_logger
from ..utils.progress import ProgressTracker
from .static_coordinator import StaticAnalysisCoordinator
from .deep_analyzer import DeepAnalysisRequest


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
                 progress: Optional[ProgressTracker] = None, max_context_length: int = 15,
                 enable_performance_monitoring: bool = True, enable_caching: bool = True):
        """
        初始化CLI交互式协调器

        Args:
            mode: 分析模式 (deep/fix)
            output_file: 输出文件路径
            progress: 进度跟踪器
            max_context_length: 最大上下文长度
            enable_performance_monitoring: 是否启用性能监控
            enable_caching: 是否启用缓存功能
        """
        self.mode = mode
        self.output_file = output_file
        self.progress = progress or ProgressTracker(verbose=True)
        self.logger = get_logger()
        self.max_context_length = max_context_length
        self.conversation_context = None

        # 性能监控
        self.enable_performance_monitoring = enable_performance_monitoring
        self.enable_caching = enable_caching

        # 性能统计
        self.performance_stats = {
            'total_analysis_time': 0.0,
            'total_cache_hits': 0,
            'total_cache_misses': 0,
            'analysis_count': 0,
            'avg_response_time': 0.0,
            'slow_requests': []
        }

        # 缓存系统
        self.analysis_cache = {}
        self.cache_ttl = 300  # 5分钟缓存时间

        # 性能优化配置
        self.optimization_config = {
            'context_length_limit': 8000,  # 上下文长度限制（字符数）
            'enable_batch_processing': True,
            'parallel_file_analysis': False,  # 暂时禁用并行分析以避免复杂性
            'smart_context_trimming': True,
            'response_timeout': 60  # 响应超时（秒）
        }

        # 深度分析配置选项
        self.analysis_config = {
            'model_selection': 'auto',  # 模型选择: auto, glm-4.5, glm-4.6, gpt-4, claude-3
            'analysis_depth': 'standard',  # 分析深度: basic, standard, detailed, comprehensive
            'custom_prompt_template': None,  # 自定义提示词模板
            'temperature': 0.3,  # AI响应创造性 (0.0-1.0)
            'max_tokens': 4000,  # 最大生成token数
            'enable_structured_output': True,  # 启用结构化输出
            'focus_areas': [],  # 重点关注领域: ['security', 'performance', 'architecture', 'code_quality']
            'exclude_patterns': [],  # 排除文件模式
            'include_patterns': [],  # 包含文件模式
            'language_style': 'professional',  # 语言风格: casual, professional, technical
            'output_format': 'comprehensive'  # 输出格式: concise, standard, comprehensive
        }

        # 错误处理和恢复配置
        self.error_handling_config = {
            'max_retry_attempts': 3,  # 最大重试次数
            'retry_delay': 2,  # 重试延迟（秒）
            'enable_fallback_mode': True,  # 启用降级模式
            'offline_mode_available': True,  # 离线模式可用
            'error_recovery_strategies': {
                'network_error': 'retry_with_backoff',  # 网络错误重试策略
                'api_error': 'fallback_model',  # API错误降级策略
                'timeout_error': 'increase_timeout',  # 超时错误处理策略
                'rate_limit_error': 'exponential_backoff'  # 限流错误处理策略
            }
        }

        # 错误统计和日志
        self.error_stats = {
            'total_errors': 0,
            'network_errors': 0,
            'api_errors': 0,
            'timeout_errors': 0,
            'file_errors': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0,
            'recent_errors': []  # 保存最近10个错误
        }

        # 静态分析集成配置
        self.static_analysis_integration = {
            'auto_load_reports': True,  # 自动加载静态分析报告
            'report_search_paths': ['.', 'static_analysis_report_*.json'],  # 报告搜索路径
            'max_report_age_days': 7,  # 最大报告年龄（天）
            'priority_threshold': 5,  # 优先级阈值（低于此值的问题优先处理）
            'report_cache': {},  # 静态分析报告缓存
            'integrated_reports': []  # 已集成的报告列表
        }

        # 高级深度分析缓存机制 (T026-010)
        self.advanced_cache_config = {
            'enable_persistent_cache': True,  # 启用持久化缓存
            'cache_file_path': '.aidefect_deep_analysis_cache.json',  # 缓存文件路径
            'max_cache_size_mb': 50,  # 最大缓存大小（MB）
            'smart_cache_key_generation': True,  # 智能缓存键生成
            'cache_validation_enabled': True,  # 启用缓存验证
            'cache_compression': True,  # 启用缓存压缩
            'semantic_cache_enabled': True,  # 启用语义缓存
            'cache_hierarchy': {
                'L1_memory': {'size_limit': 20, 'ttl': 300},      # 内存缓存: 20项, 5分钟
                'L2_disk': {'size_limit': 100, 'ttl': 86400},     # 磁盘缓存: 100项, 24小时
                'L3_semantic': {'size_limit': 50, 'ttl': 3600}    # 语义缓存: 50项, 1小时
            }
        }

        # 智能缓存统计
        self.cache_stats = {
            'L1_memory_hits': 0,
            'L1_memory_misses': 0,
            'L2_disk_hits': 0,
            'L2_disk_misses': 0,
            'L3_semantic_hits': 0,
            'L3_semantic_misses': 0,
            'cache_evictions': 0,
            'cache_compressions': 0,
            'semantic_matches': 0,
            'total_cache_writes': 0,
            'cache_size_bytes': 0,
            'average_cache retrieval_time': 0.0
        }

        # 常见问题和答案缓存（智能问答缓存）
        self.common_qa_cache = {
            'common_issues': [
                "高复杂度函数",
                "代码重复",
                "安全漏洞",
                "性能问题",
                "代码风格",
                "架构问题",
                "错误处理",
                "内存泄漏"
            ],
            'qa_pairs': {}  # 缓存常见问答对
        }

        # 语义相似度缓存
        self.semantic_cache = {
            'enabled': True,
            'similarity_threshold': 0.85,  # 相似度阈值
            'max_text_length': 1000,  # 最大文本长度
            'cache_entries': {}  # 语义缓存条目
        }

        # 缓存失效和更新策略
        self.cache_invalidation_config = {
            'auto_invalidate_on_file_change': True,  # 文件更改时自动失效
            'dependency_tracking': True,  # 依赖关系跟踪
            'cascade_invalidation': True,  # 级联失效
            'smart_invalidation': True,  # 智能失效策略
            'invalidation_triggers': {
                'file_modified': True,
                'dependency_changed': True,
                'config_updated': True,
                'manual_refresh': True
            }
        }

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

            # 加载静态分析报告
            static_reports = self._load_static_analysis_reports(target)
            if static_reports:
                print(f"📂 发现 {len(static_reports)} 个静态分析报告")
                print(f"📊 最近报告: {static_reports[0].get('age_days', 0)} 天前")
                print()

            analyzer = DeepAnalyzer()

            # 显示会话信息
            self._show_enhanced_session_info(self.conversation_context, analyzer)

            # 显示静态分析集成状态
            if static_reports:
                print(f"🔗 静态分析集成: 已启用")
                print(f"📋 可用报告文件: {len([r for r in static_reports if any(f.get('file_path', '').endswith(Path(f).name) for f in r.get('files', []))])}")
                print(f"💡 AI将基于静态分析结果提供深度建议")
                print()

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
                        session_stats = self.conversation_context.get_session_stats()
                        self._show_analysis_summary(self.conversation_context.analysis_context)
                        continue

                    # 处理性能统计命令
                    elif user_input.lower() in ['stats', 'performance', '性能']:
                        self._show_performance_stats()
                        continue

                    # 处理错误统计命令
                    elif user_input.lower() in ['errors', 'error', '错误', 'error_stats']:
                        self._show_error_statistics()
                        continue

                    # 处理配置命令
                    elif user_input.lower().startswith('config '):
                        config_parts = user_input[7:].strip().split(' ', 1)
                        if len(config_parts) == 2:
                            config_key, config_value = config_parts
                            self._configure_analysis_settings(config_key, config_value)
                        elif len(config_parts) == 1:
                            if config_parts[0].lower() in ['show', 'current', 'list']:
                                self._show_current_config()
                            elif config_parts[0].lower() in ['help', 'options', 'available']:
                                self._show_available_configs()
                            elif config_parts[0].lower() in ['reset', 'default', 'defaults']:
                                self._reset_config_to_defaults()
                            else:
                                print("❌ 配置命令格式错误，使用 'config help' 查看帮助")
                        else:
                            print("❌ 配置命令格式错误，使用 'config help' 查看帮助")
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
                'conversation_history': self.conversation_context.conversation_history,
                'analysis_context': self.conversation_context.analysis_context,
                'files_analyzed': len(self.conversation_context.analysis_context['previous_results']),
                'total_execution_time': sum(r.get('execution_time', 0) for r in self.conversation_context.analysis_context['previous_results']),
                'performance_stats': self.performance_stats
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
        print("  stats/performance/性能 - 显示性能统计")
        print("  errors/error/错误      - 显示错误统计")
        print("  config <选项> <值>      - 配置分析参数")
        print("  config show             - 显示当前配置")
        print("  config help             - 显示配置选项")
        print("  config reset            - 重置为默认配置")
        print("  export <filename>       - 导出对话历史")
        print("  quit/exit/q             - 退出分析")
        print("\n分析类型:")
        print("  comprehensive           - 综合分析")
        print("  security                - 安全分析")
        print("  performance             - 性能分析")
        print("  architecture            - 架构分析")
        print("  code_review             - 代码审查")
        print("  refactoring             - 重构建议")
        print("\n配置选项:")
        print("  config model <模型>     - 选择AI模型 (auto,glm-4.5,glm-4.6,gpt-4,claude-3)")
        print("  config depth <级别>     - 设置分析深度 (basic,standard,detailed,comprehensive)")
        print("  config temperature <值> - 设置创造性参数 (0.0-1.0)")
        print("  config max_tokens <数字> - 设置最大生成token数")
        print("  config style <风格>     - 设置语言风格 (casual,professional,technical)")
        print("  config format <格式>    - 设置输出格式 (concise,standard,comprehensive)")
        print("  config focus_areas <领域> - 设置关注领域 (security,performance,architecture)")
        print("\n高级功能:")
        print("  🚀 智能缓存系统         - 自动缓存分析结果")
        print("  📊 性能监控             - 实时跟踪响应时间")
        print("  🔍 上下文优化           - 智能修剪对话上下文")
        print("  ⏱️ 超时保护             - 防止长时间等待")
        print("  ⚙️ 灵活配置             - 多样化分析参数配置")
        print("  🛡️ 错误处理             - 自动重试和降级模式")
        print("  📈 错误统计             - 详细错误分析和建议")
        print("  🔄 降级模式             - 网络异常时的离线分析")
        print("\n错误处理:")
        print("  自动重试机制           - 网络异常时自动重试")
        print("  智能降级模式           - AI服务不可用时使用静态分析")
        print("  详细错误建议           - 针对不同错误类型提供解决方案")
        print("  错误统计报告           - 跟踪和分析错误模式")
        print("\n示例:")
        print("  analyze src/main.py")
        print("  type security")
        print("  config model glm-4.6")
        print("  config depth comprehensive")
        print("  config temperature 0.7")
        print("  stats                   # 查看性能统计")
        print("  errors                  # 查看错误统计")
        print("  export conversation.json")
        print()

    def _analyze_file_interactive_with_context(self, analyzer, file_path: str) -> dict:
        """使用上下文管理器的交互式文件分析"""
        from pathlib import Path
        import asyncio
        import time
        import hashlib

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

            # 性能优化：检查缓存
            cache_key = self._generate_cache_key(str(full_path), self.conversation_context.analysis_context['analysis_type'])
            cached_result = self._get_cached_result(cache_key)

            if cached_result:
                print(f"\n⚡ 使用缓存结果")
                print(f"📄 文件: {full_path.name}")
                print(f"🔄 缓存时间: {cached_result.get('cached_at', '未知')}")

                # 更新性能统计
                self.performance_stats['total_cache_hits'] += 1

                # 添加到上下文管理器
                self.conversation_context.add_analysis_result(
                    str(full_path),
                    self.conversation_context.analysis_context['analysis_type'],
                    cached_result['result'],
                    0.01  # 缓存响应时间
                )

                print(f"✅ 缓存分析完成")
                return cached_result['result']

            # 性能监控：开始计时
            analysis_start_time = time.time()
            self.performance_stats['analysis_count'] += 1

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

            # 显示静态分析摘要（如果有）
            self._show_static_analysis_summary(str(full_path))

            print("-" * 50)

            # 显示分析进度
            self._show_analyzing_animation("AI正在深度分析代码结构")

            # 性能优化：创建优化的分析请求
            optimized_context = self._optimize_context_for_analysis()

            # 集成静态分析结果
            integrated_context = self._integrate_static_analysis_into_context(str(full_path), optimized_context)

            # 应用配置参数到请求
            request_params = {
                'file_path': str(full_path),
                'analysis_type': self.conversation_context.analysis_context['analysis_type'],
                'context': integrated_context
            }

            # 添加配置参数到上下文
            request_params['context']['analysis_config'] = self.analysis_config.copy()

            # 如果设置了关注领域，添加到请求中
            if self.analysis_config['focus_areas']:
                request_params['focus_areas'] = self.analysis_config['focus_areas']

            # 根据分析深度调整请求
            if self.analysis_config['analysis_depth'] == 'basic':
                request_params['max_tokens'] = min(self.analysis_config['max_tokens'], 2000)
            elif self.analysis_config['analysis_depth'] == 'detailed':
                request_params['max_tokens'] = max(self.analysis_config['max_tokens'], 6000)
            elif self.analysis_config['analysis_depth'] == 'comprehensive':
                request_params['max_tokens'] = max(self.analysis_config['max_tokens'], 8000)

            # 设置其他参数
            request_params['temperature'] = self.analysis_config['temperature']
            # 将额外的配置参数添加到context中
            request_params['context']['extra_config'] = {
                'enable_structured_output': self.analysis_config.get('enable_structured_output', False),
                'language_style': self.analysis_config.get('language_style', 'professional'),
                'output_format': self.analysis_config.get('output_format', 'json')
            }

            request = DeepAnalysisRequest(**request_params)

            # 执行异步分析（带重试和错误处理）
            result = None
            execution_time = 0
            attempt = 1

            while attempt <= self.error_handling_config['max_retry_attempts']:
                try:
                    # 调整超时时间（如果是重试且有超时错误）
                    current_timeout = self.optimization_config['response_timeout']
                    if attempt > 1:
                        current_timeout *= 1.5  # 每次重试增加50%超时时间

                    result = asyncio.run(
                        asyncio.wait_for(
                            analyzer.analyze_file(request),
                            timeout=current_timeout
                        )
                    )

                    execution_time = time.time() - analysis_start_time
                    break  # 成功则跳出重试循环

                except asyncio.TimeoutError as e:
                    execution_time = time.time() - analysis_start_time
                    retry_decision = self._handle_analysis_error(e, str(full_path), attempt)

                    if retry_decision == 'retry_with_increased_timeout':
                        # 增加超时时间继续重试
                        attempt += 1
                        continue
                    elif retry_decision == 'retry':
                        # 标准重试
                        attempt += 1
                        continue
                    else:
                        # 降级模式或失败处理
                        if isinstance(retry_decision, dict):
                            result = retry_decision
                            execution_time = time.time() - analysis_start_time
                        break

                except Exception as e:
                    execution_time = time.time() - analysis_start_time
                    retry_decision = self._handle_analysis_error(e, str(full_path), attempt)

                    if retry_decision == 'retry':
                        attempt += 1
                        continue
                    else:
                        # 降级模式或失败处理
                        if isinstance(retry_decision, dict):
                            result = retry_decision
                            execution_time = time.time() - analysis_start_time
                        break

            # 如果没有任何结果，返回None
            if result is None:
                return None

            # 显示分析结果横幅
            self._show_analysis_result_banner(result.success, file_name)

            if result.success:
                # 检查是否为降级模式
                if hasattr(result, 'fallback_mode'):
                    fallback_mode = getattr(result, 'fallback_mode', '')
                    if fallback_mode:
                        print(f"\n🔄 使用了降级分析模式: {fallback_mode}")
                        self.error_stats['successful_recoveries'] += 1
                else:
                    print(f"\n🎉 分析成功完成！")

                print(f"⏱️ 执行时间: {execution_time:.2f}秒")

                # 性能监控：更新统计信息
                self._update_performance_stats(execution_time, True)

                if hasattr(result, 'model_used') and result.model_used:
                    print(f"🤖 使用模型: {result.model_used}")

                # 显示分析类型和状态
                if hasattr(result, 'analysis_type'):
                    analysis_type = result.analysis_type
                else:
                    analysis_type = self.conversation_context.analysis_context['analysis_type']

                print(f"📊 分析类型: {analysis_type}")
                print(f"🚀 缓存状态: {self._get_cache_status()}")
                print("-" * 50)

                # 根据结果类型显示不同的内容
                if hasattr(result, 'fallback_mode'):
                    if result.fallback_mode == 'static_analysis':
                        self._show_static_analysis_fallback_result(result)
                    elif result.fallback_mode == 'basic_info':
                        self._show_basic_file_info_result(result)
                else:
                    # 正常分析结果
                    if hasattr(result, 'structured_analysis') and result.structured_analysis and result.structured_analysis.get('structured'):
                        self._show_enhanced_structured_result(result.structured_analysis)
                    else:
                        # 显示文本结果的摘要
                        content = getattr(result, 'content', '')
                        if content:
                            self._show_text_result_preview(content)

                # 只有非降级模式才缓存结果
                if not hasattr(result, 'fallback_mode'):
                    self._cache_result(cache_key, result.to_dict())

                # 添加到上下文管理器
                self.conversation_context.add_analysis_result(
                    str(full_path),
                    analysis_type,
                    result.to_dict(),
                    execution_time
                )

                print(f"\n💡 提示: 使用 'summary' 查看会话总结")
                print(f"💡 提示: 使用 'export <filename>' 导出对话历史")
                print(f"💡 提示: 使用 'stats' 查看性能统计")
                print(f"💡 提示: 使用 'errors' 查看错误统计")

                return result.to_dict()
            else:
                print(f"\n❌ 分析失败")
                error_msg = getattr(result, 'error', '未知错误')
                print(f"🔴 错误信息: {error_msg}")
                print(f"⏱️ 耗时: {execution_time:.2f}秒")

                # 性能监控：更新统计信息
                self._update_performance_stats(execution_time, False)

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
                print(f"  • 使用 'errors' 查看详细错误信息")

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

    def _generate_cache_key(self, file_path: str, analysis_type: str) -> str:
        """生成缓存键"""
        import hashlib
        import os

        # 使用文件路径、分析类型和修改时间生成缓存键
        try:
            mtime = os.path.getmtime(file_path)
            cache_data = f"{file_path}:{analysis_type}:{mtime}"
            return hashlib.md5(cache_data.encode()).hexdigest()
        except OSError:
            # 如果文件不存在或无法获取修改时间，使用简单缓存键
            cache_data = f"{file_path}:{analysis_type}"
            return hashlib.md5(cache_data.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str) -> Optional[dict]:
        """获取缓存结果"""
        if not self.enable_caching:
            return None

        cache_entry = self.analysis_cache.get(cache_key)
        if not cache_entry:
            return None

        # 检查缓存是否过期
        import time
        current_time = time.time()
        if current_time - cache_entry['timestamp'] > self.cache_ttl:
            del self.analysis_cache[cache_key]
            return None

        self.performance_stats['total_cache_hits'] += 1
        return cache_entry

    def _cache_result(self, cache_key: str, result: dict):
        """缓存分析结果"""
        if not self.enable_caching:
            return

        import time
        cache_entry = {
            'result': result,
            'timestamp': time.time(),
            'cached_at': self._get_current_time(),
            'cache_key': cache_key
        }

        self.analysis_cache[cache_key] = cache_entry

        # 清理过期缓存
        self._cleanup_expired_cache()

        # 限制缓存大小
        if len(self.analysis_cache) > 100:  # 最多缓存100个结果
            # 删除最旧的缓存项
            oldest_key = min(self.analysis_cache.keys(),
                           key=lambda k: self.analysis_cache[k]['timestamp'])
            del self.analysis_cache[oldest_key]

    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        import time
        current_time = time.time()
        expired_keys = []

        for cache_key, cache_entry in self.analysis_cache.items():
            if current_time - cache_entry['timestamp'] > self.cache_ttl:
                expired_keys.append(cache_key)

        for key in expired_keys:
            del self.analysis_cache[key]

    def _optimize_context_for_analysis(self) -> dict:
        """优化分析上下文"""
        if not self.conversation_context:
            return {}

        # 获取原始上下文
        original_context = self.conversation_context.analysis_context.copy()

        # 智能上下文修剪
        if self.optimization_config['smart_context_trimming']:
            context_str = str(original_context)
            if len(context_str) > self.optimization_config['context_length_limit']:
                # 保留重要信息，删除冗余内容
                optimized_context = {
                    'target': original_context.get('target', ''),
                    'analysis_type': original_context.get('analysis_type', 'comprehensive'),
                    'current_file': original_context.get('current_file', ''),
                    'previous_results': original_context.get('previous_results', [])[-3:],  # 只保留最近3个结果
                    'preferences': original_context.get('preferences', {}),
                    'session_stats': {
                        'total_analyses': original_context.get('session_stats', {}).get('total_analyses', 0),
                        'successful_analyses': original_context.get('session_stats', {}).get('successful_analyses', 0),
                        'most_used_analysis_type': self.conversation_context.get_session_stats().get('most_used_analysis_type', 'comprehensive')
                    }
                }
                return optimized_context

        return original_context

    def _update_performance_stats(self, execution_time: float, success: bool):
        """更新性能统计"""
        if not self.enable_performance_monitoring:
            return

        self.performance_stats['total_analysis_time'] += execution_time
        self.performance_stats['total_cache_misses'] += 1

        # 更新平均响应时间
        if self.performance_stats['analysis_count'] > 0:
            self.performance_stats['avg_response_time'] = (
                self.performance_stats['total_analysis_time'] / self.performance_stats['analysis_count']
            )

        # 记录慢请求
        if execution_time > 30:  # 超过30秒的请求
            slow_request = {
                'timestamp': self._get_current_time(),
                'execution_time': execution_time,
                'success': success
            }
            self.performance_stats['slow_requests'].append(slow_request)

            # 只保留最近10个慢请求记录
            if len(self.performance_stats['slow_requests']) > 10:
                self.performance_stats['slow_requests'] = self.performance_stats['slow_requests'][-10:]

    def _get_cache_status(self) -> str:
        """获取缓存状态信息"""
        if not self.enable_caching:
            return "已禁用"

        cache_hits = self.performance_stats['total_cache_hits']
        cache_misses = self.performance_stats['total_cache_misses']
        total_requests = cache_hits + cache_misses

        if total_requests == 0:
            return f"缓存: {len(self.analysis_cache)} 项"

        hit_rate = (cache_hits / total_requests) * 100
        return f"缓存: {len(self.analysis_cache)} 项, 命中率: {hit_rate:.1f}%"

    def _show_performance_stats(self):
        """显示性能统计信息"""
        if not self.enable_performance_monitoring:
            print("❌ 性能监控已禁用")
            return

        print("\n📊 性能统计报告")
        print("=" * 50)

        stats = self.performance_stats
        print(f"🔍 总分析次数: {stats['analysis_count']}")
        print(f"⏱️ 总分析时间: {stats['total_analysis_time']:.2f}秒")
        print(f"📈 平均响应时间: {stats['avg_response_time']:.2f}秒")

        if stats['total_cache_hits'] + stats['total_cache_misses'] > 0:
            total_requests = stats['total_cache_hits'] + stats['total_cache_misses']
            hit_rate = (stats['total_cache_hits'] / total_requests) * 100
            print(f"🚀 缓存命中率: {hit_rate:.1f}% ({stats['total_cache_hits']}/{total_requests})")

        print(f"💾 缓存大小: {len(self.analysis_cache)} 项")

        # 慢请求分析
        if stats['slow_requests']:
            print(f"\n⚠️ 慢请求记录 ({len(stats['slow_requests'])} 个):")
            for i, req in enumerate(stats['slow_requests'][-5:], 1):  # 显示最近5个
                print(f"  {i}. {req['timestamp']} - {req['execution_time']:.1f}秒 {'✅' if req['success'] else '❌'}")

        # 优化建议
        print(f"\n💡 性能优化建议:")
        if stats['avg_response_time'] > 20:
            print(f"  • 平均响应时间较长，建议启用缓存功能")
        if stats.get('total_cache_hits', 0) + stats.get('total_cache_misses', 0) > 0:
            hit_rate = stats['total_cache_hits'] / (stats['total_cache_hits'] + stats['total_cache_misses']) * 100
            if hit_rate < 30:
                print(f"  • 缓存命中率较低，建议分析相似文件以提高缓存效率")
        if len(stats['slow_requests']) > 3:
            print(f"  • 慢请求较多，建议检查网络连接或使用较小的文件")

        print()

    def _configure_analysis_settings(self, config_key: str, config_value: str) -> bool:
        """配置分析设置"""
        try:
            config_key = config_key.strip()
            config_value = config_value.strip()

            if config_key in ['model', 'model_selection']:
                valid_models = ['auto', 'glm-4.5', 'glm-4.6', 'gpt-4', 'claude-3']
                if config_value.lower() in valid_models:
                    self.analysis_config['model_selection'] = config_value.lower()
                    print(f"✅ 模型已设置为: {config_value}")
                    return True
                else:
                    print(f"❌ 不支持的模型: {config_value}")
                    print(f"支持的模型: {', '.join(valid_models)}")
                    return False

            elif config_key in ['depth', 'analysis_depth']:
                valid_depths = ['basic', 'standard', 'detailed', 'comprehensive']
                if config_value.lower() in valid_depths:
                    self.analysis_config['analysis_depth'] = config_value.lower()
                    print(f"✅ 分析深度已设置为: {config_value}")
                    return True
                else:
                    print(f"❌ 不支持的深度级别: {config_value}")
                    print(f"支持的深度: {', '.join(valid_depths)}")
                    return False

            elif config_key == 'temperature':
                try:
                    temp = float(config_value)
                    if 0.0 <= temp <= 1.0:
                        self.analysis_config['temperature'] = temp
                        print(f"✅ 创造性参数已设置为: {temp}")
                        return True
                    else:
                        print(f"❌ 温度值必须在0.0-1.0之间")
                        return False
                except ValueError:
                    print(f"❌ 无效的温度值: {config_value}")
                    return False

            elif config_key == 'max_tokens':
                try:
                    tokens = int(config_value)
                    if tokens > 0:
                        self.analysis_config['max_tokens'] = tokens
                        print(f"✅ 最大token数已设置为: {tokens}")
                        return True
                    else:
                        print(f"❌ token数必须大于0")
                        return False
                except ValueError:
                    print(f"❌ 无效的token数: {config_value}")
                    return False

            elif config_key in ['style', 'language_style']:
                valid_styles = ['casual', 'professional', 'technical']
                if config_value.lower() in valid_styles:
                    self.analysis_config['language_style'] = config_value.lower()
                    print(f"✅ 语言风格已设置为: {config_value}")
                    return True
                else:
                    print(f"❌ 不支持的语言风格: {config_value}")
                    print(f"支持的风格: {', '.join(valid_styles)}")
                    return False

            elif config_key in ['format', 'output_format']:
                valid_formats = ['concise', 'standard', 'comprehensive']
                if config_value.lower() in valid_formats:
                    self.analysis_config['output_format'] = config_value.lower()
                    print(f"✅ 输出格式已设置为: {config_value}")
                    return True
                else:
                    print(f"❌ 不支持的输出格式: {config_value}")
                    print(f"支持的格式: {', '.join(valid_formats)}")
                    return False

            elif config_key == 'structured_output':
                if config_value.lower() in ['true', 'on', 'enable', '1']:
                    self.analysis_config['enable_structured_output'] = True
                    print(f"✅ 结构化输出已启用")
                    return True
                elif config_value.lower() in ['false', 'off', 'disable', '0']:
                    self.analysis_config['enable_structured_output'] = False
                    print(f"✅ 结构化输出已禁用")
                    return True
                else:
                    print(f"❌ 无效的值: {config_value} (使用 true/false)")
                    return False

            elif config_key == 'focus_areas':
                areas = [area.strip() for area in config_value.split(',')]
                valid_areas = ['security', 'performance', 'architecture', 'code_quality', 'best_practices', 'testing']
                valid_area_list = []
                for area in areas:
                    if area.lower() in valid_areas:
                        valid_area_list.append(area.lower())
                    else:
                        print(f"⚠️ 跳过无效的关注领域: {area}")

                if valid_area_list:
                    self.analysis_config['focus_areas'] = valid_area_list
                    print(f"✅ 关注领域已设置为: {', '.join(valid_area_list)}")
                    return True
                else:
                    print(f"❌ 没有有效的关注领域")
                    print(f"支持的领域: {', '.join(valid_areas)}")
                    return False

            else:
                print(f"❌ 不支持的配置项: {config_key}")
                self._show_available_configs()
                return False

        except Exception as e:
            print(f"❌ 配置设置失败: {e}")
            return False

    def _show_current_config(self):
        """显示当前配置"""
        print("\n⚙️ 当前分析配置")
        print("=" * 50)

        print(f"🤖 AI模型: {self.analysis_config['model_selection']}")
        print(f"🔍 分析深度: {self.analysis_config['analysis_depth']}")
        print(f"🎨 创造性参数: {self.analysis_config['temperature']}")
        print(f"📝 最大tokens: {self.analysis_config['max_tokens']}")
        print(f"🏗️ 结构化输出: {'启用' if self.analysis_config['enable_structured_output'] else '禁用'}")
        print(f"💬 语言风格: {self.analysis_config['language_style']}")
        print(f"📋 输出格式: {self.analysis_config['output_format']}")

        if self.analysis_config['focus_areas']:
            print(f"🎯 关注领域: {', '.join(self.analysis_config['focus_areas'])}")
        else:
            print(f"🎯 关注领域: 全部")

        if self.analysis_config['custom_prompt_template']:
            print(f"📄 自定义提示词: 已设置")
        else:
            print(f"📄 自定义提示词: 未设置")

        print()

    def _show_available_configs(self):
        """显示可用的配置选项"""
        print("\n⚙️ 可用配置选项")
        print("=" * 50)
        print("配置格式: config <选项> <值>")
        print()
        print("模型选择:")
        print("  config model auto|glm-4.5|glm-4.6|gpt-4|claude-3")
        print()
        print("分析深度:")
        print("  config depth basic|standard|detailed|comprehensive")
        print()
        print("响应参数:")
        print("  config temperature <0.0-1.0>")
        print("  config max_tokens <数字>")
        print("  config structured_output true|false")
        print()
        print("输出格式:")
        print("  config style casual|professional|technical")
        print("  config format concise|standard|comprehensive")
        print()
        print("关注领域:")
        print("  config focus_areas security,performance,architecture")
        print()
        print("示例:")
        print("  config model glm-4.6")
        print("  config depth comprehensive")
        print("  config temperature 0.7")
        print("  config focus_areas security,performance")
        print()

    def _reset_config_to_defaults(self):
        """重置配置为默认值"""
        self.analysis_config = {
            'model_selection': 'auto',
            'analysis_depth': 'standard',
            'custom_prompt_template': None,
            'temperature': 0.3,
            'max_tokens': 4000,
            'enable_structured_output': True,
            'focus_areas': [],
            'exclude_patterns': [],
            'include_patterns': [],
            'language_style': 'professional',
            'output_format': 'comprehensive'
        }
        print("✅ 配置已重置为默认值")

    def _handle_analysis_error(self, error: Exception, file_path: str, attempt: int = 1) -> Optional[dict]:
        """处理分析错误并尝试恢复"""
        import time
        import traceback
        from datetime import datetime

        # 记录错误信息
        error_info = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'file_path': file_path,
            'attempt': attempt,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc()
        }

        # 更新错误统计
        self._update_error_stats(error_info)

        # 判断错误类型并采取相应策略
        error_type = self._classify_error(error)
        recovery_strategy = self.error_handling_config['error_recovery_strategies'].get(error_type)

        print(f"\n⚠️ 分析出现错误 (第{attempt}次尝试)")
        print(f"🔴 错误类型: {error_type}")
        print(f"📝 错误信息: {str(error)}")

        # 根据错误类型提供解决建议
        suggestions = self._get_error_suggestions(error_type, error)
        if suggestions:
            print("💡 建议解决方案:")
            for i, suggestion in enumerate(suggestions, 1):
                print(f"  {i}. {suggestion}")

        # 检查是否应该重试
        if attempt < self.error_handling_config['max_retry_attempts']:
            if recovery_strategy == 'retry_with_backoff':
                delay = self.error_handling_config['retry_delay'] * (2 ** (attempt - 1))
                print(f"🔄 {delay}秒后自动重试...")
                time.sleep(delay)
                return 'retry'
            elif recovery_strategy == 'exponential_backoff':
                delay = min(self.error_handling_config['retry_delay'] * (2 ** (attempt - 1)), 30)
                print(f"🔄 {delay}秒后自动重试...")
                time.sleep(delay)
                return 'retry'
            elif recovery_strategy == 'increase_timeout':
                print("🔄 增加超时时间后重试...")
                return 'retry_with_increased_timeout'

        # 如果达到最大重试次数或错误不可重试，返回None
        print(f"❌ 已达到最大重试次数({self.error_handling_config['max_retry_attempts']})或错误不可重试")

        # 尝试降级模式
        if self.error_handling_config['enable_fallback_mode']:
            return self._try_fallback_analysis(file_path, error_info)

        return None

    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_msg = str(error).lower()
        error_type_name = type(error).__name__.lower()

        # 网络相关错误
        if any(keyword in error_msg for keyword in ['connection', 'network', 'timeout', 'unreachable', 'dns']):
            return 'network_error'

        # API相关错误
        if any(keyword in error_msg for keyword in ['api', 'authentication', 'authorization', 'quota', 'limit']):
            return 'api_error'

        # 超时错误
        if any(keyword in error_msg for keyword in ['timeout', 'timed out']) or 'timeout' in error_type_name:
            return 'timeout_error'

        # 限流错误
        if any(keyword in error_msg for keyword in ['rate limit', 'too many requests', 'quota exceeded']):
            return 'rate_limit_error'

        # 文件相关错误
        if any(keyword in error_msg for keyword in ['file', 'not found', 'permission', 'access']) or 'file' in error_type_name:
            return 'file_error'

        # 其他错误
        return 'unknown_error'

    def _get_error_suggestions(self, error_type: str, error: Exception) -> list:
        """根据错误类型提供解决建议"""
        suggestions = []

        if error_type == 'network_error':
            suggestions = [
                "检查网络连接是否正常",
                "尝试切换到其他网络环境",
                "检查防火墙设置是否阻止了连接",
                "稍后重试，可能是临时网络问题"
            ]
        elif error_type == 'api_error':
            suggestions = [
                "检查API密钥是否正确配置",
                "确认API配额是否充足",
                "尝试切换到其他AI模型",
                "检查认证信息是否过期"
            ]
        elif error_type == 'timeout_error':
            suggestions = [
                "尝试分析较小的文件",
                "增加超时时间设置",
                "检查网络延迟是否过高",
                "简化分析参数"
            ]
        elif error_type == 'rate_limit_error':
            suggestions = [
                "等待一段时间后重试",
                "降低请求频率",
                "尝试使用其他AI模型",
                "升级API配额"
            ]
        elif error_type == 'file_error':
            suggestions = [
                "检查文件路径是否正确",
                "确认文件权限是否可读",
                "检查文件是否为有效的Python代码",
                "尝试分析其他文件"
            ]
        else:
            suggestions = [
                "查看详细错误日志",
                "尝试重启应用程序",
                "联系技术支持",
                "检查系统资源是否充足"
            ]

        return suggestions

    def _update_error_stats(self, error_info: dict):
        """更新错误统计"""
        self.error_stats['total_errors'] += 1

        error_type = error_info['error_type'].lower()
        if 'network' in error_type or 'connection' in error_type:
            self.error_stats['network_errors'] += 1
        elif 'api' in error_type or 'auth' in error_type:
            self.error_stats['api_errors'] += 1
        elif 'timeout' in error_type:
            self.error_stats['timeout_errors'] += 1
        elif 'file' in error_type:
            self.error_stats['file_errors'] += 1

        # 保存最近的错误信息
        self.error_stats['recent_errors'].append(error_info)
        if len(self.error_stats['recent_errors']) > 10:
            self.error_stats['recent_errors'] = self.error_stats['recent_errors'][-10:]

    def _try_fallback_analysis(self, file_path: str, error_info: dict) -> Optional[dict]:
        """尝试降级分析模式"""
        print("\n🔄 尝试降级分析模式...")

        try:
            # 如果有静态分析结果，提供基本的静态分析
            if self.error_handling_config['offline_mode_available']:
                print("📊 启用离线静态分析模式")
                return self._perform_static_analysis_fallback(file_path)

            # 提供基本的文件信息分析
            print("📋 提供基本文件信息分析")
            return self._perform_basic_file_analysis(file_path)

        except Exception as fallback_error:
            print(f"❌ 降级模式也失败: {fallback_error}")
            self.error_stats['failed_recoveries'] += 1
            return None

    def _perform_static_analysis_fallback(self, file_path: str) -> dict:
        """执行静态分析降级模式"""
        try:
            from .static_coordinator import StaticAnalysisCoordinator
            from pathlib import Path

            # 使用静态分析工具
            coordinator = StaticAnalysisCoordinator()
            result = coordinator.analyze_file(file_path)

            return {
                'success': True,
                'fallback_mode': 'static_analysis',
                'file_path': file_path,
                'analysis_type': 'static_fallback',
                'issues': [issue.to_dict() for issue in result.issues] if result.issues else [],
                'execution_time': result.execution_time if hasattr(result, 'execution_time') else 0,
                'message': f"使用了静态分析降级模式，发现 {len(result.issues) if result.issues else 0} 个问题"
            }

        except Exception as e:
            return {
                'success': False,
                'fallback_mode': 'static_analysis',
                'error': str(e),
                'message': "静态分析降级模式也失败"
            }

    def _perform_basic_file_analysis(self, file_path: str) -> dict:
        """执行基本文件信息分析"""
        try:
            from pathlib import Path
            import os

            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return {
                    'success': False,
                    'fallback_mode': 'basic_info',
                    'error': 'File not found',
                    'message': "文件不存在"
                }

            # 获取基本文件信息
            stat = file_path_obj.stat()
            file_size = stat.st_size

            # 读取文件内容进行基本分析
            try:
                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试其他编码
                try:
                    with open(file_path_obj, 'r', encoding='gbk') as f:
                        content = f.read()
                except:
                    content = ""

            line_count = len(content.splitlines()) if content else 0
            char_count = len(content) if content else 0

            # 基本的代码结构分析
            import_count = content.count('import ')
            class_count = content.count('class ')
            function_count = content.count('def ')

            return {
                'success': True,
                'fallback_mode': 'basic_info',
                'file_path': str(file_path_obj),
                'analysis_type': 'basic_fallback',
                'basic_stats': {
                    'file_size': file_size,
                    'line_count': line_count,
                    'character_count': char_count,
                    'import_count': import_count,
                    'class_count': class_count,
                    'function_count': function_count
                },
                'message': f"基本文件信息: {line_count} 行, {class_count} 个类, {function_count} 个函数"
            }

        except Exception as e:
            return {
                'success': False,
                'fallback_mode': 'basic_info',
                'error': str(e),
                'message': "基本文件信息分析失败"
            }

    def _show_error_statistics(self):
        """显示错误统计信息"""
        print("\n🚨 错误统计报告")
        print("=" * 50)

        stats = self.error_stats
        print(f"📊 总错误数: {stats['total_errors']}")
        print(f"🌐 网络错误: {stats['network_errors']}")
        print(f"🔌 API错误: {stats['api_errors']}")
        print(f"⏱️ 超时错误: {stats['timeout_errors']}")
        print(f"📁 文件错误: {stats['file_errors']}")
        print(f"✅ 成功恢复: {stats['successful_recoveries']}")
        print(f"❌ 恢复失败: {stats['failed_recoveries']}")

        if stats['total_errors'] > 0:
            recovery_rate = (stats['successful_recoveries'] / stats['total_errors']) * 100
            print(f"📈 恢复成功率: {recovery_rate:.1f}%")

        # 显示最近的错误
        if stats['recent_errors']:
            print(f"\n📋 最近错误记录:")
            for i, error in enumerate(stats['recent_errors'][-3:], 1):
                print(f"  {i}. {error['timestamp']} - {error['error_type']}: {error['file_path']}")

        print()

    def _show_static_analysis_fallback_result(self, result: dict):
        """显示静态分析降级结果"""
        print(f"\n📊 静态分析结果 (降级模式)")
        print("-" * 50)

        if hasattr(result, 'message'):
            print(f"💬 {result.message}")

        if hasattr(result, 'issues') and result.issues:
            print(f"\n🔍 发现问题 ({len(result.issues)}个):")

            # 按严重程度分组
            severity_groups = {}
            for issue in result.issues:
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
                        tool = issue.get('tool', 'Unknown')
                        print(f"  {i}. 第{line}行 [{tool}]: {message}")

                    if len(severity_groups[severity]) > 5:
                        print(f"     ... 还有 {len(severity_groups[severity]) - 5} 个{severity}级别问题")

        print(f"\n💡 这是静态分析结果，可能不如AI分析详细。")
        print(f"💡 网络恢复后可重新分析获得更深入的结果。")
        print()

    def _show_basic_file_info_result(self, result: dict):
        """显示基本文件信息结果"""
        print(f"\n📋 基本文件信息 (降级模式)")
        print("-" * 50)

        if hasattr(result, 'message'):
            print(f"💬 {result.message}")

        if hasattr(result, 'basic_stats'):
            stats = result.basic_stats
            print(f"\n📊 文件统计:")
            print(f"  📁 文件大小: {self._format_file_size(stats.get('file_size', 0))}")
            print(f"  📝 代码行数: {stats.get('line_count', 0)}")
            print(f"  🔤 字符数量: {stats.get('character_count', 0)}")
            print(f"  📦 导入语句: {stats.get('import_count', 0)}")
            print(f"  🏗️ 类定义: {stats.get('class_count', 0)}")
            print(f"  ⚙️ 函数定义: {stats.get('function_count', 0)}")

            # 基本分析建议
            if stats.get('function_count', 0) > 20:
                print(f"\n💡 建议: 函数数量较多({stats.get('function_count', 0)})，建议考虑模块化重构")
            if stats.get('class_count', 0) > 10:
                print(f"💡 建议: 类数量较多({stats.get('class_count', 0)})，建议检查单一职责原则")
            if stats.get('import_count', 0) > 15:
                print(f"💡 建议: 导入语句较多({stats.get('import_count', 0)})，可能存在依赖耦合")

        print(f"\n💡 这是基本文件信息，仅提供代码结构统计。")
        print(f"💡 网络恢复后可重新分析获得深入的代码质量分析。")
        print()

    def _load_static_analysis_reports(self, target_path: str) -> list:
        """加载静态分析报告"""
        import glob
        import os
        from datetime import datetime
        from pathlib import Path

        if not self.static_analysis_integration['auto_load_reports']:
            return []

        reports = []
        current_time = datetime.now()

        # 搜索静态分析报告
        for pattern in self.static_analysis_integration['report_search_paths']:
            search_path = Path(target_path) / pattern if not os.path.isabs(pattern) else Path(pattern)

            if '*' in pattern:
                # 通配符搜索
                matching_files = list(Path(search_path.parent).glob(search_path.name))
            else:
                # 直接路径
                if search_path.exists():
                    matching_files = [search_path]
                else:
                    matching_files = []

            for report_file in matching_files:
                try:
                    # 检查文件年龄
                    file_mtime = datetime.fromtimestamp(report_file.stat().st_mtime)
                    age_days = (current_time - file_mtime).days

                    if age_days <= self.static_analysis_integration['max_report_age_days']:
                        # 读取报告内容
                        with open(report_file, 'r', encoding='utf-8') as f:
                            report_data = json.load(f)

                        # 验证报告格式
                        if self._is_valid_static_report(report_data):
                            report_data['file_path'] = str(report_file)
                            report_data['age_days'] = age_days
                            reports.append(report_data)

                            # 缓存报告
                            self.static_analysis_integration['report_cache'][str(report_file)] = report_data

                except Exception as e:
                    self.logger.warning(f"Failed to load static report {report_file}: {e}")

        # 按年龄排序（最新的在前）
        reports.sort(key=lambda x: x.get('age_days', float('inf')))

        self.static_analysis_integration['integrated_reports'] = reports
        return reports

    def _is_valid_static_report(self, report_data: dict) -> bool:
        """验证是否为有效的静态分析报告"""
        required_fields = ['target', 'files_analyzed', 'total_issues', 'files']

        if not all(field in report_data for field in required_fields):
            return False

        # 检查文件结构
        if 'files' in report_data and isinstance(report_data['files'], list):
            for file_info in report_data['files']:
                if not isinstance(file_info, dict):
                    return False
                if 'file_path' not in file_info:
                    return False

        return True

    def _get_static_analysis_for_file(self, file_path: str) -> Optional[dict]:
        """获取指定文件的静态分析结果"""
        target_path = Path(file_path)

        # 从已加载的报告中查找
        for report in self.static_analysis_integration['integrated_reports']:
            for file_info in report.get('files', []):
                report_file_path = Path(file_info.get('file_path', ''))

                # 检查是否为同一文件（相对路径或绝对路径匹配）
                if (report_file_path.name == target_path.name or
                    str(report_file_path) == str(target_path.resolve())):

                    # 返回匹配的文件信息
                    file_result = file_info.copy()
                    file_result['report_metadata'] = {
                        'report_target': report.get('target'),
                        'report_age_days': report.get('age_days', 0),
                        'total_issues_in_report': report.get('total_issues', 0)
                    }
                    return file_result

        return None

    def _integrate_static_analysis_into_context(self, file_path: str, context: dict) -> dict:
        """将静态分析结果集成到分析上下文中"""
        static_result = self._get_static_analysis_for_file(file_path)

        if not static_result:
            return context

        # 创建集成的上下文
        integrated_context = context.copy()

        # 添加静态分析信息到上下文
        if 'static_analysis' not in integrated_context:
            integrated_context['static_analysis'] = {}

        integrated_context['static_analysis'][file_path] = {
            'issues_count': static_result.get('issues_count', 0),
            'execution_time': static_result.get('execution_time', 0),
            'issues_summary': static_result.get('summary', {}),
            'total_issues_in_report': static_result['report_metadata']['total_issues_in_report']
        }

        # 添加问题列表（如果有）
        if 'issues' in static_result:
            # 过滤高优先级问题
            all_issues = static_result['issues']
            high_priority_issues = []

            for issue in all_issues:
                severity = issue.get('severity', 'info')
                if severity in ['error', 'warning']:
                    high_priority_issues.append(issue)

            # 只保留前10个高优先级问题
            integrated_context['static_analysis'][file_path]['high_priority_issues'] = high_priority_issues[:10]

        return integrated_context

    def _show_static_analysis_summary(self, file_path: str):
        """显示静态分析摘要"""
        static_result = self._get_static_analysis_for_file(file_path)

        if not static_result:
            return

        print(f"\n📊 静态分析摘要")
        print("-" * 40)

        issues_count = static_result.get('issues_count', 0)
        execution_time = static_result.get('execution_time', 0)
        total_report_issues = static_result['report_metadata']['total_issues_in_report']

        print(f"📁 文件: {Path(file_path).name}")
        print(f"🔍 发现问题: {issues_count} 个")
        print(f"⏱️ 分析耗时: {execution_time:.2f}秒")
        print(f"📋 报告总问题: {total_report_issues} 个")

        # 显示问题严重程度分布
        if 'summary' in static_result and 'severity_distribution' in static_result['summary']:
            severity_dist = static_result['summary']['severity_distribution']
            if severity_dist:
                print(f"\n📈 问题严重程度:")
                for severity, count in severity_dist.items():
                    emoji = {'error': '🔴', 'warning': '🟡', 'info': '🔵'}.get(severity, '⚪')
                    print(f"  {emoji} {severity}: {count} 个")

        # 显示前几个高优先级问题
        if 'high_priority_issues' in static_result.get('static_analysis', {}).get(file_path, {}):
            high_issues = static_result['static_analysis'][file_path]['high_priority_issues']
            if high_issues:
                print(f"\n⚠️  高优先级问题:")
                for i, issue in enumerate(high_issues[:5], 1):
                    line = issue.get('line', 'N/A')
                    message = issue.get('message', 'No message')
                    tool = issue.get('tool', 'Unknown')
                    print(f"  {i}. 第{line}行 [{tool}]: {message}")

        print(f"\n💡 AI将基于这些静态分析结果提供深度建议")
        print()

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

    # ===== T026-010: 高级深度分析缓存机制 =====

    def initialize_advanced_cache(self):
        """初始化高级缓存系统"""
        try:
            # 加载持久化缓存
            if self.advanced_cache_config['enable_persistent_cache']:
                self._load_persistent_cache()

            # 初始化缓存层次结构
            self._initialize_cache_hierarchy()

            # 预热常见问题缓存
            self._preload_common_qa_cache()

            self.logger.info("高级缓存系统初始化完成")

        except Exception as e:
            self.logger.error(f"高级缓存系统初始化失败: {e}")

    def _load_persistent_cache(self):
        """加载持久化缓存"""
        import os
        import json
        from pathlib import Path

        cache_file = Path(self.advanced_cache_config['cache_file_path'])

        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)

                # 恢复缓存数据
                self.analysis_cache.update(cache_data.get('analysis_cache', {}))
                self.semantic_cache['cache_entries'].update(cache_data.get('semantic_cache', {}))
                self.common_qa_cache['qa_pairs'].update(cache_data.get('qa_cache', {}))

                # 更新缓存统计
                self.cache_stats['cache_size_bytes'] = cache_data.get('cache_size_bytes', 0)

                self.logger.info(f"加载持久化缓存: {len(self.analysis_cache)} 项")

            except Exception as e:
                self.logger.warning(f"加载持久化缓存失败: {e}")

    def _save_persistent_cache(self):
        """保存持久化缓存"""
        if not self.advanced_cache_config['enable_persistent_cache']:
            return

        try:
            import json
            from pathlib import Path

            cache_file = Path(self.advanced_cache_config['cache_file_path'])
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                'analysis_cache': self.analysis_cache,
                'semantic_cache': self.semantic_cache['cache_entries'],
                'qa_cache': self.common_qa_cache['qa_pairs'],
                'cache_size_bytes': self.cache_stats['cache_size_bytes'],
                'saved_at': self._get_current_time(),
                'version': '1.0'
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            self.logger.debug("持久化缓存已保存")

        except Exception as e:
            self.logger.warning(f"保存持久化缓存失败: {e}")

    def _initialize_cache_hierarchy(self):
        """初始化缓存层次结构"""
        # L1 内存缓存 (已在 __init__ 中初始化为 self.analysis_cache)

        # L2 磁盘缓存
        self.disk_cache_path = '.aidefect_l2_cache'

        # L3 语义缓存
        self.semantic_similarity_cache = {}

        # 清理过期的持久化缓存
        self._cleanup_expired_persistent_cache()

    def _preload_common_qa_cache(self):
        """预加载常见问答缓存"""
        # 预定义一些常见的问答对
        common_qa = {
            "高复杂度函数": {
                "question": "如何处理高复杂度函数？",
                "answer": "高复杂度函数应该进行重构，考虑以下策略：\n1. 将大函数拆分为多个小函数\n2. 使用设计模式简化逻辑\n3. 提取公共逻辑到独立方法\n4. 考虑使用策略模式或状态模式",
                "category": "重构建议",
                "priority": "high"
            },
            "代码重复": {
                "question": "如何消除代码重复？",
                "answer": "消除代码重复的方法：\n1. 提取公共函数或方法\n2. 使用继承和多态\n3. 创建工具类或辅助函数\n4. 使用模板方法模式\n5. 考虑使用装饰器",
                "category": "重构建议",
                "priority": "medium"
            },
            "安全漏洞": {
                "question": "如何修复常见安全漏洞？",
                "answer": "常见安全漏洞修复方法：\n1. SQL注入：使用参数化查询\n2. XSS攻击：输入验证和输出编码\n3. CSRF：使用令牌验证\n4. 权限问题：实施最小权限原则\n5. 敏感数据：加密存储和传输",
                "category": "安全修复",
                "priority": "critical"
            },
            "性能问题": {
                "question": "如何优化代码性能？",
                "answer": "代码性能优化策略：\n1. 减少不必要的计算和I/O操作\n2. 使用缓存机制\n3. 优化算法和数据结构\n4. 异步处理长时间操作\n5. 减少内存分配和垃圾回收\n6. 使用性能分析工具定位瓶颈",
                "category": "性能优化",
                "priority": "high"
            }
        }

        self.common_qa_cache['qa_pairs'] = common_qa

    def get_smart_cache_result(self, file_path: str, analysis_type: str, user_context: str = "") -> Optional[dict]:
        """智能缓存获取 - 支持多级缓存和语义匹配"""
        import time
        start_time = time.time()

        # L1: 内存缓存查找
        l1_result = self._get_l1_cache_result(file_path, analysis_type)
        if l1_result:
            self.cache_stats['L1_memory_hits'] += 1
            self._update_cache_retrieval_time(time.time() - start_time)
            return l1_result

        self.cache_stats['L1_memory_misses'] += 1

        # L2: 磁盘缓存查找
        l2_result = self._get_l2_cache_result(file_path, analysis_type)
        if l2_result:
            self.cache_stats['L2_disk_hits'] += 1
            # 提升到L1缓存
            self._cache_result(file_path, analysis_type, l2_result)
            self._update_cache_retrieval_time(time.time() - start_time)
            return l2_result

        self.cache_stats['L2_disk_misses'] += 1

        # L3: 语义缓存查找
        if self.advanced_cache_config['semantic_cache_enabled'] and user_context:
            l3_result = self._get_semantic_cache_result(file_path, user_context)
            if l3_result:
                self.cache_stats['L3_semantic_hits'] += 1
                self.cache_stats['semantic_matches'] += 1
                self._update_cache_retrieval_time(time.time() - start_time)
                return l3_result

        self.cache_stats['L3_semantic_misses'] += 1
        self._update_cache_retrieval_time(time.time() - start_time)
        return None

    def _get_l1_cache_result(self, file_path: str, analysis_type: str) -> Optional[dict]:
        """获取L1内存缓存结果"""
        cache_key = self._generate_smart_cache_key(file_path, analysis_type)
        return self._get_cached_result(cache_key)

    def _get_l2_cache_result(self, file_path: str, analysis_type: str) -> Optional[dict]:
        """获取L2磁盘缓存结果"""
        import os
        import json
        from pathlib import Path

        try:
            cache_key = self._generate_smart_cache_key(file_path, analysis_type)
            cache_file = Path(self.disk_cache_path) / f"{cache_key}.json"

            if cache_file.exists():
                # 检查文件修改时间
                file_mtime = cache_file.stat().st_mtime
                import time
                if time.time() - file_mtime <= self.advanced_cache_config['cache_hierarchy']['L2_disk']['ttl']:

                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)

                    return cache_data.get('result')
                else:
                    # 删除过期缓存
                    cache_file.unlink()

        except Exception as e:
            self.logger.warning(f"L2缓存读取失败: {e}")

        return None

    def _get_semantic_cache_result(self, file_path: str, user_context: str) -> Optional[dict]:
        """获取语义缓存结果"""
        if not self.semantic_cache['enabled']:
            return None

        try:
            # 计算用户输入的语义指纹
            context_fingerprint = self._generate_semantic_fingerprint(user_context)

            # 在语义缓存中查找相似条目
            for cached_fingerprint, cached_data in self.semantic_cache['cache_entries'].items():
                similarity = self._calculate_semantic_similarity(context_fingerprint, cached_fingerprint)

                if similarity >= self.semantic_cache['similarity_threshold']:
                    return cached_data['result']

        except Exception as e:
            self.logger.warning(f"语义缓存查找失败: {e}")

        return None

    def cache_smart_result(self, file_path: str, analysis_type: str, result: dict, user_context: str = ""):
        """智能缓存存储 - 多级缓存策略"""
        import time

        # 生成智能缓存键
        cache_key = self._generate_smart_cache_key(file_path, analysis_type)

        # L1: 内存缓存
        self._cache_result(cache_key, result)

        # L2: 磁盘缓存（异步）
        if len(str(result)) < 1024 * 1024:  # 小于1MB的结果才存磁盘
            self._cache_to_l2_disk(cache_key, result)

        # L3: 语义缓存
        if self.advanced_cache_config['semantic_cache_enabled'] and user_context:
            self._cache_to_semantic(user_context, result)

        # 更新统计
        self.cache_stats['total_cache_writes'] += 1
        self.cache_stats['cache_size_bytes'] += len(str(result))

        # 定期保存持久化缓存
        if self.cache_stats['total_cache_writes'] % 10 == 0:
            self._save_persistent_cache()

    def _generate_smart_cache_key(self, file_path: str, analysis_type: str) -> str:
        """生成智能缓存键"""
        import hashlib
        import os

        # 基础信息
        key_components = [
            file_path,
            analysis_type,
            str(self.analysis_config.get('analysis_depth', 'standard')),
            str(self.analysis_config.get('model_selection', 'auto'))
        ]

        # 文件修改时间（如果启用智能失效）
        if self.cache_invalidation_config['auto_invalidate_on_file_change']:
            try:
                mtime = os.path.getmtime(file_path)
                key_components.append(str(mtime))
            except OSError:
                pass

        # 分析配置哈希
        config_hash = hashlib.md5(str(sorted(self.analysis_config.items())).encode()).hexdigest()[:8]
        key_components.append(config_hash)

        # 生成最终缓存键
        cache_data = ":".join(key_components)
        return hashlib.md5(cache_data.encode()).hexdigest()

    def _cache_to_l2_disk(self, cache_key: str, result: dict):
        """缓存到L2磁盘"""
        import json
        import os
        import time
        from pathlib import Path

        try:
            cache_dir = Path(self.disk_cache_path)
            cache_dir.mkdir(exist_ok=True)

            cache_file = cache_dir / f"{cache_key}.json"

            cache_data = {
                'result': result,
                'timestamp': time.time(),
                'cache_key': cache_key,
                'analysis_config': self.analysis_config
            }

            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)

            # 检查缓存大小限制
            self._enforce_disk_cache_size_limit()

        except Exception as e:
            self.logger.warning(f"L2磁盘缓存写入失败: {e}")

    def _cache_to_semantic(self, user_context: str, result: dict):
        """缓存到语义缓存"""
        try:
            import time

            # 生成语义指纹
            context_fingerprint = self._generate_semantic_fingerprint(user_context)

            # 存储到语义缓存
            cache_entry = {
                'result': result,
                'user_context': user_context[:self.semantic_cache['max_text_length']],
                'timestamp': time.time(),
                'access_count': 1
            }

            self.semantic_cache['cache_entries'][context_fingerprint] = cache_entry

            # 限制语义缓存大小
            max_size = self.advanced_cache_config['cache_hierarchy']['L3_semantic']['size_limit']
            if len(self.semantic_cache['cache_entries']) > max_size:
                # 删除最旧的条目
                oldest_fingerprint = min(
                    self.semantic_cache['cache_entries'].keys(),
                    key=lambda k: self.semantic_cache['cache_entries'][k]['timestamp']
                )
                del self.semantic_cache['cache_entries'][oldest_fingerprint]
                self.cache_stats['cache_evictions'] += 1

        except Exception as e:
            self.logger.warning(f"语义缓存写入失败: {e}")

    def _generate_semantic_fingerprint(self, text: str) -> str:
        """生成语义指纹"""
        import hashlib

        # 文本预处理
        processed_text = text.lower().strip()

        # 提取关键词
        keywords = []
        for issue in self.common_qa_cache['common_issues']:
            if issue in processed_text:
                keywords.append(issue)

        # 如果没有匹配的关键词，使用文本哈希
        if not keywords:
            return hashlib.md5(processed_text.encode()).hexdigest()[:16]

        # 生成基于关键词的指纹
        keyword_fingerprint = ":".join(sorted(keywords))
        return hashlib.md5(keyword_fingerprint.encode()).hexdigest()[:16]

    def _calculate_semantic_similarity(self, fingerprint1: str, fingerprint2: str) -> float:
        """计算语义相似度"""
        if fingerprint1 == fingerprint2:
            return 1.0

        # 简单的相似度计算（可以后续升级为更复杂的算法）
        common_chars = set(fingerprint1) & set(fingerprint2)
        total_chars = set(fingerprint1) | set(fingerprint2)

        if not total_chars:
            return 0.0

        return len(common_chars) / len(total_chars)

    def _enforce_disk_cache_size_limit(self):
        """强制执行磁盘缓存大小限制"""
        try:
            import os
            from pathlib import Path

            cache_dir = Path(self.disk_cache_path)
            if not cache_dir.exists():
                return

            # 计算当前缓存大小
            total_size = sum(f.stat().st_size for f in cache_dir.rglob('*.json') if f.is_file())
            max_size_bytes = self.advanced_cache_config['max_cache_size_mb'] * 1024 * 1024

            if total_size > max_size_bytes:
                # 删除最旧的缓存文件
                cache_files = list(cache_dir.glob('*.json'))
                cache_files.sort(key=lambda f: f.stat().st_mtime)

                for cache_file in cache_files:
                    try:
                        cache_file.unlink()
                        total_size -= cache_file.stat().st_size
                        self.cache_stats['cache_evictions'] += 1

                        if total_size <= max_size_bytes * 0.8:  # 删除到80%容量
                            break
                    except OSError:
                        continue

        except Exception as e:
            self.logger.warning(f"磁盘缓存大小限制执行失败: {e}")

    def _cleanup_expired_persistent_cache(self):
        """清理过期的持久化缓存"""
        import time
        from pathlib import Path

        try:
            cache_dir = Path(self.disk_cache_path)
            if not cache_dir.exists():
                return

            current_time = time.time()
            l2_ttl = self.advanced_cache_config['cache_hierarchy']['L2_disk']['ttl']

            for cache_file in cache_dir.glob('*.json'):
                try:
                    file_mtime = cache_file.stat().st_mtime
                    if current_time - file_mtime > l2_ttl:
                        cache_file.unlink()
                        self.cache_stats['cache_evictions'] += 1
                except OSError:
                    continue

        except Exception as e:
            self.logger.warning(f"清理过期缓存失败: {e}")

    def _update_cache_retrieval_time(self, retrieval_time: float):
        """更新缓存检索时间统计"""
        current_avg = self.cache_stats['average_cache_retrieval_time']
        count = self.cache_stats['L1_memory_hits'] + self.cache_stats['L2_disk_hits'] + self.cache_stats['L3_semantic_hits']

        if count > 0:
            self.cache_stats['average_cache_retrieval_time'] = (current_avg * (count - 1) + retrieval_time) / count

    def get_common_qa_suggestion(self, user_input: str) -> Optional[dict]:
        """获取常见问答建议"""
        user_lower = user_input.lower()

        # 查找匹配的常见问题
        for issue in self.common_qa_cache['common_issues']:
            if issue in user_lower:
                qa_pair = self.common_qa_cache['qa_pairs'].get(issue)
                if qa_pair:
                    return {
                        'question': qa_pair['question'],
                        'answer': qa_pair['answer'],
                        'category': qa_pair['category'],
                        'priority': qa_pair['priority'],
                        'match_type': 'exact'
                    }

        return None

    def invalidate_cache_for_file(self, file_path: str):
        """为特定文件失效缓存"""
        import os

        try:
            # 失效内存缓存
            cache_keys_to_remove = []
            for cache_key, cache_entry in self.analysis_cache.items():
                # 简单的文件路径匹配检查
                if file_path in str(cache_entry.get('result', {})):
                    cache_keys_to_remove.append(cache_key)

            for cache_key in cache_keys_to_remove:
                del self.analysis_cache[cache_key]

            # 失效磁盘缓存
            from pathlib import Path
            import json
            cache_dir = Path(self.disk_cache_path)
            if cache_dir.exists():
                for cache_file in cache_dir.glob('*.json'):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)

                        if file_path in str(cache_data.get('result', {})):
                            cache_file.unlink()
                    except:
                        continue

            self.logger.info(f"已为文件 {file_path} 失效缓存")

        except Exception as e:
            self.logger.warning(f"缓存失效失败: {e}")

    def get_comprehensive_cache_stats(self) -> dict:
        """获取综合缓存统计信息"""
        total_requests = (
            self.cache_stats['L1_memory_hits'] + self.cache_stats['L1_memory_misses'] +
            self.cache_stats['L2_disk_hits'] + self.cache_stats['L2_disk_misses'] +
            self.cache_stats['L3_semantic_hits'] + self.cache_stats['L3_semantic_misses']
        )

        l1_hit_rate = 0.0
        if self.cache_stats['L1_memory_hits'] + self.cache_stats['L1_memory_misses'] > 0:
            l1_hit_rate = self.cache_stats['L1_memory_hits'] / (self.cache_stats['L1_memory_hits'] + self.cache_stats['L1_memory_misses']) * 100

        l2_hit_rate = 0.0
        if self.cache_stats['L2_disk_hits'] + self.cache_stats['L2_disk_misses'] > 0:
            l2_hit_rate = self.cache_stats['L2_disk_hits'] / (self.cache_stats['L2_disk_hits'] + self.cache_stats['L2_disk_misses']) * 100

        l3_hit_rate = 0.0
        if self.cache_stats['L3_semantic_hits'] + self.cache_stats['L3_semantic_misses'] > 0:
            l3_hit_rate = self.cache_stats['L3_semantic_hits'] / (self.cache_stats['L3_semantic_hits'] + self.cache_stats['L3_semantic_misses']) * 100

        overall_hit_rate = 0.0
        if total_requests > 0:
            overall_hit_rate = (self.cache_stats['L1_memory_hits'] + self.cache_stats['L2_disk_hits'] + self.cache_stats['L3_semantic_hits']) / total_requests * 100

        from pathlib import Path
        l2_items = len(list(Path(self.disk_cache_path).glob('*.json'))) if Path(self.disk_cache_path).exists() else 0

        return {
            'cache_hierarchy_performance': {
                'L1_memory': {
                    'hits': self.cache_stats['L1_memory_hits'],
                    'misses': self.cache_stats['L1_memory_misses'],
                    'hit_rate_percent': round(l1_hit_rate, 2),
                    'current_items': len(self.analysis_cache)
                },
                'L2_disk': {
                    'hits': self.cache_stats['L2_disk_hits'],
                    'misses': self.cache_stats['L2_disk_misses'],
                    'hit_rate_percent': round(l2_hit_rate, 2),
                    'current_items': l2_items
                },
                'L3_semantic': {
                    'hits': self.cache_stats['L3_semantic_hits'],
                    'misses': self.cache_stats['L3_semantic_misses'],
                    'hit_rate_percent': round(l3_hit_rate, 2),
                    'semantic_matches': self.cache_stats['semantic_matches'],
                    'current_items': len(self.semantic_cache['cache_entries'])
                }
            },
            'overall_stats': {
                'total_requests': total_requests,
                'overall_hit_rate_percent': round(overall_hit_rate, 2),
                'total_cache_writes': self.cache_stats['total_cache_writes'],
                'cache_evictions': self.cache_stats['cache_evictions'],
                'cache_size_mb': round(self.cache_stats['cache_size_bytes'] / (1024 * 1024), 2),
                'average_retrieval_time_ms': round(self.cache_stats['average_cache_retrieval_time'] * 1000, 2)
            },
            'qa_cache_stats': {
                'common_issues_count': len(self.common_qa_cache['common_issues']),
                'qa_pairs_count': len(self.common_qa_cache['qa_pairs']),
                'enabled_features': {
                    'persistent_cache': self.advanced_cache_config['enable_persistent_cache'],
                    'semantic_cache': self.advanced_cache_config['semantic_cache_enabled'],
                    'smart_cache_keys': self.advanced_cache_config['smart_cache_key_generation'],
                    'cache_validation': self.advanced_cache_config['cache_validation_enabled']
                }
            }
        }

    def show_advanced_cache_status(self):
        """显示高级缓存状态"""
        stats = self.get_comprehensive_cache_stats()

        print("\n🗄️ 高级缓存系统状态")
        print("=" * 50)

        # 总体统计
        overall = stats['overall_stats']
        print(f"📊 总体统计:")
        print(f"  总请求数: {overall['total_requests']}")
        print(f"  总命中率: {overall['overall_hit_rate_percent']}%")
        print(f"  缓存写入: {overall['total_cache_writes']}")
        print(f"  缓存大小: {overall['cache_size_mb']} MB")
        print(f"  平均检索时间: {overall['average_retrieval_time_ms']} ms")

        # 层次性能
        hierarchy = stats['cache_hierarchy_performance']
        print(f"\n🏗️ 缓存层次性能:")

        print(f"  L1 内存缓存:")
        print(f"    命中率: {hierarchy['L1_memory']['hit_rate_percent']}%")
        print(f"    当前项: {hierarchy['L1_memory']['current_items']}")

        print(f"  L2 磁盘缓存:")
        print(f"    命中率: {hierarchy['L2_disk']['hit_rate_percent']}%")
        print(f"    当前项: {hierarchy['L2_disk']['current_items']}")

        print(f"  L3 语义缓存:")
        print(f"    命中率: {hierarchy['L3_semantic']['hit_rate_percent']}%")
        print(f"    语义匹配: {hierarchy['L3_semantic']['semantic_matches']}")
        print(f"    当前项: {hierarchy['L3_semantic']['current_items']}")

        # 启用的功能
        features = stats['qa_cache_stats']['enabled_features']
        print(f"\n⚙️ 启用功能:")
        for feature, enabled in features.items():
            status = "✅" if enabled else "❌"
            feature_name = feature.replace('_', ' ').title()
            print(f"  {status} {feature_name}")

        print()