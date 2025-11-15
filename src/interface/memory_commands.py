"""记忆管理命令 - /memory 命令集"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from ..config.config import COLORS, console


def safe_get_content(memory_item) -> str:
    """安全地从记忆项中获取内容，支持字典和Message对象"""
    if hasattr(memory_item, "content"):
        # LangChain Message对象
        return memory_item.content
    elif hasattr(memory_item, "get"):
        # 字典对象
        return memory_item.get("content", "")
    else:
        # 字符串或其他对象
        return str(memory_item)


def safe_get_attribute(memory_item, attr_name: str, default=None):
    """安全地从记忆项中获取属性，支持字典和Message对象"""
    if hasattr(memory_item, attr_name):
        return getattr(memory_item, attr_name)
    elif hasattr(memory_item, "get"):
        return memory_item.get(attr_name, default)
    else:
        return default


class MemoryManager:
    """记忆管理器"""

    def __init__(self, assistant_id: str):
        self.assistant_id = assistant_id
        self.agent_dir = Path.home() / ".deepagents" / assistant_id
        self.agent_dir.mkdir(parents=True, exist_ok=True)

        # 记忆文件路径
        self.agent_memory_file = self.agent_dir / "agent.md"
        self.memories_dir = self.agent_dir / "memories"
        self.memories_dir.mkdir(parents=True, exist_ok=True)

        # 分层记忆文件
        self.semantic_memory_file = self.memories_dir / "semantic_memory.json"
        self.episodic_memory_file = self.memories_dir / "episodic_memory.json"

    def read_agent_memory(self) -> str:
        """读取agent主记忆文件"""
        if self.agent_memory_file.exists():
            return self.agent_memory_file.read_text(encoding="utf-8")
        return ""

    def write_agent_memory(self, content: str) -> bool:
        """写入agent主记忆文件"""
        try:
            # 创建备份
            self._create_backup(self.agent_memory_file)

            # 写入新内容
            self.agent_memory_file.write_text(content, encoding="utf-8")
            return True
        except Exception as e:
            console.print(f"[red]❌ 写入记忆失败: {e}[/red]")
            return False

    def read_semantic_memory(self) -> List[Dict]:
        """读取语义记忆"""
        if self.semantic_memory_file.exists():
            try:
                content = self.semantic_memory_file.read_text(encoding="utf-8")
                if content.strip():
                    return json.loads(content)
            except json.JSONDecodeError:
                console.print("[yellow]⚠️ 语义记忆文件格式错误，尝试修复...[/yellow]")
                return self._repair_json_file(self.semantic_memory_file)
        return []

    def write_semantic_memory(self, memories: List[Dict]) -> bool:
        """写入语义记忆"""
        try:
            # 创建备份
            self._create_backup(self.semantic_memory_file)

            # 写入记忆
            self.semantic_memory_file.write_text(
                json.dumps(memories, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return True
        except Exception as e:
            console.print(f"[red]❌ 写入语义记忆失败: {e}[/red]")
            return False

    def read_episodic_memory(self) -> List[Dict]:
        """读取情节记忆"""
        if self.episodic_memory_file.exists():
            try:
                content = self.episodic_memory_file.read_text(encoding="utf-8")
                if content.strip():
                    return json.loads(content)
            except json.JSONDecodeError:
                console.print("[yellow]⚠️ 情节记忆文件格式错误，尝试修复...[/yellow]")
                return self._repair_json_file(self.episodic_memory_file)
        return []

    def write_episodic_memory(self, memories: List[Dict]) -> bool:
        """写入情节记忆"""
        try:
            # 创建备份
            self._create_backup(self.episodic_memory_file)

            # 写入记忆
            self.episodic_memory_file.write_text(
                json.dumps(memories, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return True
        except Exception as e:
            console.print(f"[red]❌ 写入情节记忆失败: {e}[/red]")
            return False

    def _create_backup(self, file_path: Path) -> None:
        """创建文件备份"""
        try:
            if file_path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = (
                    file_path.parent
                    / f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
                )
                shutil.copy2(file_path, backup_path)
        except Exception:
            pass  # 备份失败不影响主要功能

    def _repair_json_file(self, file_path: Path) -> List[Dict]:
        """修复损坏的JSON文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 简单的JSON修复
            # 尝试移除常见的JSON错误
            content = content.replace(",,", ",")
            content = content.replace(",}", "}")

            # 尝试解析修复后的内容
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                console.print(
                    f"[yellow]⚠️ 无法修复文件 {file_path.name}，返回空列表[/yellow]"
                )
                return []
        except Exception:
            return []

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        agent_content = self.read_agent_memory()
        semantic_count = len(self.read_semantic_memory())
        episodic_count = len(self.read_episodic_memory())

        return {
            "agent_memory_size": len(agent_content),
            "agent_memory_lines": (
                len(agent_content.splitlines()) if agent_content else 0
            ),
            "semantic_memory_count": semantic_count,
            "episodic_memory_count": episodic_count,
            "total_memories": semantic_count + episodic_count,
            "memory_dir": str(self.memories_dir),
            "last_modified": datetime.now().isoformat(),
        }

    def search_memories(self, query: str, memory_type: str = "all") -> Dict[str, Any]:
        """搜索记忆内容"""
        results = {"agent_memory": [], "semantic_memory": [], "episodic_memory": []}

        query_lower = query.lower()

        # 搜索agent记忆
        if memory_type in ["agent", "all"]:
            agent_content = self.read_agent_memory()
            if query_lower in agent_content.lower():
                lines = agent_content.splitlines()
                for i, line in enumerate(lines, 1):
                    if query_lower in line.lower():
                        results["agent_memory"].append(
                            {"line": i, "content": line.strip(), "type": "agent_memory"}
                        )

        # 搜索语义记忆
        if memory_type in ["semantic", "all"]:
            semantic_memories = self.read_semantic_memory()
            for memory in semantic_memories:
                content = safe_get_content(memory)
                if query_lower in content.lower():
                    results["semantic_memory"].append(
                        {
                            "timestamp": safe_get_attribute(memory, "timestamp"),
                            "content": content,
                            "importance": safe_get_attribute(memory, "importance", 1.0),
                            "type": "semantic_memory",
                        }
                    )

        # 搜索情节记忆
        if memory_type in ["episodic", "all"]:
            episodic_memories = self.read_episodic_memory()
            for memory in episodic_memories:
                content = safe_get_content(memory)
                if query_lower in content.lower():
                    results["episodic_memory"].append(
                        {
                            "timestamp": safe_get_attribute(memory, "timestamp"),
                            "content": content,
                            "importance": safe_get_attribute(memory, "importance", 0.8),
                            "type": "episodic_memory",
                        }
                    )

        return results

    def export_memories(self, export_path: Optional[str] = None) -> str:
        """导出所有记忆到文件"""
        if not export_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_path = f"memory_export_{timestamp}.json"

        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "assistant_id": self.assistant_id,
            "export_version": "1.0",
            "stats": self.get_memory_stats(),
            "agent_memory": self.read_agent_memory(),
            "semantic_memory": self.read_semantic_memory(),
            "episodic_memory": self.read_episodic_memory(),
        }

        try:
            export_path = Path(export_path)
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            console.print(f"[green]✅ 记忆已导出到: {export_path}[/green]")
            return str(export_path)
        except Exception as e:
            console.print(f"[red]❌ 导出失败: {e}[/red]")
            return ""

    def import_memories(self, import_path: str) -> bool:
        """从文件导入记忆"""
        try:
            import_path = Path(import_path)
            if not import_path.exists():
                console.print(f"[red]❌ 导入文件不存在: {import_path}[/red]")
                return False

            with open(import_path, "r", encoding="utf-8") as f:
                import_data = json.load(f)

            # 验证导入数据格式
            required_fields = ["agent_memory", "semantic_memory", "episodic_memory"]
            if not all(field in import_data for field in required_fields):
                console.print(f"[red]❌ 导入文件格式不正确[/red]")
                return False

            # 导入记忆数据
            success = True
            success &= self.write_agent_memory(import_data.get("agent_memory", ""))
            success &= self.write_semantic_memory(
                import_data.get("semantic_memory", [])
            )
            success &= self.write_episodic_memory(
                import_data.get("episodic_memory", [])
            )

            if success:
                console.print(f"[green]✅ 记忆已从 {import_path} 导入[/green]")
                agent_memory_content = import_data.get("agent_memory", "")
                console.print(f"   - Agent记忆: {len(agent_memory_content)} 字符")
                console.print(
                    f"   - 语义记忆: {len(import_data.get('semantic_memory', []))} 条"
                )
                console.print(
                    f"   - 情节记忆: {len(import_data.get('episodic_memory', []))} 条"
                )

            return success
        except Exception as e:
            console.print(f"[red]❌ 导入失败: {e}[/red]")
            return False

    def list_memory_files(self) -> List[Dict[str, Any]]:
        """列出所有记忆相关文件"""
        files = []

        # 主记忆文件
        if self.agent_memory_file.exists():
            files.append(
                {
                    "name": "agent.md",
                    "type": "主记忆",
                    "path": str(self.agent_memory_file),
                    "size": self.agent_memory_file.stat().st_size,
                    "modified": datetime.fromtimestamp(
                        self.agent_memory_file.stat().st_mtime
                    ).isoformat(),
                }
            )

        # 分层记忆文件
        for file_path in [self.semantic_memory_file, self.episodic_memory_file]:
            if file_path.exists():
                files.append(
                    {
                        "name": file_path.name,
                        "type": "分层记忆",
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat(),
                    }
                )

        # 备份文件
        for file_path in self.agent_dir.rglob("*_backup_*.md"):
            if file_path.is_file():
                files.append(
                    {
                        "name": file_path.name,
                        "type": "备份文件",
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat(),
                    }
                )

        return sorted(files, key=lambda x: x["modified"], reverse=True)


