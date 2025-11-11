#!/usr/bin/env python3
"""
DeepAgents CLI 启动接口
解决相对导入问题的独立运行脚本
"""

import sys
import traceback

try:
    from src.main import cli_main

    if __name__ == "__main__":
        cli_main()

except ImportError as e:
    print(f"导入错误: {e}")
    print("当前 Python 路径:")
    for p in sys.path:
        print(f"  - {p}")
    traceback.print_exc()

except Exception as e:
    print(f"运行时错误: {e}")
    traceback.print_exc()
