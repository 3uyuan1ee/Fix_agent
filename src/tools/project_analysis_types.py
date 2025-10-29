"""
项目分析工作流数据类型定义
定义项目分析过程中使用的所有数据结构和枚举类型
"""

from typing import Dict, List, Any, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

from .static_coordinator import AnalysisIssue, SeverityLevel


class AnalysisPhase(Enum):
    """分析阶段枚举"""
    INITIALIZATION = "initialization"
    STATIC_ANALYSIS = "static_analysis"
    FILE_SELECTION = "file_selection"
    CONTEXT_BUILDING = "context_building"
    AI_ANALYSIS = "ai_analysis"
    FIX_GENERATION = "fix_generation"
    FIX_VALIDATION = "fix_validation"
    COMPLETED = "completed"
    FAILED = "failed"


class FixStrategy(Enum):
    """修复策略枚举"""
    AUTOMATIC = "automatic"  # 自动应用
    INTERACTIVE = "interactive"  # 交互确认
    SUGGESTION_ONLY = "suggestion_only"  # 仅建议
    MANUAL = "manual"  # 手动修复


class FileCategory(Enum):
    """文件分类枚举"""
    SOURCE = "source"  # 源代码文件
    CONFIG = "config"  # 配置文件
    TEST = "test"  # 测试文件
    DOCUMENTATION = "documentation"  # 文档文件
    BUILD = "build"  # 构建文件
    DEPLOYMENT = "deployment"  # 部署文件
    OTHER = "other"  # 其他文件


@dataclass
class ProjectInfo:
    """项目基本信息数据类

    包含项目的基本元数据、文件统计、技术栈信息等
    """
    # 基本信息
    project_path: str
    project_name: str
    description: str = ""
    version: str = ""

    # 文件统计
    total_files: int = 0
    source_files: int = 0
    test_files: int = 0
    config_files: int = 0
    doc_files: int = 0

    # 编程语言分布
    languages: Dict[str, int] = field(default_factory=dict)  # 语言名 -> 文件数量
    primary_language: str = ""

    # 项目结构信息
    directories: List[str] = field(default_factory=list)
    root_files: List[str] = field(default_factory=list)

    # 依赖信息
    dependencies: Dict[str, str] = field(default_factory=dict)  # 包名 -> 版本
    dependency_files: List[str] = field(default_factory=list)  # requirements.txt, package.json等

    # 项目配置
    config_files_found: List[str] = field(default_factory=list)
    build_systems: List[str] = field(default_factory=list)  # Maven, Gradle, npm, pip等

    # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    analyzed_at: datetime = field(default_factory=datetime.now)

    # 项目特征
    is_git_repo: bool = False
    git_branch: str = ""
    git_commit: str = ""
    has_tests: bool = False
    has_ci_cd: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "project_path": self.project_path,
            "project_name": self.project_name,
            "description": self.description,
            "version": self.version,
            "total_files": self.total_files,
            "source_files": self.source_files,
            "test_files": self.test_files,
            "config_files": self.config_files,
            "doc_files": self.doc_files,
            "languages": self.languages,
            "primary_language": self.primary_language,
            "directories": self.directories,
            "root_files": self.root_files,
            "dependencies": self.dependencies,
            "dependency_files": self.dependency_files,
            "config_files_found": self.config_files_found,
            "build_systems": self.build_systems,
            "created_at": self.created_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "analyzed_at": self.analyzed_at.isoformat(),
            "is_git_repo": self.is_git_repo,
            "git_branch": self.git_branch,
            "git_commit": self.git_commit,
            "has_tests": self.has_tests,
            "has_ci_cd": self.has_ci_cd
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectInfo':
        """从字典创建实例"""
        # 处理日期时间字段
        datetime_fields = ['created_at', 'last_modified', 'analyzed_at']
        for field_name in datetime_fields:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])

        return cls(**data)


