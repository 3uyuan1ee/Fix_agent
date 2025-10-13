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


def main():
    """主入口函数"""
    print("AIDefectDetector - 基于AI Agent的软件项目缺陷自主检测与修复系统")
    print("=" * 70)

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        web_main()
    else:
        cli_main()


if __name__ == "__main__":
    main()