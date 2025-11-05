"""
AST静态分析工具模块
集成Python ast模块，实现基础语法分析和问题检测
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..utils.config import get_config_manager
from ..utils.logger import get_logger


class ASTAnalysisError(Exception):
    """AST分析异常"""

    pass


class ASTAnalyzer:
    """AST静态分析器"""

    def __init__(self, config_manager=None):
        """
        初始化AST分析器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 获取配置
        static_config = self.config_manager.get_section("static_analysis")
        ast_config = static_config.get("ast", {})
        self.max_file_size = ast_config.get("max_file_size", 1024 * 1024)  # 1MB

    def analyze_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        分析Python文件

        Args:
            file_path: 文件路径

        Returns:
            分析结果字典

        Raises:
            ASTAnalysisError: 文件分析失败
        """
        file_path = Path(file_path)

        # 检查文件是否存在
        if not file_path.exists():
            raise ASTAnalysisError(f"File does not exist: {file_path}")

        # 检查是否为Python文件
        if file_path.suffix != ".py":
            raise ASTAnalysisError(f"File is not a Python file: {file_path}")

        # 检查文件大小
        if file_path.stat().st_size > self.max_file_size:
            raise ASTAnalysisError(
                f"File too large, exceeds limit {self.max_file_size} bytes"
            )

        try:
            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 解析AST
            tree = ast.parse(content, filename=str(file_path))

            # 执行分析
            result = {
                "file_path": str(file_path),
                "errors": [],
                "functions": [],
                "classes": [],
                "variables": [],
                "imports": [],
            }

            # 收集分析信息
            self._collect_functions(tree, result)
            self._collect_classes(tree, result)
            self._collect_variables(tree, result)
            self._collect_imports(tree, result)
            self._calculate_complexity(tree, result)

            self.logger.debug(f"AST分析完成: {file_path}")
            return result

        except SyntaxError as e:
            # 处理语法错误
            error_msg = f"Syntax error: {e.msg} (line {e.lineno})"
            self.logger.warning(f"AST syntax error {file_path}: {error_msg}")
            return {
                "file_path": str(file_path),
                "errors": [
                    {
                        "type": "Syntax Error",
                        "message": error_msg,
                        "line": e.lineno,
                        "column": e.offset,
                    }
                ],
                "functions": [],
                "classes": [],
                "variables": [],
                "imports": [],
            }

        except UnicodeDecodeError as e:
            raise ASTAnalysisError(f"File encoding error: {e}")

        except Exception as e:
            raise ASTAnalysisError(f"AST analysis failed: {e}")

    def _collect_functions(self, tree: ast.AST, result: Dict[str, Any]):
        """收集函数定义信息（只收集模块级别函数，不包含类方法）"""
        # 首先收集所有类的行号范围
        class_line_ranges = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 添加类定义的所有行号
                class_line_ranges.update(
                    range(node.lineno, node.end_lineno or node.lineno)
                )

        # 然后收集不在类中的函数
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # 检查函数是否在类中
                if node.lineno not in class_line_ranges:
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "defaults": len(node.args.defaults),
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "docstring": ast.get_docstring(node),
                        "complexity": 1,  # 基础复杂度
                    }
                    result["functions"].append(func_info)

    def _collect_classes(self, tree: ast.AST, result: Dict[str, Any]):
        """收集类定义信息"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 提取基类
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(f"{base.value.id}.{base.attr}")

                # 计算方法数量
                methods = [
                    n
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]

                class_info = {
                    "name": node.name,
                    "line": node.lineno,
                    "bases": bases,
                    "method_count": len(methods),
                    "docstring": ast.get_docstring(node),
                }
                result["classes"].append(class_info)

    def _collect_variables(self, tree: ast.AST, result: Dict[str, Any]):
        """收集变量定义信息（模块级别）"""
        for node in ast.walk(tree):
            # 只处理模块级别的变量
            if isinstance(node, ast.Module):
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                var_info = {
                                    "name": target.id,
                                    "line": stmt.lineno,
                                    "type": "assignment",
                                }
                                result["variables"].append(var_info)

    def _collect_imports(self, tree: ast.AST, result: Dict[str, Any]):
        """收集导入依赖信息"""
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_info = {
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                    result["imports"].append(import_info)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    import_info = {
                        "type": "from_import",
                        "module": module if module else alias.name,
                        "from_module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno,
                    }
                    result["imports"].append(import_info)

    def _calculate_complexity(self, tree: ast.AST, result: Dict[str, Any]):
        """计算圈复杂度"""
        # 为每个函数计算复杂度
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = self._calculate_node_complexity(node)

                # 更新对应函数的复杂度
                for func in result["functions"]:
                    if func["name"] == node.name and func["line"] == node.lineno:
                        func["complexity"] = complexity
                        break

    def _calculate_node_complexity(self, node: ast.AST) -> int:
        """计算节点的圈复杂度"""
        complexity = 1  # 基础复杂度

        for child in ast.walk(node):
            if isinstance(
                child,
                (ast.If, ast.For, ast.While, ast.With, ast.AsyncFor, ast.AsyncWith),
            ):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1

        return complexity

    def get_analysis_summary(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取分析摘要

        Args:
            result: 分析结果

        Returns:
            分析摘要字典
        """
        summary = {
            "file_path": result["file_path"],
            "total_functions": len(result["functions"]),
            "total_classes": len(result["classes"]),
            "total_variables": len(result["variables"]),
            "total_imports": len(result["imports"]),
            "max_complexity": 0,
            "error_count": len(result["errors"]),
            "has_errors": len(result["errors"]) > 0,
        }

        # 计算最大复杂度
        if result["functions"]:
            summary["max_complexity"] = max(
                func["complexity"] for func in result["functions"]
            )

        return summary
