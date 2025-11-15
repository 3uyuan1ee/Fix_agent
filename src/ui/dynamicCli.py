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

        # 构建输出内容
        output_text = f"{prefix}{text}"

        # 使用Rich的打字机效果
        console.print(output_text, style=final_style, end=end)

    def print_fast(self, text: str, style: str = "primary", end: str = "\n"):
        """快速打字机效果"""
        self.print_animated(text, style, self.fast_delay, end)

    def print_slow(self, text: str, style: str = "primary", end: str = "\n"):
        """慢速打字机效果"""
        self.print_animated(text, style, self.slow_delay, end)

    def print_with_random_speed(
        self, text: str, style: str = "primary", end: str = "\n"
    ):
        """使用Live的随机速度打字机效果"""
        from rich.live import Live

        final_style = COLORS.get(style, style)

        with Live("", console=console, refresh_per_second=20) as live:
            current_text = ""
            for char in text:
                current_text += char
                live.update(f"[{final_style}]{current_text}[/{final_style}]")
                # 随机延迟，模拟真实打字的不均匀速度
                delay = random.uniform(0.02, 0.08)
                time.sleep(delay)

        # 最后输出结束字符
        if end:
            console.print(end=end)

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
                "Goodbye! ",
                "See you next time! ",
                "Until we meet again! ",
                "Session ended. Thank you! ",
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
        self.print_animated(f"⚠ {text}", style="warning")

    def error(self, text: str):
        """错误消息"""
        self.print_animated(f"❌ {text}", style="red")

    def success(self, text: str):
        """成功消息"""
        self.print_animated(f"✅ {text}", style="green")

    def info(self, text: str):
        """信息消息"""
        self.print_animated(f"ℹ {text}", style="blue")

    def loading_progress(self, task_name: str = "处理中", duration: float = 2.0):
        """显示加载进度条动画"""
        from rich.progress import (BarColumn, Progress, SpinnerColumn,
                                   TaskProgressColumn, TextColumn)

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(task_name, total=100)

            for i in range(100):
                progress.update(task, advance=1)
                time.sleep(duration / 100)

    def typewriter_with_cursor(self, text: str, style: str = "primary"):
        """带光标的打字机效果"""
        from rich.live import Live

        final_style = COLORS.get(style, style)
        cursor_chars = [
            "▏",
            "▎",
            "▍",
            "▌",
            "▋",
            "▊",
            "▉",
            "█",
            "▉",
            "▊",
            "▋",
            "▌",
            "▍",
            "▎",
            "▏",
        ]
        cursor_index = 0

        with Live("", console=console, refresh_per_second=30) as live:
            current_text = ""
            for char in text:
                current_text += char
                cursor = cursor_chars[cursor_index % len(cursor_chars)]
                cursor_index += 1
                live.update(
                    f"[{final_style}]{current_text}[white]{cursor}[/{final_style}]"
                )
                time.sleep(0.05)

            # 完成后移除光标
            live.update(f"[{final_style}]{current_text}[/{final_style}]")

    def rainbow_text(self, text: str):
        """彩虹色文字效果"""
        from rich.live import Live
        from rich.text import Text

        colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]

        with Live(console=console, refresh_per_second=10) as live:
            for offset in range(len(colors) * 2):
                styled_text = Text()
                for i, char in enumerate(text):
                    color_index = (i + offset) % len(colors)
                    styled_text.append(char, style=colors[color_index])

                live.update(styled_text)
                time.sleep(0.3)

    def pulse_text(self, text: str, style: str = "primary", pulses: int = 3):
        """脉冲文字效果"""
        from rich.live import Live

        final_style = COLORS.get(style, style)

        with Live(console=console, refresh_per_second=20) as live:
            for pulse in range(pulses):
                # 淡入
                for alpha in range(0, 11):
                    opacity = alpha / 10
                    dimmed_style = f"{final_style} dim {int(opacity * 100)}%"
                    live.update(f"[{dimmed_style}]{text}[/{dimmed_style}]")
                    time.sleep(0.05)

                # 淡出
                for alpha in range(10, -1, -1):
                    opacity = alpha / 10
                    dimmed_style = f"{final_style} dim {int(opacity * 100)}%"
                    live.update(f"[{dimmed_style}]{text}[/{dimmed_style}]")
                    time.sleep(0.05)

    def typing_indicator(self, duration: float = 2.0):
        """显示"正在输入"指示器"""
        from rich.live import Live

        indicators = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

        with Live("", console=console, refresh_per_second=10) as live:
            start_time = time.time()
            while time.time() - start_time < duration:
                for indicator in indicators:
                    if time.time() - start_time >= duration:
                        break
                    live.update(f"[dim]正在输入{indicator}[/dim]")
                    time.sleep(0.1)

    def matrix_rain(self, text: str, style: str = "green"):
        """矩阵雨效果"""
        import random

        from rich.live import Live
        from rich.text import Text

        final_style = COLORS.get(style, style)

        with Live(console=console, refresh_per_second=15) as live:
            for step in range(20):
                lines = []
                for _ in range(5):
                    line = ""
                    for char in text:
                        if random.random() > 0.7:
                            line += random.choice("01")
                        else:
                            line += " "
                    lines.append(line)

                # 在最后一行显示实际文本
                lines.append(f"[{final_style}]{text}[/{final_style}]")

                live.update("\n".join(lines))
                time.sleep(0.1)

    def success_animation(self, message: str):
        """成功消息动画"""
        steps = ["   ○     ", "  ○○    ", " ○○○○   ", "○○○○○○○○", f"✅ {message}"]

        for step in steps:
            console.print(f"[green]{step}[/green]")
            time.sleep(0.2)
            # 清除上一行
            console.print("\r" + " " * 50 + "\r", end="")

    def error_shake(self, message: str):
        """错误消息震动效果"""
        from rich.live import Live

        shake_positions = ["", " ", "  ", "   ", "  ", " ", ""]

        with Live("", console=console, refresh_per_second=30) as live:
            # 震动效果
            for pos in shake_positions:
                live.update(f"[red]{pos}❌ {message}[/red]")
                time.sleep(0.05)

            # 最终显示
            time.sleep(0.5)
            live.update(f"[red]❌ {message}[/red]")

    def thinking_dots(self, text: str, style: str = "thinking", duration: float = 2.0):
        """思考中动画"""
        from rich.live import Live

        final_style = COLORS.get(style, style)

        with Live(console=console, refresh_per_second=2) as live:
            start_time = time.time()
            dot_count = 1
            while time.time() - start_time < duration:
                dots = "." * dot_count
                live.update(f"[{final_style}]{text}{dots}[/{final_style}]")
                dot_count = (dot_count % 3) + 1
                time.sleep(0.5)

    def slide_in_text(self, text: str, style: str = "primary", direction: str = "left"):
        """文字滑入效果"""
        from rich.live import Live

        final_style = COLORS.get(style, style)

        if direction == "left":
            # 从左边滑入
            with Live(console=console, refresh_per_second=30) as live:
                for i in range(len(text) + 1):
                    live.update(f"[{final_style}]{text[:i]}[/{final_style}]")
                    time.sleep(0.05)
        elif direction == "right":
            # 从右边滑入
            with Live(console=console, refresh_per_second=30) as live:
                for i in range(len(text) + 1):
                    padding = " " * (len(text) - i)
                    live.update(f"[{final_style}]{padding}{text[-i:]}[/{final_style}]")
                    time.sleep(0.05)

    def typewriter_effect_with_sound(self, text: str, style: str = "primary"):
        """模拟打字机声音效果（视觉模拟）"""
        from rich.live import Live

        final_style = COLORS.get(style, style)

        with Live(console=console, refresh_per_second=60) as live:
            current_text = ""
            for i, char in enumerate(text):
                current_text += char

                # 模拟打字机的视觉反馈
                if char == " ":
                    # 空格时短暂停顿
                    time.sleep(0.1)
                elif i % 5 == 0:
                    # 每5个字符有一个轻微的"卡顿"
                    time.sleep(0.08)
                else:
                    time.sleep(0.03)

                live.update(f"[{final_style}]{current_text}[/{final_style}]")


# 创建全局实例
typewriter = TypewriterPrinter()
