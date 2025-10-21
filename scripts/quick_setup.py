#!/usr/bin/env python3
"""
AIDefectDetector 快速设置向导
帮助用户快速配置和开始使用深度分析功能
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

class QuickSetup:
    """快速设置向导"""

    def __init__(self):
        self.base_dir = Path(__file__).parent

    def run(self):
        """运行快速设置向导"""
        print("🚀 AIDefectDetector 快速设置向导")
        print("=" * 50)
        print("")

        # 步骤1: 欢迎和说明
        self._show_welcome()

        # 步骤2: 检查环境
        self._check_environment()

        # 步骤3: 选择配置方式
        setup_method = self._choose_setup_method()

        # 步骤4: 执行配置
        if setup_method == "template":
            self._setup_from_template()
        elif setup_method == "api":
            self._setup_api_key()
        elif setup_method == "script":
            self._run_setup_script()
        else:
            self._setup_mock()

        # 步骤5: 验证配置
        self._validate_setup()

        # 步骤6: 使用演示
        self._show_usage_demo()

    def _show_welcome(self):
        """显示欢迎信息"""
        print("👋 欢迎使用AIDefectDetector深度分析功能！")
        print("")
        print("本向导将帮助您：")
        print("✅ 选择合适的配置方式")
        print("✅ 设置API密钥或使用Mock模式")
        print("✅ 验证配置是否正确")
        print("✅ 开始使用深度分析功能")
        print("")

    def _check_environment(self):
        """检查环境"""
        print("🔍 检查运行环境...")
        print("-" * 30)

        # Python版本
        python_version = sys.version_info
        if python_version >= (3, 8):
            print(f"✅ Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}")
        else:
            print(f"⚠️ Python版本较低: {python_version.major}.{python_version.minor}")
            print("   建议升级到Python 3.8+")

        # 检查必要文件
        required_files = [
            'main.py',
            'src/llm/client.py',
            'config/default.yaml',
            'API_CONFIG_GUIDE.md'
        ]

        for file_name in required_files:
            file_path = self.base_dir / file_name
            if file_path.exists():
                print(f"✅ {file_name}")
            else:
                print(f"❌ {file_name} 缺失")

        print("")

    def _choose_setup_method(self) -> str:
        """选择配置方式"""
        print("📋 请选择配置方式:")
        print("1) 🎯 使用配置模板 (推荐)")
        print("   - 适合不同场景的预设配置")
        print("   - 包含完整的配置示例")
        print("")
        print("2) 🔑 直接设置API密钥")
        print("   - 最快的方式，立即开始使用")
        print("   - 适合已有API密钥的用户")
        print("")
        print("3) 🛠️ 运行配置脚本")
        print("   - 交互式配置向导")
        print("   - 适合需要详细配置的用户")
        print("")
        print("4) 🧪 使用Mock模式 (无需API)")
        print("   - 无需API密钥，立即可用")
        print("   - 适合测试和演示")
        print("")

        while True:
            choice = input("请选择 (1-4): ").strip()
            if choice == '1':
                return "template"
            elif choice == '2':
                return "api"
            elif choice == '3':
                return "script"
            elif choice == '4':
                return "mock"
            else:
                print("❌ 无效选择，请输入1-4")

    def _setup_from_template(self):
        """从模板设置配置"""
        print("\n📁 选择配置模板:")
        print("-" * 30)

        templates = {
            '1': ('minimal', '最小化配置 - 快速体验'),
            '2': ('development', '开发环境 - 本地开发'),
            '3': ('production', '生产环境 - 正式部署'),
            '4': ('testing', '测试环境 - 自动化测试')
        }

        for key, (name, description) in templates.items():
            print(f"{key}) {name}")
            print(f"   {description}")
            print("")

        while True:
            choice = input("请选择模板 (1-4): ").strip()
            if choice in templates:
                template_name = templates[choice][0]
                break
            else:
                print("❌ 无效选择，请输入1-4")

        # 应用模板
        print(f"\n🔧 应用模板 '{template_name}'...")
        try:
            result = subprocess.run([
                'python3', 'manage_config.py', 'apply', template_name
            ], capture_output=True, text=True, cwd=self.base_dir)

            if result.returncode == 0:
                print("✅ 模板应用成功")
                print(result.stdout)
            else:
                print(f"❌ 模板应用失败: {result.stderr}")
                return

        except FileNotFoundError:
            print("❌ manage_config.py 工具不存在")
            return

        # 询问是否设置API密钥
        print("\n🔑 是否现在设置API密钥? (y/n): ", end="")
        set_api = input().strip().lower()
        if set_api in ['y', 'yes', '是']:
            self._setup_api_key()

    def _setup_api_key(self):
        """设置API密钥"""
        print("\n🔑 设置API密钥:")
        print("-" * 30)

        providers = {
            '1': ('zhipu', '智谱AI', '国内推荐，访问稳定'),
            '2': ('openai', 'OpenAI', '需要代理访问'),
            '3': ('anthropic', 'Anthropic', '需要代理访问'),
            '4': ('skip', '跳过', '稍后设置')
        }

        print("选择LLM提供商:")
        for key, (name, display_name, description) in providers.items():
            print(f"{key}) {display_name} - {description}")

        while True:
            choice = input("请选择 (1-4): ").strip()
            if choice in providers:
                provider_name = providers[choice][0]
                break
            else:
                print("❌ 无效选择，请输入1-4")

        if provider_name == 'skip':
            print("⚠️ 跳过API密钥设置，将使用Mock模式")
            return

        # 获取API密钥
        env_var = f"{provider_name.upper()}_API_KEY"
        current_value = os.environ.get(env_var)

        if current_value:
            print(f"✅ {env_var} 已设置")
            print(f"   当前值: {current_value[:10]}...")
            change = input("是否更换? (y/n): ").strip().lower()
            if change not in ['y', 'yes', '是']:
                print("✅ 保持现有API密钥")
                return

        print(f"\n📝 获取{providers[choice][1]}API密钥:")
        if provider_name == 'zhipu':
            print("1. 访问: https://open.bigmodel.cn/")
            print("2. 注册账号并获取API密钥")
            print("3. 确保账户有余额")
        elif provider_name == 'openai':
            print("1. 访问: https://platform.openai.com/")
            print("2. 创建API密钥")
            print("3. 确保账户有支付方式")
        elif provider_name == 'anthropic':
            print("1. 访问: https://console.anthropic.com/")
            print("2. 创建API密钥")
            print("3. 设置使用限制")

        print("\n请输入API密钥 (或输入 'skip' 跳过):")
        api_key = input("> ").strip()

        if api_key and api_key != 'skip':
            # 设置环境变量
            os.environ[env_var] = api_key
            print(f"✅ 已设置 {env_var}")

            # 询问是否保存到.env文件
            save_env = input("是否保存到 .env 文件? (y/n): ").strip().lower()
            if save_env in ['y', 'yes', '是']:
                env_file = self.base_dir / '.env'
                with open(env_file, 'a') as f:
                    f.write(f"\n{env_var}={api_key}\n")
                print("✅ 已保存到 .env 文件")

            # 询问是否添加到shell配置
            save_shell = input("是否添加到 ~/.bashrc 永久生效? (y/n): ").strip().lower()
            if save_shell in ['y', 'yes', '是']:
                bashrc = Path.home() / '.bashrc'
                with open(bashrc, 'a') as f:
                    f.write(f'\n# AIDefectDetector\nexport {env_var}="{api_key}"\n')
                print("✅ 已添加到 ~/.bashrc")
                print("   请运行 'source ~/.bashrc' 或重新打开终端")
        else:
            print("⚠️ 跳过API密钥设置")

    def _run_setup_script(self):
        """运行设置脚本"""
        print("\n🛠️ 运行配置脚本...")
        print("-" * 30)

        script_path = self.base_dir / 'setup_api.sh'
        if not script_path.exists():
            print("❌ setup_api.sh 脚本不存在")
            return

        try:
            # 运行脚本
            subprocess.run(['bash', str(script_path)], cwd=self.base_dir)
        except KeyboardInterrupt:
            print("\n❌ 脚本被用户中断")
        except Exception as e:
            print(f"❌ 脚本运行失败: {e}")

    def _setup_mock(self):
        """设置Mock模式"""
        print("\n🧪 设置Mock模式...")
        print("-" * 30)

        try:
            result = subprocess.run([
                'python3', 'manage_config.py', 'apply', 'minimal'
            ], capture_output=True, text=True, cwd=self.base_dir)

            if result.returncode == 0:
                print("✅ Mock模式配置成功")
                print("🎯 无需API密钥，立即可用")
            else:
                print(f"❌ Mock模式配置失败: {result.stderr}")

        except FileNotFoundError:
            print("❌ manage_config.py 工具不存在")

    def _validate_setup(self):
        """验证配置"""
        print("\n🔍 验证配置...")
        print("-" * 30)

        # 检查是否有诊断工具
        diagnose_tool = self.base_dir / 'diagnose_config.py'
        if diagnose_tool.exists():
            print("🔬 运行配置诊断...")
            try:
                subprocess.run(['python3', 'diagnose_config.py'], cwd=self.base_dir)
            except KeyboardInterrupt:
                print("\n⚠️ 诊断被用户中断")
            except Exception as e:
                print(f"❌ 诊断失败: {e}")
        else:
            print("⚠️ 诊断工具不存在，进行基础验证...")

            # 基础验证
            user_config = self.base_dir / 'config' / 'user_config.yaml'
            if user_config.exists():
                print("✅ 用户配置文件存在")
            else:
                print("❌ 用户配置文件不存在")

            # 检查API密钥
            api_vars = ['ZHIPU_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
            has_api = any(os.environ.get(var) for var in api_vars)

            if has_api:
                print("✅ 已配置API密钥")
            else:
                print("⚠️ 未配置API密钥，将使用Mock模式")

    def _show_usage_demo(self):
        """显示使用演示"""
        print("\n🎯 开始使用!")
        print("=" * 50)

        print("🚀 基本用法:")
        print("python3 main.py analyze deep <文件路径>")
        print("")

        print("📝 示例:")
        print("# 分析配置文件")
        print("python3 main.py analyze deep src/utils/config.py")
        print("")
        print("# 分析多个文件")
        print("python3 main.py analyze deep src/**/*.py")
        print("")
        print("# 详细输出")
        print("python3 main.py analyze deep src/utils/config.py --verbose")
        print("")

        print("💡 交互模式命令:")
        print("- help: 显示帮助")
        print("- analyze <文件>: 分析指定文件")
        print("- summary: 显示分析摘要")
        print("- export <文件>: 导出对话历史")
        print("- exit: 退出")
        print("")

        print("📚 更多帮助:")
        print("- 配置指南: cat API_CONFIG_GUIDE.md")
        print("- 配置管理: python3 manage_config.py --help")
        print("- 问题诊断: python3 diagnose_config.py")
        print("")

        # 询问是否立即运行示例
        run_demo = input("是否立即运行示例分析? (y/n): ").strip().lower()
        if run_demo in ['y', 'yes', '是']:
            print("\n🔬 运行示例分析...")
            print("分析目标: src/utils/config.py")
            print("")

            try:
                # 使用简单的测试输入
                process = subprocess.Popen([
                    'python3', 'main.py', 'analyze', 'deep', 'src/utils/config.py'
                ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=self.base_dir)

                # 发送简单命令
                stdout, stderr = process.communicate(input="分析这个文件\nexit\n", timeout=30)

                if process.returncode == 0:
                    print("✅ 示例分析运行成功")
                else:
                    print("⚠️ 示例分析可能遇到问题")
                    if stderr:
                        print(f"错误信息: {stderr}")

            except subprocess.TimeoutExpired:
                print("⚠️ 分析超时")
            except KeyboardInterrupt:
                print("\n❌ 分析被用户中断")
            except Exception as e:
                print(f"❌ 分析失败: {e}")

        print("\n🎉 快速设置完成!")
        print("祝您使用愉快！")

def main():
    """主函数"""
    try:
        setup = QuickSetup()
        setup.run()
    except KeyboardInterrupt:
        print("\n\n❌ 设置被用户中断")
    except Exception as e:
        print(f"\n❌ 设置失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()