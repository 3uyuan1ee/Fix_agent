"""
统一路径解析工具模块
解决相对路径和绝对路径在整个工作流中的解析问题
"""

import os
from pathlib import Path
from typing import Union, List, Optional
import logging

logger = logging.getLogger(__name__)


class PathResolver:
    """统一路径解析器"""

    def __init__(self, project_root: Optional[Union[str, Path]] = None):
        """
        初始化路径解析器

        Args:
            project_root: 项目根目录，如果为None则使用当前工作目录
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.project_root = self.project_root.resolve()  # 转换为绝对路径

        # 保存项目根目录的绝对路径，确保在整个工作流中不会丢失位置
        self._saved_project_root = self.project_root

        logger.debug(f"PathResolver初始化，项目根目录: {self.project_root}")

    def set_project_root(self, project_root: Union[str, Path]):
        """
        设置并保存项目根目录的绝对路径

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root).resolve()
        self._saved_project_root = self.project_root
        logger.info(f"项目根目录已设置并保存: {self.project_root}")

    def get_saved_project_root(self) -> Path:
        """
        获取保存的项目根目录绝对路径

        Returns:
            保存的项目根目录绝对路径
        """
        return self._saved_project_root

    def ensure_project_root_set(self, target_path: Optional[Union[str, Path]] = None):
        """
        确保项目根目录已设置

        Args:
            target_path: 如果项目根目录未设置，使用此路径作为项目根目录
        """
        if not self._saved_project_root or not self._saved_project_root.exists():
            if target_path:
                self.set_project_root(target_path)
            else:
                self.set_project_root(Path.cwd())
            logger.info(f"项目根目录已确保设置: {self._saved_project_root}")

    def resolve_path(self, file_path: Union[str, Path],
                    search_dirs: Optional[List[str]] = None) -> Optional[Path]:
        """
        解析文件路径，支持相对路径和绝对路径

        Args:
            file_path: 要解析的文件路径
            search_dirs: 如果是相对路径，搜索的目录列表

        Returns:
            解析后的绝对路径，如果文件不存在则返回None
        """
        file_path = Path(file_path)

        # 如果已经是绝对路径，直接检查存在性
        if file_path.is_absolute():
            if file_path.exists():
                logger.debug(f"绝对路径解析成功: {file_path}")
                return file_path.resolve()
            else:
                logger.warning(f"绝对路径文件不存在: {file_path}")
                return None

        # 处理相对路径
        if search_dirs is None:
            # 默认搜索目录
            search_dirs = [
                ".",  # 当前工作目录
                "src",  # 源码目录
                "example",  # 示例目录
                "tests",  # 测试目录
                "config",  # 配置目录
            ]

        # 在各个搜索目录中查找文件
        for search_dir in search_dirs:
            # 构建候选路径
            if search_dir == ".":
                candidate = self.project_root / file_path
            else:
                candidate = self.project_root / search_dir / file_path

            # 检查文件是否存在
            if candidate.exists():
                resolved_path = candidate.resolve()
                logger.debug(f"相对路径解析成功: {file_path} -> {resolved_path}")
                return resolved_path

        # 如果都没找到，尝试直接在项目根目录下查找
        candidate = self.project_root / file_path
        if candidate.exists():
            resolved_path = candidate.resolve()
            logger.debug(f"项目根目录查找成功: {file_path} -> {resolved_path}")
            return resolved_path

        logger.warning(f"无法找到文件: {file_path}")
        return None

    def normalize_path(self, file_path: Union[str, Path]) -> Path:
        """
        标准化路径格式

        Args:
            file_path: 要标准化的路径

        Returns:
            标准化后的Path对象
        """
        path = Path(file_path)

        # 清理路径（移除 ./ 等）
        if str(path).startswith("./"):
            path = Path(str(path)[2:])

        # 转换为绝对路径
        if not path.is_absolute():
            path = self.project_root / path

        # 解析 .. 和 .
        path = path.resolve()

        return path

    def get_relative_path(self, file_path: Union[str, Path],
                         base: Optional[Union[str, Path]] = None) -> Path:
        """
        获取相对路径

        Args:
            file_path: 文件路径
            base: 基准路径，如果为None则使用项目根目录

        Returns:
            相对路径
        """
        file_path = self.normalize_path(file_path)
        base_path = self.normalize_path(base) if base else self.project_root

        try:
            # 尝试获取相对路径
            relative_path = file_path.relative_to(base_path)
            return relative_path
        except ValueError:
            # 如果无法获取相对路径，返回原始路径
            logger.debug(f"无法获取相对路径: {file_path} 相对于 {base_path}")
            return file_path

    def batch_resolve_paths(self, file_paths: List[Union[str, Path]],
                           search_dirs: Optional[List[str]] = None) -> List[Path]:
        """
        批量解析路径

        Args:
            file_paths: 文件路径列表
            search_dirs: 搜索目录列表

        Returns:
            解析成功后的绝对路径列表
        """
        resolved_paths = []

        for file_path in file_paths:
            resolved = self.resolve_path(file_path, search_dirs)
            if resolved:
                resolved_paths.append(resolved)
            else:
                logger.warning(f"跳过不存在的文件: {file_path}")

        return resolved_paths

    def validate_project_structure(self, target_path: Union[str, Path]) -> dict:
        """
        验证项目结构

        Args:
            target_path: 目标项目路径

        Returns:
            验证结果字典
        """
        target_path = Path(target_path).resolve()

        result = {
            "valid": False,
            "absolute_path": str(target_path),
            "exists": target_path.exists(),
            "is_directory": target_path.is_dir() if target_path.exists() else False,
            "subdirectories": [],
            "files": [],
            "errors": []
        }

        if not target_path.exists():
            result["errors"].append(f"路径不存在: {target_path}")
            return result

        if not target_path.is_dir():
            result["errors"].append(f"路径不是目录: {target_path}")
            return result

        # 扫描项目结构
        try:
            for item in target_path.iterdir():
                if item.is_dir():
                    result["subdirectories"].append(item.name)
                elif item.is_file():
                    result["files"].append(item.name)
        except PermissionError as e:
            result["errors"].append(f"权限不足: {e}")

        result["valid"] = len(result["errors"]) == 0
        return result


# 全局路径解析器实例
_global_resolver: Optional[PathResolver] = None


def get_path_resolver(project_root: Optional[Union[str, Path]] = None) -> PathResolver:
    """
    获取全局路径解析器实例

    Args:
        project_root: 项目根目录

    Returns:
        PathResolver实例
    """
    global _global_resolver

    if _global_resolver is None:
        _global_resolver = PathResolver(project_root)

    return _global_resolver


def resolve_file_path(file_path: Union[str, Path],
                     search_dirs: Optional[List[str]] = None) -> Optional[Path]:
    """
    便捷函数：解析单个文件路径

    Args:
        file_path: 文件路径
        search_dirs: 搜索目录列表

    Returns:
        解析后的绝对路径
    """
    resolver = get_path_resolver()
    return resolver.resolve_path(file_path, search_dirs)


def batch_resolve_file_paths(file_paths: List[Union[str, Path]],
                           search_dirs: Optional[List[str]] = None) -> List[Path]:
    """
    便捷函数：批量解析文件路径

    Args:
        file_paths: 文件路径列表
        search_dirs: 搜索目录列表

    Returns:
        解析成功后的绝对路径列表
    """
    resolver = get_path_resolver()
    return resolver.batch_resolve_paths(file_paths, search_dirs)