"""
任务规划器模块
负责分析用户需求，制定执行计划和任务序列
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ..utils.logger import get_logger
from ..utils.config import get_config_manager


class AnalysisMode(Enum):
    """分析模式枚举"""
    STATIC = "static"
    DEEP = "deep"
    FIX = "fix"


@dataclass
class UserRequest:
    """用户请求数据结构"""
    raw_input: str
    mode: AnalysisMode
    target_path: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    intent: str = ""


@dataclass
class Task:
    """任务数据结构"""
    task_id: str
    task_type: str
    description: str
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


@dataclass
class ExecutionPlan:
    """执行计划数据结构"""
    plan_id: str
    mode: AnalysisMode
    target_path: str
    tasks: List[Task]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: __import__('time').time())


class TaskPlanner:
    """任务规划器"""

    def __init__(self, config_manager=None):
        """
        初始化任务规划器

        Args:
            config_manager: 配置管理器实例
        """
        self.logger = get_logger()
        self.config_manager = config_manager or get_config_manager()

        # 解析器配置
        self.config = self.config_manager.get_section('planner') or {}

        # 支持的关键词
        self.static_keywords = ['static', 'quick', 'fast', 'basic', 'simple', '静态', '快速', '基础', '简单']
        self.deep_keywords = ['deep', 'detailed', 'thorough', 'comprehensive', '深度', '详细', '全面', '智能']
        self.fix_keywords = ['fix', 'repair', 'resolve', 'correct', '修复', '修复', '解决', '更正']

        # 支持的文件扩展名
        self.supported_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.hpp'}

        self.logger.info("TaskPlanner initialized")

    def parse_user_request(self, user_input: str, current_path: str = ".") -> UserRequest:
        """
        解析用户输入需求

        Args:
            user_input: 用户输入
            current_path: 当前工作路径

        Returns:
            解析后的用户请求
        """
        self.logger.debug(f"Parsing user request: {user_input}")

        # 清理输入
        cleaned_input = user_input.strip()

        # 检测分析模式
        mode = self._detect_analysis_mode(cleaned_input)

        # 提取目标路径
        target_path = self._extract_target_path(cleaned_input, current_path)

        # 提取选项
        options = self._extract_options(cleaned_input)

        # 提取关键词
        keywords = self._extract_keywords(cleaned_input)

        # 分析用户意图
        intent = self._analyze_intent(cleaned_input, mode)

        request = UserRequest(
            raw_input=user_input,
            mode=mode,
            target_path=target_path,
            options=options,
            keywords=keywords,
            intent=intent
        )

        self.logger.info(f"Parsed request: mode={mode.value}, target={target_path}, intent={intent}")
        return request

    def create_execution_plan(self, request: UserRequest) -> ExecutionPlan:
        """
        创建执行计划

        Args:
            request: 用户请求

        Returns:
            执行计划
        """
        self.logger.info(f"Creating execution plan for mode: {request.mode.value}")

        plan_id = self._generate_plan_id()
        target_path = request.target_path or os.getcwd()

        # 根据模式创建任务
        tasks = self._create_tasks_for_mode(request)

        plan = ExecutionPlan(
            plan_id=plan_id,
            mode=request.mode,
            target_path=target_path,
            tasks=tasks,
            metadata={
                'user_request': request.raw_input,
                'keywords': request.keywords,
                'intent': request.intent,
                'options': request.options
            }
        )

        self.logger.info(f"Created execution plan {plan_id} with {len(tasks)} tasks")
        return plan

    def validate_plan(self, plan: ExecutionPlan, allow_empty_tasks: bool = True) -> Tuple[bool, List[str]]:
        """
        验证执行计划

        Args:
            plan: 执行计划
            allow_empty_tasks: 是否允许空任务列表（T014阶段允许）

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 检查目标路径
        if not plan.target_path or not os.path.exists(plan.target_path):
            errors.append(f"Target path does not exist: {plan.target_path}")

        # 检查任务
        if not plan.tasks:
            if not allow_empty_tasks:
                errors.append("No tasks in execution plan")
        else:
            # 只有当有任务时才检查依赖和优先级
            # 检查任务依赖
            task_ids = {task.task_id for task in plan.tasks}
            for task in plan.tasks:
                for dep in task.dependencies:
                    if dep not in task_ids:
                        errors.append(f"Task {task.task_id} depends on non-existent task {dep}")

            # 检查优先级
            for task in plan.tasks:
                if task.priority < 1 or task.priority > 10:
                    errors.append(f"Task {task.task_id} has invalid priority: {task.priority}")

        is_valid = len(errors) == 0
        if not is_valid:
            self.logger.warning(f"Plan validation failed: {errors}")
        else:
            self.logger.info("Plan validation passed")

        return is_valid, errors

    def _detect_analysis_mode(self, user_input: str) -> AnalysisMode:
        """检测分析模式"""
        input_lower = user_input.lower()

        # 检查每种模式的关键词
        if any(keyword in input_lower for keyword in self.static_keywords):
            return AnalysisMode.STATIC
        elif any(keyword in input_lower for keyword in self.fix_keywords):
            return AnalysisMode.FIX
        elif any(keyword in input_lower for keyword in self.deep_keywords):
            return AnalysisMode.DEEP

        # 默认使用静态分析
        return AnalysisMode.STATIC

    def _extract_target_path(self, user_input: str, current_path: str) -> Optional[str]:
        """提取目标路径"""
        # 匹配路径模式
        path_patterns = [
            r'(?:path|dir|directory|folder)[\s:=]+([^\s]+)',
            r'([\/\w\.-]+\/[^\s]*)',  # Unix路径
            r'([A-Za-z]:\\[^\s]*)',   # Windows路径
            r'\.\/([^\s]+)',          # 相对路径
        ]

        for pattern in path_patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            if matches:
                path = matches[0].strip('\'"')
                # 转换为绝对路径
                if not os.path.isabs(path):
                    path = os.path.abspath(os.path.join(current_path, path))
                return path

        # 如果没有找到路径，返回当前路径
        return os.path.abspath(current_path)

    def _extract_options(self, user_input: str) -> Dict[str, Any]:
        """提取选项参数"""
        options = {}

        # 匹配键值对选项 - 修复正则表达式
        # 格式：--key value, --key=value, -k value, -k=value
        pattern = r'--?([a-zA-Z0-9_-]+)(?:[=\s]+([^\s-]+))?'
        matches = re.finditer(pattern, user_input)

        for match in matches:
            key = match.group(1)
            value = match.group(2) if match.group(2) is not None else True

            # 转换值类型
            if value is not True:
                if isinstance(value, str):
                    if value.lower() in ['true', 'false']:
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    elif '.' in value and value.replace('.', '').isdigit():
                        value = float(value)

            options[key] = value

        return options

    def _extract_keywords(self, user_input: str) -> List[str]:
        """提取关键词"""
        keywords = []

        # 技术关键词
        tech_keywords = [
            'security', 'performance', 'bug', 'error', 'vulnerability', 'issue',
            'refactor', 'optimize', 'cleanup', 'test', 'documentation',
            '安全', '性能', '漏洞', '错误', '问题', '重构', '优化', '清理', '测试', '文档'
        ]

        # 代码质量关键词
        quality_keywords = [
            'maintainability', 'readability', 'complexity', 'duplication',
            'style', 'convention', 'best practice', 'anti-pattern',
            '可维护性', '可读性', '复杂度', '重复', '风格', '约定', '最佳实践', '反模式'
        ]

        all_keywords = tech_keywords + quality_keywords

        for keyword in all_keywords:
            if keyword in user_input.lower():
                keywords.append(keyword)

        return keywords

    def _analyze_intent(self, user_input: str, mode: AnalysisMode) -> str:
        """分析用户意图"""
        input_lower = user_input.lower()

        if mode == AnalysisMode.STATIC:
            # 优先检查特定意图
            if any(word in input_lower for word in ['style', 'format', 'convention']):
                return "代码风格检查"
            elif any(word in input_lower for word in ['security', 'vulnerable']):
                return "安全漏洞扫描"
            elif any(word in input_lower for word in ['quick', 'fast', 'check']):
                return "快速检查代码质量"
            else:
                return "基础静态分析"

        elif mode == AnalysisMode.DEEP:
            if any(word in input_lower for word in ['architecture', 'design']):
                return "架构分析"
            elif any(word in input_lower for word in ['performance', 'optimize']):
                return "性能优化分析"
            else:
                return "深度代码分析"

        elif mode == AnalysisMode.FIX:
            if any(word in input_lower for word in ['auto', 'automatic']):
                return "自动修复问题"
            else:
                return "问题修复建议"

        return "通用分析"

    def _generate_plan_id(self) -> str:
        """生成计划ID"""
        import uuid
        return f"plan_{uuid.uuid4().hex[:8]}"

    def _create_tasks_for_mode(self, request: UserRequest) -> List[Task]:
        """根据模式创建任务"""
        tasks = []

        if request.mode == AnalysisMode.STATIC:
            tasks = self._create_static_analysis_tasks(request)
        elif request.mode == AnalysisMode.DEEP:
            tasks = self._create_deep_analysis_tasks(request)
        elif request.mode == AnalysisMode.FIX:
            tasks = self._create_fix_analysis_tasks(request)

        self.logger.debug(f"Created {len(tasks)} tasks for {request.mode.value} mode")
        return tasks

    def _create_static_analysis_tasks(self, request: UserRequest) -> List[Task]:
        """创建静态分析任务序列"""
        tasks = []

        # 任务1: 文件选择
        file_selector_task = Task(
            task_id="static_file_selection",
            task_type="file_selection",
            description="选择需要分析的Python文件",
            priority=1,
            parameters={
                "keywords": request.keywords,
                "max_files": request.options.get("max_files", 100),
                "target_path": request.target_path
            }
        )
        tasks.append(file_selector_task)

        # 任务2: AST语法分析
        ast_task = Task(
            task_id="static_ast_analysis",
            task_type="ast_analysis",
            description="执行AST语法分析，检查语法错误和基本结构",
            priority=2,
            dependencies=["static_file_selection"],
            parameters={
                "check_syntax": True,
                "extract_structure": True
            }
        )
        tasks.append(ast_task)

        # 任务3: Pylint代码质量检查
        pylint_task = Task(
            task_id="static_pylint_analysis",
            task_type="pylint_analysis",
            description="执行Pylint代码质量检查",
            priority=3,
            dependencies=["static_file_selection"],
            parameters={
                "disable_rules": request.options.get("pylint_disable", []),
                "enable_rules": request.options.get("pylint_enable", [])
            }
        )
        tasks.append(pylint_task)

        # 任务4: Flake8代码风格检查
        flake8_task = Task(
            task_id="static_flake8_analysis",
            task_type="flake8_analysis",
            description="执行Flake8代码风格检查",
            priority=3,
            dependencies=["static_file_selection"],
            parameters={
                "max_line_length": request.options.get("max_line_length", 88),
                "ignore_errors": request.options.get("flake8_ignore", [])
            }
        )
        tasks.append(flake8_task)

        # 任务5: Bandit安全检查
        bandit_task = Task(
            task_id="static_bandit_analysis",
            task_type="bandit_analysis",
            description="执行Bandit安全漏洞检查",
            priority=3,
            dependencies=["static_file_selection"],
            parameters={
                "severity_level": request.options.get("security_level", "medium"),
                "confidence_level": request.options.get("confidence_level", "medium")
            }
        )
        tasks.append(bandit_task)

        # 任务6: 结果合并和报告生成
        report_task = Task(
            task_id="static_report_generation",
            task_type="report_generation",
            description="合并分析结果并生成综合报告",
            priority=4,
            dependencies=["static_ast_analysis", "static_pylint_analysis",
                         "static_flake8_analysis", "static_bandit_analysis"],
            parameters={
                "output_format": request.options.get("output_format", "json"),
                "sort_by_severity": True,
                "group_by_file": True
            }
        )
        tasks.append(report_task)

        return tasks

    def _create_deep_analysis_tasks(self, request: UserRequest) -> List[Task]:
        """创建深度分析任务序列"""
        tasks = []

        # 任务1: 智能文件选择
        file_selector_task = Task(
            task_id="deep_file_selection",
            task_type="intelligent_file_selection",
            description="基于用户需求和依赖关系智能选择重要文件",
            priority=1,
            parameters={
                "keywords": request.keywords,
                "max_files": request.options.get("max_files", 20),
                "target_path": request.target_path,
                "analyze_dependencies": True,
                "prioritize_recent": True
            }
        )
        tasks.append(file_selector_task)

        # 任务2: 文件内容读取和分析
        content_analysis_task = Task(
            task_id="deep_content_analysis",
            task_type="content_analysis",
            description="深度分析选定文件的内容和结构",
            priority=2,
            dependencies=["deep_file_selection"],
            parameters={
                "analyze_complexity": True,
                "extract_patterns": True,
                "identify_smells": True
            }
        )
        tasks.append(content_analysis_task)

        # 任务3: LLM分析准备
        llm_prep_task = Task(
            task_id="deep_llm_preparation",
            task_type="llm_preparation",
            description="准备LLM分析的上下文和prompt",
            priority=3,
            dependencies=["deep_content_analysis"],
            parameters={
                "analysis_type": self._determine_analysis_type(request),
                "include_context": True,
                "prompt_template": "deep_analysis"
            }
        )
        tasks.append(llm_prep_task)

        # 任务4: LLM深度分析
        llm_analysis_task = Task(
            task_id="deep_llm_analysis",
            task_type="llm_analysis",
            description="使用LLM进行深度代码分析",
            priority=4,
            dependencies=["deep_llm_preparation"],
            parameters={
                "model": request.options.get("model", "gpt-3.5-turbo"),
                "temperature": request.options.get("temperature", 0.3),
                "max_tokens": request.options.get("max_tokens", 2000)
            }
        )
        tasks.append(llm_analysis_task)

        # 任务5: 结果整理和格式化
        result_format_task = Task(
            task_id="deep_result_formatting",
            task_type="result_formatting",
            description="整理和格式化LLM分析结果",
            priority=5,
            dependencies=["deep_llm_analysis"],
            parameters={
                "output_format": request.options.get("output_format", "structured"),
                "include_suggestions": True,
                "include_examples": True
            }
        )
        tasks.append(result_format_task)

        return tasks

    def _create_fix_analysis_tasks(self, request: UserRequest) -> List[Task]:
        """创建修复分析任务序列"""
        tasks = []

        # 任务1: 问题检测和分析
        problem_detection_task = Task(
            task_id="fix_problem_detection",
            task_type="problem_detection",
            description="检测代码中存在的问题",
            priority=1,
            parameters={
                "target_path": request.target_path,
                "analysis_scope": request.options.get("scope", "all"),
                "severity_threshold": request.options.get("severity", "medium")
            }
        )
        tasks.append(problem_detection_task)

        # 任务2: 问题分类和优先级排序
        problem_classification_task = Task(
            task_id="fix_problem_classification",
            task_type="problem_classification",
            description="对检测到的问题进行分类和优先级排序",
            priority=2,
            dependencies=["fix_problem_detection"],
            parameters={
                "group_by_type": True,
                "sort_by_priority": True,
                "auto_fixable_only": request.options.get("auto_fix_only", False)
            }
        )
        tasks.append(problem_classification_task)

        # 任务3: LLM修复建议生成
        fix_suggestion_task = Task(
            task_id="fix_suggestion_generation",
            task_type="fix_suggestion_generation",
            description="使用LLM生成具体的修复建议和代码",
            priority=3,
            dependencies=["fix_problem_classification"],
            parameters={
                "include_explanation": True,
                "include_diff": True,
                "verify_fix": True
            }
        )
        tasks.append(fix_suggestion_task)

        # 任务4: 用户确认和验证
        user_confirmation_task = Task(
            task_id="fix_user_confirmation",
            task_type="user_confirmation",
            description="等待用户确认修复操作",
            priority=4,
            dependencies=["fix_suggestion_generation"],
            parameters={
                "show_diff": True,
                "show_backup_info": True,
                "allow_batch_confirmation": request.options.get("batch", False)
            }
        )
        tasks.append(user_confirmation_task)

        # 任务5: 代码修复执行
        fix_execution_task = Task(
            task_id="fix_execution",
            task_type="fix_execution",
            description="执行代码修复操作",
            priority=5,
            dependencies=["fix_user_confirmation"],
            parameters={
                "create_backup": True,
                "apply_fixes": True,
                "verify_after_fix": True
            }
        )
        tasks.append(fix_execution_task)

        # 任务6: 修复结果报告
        fix_report_task = Task(
            task_id="fix_report_generation",
            task_type="fix_report_generation",
            description="生成修复结果报告",
            priority=6,
            dependencies=["fix_execution"],
            parameters={
                "include_summary": True,
                "include_changes": True,
                "include_validation": True
            }
        )
        tasks.append(fix_report_task)

        return tasks

    def _determine_analysis_type(self, request: UserRequest) -> str:
        """确定深度分析的类型"""
        intent = request.intent.lower()
        keywords = [k.lower() for k in request.keywords]

        if any(word in intent or word in keywords for word in ['architecture', 'design', '架构', '设计']):
            return "architecture"
        elif any(word in intent or word in keywords for word in ['performance', 'optimize', '性能', '优化']):
            return "performance"
        elif any(word in intent or word in keywords for word in ['security', 'vulnerability', '安全', '漏洞']):
            return "security"
        elif any(word in intent or word in keywords for word in ['maintainability', 'readability', '可维护性', '可读性']):
            return "maintainability"
        elif any(word in intent or word in keywords for word in ['refactor', 'cleanup', '重构', '清理']):
            return "refactor"
        else:
            return "comprehensive"

    def get_supported_modes(self) -> List[str]:
        """获取支持的分析模式"""
        return [mode.value for mode in AnalysisMode]

    def get_mode_description(self, mode: str) -> str:
        """获取模式描述"""
        descriptions = {
            "static": "静态分析：使用工具快速检查代码质量、安全和风格问题",
            "deep": "深度分析：使用AI进行深入的代码分析和建议",
            "fix": "修复分析：分析问题并提供修复建议和代码"
        }
        return descriptions.get(mode, "未知模式")