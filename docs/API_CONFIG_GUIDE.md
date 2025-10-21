# API配置指南 - 深度分析功能

本指南将帮助您配置真实的LLM API来使用深度分析功能。

## 📋 项目架构概览

本项目采用**分层架构设计**的LLM配置系统：

```
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                 │
├─────────────────────────────────────────────────────────────┤
│  LLMClient (统一客户端)  │  LLMConfigManager (配置管理器)      │
├─────────────────────────────────────────────────────────────┤
│                  抽象层 (Abstraction Layer)                  │
├─────────────────────────────────────────────────────────────┤
│     LLMProvider (抽象基类)    │    LLMConfig (数据模型)        │
├─────────────────────────────────────────────────────────────┤
│                  实现层 (Implementation Layer)                │
├─────────────────────────────────────────────────────────────┤
│ OpenAI │ Anthropic │ ZhipuAI │ Mock │ HTTPClient │ Exception  │
├─────────────────────────────────────────────────────────────┤
│                  配置层 (Configuration Layer)                │
├─────────────────────────────────────────────────────────────┤
│ default.yaml │ user_config.yaml │ llm_config.yaml │ 环境变量   │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 LLM提供商选择指南

项目支持以下LLM提供商，各有特色：

### 🇨🇳 智谱AI (强烈推荐国内用户)

**优势:**
- ✅ 国内访问稳定，无网络限制
- ✅ 支持中文优化，理解能力强
- ✅ 性价比高，新用户有免费额度
- ✅ 支持函数调用和流式响应
- ✅ 支持视觉模型 (glm-4v)

**适用场景:**
- 国内生产环境部署
- 中文代码分析
- 成本敏感的项目
- 需要稳定服务

**配置示例:**
```yaml
zhipu:
  provider: "zhipu"
  model: "glm-4.5"           # 推荐模型
  api_key: "${ZHIPU_API_KEY}"
  api_base: "https://open.bigmodel.cn/api/paas/v4/"
  max_tokens: 4000
  temperature: 0.3
  timeout: 30
  max_retries: 3
```

### 🌐 OpenAI (功能最强)

**优势:**
- ✅ 模型能力最强，生态最完善
- ✅ 支持最新的GPT-4 Turbo
- ✅ 函数调用功能强大
- ✅ 社区支持丰富

**限制:**
- ⚠️ 需要科学上网，国内访问不稳定
- ⚠️ 成本相对较高

**配置示例:**
```yaml
openai:
  provider: "openai"
  model: "gpt-4-turbo"        # 性价比高
  api_key: "${OPENAI_API_KEY}"
  api_base: "${OPENAI_BASE_URL:https://api.openai.com/v1}"
  max_tokens: 4000
  temperature: 0.3
  timeout: 30
  max_retries: 3
  # 代理配置示例
  # api_base: "https://your-proxy.com/v1"
```

### 🤖 Anthropic Claude (推理能力优秀)

**优势:**
- ✅ 长文本处理能力最强
- ✅ 推理能力和安全性优秀
- ✅ Claude-3系列模型表现优异
- ✅ 代码分析能力强

**限制:**
- ⚠️ 需要科学上网
- ⚠️ 成本较高

**配置示例:**
```yaml
anthropic:
  provider: "anthropic"
  model: "claude-3-sonnet-20240229"
  api_key: "${ANTHROPIC_API_KEY}"
  api_base: "${ANTHROPIC_BASE_URL:https://api.anthropic.com}"
  max_tokens: 4000
  temperature: 0.3
  timeout: 30
  max_retries: 3
```

### 🧪 Mock Provider (测试开发)

**用途:**
- ✅ 测试和开发环境
- ✅ 演示和原型验证
- ✅ 成本控制
- ✅ 离线开发

**配置示例:**
```yaml
mock:
  provider: "mock"
  model: "mock-model"
  api_key: "mock-api-key"
  api_base: "https://mock.api.com"
  max_tokens: 4000
  temperature: 0.7
  timeout: 30
