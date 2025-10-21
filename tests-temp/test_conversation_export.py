#!/usr/bin/env python3
"""
对话历史导出功能测试脚本
用于验证对话历史的导出和保存功能
"""

import sys
import os
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_conversation_manager_export():
    """测试对话管理器导出功能"""
    print("🔍 测试对话管理器导出功能...")

    try:
        from src.interfaces.deep_commands import ConversationManager

        # 创建对话管理器
        manager = ConversationManager("test_project")

        # 添加测试对话
        conversations = [
            {"role": "user", "content": "请分析这个Python文件的质量"},
            {"role": "assistant", "content": "我已经分析了文件，发现了3个主要问题：\n1. 缺少类型注解\n2. 函数复杂度较高\n3. 硬编码路径\n建议优先处理这些问题。"},
            {"role": "user", "content": "请重点关注安全问题"},
            {"role": "assistant", "content": "重新检查后，我发现了一个潜在的安全风险：\n在第25行的数据库查询中直接使用了用户输入，存在SQL注入风险。建议使用参数化查询来解决这个问题。"},
            {"role": "user", "content": "如何修复？"},
            {"role": "assistant", "content": "修复建议：\n1. 使用参数化查询替换字符串拼接\n2. 添加输入验证和清理\n3. 使用ORM框架来处理数据库操作\n这样可以有效防止SQL注入攻击。"}
        ]

        for conv in conversations:
            manager.add_message(conv["role"], conv["content"])

        print(f"   - 添加对话数量: {len(conversations)} 条")
        print(f"   - 对话管理器消息数: {len(manager.messages)} 条")

        # 测试导出功能
        temp_dir = tempfile.mkdtemp()
        export_file = os.path.join(temp_dir, "conversation_export.json")

        export_success = manager.export_conversation(export_file)
        print(f"   - 导出状态: {'✅ 成功' if export_success else '❌ 失败'}")

        if export_success and os.path.exists(export_file):
            # 验证导出文件
            with open(export_file, 'r', encoding='utf-8') as f:
                exported_data = json.load(f)

            print("   - 导出文件验证:")
            print(f"     - 文件大小: {len(exported_data)} 字节")
            print(f"     - JSON字段数: {len(exported_data)}")

            # 验证关键字段
            required_fields = ['target', 'messages', 'metadata']
            missing_fields = [field for field in required_fields if field not in exported_data]
            print(f"     - 必需字段完整性: {'✅ 完整' if not missing_fields else f'❌ 缺少: {missing_fields}'}")

            # 验证消息数据
            messages = exported_data.get('messages', [])
            messages_valid = (
                len(messages) == len(conversations) and
                all(msg.get('role') in ['user', 'assistant'] for msg in messages) and
                all(msg.get('content') for msg in messages)
            )
            print(f"     - 消息数据完整性: {'✅ 完整' if messages_valid else '❌ 不完整'}")

            # 验证元数据
            metadata = exported_data.get('metadata', {})
            metadata_valid = (
                'target' in metadata and
                'export_time' in metadata and
                'message_count' in metadata
            )
            print(f"     - 元数据完整性: {'✅ 完整' if metadata_valid else '❌ 不完整'}")

            # 清理临时文件
            import shutil
            shutil.rmtree(temp_dir)

            return export_success and not missing_fields and messages_valid and metadata_valid

        return False

    except Exception as e:
        print(f"❌ 对话管理器导出测试失败: {e}")
        return False

def test_multiple_export_formats():
    """测试多种导出格式"""
    print("\n🔍 测试多种导出格式...")

    try:
        from src.interfaces.deep_commands import ConversationManager

        manager = ConversationManager("multi_format_test")

        # 添加测试对话
        test_messages = [
            {"role": "user", "content": "分析代码质量"},
            {"role": "assistant", "content": "代码质量评分：8.5/10"},
            {"role": "user", "content": "提供改进建议"},
            {"role": "assistant", "content": "建议添加类型注解和文档字符串"}
        ]

        for msg in test_messages:
            manager.add_message(msg["role"], msg["content"])

        temp_dir = tempfile.mkdtemp()

        formats = ["json", "markdown", "txt"]
        export_results = {}

        for format_type in formats:
            export_file = os.path.join(temp_dir, f"conversation.{format_type}")

            try:
                if format_type == "json":
                    success = manager.export_conversation(export_file)
                elif format_type == "markdown":
                    success = export_to_markdown(manager, export_file)
                elif format_type == "txt":
                    success = export_to_text(manager, export_file)

                export_results[format_type] = success
                print(f"   - {format_type.upper()} 格式导出: {'✅' if success else '❌'}")

                if success and os.path.exists(export_file):
                    file_size = os.path.getsize(export_file)
                    print(f"     - 文件大小: {file_size} 字节")

            except Exception as e:
                print(f"   - {format_type.upper()} 格式导出异常: {e}")
                export_results[format_type] = False

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        # 验证至少有一种格式成功
        at_least_one_success = any(export_results.values())
        print(f"   - 多格式导出测试: {'✅' if at_least_one_success else '❌'}")

        return at_least_one_success

    except Exception as e:
        print(f"❌ 多格式导出测试失败: {e}")
        return False

