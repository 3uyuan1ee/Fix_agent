#!/bin/bash

# API配置快速设置脚本
# 用于快速设置LLM API密钥并测试深度分析功能

echo "🚀 AIDefectDetector API配置向导"
echo "=================================="

# 加载配置文件
load_configurations() {
    # 优先加载.env文件
    if [ -f ".env" ]; then
        echo "🔄 加载 .env 文件..."
        set -a  # 自动导出变量
        source .env
        set +a
    fi

    # 加载 ~/.bashrc 中的环境变量（仅提取API相关）
    if [ -f "$HOME/.bashrc" ]; then
        echo "🔄 检查 ~/.bashrc 中的API配置..."
        # 提取API相关变量并设置
        eval $(grep -E '^export (ZHIPU|OPENAI|ANTHROPIC)_API_KEY=' "$HOME/.bashrc" | sed 's/^export //')
    fi
}

# 检查是否已有API密钥环境变量
check_existing_keys() {
    echo "📋 检查现有API密钥..."

    if [ -n "$ZHIPU_API_KEY" ]; then
        echo "✅ 智谱AI API密钥已配置"
        ZHIPU_CONFIGURED=true
    else
        echo "❌ 智谱AI API密钥未配置"
        ZHIPU_CONFIGURED=false
    fi

    if [ -n "$OPENAI_API_KEY" ]; then
        echo "✅ OpenAI API密钥已配置"
        OPENAI_CONFIGURED=true
    else
        echo "❌ OpenAI API密钥未配置"
        OPENAI_CONFIGURED=false
    fi

    if [ -n "$ANTHROPIC_API_KEY" ]; then
        echo "✅ Anthropic API密钥已配置"
        ANTHROPIC_CONFIGURED=true
    else
        echo "❌ Anthropic API密钥未配置"
        ANTHROPIC_CONFIGURED=false
    fi
}

# 配置智谱AI
setup_zhipu() {
    echo ""
    echo "🎯 配置智谱AI (推荐用于国内用户)"
    echo "----------------------------------"

    read -p "请输入您的智谱AI API密钥: " ZHIPU_KEY

    if [ -n "$ZHIPU_KEY" ]; then
        export ZHIPU_API_KEY="$ZHIPU_KEY"
        echo "✅ 智谱AI API密钥已设置"

        # 询问是否保存到shell配置文件
        read -p "是否保存到 ~/.bashrc? (y/n): " save_bashrc
        if [ "$save_bashrc" = "y" ] || [ "$save_bashrc" = "Y" ]; then
            echo "export ZHIPU_API_KEY=\"$ZHIPU_KEY\"" >> ~/.bashrc
            echo "✅ 已保存到 ~/.bashrc"
        fi

        # 询问是否保存到.env文件
        read -p "是否创建 .env 文件? (y/n): " create_env
        if [ "$create_env" = "y" ] || [ "$create_env" = "Y" ]; then
            echo "ZHIPU_API_KEY=$ZHIPU_KEY" > .env
            echo "✅ 已创建 .env 文件"
        fi

        return 0
    else
        echo "❌ 未输入API密钥"
        return 1
    fi
}

# 配置OpenAI
setup_openai() {
    echo ""
    echo "🎯 配置OpenAI"
    echo "----------------------------------"

    read -p "请输入您的OpenAI API密钥: " OPENAI_KEY
    read -p "请输入OpenAI API地址 (默认: https://api.openai.com/v1): " OPENAI_URL

    if [ -n "$OPENAI_KEY" ]; then
        export OPENAI_API_KEY="$OPENAI_KEY"
        export OPENAI_BASE_URL="${OPENAI_URL:-https://api.openai.com/v1}"
        echo "✅ OpenAI API密钥已设置"
        echo "✅ OpenAI API地址: $OPENAI_BASE_URL"

        # 保存到.env文件
        echo "OPENAI_API_KEY=$OPENAI_KEY" >> .env
        echo "OPENAI_BASE_URL=$OPENAI_BASE_URL" >> .env
        echo "✅ 已保存到 .env 文件"

        return 0
    else
        echo "❌ 未输入API密钥"
        return 1
    fi
}

# 配置Anthropic
setup_anthropic() {
    echo ""
    echo "🎯 配置Anthropic"
    echo "----------------------------------"

    read -p "请输入您的Anthropic API密钥: " ANTHROPIC_KEY
    read -p "请输入Anthropic API地址 (默认: https://api.anthropic.com): " ANTHROPIC_URL

    if [ -n "$ANTHROPIC_KEY" ]; then
        export ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
        export ANTHROPIC_BASE_URL="${ANTHROPIC_URL:-https://api.anthropic.com}"
        echo "✅ Anthropic API密钥已设置"
        echo "✅ Anthropic API地址: $ANTHROPIC_BASE_URL"

        # 保存到.env文件
        echo "ANTHROPIC_API_KEY=$ANTHROPIC_KEY" >> .env
        echo "ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL" >> .env
        echo "✅ 已保存到 .env 文件"

        return 0
    else
        echo "❌ 未输入API密钥"
        return 1
    fi
}

# 测试API连接
test_api_connection() {
    echo ""
    echo "🧪 测试API连接..."
    echo "----------------------------------"

    # 检查是否有诊断工具
    if [ -f "scripts/diagnose_config.py" ]; then
        echo "🔍 使用专业诊断工具进行深度检查..."
        python3 scripts/diagnose_config.py
    else
        echo "⚠️ 诊断工具不存在，使用基础检查..."

        # 创建临时测试脚本
        cat > test_api.py << 'EOF'
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path('.') / 'src'))

