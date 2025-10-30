"""
工作流特定数据结构
定义工作流各节点间的标准化数据结构
"""

import uuid
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..utils.logger import get_logger


class ProblemType(Enum):
    """问题类型枚举"""
    SECURITY = "security"        # 安全问题
    PERFORMANCE = "performance"  # 性能问题
    LOGIC = "logic"             # 逻辑问题
    STYLE = "style"             # 代码风格
    MAINTAINABILITY = "maintainability"  # 可维护性问题
    RELIABILITY = "reliability"  # 可靠性问题
    COMPATIBILITY = "compatibility"    # 兼容性问题
    DOCUMENTATION = "documentation"    # 文档问题


class SeverityLevel(Enum):
    """严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskLevel(Enum):
    """风险级别枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FixType(Enum):
    """修复类型枚举"""
    CODE_REPLACEMENT = "code_replacement"    # 代码替换
    CODE_INSERTION = "code_insertion"        # 代码插入
    CODE_DELETION = "code_deletion"          # 代码删除
    REFACTORING = "refactoring"              # 重构
    CONFIGURATION = "configuration"          # 配置修改
    DEPENDENCY_UPDATE = "dependency_update"  # 依赖更新


@dataclass
class CodeContext:
    """代码上下文"""
    file_path: str
    line_number: int
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    module_name: Optional[str] = None
    surrounding_lines: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "function_name": self.function_name,
            "class_name": self.class_name,
            "module_name": self.module_name,
            "surrounding_lines": self.surrounding_lines,
            "imports": self.imports,
            "variables": self.variables
        }


@dataclass
class AIDetectedProblem:
    """AI检测到的问题 - 节点B输出"""
    problem_id: str
    file_path: str
    line_number: int
    problem_type: ProblemType
    severity: SeverityLevel
    description: str
    code_snippet: str
    confidence: float  # 0.0-1.0
    reasoning: str
    suggested_fix_type: FixType = FixType.CODE_REPLACEMENT
    context: Optional[CodeContext] = None
    tags: List[str] = field(default_factory=list)
    estimated_fix_time: int = 0  # 分钟
    dependencies: List[str] = field(default_factory=list)
    detection_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "problem_id": self.problem_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "problem_type": self.problem_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "code_snippet": self.code_snippet,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "suggested_fix_type": self.suggested_fix_type.value,
            "context": self.context.to_dict() if self.context else None,
            "tags": self.tags,
            "estimated_fix_time": self.estimated_fix_time,
            "dependencies": self.dependencies,
            "detection_timestamp": self.detection_timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIDetectedProblem':
        """从字典创建实例"""
        data["problem_type"] = ProblemType(data["problem_type"])
        data["severity"] = SeverityLevel(data["severity"])
        data["suggested_fix_type"] = FixType(data["suggested_fix_type"])
        data["detection_timestamp"] = datetime.fromisoformat(data["detection_timestamp"])

        if data.get("context"):
            data["context"] = CodeContext(**data["context"])

        return cls(**data)


@dataclass
class AlternativeFix:
    """替代修复方案"""
    fix_id: str
    approach: str
    code: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    estimated_time: int = 0  # 分钟
    compatibility: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "fix_id": self.fix_id,
            "approach": self.approach,
            "code": self.code,
            "pros": self.pros,
            "cons": self.cons,
            "risk_level": self.risk_level.value,
            "estimated_time": self.estimated_time,
            "compatibility": self.compatibility
        }


@dataclass
class AIFixSuggestion:
    """AI修复建议 - 节点C输出"""
    suggestion_id: str
    problem_id: str
    file_path: str
    line_number: int
    original_code: str
    suggested_code: str
    explanation: str
    reasoning: str
    confidence: float  # 0.0-1.0
    risk_level: RiskLevel = RiskLevel.MEDIUM
    side_effects: List[str] = field(default_factory=list)
    alternatives: List[AlternativeFix] = field(default_factory=list)
    estimated_impact: str = ""
    fix_type: FixType = FixType.CODE_REPLACEMENT
    dependencies: List[str] = field(default_factory=list)
    testing_requirements: List[str] = field(default_factory=list)
    generation_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "suggestion_id": self.suggestion_id,
            "problem_id": self.problem_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "original_code": self.original_code,
            "suggested_code": self.suggested_code,
            "explanation": self.explanation,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "risk_level": self.risk_level.value,
            "side_effects": self.side_effects,
            "alternatives": [alt.to_dict() for alt in self.alternatives],
            "estimated_impact": self.estimated_impact,
            "fix_type": self.fix_type.value,
            "dependencies": self.dependencies,
            "testing_requirements": self.testing_requirements,
            "generation_timestamp": self.generation_timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIFixSuggestion':
        """从字典创建实例"""
        data["risk_level"] = RiskLevel(data["risk_level"])
        data["fix_type"] = FixType(data["fix_type"])
        data["generation_timestamp"] = datetime.fromisoformat(data["generation_timestamp"])

        # 重建替代方案
        alternatives = []
        for alt_data in data.get("alternatives", []):
            alt_data["risk_level"] = RiskLevel(alt_data["risk_level"])
            alternatives.append(AlternativeFix(**alt_data))
        data["alternatives"] = alternatives

        return cls(**data)


