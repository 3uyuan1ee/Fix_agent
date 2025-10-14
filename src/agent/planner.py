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
            # 静态分析任务 - 暂时返回空列表
            tasks = []

        elif request.mode == AnalysisMode.DEEP:
            # 深度分析任务 - 暂时返回空列表
            tasks = []

        elif request.mode == AnalysisMode.FIX:
            # 修复分析任务 - 暂时返回空列表
            tasks = []

        self.logger.debug(f"Created {len(tasks)} tasks for {request.mode.value} mode")
        return tasks

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