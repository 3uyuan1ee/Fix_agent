"""
修复代码生成器
负责基于LLM生成代码修复方案
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..llm.client import LLMClient
from ..prompts.manager import PromptManager
from ..utils.config import get_config_manager
from ..utils.logger import get_logger


@dataclass
class FixRequest:
    """修复请求"""

    file_path: str
    issues: List[Dict[str, Any]]  # 问题列表
    original_content: str
    analysis_type: str = "security"  # security, performance, style, etc.
    model: Optional[str] = None
    temperature: float = 0.2  # 较低温度确保修复代码的准确性
    max_tokens: int = 6000
    user_instructions: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class FixSuggestion:
    """修复建议"""

    issue_id: str
    issue_type: str
    description: str
    location: Dict[str, Any]  # {line: int, column: int}
    severity: str
    fixed_code: str
    explanation: str
    confidence: float  # 0.0-1.0
    tags: List[str] = field(default_factory=list)


@dataclass
class FixResult:
    """修复结果"""

    file_path: str
    success: bool
    suggestions: List[FixSuggestion] = field(default_factory=list)
    complete_fixed_content: str = ""
    execution_time: float = 0.0
    model_used: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "success": self.success,
            "suggestions": [self._suggestion_to_dict(s) for s in self.suggestions],
            "complete_fixed_content": self.complete_fixed_content,
            "execution_time": self.execution_time,
            "model_used": self.model_used,
            "token_usage": self.token_usage,
            "error": self.error,
            "metadata": self.metadata,
        }

    def _suggestion_to_dict(self, suggestion: FixSuggestion) -> Dict[str, Any]:
        """将修复建议转换为字典"""
        return {
            "issue_id": suggestion.issue_id,
            "issue_type": suggestion.issue_type,
            "description": suggestion.description,
            "location": suggestion.location,
            "severity": suggestion.severity,
            "fixed_code": suggestion.fixed_code,
            "explanation": suggestion.explanation,
            "confidence": suggestion.confidence,
            "tags": suggestion.tags,
        }


class FixGenerator:
    """修复代码生成器"""

    def __init__(self, config_manager=None, llm_client: Optional[LLMClient] = None):
        """
        初始化修复生成器

        Args:
            config_manager: 配置管理器实例
            llm_client: LLM客户端实例
        """
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger()

        # 初始化LLM客户端
        self.llm_client = llm_client or LLMClient()

        # 初始化Prompt管理器
        self.prompt_manager = PromptManager()

        # 获取配置
        try:
            self.config = self.config_manager.get_section("fix_generation")
        except:
            self.config = {}

        self.default_model = self.config.get("default_model", "gpt-4")
        self.default_temperature = self.config.get("temperature", 0.2)
        self.max_tokens = self.config.get("max_tokens", 6000)
        self.max_file_size = self.config.get("max_file_size", 50 * 1024)  # 50KB

        self.logger.info(f"FixGenerator initialized with model: {self.default_model}")

    async def generate_fixes(self, request: FixRequest) -> FixResult:
        """
        生成修复建议

        Args:
            request: 修复请求

        Returns:
            修复结果
        """
        import time

        start_time = time.time()

        self.logger.info(f"Starting fix generation for {request.file_path}")

        result = FixResult(file_path=request.file_path, success=False)

        try:
            # 1. 验证输入
            if not self._validate_request(request):
                result.error = "Invalid fix request"
                result.execution_time = time.time() - start_time
                return result

            # 2. 构造修复prompt
            fix_prompt = self._construct_fix_prompt(request)
            if not fix_prompt:
                result.error = f"Failed to construct fix prompt for analysis type: {request.analysis_type}"
                result.execution_time = time.time() - start_time
                return result

            # 3. 调用LLM生成修复
            llm_request = self.llm_client.create_request(
                messages=fix_prompt,
                model=request.model or self.default_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            llm_response = await self.llm_client.complete(llm_request)

            # 4. 解析LLM响应获取修复建议和完整文件内容
            suggestions, complete_fixed_content = self._parse_llm_response(
                llm_response.content, request
            )

            # 5. 如果没有完整文件内容，则生成
            if not complete_fixed_content:
                complete_fixed_content = self._generate_complete_fixed_content(
                    request.original_content, suggestions
                )

            # 6. 构建结果
            result.success = True
            result.suggestions = suggestions
            result.complete_fixed_content = complete_fixed_content
            result.model_used = (
                llm_response.model or request.model or self.default_model
            )
            result.token_usage = llm_response.usage or {}
            result.metadata = {
                "request_analysis_type": request.analysis_type,
                "issues_count": len(request.issues),
                "suggestions_count": len(suggestions),
                "has_user_instructions": bool(request.user_instructions),
            }

            self.logger.info(
                f"Fix generation completed for {request.file_path} in {result.execution_time:.2f}s"
            )

        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Fix generation failed for {request.file_path}: {e}")

        result.execution_time = time.time() - start_time
        return result

    def _validate_request(self, request: FixRequest) -> bool:
        """验证修复请求"""
        try:
            # 检查文件路径
            if not request.file_path or not Path(request.file_path).exists():
                self.logger.error(f"File does not exist: {request.file_path}")
                return False

            # 检查原始内容
            if not request.original_content or not request.original_content.strip():
                self.logger.error("Original content is empty")
                return False

            # 检查问题列表
            if not request.issues:
                self.logger.warning("No issues provided for fix generation")
                return True  # 允许空问题列表，可能只是整体优化

            # 检查文件大小
            if len(request.original_content) > self.max_file_size:
                self.logger.warning(
                    f"File too large ({len(request.original_content)} bytes), truncating"
                )
                return True  # 继续处理，但会截断

            return True

        except Exception as e:
            self.logger.error(f"Request validation failed: {e}")
            return False

    def _construct_fix_prompt(self, request: FixRequest) -> List[Dict[str, str]]:
        """构造修复prompt"""
        try:
            # 获取系统提示
            system_template = self.prompt_manager.get_template("fix_system")
            if system_template:
                render_result = self.prompt_manager.render_template(
                    "fix_system", {"analysis_type": request.analysis_type}
                )
                if render_result.success:
                    system_message = render_result.content
                else:
                    system_message = self._get_default_fix_system_message(
                        request.analysis_type
                    )
            else:
                system_message = self._get_default_fix_system_message(
                    request.analysis_type
                )

            # 构造用户消息
            user_message = self._construct_fix_user_message(request)

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ]

            return messages

        except Exception as e:
            self.logger.error(f"Failed to construct fix prompt: {e}")
            return []

    def _get_default_fix_system_message(self, analysis_type: str) -> str:
        """获取默认的修复系统消息"""
        base_message = """You are an expert code repair assistant. Your task is to analyze code issues and provide precise fixes.

