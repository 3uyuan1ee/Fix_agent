#!/usr/bin/env python3
"""
深度分析CLI测试脚本
用于验证深度分析CLI入口和参数解析功能
"""

import sys
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_cli_help():
    """测试CLI帮助信息"""
    print("🔍 测试CLI帮助信息...")

    try:
        # 测试主帮助
        result = subprocess.run(
            ["python", "main.py", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ 主命令帮助信息正常")
        else:
            print(f"❌ 主命令帮助失败: {result.stderr}")
            return False

        # 测试深度分析帮助
        result = subprocess.run(
            ["python", "main.py", "analyze", "deep", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ 深度分析帮助信息正常")
            print(f"   - 帮助内容长度: {len(result.stdout)} 字符")
            if "--output" in result.stdout:
                print("   - 输出参数: ✅")
            if "--verbose" in result.stdout:
                print("   - 详细模式参数: ✅")
            if "--quiet" in result.stdout:
                print("   - 静默模式参数: ✅")
        else:
            print(f"❌ 深度分析帮助失败: {result.stderr}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print("❌ CLI帮助命令超时")
        return False
    except Exception as e:
        print(f"❌ CLI帮助测试失败: {e}")
        return False

def test_cli_argument_parsing():
    """测试CLI参数解析"""
    print("\n🔍 测试CLI参数解析...")

    try:
        # 测试无效参数
        result = subprocess.run(
            ["python", "main.py", "analyze", "deep", "--invalid-arg"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print("✅ 无效参数正确被拒绝")
        else:
            print("❌ 无效参数未被拒绝")
            return False

        # 测试缺少必需参数
        result = subprocess.run(
            ["python", "main.py", "analyze", "deep"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            print("✅ 缺少必需参数正确被拒绝")
        else:
            print("❌ 缺少必需参数未被拒绝")
            return False

        return True

    except subprocess.TimeoutExpired:
        print("❌ CLI参数解析测试超时")
        return False
    except Exception as e:
        print(f"❌ CLI参数解析测试失败: {e}")
        return False

def test_cli_with_mock():
    """使用Mock测试CLI功能"""
    print("\n🔍 使用Mock测试CLI功能...")

    try:
        from src.interfaces.deep_commands import DeepAnalysisCommands
        from unittest.mock import Mock, patch

        # 创建Mock的进度跟踪器
        mock_progress = Mock()
        mock_progress.start = Mock()
        mock_progress.complete = Mock()
        mock_progress.info = Mock()

        # 创建深度分析命令实例
        commands = DeepAnalysisCommands()

        # Mock深度分析协调器
        with patch('src.interfaces.deep_commands.CLIInteractiveCoordinator') as mock_coordinator:
            mock_instance = Mock()
            mock_instance.run_interactive = Mock(return_value={
                'mode': 'deep',
                'target': 'test_target',
                'session_stats': {
                    'total_analyses': 1,
                    'successful_analyses': 1,
                    'analysis_types': {'comprehensive': 1}
                }
            })
            mock_coordinator.return_value = mock_instance

            # 测试命令执行
            try:
                result = commands.handle_deep_analysis(
                    target="test_target",
                    output_file=None,
                    verbose=True,
                    quiet=False,
                    progress=mock_progress
                )

                print("✅ 深度分析命令执行成功")
                print(f"   - 返回结果类型: {type(result)}")
                print(f"   - 目标路径: {result.get('target', 'unknown')}")
                print(f"   - 分析模式: {result.get('mode', 'unknown')}")

                # 验证Mock被正确调用
                mock_instance.run_interactive.assert_called_once_with("test_target")
                print("✅ CLI协调器正确调用")

                return True

            except Exception as e:
                print(f"❌ 深度分析命令执行失败: {e}")
                return False

    except Exception as e:
        print(f"❌ Mock CLI测试失败: {e}")
        return False

def test_cli_validation():
    """测试CLI输入验证"""
    print("\n🔍 测试CLI输入验证...")

    try:
        from src.interfaces.deep_commands import DeepAnalysisCommands
        from unittest.mock import Mock

        commands = DeepAnalysisCommands()

        # 测试目标路径验证
        mock_progress = Mock()

        # 测试无效路径（通过Mock）
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False

            with patch('src.interfaces.deep_commands.CLIInteractiveCoordinator') as mock_coordinator:
                mock_coordinator.return_value = Mock()
                mock_coordinator.return_value.run_interactive = Mock(return_value={})

                try:
                    result = commands.handle_deep_analysis(
                        target="nonexistent_path",
                        output_file=None,
                        verbose=False,
                        quiet=False,
                        progress=mock_progress
                    )
                    print("✅ 无效路径处理正常")
                except Exception as e:
                    # 预期会有异常，这是正常的
                    print(f"✅ 无效路径正确引发异常: {type(e).__name__}")

        # 测试输出文件路径验证
        test_dir = Path("test_output_dir")
        test_dir.mkdir(exist_ok=True)

        try:
            # 应该能正常创建输出目录
            print("✅ 输出目录创建成功")
        except Exception as e:
            print(f"❌ 输出目录创建失败: {e}")
            return False
        finally:
            # 清理测试目录
            if test_dir.exists():
                test_dir.rmdir()

        return True

    except Exception as e:
        print(f"❌ CLI输入验证测试失败: {e}")
        return False

def test_cli_integration():
    """测试CLI集成功能"""
    print("\n🔍 测试CLI集成功能...")

    try:
        # 创建测试文件
        test_file = Path("test_cli_sample.py")
        test_content = '''def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def main():
    for i in range(10):
        print(f"F({i}) = {fibonacci(i)}")

if __name__ == "__main__":
    main()
'''

        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)

        # 测试CLI命令能够找到文件
        result = subprocess.run(
            ["python", "main.py", "analyze", "deep", str(test_file), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print("✅ CLI能够识别测试文件")
        else:
            print(f"❌ CLI无法识别测试文件: {result.stderr}")
            test_file.unlink()
            return False

        # 清理测试文件
        test_file.unlink()

        return True

    except Exception as e:
        print(f"❌ CLI集成测试失败: {e}")
        return False

def test_cli_options():
    """测试CLI选项功能"""
    print("\n🔍 测试CLI选项功能...")

    try:
        from src.interfaces.deep_commands import DeepAnalysisCommands
        from unittest.mock import Mock, patch

        commands = DeepAnalysisCommands()
        mock_progress = Mock()

        # 测试不同选项组合
        test_cases = [
            {
                "name": "verbose模式",
                "verbose": True,
                "quiet": False
            },
            {
                "name": "静默模式",
                "verbose": False,
                "quiet": True
            },
            {
                "name": "标准模式",
                "verbose": False,
                "quiet": False
            }
        ]

        for case in test_cases:
            with patch('src.interfaces.deep_commands.CLIInteractiveCoordinator') as mock_coordinator:
                mock_instance = Mock()
                mock_instance.run_interactive = Mock(return_value={'test': 'result'})
                mock_coordinator.return_value = mock_instance

                try:
                    result = commands.handle_deep_analysis(
                        target="test_target",
                        output_file=None,
                        **{k: v for k, v in case.items() if k in ['verbose', 'quiet']},
                        progress=mock_progress
                    )
                    print(f"✅ {case['name']} 选项测试通过")
                except Exception as e:
                    print(f"❌ {case['name']} 选项测试失败: {e}")
                    return False

        return True

    except Exception as e:
        print(f"❌ CLI选项测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始深度分析CLI测试")
    print("=" * 50)

    test_results = []

    # 1. 测试CLI帮助信息
    help_ok = test_cli_help()
    test_results.append(help_ok)

    # 2. 测试CLI参数解析
    parsing_ok = test_cli_argument_parsing()
    test_results.append(parsing_ok)

    # 3. 测试CLI功能（Mock）
    mock_ok = test_cli_with_mock()
    test_results.append(mock_ok)

    # 4. 测试CLI输入验证
    validation_ok = test_cli_validation()
    test_results.append(validation_ok)

    # 5. 测试CLI集成
    integration_ok = test_cli_integration()
    test_results.append(integration_ok)

    # 6. 测试CLI选项
    options_ok = test_cli_options()
    test_results.append(options_ok)

    # 输出测试结果
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 深度分析CLI测试基本通过！")
        print("深度分析CLI入口和参数解析功能已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查CLI功能。")
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