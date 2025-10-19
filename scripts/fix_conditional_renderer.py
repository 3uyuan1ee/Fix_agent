#!/usr/bin/env python3

import re

def fix_conditional_renderer():
    """修复条件渲染器中的}字符问题"""

    # 读取原始文件
    with open('/Users/macbookair/Fff/Software_Engine/Agent/Fix_agent/src/prompts/renderer.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 找到 _render_conditionals 方法
    start_pattern = 'def _render_conditionals(self, content: str, parameters: Dict[str, Any]) -> str:'
    start_pos = content.find(start_pattern)

    if start_pos == -1:
        print("Method _render_conditionals not found!")
        return False

    # 找到方法的结束（下一个方法或类的开始）
    method_end_patterns = [
        '\n    def ',
        '\n    @',
        '\n    class ',
        '\n\n\nclass ',
        '\n\n\ndef '
    ]

    end_pos = len(content)
    for pattern in method_end_patterns:
        pos = content.find(pattern, start_pos)
        if pos != -1 and pos < end_pos:
            end_pos = pos

    # 提取方法
    method_content = content[start_pos:end_pos]

    # 创建新的方法实现
    new_method = '''def _render_conditionals(self, content: str, parameters: Dict[str, Any]) -> str:
        \"\"\"渲染条件块\"\"\"
        pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}}'

        def replace_conditional(match):
            param_name = match.group(1)
            conditional_content = match.group(2)

            if param_name in parameters and parameters[param_name]:
                # 递归渲染条件块内的内容
                return self._render_nested_content(conditional_content, parameters)
            else:
                return ""

        return re.sub(pattern, replace_conditional, content, flags=re.DOTALL)

    def _render_loops(self, content: str, parameters: Dict[str, Any]) -> str:'''

    print(f"Original method:\n{method_content}\n")
    print(f"New method:\n{new_method}\n")

    # 替换方法
    new_content = content[:start_pos] + new_method + content[end_pos:]

    # 写回文件
    with open('/Users/macbookair/Fff/Software_Engine/Agent/Fix_agent/src/prompts/renderer.py', 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("Conditional renderer method has been replaced!")
    return True

if __name__ == "__main__":
    fix_conditional_renderer()