"""
问题检测上下文构建器 - T008.1
为AI问题检测构建上下文
"""

import os
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from ..utils.logger import get_logger
try:
    from .workflow_data_types import AIDetectedProblem, ProblemType, SeverityLevel, CodeContext
    from .multilang_static_analyzer import StaticAnalysisResult
    from .project_structure_scanner import ProjectStructure
except ImportError:
    # 如果相关模块不可用，定义基本类型
    from enum import Enum

    class ProblemType(Enum):
        SECURITY = "security"
        PERFORMANCE = "performance"
        LOGIC = "logic"
        STYLE = "style"
        MAINTAINABILITY = "maintainability"
        RELIABILITY = "reliability"
        COMPATIBILITY = "compatibility"
        DOCUMENTATION = "documentation"

    class SeverityLevel(Enum):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    @dataclass
    class CodeContext:
        file_path: str
        line_number: int
        function_name: Optional[str] = None
        class_name: Optional[str] = None
        module_name: Optional[str] = None
        surrounding_lines: List[str] = field(default_factory=list)
        imports: List[str] = field(default_factory=list)
        variables: List[str] = field(default_factory=list)

    @dataclass
    class AIDetectedProblem:
        problem_id: str
        file_path: str
        line_number: int
        problem_type: ProblemType
        severity: SeverityLevel
        description: str
        code_snippet: str
        confidence: float
        reasoning: str

    @dataclass
    class StaticAnalysisResult:
        language: str
        tool_name: str
        issues: List[Dict[str, Any]] = field(default_factory=list)

    @dataclass
    class ProjectStructure:
        project_path: str
        total_files: int = 0
        language_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class ProblemDetectionContext:
    """问题检测上下文"""
    context_id: str
    project_info: Dict[str, Any]
    selected_files: List[Dict[str, Any]]
    static_analysis_results: Dict[str, StaticAnalysisResult]
    file_contents: Dict[str, str] = field(default_factory=dict)
    code_contexts: Dict[str, List[CodeContext]] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    detection_focus: List[str] = field(default_factory=list)
    context_statistics: Dict[str, Any] = field(default_factory=dict)
    build_timestamp: str = ""
    token_estimate: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "context_id": self.context_id,
            "project_info": self.project_info,
            "selected_files": self.selected_files,
            "static_analysis_results": {
                path: {
                    "language": result.language,
                    "tool_name": result.tool_name,
                    "issues": result.issues
                }
                for path, result in self.static_analysis_results.items()
            },
            "file_contents": self.file_contents,
            "code_contexts": {
                path: [ctx.to_dict() for ctx in contexts]
                for path, contexts in self.code_contexts.items()
            },
            "user_preferences": self.user_preferences,
            "detection_focus": self.detection_focus,
            "context_statistics": self.context_statistics,
            "build_timestamp": self.build_timestamp,
            "token_estimate": self.token_estimate
        }