def handle_memory_command(args: List[str]) -> bool:
    """处理 /memory 命令"""
    if not args:
        # 显示记忆管理主菜单
        show_memory_menu()
        return True

    # 获取assistant_id
    try:
        from agents.agent import get_current_assistant_id

        assistant_id = get_current_assistant_id()
    except ImportError:
        console.print("[red]❌ 无法获取当前assistant ID[/red]")
        return False

    memory_manager = MemoryManager(assistant_id)
    command = args[0]

    if command == "edit":
        return handle_memory_edit(memory_manager, args[1:])
    elif command == "view":
        return handle_memory_view(memory_manager, args[1:])
    elif command == "search":
        return handle_memory_search(memory_manager, args[1:])
    elif command == "stats":
        return handle_memory_stats(memory_manager)
    elif command == "export":
        return handle_memory_export(memory_manager, args[1:])
    elif command == "import":
        return handle_memory_import(memory_manager, args[1:])
    elif command == "list":
        return handle_memory_list(memory_manager)
    elif command == "backup":
        return handle_memory_backup(memory_manager)
    elif command == "restore":
        return handle_memory_restore(memory_manager, args[1:])
    elif command == "clear":
        return handle_memory_clear(memory_manager, args[1:])
    else:
        console.print(f"[red]❌ 未知的记忆命令: {command}[/red]")
        show_memory_menu()
        return True