```

## 🔑 API密钥获取指南

### 智谱AI (推荐)

#### 步骤1: 注册账号
1. 访问 [智谱AI开放平台](https://open.bigmodel.cn/)
2. 点击"注册"按钮
3. 使用手机号或邮箱完成注册
4. 完成实名认证（需要身份证）

#### 步骤2: 获取API密钥
1. 登录后进入"控制台"
2. 在左侧菜单选择"API密钥"
3. 点击"创建API密钥"
4. 设置密钥名称（如：AIDefectDetector）
5. 复制生成的API密钥
6. 保存密钥到安全位置

#### 步骤3: 充值余额
1. 在控制台选择"余额管理"
2. 选择充值套餐
3. 新用户通常有免费试用额度
4. 根据需要选择合适的充值方案

### OpenAI

#### 步骤1: 注册账号
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 使用邮箱或Google账号注册
3. 验证邮箱地址

#### 步骤2: 获取API密钥
1. 登录后进入 "API Keys" 页面
2. 点击 "Create new secret key"
3. 设置密钥名称和权限
4. 复制并保存API密钥（只显示一次）

#### 步骤3: 绑定支付
1. 在 "Settings" → "Billing" 中
2. 添加支付方式（信用卡或借记卡）
3. 设置使用限额

### Anthropic Claude

#### 步骤1: 注册账号
1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 使用邮箱注册账号
3. 验证邮箱地址

#### 步骤2: 获取API密钥
1. 登录后进入 "API Keys" 页面
2. 点击 "Create Key"
3. 设置密钥名称和权限
4. 复制并保存API密钥

#### 步骤3: 设置计费
1. 在 "Usage" 页面查看用量
2. 设置预算提醒
3. 根据需要选择计费方案

## 🛠️ 配置方法详解

### 方法1: 环境变量 (推荐)

**优势:**
- ✅ 安全性好，API密钥不存储在文件中
- ✅ 易于在不同环境间切换
- ✅ 支持CI/CD自动化部署

**配置步骤:**

1. **临时配置 (当前会话有效):**
```bash
# 智谱AI
export ZHIPU_API_KEY="your-zhipu-api-key-here"

# OpenAI (如果使用)
export OPENAI_API_KEY="your-openai-api-key-here"
export OPENAI_BASE_URL="https://api.openai.com/v1"

# Anthropic (如果使用)
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

2. **永久配置 (推荐):**
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export ZHIPU_API_KEY="your-zhipu-api-key-here"' >> ~/.bashrc

# 立即生效
source ~/.bashrc

# 或者创建 .env 文件
echo "ZHIPU_API_KEY=your-zhipu-api-key-here" > .env
echo ".env" >> .gitignore  # 不要提交到版本控制
```

### 方法2: 配置文件

**项目配置文件结构:**
```
config/
├── default.yaml              # 默认配置
├── user_config.example.yaml  # 用户配置示例
├── user_config.yaml          # 用户实际配置
└── llm_config.yaml          # LLM专用配置
```

**1. 复制用户配置示例:**
```bash
cp config/user_config.example.yaml config/user_config.yaml
```

**2. 编辑用户配置文件:**
```yaml
# config/user_config.yaml

llm:
  # 选择默认provider
  default_provider: "zhipu"

  # 智谱AI配置
  zhipu:
    api_key: "${ZHIPU_API_KEY}"
    model: "glm-4.5"
    base_url: "https://open.bigmodel.cn/api/paas/v4/"
    max_tokens: 4000
    temperature: 0.3
    timeout: 30

  # OpenAI配置 (可选)
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4"
    base_url: "${OPENAI_BASE_URL:https://api.openai.com/v1}"
    max_tokens: 4000
    temperature: 0.3
    timeout: 30

# 深度分析配置
deep_analysis:
  default_model: "glm-4.5"
  max_file_size: 100000      # 100KB
  temperature: 0.3
  max_tokens: 4000
```

### 方法3: 使用配置脚本 (最简单)

项目提供了自动配置脚本：

```bash
# 智谱AI专用配置脚本
./set_zhipu_key.sh

