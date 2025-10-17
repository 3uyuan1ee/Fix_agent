#!/usr/bin/env python3
"""
CLI命令行接口模块
提供完整的命令行参数解析、帮助信息显示和错误处理功能
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import json

from ..utils.config import ConfigManager
from ..utils.logger import get_logger
from ..agent.planner import AnalysisMode
from ..agent.orchestrator import AgentOrchestrator, Session

logger = get_logger()


@dataclass
class CLIArguments:
    """CLI参数数据类"""
    # 基本参数
    mode: Optional[str] = None
    target: Optional[str] = None
    output: Optional[str] = None
    config: Optional[str] = None
    verbose: bool = False
    quiet: bool = False

    # 分析选项
    static_tools: Optional[List[str]] = None
    deep_model: Optional[str] = None
    fix_confirm: bool = True

    # 输出格式
    format: str = "simple"
    export: Optional[str] = None

    # 交互控制
    interactive: Optional[bool] = None
    batch_file: Optional[str] = None

    # 功能开关
    enable_cache: bool = True
    enable_logging: bool = True
    dry_run: bool = False

    # 帮助和版本
    help: bool = False
    version: bool = False
    list_tools: bool = False

    # 子命令相关
    command: Optional[str] = None
    analyze_command: Optional[str] = None
    sub_target: Optional[str] = None  # 子命令中的target参数
    sub_tools: Optional[List[str]] = None  # 子命令中的tools参数
    sub_format: Optional[str] = None  # 子命令中的format参数
    sub_output: Optional[str] = None  # 子命令中的output参数
    sub_verbose: bool = False  # 子命令中的verbose参数
    sub_quiet: bool = False  # 子命令中的quiet参数
    sub_dry_run: bool = False  # 子命令中的dry_run参数



class CLIArgumentParser:
    """CLI参数解析器"""

    def __init__(self):
        """初始化CLI参数解析器"""
        self.parser = None
        self.subparsers = None
        self._setup_parser()

    def _setup_parser(self):
        """设置参数解析器"""
        self.parser = argparse.ArgumentParser(
            prog='aidetector',
            description='AI缺陷检测系统 - 智能代码缺陷检测与修复工具',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=self._get_examples_epilog()
        )

        # 添加子命令解析器
        self.subparsers = self.parser.add_subparsers(
            dest='command',
            help='可用命令',
            metavar='{analyze,version,help}'
        )

        self._add_analyze_subcommand()
        self._add_global_arguments()
        self._add_analysis_arguments()
        self._add_output_arguments()
        self._add_control_arguments()
        self._add_advanced_arguments()

    def _get_examples_epilog(self) -> str:
        """获取示例文本"""
        return """
使用示例:
  # 交互式模式（默认）
  aidetector

  # 静态分析模式
  aidetector --mode static --target src/

  # 深度分析模式
  aidetector --mode deep --target main.py --format detailed

  # 分析修复模式
  aidetector --mode fix --target utils/ --confirm

  # 批处理模式
  aidetector --batch commands.txt --output results.json

  # 列出可用工具
  aidetector --list-tools

  # 显示详细帮助
  aidetector --help --verbose

