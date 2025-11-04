"""
日志系统模块
实现统一的日志记录系统，支持不同级别日志输出和文件轮转
支持工作流特定的日志功能
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger as loguru_logger
from .config import get_config_manager


class WorkflowLogger:
    """工作流日志管理器 - 专门用于工作流相关日志"""

    def __init__(self, session_id: str, base_logger=None):
        """
        初始化工作流日志管理器

        Args:
            session_id: 工作流会话ID
            base_logger: 基础日志管理器
        """
        self.session_id = session_id
        self.base_logger = base_logger or get_logger()
        self.workflow_logs = []

    def log_workflow_transition(self, from_node: str, to_node: str,
                               reason: str = "", metadata: Dict[str, Any] = None):
        """
        记录工作流状态转换

        Args:
            from_node: 源节点
            to_node: 目标节点
            reason: 转换原因
            metadata: 转换元数据
        """
        log_data = {
            "session_id": self.session_id,
            "event_type": "workflow_transition",
            "from_node": from_node,
            "to_node": to_node,
            "reason": reason,
            "metadata": metadata or {},
            "timestamp": loguru_logger._core.now
        }

        self.workflow_logs.append(log_data)
        self.base_logger.info(f"工作流转换: {from_node} → {to_node} - {reason}")

    def log_user_decision(self, node: str, decision_type: str,
                         decision_id: str, details: Dict[str, Any]):
        """
        记录用户决策

        Args:
            node: 决策节点
            decision_type: 决策类型
            decision_id: 决策ID
            details: 决策详情
        """
        log_data = {
            "session_id": self.session_id,
            "event_type": "user_decision",
            "node": node,
            "decision_type": decision_type,
            "decision_id": decision_id,
            "details": details,
            "timestamp": loguru_logger._core.now
        }

        self.workflow_logs.append(log_data)
        self.base_logger.info(f"用户决策 [{node}]: {decision_type} - {decision_id}")

    def log_ai_interaction(self, interaction_type: str, node: str,
                          request_data: Dict[str, Any],
                          response_data: Dict[str, Any] = None):
        """
        记录AI交互

        Args:
            interaction_type: 交互类型
            node: 工作流节点
            request_data: 请求数据
            response_data: 响应数据
        """
        log_data = {
            "session_id": self.session_id,
            "event_type": "ai_interaction",
            "interaction_type": interaction_type,
            "node": node,
            "request_data": request_data,
            "response_data": response_data,
            "timestamp": loguru_logger._core.now
        }

        self.workflow_logs.append(log_data)
        self.base_logger.info(f"AI交互 [{node}]: {interaction_type}")

    def log_fix_execution(self, operation_id: str, file_path: str,
                          operation_type: str, success: bool,
                          details: Dict[str, Any] = None):
        """
        记录修复执行

        Args:
            operation_id: 操作ID
            file_path: 文件路径
            operation_type: 操作类型
            success: 执行是否成功
            details: 执行详情
        """
        log_data = {
            "session_id": self.session_id,
            "event_type": "fix_execution",
            "operation_id": operation_id,
            "file_path": file_path,
            "operation_type": operation_type,
            "success": success,
            "details": details or {},
            "timestamp": loguru_logger._core.now
        }

        self.workflow_logs.append(log_data)
        status = "成功" if success else "失败"
        self.base_logger.info(f"修复执行 [{operation_id}]: {operation_type} - {status}")

    def log_error(self, error_type: str, node: str, error_message: str,
                   details: Dict[str, Any] = None):
        """
        记录工作流错误

        Args:
            error_type: 错误类型
            node: 发生错误的节点
            error_message: 错误消息
            details: 错误详情
        """
        log_data = {
            "session_id": self.session_id,
            "event_type": "error",
            "error_type": error_type,
            "node": node,
            "error_message": error_message,
            "details": details or {},
            "timestamp": loguru_logger._core.now
        }

        self.workflow_logs.append(log_data)
        self.base_logger.error(f"工作流错误 [{node}]: {error_type} - {error_message}")

    def get_workflow_logs(self) -> list:
        """获取工作流日志"""
        return self.workflow_logs.copy()

    def export_workflow_logs(self, file_path: str) -> bool:
        """
        导出工作流日志到文件

        Args:
            file_path: 导出文件路径

        Returns:
            bool: 导出是否成功
        """
        try:
            import json
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.workflow_logs, f, ensure_ascii=False, indent=2)
            self.base_logger.info(f"工作流日志已导出到: {file_path}")
            return True
        except Exception as e:
            self.base_logger.error(f"导出工作流日志失败: {e}")
            return False


class Logger:
    """统一日志管理器"""

    def __init__(self, config_manager=None):
        """
        初始化日志管理器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self._logger = None
        self._setup_logger()

    def _setup_logger(self):
        """设置日志系统"""
        # 获取日志配置
        log_config = self.config_manager.get_section('logging')

        # 移除默认的处理器
        loguru_logger.remove()

        # 设置日志级别
        level = log_config.get('level', 'INFO')

        # 设置日志格式
        format_str = log_config.get('format',
            "{time:YYYY-MM-DD HH:mm:ss} | {level} | {module} | {message}")

        # 确保日志目录存在
        log_file = log_config.get('file_path', 'logs/app.log')
        log_dir = Path(log_file).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        # 添加文件处理器
        rotation = log_config.get('max_size', '10 MB')
        retention = log_config.get('backup_count', 5)

        # 添加文件处理器
        loguru_logger.add(
            log_file,
            level=level,
            format=format_str,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8"
        )

        # 添加控制台处理器（如果启用）
        if log_config.get('enable_console', True):
            console_format = log_config.get('console_format', format_str)
            loguru_logger.add(
                sys.stdout,
                level=level,
                format=console_format,
                colorize=True
            )

        self._logger = loguru_logger

    def debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs):
        """记录ERROR级别日志"""
        self._logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs):
        """记录CRITICAL级别日志"""
        self._logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs):
        """记录异常信息"""
        self._logger.exception(message, **kwargs)

    def log_api_request(self, api_type: str, endpoint: str, status: str,
                       response_time: float, **kwargs):
        """
        记录API请求日志

        Args:
            api_type: API类型 (LLM, static_analysis等)
            endpoint: API端点
            status: 请求状态
            response_time: 响应时间(秒)
        """
        self.info(
            f"API Request - {api_type} | {endpoint} | {status} | {response_time:.2f}s",
            api_type=api_type,
            endpoint=endpoint,
            status=status,
            response_time=response_time,
            **kwargs
        )

    def log_file_operation(self, operation: str, file_path: str,
                          result: str, **kwargs):
        """
        记录文件操作日志

        Args:
            operation: 操作类型 (read, write, delete等)
            file_path: 文件路径
            result: 操作结果
        """
        self.info(
            f"File Operation - {operation} | {file_path} | {result}",
            operation=operation,
            file_path=file_path,
            result=result,
            **kwargs
        )

    def log_analysis_result(self, analysis_type: str, file_count: int,
                           issue_count: int, duration: float, **kwargs):
        """
        记录分析结果日志

        Args:
            analysis_type: 分析类型 (static, deep, fix等)
            file_count: 分析的文件数量
            issue_count: 发现的问题数量
            duration: 分析耗时(秒)
        """
        self.info(
            f"Analysis Complete - {analysis_type} | {file_count} files | "
            f"{issue_count} issues | {duration:.2f}s",
            analysis_type=analysis_type,
            file_count=file_count,
            issue_count=issue_count,
            duration=duration,
            **kwargs
        )

    def log_user_action(self, action: str, user_input: str,
                       result: str, **kwargs):
        """
        记录用户操作日志

        Args:
            action: 操作类型
            user_input: 用户输入
            result: 操作结果
        """
        self.info(
            f"User Action - {action} | Input: {user_input[:100]} | {result}",
            action=action,
            user_input=user_input,
            result=result,
            **kwargs
        )

    def get_logger(self):
        """获取底层logger实例"""
        return self._logger

    def set_level(self, level: str):
        """
        动态设置日志级别

        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # 移除现有处理器并重新配置
        loguru_logger.remove()

        # 更新配置
        log_config = self.config_manager.get_section('logging')
        log_config['level'] = level

        # 重新设置
        self._setup_logger()

    def add_file_handler(self, file_path: str, level: str = None,
                        format_str: str = None):
        """
        添加额外的文件处理器

        Args:
            file_path: 日志文件路径
            level: 日志级别
            format_str: 日志格式
        """
        log_config = self.config_manager.get_section('logging')

        loguru_logger.add(
            file_path,
            level=level or log_config.get('level', 'INFO'),
            format=format_str or log_config.get('format',
                "{time:YYYY-MM-DD HH:mm:ss} | {level} | {module} | {message}"),
            rotation=log_config.get('max_size', '10 MB'),
            retention=log_config.get('backup_count', 5),
            encoding="utf-8"
        )

    # 项目分析工作流专门的日志方法
    def log_project_analysis_start(self, project_path: str, analysis_mode: str, **kwargs):
        """
        记录项目分析开始

        Args:
            project_path: 项目路径
            analysis_mode: 分析模式
        """
        self.info(
            f"Project Analysis Started | Path: {project_path} | Mode: {analysis_mode}",
            channel="project_analysis",
            event_type="analysis_start",
            project_path=project_path,
            analysis_mode=analysis_mode,
            **kwargs
        )

    def log_project_analysis_complete(self, project_path: str, analysis_id: str,
                                    duration: float, files_analyzed: int,
                                    issues_found: int, **kwargs):
        """
        记录项目分析完成

        Args:
            project_path: 项目路径
            analysis_id: 分析ID
            duration: 分析耗时（秒）
            files_analyzed: 分析的文件数量
            issues_found: 发现的问题数量
        """
        self.info(
            f"Project Analysis Complete | {project_path} | ID: {analysis_id} | "
            f"Duration: {duration:.2f}s | Files: {files_analyzed} | Issues: {issues_found}",
            channel="project_analysis",
            event_type="analysis_complete",
            project_path=project_path,
            analysis_id=analysis_id,
            duration=duration,
            files_analyzed=files_analyzed,
            issues_found=issues_found,
            **kwargs
        )

    def log_analysis_phase_start(self, phase: str, analysis_id: str, **kwargs):
        """
        记录分析阶段开始

        Args:
            phase: 阶段名称
            analysis_id: 分析ID
        """
        self.info(
            f"Analysis Phase Started | {phase} | ID: {analysis_id}",
            channel="project_analysis",
            event_type="phase_start",
            phase=phase,
            analysis_id=analysis_id,
            **kwargs
        )

    def log_analysis_phase_complete(self, phase: str, analysis_id: str,
                                  duration: float, result_summary: str = "", **kwargs):
        """
        记录分析阶段完成

        Args:
            phase: 阶段名称
            analysis_id: 分析ID
            duration: 阶段耗时（秒）
            result_summary: 结果摘要
        """
        self.info(
            f"Analysis Phase Complete | {phase} | ID: {analysis_id} | "
            f"Duration: {duration:.2f}s | {result_summary}",
            channel="project_analysis",
            event_type="phase_complete",
            phase=phase,
            analysis_id=analysis_id,
            duration=duration,
            result_summary=result_summary,
            **kwargs
        )

    def log_file_selection(self, total_files: int, selected_files: int,
                          selection_strategy: str, **kwargs):
        """
        记录文件选择过程

        Args:
            total_files: 总文件数
            selected_files: 选择的文件数
            selection_strategy: 选择策略
        """
        self.info(
            f"File Selection | Total: {total_files} | Selected: {selected_files} | "
            f"Strategy: {selection_strategy}",
            channel="project_analysis",
            event_type="file_selection",
            total_files=total_files,
            selected_files=selected_files,
            selection_strategy=selection_strategy,
            **kwargs
        )

    def log_token_usage(self, analysis_id: str, phase: str, tokens_used: int,
                       model: str, cost_estimate: float = 0.0, **kwargs):
        """
        记录Token使用情况

        Args:
            analysis_id: 分析ID
            phase: 分析阶段
            tokens_used: 使用的token数量
            model: 使用的模型
            cost_estimate: 成本估算
        """
        self.info(
            f"Token Usage | ID: {analysis_id} | Phase: {phase} | "
            f"Tokens: {tokens_used} | Model: {model} | Cost: ${cost_estimate:.4f}",
            channel="project_analysis",
            event_type="token_usage",
            analysis_id=analysis_id,
            phase=phase,
            tokens_used=tokens_used,
            model=model,
            cost_estimate=cost_estimate,
            **kwargs
        )

    def log_progress_update(self, analysis_id: str, current_step: int,
                          total_steps: int, step_description: str,
                          progress_percent: float, **kwargs):
        """
        记录进度更新

        Args:
            analysis_id: 分析ID
            current_step: 当前步骤
            total_steps: 总步骤数
            step_description: 步骤描述
            progress_percent: 进度百分比
        """
        self.info(
            f"Progress Update | ID: {analysis_id} | Step {current_step}/{total_steps} | "
            f"{step_description} | {progress_percent:.1f}%",
            channel="project_analysis",
            event_type="progress_update",
            analysis_id=analysis_id,
            current_step=current_step,
            total_steps=total_steps,
            step_description=step_description,
            progress_percent=progress_percent,
            **kwargs
        )

    def log_fix_generation(self, file_path: str, issues_count: int,
                          fixes_generated: int, **kwargs):
        """
        记录修复建议生成

        Args:
            file_path: 文件路径
            issues_count: 问题数量
            fixes_generated: 生成的修复建议数量
        """
        self.info(
            f"Fix Generation | {file_path} | Issues: {issues_count} | Fixes: {fixes_generated}",
            channel="project_analysis",
            event_type="fix_generation",
            file_path=file_path,
            issues_count=issues_count,
            fixes_generated=fixes_generated,
            **kwargs
        )

    def log_fix_application(self, file_path: str, fix_id: str,
                           success: bool, error_message: str = "", **kwargs):
        """
        记录修复应用

        Args:
            file_path: 文件路径
            fix_id: 修复ID
            success: 是否成功
            error_message: 错误信息
        """
        status = "SUCCESS" if success else "FAILED"
        message = f"Fix Application | {file_path} | Fix: {fix_id} | Status: {status}"
        if error_message:
            message += f" | Error: {error_message}"

        log_method = self.info if success else self.error
        log_method(
            message,
            channel="project_analysis",
            event_type="fix_application",
            file_path=file_path,
            fix_id=fix_id,
            success=success,
            error_message=error_message,
            **kwargs
        )

    def log_performance_metrics(self, analysis_id: str, phase: str,
                              metric_name: str, metric_value: float,
                              unit: str = "", **kwargs):
        """
        记录性能指标

        Args:
            analysis_id: 分析ID
            phase: 分析阶段
            metric_name: 指标名称
            metric_value: 指标值
            unit: 单位
        """
        unit_str = f" {unit}" if unit else ""
        self.debug(
            f"Performance Metric | ID: {analysis_id} | Phase: {phase} | "
            f"{metric_name}: {metric_value}{unit_str}",
            channel="project_analysis",
            event_type="performance_metric",
            analysis_id=analysis_id,
            phase=phase,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=unit,
            **kwargs
        )

    def log_error_with_context(self, analysis_id: str, phase: str,
                              error_type: str, error_message: str,
                              context: Dict[str, Any] = None, **kwargs):
        """
        记录带上下文的错误信息

        Args:
            analysis_id: 分析ID
            phase: 分析阶段
            error_type: 错误类型
            error_message: 错误信息
            context: 上下文信息
        """
        context_str = f" | Context: {context}" if context else ""
        self.error(
            f"Analysis Error | ID: {analysis_id} | Phase: {phase} | "
            f"Type: {error_type} | Message: {error_message}{context_str}",
            channel="project_analysis",
            event_type="error",
            analysis_id=analysis_id,
            phase=phase,
            error_type=error_type,
            error_message=error_message,
            context=context or {},
            **kwargs
        )

    def log_cost_summary(self, analysis_id: str, total_tokens: int,
                        total_cost: float, token_breakdown: Dict[str, int] = None, **kwargs):
        """
        记录成本汇总

        Args:
            analysis_id: 分析ID
            total_tokens: 总token数
            total_cost: 总成本
            token_breakdown: token使用明细
        """
        breakdown_str = ""
        if token_breakdown:
            breakdown_parts = [f"{model}: {tokens}" for model, tokens in token_breakdown.items()]
            breakdown_str = f" | Breakdown: {', '.join(breakdown_parts)}"

        self.info(
            f"Cost Summary | ID: {analysis_id} | Total Tokens: {total_tokens} | "
            f"Total Cost: ${total_cost:.4f}{breakdown_str}",
            channel="project_analysis",
            event_type="cost_summary",
            analysis_id=analysis_id,
            total_tokens=total_tokens,
            total_cost=total_cost,
            token_breakdown=token_breakdown or {},
            **kwargs
        )


# 全局日志器实例
_logger_instance: Optional[Logger] = None


def get_logger() -> Logger:
    """
    获取全局日志器实例

    Returns:
        日志器实例
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = Logger()
    return _logger_instance


def setup_logging(config_manager=None):
    """
    设置日志系统

    Args:
        config_manager: 配置管理器实例
    """
    global _logger_instance
    _logger_instance = Logger(config_manager)


# 便捷函数
def debug(message: str, **kwargs):
    """记录DEBUG级别日志"""
    get_logger().debug(message, **kwargs)


def info(message: str, **kwargs):
    """记录INFO级别日志"""
    get_logger().info(message, **kwargs)


def warning(message: str, **kwargs):
    """记录WARNING级别日志"""
    get_logger().warning(message, **kwargs)


def error(message: str, **kwargs):
    """记录ERROR级别日志"""
    get_logger().error(message, **kwargs)


def critical(message: str, **kwargs):
    """记录CRITICAL级别日志"""
    get_logger().critical(message, **kwargs)


def exception(message: str, **kwargs):
    """记录异常信息"""
    get_logger().exception(message, **kwargs)