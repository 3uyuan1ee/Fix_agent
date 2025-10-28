#!/usr/bin/env python3
"""
深度分析命令模块
实现`analyze deep`命令的处理逻辑，提供交互式对话界面
"""

import sys
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import threading

from ..utils.logger import get_logger
from ..utils.config import ConfigManager
from ..agent.orchestrator import AgentOrchestrator

logger = get_logger()


@dataclass
class ConversationMessage:
    """对话消息数据类"""
    role: str  # 'user' 或 'assistant'
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DeepAnalysisResult:
    """深度分析结果数据类"""
    success: bool
    target: str
    conversation: List[ConversationMessage]
    analysis_summary: str
    execution_time: float
    export_file: Optional[str] = None


class ConversationManager:
    """对话管理器"""

    def __init__(self, target: str):
        """初始化对话管理器"""
        self.target = target
        self.conversation: List[ConversationMessage] = []
        self.session = None
        self.start_time = time.time()
        self._lock = threading.Lock()

    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """添加对话消息"""
        with self._lock:
            message = ConversationMessage(
                role=role,
                content=content,
                metadata=metadata or {}
            )
            self.conversation.append(message)

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        with self._lock:
            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in self.conversation
            ]

    def export_conversation(self, file_path: str) -> bool:
        """导出对话历史"""
        try:
            export_data = {
                "target": self.target,
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "export_time": datetime.now().isoformat(),
                "conversation": self.get_conversation_history(),
                "message_count": len(self.conversation)
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            return True
        except Exception as e:
            logger.error(f"导出对话历史失败: {e}")
            return False


class ProgressIndicator:
    """进度指示器"""

    def __init__(self):
        """初始化进度指示器"""
        self.is_running = False
        self._thread = None
        self._stop_event = threading.Event()

    def start(self, message: str = "AI正在思考中"):
        """开始显示进度"""
        if self.is_running:
            return

        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._show_progress, args=(message,))
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        """停止显示进度"""
        if not self.is_running:
            return

        self.is_running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _show_progress(self, message: str):
        """显示进度动画"""
        symbols = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        idx = 0

        while not self._stop_event.is_set():
            symbol = symbols[idx % len(symbols)]
            sys.stdout.write(f'\r{symbol} {message}...')
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)

        # 清除进度行
        sys.stdout.write('\r' + ' ' * (len(message) + 10) + '\r')
        sys.stdout.flush()