更多信息请访问: https://github.com/your-repo/ai-defect-detector
        """

    def _add_global_arguments(self):
        """添加全局参数"""
        global_group = self.parser.add_argument_group('全局选项')

        global_group.add_argument(
            '--mode', '-m',
            choices=['static', 'deep', 'fix'],
            help='分析模式: static(静态分析), deep(LLM深度分析), fix(分析修复)'
        )

        global_group.add_argument(
            '--target', '-t',
            help='目标文件或目录路径'
        )

        global_group.add_argument(
            '--config', '-c',
            help='配置文件路径 (默认: config/user_config.yaml)'
        )

        global_group.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='显示详细输出信息'
        )

        global_group.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='静默模式，最小化输出'
        )

        global_group.add_argument(
            '--version',
            action='store_true',
            help='显示版本信息'
        )

    def _add_analysis_arguments(self):
        """添加分析相关参数"""
        analysis_group = self.parser.add_argument_group('分析选项')

        analysis_group.add_argument(
            '--static-tools',
            nargs='+',
            help='指定静态分析工具 (默认: 使用配置文件中的工具)'
        )

        analysis_group.add_argument(
            '--deep-model',
            help='指定深度分析使用的LLM模型'
        )

        analysis_group.add_argument(
            '--no-confirm',
            action='store_true',
            help='修复模式下跳过确认步骤'
        )

        analysis_group.add_argument(
            '--dry-run',
            action='store_true',
            help='模拟运行，不执行实际的分析操作'
        )

    def _add_output_arguments(self):
        """添加输出相关参数"""
        output_group = self.parser.add_argument_group('输出选项')

        output_group.add_argument(
            '--output', '-o',
            help='输出文件路径'
        )

        output_group.add_argument(
            '--format', '-f',
            choices=['simple', 'detailed', 'json', 'table', 'markdown'],
            default='simple',
            help='输出格式 (默认: simple)'
        )

        output_group.add_argument(
            '--export',
            choices=['pdf', 'html', 'csv'],
            help='导出格式 (需要额外依赖)'
        )

        output_group.add_argument(
            '--list-tools',
            action='store_true',
            help='列出所有可用的分析工具'
        )

    def _add_control_arguments(self):
        """添加控制相关参数"""
        control_group = self.parser.add_argument_group('控制选项')

        control_group.add_argument(
            '--interactive',
            action='store_true',
            help='强制交互式模式'
        )

        control_group.add_argument(
            '--no-interactive',
            action='store_true',
            help='禁用交互式模式'
        )

        control_group.add_argument(
            '--batch',
            dest='batch_file',
            help='批处理文件，包含待执行的命令'
        )

    def _add_analyze_subcommand(self):
        """添加analyze子命令"""
        analyze_parser = self.subparsers.add_parser(
            'analyze',
            help='执行代码分析',
            description='执行静态分析、深度分析或修复分析'
        )

        # analyze子命令的子命令
        analyze_subparsers = analyze_parser.add_subparsers(
            dest='analyze_command',
            help='分析模式',
            metavar='{static,deep,fix}'
        )

        # static子命令
        static_parser = analyze_subparsers.add_parser(
            'static',
            help='执行静态分析',
            description='使用传统静态分析工具进行代码质量检查'
        )

        static_parser.add_argument(
            'target',
            help='目标文件或目录路径'
        )

        static_parser.add_argument(
            '--tools',
            nargs='+',
            help='指定要使用的静态分析工具'
        )

        static_parser.add_argument(
            '--format', '-f',
            choices=['simple', 'detailed', 'json', 'table', 'markdown'],
            default='simple',
            help='输出格式 (默认: simple)'
        )

        static_parser.add_argument(
            '--output', '-o',
            help='输出文件路径'
        )

        static_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='显示详细输出信息'
        )

        static_parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='静默模式，最小化输出'
        )

        static_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模拟运行，不执行实际的分析操作'
        )

        # deep子命令（占位符）
        deep_parser = analyze_subparsers.add_parser(
            'deep',
            help='执行深度分析（开发中）',
            description='使用大语言模型进行深度代码分析'
        )

        deep_parser.add_argument(
            'target',
            help='目标文件或目录路径'
        )

        # fix子命令（占位符）
        fix_parser = analyze_subparsers.add_parser(
            'fix',
            help='执行分析修复（开发中）',
            description='分析问题并提供修复建议'
        )

        fix_parser.add_argument(
            'target',
            help='目标文件或目录路径'
        )

    def _add_advanced_arguments(self):
        """添加高级参数"""
        advanced_group = self.parser.add_argument_group('高级选项')

        advanced_group.add_argument(
            '--no-cache',
            action='store_true',
            help='禁用缓存功能'
        )

        advanced_group.add_argument(
            '--no-logging',
            action='store_true',
            help='禁用日志记录'
        )

    def parse_args(self, args: Optional[List[str]] = None, validate_paths: bool = True) -> CLIArguments:
        """
        解析命令行参数

        Args:
            args: 参数列表，None表示从sys.argv获取
            validate_paths: 是否验证文件路径存在性

        Returns:
            CLIArguments: 解析后的参数对象

        Raises:
            SystemExit: 参数解析失败时退出程序
        """
        try:
            parsed = self.parser.parse_args(args)

            # 转换为CLIArguments对象
            cli_args = CLIArguments(
                mode=parsed.mode,
                target=parsed.target,
                output=parsed.output,
                config=parsed.config,
                verbose=parsed.verbose,
                quiet=parsed.quiet,
                static_tools=parsed.static_tools,
                deep_model=parsed.deep_model,
                fix_confirm=not parsed.no_confirm,
                format=parsed.format,
                export=parsed.export,
                interactive=self._determine_interactive_mode(parsed),
                batch_file=parsed.batch_file,
                enable_cache=not parsed.no_cache,
                enable_logging=not parsed.no_logging,
                dry_run=parsed.dry_run,
                help=getattr(parsed, 'help', False),
                version=parsed.version,
                list_tools=parsed.list_tools,
                # 子命令参数
                command=getattr(parsed, 'command', None),
                analyze_command=getattr(parsed, 'analyze_command', None),
                sub_target=getattr(parsed, 'target', None),
                sub_tools=getattr(parsed, 'tools', None),
                sub_format=getattr(parsed, 'format', None),
                sub_output=getattr(parsed, 'output', None),
                sub_verbose=getattr(parsed, 'verbose', False),
                sub_quiet=getattr(parsed, 'quiet', False),
                sub_dry_run=getattr(parsed, 'dry_run', False)
            )

            # 验证参数组合
            self._validate_arguments(cli_args, validate_paths)

            return cli_args

        except argparse.ArgumentError as e:
            logger.error(f"参数解析错误: {e}")
            self.parser.print_usage()
            raise SystemExit(1)
        except Exception as e:
            logger.error(f"未知错误: {e}")
            raise SystemExit(1)

    def _determine_interactive_mode(self, parsed) -> Optional[bool]:
        """确定交互模式"""
        if parsed.interactive:
            return True
        elif parsed.no_interactive or parsed.batch_file:
            return False
        else:
            return None  # 使用默认逻辑

    def _validate_arguments(self, args: CLIArguments, validate_paths: bool = True):
        """验证参数组合的有效性"""
        errors = []

        # 检查互斥参数
        if args.verbose and args.quiet:
            errors.append("不能同时指定 --verbose 和 --quiet")

        # 检查必需参数
        if args.mode and not args.target and not args.list_tools and validate_paths:
            errors.append("指定模式时需要提供 --target 参数")

        # 检批处理文件
        if args.batch_file and args.interactive:
            errors.append("批处理模式不支持交互模式")

        # 检查输出格式
        if args.export and not args.output:
            errors.append("指定 --export 时需要提供 --output 参数")

        # 检查文件路径（仅在需要验证时）
        if validate_paths:
            if args.target:
                target_path = Path(args.target)
                if not target_path.exists():
                    errors.append(f"目标路径不存在: {args.target}")

            if args.batch_file:
                batch_path = Path(args.batch_file)
                if not batch_path.exists():
                    errors.append(f"批处理文件不存在: {args.batch_file}")

        if errors:
            for error in errors:
                logger.error(f"参数验证失败: {error}")
            self.parser.print_usage()
            raise SystemExit(1)

    def print_help(self, topic: Optional[str] = None):
        """打印帮助信息"""
        if topic:
            self._print_topic_help(topic)
        else:
            self.parser.print_help()

    def _print_topic_help(self, topic: str):
        """打印特定主题的帮助"""
        help_topics = {
            'modes': self._get_modes_help(),
            'tools': self._get_tools_help(),
            'formats': self._get_formats_help(),
            'examples': self._get_examples_help()
        }

        if topic.lower() in help_topics:
            print(f"\n{help_topics[topic.lower()]}")
        else:
            print(f"\n未知帮助主题: {topic}")
            print(f"可用主题: {', '.join(help_topics.keys())}")

    def _get_modes_help(self) -> str:
        """获取模式帮助信息"""
        return """