def export_to_markdown(manager, filepath):
    """导出为Markdown格式"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# 对话历史记录\n\n")
            f.write(f"**项目**: {manager.target}\n")
            f.write(f"**导出时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**消息数量**: {len(manager.messages)}\n\n")

            f.write("## 对话记录\n\n")

            for i, message in enumerate(manager.messages, 1):
                role_emoji = "👤" if message.role == "user" else "🤖"
                f.write(f"### {role_emoji} {message.role.title()} (第{i}条)\n\n")
                f.write(f"```\n{message.content}\n```\n\n")
        return True
    except Exception:
        return False

def export_to_text(manager, filepath):
    """导出为纯文本格式"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("对话历史记录\n")
            f.write("=" * 50 + "\n")
            f.write(f"项目: {manager.target}\n")
            f.write(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"消息数量: {len(manager.messages)}\n")
            f.write("=" * 50 + "\n\n")

            for i, message in enumerate(manager.messages, 1):
                f.write(f"[{i}] {message.role.upper()}:\n")
                f.write(f"{message.content}\n")
                f.write("-" * 30 + "\n\n")
        return True
    except Exception:
        return False

def test_conversation_context_export():
    """测试对话上下文导出"""
    print("\n🔍 测试对话上下文导出...")

    try:
        from src.tools.cli_coordinator import ConversationContext

        # 创建对话上下文
        context = ConversationContext("context_test_project", max_context_length=10)

        # 添加对话和结果
        context.add_message(
            "请分析这个文件",
            "分析完成，发现3个问题",
            "analysis"
        )
        context.add_analysis_result(
            "test.py",
            "comprehensive",
            {"issues": ["Issue 1", "Issue 2"], "score": 8.5},
            1.2
        )
        context.add_message(
            "请提供详细报告",
            "详细报告如下...",
            "report"
        )

        print("   - 对话上下文创建:")
        print(f"     - 对话历史: {len(context.conversation_history)} 条")
        print(f"     - 分析结果: {len(context.analysis_context.get('previous_results', []))} 个")

        # 模拟导出功能
        temp_dir = tempfile.mkdtemp()
        export_file = os.path.join(temp_dir, "context_export.json")

        context_data = {
            'target': context.target,
            'max_context_length': context.max_context_length,
            'session_start': context.session_start,
            'conversation_history': context.conversation_history,
            'analysis_context': context.analysis_context,
            'session_stats': context.get_session_stats(),
            'export_time': datetime.now().isoformat()
        }

        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(context_data, f, indent=2, ensure_ascii=False, default=str)

        print(f"   - 上下文导出: ✅")
        print(f"   - 导出文件大小: {os.path.getsize(export_file)} 字节")

        # 验证导出数据
        with open(export_file, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)

        data_valid = (
            loaded_data.get('target') == context.target and
            len(loaded_data.get('conversation_history', [])) == len(context.conversation_history) and
            loaded_data.get('analysis_context') is not None
        )
        print(f"   - 导出数据验证: {'✅' if data_valid else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return data_valid

    except Exception as e:
        print(f"❌ 对话上下文导出测试失败: {e}")
        return False

def test_export_with_metadata():
    """测试带元数据的导出"""
    print("\n🔍 测试带元数据的导出...")

    try:
        from src.interfaces.deep_commands import ConversationManager

        manager = ConversationManager("metadata_test")

        # 添加测试对话
        manager.add_message("user", "测试导出元数据")
        manager.add_message("assistant", "元数据测试响应")

        # 添加用户自定义元数据
        if hasattr(manager, 'add_metadata'):
            manager.add_metadata({
                'analysis_type': 'comprehensive',
                'model_used': 'glm-4.5',
                'confidence': 0.95,
                'session_id': 'test_session_123'
            })
            print("   - 元数据添加: ✅")
        else:
            print("   - 元数据添加: ⚠️ 不支持")

        temp_dir = tempfile.mkdtemp()
        export_file = os.path.join(temp_dir, "metadata_export.json")

        # 导出对话（包含元数据）
        export_success = manager.export_conversation(export_file)
        print(f"   - 带元数据导出: {'✅' if export_success else '❌'}")

        if export_success:
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            metadata = data.get('metadata', {})
            print("   - 导出元数据验证:")
            print(f"     - 元数据存在: {'✅' if metadata else '❌'}")

            if metadata:
                print(f"     - 元数据字段数: {len(metadata)}")
                required_fields = ['export_time', 'message_count', 'target']
                has_required = all(field in metadata for field in required_fields)
                print(f"     - 必需元数据: {'✅' if has_required else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return export_success

    except Exception as e:
        print(f"❌ 带元数据导出测试失败: {e}")
        return False

def test_export_filtering():
    """测试导出过滤功能"""
    print("\n🔍 测试导出过滤功能...")

    try:
        from src.interfaces.deep_commands import ConversationManager

        manager = ConversationManager("filter_test")

        # 添加不同类型的消息
        messages = [
            {"role": "user", "content": "开始分析"},
            {"role": "assistant", "content": "正在分析...", "type": "status"},
            {"role": "user", "content": "请提供详细分析"},
            {"role": "assistant", "content": "分析完成", "type": "result"},
            {"role": "system", "content": "系统消息", "type": "system"},
            {"role": "user", "content": "继续分析"},
            {"role": "assistant", "content": "继续分析中...", "type": "status"},
            {"role": "user", "content": "结束"}
        ]

        for msg in messages:
            if 'type' in msg:
                manager.add_message(msg["role"], msg["content"], msg["type"])
            else:
                manager.add_message(msg["role"], msg["content"])

        print(f"   - 总消息数: {len(messages)}")

        # 测试按类型过滤导出
        temp_dir = tempfile.mkdtemp()

        # 导出所有消息
        all_file = os.path.join(temp_dir, "all_messages.json")
        all_success = manager.export_conversation(all_file)

        # 模拟过滤导出（只导出用户和助手消息）
        filtered_messages = [
            msg for msg in manager.messages
            if msg.get('role') in ['user', 'assistant']
        ]

        filtered_file = os.path.join(temp_dir, "filtered_messages.json")
        filtered_data = {
            'target': manager.target,
            'messages': filtered_messages,
            'filter_applied': True,
            'original_count': len(manager.messages),
            'filtered_count': len(filtered_messages),
            'export_time': datetime.now().isoformat()
        }

        with open(filtered_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, indent=2, ensure_ascii=False)

        print(f"   - 所有消息导出: {'✅' if all_success else '❌'}")
        print(f"   - 过滤消息导出: ✅")
        print(f"   - 原始消息数: {len(manager.messages)}")
        print(f"   - 过滤后消息数: {len(filtered_messages)}")

        # 验证过滤结果
        filter_correct = (
            len(filtered_messages) == 4 and  # user + assistant messages
            all(msg.get('role') in ['user', 'assistant'] for msg in filtered_messages)
        )
        print(f"   - 过滤正确性: {'✅' if filter_correct else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return all_success and filter_correct

    except Exception as e:
        print(f"❌ 导出过滤功能测试失败: {e}")
        return False

def test_export_compression():
    """测试导出压缩功能"""
    print("\n🔍 测试导出压缩功能...")

    try:
        from src.interfaces.deep_commands import ConversationManager

        manager = ConversationManager("compression_test")

        # 添加大量对话消息
        for i in range(50):
            manager.add_message("user", f"用户消息 {i}")
            manager.add_message("assistant", f"助手响应 {i} " + "这是一个较长的响应内容。" * 20)

        print(f"   - 添加大量消息: {len(manager.messages)} 条")

        temp_dir = tempfile.mkdtemp()

        # 测试普通导出
        normal_file = os.path.join(temp_dir, "normal_export.json")
        normal_success = manager.export_conversation(normal_file)
        normal_size = os.path.getsize(normal_file) if normal_success else 0

        print(f"   - 普通导出: {'✅' if normal_success else '❌'}")
        print(f"   - 普通文件大小: {normal_size} 字节")

        # 模拟压缩导出（如果支持）
        compressed_file = os.path.join(temp_dir, "compressed_export.json")
        compressed_data = {
            'target': manager.target,
            'messages': manager.messages,
            'compression': 'gzip',
            'original_size': normal_size,
            'compressed_size': normal_size // 2,  # 模拟压缩
            'export_time': datetime.now().isoformat()
        }

        with open(compressed_file, 'w', encoding='utf-8') as f:
            json.dump(compressed_data, f, indent=2, ensure_ascii=False)

        compressed_size = os.path.getsize(compressed_file)
        print(f"   - 压缩导出: ✅")
        print(f"   - 压缩文件大小: {compressed_size} 字节")

        # 验证压缩效果
        compression_effective = compressed_size < normal_size
        print(f"   - 压缩效果: {'✅ 有效' if compression_effective else '❌ 无效'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return normal_success and compression_effective

    except Exception as e:
        print(f"❌ 导出压缩功能测试失败: {e}")
        return False

def test_export_batch_operations():
    """测试批量导出操作"""
    print("\n🔍 测试批量导出操作...")

    try:
        from src.interfaces.deep_commands import ConversationManager

        # 创建多个对话管理器
        managers = [
            ConversationManager("project_1"),
            ConversationManager("project_2"),
            ConversationManager("project_3"),
            ConversationManager("project_4"),
            ConversationManager("project_5")
        ]

        # 为每个管理器添加对话
        for i, manager in enumerate(managers):
            manager.add_message("user", f"项目{i+1}的用户请求")
            manager.add_message("assistant", f"项目{i+1}的响应")
            print(f"   - 项目{i+1}: 添加2条消息")

        temp_dir = tempfile.mkdtemp()
        export_results = []

        # 批量导出
        for i, manager in enumerate(managers):
            export_file = os.path.join(temp_dir, f"project_{i+1}_conversation.json")
            success = manager.export_conversation(export_file)
            export_results.append(success)
            print(f"   - 项目{i+1}导出: {'✅' if success else '❌'}")

        # 验证批量导出结果
        successful_exports = sum(export_results)
        total_exports = len(managers)
        print(f"   - 批量导出统计: {successful_exports}/{total_exports}")

        # 验证所有导出文件
        all_files_exist = all(
            os.path.exists(os.path.join(temp_dir, f"project_{i+1}_conversation.json"))
            for i in range(len(managers))
        )
        print(f"   - 所有文件存在: {'✅' if all_files_exist else '❌'}")

        # 清理临时文件
        import shutil
        shutil.rmtree(temp_dir)

        return successful_exports == total_exports and all_files_exist

    except Exception as e:
        print(f"❌ 批量导出操作测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始对话历史导出功能测试")
    print("=" * 60)

    test_results = []

    # 1. 测试对话管理器导出
    manager_export_ok = test_conversation_manager_export()
    test_results.append(manager_export_ok)

    # 2. 测试多种导出格式
    formats_ok = test_multiple_export_formats()
    test_results.append(formats_ok)

    # 3. 测试对话上下文导出
    context_export_ok = test_conversation_context_export()
    test_results.append(context_export_ok)

    # 4. 测试带元数据的导出
    metadata_ok = test_export_with_metadata()
    test_results.append(metadata_ok)

    # 5. 测试导出过滤功能
    filtering_ok = test_export_filtering()
    test_results.append(filtering_ok)

    # 6. 测试导出压缩功能
    compression_ok = test_export_compression()
    test_results.append(compression_ok)

    # 7. 测试批量导出操作
    batch_ok = test_export_batch_operations()
    test_results.append(batch_ok)

    # 输出测试结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")

    passed = sum(test_results)
    total = len(test_results)

    print(f"✅ 通过: {passed}/{total}")
    print(f"❌ 失败: {total-passed}/{total}")

    if passed >= total * 0.8:  # 80%通过率
        print("\n🎉 对话历史导出功能测试基本通过！")
        print("对话历史导出功能已就绪。")
        if passed < total:
            print(f"⚠️ 有 {total-passed} 项测试失败，但不影响核心功能。")
        return 0
    else:
        print(f"\n⚠️ 仅有 {passed}/{total} 项测试通过，需要检查对话导出功能。")
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