# 完整配置向导
./setup_api.sh
```

## 🎯 配置参数详解

### 基础参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `provider` | str | "zhipu" | LLM提供商 |
| `model` | str | "glm-4.5" | 模型名称 |
| `api_key` | str | - | API密钥 |
| `api_base` | str | - | API基础URL |

### 性能参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `timeout` | int | 30 | 请求超时时间(秒) |
| `max_retries` | int | 3 | 最大重试次数 |
| `retry_delay` | float | 1.0 | 重试延迟(秒) |
| `max_tokens` | int | 4000 | 最大生成token数 |

### 生成参数

| 参数 | 类型 | 默认值 | 范围 | 说明 |
|------|------|--------|------|------|
| `temperature` | float | 0.3 | 0.0-2.0 | 创造性参数 |
| `top_p` | float | 1.0 | 0.0-1.0 | 核采样参数 |
| `frequency_penalty` | float | 0.0 | -2.0-2.0 | 频率惩罚 |
| `presence_penalty` | float | 0.0 | -2.0-2.0 | 存在惩罚 |

### 智谱AI特定参数

```yaml
zhipu:
  provider: "zhipu"
  model: "glm-4.5"           # 或 glm-4.5-air, glm-4, glm-4-airx, glm-4-flash
  api_key: "${ZHIPU_API_KEY}"
  api_base: "https://open.bigmodel.cn/api/paas/v4/"
  max_tokens: 4000
  temperature: 0.3
  timeout: 30
  max_retries: 3

  # 智谱AI特有参数
  user_id: "optional_user_id"  # 用户标识
```

### OpenAI特定参数

```yaml
openai:
  provider: "openai"
  model: "gpt-4-turbo"      # 或 gpt-4, gpt-3.5-turbo
  api_key: "${OPENAI_API_KEY}"
  api_base: "${OPENAI_BASE_URL:https://api.openai.com/v1}"
  max_tokens: 4000
  temperature: 0.3
  timeout: 30
  max_retries: 3

  # OpenAI特有参数
  organization: "org-your-org-id"  # 组织ID
  deployment_id: "deploy-id"  # 部署ID（私有模型）
```

### Anthropic特定参数

```yaml
anthropic:
  provider: "anthropic"
  model: "claude-3-sonnet-20240229"  # 或 claude-3-opus-20240229
  api_key: "${ANTHROPIC_API_KEY}"
  api_base: "${ANTHROPIC_BASE_URL:https://api.anthropic.com}"
  max_tokens: 4000
  temperature: 0.3
  timeout: 30
  max_retries: 3

  # Anthropic特有参数
  anthropic_version: "2023-06-01"
  anthropic-dangerous-directive: "block"
```

## 🔧 高级配置

### 自定义配置文件

**1. 创建生产环境配置:**
```yaml
# config/production.yaml
llm:
  default_provider: "zhipu"

  zhipu:
    api_key: "${ZHIPU_API_KEY}"
    model: "glm-4.5"
    max_tokens: 8000  # 生产环境增加token限制
    temperature: 0.2  # 生产环境降低创造性

  openai:
    api_key: "${OPENAI_API_KEY}"
    model: "gpt-4-turbo"
    max_tokens: 8000
    temperature: 0.2

  # 开发回退
  mock:
    provider: "mock"
    model: "mock-model"
    max_tokens: 4000
    temperature: 0.7
```

**2. 创建开发环境配置:**
```yaml
# config/development.yaml
llm:
  default_provider: "mock"  # 开发环境使用mock

  mock:
    provider: "mock"
    model: "mock-model"
    max_tokens: 2000
    temperature: 0.7
    timeout: 10  # 开发环境减少超时时间
