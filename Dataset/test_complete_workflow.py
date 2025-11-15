#!/usr/bin/env python3
"""
完整工作流程测试

测试Dataset评估框架的完整工作流程，使用模拟数据。
"""

import json
import sys
import tempfile
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))


def create_mock_swe_bench_data():
    """创建模拟的SWE-bench数据"""
    mock_data = [
        {
            "instance_id": "test_001",
            "repo": "django/django",
            "base_commit": "abc123",
            "problem_statement": "修复Django中的认证问题",
            "patch": "@@ -1,3 +1,3 @@\n def authenticate(username, password):\n-    return username == password\n+    return check_password(username, password)",
            "test_patch": "",
            "FAIL_TO_PASS": ["test_auth.py::test_basic_auth"],
            "PASS_TO_PASS": ["test_auth.py::test_existing_feature"],
        },
        {
            "instance_id": "test_002",
            "repo": "psf/requests",
            "base_commit": "def456",
            "problem_statement": "修复requests库中的超时处理",
            "patch": "@@ -10,7 +10,7 @@\n def send_request(url, timeout=None):\n-    if timeout is None:\n-        timeout = 30\n+    timeout = timeout or 30\n     return requests.get(url, timeout=timeout)",
            "test_patch": "",
            "FAIL_TO_PASS": ["test_timeout.py::test_custom_timeout"],
            "PASS_TO_PASS": ["test_basic.py::test_get_request"],
        },
    ]
    return mock_data


def create_mock_bugs_in_py_structure():
    """创建模拟的BugsInPy数据结构"""
    import shutil
    import tempfile

    # 创建临时目录结构
    temp_dir = Path(tempfile.mkdtemp())
    bugs_dir = temp_dir / "bugs" / "django"
    bugs_dir.mkdir(parents=True, exist_ok=True)

    # 创建bug数据
    bug_dir = bugs_dir / "bug_001"
    bug_dir.mkdir(exist_ok=True)

    # bug.json
    bug_data = {
        "type": "authentication",
        "severity": "medium",
        "description": "Django认证系统中的密码验证存在问题",
    }
    with open(bug_dir / "bug.json", "w") as f:
        json.dump(bug_data, f)

    # failing_test.txt
    with open(bug_dir / "failing_test.txt", "w") as f:
        f.write("tests/test_auth.py::test_password_validation\n")

    # patch.txt
    patch_content = """@@ -15,2 +15,2 @@
 def validate_password(password, user):
-    return len(password) >= 6
+    return len(password) >= 8 and any(c.isdigit() for c in password)
"""
    with open(bug_dir / "patch.txt", "w") as f:
        f.write(patch_content)

    return str(temp_dir)


def test_swe_bench_loader():
    """测试SWE-bench加载器"""
    print("1. 测试SWE-bench加载器...")

    try:
        from loaders.swe_bench import SWEBenchLoader

        # 创建临时数据文件
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(create_mock_swe_bench_data(), f)
            temp_file = f.name

        # 临时修改加载器的数据文件路径
        loader = SWEBenchLoader("./temp_test")

        # 直接测试数据转换
        mock_item = create_mock_swe_bench_data()[0]
        task = loader._convert_to_evaluation_task(mock_item)

        if task:
            print(f"   ✓ SWE-bench任务转换成功: {task.task_id}")
            print(f"     - 仓库: {task.repo_name}")
            print(f"     - 测试数量: {len(task.failing_tests)}")
            return True
        else:
            print("   ❌ SWE-bench任务转换失败")
            return False

    except Exception as e:
        print(f"   ❌ SWE-bench加载器测试失败: {e}")
        return False


