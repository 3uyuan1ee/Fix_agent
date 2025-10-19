#!/usr/bin/env python3
"""
AIDefectDetector - 主入口文件
基于AI Agent的软件项目缺陷自主检测与修复系统
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.interfaces.cli import main as cli_main
from src.interfaces.web import main as web_main


def show_usage():
    """显示使用说明"""
    print("""
使用方法:
    python main.py [选项]

选项:
    web             启动Web界面
    help, -h        显示此帮助信息

示例:
    python main.py              # 启动CLI模式
    python main.py web          # 启动Web界面

更多信息请访问: https://github.com/your-repo/AIDefectDetector
    """)


def main():
    """主入口函数"""
    print("AIDefectDetector - 基于AI Agent的软件项目缺陷自主检测与修复系统")
    print("=" * 70)

    # 处理命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()

        if arg in ["help", "-h", "--help"]:
            show_usage()
            return 0

        elif arg == "web":
            try:
                print("正在启动Web界面...")
                return web_main()
            except ImportError as e:
                print(f"错误: 缺少Flask依赖 - {e}")
                print("请安装依赖: pip install flask")
                return 1
            except Exception as e:
                print(f"启动Web界面失败: {e}")
                return 1

        elif arg == "cli":
            try:
                return cli_main()
            except Exception as e:
                print(f"启动CLI失败: {e}")
                return 1

        else:
            print(f"错误: 未知参数 '{arg}'")
            show_usage()
            return 1

    else:
        # 默认启动CLI模式
        try:
            return cli_main()
        except KeyboardInterrupt:
            print("\n用户中断操作")
            return 0
        except Exception as e:
            print(f"启动失败: {e}")
            return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序异常退出: {e}")
        sys.exit(1)