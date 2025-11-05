"""
项目分析配置管理器
Project Analysis Configuration Manager

负责加载、管理和验证项目分析工作流的所有配置参数
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from ..utils.config import get_config_manager


@dataclass
class BasicConfig:
    """基本配置"""

    analysis_mode: str = "comprehensive"
    max_concurrent_files: int = 5
    max_concurrent_analyses: int = 3
    file_analysis_timeout: int = 300
    total_analysis_timeout: int = 3600


@dataclass
class FileSelectionConfig:
    """文件选择配置"""

    max_files_to_analyze: int = 50
    max_tokens_per_file: int = 4000
    max_total_tokens: int = 50000
    max_file_size: int = 1048576
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)


@dataclass
class ImportanceScoringConfig:
    """重要性评分配置"""

    weights: Dict[str, float] = field(default_factory=dict)
    complexity_thresholds: Dict[str, int] = field(default_factory=dict)
    issue_density_thresholds: Dict[str, int] = field(default_factory=dict)


@dataclass
class StaticAnalysisConfig:
    """静态分析配置"""

    enabled_tools: List[str] = field(default_factory=list)
    tool_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIAnalysisConfig:
    """AI分析配置"""

    provider: str = "zhipu"
    model: str = "glm-4.5-air"
    temperature: float = 0.3
    max_tokens: int = 4000
    context_priority: str = "balanced"
    include_related_files: bool = True
    max_related_files: int = 3
    context_lines: int = 5
    analysis_depth: str = "standard"
    focus_areas: List[str] = field(default_factory=list)


@dataclass
class FixGenerationConfig:
    """修复建议配置"""

    default_strategy: str = "suggestion_only"
    risk_thresholds: Dict[str, str] = field(default_factory=dict)
    confidence_threshold: float = 0.7
    analyze_impact: bool = True
    check_breaking_changes: bool = True
    generate_alternatives: bool = True
    max_alternatives: int = 3
    include_tests: bool = True


@dataclass
class ReportingConfig:
    """报告配置"""

    formats: List[str] = field(default_factory=list)
    include_sections: List[str] = field(default_factory=list)
    detail_level: str = "standard"
    generate_charts: bool = True
    include_code_snippets: bool = True


@dataclass
class CacheConfig:
    """缓存配置"""

    enabled: bool = True
    cache_dir: str = ".cache/project_analysis"
    ttl: int = 86400
    max_size: int = 104857600
    cache_analysis_results: bool = True
    cache_ai_responses: bool = True
    cache_importance_scores: bool = True


@dataclass
class PerformanceConfig:
    """性能配置"""

    max_memory_mb: int = 2048
    max_processes: int = 4
    batch_size: int = 10
    rate_limit: int = 10


@dataclass
class CostControlConfig:
    """成本控制配置"""

    daily_token_limit: int = 100000
    monthly_token_limit: int = 1000000
    daily_budget_limit: float = 10.0
    monthly_budget_limit: float = 100.0
    track_costs: bool = True
    cost_alerts: bool = True


@dataclass
class SecurityConfig:
    """安全配置"""

    filter_secrets: bool = True
    secret_patterns: List[str] = field(default_factory=list)
    allow_code_execution: bool = False
    sandbox_mode: bool = True


@dataclass
class IntegrationConfig:
    """集成配置"""

    git: Dict[str, Any] = field(default_factory=dict)
    cicd: Dict[str, Any] = field(default_factory=dict)
    notifications: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LoggingConfig:
    """日志配置"""

    level: str = "INFO"
    format: str = "structured"
    outputs: List[str] = field(default_factory=list)
    log_file: str = "logs/project_analysis.log"
    max_file_size: str = "10MB"
    max_files: int = 5
    debug_mode: bool = False
    verbose_output: bool = False


@dataclass
class EnvironmentConfig:
    """环境配置"""

    work_dir: str = "./workspace"
    temp_dir: str = "./temp"
    backup_dir: str = "./backups"
    output_dir: str = "./output"


@dataclass
class AdvancedConfig:
    """高级配置"""

    experimental_features: Dict[str, bool] = field(default_factory=dict)
    plugins: Dict[str, Any] = field(default_factory=dict)
    custom_rules: Dict[str, Any] = field(default_factory=dict)


class ProjectAnalysisConfig:
    """项目分析配置管理器

    负责加载、验证和管理项目分析工作流的所有配置参数
    支持环境变量覆盖、配置验证和默认值处理
    """

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，默认使用项目根目录下的配置文件
        """
        self.config_file = config_file or self._get_default_config_path()
        self._config_data: Dict[str, Any] = {}
        self._logger = logging.getLogger(__name__)

        # 配置对象实例
        self.basic: BasicConfig = BasicConfig()
        self.file_selection: FileSelectionConfig = FileSelectionConfig()
        self.importance_scoring: ImportanceScoringConfig = ImportanceScoringConfig()
        self.static_analysis: StaticAnalysisConfig = StaticAnalysisConfig()
        self.ai_analysis: AIAnalysisConfig = AIAnalysisConfig()
        self.fix_generation: FixGenerationConfig = FixGenerationConfig()
        self.reporting: ReportingConfig = ReportingConfig()
        self.cache: CacheConfig = CacheConfig()
        self.performance: PerformanceConfig = PerformanceConfig()
        self.cost_control: CostControlConfig = CostControlConfig()
        self.security: SecurityConfig = SecurityConfig()
        self.integration: IntegrationConfig = IntegrationConfig()
        self.logging: LoggingConfig = LoggingConfig()
        self.environment: EnvironmentConfig = EnvironmentConfig()
        self.advanced: AdvancedConfig = AdvancedConfig()

        # 加载配置
        self.load_config()

    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        project_root = Path(__file__).parent.parent.parent
        return str(project_root / "config" / "project_analysis_config.yaml")

    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self._config_data = yaml.safe_load(f) or {}
                self._logger.info(f"配置文件加载成功: {self.config_file}")
            else:
                self._logger.warning(
                    f"配置文件不存在，使用默认配置: {self.config_file}"
                )
                self._config_data = {}

            # 处理环境变量覆盖
            self._apply_env_overrides()

            # 验证配置
            self._validate_config()

            # 更新配置对象
            self._update_config_objects()

        except Exception as e:
            self._logger.error(f"配置文件加载失败: {e}")
            raise

    def _apply_env_overrides(self) -> None:
        """应用环境变量覆盖"""
        env_mappings = {
            "PROJECT_ANALYSIS_MODE": ("basic", "analysis_mode"),
            "PROJECT_MAX_FILES": ("basic", "max_concurrent_files"),
            "PROJECT_AI_PROVIDER": ("ai_analysis", "provider"),
            "PROJECT_AI_MODEL": ("ai_analysis", "model"),
            "PROJECT_AI_TEMPERATURE": ("ai_analysis", "temperature"),
            "PROJECT_LOG_LEVEL": ("logging", "level"),
            "PROJECT_DEBUG": ("logging", "debug_mode"),
            "PROJECT_CACHE_DIR": ("cache", "cache_dir"),
            "PROJECT_WORK_DIR": ("environment", "work_dir"),
            "PROJECT_MAX_TOKENS": ("file_selection", "max_total_tokens"),
            "PROJECT_DAILY_BUDGET": ("cost_control", "daily_budget_limit"),
        }

        for env_var, (section, key) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # 确保section存在
                if section not in self._config_data:
                    self._config_data[section] = {}

                # 类型转换
                converted_value = self._convert_env_value(env_value, key)
                self._config_data[section][key] = converted_value
                self._logger.debug(
                    f"环境变量覆盖: {env_var} -> {section}.{key} = {converted_value}"
                )

    def _convert_env_value(self, value: str, key: str) -> Any:
        """转换环境变量值类型"""
        # 布尔值转换
        if key in ["debug_mode", "verbose_output", "enabled", "filter_secrets"]:
            return value.lower() in ("true", "1", "yes", "on")

        # 数字转换
        if key in [
            "max_concurrent_files",
            "temperature",
            "max_tokens",
            "daily_budget_limit",
        ]:
            try:
                if "." in value:
                    return float(value)
                else:
                    return int(value)
            except ValueError:
                self._logger.warning(f"无法转换环境变量值: {value} for {key}")
                return value

        return value

    def _validate_config(self) -> None:
        """验证配置参数"""
        # 基本验证
        if "basic" in self._config_data:
            basic = self._config_data["basic"]
            if basic.get("max_concurrent_files", 0) <= 0:
                raise ValueError("max_concurrent_files 必须大于0")
            if basic.get("file_analysis_timeout", 0) <= 0:
                raise ValueError("file_analysis_timeout 必须大于0")

        # 文件选择验证
        if "file_selection" in self._config_data:
            fs = self._config_data["file_selection"]
            if fs.get("max_files_to_analyze", 0) <= 0:
                raise ValueError("max_files_to_analyze 必须大于0")
            if fs.get("max_total_tokens", 0) <= 0:
                raise ValueError("max_total_tokens 必须大于0")

        # AI分析验证
        if "ai_analysis" in self._config_data:
            ai = self._config_data["ai_analysis"]
            valid_providers = ["zhipu", "openai", "anthropic"]
            if ai.get("provider") not in valid_providers:
                raise ValueError(f"AI提供商必须是以下之一: {valid_providers}")

            # 根据provider验证model的合理性
            provider = ai.get("provider")
            model = ai.get("model", "")
            if not model:
                raise ValueError("AI模型名称不能为空")

            temp = ai.get("temperature", 0)
            if not 0 <= temp <= 2:
                raise ValueError("AI temperature 必须在0-2之间")

        self._logger.debug("配置验证通过")

    def _update_config_objects(self) -> None:
        """更新配置对象"""
        # 更新基本配置
        if "basic" in self._config_data:
            self._update_dataclass(self.basic, self._config_data["basic"])

        # 更新其他配置
        config_mappings = [
            ("file_selection", self.file_selection),
            ("importance_scoring", self.importance_scoring),
            ("static_analysis", self.static_analysis),
            ("ai_analysis", self.ai_analysis),
            ("fix_generation", self.fix_generation),
            ("reporting", self.reporting),
            ("cache", self.cache),
            ("performance", self.performance),
            ("cost_control", self.cost_control),
            ("security", self.security),
            ("integration", self.integration),
            ("logging", self.logging),
            ("environment", self.environment),
            ("advanced", self.advanced),
        ]

        for section_name, config_obj in config_mappings:
            if section_name in self._config_data:
                self._update_dataclass(config_obj, self._config_data[section_name])

    def _update_dataclass(self, obj: Any, data: Dict[str, Any]) -> None:
        """更新dataclass对象属性"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)

    def get_config_value(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            section: 配置节名
            key: 配置键名
            default: 默认值

        Returns:
            配置值
        """
        return self._config_data.get(section, {}).get(key, default)

    def set_config_value(self, section: str, key: str, value: Any) -> None:
        """
        设置配置值

        Args:
            section: 配置节名
            key: 配置键名
            value: 配置值
        """
        if section not in self._config_data:
            self._config_data[section] = {}
        self._config_data[section][key] = value

    def reload_config(self) -> None:
        """重新加载配置"""
        self.load_config()

    def save_config(self, file_path: Optional[str] = None) -> None:
        """
        保存配置到文件

        Args:
            file_path: 保存路径，默认使用原配置文件路径
        """
        save_path = file_path or self.config_file
        try:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    self._config_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                )
            self._logger.info(f"配置已保存到: {save_path}")
        except Exception as e:
            self._logger.error(f"配置保存失败: {e}")
            raise

    def get_effective_config(self) -> Dict[str, Any]:
        """获取有效配置（包含默认值）"""
        return {
            "basic": self.basic.__dict__,
            "file_selection": self.file_selection.__dict__,
            "importance_scoring": self.importance_scoring.__dict__,
            "static_analysis": self.static_analysis.__dict__,
            "ai_analysis": self.ai_analysis.__dict__,
            "fix_generation": self.fix_generation.__dict__,
            "reporting": self.reporting.__dict__,
            "cache": self.cache.__dict__,
            "performance": self.performance.__dict__,
            "cost_control": self.cost_control.__dict__,
            "security": self.security.__dict__,
            "integration": self.integration.__dict__,
            "logging": self.logging.__dict__,
            "environment": self.environment.__dict__,
            "advanced": self.advanced.__dict__,
        }

    def validate_analysis_feasibility(
        self, file_count: int, estimated_tokens: int
    ) -> Dict[str, Any]:
        """
        验证分析可行性

        Args:
            file_count: 文件数量
            estimated_tokens: 估计的token数量

        Returns:
            验证结果
        """
        result = {"feasible": True, "warnings": [], "errors": [], "recommendations": []}

        # 文件数量检查
        if file_count > self.file_selection.max_files_to_analyze:
            result["warnings"].append(
                f"文件数量({file_count})超过限制({self.file_selection.max_files_to_analyze})"
            )
            result["recommendations"].append("考虑减少分析文件数量或调整配置")

        # Token数量检查
        if estimated_tokens > self.file_selection.max_total_tokens:
            result["errors"].append(
                f"估计token数量({estimated_tokens})超过限制({self.file_selection.max_total_tokens})"
            )
            result["feasible"] = False

        # 预算检查
        if self.cost_control.track_costs:
            # 简单的成本估算（假设每个token成本为$0.00001）
            estimated_cost = estimated_tokens * 0.00001
            if estimated_cost > self.cost_control.daily_budget_limit:
                result["warnings"].append(
                    f"估计成本(${estimated_cost:.2f})超过日预算限制(${self.cost_control.daily_budget_limit})"
                )

        return result

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """
        获取特定工具的配置

        Args:
            tool_name: 工具名称

        Returns:
            工具配置
        """
        return self.static_analysis.tool_configs.get(tool_name, {})

    def is_tool_enabled(self, tool_name: str) -> bool:
        """
        检查工具是否启用

        Args:
            tool_name: 工具名称

        Returns:
            是否启用
        """
        return tool_name in self.static_analysis.enabled_tools


# 全局配置实例
_config_instance: Optional[ProjectAnalysisConfig] = None


def get_project_analysis_config(
    config_file: Optional[str] = None,
) -> ProjectAnalysisConfig:
    """
    获取全局配置实例

    Args:
        config_file: 配置文件路径

    Returns:
        配置实例
    """
    global _config_instance
    if _config_instance is None or config_file is not None:
        _config_instance = ProjectAnalysisConfig(config_file)
    return _config_instance


def reload_project_analysis_config() -> None:
    """重新加载全局配置"""
    global _config_instance
    if _config_instance is not None:
        _config_instance.reload_config()
