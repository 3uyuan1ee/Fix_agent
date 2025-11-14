"""
专业代码格式化工具

基于原生包(black, isort, prettier, clang-format)构建的deepagents格式化工具，
充分发挥每个工具的原生功能，提供专业级的代码格式化能力。
"""

import json
import os
import subprocess
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import tool


class FormatOperation(Enum):
    """格式化操作类型"""

    AUTO_FIX = "auto_fix"  # 自动格式化
    PREVIEW = "preview"  # 预览变更
    CHECK = "check"  # 检查是否需要格式化
    DIFF = "diff"  # 显示差异


class FormatResult:
    """格式化结果"""

    def __init__(
        self,
        success: bool,
        file_path: str,
        tool_name: str,
        operation: FormatOperation,
        original_code: str = "",
        formatted_code: str = "",
        needs_formatting: bool = False,
        diff_output: str = "",
        execution_time: float = 0.0,
        error: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.file_path = file_path
        self.tool_name = tool_name
        self.operation = operation
        self.original_code = original_code
        self.formatted_code = formatted_code
        self.needs_formatting = needs_formatting
        self.diff_output = diff_output
        self.execution_time = execution_time
        self.error = error
        self.stats = stats or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "file_path": self.file_path,
            "tool_name": self.tool_name,
            "operation": self.operation.value,
            "needs_formatting": self.needs_formatting,
            "changes_made": self.original_code != self.formatted_code,
            "execution_time": self.execution_time,
            "error": self.error,
            "stats": self.stats,
            "has_diff": bool(self.diff_output),
        }