try:
    from llm.config import LLMConfigManager

    config_manager = LLMConfigManager()
    providers = config_manager.list_providers()

    print(f"可用providers: {providers}")

    # 检查智谱AI
    if 'zhipu' in providers and os.environ.get('ZHIPU_API_KEY'):
        print("✅ 智谱AI配置可用")
    elif 'zhipu' in providers:
        print("⚠️ 智谱AI已配置但缺少API密钥")

    # 检查OpenAI
    if 'openai' in providers and os.environ.get('OPENAI_API_KEY'):
        print("✅ OpenAI配置可用")
    elif 'openai' in providers:
        print("⚠️ OpenAI已配置但缺少API密钥")

    # 检查Anthropic
    if 'anthropic' in providers and os.environ.get('ANTHROPIC_API_KEY'):
        print("✅ Anthropic配置可用")
    elif 'anthropic' in providers:
        print("⚠️ Anthropic已配置但缺少API密钥")

    # 检查Mock
    if 'mock' in providers:
        print("✅ Mock配置可用 (回退选项)")

except Exception as e:
    print(f"❌ 配置检查失败: {e}")
    print("💡 建议: 运行 python3 scripts/diagnose_config.py 进行详细诊断")
    sys.exit(1)
EOF

        python3 test_api.py
        rm test_api.py
    fi
}

# 运行深度分析测试
run_test_analysis() {
    echo ""
    echo "🔬 运行深度分析测试..."
    echo "----------------------------------"

    read -p "是否运行深度分析测试? (需要API密钥) (y/n): " run_test
    if [ "$run_test" = "y" ] || [ "$run_test" = "Y" ]; then
        echo "正在测试深度分析功能..."
        echo "分析目标: src/utils/config.py"
        echo ""

        # 使用echo提供测试输入
        echo "分析这个文件" | timeout 30 python3 main.py analyze deep src/utils/config.py --verbose 2>/dev/null || {
            echo ""
            echo "⚠️ 测试超时或失败，但基本配置已完成"
            echo "请检查API密钥和网络连接"
        }
    fi
}

# 运行完整诊断
run_full_diagnosis() {
    echo ""
    echo "🔍 运行完整系统诊断..."
    echo "----------------------------------"

    if [ -f "scripts/diagnose_config.py" ]; then
        echo "🔬 启动专业诊断工具..."
        python3 scripts/diagnose_config.py
    else
        echo "❌ 诊断工具不存在"
        echo "💡 请确保 scripts/diagnose_config.py 文件存在"
    fi
}

# 主菜单
main_menu() {
    while true; do
        echo ""
        echo "📋 API配置选项:"
        echo "1) 检查现有配置"
        echo "2) 配置智谱AI (推荐)"
        echo "3) 配置OpenAI"
        echo "4) 配置Anthropic"
        echo "5) 测试API连接"
        echo "6) 运行深度分析测试"
        echo "7) 运行完整系统诊断 🔥"
        echo "8) 退出"
        echo ""

        read -p "请选择操作 (1-8): " choice

        case $choice in
            1)
                load_configurations
                check_existing_keys
                ;;
            2)
                setup_zhipu
                ;;
            3)
                setup_openai
                ;;
            4)
                setup_anthropic
                ;;
            5)
                test_api_connection
                ;;
            6)
                run_test_analysis
                ;;
            7)
                run_full_diagnosis
                ;;
            8)
                echo "👋 配置完成！"
                break
                ;;
            *)
                echo "❌ 无效选择，请输入1-8"
                ;;
        esac
    done
}

# 显示使用说明
show_usage() {
    echo ""
    echo "📖 使用说明:"
    echo "=================================="
    echo "1. 配置API密钥后，使用以下命令进行深度分析："
    echo "   python main.py analyze deep <文件路径> --verbose"
    echo ""
    echo "2. 示例："
    echo "   python main.py analyze deep src/utils/config.py"
    echo ""
    echo "3. 交互模式命令："
    echo "   - help: 显示帮助"
    echo "   - analyze <文件>: 分析指定文件"
    echo "   - summary: 显示分析摘要"
    echo "   - export <文件>: 导出对话历史"
    echo "   - exit: 退出"
    echo ""
    echo "4. 详细配置指南请查看: docs/API_CONFIG_GUIDE.md"
}

# 主程序
main() {
    # 首先加载现有配置
    load_configurations

    # 然后检查配置状态
    check_existing_keys

    if [ "$ZHIPU_CONFIGURED" = false ] && [ "$OPENAI_CONFIGURED" = false ] && [ "$ANTHROPIC_CONFIGURED" = false ]; then
        echo ""
        echo "🚀 欢迎使用AIDefectDetector深度分析功能！"
        echo "请先配置至少一个LLM提供商的API密钥。"
        echo ""
        echo "推荐使用智谱AI（国内访问稳定）："
        echo "1. 访问 https://open.bigmodel.cn/ 注册账号"
        echo "2. 获取API密钥"
        echo "3. 在下面选择选项2进行配置"
        echo ""
    fi

    main_menu
    show_usage
}

# 检查是否直接运行脚本
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi