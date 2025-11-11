#!/usr/bin/env python3
"""
DeepAgents CLI 启动接口
解决相对导入问题的独立运行脚本
"""

import sys
import traceback
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    # 现在可以使用绝对导入
    from src.workflow.deepagents_cli.main import cli_main

    if __name__ == "__main__":
        print("启动 DeepAgents CLI...")
        print("注意: 在调试环境中运行，某些终端功能可能受限")
        print("建议在真实的终端中运行以获得完整体验")
        print("-" * 50)
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
