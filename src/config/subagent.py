from ..prompt.prompt_template import (code_fixer_subagent_system_prompt,
                                      defect_analyzer_subagent_system_prompt,
                                      fix_validator_subagent_system_prompt)

# 创建子代理配置
defect_analyzer_subagent = {
    "name": "defect-analyzer",
    "description": "专门负责分析代码缺陷，包括语法错误、逻辑问题、性能问题和安全隐患",
    "system_prompt": defect_analyzer_subagent_system_prompt,
    "debug": False,
}

# 代码修复代理
code_fixer_subagent = {
    "name": "code-fixer",
    "description": "专门负责修复代码缺陷，基于缺陷分析报告进行代码修改",
    "system_prompt": code_fixer_subagent_system_prompt,
    "debug": False,
}

# 修复验证代理
fix_validator_subagent = {
    "name": "fix-validator",
    "description": "专门负责验证代码修复的有效性，确保缺陷被正确修复且无新问题",
    "system_prompt": fix_validator_subagent_system_prompt,
    "debug": False,
}
