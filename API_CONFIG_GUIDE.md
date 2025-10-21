# API配置指南 - 深度分析功能

本指南将帮助您配置真实的LLM API来使用深度分析功能。

## 📋 配置步骤

### 1. 选择LLM提供商

项目支持以下LLM提供商：

| 提供商 | 推荐度 | 说明 | API获取方式 |
|--------|--------|------|-------------|
| **智谱AI** | ⭐⭐⭐⭐⭐ | 国内访问稳定，性价比高 | [智谱AI开放平台](https://open.bigmodel.cn/) |
| **OpenAI** | ⭐⭐⭐⭐ | 功能强大，需要代理访问 | [OpenAI Platform](https://platform.openai.com/) |
| **Anthropic** | ⭐⭐⭐⭐ | Claude模型优秀，需要代理访问 | [Anthropic Console](https://console.anthropic.com/) |

### 2. 获取API密钥

#### 智谱AI (推荐)
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 注册并登录账号
3. 在控制台获取API Key
4. 充值余额（新用户通常有免费额度）

#### OpenAI
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 注册并登录账号
3. 在API Keys页面创建新的API Key
4. 绑定支付方式

#### Anthropic
1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 注册并登录账号
3. 在API Keys页面创建新的API Key
4. 绑定支付方式

### 3. 配置环境变量

创建环境变量文件或直接在终端设置：

```bash
# 智谱AI配置 (推荐)
export ZHIPU_API_KEY="your-zhipu-api-key-here"

# OpenAI配置 (如果使用)
export OPENAI_API_KEY="your-openai-api-key-here"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 或使用代理地址

# Anthropic配置 (如果使用)
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"  # 或使用代理地址
```

### 4. 配置项目

配置文件已经预设在 `config/user_config.yaml` 和 `config/llm_config.yaml` 中，支持环境变量替换。

## 🚀 使用方法

### 方法1: 使用环境变量 (推荐)

```bash
# 1. 设置环境变量
export ZHIPU_API_KEY="your-zhipu-api-key-here"

# 2. 运行深度分析
python main.py analyze deep src/utils/config.py --verbose
```

### 方法2: 修改配置文件

编辑 `config/user_config.yaml`：

```yaml
llm:
  default_provider: "zhipu"
  zhipu:
    api_key: "your-actual-api-key-here"  # 直接填写API密钥
    model: "glm-4.5"
```

### 方法3: 使用.env文件 (推荐用于开发)

创建 `.env` 文件：

```env
ZHIPU_API_KEY=your-zhipu-api-key-here
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

然后安装python-dotenv并加载：

```bash
pip install python-dotenv
```

## 🎯 深度分析使用示例

### 基本用法

```bash
# 分析单个文件
python main.py analyze deep path/to/your/file.py

# 详细输出
python main.py analyze deep path/to/your/file.py --verbose

# 静默模式
python main.py analyze deep path/to/your/file.py --quiet
```

### 交互式对话

深度分析启动后会进入交互模式：

```bash
🤖 AI分析助手> 分析这个代码
🔍 AI正在思考...
🤖 AI: [代码分析结果...]

🤖 AI分析助手> 这个函数有什么问题？
🔍 AI正在思考...
🤖 AI: [针对函数的详细分析...]
```

### 支持的命令

在交互模式中，您可以使用以下命令：

- `help` - 显示帮助信息
- `analyze <文件路径>` - 分析指定文件
- `summary` - 显示当前分析摘要
- `export <文件路径>` - 导出对话历史
- `exit` 或 `quit` - 退出分析

## 🔧 高级配置

### 自定义分析参数

编辑 `config/user_config.yaml` 中的深度分析配置：

```yaml
deep_analysis:
  default_model: "glm-4.5"      # 默认模型
  max_file_size: 100000          # 最大文件大小 (字节)
  temperature: 0.3               # 创造性参数 (0-1)
  max_tokens: 4000               # 最大生成token数
```

### 调整模型参数

不同场景的推荐参数：

```yaml
# 代码审查 (更严格的参数)
code_review:
  temperature: 0.1
  max_tokens: 2000

# 创意改进 (更有创意的参数)
creative_suggestions:
  temperature: 0.7
  max_tokens: 3000

# 安全分析 (更保守的参数)
security_analysis:
  temperature: 0.2
  max_tokens: 4000
```

## 🛠️ 故障排除

### 常见问题

#### 1. API密钥错误
```
ERROR: Authentication failed: Invalid API key
```
**解决方案**: 检查API密钥是否正确，确保没有多余的空格

#### 2. 网络连接问题
```
ERROR: Connection timeout
```
**解决方案**:
- 检查网络连接
- 如果使用OpenAI/Anthropic，配置代理地址
- 考虑使用智谱AI（国内访问更稳定）

#### 3. 配额不足
```
ERROR: Insufficient quota
```
**解决方案**: 检查账户余额并充值

#### 4. 回退到Mock模式
如果遇到API问题，可以临时使用Mock模式：

```bash
# 使用mock配置
cp config/mock_llm_config.yaml config/llm_config.yaml
python main.py analyze deep src/utils/config.py
```

### 检查配置

验证配置是否正确：

```bash
# 检查当前加载的providers
python -c "
import sys
sys.path.insert(0, 'src')
from llm.config import LLMConfigManager
config = LLMConfigManager()
print('可用providers:', config.list_providers())
"
```

## 📝 最佳实践

1. **使用环境变量**: 避免将API密钥硬编码在代码中
2. **选择合适的模型**:
   - 智谱GLM-4.5: 性价比高，中文优秀
   - OpenAI GPT-4: 功能强大，英文优秀
   - Anthropic Claude: 推理能力强，安全性高
3. **合理设置参数**:
   - 温度0.1-0.3适合代码分析
   - 温度0.5-0.7适合创意建议
4. **控制文件大小**: 大文件会被截断，建议先分析小文件
5. **使用交互模式**: 多轮对话能获得更深入的分析

## 🎉 开始使用

配置完成后，您就可以开始使用深度分析功能了：

```bash
# 1. 设置API密钥
export ZHIPU_API_KEY="your-api-key"

# 2. 分析您的代码
python main.py analyze deep src/your_code.py

# 3. 与AI对话深入分析
# 在交互模式中提出具体问题
```

祝您使用愉快！🚀