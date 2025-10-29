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
        """分析文件复杂度"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 基础指标
            lines = content.splitlines()
            importance_score.lines_of_code = len([line for line in lines if line.strip() and not line.strip().startswith('#')])

            # AST分析
            if file_path.endswith('.py'):
                self._analyze_python_complexity(importance_score, content)
            else:
                # 对于其他语言类型的简单启发式分析
                self._analyze_generic_complexity(importance_score, content)

            # 计算复杂度评分 (0-100)
            base_score = min(100, importance_score.cyclomatic_complexity * 2)
            function_score = min(50, importance_score.function_count * 3)
            class_score = min(30, importance_score.class_count * 5)

            importance_score.complexity_score = min(100, base_score + function_score + class_score)

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
        """分析问题密度"""
        if not static_issues:
            importance_score.issue_density_score = 0.0
            return

        # 统计问题数量
        importance_score.total_issues = len(static_issues)
        importance_score.error_count = len([issue for issue in static_issues if issue.severity.value == 'error'])
        importance_score.warning_count = len([issue for issue in static_issues if issue.severity.value == 'warning'])
        importance_score.critical_issues = len([issue for issue in static_issues if issue.severity.value == 'critical'])

        # 计算问题密度（每100行代码的问题数）
        if importance_score.lines_of_code > 0:
            density = (importance_score.total_issues / importance_score.lines_of_code) * 100

            # 根据密度阈值计算评分
            if density <= self._issue_density_thresholds['low']:
                importance_score.issue_density_score = 20.0  # 低密度，低重要性
            elif density <= self._issue_density_thresholds['medium']:
                importance_score.issue_density_score = 50.0  # 中等密度
            elif density <= self._issue_density_thresholds['high']:
                importance_score.issue_density_score = 80.0  # 高密度
            else:
                importance_score.issue_density_score = 100.0  # 极高密度
        else:
            importance_score.issue_density_score = 0.0

    def _analyze_dependencies(self, importance_score: FileImportanceScore, file_path: str, project_context: Optional[Dict[str, Any]]):
        """分析依赖关系"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 分析导入依赖
            imports = self._extract_imports(file_path, content)
            importance_score.imports_count = len(imports)

            # 从项目上下文中获取被依赖信息
            if project_context and 'dependency_graph' in project_context:
                dependency_graph = project_context['dependency_graph']
                importance_score.dependents_count = len([
                    dep for deps in dependency_graph.values()
                    for dep in deps if file_path in dep
                ])

            # 判断是否为核心模块或入口点
            importance_score.is_core_module = self._is_core_module(file_path, project_context)
            importance_score.is_entry_point = self._is_entry_point(file_path, project_context)

            # 计算依赖关系评分
            dependency_score = 0

            # 被依赖数量权重最高
            dependency_score += min(40, importance_score.dependents_count * 5)

            # 导入数量适中加分
            if 1 <= importance_score.imports_count <= 10:
                dependency_score += 20
            elif importance_score.imports_count > 10:
                dependency_score += 10

            # 核心模块加分
            if importance_score.is_core_module:
                dependency_score += 30

            # 入口点加分
            if importance_score.is_entry_point:
                dependency_score += 10

            importance_score.dependency_score = min(100, dependency_score)

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