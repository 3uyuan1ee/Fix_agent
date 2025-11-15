"""
基础数据集加载器

定义数据集加载器的通用接口和基础功能。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import os
import subprocess
import tempfile
import shutil

# 使用本地数据类型定义以避免循环导入
try:
    from ..data_types import EvaluationTask
except ImportError:
    try:
        from data_types import EvaluationTask
    except ImportError:
        from Dataset.data_types import EvaluationTask

class BaseDatasetLoader(ABC):
    """
    数据集加载器基类

    所有数据集加载器都应该继承这个基类并实现其抽象方法。
    """

    def __init__(self, dataset_path: str, cache_dir: str = None):
        self.dataset_path = Path(dataset_path)
        self.cache_dir = Path(cache_dir or tempfile.mkdtemp(prefix="dataset_cache_"))
        self.cache_dir.mkdir(exist_ok=True)

    @abstractmethod
    def download_dataset(self) -> bool:
        """
        下载数据集

        Returns:
            bool: 下载是否成功
        """
        pass

    @abstractmethod
    def load_tasks(self, sample_size: int = None, difficulty_filter: str = None) -> List[EvaluationTask]:
        """
        加载评估任务

        Args:
            sample_size: 采样大小，None表示加载全部
            difficulty_filter: 难度过滤器 ('easy', 'medium', 'hard', None)

        Returns:
            List[EvaluationTask]: 评估任务列表
        """
        pass

    @abstractmethod
    def get_dataset_info(self) -> Dict[str, Any]:
        """
        获取数据集信息

        Returns:
            Dict[str, Any]: 数据集信息
        """
        pass

    def validate_dataset(self) -> bool:
        """
        验证数据集是否完整

        Returns:
            bool: 数据集是否有效
        """
        if not self.dataset_path.exists():
            print(f"[BaseDatasetLoader] 数据集路径不存在: {self.dataset_path}")
            return False

        # 检查关键文件
        required_files = self.get_required_files()
        for file_path in required_files:
            if not (self.dataset_path / file_path).exists():
                print(f"[BaseDatasetLoader] 缺少必要文件: {file_path}")
                return False

        return True

    @abstractmethod
    def get_required_files(self) -> List[str]:
        """
        获取数据集必需的文件列表

        Returns:
            List[str]: 必需文件列表
        """
        pass

    def clone_repository(self, repo_url: str, commit_hash: str, target_dir: Path) -> bool:
        """
        克隆Git仓库到指定commit

        Args:
            repo_url: 仓库URL
            commit_hash: commit哈希
            target_dir: 目标目录

        Returns:
            bool: 克隆是否成功
        """
        try:
            # 克隆仓库
            result = subprocess.run(
                ["git", "clone", repo_url, str(target_dir)],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"[BaseDatasetLoader] 克隆失败: {result.stderr}")
                return False

            # 切换到指定commit
            result = subprocess.run(
                ["git", "checkout", commit_hash],
                cwd=target_dir,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                print(f"[BaseDatasetLoader] 切换commit失败: {result.stderr}")
                return False

            return True

        except Exception as e:
            print(f"[BaseDatasetLoader] 克隆仓库异常: {e}")
            return False

    def install_dependencies(self, workspace_path: Path, requirements: List[str]) -> bool:
        """
        安装项目依赖

        Args:
            workspace_path: 工作空间路径
            requirements: 依赖列表

        Returns:
            bool: 安装是否成功
        """
        try:
            for requirement in requirements:
                result = subprocess.run(
                    ["pip", "install", requirement],
                    capture_output=True,
                    text=True
                )

                if result.returncode != 0:
                    print(f"[BaseDatasetLoader] 安装依赖失败: {requirement}")
                    print(f"[BaseDatasetLoader] 错误信息: {result.stderr}")
                    return False

            return True

        except Exception as e:
            print(f"[BaseDatasetLoader] 安装依赖异常: {e}")
            return False

    def detect_project_info(self, workspace_path: Path) -> Dict[str, Any]:
        """
        检测项目信息

        Args:
            workspace_path: 项目路径

        Returns:
            Dict[str, Any]: 项目信息
        """
        project_info = {
            "language": "unknown",
            "framework": None,
            "test_framework": None,
            "build_system": None
        }

        # 检测主要语言
        language_counts = {}
        for ext in [".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs"]:
            count = len(list(workspace_path.rglob(f"*{ext}")))
            if count > 0:
                language_counts[ext] = count

        if language_counts:
            max_ext = max(language_counts, key=language_counts.get)
            language_map = {
                ".py": "python",
                ".js": "javascript",
                ".ts": "typescript",
                ".java": "java",
                ".cpp": "cpp",
                ".c": "c",
                ".go": "go",
                ".rs": "rust"
            }
            project_info["language"] = language_map.get(max_ext, "unknown")

        # 检测框架
        framework_files = [
            ("django", "django"),
            ("flask", "flask"),
            ("react", "react"),
            ("vue", "vue"),
            ("angular", "angular"),
            ("spring", "spring"),
            ("rails", "rails")
        ]

        for framework, file_pattern in framework_files:
            if any(workspace_path.rglob(f"*{framework}*")):
                project_info["framework"] = framework
                break

        # 检测测试框架
        test_indicators = [
            ("pytest", "pytest"),
            ("unittest", "unittest"),
            ("jest", "jest"),
            ("mocha", "mocha"),
            ("junit", "junit")
        ]

        for test_framework, indicator in test_indicators:
            if any(workspace_path.rglob(f"*{indicator}*")):
                project_info["test_framework"] = test_framework
                break

        # 检测构建系统
        build_files = [
            ("setup.py", "setuptools"),
            ("pyproject.toml", "poetry/setuptools"),
            ("package.json", "npm"),
            ("pom.xml", "maven"),
            ("build.gradle", "gradle"),
            ("Cargo.toml", "cargo"),
            ("go.mod", "go_modules")
        ]

        for build_file, build_system in build_files:
            if (workspace_path / build_file).exists():
                project_info["build_system"] = build_system
                break

        return project_info

    def get_cache_path(self, key: str) -> Path:
        """
        获取缓存文件路径

        Args:
            key: 缓存键

        Returns:
            Path: 缓存文件路径
        """
        return self.cache_dir / f"{key}.json"

    def load_cache(self, key: str) -> Optional[Any]:
        """
        加载缓存数据

        Args:
            key: 缓存键

        Returns:
            Optional[Any]: 缓存数据，如果不存在则返回None
        """
        cache_file = self.get_cache_path(key)
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[BaseDatasetLoader] 加载缓存失败 {key}: {e}")
        return None

    def save_cache(self, key: str, data: Any):
        """
        保存缓存数据

        Args:
            key: 缓存键
            data: 缓存数据
        """
        cache_file = self.get_cache_path(key)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[BaseDatasetLoader] 保存缓存失败 {key}: {e}")

    def cleanup_cache(self):
        """
        清理缓存
        """
        try:
            if self.cache_dir.exists():
                shutil.rmtree(self.cache_dir)
                print(f"[BaseDatasetLoader] 清理缓存: {self.cache_dir}")
        except Exception as e:
            print(f"[BaseDatasetLoader] 清理缓存失败: {e}")

    def __del__(self):
        """
        析构函数，清理缓存
        """
        self.cleanup_cache()