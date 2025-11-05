"""
具体的Prompt模板定义
"""

from typing import Any, Dict, List

from .base import PromptCategory, PromptTemplate, PromptType


class StaticAnalysisTemplate:
    """静态分析Prompt模板"""

    @staticmethod
    def get_system_prompt() -> PromptTemplate:
        """获取系统提示模板"""
        return PromptTemplate(
            name="static_analysis_system",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.SYSTEM,
            template="""你是一个专业的软件缺陷检测专家，擅长使用静态分析工具识别代码中的潜在问题。

你的任务是分析静态分析工具的输出结果，识别真正的缺陷并过滤掉误报。

分析原则：
1. 优先关注安全漏洞和崩溃风险
2. 考虑代码的实际使用场景
3. 区分真正的缺陷和代码风格问题
4. 提供可操作的建议

请仔细分析提供的静态分析结果。""",
            description="静态分析系统提示",
            version="1.0",
            author="AIDefectDetector",
            tags=["static_analysis", "security", "code_quality"],
        )

    @staticmethod
    def get_analysis_prompt() -> PromptTemplate:
        """获取分析提示模板"""
        return PromptTemplate(
            name="static_analysis_main",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="""请分析以下静态分析结果：

## 项目信息
- 项目名称：{{project_name}}
- 编程语言：{{language}}
- 代码行数：{{lines_of_code}}
- 分析工具：{{tool_name}}

## 分析结果概览
{{#if summary}}
总问题数：{{summary.total_issues}}
严重问题：{{summary.critical_issues}}
高危问题：{{summary.high_issues}}
中危问题：{{summary.medium_issues}}
低危问题：{{summary.low_issues}}
{{/if}}

## 详细问题列表
{{#each issues}}
### 问题 {{index + 1}}
**类型：** {{type}}
**严重性：** {{severity}}
**文件：** {{file}}:{{line}}
**描述：** {{description}}
**代码片段：**
```
{{code_snippet}}
```
**规则：** {{rule}}
{{/each}}

请提供以下分析：
1. 真正需要修复的缺陷列表（按优先级排序）
2. 每个缺陷的风险评估
3. 误报分析（如有）
4. 总体安全评估""",
            description="静态分析主要提示模板",
            parameters={
                "project_name": "项目名称",
                "language": "编程语言",
                "lines_of_code": "代码行数",
                "tool_name": "分析工具名称",
                "summary.total_issues": "总问题数",
                "summary.critical_issues": "严重问题数",
                "summary.high_issues": "高危问题数",
                "summary.medium_issues": "中危问题数",
                "summary.low_issues": "低危问题数",
                "issues": "问题列表",
                "type": "问题类型",
                "severity": "严重性",
                "file": "文件",
                "line": "行号",
                "description": "描述",
                "code_snippet": "代码片段",
                "rule": "规则",
                "index": "索引",
            },
            version="1.0",
            author="AIDefectDetector",
            tags=["static_analysis", "defect_analysis", "security"],
        )

    @staticmethod
    def get_summary_prompt() -> PromptTemplate:
        """获取总结提示模板"""
        return PromptTemplate(
            name="static_analysis_summary",
            category=PromptCategory.STATIC_ANALYSIS,
            prompt_type=PromptType.USER,
            template="""基于以下静态分析结果，请提供一个简洁的总结报告：

## 关键指标
- 总缺陷数：{{total_defects}}
- 严重缺陷：{{critical_defects}}
- 高危缺陷：{{high_defects}}
- 误报数量：{{false_positives}}

## 最严重的缺陷
{{#each top_defects}}
{{index + 1}}. {{type}} - {{file}}:{{line}} - {{description}}
{{/each}}

## 总体评估
{{overall_assessment}}

请提供：
1. 执行摘要（2-3句话）
2. 主要风险点
3. 建议的修复优先级
4. 预估修复工作量""",
            description="静态分析总结提示模板",
            parameters={
                "total_defects": "总缺陷数",
                "critical_defects": "严重缺陷数",
                "high_defects": "高危缺陷数",
                "false_positives": "误报数量",
                "top_defects": "最严重缺陷列表",
                "overall_assessment": "总体评估",
                "index": "索引",
                "type": "类型",
                "file": "文件",
                "line": "行号",
                "description": "描述",
            },
            version="1.0",
            author="AIDefectDetector",
            tags=["summary", "report", "prioritization"],
        )


