# Fix Agent Web 部署指南

## 项目概述

Fix Agent Web 是基于现有CLI项目的Web版本，完全保持了原有的AI代理协作逻辑和工具系统，通过现代化的Web界面提供更好的用户体验。

## 核心特性

### ✅ 已实现功能
- **AI代理协作**: 完整复用CLI的defect-analyzer、code-fixer、fix-validator三个子代理
- **实时通信**: WebSocket流式响应，保持CLI的实时交互体验
- **会话管理**: 多会话支持，独立的记忆系统和工作空间
- **文件上传**: 支持项目文件上传，AI可以引用和分析
- **记忆系统**: 复用CLI的长期记忆系统，支持跨会话学习
- **工具集成**: 完整集成所有CLI工具（代码分析、网络请求等）

### 🔄 技术架构
- **后端**: FastAPI + SQLAlchemy + WebSocket
- **前端**: React 18 + TypeScript + Tailwind CSS
- **AI系统**: DeepAgents + LangChain (直接复用CLI逻辑)
- **数据库**: PostgreSQL + Redis
- **部署**: Docker + Docker Compose

## 快速启动

### 1. 环境准备

确保系统已安装：
- Docker & Docker Compose
- Git

### 2. 配置环境变量

创建 `.env` 文件：
```bash
# AI模型配置
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
TAVILY_API_KEY=your_tavily_key_here

# 可选：自定义API端点
OPENAI_BASE_URL=https://api.openai.com/v1
ANTHROPIC_BASE_URL=https://api.anthropic.com

# 模型参数
MODEL_TEMPERATURE=0.3
MODEL_MAX_TOKENS=50000
```

### 3. 启动服务

```bash
# 克隆项目（如果需要）
git clone <repository-url>
cd Fix_agent/web_app

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 访问应用

- **前端界面**: http://localhost:3000
- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs

## 开发模式

### 后端开发
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 前端开发
```bash
cd frontend
npm install
npm start
```

## 核心组件说明

### AI系统复用
```python
# 直接复用CLI的核心逻辑
from ai_adapter import AIAdapter

# 创建会话时自动初始化AI代理
adapter = AIAdapter(session_id, workspace_path)

# 流式响应保持与CLI一致
async for chunk in adapter.stream_response(message, file_references):
    yield chunk
```

### WebSocket实时通信
- 保持与CLI相同的流式响应体验
- 支持工具调用状态实时更新
- 自动重连和错误处理

### 会话管理
- 每个Web会话对应独立的AI代理实例
- 隔离的工作空间和记忆系统
- 数据库持久化会话状态

## 功能演示

### 1. 代码缺陷分析
```
用户: 请分析这个Python文件的缺陷 @main.py
AI: [defect-analyzer子代理] 正在分析代码...
     发现3个潜在问题：
     1. 未处理的异常 (第15行)
     2. 资源泄漏风险 (第23行)
     3. 安全漏洞: SQL注入可能 (第42行)
```

### 2. 文件引用
- 上传项目文件或拖拽到界面
- 使用 `@文件名` 引用文件内容
- AI可以分析、修改和验证代码

### 3. 记忆系统
- AI会记住用户的偏好和项目上下文
- 支持手动编辑记忆文件
- 跨会话保持学习状态

## 部署配置

### 生产环境
```bash
# 使用生产配置启动
docker-compose --profile production up -d

# 配置Nginx反向代理
# SSL证书配置
# 性能优化设置
```

### 监控和日志
- 应用日志：`docker-compose logs -f backend`
- 健康检查：`curl http://localhost:8000/health`
- 数据库状态：连接PostgreSQL查看

## 故障排除

### 常见问题

1. **AI模型连接失败**
   - 检查API密钥配置
   - 验证网络连接
   - 查看后端日志

2. **WebSocket连接问题**
   - 检查防火墙设置
   - 验证端口8000可访问
   - 查看浏览器控制台错误

3. **文件上传失败**
   - 检查上传目录权限
   - 验证文件大小限制
   - 查看磁盘空间

### 日志查看
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务
docker-compose logs -f backend
docker-compose logs -f frontend

# 查看最近的错误
docker-compose logs --tail=50 backend | grep ERROR
```

## 扩展开发

### 添加新的AI工具
1. 在CLI项目中实现工具
2. 在 `backend/app/core/ai_adapter.py` 中注册
3. 前端添加相应的UI组件

### 自定义前端界面
1. 修改 `frontend/src/components/`
2. 更新样式主题
3. 添加新功能页面

### 数据库扩展
1. 修改 `backend/app/models/database.py`
2. 运行数据库迁移
3. 更新API接口

## 性能优化

### 后端优化
- 使用Redis缓存会话数据
- 数据库连接池配置
- 异步处理长时间任务

### 前端优化
- 代码分割和懒加载
- 虚拟滚动处理大量消息
- 图片和文件压缩

## 安全考虑

- API密钥安全存储
- 文件上传安全检查
- 用户认证和授权
- HTTPS通信加密
- 输入验证和清理

## 技术支持

- **GitHub Issues**: 报告bug和功能请求
- **文档**: 查看详细API文档
- **社区**: 加入讨论和交流

---

**注意**: 这个Web版本完全保持了CLI项目的所有功能逻辑，只是提供了更好的用户界面。所有的AI代理协作、工具系统、记忆管理都与CLI版本保持一致。