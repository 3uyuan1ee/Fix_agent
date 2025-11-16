"""
文件工具模块 - 修复文件名过长等文件操作问题
"""

import hashlib
import json
import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional


def create_secure_temp_filename(content: str, prefix: str = "patch_", max_length: int = 100) -> str:
    """
    创建安全的临时文件名，解决文件名过长问题

    Args:
        content: 文件内容（用于生成哈希）
        prefix: 文件名前缀
        max_length: 最大文件名长度

    Returns:
        str: 安全的文件名
    """
    # 生成内容的哈希值
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]

    # 使用UUID确保唯一性
    unique_id = str(uuid.uuid4())[:8]

    # 组合文件名
    filename = f"{prefix}{content_hash}_{unique_id}.patch"

    # 确保文件名不超过最大长度
    if len(filename) > max_length:
        filename = f"{prefix}{content_hash}.patch"

    return filename


def create_temp_directory(base_dir: str = None) -> str:
    """
    创建临时目录

    Args:
        base_dir: 基础目录，如果为None则使用系统默认临时目录

    Returns:
        str: 临时目录路径
    """
    if base_dir:
        temp_dir = Path(base_dir) / f"temp_{uuid.uuid4().hex[:8]}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        return str(temp_dir)
    else:
        return tempfile.mkdtemp(prefix="dataset_eval_")


def safe_write_file(file_path: str, content: str, max_filename_length: int = 255) -> bool:
    """
    安全写入文件，处理文件名过长问题

    Args:
        file_path: 原始文件路径
        content: 文件内容
        max_filename_length: 最大文件名长度

    Returns:
        bool: 写入是否成功
    """
    try:
        file_path = Path(file_path)

        # 检查文件名长度
        if len(file_path.name) > max_filename_length:
            # 生成新的安全文件名
            safe_name = create_secure_temp_filename(content)
            new_path = file_path.parent / safe_name
            file_path = new_path

            logging.warning(f"文件名过长，使用新文件名: {file_path}")

        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return True

    except Exception as e:
        logging.error(f"写入文件失败 {file_path}: {e}")
        return False


