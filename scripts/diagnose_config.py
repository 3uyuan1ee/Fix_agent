#!/usr/bin/env python3
"""
AIDefectDetector 配置诊断工具
用于诊断和修复API配置问题
"""

import os
import sys
import json
import yaml
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

@dataclass
class DiagnosticResult:
    """诊断结果"""
    category: str
    status: str  # "✅ 正常", "⚠️ 警告", "❌ 错误"
    message: str
    solution: Optional[str] = None
    auto_fixable: bool = False

@dataclass
class HealthScore:
    """健康度评分"""
    overall_score: float
    config_status: float
    api_keys_status: float
    connectivity_status: float
    recommendations: List[str]

class ConfigDiagnostics:
    """配置诊断器"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent  # 指向项目根目录
        self.config_dir = self.base_dir / 'config'
        self.src_dir = self.base_dir / 'src'
        self.results: List[DiagnosticResult] = []

    async def run_full_diagnosis(self) -> HealthScore:
        """运行完整诊断"""
        print("🔍 AIDefectDetector 配置诊断工具")
        print("=" * 50)
        print("")

        self.results.clear()

        # 1. 环境检查
        await self._check_environment()

        # 2. 配置文件检查
        await self._check_config_files()

        # 3. API密钥检查
        await self._check_api_keys()

        # 4. 依赖检查
        await self._check_dependencies()

        # 5. LLM配置检查
        await self._check_llm_config()

        # 6. 连接测试
        await self._test_connectivity()

        # 7. 生成报告
        return self._generate_health_report()

    async def _check_environment(self):
        """检查环境"""
        print("📋 检查运行环境...")

        # Python版本检查
        python_version = sys.version_info
        if python_version >= (3, 8):
            self.results.append(DiagnosticResult(
                category="环境",
                status="✅ 正常",
                message=f"Python版本: {python_version.major}.{python_version.minor}.{python_version.micro}"
            ))
        else:
            self.results.append(DiagnosticResult(
                category="环境",
                status="❌ 错误",
                message=f"Python版本过低: {python_version.major}.{python_version.minor}.{python_version.micro}",
                solution="请升级到Python 3.8或更高版本",
                auto_fixable=False
            ))

        # 工作目录检查
        if (self.base_dir / 'main.py').exists():
            self.results.append(DiagnosticResult(
                category="环境",
                status="✅ 正常",
                message="项目目录结构正确"
            ))
        else:
            self.results.append(DiagnosticResult(
                category="环境",
                status="❌ 错误",
                message="不在项目根目录",
                solution="请在AIDefectDetector项目根目录运行此工具",
                auto_fixable=False
            ))

    async def _check_config_files(self):
        """检查配置文件"""
        print("📁 检查配置文件...")

        required_files = [
            'config/default.yaml',
            'config/user_config.example.yaml',
            'config/llm_config.yaml',
            'docs/API_CONFIG_GUIDE.md'
        ]

        for file_path in required_files:
            full_path = self.base_dir / file_path
            if full_path.exists():
                self.results.append(DiagnosticResult(
                    category="配置文件",
                    status="✅ 正常",
                    message=f"存在: {file_path}"
                ))
            else:
                self.results.append(DiagnosticResult(
                    category="配置文件",
                    status="❌ 错误",
                    message=f"缺失: {file_path}",
                    solution=f"请确保 {file_path} 文件存在",
                    auto_fixable=False
                ))

        # 检查用户配置文件
        user_config = self.base_dir / 'config/user_config.yaml'
        if not user_config.exists():
            self.results.append(DiagnosticResult(
                category="配置文件",
                status="⚠️ 警告",
                message="用户配置文件不存在",
                solution="从示例文件复制: cp config/user_config.example.yaml config/user_config.yaml",
                auto_fixable=True
            ))

        # 检查.env文件
        env_file = self.base_dir / '.env'
        if env_file.exists():
            self.results.append(DiagnosticResult(
                category="配置文件",
                status="✅ 正常",
                message=".env文件存在"
            ))
        else:
            self.results.append(DiagnosticResult(
                category="配置文件",
                status="⚠️ 警告",
                message=".env文件不存在",
                solution="创建.env文件存储API密钥",
                auto_fixable=True
            ))

    async def _check_api_keys(self):
        """检查API密钥"""
        print("🔑 检查API密钥...")

        providers = {
            'ZHIPU_API_KEY': '智谱AI',
            'OPENAI_API_KEY': 'OpenAI',
            'ANTHROPIC_API_KEY': 'Anthropic'
        }

        configured_count = 0
        for env_var, provider_name in providers.items():
            api_key = os.environ.get(env_var)
            if api_key:
                if len(api_key) > 10 and not api_key.startswith('your-'):
                    self.results.append(DiagnosticResult(
                        category="API密钥",
                        status="✅ 正常",
                        message=f"{provider_name} API密钥已配置"
                    ))
                    configured_count += 1
                else:
                    self.results.append(DiagnosticResult(
                        category="API密钥",
                        status="⚠️ 警告",
                        message=f"{provider_name} API密钥格式不正确",
                        solution=f"请设置有效的{env_var}"
                    ))
            else:
                self.results.append(DiagnosticResult(
                    category="API密钥",
                    status="⚠️ 警告",
                    message=f"{provider_name} API密钥未配置",
                    solution=f"设置环境变量 {env_var} 或使用配置脚本",
                    auto_fixable=False
                ))

        if configured_count == 0:
            self.results.append(DiagnosticResult(
                category="API密钥",
                status="⚠️ 警告",
                message="没有配置任何API密钥",
                solution="运行 ./setup_api.sh 配置API密钥",
                auto_fixable=False
            ))
        elif configured_count >= 1:
            self.results.append(DiagnosticResult(
                category="API密钥",
                status="✅ 正常",
                message=f"已配置{configured_count}个API密钥"
            ))

    async def _check_dependencies(self):
        """检查Python依赖"""
        print("📦 检查Python依赖...")

        required_packages = [
            ('yaml', 'PyYAML'),
            ('loguru', 'loguru'),
            ('pathlib', None),  # 标准库
            ('asyncio', None),  # 标准库
            ('typing', None)    # 标准库
        ]

        missing_packages = []

        for module_name, package_name in required_packages:
            try:
                __import__(module_name)
                self.results.append(DiagnosticResult(
                    category="依赖",
                    status="✅ 正常",
                    message=f"模块可用: {module_name}"
                ))
            except ImportError:
                if package_name:
                    missing_packages.append(package_name)
                    self.results.append(DiagnosticResult(
                        category="依赖",
                        status="❌ 错误",
                        message=f"缺失模块: {module_name}",
                        solution=f"安装: pip install {package_name}",
                        auto_fixable=True
                    ))
                else:
                    self.results.append(DiagnosticResult(
                        category="依赖",
                        status="❌ 错误",
                        message=f"标准库模块缺失: {module_name}",
                        solution="Python安装有问题，请重新安装Python",
                        auto_fixable=False
                    ))

        if missing_packages:
            solution = f"pip install {' '.join(missing_packages)}"
            self.results.append(DiagnosticResult(
                category="依赖",
                status="❌ 错误",
                message=f"缺失{len(missing_packages)}个依赖包",
                solution=solution,
                auto_fixable=True
            ))

    async def _check_llm_config(self):
        """检查LLM配置"""
        print("🤖 检查LLM配置...")

        try:
            from llm.config import LLMConfigManager

            config_manager = LLMConfigManager()
            providers = config_manager.list_providers()

            if providers:
                self.results.append(DiagnosticResult(
                    category="LLM配置",
                    status="✅ 正常",
                    message=f"可用providers: {', '.join(providers)}"
                ))

                # 检查默认provider
                try:
                    default_config = config_manager.get_default_config()
                    if default_config:
                        self.results.append(DiagnosticResult(
                            category="LLM配置",
                            status="✅ 正常",
                            message=f"默认provider: {default_config.provider}"
                        ))
                    else:
                        self.results.append(DiagnosticResult(
                            category="LLM配置",
                            status="⚠️ 警告",
                            message="默认provider配置失败",
                            solution="检查llm_config.yaml配置",
                            auto_fixable=False
                        ))
                except Exception as e:
                    self.results.append(DiagnosticResult(
                        category="LLM配置",
                        status="❌ 错误",
                        message=f"默认provider错误: {e}",
                        solution="检查llm_config.yaml配置",
                        auto_fixable=False
                    ))
            else:
                self.results.append(DiagnosticResult(
                    category="LLM配置",
                    status="❌ 错误",
                    message="没有可用的LLM providers",
                    solution="检查llm_config.yaml文件",
                    auto_fixable=False
                ))

        except Exception as e:
            self.results.append(DiagnosticResult(
                category="LLM配置",
                status="❌ 错误",
                message=f"LLM配置加载失败: {e}",
                solution="检查配置文件和依赖",
                auto_fixable=False
            ))

    async def _test_connectivity(self):
        """测试连接"""
        print("🌐 测试网络连接...")

        # 只测试有API密钥的provider
        providers_to_test = []

        if os.environ.get('ZHIPU_API_KEY'):
            providers_to_test.append('zhipu')
        if os.environ.get('OPENAI_API_KEY'):
            providers_to_test.append('openai')
        if os.environ.get('ANTHROPIC_API_KEY'):
            providers_to_test.append('anthropic')

        if not providers_to_test:
            self.results.append(DiagnosticResult(
                category="连接",
                status="⚠️ 警告",
                message="没有API密钥，跳过连接测试",
                solution="配置API密钥后进行连接测试",
                auto_fixable=False
            ))
            return

        # 测试每个provider
        for provider_name in providers_to_test:
            try:
                from llm.client import LLMClient
                client = LLMClient()

                # 创建测试请求
                from llm.interfaces import LLMRequest
                request = LLMRequest(
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10,
                    temperature=0.1
                )

                # 尝试调用
                response = await client.complete(request, provider_name)

                self.results.append(DiagnosticResult(
                    category="连接",
                    status="✅ 正常",
                    message=f"{provider_name} 连接测试成功"
                ))

            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower():
                    solution = "检查网络连接或代理设置"
                elif "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower():
                    solution = "检查API密钥是否正确"
                elif "connection" in error_msg.lower():
                    solution = "检查网络连接和API地址"
                else:
                    solution = "检查配置和网络连接"

                self.results.append(DiagnosticResult(
                    category="连接",
                    status="❌ 错误",
                    message=f"{provider_name} 连接失败: {error_msg}",
                    solution=solution,
                    auto_fixable=False
                ))

    def _generate_health_report(self) -> HealthScore:
        """生成健康报告"""
        print("")
        print("📊 诊断报告")
        print("=" * 50)

        # 统计各类状态
        normal_count = len([r for r in self.results if r.status == "✅ 正常"])
        warning_count = len([r for r in self.results if r.status == "⚠️ 警告"])
        error_count = len([r for r in self.results if r.status == "❌ 错误"])
        total_count = len(self.results)

        # 分类显示结果
        categories = {}
        for result in self.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)

        for category, results in categories.items():
            print(f"\n🔸 {category}:")
            for result in results:
                print(f"   {result.status} {result.message}")
                if result.solution:
                    print(f"      💡 解决方案: {result.solution}")

        # 计算健康分数
        config_status = 1.0 - (error_count / max(total_count, 1)) if total_count > 0 else 1.0
        api_keys_status = normal_count / max(total_count, 1) if total_count > 0 else 1.0
        connectivity_status = 1.0 - (error_count * 0.5 / max(total_count, 1)) if total_count > 0 else 1.0

        overall_score = (config_status + api_keys_status + connectivity_status) / 3 * 100

        # 生成建议
        recommendations = []
        if error_count > 0:
            recommendations.append(f"修复 {error_count} 个错误项")
        if warning_count > 0:
            recommendations.append(f"解决 {warning_count} 个警告项")
        if not os.environ.get('ZHIPU_API_KEY') and not os.environ.get('OPENAI_API_KEY'):
            recommendations.append("配置至少一个API密钥")
        if not (self.base_dir / 'config/user_config.yaml').exists():
            recommendations.append("创建用户配置文件")

        print(f"\n🎯 健康评分: {overall_score:.1f}/100")
        print(f"   - 配置状态: {config_status*100:.1f}%")
        print(f"   - API密钥: {api_keys_status*100:.1f}%")
        print(f"   - 连接状态: {connectivity_status*100:.1f}%")

        if recommendations:
            print(f"\n💡 改进建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")

        return HealthScore(
            overall_score=overall_score,
            config_status=config_status,
            api_keys_status=api_keys_status,
            connectivity_status=connectivity_status,
            recommendations=recommendations
        )

    async def auto_fix_issues(self):
        """自动修复问题"""
        print("\n🔧 尝试自动修复...")

        fixable_issues = [r for r in self.results if r.auto_fixable]

        if not fixable_issues:
            print("✅ 没有可自动修复的问题")
            return

        for issue in fixable_issues:
            print(f"   修复: {issue.message}")

            try:
                if "用户配置文件不存在" in issue.message:
                    # 复制用户配置文件
                    src = self.config_dir / 'user_config.example.yaml'
                    dst = self.config_dir / 'user_config.yaml'
                    if src.exists():
                        import shutil
                        shutil.copy2(src, dst)
                        print(f"   ✅ 已创建: {dst}")

                elif ".env文件不存在" in issue.message:
                    # 创建.env文件
                    env_file = self.base_dir / '.env'
                    with open(env_file, 'w') as f:
                        f.write("# AIDefectDetector 环境变量\n")
                        f.write("# 请在此处添加您的API密钥\n")
                        f.write("# ZHIPU_API_KEY=your-zhipu-api-key\n")
                        f.write("# OPENAI_API_KEY=your-openai-api-key\n")
                        f.write("# ANTHROPIC_API_KEY=your-anthropic-api-key\n")
                    print(f"   ✅ 已创建: {env_file}")

                elif "缺失模块" in issue.message and "安装: pip install" in issue.solution:
                    # 安装Python包
                    package = issue.solution.split("pip install ")[1]
                    print(f"   安装包: {package}")
                    # 注意：这里不自动执行pip install，由用户手动执行
                    print(f"   ⚠️ 请手动执行: {issue.solution}")

            except Exception as e:
                print(f"   ❌ 修复失败: {e}")

async def main():
    """主函数"""
    diagnostics = ConfigDiagnostics()

    try:
        # 运行完整诊断
        health_score = await diagnostics.run_full_diagnosis()

        # 询问是否自动修复
        if any(r.auto_fixable for r in diagnostics.results):
            print("\n" + "=" * 50)
            response = input("是否尝试自动修复可修复的问题? (y/n): ")
            if response.lower() in ['y', 'yes', '是']:
                await diagnostics.auto_fix_issues()

        print("\n" + "=" * 50)
        print("🎉 诊断完成！")

        if health_score.overall_score >= 80:
            print("✅ 配置状态良好，可以开始使用深度分析功能")
            print("\n🚀 快速开始:")
            print("   python3 main.py analyze deep src/utils/config.py")
        else:
            print("⚠️ 存在配置问题，建议先解决上述问题")
            print("\n📖 获取帮助:")
            print("   cat API_CONFIG_GUIDE.md")
            print("   ./setup_api.sh")

    except KeyboardInterrupt:
        print("\n\n❌ 诊断被用户中断")
    except Exception as e:
        print(f"\n❌ 诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())