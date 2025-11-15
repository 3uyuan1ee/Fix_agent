"""
评估指标计算器

提供全面的评估指标计算和分析功能。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import json
import time
from pathlib import Path

from ..core.evaluation import EvaluationResult, EvaluationSummary

@dataclass
class PerformanceMetrics:
    """性能指标"""
    success_rate: float
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    average_execution_time: float
    median_execution_time: float
    tasks_per_hour: float
    error_rate: float

@dataclass
class ErrorAnalysis:
    """错误分析结果"""
    total_errors: int
    error_types: Dict[str, int]
    error_by_dataset: Dict[str, Dict[str, int]]
    error_by_phase: Dict[str, int]
    most_common_errors: List[Tuple[str, int]]

class MetricsCalculator:
    """
    评估指标计算器

    提供全面的指标计算功能，包括：
    - 基础成功率统计
    - 性能指标分析
    - 错误模式分析
    - 时间分布分析
    - 数据集对比分析
    """

    def __init__(self):
        self.results_history = []

    def calculate_basic_metrics(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        计算基础指标

        Args:
            results: 评估结果列表

        Returns:
            Dict[str, Any]: 基础指标
        """
        if not results:
            return {"error": "No results to analyze"}

        total_tasks = len(results)
        successful_tasks = sum(1 for r in results if r.success)
        failed_tasks = total_tasks - successful_tasks

        execution_times = [r.execution_time for r in results if r.execution_time > 0]

        return {
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "failure_rate": failed_tasks / total_tasks if total_tasks > 0 else 0,
            "average_execution_time": np.mean(execution_times) if execution_times else 0,
            "median_execution_time": np.median(execution_times) if execution_times else 0,
            "min_execution_time": np.min(execution_times) if execution_times else 0,
            "max_execution_time": np.max(execution_times) if execution_times else 0,
            "std_execution_time": np.std(execution_times) if execution_times else 0,
            "total_execution_time": sum(execution_times),
            "tasks_per_hour": len(execution_times) / (sum(execution_times) / 3600) if sum(execution_times) > 0 else 0
        }

    def calculate_performance_metrics(self, results: List[EvaluationResult]) -> PerformanceMetrics:
        """
        计算详细性能指标

        Args:
            results: 评估结果列表

        Returns:
            PerformanceMetrics: 性能指标
        """
        basic_metrics = self.calculate_basic_metrics(results)

        # 计算精确率、召回率等指标（如果有真值标签）
        precision, recall, f1_score = self._calculate_classification_metrics(results)

        return PerformanceMetrics(
            success_rate=basic_metrics["success_rate"],
            accuracy=basic_metrics["success_rate"],  # 在这个场景下accuracy = success_rate
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            average_execution_time=basic_metrics["average_execution_time"],
            median_execution_time=basic_metrics["median_execution_time"],
            tasks_per_hour=basic_metrics["tasks_per_hour"],
            error_rate=basic_metrics["failure_rate"]
        )

    def analyze_errors(self, results: List[EvaluationResult]) -> ErrorAnalysis:
        """
        分析错误模式

        Args:
            results: 评估结果列表

        Returns:
            ErrorAnalysis: 错误分析结果
        """
        error_analysis = {
            "total_errors": 0,
            "error_types": {},
            "error_by_dataset": {},
            "error_by_phase": {},
            "most_common_errors": []
        }

        failed_results = [r for r in results if not r.success]

        for result in failed_results:
            error_analysis["total_errors"] += 1

            # 错误类型分析
            error_msg = result.error or "Unknown error"
            error_analysis["error_types"][error_msg] = error_analysis["error_types"].get(error_msg, 0) + 1

            # 按数据集分析
            dataset = result.dataset_name
            if dataset not in error_analysis["error_by_dataset"]:
                error_analysis["error_by_dataset"][dataset] = {}
            error_analysis["error_by_dataset"][dataset][error_msg] = error_analysis["error_by_dataset"][dataset].get(error_msg, 0) + 1

            # 按阶段分析
            phase = self._determine_error_phase(result)
            error_analysis["error_by_phase"][phase] = error_analysis["error_by_phase"].get(phase, 0) + 1

        # 最常见的错误
        error_analysis["most_common_errors"] = sorted(
            error_analysis["error_types"].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return ErrorAnalysis(**error_analysis)

    def analyze_time_distribution(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        分析执行时间分布

        Args:
            results: 评估结果列表

        Returns:
            Dict[str, Any]: 时间分布分析
        """
        execution_times = [r.execution_time for r in results if r.execution_time > 0]

        if not execution_times:
            return {"error": "No execution time data available"}

        # 时间分布统计
        distribution = {
            "under_30s": len([t for t in execution_times if t < 30]),
            "30s_to_60s": len([t for t in execution_times if 30 <= t < 60]),
            "60s_to_120s": len([t for t in execution_times if 60 <= t < 120]),
            "120s_to_300s": len([t for t in execution_times if 120 <= t < 300]),
            "over_300s": len([t for t in execution_times if t >= 300])
        }

        # 成功率与时间的关系
        success_time_data = []
        for result in results:
            if result.execution_time > 0:
                success_time_data.append({
                    "success": result.success,
                    "time": result.execution_time
                })

        # 时间与成功率的相关性
        successful_times = [d["time"] for d in success_time_data if d["success"]]
        failed_times = [d["time"] for d in success_time_data if not d["success"]]

        return {
            "basic_stats": {
                "mean": np.mean(execution_times),
                "median": np.median(execution_times),
                "std": np.std(execution_times),
                "min": np.min(execution_times),
                "max": np.max(execution_times),
                "q25": np.percentile(execution_times, 25),
                "q75": np.percentile(execution_times, 75)
            },
            "distribution": distribution,
            "success_time_correlation": {
                "successful_mean": np.mean(successful_times) if successful_times else 0,
                "failed_mean": np.mean(failed_times) if failed_times else 0,
                "successful_median": np.median(successful_times) if successful_times else 0,
                "failed_median": np.median(failed_times) if failed_times else 0
            }
        }

    def compare_datasets(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """
        比较不同数据集的性能

        Args:
            results: 评估结果列表

        Returns:
            Dict[str, Any]: 数据集对比结果
        """
        # 按数据集分组
        dataset_groups = {}
        for result in results:
            dataset = result.dataset_name
            if dataset not in dataset_groups:
                dataset_groups[dataset] = []
            dataset_groups[dataset].append(result)

        # 计算每个数据集的指标
        dataset_metrics = {}
        for dataset, dataset_results in dataset_groups.items():
            metrics = self.calculate_basic_metrics(dataset_results)
            metrics["error_analysis"] = self.analyze_errors(dataset_results)._asdict()
            dataset_metrics[dataset] = metrics

        # 计算相对性能
        if len(dataset_metrics) > 1:
            best_success_rate = max(metrics["success_rate"] for metrics in dataset_metrics.values())
            best_speed = min(metrics["average_execution_time"] for metrics in dataset_metrics.values())

            for dataset, metrics in dataset_metrics.items():
                metrics["relative_success_rate"] = metrics["success_rate"] / best_success_rate
                metrics["relative_speed"] = best_speed / metrics["average_execution_time"] if metrics["average_execution_time"] > 0 else 0

        return {
            "dataset_count": len(dataset_groups),
            "dataset_metrics": dataset_metrics,
            "overall_best": {
                "success_rate": max(dataset_metrics.items(), key=lambda x: x[1]["success_rate"])[0] if dataset_metrics else None,
                "speed": min(dataset_metrics.items(), key=lambda x: x[1]["average_execution_time"])[0] if dataset_metrics else None
            }
        }

    def calculate_trend_analysis(self, results_history: List[List[EvaluationResult]]) -> Dict[str, Any]:
        """
        计算趋势分析

        Args:
            results_history: 历史评估结果列表

        Returns:
            Dict[str, Any]: 趋势分析结果
        """
        if len(results_history) < 2:
            return {"error": "需要至少2个时间点的数据才能进行趋势分析"}

        # 计算每个时间点的指标
        time_series = []
        for i, results in enumerate(results_history):
            metrics = self.calculate_basic_metrics(results)
            metrics["timestamp"] = i
            time_series.append(metrics)

        # 计算趋势
        success_rates = [point["success_rate"] for point in time_series]
        execution_times = [point["average_execution_time"] for point in time_series]

        # 简单线性趋势计算
        def calculate_trend(values):
            if len(values) < 2:
                return 0
            x = list(range(len(values)))
            return np.polyfit(x, values, 1)[0]  # 斜率

        return {
            "time_series": time_series,
            "trends": {
                "success_rate_trend": calculate_trend(success_rates),
                "execution_time_trend": calculate_trend(execution_times),
                "success_rate_change": success_rates[-1] - success_rates[0],
                "execution_time_change": execution_times[-1] - execution_times[0]
            },
            "improvement": {
                "success_rate_improved": success_rates[-1] > success_rates[0],
                "speed_improved": execution_times[-1] < execution_times[0],
                "success_rate_improvement_pct": (success_rates[-1] - success_rates[0]) / success_rates[0] * 100 if success_rates[0] > 0 else 0,
                "speed_improvement_pct": (execution_times[0] - execution_times[-1]) / execution_times[0] * 100 if execution_times[0] > 0 else 0
            }
        }

    def generate_comprehensive_report(self, results: List[EvaluationResult], results_history: List[List[EvaluationResult]] = None) -> Dict[str, Any]:
        """
        生成综合评估报告

        Args:
            results: 当前评估结果
            results_history: 历史评估结果

        Returns:
            Dict[str, Any]: 综合报告
        """
        report = {
            "generation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "basic_metrics": self.calculate_basic_metrics(results),
            "performance_metrics": self.calculate_performance_metrics(results)._asdict(),
            "error_analysis": self.analyze_errors(results)._asdict(),
            "time_distribution": self.analyze_time_distribution(results),
            "dataset_comparison": self.compare_datasets(results)
        }

        # 添加趋势分析（如果有历史数据）
        if results_history:
            report["trend_analysis"] = self.calculate_trend_analysis(results_history)

        # 添加建议
        report["recommendations"] = self._generate_recommendations(results)

        return report

    def _calculate_classification_metrics(self, results: List[EvaluationResult]) -> Tuple[float, float, float]:
        """
        计算分类指标（精确率、召回率、F1分数）

        Args:
            results: 评估结果列表

        Returns:
            Tuple[float, float, float]: (precision, recall, f1_score)
        """
        # 在没有真值标签的情况下，这些指标可能与成功率相同
        # 这里提供基础实现，可以根据需要扩展
        successful_tasks = sum(1 for r in results if r.success)
        total_tasks = len(results)

        if total_tasks == 0:
            return 0.0, 0.0, 0.0

        # 简化实现：假设成功率 = 精确率 = 召回率
        success_rate = successful_tasks / total_tasks
        precision = success_rate
        recall = success_rate
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return precision, recall, f1_score

    def _determine_error_phase(self, result: EvaluationResult) -> str:
        """
        确定错误发生的阶段

        Args:
            result: 评估结果

        Returns:
            str: 错误阶段
        """
        error_msg = result.error or ""

        if "agent" in error_msg.lower():
            return "agent_execution"
        elif "test" in error_msg.lower() or "compilation" in error_msg.lower():
            return "testing"
        elif "setup" in error_msg.lower() or "environment" in error_msg.lower():
            return "setup"
        elif "timeout" in error_msg.lower():
            return "timeout"
        else:
            return "other"

    def _generate_recommendations(self, results: List[EvaluationResult]) -> List[str]:
        """
        生成改进建议

        Args:
            results: 评估结果列表

        Returns:
            List[str]: 改进建议列表
        """
        recommendations = []
        basic_metrics = self.calculate_basic_metrics(results)
        error_analysis = self.analyze_errors(results)

        success_rate = basic_metrics["success_rate"]
        avg_time = basic_metrics["average_execution_time"]

        # 成功率建议
        if success_rate < 0.5:
            recommendations.append("成功率较低（<50%），建议检查agent的核心逻辑和错误处理机制")
        elif success_rate < 0.7:
            recommendations.append("成功率中等（50-70%），建议优化缺陷检测和修复算法")
        elif success_rate < 0.9:
            recommendations.append("成功率较高（70-90%），建议处理边界情况和特殊情况")

        # 性能建议
        if avg_time > 300:
            recommendations.append("平均执行时间较长（>5分钟），建议优化算法复杂度和并发处理")
        elif avg_time > 120:
            recommendations.append("执行时间偏长（>2分钟），可以考虑缓存和预处理优化")

        # 错误分析建议
        most_common_error = error_analysis.most_common_errors[0] if error_analysis.most_common_errors else None
        if most_common_error and most_common_error[1] > len(results) * 0.2:
            recommendations.append(f"最常见错误：{most_common_error[0]}（出现{most_common_error[1]}次），建议针对性解决")

        # 阶段建议
        if error_analysis.error_by_phase.get("agent_execution", 0) > len(results) * 0.3:
            recommendations.append("agent执行阶段错误较多，建议增强错误处理和异常恢复机制")

        if error_analysis.error_by_phase.get("testing", 0) > len(results) * 0.2:
            recommendations.append("测试阶段错误较多，建议改进测试环境配置和测试用例设计")

        return recommendations

    def save_metrics_to_file(self, metrics: Dict[str, Any], output_path: str):
        """
        保存指标到文件

        Args:
            metrics: 指标数据
            output_path: 输出文件路径
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)

        print(f"[MetricsCalculator] 指标已保存到: {output_file}")