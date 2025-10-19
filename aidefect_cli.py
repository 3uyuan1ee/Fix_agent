#!/usr/bin/env python3
"""
AIDefectDetector 命令行包装脚本
用于解决全局命令的路径问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入并执行主函数
from main import main as cli_main

def main():
    """主入口函数"""
    import sys
    sys.exit(cli_main())

if __name__ == "__main__":
    main()