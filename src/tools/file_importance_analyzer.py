"""
文件重要性评估器
File Importance Analyzer

基于多种因素评估文件在项目中的重要性，支持智能文件选择
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import os
import ast
import re
from datetime import datetime
from dataclasses import dataclass
import json

from ..utils.logger import get_logger
from ..utils.config import get_config_manager
from .project_analysis_types import FileImportanceScore, FileCategory
from .project_analysis_config import get_project_analysis_config
from .static_coordinator import AnalysisIssue


class FileImportanceAnalyzer:
    """文件重要性评估器

    基于多种因素评估文件在项目中的重要性，包括：
    - 静态分析问题密度
    - 文件复杂度
    - 依赖关系
    - 变更频率
    - 业务逻辑重要性
    """

    def __init__(self, config=None):
        """初始化文件重要性评估器

        Args:
            config: 项目分析配置，如果为None则使用默认配置
        """
        self.config = config or get_project_analysis_config()
        self.logger = get_logger()
        self._weights = self.config.importance_scoring.weights
        self._complexity_thresholds = self.config.importance_scoring.complexity_thresholds
        self._issue_density_thresholds = self.config.importance_scoring.issue_density_thresholds

        # 初始化权重配置
        self._initialize_default_weights()

        self.logger.debug("FileImportanceAnalyzer初始化完成",
                         weights=self._weights,
                         complexity_thresholds=self._complexity_thresholds,
                         issue_density_thresholds=self._issue_density_thresholds)

    def _initialize_default_weights(self):
        """初始化默认权重配置"""
        if not self._weights:
            self._weights = {
                'complexity': 0.25,
                'issue_density': 0.30,
                'dependency': 0.20,
                'change_frequency': 0.15,
                'business_logic': 0.10
            }

        if not self._complexity_thresholds:
            self._complexity_thresholds = {
                'simple': 5,
                'medium': 15,
                'high': 30
            }

        if not self._issue_density_thresholds:
            self._issue_density_thresholds = {
                'low': 1,
                'medium': 3,
                'high': 5
            }

    def analyze_file_importance(self,
                              file_path: str,
                              static_issues: Optional[List[AnalysisIssue]] = None,
                              project_context: Optional[Dict[str, Any]] = None) -> FileImportanceScore:
        """分析单个文件的重要性

        Args:
            file_path: 文件路径
            static_issues: 静态分析问题列表
            project_context: 项目上下文信息

        Returns:
            文件重要性评分对象
        """
        self.logger.debug(f"开始分析文件重要性: {file_path}")

        # 创建基础评分对象
        file_path_obj = Path(file_path)
        importance_score = FileImportanceScore(
            file_path=str(file_path_obj.absolute()),
            file_name=file_path_obj.name,
            file_category=self._determine_file_category(file_path_obj),
            file_size=self._get_file_size(file_path),
            weights=self._weights.copy()
        )

        # 分析各种评分因子
        self._analyze_complexity(importance_score, file_path)
        self._analyze_issue_density(importance_score, static_issues or [])
        self._analyze_dependencies(importance_score, file_path, project_context)
        self._analyze_change_frequency(importance_score, file_path, project_context)
        self._analyze_business_logic_importance(importance_score, file_path, project_context)

        # 计算综合评分
        self._calculate_overall_score(importance_score)

        self.logger.debug(f"文件重要性分析完成: {file_path}",
                         overall_score=importance_score.overall_score,
                         complexity_score=importance_score.complexity_score,
                         issue_density_score=importance_score.issue_density_score,
                         dependency_score=importance_score.dependency_score)

        return importance_score

    def _determine_file_category(self, file_path: Path) -> FileCategory:
        """确定文件分类"""
        # 基于文件扩展名和路径模式判断文件类别
        name = file_path.name.lower()
        path_str = str(file_path).lower()

        # 测试文件
        if any(pattern in name or pattern in path_str for pattern in ['test', 'spec']):
            return FileCategory.TEST

        # 配置文件
        config_extensions = {'.yaml', '.yml', '.json', '.toml', '.ini', '.cfg', '.conf'}
        config_patterns = {'config', 'settings', 'env', 'dockerfile'}
        if (file_path.suffix in config_extensions or
            any(pattern in name for pattern in config_patterns)):
            return FileCategory.CONFIG

        # 文档文件
        doc_extensions = {'.md', '.rst', '.txt', '.doc', '.pdf', '.html'}
        if file_path.suffix in doc_extensions:
            return FileCategory.DOCUMENTATION

        # 构建文件
        build_patterns = {'makefile', 'cmake', 'build', 'webpack', 'gulp', 'grunt'}
        if any(pattern in name for pattern in build_patterns):
            return FileCategory.BUILD

        # 部署文件
        deploy_patterns = {'deploy', 'k8s', 'kubernetes', 'docker'}
        if any(pattern in path_str for pattern in deploy_patterns):
            return FileCategory.DEPLOYMENT

        # 源代码文件（默认）
        return FileCategory.SOURCE

    def _get_file_size(self, file_path: str) -> int:
        """获取文件大小"""
        try:
            return os.path.getsize(file_path)
        except OSError:
            self.logger.warning(f"无法获取文件大小: {file_path}")
            return 0

    def _analyze_complexity(self, importance_score: FileImportanceScore, file_path: str):
        """分析文件复杂度

        基于多个维度计算文件复杂度评分：
        1. 代码行数和结构复杂度
        2. 圈复杂度和控制流复杂度
        3. 函数和类的复杂度分析
        4. 代码嵌套深度分析
        5. 代码重复度分析
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 基础指标
            lines = content.splitlines()
            non_empty_lines = [line for line in lines if line.strip()]
            comment_lines = [line for line in lines if line.strip().startswith('#')]
            importance_score.lines_of_code = len(non_empty_lines) - len(comment_lines)

            # AST分析
            if file_path.endswith('.py'):
                self._analyze_python_complexity(importance_score, content)
            else:
                # 对于其他语言类型的简单启发式分析
                self._analyze_generic_complexity(importance_score, content)

            # 高级复杂度分析
            nesting_depth = self._analyze_nesting_depth(file_path, content)
            code_duplication = self._analyze_code_duplication(content)
            parameter_complexity = self._analyze_parameter_complexity(file_path, content)

            # 计算复杂度评分 (0-100)
            # 基础复杂度分数
            base_score = min(40, importance_score.cyclomatic_complexity * 1.5)

            # 结构复杂度分数
            structure_score = min(30, (importance_score.function_count * 2 + importance_score.class_count * 3))

            # 规模复杂度分数
            loc_score = min(20, importance_score.lines_of_code / 50)  # 每50行1分，最多20分

            # 嵌套深度分数
            nesting_score = min(15, nesting_depth * 3)

            # 参数复杂度分数
            param_score = min(10, parameter_complexity)

            # 代码重复度分数（重复度越高，复杂度分数越高）
            duplication_score = min(10, code_duplication * 5)

            # 综合复杂度评分
            raw_complexity_score = (
                base_score + structure_score + loc_score +
                nesting_score + param_score + duplication_score
            )

            # 根据文件大小调整评分（避免小文件获得不公平的高分）
            size_adjustment = self._calculate_size_adjustment(importance_score.lines_of_code)
            final_score = raw_complexity_score * size_adjustment

            importance_score.complexity_score = min(100.0, round(final_score, 2))

            self.logger.debug(f"复杂度分析完成: {importance_score.file_name}",
                            complexity_score=importance_score.complexity_score,
                            cyclomatic_complexity=importance_score.cyclomatic_complexity,
                            function_count=importance_score.function_count,
                            class_count=importance_score.class_count,
                            nesting_depth=nesting_depth,
                            lines_of_code=importance_score.lines_of_code)

        except Exception as e:
            self.logger.error(f"分析文件复杂度失败: {file_path}", error=str(e))
            importance_score.complexity_score = 0.0

    def _analyze_python_complexity(self, importance_score: FileImportanceScore, content: str):
        """分析Python文件复杂度"""
        try:
            tree = ast.parse(content)

            # 统计函数和类
            importance_score.function_count = len([node for node in ast.walk(tree)
                                                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))])
            importance_score.class_count = len([node for node in ast.walk(tree)
                                              if isinstance(node, ast.ClassDef)])

            # 简单的圈复杂度计算（基于决策点）
            complexity_nodes = [ast.If, ast.For, ast.While, ast.With, ast.Try,
                              ast.ExceptHandler, ast.BoolOp, ast.ListComp]
            importance_score.cyclomatic_complexity = len([node for node in ast.walk(tree)
                                                        if type(node) in complexity_nodes])

        except SyntaxError as e:
            self.logger.warning(f"Python语法错误，使用简单分析: {e}")
            self._analyze_generic_complexity(importance_score, content)

    def _analyze_generic_complexity(self, importance_score: FileImportanceScore, content: str):
        """通用复杂度分析（适用于非Python文件）"""
        lines = content.splitlines()

        # 简单启发式方法
        function_patterns = [r'function\s+\w+', r'def\s+\w+', r'\w+\s*\([^)]*\)\s*{']
        class_patterns = [r'class\s+\w+', r'struct\s+\w+', r'type\s+\w+']

        for line in lines:
            line = line.strip()
            for pattern in function_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    importance_score.function_count += 1
            for pattern in class_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    importance_score.class_count += 1

        # 简单的复杂度估算
        control_flow_patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b', r'\btry\b', r'\bcatch\b']
        complexity_count = 0
        for line in lines:
            for pattern in control_flow_patterns:
                complexity_count += len(re.findall(pattern, line, re.IGNORECASE))

        importance_score.cyclomatic_complexity = complexity_count

    def _analyze_issue_density(self, importance_score: FileImportanceScore, static_issues: List[AnalysisIssue]):
        """分析问题密度

        基于静态分析结果计算问题密度评分，考虑：
        1. 问题数量与代码行数的比例
        2. 问题严重程度的权重
        3. 问题类型的多样性
        4. 问题集中度分析
        """
        if not static_issues:
            importance_score.issue_density_score = 0.0
            return

        # 统计问题数量和严重程度
        importance_score.total_issues = len(static_issues)
        importance_score.error_count = len([issue for issue in static_issues if issue.severity.value == 'error'])
        importance_score.warning_count = len([issue for issue in static_issues if issue.severity.value == 'warning'])
        importance_score.critical_issues = len([issue for issue in static_issues if issue.severity.value == 'critical'])

        # 计算加权问题分数（严重程度权重）
        critical_weight = 4.0
        error_weight = 3.0
        warning_weight = 2.0
        info_weight = 1.0

        weighted_score = (
            importance_score.critical_issues * critical_weight +
            importance_score.error_count * error_weight +
            importance_score.warning_count * warning_weight +
            (importance_score.total_issues - importance_score.critical_issues -
             importance_score.error_count - importance_score.warning_count) * info_weight
        )

        # 计算问题密度（每100行代码的加权问题数）
        if importance_score.lines_of_code > 0:
            # 基础密度：加权问题数 / 代码行数 * 100
            base_density = (weighted_score / importance_score.lines_of_code) * 100

            # 问题类型多样性因子
            issue_types = set(issue.issue_type for issue in static_issues if issue.issue_type)
            diversity_factor = min(1.5, 1.0 + (len(issue_types) - 1) * 0.1)  # 最多增加50%分数

            # 问题集中度分析（问题是否集中在少数几行）
            line_numbers = [issue.line for issue in static_issues if issue.line > 0]
            concentration_factor = 1.0
            if len(line_numbers) > 1:
                line_range = max(line_numbers) - min(line_numbers) + 1
                if line_range < len(line_numbers) * 2:  # 问题比较集中
                    concentration_factor = 1.2

            # 调整后的密度分数
            adjusted_density = base_density * diversity_factor * concentration_factor

            # 根据密度阈值计算评分（使用更细粒度的评分）
            if adjusted_density <= self._issue_density_thresholds['low']:
                importance_score.issue_density_score = min(30.0, adjusted_density * 10)  # 低密度
            elif adjusted_density <= self._issue_density_thresholds['medium']:
                # 中等密度：线性插值
                low_threshold = self._issue_density_thresholds['low']
                medium_threshold = self._issue_density_thresholds['medium']
                ratio = (adjusted_density - low_threshold) / (medium_threshold - low_threshold)
                importance_score.issue_density_score = 30.0 + ratio * 30.0  # 30-60分
            elif adjusted_density <= self._issue_density_thresholds['high']:
                # 高密度：线性插值
                medium_threshold = self._issue_density_thresholds['medium']
                high_threshold = self._issue_density_thresholds['high']
                ratio = (adjusted_density - medium_threshold) / (high_threshold - medium_threshold)
                importance_score.issue_density_score = 60.0 + ratio * 25.0  # 60-85分
            else:
                # 极高密度：对数增长避免分数过高
                excess = adjusted_density - self._issue_density_thresholds['high']
                importance_score.issue_density_score = min(100.0, 85.0 + min(15.0, excess * 2))

            # 如果有严重问题，额外加分
            if importance_score.critical_issues > 0:
                critical_bonus = min(10.0, importance_score.critical_issues * 2.0)
                importance_score.issue_density_score = min(100.0, importance_score.issue_density_score + critical_bonus)

        else:
            # 没有代码行数信息时，基于问题数量的简单评分
            if importance_score.total_issues == 0:
                importance_score.issue_density_score = 0.0
            elif importance_score.total_issues <= 3:
                importance_score.issue_density_score = 20.0
            elif importance_score.total_issues <= 10:
                importance_score.issue_density_score = 50.0
            elif importance_score.total_issues <= 20:
                importance_score.issue_density_score = 80.0
            else:
                importance_score.issue_density_score = 100.0

        # 记录详细的密度分析信息
        self.logger.debug(f"问题密度分析完成: {importance_score.file_name}",
                         total_issues=importance_score.total_issues,
                         weighted_score=weighted_score,
                         lines_of_code=importance_score.lines_of_code,
                         density_score=importance_score.issue_density_score,
                         critical_issues=importance_score.critical_issues,
                         error_count=importance_score.error_count)

    def _analyze_dependencies(self, importance_score: FileImportanceScore, file_path: str, project_context: Optional[Dict[str, Any]]):
        """分析依赖关系重要性

        基于多个维度计算依赖关系重要性评分：
        1. 被依赖数量（入度）
        2. 导入依赖数量（出度）
        3. 依赖网络中心性
        4. 模块层次结构位置
        5. 依赖稳定性分析
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 分析导入依赖
            imports = self._extract_imports(file_path, content)
            importance_score.imports_count = len(imports)

            # 从项目上下文中获取依赖信息
            dependency_graph = {}
            reverse_deps = []
            module_hierarchy = {}

            if project_context:
                dependency_graph = project_context.get('dependency_graph', {})
                reverse_deps = project_context.get('reverse_dependencies', [])
                module_hierarchy = project_context.get('module_hierarchy', {})

            # 计算被依赖数量（入度）
            if dependency_graph:
                importance_score.dependents_count = len([
                    dep for deps in dependency_graph.values()
                    for dep in deps if file_path in dep
                ])
            elif reverse_deps:
                importance_score.dependents_count = len(reverse_deps.get(file_path, []))

            # 分析依赖网络特征
            centrality_score = self._calculate_dependency_centrality(file_path, dependency_graph)
            stability_score = self._calculate_dependency_stability(file_path, imports, dependency_graph)
            hierarchy_score = self._calculate_hierarchy_importance(file_path, module_hierarchy)

            # 判断模块特征
            importance_score.is_core_module = self._is_core_module(file_path, project_context)
            importance_score.is_entry_point = self._is_entry_point(file_path, project_context)

            # 计算依赖关系评分 (0-100)
            dependency_score = 0

            # 被依赖数量评分（权重最高：40分）
            dependency_score += min(40, importance_score.dependents_count * 5)

            # 导入数量评分（20分）
            if 1 <= importance_score.imports_count <= 10:
                dependency_score += 20  # 适中依赖
            elif 11 <= importance_score.imports_count <= 20:
                dependency_score += 15  # 较多依赖
            elif importance_score.imports_count > 20:
                dependency_score += 10  # 很多依赖（可能过于复杂）
            else:
                dependency_score += 5   # 很少或无依赖

            # 网络中心性评分（20分）
            dependency_score += min(20, centrality_score)

            # 依赖稳定性评分（10分）
            dependency_score += min(10, stability_score)

            # 层次结构重要性评分（5分）
            dependency_score += min(5, hierarchy_score)

            # 模块特征加分（5分）
            if importance_score.is_core_module:
                dependency_score += 3
            if importance_score.is_entry_point:
                dependency_score += 2

            # 特殊模块类型加分
            if self._is_utility_module(file_path):
                dependency_score += 5  # 工具模块通常被广泛依赖
            if self._is_interface_module(file_path):
                dependency_score += 3  # 接口模块重要性高

            importance_score.dependency_score = min(100.0, round(dependency_score, 2))

            self.logger.debug(f"依赖关系分析完成: {importance_score.file_name}",
                            dependency_score=importance_score.dependency_score,
                            imports_count=importance_score.imports_count,
                            dependents_count=importance_score.dependents_count,
                            is_core_module=importance_score.is_core_module,
                            is_entry_point=importance_score.is_entry_point)

        except Exception as e:
            self.logger.error(f"分析依赖关系失败: {file_path}", error=str(e))
            importance_score.dependency_score = 0.0

    def _extract_imports(self, file_path: str, content: str) -> List[str]:
        """提取文件中的导入"""
        imports = []

        if file_path.endswith('.py'):
            # Python导入
            for match in re.finditer(r'^(?:from\s+(\S+)\s+)?import\s+(.+)', content, re.MULTILINE):
                if match.group(1):
                    imports.append(match.group(1))
                for imp in match.group(2).split(','):
                    imports.append(imp.strip().split('.')[0])
        else:
            # 通用导入模式（JavaScript, Java等）
            patterns = [
                r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
                r'require\([\'"]([^\'"]+)[\'"]\)',
                r'import\s+[\'"]([^\'"]+)[\'"]'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)

        return list(set(imports))  # 去重

    def _is_core_module(self, file_path: str, project_context: Optional[Dict[str, Any]]) -> bool:
        """判断是否为核心模块"""
        if not project_context:
            return False

        file_name = Path(file_path).name

        # 基于项目上下文判断
        if 'core_modules' in project_context:
            core_modules = project_context['core_modules']
            return any(core in file_path or file_name == core for core in core_modules)

        # 基于常见模式判断
        core_patterns = ['core', 'main', 'base', 'common', 'utils', 'lib']
        return any(pattern in file_path.lower() for pattern in core_patterns)

    def _is_entry_point(self, file_path: str, project_context: Optional[Dict[str, Any]]) -> bool:
        """判断是否为入口点"""
        file_name = Path(file_path).name

        # 常见入口点文件
        entry_patterns = [
            'main.py', 'app.py', 'index.js', 'server.js',
            '__init__.py', 'setup.py', 'manage.py'
        ]

        if file_name in entry_patterns:
            return True

        # 基于项目上下文判断
        if project_context and 'entry_points' in project_context:
            return file_path in project_context['entry_points']

        return False

    def _analyze_change_frequency(self, importance_score: FileImportanceScore, file_path: str, project_context: Optional[Dict[str, Any]]):
        """分析变更频率"""
        # 这里可以集成Git历史分析
        # 暂时使用简单的启发式方法

        if project_context and 'git_history' in project_context:
            git_history = project_context['git_history']
            file_history = git_history.get(file_path, {})

            importance_score.commit_count = file_history.get('commit_count', 0)
            importance_score.authors_count = file_history.get('authors_count', 0)
            last_modified_str = file_history.get('last_modified')
            if last_modified_str:
                importance_score.last_modified = datetime.fromisoformat(last_modified_str)
        else:
            # 使用文件修改时间
            try:
                mtime = os.path.getmtime(file_path)
                importance_score.last_modified = datetime.fromtimestamp(mtime)
            except OSError:
                importance_score.last_modified = datetime.now()

        # 计算变更频率评分
        # 频繁变更的文件通常更重要
        time_since_modified = (datetime.now() - importance_score.last_modified).days
        recency_score = max(0, 30 - time_since_modified)  # 最近修改的文件得分更高

        commit_score = min(40, importance_score.commit_count * 2)
        author_score = min(30, importance_score.authors_count * 10)

        importance_score.change_frequency_score = min(100, recency_score + commit_score + author_score)

    def _analyze_business_logic_importance(self, importance_score: FileImportanceScore, file_path: str, project_context: Optional[Dict[str, Any]]):
        """分析业务逻辑重要性"""
        file_name = Path(file_path).name.lower()
        path_str = file_path.lower()

        score = 0

        # 基于路径和文件名判断业务重要性
        business_patterns = [
            'models', 'views', 'controllers', 'services', 'business',
            'logic', 'api', 'routes', 'handlers', 'managers'
        ]

        for pattern in business_patterns:
            if pattern in path_str:
                score += 20

        # 基于文件名判断
        important_names = ['user', 'auth', 'payment', 'order', 'product', 'admin']
        for name in important_names:
            if name in file_name:
                score += 15

        # 基于项目上下文判断
        if project_context and 'business_modules' in project_context:
            business_modules = project_context['business_modules']
            if any(module in file_path for module in business_modules):
                score += 30

        importance_score.business_logic_score = min(100, score)

    def _calculate_overall_score(self, importance_score: FileImportanceScore):
        """计算综合重要性评分"""
        # 使用权重计算综合评分
        overall_score = (
            importance_score.complexity_score * self._weights.get('complexity', 0.25) +
            importance_score.issue_density_score * self._weights.get('issue_density', 0.30) +
            importance_score.dependency_score * self._weights.get('dependency', 0.20) +
            importance_score.change_frequency_score * self._weights.get('change_frequency', 0.15) +
            importance_score.business_logic_score * self._weights.get('business_logic', 0.10)
        )

        importance_score.overall_score = round(overall_score, 2)
        importance_score.scored_at = datetime.now()

    def analyze_multiple_files(self,
                             file_paths: List[str],
                             static_issues_map: Optional[Dict[str, List[AnalysisIssue]]] = None,
                             project_context: Optional[Dict[str, Any]] = None) -> List[FileImportanceScore]:
        """批量分析多个文件的重要性

        Args:
            file_paths: 文件路径列表
            static_issues_map: 文件路径到问题列表的映射
            project_context: 项目上下文信息

        Returns:
            文件重要性评分列表，已按重要性降序排列
        """
        self.logger.info(f"开始批量分析文件重要性，文件数量: {len(file_paths)}")

        scores = []
        static_issues_map = static_issues_map or {}

        for file_path in file_paths:
            try:
                static_issues = static_issues_map.get(file_path, [])
                score = self.analyze_file_importance(file_path, static_issues, project_context)
                scores.append(score)
            except Exception as e:
                self.logger.error(f"分析文件重要性失败: {file_path}", error=str(e))
                continue

        # 按综合评分降序排列
        scores.sort(key=lambda x: x.overall_score, reverse=True)

        # 设置排名
        for rank, score in enumerate(scores, 1):
            score.priority_rank = rank

        self.logger.info(f"文件重要性批量分析完成，有效评分数量: {len(scores)}")

        return scores

    def get_top_files(self,
                     file_paths: List[str],
                     top_n: int = 10,
                     static_issues_map: Optional[Dict[str, List[AnalysisIssue]]] = None,
                     project_context: Optional[Dict[str, Any]] = None) -> List[FileImportanceScore]:
        """获取最重要的N个文件

        Args:
            file_paths: 文件路径列表
            top_n: 返回的文件数量
            static_issues_map: 文件路径到问题列表的映射
            project_context: 项目上下文信息

        Returns:
            最重要文件的重要性评分列表
        """
        all_scores = self.analyze_multiple_files(file_paths, static_issues_map, project_context)
        return all_scores[:top_n]

    def update_weights(self, new_weights: Dict[str, float]):
        """更新评分权重

        Args:
            new_weights: 新的权重配置
        """
        # 验证权重总和
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            self.logger.warning(f"权重总和不等于1.0，当前总和: {total_weight}")

        self._weights.update(new_weights)
        self.logger.info("评分权重已更新", new_weights=self._weights)

    def get_current_weights(self) -> Dict[str, float]:
        """获取当前权重配置"""
        return self._weights.copy()

    def _analyze_nesting_depth(self, file_path: str, content: str) -> int:
        """分析代码嵌套深度"""
        if file_path.endswith('.py'):
            return self._analyze_python_nesting_depth(content)
        else:
            return self._analyze_generic_nesting_depth(content)

    def _analyze_python_nesting_depth(self, content: str) -> int:
        """分析Python代码的嵌套深度"""
        try:
            tree = ast.parse(content)

            max_depth = 0

            def calculate_depth(node, current_depth=0):
                nonlocal max_depth
                max_depth = max(max_depth, current_depth)

                # 递增深度的节点类型
                if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try,
                                  ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    for child in ast.iter_child_nodes(node):
                        calculate_depth(child, current_depth + 1)
                else:
                    for child in ast.iter_child_nodes(node):
                        calculate_depth(child, current_depth)

            calculate_depth(tree)
            return max_depth

        except SyntaxError:
            return self._analyze_generic_nesting_depth(content)

    def _analyze_generic_nesting_depth(self, content: str) -> int:
        """通用嵌套深度分析"""
        lines = content.splitlines()
        max_depth = 0
        current_depth = 0

        # 简单的括号和缩进分析
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue

            # 计算缩进
            indent = len(line) - len(line.lstrip())
            estimated_depth = indent // 4  # 假设4个空格为一级缩进
            current_depth = estimated_depth
            max_depth = max(max_depth, current_depth)

            # 基于括号的简单分析
            open_brackets = stripped.count('{') + stripped.count('(') + stripped.count('[')
            close_brackets = stripped.count('}') + stripped.count(')') + stripped.count(']')
            current_depth += open_brackets - close_brackets
            max_depth = max(max_depth, current_depth)

        return max_depth

    def _analyze_code_duplication(self, content: str) -> float:
        """分析代码重复度"""
        lines = content.splitlines()
        non_empty_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]

        if len(non_empty_lines) < 2:
            return 0.0

        # 简单的行重复检测
        line_counts = {}
        for line in non_empty_lines:
            line_counts[line] = line_counts.get(line, 0) + 1

        # 计算重复行比例
        duplicated_lines = sum(count - 1 for count in line_counts.values() if count > 1)
        total_lines = len(non_empty_lines)

        duplication_ratio = duplicated_lines / total_lines if total_lines > 0 else 0.0
        return round(duplication_ratio, 3)

    def _analyze_parameter_complexity(self, file_path: str, content: str) -> float:
        """分析参数复杂度"""
        if file_path.endswith('.py'):
            return self._analyze_python_parameter_complexity(content)
        else:
            return self._analyze_generic_parameter_complexity(content)

    def _analyze_python_parameter_complexity(self, content: str) -> float:
        """分析Python函数参数复杂度"""
        try:
            tree = ast.parse(content)

            total_params = 0
            function_count = 0

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    function_count += 1
                    # 不包括self参数
                    params = len(node.args.args)
                    if params > 0 and node.args.args[0].arg == 'self':
                        params -= 1
                    total_params += params

            if function_count == 0:
                return 0.0

            avg_params = total_params / function_count
            # 参数越多，复杂度越高
            return min(10.0, avg_params * 2.0)

        except SyntaxError:
            return self._analyze_generic_parameter_complexity(content)

    def _analyze_generic_parameter_complexity(self, content: str) -> float:
        """通用参数复杂度分析"""
        lines = content.splitlines()
        total_params = 0
        function_count = 0

        # 简单的函数参数匹配
        function_pattern = r'(?:function|def)\s+\w+\s*\(([^)]*)\)'

        for line in lines:
            match = re.search(function_pattern, line, re.IGNORECASE)
            if match:
                function_count += 1
                params_str = match.group(1).strip()
                if params_str:
                    params = len([p.strip() for p in params_str.split(',')])
                    total_params += params

        if function_count == 0:
            return 0.0

        avg_params = total_params / function_count
        return min(10.0, avg_params * 2.0)

    def _calculate_size_adjustment(self, lines_of_code: int) -> float:
        """计算基于文件大小的调整因子"""
        if lines_of_code == 0:
            return 0.0
        elif lines_of_code < 10:
            return 0.5  # 很小的文件分数减半
        elif lines_of_code < 50:
            return 0.8  # 小文件分数略微减少
        elif lines_of_code < 200:
            return 1.0  # 中等文件保持原分数
        elif lines_of_code < 500:
            return 1.1  # 较大文件略微加分
        else:
            return 1.2  # 大文件加分更多

    def _calculate_dependency_centrality(self, file_path: str, dependency_graph: Dict[str, List[str]]) -> float:
        """计算依赖网络中心性"""
        if not dependency_graph:
            return 0.0

        # 简单的中心性计算：基于入度和出度的总和
        in_degree = 0  # 被依赖数量
        out_degree = 0  # 依赖数量

        # 计算入度
        for deps in dependency_graph.values():
            if file_path in deps:
                in_degree += 1

        # 计算出度
        out_degree = len(dependency_graph.get(file_path, []))

        # 中心性评分
        total_nodes = len(dependency_graph)
        if total_nodes == 0:
            return 0.0

        # 归一化的中心性分数
        centrality = (in_degree + out_degree) / (2 * total_nodes)
        return centrality * 20  # 放大到0-20分

    def _calculate_dependency_stability(self, file_path: str, imports: List[str], dependency_graph: Dict[str, List[str]]) -> float:
        """计算依赖稳定性"""
        if not imports:
            return 5.0  # 无依赖，稳定性高

        # 检查依赖的稳定性
        stable_deps = 0
        unstable_deps = 0

        for dep in imports:
            # 如果依赖是标准库或知名第三方库，认为是稳定的
            if self._is_stable_dependency(dep):
                stable_deps += 1
            # 如果依赖是项目内部文件且被很多文件依赖，认为是稳定的
            elif dep in dependency_graph and len(dependency_graph.get(dep, [])) > 3:
                stable_deps += 1
            else:
                unstable_deps += 1

        total_deps = len(imports)
        if total_deps == 0:
            return 5.0

        stability_ratio = stable_deps / total_deps
        return stability_ratio * 10  # 0-10分

    def _calculate_hierarchy_importance(self, file_path: str, module_hierarchy: Dict[str, str]) -> float:
        """计算层次结构重要性"""
        if not module_hierarchy or file_path not in module_hierarchy:
            return 2.5  # 默认分数

        level = module_hierarchy[file_path]

        # 基于模块层次的重要性评分
        if level == 'core':
            return 5.0
        elif level == 'infrastructure':
            return 4.0
        elif level == 'business':
            return 3.0
        elif level == 'presentation':
            return 2.0
        else:
            return 1.0

    def _is_stable_dependency(self, dependency: str) -> bool:
        """判断依赖是否稳定"""
        # 标准库模块
        stdlib_modules = {
            'os', 'sys', 'json', 'datetime', 're', 'math', 'random',
            'collections', 'itertools', 'functools', 'operator',
            'pathlib', 'urllib', 'http', 'socket', 'threading',
            'asyncio', 'logging', 'unittest', 'sqlite3'
        }

        # 知名稳定的第三方库
        stable_third_party = {
            'numpy', 'pandas', 'requests', 'flask', 'django',
            'pytest', 'sqlalchemy', 'celery', 'redis', 'psycopg2'
        }

        dep_lower = dependency.lower()
        return (dep_lower in stdlib_modules or
                any(stable in dep_lower for stable in stable_third_party))

    def _is_utility_module(self, file_path: str) -> bool:
        """判断是否为工具模块"""
        path_lower = file_path.lower()
        utility_patterns = ['utils', 'tools', 'helpers', 'common', 'shared']
        return any(pattern in path_lower for pattern in utility_patterns)

    def _is_interface_module(self, file_path: str) -> bool:
        """判断是否为接口模块"""
        path_lower = file_path.lower()
        interface_patterns = ['interface', 'api', 'protocol', 'abstract', 'base']
        return any(pattern in path_lower for pattern in interface_patterns)