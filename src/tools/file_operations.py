"""
文件操作工具模块
实现项目文件扫描、读取和基础操作功能
集成PathResolver以提供统一的路径解析功能
"""

import os
import shutil
import chardet
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from ..utils.path_resolver import get_path_resolver


class FileOperationError(Exception):
    """文件操作异常"""
    pass


class FileOperations:
    """文件操作工具类"""

    def __init__(self, config_manager=None):
        """
        初始化文件操作工具

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 初始化PathResolver
        self.path_resolver = get_path_resolver()

        # 获取配置
        file_ops_config = self.config_manager.get_section('file_operations')
        self.max_file_size = file_ops_config.get('max_file_size', 10 * 1024 * 1024)  # 10MB
        security_config = self.config_manager.get_section('security')
        self.backup_dir = security_config.get('backup_dir', '.aiderector_backups')

    def scan_directory(self, directory: Union[str, Path],
                      recursive: bool = True,
                      extensions: Optional[List[str]] = None,
                      exclude_patterns: Optional[List[str]] = None) -> List[str]:
        """
        扫描目录获取文件列表

        Args:
            directory: 目录路径
            recursive: 是否递归扫描
            extensions: 文件扩展名过滤列表
            exclude_patterns: 排除模式列表

        Returns:
            文件路径列表

        Raises:
            FileOperationError: 目录不存在或访问失败
        """
        # 使用PathResolver解析目录路径
        resolved_directory = self.path_resolver.resolve_path(directory)
        if not resolved_directory:
            raise FileOperationError(f"Cannot resolve directory path: {directory}")

        directory = resolved_directory

        # 检查目录是否存在
        if not directory.exists():
            raise FileOperationError(f"Directory does not exist: {directory}")

        if not directory.is_dir():
            raise FileOperationError(f"Path is not a directory: {directory}")

        try:
            files = []

            # 选择扫描方式
            if recursive:
                pattern = "**/*"
                file_paths = directory.glob(pattern)
            else:
                pattern = "*"
                file_paths = directory.glob(pattern)

            for file_path in file_paths:
                if not file_path.is_file():
                    continue

                # 检查扩展名过滤
                if extensions:
                    if file_path.suffix.lower() not in [ext.lower() for ext in extensions]:
                        continue

                # 检查排除模式
                if exclude_patterns:
                    should_exclude = False
                    for pattern in exclude_patterns:
                        if pattern in str(file_path):
                            should_exclude = True
                            break
                    if should_exclude:
                        continue

                files.append(str(file_path))

            self.logger.info(f"Scanned directory {directory}, found {len(files)} files")
            return files

        except Exception as e:
            raise FileOperationError(f"Failed to scan directory {directory}: {e}")

    def read_file(self, file_path: Union[str, Path],
                 encoding: str = "utf-8",
                 fallback_encodings: Optional[List[str]] = None,
                 streaming: bool = False) -> str:
        """
        安全读取文件内容

        Args:
            file_path: 文件路径
            encoding: 首选编码
            fallback_encodings: 备用编码列表
            streaming: 是否流式读取（用于大文件）

        Returns:
            文件内容

        Raises:
            FileOperationError: 文件读取失败
        """
        # 使用PathResolver解析文件路径
        resolved_file_path = self.path_resolver.resolve_path(file_path)
        if not resolved_file_path:
            raise FileOperationError(f"Cannot resolve file path: {file_path}")

        file_path = resolved_file_path

        # 检查文件是否存在
        if not file_path.exists():
            raise FileOperationError(f"File does not exist: {file_path}")

        if not file_path.is_file():
            raise FileOperationError(f"Path is not a file: {file_path}")

        # 检查文件大小
        file_size = file_path.stat().st_size
        if file_size > self.max_file_size and not streaming:
            self.logger.warning(f"File {file_path} is large ({file_size} bytes), enabling streaming mode")
            streaming = True

        try:
            if streaming:
                return self._read_file_streaming(file_path, encoding, fallback_encodings)
            else:
                return self._read_file_normal(file_path, encoding, fallback_encodings)

        except Exception as e:
            raise FileOperationError(f"Failed to read file {file_path}: {e}")

    def _read_file_normal(self, file_path: Path, encoding: str,
                         fallback_encodings: Optional[List[str]]) -> str:
        """正常模式读取文件"""
        if fallback_encodings is None:
            fallback_encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']

        # 首先尝试指定编码
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            self.logger.debug(f"Successfully read file {file_path} with encoding {encoding}")
            return content
        except UnicodeDecodeError:
            pass

        # 尝试备用编码
        for fallback_encoding in fallback_encodings:
            if fallback_encoding == encoding:
                continue
            try:
                with open(file_path, 'r', encoding=fallback_encoding) as f:
                    content = f.read()
                self.logger.debug(f"Successfully read file {file_path} with fallback encoding {fallback_encoding}")
                return content
            except UnicodeDecodeError:
                continue

        # 最后尝试自动检测编码
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()

            detected = chardet.detect(raw_data)
            if detected['encoding']:
                with open(file_path, 'r', encoding=detected['encoding']) as f:
                    content = f.read()
                self.logger.debug(f"Successfully read file {file_path} with detected encoding {detected['encoding']}")
                return content
        except Exception:
            pass

        raise FileOperationError(f"Unable to decode file {file_path} with any encoding")

    def _read_file_streaming(self, file_path: Path, encoding: str,
                            fallback_encodings: Optional[List[str]]) -> str:
        """流式模式读取大文件"""
        if fallback_encodings is None:
            fallback_encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']

        # 测试编码
        test_encoding = encoding
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read(1024)  # 读取一小块测试编码
        except UnicodeDecodeError:
            # 找到可用编码
            for fallback_encoding in fallback_encodings:
                try:
                    with open(file_path, 'r', encoding=fallback_encoding) as f:
                        f.read(1024)
                    test_encoding = fallback_encoding
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # 尝试自动检测
                with open(file_path, 'rb') as f:
                    raw_data = f.read(8192)
                detected = chardet.detect(raw_data)
                if detected['encoding']:
                    test_encoding = detected['encoding']
                else:
                    raise FileOperationError(f"Unable to determine encoding for large file {file_path}")

        # 流式读取
        content_chunks = []
        with open(file_path, 'r', encoding=test_encoding) as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                content_chunks.append(chunk)

        self.logger.debug(f"Successfully read large file {file_path} with streaming mode")
        return ''.join(content_chunks)

    def write_file(self, file_path: Union[str, Path],
                   content: str,
                   encoding: str = "utf-8",
                   create_directories: bool = True) -> None:
        """
        写入文件内容

        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 文件编码
            create_directories: 是否自动创建目录

        Raises:
            FileOperationError: 文件写入失败
        """
        file_path = Path(file_path)

        try:
            # 创建目录（如果需要）
            if create_directories:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)

            self.logger.debug(f"Successfully wrote file {file_path}")

        except Exception as e:
            raise FileOperationError(f"Failed to write file {file_path}: {e}")

    def search_files(self, directory: Union[str, Path],
                    pattern: Optional[str] = None,
                    content_pattern: Optional[str] = None,
                    extensions: Optional[List[str]] = None,
                    recursive: bool = True) -> List[str]:
        """
        搜索文件

        Args:
            directory: 搜索目录
            pattern: 文件名模式
            content_pattern: 文件内容模式
            extensions: 文件扩展名过滤
            recursive: 是否递归搜索

        Returns:
            匹配的文件路径列表
        """
        files = self.scan_directory(directory, recursive=recursive, extensions=extensions)
        matching_files = []

        for file_path in files:
            file_path_obj = Path(file_path)

            # 检查文件名模式
            if pattern:
                if pattern.lower() not in file_path_obj.name.lower():
                    continue

            # 检查文件内容模式
            if content_pattern:
                try:
                    content = self.read_file(file_path_obj)
                    if content_pattern.lower() not in content.lower():
                        continue
                except FileOperationError:
                    # 跳过无法读取的文件
                    continue

            matching_files.append(file_path)

        return matching_files

    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            文件信息字典
        """
        # 使用PathResolver解析文件路径
        resolved_file_path = self.path_resolver.resolve_path(file_path)
        if not resolved_file_path:
            raise FileOperationError(f"Cannot resolve file path: {file_path}")

        file_path = resolved_file_path

        if not file_path.exists():
            raise FileOperationError(f"File does not exist: {file_path}")

        stat = file_path.stat()

        info = {
            'path': str(file_path),
            'name': file_path.name,
            'size': stat.st_size,
            'modified_time': stat.st_mtime,
            'is_file': file_path.is_file(),
            'is_directory': file_path.is_dir(),
            'extension': file_path.suffix if file_path.is_file() else None,
            'absolute_path': str(file_path.absolute())
        }

        # 如果是文件，尝试检测编码
        if info['is_file'] and info['size'] > 0:
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read(8192)
                detected = chardet.detect(raw_data)
                info['encoding'] = detected.get('encoding')
                info['confidence'] = detected.get('confidence')
            except Exception:
                info['encoding'] = None
                info['confidence'] = None

        return info

    def is_text_file(self, file_path: Union[str, Path]) -> bool:
        """
        判断是否为文本文件

        Args:
            file_path: 文件路径

        Returns:
            是否为文本文件
        """
        try:
            file_path = Path(file_path)

            if not file_path.is_file():
                return False

            # 读取文件头部检测
            with open(file_path, 'rb') as f:
                raw_data = f.read(8192)

            # 如果是空文件，认为是文本文件
            if not raw_data:
                return True

            # 首先检查是否包含null字节（明确是二进制文件的特征）
            if b'\x00' in raw_data:
                return False

            # 检查是否包含太多控制字符（二进制文件特征）
            text_chars = len([c for c in raw_data if 32 <= c <= 126 or c in [9, 10, 13]])
            text_ratio = text_chars / len(raw_data) if raw_data else 0

            # 如果文本字符比例低于70%，认为是二进制文件
            if text_ratio < 0.7:
                return False

            # 使用chardet检测
            result = chardet.detect(raw_data)

            # 如果检测置信度高且编码为常见文本编码，认为是文本文件
            text_encodings = ['utf-8', 'ascii', 'gb2312', 'gbk', 'big5', 'latin-1']

            if result['confidence'] > 0.7 and result['encoding'] in text_encodings:
                return True

            return True

        except Exception:
            return False

    def get_relative_path(self, file_path: Union[str, Path],
                         base_path: Union[str, Path]) -> str:
        """
        获取相对路径

        Args:
            file_path: 文件路径
            base_path: 基础路径

        Returns:
            相对路径
        """
        # 使用PathResolver获取相对路径
        resolved_file_path = self.path_resolver.resolve_path(file_path)
        if not resolved_file_path:
            # 如果解析失败，返回原始路径
            return str(file_path)

        relative_path = self.path_resolver.get_relative_path(resolved_file_path, base_path)
        return str(relative_path)

    def backup_file(self, file_path: Union[str, Path],
                   backup_dir: Optional[str] = None) -> str:
        """
        备份文件

        Args:
            file_path: 文件路径
            backup_dir: 备份目录

        Returns:
            备份文件路径
        """
        # 使用PathResolver解析文件路径
        resolved_file_path = self.path_resolver.resolve_path(file_path)
        if not resolved_file_path:
            raise FileOperationError(f"Cannot resolve file path: {file_path}")

        file_path = resolved_file_path

        if not file_path.exists():
            raise FileOperationError(f"File does not exist: {file_path}")

        # 确定备份目录
        if backup_dir is None:
            backup_dir = self.backup_dir

        # 使用PathResolver解析备份目录路径
        resolved_backup_dir = self.path_resolver.resolve_path(backup_dir)
        if not resolved_backup_dir:
            # 如果备份目录路径解析失败，创建相对路径
            resolved_backup_dir = Path.cwd() / backup_dir

        backup_dir_path = resolved_backup_dir
        backup_dir_path.mkdir(parents=True, exist_ok=True)

        # 生成备份文件名
        import time
        timestamp = int(time.time())
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}.backup"
        backup_path = backup_dir_path / backup_name

        try:
            # 复制文件
            shutil.copy2(file_path, backup_path)

            self.logger.info(f"Created backup: {backup_path}")
            return str(backup_path)

        except Exception as e:
            raise FileOperationError(f"Failed to backup file {file_path}: {e}")