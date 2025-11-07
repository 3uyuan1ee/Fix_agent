"""
AIDefectDetector 包入口点
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

# 导入并运行main模块的main函数
from main import main


def cli_main():
    """CLI入口点"""
    main()


def web_main():
    """Web入口点"""
    import sys

    sys.argv.insert(1, "web")
    main()
