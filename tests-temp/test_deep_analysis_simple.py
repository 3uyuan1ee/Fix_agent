#!/usr/bin/env python3
"""
简单的深度分析功能测试脚本
"""

import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_deep_analysis():
    """测试深度分析功能"""
    print("🔍 测试深度分析功能...")

    try:
        from tools.deep_analyzer import DeepAnalyzer, DeepAnalysisRequest

        # 创建深度分析器
        analyzer = DeepAnalyzer()
        print("✅ DeepAnalyzer 初始化成功")

        # 测试文件读取
        test_file = "src/utils/config.py"
        if not Path(test_file).exists():
            print(f"❌ 测试文件不存在: {test_file}")
            return False

        # 创建分析请求
        request = DeepAnalysisRequest(
            file_path=test_file,
            analysis_type="comprehensive",
            user_instructions="请重点关注代码结构和错误处理"
        )

        print(f"🔍 开始分析文件: {test_file}")

        # 执行分析
        result = await analyzer.analyze_file(request)

        if result.success:
            print("✅ 深度分析成功")
            print(f"   - 分析文件: {result.file_path}")
            print(f"   - 分析类型: {result.analysis_type}")
            print(f"   - 使用模型: {result.model_used}")
            print(f"   - 执行时间: {result.execution_time:.2f}秒")
            print(f"   - 内容长度: {len(result.content)} 字符")

            # 显示部分分析内容
            if result.content:
                print(f"   - 分析内容预览: {result.content[:200]}...")

            # 检查结构化分析
            if result.structured_analysis:
                print(f"   - 结构化分析: {result.structured_analysis.get('format', 'unknown')}")

            return True
        else:
            print(f"❌ 深度分析失败: {result.error}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def main():
    """主函数"""
    import asyncio

    print("🚀 开始深度分析功能测试")
    print("=" * 50)

    # 运行异步测试
    success = asyncio.run(test_deep_analysis())

    print("\n" + "=" * 50)
    if success:
        print("🎉 深度分析功能测试通过！")
        return 0
    else:
        print("❌ 深度分析功能测试失败")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n用户中断测试")
        sys.exit(0)
    except Exception as e:
        print(f"\n测试异常: {e}")
        sys.exit(1)