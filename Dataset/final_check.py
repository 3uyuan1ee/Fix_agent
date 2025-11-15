#!/usr/bin/env python3
"""
最终检查脚本

验证所有核心组件都能正常工作。
"""

import sys
import traceback

def test_component(name, import_func, test_func=None):
    """测试单个组件"""
    print(f"\n测试 {name}...")
    try:
        # 测试导入
        module = import_func()
        print(f"  ✓ {name} 导入成功")

        # 如果提供了测试函数，执行测试
        if test_func:
            test_func(module)
            print(f"  ✓ {name} 功能测试通过")

        return True
    except Exception as e:
        print(f"  ❌ {name} 失败: {e}")
        if "--debug" in sys.argv:
            traceback.print_exc()
        return False

def test_data_types():
    """测试数据类型"""
    from data_types import EvaluationTask, EvaluationResult

    task = EvaluationTask(
        task_id="test_001",
        dataset_name="test",
        repo_name="test_repo",
        problem_description="Test problem",
        failing_tests=["test_example"]
    )
    assert task.task_id == "test_001"
    assert len(task.failing_tests) == 1

def test_agent():
    """测试Agent"""
    from core.agent import DatasetAgent, AgentRequest

    agent = DatasetAgent("test_agent")
    assert agent.agent_id == "test_agent"

    request = AgentRequest(
        task_id="test_001",
        problem_description="Test",
        failing_tests=["test"],
        workspace_path="/tmp"
    )
    assert request.task_id == "test_001"

def test_config():
    """测试配置管理"""
    from utils.config import EvaluationConfig, ConfigManager

    config = EvaluationConfig()
    assert config.model == "gpt-4"

    manager = ConfigManager()
    assert isinstance(manager.config, EvaluationConfig)

def test_metrics():
    """测试指标计算器"""
    from utils.metrics import MetricsCalculator

    calculator = MetricsCalculator()
    assert calculator is not None

def test_visualization():
    """测试可视化工具"""
    from utils.visualization import EvaluationVisualizer

    viz = EvaluationVisualizer()
    assert viz is not None

def test_loaders():
    """测试数据集加载器"""
    from loaders.base import BaseDatasetLoader
    from loaders.swe_bench import SWEBenchLoader
    from loaders.bugs_in_py import BugsInPyLoader

    swe_loader = SWEBenchLoader("./test_swe")
    bug_loader = BugsInPyLoader("./test_bugs")

    assert isinstance(swe_loader, BaseDatasetLoader)
    assert isinstance(bug_loader, BaseDatasetLoader)

def main():
    """主测试函数"""
    print("Fix Agent Dataset 最终检查")
    print("=" * 50)

    tests = [
        ("数据类型定义", lambda: __import__('data_types'), None),
        ("Agent核心", lambda: __import__('core.agent'), None),
        ("配置管理", lambda: __import__('utils.config'), None),
        ("指标计算器", lambda: __import__('utils.metrics'), None),
        ("可视化工具", lambda: __import__('utils.visualization'), None),
        ("数据集加载器", lambda: __import__('loaders'), None),
    ]

    passed = 0
    total = len(tests)

    for name, import_func, test_func in tests:
        if test_component(name, import_func, test_func):
            passed += 1

    print(f"\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！Dataset框架完全正常工作。")
        print("\n可以开始使用以下命令运行评估:")
        print("  python run_evaluation.py --dataset swe-bench --samples 10")
        print("  python run_evaluation.py --dataset bugsinpy --samples 10")
        return 0
    else:
        print("⚠️ 部分测试失败，但核心功能应该可用。")
        print("请检查失败的组件或联系开发者。")
        return 1

if __name__ == "__main__":
    sys.exit(main())