```

### 环境特定配置

**开发环境 (.env.development):**
```env
# 开发环境配置
LLM_DEFAULT_PROVIDER=mock
ZHIPU_API_KEY=dev-api-key
OPENAI_API_KEY=dev-openai-key
```

**测试环境 (.env.test):**
```env
# 测试环境配置
LLM_DEFAULT_PROVIDER=mock
# 测试使用Mock，避免API调用成本
```

**生产环境 (.env.production):**
```env
# 生产环境配置
LLM_DEFAULT_PROVIDER=zhipu
ZHIPU_API_KEY=prod-api-key
OPENAI_API_KEY=prod-openai-key
ANTHROPIC_API_KEY=prod-anthropic-key
```

### 条件配置

**根据文件类型选择模型:**
```python
# 伪代码示例
def choose_provider_for_file(file_path: str):
    if file_path.endswith('.py'):
        return "zhipu"  # Python代码用智谱AI
    elif file_path.endswith('.js'):
        return "openai"  # JavaScript用OpenAI
    elif file_path.endswith(('.md', '.rst')):
        return "anthropic"  # 文档用Claude
    else:
        return "zhipu"  # 默认
```

**根据分析类型选择参数:**
```yaml
# 不同分析类型的参数配置
analysis_types:
  security:
    temperature: 0.1      # 安全分析用低温度
    max_tokens: 6000      # 需要详细输出
    model: "glm-4.5"

  performance:
    temperature: 0.2      # 性能分析用中低温度
    max_tokens: 3000      # 关注重点
    model: "gpt-4-turbo"

  creativity:
    temperature: 0.8      # 创意建议用高温度
    max_tokens: 4000
    model: "claude-3-sonnet"

  debugging:
    temperature: 0.1      # 调试用低温度，输出精确
    max_tokens: 2000
    model: "glm-4.5"
```

## 🚀 使用方法

### 基本用法

```bash
# 1. 设置API密钥
export ZHIPU_API_KEY="your-api-key"

# 2. 分析单个文件
python3 main.py analyze deep src/utils/config.py

# 3. 详细输出
python3 main.py analyze deep src/utils/config.py --verbose

# 4. 分析整个目录
python3 main.py analyze deep src/ --verbose
```

### 交互式对话

**启动深度分析后会进入AI对话模式:**

```bash
🤖 AI分析助手> help
🔍 AI正在思考...
🤖 AI: 我是AI代码分析助手，可以帮助您进行深度代码分析...
支持的分析类型：comprehensive, security, performance, architecture, code_review, refactoring
可用命令：help, analyze <文件>, summary, export <文件>, exit

🤖 AI分析助手> analyze src/utils/config.py
🔍 AI正在思考...
🤖 AI: [详细的代码分析结果，包括：]
- 代码结构分析
- 潜在问题识别
- 改进建议
- 安全评估
- 性能优化建议...

🤖 AI分析助手> 这个函数有什么安全问题？
🔍 AI正在思考...
🤖 AI: [针对函数的安全问题详细分析...]
```

### 支持的交互命令

| 命令 | 功能 | 示例 |
|------|------|------|
| `help` | 显示帮助信息 | `help` |
| `analyze <文件>` | 分析指定文件 | `analyze src/main.py` |
| `analyze <目录>` | 分析整个目录 | `analyze src/` |
| `summary` | 显示分析摘要 | `summary` |
| `export <文件>` | 导出对话历史 | `export analysis.json` |
| `history` | 显示对话历史 | `history` |
| `clear` | 清空对话历史 | `clear` |
| `exit` / `quit` | 退出分析 | `exit` |

### 批量分析

```bash
# 分析多个文件
python3 main.py analyze deep file1.py file2.py file3.py

# 分析特定类型文件
python3 main.py analyze deep src/**/*.py

# 使用通配符
python3 main.py analyze deep "src/*/*.py"
```

## 🛡️ 安全最佳实践

### API密钥安全

1. **永不提交API密钥到版本控制:**
```bash
# 确保 .env 文件在 .gitignore 中
echo ".env" >> .gitignore
echo "config/user_config.yaml" >> .gitignore
```

2. **使用环境变量:**
```bash
# 推荐：使用环境变量
export ZHIPU_API_KEY="your-key"

# 避免：硬编码在代码中
# ❌ 错误做法
api_key = "sk-xxxxxxxxxxxxxxxx"  # 不要这样做
```

3. **定期轮换API密钥:**
```bash
# 定期更换API密钥（如每月）
# 在控制台中禁用旧密钥，创建新密钥
```

### 配置文件安全

1. **文件权限设置:**
```bash
# 设置配置文件权限
chmod 600 config/user_config.yaml
chmod 600 config/llm_config.yaml
```

2. **敏感信息过滤:**
```yaml
# ✅ 正确：使用环境变量
api_key: "${ZHIPU_API_KEY}"

