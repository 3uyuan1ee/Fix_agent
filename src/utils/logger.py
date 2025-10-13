"""
日志系统模块
实现统一的日志记录系统，支持不同级别日志输出和文件轮转
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger as loguru_logger
from .config import get_config_manager


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