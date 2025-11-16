# Dataset评估框架 - 完全自动化的SWE-bench评估

🚀 **完全隔离的Dataset评估框架，实现标准SWE-bench评估流程**

## 🎯 核心特性

- ✅ **完全隔离**: 独立运行，不依赖主项目src/目录
- ✅ **功能完整**: 保留所有工具和中间件功能
- ✅ **自动化**: 去除交互式命令行，全自动测试
- ✅ **SWE-bench标准**: 实现官方评估流程
- ✅ **修复文件名问题**: 使用哈希值避免文件名过长
- ✅ **手动数据集管理**: 去除自动下载，更稳定可靠

## 📁 架构设计

```
Dataset/
├── 🚀 快速开始
│   ├── main.py                 # 主入口脚本
│   ├── quick_start.py          # 一键设置脚本
│   ├── test_framework.py       # 功能测试脚本
│   └── requirements.txt        # Python依赖
├── ⚙️ 配置与数据
│   ├── config.json            # 配置文件（需添加API密钥）
│   ├── data_types.py          # 数据类型定义
│   └── .gitignore             # Git忽略文件
├── 🔧 核心模块
│   ├── core/                  # 核心评估逻辑
│   │   ├── evaluation.py      # 评估框架主类
│   │   ├── agent.py           # 独立Agent
│   │   └── agent_config.py    # Agent配置
│   ├── loaders/               # 数据集加载器
│   │   ├── swe_bench.py       # SWE-bench Lite加载器
│   │   ├── base.py            # 基础加载器
│   │   └── bugs_in_py.py      # BugsInPy加载器
│   └── utils/                 # 工具模块
│       ├── file_utils.py      # 文件工具（修复文件名问题）
│       ├── config.py          # 配置管理
│       ├── validation.py      # 验证工具
│       ├── metrics.py         # 指标计算
│       └── visualization.py   # 可视化工具
├── 📊 数据与结果
│   ├── datasets/              # 数据集存储（手动下载）
│   │   ├── predictions/       # 预测文件输出
│   │   └── swe-bench/        # SWE-bench仓库（可选）
│   ├── logs/                  # 日志目录
│   ├── temp/                  # 临时文件
│   ├── results/               # 评估结果
│   └── testbed/               # 测试床目录
└── 📚 文档
    ├── README.md              # 本文档
    └── MIGRATION_GUIDE.md      # 迁移指南
```

## 🛠️ 安装与准备

### 1. 环境要求

```bash
# Python 3.8+
python --version

# Git（必需）
git --version

# Docker（可选，用于标准评估）
docker --version
```

### 2. 依赖安装

```bash
cd Dataset/
pip install -r requirements.txt
```

### 3. 数据集准备

#### 手动下载SWE-bench Lite（推荐）

```bash
# 创建数据集目录
mkdir -p datasets

# 下载SWE-bench Lite（229个实例）
wget https://github.com/princeton-nlp/SWE-bench/raw/main/data/swe-bench-lite.jsonl \
  -O datasets/swe-bench-lite.jsonl

# 或者下载完整SWE-bench（可选）
wget https://github.com/princeton-nlp/SWE-bench/raw/main/data/swe-bench-test.json \
  -O datasets/swe-bench-full.jsonl
```

#### 手动下载SWE-bench仓库（用于标准评估）

```bash
# 克隆SWE-bench仓库
cd datasets/
git clone https://github.com/princeton-nlp/SWE-bench.git
```

### 4. 配置文件

创建或修改 `config.json`:

```json
{
  "agent": {
    "model": "gpt-4",
    "api_key": "your-api-key",
    "api_base": "https://api.openai.com/v1/",
    "temperature": 0.1,
    "max_tokens": 4000
  },
  "evaluation": {
    "default_timeout": 300,
    "max_workers": 4,
    "enable_caching": true
  }
}
```

## 🚀 使用方法

### 1. 快速测试

```bash
# 测试5个样本的完整流程
python main.py --mode complete --samples 5 --debug

# 只生成预测文件
python main.py --mode generate --samples 10

# 只运行评估（需要已有预测文件）
python main.py --mode evaluate --predictions ./datasets/predictions/test_predictions.jsonl
```

### 2. 完整评估流程

```bash
# 生成预测文件
python main.py \
  --mode generate \
  --dataset ./datasets/swe-bench-lite.jsonl \
  --samples 50 \
  --debug

# 运行SWE-bench标准评估
python main.py \
  --mode evaluate \
  --predictions ./datasets/predictions/test_predictions.jsonl \
  --swe-bench-path ./datasets/SWE-bench

# 一键完整流程
python main.py \
  --mode complete \
  --dataset ./datasets/swe-bench-lite.jsonl \
  --samples 100 \
  --log-dir ./logs \
  --results-dir ./results
```

### 3. 高级用法

```bash
# 使用特定配置文件
python main.py --config ./custom_config.json --mode complete

# 调试模式
python main.py --mode complete --debug --samples 3

# 自定义临时目录
python main.py --temp-dir ./my_temp --mode complete
```

## 📊 评估流程

### 标准SWE-bench流程

框架实现了完整的SWE-bench标准评估流程：

#### 1. 问题理解与规划
- **输入**: `problem_statement` (GitHub Issue文本)
- **任务**: 理解Bug描述、期望行为、复现方式
- **输出**: 解决计划（目标文件、修复方法、复杂度评估）

