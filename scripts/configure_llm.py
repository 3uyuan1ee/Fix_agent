#!/usr/bin/env python3
"""
AIDefectDetector LLM配置统一脚本
合并了setup_api.sh, set_zhipu_key.sh, quick_setup.py等功能
提供交互式的LLM配置向导
"""

import os
import sys
import json
import yaml
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

@dataclass
class LLMProvider:
    """LLM提供商信息"""
    name: str
    display_name: str
    env_key: str
    description: str
    setup_url: str
    base_url_default: str = ""
    requires_base_url: bool = False

class LLMConfigurator:
    """LLM配置器"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent  # 项目根目录
        self.config_dir = Path.home() / '.aidefect'
        self.env_file = self.config_dir / '.env'
        self.user_config_file = self.config_dir / 'config.yaml'
        self.llm_config_file = self.base_dir / 'config' / 'llm_config.yaml'

        # 支持的LLM提供商
        self.providers = {
            'zhipu': LLMProvider(
                name='zhipu',
                display_name='智谱AI',
                env_key='ZHIPU_API_KEY',
                description='国内推荐，访问稳定',
                setup_url='https://open.bigmodel.cn/'
            ),
            'openai': LLMProvider(
                name='openai',
                display_name='OpenAI',
                env_key='OPENAI_API_KEY',
                description='需要代理访问',
                setup_url='https://platform.openai.com/',
                base_url_default='https://api.openai.com/v1',
                requires_base_url=True
            ),
            'anthropic': LLMProvider(
                name='anthropic',
                display_name='Anthropic',
                env_key='ANTHROPIC_API_KEY',
                description='需要代理访问',
                setup_url='https://console.anthropic.com/',
                base_url_default='https://api.anthropic.com',
                requires_base_url=True
            ),
            'mock': LLMProvider(
                name='mock',
                display_name='Mock模式',
                env_key='',
                description='无需API，用于测试',
                setup_url=''
            )
        }

        # 初始化配置目录
        self._init_config_dir()

    def _init_config_dir(self):
        """初始化配置目录"""
        self.config_dir.mkdir(exist_ok=True)

        # 创建logs和cache目录
        (self.config_dir / 'logs').mkdir(exist_ok=True)
        (self.config_dir / 'cache').mkdir(exist_ok=True)

    def _print_header(self, title: str):
        """打印标题"""
        print(f"\n{'='*60}")
        print(f"🚀 {title}")
        print('='*60)

    def _print_success(self, message: str):
        """打印成功消息"""
        print(f"✅ {message}")

    def _print_warning(self, message: str):
        """打印警告消息"""
        print(f"⚠️  {message}")

    def _print_error(self, message: str):
        """打印错误消息"""
        print(f"❌ {message}")

    def _print_info(self, message: str):
        """打印信息消息"""
        print(f"ℹ️  {message}")

    def load_existing_config(self) -> Dict[str, str]:
        """加载现有配置"""
        config = {}

        # 从.env文件加载
        if self.env_file.exists():
            try:
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            except Exception as e:
                self._print_warning(f"读取.env文件失败: {e}")

        # 从环境变量加载
        for provider in self.providers.values():
            if provider.env_key:
                env_value = os.environ.get(provider.env_key)
                if env_value and provider.env_key not in config:
                    config[provider.env_key] = env_value

        return config

    def check_existing_config(self) -> Dict[str, bool]:
        """检查现有配置状态"""
        config = self.load_existing_config()
        status = {}

        for provider_name, provider in self.providers.items():
            if provider.env_key:
                api_key = config.get(provider.env_key, '')
                if api_key and len(api_key) > 10 and not api_key.startswith('your-'):
                    status[provider_name] = True
                else:
                    status[provider_name] = False
            else:
                status[provider_name] = provider_name == 'mock'  # Mock总是可用

        return status

    def display_current_status(self):
        """显示当前配置状态"""
        self._print_header("当前配置状态")

        config = self.load_existing_config()
        configured_providers = []

        print("🔑 API密钥状态:")
        for provider_name, provider in self.providers.items():
            if provider.env_key:
                api_key = config.get(provider.env_key, '')
                if api_key and len(api_key) > 10 and not api_key.startswith('your-'):
                    print(f"   ✅ {provider.display_name}: 已配置 ({api_key[:10]}...)")
                    configured_providers.append(provider_name)
                else:
                    print(f"   ❌ {provider.display_name}: 未配置")

        # Mock模式状态
        mock_available = self._check_mock_availability()
        if mock_available:
            print(f"   ✅ Mock模式: 可用")
        else:
            print(f"   ❌ Mock模式: 不可用")

        print(f"\n📊 配置摘要:")
        if configured_providers:
            print(f"   已配置 {len(configured_providers)} 个LLM提供商: {', '.join(configured_providers)}")
        else:
            print(f"   未配置任何LLM提供商")

        # 检查配置文件
        if self.user_config_file.exists():
            print(f"   ✅ 用户配置文件存在: {self.user_config_file}")
        else:
            print(f"   ❌ 用户配置文件不存在")

        if self.env_file.exists():
            print(f"   ✅ 环境变量文件存在: {self.env_file}")
        else:
            print(f"   ❌ 环境变量文件不存在")

        # 检查LLM配置文件
        if self.llm_config_file.exists():
            print(f"   ✅ LLM配置文件存在: {self.llm_config_file}")
            self._display_llm_config_status()
        else:
            print(f"   ❌ LLM配置文件不存在")

    def _display_llm_config_status(self):
        """显示LLM配置文件状态"""
        try:
            with open(self.llm_config_file, 'r', encoding='utf-8') as f:
                llm_config = yaml.safe_load(f)

            if llm_config and 'providers' in llm_config:
                print("   📋 LLM提供商配置:")
                for provider_name, provider_config in llm_config['providers'].items():
                    if provider_name in self.providers:
                        provider = self.providers[provider_name]
                        model = provider_config.get('model', 'unknown')
                        api_key = provider_config.get('api_key', '')

                        # 检查API密钥是否配置
                        if api_key:
                            if api_key.startswith('${') and '}' in api_key:
                                # 环境变量形式
                                env_var = api_key[2:-1].split(':')[0]
                                env_value = os.environ.get(env_var)
                                if env_value and len(env_value) > 10:
                                    print(f"      ✅ {provider.display_name}: {model} (环境变量已配置)")
                                else:
                                    print(f"      ❌ {provider.display_name}: {model} (环境变量未配置)")
                            else:
                                # 直接配置的API密钥
                                if len(api_key) > 10 and not api_key.startswith('mock-'):
                                    print(f"      ✅ {provider.display_name}: {model} (API密钥已配置)")
                                else:
                                    print(f"      ⚠️  {provider.display_name}: {model} (API密钥格式异常)")
                        else:
                            print(f"      ❌ {provider.display_name}: {model} (API密钥未配置)")
                    else:
                        print(f"      ❓ {provider_name}: 未知提供商")

        except Exception as e:
            print(f"      ⚠️ 读取LLM配置文件失败: {e}")

    def _check_mock_availability(self) -> bool:
        """检查Mock模式是否可用"""
        try:
            # 检查llm_config.yaml中的Mock配置
            if self.llm_config_file.exists():
                with open(self.llm_config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'mock:' in content.lower():
                        return True

            # 检查用户配置文件
            if self.user_config_file.exists():
                with open(self.user_config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'mock:' in content.lower() or 'provider: mock' in content.lower():
                        return True

            # 检查默认配置文件
            default_config = self.base_dir / 'config' / 'default.yaml'
            if default_config.exists():
                with open(default_config, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'mock:' in content.lower():
                        return True

            return True  # 默认支持Mock模式
        except Exception:
            return True  # 出错时假设可用

    def configure_provider(self, provider_name: str) -> bool:
        """配置指定的LLM提供商"""
        if provider_name not in self.providers:
            self._print_error(f"不支持的提供商: {provider_name}")
            return False

        provider = self.providers[provider_name]

        if provider_name == 'mock':
            return self._configure_mock()

        self._print_header(f"配置{provider.display_name}")

        # 显示配置说明
        print(f"📝 获取{provider.display_name}API密钥:")
        print(f"   1. 访问: {provider.setup_url}")
        if provider_name == 'zhipu':
            print(f"   2. 注册账号并获取API密钥")
            print(f"   3. 确保账户有余额")
        elif provider_name == 'openai':
            print(f"   2. 创建API密钥")
            print(f"   3. 确保账户有支付方式")
        elif provider_name == 'anthropic':
            print(f"   2. 创建API密钥")
            print(f"   3. 设置使用限制")
        print()

        # 获取现有配置
        config = self.load_existing_config()
        current_key = config.get(provider.env_key, '')

        if current_key and len(current_key) > 10 and not current_key.startswith('your-'):
            print(f"当前API密钥: {current_key[:10]}...")
            change = input("是否更换API密钥? (y/N): ").strip().lower()
            if change not in ['y', 'yes', '是']:
                self._print_success("保持现有API密钥")
                return True

        # 获取新的API密钥
        print(f"请输入{provider.display_name}API密钥 (或输入 'skip' 跳过):")
        api_key = input("> ").strip()

        if not api_key or api_key.lower() == 'skip':
            self._print_warning("跳过API密钥配置")
            return False

        # 验证API密钥格式
        if len(api_key) < 10:
            self._print_warning("API密钥长度似乎过短，请确认是否正确")
            confirm = input("是否继续? (y/N): ").strip().lower()
            if confirm not in ['y', 'yes', '是']:
                return False

        # 获取API基础URL（如果需要）
        base_url = ""
        if provider.requires_base_url:
            default_url = provider.base_url_default
            print(f"请输入API基础URL (默认: {default_url}):")
            user_url = input("> ").strip()
            base_url = user_url if user_url else default_url

        # 保存配置
        return self._save_provider_config(provider, api_key, base_url)

    def _configure_mock(self) -> bool:
        """配置Mock模式"""
        self._print_header("配置Mock模式")

        self._print_info("Mock模式无需API密钥，用于测试和演示")

        # 创建Mock配置
        mock_config = {
            'llm': {
                'default_provider': 'mock',
                'mock': {
                    'provider': 'mock',
                    'model': 'mock-model',
                    'api_base': 'http://mock-api',
                    'max_tokens': 4000,
                    'temperature': 0.1
                }
            }
        }

        try:
            # 保存配置文件
            with open(self.user_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(mock_config, f, default_flow_style=False, allow_unicode=True)

            self._print_success("Mock模式配置完成")
            return True

        except Exception as e:
            self._print_error(f"保存Mock配置失败: {e}")
            return False

    def _save_provider_config(self, provider: LLMProvider, api_key: str, base_url: str = "") -> bool:
        """保存提供商配置"""
        try:
            # 保存到.env文件
            env_lines = []
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    env_lines = f.readlines()

            # 更新或添加API密钥
            updated = False
            for i, line in enumerate(env_lines):
                if line.strip().startswith(f"{provider.env_key}="):
                    env_lines[i] = f"{provider.env_key}={api_key}\n"
                    updated = True
                    break

            if not updated:
                env_lines.append(f"{provider.env_key}={api_key}\n")

            # 添加API基础URL（如果有）
            if base_url and provider.requires_base_url:
                base_url_key = f"{provider.env_key.replace('_API_KEY', '_BASE_URL')}"
                base_updated = False
                for i, line in enumerate(env_lines):
                    if line.strip().startswith(f"{base_url_key}="):
                        env_lines[i] = f"{base_url_key}={base_url}\n"
                        base_updated = True
                        break

                if not base_updated:
                    env_lines.append(f"{base_url_key}={base_url}\n")

            # 写入.env文件
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(env_lines)

            # 设置环境变量（当前会话）
            os.environ[provider.env_key] = api_key
            if base_url and provider.requires_base_url:
                base_url_key = f"{provider.env_key.replace('_API_KEY', '_BASE_URL')}"
                os.environ[base_url_key] = base_url

            # 询问是否更新配置文件
            update_config = input("是否更新配置文件? (y/N): ").strip().lower()
            if update_config in ['y', 'yes', '是']:
                # 询问更新哪种配置文件
                print("选择要更新的配置文件:")
                print("1) 用户配置文件 (~/.aidefect/config.yaml)")
                print("2) LLM配置文件 (config/llm_config.yaml)")
                print("3) 两者都更新")

                config_choice = input("请选择 (1-3): ").strip()

                if config_choice in ['1', '3']:
                    self._update_user_config_default(provider.name, base_url)
                if config_choice in ['2', '3']:
                    self._update_llm_config(provider, api_key, base_url)

            self._print_success(f"{provider.display_name}配置完成")
            return True

        except Exception as e:
            self._print_error(f"保存配置失败: {e}")
            return False

    def _update_user_config_default(self, provider_name: str, base_url: str = ""):
        """更新用户配置文件的默认提供商"""
        try:
            config = {}
            if self.user_config_file.exists():
                with open(self.user_config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}

            # 确保llm配置存在
            if 'llm' not in config:
                config['llm'] = {}

            config['llm']['default_provider'] = provider_name

            # 确保提供商配置存在
            if provider_name not in config['llm']:
                provider = self.providers[provider_name]
                config['llm'][provider_name] = {
                    'provider': provider_name,
                    'model': self._get_default_model(provider_name),
                    'api_base': base_url if base_url else provider.base_url_default,
                    'max_tokens': 4000,
                    'temperature': 0.1
                }

            with open(self.user_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            self._print_success(f"已设置{provider_name}为默认提供商")

        except Exception as e:
            self._print_warning(f"更新配置文件失败: {e}")

    def _update_llm_config(self, provider: LLMProvider, api_key: str, base_url: str = ""):
        """更新LLM配置文件"""
        try:
            # 读取现有LLM配置
            llm_config = {}
            if self.llm_config_file.exists():
                with open(self.llm_config_file, 'r', encoding='utf-8') as f:
                    llm_config = yaml.safe_load(f) or {}

            # 确保providers配置存在
            if 'providers' not in llm_config:
                llm_config['providers'] = {}

            # 更新或添加提供商配置
            provider_config = {
                'provider': provider.name,
                'model': self._get_default_model(provider.name),
                'api_key': f"${{{provider.env_key}}}",  # 使用环境变量
                'api_base': base_url if base_url else provider.base_url_default,
                'max_tokens': 4000,
                'temperature': 0.3,
                'timeout': 60 if provider.name == 'zhipu' else 30,
                'max_retries': 3
            }

            llm_config['providers'][provider.name] = provider_config

            # 备份现有配置
            if self.llm_config_file.exists():
                backup_file = self.llm_config_file.with_suffix('.yaml.backup')
                import shutil
                shutil.copy2(self.llm_config_file, backup_file)
                self._print_info(f"已备份LLM配置文件: {backup_file}")

            # 写入新配置
            with open(self.llm_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(llm_config, f, default_flow_style=False, allow_unicode=True)

            self._print_success(f"已更新LLM配置文件: {self.llm_config_file}")

        except Exception as e:
            self._print_error(f"更新LLM配置文件失败: {e}")

    def _get_default_model(self, provider_name: str) -> str:
        """获取提供商的默认模型"""
        model_mapping = {
            'zhipu': 'glm-4',
            'openai': 'gpt-3.5-turbo',
            'anthropic': 'claude-3-sonnet-20240229',
            'mock': 'mock-model'
        }
        return model_mapping.get(provider_name, 'default-model')

    def test_provider_connection(self, provider_name: str) -> bool:
        """测试提供商连接"""
        if provider_name not in self.providers:
            self._print_error(f"不支持的提供商: {provider_name}")
            return False

        if provider_name == 'mock':
            self._print_success("Mock模式无需测试连接")
            return True

        provider = self.providers[provider_name]
        self._print_header(f"测试{provider.display_name}连接")

        # 检查API密钥
        api_key = os.environ.get(provider.env_key)
        if not api_key:
            self._print_error(f"未找到{provider.display_name}的API密钥")
            return False

        self._print_info("正在测试连接...")

        try:
            # 尝试导入LLM客户端
            from llm.client import LLMClient
            from llm.interfaces import LLMRequest

            client = LLMClient()

            # 创建测试请求
            request = LLMRequest(
                messages=[{"role": "user", "content": "Hello, this is a test."}],
                max_tokens=10,
                temperature=0.1
            )

            # 异步测试
            import asyncio

            async def test_connection():
                response = await client.complete(request, provider_name)
                return response

            # 运行测试
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(test_connection())
                loop.close()

                if response and hasattr(response, 'content') and response.content:
                    self._print_success(f"{provider.display_name}连接测试成功")
                    self._print_info(f"响应内容: {response.content[:50]}...")
                    return True
                else:
                    self._print_error(f"{provider.display_name}连接测试失败: 无有效响应")
                    return False

            except Exception as e:
                loop.close()
                raise e

        except ImportError:
            self._print_warning("LLM客户端模块不可用，使用基础测试")
            return self._basic_connection_test(provider)
        except Exception as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg:
                self._print_error(f"{provider.display_name}连接超时")
                self._print_info("解决方案: 检查网络连接或代理设置")
            elif "authentication" in error_msg or "unauthorized" in error_msg:
                self._print_error(f"{provider.display_name}认证失败")
                self._print_info("解决方案: 检查API密钥是否正确")
            elif "connection" in error_msg:
                self._print_error(f"{provider.display_name}连接失败")
                self._print_info("解决方案: 检查网络连接和API地址")
            else:
                self._print_error(f"{provider.display_name}连接失败: {e}")

            return False

    def _basic_connection_test(self, provider: LLMProvider) -> bool:
        """基础连接测试（当LLM客户端不可用时）"""
        import requests
        import time

        try:
            if provider.name == 'zhipu':
                # 测试智谱API连接
                headers = {
                    'Authorization': f'Bearer {os.environ.get(provider.env_key)}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'model': 'glm-4',
                    'messages': [{'role': 'user', 'content': 'test'}],
                    'max_tokens': 10
                }
                response = requests.post('https://open.bigmodel.cn/api/paas/v4/chat/completions',
                                       headers=headers, json=data, timeout=10)

                if response.status_code == 200:
                    self._print_success(f"{provider.display_name}连接测试成功")
                    return True
                elif response.status_code == 401:
                    self._print_error(f"{provider.display_name}认证失败")
                    return False
                else:
                    self._print_error(f"{provider.display_name}连接失败: HTTP {response.status_code}")
                    return False

            elif provider.name == 'openai':
                # 测试OpenAI API连接
                headers = {
                    'Authorization': f'Bearer {os.environ.get(provider.env_key)}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'model': 'gpt-3.5-turbo',
                    'messages': [{'role': 'user', 'content': 'test'}],
                    'max_tokens': 10
                }
                base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
                response = requests.post(f'{base_url}/chat/completions',
                                       headers=headers, json=data, timeout=10)

                if response.status_code == 200:
                    self._print_success(f"{provider.display_name}连接测试成功")
                    return True
                elif response.status_code == 401:
                    self._print_error(f"{provider.display_name}认证失败")
                    return False
                else:
                    self._print_error(f"{provider.display_name}连接失败: HTTP {response.status_code}")
                    return False

            else:
                self._print_warning(f"暂不支持{provider.display_name}的基础连接测试")
                return True  # 假设可用

        except requests.exceptions.Timeout:
            self._print_error(f"{provider.display_name}连接超时")
            return False
        except requests.exceptions.ConnectionError:
            self._print_error(f"{provider.display_name}连接失败")
            return False
        except Exception as e:
            self._print_error(f"{provider.display_name}连接测试失败: {e}")
            return False

    def run_diagnosis(self):
        """运行配置诊断"""
        self._print_header("运行配置诊断")

        try:
            # 尝试运行专业的诊断工具
            diagnose_script = self.base_dir / 'scripts' / 'diagnose_config.py'
            if diagnose_script.exists():
                self._print_info("运行专业诊断工具...")
                result = subprocess.run([sys.executable, str(diagnose_script)],
                                      cwd=self.base_dir, capture_output=False, text=True)
                return result.returncode == 0
            else:
                self._print_warning("专业诊断工具不存在，运行基础诊断...")
                return self._basic_diagnosis()

        except Exception as e:
            self._print_error(f"诊断失败: {e}")
            return False

    def _basic_diagnosis(self) -> bool:
        """基础诊断"""
        issues = []
        suggestions = []

        # 检查配置文件
        if not self.user_config_file.exists():
            issues.append("用户配置文件不存在")
            suggestions.append("创建用户配置文件")

        # 检查API密钥
        config = self.load_existing_config()
        has_api = any(provider.env_key and config.get(provider.env_key)
                     for provider in self.providers.values())

        if not has_api:
            issues.append("未配置任何API密钥")
            suggestions.append("配置至少一个LLM提供商")

        # 检查Python依赖
        try:
            import yaml
            import requests
        except ImportError as e:
            issues.append(f"缺少Python依赖: {e}")
            suggestions.append(f"安装依赖: pip install {str(e).split()[-1]}")

        # 输出诊断结果
        if issues:
            print("🔍 发现的问题:")
            for issue in issues:
                print(f"   ❌ {issue}")

            print("\n💡 解决建议:")
            for suggestion in suggestions:
                print(f"   ✅ {suggestion}")
            return False
        else:
            self._print_success("未发现配置问题")
            return True

    def interactive_menu(self):
        """交互式配置菜单"""
        while True:
            self._print_header("LLM配置向导")

            # 显示当前状态
            status = self.check_existing_config()
            configured_count = sum(1 for v in status.values() if v and v != 'mock')

            print(f"当前状态: 已配置 {configured_count} 个LLM提供商")
            print()

            # 显示菜单选项
            print("📋 配置选项:")
            print("1) 📊 查看当前配置状态")
            print("2) 🔑 配置智谱AI (推荐国内用户)")
            print("3) 🔑 配置OpenAI")
            print("4) 🔑 配置Anthropic")
            print("5) 🧪 配置Mock模式 (无需API)")
            print("6) 🧪 测试API连接")
            print("7) 🔍 运行配置诊断")
            print("8) 📝 编辑配置文件")
            print("9) 📖 显示使用指南")
            print("0) 🚪 退出")
            print()

            choice = input("请选择操作 (0-9): ").strip()

            if choice == '1':
                self.display_current_status()
                input("\n按回车键继续...")

            elif choice == '2':
                self.configure_provider('zhipu')
                input("\n按回车键继续...")

            elif choice == '3':
                self.configure_provider('openai')
                input("\n按回车键继续...")

            elif choice == '4':
                self.configure_provider('anthropic')
                input("\n按回车键继续...")

            elif choice == '5':
                self.configure_provider('mock')
                input("\n按回车键继续...")

            elif choice == '6':
                print("\n选择要测试的提供商:")
                providers_list = [(k, v) for k, v in self.providers.items()
                                if k != 'mock' and status.get(k, False)]

                if not providers_list:
                    print("❌ 没有已配置的LLM提供商可供测试")
                    input("\n按回车键继续...")
                    continue

                for i, (key, provider) in enumerate(providers_list, 1):
                    print(f"{i}) {provider.display_name}")

                test_choice = input(f"请选择 (1-{len(providers_list)}): ").strip()
                try:
                    test_index = int(test_choice) - 1
                    if 0 <= test_index < len(providers_list):
                        provider_key = providers_list[test_index][0]
                        self.test_provider_connection(provider_key)
                    else:
                        print("❌ 无效选择")
                except ValueError:
                    print("❌ 无效选择")

                input("\n按回车键继续...")

            elif choice == '7':
                self.run_diagnosis()
                input("\n按回车键继续...")

            elif choice == '8':
                self._edit_config_file()
                input("\n按回车键继续...")

            elif choice == '9':
                self._show_usage_guide()
                input("\n按回车键继续...")

            elif choice == '0':
                print("\n👋 配置完成！")
                break

            else:
                print("❌ 无效选择，请输入0-9")
                input("\n按回车键继续...")

    def _edit_config_file(self):
        """编辑配置文件"""
        if not self.user_config_file.exists():
            self._print_warning("用户配置文件不存在，创建基础配置...")
            self._configure_mock()

        # 检测系统并尝试用默认编辑器打开
        system = platform.system()
        try:
            if system == "Windows":
                os.startfile(str(self.user_config_file))
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(self.user_config_file)], check=True)
            else:  # Linux
                editor = os.environ.get('EDITOR', 'nano')
                subprocess.run([editor, str(self.user_config_file)], check=True)

            self._print_success(f"已打开配置文件: {self.user_config_file}")

        except Exception as e:
            self._print_error(f"无法打开配置文件: {e}")
            self._print_info(f"请手动编辑: {self.user_config_file}")

    def _show_usage_guide(self):
        """显示使用指南"""
        self._print_header("使用指南")

        print("🚀 快速开始:")
        print("1. 配置API密钥（使用选项2-4）")
        print("2. 测试API连接（选项6）")
        print("3. 运行深度分析:")
        print("   python main.py analyze deep <文件路径> --verbose")
        print()

        print("📝 示例命令:")
        print("# 分析配置文件")
        print("python main.py analyze deep src/utils/config.py")
        print()
        print("# 分析多个文件")
        print("python main.py analyze deep src/**/*.py")
        print()
        print("# 启动Web界面")
        print("python main.py web")
        print()

        print("💡 交互模式命令:")
        print("- help: 显示帮助")
        print("- analyze <文件>: 分析指定文件")
        print("- summary: 显示分析摘要")
        print("- export <文件>: 导出对话历史")
        print("- exit: 退出")
        print()

        print("📚 更多帮助:")
        print("- 完整文档: docs/README.md")
        print("- API配置: docs/API_CONFIG_GUIDE.md")
        print("- 故障排除: python scripts/diagnose_config.py")
        print()

        print("🔧 配置文件位置:")
        print(f"- 用户配置: {self.user_config_file}")
        print(f"- 环境变量: {self.env_file}")

    def quick_setup(self):
        """快速设置（非交互式）"""
        self._print_header("快速设置")

        # 检查现有配置
        status = self.check_existing_config()
        configured_providers = [name for name, configured in status.items()
                              if configured and name != 'mock']

        if configured_providers:
            self._print_success(f"已配置提供商: {', '.join(configured_providers)}")

            # 测试连接
            for provider_name in configured_providers[:1]:  # 只测试第一个
                self.test_provider_connection(provider_name)
                break
        else:
            self._print_warning("未配置任何LLM提供商")

            # 尝试配置智谱AI（推荐给国内用户）
            print("尝试配置智谱AI（推荐给国内用户）...")
            if self.configure_provider('zhipu'):
                self.test_provider_connection('zhipu')
            else:
                print("配置失败，使用Mock模式...")
                self._configure_mock()

        # 运行诊断
        self._print_info("运行配置诊断...")
        self.run_diagnosis()

        self._print_success("快速设置完成！")

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='AIDefectDetector LLM配置工具')
    parser.add_argument('--quick', action='store_true', help='快速设置模式')
    parser.add_argument('--provider', choices=['zhipu', 'openai', 'anthropic', 'mock'],
                       help='直接配置指定提供商')
    parser.add_argument('--test', choices=['zhipu', 'openai', 'anthropic'],
                       help='测试指定提供商连接')
    parser.add_argument('--status', action='store_true', help='显示当前配置状态')
    parser.add_argument('--diagnose', action='store_true', help='运行配置诊断')

    args = parser.parse_args()

    try:
        configurator = LLMConfigurator()

        if args.status:
            configurator.display_current_status()

        elif args.provider:
            if configurator.configure_provider(args.provider):
                if args.provider != 'mock':
                    configurator.test_provider_connection(args.provider)

        elif args.test:
            configurator.test_provider_connection(args.test)

        elif args.diagnose:
            success = configurator.run_diagnosis()
            sys.exit(0 if success else 1)

        elif args.quick:
            configurator.quick_setup()

        else:
            # 默认进入交互式菜单
            configurator.interactive_menu()

    except KeyboardInterrupt:
        print("\n\n❌ 配置被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 配置失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()