def show_memory_menu():
    """显示记忆管理主菜单"""
    menu_text = """
# 🧠 Fix Agent 记忆管理系统

## 可用命令

### 📝 记忆编辑
- `/memory edit` - 使用编辑器编辑Agent主记忆
- `/memory edit agent.md` - 编辑指定的记忆文件

### 👁 记忆查看
- `/memory view` - 查看所有记忆概览
- `/memory view agent.md` - 查看指定记忆文件
- `/memory view semantic` - 查看语义记忆
- `/memory view episodic` - 查看情节记忆

### 🔍 记忆搜索
- `/memory search <关键词>` - 搜索所有类型的记忆
- `/memory search <关键词> agent` - 只搜索Agent记忆
- `/memory search <关键词> semantic` - 只搜索语义记忆
- `/memory search <关键词> episodic` - 只搜索情节记忆

### 📊 记忆统计
- `/memory stats` - 显示记忆使用统计

### 💾 导入导出
- `/memory export` - 导出所有记忆到JSON文件
- `/memory export <文件路径>` - 导出到指定路径
- `/memory import <文件路径>` - 从JSON文件导入记忆

### 📁 文件管理
- `/memory list` - 列出所有记忆相关文件
- `/memory backup` - 创建记忆备份
- `/memory restore <备份文件>` - 从备份恢复
- `/memory clear` - 清空指定类型的记忆

## 🎯 使用示例

### 编辑记忆
```bash
/memory edit                    # 编辑主记忆
/memory edit agent.md             # 使用指定编辑器
/memory edit semantic_memory.json   # 编辑语义记忆
```

### 查看记忆
```bash
/memory view                    # 查看所有记忆
/memory view agent.md             # 查看主记忆文件
/memory view semantic              # 查看语义记忆列表
```

### 搜索记忆
```bash
/memory search Python            # 搜索包含"Python"的记忆
/memory search "bug fix" semantic   # 在语义记忆中搜索
```

### 导出导入
```bash
/memory export                   # 导出当前时间戳的文件
/memory export backup_2024.json     # 导出到指定文件
/memory import backup_2024.json     # 从文件导入记忆
```
"""

    console.print(Panel(menu_text, title="🧠 记忆管理帮助", border_style="blue"))


def handle_memory_edit(memory_manager: MemoryManager, args: List[str]) -> bool:
    """处理记忆编辑命令"""
    if args:
        file_name = args[0]

        if file_name == "agent.md":
            edit_agent_memory(memory_manager)
        elif file_name == "semantic_memory.json":
            edit_semantic_memory(memory_manager)
        elif file_name == "episodic_memory.json":
            edit_episodic_memory(memory_manager)
        else:
            console.print(f"[red]❌ 未知的记忆文件: {file_name}[/red]")
            console.print(
                "可用的文件名: agent.md, semantic_memory.json, episodic_memory.json"
            )
    else:
        # 显示可编辑的文件列表
        show_editable_files(memory_manager)

    return True


def show_editable_files(memory_manager: MemoryManager):
    """显示可编辑的文件列表"""
    files = [
        {
            "name": "agent.md",
            "description": "Agent主记忆文件",
            "type": "主记忆",
            "size": (
                memory_manager.agent_memory_file.stat().st_size
                if memory_manager.agent_memory_file.exists()
                else 0
            ),
        },
        {
            "name": "semantic_memory.json",
            "description": "语义记忆（概念、规则、偏好）",
            "type": "分层记忆",
            "size": (
                memory_manager.semantic_memory_file.stat().st_size
                if memory_manager.semantic_memory_file.exists()
                else 0
            ),
        },
        {
            "name": "episodic_memory.json",
            "description": "情节记忆（重要事件、对话）",
            "type": "分层记忆",
            "size": (
                memory_manager.episodic_memory_file.stat().st_size
                if memory_manager.episodic_memory_file.exists()
                else 0
            ),
        },
    ]

    table = Table(title="📝 可编辑的记忆文件")
    table.add_column("文件名", style="cyan")
    table.add_column("类型", style="magenta")
    table.add_column("描述", style="green")
    table.add_column("大小", style="blue")

    for file_info in files:
        size_text = f"{file_info['size']} bytes"
        table.add_row(
            file_info["name"], file_info["type"], file_info["description"], size_text
        )

    console.print(table)

    console.print("\n[dim]使用方法: /memory edit <文件名>[/dim]")
    console.print("[dim]例如: /memory edit agent.md[/dim]")


def edit_agent_memory(memory_manager: MemoryManager):
    """编辑Agent主记忆"""
    console.print("[bold blue]📝 编辑Agent主记忆[/bold blue]")

    current_content = memory_manager.read_agent_memory()

    # 获取编辑器偏好
    editor = os.environ.get("EDITOR", "nano")  # 默认使用nano

    # 检查编辑器可用性
    if not shutil.which(editor):
        console.print(f"[yellow]⚠ 编辑器 '{editor}' 不可用，使用默认编辑器[/yellow]")
        editor = "nano"

    # 写入临时文件
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as temp_file:
        temp_file.write(current_content)
        temp_path = temp_file.name

    # 启动编辑器
    console.print(f"[dim]使用编辑器: {editor}[/dim]")
    os.system(f"{editor} {temp_path}")

    # 读取编辑后的内容
    try:
        new_content = Path(temp_path).read_text(encoding="utf-8")

        # 检查内容是否有变化
        if new_content != current_content:
            if memory_manager.write_agent_memory(new_content):
                console.print("[green]✅ Agent记忆已更新[/green]")

                # 显示内容统计
                line_count = len(new_content.splitlines())
                char_count = len(new_content)
                console.print(
                    f"[dim]更新内容: {line_count} 行, {char_count} 字符[/dim]"
                )
            else:
                console.print("[yellow]⚠️ 内容没有变化，保持原样[/yellow]")
        else:
            console.print("[blue]ℹ️ 内容没有变化，保持原样[/blue]")
    except Exception as e:
        console.print(f"[red]❌ 读取编辑器内容失败: {e}[/red]")
    finally:
        # 清理临时文件
        try:
            os.unlink(temp_path)
        except Exception:
            pass