# ❌ 错误：直接写入密钥
api_key: "sk-xxxxxxxxxxxxxxxx"
```

### 网络安全

1. **使用HTTPS:**
```yaml
# ✅ 正确：使用HTTPS
api_base: "https://api.openai.com/v1"

# ❌ 错误：使用HTTP（不安全）
api_base: "http://api.openai.com/v1"
```

2. **代理配置（如需要）:**
```yaml
# 配置代理服务器
api_base: "https://your-proxy.com/v1"
# 或设置环境变量
export HTTPS_PROXY="http://your-proxy:8080"
export HTTP_PROXY="http://your-proxy:8080"
```

## 🔧 故障排除

### 常见问题及解决方案

#### 1. API密钥相关错误

**错误信息:**
```
❌ Authentication failed: Invalid API key
❌ API密钥认证失败
```

**解决方案:**
```bash
# 检查API密钥是否正确设置
echo $ZHIPU_API_KEY

# 验证API密钥格式
# 智谱AI：通常以 "sk-" 开头
# OpenAI：通常以 "sk-" 开头
# Anthropic：通常以 "sk-ant-" 开头

# 重新设置API密钥
export ZHIPU_API_KEY="correct-api-key"
```

#### 2. 网络连接问题

**错误信息:**
```
❌ Connection timeout
❌ 网络连接超时
❌ 无法连接到API服务器
```

**解决方案:**
```bash
# 检查网络连接
ping open.bigmodel.cn

# 检查代理设置（如果使用）
echo $HTTPS_PROXY
echo $HTTP_PROXY

# 测试API连接
curl -X POST "https://open.bigmodel.cn/api/paas/v4/chat/completions" \
  -H "Authorization: Bearer $ZHIPU_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"glm-4.5","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
```

#### 3. 配额不足问题

**错误信息:**
```
❌ Insufficient quota
❌ 账户余额不足
❌ API配额已用完
```

**解决方案:**
```bash
# 检查账户余额
# 登录智谱AI控制台查看余额

# 充值账户
# 在控制台选择合适的充值方案

# 设置使用限制
export LLM_MAX_REQUESTS_PER_MIN=60  # 限制请求频率
```

#### 4. 模型不支持问题

**错误信息:**
```
❌ Model not found: invalid-model
❌ 模型不存在
❌ 不支持的模型
```

**解决方案:**
```bash
# 查看支持的模型列表
智谱AI: glm-4.5, glm-4.5-air, glm-4, glm-4-airx, glm-4-flash, glm-4v
OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
Anthropic: claude-3-opus-20240229, claude-3-sonnet-20240229

# 检查当前配置的模型
python3 -c "
import sys; sys.path.insert(0, 'src')
from llm.config import LLMConfigManager
config = LLMConfigManager()
zhipu = config.get_config('zhipu')
print(f'当前模型: {zhipu.model if zhipu else \"未配置\"}')
"
```

#### 5. 配置文件问题

**错误信息:**
```
❌ Configuration file not found
❌ 配置文件解析错误
❌ 配置验证失败
```

**解决方案:**
```bash
# 检查配置文件是否存在
ls -la config/

# 验证配置文件语法
python3 -c "import yaml; yaml.safe_load(open('config/llm_config.yaml'))"

# 重新生成配置文件
cp config/user_config.example.yaml config/user_config.yaml
```

### 配置诊断工具

**1. 检查配置加载状态:**
```bash
python3 -c "
import sys; sys.path.insert(0, 'src')
from llm.config import LLMConfigManager
config = LLMConfigManager()
print('可用providers:', config.list_providers())
for provider in config.list_providers():
    cfg = config.get_config(provider)
    if cfg:
        print(f'{provider}: ✅ 配置正常')
        print(f'  - 模型: {cfg.model}')
        print(f'  - API Base: {cfg.api_base}')
    else:
        print(f'{provider}: ❌ 配置失败')