#### 2. 代码生成与编辑
- **输入**: Issue描述 + 检索的相关代码
- **任务**: 生成符合项目风格的精确补丁（diff格式）
- **输出**: 标准patch格式，可通过 `patch -p1` 应用

#### 3. 补丁验证与提交
- **任务**: 使用 `git apply` 应用补丁
- **处理**: 自动处理应用失败情况（如冲突）
- **验证**: 运行测试套件验证修复效果

#### 4. SWE-bench官方评估
```bash
python run_evaluation.py \
  --predictions_path predictions.jsonl \
  --swe_bench_tasks swe-bench-lite.jsonl \
  --log_dir logs \
  --testbed testbed_dir
```

### 预测文件格式

生成的预测文件符合SWE-bench标准格式：

```json
{"instance_id": "django__django-10101", "model_patch": "--- a/file.py\n+++ b/file.py\n...", "model_name_or_path": "fix-agent-dataset"}
{"instance_id": "numpy__numpy-12345", "model_patch": "--- a/file.py\n+++ b/file.py\n...", "model_name_or_path": "fix-agent-dataset"}
```

## 🔧 关键改进

### 1. 文件名过长问题修复

```python
# 原有问题：直接使用补丁内容作为文件名
patch_file = f"temp_{patch_content[:50]}.patch"  # 可能过长

# 修复方案：使用哈希值 + UUID
def create_secure_temp_filename(content: str, prefix: str = "patch_") -> str:
    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:12]
    unique_id = str(uuid.uuid4())[:8]
    return f"{prefix}{content_hash}_{unique_id}.patch"
```

### 2. 完全隔离架构

- ✅ 不再依赖 `src/` 目录
- ✅ 复制必要的工具和中间件到 `Dataset/` 下
- ✅ 独立的导入和配置系统
- ✅ 自包含的依赖管理

### 3. 手动数据集管理

- ✅ 去除自动下载功能（减少错误）
- ✅ 支持多种数据集格式（JSON/JSONL）
- ✅ 灵活的数据集路径配置
- ✅ 完善的数据验证

### 4. 优化错误处理

```python
# 安全的补丁应用
result = apply_patch_safely(patch_content, target_dir)
if result["success"]:
    # 补丁应用成功
    applied_files = result["applied_files"]
else:
    # 优雅处理失败
    logger.error(f"补丁应用失败: {result['error']}")
```

## 📈 结果分析

### 输出文件

评估完成后会生成以下文件：

```
results/
├── final_report.json          # 详细JSON报告
├── evaluation_report.md       # Markdown报告
└── evaluation_results.json    # 原始评估结果
```

### 报告内容

- **评估摘要**: 总任务数、解决数、成功率、性能等级
- **详细结果**: 每个任务的执行情况和错误分析
- **性能指标**: 执行时间分布、错误类型统计
- **改进建议**: 基于结果的优化建议

## 🐛 故障排除

### 常见问题

#### 1. 数据集文件不存在
```bash
# 错误: 数据集文件不存在: ./datasets/swe-bench-lite.jsonl
# 解决: 手动下载数据集文件
wget https://github.com/princeton-nlp/SWE-bench/raw/main/data/swe-bench-lite.jsonl \
  -O datasets/swe-bench-lite.jsonl
```

#### 2. SWE-bench评估脚本不存在
```bash
# 错误: SWE-bench评估脚本不存在
# 解决: 克隆SWE-bench仓库
cd datasets/
git clone https://github.com/princeton-nlp/SWE-bench.git
```

#### 3. API密钥配置
```bash
# 错误: API密钥未配置
# 解决: 在config.json中配置正确的API密钥
```

#### 4. 权限问题
```bash
# 错误: 权限被拒绝
# 解决: 确保有创建临时文件和目录的权限
chmod -R 755 Dataset/
```

### 调试技巧

```bash
# 启用详细日志
python main.py --mode complete --debug --samples 1

# 检查日志文件
tail -f logs/generate_evaluation.log

# 验证预测文件格式
python -c "
import json
with open('datasets/predictions/test_predictions.jsonl', 'r') as f:
    for i, line in enumerate(f):
        data = json.loads(line)
        print(f'Line {i+1}: {data[\"instance_id\"]} - {\"valid\" if data.get(\"model_patch\") else \"missing patch\"}')
"
```

## 🚀 性能优化

### 1. 并行处理
- 使用 `ThreadPoolExecutor` 并行处理任务
- 可配置工作线程数量（默认4个）

### 2. 缓存机制
- 任务结果缓存
- 中间文件智能管理

### 3. 资源管理
- 自动清理临时文件
- 内存使用优化

## 📝 开发指南

### 扩展数据集支持

```python
# 在 loaders/ 目录下创建新的加载器
class CustomDatasetLoader(BaseDatasetLoader):
    def load_tasks(self, sample_size=None):
        # 实现自定义数据集加载逻辑
        pass
```

### 自定义Agent

```python
# 在 core/agent.py 中扩展现有Agent
class CustomAgent(DatasetAgent):
    def _understand_and_plan(self, task):
        # 实现自定义的问题理解逻辑
        pass
```

## 🤝 贡献

欢迎提交Issue和Pull Request来改进这个框架！

### 开发环境设置

```bash
# 克隆项目
git clone <your-repo>
cd Dataset/

# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
python -m pytest tests/
```

## 📄 许可证

本项目采用 MIT 许可证。

---

**🎉 现在你有了一个完全隔离、功能完整的Dataset评估框架！**

开始使用：
```bash
python main.py --mode complete --samples 5 --debug
```