def apply_patch_safely(patch_content: str, target_dir: str, max_filename_length: int = 100) -> Dict[str, Any]:
    """
    安全应用补丁，处理文件名过长问题

    Args:
        patch_content: 补丁内容
        target_dir: 目标目录
        max_filename_length: 最大文件名长度

    Returns:
        Dict[str, Any]: 应用结果
    """
    result = {
        "success": False,
        "error": None,
        "patch_file": None,
        "applied_files": []
    }

    try:
        target_dir = Path(target_dir)

        # 创建安全的补丁文件名
        patch_filename = create_secure_temp_filename(patch_content, prefix="diff_", max_length=max_filename_length)
        patch_file = target_dir / patch_filename

        # 写入补丁文件
        if not safe_write_file(patch_file, patch_content):
            result["error"] = "无法创建补丁文件"
            return result

        result["patch_file"] = str(patch_file)

        # 应用补丁
        import subprocess

        try:
            # 使用git apply应用补丁
            apply_result = subprocess.run(
                ["git", "apply", "--check", str(patch_file)],
                cwd=target_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            if apply_result.returncode == 0:
                # 补丁可以应用，实际应用
                apply_result = subprocess.run(
                    ["git", "apply", str(patch_file)],
                    cwd=target_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if apply_result.returncode == 0:
                    result["success"] = True
                    # 解析补丁中的文件（简化版本）
                    result["applied_files"] = parse_patch_files(patch_content)
                else:
                    result["error"] = f"应用补丁失败: {apply_result.stderr}"
            else:
                result["error"] = f"补丁检查失败: {apply_result.stderr}"

        except subprocess.TimeoutExpired:
            result["error"] = "应用补丁超时"
        except Exception as e:
            result["error"] = f"应用补丁时发生错误: {e}"

        # 清理临时补丁文件
        try:
            if patch_file.exists():
                patch_file.unlink()
        except:
            pass

    except Exception as e:
        result["error"] = f"处理补丁时发生错误: {e}"

    return result


def parse_patch_files(patch_content: str) -> List[str]:
    """
    解析补丁中涉及的文件

    Args:
        patch_content: 补丁内容

    Returns:
        List[str]: 涉及的文件列表
    """
    files = []

    for line in patch_content.split('\n'):
        if line.startswith('+++ b/'):
            file_path = line[6:].strip()  # 移除 '+++ b/' 前缀
            if file_path and file_path != '/dev/null':
                files.append(file_path)
        elif line.startswith('--- a/'):
            file_path = line[6:].strip()  # 移除 '--- a/' 前缀
            if file_path and file_path != '/dev/null':
                files.append(file_path)

    # 去重
    return list(set(files))


def safe_copy_directory(src: str, dst: str) -> bool:
    """
    安全复制目录

    Args:
        src: 源目录
        dst: 目标目录

    Returns:
        bool: 复制是否成功
    """
    try:
        src_path = Path(src)
        dst_path = Path(dst)

        if not src_path.exists():
            logging.error(f"源目录不存在: {src}")
            return False

        # 如果目标目录存在，先删除
        if dst_path.exists():
            shutil.rmtree(dst_path)

        # 复制目录
        shutil.copytree(src_path, dst_path)
        return True

    except Exception as e:
        logging.error(f"复制目录失败 {src} -> {dst}: {e}")
        return False


def cleanup_temp_files(temp_dir: str, max_age_hours: int = 24) -> None:
    """
    清理过期的临时文件

    Args:
        temp_dir: 临时文件目录
        max_age_hours: 最大保存时间（小时）
    """
    try:
        import time

        temp_path = Path(temp_dir)
        if not temp_path.exists():
            return

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600

        for item in temp_path.iterdir():
            try:
                if item.is_dir():
                    # 检查目录的修改时间
                    if current_time - item.stat().st_mtime > max_age_seconds:
                        shutil.rmtree(item)
                        logging.info(f"清理过期目录: {item}")
                elif item.is_file():
                    if current_time - item.stat().st_mtime > max_age_seconds:
                        item.unlink()
                        logging.info(f"清理过期文件: {item}")
            except Exception as e:
                logging.warning(f"清理文件时出错 {item}: {e}")

    except Exception as e:
        logging.error(f"清理临时文件时出错: {e}")


def setup_logging(
    log_level: int = logging.INFO,
    log_dir: str = "./logs",
    mode: str = "default"
) -> logging.Logger:
    """
    设置日志记录

    Args:
        log_level: 日志级别
        log_dir: 日志目录
        mode: 运行模式

    Returns:
        logging.Logger: 配置好的logger
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 设置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # 创建logger
    logger = logging.getLogger(f"dataset_{mode}")
    logger.setLevel(log_level)

    # 清除现有的handlers
    logger.handlers.clear()

    # 控制台handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 文件handler
    log_file = log_path / f"{mode}_evaluation.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    return logger


def validate_json_file(file_path: str) -> bool:
    """
    验证JSON文件格式

    Args:
        file_path: JSON文件路径

    Returns:
        bool: 是否为有效的JSON文件
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except Exception as e:
        logging.error(f"JSON文件格式错误 {file_path}: {e}")
        return False


def get_file_hash(file_path: str) -> str:
    """
    获取文件的SHA256哈希值

    Args:
        file_path: 文件路径

    Returns:
        str: 文件哈希值
    """
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    except Exception as e:
        logging.error(f"计算文件哈希失败 {file_path}: {e}")
        return ""


def ensure_directory_exists(dir_path: str) -> bool:
    """
    确保目录存在，如果不存在则创建

    Args:
        dir_path: 目录路径

    Returns:
        bool: 目录是否可用
    """
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"创建目录失败 {dir_path}: {e}")
        return False