def edit_semantic_memory(memory_manager: MemoryManager):
    """编辑语义记忆"""
    console.print("[bold blue]🧠 编辑语义记忆[/bold blue]")

    current_memories = memory_manager.read_semantic_memory()

    # 显示当前语义记忆概览
    if current_memories:
        table = Table(title="📊 当前语义记忆概览")
        table.add_column("序号", style="cyan")
        table.add_column("内容预览", style="green")
        table.add_column("重要性", style="magenta")
        table.add_column("时间", style="blue")

        for i, memory in enumerate(current_memories[:10], 1):
            content = safe_get_content(memory)
            content_preview = content[:50]
            if len(content) > 50:
                content_preview += "..."
            importance = safe_get_attribute(memory, "importance", 1.0)
            timestamp = safe_get_attribute(memory, "timestamp", 0)

            table.add_row(
                i,
                content_preview,
                f"{importance:.2f}",
                datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)

        if len(current_memories) > 10:
            console.print(
                f"[dim]还有 {len(current_memories) - 10} 条语义记忆未显示[/dim]"
            )

    console.print("\n[dim]语义记忆包含: 概念、规则、用户偏好等长期知识[/dim]")
    console.print("[dim]使用 'vs code <文件名>' 或其他编辑器编辑原始JSON文件[/dim]")

    # 直接编辑JSON文件
    file_path = memory_manager.semantic_memory_file
    editor = os.environ.get("EDITOR", "nano")

    if not shutil.which(editor):
        console.print(f"[yellow]⚠ 编辑器 '{editor}' 不可用，使用nano[/yellow]")
        editor = "nano"

    console.print(f"[dim]使用编辑器: {editor} {file_path}[/dim]")
    os.system(f"{editor} {file_path}")


def edit_episodic_memory(memory_manager: MemoryManager):
    """编辑情节记忆"""
    console.print("[bold blue]🧠 编辑情节记忆[/bold blue]")

    current_memories = memory_manager.read_episodic_memory()

    # 显示当前情节记忆概览
    if current_memories:
        table = Table(title="📊 当前情节记忆概览")
        table.add_column("序号", style="cyan")
        table.add_column("内容预览", style="green")
        table.add_column("重要性", style="magenta")
        table.add_column("时间", style="blue")

        for i, memory in enumerate(current_memories[:10], 1):
            content = safe_get_content(memory)
            content_preview = content[:50]
            if len(content) > 50:
                content_preview += "..."
            importance = safe_get_attribute(memory, "importance", 0.8)
            timestamp = safe_get_attribute(memory, "timestamp", 0)

            table.add_row(
                i,
                content_preview,
                f"{importance:.2f}",
                datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M"),
            )

        console.print(table)

        if len(current_memories) > 10:
            console.print(
                f"[dim]还有 {len(current_memories) - 10} 条情节记忆未显示[/dim]"
            )

    console.print("\n[dim]情节记忆包含: 重要事件、具体对话、交互记录[/dim]")
    console.print("[dim]使用 'vs code <文件名>' 或其他编辑器编辑原始JSON文件[/dim]")

    # 直接编辑JSON文件
    file_path = memory_manager.episodic_memory_file
    editor = os.environ.get("EDITOR", "nano")

    if not shutil.which(editor):
        console.print(f"[yellow]⚠ 编辑器 '{editor}' 不可用，使用nano[/yellow]")
        editor = "nano"

    console.print(f"[dim]使用编辑器: {editor} {file_path}[/dim]")
    os.system(f"{editor} {file_path}")


def handle_memory_view(memory_manager: MemoryManager, args: List[str]) -> bool:
    """处理记忆查看命令"""
    if args:
        file_name = args[0]

        if file_name == "agent.md":
            view_agent_memory(memory_manager)
        elif file_name == "semantic":
            view_semantic_memory(memory_manager)
        elif file_name == "episodic":
            view_episodic_memory(memory_manager)
        else:
            # 尝试作为文件路径
            view_memory_file(memory_manager, file_name)
    else:
        # 显示所有记忆概览
        view_all_memories(memory_manager)

    return True


def view_agent_memory(memory_manager: MemoryManager):
    """查看Agent主记忆"""
    console.print("[bold blue]📖 Agent主记忆内容[/bold blue]")

    content = memory_manager.read_agent_memory()

    if not content:
        console.print("[yellow]⚠ Agent主记忆为空[/yellow]")
        return

    # 显示内容统计
    lines = content.splitlines()
    chars = len(content)
    words = len(content.split())

    console.print(f"[dim]统计: {lines} 行, {chars} 字符, {words} 词[/dim]")
    console.print()

    # 显示内容
    console.print(Panel(content, title="Agent主记忆", border_style="blue"))


