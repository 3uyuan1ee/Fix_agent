#!/usr/bin/env python3
"""
AIDefectDetector - AI驱动的智能代码缺陷检测与修复系统
基于AI Agent架构的代码分析和自动修复工具

使用方法：
python scripts/setup.py sdist bdist_wheel
pip install dist/aidefect-1.0.0-py3-none-any.whl
"""

from setuptools import setup, find_packages
from pathlib import Path
import sys
import os

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.utils.config import get_config_manager
    from src.utils.logger import get_logger
except ImportError:
    # 如果无法导入，使用基础配置
    def get_config_manager():
        return None
    def get_logger():
        import logging
        return logging.getLogger(__name__)

logger = get_logger()

def read_requirements():
    """读取requirements.txt文件"""
    requirements_file = Path(__file__).parent.parent / "requirements.txt"
    requirements = []

    if requirements_file.exists():
        with open(requirements_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 跳过注释和空行
                if line and not line.startswith("#"):
                    # 跳过可选依赖（在requirements.txt中用#注释标记的）
                    if not any(line.startswith(pkg) for pkg in ["jinja2", "sqlalchemy", "matplotlib", "plotly", "psutil", "memory-profiler"]):
                        requirements.append(line)
    else:
        logger.warning("requirements.txt文件不存在，使用默认依赖")
        # 基础依赖
        requirements = [
            "zai-sdk>=0.0.3.3",
            "flask>=2.3.0",
            "flask-cors>=4.0.0",
            "pylint>=3.0.0",
            "flake8>=6.0.0",
            "bandit>=1.7.0",
            "mccabe>=0.7.0",
            "pyyaml>=6.0.1",
            "loguru>=0.7.0",
            "click>=8.1.0",
            "rich>=13.0.0",
            "tqdm>=4.66.0",
            "requests>=2.31.0",
            "python-dotenv>=1.0.0",
            "chardet>=5.0.0",
            "aiofiles>=23.0.0",
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.5.0",
        ]

    return requirements

def read_readme():
    """读取README.md文件"""
    readme_file = Path(__file__).parent.parent / "README.md"
    if readme_file.exists():
        return readme_file.read_text(encoding="utf-8")
    else:
        return "AIDefectDetector - AI驱动的智能代码缺陷检测与修复系统"

def main():
    """主函数"""
    try:
        requirements = read_requirements()
        long_description = read_readme()

        # 可选依赖定义
        extras_require = {
            "dev": [
                "pytest>=7.4.0",
                "pytest-asyncio>=0.21.0",
                "pytest-cov>=4.1.0",
                "black>=23.0.0",
                "isort>=5.12.0",
                "mypy>=1.5.0",
            ],
            "web": [
                "jinja2>=3.0.0",
                "bootstrap-flask>=2.0.0",
                "flask-socketio>=5.3.0",
                "python-socketio>=5.8.0",
            ],
            "database": [
                "sqlalchemy>=2.0.0",
                "alembic>=1.8.0",
            ],
            "reporting": [
                "matplotlib>=3.5.0",
                "plotly>=5.0.0",
                "jupyter>=1.0.0",
            ],
            "monitoring": [
                "psutil>=5.8.0",
                "memory-profiler>=0.60.0",
            ],
            "all": [
                # 包含所有可选依赖
                "jinja2>=3.0.0",
                "bootstrap-flask>=2.0.0",
                "flask-socketio>=5.3.0",
                "python-socketio>=5.8.0",
                "sqlalchemy>=2.0.0",
                "alembic>=1.8.0",
                "matplotlib>=3.5.0",
                "plotly>=5.0.0",
                "jupyter>=1.0.0",
                "psutil>=5.8.0",
                "memory-profiler>=0.60.0",
                # 开发工具
                "pytest>=7.4.0",
                "pytest-asyncio>=0.21.0",
                "pytest-cov>=4.1.0",
                "black>=23.0.0",
                "isort>=5.12.0",
                "mypy>=1.5.0",
            ],
        }

        setup(
            name="aidefect",
            version="1.0.0",
            author="AIDefectDetector Team",
            author_email="contact@aidefect.com",
            description="AI驱动的智能代码缺陷检测与修复系统",
            long_description=long_description,
            long_description_content_type="text/markdown",
            url="https://github.com/3uyuan1ee/Fix_agent",
            packages=find_packages(where="src"),
            package_dir={"": "src"},
            classifiers=[
                "Development Status :: 4 - Beta",
                "Intended Audience :: Developers",
                "Topic :: Software Development :: Quality Assurance",
                "Topic :: Software Development :: Debuggers",
                "Topic :: Software Development :: Libraries :: Python Modules",
                "License :: OSI Approved :: MIT License",
                "Programming Language :: Python :: 3",
                "Programming Language :: Python :: 3.8",
                "Programming Language :: Python :: 3.9",
                "Programming Language :: Python :: 3.10",
                "Programming Language :: Python :: 3.11",
                "Programming Language :: Python :: 3.12",
                "Operating System :: OS Independent",
            ],
            python_requires=">=3.8",
            install_requires=requirements,
            extras_require=extras_require,
            entry_points={
                "console_scripts": [
                    "aidefect=interfaces.cli:main",
                    "aidefect-web=interfaces.web:main",
                ],
            },
            include_package_data=True,
            package_data={
                "": ["*.yaml", "*.yml", "*.json", "*.txt", "*.md"],
                "config": ["*.yaml", "*.yml"],
                "prompts": ["*.yaml", "*.yml", "*.txt"],
                "docs": ["*.md"],
                "scripts": ["*.sh", "*.bat", "*.py"],
            },
            zip_safe=False,
            keywords=[
                "ai",
                "code analysis",
                "defect detection",
                "repair",
                "static analysis",
                "deep analysis",
                "automated fixing",
                "llm",
                "artificial intelligence",
                "code quality",
                "security scanning",
                "pytest",
                "pylint",
                "flake8",
                "bandit",
            ],
        )

        print("✅ setup.py 配置完成")
        print("📦 构建命令:")
        print("   python scripts/setup.py sdist bdist_wheel")
        print("📦 安装命令:")
        print("   pip install dist/aidefect-1.0.0-py3-none-any.whl")
        print("📦 开发模式安装:")
        print("   pip install -e .")
        print("📦 完整功能安装:")
        print("   pip install -e .[all]")

    except Exception as e:
        print(f"❌ setup.py 配置失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()