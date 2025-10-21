# 深度分析功能快速开始

## 🚀 快速配置 (推荐方法)

### 方法1: 使用配置脚本 (最简单)

```bash
# 运行配置向导
./setup_api.sh

# 按照提示配置API密钥
# 推荐使用智谱AI (国内访问稳定)
```

### 方法2: 手动配置

```bash
# 1. 设置智谱AI API密钥 (推荐)
export ZHIPU_API_KEY="your-api-key-here"

# 2. 立即开始使用
python main.py analyze deep src/utils/config.py
```

## 📋 配置选项

### 智谱AI (推荐国内用户)
- 🌟 **优势**: 国内访问稳定，性价比高，中文优秀
- 🔗 **注册**: https://open.bigmodel.cn/
- 💰 **费用**: 新用户有免费额度
- 🚀 **速度**: 国内访问快速

### OpenAI (需要代理)
- 🌟 **优势**: 功能强大，生态丰富
- 🔗 **注册**: https://platform.openai.com/
- 💰 **费用**: 按使用量计费
- 🌐 **注意**: 需要代理访问

### Anthropic Claude (需要代理)
- 🌟 **优势**: 推理能力强，安全性高
- 🔗 **注册**: https://console.anthropic.com/
- 💰 **费用**: 按使用量计费
- 🌐 **注意**: 需要代理访问

## 🎯 使用示例

### 基本用法

```bash
# 分析单个文件
python main.py analyze deep src/utils/config.py

# 详细输出
python main.py analyze deep src/utils/config.py --verbose

# 分析整个目录
python main.py analyze deep src/ --verbose
```

### 交互式对话

启动后会进入AI对话模式：

```bash
🤖 AI分析助手> 分析这个文件
🔍 AI正在思考...
🤖 AI: [详细的代码分析结果...]

🤖 AI分析助手> 这个函数有什么安全问题？
🔍 AI正在思考...
🤖 AI: [安全问题的详细分析...]
```

### 支持的分析类型

- `comprehensive` - 综合分析 (默认)
- `security` - 安全分析
- `performance` - 性能分析
- `architecture` - 架构分析
- `code_review` - 代码审查
- `refactoring` - 重构建议

## ⚙️ 高级配置

### 自定义配置文件

编辑 `config/user_config.yaml`:

```yaml
llm:
  default_provider: "zhipu"
  zhipu:
    model: "glm-4.5"
    temperature: 0.3
    max_tokens: 4000

deep_analysis:
  max_file_size: 200000  # 200KB
  temperature: 0.3
```

### 环境变量配置

创建 `.env` 文件:

```env
ZHIPU_API_KEY=your-api-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

## 🛠️ 故障排除

### 常见问题

**Q: 显示"No LLM providers available"**
```bash
# 解决方案: 检查配置文件
ls config/llm_config.yaml
python -c "
import sys; sys.path.insert(0, 'src')
from llm.config import LLMConfigManager
print(LLMConfigManager().list_providers())
"
```

**Q: API密钥认证失败**
```bash
# 解决方案: 验证API密钥
export ZHIPU_API_KEY="your-key"
python main.py analyze deep src/utils/config.py --verbose
```

**Q: 网络连接超时**
```bash
# 解决方案: 使用智谱AI (国内更稳定)
export ZHIPU_API_KEY="your-key"
python main.py analyze deep src/utils/config.py
```

### 回退到Mock模式

如果API有问题，可以临时使用Mock模式：

```bash
# 使用mock配置
cp config/mock_llm_config.yaml config/llm_config.yaml
python main.py analyze deep src/utils/config.py
```

## 📚 详细文档

- 📖 [完整API配置指南](API_CONFIG_GUIDE.md)
- 🔧 [项目架构文档](docs/)
- 🚀 [使用示例](demos/)

## 🎉 开始使用

```bash
# 1. 配置API (推荐智谱AI)
export ZHIPU_API_KEY="your-api-key"

# 2. 分析您的第一个文件
python main.py analyze deep src/your_file.py

# 3. 与AI对话深入分析
# 在交互模式中提问具体问题
```

祝您使用愉快！如有问题，请查看 [API_CONFIG_GUIDE.md](API_CONFIG_GUIDE.md) 获取详细帮助。