def view_semantic_memory(memory_manager: MemoryManager):
    """查看语义记忆"""
    console.print("[bold blue]🧠 语义记忆内容[/bold blue]")

    memories = memory_manager.read_semantic_memory()

    if not memories:
        console.print("[yellow]⚠ 语义记忆为空[/yellow]")
        return

    table = Table(title="🧠 语义记忆列表")
    table.add_column("序号", style="cyan")
    table.add_column("内容", style="green")
    table.add_column("重要性", style="magenta")
    table.add_column("时间", style="blue")

    for i, memory in enumerate(memories, 1):
        content = safe_get_content(memory)
        importance = safe_get_attribute(memory, "importance", 1.0)
        timestamp = safe_get_attribute(memory, "timestamp", 0)

        table.add_row(
            i,
            content[:80] + ("..." if len(content) > 80 else ""),
            f"{importance:.2f}",
            datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        )

    console.print(table)
    console.print(f"[dim]总计: {len(memories)} 条语义记忆[/dim]")


def view_episodic_memory(memory_manager: MemoryManager):
    """查看情节记忆"""
    console.print("[bold blue]📜 情节记忆内容[/bold blue]")

    memories = memory_manager.read_episodic_memory()

    if not memories:
        console.print("[yellow]⚠ 情节记忆为空[/yellow]")
        return

    table = Table(title="📜 情节记忆列表")
    table.add_column("序号", style="cyan")
    table.add_column("内容", style="green")
    table.add_column("重要性", style="magenta")
    table.add_column("时间", style="blue")

    for i, memory in enumerate(memories, 1):
        content = safe_get_content(memory)
        importance = safe_get_attribute(memory, "importance", 0.8)
        timestamp = safe_get_attribute(memory, "timestamp", 0)

        table.add_row(
            i,
            content[:80] + ("..." if len(content) > 80 else ""),
            f"{importance:.2f}",
            datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S"),
        )

    console.print(table)
    console.print(f"[dim]总计: {len(memories)} 条情节记忆[/dim]")


def view_memory_file(memory_manager: MemoryManager, file_path: str):
    """查看指定的记忆文件"""
    full_path = memory_manager.agent_dir / file_path

    if not full_path.exists():
        console.print(f"[red]❌ 记忆文件不存在: {file_path}[/red]")
        return

    try:
        content = full_path.read_text(encoding="utf-8")
        file_size = full_path.stat().st_size
        file_mtime = datetime.fromtimestamp(full_path.stat().st_mtime)

        console.print(f"[bold blue]📖 文件: {file_path}[/bold blue]")
        console.print(f"[dim]大小: {file_size} bytes[/dim]")
        console.print(f"[dim]修改时间: {file_mtime}[/dim]")
        console.print()

        # 根据文件类型选择显示方式
        if file_path.endswith(".json"):
            # JSON文件 - 美化显示
            try:
                json_data = json.loads(content)
                console.print(
                    Panel(
                        json.dumps(json_data, ensure_ascii=False, indent=2),
                        title="JSON文件内容",
                        border_style="blue",
                    )
                )
            except json.JSONDecodeError:
                console.print("[yellow]⚠ JSON格式错误，显示原始内容[/yellow]")
                console.print(Panel(content, title="文件内容", border_style="red"))
        else:
            # 普通文件 - 语法高亮
            try:
                # 根据文件扩展名确定语法高亮
                if file_path.endswith(".md"):
                    syntax = "markdown"
                elif file_path.endswith(".py"):
                    syntax = "python"
                elif file_path.endswith(".js"):
                    syntax = "javascript"
                elif file_path.endswith(".json"):
                    syntax = "json"
                else:
                    syntax = "text"

                console.print(
                    Panel(
                        Syntax(content, syntax=syntax),
                        title=f"文件内容 ({syntax})",
                        border_style="blue",
                    )
                )
            except Exception:
                console.print(Panel(content, title="文件内容", border_style="blue"))

    except Exception as e:
        console.print(f"[red]❌ 读取文件失败: {e}[/red]")


def view_all_memories(memory_manager: MemoryManager):
    """查看所有记忆概览"""
    console.print("[bold blue]📊 Fix Agent 记忆概览[/bold blue]")

    # 获取统计信息
    stats = memory_manager.get_memory_stats()

    # 显示统计信息
    stats_table = Table(title="📊 记忆统计")
    stats_table.add_column("类型", style="cyan")
    stats_table.add_column("数量/大小", style="green")
    stats_table.add_column("描述", style="blue")

    stats_table.add_row(
        "Agent主记忆",
        f"{stats['agent_memory_lines']} 行 / {stats['agent_memory_size']} 字符",
        "AI Agent的核心指令和配置信息",
    )
    stats_table.add_row(
        "语义记忆", f"{stats['semantic_memory_count']} 条", "概念、规则、偏好等长期知识"
    )
    stats_table.add_row(
        "情节记忆", f"{stats['episodic_memory_count']} 条", "重要事件、对话、交互记录"
    )
    stats_table.add_row("总计", f"{stats['total_memories']} 条", "所有类型的记忆")

    console.print(stats_table)

    # 显示文件列表
    files = memory_manager.list_memory_files()

    if files:
        console.print("\n[bold blue]📁 记忆文件列表[/bold blue]")
        files_table = Table()
        files_table.add_column("文件名", style="cyan")
        files_table.add_column("类型", style="magenta")
        files_table.add_column("大小", style="blue")
        files_table.add_column("修改时间", style="green")

        for file_info in files:
            size_text = f"{file_info['size']} bytes"
            modified_time = file_info["modified"][:19]  # 只显示前19个字符

            files_table.add_row(
                file_info["name"], file_info["type"], size_text, modified_time
            )

        console.print(files_table)


