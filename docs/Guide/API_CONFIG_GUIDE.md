# 🔑 LLM API配置指南

本指南将帮助您配置真实的LLM API来使用AIDefectDetector的深度分析、修复分析和工作流修复功能。

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
│ llm_config.yaml │ user_config.yaml │ 环境变量 │ configure_llm.py │
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
  model: "glm-4.5-air"       # 推荐模型
  api_key: "${ZHIPU_API_KEY}"
  api_base: "https://open.bigmodel.cn/api/paas/v4/"
  max_tokens: 4000
  temperature: 0.3
  timeout: 60
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

## 🚀 快速配置方法

### 方法1: 使用统一配置脚本 (最简单) ⭐

```bash
# 交互式配置向导
python3 scripts/configure_llm.py

# 快速配置模式
python3 scripts/configure_llm.py --quick

# 直接配置指定提供商
python3 scripts/configure_llm.py --provider zhipu
python3 scripts/configure_llm.py --provider openai
python3 scripts/configure_llm.py --provider anthropic
```

**配置脚本功能特点:**
- 🎯 交互式向导，一步步引导配置
- 📋 支持所有主流LLM提供商
- 🔧 自动更新配置文件
- ✅ 配置验证和连接测试
- 🎯 支持环境变量和配置文件两种方式
- 💡 智能故障诊断和建议

### 方法2: 环境变量配置 (推荐开发者)

```bash
# 智谱AI (推荐国内用户)
export ZHIPU_API_KEY="your-zhipu-api-key-here"

# OpenAI
export OPENAI_API_KEY="your-openai-api-key-here"
export OPENAI_BASE_URL="https://api.openai.com/v1"

# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"

# 立即使用
python3 main.py analyze deep ./src
```

### 方法3: 手动编辑配置文件

编辑 `config/llm_config.yaml`：

```yaml
providers:
  zhipu:
    provider: "zhipu"
    model: "glm-4.5-air"
    api_key: "your-actual-api-key"  # 或 "${ZHIPU_API_KEY}"
    api_base: "https://open.bigmodel.cn/api/paas/v4/"
    max_tokens: 4000
    temperature: 0.3
    timeout: 60
    max_retries: 3
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

## 🛠️ 配置验证和测试

### 使用配置脚本验证

```bash
# 查看当前配置状态
python3 scripts/configure_llm.py --status

# 运行配置诊断
python3 scripts/configure_llm.py --diagnose

# 测试指定提供商连接
python3 scripts/configure_llm.py --test zhipu
python3 scripts/configure_llm.py --test openai
python3 scripts/configure_llm.py --test anthropic
```

### 手动验证配置

```bash
# 检查环境变量是否设置
echo $ZHIPU_API_KEY
echo $OPENAI_API_KEY
echo $ANTHROPIC_API_KEY

# 测试深度分析功能
python3 main.py analyze deep ./src/utils/config.py --verbose

# 测试修复分析功能
python3 main.py analyze fix ./src/utils/config.py --verbose

# 测试工作流功能
python3 main.py analyze workflow ./src/utils/config.py --dry-run
```

## 🔧 高级配置选项

### 多提供商配置

配置文件支持同时配置多个提供商：

```yaml
# config/llm_config.yaml
providers:
  zhipu:
    provider: "zhipu"
    model: "glm-4.5-air"
    api_key: "${ZHIPU_API_KEY}"
    api_base: "https://open.bigmodel.cn/api/paas/v4/"
    max_tokens: 4000
    temperature: 0.3
    timeout: 60
    max_retries: 3

  openai:
    provider: "openai"
    model: "gpt-4-turbo"
    api_key: "${OPENAI_API_KEY}"
    api_base: "${OPENAI_BASE_URL:https://api.openai.com/v1}"
    max_tokens: 4000
    temperature: 0.3
    timeout: 30
    max_retries: 3

  mock:
    provider: "mock"
    model: "mock-model"
    api_key: "mock-api-key"
    api_base: "https://mock.api.com"
    max_tokens: 4000
    temperature: 0.7
    timeout: 30
