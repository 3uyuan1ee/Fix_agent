"""
代码差异查看器
负责生成和展示修改前后的代码差异
"""

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..utils.config import get_config_manager
from ..utils.logger import get_logger


@dataclass
class DiffChunk:
    """差异块"""

    old_start: int
    old_lines: List[str]
    new_start: int
    new_lines: List[str]
    chunk_type: str  # 'equal', 'replace', 'delete', 'insert'
    context_lines: List[str] = field(default_factory=list)


@dataclass
class DiffResult:
    """差异结果"""

    file_path: str
    old_content: str
    new_content: str
    chunks: List[DiffChunk] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    summary: str = ""
    formatted_diff: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "stats": self.stats,
            "summary": self.summary,
            "chunks": [self._chunk_to_dict(chunk) for chunk in self.chunks],
            "formatted_diff": self.formatted_diff,
        }

    def _chunk_to_dict(self, chunk: DiffChunk) -> Dict[str, Any]:
        """将差异块转换为字典"""
        return {
            "old_start": chunk.old_start,
            "old_lines": chunk.old_lines,
            "new_start": chunk.new_start,
            "new_lines": chunk.new_lines,
            "chunk_type": chunk.chunk_type,
            "context_lines": chunk.context_lines,
        }


class DiffViewer:
    """代码差异查看器"""

    def __init__(self, config_manager=None):
        """
        初始化差异查看器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        try:
            self.config = self.config_manager.get_section("diff_viewer")
        except:
            self.config = {}

        self.context_lines = self.config.get("context_lines", 3)
        self.show_line_numbers = self.config.get("show_line_numbers", True)
        self.highlight_syntax = self.config.get("highlight_syntax", True)
        self.ignore_whitespace = self.config.get("ignore_whitespace", False)

        self.logger.info("DiffViewer initialized")

    def generate_diff(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        output_format: str = "unified",
    ) -> DiffResult:
        """
        生成代码差异

        Args:
            file_path: 文件路径
            old_content: 原始内容
            new_content: 新内容
            output_format: 输出格式 (unified, context, html, json)

        Returns:
            差异结果
        """
        self.logger.info(f"Generating diff for {file_path}")

        try:
            # 标准化行结束符
            old_lines = self._normalize_lines(old_content)
            new_lines = self._normalize_lines(new_content)

            # 生成差异块
            chunks = self._generate_diff_chunks(old_lines, new_lines)

            # 计算统计信息
            stats = self._calculate_diff_stats(old_lines, new_lines)

            # 生成摘要
            summary = self._generate_summary(stats)

            # 格式化差异输出
            formatted_diff = self._format_diff(chunks, file_path, output_format)

            result = DiffResult(
                file_path=file_path,
                old_content=old_content,
                new_content=new_content,
                chunks=chunks,
                stats=stats,
                summary=summary,
                formatted_diff=formatted_diff,
            )

            self.logger.info(f"Diff generated for {file_path}: {summary}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to generate diff for {file_path}: {e}")
            # 返回空结果
            return DiffResult(
                file_path=file_path,
                old_content=old_content,
                new_content=new_content,
                summary=f"Error generating diff: {e}",
            )

    def generate_unified_diff(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        context_lines: Optional[int] = None,
    ) -> str:
        """
        生成统一格式的差异

        Args:
            file_path: 文件路径
            old_content: 原始内容
            new_content: 新内容
            context_lines: 上下文行数

        Returns:
            统一格式的差异字符串
        """
        try:
            old_lines = self._normalize_lines(old_content)
            new_lines = self._normalize_lines(new_content)
            context = context_lines or self.context_lines

            # 使用difflib生成统一差异
            diff_lines = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"a/{Path(file_path).name}",
                    tofile=f"b/{Path(file_path).name}",
                    lineterm="",
                    n=context,
                )
            )

            return "\n".join(diff_lines)

        except Exception as e:
            self.logger.error(f"Failed to generate unified diff: {e}")
            return f"Error generating diff: {e}"

    def generate_context_diff(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        context_lines: Optional[int] = None,
    ) -> str:
        """
        生成上下文格式的差异

        Args:
            file_path: 文件路径
            old_content: 原始内容
            new_content: 新内容
            context_lines: 上下文行数

        Returns:
            上下文格式的差异字符串
        """
        try:
            old_lines = self._normalize_lines(old_content)
            new_lines = self._normalize_lines(new_content)
            context = context_lines or self.context_lines

            # 使用difflib生成上下文差异
            diff_lines = list(
                difflib.context_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"a/{Path(file_path).name}",
                    tofile=f"b/{Path(file_path).name}",
                    lineterm="",
                    n=context,
                )
            )

            return "\n".join(diff_lines)

        except Exception as e:
            self.logger.error(f"Failed to generate context diff: {e}")
            return f"Error generating diff: {e}"

    def generate_html_diff(
        self, file_path: str, old_content: str, new_content: str
    ) -> str:
        """
        生成HTML格式的差异

        Args:
            file_path: 文件路径
            old_content: 原始内容
            new_content: 新内容

        Returns:
            HTML格式的差异字符串
        """
        try:
            diff_result = self.generate_diff(
                file_path, old_content, new_content, "internal"
            )
            return self._format_html_diff(diff_result)

        except Exception as e:
            self.logger.error(f"Failed to generate HTML diff: {e}")
            return f"<div class='error'>Error generating diff: {e}</div>"

    def generate_side_by_side_diff(
        self, file_path: str, old_content: str, new_content: str
    ) -> str:
        """
        生成并排格式的差异

        Args:
            file_path: 文件路径
            old_content: 原始内容
            new_content: 新内容

        Returns:
            并排格式的差异字符串
        """
        try:
            old_lines = self._normalize_lines(old_content)
            new_lines = self._normalize_lines(new_content)

            # 生成匹配器
            matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

            # 构建并排差异
            result_lines = []
            old_line_num = 1
            new_line_num = 1

            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    # 相同行
                    for i in range(i1, i2):
                        old_line = old_lines[i]
                        new_line = new_lines[j1 + (i - i1)]
                        result_lines.append(
                            self._format_side_by_side_line(
                                old_line_num, old_line, new_line_num, new_line, "equal"
                            )
                        )
                        old_line_num += 1
                        new_line_num += 1

                elif tag == "replace":
                    # 替换行
                    # 先显示删除旧行
                    for i in range(i1, i2):
                        result_lines.append(
                            self._format_side_by_side_line(
                                old_line_num, old_lines[i], new_line_num, "", "delete"
                            )
                        )
                        old_line_num += 1

                    # 再显示插入新行
                    for j in range(j1, j2):
                        result_lines.append(
                            self._format_side_by_side_line(
                                old_line_num, "", new_line_num, new_lines[j], "insert"
                            )
                        )
                        new_line_num += 1

                elif tag == "delete":
                    # 删除行
                    for i in range(i1, i2):
                        result_lines.append(
                            self._format_side_by_side_line(
                                old_line_num, old_lines[i], new_line_num, "", "delete"
                            )
                        )
                        old_line_num += 1

                elif tag == "insert":
                    # 插入行
                    for j in range(j1, j2):
                        result_lines.append(
                            self._format_side_by_side_line(
                                old_line_num, "", new_line_num, new_lines[j], "insert"
                            )
                        )
                        new_line_num += 1

            return "\n".join(result_lines)

        except Exception as e:
            self.logger.error(f"Failed to generate side-by-side diff: {e}")
            return f"Error generating diff: {e}"

    def _normalize_lines(self, content: str) -> List[str]:
        """标准化行列表"""
        if not content:
            return []

        lines = content.splitlines()
        if self.ignore_whitespace:
            # 移除行尾空白
            lines = [line.rstrip() for line in lines]

        return lines

    def _generate_diff_chunks(
        self, old_lines: List[str], new_lines: List[str]
    ) -> List[DiffChunk]:
        """生成差异块"""
        chunks = []
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            chunk = DiffChunk(
                old_start=i1 + 1 if i1 < len(old_lines) else 0,
                old_lines=old_lines[i1:i2],
                new_start=j1 + 1 if j1 < len(new_lines) else 0,
                new_lines=new_lines[j1:j2],
                chunk_type=tag,
            )
            chunks.append(chunk)

        return chunks

    def _calculate_diff_stats(
        self, old_lines: List[str], new_lines: List[str]
    ) -> Dict[str, int]:
        """计算差异统计"""
        stats = {
            "old_lines": len(old_lines),
            "new_lines": len(new_lines),
            "added": 0,
            "deleted": 0,
            "modified": 0,
            "unchanged": 0,
        }

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                stats["unchanged"] += i2 - i1
            elif tag == "replace":
                stats["deleted"] += i2 - i1
                stats["added"] += j2 - j1
                stats["modified"] += min(i2 - i1, j2 - j1)
            elif tag == "delete":
                stats["deleted"] += i2 - i1
            elif tag == "insert":
                stats["added"] += j2 - j1

        return stats

    def _generate_summary(self, stats: Dict[str, int]) -> str:
        """生成差异摘要"""
        parts = []

        if stats["added"] > 0:
            parts.append(f"+{stats['added']} 行新增")
        if stats["deleted"] > 0:
            parts.append(f"-{stats['deleted']} 行删除")
        if stats["modified"] > 0:
            parts.append(f"~{stats['modified']} 行修改")

        if not parts:
            return "文件内容相同"

        return f"差异: {', '.join(parts)}"

    def _format_diff(
        self, chunks: List[DiffChunk], file_path: str, output_format: str
    ) -> str:
        """格式化差异输出"""
        if output_format == "json":
            return self._format_json_diff(chunks, file_path)
        elif output_format == "html":
            return self._format_html_diff_from_chunks(chunks, file_path)
        else:
            return self._format_unified_diff_from_chunks(chunks, file_path)

    def _format_unified_diff_from_chunks(
        self, chunks: List[DiffChunk], file_path: str
    ) -> str:
        """从差异块格式化统一差异"""
        lines = []
        filename = Path(file_path).name

        # 文件头
        lines.append(f"--- a/{filename}")
        lines.append(f"+++ b/{filename}")

        old_line_num = 1
        new_line_num = 1

        for chunk in chunks:
            if chunk.chunk_type == "equal":
                # 相同行
                for line in chunk.old_lines:
                    lines.append(f" {line}")
                    old_line_num += 1
                    new_line_num += 1

            elif chunk.chunk_type == "replace":
                # 替换 - 先删除后添加
                lines.append(
                    f"@@ -{old_line_num},{len(chunk.old_lines)} +{new_line_num},{len(chunk.new_lines)} @@"
                )

                # 删除的行
                for line in chunk.old_lines:
                    lines.append(f"-{line}")
                    old_line_num += 1

                # 添加的行
                for line in chunk.new_lines:
                    lines.append(f"+{line}")
                    new_line_num += 1

            elif chunk.chunk_type == "delete":
                # 删除
                lines.append(
                    f"@@ -{old_line_num},{len(chunk.old_lines)} +{new_line_num},0 @@"
                )
                for line in chunk.old_lines:
                    lines.append(f"-{line}")
                    old_line_num += 1

            elif chunk.chunk_type == "insert":
                # 插入
                lines.append(
                    f"@@ -{old_line_num},0 +{new_line_num},{len(chunk.new_lines)} @@"
                )
                for line in chunk.new_lines:
                    lines.append(f"+{line}")
                    new_line_num += 1

        return "\n".join(lines)

    def _format_json_diff(self, chunks: List[DiffChunk], file_path: str) -> str:
        """格式化JSON差异"""
        import json

        data = {
            "file_path": file_path,
            "chunks": [self._chunk_to_dict(chunk) for chunk in chunks],
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _chunk_to_dict(self, chunk: DiffChunk) -> Dict[str, Any]:
        """将差异块转换为字典"""
        return {
            "old_start": chunk.old_start,
            "old_lines": chunk.old_lines,
            "new_start": chunk.new_start,
            "new_lines": chunk.new_lines,
            "chunk_type": chunk.chunk_type,
        }

    def _format_html_diff_from_chunks(
        self, chunks: List[DiffChunk], file_path: str
    ) -> str:
        """从差异块格式化HTML差异"""
        html_parts = [
            '<div class="diff-container">',
            f'<div class="diff-header">文件: {Path(file_path).name}</div>',
            '<table class="diff-table">',
        ]

        for chunk in chunks:
            if chunk.chunk_type == "equal":
                for line in chunk.old_lines:
                    html_parts.append(
                        f'<tr class="diff-equal"><td class="line-number"></td><td class="code">{self._escape_html(line)}</td></tr>'
                    )

            elif chunk.chunk_type == "replace":
                # 替换 - 显示删除和添加
                for line in chunk.old_lines:
                    html_parts.append(
                        f'<tr class="diff-deleted"><td class="line-number">-</td><td class="code">{self._escape_html(line)}</td></tr>'
                    )
                for line in chunk.new_lines:
                    html_parts.append(
                        f'<tr class="diff-added"><td class="line-number">+</td><td class="code">{self._escape_html(line)}</td></tr>'
                    )

            elif chunk.chunk_type == "delete":
                for line in chunk.old_lines:
                    html_parts.append(
                        f'<tr class="diff-deleted"><td class="line-number">-</td><td class="code">{self._escape_html(line)}</td></tr>'
                    )

            elif chunk.chunk_type == "insert":
                for line in chunk.new_lines:
                    html_parts.append(
                        f'<tr class="diff-added"><td class="line-number">+</td><td class="code">{self._escape_html(line)}</td></tr>'
                    )

        html_parts.extend(["</table>", "</div>"])

        # 添加样式
        css = """
        <style>
        .diff-container { font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; }
        .diff-header { background: #f5f5f5; padding: 10px; border-bottom: 1px solid #ddd; font-weight: bold; }
        .diff-table { width: 100%; border-collapse: collapse; }
        .diff-equal { background: #ffffff; }
        .diff-added { background: #e6ffed; }
        .diff-deleted { background: #ffeef0; }
        .line-number { width: 30px; text-align: center; color: #666; background: #f8f8f8; }
        .code { padding: 2px 5px; white-space: pre-wrap; }
        </style>
        """

        return css + "\n".join(html_parts)

    def _format_html_diff(self, diff_result: DiffResult) -> str:
        """格式化HTML差异（完整版本）"""
        return self._format_html_diff_from_chunks(
            diff_result.chunks, diff_result.file_path
        )

    def _format_side_by_side_line(
        self, old_num: int, old_line: str, new_num: int, new_line: str, change_type: str
    ) -> str:
        """格式化并排差异行"""
        # 转义HTML字符
        old_line_html = self._escape_html(old_line)
        new_line_html = self._escape_html(new_line)

        # 确定CSS类
        css_class = f"diff-{change_type}"
        old_num_str = str(old_num) if old_num > 0 else ""
        new_num_str = str(new_num) if new_num > 0 else ""

        # 构建HTML行
        return f'<tr class="{css_class}"><td class="old-line">{old_num_str}</td><td class="old-code">{old_line_html}</td><td class="new-line">{new_num_str}</td><td class="new-code">{new_line_html}</td></tr>'

    def _escape_html(self, text: str) -> str:
        """转义HTML字符"""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def analyze_change_complexity(self, diff_result: DiffResult) -> Dict[str, Any]:
        """分析变更复杂度"""
        try:
            stats = diff_result.stats

            # 计算变更比例
            total_changes = stats["added"] + stats["deleted"] + stats["modified"]
            total_lines = max(stats["old_lines"], stats["new_lines"])
            change_ratio = total_changes / total_lines if total_lines > 0 else 0

            # 分析变更类型分布
            change_types = {
                "additions": stats["added"],
                "deletions": stats["deleted"],
                "modifications": stats["modified"],
            }

            # 评估复杂度
            if change_ratio > 0.5:
                complexity = "high"
            elif change_ratio > 0.2:
                complexity = "medium"
            else:
                complexity = "low"

            # 风险评估
            risk_factors = []
            if stats["added"] > 50:
                risk_factors.append("大量新增代码")
            if stats["deleted"] > 30:
                risk_factors.append("大量删除代码")
            if change_ratio > 0.7:
                risk_factors.append("大幅重构")

            return {
                "complexity": complexity,
                "change_ratio": round(change_ratio, 3),
                "total_changes": total_changes,
                "change_types": change_types,
                "risk_factors": risk_factors,
                "recommendation": self._get_complexity_recommendation(
                    complexity, risk_factors
                ),
            }

        except Exception as e:
            self.logger.error(f"Failed to analyze change complexity: {e}")
            return {"complexity": "unknown", "error": str(e)}

    def _get_complexity_recommendation(
        self, complexity: str, risk_factors: List[str]
    ) -> str:
        """获取复杂度建议"""
        if complexity == "high":
            return "建议仔细审查此次变更，考虑分步骤实施并进行充分测试。"
        elif complexity == "medium":
            return "建议进行代码审查和基本的单元测试。"
        else:
            return "变更相对简单，但仍建议进行基本验证。"
