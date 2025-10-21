# 项目文件整理说明

## 📁 整理后的目录结构

```
AIDefectDetector/
├── main.py                    # 主程序入口（保持在根目录）
├── requirements.txt           # 依赖文件（如果在根目录）
├── README_NEW.md             # 新的项目说明文档
├── src/                      # 核心源代码
│   ├── agent/               # Agent核心逻辑
│   ├── interfaces/          # 接口层（CLI/Web）
│   ├── llm/                 # LLM集成模块
│   ├── tools/               # 工具集成模块
│   └── utils/               # 工具类（配置、日志、缓存等）
├── config/                   # 配置文件
│   ├── examples/           # 配置模板
│   ├── default.yaml        # 默认配置
│   └── user_config.yaml    # 用户配置
├── scripts/                  # 配置和管理脚本 ⭐ 新增目录
│   ├── quick_setup.py      # 🚀 快速设置向导
│   ├── manage_config.py    # 🔧 配置管理工具
│   ├── diagnose_config.py  # 🔍 配置诊断工具
│   ├── setup_api.sh        # 📋 API配置向导
│   └── set_zhipu_key.sh    # ⚡ 智谱AI快速配置
├── tools/                    # 辅助工具 ⭐ 新增目录
│   ├── aidefect_cli.py     # CLI工具
│   ├── aidefect_web.py     # Web工具
│   └── setup.py            # 安装脚本
├── demos/                    # 演示和示例 ⭐ 新增目录
│   ├── simple_demo.py      # 简单演示
│   └── demo_cli.py         # CLI演示
├── docs/                     # 文档 📚 ⭐ 新增目录
│   ├── API_CONFIG_GUIDE.md        # API配置详细指南
│   ├── CONFIG_IMPROVEMENTS.md     # 配置改进总结
│   ├── QUICK_START.md             # 快速开始指南
│   └── T026_DEEP_ANALYSIS_TASKS.md # 深度分析任务
├── tests/                    # 正式测试（保持原样）
├── tests-temp/               # 临时测试文件 ⭐ 新增目录
└── logs/                     # 日志文件（如果在根目录）
```

## 🔄 文件移动记录

### 移动到 `scripts/` 目录的文件：
- `diagnose_config.py` - 配置诊断工具
- `manage_config.py` - 配置管理工具
- `quick_setup.py` - 快速设置向导
- `setup_api.sh` - API配置向导
- `set_zhipu_key.sh` - 智谱AI快速配置

### 移动到 `docs/` 目录的文件：
- `API_CONFIG_GUIDE.md` - API配置指南
- `CONFIG_IMPROVEMENTS.md` - 配置改进总结
- `QUICK_START.md` - 快速开始指南
- `T026_DEEP_ANALYSIS_TASKS.md` - 深度分析任务文档

### 移动到 `tools/` 目录的文件：
- `aidefect_cli.py` - CLI工具
- `aidefect_web.py` - Web工具
- `setup.py` - 安装脚本

### 移动到 `demos/` 目录的文件：
- `simple_demo.py` - 简单演示
- `demo_cli.py` - CLI演示

### 移动到 `tests-temp/` 目录的文件：
- 所有 `test_*.py` 文件（根目录下的测试文件）

## 🔧 路径更新

### 更新的脚本路径引用：

1. **setup_api.sh**：
   - `diagnose_config.py` → `scripts/diagnose_config.py`
   - `API_CONFIG_GUIDE.md` → `docs/API_CONFIG_GUIDE.md`

2. **set_zhipu_key.sh**：
   - `diagnose_config.py` → `scripts/diagnose_config.py`
   - `setup_api.sh` → `scripts/setup_api.sh`

## 📋 使用指南更新

### 新的命令使用方式：

```bash
# 快速设置向导
python3 scripts/quick_setup.py

# 配置管理
python3 scripts/manage_config.py list
python3 scripts/manage_config.py apply minimal

# 配置诊断
python3 scripts/diagnose_config.py

# API配置向导
./scripts/setup_api.sh

# 智谱AI快速配置
./scripts/set_zhipu_key.sh
```

### 文档访问方式：

```bash
# API配置指南
cat docs/API_CONFIG_GUIDE.md

# 快速开始
cat docs/QUICK_START.md

# 配置改进总结
cat docs/CONFIG_IMPROVEMENTS.md
```

## ✅ 整理的好处

### 1. 清晰的目录结构
- **scripts/** - 所有配置和管理脚本集中管理
- **docs/** - 所有文档集中存储
- **tools/** - 辅助工具分类存放
- **demos/** - 演示文件独立管理

### 2. 更好的可维护性
- 同类文件集中存放，便于查找和维护
- 减少根目录的文件数量，提高项目整洁度
- 明确的目录职责划分

### 3. 改进的用户体验
- 用户可以清楚地知道去哪里找特定类型的文件
- 脚本和文档的路径更加直观
- 项目的专业性和组织性得到提升

### 4. 便于扩展
- 新增配置脚本可以直接放在 scripts/ 目录
- 新增文档可以放在 docs/ 目录
- 新增工具可以放在 tools/ 目录

## 📝 注意事项

1. **脚本路径更新**：所有脚本中的相对路径引用已更新
2. **文档链接更新**：文档中的交叉引用需要相应更新
3. **用户文档**：README_NEW.md 已创建，说明新的文件结构
4. **向后兼容**：主要功能的使用方式保持不变，只是路径有所调整

## 🚀 下一步建议

1. **更新现有文档**：检查并更新其他文档中的路径引用
2. **创建符号链接**：如果需要，可以为常用命令创建符号链接
3. **更新CI/CD**：如果有自动化脚本，需要更新文件路径
4. **用户通知**：通知用户新的文件结构和使用方式

通过这次整理，项目的文件结构更加清晰和专业，便于维护和扩展。