def handle_memory_search(memory_manager: MemoryManager, args: List[str]) -> bool:
    """处理记忆搜索命令"""
    if not args:
        console.print("[red]❌ 请提供搜索关键词[/red]")
        return False

    query = " ".join(args)
    memory_type = "all"

    # 检查是否有类型参数
    if len(args) > 1 and args[1] in ["agent", "semantic", "episodic"]:
        query = " ".join(args[:-1])
        memory_type = args[-1]

    console.print(
        f"[bold blue]🔍 搜索记忆: '{query}' (类型: {memory_type})[/bold blue]"
    )

    results = memory_manager.search_memories(query, memory_type)

    total_results = (
        len(results["agent_memory"])
        + len(results["semantic_memory"])
        + len(results["episodic_memory"])
    )

    if total_results == 0:
        console.print(f"[yellow]⚠ 没有找到包含 '{query}' 的记忆[/yellow]")
        return True

    # 显示搜索结果
    console.print(f"[green]✅ 找到 {total_results} 条匹配的记忆[/green]")

    # 显示Agent记忆结果
    if results["agent_memory"]:
        console.print("\n[bold blue]📝 Agent记忆匹配项:[/bold blue]")
        for i, result in enumerate(results["agent_memory"][:10], 1):
            console.print(
                f"  {i}. [cyan]第{result['line']}行[/cyan]: {result['content']}"
            )

        if len(results["agent_memory"]) > 10:
            console.print(
                f"[dim]... 还有 {len(results['agent_memory']) - 10} 个匹配项[/dim]"
            )

    # 显示语义记忆结果
    if results["semantic_memory"]:
        console.print("\n[bold blue]🧠 语义记忆匹配项:[/bold blue]")
        for i, result in enumerate(results["semantic_memory"][:5], 1):
            timestamp = result.get("timestamp", 0)
            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            console.print(
                f"  {i}. [magenta]{result['content'][:80]}...[/magenta] (重要性: {result['importance']}, 时间: {time_str})"
            )

        if len(results["semantic_memory"]) > 5:
            console.print(
                f"[dim]... 还有 {len(results['semantic_memory']) - 5} 个匹配项[/dim]"
            )

    # 显示情节记忆结果
    if results["episodic_memory"]:
        console.print("\n[bold blue]📜 情节记忆匹配项:[/bold blue]")
        for i, result in enumerate(results["episodic_memory"][:5], 1):
            timestamp = result.get("timestamp", 0)
            time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            console.print(
                f"  {i}. [green]{result['content'][:80]}...[/green] (重要性: {result['importance']}, 时间: {time_str})"
            )

        if len(results["episodic_memory"]) > 5:
            console.print(
                f"[dim]... 还有 {len(results['episodic_memory']) - 5} 个匹配项[/dim]"
            )

    console.print(f"\n[dim]提示: 使用 '/memory view <类型>' 查看详细内容[/dim]")

    return True


def handle_memory_stats(memory_manager: MemoryManager, args: List[str]) -> bool:
    """处理记忆统计命令"""
    console.print("[bold blue]📊 记忆使用统计[/bold blue]")

    stats = memory_manager.get_memory_stats()

    # 详细统计表
    table = Table(title="📊 详细统计信息")
    table.add_column("指标", style="cyan")
    table.add_column("数值", style="green")
    table.add_column("说明", style="blue")

    table.add_row("Agent记忆行数", stats["agent_memory_lines"], "Agent主记忆的总行数")
    table.add_row(
        "Agent记忆大小", f"{stats['agent_memory_size']} 字符", "Agent主记忆文件的大小"
    )
    table.add_row("语义记忆条数", stats["semantic_memory_count"], "语义记忆的条目数量")
    table.add_row("情节记忆条数", stats["episodic_memory_count"], "情节记忆的条目数量")
    table.add_row("总记忆条目", stats["total_memories"], "所有记忆类型的总条目数")
    table.add_row("记忆目录", stats["memory_dir"], "记忆存储的目录路径")
    table.add_row("最后更新", stats["last_modified"], "记忆的最后更新时间")

    console.print(table)

    # 内存使用情况
    try:
        dir_size = sum(
            f.stat().st_size
            for f in memory_manager.memories_dir.rglob("*")
            if f.is_file()
        )

        console.print(f"\n[bold blue]💾 内存使用:[/bold blue]")
        console.print(f"  记忆目录大小: {dir_size / 1024:.2f} KB")

        if stats["total_memories"] > 0:
            avg_size = dir_size / stats["total_memories"]
            console.print(f"  平均记忆项大小: {avg_size:.2f} bytes")
    except Exception:
        pass

    # 记忆分布
    semantic_count = stats["semantic_memory_count"]
    episodic_count = stats["episodic_memory_count"]

    if semantic_count + episodic_count > 0:
        console.print(f"\n[bold blue]📈 记忆分布:[/bold blue]")
        total = semantic_count + episodic_count
        console.print(
            f"  语义记忆: {semantic_count} 条 ({semantic_count/total*100:.1f}%)"
        )
        console.print(
            f"  情节记忆: {episodic_count} 条 ({episodic_count/total*100:.1f}%)"
        )

    # 使用建议
    console.print(f"\n[bold blue]💡 使用建议:[/bold blue]")
    if stats["agent_memory_size"] == 0:
        console.print("  • Agent主记忆为空，建议添加基础配置信息")
    if stats["total_memories"] == 0:
        console.print("  • 还没有分层记忆，通过对话会自动创建")
    console.print("  • 定期导出记忆备份，防止数据丢失")
    console.print("  • 使用搜索功能快速查找相关信息")

    return True