分析模式详解:

  static    静态分析模式
    使用传统静态分析工具（Pylint、Bandit、Mypy等）
    快速、准确、无API调用成本
    适用于常规代码质量检查和安全扫描

  deep      深度分析模式
    使用大语言模型进行代码理解
    能够发现复杂逻辑问题和架构缺陷
    适用于关键业务逻辑和复杂算法分析

  fix       分析修复模式
    结合静态分析和LLM生成修复建议
    提供具体的问题修复方案
    支持自动应用修复（需确认）
        """

    def _get_tools_help(self) -> str:
        """获取工具帮助信息"""
        try:
            config = ConfigManager()
            tools = config.get_tools_config()

            help_text = "可用分析工具:\n\n"

            static_tools = tools.get('static_analysis_tools', {})
            for tool_name, tool_config in static_tools.items():
                enabled = "✓" if tool_config.get('enabled', True) else "✗"
                description = tool_config.get('description', '无描述')
                help_text += f"  {tool_name:12} {enabled} {description}\n"

            return help_text

        except Exception as e:
            return f"获取工具信息失败: {e}"

    def _get_formats_help(self) -> str:
        """获取格式帮助信息"""
        return """
输出格式详解:

  simple     简洁格式
    只显示关键问题和统计信息
    适用于快速查看结果概要

  detailed   详细格式
    显示完整的分析过程和详细结果
    包含上下文信息和修复建议

  json       JSON格式
    结构化数据，便于程序处理
    支持与其他工具集成

  table      表格格式
    以表格形式显示问题清单
    便于阅读和比较

  markdown   Markdown格式
    生成文档友好的报告
    支持直接发布到文档系统
        """

    def _get_examples_help(self) -> str:
        """获取示例帮助信息"""
        return """
