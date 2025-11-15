#!/usr/bin/env python3
"""
简单的Dataset模块功能测试
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

def test_basic_imports():
    """测试基本导入功能"""
    print("=" * 50)
    print("Dataset模块简单测试")
    print("=" * 50)

    try:
        # 测试数据类型
        print("1. 测试数据类型导入...")
        from data_types import EvaluationTask, EvaluationResult
        print("   ✓ 数据类型导入成功")

        # 创建一个简单的评估任务
        task = EvaluationTask(
            task_id="test_001",
            dataset_name="test_dataset",
            repo_name="test_repo",
            problem_description="测试问题描述",
            failing_tests=["test_example"],
            test_command="echo 'test'",
            setup_commands=[],
            timeout=60
        )
        print(f"   ✓ 评估任务创建成功: {task.task_id}")

        # 测试工具模块
        print("\n2. 测试工具模块...")

        # 测试简化版工具
        from utils.metrics_simple import MetricsCalculator
        print("   ✓ 简化版指标计算器导入成功")

        from utils.visualization_simple import EvaluationVisualizer
        print("   ✓ 简化版可视化工具导入成功")

        from utils.config import EvaluationConfig, ConfigManager
        print("   ✓ 配置管理工具导入成功")

        # 测试基础功能
        print("\n3. 测试基础功能...")

        # 测试指标计算
        calc = MetricsCalculator()
        test_results = [
            {"success": True, "execution_time": 30.5},
            {"success": False, "execution_time": 45.2},
            {"success": True, "execution_time": 28.7}
        ]
        metrics = calc.calculate_basic_metrics(test_results)
        print(f"   ✓ 指标计算成功: 成功率={metrics['success_rate']:.2%}")

        # 测试配置管理
        config_manager = ConfigManager()
        agent_config = config_manager.get_agent_config()
        eval_config = config_manager.get_evaluation_config()
        print(f"   ✓ 配置加载成功: 代理超时={agent_config.get('timeout', 'default')}秒")
        print(f"   ✓ 评估配置: 最大工作线程={eval_config.get('max_workers', 'default')}")

        print("\n" + "=" * 50)
        print("✅ 所有基础功能测试通过!")
        print("Dataset框架基本功能正常")
        print("=" * 50)

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始Dataset模块基础功能测试...")
    
    if test_basic_imports():
        print("\n🎉 Dataset基础框架完全正常!")
        exit(0)
    else:
        print("\n❌ Dataset基础框架存在问题")
        exit(1)