class DeepAnalysisTemplate:
    """深度分析Prompt模板"""

    @staticmethod
    def get_system_prompt() -> PromptTemplate:
        """获取系统提示模板"""
        return PromptTemplate(
            name="deep_analysis_system",
            category=PromptCategory.DEEP_ANALYSIS,
            prompt_type=PromptType.SYSTEM,
            template="""你是一个资深的软件架构师和安全专家，具备深厚的代码分析和漏洞挖掘经验。

你的任务是对代码进行深度分析，发现潜在的安全风险、性能问题和架构缺陷。

分析重点：
1. 安全漏洞（注入、越权、信息泄露等）
2. 性能瓶颈和资源泄漏
3. 架构设计缺陷
4. 业务逻辑漏洞
5. 数据一致性问题

请从多个维度深入分析代码，提供专业的见解和建议。""",
            description="深度分析系统提示",
            version="1.0",
            author="AIDefectDetector",
            tags=["deep_analysis", "security", "architecture", "performance"],
        )

    @staticmethod
    def get_code_analysis_prompt() -> PromptTemplate:
        """获取代码分析提示模板"""
        return PromptTemplate(
            name="deep_code_analysis",
            category=PromptCategory.DEEP_ANALYSIS,
            prompt_type=PromptType.USER,
            template="""请对以下代码进行深度分析：

## 代码上下文
- 文件：{{file_path}}
- 函数：{{function_name}}
- 语言：{{language}}
- 代码行数：{{code_lines}}

## 代码内容
```{{language}}
{{code_content}}
```

## 相关信息
{{#if dependencies}}
依赖项：
{{#each dependencies}}
- {{name}}: {{version}}
{{/each}}
{{/if}}

{{#if usage_context}}
使用场景：{{usage_context}}
{{/if}}

请从以下角度进行分析：

### 1. 安全性分析
- 输入验证和过滤
- 权限检查
- 敏感数据处理
- 注入攻击风险

### 2. 性能分析
- 时间复杂度
- 空间复杂度
- 资源使用效率
- 潜在性能瓶颈

### 3. 架构分析
- 设计模式使用
- 模块耦合度
- 可扩展性
- 可维护性

### 4. 业务逻辑分析
- 边界条件处理
- 异常情况处理
- 数据一致性
- 业务规则实现

### 5. 代码质量分析
- 可读性
- 可测试性
- 重构建议
- 最佳实践遵循

请提供具体的发现、风险评估和改进建议。""",
            description="深度代码分析提示模板",
            parameters={
                "file_path": "文件路径",
                "function_name": "函数名称",
                "language": "编程语言",
                "code_lines": "代码行数",
                "code_content": "代码内容",
                "dependencies": "依赖项列表",
                "usage_context": "使用场景",
                "name": "名称",
                "version": "版本",
            },
            version="1.0",
            author="AIDefectDetector",
            tags=[
                "deep_analysis",
                "code_analysis",
                "security",
                "performance",
                "architecture",
            ],
        )

    @staticmethod
    def get_vulnerability_assessment_prompt() -> PromptTemplate:
        """获取漏洞评估提示模板"""
        return PromptTemplate(
            name="vulnerability_assessment",
            category=PromptCategory.DEEP_ANALYSIS,
            prompt_type=PromptType.USER,
            template="""请对以下潜在的漏洞进行深入评估：

## 漏洞基本信息
- 漏洞类型：{{vulnerability_type}}
- 严重程度：{{severity_level}}
- 影响范围：{{affected_components}}
- 发现位置：{{location}}

## 漏洞描述
{{description}}

## 漏洞上下文
```{{language}}
{{vulnerable_code}}
```

## 攻击场景分析
{{#if attack_scenarios}}
{{#each attack_scenarios}}
- {{title}}: {{description}}
  影响程度：{{impact}}
  利用难度：{{difficulty}}
{{/each}}
{{/if}}

请进行深入分析：

### 1. 漏洞机理
- 根本原因分析
- 触发条件
- 攻击向量

### 2. 影响评估
- 数据安全影响
- 系统可用性影响
- 业务影响
- 合规性影响

### 3. 利用风险评估
- 攻击门槛
- 所需技能
- 所需资源
- 成功概率

### 4. 修复建议
- 短期缓解措施
- 长期修复方案
- 修复优先级
- 测试验证方法

### 5. 预防措施
- 类似漏洞预防
- 安全开发实践
- 检测机制改进""",
            description="漏洞评估提示模板",
            parameters={
                "vulnerability_type": "漏洞类型",
                "severity_level": "严重程度",
                "affected_components": "影响组件",
                "location": "位置",
                "description": "漏洞描述",
                "language": "编程语言",
                "vulnerable_code": "漏洞代码",
                "attack_scenarios": "攻击场景列表",
                "title": "标题",
                "impact": "影响程度",
                "difficulty": "利用难度",
            },
            version="1.0",
            author="AIDefectDetector",
            tags=[
                "deep_analysis",
                "security",
                "vulnerability",
                "security_assessment",
                "risk_analysis",
            ],
        )


