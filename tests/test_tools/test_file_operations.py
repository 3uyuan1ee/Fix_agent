"""
文件操作工具单元测试
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.tools.file_operations import FileOperations, FileOperationError


class TestFileOperations:
    """文件操作工具测试类"""

    def setup_method(self):
        """测试前设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.file_ops = FileOperations()

    def teardown_method(self):
        """测试后清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_directory_recursive(self):
        """测试递归扫描目录"""
        # 创建测试文件结构
        (Path(self.temp_dir) / "test1.py").touch()
        (Path(self.temp_dir) / "subdir").mkdir()
        (Path(self.temp_dir) / "subdir" / "test2.py").touch()
        (Path(self.temp_dir) / "test3.txt").touch()

        # 扫描目录
        files = self.file_ops.scan_directory(self.temp_dir, recursive=True)

        # 验证结果
        assert len(files) == 3
        file_names = [Path(f).name for f in files]
        assert "test1.py" in file_names
        assert "test2.py" in file_names
        assert "test3.txt" in file_names

    def test_scan_directory_non_recursive(self):
        """测试非递归扫描目录"""
        # 创建测试文件结构
        (Path(self.temp_dir) / "test1.py").touch()
        (Path(self.temp_dir) / "subdir").mkdir()
        (Path(self.temp_dir) / "subdir" / "test2.py").touch()

        # 扫描目录（非递归）
        files = self.file_ops.scan_directory(self.temp_dir, recursive=False)

        # 验证结果
        assert len(files) == 1
        assert Path(files[0]).name == "test1.py"

    def test_scan_directory_with_extension_filter(self):
        """测试根据扩展名过滤文件"""
        # 创建测试文件
        (Path(self.temp_dir) / "test1.py").touch()
        (Path(self.temp_dir) / "test2.py").touch()
        (Path(self.temp_dir) / "test3.txt").touch()
        (Path(self.temp_dir) / "test4.js").touch()

        # 扫描Python文件
        python_files = self.file_ops.scan_directory(
            self.temp_dir, extensions=[".py"]
        )

        # 验证结果
        assert len(python_files) == 2
        for file_path in python_files:
            assert file_path.endswith(".py")

    def test_scan_directory_multiple_extensions(self):
        """测试多扩展名过滤"""
        # 创建测试文件
        (Path(self.temp_dir) / "test1.py").touch()
        (Path(self.temp_dir) / "test2.txt").touch()
        (Path(self.temp_dir) / "test3.js").touch()

        # 扫描多种文件类型
        files = self.file_ops.scan_directory(
            self.temp_dir, extensions=[".py", ".txt"]
        )

        # 验证结果
        assert len(files) == 2
        extensions = [Path(f).suffix for f in files]
        assert ".py" in extensions
        assert ".txt" in extensions

    def test_scan_directory_nonexistent(self):
        """测试扫描不存在的目录"""
        with pytest.raises(FileOperationError) as exc_info:
            self.file_ops.scan_directory("/nonexistent/directory")

        assert "does not exist" in str(exc_info.value)

    def test_read_file_success(self):
        """测试成功读取文件"""
        # 创建测试文件
        test_content = "这是测试内容\nwith multiple lines"
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text(test_content, encoding="utf-8")

        # 读取文件
        content = self.file_ops.read_file(str(test_file))

        # 验证结果
        assert content == test_content

    def test_read_file_with_encoding(self):
        """测试指定编码读取文件"""
        # 创建测试文件（GBK编码）
        test_content = "中文测试内容"
        test_file = Path(self.temp_dir) / "test_gbk.txt"
        test_file.write_text(test_content, encoding="gbk")

        # 读取文件
        content = self.file_ops.read_file(str(test_file), encoding="gbk")

        # 验证结果
        assert content == test_content

    def test_read_file_encoding_error(self):
        """测试编码错误处理"""
        # 创建测试文件（GBK编码）
        test_content = "中文测试内容"
        test_file = Path(self.temp_dir) / "test_gbk.txt"
        test_file.write_text(test_content, encoding="gbk")

        # 尝试用UTF-8读取，应该回退到备用编码
        content = self.file_ops.read_file(str(test_file), encoding="utf-8")
        assert content is not None  # 应该能够读取内容（通过回退机制）

    def test_read_file_nonexistent(self):
        """测试读取不存在的文件"""
        with pytest.raises(FileOperationError) as exc_info:
            self.file_ops.read_file("/nonexistent/file.txt")

        assert "does not exist" in str(exc_info.value)

    def test_read_large_file_streaming(self):
        """测试大文件流式读取"""
        # 创建大文件
        large_content = "x" * 10000  # 10KB
        test_file = Path(self.temp_dir) / "large.txt"
        test_file.write_text(large_content)

        # 流式读取
        content = self.file_ops.read_file(str(test_file), streaming=True)

        # 验证结果
        assert content == large_content

    def test_search_files_by_pattern(self):
        """测试按模式搜索文件"""
        # 创建测试文件
        (Path(self.temp_dir) / "test_model.py").touch()
        (Path(self.temp_dir) / "user_model.py").touch()
        (Path(self.temp_dir) / "controller.py").touch()
        (Path(self.temp_dir) / "utils.py").touch()

        # 搜索包含"model"的文件
        matching_files = self.file_ops.search_files(
            self.temp_dir, pattern="model"
        )

        # 验证结果
        assert len(matching_files) == 2
        for file_path in matching_files:
            assert "model" in Path(file_path).name.lower()

    def test_search_files_by_content(self):
        """测试按内容搜索文件"""
        # 创建测试文件
        test_file1 = Path(self.temp_dir) / "file1.py"
        test_file1.write_text("def function_a():\n    pass")

        test_file2 = Path(self.temp_dir) / "file2.py"
        test_file2.write_text("def function_b():\n    pass")

        test_file3 = Path(self.temp_dir) / "file3.py"
        test_file3.write_text("print('hello')")

        # 搜索包含"function"的文件
        matching_files = self.file_ops.search_files(
            self.temp_dir, content_pattern="function"
        )

        # 验证结果
        assert len(matching_files) == 2
        for file_path in matching_files:
            assert Path(file_path).name in ["file1.py", "file2.py"]

    def test_get_file_info(self):
        """测试获取文件信息"""
        # 创建测试文件
        test_content = "test content"
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text(test_content)

        # 获取文件信息
        info = self.file_ops.get_file_info(str(test_file))

        # 验证结果
        assert info["size"] == len(test_content)
        assert "extension" in info
        assert info["extension"] == ".txt"
        assert "modified_time" in info
        assert "is_file" in info
        assert info["is_file"] is True

    def test_get_file_info_directory(self):
        """测试获取目录信息"""
        # 获取目录信息
        info = self.file_ops.get_file_info(self.temp_dir)

        # 验证结果
        assert info["is_file"] is False
        assert info["is_directory"] is True
        assert "size" in info

    def test_write_file_success(self):
        """测试成功写入文件"""
        content = "这是写入的内容"
        file_path = Path(self.temp_dir) / "output.txt"

        # 写入文件
        self.file_ops.write_file(str(file_path), content)

        # 验证文件存在且内容正确
        assert file_path.exists()
        assert file_path.read_text(encoding="utf-8") == content

    def test_write_file_with_encoding(self):
        """测试指定编码写入文件"""
        content = "中文内容"
        file_path = Path(self.temp_dir) / "output_gbk.txt"

        # 写入文件
        self.file_ops.write_file(str(file_path), content, encoding="gbk")

        # 验证文件内容
        assert file_path.read_text(encoding="gbk") == content

    def test_write_file_create_directory(self):
        """测试写入文件时自动创建目录"""
        content = "test content"
        nested_path = Path(self.temp_dir) / "nested" / "dir" / "output.txt"

        # 写入文件
        self.file_ops.write_file(str(nested_path), content)

        # 验证目录和文件都被创建
        assert nested_path.exists()
        assert nested_path.read_text() == content

    def test_is_text_file(self):
        """测试判断是否为文本文件"""
        # 创建文本文件
        text_file = Path(self.temp_dir) / "test.txt"
        text_file.write_text("text content")

        # 创建二进制文件
        binary_file = Path(self.temp_dir) / "test.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03')

        # 测试判断
        assert self.file_ops.is_text_file(str(text_file)) is True
        assert self.file_ops.is_text_file(str(binary_file)) is False

    def test_get_relative_path(self):
        """测试获取相对路径"""
        # 创建文件
        file_path = Path(self.temp_dir) / "subdir" / "test.py"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch()

        # 获取相对路径
        relative = self.file_ops.get_relative_path(str(file_path), self.temp_dir)

        # 验证结果
        assert relative == "subdir/test.py"

    def test_backup_file(self):
        """测试文件备份"""
        # 创建原始文件
        original_content = "original content"
        original_file = Path(self.temp_dir) / "original.txt"
        original_file.write_text(original_content)

        # 创建备份
        backup_path = self.file_ops.backup_file(str(original_file))

        # 验证备份文件存在且内容相同
        assert Path(backup_path).exists()
        assert Path(backup_path).read_text() == original_content
        assert backup_path.endswith(".backup")