"
```

**2. 测试API连接:**
```bash
# 使用配置脚本测试
./setup_api.sh
# 选择选项5：测试API连接

# 或手动测试
echo "测试连接" | python3 main.py analyze deep src/utils/config.py --verbose
```

**3. 检查环境变量:**
```bash
# 显示所有相关环境变量
env | grep -E "(ZHIPU|OPENAI|ANTHROPIC|LLM)_API_KEY"

# 检查配置文件
python3 -c "
import os
vars = ['ZHIPU_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
for var in vars:
    value = os.environ.get(var)
    if value:
        print(f'{var}: {"✅ 已设置" if len(value) > 10 else "❌ 可能未设置"}')
    else:
        print(f'{var}: ❌ 未设置')
"
```

## 📝 配置示例模板

### 基础开发配置

```yaml
# config/basic_setup.yaml
llm:
  default_provider: "mock"  # 开发时使用mock
  max_tokens: 2000
  temperature: 0.7

  mock:
    provider: "mock"
    model: "mock-model"
    max_tokens: 2000
    temperature: 0.7
```

### 生产环境配置

```yaml
# config/production_setup.yaml
llm:
  default_provider: "zhipu"  # 生产用智谱AI
  max_tokens: 8000
  temperature: 0.2

  zhipu:
    provider: "zhipu"
    model: "glm-4.5"
    api_key: "${ZHIPU_API_KEY}"
    api_base: "https://open.bigmodel.cn/api/paas/v4/"
    max_tokens: 8000
    temperature: 0.2
    timeout: 60
    max_retries: 5

  # 生产回退
  openai:
    provider: "openai"
    model: "gpt-4-turbo"
    api_key: "${OPENAI_API_KEY}"
    max_tokens: 8000
    temperature: 0.2
    timeout: 60
    max_retries: 5
```

### 高级配置

```yaml
# config/advanced_setup.yaml
llm:
  default_provider: "zhipu"
  fallback_providers: ["openai", "anthropic", "mock"]
  enable_fallback: true
  max_retry_attempts: 3

  # 不同场景的配置
  scenarios:
    code_review:
      temperature: 0.1
      max_tokens: 4000
      model: "glm-4.5"

    security_analysis:
      temperature: 0.2
      max_tokens: 6000
      model: "glm-4.5"

    creative_suggestions:
      temperature: 0.8
      max_tokens: 4000
      model: "claude-3-sonnet-20240229"

    debugging:
      temperature: 0.1
      max_tokens: 2000
      model: "glm-4.5"

  # 成本优化配置
  cost_optimization:
    use_cache: true
    cache_ttl: 3600  # 1小时
    prefer_cheaper: true
    max_tokens_per_request: 4000
```

## 🛠️ 配置工具和脚本

项目提供了多种配置工具，帮助您快速设置和管理API配置：

### 🚀 快速设置向导 (推荐新手)

```bash
python3 quick_setup.py
```

**功能特点:**
- 🎯 交互式向导，一步步引导配置
- 📋 多种配置方式选择
- 🔧 自动应用配置模板
- ✅ 配置验证和测试
- 🎯 立即运行示例分析

**适用场景:**
- 第一次使用的用户
- 需要快速配置和体验
- 不熟悉命令行的用户

### 🔧 配置管理工具

```bash
# 列出所有配置模板
python3 manage_config.py list

# 应用配置模板
python3 manage_config.py apply development

# 查看模板内容
python3 manage_config.py show production

# 验证当前配置
python3 manage_config.py validate

# 查看配置状态
python3 manage_config.py status

# 备份配置
python3 manage_config.py backup

# 恢复配置
python3 manage_config.py restore backup_name
```

**功能特点:**
- 📁 管理多种配置模板
- 💾 配置备份和恢复
- ✅ 配置验证和状态检查
- 🔄 快速切换不同环境配置

### 🔍 配置诊断工具

```bash
python3 diagnose_config.py
```

**功能特点:**
- 🔍 全面检查系统配置
- 🌐 测试API连接
- 📊 生成健康评分报告
- 🔧 自动修复可修复的问题
- 💡 提供改进建议

**检查项目:**
- Python环境和依赖
- 配置文件完整性
- API密钥状态
- LLM配置正确性
- 网络连接测试

### 📋 API配置向导

```bash
./setup_api.sh
```

**功能特点:**
- 🎯 交互式配置菜单
- 🔑 支持多个LLM提供商
- 🧪 API连接测试
- 🔬 深度分析功能测试

**菜单选项:**
1. 检查现有配置
2. 配置智谱AI (推荐)
3. 配置OpenAI
4. 配置Anthropic
5. 测试API连接
6. 运行深度分析测试
7. 运行完整系统诊断 🔥

### ⚡ 智谱AI快速配置

```bash
./set_zhipu_key.sh
```

**功能特点:**
- 🎯 专门针对智谱AI优化
- ⚡ 最简配置流程
- 💾 多种保存方式
- 🧪 自动配置验证

## 📁 配置模板系统

项目提供了预配置的模板，适应不同使用场景：

### 模板列表

| 模板名称 | 适用场景 | 特点 |
|----------|----------|------|
| `minimal` | 快速体验 | 最简配置，立即可用 |
| `development` | 开发测试 | Mock默认，节省成本 |
| `production` | 生产部署 | 高可用，性能优化 |
| `testing` | 自动化测试 | 确定性输出，无API调用 |

### 使用模板

```bash
# 查看可用模板
python3 manage_config.py list

# 应用开发环境模板
python3 manage_config.py apply development

# 应用最小化模板
python3 manage_config.py apply minimal
```

## 🎉 快速开始

现在您已经了解了完整的API配置流程，选择最适合您的配置方式开始使用：

### 🚀 最快方式 - 快速设置向导

```bash
# 1. 运行快速设置向导
python3 quick_setup.py

# 2. 按提示选择配置方式
# 3. 根据需要设置API密钥
# 4. 立即开始使用
```

### ⚡ 简单方式 - 智谱AI配置

```bash
# 1. 配置智谱AI（推荐国内用户）
./set_zhipu_key.sh

# 2. 按提示输入API密钥

# 3. 开始深度分析
python3 main.py analyze deep src/utils/config.py
```

### 🔧 手动配置方式

```bash
# 1. 设置环境变量
export ZHIPU_API_KEY="your-api-key"

# 2. 立即使用
python3 main.py analyze deep <文件路径>
```

### 📁 使用配置模板

```bash
# 1. 选择并应用模板
python3 manage_config.py apply minimal

# 2. 设置API密钥
export ZHIPU_API_KEY="your-api-key"

# 3. 验证配置
python3 diagnose_config.py

# 4. 开始使用
python3 main.py analyze deep <文件路径>
```

## 🔧 工具使用流程推荐

### 新用户推荐流程:

1. **快速体验**: `python3 quick_setup.py` → 选择Mock模式
2. **真实使用**: `./set_zhipu_key.sh` → 配置API密钥
3. **问题诊断**: `python3 diagnose_config.py` → 检查配置
4. **深入学习**: `cat API_CONFIG_GUIDE.md` → 阅读完整指南

### 开发者推荐流程:

1. **开发环境**: `python3 manage_config.py apply development`
2. **配置管理**: `python3 manage_config.py status`
3. **问题排查**: `python3 diagnose_config.py`
4. **生产部署**: `python3 manage_config.py apply production`

### 运维推荐流程:

1. **系统检查**: `python3 diagnose_config.py`
2. **配置备份**: `python3 manage_config.py backup`
3. **模板切换**: `python3 manage_config.py apply production`
4. **定期验证**: `python3 manage_config.py validate`

祝您使用愉快！🚀 如有问题，可以：

- 🔍 运行诊断: `python3 diagnose_config.py`
- 📖 查看指南: `cat API_CONFIG_GUIDE.md`
- 🛠️ 使用向导: `./setup_api.sh`
- 🚀 快速开始: `python3 quick_setup.py`

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