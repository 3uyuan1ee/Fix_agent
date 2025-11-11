"""打字机效果输出工具"""

import random
import time
from typing import Optional

from ..config.config import COLORS, DEEP_AGENTS_ASCII, console


class TypewriterPrinter:
    """打字机效果输出类"""

    def __init__(self):
        self.default_delay = 0.03
        self.fast_delay = 0.01
        self.slow_delay = 0.05

    def print_animated(
        self,
        text: str,
        style: str = "primary",
        delay: Optional[float] = None,
        end: str = "\n",
        same_line: bool = False,
    ):
        """
        以打字机效果输出文本

        Args:
            text: 要输出的文本
            style: 样式名称
            delay: 每个字符的延迟时间（秒）
            end: 结束字符
            same_line: 是否在同一行输出（使用回车符）
        """
        if delay is None:
            delay = self.default_delay

        final_style = COLORS.get(style, style)

        # 如果是同一行，使用回车符
        prefix = "\r" if same_line else ""

        for i in range(len(text) + 1):
            console.print(f"{prefix}{text[:i]}", style=final_style, end="")
            time.sleep(delay)

        # 输出结束字符
        if end:
            console.print(end, style=final_style, end="")

    def print_fast(self, text: str, style: str = "primary", end: str = "\n"):
        """快速打字机效果"""
        self.print_animated(text, style, self.fast_delay, end)

    def print_slow(self, text: str, style: str = "primary", end: str = "\n"):
        """慢速打字机效果"""
        self.print_animated(text, style, self.slow_delay, end)

    def print_with_random_speed(
        self, text: str, style: str = "primary", end: str = "\n"
    ):
        """随机速度打字机效果，模拟真实打字"""
        final_style = COLORS.get(style, style)
        for char in text:
            console.print(char, style=final_style, end="")
            # 随机延迟，模拟真实打字的不均匀速度
            delay = random.uniform(0.02, 0.08)
            time.sleep(delay)

        if end:
            console.print(end, style=final_style, end="")

    def print_clean_ascii(self, ascii_text: str, style: str = "primary"):
        """
        输出干净的ASCII艺术字（不应用打字机效果）
        用于处理包含ANSI转义码的预着色文本
        """
        console.print(ascii_text, style=COLORS.get(style, "primary"))

    def goodbye(self, message: Optional[str] = None, style: str = "primary"):
        """优雅的告别消息"""
        if message is None:
            messages = [
                "Goodbye! 👋",
                "Farewell, adventurer! ✨",
                "See you next time! 😊",
                "Until we meet again! 🙏",
                "Session ended. Thank you! ✅",
            ]
            message = random.choice(messages)
            style = random.choice(["primary", "success", "warning", "info"])

        console.print()  # 空行
        self.print_animated(message, style)
        console.print()  # 空行

    def welcome(
        self,
        ascii_art: str = DEEP_AGENTS_ASCII,
        welcome_text: str = "... Ready to code! What would you like to do?",
    ):
        """欢迎界面"""

        # 直接输出ASCII艺术字（不应用打字机效果，避免ANSI转义码问题）
        self.print_clean_ascii(ascii_art)
        console.print()

        # 输出欢迎文本（使用随机速度打字机效果）
        self.print_with_random_speed(welcome_text, style="agent")

    def warning(self, text: str):
        """警告消息"""
        self.print_animated(f"⚠ {text}", style="yellow")

    def error(self, text: str):
        """错误消息"""
        self.print_animated(f"❌ {text}", style="red")

    def success(self, text: str):
        """成功消息"""
        self.print_animated(f"✅ {text}", style="green")

    def info(self, text: str):
        """信息消息"""
        self.print_animated(f"ℹ {text}", style="blue")


# 创建全局实例
typewriter = TypewriterPrinter()
