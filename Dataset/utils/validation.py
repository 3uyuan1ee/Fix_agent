"""
验证工具模块

提供各种验证功能，包括数据格式验证、预测文件验证等。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..data_types import EvaluationTask


class DatasetValidator:
    """数据集验证器"""

    @staticmethod
    def validate_evaluation_tasks(tasks: List[EvaluationTask]) -> Dict[str, Any]:
        """
        验证评估任务列表

        Args:
            tasks: 评估任务列表

        Returns:
            Dict[str, Any]: 验证结果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "stats": {}
        }

        if not tasks:
            result["errors"].append("任务列表为空")
            result["valid"] = False
            return result

        # 检查每个任务
        for i, task in enumerate(tasks):
            try:
                # 检查必需字段
                if not task.task_id:
                    result["errors"].append(f"任务 {i} 缺少task_id")
                    result["valid"] = False

                if not task.problem_description:
                    result["errors"].append(f"任务 {task.task_id} 缺少问题描述")
                    result["valid"] = False

                if not task.repo_name:
                    result["warnings"].append(f"任务 {task.task_id} 缺少仓库名")

                # 检查超时设置
                if task.timeout <= 0:
                    result["warnings"].append(f"任务 {task.task_id} 超时时间无效: {task.timeout}")

            except Exception as e:
                result["errors"].append(f"验证任务 {i} 时发生错误: {e}")
                result["valid"] = False

        # 统计信息
        result["stats"] = {
            "total_tasks": len(tasks),
            "tasks_with_repo": len([t for t in tasks if t.repo_name]),
            "tasks_with_failing_tests": len([t for t in tasks if t.failing_tests]),
            "average_timeout": sum(t.timeout for t in tasks) / len(tasks) if tasks else 0
        }

        return result

    @staticmethod
    def validate_prediction_format(prediction: Dict[str, Any]) -> bool:
        """
        验证单个预测的格式

        Args:
            prediction: 预测数据

        Returns:
            bool: 格式是否有效
        """
        required_fields = ["instance_id", "model_patch", "model_name_or_path"]

        for field in required_fields:
            if field not in prediction:
                logging.error(f"预测缺少必需字段: {field}")
                return False

        # 检查字段类型
        if not isinstance(prediction["instance_id"], str):
            logging.error("instance_id必须是字符串")
            return False

        if not isinstance(prediction["model_patch"], str):
            logging.error("model_patch必须是字符串")
            return False

        # 检查补丁格式（基本检查）
        patch = prediction["model_patch"].strip()
        if not patch:
            logging.warning("model_patch为空")
            return False

        if not ("--- a/" in patch and "+++" in patch):
            logging.warning("model_patch格式可能不正确")

        return True


class PatchValidator:
    """补丁验证器"""

    @staticmethod
    def validate_patch_structure(patch_content: str) -> Dict[str, Any]:
        """
        验证补丁结构

        Args:
            patch_content: 补丁内容

        Returns:
            Dict[str, Any]: 验证结果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "files_modified": []
        }

        lines = patch_content.split('\n')
        has_file_headers = False
        current_file = None
        has_changes = False

        for line in lines:
            line = line.strip()

            if line.startswith('--- a/'):
                has_file_headers = True
                # 提取文件名
                current_file = line[6:].strip()
                if current_file and current_file not in result["files_modified"]:
                    result["files_modified"].append(current_file)

            elif line.startswith('+++ b/'):
                if current_file:
                    # 更新文件名（可能有重命名）
                    new_file = line[6:].strip()
                    if new_file != current_file:
                        result["files_modified"].append(new_file)
                has_file_headers = True

            elif line.startswith('-') or line.startswith('+'):
                has_changes = True

        # 验证结果
        if not has_file_headers:
            result["errors"].append("补丁缺少文件头（--- a/ 和 +++ b/）")
            result["valid"] = False

        if not has_changes:
            result["warnings"].append("补丁不包含任何变更")

        if not result["files_modified"]:
            result["warnings"].append("未识别到修改的文件")

        return result


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证配置文件

        Args:
            config: 配置数据

        Returns:
            Dict[str, Any]: 验证结果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }

        # 检查agent配置
        if "agent" not in config:
            result["errors"].append("缺少agent配置")
            result["valid"] = False
        else:
            agent_config = config["agent"]

            if "model" not in agent_config:
                result["errors"].append("agent配置缺少model字段")
                result["valid"] = False

            if "api_key" not in agent_config or not agent_config["api_key"]:
                result["warnings"].append("agent配置缺少api_key或api_key为空")

            if "temperature" in agent_config:
                temp = agent_config["temperature"]
                if not isinstance(temp, (int, float)) or temp < 0 or temp > 2:
                    result["warnings"].append(f"temperature值异常: {temp}")

        # 检查evaluation配置
        if "evaluation" in config:
            eval_config = config["evaluation"]

            if "max_workers" in eval_config:
                workers = eval_config["max_workers"]
                if not isinstance(workers, int) or workers < 1:
                    result["warnings"].append(f"max_workers值异常: {workers}")

            if "default_timeout" in eval_config:
                timeout = eval_config["default_timeout"]
                if not isinstance(timeout, (int, float)) or timeout <= 0:
                    result["warnings"].append(f"default_timeout值异常: {timeout}")

        return result


class LogValidator:
    """日志验证器"""

    @staticmethod
    def validate_log_directory(log_dir: str) -> Dict[str, Any]:
        """
        验证日志目录

        Args:
            log_dir: 日志目录路径

        Returns:
            Dict[str, Any]: 验证结果
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "log_files": []
        }

        log_path = Path(log_dir)

        if not log_path.exists():
            result["warnings"].append(f"日志目录不存在: {log_dir}")
            return result

        if not log_path.is_dir():
            result["errors"].append(f"日志路径不是目录: {log_dir}")
            result["valid"] = False
            return result

        # 检查日志文件
        for log_file in log_path.glob("*.log"):
            try:
                # 检查文件是否可读
                if log_file.stat().st_size > 0:
                    result["log_files"].append(str(log_file))
                else:
                    result["warnings"].append(f"日志文件为空: {log_file}")
            except Exception as e:
                result["warnings"].append(f"无法访问日志文件 {log_file}: {e}")

        return result


def validate_all_components(
    tasks: Optional[List[EvaluationTask]] = None,
    config: Optional[Dict[str, Any]] = None,
    predictions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    验证所有组件

    Args:
        tasks: 评估任务列表
        config: 配置数据
        predictions: 预测数据列表

    Returns:
        Dict[str, Any]: 综合验证结果
    """
    result = {
        "overall_valid": True,
        "components": {}
    }

    # 验证任务
    if tasks is not None:
        task_result = DatasetValidator.validate_evaluation_tasks(tasks)
        result["components"]["tasks"] = task_result
        if not task_result["valid"]:
            result["overall_valid"] = False

    # 验证配置
    if config is not None:
        config_result = ConfigValidator.validate_config(config)
        result["components"]["config"] = config_result
        if not config_result["valid"]:
            result["overall_valid"] = False

    # 验证预测
    if predictions is not None:
        pred_results = []
        for i, pred in enumerate(predictions):
            pred_valid = DatasetValidator.validate_prediction_format(pred)
            pred_results.append(pred_valid)
            if not pred_valid:
                result["overall_valid"] = False

        result["components"]["predictions"] = {
            "valid": all(pred_results),
            "total": len(predictions),
            "valid_count": sum(pred_results),
            "invalid_count": len(pred_results) - sum(pred_results)
        }

    return result