def handle_memory_export(memory_manager: MemoryManager, args: List[str]) -> bool:
    """处理记忆导出命令"""
    export_path = args[0] if args else None

    console.print("[bold blue]💾 导出记忆数据[/bold blue]")

    export_file = memory_manager.export_memories(export_path)

    if export_file:
        console.print(f"[green]✅ 记忆导出成功[/green]")
        console.print(f"  导出文件: {export_file}")

        # 显示导出统计
        stats = memory_manager.get_memory_stats()
        console.print(f"  导出时间: {stats['last_modified']}")
        console.print(f"  包含记忆: {stats['total_memories']} 条")
        console.print(f"  文件大小: {Path(export_file).stat().st_size} bytes")


def handle_memory_import(memory_manager: MemoryManager, args: List[str]) -> bool:
    """处理记忆导入命令"""
    if not args:
        console.print("[red]❌ 请指定导入文件路径[/red]")
        return False

    import_path = args[0]

    console.print("[bold blue]📥 导入记忆数据[/bold blue]")

    success = memory_manager.import_memories(import_path)

    if success:
        console.print(f"[green]✅ 记忆导入成功[/green]")
        console.print(f"  导入文件: {import_path}")

        # 显示导入后的统计
        stats = memory_manager.get_memory_stats()
        console.print(f"  当前记忆总数: {stats['total_memories']} 条")
        return True
    else:
        console.print(f"[red]❌ 记忆导入失败[/red]")
        return False


def handle_memory_list(memory_manager: MemoryManager, args: List[str]) -> bool:
    """处理记忆文件列表命令"""
    console.print("[bold blue]📁 记忆文件列表[/bold blue]")

    files = memory_manager.list_memory_files()

    if not files:
        console.print("[yellow]⚠ 没有找到记忆相关文件[/yellow]")
        return True

    table = Table(title="📁 记忆文件列表")
    table.add_column("文件名", style="cyan")
    table.add_column("类型", style="magenta")
    table.add_column("大小", style="blue")
    table.add_column("修改时间", style="green")

    for file_info in files:
        table.add_row(
            file_info["name"],
            file_info["type"],
            f"{file_info['size']} bytes",
            file_info["modified"],
        )

    console.print(table)

    # 显示存储使用情况
    total_size = sum(f["size"] for f in files)
    console.print(f"\n[dim]总存储: {total_size / 1024:.2f} KB[/dim]")

    # 按类型统计
    type_counts = {}
    for file_info in files:
        file_type = file_info["type"]
        type_counts[file_type] = type_counts.get(file_type, 0) + 1

    if type_counts:
        console.print(f"\n[dim]文件类型分布:[/dim]")
        for file_type, count in type_counts.items():
            console.print(f"  {file_type}: {count} 个文件")

    return True


def handle_memory_backup(memory_manager: MemoryManager, args: List[str]) -> bool:
    """创建记忆备份"""
    console.print("[bold blue]💾 创建记忆备份[/bold blue]")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = memory_manager.agent_dir / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_files = []

    try:
        # 备份主记忆文件
        if memory_manager.agent_memory_file.exists():
            backup_file = backup_dir / f"agent_backup_{timestamp}.md"
            shutil.copy2(memory_manager.agent_memory_file, backup_file)
            backup_files.append(backup_file)
            console.print(f"✅ 备份: {backup_file.name}")

        # 备份分层记忆文件
        if memory_manager.semantic_memory_file.exists():
            backup_file = backup_dir / f"semantic_memory_backup_{timestamp}.json"
            shutil.copy2(memory_manager.semantic_memory_file, backup_file)
            backup_files.append(backup_file)
            console.print(f"✅ 备份: {backup_file.name}")

        if memory_manager.episodic_memory_file.exists():
            backup_file = backup_dir / f"episodic_memory_backup_{timestamp}.json"
            shutil.copy2(memory_manager.episodic_memory_file, backup_file)
            backup_files.append(backup_file)
            console.print(f"✅ 备份: {backup_file.name}")

        if backup_files:
            console.print(
                f"\n[green]✅ 备份完成！共 {len(backup_files)} 个文件[/green]"
            )
            console.print(f"备份目录: {backup_dir}")
            console.print(f"备份时间: {timestamp}")
            return True
        else:
            console.print("[yellow]⚠ 没有文件需要备份[/yellow]")
            return True

    except Exception as e:
        console.print(f"[red]❌ 备份失败: {e}[/red]")
        return False