```

### 用户配置文件

编辑 `~/.aidefect/config.yaml` 设置默认提供商：

```yaml
llm:
  default_provider: "zhipu"  # 设置默认使用的提供商
  fallback_providers: ["mock"]  # 备用提供商

  # 提供商特定配置可以覆盖全局配置
  zhipu:
    temperature: 0.2  # 更保守的参数
    max_tokens: 6000   # 更大的输出长度
```

### 模型参数优化

#### 不同场景的推荐参数

**代码审查 (严格模式)**
```yaml
code_review:
  temperature: 0.1      # 低温度，更确定性的输出
  max_tokens: 2000      # 适中的输出长度
  model: "glm-4.5"      # 使用强模型
```

**创意改进 (创意模式)**
```yaml
creative_improvement:
  temperature: 0.8      # 高温度，更有创意
  max_tokens: 4000      # 较长的输出
  model: "claude-3-sonnet-20240229"  # 使用创意模型
```

**安全分析 (保守模式)**
```yaml
security_analysis:
  temperature: 0.2      # 低温度，确保准确性
  max_tokens: 6000      # 详细的安全分析
  model: "gpt-4"        # 使用最强模型
```

## 🛡️ 安全最佳实践

### API密钥安全

1. **永不提交API密钥到版本控制:**
```bash
# 确保 .env 文件在 .gitignore 中
echo ".env" >> .gitignore
echo "~/.aidefect/.env" >> .gitignore
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
chmod 600 ~/.aidefect/config.yaml
chmod 600 config/llm_config.yaml
chmod 600 ~/.aidefect/.env
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
# 智谱AI：通常以数字开头
# OpenAI：通常以 "sk-" 开头
# Anthropic：通常以 "sk-ant-" 开头

# 重新设置API密钥
export ZHIPU_API_KEY="correct-api-key"

