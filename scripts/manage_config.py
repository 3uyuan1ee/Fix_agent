#!/usr/bin/env python3
"""
AIDefectDetector 配置管理工具
用于管理不同环境的配置模板
"""

import os
import sys
import shutil
import argparse
from pathlib import Path
from typing import Dict, List, Optional

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / 'src'))

class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent  # 指向项目根目录
        self.config_dir = self.base_dir / 'config'
        self.examples_dir = self.config_dir / 'examples'
        self.user_config_file = self.config_dir / 'user_config.yaml'

        self.templates = {
            'development': '开发环境 - 本地开发和功能测试',
            'production': '生产环境 - 正式部署和高可用服务',
            'testing': '测试环境 - 自动化测试和CI/CD',
            'minimal': '最小化 - 快速体验和演示'
        }

    def list_templates(self) -> None:
        """列出所有可用模板"""
        print("📁 可用配置模板:")
        print("=" * 50)

        for name, description in self.templates.items():
            template_file = self.examples_dir / f'{name}.yaml'
            status = "✅" if template_file.exists() else "❌"
            print(f"  {status} {name:12} - {description}")

        print(f"\n模板目录: {self.examples_dir}")
        print(f"用户配置: {self.user_config_file}")

    def show_template(self, template_name: str) -> None:
        """显示模板内容"""
        template_file = self.examples_dir / f'{template_name}.yaml'

        if not template_file.exists():
            print(f"❌ 模板 '{template_name}' 不存在")
            print("💡 使用 'list' 命令查看可用模板")
            return

        print(f"📄 模板内容: {template_name}")
        print("=" * 50)

        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)

    def apply_template(self, template_name: str, backup: bool = True) -> bool:
        """应用模板到用户配置"""
        template_file = self.examples_dir / f'{template_name}.yaml'

        if not template_file.exists():
            print(f"❌ 模板 '{template_name}' 不存在")
            return False

        # 备份现有配置
        if self.user_config_file.exists() and backup:
            backup_file = self.config_dir / f'user_config.backup.{int(os.path.getmtime(self.user_config_file))}.yaml'
            shutil.copy2(self.user_config_file, backup_file)
            print(f"✅ 已备份现有配置到: {backup_file.name}")

        # 应用新模板
        shutil.copy2(template_file, self.user_config_file)
        print(f"✅ 已应用模板 '{template_name}' 到用户配置")
        print(f"📁 配置文件: {self.user_config_file}")

        # 显示后续步骤
        print(f"\n📋 后续步骤:")
        print(f"1. 编辑配置文件: vim config/user_config.yaml")
        print(f"2. 设置环境变量:")

        # 读取模板内容，提取需要的环境变量
        with open(template_file, 'r', encoding='utf-8') as f:
            content = f.read()

        import re
        env_vars = re.findall(r'\$\{([^:}]+)', content)
        unique_vars = list(set(env_vars))

        for var in unique_vars:
            print(f"   export {var}='your-value'")

        print(f"3. 验证配置: python3 scripts/diagnose_config.py")

        return True

    def backup_config(self) -> None:
        """备份当前配置"""
        if not self.user_config_file.exists():
            print("❌ 用户配置文件不存在")
            return

        timestamp = int(os.path.getmtime(self.user_config_file))
        backup_file = self.config_dir / f'user_config.backup.{timestamp}.yaml'

        shutil.copy2(self.user_config_file, backup_file)
        print(f"✅ 配置已备份到: {backup_file}")

    def restore_config(self, backup_name: str) -> bool:
        """恢复配置备份"""
        if not backup_name.startswith('user_config.backup.'):
            backup_name = f'user_config.backup.{backup_name}.yaml'
        elif not backup_name.endswith('.yaml'):
            backup_name += '.yaml'

        backup_file = self.config_dir / backup_name

        if not backup_file.exists():
            print(f"❌ 备份文件 '{backup_name}' 不存在")
            return False

        # 备份当前配置
        if self.user_config_file.exists():
            timestamp = int(os.path.getmtime(self.user_config_file))
            current_backup = self.config_dir / f'user_config.backup.{timestamp}.yaml'
            shutil.copy2(self.user_config_file, current_backup)
            print(f"✅ 已备份当前配置")

        # 恢复备份
        shutil.copy2(backup_file, self.user_config_file)
        print(f"✅ 已恢复配置备份: {backup_name}")

        return True

    def list_backups(self) -> None:
        """列出所有配置备份"""
        print("📦 配置备份列表:")
        print("=" * 50)

        backups = list(self.config_dir.glob('user_config.backup.*.yaml'))

        if not backups:
            print("  没有找到配置备份")
            return

        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for backup in backups:
            mtime = backup.stat().st_mtime
            import datetime
            time_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            size = backup.stat().st_size

            print(f"  📄 {backup.name}")
            print(f"     时间: {time_str}")
            print(f"     大小: {size} bytes")
            print()

    def validate_config(self) -> None:
        """验证当前配置"""
        print("🔍 验证配置...")
        print("=" * 50)

        if not self.user_config_file.exists():
            print("❌ 用户配置文件不存在")
            print("💡 使用 'apply <template>' 创建配置文件")
            return

        try:
            import yaml
            with open(self.user_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            print("✅ 配置文件语法正确")

            # 检查必要字段
            if 'llm' in config:
                llm_config = config['llm']
                if 'default_provider' in llm_config:
                    provider = llm_config['default_provider']
                    print(f"✅ 默认provider: {provider}")

                    if provider in llm_config:
                        provider_config = llm_config[provider]
                        required_fields = ['provider', 'model']
                        missing_fields = [f for f in required_fields if f not in provider_config]

                        if missing_fields:
                            print(f"⚠️ Provider配置缺少字段: {missing_fields}")
                        else:
                            print(f"✅ Provider配置完整")
                    else:
                        print(f"❌ Provider '{provider}' 配置缺失")
                else:
                    print("❌ 缺少default_provider配置")
            else:
                print("❌ 缺少llm配置")

            # 检查环境变量
            print("\n🔑 环境变量检查:")
            import re
            with open(self.user_config_file, 'r', encoding='utf-8') as f:
                content = f.read()

            env_vars = re.findall(r'\$\{([^:}]+)', content)
            unique_vars = list(set(env_vars))

            for var in unique_vars:
                value = os.environ.get(var)
                if value:
                    if len(value) > 10:
                        print(f"✅ {var}: 已设置")
                    else:
                        print(f"⚠️ {var}: 已设置但可能不完整")
                else:
                    print(f"❌ {var}: 未设置")

            print(f"\n💡 建议运行 'python3 scripts/diagnose_config.py' 进行完整诊断")

        except yaml.YAMLError as e:
            print(f"❌ YAML语法错误: {e}")
        except Exception as e:
            print(f"❌ 验证失败: {e}")

    def show_status(self) -> None:
        """显示当前配置状态"""
        print("📊 当前配置状态:")
        print("=" * 50)

        # 检查用户配置文件
        if self.user_config_file.exists():
            mtime = self.user_config_file.stat().st_mtime
            import datetime
            time_str = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            size = self.user_config_file.stat().st_size

            print(f"✅ 用户配置文件存在")
            print(f"   路径: {self.user_config_file}")
            print(f"   修改时间: {time_str}")
            print(f"   文件大小: {size} bytes")
        else:
            print(f"❌ 用户配置文件不存在")

        # 检查环境变量
        print(f"\n🔑 API密钥状态:")
        api_vars = ['ZHIPU_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
        for var in api_vars:
            value = os.environ.get(var)
            if value:
                print(f"✅ {var}: 已配置")
            else:
                print(f"❌ {var}: 未配置")

        # 检查诊断工具
        diagnose_tool = self.base_dir / 'scripts' / 'diagnose_config.py'
        if diagnose_tool.exists():
            print(f"\n✅ 诊断工具可用: python3 scripts/diagnose_config.py")
        else:
            print(f"\n❌ 诊断工具不存在")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AIDefectDetector 配置管理工具')
    parser.add_argument('command', choices=[
        'list', 'show', 'apply', 'backup', 'restore', 'backups', 'validate', 'status'
    ], help='要执行的命令')

    parser.add_argument('template', nargs='?', help='模板名称 (用于show和apply命令)')
    parser.add_argument('--no-backup', action='store_true', help='应用模板时不备份现有配置')

    args = parser.parse_args()

    manager = ConfigManager()

    try:
        if args.command == 'list':
            manager.list_templates()

        elif args.command == 'show':
            if not args.template:
                print("❌ 请指定模板名称")
                print("💡 使用 'list' 查看可用模板")
                return
            manager.show_template(args.template)

        elif args.command == 'apply':
            if not args.template:
                print("❌ 请指定模板名称")
                print("💡 使用 'list' 查看可用模板")
                return
            manager.apply_template(args.template, backup=not args.no_backup)

        elif args.command == 'backup':
            manager.backup_config()

        elif args.command == 'restore':
            if not args.template:
                print("❌ 请指定备份名称")
                print("💡 使用 'backups' 查看可用备份")
                return
            manager.restore_config(args.template)

        elif args.command == 'backups':
            manager.list_backups()

        elif args.command == 'validate':
            manager.validate_config()

        elif args.command == 'status':
            manager.show_status()

    except KeyboardInterrupt:
        print("\n❌ 操作被用户中断")
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()