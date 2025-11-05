#!/usr/bin/env python3
"""
进度跟踪工具模块
提供分析进度显示和时间统计功能
"""

import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional


class ProgressTracker:
    """进度跟踪器"""

    def __init__(self, verbose: bool = False):
        """
        初始化进度跟踪器

        Args:
            verbose: 是否显示详细信息
        """
        self.verbose = verbose
        self.start_time = None
        self.current_step = 0
        self.total_steps = 0
        self.step_info = {}
        self.file_count = 0
        self.issue_count = 0

    def start(self, total_steps: int = 0):
        """开始进度跟踪"""
        self.start_time = time.time()
        self.total_steps = total_steps
        self.current_step = 0

        if not self.verbose:
            print("开始分析...")
        else:
            print(f"开始分析，预计 {total_steps} 个步骤")

    def step(self, description: str, current: int = None, total: int = None):
        """
        更新进度

        Args:
            description: 步骤描述
            current: 当前进度
            total: 总数
        """
        self.current_step += 1

        if total:
            self.total_steps = total

        if self.verbose:
            elapsed = time.time() - self.start_time if self.start_time else 0
            percent = (
                (self.current_step / self.total_steps * 100)
                if self.total_steps > 0
                else 0
            )
            print(f"[{percent:5.1f}%] {description} (耗时: {elapsed:.1f}s)")
        elif not self.verbose and self.total_steps > 0:
            # 简化进度显示
            percent = self.current_step / self.total_steps * 100
            bar_length = 30
            filled_length = int(bar_length * percent / 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            print(f"\r[{percent:5.1f}%] {bar}", end="", flush=True)

    def update_file_count(self, count: int):
        """更新文件计数"""
        self.file_count = count
        if self.verbose:
            print(f"正在处理第 {count} 个文件...")

    def update_issue_count(self, count: int):
        """更新问题计数"""
        self.issue_count = count
        if self.verbose and count > 0:
            print(f"已发现 {count} 个问题...")

    def finish(self):
        """完成进度跟踪"""
        if self.start_time:
            elapsed = time.time() - self.start_time
            if not self.verbose:
                print()  # 换行
            print(f"✅ 完成！总耗时: {elapsed:.2f}秒")

            if self.file_count > 0:
                print(f"📁 分析文件: {self.file_count} 个")
            if self.issue_count > 0:
                print(f"🔍 发现问题: {self.issue_count} 个")
        else:
            print("✅ 完成！")

    def show_file_progress(self, current_file: str, processed: int, total: int):
        """显示文件处理进度"""
        if total > 0:
            percent = processed / total * 100
            if self.verbose:
                print(f"[{percent:5.1f}%] 处理文件: {current_file}")
            else:
                bar_length = 20
                filled_length = int(bar_length * percent / 100)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                filename = (
                    Path(current_file).name if len(current_file) > 30 else current_file
                )
                print(f"\r[{percent:5.1f}%] {bar} {filename}", end="", flush=True)

    def log(self, message: str):
        """记录日志信息"""
        if self.verbose:
            print(f"  ℹ️  {message}")

    def warning(self, message: str):
        """记录警告信息"""
        print(f"  ⚠️  {message}")

    def error(self, message: str):
        """记录错误信息"""
        print(f"  ❌ {message}")

    def success(self, message: str):
        """记录成功信息"""
        print(f"  ✅ {message}")

    def get_summary(self) -> Dict[str, Any]:
        """获取分析摘要"""
        return {
            "total_files": self.file_count,
            "total_issues": self.issue_count,
            "total_time": time.time() - self.start_time if self.start_time else 0,
            "steps_completed": self.current_step,
            "total_steps": self.total_steps,
        }
