#!/usr/bin/env python3
"""
Dataset评估框架 - 快速开始脚本

自动完成环境设置、依赖安装、数据集下载和基础测试。
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

def print_banner():
    """打印横幅"""
    print("=" * 80)
    print("🚀 Dataset评估框架 - 快速开始")
    print("=" * 80)
    print("这个脚本将帮助你快速设置和测试Dataset评估框架")
    print()

def check_python_version():
    """检查Python版本"""
    print("🔍 检查Python版本...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python版本过低: {version.major}.{version.minor}")
        print("需要Python 3.8或更高版本")
        return False

    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查系统依赖"""
    print("🔍 检查系统依赖...")

    # 检查Git
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True)
        print(f"✅ Git: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Git未安装，请先安装Git")
        return False

    # 检查Docker（可选）
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        print(f"✅ Docker: {result.stdout.strip()}")
    except FileNotFoundError:
        print("⚠️  Docker未安装，将使用本地环境进行评估")

    return True

def install_python_dependencies():
    """安装Python依赖"""
    print("📦 安装Python依赖...")

    requirements_file = Path(__file__).parent / "requirements.txt"
    if not requirements_file.exists():
        print("⚠️  requirements.txt不存在，跳过依赖安装")
        return True

    try:
        # 使用当前Python环境安装依赖
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Python依赖安装成功")
        else:
            print(f"⚠️  部分依赖安装失败: {result.stderr}")
            print("你可以手动安装: pip install -r requirements.txt")

        return True

    except Exception as e:
        print(f"❌ 安装依赖时发生错误: {e}")
        return False

def create_directories():
    """创建必要的目录"""
    print("📁 创建目录结构...")

    directories = [
        "datasets",
        "datasets/predictions",
        "logs",
        "temp",
        "results",
        "testbed"
    ]

    for dir_name in directories:
        dir_path = Path(dir_name)
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✅ 创建目录: {dir_path}")

def create_sample_config():
    """创建示例配置文件"""
    print("⚙️  创建配置文件...")

    config_file = Path("config.json")
    if config_file.exists():
        print("⚠️  config.json已存在，跳过创建")
        return True

    sample_config = {
        "agent": {
            "model": "gpt-4",
            "api_key": "your-api-key-here",
            "api_base": "https://api.openai.com/v1/",
            "temperature": 0.1,
            "max_tokens": 4000
        },
        "evaluation": {
            "default_timeout": 300,
            "max_workers": 4,
            "enable_caching": True
        },
        "dataset": {
            "default_samples": 10,
            "cache_metadata": True
        }
    }

    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        print("✅ 配置文件已创建: config.json")
        print("⚠️  请编辑config.json，填入你的API密钥")
        return True

    except Exception as e:
        print(f"❌ 创建配置文件失败: {e}")
        return False

def download_sample_dataset():
    """下载示例数据集"""
    print("📥 准备示例数据集...")

    datasets_dir = Path("datasets")
    sample_file = datasets_dir / "sample_dataset.jsonl"

    if sample_file.exists():
        print("⚠️  示例数据集已存在，跳过下载")
        return True

    # 创建简单的示例数据集
    sample_data = [
        {
            "instance_id": "django__django-001",
            "repo": "django/django",
            "base_commit": "abc123def456",
            "problem_statement": "修复QuerySet中的空值处理问题，当查询为空时应该返回空列表而不是None",
            "patch": "--- a/django/db/models/query.py\n+++ b/django/db/models/query.py\n@@ -100,6 +100,8 @@\n class QuerySet:\n     def __getitem__(self, k):\n         if isinstance(k, slice):\n             return self._slice(k)\n+        if not self.query:\n+            return list()\n         return self._get_obj(k)\n",
            "FAIL_TO_PASS": ["tests/queries/test_queryset.py::test_empty_queryset"],
            "PASS_TO_PASS": ["tests/queries/test_queryset.py::test_normal_queryset"],
            "difficulty": "easy"
        },
        {
            "instance_id": "requests__requests-002",
            "repo": "psf/requests",
            "base_commit": "def456abc789",
            "problem_statement": "修复Session对象中的timeout处理，确保timeout参数正确传递",
            "patch": "--- a/requests/sessions.py\n+++ b/requests/sessions.py\n@@ -50,7 +50,7 @@\n class Session:\n     def request(self, method, url, **kwargs):\n         # Merge session settings with kwargs\n         settings = self.merge_environment_settings(\n-            prep, kwargs, stream=stream, verify=verify, cert=cert, proxies=proxies\n+            prep, kwargs, stream=stream, verify=verify, cert=cert, proxies=proxies, timeout=kwargs.get('timeout')\n         )\n",
            "FAIL_TO_PASS": ["tests/test_sessions.py::test_session_timeout"],
            "PASS_TO_PASS": ["tests/test_sessions.py::test_basic_session"],
            "difficulty": "medium"
        }
    ]

    try:
        with open(sample_file, 'w', encoding='utf-8') as f:
            for item in sample_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        print(f"✅ 示例数据集已创建: {sample_file}")
        return True

    except Exception as e:
        print(f"❌ 创建示例数据集失败: {e}")
        return False

