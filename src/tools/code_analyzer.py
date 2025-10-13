"""
代码分析工具模块
实现代码模式识别、复杂度分析和依赖分析功能
"""

import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple
from collections import defaultdict, deque
import radon.metrics
import radon.complexity
from radon.complexity import cc_rank

from ..utils.logger import get_logger
from ..utils.config import get_config_manager


class CodeAnalysisError(Exception):
    """代码分析异常"""
    pass


class CodeAnalyzer:
    """代码分析器"""

    def __init__(self, config_manager=None):
        """
        初始化代码分析器

        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 反模式定义
        self.anti_patterns = {
            'long_method': {
                'threshold': 20,  # 最大行数
                'description': '方法过长，超过20行'
            },
            'long_parameter_list': {
                'threshold': 5,  # 最大参数数量
                'description': '参数列表过长，超过5个参数'
            },
            'large_class': {
                'threshold': 200,  # 最大类行数
                'description': '类过大，超过200行'
            },
            'deeply_nested': {
                'threshold': 4,  # 最大嵌套深度
                'description': '嵌套过深，超过4层'
            },
            'duplicate_code': {
                'threshold': 5,  # 相似代码行数阈值
                'description': '可能存在重复代码'
            },
            'magic_numbers': {
                'pattern': r'\b(?!1|0|2|10|100)\d{2,}\b',  # 魔法数字模式
                'description': '发现魔法数字，应使用常量替代'
            },
            'god_object': {
                'method_threshold': 15,  # 方法数量阈值
                'description': '可能是上帝对象，方法过多'
            },
            'feature_envy': {
                'import_threshold': 10,  # 导入其他模块类/函数数量阈值
                'description': '可能存在特性嫉妒，过度依赖其他模块'
            }
        }

        # 依赖图
        self.dependency_graph = defaultdict(set)

    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """
        分析Python文件

        Args:
            file_path: 文件路径

        Returns:
            分析结果字典

        Raises:
            CodeAnalysisError: 文件分析失败
        """
        file_path = Path(file_path)

        # 检查文件是否存在
        if not file_path.exists():
            raise CodeAnalysisError(f"File does not exist: {file_path}")

        # 检查是否为Python文件
        if file_path.suffix != ".py":
            raise CodeAnalysisError(f"File is not a Python file: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            # 解析AST
            try:
                tree = ast.parse(source_code)
            except SyntaxError as e:
                raise CodeAnalysisError(f"Syntax error in {file_path}: {e}")

            # 执行各项分析
            result = {
                "file_path": str(file_path),
                "complexity": self._analyze_complexity(tree, source_code),
                "anti_patterns": self._detect_anti_patterns(tree, source_code),
                "dependencies": self._analyze_dependencies(tree, file_path),
                "quality_metrics": self._calculate_quality_metrics(tree, source_code),
                "import_analysis": self._analyze_imports(tree)
            }

            self.logger.debug(f"Code analysis completed: {file_path}")
            return result

        except Exception as e:
            raise CodeAnalysisError(f"Code analysis failed: {e}")

    def _analyze_complexity(self, tree: ast.AST, source_code: str) -> Dict[str, Any]:
        """分析代码复杂度"""
        complexity_result = {
            "cyclomatic_complexity": {},
            "maintainability_index": 0,
            "halstead_metrics": {},
            "loc_metrics": {}
        }

        # 圈复杂度分析
        try:
            cc = radon.complexity.cc_visit(tree)
            for item in cc:
                complexity_result["cyclomatic_complexity"][item.name] = {
                    "complexity": item.complexity,
                    "rank": cc_rank(item.complexity),
                    "line": item.lineno,
                    "endline": getattr(item, 'endline', item.lineno)
                }
        except Exception as e:
            self.logger.warning(f"Cyclomatic complexity analysis failed: {e}")

        # 可维护性指数
        try:
            mi = radon.metrics.mi_visit(tree, source_code)
            complexity_result["maintainability_index"] = mi
        except Exception as e:
            self.logger.warning(f"Maintainability index analysis failed: {e}")

        # Halstead指标
        try:
            h_metrics = radon.metrics.h_visit(tree)
            complexity_result["halstead_metrics"] = {
                "difficulty": h_metrics.difficulty,
                "effort": h_metrics.effort,
                "time": h_metrics.time,
                "bugs": h_metrics.bugs,
                "length": h_metrics.length,
                "vocabulary": h_metrics.vocabulary,
                "volume": h_metrics.volume
            }
        except Exception as e:
            self.logger.warning(f"Halstead metrics analysis failed: {e}")

        # 代码行数指标
        try:
            loc_metrics = radon.metrics.raw_functions(source_code)
            complexity_result["loc_metrics"] = {
                "loc": len(source_code.splitlines()),
                "lloc": loc_metrics.get('lloc', 0),
                "sloc": loc_metrics.get('sloc', 0),
                "comments": loc_metrics.get('comments', 0),
                "multi": loc_metrics.get('multi', 0),
                "blank": loc_metrics.get('blank', 0)
            }
        except Exception as e:
            self.logger.warning(f"LOC metrics analysis failed: {e}")

        return complexity_result

    def _detect_anti_patterns(self, tree: ast.AST, source_code: str) -> List[Dict[str, Any]]:
        """检测反模式"""
        anti_patterns = []

        # 获取源码行列表
        lines = source_code.splitlines()

        # 遍历AST节点检测反模式
        for node in ast.walk(tree):
            # 长方法检测
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_info = self._check_long_method(node, lines)
                if method_info:
                    anti_patterns.append(method_info)

                # 长参数列表检测
                param_info = self._check_long_parameter_list(node)
                if param_info:
                    anti_patterns.append(param_info)

            # 深度嵌套检测
            nested_info = self._check_deeply_nested(node, lines)
            if nested_info:
                anti_patterns.append(nested_info)

            # 魔法数字检测
            magic_info = self._check_magic_numbers(node, lines)
            if magic_info:
                anti_patterns.extend(magic_info)

        # 大类检测
        class_info = self._check_large_class(tree, lines)
        if class_info:
            anti_patterns.append(class_info)

        # 上帝对象检测
        god_object_info = self._check_god_object(tree)
        if god_object_info:
            anti_patterns.append(god_object_info)

        # 特性嫉妒检测
        feature_envy_info = self._check_feature_envy(tree)
        if feature_envy_info:
            anti_patterns.append(feature_envy_info)

        # 重复代码检测（简化版）
        duplicate_info = self._check_duplicate_code(lines)
        if duplicate_info:
            anti_patterns.extend(duplicate_info)

        return anti_patterns

    def _check_long_method(self, node: ast.FunctionDef, lines: List[str]) -> Optional[Dict[str, Any]]:
        """检查长方法"""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        # 计算方法行数
        end_line = getattr(node, 'end_lineno', node.lineno)
        method_lines = end_line - node.lineno + 1

        if method_lines > self.anti_patterns['long_method']['threshold']:
            return {
                "type": "long_method",
                "name": node.name,
                "line": node.lineno,
                "end_line": end_line,
                "lines_count": method_lines,
                "threshold": self.anti_patterns['long_method']['threshold'],
                "description": self.anti_patterns['long_method']['description'],
                "severity": "medium" if method_lines < 30 else "high"
            }
        return None

    def _check_long_parameter_list(self, node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """检查长参数列表"""
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return None

        param_count = len(node.args.args)
        if param_count > self.anti_patterns['long_parameter_list']['threshold']:
            return {
                "type": "long_parameter_list",
                "name": node.name,
                "line": node.lineno,
                "parameter_count": param_count,
                "threshold": self.anti_patterns['long_parameter_list']['threshold'],
                "description": self.anti_patterns['long_parameter_list']['description'],
                "severity": "low" if param_count < 8 else "medium"
            }
        return None

    def _check_large_class(self, tree: ast.AST, lines: List[str]) -> Optional[Dict[str, Any]]:
        """检查大类"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 计算类行数
                end_line = getattr(node, 'end_lineno', node.lineno)
                class_lines = end_line - node.lineno + 1

                if class_lines > self.anti_patterns['large_class']['threshold']:
                    return {
                        "type": "large_class",
                        "name": node.name,
                        "line": node.lineno,
                        "end_line": end_line,
                        "lines_count": class_lines,
                        "threshold": self.anti_patterns['large_class']['threshold'],
                        "description": self.anti_patterns['large_class']['description'],
                        "severity": "medium" if class_lines < 300 else "high"
                    }
        return None

    def _check_deeply_nested(self, node: ast.AST, lines: List[str]) -> Optional[Dict[str, Any]]:
        """检查深度嵌套"""
        def get_nesting_depth(node):
            depth = 0
            current = node

            while hasattr(current, 'parent'):
                if isinstance(current.parent, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                    depth += 1
                current = current.parent
            return depth

        # 为节点设置父节点引用
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                child.parent = parent

        max_depth = 0
        max_depth_node = None

        for current_node in ast.walk(tree):
            if isinstance(current_node, (ast.If, ast.While, ast.For, ast.With, ast.Try)):
                depth = get_nesting_depth(current_node)
                if depth > max_depth:
                    max_depth = depth
                    max_depth_node = current_node

        if max_depth > self.anti_patterns['deeply_nested']['threshold']:
            return {
                "type": "deeply_nested",
                "line": max_depth_node.lineno if max_depth_node else 0,
                "nesting_depth": max_depth,
                "threshold": self.anti_patterns['deeply_nested']['threshold'],
                "description": self.anti_patterns['deeply_nested']['description'],
                "severity": "medium" if max_depth < 6 else "high"
            }
        return None

    def _check_magic_numbers(self, node: ast.AST, lines: List[str]) -> List[Dict[str, Any]]:
        """检查魔法数字"""
        magic_numbers = []

        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            # 检查是否匹配魔法数字模式
            pattern = re.compile(self.anti_patterns['magic_numbers']['pattern'])
            if pattern.match(str(node.value)):
                magic_numbers.append({
                    "type": "magic_numbers",
                    "line": node.lineno,
                    "value": node.value,
                    "description": self.anti_patterns['magic_numbers']['description'],
                    "severity": "low"
                })

        return magic_numbers

    def _check_god_object(self, tree: ast.AST) -> Optional[Dict[str, Any]]:
        """检查上帝对象"""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # 统计方法数量
                method_count = sum(1 for child in node.body
                                 if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)))

                if method_count > self.anti_patterns['god_object']['method_threshold']:
                    return {
                        "type": "god_object",
                        "name": node.name,
                        "line": node.lineno,
                        "method_count": method_count,
                        "threshold": self.anti_patterns['god_object']['method_threshold'],
                        "description": self.anti_patterns['god_object']['description'],
                        "severity": "medium" if method_count < 25 else "high"
                    }
        return None

    def _check_feature_envy(self, tree: ast.AST) -> Optional[Dict[str, Any]]:
        """检查特性嫉妒"""
        external_dependencies = defaultdict(int)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    external_dependencies[alias.name] += 1
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    external_dependencies[node.module] += 1

        # 统计外部依赖
        total_external_deps = len(external_dependencies)

        if total_external_deps > self.anti_patterns['feature_envy']['import_threshold']:
            return {
                "type": "feature_envy",
                "line": 1,
                "external_dependencies": total_external_deps,
                "threshold": self.anti_patterns['feature_envy']['import_threshold'],
                "dependencies": list(external_dependencies.keys()),
                "description": self.anti_patterns['feature_envy']['description'],
                "severity": "low" if total_external_deps < 15 else "medium"
            }
        return None

    def _check_duplicate_code(self, lines: List[str]) -> List[Dict[str, Any]]:
        """检查重复代码（简化版）"""
        duplicates = []
        code_blocks = defaultdict(list)

        # 简单的行相似度检测
        for i, line in enumerate(lines, 1):
            if len(line.strip()) > 10:  # 忽略短行
                # 简单规范化：移除空格和制表符
                normalized = re.sub(r'\s+', '', line.strip())
                code_blocks[normalized].append(i)

        # 查找重复的代码块
        for normalized, line_numbers in code_blocks.items():
            if len(line_numbers) > 1:
                duplicates.append({
                    "type": "duplicate_code",
                    "lines": line_numbers,
                    "count": len(line_numbers),
                    "pattern": normalized[:50] + "..." if len(normalized) > 50 else normalized,
                    "description": self.anti_patterns['duplicate_code']['description'],
                    "severity": "low"
                })

        return duplicates

    def _analyze_dependencies(self, tree: ast.AST, file_path: Path) -> Dict[str, Any]:
        """分析模块依赖"""
        dependencies = {
            "imports": [],
            "internal_dependencies": [],
            "external_dependencies": [],
            "dependency_graph": {}
        }

        # 收集导入信息
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies["imports"].append({
                        "module": alias.name,
                        "alias": alias.asname,
                        "line": node.lineno
                    })

            elif isinstance(node, ast.ImportFrom):
                dependencies["imports"].append({
                    "module": node.module or "",
                    "names": [alias.name for alias in node.names],
                    "line": node.lineno
                })

        # 构建依赖图
        file_module = file_path.stem
        self.dependency_graph[file_module] = set()

        for imp in dependencies["imports"]:
            module_name = imp["module"]
            if module_name and not module_name.startswith('.'):
                self.dependency_graph[file_module].add(module_name)

        dependencies["dependency_graph"] = {
            node: list(deps) for node, deps in self.dependency_graph.items()
        }

        return dependencies

    def _calculate_quality_metrics(self, tree: ast.AST, source_code: str) -> Dict[str, Any]:
        """计算代码质量指标"""
        metrics = {
            "functions_count": 0,
            "classes_count": 0,
            "lines_of_code": len(source_code.splitlines()),
            "comment_ratio": 0,
            "average_function_length": 0,
            "max_function_length": 0
        }

        functions_lengths = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                metrics["functions_count"] += 1
                end_line = getattr(node, 'end_lineno', node.lineno)
                func_length = end_line - node.lineno + 1
                functions_lengths.append(func_length)
                metrics["max_function_length"] = max(metrics["max_function_length"], func_length)

            elif isinstance(node, ast.ClassDef):
                metrics["classes_count"] += 1

        # 计算平均函数长度
        if functions_lengths:
            metrics["average_function_length"] = sum(functions_lengths) / len(functions_lengths)

        # 计算注释比例
        comment_lines = 0
        for line in source_code.splitlines():
            if line.strip().startswith('#'):
                comment_lines += 1

        if metrics["lines_of_code"] > 0:
            metrics["comment_ratio"] = comment_lines / metrics["lines_of_code"]

        return metrics

    def _analyze_imports(self, tree: ast.AST) -> Dict[str, Any]:
        """分析导入语句"""
        import_analysis = {
            "standard_library_imports": [],
            "third_party_imports": [],
            "local_imports": [],
            "unused_imports": [],
            "import_complexity": 0
        }

        # 标准库模块列表（简化版）
        stdlib_modules = {
            'os', 'sys', 'json', 're', 'datetime', 'collections',
            'math', 'random', 'itertools', 'functools', 'operator',
            'pathlib', 'urllib', 'http', 'socket', 'threading',
            'multiprocessing', 'asyncio', 'logging', 'unittest'
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split('.')[0]
                    if module_name in stdlib_modules:
                        import_analysis["standard_library_imports"].append(alias.name)
                    else:
                        import_analysis["third_party_imports"].append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_name = node.module.split('.')[0]
                    if module_name in stdlib_modules:
                        import_analysis["standard_library_imports"].append(node.module)
                    elif node.module.startswith('.'):
                        import_analysis["local_imports"].append(node.module)
                    else:
                        import_analysis["third_party_imports"].append(node.module)

        # 计算导入复杂度
        total_imports = (len(import_analysis["standard_library_imports"]) +
                        len(import_analysis["third_party_imports"]) +
                        len(import_analysis["local_imports"]))
        import_analysis["import_complexity"] = total_imports

        return import_analysis

    def build_dependency_graph(self, files: List[Path]) -> Dict[str, Any]:
        """
        构建多文件依赖图

        Args:
            files: 文件列表

        Returns:
            依赖图分析结果
        """
        # 清空依赖图
        self.dependency_graph.clear()

        # 分析每个文件
        for file_path in files:
            if file_path.exists() and file_path.suffix == ".py":
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    tree = ast.parse(source_code)
                    self._analyze_dependencies(tree, file_path)
                except Exception as e:
                    self.logger.warning(f"Failed to analyze dependencies for {file_path}: {e}")

        # 分析图的特性
        graph_analysis = {
            "nodes": len(self.dependency_graph),
            "edges": sum(len(deps) for deps in self.dependency_graph.values()),
            "graph": {node: list(deps) for node, deps in self.dependency_graph.items()},
            "most_connected": self._find_most_connected_nodes(),
            "circular_dependencies": self._detect_circular_dependencies(),
            "dependency_levels": self._calculate_dependency_levels()
        }

        return graph_analysis

    def _find_most_connected_nodes(self) -> List[Dict[str, Any]]:
        """找到连接度最高的节点"""
        connections = [(node, len(deps)) for node, deps in self.dependency_graph.items()]
        connections.sort(key=lambda x: x[1], reverse=True)

        return [
            {"node": node, "dependencies": deps}
            for node, deps in connections[:5]
        ]

    def _detect_circular_dependencies(self) -> List[List[str]]:
        """检测循环依赖"""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            if node in rec_stack:
                # 找到循环
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.dependency_graph.get(node, []):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for node in self.dependency_graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def _calculate_dependency_levels(self) -> Dict[str, int]:
        """计算依赖层级"""
        levels = {}
        visited = set()

        def calculate_level(node):
            if node in visited:
                return levels.get(node, 0)

            visited.add(node)
            max_dep_level = 0

            for dep in self.dependency_graph.get(node, []):
                max_dep_level = max(max_dep_level, calculate_level(dep))

            levels[node] = max_dep_level + 1
            return levels[node]

        for node in self.dependency_graph:
            calculate_level(node)

        return levels

    def assess_change_impact(self, file_path: Path, changed_items: List[str]) -> Dict[str, Any]:
        """
        评估修改影响范围

        Args:
            file_path: 修改的文件路径
            changed_items: 修改的项目列表（函数、类等）

        Returns:
            影响范围评估结果
        """
        file_module = file_path.stem

        # 找到依赖该文件的其他文件
        dependents = []
        for node, deps in self.dependency_graph.items():
            if file_module in deps:
                dependents.append(node)

        # 评估影响范围
        impact_assessment = {
            "file_path": str(file_path),
            "changed_items": changed_items,
            "direct_dependents": dependents,
            "impact_score": 0,
            "risk_level": "low",
            "recommendations": []
        }

        # 计算影响评分
        impact_score = len(dependents) * 10  # 基础分数
        impact_score += len(changed_items) * 5  # 修改项目数量

        # 考虑依赖者的依赖数量
        for dependent in dependents:
            impact_score += len(self.dependency_graph.get(dependent, [])) * 2

        impact_assessment["impact_score"] = impact_score

        # 确定风险等级
        if impact_score < 30:
            impact_assessment["risk_level"] = "low"
        elif impact_score < 70:
            impact_assessment["risk_level"] = "medium"
        else:
            impact_assessment["risk_level"] = "high"

        # 生成建议
        if impact_assessment["risk_level"] == "high":
            impact_assessment["recommendations"].append("建议进行回归测试")
            impact_assessment["recommendations"].append("考虑创建接口隔离变化")

        if dependents:
            impact_assessment["recommendations"].append(f"需要测试 {len(dependents)} 个依赖文件")

        return impact_assessment