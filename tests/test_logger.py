"""
日志系统模块单元测试
"""

import pytest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.utils.logger import Logger, get_logger, setup_logging
from src.utils.config import ConfigManager


class TestLogger:
    """日志管理器测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试配置
        self.test_config = {
            'app': {'name': 'TestApp'},
            'logging': {
                'level': 'INFO',
                'format': "{time:YYYY-MM-DD HH:mm:ss} | {level} | {module} | {message}",
                'file_path': f'{self.temp_dir}/test.log',
                'max_size': '10 MB',
                'backup_count': 5,
                'enable_console': True
            },
            'llm': {
                'default_provider': 'openai',
                'openai': {'api_key': 'test-key'}
            },
            'static_analysis': {'enabled_tools': ['ast']}
        }

        config_path = Path(self.temp_dir) / "default.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)

        self.config_manager = ConfigManager(self.temp_dir)
        self.config_manager.load_config()

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_logger_initialization_success(self):
        """测试日志器初始化成功"""
        logger = Logger(self.config_manager)

        assert logger is not None
        assert logger._logger is not None
        assert logger.config_manager == self.config_manager

    def test_logger_with_default_config(self):
        """测试使用默认配置创建日志器"""
        with patch('src.utils.logger.get_config_manager') as mock_get_config:
            mock_config_manager = MagicMock()
            mock_config_manager.get_section.return_value = {
                'level': 'DEBUG',
                'file_path': 'logs/test.log',
                'enable_console': True
            }
            mock_get_config.return_value = mock_config_manager

            logger = Logger()

            assert logger is not None
            mock_get_config.assert_called_once()

    def test_log_levels_output(self):
        """测试不同日志级别输出"""
        logger = Logger(self.config_manager)

        # 这些操作不应该抛出异常
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_log_with_extra_fields(self):
        """测试带额外字段的日志输出"""
        logger = Logger(self.config_manager)

        # 测试带额外参数的日志
        logger.info("Test message", user_id="123", action="test")

    def test_log_api_request(self):
        """测试API请求日志记录"""
        logger = Logger(self.config_manager)

        # 不应该抛出异常
        logger.log_api_request(
            api_type="LLM",
            endpoint="/chat/completions",
            status="success",
            response_time=1.5
        )

    def test_log_file_operation(self):
        """测试文件操作日志记录"""
        logger = Logger(self.config_manager)

        # 不应该抛出异常
        logger.log_file_operation(
            operation="read",
            file_path="/test/file.py",
            result="success"
        )

    def test_log_analysis_result(self):
        """测试分析结果日志记录"""
        logger = Logger(self.config_manager)

        # 不应该抛出异常
        logger.log_analysis_result(
            analysis_type="static",
            file_count=10,
            issue_count=5,
            duration=2.3
        )

    def test_log_user_action(self):
        """测试用户操作日志记录"""
        logger = Logger(self.config_manager)

        # 不应该抛出异常
        logger.log_user_action(
            action="analyze",
            user_input="Analyze this code",
            result="completed"
        )

    def test_set_level_dynamically(self):
        """测试动态设置日志级别"""
        logger = Logger(self.config_manager)

        # 设置不同级别
        logger.set_level("DEBUG")
        logger.set_level("WARNING")
        logger.set_level("ERROR")

    def test_add_file_handler(self):
        """测试添加额外文件处理器"""
        logger = Logger(self.config_manager)

        extra_log_file = os.path.join(self.temp_dir, "extra.log")

        # 不应该抛出异常
        logger.add_file_handler(
            file_path=extra_log_file,
            level="DEBUG",
            format_str="{level} | {message}"
        )

    def test_get_logger_instance(self):
        """测试获取日志器实例"""
        logger = Logger(self.config_manager)
        instance = logger.get_logger()

        assert instance is not None

    def test_log_exception(self):
        """测试异常日志记录"""
        logger = Logger(self.config_manager)

        try:
            raise ValueError("Test exception")
        except ValueError:
            # 不应该抛出异常
            logger.exception("Exception occurred")


class TestGlobalLoggerFunctions:
    """全局日志器函数测试"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()

        # 创建测试配置
        self.test_config = {
            'app': {'name': 'TestApp'},
            'logging': {
                'level': 'INFO',
                'file_path': f'{self.temp_dir}/test.log',
                'enable_console': False  # 避免控制台输出干扰测试
            },
            'llm': {
                'default_provider': 'openai',
                'openai': {'api_key': 'test-key'}
            },
            'static_analysis': {'enabled_tools': ['ast']}
        }

        config_path = Path(self.temp_dir) / "default.yaml"
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.test_config, f)

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_logger_singleton(self):
        """测试全局日志器单例"""
        with patch('src.utils.logger.get_config_manager') as mock_get_config:
            mock_config_manager = MagicMock()
            mock_config_manager.get_section.return_value = {
                'level': 'INFO',
                'file_path': 'logs/test.log',
                'enable_console': False
            }
            mock_get_config.return_value = mock_config_manager

            # 多次调用应该返回同一实例
            logger1 = get_logger()
            logger2 = get_logger()

            assert logger1 is logger2

    def test_setup_logging_function(self):
        """测试setup_logging函数"""
        with patch('src.utils.logger.get_config_manager') as mock_get_config:
            mock_config_manager = MagicMock()
            mock_config_manager.get_section.return_value = {
                'level': 'DEBUG',
                'file_path': 'logs/setup_test.log',
                'enable_console': False
            }
            mock_get_config.return_value = mock_config_manager

            # 不应该抛出异常
            setup_logging()

            # 验证配置管理器被调用
            mock_get_config.assert_called_once()

    def test_convenience_logging_functions(self):
        """测试便捷日志函数"""
        with patch('src.utils.logger.get_logger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            # 调用便捷函数
            from src.utils.logger import debug, info, warning, error, critical, exception

            debug("Debug message")
            info("Info message")
            warning("Warning message")
            error("Error message")
            critical("Critical message")
            exception("Exception message")

            # 验证底层日志器被调用
            assert mock_logger.debug.called
            assert mock_logger.info.called
            assert mock_logger.warning.called
            assert mock_logger.error.called
            assert mock_logger.critical.called
            assert mock_logger.exception.called

    def test_log_file_creation(self):
        """测试日志文件创建"""
        with patch('src.utils.logger.get_config_manager') as mock_get_config:
            mock_config_manager = MagicMock()
            mock_config_manager.get_section.return_value = {
                'level': 'INFO',
                'format': "{time} | {level} | {message}",
                'file_path': f'{self.temp_dir}/integration_test.log',
                'max_size': '1 MB',
                'backup_count': 3,
                'enable_console': False
            }
            mock_get_config.return_value = mock_config_manager

            logger = Logger(mock_config_manager)
            logger.info("Test message")

            # 验证日志文件被创建
            log_file = Path(self.temp_dir) / "integration_test.log"
            assert log_file.exists()

    def test_log_file_rotation_config(self):
        """测试日志轮转配置"""
        with patch('src.utils.logger.get_config_manager') as mock_get_config:
            mock_config_manager = MagicMock()
            mock_config_manager.get_section.return_value = {
                'level': 'INFO',
                'file_path': f'{self.temp_dir}/rotation_test.log',
                'max_size': '1 KB',  # 小文件大小便于测试
                'backup_count': 2,
                'enable_console': False
            }
            mock_get_config.return_value = mock_config_manager

            logger = Logger(mock_config_manager)

            # 验证日志器配置成功
            assert logger is not None