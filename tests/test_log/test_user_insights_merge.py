#!/usr/bin/env python3
"""
测试用户见解合并功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.tools.phase_a_coordinator import PhaseACoordinator

def test_merge_user_insights():
    """测试用户见解合并功能"""

    # 创建PhaseACoordinator实例
    coordinator = PhaseACoordinator()

    # 测试数据
    original_requirements = "优化代码质量，修复安全漏洞"

    user_insights = {
        'focus_area': '代码质量',
        'concerns': '内存泄漏问题',
        'specific_files': ['main.py', 'utils.py'],
        'technical_questions': '如何优化性能？',
        'business_context': '这是一个Web应用项目',
        'time_constraint': '高',
        'quality_standard': '需要符合企业级标准',
        'fix_preference': '最小改动'
    }

    # 调用合并方法
    merged_requirements = coordinator._merge_user_insights_with_requirements(
        original_requirements, user_insights
    )

    print("=== 用户见解合并测试 ===")
    print(f"原始需求: {original_requirements}")
    print(f"用户见解: {user_insights}")
    print(f"\n合并后的需求:")
    print("=" * 50)
    print(merged_requirements)
    print("=" * 50)

    # 验证合并结果
    assert "优化代码质量，修复安全漏洞" in merged_requirements
    assert "代码质量" in merged_requirements
    assert "内存泄漏问题" in merged_requirements
    assert "main.py, utils.py" in merged_requirements
    assert "如何优化性能？" in merged_requirements
    assert "Web应用项目" in merged_requirements
    assert "高" in merged_requirements
    assert "企业级标准" in merged_requirements
    assert "最小改动" in merged_requirements

    print("\n✅ 测试通过：用户见解已正确合并到需求中")

if __name__ == "__main__":
    test_merge_user_insights()