@dataclass
class StaticAnalysisIssue:
    """静态分析问题"""
    tool_name: str
    rule_id: str
    severity: SeverityLevel
    message: str
    line_number: int
    column_number: Optional[int] = None
    category: str = ""
    source_file: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "tool_name": self.tool_name,
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "line_number": self.line_number,
            "column_number": self.column_number,
            "category": self.category,
            "source_file": self.source_file
        }


@dataclass
class AIAnalysisResult:
    """AI分析结果"""
    analysis_id: str
    problem_id: str
    analysis_type: str  # "pre_fix", "post_fix"
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    quality_score: float = 0.0  # 0.0-1.0
    confidence: float = 0.0  # 0.0-1.0
    analysis_timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "analysis_id": self.analysis_id,
            "problem_id": self.problem_id,
            "analysis_type": self.analysis_type,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "quality_score": self.quality_score,
            "confidence": self.confidence,
            "analysis_timestamp": self.analysis_timestamp.isoformat()
        }


@dataclass
class FixVerificationResult:
    """修复验证结果 - 节点H输出"""
    verification_id: str
    fix_id: str
    problem_id: str
    static_analysis_result: List[StaticAnalysisIssue]
    ai_analysis_result: AIAnalysisResult
    problem_resolved: bool
    new_issues_introduced: List[StaticAnalysisIssue] = field(default_factory=list)
    quality_improvement_score: float = 0.0  # 0.0-1.0
    overall_success: bool = False
    verification_timestamp: datetime = field(default_factory=datetime.now)
    verification_details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "verification_id": self.verification_id,
            "fix_id": self.fix_id,
            "problem_id": self.problem_id,
            "static_analysis_result": [issue.to_dict() for issue in self.static_analysis_result],
            "ai_analysis_result": self.ai_analysis_result.to_dict(),
            "problem_resolved": self.problem_resolved,
            "new_issues_introduced": [issue.to_dict() for issue in self.new_issues_introduced],
            "quality_improvement_score": self.quality_improvement_score,
            "overall_success": self.overall_success,
            "verification_timestamp": self.verification_timestamp.isoformat(),
            "verification_details": self.verification_details
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FixVerificationResult':
        """从字典创建实例"""
        data["verification_timestamp"] = datetime.fromisoformat(data["verification_timestamp"])

        # 重建静态分析问题
        static_issues = []
        for issue_data in data.get("static_analysis_result", []):
            issue_data["severity"] = SeverityLevel(issue_data["severity"])
            static_issues.append(StaticAnalysisIssue(**issue_data))
        data["static_analysis_result"] = static_issues

        # 重建新引入的问题
        new_issues = []
        for issue_data in data.get("new_issues_introduced", []):
            issue_data["severity"] = SeverityLevel(issue_data["severity"])
            new_issues.append(StaticAnalysisIssue(**issue_data))
        data["new_issues_introduced"] = new_issues

        # 重建AI分析结果
        if data.get("ai_analysis_result"):
            data["ai_analysis_result"] = AIAnalysisResult.from_dict(data["ai_analysis_result"])

        return cls(**data)


@dataclass
class WorkflowDataPacket:
    """工作流数据包 - 节点间传递的数据"""
    packet_id: str
    source_node: str
    target_node: str
    data_type: str  # "problem", "suggestion", "verification"
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "packet_id": self.packet_id,
            "source_node": self.source_node,
            "target_node": self.target_node,
            "data_type": self.data_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def create_for_problem(cls, source_node: str, target_node: str,
                          problem: AIDetectedProblem) -> 'WorkflowDataPacket':
        """为问题检测创建数据包"""
        return cls(
            packet_id=f"packet_{uuid.uuid4().hex[:8]}",
            source_node=source_node,
            target_node=target_node,
            data_type="problem",
            payload=problem.to_dict()
        )

    @classmethod
    def create_for_suggestion(cls, source_node: str, target_node: str,
                             suggestion: AIFixSuggestion) -> 'WorkflowDataPacket':
        """为修复建议创建数据包"""
        return cls(
            packet_id=f"packet_{uuid.uuid4().hex[:8]}",
            source_node=source_node,
            target_node=target_node,
            data_type="suggestion",
            payload=suggestion.to_dict()
        )

    @classmethod
    def create_for_verification(cls, source_node: str, target_node: str,
                               verification: FixVerificationResult) -> 'WorkflowDataPacket':
        """为修复验证创建数据包"""
        return cls(
            packet_id=f"packet_{uuid.uuid4().hex[:8]}",
            source_node=source_node,
            target_node=target_node,
            data_type="verification",
            payload=verification.to_dict()
        )


