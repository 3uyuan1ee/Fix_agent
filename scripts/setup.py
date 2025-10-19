#!/usr/bin/env python3
"""
AIDefectDetector 安装配置文件
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# 读取requirements文件
requirements = []
requirements_path = this_directory / "requirements.txt"
if requirements_path.exists():
    requirements = requirements_path.read_text(encoding='utf-8').strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="aidefect",
    version="1.0.0",
    author="AIDefectDetector Team",
    author_email="contact@aidefect.com",
    description="基于AI Agent的软件项目缺陷自主检测与修复系统",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-repo/AIDefectDetector",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Quality Assurance",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Debuggers",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.900",
        ],
        "web": [
            "flask>=2.0.0",
            "bootstrap-flask>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "aidefect=main:main",
            "aidefect-web=main:web_main_wrapper",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.txt", "*.md"],
        "web": ["templates/*.html", "static/css/*.css", "static/js/*.js"],
        "config": ["*.yaml", "*.yml"],
    },
    zip_safe=False,
    keywords="ai code analysis defect detection repair static analysis deep analysis",
    project_urls={
        "Bug Reports": "https://github.com/your-repo/AIDefectDetector/issues",
        "Source": "https://github.com/your-repo/AIDefectDetector",
        "Documentation": "https://github.com/your-repo/AIDefectDetector/docs",
    },
)