"""
SWE-bench Lite数据集加载器 - 简化版本

专门为自动评估设计，去除了自动下载功能，专注于处理手动下载的数据。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..data_types import EvaluationTask


class SWEBenchLiteLoader:
    """
    SWE-bench Lite数据集加载器

    特点：
    - 不自动下载，使用手动下载的数据集
    - 支持SWE-bench Lite格式
    - 提供灵活的采样和过滤
    - 生成标准格式的预测文件
    """

    def __init__(self, dataset_path: str):
        """
        初始化加载器

        Args:
            dataset_path: SWE-bench数据集文件路径
        """
        self.dataset_path = Path(dataset_path)
        self.logger = logging.getLogger("swe_bench_loader")
        self.tasks: List[EvaluationTask] = []

    def validate_dataset(self) -> bool:
        """
        验证数据集文件格式

        Returns:
            bool: 验证是否通过
        """
        try:
            if not self.dataset_path.exists():
                self.logger.error(f"数据集文件不存在: {self.dataset_path}")
                return False

            # 尝试加载并验证格式
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                if self.dataset_path.suffix == '.jsonl':
                    # 验证JSONL格式
                    for i, line in enumerate(f):
                        if i >= 5:  # 只验证前5行
                            break
                        if line.strip():
                            data = json.loads(line)
                            self._validate_task_format(data)
                else:
                    # 验证JSON格式
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data[:5]:  # 只验证前5个
                            self._validate_task_format(item)

            self.logger.info("数据集格式验证通过")
            return True

        except Exception as e:
            self.logger.error(f"数据集验证失败: {e}")
            return False

    def _validate_task_format(self, task_data: Dict[str, Any]) -> None:
        """验证单个任务格式"""
        required_fields = ["instance_id", "repo", "problem_statement", "base_commit"]
        for field in required_fields:
            if field not in task_data:
                raise ValueError(f"缺少必需字段: {field}")

    def load_tasks(
        self,
        sample_size: Optional[int] = None,
        difficulty_filter: Optional[str] = None,
        repo_filter: Optional[List[str]] = None
    ) -> List[EvaluationTask]:
        """
        加载数据集任务

        Args:
            sample_size: 采样数量
            difficulty_filter: 难度过滤器
            repo_filter: 仓库过滤器

        Returns:
            List[EvaluationTask]: 加载的任务列表
        """
        try:
            self.logger.info(f"开始加载数据集: {self.dataset_path}")

            # 验证数据集
            if not self.validate_dataset():
                return []

            # 加载数据
            tasks_data = []

            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                if self.dataset_path.suffix == '.jsonl':
                    # JSONL格式
                    for line in f:
                        if line.strip():
                            tasks_data.append(json.loads(line))
                else:
                    # JSON格式
                    data = json.load(f)
                    if isinstance(data, list):
                        tasks_data = data
                    else:
                        tasks_data = [data]

            self.logger.info(f"原始数据包含 {len(tasks_data)} 个任务")

            # 应用过滤器
            filtered_tasks = self._apply_filters(tasks_data, difficulty_filter, repo_filter)

            # 采样
            if sample_size:
                filtered_tasks = filtered_tasks[:sample_size]

            # 转换为EvaluationTask
            self.tasks = [self._convert_to_evaluation_task(task_data) for task_data in filtered_tasks]

            self.logger.info(f"成功加载 {len(self.tasks)} 个任务")
            return self.tasks

        except Exception as e:
            self.logger.error(f"加载数据集失败: {e}")
            return []

    def _apply_filters(
        self,
        tasks_data: List[Dict[str, Any]],
        difficulty_filter: Optional[str],
        repo_filter: Optional[List[str]]
    ) -> List[Dict[str, Any]]:
        """应用过滤器"""
        filtered = tasks_data

        # 难度过滤器（如果数据中有difficulty字段）
        if difficulty_filter:
            filtered = [
                task for task in filtered
                if task.get("difficulty", "").lower() == difficulty_filter.lower()
            ]

        # 仓库过滤器
        if repo_filter:
            repo_set = set(repo_filter)
            filtered = [
                task for task in filtered
                if any(repo in task.get("repo", "") for repo in repo_set)
            ]

        return filtered

    def _convert_to_evaluation_task(self, task_data: Dict[str, Any]) -> EvaluationTask:
        """将数据转换为EvaluationTask"""
        # 提取测试信息
        failing_tests = task_data.get("FAIL_TO_PASS", [])
        passing_tests = task_data.get("PASS_TO_PASS", [])

        # 构建测试命令
        test_command = self._build_test_command(task_data)

        # 设置超时时间
        timeout = task_data.get("timeout", 300)

        return EvaluationTask(
            task_id=task_data["instance_id"],
            dataset_name="swe-bench-lite",
            repo_name=task_data["repo"],
            problem_description=task_data["problem_statement"],
            failing_tests=failing_tests,
            test_command=test_command,
            timeout=timeout,
            ground_truth=task_data.get("patch"),
            repo_info={
                "base_commit": task_data.get("base_commit"),
                "hints_text": task_data.get("hints_text"),
                "created_at": task_data.get("created_at"),
                "difficulty": task_data.get("difficulty"),
                "test_patch": task_data.get("test_patch")
            }
        )

    def _build_test_command(self, task_data: Dict[str, Any]) -> str:
        """构建测试命令"""
        # 根据仓库类型确定测试命令
        repo = task_data.get("repo", "").lower()

        if "django" in repo:
            return "python manage.py test"
        elif "numpy" in repo:
            return "python -m pytest -xvs"
        elif "requests" in repo:
            return "python -m pytest"
        elif "flask" in repo:
            return "python -m pytest"
        elif "matplotlib" in repo:
            return "python -m pytest"
        elif "seaborn" in repo:
            return "python -m pytest"
        else:
            # 默认使用pytest
            return "python -m pytest -xvs"

    def save_predictions(self, predictions: List[Dict[str, Any]], output_path: str) -> bool:
        """
        保存预测文件

        Args:
            predictions: 预测结果列表
            output_path: 输出文件路径

        Returns:
            bool: 保存是否成功
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 确保预测数据格式正确
            formatted_predictions = []
            for pred in predictions:
                formatted_pred = {
                    "instance_id": pred["instance_id"],
                    "model_patch": pred.get("model_patch", ""),
                    "model_name_or_path": "fix-agent-dataset"
                }
                formatted_predictions.append(formatted_pred)

            # 写入JSONL格式
            with open(output_path, 'w', encoding='utf-8') as f:
                for pred in formatted_predictions:
                    f.write(json.dumps(pred, ensure_ascii=False) + '\n')

            self.logger.info(f"预测文件已保存到: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"保存预测文件失败: {e}")
            return False

    def load_predictions(self, predictions_path: str) -> List[Dict[str, Any]]:
        """
        加载预测文件

        Args:
            predictions_path: 预测文件路径

        Returns:
            List[Dict[str, Any]]: 预测结果列表
        """
        try:
            predictions = []
            with open(predictions_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        pred = json.loads(line)
                        predictions.append(pred)

            self.logger.info(f"加载了 {len(predictions)} 个预测")
            return predictions

        except Exception as e:
            self.logger.error(f"加载预测文件失败: {e}")
            return []

    def get_dataset_stats(self) -> Dict[str, Any]:
        """
        获取数据集统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        if not self.tasks:
            return {}

        repos = {}
        difficulties = {}

        for task in self.tasks:
            repo = task.repo_name
            repos[repo] = repos.get(repo, 0) + 1

            difficulty = task.repo_info.get("difficulty", "unknown")
            difficulties[difficulty] = difficulties.get(difficulty, 0) + 1

        return {
            "total_tasks": len(self.tasks),
            "repositories": repos,
            "difficulties": difficulties,
            "average_timeout": sum(task.timeout for task in self.tasks) / len(self.tasks)
        }


class PredictionValidator:
    """
    预测结果验证器
    """

    @staticmethod
    def validate_predictions(
        predictions: List[Dict[str, Any]],
        dataset_tasks: List[EvaluationTask]
    ) -> Dict[str, Any]:
        """
        验证预测结果的完整性和格式

        Args:
            predictions: 预测结果
            dataset_tasks: 数据集任务

        Returns:
            Dict[str, Any]: 验证结果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {}
        }

        # 检查数量
        dataset_ids = {task.task_id for task in dataset_tasks}
        prediction_ids = {pred["instance_id"] for pred in predictions}

        missing_predictions = dataset_ids - prediction_ids
        extra_predictions = prediction_ids - dataset_ids

        if missing_predictions:
            result["warnings"].append(f"缺少 {len(missing_predictions)} 个预测")
            result["stats"]["missing_predictions"] = len(missing_predictions)

        if extra_predictions:
            result["warnings"].append(f"多出 {len(extra_predictions)} 个预测")
            result["stats"]["extra_predictions"] = len(extra_predictions)

        # 检查预测格式
        for i, pred in enumerate(predictions):
            if "instance_id" not in pred:
                result["errors"].append(f"预测 {i} 缺少 instance_id")
                result["valid"] = False

            if "model_patch" not in pred:
                result["errors"].append(f"预测 {i} 缺少 model_patch")
                result["valid"] = False

        result["stats"]["total_predictions"] = len(predictions)
        result["stats"]["valid_predictions"] = len([p for p in predictions if p.get("model_patch")])

        return result