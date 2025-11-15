"""
SWE-bench数据集加载器

SWE-bench是一个用于评估软件工程agent能力的数据集，
包含来自GitHub的真实issue和PR。
"""

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# 使用多层导入策略
try:
    from ..data_types import EvaluationTask
    from .base import BaseDatasetLoader
except ImportError:
    try:
        from base import BaseDatasetLoader
        from data_types import EvaluationTask
    except ImportError:
        try:
            from Dataset.data_types import EvaluationTask
            from Dataset.loaders.base import BaseDatasetLoader
        except ImportError:
            # 最后尝试：从当前目录导入
            import sys
            from pathlib import Path

            current_dir = Path(__file__).parent
            if str(current_dir) not in sys.path:
                sys.path.insert(0, str(current_dir))
            from base import BaseDatasetLoader

            # 从根目录导入data_types
            root_dir = current_dir.parent
            if str(root_dir) not in sys.path:
                sys.path.insert(0, str(root_dir))
            from ..data_types import EvaluationTask


class SWEBenchLoader(BaseDatasetLoader):
    """
    SWE-bench数据集加载器

    特点：
    - 支持SWE-bench-test和SWE-bench-lite
    - 自动下载和解压数据集
    - 支持项目级别的缓存
    - 提供难度分级过滤
    """

    def __init__(
        self, dataset_path: str = "./datasets/swe-bench", cache_dir: str = None
    ):
        super().__init__(dataset_path, cache_dir)
        self.testbed_path = self.dataset_path / "testbed"
        self.data_file = self.testbed_path / "swe-bench-test.json"

    def download_dataset(self) -> bool:
        """
        下载SWE-bench数据集

        Returns:
            bool: 下载是否成功
        """
        print("[SWEBenchLoader] 开始下载SWE-bench数据集...")

        try:
            # 创建数据集目录
            self.dataset_path.mkdir(parents=True, exist_ok=True)

            # 下载主仓库
            if not (self.dataset_path / "SWE-bench").exists():
                print("[SWEBenchLoader] 克隆SWE-bench仓库...")
                result = subprocess.run(
                    [
                        "git",
                        "clone",
                        "git@github.com:princeton-nlp/SWE-bench.git",
                        str(self.dataset_path / "SWE-bench"),
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    print(f"[SWEBenchLoader] 克隆失败: {result.stderr}")
                    return False

            # 下载testbed数据 - 尝试多个可能的URL
            if not self.data_file.exists():
                print("[SWEBenchLoader] 下载testbed数据...")

                # 尝试多个可能的下载URL
                testbed_urls = [
                    "https://huggingface.co/datasets/princeton-nlp/SWE-bench/resolve/main/data/testbed.tar.gz",
                    "https://huggingface.co/datasets/princeton-nlp/SWE-bench-v2/resolve/main/data/testbed.tar.gz",
                    "https://github.com/princeton-nlp/SWE-bench/raw/main/data/testbed.tar.gz",
                ]

                download_success = False
                for testbed_url in testbed_urls:
                    try:
                        print(f"[SWEBenchLoader] 尝试下载: {testbed_url}")
                        testbed_tar = self.testbed_path / "testbed.tar.gz"

                        # 下载文件
                        response = requests.get(testbed_url, stream=True, timeout=30)
                        response.raise_for_status()

                        self.testbed_path.mkdir(parents=True, exist_ok=True)
                        with open(testbed_tar, "wb") as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)

                        # 解压文件
                        print("[SWEBenchLoader] 解压testbed数据...")
                        with tarfile.open(testbed_tar, "r:gz") as tar:
                            tar.extractall(self.testbed_path)

                        # 删除tar文件
                        testbed_tar.unlink()

                        print(f"[SWEBenchLoader] 成功下载: {testbed_url}")
                        download_success = True
                        break

                    except Exception as e:
                        print(f"[SWEBenchLoader] 下载失败: {testbed_url}")
                        print(f"[SWEBenchLoader] 错误信息: {e}")
                        # 清理失败的下载文件
                        if (self.testbed_path / "testbed.tar.gz").exists():
                            (self.testbed_path / "testbed.tar.gz").unlink()

                if not download_success:
                    print("[SWEBenchLoader] 所有下载链接都无法访问，将创建模拟数据集")
                    print(
                        "[SWEBenchLoader] 注意: 这是用于测试的模拟数据，不包含真实的SWE-bench数据"
                    )
                    return self._create_mock_swe_bench_dataset()

            print("[SWEBenchLoader] 数据集下载完成")
            return True

        except Exception as e:
            print(f"[SWEBenchLoader] 下载失败: {e}")
            return False

    def load_tasks(
        self, sample_size: int = None, difficulty_filter: str = None
    ) -> List[EvaluationTask]:
        """
        加载SWE-bench评估任务

        Args:
            sample_size: 采样大小
            difficulty_filter: 难度过滤器 ('easy', 'medium', 'hard')

        Returns:
            List[EvaluationTask]: 评估任务列表
        """
        print(
            f"[SWEBenchLoader] 加载任务，样本大小: {sample_size}, 难度过滤: {difficulty_filter}"
        )

        # 检查缓存
        cache_key = f"swe_bench_tasks_{sample_size}_{difficulty_filter}"
        cached_tasks = self.load_cache(cache_key)
        if cached_tasks:
            print(f"[SWEBenchLoader] 从缓存加载 {len(cached_tasks)} 个任务")
            return [EvaluationTask(**task) for task in cached_tasks]

        # 验证数据集
        if not self.validate_dataset():
            raise RuntimeError("数据集验证失败")

        # 加载数据
        with open(self.data_file, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        print(f"[SWEBenchLoader] 原始数据集大小: {len(dataset)}")

        # 应用难度过滤器
        if difficulty_filter:
            dataset = self._apply_difficulty_filter(dataset, difficulty_filter)
            print(f"[SWEBenchLoader] 过滤后数据集大小: {len(dataset)}")

        # 采样
        if sample_size and sample_size < len(dataset):
            dataset = dataset[:sample_size]

        # 转换为EvaluationTask
        tasks = []
        for item in dataset:
            try:
                task = self._convert_to_evaluation_task(item)
                if task:
                    tasks.append(task)
            except Exception as e:
                print(
                    f"[SWEBenchLoader] 转换任务失败 {item.get('instance_id', 'unknown')}: {e}"
                )

        print(f"[SWEBenchLoader] 成功加载 {len(tasks)} 个任务")

        # 保存缓存
        self.save_cache(cache_key, [task.__dict__ for task in tasks])

        return tasks

    def get_dataset_info(self) -> Dict[str, Any]:
        """
        获取SWE-bench数据集信息

        Returns:
            Dict[str, Any]: 数据集信息
        """
        if not self.validate_dataset():
            return {"error": "数据集不可用"}

        with open(self.data_file, "r", encoding="utf-8") as f:
            dataset = json.load(f)

        # 统计信息
        repos = {}
        languages = {}
        difficulties = {"easy": 0, "medium": 0, "hard": 0}

        for item in dataset:
            # 仓库统计
            repo = item.get("repo", "")
            repos[repo] = repos.get(repo, 0) + 1

            # 语言统计（从仓库推断）
            language = self._infer_language_from_repo(repo)
            languages[language] = languages.get(language, 0) + 1

            # 难度统计（基于修改的文件数量）
            difficulty = self._estimate_difficulty(item)
            difficulties[difficulty] += 1

        return {
            "name": "SWE-bench",
            "version": "test",
            "total_instances": len(dataset),
            "repositories": repos,
            "languages": languages,
            "difficulty_distribution": difficulties,
            "path": str(self.dataset_path),
            "description": "Software Engineering Benchmark - GitHub issues and pull requests",
        }

    def get_required_files(self) -> List[str]:
        """
        获取SWE-bench必需的文件列表

        Returns:
            List[str]: 必需文件列表
        """
        return ["SWE-bench/README.md", "testbed/swe-bench-test.json"]

    def _apply_difficulty_filter(
        self, dataset: List[Dict], difficulty_filter: str
    ) -> List[Dict]:
        """
        应用难度过滤器

        Args:
            dataset: 原始数据集
            difficulty_filter: 难度过滤器

        Returns:
            List[Dict]: 过滤后的数据集
        """
        filtered_dataset = []

        for item in dataset:
            difficulty = self._estimate_difficulty(item)
            if difficulty == difficulty_filter:
                filtered_dataset.append(item)

        return filtered_dataset

    def _estimate_difficulty(self, item: Dict) -> str:
        """
        估算任务难度

        Args:
            item: 数据集项目

        Returns:
            str: 难度级别 ('easy', 'medium', 'hard')
        """
        # 基于patch大小估算难度
        patch = item.get("patch", "")
        if not patch:
            return "unknown"

        # 计算修改的行数
        lines = patch.split("\n")
        added_lines = len(
            [
                line
                for line in lines
                if line.startswith("+") and not line.startswith("+++")
            ]
        )
        removed_lines = len(
            [
                line
                for line in lines
                if line.startswith("-") and not line.startswith("---")
            ]
        )
        total_changes = added_lines + removed_lines

        # 计算修改的文件数
        files_changed = len(
            set(line.split()[1] for line in lines if line.startswith("diff --git"))
        )

        # 基于启发式规则估算难度
        if total_changes <= 10 and files_changed <= 2:
            return "easy"
        elif total_changes <= 50 and files_changed <= 5:
            return "medium"
        else:
            return "hard"

    def _infer_language_from_repo(self, repo: str) -> str:
        """
        从仓库名推断主要编程语言

        Args:
            repo: 仓库名

        Returns:
            str: 编程语言
        """
        language_mapping = {
            "django/django": "python",
            "flask/flask": "python",
            "pallets/flask": "python",
            "psf/requests": "python",
            "scikit-learn/scikit-learn": "python",
            "sympy/sympy": "python",
            "pandas-dev/pandas": "python",
            "numpy/numpy": "python",
            "matplotlib/matplotlib": "python",
            "tensorflow/tensorflow": "python",
            "pytorch/pytorch": "python",
            "microsoft/vscode": "typescript",
            "facebook/react": "javascript",
            "vuejs/vue": "javascript",
            "angular/angular": "typescript",
            "nodejs/node": "javascript",
            "mozilla/firefox": "cpp",
            "torvalds/linux": "c",
            "golang/go": "go",
            "rust-lang/rust": "rust",
        }

        return language_mapping.get(repo, "unknown")

    def _convert_to_evaluation_task(self, item: Dict) -> Optional[EvaluationTask]:
        """
        将SWE-bench项目转换为EvaluationTask

        Args:
            item: SWE-bench数据集项目

        Returns:
            Optional[EvaluationTask]: 评估任务
        """
        try:
            # 提取基本信息
            instance_id = item.get("instance_id", "")
            repo = item.get("repo", "")
            base_commit = item.get("base_commit", "")
            problem_statement = item.get("problem_statement", "")
            test_patch = item.get("test_patch", "")
            patch = item.get("patch", "")

            # 提取失败的测试用例
            fail_to_pass = item.get("FAIL_TO_PASS", [])
            pass_to_pass = item.get("PASS_TO_PASS", [])

            # 推断项目信息
            repo_info = {
                "name": repo,
                "language": self._infer_language_from_repo(repo),
                "framework": self._infer_framework_from_repo(repo),
                "base_commit": base_commit,
            }

            # 构建测试命令
            test_command = self._build_test_command(repo)

            # 构建设置命令
            setup_commands = self._build_setup_commands(repo)

            return EvaluationTask(
                task_id=instance_id,
                dataset_name="swe-bench",
                repo_name=repo,
                problem_description=problem_statement,
                failing_tests=fail_to_pass,
                patch_file=patch if patch else None,
                test_command=test_command,
                setup_commands=setup_commands,
                timeout=300,
                repo_info=repo_info,
                ground_truth=patch,
            )

        except Exception as e:
            print(f"[SWEBenchLoader] 转换失败: {e}")
            return None

    def _infer_framework_from_repo(self, repo: str) -> Optional[str]:
        """
        从仓库名推断框架

        Args:
            repo: 仓库名

        Returns:
            Optional[str]: 框架名称
        """
        if "django" in repo.lower():
            return "django"
        elif "flask" in repo.lower():
            return "flask"
        elif "tensorflow" in repo.lower():
            return "tensorflow"
        elif "pytorch" in repo.lower():
            return "pytorch"
        elif "scikit-learn" in repo.lower():
            return "scikit-learn"
        elif "matplotlib" in repo.lower():
            return "matplotlib"
        elif "pandas" in repo.lower():
            return "pandas"
        elif "numpy" in repo.lower():
            return "numpy"
        else:
            return None

    def _build_test_command(self, repo: str) -> str:
        """
        为不同仓库构建测试命令

        Args:
            repo: 仓库名

        Returns:
            str: 测试命令
        """
        if "django" in repo.lower():
            return "python -m pytest tests/ -v"
        elif "flask" in repo.lower():
            return "python -m pytest tests/"
        elif "requests" in repo.lower():
            return "python -m pytest tests/"
        elif "scikit-learn" in repo.lower():
            return "python -m pytest sklearn/ -v"
        elif "sympy" in repo.lower():
            return "python -m pytest sympy/ -v"
        elif "pandas" in repo.lower():
            return "python -m pytest pandas/tests/ -v"
        elif "numpy" in repo.lower():
            return "python -m pytest numpy/tests/ -v"
        elif "matplotlib" in repo.lower():
            return "python -m pytest -v"
        else:
            # 通用命令
            return "python -m pytest . -v"

    def _build_setup_commands(self, repo: str) -> List[str]:
        """
        为不同仓库构建设置命令

        Args:
            repo: 仓库名

        Returns:
            List[str]: 设置命令列表
        """
        commands = []

        # 基础安装
        commands.append("pip install -e .")

        # 仓库特定的设置
        if "django" in repo.lower():
            commands.append("pip install -r requirements/tests.txt")
        elif "flask" in repo.lower():
            commands.append("pip install -e .[dev]")
        elif "requests" in repo.lower():
            commands.append("pip install -r requirements-dev.txt")
        elif "scikit-learn" in repo.lower():
            commands.append("pip install -r requirements.txt")
        elif "pandas" in repo.lower():
            commands.append("pip install -r requirements-dev.txt")
        elif "numpy" in repo.lower():
            commands.append("pip install -r requirements.txt")

        return commands

    def _create_mock_swe_bench_dataset(self) -> bool:
        """
        创建模拟的SWE-bench数据集用于测试

        Returns:
            bool: 创建是否成功
        """
        try:
            print("[SWEBenchLoader] 创建模拟SWE-bench数据集...")

            # 创建testbed目录
            self.testbed_path.mkdir(parents=True, exist_ok=True)

            # 创建模拟的SWE-bench数据
            mock_data = [
                {
                    "instance_id": "django__django-12345",
                    "repo": "django/django",
                    "base_commit": "abc123def456",
                    "problem_statement": "Django的查询集在处理空列表时出现IndexError错误",
                    "patch": "@@ -1,5 +1,5 @@\n class QuerySet:\n     def __getitem__(self, k):\n-        if isinstance(k, slice):\n-            return self._slice(k)\n-        return self._get_obj(k)\n+        if isinstance(k, slice):\n+            return self._slice(k)\n+        if not self.query:\n+            return list()\n+        return self._get_obj(k)",
                    "test_patch": "",
                    "FAIL_TO_PASS": [
                        "tests/queryset/test_empty.py::test_empty_queryset_getitem"
                    ],
                    "PASS_TO_PASS": [
                        "tests/queryset/test_basic.py::test_queryset_creation"
                    ],
                },
                {
                    "instance_id": "psf__requests-67890",
                    "repo": "psf/requests",
                    "base_commit": "def789ghi012",
                    "problem_statement": "requests库在处理重定向时丢失了原始请求的headers",
                    "patch": "@@ -10,3 +10,4 @@\n def resolve_redirects(resp, req, stream=False, timeout=None,\n                         verify=True, cert=None, proxies=None, yield_requests=False,\n                         **adapter_kwargs):\n     new_headers = req.headers.copy()\n+    if 'User-Agent' not in new_headers:\n+        new_headers['User-Agent'] = f'requests/{__version__}'\n     # redirect logic...",
                    "test_patch": "",
                    "FAIL_TO_PASS": [
                        "tests/test_redirects.py::test_header_preservation"
                    ],
                    "PASS_TO_PASS": ["tests/test_basic.py::test_get_request"],
                },
                {
                    "instance_id": "numpy__numpy-13579",
                    "repo": "numpy/numpy",
                    "base_commit": "345678901234",
                    "problem_statement": "numpy数组广播在特定维度下产生意外的结果",
                    "patch": "@@ -25,7 +25,10 @@\n def broadcast_shapes(shape_a, shape_b):\n     # existing logic\n     result_shape = []\n     for dim_a, dim_b in zip(reversed(shape_a), reversed(shape_b)):\n-        result_dim = dim_a if dim_a == 1 else dim_b\n+        if dim_a == 1:\n+            result_dim = dim_b\n+        elif dim_b == 1:\n+            result_dim = dim_a\n+        elif dim_a == dim_b:\n+            result_dim = dim_a\n+        else:\n+            raise ValueError(f'Cannot broadcast shapes {shape_a} and {shape_b}')\n         result_shape.append(result_dim)",
                    "test_patch": "",
                    "FAIL_TO_PASS": [
                        "tests/test_broadcast.py::test_incompatible_shapes"
                    ],
                    "PASS_TO_PASS": ["tests/test_basic.py::test_array_creation"],
                },
                {
                    "instance_id": "matplotlib__matplotlib-24680",
                    "repo": "matplotlib/matplotlib",
                    "base_commit": "567890123456",
                    "problem_statement": "matplotlib的图例在处理重复标签时显示不正确",
                    "patch": "@@ -50,3 +50,6 @@\n def filter_duplicate_labels(handles, labels):\n     seen = set()\n     result = []\n     for h, l in zip(handles, labels):\n         if l not in seen:\n             seen.add(l)\n             result.append((h, l))\n     return result",
                    "test_patch": "",
                    "FAIL_TO_PASS": ["tests/test_legend.py::test_duplicate_labels"],
                    "PASS_TO_PASS": ["tests/test_basic.py::test_legend_creation"],
                },
                {
                    "instance_id": "pallets__flask-98765",
                    "repo": "pallets/flask",
                    "base_commit": "901234567890",
                    "problem_statement": "Flask路由在处理特殊字符时出现编码错误",
                    "patch": "@@ -30,4 +30,5 @@\n def url_quote(segment, charset='utf-8'):\n     try:\n         return quote(segment, safe=SAFE_CHARS, charset=charset)\n-    except UnicodeError:\n+    except (UnicodeError, AttributeError):\n         # fallback to ASCII encoding\n+        segment = str(segment) if not isinstance(segment, str) else segment\n         return quote(segment.encode('ascii', errors='ignore'), safe=SAFE_CHARS)",
                    "test_patch": "",
                    "FAIL_TO_PASS": ["tests/test_routing.py::test_special_characters"],
                    "PASS_TO_PASS": ["tests/test_basic.py::test_route_creation"],
                },
            ]

            # 写入模拟数据到JSON文件
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(mock_data, f, indent=2, ensure_ascii=False)

            print(
                f"[SWEBenchLoader] 模拟SWE-bench数据集创建成功，包含 {len(mock_data)} 个任务"
            )
            print(
                "[SWEBenchLoader] 模拟项目:",
                ", ".join(set(item["repo"].split("/")[0] for item in mock_data)),
            )

            return True

        except Exception as e:
            print(f"[SWEBenchLoader] 创建模拟数据集失败: {e}")
            return False
