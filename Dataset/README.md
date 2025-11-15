# Fix Agent Dataset 评估框架

这是一个独立的评估框架，专门用于评估Fix Agent在SWE-bench和BugsInPy数据集上的性能。该框架完全独立于主程序的交互式环境，不会影响现有功能。

## 🎯 功能特点

- **独立运行**: 完全独立于交互式环境，不影响主程序
- **多数据集支持**: 支持SWE-bench和BugsInPy标准数据集
- **并行处理**: 支持多线程并行评估，提高效率
- **灵活配置**: 支持多种配置选项和过滤器
- **详细报告**: 生成详细的评估报告和可视化图表
- **容错性强**: 完善的错误处理和回退机制

## 🚀 快速开始

### 1. 基础测试
```bash
python simple_test.py
```

### 2. 完整工作流程测试
```bash
python test_complete_workflow.py
```

### 3. 运行实际评估

#### 评估SWE-bench数据集（10个样本）：
```bash
python run_evaluation.py --dataset swe-bench --samples 10
```

#### 评估BugsInPy数据集（5个样本，调试模式）：
```bash
python run_evaluation.py --dataset bugsinpy --samples 5 --debug
```

## 📋 核心组件

- **core/**: 核心评估逻辑和独立的DatasetAgent
- **loaders/**: SWE-bench和BugsInPy数据集加载器
- **utils/**: 指标计算、可视化和配置管理工具
- **run_evaluation.py**: 主评估脚本，支持完整的命令行接口

## 🎉 测试结果

经过完整测试，Dataset评估框架已验证：
- ✅ 所有核心功能正常工作
- ✅ 数据加载器工作正常  
- ✅ 评估框架工作正常
- ✅ 指标计算工作正常
- ✅ 导入机制完善，支持多层回退
- ✅ 简化版工具无外部依赖

框架已准备就绪，可以开始使用！
