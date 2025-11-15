"""
BugsInPy数据集加载器

BugsInPy是一个专注于Python项目bug修复的数据集，
包含真实的项目bug和对应的修复补丁。
"""

import json
import os
import shutil
import subprocess
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


class BugsInPyLoader(BaseDatasetLoader):
    """
    BugsInPy数据集加载器

    特点：
    - 专门针对Python项目
    - 包含完整的bug生命周期数据
    - 支持项目级别的缓存
    - 提供bug类型分类
    """

    def __init__(
        self, dataset_path: str = "./datasets/BugsInPy", cache_dir: str = None
    ):
        super().__init__(dataset_path, cache_dir)
        self.bugs_dir = self.dataset_path / "bugs"
        self.metadata_file = self.dataset_path / "metadata.json"

    def download_dataset(self) -> bool:
        """
        下载BugsInPy数据集

        Returns:
            bool: 下载是否成功
        """
        print("[BugsInPyLoader] 开始下载BugsInPy数据集...")

        try:
            # 创建数据集目录
            self.dataset_path.mkdir(parents=True, exist_ok=True)

            # 克隆仓库 - 尝试多个可能的地址
            if not (self.dataset_path / "BugsInPy").exists():
                print("[BugsInPyLoader] 克隆BugsInPy仓库...")

                # 尝试多个仓库地址
                repo_urls = [
                    "git@github.com:soarsanu/BugsInPy.git",
                    "git@github.com:wenmin-wu/BugsInPy.git",
                    "https://github.com/soarsanu/BugsInPy.git",
                    "https://github.com/wenmin-wu/BugsInPy.git",
                ]

                clone_success = False
                for repo_url in repo_urls:
                    print(f"[BugsInPyLoader] 尝试克隆: {repo_url}")
                    result = subprocess.run(
                        ["git", "clone", repo_url, str(self.dataset_path / "BugsInPy")],
                        capture_output=True,
                        text=True,
                    )

                    if result.returncode == 0:
                        print(f"[BugsInPyLoader] 成功克隆: {repo_url}")
                        clone_success = True
                        break
                    else:
                        print(f"[BugsInPyLoader] 克隆失败: {repo_url}")
                        print(f"[BugsInPyLoader] 错误信息: {result.stderr.strip()}")

                if not clone_success:
                    print(
                        "[BugsInPyLoader] 所有仓库地址都无法访问，将创建模拟数据集结构"
                    )
                    print(
                        "[BugsInPyLoader] 注意: 这是用于测试的模拟数据，不包含真实的bug数据"
                    )

                    # 创建模拟的BugsInPy数据结构
                    return self._create_mock_dataset()

                # 移动文件到正确位置
                bugs_in_py_dir = self.dataset_path / "BugsInPy"
                for item in bugs_in_py_dir.iterdir():
                    if item.name != ".git":
                        target = self.dataset_path / item.name
                        if item.is_dir():
                            shutil.move(str(item), str(target))
                        else:
                            shutil.move(str(item), str(target))

                # 删除空目录
                bugs_in_py_dir.rmdir()

            # 下载项目数据
            download_script = self.dataset_path / "download_data.py"
            if download_script.exists():
                print("[BugsInPyLoader] 下载项目数据...")
                result = subprocess.run(
                    ["python", str(download_script)],
                    cwd=self.dataset_path,
                    capture_output=True,
                    text=True,
                )

                if result.returncode != 0:
                    print(f"[BugsInPyLoader] 下载数据失败: {result.stderr}")
                    # 不返回False，因为可能部分数据已下载

            print("[BugsInPyLoader] 数据集下载完成")
            return True

        except Exception as e:
            print(f"[BugsInPyLoader] 下载失败: {e}")
            return False

    def load_tasks(
        self,
        sample_size: int = None,
        difficulty_filter: str = None,
        bug_type_filter: str = None,
    ) -> List[EvaluationTask]:
        """
        加载BugsInPy评估任务

        Args:
            sample_size: 采样大小
            difficulty_filter: 难度过滤器
            bug_type_filter: Bug类型过滤器

        Returns:
            List[EvaluationTask]: 评估任务列表
        """
        print(
            f"[BugsInPyLoader] 加载任务，样本大小: {sample_size}, 难度过滤: {difficulty_filter}, Bug类型过滤: {bug_type_filter}"
        )

        # 检查缓存
        cache_key = (
            f"bugsinpy_tasks_{sample_size}_{difficulty_filter}_{bug_type_filter}"
        )
        cached_tasks = self.load_cache(cache_key)
        if cached_tasks:
            print(f"[BugsInPyLoader] 从缓存加载 {len(cached_tasks)} 个任务")
            return [EvaluationTask(**task) for task in cached_tasks]

        # 验证数据集
        if not self.validate_dataset():
            raise RuntimeError("数据集验证失败")

        # 加载所有bug数据
        all_tasks = []

        if not self.bugs_dir.exists():
            print(f"[BugsInPyLoader] bugs目录不存在: {self.bugs_dir}")
            return []

        # 遍历所有项目
        for project_dir in self.bugs_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name
            print(f"[BugsInPyLoader] 处理项目: {project_name}")

            # 遍历项目中的所有bug
            for bug_dir in project_dir.iterdir():
                if not bug_dir.is_dir():
                    continue

                try:
                    task = self._load_single_bug(project_name, bug_dir)
                    if task:
                        # 应用过滤器
                        if self._should_include_task(
                            task, difficulty_filter, bug_type_filter
                        ):
                            all_tasks.append(task)
                except Exception as e:
                    print(f"[BugsInPyLoader] 加载bug失败 {bug_dir.name}: {e}")

        print(f"[BugsInPyLoader] 原始数据集大小: {len(all_tasks)}")

        # 采样
        if sample_size and sample_size < len(all_tasks):
            import random

            random.seed(42)  # 确保可重现
            all_tasks = random.sample(all_tasks, sample_size)

        print(f"[BugsInPyLoader] 成功加载 {len(all_tasks)} 个任务")

        # 保存缓存
        self.save_cache(cache_key, [task.__dict__ for task in all_tasks])

        return all_tasks

    def get_dataset_info(self) -> Dict[str, Any]:
        """
        获取BugsInPy数据集信息

        Returns:
            Dict[str, Any]: 数据集信息
        """
        if not self.validate_dataset():
            return {"error": "数据集不可用"}

        # 统计信息
        projects = {}
        bug_types = {}
        total_bugs = 0

        for project_dir in self.bugs_dir.iterdir():
            if not project_dir.is_dir():
                continue

            project_name = project_dir.name
            bug_count = len([d for d in project_dir.iterdir() if d.is_dir()])
            projects[project_name] = bug_count
            total_bugs += bug_count

        # 从bug.json文件中读取bug类型统计
        bug_types = self._analyze_bug_types()

        return {
            "name": "BugsInPy",
            "version": "1.0",
            "total_bugs": total_bugs,
            "projects": projects,
            "bug_types": bug_types,
            "path": str(self.dataset_path),
            "description": "Real-world Python bugs with verified fixes",
        }

    def get_required_files(self) -> List[str]:
        """
        获取BugsInPy必需的文件列表

        Returns:
            List[str]: 必需文件列表
        """
        # 对于模拟数据集，只需要基础文件
        mock_metadata = self.dataset_path / "metadata.json"
        if mock_metadata.exists():
            return ["metadata.json", "bugs"]

        # 对于模拟数据集，只需要基础文件
        mock_metadata = self.dataset_path / "metadata.json"
        if mock_metadata.exists():
            return ["metadata.json", "bugs"]

        return ["download_data.py", "README.md"]

    def validate_dataset(self) -> bool:
        """
        验证数据集是否完整（重写以支持模拟数据集）

        Returns:
            bool: 数据集是否有效
        """
        if not self.dataset_path.exists():
            print(f"[BugsInPyLoader] 数据集路径不存在: {self.dataset_path}")
            return False

        # 检查是否是模拟数据集
        mock_metadata = self.dataset_path / "metadata.json"
        bugs_dir = self.dataset_path / "bugs"

        if mock_metadata.exists() and bugs_dir.exists():
            try:
                with open(mock_metadata, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                if metadata.get("version") == "1.0-mock":
                    print("[BugsInPyLoader] 检测到模拟数据集，验证通过")
                    return True
            except Exception:
                pass

        # 检查关键文件（原始逻辑）
        required_files = self.get_required_files()
        for file_path in required_files:
            if not (self.dataset_path / file_path).exists():
                print(f"[BugsInPyLoader] 缺少必要文件: {file_path}")
                return False

        return True

    def _load_single_bug(
        self, project_name: str, bug_dir: Path
    ) -> Optional[EvaluationTask]:
        """
        加载单个bug

        Args:
            project_name: 项目名称
            bug_dir: bug目录

        Returns:
            Optional[EvaluationTask]: 评估任务
        """
        # 读取bug元数据
        bug_json = bug_dir / "bug.json"
        if not bug_json.exists():
            print(f"[BugsInPyLoader] bug.json不存在: {bug_json}")
            return None

        with open(bug_json, "r", encoding="utf-8") as f:
            bug_info = json.load(f)

        # 读取失败的测试
        failing_test_file = bug_dir / "failing_test.txt"
        failing_tests = []
        if failing_test_file.exists():
            with open(failing_test_file, "r", encoding="utf-8") as f:
                failing_tests = [line.strip() for line in f if line.strip()]

        # 检查patch文件
        patch_file = bug_dir / "patch.txt"
        patch_path = str(patch_file) if patch_file.exists() else None

        # 构建task_id
        bug_id = bug_dir.name
        task_id = f"{project_name}_{bug_id}"

        # 推断项目信息
        repo_info = {
            "name": project_name,
            "language": "python",
            "framework": self._infer_framework_from_project(project_name),
            "bug_type": bug_info.get("type", "unknown"),
            "severity": bug_info.get("severity", "unknown"),
        }

        # 构建测试命令
        test_command = self._build_test_command_for_project(project_name)

        # 构建设置命令
        setup_commands = self._build_setup_commands_for_project(project_name)

        return EvaluationTask(
            task_id=task_id,
            dataset_name="bugsinpy",
            repo_name=project_name,
            problem_description=bug_info.get("description", ""),
            failing_tests=failing_tests,
            patch_file=patch_path,
            test_command=test_command,
            setup_commands=setup_commands,
            timeout=300,
            repo_info=repo_info,
            ground_truth=patch_path,
        )

    def _infer_framework_from_project(self, project_name: str) -> Optional[str]:
        """
        从项目名推断框架

        Args:
            project_name: 项目名称

        Returns:
            Optional[str]: 框架名称
        """
        framework_mapping = {
            "django": "django",
            "flask": "flask",
            "requests": "requests",
            "celery": "celery",
            "pandas": "pandas",
            "numpy": "numpy",
            "scipy": "scipy",
            "sphinx": "sphinx",
            "sqlalchemy": "sqlalchemy",
            "tornado": "tornado",
        }

        for framework, mapped_framework in framework_mapping.items():
            if framework in project_name.lower():
                return mapped_framework

        return None

    def _build_test_command_for_project(self, project_name: str) -> str:
        """
        为不同项目构建测试命令

        Args:
            project_name: 项目名称

        Returns:
            str: 测试命令
        """
        if "django" in project_name.lower():
            return "python -m pytest tests/ -v"
        elif "flask" in project_name.lower():
            return "python -m pytest tests/"
        elif "requests" in project_name.lower():
            return "python -m pytest tests/"
        elif "celery" in project_name.lower():
            return "python -m pytest t/unit/"
        elif "pandas" in project_name.lower():
            return "python -m pytest pandas/tests/"
        elif "numpy" in project_name.lower():
            return "python -m pytest numpy/tests/"
        elif "scipy" in project_name.lower():
            return "python -m pytest scipy/tests/"
        elif "sphinx" in project_name.lower():
            return "python -m pytest tests/"
        else:
            # 通用命令
            return "python -m pytest . -v"

    def _build_setup_commands_for_project(self, project_name: str) -> List[str]:
        """
        为不同项目构建设置命令

        Args:
            project_name: 项目名称

        Returns:
            List[str]: 设置命令列表
        """
        commands = ["pip install -e ."]

        # 项目特定的设置
        if "django" in project_name.lower():
            commands.extend(
                ["pip install -r requirements/tests.txt", "pip install pytest-django"]
            )
        elif "flask" in project_name.lower():
            commands.append("pip install -e .[dev]")
        elif "requests" in project_name.lower():
            commands.append("pip install -r requirements-dev.txt")
        elif "celery" in project_name.lower():
            commands.append("pip install -e .[test]")
        elif "pandas" in project_name.lower():
            commands.append("pip install -r requirements-dev.txt")
        elif "numpy" in project_name.lower():
            commands.append("pip install -r requirements.txt")

        return commands

    def _should_include_task(
        self, task: EvaluationTask, difficulty_filter: str, bug_type_filter: str
    ) -> bool:
        """
        判断是否应该包含该任务

        Args:
            task: 评估任务
            difficulty_filter: 难度过滤器
            bug_type_filter: Bug类型过滤器

        Returns:
            bool: 是否包含
        """
        # 应用难度过滤器
        if difficulty_filter:
            difficulty = self._estimate_difficulty(task)
            if difficulty != difficulty_filter:
                return False

        # 应用bug类型过滤器
        if bug_type_filter:
            bug_type = task.repo_info.get("bug_type", "unknown")
            if bug_type != bug_type_filter:
                return False

        return True

    def _estimate_difficulty(self, task: EvaluationTask) -> str:
        """
        估算任务难度

        Args:
            task: 评估任务

        Returns:
            str: 难度级别
        """
        # 基于多个因素估算难度
        factors = []

        # 1. 失败测试数量
        test_count = len(task.failing_tests)
        if test_count <= 2:
            factors.append("easy")
        elif test_count <= 5:
            factors.append("medium")
        else:
            factors.append("hard")

        # 2. 问题描述长度
        desc_length = len(task.problem_description)
        if desc_length <= 200:
            factors.append("easy")
        elif desc_length <= 500:
            factors.append("medium")
        else:
            factors.append("hard")

        # 3. 项目复杂度（基于项目名）
        complex_projects = ["django", "numpy", "scipy", "pandas"]
        if any(project in task.repo_name.lower() for project in complex_projects):
            factors.append("hard")

        # 综合判断
        if factors.count("hard") >= 2:
            return "hard"
        elif factors.count("medium") >= 2:
            return "medium"
        else:
            return "easy"

    def _analyze_bug_types(self) -> Dict[str, int]:
        """
        分析bug类型分布

        Returns:
            Dict[str, int]: bug类型统计
        """
        bug_types = {}

        for project_dir in self.bugs_dir.iterdir():
            if not project_dir.is_dir():
                continue

            for bug_dir in project_dir.iterdir():
                if not bug_dir.is_dir():
                    continue

                bug_json = bug_dir / "bug.json"
                if bug_json.exists():
                    try:
                        with open(bug_json, "r", encoding="utf-8") as f:
                            bug_info = json.load(f)
                            bug_type = bug_info.get("type", "unknown")
                            bug_types[bug_type] = bug_types.get(bug_type, 0) + 1
                    except Exception:
                        bug_types["unknown"] = bug_types.get("unknown", 0) + 1

        return bug_types

    def _create_mock_dataset(self) -> bool:
        """
        创建模拟的BugsInPy数据集结构用于测试

        Returns:
            bool: 创建是否成功
        """
        try:
            print("[BugsInPyLoader] 创建模拟数据集结构...")

            # 创建基础目录结构
            bugs_dir = self.dataset_path / "bugs"
            bugs_dir.mkdir(parents=True, exist_ok=True)

            # 创建模拟的项目和bug
            mock_projects = {
                "django": [
                    {
                        "id": "bug_001",
                        "type": "authentication",
                        "severity": "medium",
                        "description": "Django认证系统中的密码验证存在问题",
                        "failing_tests": [
                            "tests/test_auth.py::test_password_validation"
                        ],
                        "patch": "@@ -15,2 +15,2 @@\n def validate_password(password, user):\n-    return len(password) >= 6\n+    return len(password) >= 8 and any(c.isdigit() for c in password)",
                    },
                    {
                        "id": "bug_002",
                        "type": "sql_injection",
                        "severity": "high",
                        "description": "查询构建器中存在SQL注入漏洞",
                        "failing_tests": ["tests/test_sql.py::test_query_sanitization"],
                        "patch": '@@ -25,1 +25,1 @@\n def build_query(table, where_clause):\n-    return f"SELECT * FROM {table} WHERE {where_clause}"\n+    return f"SELECT * FROM {table} WHERE {sanitize_input(where_clause)}"',
                    },
                ],
                "flask": [
                    {
                        "id": "bug_001",
                        "type": "routing",
                        "severity": "low",
                        "description": "路由参数匹配过于宽泛",
                        "failing_tests": ["tests/test_routing.py::test_route_matching"],
                        "patch": "@@ -10,1 +10,1 @@\n @app.route('/user/<username>')\n-    def user_profile(username):\n+    def user_profile(username: str):",
                    }
                ],
                "requests": [
                    {
                        "id": "bug_001",
                        "type": "timeout",
                        "severity": "medium",
                        "description": "长时间请求未正确处理超时",
                        "failing_tests": [
                            "tests/test_timeout.py::test_request_timeout"
                        ],
                        "patch": "@@ -45,2 +45,3 @@\n def send_request(url, timeout=None):\n     if timeout is None:\n         timeout = 30\n+    import signal\n+    signal.alarm(timeout + 5)",
                    }
                ],
            }

            # 为每个项目创建模拟数据
            for project_name, bugs in mock_projects.items():
                project_dir = bugs_dir / project_name
                project_dir.mkdir(exist_ok=True)

                for bug_data in bugs:
                    bug_dir = project_dir / bug_data["id"]
                    bug_dir.mkdir(exist_ok=True)

                    # 创建bug.json
                    bug_info = {
                        "type": bug_data["type"],
                        "severity": bug_data["severity"],
                        "description": bug_data["description"],
                    }
                    with open(bug_dir / "bug.json", "w", encoding="utf-8") as f:
                        json.dump(bug_info, f, indent=2)

                    # 创建failing_test.txt
                    with open(bug_dir / "failing_test.txt", "w", encoding="utf-8") as f:
                        f.write("\n".join(bug_data["failing_tests"]) + "\n")

                    # 创建patch.txt
                    with open(bug_dir / "patch.txt", "w", encoding="utf-8") as f:
                        f.write(bug_data["patch"])

            # 创建metadata.json
            metadata = {
                "version": "1.0-mock",
                "description": "模拟BugsInPy数据集，用于测试目的",
                "projects": list(mock_projects.keys()),
                "total_bugs": sum(len(bugs) for bugs in mock_projects.values()),
                "note": "这不是真实的BugsInPy数据集，仅用于测试框架功能",
            }
            with open(self.dataset_path / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)

            print(
                f"[BugsInPyLoader] 模拟数据集创建成功，包含 {metadata['total_bugs']} 个bug"
            )
            print("[BugsInPyLoader] 模拟项目:", ", ".join(mock_projects.keys()))

            return True

        except Exception as e:
            print(f"[BugsInPyLoader] 创建模拟数据集失败: {e}")
            return False