def run_basic_test():
    """运行基础测试"""
    print("🧪 运行基础测试...")

    test_script = Path(__file__).parent / "test_framework.py"
    if not test_script.exists():
        print("⚠️  测试脚本不存在，跳过测试")
        return True

    try:
        result = subprocess.run([
            sys.executable, str(test_script)
        ], capture_output=True, text=True, timeout=300)  # 5分钟超时

        if result.returncode == 0:
            print("✅ 基础测试通过")
            print(result.stdout)
            return True
        else:
            print(f"❌ 基础测试失败: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️  测试超时")
        return False
    except Exception as e:
        print(f"❌ 运行测试时发生错误: {e}")
        return False

def show_next_steps():
    """显示后续步骤"""
    print("\n" + "=" * 80)
    print("🎉 快速开始设置完成！")
    print("=" * 80)

    print("\n📋 后续步骤:")
    print()

    print("1️⃣  配置API密钥:")
    print("   编辑 config.json 文件，填入你的LLM API密钥")
    print()

    print("2️⃣  下载完整数据集（可选）:")
    print("   # SWE-bench Lite (推荐)")
    print("   wget https://github.com/princeton-nlp/SWE-bench/raw/main/data/swe-bench-lite.jsonl \\")
    print("     -O datasets/swe-bench-lite.jsonl")
    print()
    print("   # SWE-bench仓库（用于标准评估）")
    print("   cd datasets && git clone https://github.com/princeton-nlp/SWE-bench.git")
    print()

    print("3️⃣  运行评估:")
    print("   # 快速测试（5个样本）")
    print("   python main.py --mode complete --samples 5 --debug")
    print()
    print("   # 完整评估")
    print("   python main.py --mode complete --dataset datasets/swe-bench-lite.jsonl --samples 50")
    print()

    print("4️⃣  查看结果:")
    print("   # 评估报告")
    print("   cat results/evaluation_report.md")
    print()
    print("   # 详细日志")
    print("   tail -f logs/complete_evaluation.log")
    print()

    print("📚 更多信息:")
    print("   - 查看完整文档: cat README_NEW.md")
    print("   - 运行更多测试: python test_framework.py")
    print("   - 自定义配置: 编辑 config.json")

def main():
    """主函数"""
    print_banner()

    # 检查Python版本
    if not check_python_version():
        return False

    print()

    # 检查系统依赖
    if not check_dependencies():
        return False

    print()

    # 安装Python依赖
    if not install_python_dependencies():
        print("⚠️  依赖安装失败，但可以继续")

    print()

    # 创建目录结构
    create_directories()

    print()

    # 创建配置文件
    create_sample_config()

    print()

    # 下载示例数据集
    download_sample_dataset()

    print()

    # 运行基础测试
    test_success = run_basic_test()

    print()

    # 显示后续步骤
    show_next_steps()

    return test_success

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  设置被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)