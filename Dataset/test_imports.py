#!/usr/bin/env python3
"""
导入测试脚本

测试Dataset模块的导入是否正常工作。
"""

import sys
from pathlib import Path

# 添加Dataset模块到Python路径
dataset_root = Path(__file__).parent
sys.path.insert(0, str(dataset_root))

# 添加项目根目录到Python路径（用于导入src模块）
project_root = dataset_root.parent
sys.path.insert(0, str(project_root / "src"))


def test_imports():
    """测试所有导入"""
    print("开始测试导入...")

    try:
        # 测试基础模块导入
        print("1. 测试基础模块导入...")
        from core.agent import AgentRequest, AgentResponse, DatasetAgent
        from core.evaluation import (EvaluationFramework, EvaluationResult,
                                     EvaluationTask)

        print("   ✓ 核心模块导入成功")

        import sys
        from pathlib import Path

        dataset_root = Path(__file__).parent
        if str(dataset_root) not in sys.path:
            sys.path.insert(0, str(dataset_root))

        from loaders.base import BaseDatasetLoader
        from loaders.bugs_in_py import BugsInPyLoader
        from loaders.swe_bench import SWEBenchLoader

        print("   ✓ 加载器模块导入成功")

        from utils.config import ConfigManager, EvaluationConfig
        from utils.metrics import MetricsCalculator
        from utils.visualization import EvaluationVisualizer

        print("   ✓ 工具模块导入成功")

        print("2. 测试模块初始化...")

        # 测试配置管理器
        config = ConfigManager()
        print("   ✓ 配置管理器初始化成功")

        # 测试指标计算器
        metrics = MetricsCalculator()
        print("   ✓ 指标计算器初始化成功")

        # 测试可视化器
        viz = EvaluationVisualizer()
        print("   ✓ 可视化器初始化成功")

        # 测试加载器
        swe_loader = SWEBenchLoader("./test_swe")
        bug_loader = BugsInPyLoader("./test_bugs")
        print("   ✓ 数据集加载器初始化成功")

        print("\n✅ 所有导入测试通过！")
        return True

    except ImportError as e:
        print(f"\n❌ 导入错误: {e}")
        import traceback

        traceback.print_exc()
        return False

    except Exception as e:
        print(f"\n❌ 其他错误: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_agent_creation():
    """测试agent创建"""
    print("\n开始测试Agent创建...")

    try:
        from core.agent import DatasetAgent

        # 注意：这里可能会因为缺少模型配置而失败，这是正常的
        agent = DatasetAgent("test_agent")
        print("   ✓ DatasetAgent创建成功")

        # 测试请求和响应结构
        from core.agent import AgentRequest, AgentResponse

        request = AgentRequest(
            task_id="test_001",
            problem_description="Test problem",
            failing_tests=["test_example"],
            workspace_path="/tmp",
        )
        print("   ✓ AgentRequest创建成功")

        response = AgentResponse(
            task_id="test_001",
            success=True,
            message="Test response",
            fixed_files=["test.py"],
            execution_time=1.0,
            intermediate_steps=[],
            test_results={},
        )
        print("   ✓ AgentResponse创建成功")

        print("\n✅ Agent创建测试通过！")
        return True

    except Exception as e:
        print(f"\n❌ Agent创建测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Fix Agent Dataset模块测试")
    print("=" * 50)

    # 测试导入
    import_success = test_imports()

    if import_success:
        # 测试Agent创建
        agent_success = test_agent_creation()

        if import_success and agent_success:
            print("\n🎉 所有测试通过！Dataset模块可以正常使用。")
        else:
            print("\n⚠️  部分测试失败，但基础功能应该可用。")
    else:
        print("\n💥 导入测试失败，请检查路径和依赖。")