@dataclass
class StaticAnalysisSummary:
    """静态分析结果摘要数据类

    汇总多个静态分析工具的结果，提供整体质量评估
    """
    # 基本统计
    total_issues: int = 0
    files_analyzed: int = 0
    tools_used: List[str] = field(default_factory=list)
    analysis_duration: float = 0.0  # 分析耗时（秒）

    # 按严重程度统计
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    low_count: int = 0

    # 按工具统计
    tool_results: Dict[str, Dict[str, int]] = field(default_factory=dict)  # 工具名 -> {severity: count}

    # 按文件统计
    file_issue_counts: Dict[str, int] = field(default_factory=dict)  # 文件路径 -> 问题数量
    most_problematic_files: List[str] = field(default_factory=list)  # 问题最多的文件

    # 按问题类型统计
    issue_types: Dict[str, int] = field(default_factory=dict)  # 问题类型 -> 数量
    common_issues: List[str] = field(default_factory=list)  # 最常见的问题类型

    # 质量评分
    quality_score: float = 0.0  # 0-100分
    complexity_score: float = 0.0  # 复杂度评分
    security_score: float = 0.0  # 安全性评分
    maintainability_score: float = 0.0  # 可维护性评分

    # 问题分布
    severity_distribution: Dict[str, float] = field(default_factory=dict)  # 严重程度分布百分比
    file_distribution: Dict[str, int] = field(default_factory=dict)  # 文件问题数量分布

    # 详细问题列表（可选，用于深入分析）
    sample_issues: List[AnalysisIssue] = field(default_factory=list)  # 样本问题

    # 元数据
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    analyzer_version: str = ""
    configuration_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "total_issues": self.total_issues,
            "files_analyzed": self.files_analyzed,
            "tools_used": self.tools_used,
            "analysis_duration": self.analysis_duration,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "low_count": self.low_count,
            "tool_results": self.tool_results,
            "file_issue_counts": self.file_issue_counts,
            "most_problematic_files": self.most_problematic_files,
            "issue_types": self.issue_types,
            "common_issues": self.common_issues,
            "quality_score": self.quality_score,
            "complexity_score": self.complexity_score,
            "security_score": self.security_score,
            "maintainability_score": self.maintainability_score,
            "severity_distribution": self.severity_distribution,
            "file_distribution": self.file_distribution,
            "sample_issues": [issue.to_dict() for issue in self.sample_issues],
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
            "analyzer_version": self.analyzer_version,
            "configuration_hash": self.configuration_hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StaticAnalysisSummary':
        """从字典创建实例"""
        # 处理日期时间字段
        if 'analysis_timestamp' in data and isinstance(data['analysis_timestamp'], str):
            data['analysis_timestamp'] = datetime.fromisoformat(data['analysis_timestamp'])

        # 处理样本问题
        if 'sample_issues' in data:
            sample_issues = []
            for issue_data in data['sample_issues']:
                # 手动创建AnalysisIssue实例，因为没有from_dict方法
                severity = SeverityLevel(issue_data.get('severity', 'info'))
                issue = AnalysisIssue(
                    tool_name=issue_data.get('tool_name', ''),
                    file_path=issue_data.get('file_path', ''),
                    line=issue_data.get('line', 0),
                    column=issue_data.get('column', 0),
                    message=issue_data.get('message', ''),
                    severity=severity,
                    issue_type=issue_data.get('issue_type', ''),
                    code=issue_data.get('code', ''),
                    confidence=issue_data.get('confidence', ''),
                    source_code=issue_data.get('source_code', '')
                )
                sample_issues.append(issue)
            data['sample_issues'] = sample_issues

        return cls(**data)

    def calculate_quality_score(self) -> float:
        """计算综合质量评分"""
        if self.files_analyzed == 0:
            return 100.0

        # 基础分数：100分
        base_score = 100.0

        # 根据问题严重程度扣分
        error_penalty = self.error_count * 10
        warning_penalty = self.warning_count * 3
        info_penalty = self.info_count * 1
        low_penalty = self.low_count * 0.5

        total_penalty = error_penalty + warning_penalty + info_penalty + low_penalty

        # 根据文件数量调整
        penalty_per_file = total_penalty / self.files_analyzed

        # 计算最终分数（不低于0分）
        final_score = max(0.0, base_score - penalty_per_file)

        self.quality_score = round(final_score, 2)
        return self.quality_score


