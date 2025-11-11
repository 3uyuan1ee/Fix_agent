# 增强版 Agent 使用指南

## 🎯 快速开始

### 1. 替换现有的 Agent

只需将原来的 `base_agent` 导入替换为 `enhanced_base_agent`：

```python
# 原来的代码
from base_agent import create_research_agent
researcher = create_research_agent("my-agent", "研究代理", model=model)

# 替换为增强版
from enhanced_base_agent import create_enhanced_research_agent
researcher = create_enhanced_research_agent("my-agent", "研究代理", model=model)
```

### 2. 启用完整可视化

```python
from enhanced_base_agent import create_enhanced_research_agent, VisualizationConfig

# 创建带完整可视化的代理
researcher = create_enhanced_research_agent(
    name="enhanced-researcher",
    description="增强研究代理",
    model=your_model,

    # 启用所有可视化功能
    visualization_config=VisualizationConfig(
        show_thinking=True,      # 显示思考过程
        show_tool_calls=True,    # 显示工具调用
        show_todo_updates=True,  # 显示Todo更新
        show_timing=True,        # 显示执行时间
        show_subagent_calls=True # 显示子代理调用
    )
)

# 构建并使用
researcher.build()
result = researcher.invoke({"messages": [{"role": "user", "content": "你的任务"}]})
```

## 🎨 可视化效果展示

### 思考过程可视化
```
🧠 思考过程 [2.34s]
├─ 我需要分析这个复杂的问题，首先理解用户的需求...
├─ 问题的核心在于如何有效地组织和呈现信息...
└─ 我决定采用结构化的方法来回答这个问题...
```

### 工具调用可视化
```
🔧 调用工具: search_web [1.23s]
├─ 参数: {"query": "Python数据科学", "max_results": 5}
✅ 工具 search_web 执行完成
└─ 结果: 找到了10个相关资源，包括官方文档、教程和案例...
```

### Todo列表构建可视化
```
📝 Todo列表更新: 任务分解
├─ ["研究Python语言特性", "分析数据科学生态", "总结应用场景"]
📝 Todo列表更新: 进度更新
├─ ["✓ 研究Python语言特性", "分析数据科学生态", "总结应用场景"]
```

### 执行摘要
```
📊 执行摘要
├─ 总步骤数: 15
├─ 工具调用次数: 6
├─ Todo更新次数: 4
├─ 子代理调用次数: 2
└─ 总执行时间: 23.45秒
```

## 🔧 高级配置

### 自定义显示内容

```python
# 只显示关键信息
minimal_config = VisualizationConfig(
    show_thinking=False,        # 隐藏思考过程
    show_tool_calls=True,       # 只显示工具调用
    show_todo_updates=False,    # 隐藏Todo更新
    show_timing=False,          # 隐藏时间信息
    max_message_length=100      # 限制消息长度
)

# 调试模式 - 显示所有信息
debug_config = VisualizationConfig(
    show_thinking=True,
    show_tool_calls=True,
    show_todo_updates=True,
    show_timing=True,
    show_subagent_calls=True,
    max_message_length=1000,    # 更长的消息显示
    colors={
        "thinking": "🤔",
        "tool_call": "🔨",
        "tool_result": "🎯",
        "todo": "📋",
        "subagent": "👥",
        "error": "🚨",
        "success": "✨"
    }
)
```

### 不同的Agent类型

```python
# 研究代理 - 显示完整的思考和研究过程
research_agent = create_enhanced_research_agent(
    name="researcher",
    description="专业研究代理",
    visualization_config=VisualizationConfig(
        show_thinking=True,
        show_tool_calls=True,
        show_todo_updates=True,
        show_timing=True
    )
)

# 开发代理 - 重点显示代码分析和工具使用
dev_agent = create_enhanced_developer_agent(
    name="developer",
    description="软件开发代理",
    visualization_config=VisualizationConfig(
        show_thinking=False,      # 开发时不需要过多思考展示
        show_tool_calls=True,     # 重点显示工具使用
        show_todo_updates=False,  # 隐藏Todo更新
        show_timing=True          # 显示执行时间
    )
)

# 协调代理 - 重点显示子代理协调过程
coordinator_agent = create_enhanced_coordinator_agent(
    name="coordinator",
    description="项目协调代理",
    visualization_config=VisualizationConfig(
        show_thinking=True,
        show_tool_calls=True,
        show_todo_updates=True,
        show_subagent_calls=True,  # 重点显示子代理调用
        show_timing=True
    )
)
```

## 📊 获取执行日志

```python
# 执行任务
result = researcher.invoke({"messages": [{"role": "user", "content": "任务"}]})

# 获取详细日志
execution_log = researcher.get_execution_log()

# 分析执行数据
summary = execution_log["execution_summary"]
print(f"总执行时间: {summary['total_time']:.2f}秒")
print(f"工具调用次数: {summary['tool_calls']}")
print(f"Todo更新次数: {summary['todo_updates']}")

# 获取详细步骤
for step in summary["steps"]:
    print(f"{step['timestamp']}: {step['type']} - {step['content']}")
```

## 🌊 流式执行监控