class PythonFormatter:
    """Python代码格式化器 - 基于black和isort"""

    def __init__(self):
        try:
            import black
            import isort

            self.black_available = True
            self.isort_available = True
            self.black = black
            self.isort = isort
        except ImportError as e:
            self.black_available = False
            self.isort_available = False
            print(f"Python格式化工具不可用: {e}")

    def format_file(
        self, file_path: str, operation: FormatOperation = FormatOperation.AUTO_FIX
    ) -> FormatResult:
        """格式化Python文件"""
        if not self.black_available:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="python",
                operation=operation,
                error="black和isort包未安装",
            )

        try:
            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            start_time = datetime.now()

            if operation == FormatOperation.CHECK:
                # 使用black检查
                result = self._check_with_black(original_code)
            elif operation == FormatOperation.PREVIEW:
                # 生成diff
                result = self._diff_with_black(original_code, file_path)
            elif operation == FormatOperation.DIFF:
                # 详细diff
                result = self._diff_with_black(original_code, file_path, detailed=True)
            else:
                # 自动格式化
                result = self._auto_format_python(original_code, file_path)

            result.execution_time = (datetime.now() - start_time).total_seconds()
            return result

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="python",
                operation=operation,
                error=f"格式化失败: {str(e)}",
            )

    def _auto_format_python(self, code: str, file_path: str) -> FormatResult:
        """使用black和isort自动格式化Python代码"""
        try:
            # 首先用isort格式化导入
            formatted_code = self.isort.code(code)

            # 然后用black格式化
            black_result = self.black.format_str(formatted_code, mode=self.black.Mode())
            formatted_code = black_result

            # 如果格式化后有变化，写回文件
            if formatted_code != code:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(formatted_code)

            return FormatResult(
                success=True,
                file_path=file_path,
                tool_name="python",
                operation=FormatOperation.AUTO_FIX,
                original_code=code,
                formatted_code=formatted_code,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="python",
                operation=FormatOperation.AUTO_FIX,
                error=f"格式化失败: {str(e)}",
            )

    def _check_with_black(self, code: str) -> FormatResult:
        """使用black检查代码格式"""
        try:
            # 使用black的check模式
            import io

            from black import Mode, format_str

            formatted_code = format_str(code, mode=Mode())
            needs_formatting = formatted_code != code

            stats = {
                "lines_changed": len(
                    [
                        i
                        for i, (a, b) in enumerate(
                            zip(code.splitlines(), formatted_code.splitlines())
                        )
                        if a != b
                    ]
                )
            }

            return FormatResult(
                success=True,
                file_path="string",
                tool_name="python",
                operation=FormatOperation.CHECK,
                original_code=code,
                formatted_code=formatted_code,
                needs_formatting=needs_formatting,
                stats=stats,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path="string",
                tool_name="python",
                operation=FormatOperation.CHECK,
                error=f"检查失败: {str(e)}",
            )

    def _diff_with_black(
        self, code: str, file_path: str, detailed: bool = False
    ) -> FormatResult:
        """使用black生成diff"""
        try:
            # 使用diff模式
            result = subprocess.run(
                ["black", "--diff", "--color=never", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                diff_output = ""
            else:
                diff_output = result.stdout

            # 获取格式化后的代码
            formatted_code = self.black.format_str(code, mode=self.black.Mode())

            return FormatResult(
                success=True,
                file_path=file_path,
                tool_name="python",
                operation=FormatOperation.PREVIEW,
                original_code=code,
                formatted_code=formatted_code,
                diff_output=diff_output,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="python",
                operation=FormatOperation.PREVIEW,
                error=f"diff生成失败: {str(e)}",
            )


class JavaScriptFormatter:
    """JavaScript/TypeScript格式化器 - 基于prettier"""

    def __init__(self):
        self.prettier_available = self._check_prettier()

    def _check_prettier(self) -> bool:
        """检查prettier是否可用"""
        try:
            result = subprocess.run(
                ["npx", "--version"], capture_output=True, text=True, timeout=10
            )
            return result.returncode == 0
        except:
            return False

    def format_file(
        self, file_path: str, operation: FormatOperation = FormatOperation.AUTO_FIX
    ) -> FormatResult:
        """格式化JavaScript/TypeScript文件"""
        if not self.prettier_available:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="javascript",
                operation=operation,
                error="prettier不可用，请确保npx和prettier已安装",
            )

        try:
            start_time = datetime.now()

            if operation == FormatOperation.CHECK:
                result = self._check_with_prettier(file_path)
            elif operation in [FormatOperation.PREVIEW, FormatOperation.DIFF]:
                result = self._diff_with_prettier(file_path)
            else:
                result = self._auto_format_js(file_path)

            result.execution_time = (datetime.now() - start_time).total_seconds()
            return result

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="javascript",
                operation=operation,
                error=f"格式化失败: {str(e)}",
            )

    def _auto_format_js(self, file_path: str) -> FormatResult:
        """使用prettier自动格式化"""
        try:
            # 读取原始代码
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            # 使用prettier格式化
            result = subprocess.run(
                ["npx", "prettier", "--write", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 读取格式化后的代码
            with open(file_path, "r", encoding="utf-8") as f:
                formatted_code = f.read()

            return FormatResult(
                success=result.returncode == 0,
                file_path=file_path,
                tool_name="javascript",
                operation=FormatOperation.AUTO_FIX,
                original_code=original_code,
                formatted_code=formatted_code,
                error=result.stderr if result.returncode != 0 else None,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="javascript",
                operation=FormatOperation.AUTO_FIX,
                error=f"格式化失败: {str(e)}",
            )

    def _check_with_prettier(self, file_path: str) -> FormatResult:
        """使用prettier检查格式"""
        try:
            result = subprocess.run(
                ["npx", "prettier", "--check", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 读取代码
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            return FormatResult(
                success=True,
                file_path=file_path,
                tool_name="javascript",
                operation=FormatOperation.CHECK,
                original_code=original_code,
                needs_formatting=result.returncode != 0,
                error=result.stderr if result.returncode != 0 else None,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="javascript",
                operation=FormatOperation.CHECK,
                error=f"检查失败: {str(e)}",
            )

    def _diff_with_prettier(self, file_path: str) -> FormatResult:
        """使用prettier生成diff"""
        try:
            # 读取原始代码
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            result = subprocess.run(
                ["npx", "prettier", "--check", "--diff", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 获取格式化后的代码
            format_result = subprocess.run(
                ["npx", "prettier", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            formatted_code = format_result.stdout

            return FormatResult(
                success=True,
                file_path=file_path,
                tool_name="javascript",
                operation=FormatOperation.PREVIEW,
                original_code=original_code,
                formatted_code=formatted_code,
                diff_output=result.stdout if result.returncode != 0 else "",
                needs_formatting=result.returncode != 0,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="javascript",
                operation=FormatOperation.PREVIEW,
                error=f"diff生成失败: {str(e)}",
            )


class CppFormatter:
    """C/C++代码格式化器 - 基于clang-format"""

    def __init__(self):
        self.clang_format_available = self._check_clang_format()

    def _check_clang_format(self) -> bool:
        """检查clang-format是否可用"""
        try:
            result = subprocess.run(
                ["clang-format", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except:
            return False

    def format_file(
        self, file_path: str, operation: FormatOperation = FormatOperation.AUTO_FIX
    ) -> FormatResult:
        """格式化C/C++文件"""
        if not self.clang_format_available:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="cpp",
                operation=operation,
                error="clang-format不可用",
            )

        try:
            start_time = datetime.now()

            if operation == FormatOperation.CHECK:
                result = self._check_with_clang_format(file_path)
            elif operation in [FormatOperation.PREVIEW, FormatOperation.DIFF]:
                result = self._diff_with_clang_format(file_path)
            else:
                result = self._auto_format_cpp(file_path)

            result.execution_time = (datetime.now() - start_time).total_seconds()
            return result

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="cpp",
                operation=operation,
                error=f"格式化失败: {str(e)}",
            )

    def _auto_format_cpp(self, file_path: str) -> FormatResult:
        """使用clang-format自动格式化"""
        try:
            # 读取原始代码
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            # 使用clang-format格式化
            result = subprocess.run(
                ["clang-format", "-i", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 读取格式化后的代码
            with open(file_path, "r", encoding="utf-8") as f:
                formatted_code = f.read()

            return FormatResult(
                success=result.returncode == 0,
                file_path=file_path,
                tool_name="cpp",
                operation=FormatOperation.AUTO_FIX,
                original_code=original_code,
                formatted_code=formatted_code,
                error=result.stderr if result.returncode != 0 else None,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="cpp",
                operation=FormatOperation.AUTO_FIX,
                error=f"格式化失败: {str(e)}",
            )

    def _check_with_clang_format(self, file_path: str) -> FormatResult:
        """使用clang-format检查格式"""
        try:
            # 读取原始代码
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            # clang-format没有直接的check命令，通过比较来判断
            format_result = subprocess.run(
                ["clang-format", file_path], capture_output=True, text=True, timeout=30
            )

            if format_result.returncode == 0:
                formatted_code = format_result.stdout
                needs_formatting = formatted_code.rstrip() != original_code.rstrip()
            else:
                needs_formatting = False

            return FormatResult(
                success=True,
                file_path=file_path,
                tool_name="cpp",
                operation=FormatOperation.CHECK,
                original_code=original_code,
                formatted_code=formatted_code if format_result.returncode == 0 else "",
                needs_formatting=needs_formatting,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="cpp",
                operation=FormatOperation.CHECK,
                error=f"检查失败: {str(e)}",
            )

    def _diff_with_clang_format(self, file_path: str) -> FormatResult:
        """使用clang-format生成diff"""
        try:
            # 读取原始代码
            with open(file_path, "r", encoding="utf-8") as f:
                original_code = f.read()

            # 生成diff
            result = subprocess.run(
                ["clang-format", "--dry-run", "--Werror", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            # 获取格式化后的代码
            format_result = subprocess.run(
                ["clang-format", file_path], capture_output=True, text=True, timeout=30
            )

            formatted_code = (
                format_result.stdout if format_result.returncode == 0 else ""
            )

            return FormatResult(
                success=True,
                file_path=file_path,
                tool_name="cpp",
                operation=FormatOperation.PREVIEW,
                original_code=original_code,
                formatted_code=formatted_code,
                diff_output=result.stderr if result.returncode != 0 else "",
                needs_formatting=result.returncode != 0,
            )

        except Exception as e:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="cpp",
                operation=FormatOperation.PREVIEW,
                error=f"diff生成失败: {str(e)}",
            )


class ProfessionalCodeFormatter:
    """专业代码格式化器"""

    def __init__(self):
        self.python_formatter = PythonFormatter()
        self.js_formatter = JavaScriptFormatter()
        self.cpp_formatter = CppFormatter()

    def detect_language(self, file_path: str) -> str:
        """检测文件语言"""
        ext = Path(file_path).suffix.lower()
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "javascript",
            ".tsx": "javascript",
            ".mjs": "javascript",
            ".c": "cpp",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".h": "cpp",
            ".hpp": "cpp",
            ".hxx": "cpp",
        }
        return language_map.get(ext, "unknown")

    def format_file(self, file_path: str, operation: str = "auto_fix") -> FormatResult:
        """格式化文件"""
        language = self.detect_language(file_path)

        if language == "python":
            operation_enum = FormatOperation(operation)
            return self.python_formatter.format_file(file_path, operation_enum)
        elif language == "javascript":
            operation_enum = FormatOperation(operation)
            return self.js_formatter.format_file(file_path, operation_enum)
        elif language == "cpp":
            operation_enum = FormatOperation(operation)
            return self.cpp_formatter.format_file(file_path, operation_enum)
        else:
            return FormatResult(
                success=False,
                file_path=file_path,
                tool_name="unknown",
                operation=FormatOperation.AUTO_FIX,
                error=f"不支持的语言: {language}",
            )


# 创建工具函数
@tool(
    description="专业代码格式化工具，基于black/isort(Python)、prettier(JS/TS)、clang-format(C/C++)等业界标准原生包，提供多语言统一的专业级代码格式化能力。支持自动修复、预览变更、检查状态和差异显示四种操作模式。"
)
def format_code_professional(file_path: str, operation: str = "auto_fix") -> str:
    """
    使用专业工具格式化代码文件，提供给agent使用的专业级代码格式化工具。

    此工具基于业界标准原生包提供多语言统一的代码格式化能力：
    - Python: 使用black和isort进行代码风格标准化和导入排序
    - JavaScript/TypeScript: 使用prettier进行代码格式化
    - C/C++: 使用clang-format进行代码格式化
    - 支持四种操作模式：自动修复、预览变更、检查状态、差异显示
    - 智能检测文件语言，自动选择合适的格式化工具
    - 提供详细的格式化结果和统计信息

    Args:
        file_path: 要格式化的文件路径，支持相对路径和绝对路径
        operation: 格式化操作类型，可选值：
            - "auto_fix": 自动格式化并保存文件（默认）
            - "preview": 预览格式化变更，不修改文件
            - "check": 检查文件是否需要格式化
            - "diff": 显示详细的格式化差异

    Returns:
        格式化结果的JSON字符串，包含：
            - success: 格式化是否成功
            - file_path: 处理的文件路径
            - tool_name: 使用的格式化工具名称
            - operation: 执行的操作类型
            - needs_formatting: 文件是否需要格式化
            - changes_made: 是否进行了修改（仅在auto_fix操作时有意义）
            - execution_time: 格式化执行时间（秒）
            - error: 错误信息（如果有）
            - stats: 详细统计信息，包含：
                - file_extension: 文件扩展名
                - detected_language: 检测到的编程语言
                - timestamp: 执行时间戳
                - diff_lines: 差异行数（如果有diff输出）
            - has_diff: 是否有差异输出

    使用场景：
        - 代码提交前的格式化检查和修复
        - CI/CD流水线中的代码质量门禁
        - 代码审查前的代码风格统一
        - 团队开发中的代码标准化
        - 重构后的代码格式整理
        - 新项目开发中的代码规范建立

    工具优势：
        - 基于业界标准的原生工具，保证专业性
        - 多语言统一接口，简化格式化流程
        - 智能语言检测，无需手动指定格式化工具
        - 多种操作模式，满足不同场景需求
        - 详细的执行结果和错误报告

    注意事项：
        - 需要系统中安装相应的格式化工具（black、isort、prettier、clang-format等）
        - auto_fix操作会直接修改原文件，建议在版本控制下使用
        - 大文件格式化可能需要较长时间
        - 某些复杂的项目可能需要自定义配置文件
        - 格式化工具的具体行为可能受项目配置文件影响
    """
    try:
        formatter = ProfessionalCodeFormatter()
        result = formatter.format_file(file_path, operation)

        # 添加统计信息
        stats = result.stats.copy()
        stats.update(
            {
                "file_extension": Path(file_path).suffix,
                "detected_language": formatter.detect_language(file_path),
                "timestamp": datetime.now().isoformat(),
            }
        )

        result_data = {**result.to_dict(), "stats": stats}

        if result.diff_output:
            result_data["diff_lines"] = len(result.diff_output.splitlines())

        return json.dumps(result_data, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"格式化操作失败: {str(e)}",
                "file_path": file_path,
                "operation": operation,
            },
            indent=2,
            ensure_ascii=False,
        )


@tool(
    description="批量使用专业工具格式化项目代码。支持多种编程语言的批量格式化操作，包括Python、JavaScript/TypeScript、C/C++等。提供智能文件匹配、语言检测、批量处理和详细统计报告功能，适用于整个项目的代码标准化和CI/CD集成。"
)
def batch_format_professional(
    project_path: str,
    operation: str = "check",
    file_pattern: str = "**/*.{py,js,ts,cpp,c,cc,cxx,h,hpp}",
) -> str:
    """
    批量格式化项目代码

    Args:
        project_path: 项目根目录
        operation: 操作类型 (auto_fix, preview, check, diff)
        file_pattern: 文件匹配模式

    Returns:
        批量格式化结果的JSON字符串
    """
    try:
        import glob
        from pathlib import Path

        project_dir = Path(project_path)
        if not project_dir.exists():
            return json.dumps(
                {"success": False, "error": f"项目路径不存在: {project_path}"},
                indent=2,
                ensure_ascii=False,
            )

        # 查找文件
        search_pattern = str(project_dir / file_pattern)
        files = glob.glob(search_pattern, recursive=True)

        if not files:
            return json.dumps(
                {
                    "success": True,
                    "message": "未找到匹配的文件",
                    "pattern": search_pattern,
                },
                indent=2,
                ensure_ascii=False,
            )

        formatter = ProfessionalCodeFormatter()
        results = []
        summary = {
            "total_files": len(files),
            "processed_files": 0,
            "files_need_formatting": 0,
            "failed_files": 0,
            "by_language": {},
            "operation": operation,
            "project_path": project_path,
        }

        for file_path in files:
            try:
                result = formatter.format_file(file_path, operation)
                results.append(result.to_dict())

                if result.success:
                    summary["processed_files"] += 1
                    if result.needs_formatting:
                        summary["files_need_formatting"] += 1

                    # 按语言统计
                    language = formatter.detect_language(file_path)
                    if language not in summary["by_language"]:
                        summary["by_language"][language] = {
                            "count": 0,
                            "needs_formatting": 0,
                        }
                    summary["by_language"][language]["count"] += 1
                    if result.needs_formatting:
                        summary["by_language"][language]["needs_formatting"] += 1
                else:
                    summary["failed_files"] += 1

            except Exception as e:
                results.append(
                    {
                        "success": False,
                        "file_path": file_path,
                        "error": str(e),
                        "tool_name": "unknown",
                    }
                )
                summary["failed_files"] += 1

        return json.dumps(
            {"success": True, "summary": summary, "results": results},
            indent=2,
            ensure_ascii=False,
        )

    except Exception as e:
        return json.dumps(
            {"success": False, "error": f"批量格式化失败: {str(e)}"},
            indent=2,
            ensure_ascii=False,
        )


if __name__ == "__main__":
    # 测试用例
    test_python_code = """
import os,sys
def test():
    return 1+2
"""

    print("测试Python格式化:")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(test_python_code)
        temp_path = f.name

    try:
        result = format_code_professional(temp_path, "preview")
        print(result)
    finally:
        os.unlink(temp_path)
