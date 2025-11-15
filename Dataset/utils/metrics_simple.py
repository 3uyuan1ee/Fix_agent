"""
简化版指标计算器

不依赖numpy等外部库，提供基础的指标计算功能。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import time
from pathlib import Path

def calculate_basic_metrics(results: List[Any]) -> Dict[str, Any]:
    """计算基础指标，不依赖外部库"""
    if not results:
        return {"error": "No results to analyze"}

    # 假设results是字典列表
    if not isinstance(results, list) or not results:
        return {"error": "Invalid results format"}

    total_tasks = len(results)
    successful_tasks = 0
    failed_tasks = 0
    execution_times = []

    for result in results:
        if isinstance(result, dict):
            if result.get("success", False):
                successful_tasks += 1
                if "execution_time" in result:
                    execution_times.append(result["execution_time"])
            else:
                failed_tasks += 1
        else:
            # 尝试获取success属性
            try:
                if hasattr(result, 'success') and result.success:
                    successful_tasks += 1
                    if hasattr(result, 'execution_time'):
                        execution_times.append(result.execution_time)
                else:
                    failed_tasks += 1
            except:
                failed_tasks += 1

    # 计算基础统计
    avg_time = sum(execution_times) / len(execution_times) if execution_times else 0
    median_time = sorted(execution_times)[len(execution_times)//2] if execution_times else 0

    return {
        "total_tasks": total_tasks,
        "successful_tasks": successful_tasks,
        "failed_tasks": failed_tasks,
        "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
        "failure_rate": failed_tasks / total_tasks if total_tasks > 0 else 0,
        "average_execution_time": avg_time,
        "median_execution_time": median_time,
        "min_execution_time": min(execution_times) if execution_times else 0,
        "max_execution_time": max(execution_times) if execution_times else 0,
        "total_execution_time": sum(execution_time for execution_time in execution_times),
        "tasks_per_hour": len(execution_times) / (sum(execution_times) / 3600) if sum(execution_times) > 0 else 0
    }

@dataclass
class MetricsCalculator:
    """简化版指标计算器"""

    def __init__(self):
        """初始化简化版指标计算器"""
        pass

    def calculate_basic_metrics(self, results: List[Any]) -> Dict[str, Any]:
        """计算基础指标"""
        return calculate_basic_metrics(results)

    def generate_comprehensive_report(self, results: List[Any], results_history: List[List[Any]] = None) -> Dict[str, Any]:
        """生成综合报告"""
        basic_metrics = calculate_basic_metrics(results)

        report = {
            "generation_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "basic_metrics": basic_metrics,
            "analysis": "使用简化版指标计算器",
            "note": "部分高级功能需要安装matplotlib和seaborn等依赖库"
        }

        return report

    def save_metrics_to_file(self, metrics: Dict[str, Any], output_path: str):
        """保存指标到文件"""
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)

        print(f"[MetricsCalculator] 指标已保存到: {output_file}")