```python
# 流式执行
for chunk in researcher.stream({"messages": [{"role": "user", "content": "任务"}]}):
    # 显示流式进度
    if isinstance(chunk, dict):
        if "messages" in chunk:
            print(f"📦 收到 {len(chunk['messages'])} 条消息")
        if "todos" in chunk:
            print(f"📝 Todo更新: {len(chunk['todos'])} 个任务")
```

## ⚠️ 性能优化建议

### 1. 根据需要选择可视化级别

```python
# 生产环境 - 最小化显示
production_config = VisualizationConfig(
    show_thinking=False,
    show_tool_calls=True,      # 只显示关键工具调用
    show_todo_updates=False,
    show_timing=False,
    max_message_length=50
)

# 开发环境 - 完整显示
development_config = VisualizationConfig(
    show_thinking=True,
    show_tool_calls=True,
    show_todo_updates=True,
    show_timing=True,
    max_message_length=500
)
```

### 2. 批量处理时关闭时间显示

```python
# 批量任务配置
batch_config = VisualizationConfig(
    show_timing=False,          # 批量时关闭时间显示
    max_message_length=200      # 限制消息长度
)
```

### 3. 复杂任务启用完整可视化

```python
# 复杂任务配置
complex_task_config = VisualizationConfig(
    show_thinking=True,         # 复杂任务需要思考过程
    show_tool_calls=True,
    show_todo_updates=True,     # 复杂任务需要Todo管理
    show_timing=True,           # 监控执行时间
    show_subagent_calls=True    # 复杂任务可能需要子代理
)
```

## 🎯 实际使用场景

### 场景1: 代码审查代理

```python
code_reviewer = create_enhanced_developer_agent(
    name="code-reviewer",
    description="代码审查专家",
    system_prompt="""你是代码审查专家，请：
    1. 分析代码结构和逻辑
    2. 检查潜在问题和改进点
    3. 提供具体的优化建议

    请展示你的分析过程。""",

    visualization_config=VisualizationConfig(
        show_thinking=True,      # 显示代码分析思考
        show_tool_calls=True,    # 显示代码分析工具使用
        show_todo_updates=True,  # 显示审查清单
        show_timing=False        # 代码审查不需要时间显示
    )
)
```

### 场景2: 研究分析代理

```python
research_analyst = create_enhanced_research_agent(
    name="research-analyst",
    description="专业研究分析师",
    system_prompt="""你是专业研究分析师，请：
    1. 深入分析研究问题
    2. 收集和整理相关信息
    3. 提供详细的分析报告

    请展示你的研究过程。""",

    visualization_config=VisualizationConfig(
        show_thinking=True,      # 显示研究思考过程
        show_tool_calls=True,    # 显示信息收集工具
        show_todo_updates=True,  # 显示研究步骤
        show_timing=True,        # 监控研究时间
        max_message_length=300   # 详细显示研究内容
    )
)
```

### 场景3: 项目协调代理

```python
project_coordinator = create_enhanced_coordinator_agent(
    name="project-coordinator",
    description="项目协调专家",
    system_prompt="""你是项目协调专家，请：
    1. 分解复杂任务
    2. 协调不同专家代理
    3. 整合分析结果

    请展示你的协调过程。""",

    # 添加子代理
    subagents=[
        SubAgent(
            name="research-expert",
            description="研究专家",
            system_prompt="你是专业的研究专家"
        ),
        SubAgent(
            name="analysis-expert",
            description="分析专家",
            system_prompt="你是专业的数据分析专家"
        )
    ],

    visualization_config=VisualizationConfig(
        show_thinking=True,         # 显示协调思考
        show_tool_calls=True,       # 显示协调工具
        show_todo_updates=True,     # 显示任务分解
        show_subagent_calls=True,   # 重点显示子代理调用
        show_timing=True            # 监控协调时间
    )
)
```

## 📝 最佳实践

### 1. 选择合适的可视化级别
- **简单任务**: 只显示工具调用
- **复杂任务**: 显示完整过程
- **批量处理**: 最小化显示
- **调试阶段**: 显示所有信息

### 2. 自定义系统提示
在系统提示中鼓励展示思考过程：
```
请详细展示你的：
1. 思考过程和分析逻辑
2. 工具选择的原因
3. 执行步骤和结果
```

### 3. 监控执行性能
定期检查执行日志，优化性能：
```python
log = researcher.get_execution_log()
if log["execution_summary"]["total_time"] > 60:  # 超过60秒
    print("⚠️ 任务执行时间较长，考虑优化")
```

### 4. 错误处理
利用可视化来诊断问题：
- 查看详细的错误信息
- 分析工具调用失败原因
- 检查思考过程的逻辑问题

## 🎉 总结

通过使用增强版 agent，你可以：

✅ **清楚地看到** agent 的思考过程和推理逻辑
✅ **详细地监控** 工具调用的每个步骤
✅ **实时地跟踪** Todo 列表的构建过程
✅ **有效地调试** 复杂的 agent 行为
✅ **优化地提升** agent 的性能和效率

开始使用增强版 agent，享受完全透明的 agent 执行体验！