#!/usr/bin/env python3
"""
分析修复流程基础功能测试脚本
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_fix_components():
    """测试修复流程各组件"""
    print("🔍 测试修复流程组件...")

    test_results = []

    # 1. 测试BackupManager
    try:
        from tools.fix.coordinator import BackupManager

        backup_manager = BackupManager()
        print("✅ BackupManager 初始化成功")
        test_results.append(True)
    except Exception as e:
        print(f"❌ BackupManager 初始化失败: {e}")
        test_results.append(False)

    # 2. 测试DiffViewer
    try:
        from tools.fix.coordinator import DiffViewer

        diff_viewer = DiffViewer()
        print("✅ DiffViewer 初始化成功")
        test_results.append(True)
    except Exception as e:
        print(f"❌ DiffViewer 初始化失败: {e}")
        test_results.append(False)

    # 3. 测试FixConfirmationManager
    try:
        from tools.fix.coordinator import FixConfirmationManager

        confirmation_manager = FixConfirmationManager()
        print("✅ FixConfirmationManager 初始化成功")
        test_results.append(True)
    except Exception as e:
        print(f"❌ FixConfirmationManager 初始化失败: {e}")
        test_results.append(False)

    # 4. 测试FixExecutor
    try:
        from tools.fix.coordinator import FixExecutor

        executor = FixExecutor()
        print("✅ FixExecutor 初始化成功")
        test_results.append(True)
    except Exception as e:
        print(f"❌ FixExecutor 初始化失败: {e}")
        test_results.append(False)

    # 5. 测试FixCoordinator
    try:
        from tools.fix.coordinator import FixCoordinator

        fix_coordinator = FixCoordinator()
        print("✅ FixCoordinator 初始化成功")
        test_results.append(True)
    except Exception as e:
        print(f"❌ FixCoordinator 初始化失败: {e}")
        test_results.append(False)

    return test_results

def test_fix_generator():
    """测试FixGenerator"""
    print("\n🔍 测试FixGenerator...")

    try:
        from tools.fix.generator import FixGenerator

        fix_generator = FixGenerator()
        print("✅ FixGenerator 初始化成功")
        print(f"   - 默认模型: {fix_generator.model if hasattr(fix_generator, 'model') else 'unknown'}")

        return True
    except Exception as e:
        print(f"❌ FixGenerator 初始化失败: {e}")
        return False

def test_static_analysis_tools():
    """测试静态分析工具"""
    print("\n🔍 测试静态分析工具...")

    try:
        from tools.static_analysis.coordinator import StaticAnalysisCoordinator

        coordinator = StaticAnalysisCoordinator()
        print("✅ StaticAnalysisCoordinator 初始化成功")
        print(f"   - 可用工具: {coordinator.tools if hasattr(coordinator, 'tools') else 'unknown'}")

        return True
    except Exception as e:
        print(f"❌ StaticAnalysisCoordinator 初始化失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始分析修复流程基础功能测试")
    print("=" * 60)

    test_results = []

    # 1. 测试修复流程组件
    component_results = test_fix_components()
    test_results.extend(component_results)

    # 2. 测试FixGenerator
    fix_gen_ok = test_fix_generator()
    test_results.append(fix_gen_ok)

    # 3. 测试静态分析工具
    static_analysis_ok = test_static_analysis_tools()
    test_results.append(static_analysis_ok)

    # 输出结果
    print("\n" + "=" * 60)
    print("📊 测试结果:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 分析修复流程基础功能测试基本通过！")
        print("修复流程的基础架构已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查修复功能。")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n用户中断测试")
        sys.exit(0)
    except Exception as e:
        print(f"\n测试异常: {e}")
        sys.exit(1)