"""
用户交互处理模块
实现用户输入解析、参数验证、响应格式化和交互处理功能
"""

import re
import os
import sys
import signal
import threading
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .planner import AnalysisMode, ExecutionPlan
from .execution_engine import ExecutionResult


class InputType(Enum):
    """输入类型枚举"""
    COMMAND = "command"           # 命令输入
    NATURAL_LANGUAGE = "natural"  # 自然语言输入
    CONFIRMATION = "confirmation" # 确认输入
    INTERRUPTION = "interruption" # 中断输入
    EXIT = "exit"                # 退出输入
    HELP = "help"                # 帮助输入
    UNKNOWN = "unknown"          # 未知输入


class OutputFormat(Enum):
    """输出格式枚举"""
    SIMPLE = "simple"     # 简洁格式
    DETAILED = "detailed" # 详细格式
    JSON = "json"         # JSON格式
    TABLE = "table"       # 表格格式
    MARKDOWN = "markdown" # Markdown格式


@dataclass
class ParsedInput:
    """解析后的用户输入"""
    original_input: str
    input_type: InputType
    command: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    arguments: List[str] = field(default_factory=list)
    flags: Dict[str, bool] = field(default_factory=dict)
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """参数验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sanitized_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FormattedOutput:
    """格式化输出"""
    content: str
    format_type: OutputFormat
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Optional[Dict[str, Any]] = None


class InputParser:
    """用户输入解析器"""

    def __init__(self, config_manager=None):
        """
        初始化输入解析器

        Args:
            config_manager: 配置管理器实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 获取配置
        try:
            self.config = self.config_manager.get_section('input_parser') or {}
        except:
            self.config = {}

        # 命令模式
        self.command_patterns = {
            r'^/help\s*(.*)$': 'help',
            r'^/exit\s*(.*)$': 'exit',
            r'^/quit\s*(.*)$': 'quit',
            r'^/cancel\s*(.*)$': 'cancel',
            r'^/stop\s*(.*)$': 'stop',
            r'^/pause\s*(.*)$': 'pause',
            r'^/resume\s*(.*)$': 'resume',
            r'^/status\s*(.*)$': 'status',
            r'^/history\s*(.*)$': 'history',
            r'^/clear\s*(.*)$': 'clear',
            r'^/mode\s+(.+)$': 'mode',
            r'^/format\s+(.+)$': 'format',
            r'^/save\s*(.*)$': 'save',
            r'^/load\s*(.*)$': 'load',
            r'^/export\s*(.*)$': 'export',
            r'^/config\s*(.*)$': 'config',
        }

        # 自然语言模式指示符
        self.natural_language_indicators = [
            '分析', '检查', '扫描', '查看', '解释', '说明', '修复', '优化',
            'analyze', 'check', 'scan', 'review', 'explain', 'describe', 'fix', 'optimize'
        ]

        # 确认模式指示符
        self.confirmation_patterns = [
            r'^(是|y|yes|确定|继续|确认)$',
            r'^(否|n|no|取消|停止|放弃)$',
            r'^(quit|exit|cancel|stop)$'
        ]

        self.logger.info("InputParser initialized")

    def parse(self, user_input: str) -> ParsedInput:
        """
        解析用户输入

        Args:
            user_input: 用户输入字符串

        Returns:
            解析结果
        """
        input_clean = user_input.strip()

        # 空输入处理
        if not input_clean:
            return ParsedInput(
                original_input=user_input,
                input_type=InputType.UNKNOWN,
                is_valid=False,
                validation_errors=["输入不能为空"]
            )

        # 检查中断信号
        if self._is_interruption(input_clean):
            return ParsedInput(
                original_input=user_input,
                input_type=InputType.INTERRUPTION,
                command="interrupt"
            )

        # 检查退出信号
        if self._is_exit_command(input_clean):
            return ParsedInput(
                original_input=user_input,
                input_type=InputType.EXIT,
                command="exit"
            )

        # 检查帮助命令
        if self._is_help_command(input_clean):
            return ParsedInput(
                original_input=user_input,
                input_type=InputType.HELP,
                command="help"
            )

        # 检查确认命令
        confirmation_result = self._parse_confirmation(input_clean)
        if confirmation_result:
            return confirmation_result

        # 检查命令模式
        command_result = self._parse_command(input_clean)
        if command_result:
            return command_result

        # 默认为自然语言输入
        return self._parse_natural_language(input_clean)

    def _is_interruption(self, input_str: str) -> bool:
        """检查是否为中断输入"""
        interruption_patterns = [
            r'^\x03$',  # Ctrl+C
            r'^/interrupt$',
            r'^/break$',
            r'^/stop$',
            r'^/cancel$'
        ]

        for pattern in interruption_patterns:
            if re.match(pattern, input_str, re.IGNORECASE):
                return True
        return False

    def _is_exit_command(self, input_str: str) -> bool:
        """检查是否为退出命令"""
        exit_patterns = [
            r'^(exit|quit|bye|再见)$',
            r'^/(exit|quit|stop)$'
        ]

        for pattern in exit_patterns:
            if re.match(pattern, input_str, re.IGNORECASE):
                return True
        return False

    def _is_help_command(self, input_str: str) -> bool:
        """检查是否为帮助命令"""
        help_patterns = [
            r'^(/help|help|\?|？)$',
            r'^/help\s+.+$'
        ]

        for pattern in help_patterns:
            if re.match(pattern, input_str, re.IGNORECASE):
                return True
        return False

    def _parse_confirmation(self, input_str: str) -> Optional[ParsedInput]:
        """解析确认输入"""
        input_lower = input_str.lower()

        for i, pattern in enumerate(self.confirmation_patterns):
            match = re.match(pattern, input_lower)
            if match:
                if i == 0:  # 肯定确认
                    return ParsedInput(
                        original_input=input_str,
                        input_type=InputType.CONFIRMATION,
                        command="confirm",
                        parameters={"response": True}
                    )
                elif i == 1:  # 否定确认
                    return ParsedInput(
                        original_input=input_str,
                        input_type=InputType.CONFIRMATION,
                        command="confirm",
                        parameters={"response": False}
                    )
                else:  # 退出确认
                    return ParsedInput(
                        original_input=input_str,
                        input_type=InputType.EXIT,
                        command="exit"
                    )

        return None

    def _parse_command(self, input_str: str) -> Optional[ParsedInput]:
        """解析命令输入"""
        for pattern, command in self.command_patterns.items():
            match = re.match(pattern, input_str, re.IGNORECASE)
            if match:
                # 提取参数
                args = []
                if match.groups():
                    args_str = match.group(1).strip()
                    if args_str:
                        # 简单的参数分割
                        args = re.split(r'\s+', args_str)

                # 解析标志
                flags = {}
                parameters = {}

                # 处理键值对参数
                for i, arg in enumerate(args):
                    if arg.startswith('--'):
                        if '=' in arg:
                            key, value = arg[2:].split('=', 1)
                            parameters[key] = value
                        else:
                            flags[arg[2:]] = True
                    elif arg.startswith('-'):
                        flags[arg[1:]] = True
                    else:
                        # 位置参数
                        parameters[f'arg_{i}'] = arg

                # 特殊处理：对于特定命令，简化参数映射
                if command == 'mode' and args:
                    parameters['mode'] = args[0].lower()
                elif command == 'format' and args:
                    parameters['format'] = args[0].lower()
                elif command == 'export' and args:
                    # export命令的第一个参数是格式，不是文件路径
                    parameters['format'] = args[0].lower()
                elif command in ['save', 'load'] and args:
                    parameters['file_path'] = args[0]

                return ParsedInput(
                    original_input=input_str,
                    input_type=InputType.COMMAND,
                    command=command,
                    parameters=parameters,
                    arguments=args,
                    flags=flags
                )

        return None

    def _parse_natural_language(self, input_str: str) -> ParsedInput:
        """解析自然语言输入"""
        # 提取关键词
        keywords = self._extract_keywords(input_str)

        # 检测文件路径
        file_paths = self._extract_file_paths(input_str)

        # 检测模式偏好
        mode_hints = self._detect_mode_hints(input_str)

        return ParsedInput(
            original_input=input_str,
            input_type=InputType.NATURAL_LANGUAGE,
            parameters={
                'keywords': keywords,
                'file_paths': file_paths,
                'mode_hints': mode_hints,
                'text': input_str
            }
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取
        keywords = []

        # 分析相关关键词
        analysis_keywords = [
            '代码', '文件', '目录', '项目', '函数', '类', '模块',
            'code', 'file', 'directory', 'project', 'function', 'class', 'module'
        ]

        # 问题类型关键词
        issue_keywords = [
            '错误', '问题', '漏洞', '缺陷', '警告', '异常',
            'error', 'issue', 'vulnerability', 'defect', 'warning', 'exception'
        ]

        # 操作类型关键词
        action_keywords = [
            '静态', '深度', '修复', '检查', '扫描', '分析', '优化',
            'static', 'deep', 'fix', 'check', 'scan', 'analyze', 'optimize'
        ]

        all_keywords = analysis_keywords + issue_keywords + action_keywords

        for keyword in all_keywords:
            if keyword.lower() in text.lower():
                keywords.append(keyword)

        return list(set(keywords))

    def _extract_file_paths(self, text: str) -> List[str]:
        """提取文件路径"""
        # 匹配文件路径模式
        path_patterns = [
            r'[\w\-./]+\.py',      # Python文件
            r'[\w\-./]+',           # 一般路径
            r'"[^"]*"',            # 引号包围的路径
            r"'[^']*'"             # 单引号包围的路径
        ]

        file_paths = []
        for pattern in path_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # 清理引号
                clean_path = match.strip('"\'')
                if os.path.exists(clean_path) or '/' in clean_path or '\\' in clean_path:
                    file_paths.append(clean_path)

        return list(set(file_paths))

    def _detect_mode_hints(self, text: str) -> List[str]:
        """检测模式提示"""
        hints = []

        if any(keyword in text.lower() for keyword in ['静态', 'static', '快速', 'quick']):
            hints.append('static')

        if any(keyword in text.lower() for keyword in ['深度', 'deep', '详细', 'detailed', '智能']):
            hints.append('deep')

        if any(keyword in text.lower() for keyword in ['修复', 'fix', '解决', 'solve', '优化', 'optimize']):
            hints.append('fix')

        return hints


class ParameterValidator:
    """参数验证器"""

    def __init__(self, config_manager=None):
        """
        初始化参数验证器

        Args:
            config_manager: 配置管理器实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 获取配置
        try:
            self.config = self.config_manager.get_section('parameter_validator') or {}
        except:
            self.config = {}

        # 验证规则
        self.validation_rules = {
            'max_path_length': self.config.get('max_path_length', 1000),
            'allowed_extensions': self.config.get('allowed_extensions', ['.py', '.js', '.ts', '.java', '.cpp', '.c']),
            'max_file_size': self.config.get('max_file_size', 10 * 1024 * 1024),  # 10MB
            'forbidden_paths': self.config.get('forbidden_paths', ['/etc', '/usr/bin', '/bin']),
            'max_concurrent_files': self.config.get('max_concurrent_files', 100),
        }

        self.logger.info("ParameterValidator initialized")

    def validate(self, parsed_input: ParsedInput) -> ValidationResult:
        """
        验证解析后的输入

        Args:
            parsed_input: 解析后的输入

        Returns:
            验证结果
        """
        errors = []
        warnings = []
        sanitized_params = {}

        try:
            # 验证命令参数
            if parsed_input.input_type == InputType.COMMAND:
                cmd_errors, cmd_warnings, cmd_sanitized = self._validate_command_params(parsed_input)
                errors.extend(cmd_errors)
                warnings.extend(cmd_warnings)
                sanitized_params.update(cmd_sanitized)

            # 验证自然语言参数
            elif parsed_input.input_type == InputType.NATURAL_LANGUAGE:
                nl_errors, nl_warnings, nl_sanitized = self._validate_natural_language_params(parsed_input)
                errors.extend(nl_errors)
                warnings.extend(nl_warnings)
                sanitized_params.update(nl_sanitized)

            # 验证文件路径
            if 'file_paths' in parsed_input.parameters:
                file_errors, file_warnings, file_sanitized = self._validate_file_paths(
                    parsed_input.parameters['file_paths']
                )
                errors.extend(file_errors)
                warnings.extend(file_warnings)
                sanitized_params.update(file_sanitized)

            # 验证模式参数
            if 'mode' in parsed_input.parameters:
                mode_errors, mode_warnings, mode_sanitized = self._validate_mode_parameter(
                    parsed_input.parameters['mode']
                )
                errors.extend(mode_errors)
                warnings.extend(mode_warnings)
                sanitized_params.update(mode_sanitized)

            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings,
                sanitized_params=sanitized_params
            )

        except Exception as e:
            self.logger.error(f"参数验证失败: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"参数验证过程中发生错误: {str(e)}"]
            )

    def _validate_command_params(self, parsed_input: ParsedInput) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """验证命令参数"""
        errors = []
        warnings = []
        sanitized = {}

        command = parsed_input.command
        params = parsed_input.parameters

        if command == 'mode':
            # 验证模式参数 - 优先检查简化的参数
            mode = params.get('mode', params.get('arg_0', '')).lower()
            if not mode or mode not in ['static', 'deep', 'fix']:
                errors.append(f"无效的分析模式: {mode}，支持的模式: static, deep, fix")
            else:
                sanitized['mode'] = mode

        elif command == 'format':
            # 验证格式参数 - 优先检查简化的参数
            format_type = params.get('format', params.get('arg_0', '')).lower()
            if not format_type or format_type not in ['simple', 'detailed', 'json', 'table', 'markdown']:
                errors.append(f"无效的输出格式: {format_type}，支持的格式: simple, detailed, json, table, markdown")
            else:
                sanitized['format'] = format_type

        elif command == 'save' or command == 'load' or command == 'export':
            # 验证文件路径参数
            file_path = params.get('arg_0', '')
            if not file_path:
                errors.append(f"{command} 命令需要指定文件路径")
            else:
                # 验证路径安全性
                path_errors, path_sanitized = self._validate_path_security(file_path)
                if path_errors:
                    errors.extend(path_errors)
                else:
                    sanitized['file_path'] = path_sanitized

        return errors, warnings, sanitized

    def _validate_natural_language_params(self, parsed_input: ParsedInput) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """验证自然语言参数"""
        errors = []
        warnings = []
        sanitized = {}

        params = parsed_input.parameters

        # 验证文本长度
        text = params.get('text', '')
        if len(text) > 10000:
            warnings.append("输入文本较长，可能会影响处理性能")

        if len(text) > 50000:
            errors.append("输入文本过长，请简化输入")
        else:
            sanitized['text'] = text

        # 验证文件路径
        file_paths = params.get('file_paths', [])
        if file_paths:
            valid_paths = []
            for file_path in file_paths:
                path_errors, path_sanitized = self._validate_path_security(file_path)
                if path_errors:
                    warnings.extend([f"路径 {file_path}: {error}" for error in path_errors])
                else:
                    valid_paths.append(path_sanitized)
            sanitized['file_paths'] = valid_paths

        # 验证模式提示
        mode_hints = params.get('mode_hints', [])
        if mode_hints:
            valid_hints = [hint for hint in mode_hints if hint in ['static', 'deep', 'fix']]
            if len(valid_hints) != len(mode_hints):
                warnings.append("部分模式提示无效，已自动过滤")
            sanitized['mode_hints'] = valid_hints

        return errors, warnings, sanitized

    def _validate_file_paths(self, file_paths: List[str]) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """验证文件路径列表"""
        errors = []
        warnings = []
        sanitized = {}

        if len(file_paths) > self.validation_rules['max_concurrent_files']:
            errors.append(f"文件数量过多，最多支持 {self.validation_rules['max_concurrent_files']} 个文件")

        valid_paths = []
        for file_path in file_paths:
            path_errors, path_sanitized = self._validate_path_security(file_path)
            if path_errors:
                errors.extend([f"路径 {file_path}: {error}" for error in path_errors])
            else:
                valid_paths.append(path_sanitized)

                # 检查文件是否存在
                if not os.path.exists(path_sanitized):
                    warnings.append(f"文件不存在: {path_sanitized}")

                # 检查文件大小
                elif os.path.isfile(path_sanitized):
                    try:
                        file_size = os.path.getsize(path_sanitized)
                        if file_size > self.validation_rules['max_file_size']:
                            warnings.append(f"文件过大: {path_sanitized} ({file_size} bytes)")
                    except OSError:
                        warnings.append(f"无法读取文件信息: {path_sanitized}")

        sanitized['file_paths'] = valid_paths
        return errors, warnings, sanitized

    def _validate_mode_parameter(self, mode: str) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """验证模式参数"""
        errors = []
        warnings = []
        sanitized = {}

        if isinstance(mode, str):
            mode_lower = mode.lower()
            if mode_lower in ['static', 'deep', 'fix']:
                sanitized['mode'] = mode_lower
            else:
                errors.append(f"无效的分析模式: {mode}，支持的模式: static, deep, fix")
        else:
            errors.append("模式参数必须是字符串")

        return errors, warnings, sanitized

    def _validate_path_security(self, file_path: str) -> Tuple[List[str], str]:
        """验证路径安全性"""
        errors = []

        # 检查路径长度
        if len(file_path) > self.validation_rules['max_path_length']:
            errors.append(f"路径过长 (>{self.validation_rules['max_path_length']} 字符)")
            return errors, ""

        # 检查危险路径
        normalized_path = os.path.normpath(file_path)
        for forbidden in self.validation_rules['forbidden_paths']:
            if normalized_path.startswith(forbidden):
                errors.append(f"禁止访问的路径: {forbidden}")
                return errors, ""

        # 检查相对路径遍历
        if '..' in normalized_path:
            errors.append("禁止使用相对路径遍历 (..)")
            return errors, ""

        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(normalized_path):
            try:
                normalized_path = os.path.abspath(normalized_path)
            except:
                errors.append("无法解析相对路径")
                return errors, ""

        return errors, normalized_path


class ResponseFormatter:
    """响应格式化器"""

    def __init__(self, config_manager=None):
        """
        初始化响应格式化器

        Args:
            config_manager: 配置管理器实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 获取配置
        try:
            self.config = self.config_manager.get_section('response_formatter') or {}
        except:
            self.config = {}

        # 默认格式配置
        self.default_format = OutputFormat.DETAILED
        self.max_items_per_page = self.config.get('max_items_per_page', 20)
        self.enable_colors = self.config.get('enable_colors', True)
        self.enable_emoji = self.config.get('enable_emoji', True)

        self.logger.info("ResponseFormatter initialized")

    def format_execution_result(self,
                              results: List[ExecutionResult],
                              format_type: OutputFormat = None,
                              plan: Optional[ExecutionPlan] = None) -> FormattedOutput:
        """
        格式化执行结果

        Args:
            results: 执行结果列表
            format_type: 输出格式类型
            plan: 执行计划（可选）

        Returns:
            格式化输出
        """
        if format_type is None:
            format_type = self.default_format

        try:
            if format_type == OutputFormat.SIMPLE:
                content = self._format_simple_results(results, plan)
            elif format_type == OutputFormat.DETAILED:
                content = self._format_detailed_results(results, plan)
            elif format_type == OutputFormat.JSON:
                content = self._format_json_results(results, plan)
            elif format_type == OutputFormat.TABLE:
                content = self._format_table_results(results, plan)
            elif format_type == OutputFormat.MARKDOWN:
                content = self._format_markdown_results(results, plan)
            else:
                content = self._format_detailed_results(results, plan)

            return FormattedOutput(
                content=content,
                format_type=format_type,
                raw_data={
                    'results': [result.to_dict() if hasattr(result, 'to_dict') else str(result) for result in results],
                    'plan': plan.to_dict() if plan and hasattr(plan, 'to_dict') else str(plan) if plan else None,
                    'count': len(results)
                }
            )

        except Exception as e:
            self.logger.error(f"格式化执行结果失败: {e}")
            error_content = f"格式化结果时发生错误: {str(e)}"
            return FormattedOutput(
                content=error_content,
                format_type=format_type,
                raw_data={'error': str(e)}
            )

    def _format_simple_results(self, results: List[ExecutionResult], plan: Optional[ExecutionPlan]) -> str:
        """格式化简洁结果"""
        success_count = len([r for r in results if r.success])
        total_count = len(results)

        lines = []
        if self.enable_emoji:
            lines.append(f"✅ 分析完成: {success_count}/{total_count} 任务成功")
        else:
            lines.append(f"分析完成: {success_count}/{total_count} 任务成功")

        if plan:
            lines.append(f"计划ID: {plan.plan_id}")

        # 显示主要问题
        failed_results = [r for r in results if not r.success]
        if failed_results:
            lines.append(f"发现 {len(failed_results)} 个问题:")
            for i, result in enumerate(failed_results[:5], 1):  # 只显示前5个
                lines.append(f"  {i}. {result.error_message if hasattr(result, 'error_message') else str(result)}")
            if len(failed_results) > 5:
                lines.append(f"  ... 还有 {len(failed_results) - 5} 个问题")

        return "\n".join(lines)

    def _format_detailed_results(self, results: List[ExecutionResult], plan: Optional[ExecutionPlan]) -> str:
        """格式化详细结果"""
        lines = []

        if self.enable_emoji:
            lines.append("=" * 60)
            lines.append("🔍 代码分析详细报告")
            lines.append("=" * 60)
        else:
            lines.append("=" * 60)
            lines.append("代码分析详细报告")
            lines.append("=" * 60)

        # 计划信息
        if plan:
            lines.append(f"📋 分析计划: {plan.plan_id}")
            lines.append(f"🎯 目标路径: {plan.target_path}")
            lines.append(f"📊 总任务数: {len(plan.tasks)}")
            lines.append("")

        # 执行统计
        success_count = len([r for r in results if r.success])
        total_count = len(results)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        lines.append("📈 执行统计:")
        lines.append(f"  • 成功任务: {success_count}/{total_count} ({success_rate:.1f}%)")
        lines.append(f"  • 失败任务: {total_count - success_count}")
        lines.append("")

        # 详细结果
        lines.append("📝 详细结果:")
        for i, result in enumerate(results, 1):
            status_emoji = "✅" if result.success else "❌"
            lines.append(f"{status_emoji} 任务 {i}: {result.task_name if hasattr(result, 'task_name') else 'Unknown'}")

            if result.success:
                if hasattr(result, 'output') and result.output:
                    # 截断过长的输出
                    output = result.output
                    if len(output) > 200:
                        output = output[:200] + "..."
                    lines.append(f"   输出: {output}")
            else:
                error_msg = result.error_message if hasattr(result, 'error_message') else "未知错误"
                lines.append(f"   错误: {error_msg}")

            if hasattr(result, 'execution_time'):
                lines.append(f"   耗时: {result.execution_time:.2f}s")

            lines.append("")

        return "\n".join(lines)

    def _format_json_results(self, results: List[ExecutionResult], plan: Optional[ExecutionPlan]) -> str:
        """格式化JSON结果"""
        import json

        try:
            data = {
                "analysis_summary": {
                    "total_tasks": len(results),
                    "successful_tasks": len([r for r in results if r.success]),
                    "failed_tasks": len([r for r in results if not r.success]),
                    "success_rate": len([r for r in results if r.success]) / len(results) * 100 if results else 0
                },
                "execution_plan": plan.to_dict() if plan and hasattr(plan, 'to_dict') else str(plan) if plan else None,
                "results": []
            }

            for i, result in enumerate(results):
                result_data = {
                    "task_index": i,
                    "task_name": result.task_name if hasattr(result, 'task_name') else f"Task_{i}",
                    "success": result.success,
                    "output": result.output if hasattr(result, 'output') else None,
                    "error_message": result.error_message if hasattr(result, 'error_message') else None,
                    "execution_time": result.execution_time if hasattr(result, 'execution_time') else None
                }
                data["results"].append(result_data)

            return json.dumps(data, indent=2, ensure_ascii=False)

        except (TypeError, ValueError) as e:
            # 如果序列化失败，返回简单的JSON格式
            fallback_data = {
                "error": "JSON序列化失败",
                "message": str(e),
                "total_results": len(results),
                "successful_results": len([r for r in results if r.success])
            }
            return json.dumps(fallback_data, indent=2, ensure_ascii=False)

    def _format_table_results(self, results: List[ExecutionResult], plan: Optional[ExecutionPlan]) -> str:
        """格式化表格结果"""
        lines = []

        # 表格标题
        if plan:
            lines.append(f"分析计划: {plan.plan_id}")
            lines.append(f"目标: {plan.target_path}")
            lines.append("")

        # 表格头部
        lines.append("┌─────────┬────────────────────────┬──────────┬──────────────┐")
        lines.append("│ 任务编号 │ 任务名称               │ 状态     │ 耗时(秒)     │")
        lines.append("├─────────┼────────────────────────┼──────────┼──────────────┤")

        # 表格内容
        for i, result in enumerate(results, 1):
            task_name = (result.task_name if hasattr(result, 'task_name') else f"Task_{i}")[:20]
            status = "✅ 成功" if result.success else "❌ 失败"
            exec_time = f"{result.execution_time:.2f}" if hasattr(result, 'execution_time') else "N/A"

            lines.append(f"│ {i:^7} │ {task_name:<20} │ {status:<8} │ {exec_time:^12} │")

        # 表格底部
        lines.append("└─────────┴────────────────────────┴──────────┴──────────────┘")
        lines.append("")

        # 统计信息
        success_count = len([r for r in results if r.success])
        total_count = len(results)
        lines.append(f"总计: {success_count}/{total_count} 任务成功")

        return "\n".join(lines)

    def _format_markdown_results(self, results: List[ExecutionResult], plan: Optional[ExecutionPlan]) -> str:
        """格式化Markdown结果"""
        lines = []

        # 标题
        lines.append("# 🔍 代码分析报告")
        lines.append("")

        # 计划信息
        if plan:
            lines.append("## 📋 分析信息")
            lines.append(f"- **计划ID**: `{plan.plan_id}`")
            lines.append(f"- **目标路径**: `{plan.target_path}`")
            lines.append(f"- **总任务数**: {len(plan.tasks)}")
            lines.append("")

        # 执行统计
        success_count = len([r for r in results if r.success])
        total_count = len(results)
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        lines.append("## 📊 执行统计")
        lines.append(f"- **成功率**: {success_rate:.1f}% ({success_count}/{total_count})")
        lines.append(f"- **失败数**: {total_count - success_count}")
        lines.append("")

        # 详细结果
        lines.append("## 📝 执行详情")
        for i, result in enumerate(results, 1):
            status = "✅" if result.success else "❌"
            lines.append(f"### {status} 任务 {i}")

            if hasattr(result, 'task_name'):
                lines.append(f"**任务名称**: {result.task_name}")

            if result.success:
                if hasattr(result, 'output') and result.output:
                    lines.append("**输出**:")
                    lines.append("```")
                    lines.append(result.output)
                    lines.append("```")
            else:
                error_msg = result.error_message if hasattr(result, 'error_message') else "未知错误"
                lines.append(f"**错误**: {error_msg}")

            if hasattr(result, 'execution_time'):
                lines.append(f"**执行时间**: {result.execution_time:.2f}秒")

            lines.append("")

        return "\n".join(lines)

    def format_response(self, data: Any, format_type: Union[str, OutputFormat] = None) -> str:
        """
        格式化响应输出

        Args:
            data: 要格式化的数据
            format_type: 输出格式

        Returns:
            格式化后的字符串
        """
        if format_type is None:
            format_type = self.default_format
        elif isinstance(format_type, str):
            format_type = OutputFormat(format_type)

        # 如果是执行结果
        if isinstance(data, list) and data and hasattr(data[0], 'success'):
            return self.format_execution_result(data, format_type).content

        # 如果是字符串，直接返回
        if isinstance(data, str):
            return data

        # 其他类型转为JSON
        try:
            import json
            return json.dumps(data, indent=2, ensure_ascii=False)
        except:
            return str(data)


class UserInteractionHandler:
    """用户交互处理器"""

    def __init__(self, config_manager=None):
        """
        初始化用户交互处理器

        Args:
            config_manager: 配置管理器实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 初始化组件
        self.input_parser = InputParser(config_manager)
        self.parameter_validator = ParameterValidator(config_manager)
        self.response_formatter = ResponseFormatter(config_manager)

        # 中断处理
        self._interrupted = False
        self._interrupt_lock = threading.Lock()

        # 设置信号处理
        self._setup_signal_handlers()

        self.logger.info("UserInteractionHandler initialized")

    def process_user_input(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户输入

        Args:
            user_input: 用户输入

        Returns:
            处理结果
        """
        try:
            # 检查中断状态
            with self._interrupt_lock:
                if self._interrupted:
                    self._interrupted = False
                    return {
                        "success": False,
                        "input_type": InputType.INTERRUPTION.value,
                        "message": "操作已被用户中断",
                        "requires_confirmation": False
                    }

            # 解析输入
            parsed_input = self.input_parser.parse(user_input)

            if not parsed_input.is_valid:
                return {
                    "success": False,
                    "input_type": parsed_input.input_type.value,
                    "errors": parsed_input.validation_errors,
                    "message": "输入解析失败",
                    "requires_confirmation": False
                }

            # 验证参数
            validation_result = self.parameter_validator.validate(parsed_input)

            if not validation_result.is_valid:
                return {
                    "success": False,
                    "input_type": parsed_input.input_type.value,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                    "message": "参数验证失败",
                    "requires_confirmation": False
                }

            # 处理不同类型的输入
            if parsed_input.input_type == InputType.EXIT:
                return self._handle_exit_command(parsed_input)
            elif parsed_input.input_type == InputType.HELP:
                return self._handle_help_command(parsed_input)
            elif parsed_input.input_type == InputType.CONFIRMATION:
                return self._handle_confirmation(parsed_input)
            elif parsed_input.input_type == InputType.COMMAND:
                return self._handle_command(parsed_input)
            elif parsed_input.input_type == InputType.NATURAL_LANGUAGE:
                return self._handle_natural_language(parsed_input, validation_result)
            else:
                return {
                    "success": False,
                    "input_type": parsed_input.input_type.value,
                    "message": "不支持的输入类型",
                    "requires_confirmation": False
                }

        except Exception as e:
            self.logger.error(f"处理用户输入失败: {e}")
            return {
                "success": False,
                "input_type": InputType.UNKNOWN.value,
                "error": str(e),
                "message": "处理输入时发生错误",
                "requires_confirmation": False
            }

    def format_response(self, data: Any, format_type: Union[str, OutputFormat] = None) -> str:
        """
        格式化响应输出

        Args:
            data: 要格式化的数据
            format_type: 输出格式

        Returns:
            格式化后的字符串
        """
        if format_type is None:
            format_type = self.response_formatter.default_format
        elif isinstance(format_type, str):
            format_type = OutputFormat(format_type)

        # 如果是执行结果
        if isinstance(data, list) and data and hasattr(data[0], 'success'):
            return self.response_formatter.format_execution_result(data, format_type).content

        # 如果是字符串，直接返回
        if isinstance(data, str):
            return data

        # 其他类型转为JSON
        try:
            import json
            return json.dumps(data, indent=2, ensure_ascii=False)
        except:
            return str(data)

    def check_interruption(self) -> bool:
        """检查是否被中断"""
        with self._interrupt_lock:
            return self._interrupted

    def reset_interruption(self):
        """重置中断状态"""
        with self._interrupt_lock:
            self._interrupted = False

    def _setup_signal_handlers(self):
        """设置信号处理器"""
        if hasattr(signal, 'SIGINT'):
            def signal_handler(signum, frame):
                with self._interrupt_lock:
                    self._interrupted = True
                print("\n⚠️  检测到中断信号 (Ctrl+C)")

            try:
                signal.signal(signal.SIGINT, signal_handler)
            except ValueError:
                # 在某些环境中可能无法设置信号处理器
                pass

    def _handle_exit_command(self, parsed_input: ParsedInput) -> Dict[str, Any]:
        """处理退出命令"""
        return {
            "success": True,
            "input_type": InputType.EXIT.value,
            "command": "exit",
            "message": "正在退出...",
            "requires_confirmation": True,
            "confirmation_message": "确定要退出吗？(y/n)"
        }

    def _handle_help_command(self, parsed_input: ParsedInput) -> Dict[str, Any]:
        """处理帮助命令"""
        help_text = """
🔍 AI缺陷检测系统 - 使用帮助

📋 支持的命令:
  /help, ?          - 显示此帮助信息
  /exit, quit       - 退出系统
  /mode <mode>      - 切换分析模式 (static/deep/fix)
  /format <type>    - 设置输出格式 (simple/detailed/json/table/markdown)
  /status           - 显示当前状态
  /history          - 显示对话历史
  /clear            - 清空对话历史
  /save <file>      - 保存分析结果
  /export <format>  - 导出分析结果

🎯 分析模式:
  • static  - 静态分析：使用工具进行代码质量检查
  • deep    - 深度分析：使用AI进行智能代码分析
  • fix     - 修复模式：检测问题并提供修复建议

💬 自然语言输入示例:
  • "静态分析 src/ 目录"
  • "深度分析这个文件的架构"
  • "修复代码中的安全问题"

⚠️ 中断操作:
  • 按 Ctrl+C 或输入 /stop 中断当前操作
        """.strip()

        return {
            "success": True,
            "input_type": InputType.HELP.value,
            "command": "help",
            "message": help_text,
            "requires_confirmation": False
        }

    def _handle_confirmation(self, parsed_input: ParsedInput) -> Dict[str, Any]:
        """处理确认输入"""
        response = parsed_input.parameters.get('response', False)

        return {
            "success": True,
            "input_type": InputType.CONFIRMATION.value,
            "command": "confirm",
            "response": response,
            "message": "确认" if response else "取消",
            "requires_confirmation": False
        }

    def _handle_command(self, parsed_input: ParsedInput) -> Dict[str, Any]:
        """处理命令输入"""
        command = parsed_input.command
        params = parsed_input.parameters

        if command == 'mode':
            mode = params.get('mode')
            return {
                "success": True,
                "input_type": InputType.COMMAND.value,
                "command": command,
                "mode": mode,
                "message": f"已切换到 {mode} 分析模式",
                "requires_confirmation": False
            }

        elif command == 'format':
            format_type = params.get('format')
            return {
                "success": True,
                "input_type": InputType.COMMAND.value,
                "command": command,
                "format": format_type,
                "message": f"已设置输出格式为 {format_type}",
                "requires_confirmation": False
            }

        elif command == 'status':
            return {
                "success": True,
                "input_type": InputType.COMMAND.value,
                "command": command,
                "message": "系统运行正常",
                "requires_confirmation": False
            }

        elif command == 'clear':
            return {
                "success": True,
                "input_type": InputType.COMMAND.value,
                "command": command,
                "message": "已清空对话历史",
                "requires_confirmation": False
            }

        else:
            return {
                "success": False,
                "input_type": InputType.COMMAND.value,
                "command": command,
                "message": f"未知命令: {command}",
                "requires_confirmation": False
            }

    def _handle_natural_language(self, parsed_input: ParsedInput, validation_result: ValidationResult) -> Dict[str, Any]:
        """处理自然语言输入"""
        params = validation_result.sanitized_params

        return {
            "success": True,
            "input_type": InputType.NATURAL_LANGUAGE.value,
            "text": params.get('text', ''),
            "keywords": params.get('keywords', []),
            "file_paths": params.get('file_paths', []),
            "mode_hints": params.get('mode_hints', []),
            "warnings": validation_result.warnings,
            "message": "已解析自然语言输入",
            "requires_confirmation": False
        }