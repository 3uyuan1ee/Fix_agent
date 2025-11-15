#!/usr/bin/env python3
"""
Fix Agent Web应用入口点

这个模块提供了web_app的Python入口点函数，
允许通过fixagent-web命令启动Web应用。
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# 添加src目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def start_web_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """启动Web应用服务器"""
    try:
        # 检查是否在正确的目录中
        web_app_dir = current_dir.parent / "web_app"
        if not web_app_dir.exists():
            print(f"❌ 错误: 找不到web_app目录 {web_app_dir}")
            return 1

        backend_dir = web_app_dir / "backend"
        if not backend_dir.exists():
            print(f"❌ 错误: 找不到backend目录 {backend_dir}")
            return 1

        print("🚀 启动 Fix Agent Web 应用...")
        print(f"📍 服务器地址: http://{host}:{port}")
        print(f"📚 API文档: http://{host}:{port}/docs")
        print("")

        # 构建uvicorn启动命令
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            str(host),
            "--port",
            str(port),
        ]

        if reload:
            cmd.append("--reload")
            print("🔄 启用热重载模式")

        print(f"🔧 执行命令: {' '.join(cmd)}")
        print(f"📂 工作目录: {backend_dir}")
        print("")

        # 切换到backend目录并启动服务器
        env = os.environ.copy()
        env["PYTHONPATH"] = str(current_dir.parent)

        process = subprocess.run(cmd, cwd=backend_dir, env=env, check=True)

        return process.returncode

    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败 (退出码: {e.returncode})")
        return e.returncode
    except KeyboardInterrupt:
        print("\n🛑 用户中断，正在停止服务器...")
        return 0
    except Exception as e:
        print(f"❌ 启动过程中发生错误: {e}")
        return 1


def cli_main():
    """web_app的CLI主入口点函数"""
    parser = argparse.ArgumentParser(
        prog="fixagent-web", description="启动Fix Agent Web应用服务器"
    )

    parser.add_argument(
        "--host", default="0.0.0.0", help="服务器监听地址 (默认: 0.0.0.0)"
    )

    parser.add_argument(
        "--port", "-p", type=int, default=8000, help="服务器端口号 (默认: 8000)"
    )

    parser.add_argument(
        "--reload", action="store_true", help="启用热重载模式 (开发模式)"
    )

    parser.add_argument("--version", action="version", version="Fix Agent Web 1.0.0")

    args = parser.parse_args()

    return start_web_server(host=args.host, port=args.port, reload=args.reload)


def web_main():
    """简化的web入口点"""
    return cli_main()


if __name__ == "__main__":
    sys.exit(cli_main())