class DeepAnalysisCommand:
    """深度分析命令处理器"""

    def __init__(self, config: Optional[ConfigManager] = None):
        """初始化深度分析命令处理器"""
        self.config = config or ConfigManager()
        self.orchestrator = AgentOrchestrator()
        self.progress = ProgressIndicator()

    def execute_deep_analysis(
        self,
        target: str,
        output_file: Optional[str] = None,
        verbose: bool = False,
        quiet: bool = False
    ) -> DeepAnalysisResult:
        """
        执行深度分析

        Args:
            target: 目标文件或目录路径
            output_file: 输出文件路径
            verbose: 详细模式
            quiet: 静默模式

        Returns:
            DeepAnalysisResult: 分析结果
        """
        start_time = time.time()
        target_path = Path(target)

        if not target_path.exists():
            raise FileNotFoundError(f"目标路径不存在: {target}")

        # 验证目标路径
        if not self._validate_target(target_path):
            return DeepAnalysisResult(
                success=False,
                target=target,
                conversation=[],
                analysis_summary="目标路径不是有效的Python文件或目录",
                execution_time=0
            )

        if not quiet:
            print(f"🔍 启动深度分析模式")
            print(f"📁 目标: {target}")
            print(f"💡 输入 '/help' 查看帮助，输入 '/exit' 退出分析")
            print("=" * 60)

        # 创建对话管理器
        conversation_manager = ConversationManager(target)

        # 创建会话
        session = self.orchestrator.create_session(user_id="deep_analysis_user")
        conversation_manager.session = session

        try:
            # 添加初始消息（内部使用，不显示给用户）
            initial_prompt = f"请对 {target} 进行深度分析，找出潜在的代码问题、改进建议和最佳实践。"
            conversation_manager.add_message("user", initial_prompt, metadata={"internal": True})

            # 执行初始分析
            if not quiet:
                print("🤖 AI正在分析代码...")
                self.progress.start("AI正在进行深度代码分析")

            try:
                result = self.orchestrator.process_user_input(session.session_id, initial_prompt)

                self.progress.stop()

                if result.get('success', False):
                    response = result.get('message', '分析完成')
                    conversation_manager.add_message("assistant", response)

                    if not quiet:
                        print(f"\n📊 分析结果:")
                        print(f"{response}")
                else:
                    error_msg = result.get('message', '分析失败')
                    conversation_manager.add_message("assistant", f"分析失败: {error_msg}")

                    if not quiet:
                        print(f"\n❌ 分析失败: {error_msg}")

            except Exception as e:
                self.progress.stop()
                error_msg = f"分析过程中发生错误: {e}"
                conversation_manager.add_message("assistant", error_msg)

                if not quiet:
                    print(f"\n❌ {error_msg}")

            # 进入交互式对话
            if not quiet:
                print(f"\n🗣️  现在可以与AI进行对话，了解更多分析细节")

            self._interactive_conversation(conversation_manager, quiet, verbose)

        finally:
            self.orchestrator.close_session(session.session_id)

        # 计算执行时间
        execution_time = time.time() - start_time

        # 生成分析摘要
        summary = self._generate_summary(conversation_manager)

        # 导出对话历史
        export_file = None
        if output_file:
            if conversation_manager.export_conversation(output_file):
                export_file = output_file
                if not quiet:
                    print(f"💾 对话历史已保存到: {output_file}")

        return DeepAnalysisResult(
            success=True,
            target=target,
            conversation=conversation_manager.conversation,
            analysis_summary=summary,
            execution_time=execution_time,
            export_file=export_file
        )

    def _validate_target(self, target_path: Path) -> bool:
        """验证目标路径"""
        if target_path.is_file():
            return target_path.suffix == '.py'
        elif target_path.is_dir():
            # 检查目录中是否包含Python文件
            return any(target_path.rglob('*.py'))
        return False

    def _interactive_conversation(
        self,
        conversation_manager: ConversationManager,
        quiet: bool,
        verbose: bool
    ):
        """交互式对话"""
        session = conversation_manager.session

        while True:
            try:
                # 获取用户输入
                if quiet:
                    user_input = input().strip()
                else:
                    user_input = input("deep-analysis> ").strip()

                if not user_input:
                    continue

                # 处理特殊命令
                if user_input.startswith('/'):
                    if self._handle_special_command(user_input, conversation_manager, quiet):
                        break
                    continue

                # 添加用户消息
                conversation_manager.add_message("user", user_input)

                # 显示进度
                if not quiet:
                    self.progress.start("AI正在思考")

                try:
                    # 处理用户输入
                    result = self.orchestrator.process_user_input(session.session_id, user_input)

                    self.progress.stop()

                    if result.get('success', False):
                        response = result.get('message', '处理完成')
                        conversation_manager.add_message("assistant", response)

                        if not quiet:
                            print(f"🤖 {response}")
                    else:
                        error_msg = result.get('message', '处理失败')
                        conversation_manager.add_message("assistant", f"处理失败: {error_msg}")

                        if not quiet:
                            print(f"❌ {error_msg}")

                except Exception as e:
                    self.progress.stop()
                    error_msg = f"处理过程中发生错误: {e}"
                    conversation_manager.add_message("assistant", error_msg)

                    if not quiet:
                        print(f"❌ {error_msg}")

            except KeyboardInterrupt:
                if not quiet:
                    print("\n使用 '/exit' 命令退出分析")
                continue
            except EOFError:
                break

    def _handle_special_command(
        self,
        command: str,
        conversation_manager: ConversationManager,
        quiet: bool
    ) -> bool:
        """处理特殊命令"""
        cmd = command.lower()

        if cmd == '/exit':
            if not quiet:
                print("👋 退出深度分析模式")
            return True
        elif cmd == '/help':
            self._show_help(quiet)
        elif cmd == '/history':
            self._show_history(conversation_manager, quiet)
        elif cmd.startswith('/export'):
            parts = cmd.split(maxsplit=1)
            if len(parts) == 2:
                file_path = parts[1]
                if conversation_manager.export_conversation(file_path):
                    if not quiet:
                        print(f"💾 对话历史已导出到: {file_path}")
                else:
                    if not quiet:
                        print(f"❌ 导出失败")
            else:
                if not quiet:
                    print("用法: /export <文件路径>")
        elif cmd == '/summary':
            summary = self._generate_summary(conversation_manager)
            if not quiet:
                print(f"📋 分析摘要:\n{summary}")
        else:
            if not quiet:
                print(f"❌ 未知命令: {command}")
                print("输入 '/help' 查看可用命令")

        return False

    def _show_help(self, quiet: bool):
        """显示帮助信息"""
        if quiet:
            return

        help_text = """
🤖 深度分析模式帮助

可用命令:
  /help      - 显示此帮助信息
  /exit      - 退出深度分析模式
  /history   - 显示对话历史摘要
  /export <文件路径> - 导出对话历史到文件
  /summary   - 显示分析摘要

使用提示:
  - 可以询问关于代码的具体问题
  - 可以请求修复建议或最佳实践
  - 可以询问代码的设计模式和架构
  - 支持多轮对话，AI会保持上下文
        """
        print(help_text)

    def _show_history(self, conversation_manager: ConversationManager, quiet: bool):
        """显示对话历史"""
        if quiet:
            return

        print(f"\n📜 对话历史 (共 {len(conversation_manager.conversation)} 条消息):")
        print("-" * 60)

        for i, msg in enumerate(conversation_manager.conversation, 1):
            role_icon = "👤" if msg.role == "user" else "🤖"
            timestamp = msg.timestamp.strftime("%H:%M:%S")
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content

            print(f"{role_icon} [{timestamp}] {content_preview}")

        print("-" * 60)

    def _generate_summary(self, conversation_manager: ConversationManager) -> str:
        """生成分析摘要"""
        if not conversation_manager.conversation:
            return "无对话记录"

        # 获取AI的回复
        ai_messages = [msg for msg in conversation_manager.conversation if msg.role == "assistant"]

        if not ai_messages:
            return "分析未完成"

        # 提取关键信息
        summary_parts = []
        summary_parts.append(f"对话轮次: {len(ai_messages)}")

        # 分析对话内容
        all_ai_content = " ".join([msg.content for msg in ai_messages])

        if "问题" in all_ai_content or "缺陷" in all_ai_content:
            summary_parts.append("发现了代码问题")
        if "建议" in all_ai_content or "推荐" in all_ai_content:
            summary_parts.append("提供了改进建议")
        if "安全" in all_ai_content:
            summary_parts.append("涉及安全相关问题")
        if "性能" in all_ai_content:
            summary_parts.append("涉及性能相关问题")

        return "，".join(summary_parts) if summary_parts else "深度分析已完成"