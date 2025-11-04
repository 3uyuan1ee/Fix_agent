#!/usr/bin/env python3
"""
测试完整的用户见解流程 - 从收集到AI prompt
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.phase_a_coordinator import PhaseACoordinator
from src.tools.ai_file_selector import AIFileSelector

def test_full_user_insights_flow():
    """测试完整的用户见解流程"""

    # 创建协调器实例
    coordinator = PhaseACoordinator()
    ai_selector = AIFileSelector()

    # 原始用户需求
    original_requirements = "优化代码质量，修复安全漏洞"

    # 模拟用户输入（根据实际日志，用户只输入了focus_area）
    user_insights = {
        'focus_area': '代码质量'
        # 其他字段为空，因为用户跳过了
    }

    # 步骤1: 合并用户见解
    merged_requirements = coordinator._merge_user_insights_with_requirements(
        original_requirements, user_insights
    )

    print("=== 步骤1: 用户见解合并 ===")
    print(f"原始需求: {original_requirements}")
    print(f"用户见解: {user_insights}")
    print(f"合并后的需求长度: {len(merged_requirements)} 字符")
    print("合并后的完整内容:")
    print("=" * 50)
    print(merged_requirements)
    print("=" * 50)

    # 步骤2: 构建AI prompt
    prompt_builder = ai_selector.prompt_builder
    prompt_result = prompt_builder.build_prompt(
        project_path="../../example",
        analysis_results=[],
        user_requirements=merged_requirements,
        analysis_focus=[],
        runtime_errors=[],
        project_structure={}
    )

    print(f"\n=== 步骤2: AI Prompt构建 ===")
    print(f"prompt返回值类型: {type(prompt_result)}")

    # 获取prompt内容（Prompt对象有system_prompt和user_prompt属性）
    if hasattr(prompt_result, 'user_prompt'):
        user_prompt_content = prompt_result.user_prompt
        print(f"用户prompt长度: {len(user_prompt_content)} 字符")
        print("用户prompt完整内容:")
        print("=" * 50)
        print(user_prompt_content)
        print("=" * 50)

        # 查找用户需求在用户prompt中的位置
        user_requirements_start = user_prompt_content.find("用户需求:")
    else:
        print("  ❌ 错误: prompt对象没有user_prompt属性")
        user_requirements_start = -1
        user_prompt_content = ""
    if user_requirements_start != -1:
        # 提取用户需求行
        start_line = user_prompt_content.rfind('\n', 0, user_requirements_start) + 1
        end_line = user_prompt_content.find('\n', user_requirements_start)
        if end_line == -1:
            end_line = len(user_prompt_content)

        user_requirements_line = user_prompt_content[start_line:end_line]
        print(f"Prompt中的用户需求行:")
        print(f"  {user_requirements_line}")
        print(f"  该行长度: {len(user_requirements_line)} 字符")

        # 检查是否被截断
        if "..." in user_requirements_line or len(user_requirements_line) > 100:
            print("  ⚠️ 警告: 用户需求行可能被截断")
        else:
            print("  ✅ 用户需求行完整显示")

        # 步骤3: 模拟日志截断（重现问题）
        print(f"\n=== 步骤3: 模拟日志截断 ===")
        simulated_log_content = user_requirements_line[:100] + "..." if len(user_requirements_line) > 100 else user_requirements_line
        print(f"模拟日志显示:")
        print(f"  用户需求: {simulated_log_content}")

        if len(user_requirements_line) > 100:
            print(f"  ⚠️ 这就是问题所在：完整内容({len(user_requirements_line)}字符)在日志中被截断为100字符")
        else:
            print(f"  ✅ 内容较短，不会被截断")
    else:
        print("  ❌ 错误: 在prompt中未找到用户需求")

if __name__ == "__main__":
    test_full_user_insights_flow()