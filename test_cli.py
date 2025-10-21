#!/usr/bin/env python3
"""
CLI功能测试脚本
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cli_help():
    """测试CLI帮助功能"""
    try:
        from interfaces.cli import CLIArgumentParser
        import argparse

        parser = CLIArgumentParser()
        print("✅ CLI模块导入成功")

        # 测试参数解析 - 使用try-except捕获SystemExit
        try:
            args = parser.parse_args(['--help'])
        except SystemExit as e:
            if e.code == 0:  # 正常退出
                print("✅ CLI帮助信息显示正常")
            else:
                print(f"❌ CLI帮助异常退出: {e.code}")
                return False

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

    return True

def test_analyze_static():
    """测试静态分析功能"""
    try:
        from tools.cli_coordinator import CLIStaticCoordinator
        from utils.progress import ProgressTracker

        print("✅ 静态分析模块导入成功")

        # 创建协调器
        coordinator = CLIStaticCoordinator(
            tools=['ast'],
            format='simple',
            dry_run=True
        )
        print("✅ 静态分析协调器创建成功")

        return True

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_deep_analysis():
    """测试深度分析功能"""
    try:
        from tools.cli_coordinator import CLIInteractiveCoordinator

        print("✅ 深度分析模块导入成功")

        # 创建协调器
        coordinator = CLIInteractiveCoordinator(mode='deep')
        print("✅ 深度分析协调器创建成功")

        return True

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

def test_fix_analysis():
    """测试修复分析功能"""
    try:
        from tools.cli_coordinator import CLIInteractiveCoordinator

        print("✅ 修复分析模块导入成功")

        # 创建协调器
        coordinator = CLIInteractiveCoordinator(mode='fix')
        print("✅ 修复分析协调器创建成功")

        return True

    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    print("🧪 开始CLI功能测试")
    print("=" * 50)

    tests = [
        ("CLI基础功能", test_cli_help),
        ("静态分析功能", test_analyze_static),
        ("深度分析功能", test_deep_analysis),
        ("修复分析功能", test_fix_analysis)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🔍 测试: {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name} 测试通过")
        else:
            print(f"❌ {test_name} 测试失败")

    print(f"\n📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有功能模块正常!")
    else:
        print("⚠️ 部分功能存在问题，需要修复")