"""
数据类型定义

为了避免循环导入问题，将数据类型定义在这里。
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any

@dataclass
class EvaluationTask:
    """评估任务定义"""
    task_id: str
    dataset_name: str
    repo_name: str
    problem_description: str
    failing_tests: List[str]
    patch_file: Optional[str] = None
    test_command: Optional[str] = None
    setup_commands: List[str] = None
    timeout: int = 300
    workspace_path: Optional[str] = None
    repo_info: Optional[Dict[str, Any]] = None
    ground_truth: Optional[str] = None  # 正确的修复补丁（用于对比）

@dataclass
class EvaluationResult:
    """评估结果"""
    task_id: str
    dataset_name: str
    success: bool
    execution_time: float
    agent_response: Optional[Any] = None
    test_results: Dict[str, Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class EvaluationSummary:
    """评估摘要"""
    dataset_name: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    success_rate: float
    average_execution_time: float
    total_execution_time: float
    tasks_per_hour: float
    error_analysis: Dict[str, Any]
    performance_metrics: Dict[str, Any]