@dataclass
class AIAnalysisContext:
    """AI分析上下文信息数据类

    为AI分析提供完整的上下文信息，包括项目背景、静态分析结果、代码片段等
    """
    # 基本信息
    target_file_path: str
    file_category: FileCategory = FileCategory.SOURCE
    file_language: str = ""
    file_size: int = 0  # 字节数
    estimated_tokens: int = 0

    # 项目背景信息
    project_info: Optional[ProjectInfo] = None
    project_summary: str = ""  # 项目简要描述

    # 静态分析上下文
    static_issues: List[AnalysisIssue] = field(default_factory=list)
    issue_summary: str = ""  # 当前文件的问题摘要
    related_files_issues: Dict[str, List[AnalysisIssue]] = field(default_factory=dict)  # 相关文件的问题

    # 代码上下文
    file_content: str = ""  # 完整文件内容（可选）
    code_snippets: List[str] = field(default_factory=list)  # 重要的代码片段
    function_context: Dict[str, str] = field(default_factory=dict)  # 函数名 -> 函数代码
    class_context: Dict[str, str] = field(default_factory=dict)  # 类名 -> 类代码

    # 依赖关系上下文
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    import_graph: Dict[str, List[str]] = field(default_factory=dict)

    # 历史分析上下文
    previous_analysis: Optional[Dict[str, Any]] = None
    previous_fixes: List[str] = field(default_factory=list)
    fix_history: List[Dict[str, Any]] = field(default_factory=list)

    # 分析焦点
    focus_areas: List[str] = field(default_factory=list)  # 重点关注的区域
    analysis_goals: List[str] = field(default_factory=list)  # 分析目标
    exclude_patterns: List[str] = field(default_factory=list)  # 排除的模式

    # 配置和约束
    max_tokens: int = 8000
    context_priority: str = "balanced"  # minimal, balanced, comprehensive
    analysis_depth: str = "standard"  # shallow, standard, deep

    # 元数据
    context_id: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "target_file_path": self.target_file_path,
            "file_category": self.file_category.value,
            "file_language": self.file_language,
            "file_size": self.file_size,
            "estimated_tokens": self.estimated_tokens,
            "project_info": self.project_info.to_dict() if self.project_info else None,
            "project_summary": self.project_summary,
            "static_issues": [issue.to_dict() for issue in self.static_issues],
            "issue_summary": self.issue_summary,
            "related_files_issues": {
                file_path: [issue.to_dict() for issue in issues]
                for file_path, issues in self.related_files_issues.items()
            },
            "file_content": self.file_content,
            "code_snippets": self.code_snippets,
            "function_context": self.function_context,
            "class_context": self.class_context,
            "imports": self.imports,
            "dependencies": self.dependencies,
            "dependents": self.dependents,
            "import_graph": self.import_graph,
            "previous_analysis": self.previous_analysis,
            "previous_fixes": self.previous_fixes,
            "fix_history": self.fix_history,
            "focus_areas": self.focus_areas,
            "analysis_goals": self.analysis_goals,
            "exclude_patterns": self.exclude_patterns,
            "max_tokens": self.max_tokens,
            "context_priority": self.context_priority,
            "analysis_depth": self.analysis_depth,
            "context_id": self.context_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIAnalysisContext':
        """从字典创建实例"""
        # 处理枚举类型
        if 'file_category' in data:
            data['file_category'] = FileCategory(data['file_category'])

        # 处理ProjectInfo
        if 'project_info' in data and data['project_info']:
            data['project_info'] = ProjectInfo.from_dict(data['project_info'])

        # 处理静态分析问题
        if 'static_issues' in data:
            static_issues = []
            for issue_data in data['static_issues']:
                severity = SeverityLevel(issue_data.get('severity', 'info'))
                issue = AnalysisIssue(
                    tool_name=issue_data.get('tool_name', ''),
                    file_path=issue_data.get('file_path', ''),
                    line=issue_data.get('line', 0),
                    column=issue_data.get('column', 0),
                    message=issue_data.get('message', ''),
                    severity=severity,
                    issue_type=issue_data.get('issue_type', ''),
                    code=issue_data.get('code', ''),
                    confidence=issue_data.get('confidence', ''),
                    source_code=issue_data.get('source_code', '')
                )
                static_issues.append(issue)
            data['static_issues'] = static_issues

        # 处理相关文件问题
        if 'related_files_issues' in data:
            related_files_issues = {}
            for file_path, issues_data in data['related_files_issues'].items():
                issues = []
                for issue_data in issues_data:
                    severity = SeverityLevel(issue_data.get('severity', 'info'))
                    issue = AnalysisIssue(
                        tool_name=issue_data.get('tool_name', ''),
                        file_path=issue_data.get('file_path', ''),
                        line=issue_data.get('line', 0),
                        column=issue_data.get('column', 0),
                        message=issue_data.get('message', ''),
                        severity=severity,
                        issue_type=issue_data.get('issue_type', ''),
                        code=issue_data.get('code', ''),
                        confidence=issue_data.get('confidence', ''),
                        source_code=issue_data.get('source_code', '')
                    )
                    issues.append(issue)
                related_files_issues[file_path] = issues
            data['related_files_issues'] = related_files_issues

        # 处理日期时间字段
        datetime_fields = ['created_at', 'expires_at']
        for field_name in datetime_fields:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])

        return cls(**data)