class RepairSuggestionTemplate:
    """修复建议Prompt模板"""

    @staticmethod
    def get_system_prompt() -> PromptTemplate:
        """获取系统提示模板"""
        return PromptTemplate(
            name="repair_suggestion_system",
            category=PromptCategory.REPAIR_SUGGESTION,
            prompt_type=PromptType.SYSTEM,
            template="""你是一个经验丰富的软件工程师，擅长代码修复和优化。

你的任务是为发现的软件缺陷提供高质量的修复建议。

修复建议原则：
1. 提供可执行的修复代码
2. 保持原有功能不变
3. 遵循最佳实践
4. 考虑性能和安全性
5. 提供多种解决方案（如适用）

请确保修复建议的准确性和实用性。""",
            description="修复建议系统提示",
            version="1.0",
            author="AIDefectDetector",
            tags=["repair", "code_fix", "optimization", "best_practices"],
        )

    @staticmethod
    def get_fix_suggestion_prompt() -> PromptTemplate:
        """获取修复建议提示模板"""
        return PromptTemplate(
            name="defect_fix_suggestion",
            category=PromptCategory.REPAIR_SUGGESTION,
            prompt_type=PromptType.USER,
            template="""请为以下缺陷提供修复建议：

## 缺陷信息
- 缺陷类型：{{defect_type}}
- 严重程度：{{severity}}
- 文件：{{file_path}}:{{line_number}}
- 描述：{{description}}

## 问题代码
```{{language}}
{{problematic_code}}
```

## 代码上下文
```{{language}}
{{context_code}}
```

## 相关约束
{{#if constraints}}
{{#each constraints}}
- {{type}}: {{description}}
{{/each}}
{{/if}}

请提供：

### 1. 问题分析
- 问题根因
- 影响范围
- 修复优先级

### 2. 修复方案
{{#if multiple_solutions}}
#### 方案一：推荐方案
```{{language}}
{{fix_code_solution_1}}
```
**说明：**{{solution_1_explanation}}
**优点：**{{solution_1_advantages}}
**缺点：**{{solution_1_disadvantages}}
**风险评估：**{{solution_1_risks}}

#### 方案二：替代方案
```{{language}}
{{fix_code_solution_2}}
```
**说明：**{{solution_2_explanation}}
**优点：**{{solution_2_advantages}}
**缺点：**{{solution_2_disadvantages}}
{{else}}
#### 修复方案
```{{language}}
{{fix_code}}
```
**说明：**{{fix_explanation}}
{{/if}}

### 3. 实施建议
- 修复步骤
- 测试要求
- 回滚计划
- 注意事项

### 4. 预防措施
- 编码规范改进
- 代码审查重点
- 自动化检测规则""",
            description="缺陷修复建议提示模板",
            parameters={
                "defect_type": "缺陷类型",
                "severity": "严重程度",
                "file_path": "文件路径",
                "line_number": "行号",
                "description": "缺陷描述",
                "language": "编程语言",
                "problematic_code": "问题代码",
                "context_code": "上下文代码",
                "constraints": "约束条件",
                "multiple_solutions": "是否多方案",
                "fix_code": "修复代码",
                "fix_explanation": "修复说明",
                "type": "类型",
                "fix_code_solution_1": "修复代码方案1",
                "solution_1_explanation": "方案1说明",
                "solution_1_advantages": "方案1优点",
                "solution_1_disadvantages": "方案1缺点",
                "solution_1_risks": "方案1风险",
                "fix_code_solution_2": "修复代码方案2",
                "solution_2_explanation": "方案2说明",
                "solution_2_advantages": "方案2优点",
                "solution_2_disadvantages": "方案2缺点",
                "else": "else",
            },
            version="1.0",
            author="AIDefectDetector",
            tags=[
                "repair",
                "fix_suggestion",
                "code_fix",
                "code_repair",
                "best_practices",
            ],
        )

    @staticmethod
    def get_refactoring_suggestion_prompt() -> PromptTemplate:
        """获取重构建议提示模板"""
        return PromptTemplate(
            name="code_refactoring_suggestion",
            category=PromptCategory.REPAIR_SUGGESTION,
            prompt_type=PromptType.USER,
            template="""请为以下代码提供重构建议：

## 当前代码
```{{language}}
{{current_code}}
```

## 代码分析
- 复杂度：{{complexity}}
- 可读性评分：{{readability_score}}
- 维护性评分：{{maintainability_score}}
- 测试覆盖率：{{test_coverage}}

## 识别的问题
{{#each issues}}
- {{type}}: {{description}}
{{/each}}

请提供重构建议：

### 1. 重构目标
- 主要目标：{{main_goal}}
- 预期收益：{{expected_benefits}}

### 2. 重构方案
#### 步骤1：{{step_1_description}}
```{{language}}
{{step_1_code}}
```

#### 步骤2：{{step_2_description}}
```{{language}}
{{step_2_code}}
```

{{#if additional_steps}}
{{#each additional_steps}}
#### 步骤{{index + 3}}：{{description}}
```{{language}}
{{code}}
```
{{/each}}
{{/if}}

### 3. 重构效果
- 代码质量提升
- 性能改进
- 可维护性提升

### 4. 风险评估
- 重构风险
- 测试要求
- 回滚策略""",
            description="代码重构建议提示模板",
            parameters={
                "language": "编程语言",
                "current_code": "当前代码",
                "complexity": "复杂度",
                "readability_score": "可读性评分",
                "maintainability_score": "维护性评分",
                "test_coverage": "测试覆盖率",
                "issues": "问题列表",
                "main_goal": "主要目标",
                "expected_benefits": "预期收益",
                "step_1_description": "步骤1描述",
                "step_1_code": "步骤1代码",
                "step_2_description": "步骤2描述",
                "step_2_code": "步骤2代码",
                "type": "类型",
                "index": "索引",
                "description": "描述",
                "code": "代码",
            },
            version="1.0",
            author="AIDefectDetector",
            tags=["refactoring", "code_quality", "optimization"],
        )