Guidelines:
1. Preserve the original code structure and logic as much as possible
2. Only modify the specific lines that need to be fixed
3. Ensure the fixed code is syntactically correct and follows best practices
4. Provide clear explanations for each fix
5. Consider security implications and performance impact
6. Maintain code readability and maintainability"""

        type_specific = {
            "security": "\n7. Prioritize security fixes and vulnerability remediation",
            "performance": "\n7. Focus on performance optimizations and efficiency improvements",
            "style": "\n7. Ensure code follows PEP8 and style guidelines",
            "logic": "\n7. Fix logical errors and bugs in the code flow",
        }

        return base_message + type_specific.get(analysis_type, "")

    def _construct_fix_user_message(self, request: FixRequest) -> str:
        """构造修复用户消息"""
        # 截断过大的文件
        content = request.original_content
        if len(content) > self.max_file_size:
            content = (
                content[: self.max_file_size]
                + "\n\n... (content truncated due to size limit)"
            )

        # 构造问题描述
        issues_description = self._format_issues_for_prompt(request.issues)

        # 构造用户消息
        user_message = f"""Please analyze the following Python code and provide fixes for the identified issues:

## Code to Fix:
```python
{content}
```

## Issues to Fix:
{issues_description}

## Instructions:
Please provide your response in the following JSON format:

