#!/usr/bin/env python3
"""
测试日志修复效果
"""

def test_content_preview_logic():
    """测试内容预览逻辑"""

    # 模拟包含用户需求的长消息
    long_content_with_user_req = """# 文件选择任务

## 项目信息
- 项目路径: example
- 用户需求: 优化代码质量，修复安全漏洞

用户补充见解和需求:
- 重点关注领域: 代码质量
- 主要担忧: 内存泄漏问题
- 特定关注文件: main.py, utils.py
- 技术疑问: 如何优化性能？
- 业务背景: 这是一个Web应用项目，需要处理大量用户数据
- 时间约束: 高
- 质量标准: 需要符合企业级标准，代码覆盖率要达到80%以上
- 修复偏好: 最小改动

- 分析重点: 安全性, 性能

## 静态分析结果
发现严重问题，需要重点关注：
📁 main.py
  - severity: HIGH
  - message: 使用shell=True可能导致命令注入
  - line: 15
  - severity: MEDIUM
  - message: SQL注入风险
  - line: 23
  - severity: MEDIUM
  - message: 重新定义内置函数eval
  - line: 8
...

## 任务要求
基于以上信息，请选择需要重点分析的文件。
优先选择有安全风险、严重错误或核心业务逻辑的文件。
确保选择的文件覆盖最重要的问题。"""

    print("=== 测试日志截断修复效果 ===")
    print(f"原始内容长度: {len(long_content_with_user_req)} 字符")

    # 模拟原始的截断逻辑
    original_preview = long_content_with_user_req[:100] + "..." if len(long_content_with_user_req) > 100 else long_content_with_user_req
    print(f"\n原始截断效果:")
    print(f"  {original_preview}")

    # 模拟新的智能截断逻辑
    if "用户需求:" in long_content_with_user_req:
        user_req_start = long_content_with_user_req.find("用户需求:")
        user_req_end = long_content_with_user_req.find("\n", user_req_start)
        if user_req_end == -1:
            user_req_end = len(long_content_with_user_req)

        user_requirements_line = long_content_with_user_req[user_req_start:user_req_end]

        # 显示消息开头和完整的用户需求行
        if len(long_content_with_user_req) > 200:
            new_preview = long_content_with_user_req[:150] + "\n" + user_requirements_line + "\n" + "..." + long_content_with_user_req[-50:]
        else:
            new_preview = long_content_with_user_req
    else:
        new_preview = long_content_with_user_req[:100] + "..." if len(long_content_with_user_req) > 100 else long_content_with_user_req

    print(f"\n修复后的智能截断效果:")
    print(f"  {new_preview}")

    # 检查是否包含完整的用户需求信息
    contains_user_requirements = "用户需求: 优化代码质量，修复安全漏洞" in new_preview
    contains_user_insights = "重点关注领域: 代码质量" in new_preview

    print(f"\n=== 修复效果评估 ===")
    print(f"✅ 包含完整用户需求: {contains_user_requirements}")
    print(f"✅ 包含用户见解: {contains_user_insights}")
    print(f"✅ 避免重要信息截断: {contains_user_requirements and contains_user_insights}")

if __name__ == "__main__":
    test_content_preview_logic()