class WorkflowDataValidator:
    """工作流数据验证器"""

    def __init__(self):
        self.logger = get_logger()

    def validate_problem_data(self, data: Dict[str, Any]) -> bool:
        """验证问题数据格式"""
        required_fields = [
            "problem_id", "file_path", "line_number", "problem_type",
            "severity", "description", "code_snippet", "confidence", "reasoning"
        ]

        for field in required_fields:
            if field not in data:
                self.logger.error(f"问题数据缺少必需字段: {field}")
                return False

        # 验证字段类型和格式
        if not isinstance(data["confidence"], (int, float)) or not (0.0 <= data["confidence"] <= 1.0):
            self.logger.error("问题数据置信度格式错误")
            return False

        if data["line_number"] <= 0:
            self.logger.error("问题数据行号格式错误")
            return False

        return True

    def validate_suggestion_data(self, data: Dict[str, Any]) -> bool:
        """验证修复建议数据格式"""
        required_fields = [
            "suggestion_id", "problem_id", "file_path", "line_number",
            "original_code", "suggested_code", "explanation", "reasoning", "confidence"
        ]

        for field in required_fields:
            if field not in data:
                self.logger.error(f"修复建议数据缺少必需字段: {field}")
                return False

        # 验证字段类型和格式
        if not isinstance(data["confidence"], (int, float)) or not (0.0 <= data["confidence"] <= 1.0):
            self.logger.error("修复建议数据置信度格式错误")
            return False

        if data["line_number"] <= 0:
            self.logger.error("修复建议数据行号格式错误")
            return False

        return True

    def validate_verification_data(self, data: Dict[str, Any]) -> bool:
        """验证修复验证数据格式"""
        required_fields = [
            "verification_id", "fix_id", "problem_id",
            "problem_resolved", "overall_success"
        ]

        for field in required_fields:
            if field not in data:
                self.logger.error(f"修复验证数据缺少必需字段: {field}")
                return False

        # 验证布尔字段
        if not isinstance(data["problem_resolved"], bool) or not isinstance(data["overall_success"], bool):
            self.logger.error("修复验证数据布尔字段格式错误")
            return False

        return True

    def validate_data_packet(self, packet: WorkflowDataPacket) -> bool:
        """验证工作流数据包"""
        # 基本字段验证
        if not all([packet.packet_id, packet.source_node, packet.target_node, packet.data_type]):
            self.logger.error("数据包基本字段不完整")
            return False

        # 根据数据类型验证载荷
        if packet.data_type == "problem":
            return self.validate_problem_data(packet.payload)
        elif packet.data_type == "suggestion":
            return self.validate_suggestion_data(packet.payload)
        elif packet.data_type == "verification":
            return self.validate_verification_data(packet.payload)
        else:
            self.logger.error(f"未知的数据包类型: {packet.data_type}")
            return False


class WorkflowDataTransformer:
    """工作流数据转换器"""

    def __init__(self):
        self.validator = WorkflowDataValidator()

    def transform_problem_for_ai_input(self, problem: AIDetectedProblem,
                                     context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """将问题数据转换为AI输入格式"""
        data = problem.to_dict()

        if context_data:
            data["context"] = context_data

        # 为AI优化格式
        ai_input = {
            "problem_id": problem.problem_id,
            "location": f"{problem.file_path}:{problem.line_number}",
            "type": problem.problem_type.value,
            "severity": problem.severity.value,
            "description": problem.description,
            "code": problem.code_snippet,
            "context": data.get("context"),
            "suggested_fix_type": problem.suggested_fix_type.value,
            "tags": problem.tags
        }

        return ai_input

    def transform_suggestion_for_display(self, suggestion: AIFixSuggestion) -> Dict[str, Any]:
        """将修复建议转换为显示格式"""
        return {
            "suggestion_id": suggestion.suggestion_id,
            "location": f"{suggestion.file_path}:{suggestion.line_number}",
            "original_code": suggestion.original_code,
            "suggested_code": suggestion.suggested_code,
            "explanation": suggestion.explanation,
            "confidence": suggestion.confidence,
            "risk_level": suggestion.risk_level.value,
            "side_effects": suggestion.side_effects,
            "alternatives_count": len(suggestion.alternatives),
            "estimated_impact": suggestion.estimated_impact
        }

    def transform_verification_for_report(self, verification: FixVerificationResult) -> Dict[str, Any]:
        """将验证结果转换为报告格式"""
        return {
            "verification_id": verification.verification_id,
            "problem_id": verification.problem_id,
            "success": verification.overall_success,
            "problem_resolved": verification.problem_resolved,
            "quality_improvement": verification.quality_improvement_score,
            "new_issues_count": len(verification.new_issues_introduced),
            "static_issues_before": len(verification.static_analysis_result),
            "ai_quality_score": verification.ai_analysis_result.quality_score,
            "verification_timestamp": verification.verification_timestamp.isoformat()
        }