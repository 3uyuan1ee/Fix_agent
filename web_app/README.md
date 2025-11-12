# Fix Agent Web Application

基于现有CLI项目的Web版本，保持所有对话逻辑和AI代理功能。

## 功能特性

- 🤖 **AI代理协作**: 缺陷分析、代码修复、验证三个专业子代理
- 💬 **实时对话**: WebSocket流式响应，保持CLI的交互体验
- 📁 **文件管理**: 支持文件上传、项目浏览、代码编辑
- 🔍 **代码分析**: 集成所有静态分析工具链
- 📊 **可视化结果**: 缺陷报告、修复建议的图形化展示
- 🎯 **项目管理**: 多项目支持，记忆系统持久化

## 技术栈

### 后端
- **FastAPI**: 现代Python Web框架
- **WebSocket**: 实时双向通信
- **DeepAgents**: AI代理系统（复用现有逻辑）
- **SQLAlchemy**: 数据库ORM
- **Redis**: 缓存和会话管理

### 前端
- **React 18**: 用户界面框架
- **TypeScript**: 类型安全
- **Tailwind CSS**: 现代化样式
- **Socket.io**: 实时通信客户端
- **Monaco Editor**: VS Code编辑器集成
- **React Query**: 数据获取和缓存

## 项目结构

```
web_app/
├── backend/                 # FastAPI后端
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑（复用CLI组件）
│   │   └── websocket/      # WebSocket处理
│   ├── requirements.txt
│   └── main.py
├── frontend/               # React前端
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── hooks/          # 自定义Hook
│   │   ├── services/       # API服务
│   │   ├── types/          # TypeScript类型
│   │   └── utils/          # 工具函数
│   ├── package.json
│   └── tsconfig.json
└── docker-compose.yml      # 容器化部署
```

## 核心设计

### 1. 架构复用
- 直接导入现有的 `agents`, `tools`, `config` 模块
- 保持相同的AI代理协作逻辑
- 复用所有工具系统（代码分析、网络请求等）

### 2. 会话管理
- Web会话替代CLI会话
- 保持记忆系统和状态持久化
- 支持多用户并发使用

### 3. 实时通信
- WebSocket实现流式响应
- 保持CLI的实时交互体验
- 支持工具调用的实时状态更新

### 4. 用户界面
- 现代化Web界面设计
- 保持专业工具的功能完整性
- 响应式设计，支持移动端访问