def handle_memory_restore(memory_manager: MemoryManager, args: List[str]) -> bool:
    """恢复记忆备份"""
    if not args:
        console.print("[red]❌ 请指定备份文件名[/red]")
        return False

    backup_name = args[0]
    backup_dir = memory_manager.agent_dir / "backups"

    console.print(f"[bold blue]🔄 恢复记忆备份[/bold blue]")

    # 查找匹配的备份文件
    backup_files = list(backup_dir.glob(f"*{backup_name}*"))

    if not backup_files:
        console.print(f"[red]❌ 找不到匹配的备份文件: {backup_name}[/red]")
        return False

    # 如果找到多个匹配的文件，显示选择
    if len(backup_files) > 1:
        console.print(f"[cyan]找到 {len(backup_files)} 个匹配的备份文件:[/cyan]")
        for i, file_path in enumerate(backup_files, 1):
            file_name = file_path.name
            modified_time = datetime.fromtimestamp(file_path.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            console.log(f"  {i}. {file_name} ({modified_time})")

        # 让用户选择
        backup_file = backup_files[0]  # 默认选择第一个
    else:
        backup_file = backup_files[0]

    console.print(f"[dim]选择备份文件: {backup_file.name}[/dim]")

    try:
        if backup_file.name.startswith("agent_backup_"):
            # 恢复主记忆
            target_file = memory_manager.agent_memory_file
            shutil.copy2(backup_file, target_file)
            console.print(f"[green]✅ 恢复Agent主记忆[/green]")

        elif backup_file.name.startswith("semantic_memory_backup_"):
            # 恢复语义记忆
            target_file = memory_manager.semantic_memory_file
            shutil.copy2(backup_file, target_file)
            console.print("[green]✅ 恢复语义记忆[/green]")

        elif backup_file.name.startswith("episodic_memory_backup_"):
            # 恢复情节记忆
            target_file = memory_manager.episodic_memory_file
            shutil.copy2(backup_file, target_file)
            console.print("[green]✅ 恢复情节记忆[/green]")
        else:
            console.print(f"[yellow]⚠ 未知类型的备份文件，跳过[/yellow]")
            return False

        console.print(f"[green]✅ 记忆恢复完成[/green]")
        return True

    except Exception as e:
        console.print(f"[red]❌ 恢复失败: {e}[/red]")
        return False


def handle_memory_clear(memory_manager: MemoryManager, args: List[str]) -> bool:
    """清空指定类型的记忆"""
    if not args:
        console.print("[red]❌ 请指定要清空的记忆类型[/red]")
        console.print("可用类型: agent, semantic, episodic, all")
        return

    memory_type = args[0]

    console.print(f"[bold red]⚠ 清空记忆: {memory_type}[/bold red]")

    confirmed = Confirm.ask(
        f"确定要清空 {memory_type} 类型的所有记忆吗？此操作不可撤销！", default=False
    )

    if not confirmed:
        console.print("[blue]操作已取消[/blue]")
        return

    try:
        cleared_count = 0

        if memory_type in ["agent", "all"]:
            # 清空Agent记忆
            backup_file = memory_manager.agent_memory_file.with_suffix(".backup_clear")
            memory_manager._create_backup(memory_manager.agent_memory_file)

            memory_manager.agent_memory_file.write_text("")  # 清空内容
            cleared_count += 1
            console.print("✅ Agent记忆已清空")

        if memory_type in ["semantic", "all"]:
            # 清空语义记忆
            backup_file = memory_manager.semantic_memory_file.with_suffix(
                ".backup_clear"
            )
            memory_manager._create_backup(memory_manager.semantic_memory_file)

            memory_manager.write_semantic_memory([])  # 清空列表
            cleared_count += len(memory_manager.read_semantic_memory())
            console.print(f"✅ 语义记忆已清空 ({cleared_count} 条)")

        if memory_type in ["episodic", "all"]:
            # 清空情节记忆
            backup_file = memory_manager.episodic_memory_file.with_suffix(
                ".backup_clear"
            )
            memory_manager._create_backup(memory_manager.episodic_memory_file)

            memory_manager.write_episodic_memory([])  # 清空列表
            cleared_count += len(memory_manager.read_episodic_memory())
            console.print(f"✅ 情节记忆已清空 ({cleared_count} 条)")

        console.print(f"[green]✅ 已清空 {memory_type} 类型的记忆[/green]")

    except Exception as e:
        console.print(f"[red]❌ 清空失败: {e}[/red]")
        return False

    return True


# 兼容性函数 - 用于commands.py中的调用
def show_memory_help():
    """显示记忆管理帮助（兼容函数）"""
    show_memory_menu()


def search_memories(memory_manager, query: str, memory_type: str = "all"):
    """搜索记忆（兼容函数）"""
    return memory_manager.search_memories(query, memory_type)


def export_memories(export_path: Optional[str] = None):
    """导出记忆（兼容函数）"""
    # 获取当前助手ID并创建记忆管理器
    try:
        from ..agents.agent import get_current_assistant_id

        assistant_id = get_current_assistant_id()
        manager = MemoryManager(assistant_id)
        return manager.export_memories(export_path)
    except:
        return ""


def import_memories(import_path: str):
    """导入记忆（兼容函数）"""
    try:
        from ..agents.agent import get_current_assistant_id

        assistant_id = get_current_assistant_id()
        manager = MemoryManager(assistant_id)
        return manager.import_memories(import_path)
    except:
        return False


def backup_memory_files(assistant_id: str):
    """备份记忆文件（兼容函数）"""
    try:
        manager = MemoryManager(assistant_id)
        handle_memory_backup(manager, [])
    except:
        pass


def restore_memory_files(assistant_id: str, backup_name: Optional[str] = None):
    """恢复记忆文件（兼容函数）"""
    try:
        manager = MemoryManager(assistant_id)
        if backup_name:
            handle_memory_restore(manager, [backup_name])
        else:
            handle_memory_restore(manager, [])
    except:
        pass


def clean_memory_files(assistant_id: str):
    """清理记忆文件（兼容函数）"""
    try:
        manager = MemoryManager(assistant_id)
        handle_memory_clear(manager, ["all"])
    except:
        pass


def get_memory_stats(assistant_id: str):
    """获取记忆统计（兼容函数）"""
    try:
        manager = MemoryManager(assistant_id)
        handle_memory_stats(manager, [])
    except:
        pass


# 注册命令
def register_memory_commands(commands_dict: Dict[str, Any]) -> None:
    """注册记忆管理命令到命令字典"""
    commands_dict["memory"] = handle_memory_command