使用示例:

基础用法:
  aidetector                                    # 启动交互式模式
  aidetector --mode static src/                 # 静态分析src目录
  aidetector --mode deep main.py                # 深度分析main.py

高级用法:
  aidetector --mode fix utils/ --confirm        # 修复模式，需要确认
  aidetector --batch commands.txt               # 批处理执行
  aidetector --list-tools                       # 查看可用工具

输出控制:
  aidetector --format json -o report.json       # JSON格式输出
  aidetector --export pdf -o report.pdf         # 导出PDF报告
  aidetector --quiet --mode static src/         # 静默模式

配置选项:
  aidetector --config custom.yaml               # 使用自定义配置
  aidetector --deep-model gpt-4                 # 指定LLM模型
  aidetector --static-tools pylint bandit      # 指定静态工具
        """

    def print_version(self):
        """打印版本信息"""
        try:
            version_info = self._get_version_info()
            print(f"AI缺陷检测系统 v{version_info['version']}")
            print(f"构建时间: {version_info['build_time']}")
            print(f"Python版本: {version_info['python_version']}")
            print(f"配置文件: {version_info['config_file']}")
        except Exception as e:
            print(f"获取版本信息失败: {e}")
            print("AI缺陷检测系统 v0.1.0")

    def _get_version_info(self) -> Dict[str, str]:
        """获取版本信息"""
        try:
            # 尝试从版本文件读取
            version_file = Path(__file__).parent.parent.parent / "VERSION"
            if version_file.exists():
                with open(version_file, 'r', encoding='utf-8') as f:
                    version = f.read().strip()
            else:
                version = "0.1.0"

            import datetime
            build_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return {
                "version": version,
                "build_time": build_time,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "config_file": "config/user_config.yaml"
            }
        except Exception:
            return {
                "version": "0.1.0",
                "build_time": "unknown",
                "python_version": "unknown",
                "config_file": "config/user_config.yaml"
            }

    def list_tools(self):
        """列出所有可用工具"""
        try:
            config = ConfigManager()
            tools_config = config.get_tools_config()

            print("\n可用分析工具:")
            print("=" * 60)

            # 静态分析工具
            static_tools = tools_config.get('static_analysis_tools', {})
            if static_tools:
                print("\n静态分析工具:")
                for tool_name, tool_config in static_tools.items():
                    enabled = "启用" if tool_config.get('enabled', True) else "禁用"
                    description = tool_config.get('description', '无描述')
                    print(f"  {tool_name:12} [{enabled:4}] {description}")

            # LLM模型
            llm_config = tools_config.get('llm_interface', {})
            if llm_config:
                print("\nLLM模型:")
                for model_name in ['gpt-4', 'gpt-3.5-turbo', 'claude-3']:
                    configured = "✓" if model_name in str(llm_config) else "✗"
                    print(f"  {model_name:15} {configured}")

            print("\n使用 --static-tools 参数指定要使用的工具")
            print("使用 --deep-model 参数指定LLM模型")

        except Exception as e:
            logger.error(f"获取工具信息失败: {e}")
            print(f"获取工具信息失败: {e}")


class CLIHelper:
    """CLI帮助工具类"""

    @staticmethod
    def suggest_command(user_input: str, available_commands: List[str]) -> List[str]:
        """
        根据用户输入建议可能的命令

        Args:
            user_input: 用户输入
            available_commands: 可用命令列表

        Returns:
            List[str]: 建议的命令列表
        """
        import difflib

        suggestions = difflib.get_close_matches(
            user_input.lower(),
            [cmd.lower() for cmd in available_commands],
            n=3,
            cutoff=0.6
        )

        return suggestions

    @staticmethod
    def validate_path(path_str: str) -> bool:
        """
        验证路径是否有效

        Args:
            path_str: 路径字符串

        Returns:
            bool: 路径是否有效
        """
        try:
            path = Path(path_str)
            return path.exists()
        except Exception:
            return False

    @staticmethod
    def format_error_message(error_type: str, details: str) -> str:
        """
        格式化错误消息

        Args:
            error_type: 错误类型
            details: 错误详情

        Returns:
            str: 格式化的错误消息
        """
        return f"❌ {error_type}: {details}"