```json
{{
    "fixes": [
        {{
            "issue_id": "unique_id",
            "issue_type": "issue_category",
            "description": "Brief description of the issue",
            "location": {{"line": line_number, "column": column_number}},
            "severity": "critical|high|medium|low",
            "fixed_code": "the fixed code snippet",
            "explanation": "detailed explanation of the fix",
            "confidence": 0.95,
            "tags": ["tag1", "tag2"]
        }}
    ],
    "complete_fixed_file": "the complete fixed file content",
    "summary": "overall summary of changes made",
    "risk_assessment": "assessment of potential risks from these changes"
}}
```

{f'Additional user instructions: {request.user_instructions}' if request.user_instructions else ''}"""

        return user_message

    def _format_issues_for_prompt(self, issues: List[Dict[str, Any]]) -> str:
        """格式化问题描述用于prompt"""
        if not issues:
            return "No specific issues provided. Please analyze the code for general improvements."

        formatted_issues = []
        for i, issue in enumerate(issues, 1):
            issue_text = f"{i}. **{issue.get('type', 'Unknown Issue')}**"

            if "line" in issue:
                issue_text += f" (Line {issue['line']}"
                if "column" in issue:
                    issue_text += f", Column {issue['column']}"
                issue_text += ")"

            if "message" in issue:
                issue_text += f": {issue['message']}"

            if "severity" in issue:
                issue_text += f" [Severity: {issue['severity']}]"

            formatted_issues.append(issue_text)

        return "\n".join(formatted_issues)

    def _parse_llm_response(
        self, llm_response: str, request: FixRequest
    ) -> Tuple[List[FixSuggestion], str]:
        """解析LLM响应，返回修复建议和完整文件内容"""
        suggestions = []
        complete_fixed_content = ""

        try:
            # 尝试解析JSON格式响应
            if llm_response.strip().startswith("{"):
                data = json.loads(llm_response)
                suggestions = self._parse_json_fixes(data, request)
                complete_fixed_content = data.get("complete_fixed_file", "")
                return suggestions, complete_fixed_content

            # 尝试提取JSON部分
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_content = llm_response[json_start:json_end]
                data = json.loads(json_content)
                suggestions = self._parse_json_fixes(data, request)
                complete_fixed_content = data.get("complete_fixed_file", "")
                return suggestions, complete_fixed_content

            # 如果不是JSON格式，尝试解析文本格式
            suggestions = self._parse_text_fixes(llm_response, request)
            return suggestions, complete_fixed_content

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON fix response: {e}")
            suggestions = self._parse_text_fixes(llm_response, request)
            return suggestions, complete_fixed_content
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return [], ""

    def _parse_fix_suggestions(
        self, llm_response: str, request: FixRequest
    ) -> List[FixSuggestion]:
        """解析LLM响应中的修复建议"""
        try:
            # 尝试解析JSON格式响应
            if llm_response.strip().startswith("{"):
                data = json.loads(llm_response)
                return self._parse_json_fixes(data, request)

            # 尝试提取JSON部分
            json_start = llm_response.find("{")
            json_end = llm_response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_content = llm_response[json_start:json_end]
                data = json.loads(json_content)
                return self._parse_json_fixes(data, request)

            # 如果不是JSON格式，尝试解析文本格式
            return self._parse_text_fixes(llm_response, request)

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON fix response: {e}")
            return self._parse_text_fixes(llm_response, request)
        except Exception as e:
            self.logger.error(f"Error parsing fix suggestions: {e}")
            return []

    def _parse_json_fixes(
        self, data: Dict[str, Any], request: FixRequest
    ) -> List[FixSuggestion]:
        """解析JSON格式的修复建议"""
        suggestions = []

        try:
            fixes = data.get("fixes", [])
            for fix_data in fixes:
                suggestion = FixSuggestion(
                    issue_id=fix_data.get("issue_id", f"fix_{len(suggestions)}"),
                    issue_type=fix_data.get("issue_type", "unknown"),
                    description=fix_data.get("description", ""),
                    location=fix_data.get("location", {}),
                    severity=fix_data.get("severity", "medium"),
                    fixed_code=fix_data.get("fixed_code", ""),
                    explanation=fix_data.get("explanation", ""),
                    confidence=float(fix_data.get("confidence", 0.8)),
                    tags=fix_data.get("tags", []),
                )
                suggestions.append(suggestion)

        except Exception as e:
            self.logger.error(f"Error parsing JSON fixes: {e}")

        return suggestions

    def _parse_text_fixes(
        self, text_response: str, request: FixRequest
    ) -> List[FixSuggestion]:
        """解析文本格式的修复建议"""
        suggestions = []

        try:
            # 尝试从文本中提取代码块和说明
            code_blocks = re.findall(
                r"```(?:python)?\n(.*?)\n```", text_response, re.DOTALL
            )

            for i, code_block in enumerate(code_blocks):
                # 为每个代码块创建一个修复建议
                suggestion = FixSuggestion(
                    issue_id=f"text_fix_{i}",
                    issue_type=request.analysis_type,
                    description=f"Fix suggestion {i+1} from text response",
                    location={},
                    severity="medium",
                    fixed_code=code_block.strip(),
                    explanation="Generated from text-based fix suggestion",
                    confidence=0.7,
                    tags=["text_parsed"],
                )
                suggestions.append(suggestion)

        except Exception as e:
            self.logger.error(f"Error parsing text fixes: {e}")

        return suggestions

    def _generate_complete_fixed_content(
        self, original_content: str, suggestions: List[FixSuggestion]
    ) -> str:
        """生成完整的修复后内容"""
        if not suggestions:
            return original_content

        try:
            # 按行号排序建议，从后往前应用修复（避免行号偏移）
            sorted_suggestions = sorted(
                [s for s in suggestions if s.location.get("line") and s.fixed_code],
                key=lambda x: x.location["line"],
                reverse=True,
            )

            # 将原始内容分割为行
            lines = original_content.split("\n")

            # 应用修复
            for suggestion in sorted_suggestions:
                line_num = suggestion.location["line"] - 1  # 转换为0-based索引

                if 0 <= line_num < len(lines):
                    # 替换指定行
                    if "\n" in suggestion.fixed_code:
                        # 多行修复
                        fixed_lines = suggestion.fixed_code.split("\n")
                        lines[line_num : line_num + 1] = fixed_lines
                    else:
                        # 单行修复
                        lines[line_num] = suggestion.fixed_code

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"Error generating complete fixed content: {e}")
            return original_content

    def get_supported_fix_types(self) -> List[str]:
        """获取支持的修复类型"""
        return [
            "security",
            "performance",
            "style",
            "logic",
            "best_practices",
            "documentation",
            "error_handling",
        ]

    def validate_fix_safety(self, suggestion: FixSuggestion) -> Tuple[bool, str]:
        """验证修复建议的安全性"""
        try:
            # 检查是否包含危险操作
            dangerous_patterns = [
                r"eval\s*\(",
                r"exec\s*\(",
                r"__import__\s*\(",
                r'open\s*\([^)]*[\'"]\s*[+/]',  # 路径遍历
                r"subprocess\.\w*\([^)]*shell\s*=\s*True",  # shell注入
            ]

            for pattern in dangerous_patterns:
                if re.search(pattern, suggestion.fixed_code, re.IGNORECASE):
                    return (
                        False,
                        f"Fix contains potentially dangerous pattern: {pattern}",
                    )

            # 检查语法
            try:
                compile(suggestion.fixed_code, "<string>", "exec")
            except SyntaxError as e:
                return False, f"Fix contains syntax error: {e}"

            # 检查置信度
            if suggestion.confidence < 0.5:
                return False, f"Fix confidence too low: {suggestion.confidence}"

            return True, "Fix appears safe"

        except Exception as e:
            return False, f"Error validating fix safety: {e}"