# 使用配置脚本重新配置
python3 scripts/configure_llm.py --provider zhipu
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
  -d '{"model":"glm-4.5-air","messages":[{"role":"user","content":"Hello"}],"max_tokens":10}'
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
import yaml
with open('config/llm_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    zhipu_config = config['providers'].get('zhipu', {})
    print(f'当前模型: {zhipu_config.get(\"model\", \"未配置\")}')
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
ls -la config/llm_config.yaml
ls -la ~/.aidefect/config.yaml

# 验证配置文件语法
python3 -c "import yaml; yaml.safe_load(open('config/llm_config.yaml'))"

# 重新生成配置文件
python3 scripts/configure_llm.py --provider zhipu
```

### 配置诊断工具

**运行完整诊断:**
```bash
python3 scripts/configure_llm.py --diagnose
```

**检查配置加载状态:**
```bash
python3 scripts/configure_llm.py --status
```

**测试API连接:**
```bash
python3 scripts/configure_llm.py --test zhipu
```

## 📝 配置示例模板

### 基础开发配置

```yaml
# config/llm_config.yaml - 基础配置
providers:
  mock:
    provider: "mock"
    model: "mock-model"
    api_key: "mock-api-key"
    api_base: "https://mock.api.com"
    max_tokens: 2000
    temperature: 0.7
    timeout: 30
```

### 生产环境配置

```yaml
# config/llm_config.yaml - 生产配置
providers:
  zhipu:
    provider: "zhipu"
    model: "glm-4.5-air"
    api_key: "${ZHIPU_API_KEY}"
    api_base: "https://open.bigmodel.cn/api/paas/v4/"
    max_tokens: 8000  # 生产环境增加token限制
    temperature: 0.2  # 生产环境降低创造性
    timeout: 60       # 生产环境增加超时时间
    max_retries: 5    # 生产环境增加重试次数

  # 生产回退配置
  openai:
    provider: "openai"
    model: "gpt-4-turbo"
    api_key: "${OPENAI_API_KEY}"
    api_base: "${OPENAI_BASE_URL:https://api.openai.com/v1}"
    max_tokens: 8000
    temperature: 0.2
    timeout: 60
    max_retries: 5

  mock:
    provider: "mock"
    model: "mock-model"
    api_key: "mock-api-key"
    api_base: "https://mock.api.com"
    max_tokens: 4000
    temperature: 0.7
    timeout: 30
```

### 高级配置示例

```yaml
# config/llm_config.yaml - 高级配置
providers:
  zhipu:
    provider: "zhipu"
    model: "glm-4.5-air"
    api_key: "${ZHIPU_API_KEY}"
    api_base: "https://open.bigmodel.cn/api/paas/v4/"

    # 基础参数
    max_tokens: 4000
    temperature: 0.3
    timeout: 60
    max_retries: 3

    # 高级参数
    top_p: 1.0
    frequency_penalty: 0.0
    presence_penalty: 0.0

    # 流式响应配置
    stream: true
    stream_timeout: 30

    # 并发控制
    max_concurrent_requests: 5
    request_rate_limit: 60  # 每分钟请求数

    # 缓存配置
    enable_cache: true
    cache_ttl: 3600  # 缓存1小时

    # 重试策略
    retry_strategy: "exponential_backoff"
    initial_retry_delay: 1.0
    max_retry_delay: 60.0
```

## 🎯 使用模式与配置建议

### 静态分析模式
- **无需API配置**
- **推荐工具配置**: `ast, pylint, flake8, bandit`
- **输出格式**: `json, table, markdown`

### 深度分析模式
- **需要API配置**
- **推荐模型**: `glm-4.5-air` (智谱) 或 `gpt-4-turbo` (OpenAI)
- **推荐参数**: `temperature: 0.3, max_tokens: 4000`
- **适合场景**: 代码重构建议、架构分析

### 修复分析模式
- **需要API配置**
- **推荐模型**: `glm-4.5` (智谱) 或 `gpt-4` (OpenAI)
- **推荐参数**: `temperature: 0.2, max_tokens: 6000`
- **适合场景**: 安全漏洞修复、性能优化

### 工作流修复模式 ⭐
- **需要API配置**
- **推荐模型**: `glm-4.5` (智谱) 或 `gpt-4` (OpenAI)
- **推荐参数**: `temperature: 0.2, max_tokens: 6000`
- **适合场景**: 复杂修复项目、完整闭环修复

## 🚀 快速开始

现在您已经了解了完整的API配置流程，选择最适合您的配置方式开始使用：

### 🚀 最快方式 - 快速配置向导

```bash
# 1. 运行快速配置向导
python3 scripts/configure_llm.py --quick

# 2. 按提示选择提供商和输入API密钥

# 3. 测试配置
python3 scripts/configure_llm.py --test zhipu

# 4. 开始使用
python3 main.py analyze workflow ./src
```

### ⚡ 推荐方式 - 智谱AI配置

```bash
# 1. 配置智谱AI（推荐国内用户）
python3 scripts/configure_llm.py --provider zhipu

# 2. 输入您的智谱AI API密钥

# 3. 开始深度分析
python3 main.py analyze deep ./src --verbose

# 4. 体验工作流模式
python3 main.py analyze workflow ./src --dry-run
```

### 🔧 手动配置方式

```bash
# 1. 设置环境变量
export ZHIPU_API_KEY="your-api-key"

# 2. 立即使用
python3 main.py analyze deep ./src

# 3. 测试工作流
python3 main.py analyze workflow ./src
```

## 📞 获取帮助

如果遇到配置问题：

1. **运行诊断工具**: `python3 scripts/configure_llm.py --diagnose`
2. **查看配置状态**: `python3 scripts/configure_llm.py --status`
3. **测试连接**: `python3 scripts/configure_llm.py --test [provider]`
4. **重新配置**: `python3 scripts/configure_llm.py --provider [provider]`

祝您使用愉快！🚀 如有问题，请查看快速开始指南或使用配置诊断工具。