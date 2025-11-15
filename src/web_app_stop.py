#!/usr/bin/env python3
"""
Fix Agent Web应用停止工具

这个模块提供了停止Fix Agent Web应用的功能，
允许通过fixagent-web-stop命令停止正在运行的服务器。
"""

import argparse
import subprocess
import sys
from pathlib import Path

import psutil


def stop_web_servers():
    """停止所有Fix Agent Web服务器"""
    stopped_count = 0

    try:
        # 查找所有运行中的uvicorn进程
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", [])
                if not cmdline:
                    continue

                # 检查是否是我们的uvicorn进程
                if (
                    len(cmdline) >= 3
                    and cmdline[0].endswith("python")
                    and cmdline[1] == "-m"
                    and cmdline[2] == "uvicorn"
                    and any("main:app" in arg for arg in cmdline)
                ):

                    pid = proc.info["pid"]
                    print(f"🛑 正在停止Fix Agent Web服务器 (PID: {pid})")

                    # 优雅地停止进程
                    proc.terminate()

                    try:
                        proc.wait(timeout=5)
                        print(f"✅ 服务器已停止 (PID: {pid})")
                        stopped_count += 1
                    except psutil.TimeoutExpired:
                        # 如果优雅停止失败，强制停止
                        print(f"⚡ 强制停止服务器 (PID: {pid})")
                        proc.kill()
                        stopped_count += 1

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    except Exception as e:
        print(f"❌ 停止服务器时发生错误: {e}")
        return 1

    if stopped_count == 0:
        print("ℹ️  没有找到运行中的Fix Agent Web服务器")
    else:
        print(f"✅ 成功停止了 {stopped_count} 个服务器")

    return 0


def stop_by_port(port):
    """通过端口号停止服务器"""
    try:
        # 查找占用指定端口的进程
        for proc in psutil.process_iter(["pid", "name", "connections"]):
            try:
                connections = proc.info.get("connections", [])
                for conn in connections:
                    if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:

                        pid = proc.info["pid"]
                        print(f"🛑 正在停止占用端口 {port} 的服务器 (PID: {pid})")

                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                            print(f"✅ 服务器已停止 (PID: {pid})")
                            return 0
                        except psutil.TimeoutExpired:
                            print(f"⚡ 强制停止服务器 (PID: {pid})")
                            proc.kill()
                            return 0

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        print(f"ℹ️  没有找到占用端口 {port} 的服务器")
        return 0

    except Exception as e:
        print(f"❌ 停止服务器时发生错误: {e}")
        return 1


def list_web_servers():
    """列出所有运行中的Web服务器"""
    found = False

    try:
        print("🔍 搜索运行中的Fix Agent Web服务器...")
        print("")

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", [])
                if not cmdline:
                    continue

                # 检查是否是我们的uvicorn进程
                if (
                    len(cmdline) >= 3
                    and cmdline[0].endswith("python")
                    and cmdline[1] == "-m"
                    and cmdline[2] == "uvicorn"
                    and any("main:app" in arg for arg in cmdline)
                ):

                    found = True
                    pid = proc.info["pid"]

                    # 获取端口信息
                    ports = []
                    try:
                        connections = proc.connections()
                        for conn in connections:
                            if conn.status == psutil.CONN_LISTEN:
                                ports.append(conn.laddr.port)
                    except (psutil.AccessDenied, psutil.NoSuchProcess):
                        pass

                    ports_str = (
                        ", ".join(f":{port}" for port in ports) if ports else "未知"
                    )
                    print(f"📡 Fix Agent Web服务器")
                    print(f"   PID: {pid}")
                    print(f"   端口: {ports_str}")
                    print(f"   命令: {' '.join(cmdline[:4])}...")
                    print("")

            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not found:
            print("ℹ️  没有找到运行中的Fix Agent Web服务器")

    except Exception as e:
        print(f"❌ 列出服务器时发生错误: {e}")
        return 1

    return 0


def cli_main():
    """停止Web应用的CLI主入口点函数"""
    parser = argparse.ArgumentParser(
        prog="fixagent-web-stop", description="停止Fix Agent Web应用服务器"
    )

    parser.add_argument("--port", "-p", type=int, help="停止占用指定端口的服务器")

    parser.add_argument(
        "--list", "-l", action="store_true", help="列出所有运行中的Web服务器"
    )

    parser.add_argument(
        "--version", action="version", version="Fix Agent Web Stop 1.0.0"
    )

    args = parser.parse_args()

    if args.list:
        return list_web_servers()
    elif args.port:
        return stop_by_port(args.port)
    else:
        return stop_web_servers()


if __name__ == "__main__":
    sys.exit(cli_main())
