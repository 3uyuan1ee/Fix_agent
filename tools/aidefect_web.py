#!/usr/bin/env python3
"""
AIDefectDetector Web包装脚本
用于解决全局Web命令的路径问题
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 导入并执行Web主函数
from main import web_main_wrapper

def main():
    """Web入口函数"""
    import sys
    sys.exit(web_main_wrapper())

if __name__ == "__main__":
    main()