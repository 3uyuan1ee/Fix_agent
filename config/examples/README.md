# 配置模板说明

本目录包含了不同场景下的配置模板，帮助您快速设置适合的配置。

## 📁 模板文件说明

### 🔧 `development.yaml` - 开发环境
**适用场景:** 本地开发、功能测试、调试
**特点:**
- 默认使用Mock提供商，节省API成本
- 详细的DEBUG日志输出
- 内存缓存，快速重启
- 较小的文件大小限制
- 较短的超时时间

**使用方法:**
```bash
cp config/examples/development.yaml config/user_config.yaml
# 编辑配置文件，添加您的API密钥（如需真实API测试）
```

### 🚀 `production.yaml` - 生产环境
**适用场景:** 生产部署、正式服务
**特点:**
- 多provider回退机制，确保高可用性
- 智谱AI主用，OpenAI/Anthropic备用
- 较大的token限制和文件大小
- Redis缓存，支持分布式部署
- 性能监控和安全配置
- 结构化日志

**使用方法:**
```bash
cp config/examples/production.yaml config/user_config.yaml
# 必须配置所有相关的环境变量
```

### 🧪 `testing.yaml` - 测试环境
**适用场景:** 自动化测试、CI/CD
**特点:**
- 强制使用Mock，避免API调用
- 最小化日志输出
- 快速超时和重试
- 确定性输出，便于测试
- 临时文件和缓存

**使用方法:**
```bash
cp config/examples/testing.yaml config/user_config.yaml
# 用于pytest等测试场景
```

### ⚡ `minimal.yaml` - 最小化配置
**适用场景:** 快速体验、演示、最小部署
**特点:**
- 最简配置，易于理解
- 只配置必要的参数
- 快速启动和运行

**使用方法:**
```bash
cp config/examples/minimal.yaml config/user_config.yaml
# 只需设置一个API密钥即可使用
```

## 🎯 如何选择模板

| 场景 | 推荐模板 | 理由 |
|------|----------|------|
| 我刚开始学习 | `minimal.yaml` | 配置简单，快速上手 |
| 本地开发测试 | `development.yaml` | 节省成本，调试友好 |
| 准备正式部署 | `production.yaml` | 稳定可靠，功能完整 |
| 自动化测试 | `testing.yaml` | 避免API调用，结果稳定 |
| 演示和展示 | `minimal.yaml` 或 `development.yaml` | 启动快速，效果明显 |

## 🛠️ 使用步骤

1. **选择合适的模板**
   ```bash
   # 查看所有模板
   ls config/examples/

   # 查看模板内容
   cat config/examples/development.yaml
   ```

2. **复制到用户配置**
   ```bash
   cp config/examples/[模板名].yaml config/user_config.yaml
   ```

3. **编辑配置文件**
   ```bash
   vim config/user_config.yaml
   # 或使用其他编辑器
   ```

4. **设置环境变量**
   ```bash
   # 智谱AI
   export ZHIPU_API_KEY="your-api-key"

   # OpenAI (可选)
   export OPENAI_API_KEY="your-openai-key"

   # Anthropic (可选)
   export ANTHROPIC_API_KEY="your-anthropic-key"
   ```

5. **验证配置**
   ```bash
   # 运行配置诊断
   python3 diagnose_config.py

   # 或使用配置脚本
   ./setup_api.sh
   ```

## 🔧 自定义配置

您可以在模板基础上进行自定义：

### 修改默认Provider
```yaml
llm:
  default_provider: "openai"  # 改为OpenAI
```

### 调整模型参数
```yaml
deep_analysis:
  temperature: 0.7  # 增加创造性
  max_tokens: 6000  # 增加输出长度
```

### 添加专用配置
```yaml
# 为不同分析类型设置不同参数
analysis_types:
  creative:
    temperature: 0.8
    model: "claude-3-sonnet"
  technical:
    temperature: 0.1
    model: "glm-4.5"
```

## ⚠️ 注意事项

1. **API密钥安全:**
   - 不要将API密钥提交到版本控制
   - 使用环境变量存储敏感信息
   - 生产环境建议使用密钥管理服务

2. **配置验证:**
   - 修改配置后务必进行验证
   - 使用诊断工具检查配置正确性
   - 测试网络连接和API调用

3. **性能优化:**
   - 根据硬件调整并发数和缓存大小
   - 监控API使用量和成本
   - 定期清理日志和缓存

## 🆘 获取帮助

如果配置遇到问题：

1. **运行诊断工具:**
   ```bash
   python3 diagnose_config.py
   ```

2. **查看详细文档:**
   ```bash
   cat API_CONFIG_GUIDE.md
   ```

3. **使用配置向导:**
   ```bash
   ./setup_api.sh
   ```

4. **查看示例用法:**
   ```bash
   cat QUICK_START.md
   ```