class ProblemDetectionContextBuilder:
    """问题检测上下文构建器"""

    def __init__(self, max_content_lines: int = 50, max_token_estimate: int = 8000):
        self.max_content_lines = max_content_lines
        self.max_token_estimate = max_token_estimate
        self.logger = get_logger()

        # 问题类型权重配置
        self.problem_type_weights = {
            ProblemType.SECURITY: 1.5,
            ProblemType.PERFORMANCE: 1.3,
            ProblemType.LOGIC: 1.2,
            ProblemType.RELIABILITY: 1.2,
            ProblemType.MAINTAINABILITY: 1.0,
            ProblemType.STYLE: 0.8,
            ProblemType.COMPATIBILITY: 1.1,
            ProblemType.DOCUMENTATION: 0.6
        }

        # 严重程度权重配置
        self.severity_weights = {
            SeverityLevel.CRITICAL: 1.5,
            SeverityLevel.HIGH: 1.3,
            SeverityLevel.MEDIUM: 1.0,
            SeverityLevel.LOW: 0.7
        }

    def build_context(self,
                     selected_files: List[Dict[str, Any]],
                     static_analysis_results: Dict[str, StaticAnalysisResult],
                     project_structure: Optional[ProjectStructure] = None,
                     user_preferences: Optional[Dict[str, Any]] = None) -> ProblemDetectionContext:
        """
        构建问题检测上下文

        Args:
            selected_files: Phase 1-4选择的文件列表
            static_analysis_results: 静态分析结果
            project_structure: 项目结构信息
            user_preferences: 用户偏好设置

        Returns:
            ProblemDetectionContext: 构建的上下文
        """
        self.logger.info(f"开始构建问题检测上下文，包含 {len(selected_files)} 个文件")

        context = ProblemDetectionContext(
            context_id=self._generate_context_id(),
            project_info={},  # 初始化为空，后面会填充
            selected_files=[],  # 初始化为空，后面会填充
            static_analysis_results=static_analysis_results or {},
            build_timestamp=datetime.now().isoformat()
        )

        try:
            # 构建项目信息
            context.project_info = self._build_project_info(project_structure)

            # 处理选择的文件
            context.selected_files = self._process_selected_files(selected_files)

            # 处理静态分析结果
            context.static_analysis_results = static_analysis_results

            # 读取文件内容
            context.file_contents = self._read_file_contents(selected_files)

            # 构建代码上下文
            context.code_contexts = self._build_code_contexts(selected_files, context.file_contents)

            # 处理用户偏好
            context.user_preferences = user_preferences or {}

            # 确定检测重点
            context.detection_focus = self._determine_detection_focus(
                context.selected_files, context.static_analysis_results, context.user_preferences
            )

            # 生成上下文统计
            context.context_statistics = self._generate_context_statistics(context)

            # 估算token使用量
            context.token_estimate = self._estimate_token_usage(context)

            self.logger.info(f"问题检测上下文构建完成，预估token数: {context.token_estimate}")

        except Exception as e:
            self.logger.error(f"构建问题检测上下文失败: {e}")
            raise

        return context

    def _build_project_info(self, project_structure: Optional[ProjectStructure]) -> Dict[str, Any]:
        """构建项目信息"""
        if not project_structure:
            return {}

        return {
            "project_path": project_structure.project_path,
            "total_files": project_structure.total_files,
            "language_distribution": project_structure.language_distribution,
            "project_type": self._detect_project_type(project_structure),
            "complexity_level": self._assess_project_complexity(project_structure)
        }

    def _detect_project_type(self, project_structure: ProjectStructure) -> str:
        """检测项目类型"""
        languages = project_structure.language_distribution

        if languages.get("python", 0) > languages.get("javascript", 0):
            if "test" in str(languages.keys()).lower():
                return "Python测试项目"
            elif any(key in ["django", "flask", "fastapi"] for key in languages.keys()):
                return "Python Web项目"
            else:
                return "Python通用项目"
        elif languages.get("javascript", 0) > 0 or languages.get("typescript", 0) > 0:
            if "react" in str(languages.keys()).lower() or "vue" in str(languages.keys()).lower():
                return "前端Web项目"
            else:
                return "JavaScript/TypeScript项目"
        elif languages.get("java", 0) > 0:
            return "Java项目"
        elif languages.get("go", 0) > 0:
            return "Go项目"
        else:
            return "多语言混合项目"

    def _assess_project_complexity(self, project_structure: ProjectStructure) -> str:
        """评估项目复杂度"""
        total_files = project_structure.total_files
        language_count = len(project_structure.language_distribution)

        if total_files > 1000 or language_count > 5:
            return "高"
        elif total_files > 100 or language_count > 2:
            return "中"
        else:
            return "低"

    def _process_selected_files(self, selected_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理选择的文件"""
        processed_files = []

        for file_data in selected_files:
            processed_file = {
                "file_path": file_data.get("file_path", ""),
                "relative_path": file_data.get("relative_path", ""),
                "language": file_data.get("language", "unknown"),
                "priority": file_data.get("priority", "medium"),
                "analysis_priority": file_data.get("analysis_priority", 0),
                "key_issues": file_data.get("key_issues", []),
                "estimated_complexity": file_data.get("estimated_complexity", "中"),
                "expected_fixes": file_data.get("expected_fixes", 0),
                "ai_selection_reason": file_data.get("ai_selection_reason", ""),
                "file_metadata": file_data.get("file_metadata", {})
            }

            # 添加文件重要性评分
            processed_file["importance_score"] = self._calculate_file_importance(processed_file)

            processed_files.append(processed_file)

        # 按重要性评分排序
        processed_files.sort(key=lambda x: x["importance_score"], reverse=True)

        return processed_files

    def _calculate_file_importance(self, file_data: Dict[str, Any]) -> float:
        """计算文件重要性评分"""
        score = 0.0

        # 基于分析优先级
        score += file_data.get("analysis_priority", 0) * 0.1

        # 基于预期修复数量
        score += file_data.get("expected_fixes", 0) * 2.0

        # 基于关键问题数量
        score += len(file_data.get("key_issues", [])) * 1.5

        # 基于优先级
        priority_weights = {"high": 10, "medium": 5, "low": 2}
        score += priority_weights.get(file_data.get("priority", "medium"), 5)

        # 基于文件大小
        file_metadata = file_data.get("file_metadata", {})
        line_count = file_metadata.get("line_count", 0)
        if line_count > 500:
            score += 5
        elif line_count > 200:
            score += 3
        elif line_count > 100:
            score += 1

        return round(score, 2)

    def _read_file_contents(self, selected_files: List[Dict[str, Any]]) -> Dict[str, str]:
        """读取文件内容"""
        file_contents = {}

        for file_data in selected_files:
            file_path = file_data.get("file_path", "")
            if not file_path or not os.path.exists(file_path):
                continue

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()

                # 限制读取的行数
                if len(lines) > self.max_content_lines:
                    content_lines = lines[:self.max_content_lines]
                    content = ''.join(content_lines)
                    content += f"\n... (文件截断，共 {len(lines)} 行)"
                else:
                    content = ''.join(lines)

                file_contents[file_path] = content

            except Exception as e:
                self.logger.warning(f"读取文件内容失败 {file_path}: {e}")
                file_contents[file_path] = f"# 文件读取失败: {e}"

        return file_contents

    def _build_code_contexts(self,
                           selected_files: List[Dict[str, Any]],
                           file_contents: Dict[str, str]) -> Dict[str, List[CodeContext]]:
        """构建代码上下文"""
        code_contexts = {}

        for file_data in selected_files:
            file_path = file_data.get("file_path", "")
            content = file_contents.get(file_path, "")

            if not content:
                continue

            try:
                contexts = self._extract_code_contexts(file_path, content)
                code_contexts[file_path] = contexts
            except Exception as e:
                self.logger.warning(f"构建代码上下文失败 {file_path}: {e}")

        return code_contexts

    def _extract_code_contexts(self, file_path: str, content: str) -> List[CodeContext]:
        """提取代码上下文"""
        contexts = []
        lines = content.split('\n')
        language = self._detect_file_language(file_path)

        # 提取函数定义上下文
        if language in ["python", "javascript", "typescript"]:
            contexts.extend(self._extract_function_contexts(file_path, lines, language))

        # 提取类定义上下文
        if language in ["python", "java", "javascript", "typescript", "cpp", "csharp"]:
            contexts.extend(self._extract_class_contexts(file_path, lines, language))

        # 如果没有找到特别的上下文，创建通用上下文
        if not contexts:
            contexts = self._create_generic_contexts(file_path, lines)

        return contexts

    def _detect_file_language(self, file_path: str) -> str:
        """检测文件语言"""
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".cpp": "cpp",
            ".cxx": "cpp",
            ".cc": "cpp",
            ".c": "c",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rs": "rust",
            ".php": "php",
            ".rb": "ruby"
        }

        return language_map.get(ext, "unknown")

    def _extract_function_contexts(self, file_path: str, lines: List[str], language: str) -> List[CodeContext]:
        """提取函数定义上下文"""
        contexts = []

        if language == "python":
            contexts.extend(self._extract_python_functions(file_path, lines))
        elif language in ["javascript", "typescript"]:
            contexts.extend(self._extract_js_functions(file_path, lines))

        return contexts

    def _extract_python_functions(self, file_path: str, lines: List[str]) -> List[CodeContext]:
        """提取Python函数上下文"""
        contexts = []
        imports = []

        for i, line in enumerate(lines):
            line = line.strip()

            # 收集导入语句
            if line.startswith(('import ', 'from ')):
                imports.append(line)

            # 查找函数定义
            if line.startswith('def ') and '(' in line:
                function_name = line.split('(')[0].replace('def ', '').strip()

                # 获取函数上下文（前后几行）
                start_line = max(0, i - 3)
                end_line = min(len(lines), i + 10)
                surrounding_lines = lines[start_line:end_line]

                context = CodeContext(
                    file_path=file_path,
                    line_number=i + 1,
                    function_name=function_name,
                    surrounding_lines=surrounding_lines,
                    imports=imports.copy()
                )
                contexts.append(context)

        return contexts

    def _extract_js_functions(self, file_path: str, lines: List[str]) -> List[CodeContext]:
        """提取JavaScript/TypeScript函数上下文"""
        contexts = []

        for i, line in enumerate(lines):
            line = line.strip()

            # 查找函数定义
            if ('function ' in line and '(' in line) or ('=>' in line and '(' in line):
                # 提取函数名
                if 'function ' in line:
                    function_name = line.split('function ')[1].split('(')[0].strip()
                else:
                    # 箭头函数，尝试从变量名推断
                    parts = line.split('=')[0].strip().split()
                    function_name = parts[-1] if parts else "anonymous"

                # 获取函数上下文
                start_line = max(0, i - 3)
                end_line = min(len(lines), i + 10)
                surrounding_lines = lines[start_line:end_line]

                context = CodeContext(
                    file_path=file_path,
                    line_number=i + 1,
                    function_name=function_name,
                    surrounding_lines=surrounding_lines
                )
                contexts.append(context)

        return contexts

    def _extract_class_contexts(self, file_path: str, lines: List[str], language: str) -> List[CodeContext]:
        """提取类定义上下文"""
        contexts = []

        for i, line in enumerate(lines):
            line = line.strip()

            # 查找类定义
            if language == "python" and line.startswith('class '):
                class_name = line.split('(')[0].replace('class ', '').strip()

                start_line = max(0, i - 2)
                end_line = min(len(lines), i + 15)
                surrounding_lines = lines[start_line:end_line]

                context = CodeContext(
                    file_path=file_path,
                    line_number=i + 1,
                    class_name=class_name,
                    surrounding_lines=surrounding_lines
                )
                contexts.append(context)

        return contexts

    def _create_generic_contexts(self, file_path: str, lines: List[str]) -> List[CodeContext]:
        """创建通用上下文"""
        contexts = []

        # 每50行创建一个上下文
        for i in range(0, len(lines), 50):
            start_line = i
            end_line = min(len(lines), i + 50)
            surrounding_lines = lines[start_line:end_line]

            context = CodeContext(
                file_path=file_path,
                line_number=start_line + 1,
                surrounding_lines=surrounding_lines
            )
            contexts.append(context)

        return contexts

    def _determine_detection_focus(self,
                                 selected_files: List[Dict[str, Any]],
                                 static_analysis_results: Dict[str, StaticAnalysisResult],
                                 user_preferences: Dict[str, Any]) -> List[str]:
        """确定检测重点"""
        focus_areas = []

        # 基于用户偏好
        if user_preferences.get("focus_areas"):
            focus_areas.extend(user_preferences["focus_areas"])

        # 基于静态分析结果
        issue_types = set()
        for result in static_analysis_results.values():
            for issue in result.issues:
                category = issue.get("category", "").lower()
                if "security" in category:
                    issue_types.add("security")
                elif "performance" in category:
                    issue_types.add("performance")
                elif "style" in category:
                    issue_types.add("code_quality")

        focus_areas.extend(list(issue_types))

        # 基于文件特征
        high_priority_files = [f for f in selected_files if f.get("priority") == "high"]
        if len(high_priority_files) > len(selected_files) * 0.3:
            focus_areas.append("high_priority_files")

        # 去重并返回
        return list(set(focus_areas))

    def _generate_context_statistics(self, context: ProblemDetectionContext) -> Dict[str, Any]:
        """生成上下文统计"""
        stats = {
            "total_files": len(context.selected_files),
            "total_issues": 0,
            "language_distribution": {},
            "priority_distribution": {"high": 0, "medium": 0, "low": 0},
            "complexity_distribution": {"低": 0, "中": 0, "高": 0},
            "estimated_analysis_time": 0.0
        }

        # 统计文件信息
        for file_data in context.selected_files:
            # 语言分布
            lang = file_data.get("language", "unknown")
            stats["language_distribution"][lang] = stats["language_distribution"].get(lang, 0) + 1

            # 优先级分布
            priority = file_data.get("priority", "medium")
            stats["priority_distribution"][priority] += 1

            # 复杂度分布
            complexity = file_data.get("estimated_complexity", "中")
            stats["complexity_distribution"][complexity] += 1

            # 预期修复数量
            stats["total_issues"] += file_data.get("expected_fixes", 0)

        # 估算分析时间（每个文件平均2分钟）
        stats["estimated_analysis_time"] = len(context.selected_files) * 2

        return stats

    def _estimate_token_usage(self, context: ProblemDetectionContext) -> int:
        """估算token使用量"""
        total_chars = 0

        # 项目信息
        total_chars += len(json.dumps(context.project_info, ensure_ascii=False))

        # 文件列表
        total_chars += len(json.dumps(context.selected_files, ensure_ascii=False))

        # 文件内容（限制数量）
        content_chars = sum(len(content) for content in context.file_contents.values())
        total_chars += min(content_chars, 100000)  # 限制内容字符数

        # 静态分析结果
        analysis_chars = len(json.dumps(context.static_analysis_results, ensure_ascii=False))
        total_chars += min(analysis_chars, 50000)  # 限制分析结果字符数

        # 其他数据
        total_chars += len(json.dumps(context.user_preferences, ensure_ascii=False))
        total_chars += len(json.dumps(context.detection_focus, ensure_ascii=False))

        # 粗略估算token数（中文字符按1:1，英文字符按4:1）
        chinese_chars = len([c for c in str(total_chars) if ord(c) > 127])
        other_chars = total_chars - chinese_chars

        estimated_tokens = chinese_chars + (other_chars // 4)

        return estimated_tokens

    def _generate_context_id(self) -> str:
        """生成上下文ID"""
        import uuid
        return f"context_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"

    def optimize_context_for_tokens(self,
                                  context: ProblemDetectionContext,
                                  target_tokens: int) -> ProblemDetectionContext:
        """
        优化上下文以控制token数量

        Args:
            context: 原始上下文
            target_tokens: 目标token数量

        Returns:
            ProblemDetectionContext: 优化后的上下文
        """
        if context.token_estimate <= target_tokens:
            return context

        self.logger.info(f"优化上下文，当前token数: {context.token_estimate}, 目标: {target_tokens}")

        # 创建优化的上下文副本
        optimized_context = ProblemDetectionContext(
            context_id=context.context_id + "_optimized",
            project_info=context.project_info,
            selected_files=context.selected_files[:20],  # 限制文件数量
            static_analysis_results=context.static_analysis_results,
            user_preferences=context.user_preferences,
            detection_focus=context.detection_focus,
            build_timestamp=context.build_timestamp
        )

        # 优化文件内容
        optimized_file_contents = {}
        for file_path, content in list(context.file_contents.items())[:20]:
            # 进一步限制内容长度
            if len(content) > 5000:
                optimized_content = content[:5000] + "\n... (内容截断)"
                optimized_file_contents[file_path] = optimized_content
            else:
                optimized_file_contents[file_path] = content

        optimized_context.file_contents = optimized_file_contents

        # 简化代码上下文
        optimized_code_contexts = {}
        for file_path, contexts in list(context.code_contexts.items())[:15]:
            # 每个文件最多保留5个上下文
            optimized_contexts = contexts[:5]
            optimized_code_contexts[file_path] = optimized_contexts

        optimized_context.code_contexts = optimized_code_contexts

        # 重新估算token数量
        optimized_context.token_estimate = self._estimate_token_usage(optimized_context)

        self.logger.info(f"上下文优化完成，新token数: {optimized_context.token_estimate}")

        return optimized_context


# 便捷函数
def build_problem_detection_context(selected_files: List[Dict[str, Any]],
                                   static_analysis_results: Dict[str, Any],
                                   project_structure: Optional[Any] = None,
                                   user_preferences: Optional[Dict[str, Any]] = None,
                                   max_tokens: int = 8000) -> Dict[str, Any]:
    """
    便捷的问题检测上下文构建函数

    Args:
        selected_files: 选择的文件列表
        static_analysis_results: 静态分析结果
        project_structure: 项目结构信息
        user_preferences: 用户偏好
        max_tokens: 最大token数

    Returns:
        Dict[str, Any]: 构建的上下文
    """
    builder = ProblemDetectionContextBuilder()
    context = builder.build_context(
        selected_files=selected_files,
        static_analysis_results=static_analysis_results,
        project_structure=project_structure,
        user_preferences=user_preferences
    )

    # 如果token过多，进行优化
    if context.token_estimate > max_tokens:
        context = builder.optimize_context_for_tokens(context, max_tokens)

    return context.to_dict()