@dataclass
class FileImportanceScore:
    """文件重要性评分数据类

    基于多种因素评估文件在项目中的重要性，用于优先级排序和智能选择
    """
    # 基本信息
    file_path: str
    file_name: str
    file_category: FileCategory = FileCategory.SOURCE
    file_size: int = 0  # 字节数

    # 综合评分
    overall_score: float = 0.0  # 综合重要性评分 0-100
    priority_rank: int = 0  # 优先级排名

    # 评分因子
    complexity_score: float = 0.0  # 复杂度评分
    issue_density_score: float = 0.0  # 问题密度评分
    dependency_score: float = 0.0  # 依赖关系评分
    change_frequency_score: float = 0.0  # 变更频率评分
    business_logic_score: float = 0.0  # 业务逻辑重要性评分
    test_coverage_score: float = 0.0  # 测试覆盖评分

    # 详细评分因子
    lines_of_code: int = 0  # 代码行数
    cyclomatic_complexity: int = 0  # 圈复杂度
    function_count: int = 0  # 函数数量
    class_count: int = 0  # 类数量

    # 问题统计
    total_issues: int = 0  # 总问题数
    error_count: int = 0  # 错误数量
    warning_count: int = 0  # 警告数量
    critical_issues: int = 0  # 严重问题数量

    # 依赖关系
    imports_count: int = 0  # 导入数量
    dependents_count: int = 0  # 被依赖数量
    is_core_module: bool = False  # 是否核心模块
    is_entry_point: bool = False  # 是否入口点

    # 历史数据
    last_modified: datetime = field(default_factory=datetime.now)
    commit_count: int = 0  # 提交次数
    authors_count: int = 0  # 作者数量

    # 评分权重配置
    weights: Dict[str, float] = field(default_factory=lambda: {
        'complexity': 0.2,
        'issue_density': 0.25,
        'dependency': 0.2,
        'change_frequency': 0.15,
        'business_logic': 0.2
    })

    # 元数据
    scored_at: datetime = field(default_factory=datetime.now)
    scoring_algorithm: str = "default"  # 评分算法版本
    notes: str = ""  # 备注信息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_category": self.file_category.value,
            "file_size": self.file_size,
            "overall_score": self.overall_score,
            "priority_rank": self.priority_rank,
            "complexity_score": self.complexity_score,
            "issue_density_score": self.issue_density_score,
            "dependency_score": self.dependency_score,
            "change_frequency_score": self.change_frequency_score,
            "business_logic_score": self.business_logic_score,
            "test_coverage_score": self.test_coverage_score,
            "lines_of_code": self.lines_of_code,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "total_issues": self.total_issues,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "critical_issues": self.critical_issues,
            "imports_count": self.imports_count,
            "dependents_count": self.dependents_count,
            "is_core_module": self.is_core_module,
            "is_entry_point": self.is_entry_point,
            "last_modified": self.last_modified.isoformat(),
            "commit_count": self.commit_count,
            "authors_count": self.authors_count,
            "weights": self.weights,
            "scored_at": self.scored_at.isoformat(),
            "scoring_algorithm": self.scoring_algorithm,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileImportanceScore':
        """从字典创建实例"""
        # 处理枚举类型
        if 'file_category' in data:
            data['file_category'] = FileCategory(data['file_category'])

        # 处理日期时间字段
        datetime_fields = ['last_modified', 'scored_at']
        for field_name in datetime_fields:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = datetime.fromisoformat(data[field_name])

        return cls(**data)

    def calculate_overall_score(self) -> float:
        """计算综合重要性评分"""
        if self.lines_of_code == 0:
            return 0.0

        # 标准化各子评分到0-100范围
        scores = {
            'complexity': self._normalize_complexity(),
            'issue_density': self._normalize_issue_density(),
            'dependency': self._normalize_dependency(),
            'change_frequency': self._normalize_change_frequency(),
            'business_logic': self.business_logic_score
        }

        # 加权计算综合评分
        overall = 0.0
        for factor, score in scores.items():
            weight = self.weights.get(factor, 0.2)
            overall += score * weight

        self.overall_score = round(overall, 2)
        return self.overall_score

    def _normalize_complexity(self) -> float:
        """标准化复杂度评分"""
        if self.lines_of_code == 0:
            return 0.0

        # 基于圈复杂度和代码行数的复杂度评分
        complexity_ratio = self.cyclomatic_complexity / max(1, self.lines_of_code / 10)  # 每10行的复杂度

        # 映射到0-100分
        if complexity_ratio <= 0.1:
            return 20.0  # 简单
        elif complexity_ratio <= 0.3:
            return 50.0  # 中等
        elif complexity_ratio <= 0.5:
            return 80.0  # 复杂
        else:
            return 100.0  # 非常复杂

    def _normalize_issue_density(self) -> float:
        """标准化问题密度评分"""
        if self.lines_of_code == 0:
            return 0.0

        issues_per_line = self.total_issues / max(1, self.lines_of_code / 100)  # 每100行的问题数

        # 问题越多，重要性越高（需要优先修复）
        if issues_per_line <= 1:
            return 20.0
        elif issues_per_line <= 3:
            return 50.0
        elif issues_per_line <= 5:
            return 80.0
        else:
            return 100.0

    def _normalize_dependency(self) -> float:
        """标准化依赖关系评分"""
        dependency_score = 0.0

        # 被依赖数量评分
        if self.dependents_count >= 10:
            dependency_score += 40.0
        elif self.dependents_count >= 5:
            dependency_score += 30.0
        elif self.dependents_count >= 2:
            dependency_score += 20.0

        # 核心模块加分
        if self.is_core_module:
            dependency_score += 30.0

        # 入口点加分
        if self.is_entry_point:
            dependency_score += 30.0

        return min(100.0, dependency_score)

    def _normalize_change_frequency(self) -> float:
        """标准化变更频率评分"""
        # 基于提交次数和作者数量
        change_activity = self.commit_count + (self.authors_count * 2)

        if change_activity >= 20:
            return 100.0  # 高频变更
        elif change_activity >= 10:
            return 80.0
        elif change_activity >= 5:
            return 60.0
        elif change_activity >= 2:
            return 40.0
        else:
            return 20.0  # 低频变更


class FixSuggestion:
    """修复建议数据类"""
    pass


class ProjectAnalysisResult:
    """项目分析结果数据类"""
    pass