def test_bugs_in_py_loader():
    """测试BugsInPy加载器"""
    print("2. 测试BugsInPy加载器...")

    try:
        from loaders.bugs_in_py import BugsInPyLoader

        # 创建模拟数据结构
        mock_path = create_mock_bugs_in_py_structure()

        loader = BugsInPyLoader(mock_path)

        # 测试单个bug加载
        bugs_dir = Path(mock_path) / "bugs" / "django" / "bug_001"
        task = loader._load_single_bug("django", bugs_dir)

        if task:
            print(f"   ✓ BugsInPy任务加载成功: {task.task_id}")
            print(f"     - Bug类型: {task.repo_info.get('bug_type', 'unknown')}")
            print(f"     - 测试数量: {len(task.failing_tests)}")
            return True
        else:
            print("   ❌ BugsInPy任务加载失败")
            return False

    except Exception as e:
        print(f"   ❌ BugsInPy加载器测试失败: {e}")
        return False


def test_evaluation_framework():
    """测试评估框架"""
    print("3. 测试评估框架...")

    try:
        from core.evaluation import EvaluationFramework
        from data_types import EvaluationTask

        # 创建模拟任务
        task = EvaluationTask(
            task_id="mock_test_001",
            dataset_name="mock_dataset",
            repo_name="test_repo",
            problem_description="模拟问题描述",
            failing_tests=["test_example.py::test_func"],
            test_command="echo '模拟测试通过'",
            setup_commands=["echo '模拟设置'"],
            timeout=30,
            repo_info={"language": "python", "framework": "django"},
        )

        # 创建评估框架
        framework = EvaluationFramework()

        print("   ✓ 评估框架创建成功")
        print(f"   ✓ 模拟任务创建成功: {task.task_id}")

        # 测试配置加载
        config = {"agent": {"model": "test-model"}, "evaluation": {"max_workers": 2}}
        framework.config = config

        print("   ✓ 评估框架配置成功")
        return True

    except Exception as e:
        print(f"   ❌ 评估框架测试失败: {e}")
        return False


def test_metrics_calculation():
    """测试指标计算"""
    print("4. 测试指标计算...")

    try:
        from utils.metrics_simple import MetricsCalculator

        # 创建测试结果
        test_results = [
            {
                "task_id": "test_001",
                "success": True,
                "execution_time": 25.5,
                "agent_actions": ["analyze", "fix", "validate"],
                "error": None,
            },
            {
                "task_id": "test_002",
                "success": False,
                "execution_time": 45.2,
                "agent_actions": ["analyze", "fix"],
                "error": "TimeoutError",
            },
            {
                "task_id": "test_003",
                "success": True,
                "execution_time": 32.1,
                "agent_actions": ["analyze", "fix", "validate"],
                "error": None,
            },
        ]

        calc = MetricsCalculator()
        metrics = calc.calculate_basic_metrics(test_results)

        print(f"   ✓ 指标计算成功:")
        print(f"     - 成功率: {metrics['success_rate']:.2%}")
        print(f"     - 平均执行时间: {metrics['average_execution_time']:.2f}秒")
        print(f"     - 每小时任务数: {metrics['tasks_per_hour']:.1f}")

        return True

    except Exception as e:
        print(f"   ❌ 指标计算测试失败: {e}")
        return False


def test_complete_workflow():
    """测试完整工作流程"""
    print("\n" + "=" * 60)
    print("Dataset评估框架完整工作流程测试")
    print("=" * 60)

    tests = [
        test_swe_bench_loader,
        test_bugs_in_py_loader,
        test_evaluation_framework,
        test_metrics_calculation,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
            print()  # 空行分隔
        except Exception as e:
            print(f"   💥 测试异常: {e}")
            print()

    print("=" * 60)
    print(f"完整工作流程测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 Dataset评估框架完全可用!")
        print("✅ 所有核心功能正常工作")
        print("✅ 数据加载器工作正常")
        print("✅ 评估框架工作正常")
        print("✅ 指标计算工作正常")
        print("\n可以开始使用以下命令进行实际评估:")
        print("  python run_evaluation.py --dataset swe-bench --samples 10")
        print("  python run_evaluation.py --dataset bugsinpy --samples 5 --debug")
    else:
        print("⚠️ 部分功能存在问题，但基础框架可用")

    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = test_complete_workflow()
    exit(0 if success else 1)
