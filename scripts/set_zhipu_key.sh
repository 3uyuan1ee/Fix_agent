#!/bin/bash

# 智谱AI API密钥快速设置脚本

echo "🚀 智谱AI API密钥设置"
echo "===================="

# 检查是否已有API密钥
if [ -n "$ZHIPU_API_KEY" ]; then
    echo "✅ 智谱AI API密钥已设置"
    echo "当前API密钥: ${ZHIPU_API_KEY:0:8}..."
    echo ""
    echo "如需更换API密钥，请继续操作"
else
    echo "❌ 智谱AI API密钥未设置"
fi

echo ""
echo "📋 获取API密钥步骤："
echo "1. 访问 https://open.bigmodel.cn/"
echo "2. 注册并登录账号"
echo "3. 在控制台 -> API密钥页面获取密钥"
echo "4. 确保账户有余额"
echo ""

# 输入API密钥
read -p "请输入您的智谱AI API密钥: " api_key

if [ -z "$api_key" ]; then
    echo "❌ 未输入API密钥，设置取消"
    exit 1
fi

# 设置环境变量
export ZHIPU_API_KEY="$api_key"
echo "✅ 智谱AI API密钥已设置"

# 询问是否保存到文件
echo ""
read -p "是否保存API密钥到 .env 文件? (y/n): " save_env

if [ "$save_env" = "y" ] || [ "$save_env" = "Y" ]; then
    if [ -f ".env" ]; then
        # 更新现有文件
        if grep -q "ZHIPU_API_KEY=" .env; then
            sed -i.bak "s/ZHIPU_API_KEY=.*/ZHIPU_API_KEY=$api_key/" .env
            echo "✅ 已更新 .env 文件"
        else
            echo "ZHIPU_API_KEY=$api_key" >> .env
            echo "✅ 已添加到 .env 文件"
        fi
    else
        echo "ZHIPU_API_KEY=$api_key" > .env
        echo "✅ 已创建 .env 文件"
    fi
fi

# 询问是否保存到bashrc
echo ""
read -p "是否添加到 ~/.bashrc 以便永久生效? (y/n): " save_bashrc

if [ "$save_bashrc" = "y" ] || [ "$save_bashrc" = "Y" ]; then
    if ! grep -q "ZHIPU_API_KEY=" ~/.bashrc; then
        echo "" >> ~/.bashrc
        echo "# AIDefectDetector 智谱AI API密钥" >> ~/.bashrc
        echo "export ZHIPU_API_KEY=\"$api_key\"" >> ~/.bashrc
        echo "✅ 已添加到 ~/.bashrc"
        echo "   请运行 'source ~/.bashrc' 或重新打开终端以生效"
    else
        echo "⚠️ ~/.bashrc 中已存在ZHIPU_API_KEY设置"
    fi
fi

echo ""
echo "🧪 测试配置..."
echo "===================="

# 检查是否有专业诊断工具
if [ -f "scripts/diagnose_config.py" ]; then
    echo "🔍 使用专业诊断工具进行深度检查..."
    python3 scripts/diagnose_config.py
else
    echo "⚠️ 诊断工具不存在，使用基础测试..."

    # 测试配置
    cat > test_zhipu.py << 'EOF'
import os
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path('.') / 'src'))

print(f"API密钥设置状态: {'✅ 已设置' if os.environ.get('ZHIPU_API_KEY') else '❌ 未设置'}")

try:
    from llm.config import LLMConfigManager
    config_manager = LLMConfigManager()

    # 检查智谱AI配置
    zhipu_config = config_manager.get_config('zhipu')
    if zhipu_config:
        print(f"✅ 智谱AI配置加载成功")
        print(f"   模型: {zhipu_config.model}")
        print(f"   API地址: {zhipu_config.api_base}")
        print(f"   最大tokens: {zhipu_config.max_tokens}")
    else:
        print("❌ 智谱AI配置加载失败")

except Exception as e:
    print(f"❌ 配置测试失败: {e}")
    print("   这通常是因为缺少依赖或配置文件问题")
    print("💡 建议: 运行 python3 diagnose_config.py 进行详细诊断")
EOF

    python3 test_zhipu.py
    rm test_zhipu.py
fi

echo ""
echo "🎯 立即开始使用"
echo "===================="
echo "现在您可以运行深度分析："
echo ""
echo "python3 main.py analyze deep src/utils/config.py --verbose"
echo ""
echo "或者使用配置脚本进行更详细的配置："
echo "./scripts/setup_api.sh"
echo ""

echo "💡 提示:"
echo "- 在交互模式中输入 'analyze <文件路径>' 来分析文件"
echo "- 输入 'help' 查看所有可用命令"
echo "- 输入 'exit' 退出分析"