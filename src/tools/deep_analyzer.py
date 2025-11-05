"""
深度分析工具模块
实现基于LLM的深度代码分析功能
"""

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..llm.base import Message, MessageRole
from ..llm.client import LLMClient
from ..prompts.manager import PromptManager
from ..utils.config import get_config_manager
from ..utils.logger import get_logger


@dataclass
class DeepAnalysisRequest:
    """深度分析请求"""

    file_path: str
    analysis_type: str = (
        "comprehensive"  # comprehensive, security, performance, architecture
    )
    model: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 4000
    context: Optional[Dict[str, Any]] = None
    user_instructions: Optional[str] = None


@dataclass
class DeepAnalysisResult:
    """深度分析结果"""

    file_path: str
    analysis_type: str
    success: bool
    content: str = ""
    structured_analysis: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    model_used: str = ""
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "file_path": self.file_path,
            "analysis_type": self.analysis_type,
            "success": self.success,
            "content": self.content,
            "structured_analysis": self.structured_analysis,
            "execution_time": self.execution_time,
            "model_used": self.model_used,
            "token_usage": self.token_usage,
            "error": self.error,
            "metadata": self.metadata,
        }


class DeepAnalyzer:
    """深度分析器"""

    def __init__(self, config_manager=None, llm_client: Optional[LLMClient] = None):
        """
        初始化深度分析器

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
            self.config = self.config_manager.get_section("deep_analysis")
        except:
            self.config = {}

        self.default_model = self.config.get("default_model", "gpt-4")
        self.default_temperature = self.config.get("temperature", 0.3)
        self.max_tokens = self.config.get("max_tokens", 4000)
        self.max_file_size = self.config.get("max_file_size", 100 * 1024)  # 100KB

        self.logger.info(f"DeepAnalyzer initialized with model: {self.default_model}")

    async def analyze_file(self, request: DeepAnalysisRequest) -> DeepAnalysisResult:
        """
        分析单个文件

        Args:
            request: 深度分析请求

        Returns:
            深度分析结果
        """
        start_time = time.time()
        file_path = Path(request.file_path)

        self.logger.info(
            f"Starting deep analysis for {file_path} (type: {request.analysis_type})"
        )

        result = DeepAnalysisResult(
            file_path=str(file_path), analysis_type=request.analysis_type, success=False
        )

        try:
            # 1. 读取文件内容
            file_content = self._read_file_content(file_path)
            if file_content is None:
                result.error = f"Failed to read file: {file_path}"
                result.execution_time = time.time() - start_time
                return result

            # 2. 构造prompt
            messages = self._construct_prompt(file_content, request)
            if not messages:
                result.error = f"Failed to construct prompt for analysis type: {request.analysis_type}"
                result.execution_time = time.time() - start_time
                return result

            # 3. 调用LLM
            llm_request = self.llm_client.create_request(
                messages=messages,
                model=request.model or self.default_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )

            llm_response = await self.llm_client.complete(llm_request)

            # 4. 解析响应
            parsed_result = self._parse_llm_response(llm_response.content)

            # 5. 构建结果
            result.success = True
            result.content = llm_response.content
            result.structured_analysis = parsed_result
            result.model_used = (
                llm_response.model or request.model or self.default_model
            )
            result.token_usage = llm_response.usage or {}
            result.metadata = {
                "request_analysis_type": request.analysis_type,
                "file_size": len(file_content),
                "prompt_tokens": len(str(messages)),
                "has_user_instructions": bool(request.user_instructions),
            }

            self.logger.info(
                f"Deep analysis completed for {file_path} in {result.execution_time:.2f}s"
            )

        except Exception as e:
            result.error = str(e)
            self.logger.error(f"Deep analysis failed for {file_path}: {e}")

        result.execution_time = time.time() - start_time
        return result

    def analyze_files(
        self, requests: List[DeepAnalysisRequest]
    ) -> List[DeepAnalysisResult]:
        """
        分析多个文件

        Args:
            requests: 深度分析请求列表

        Returns:
            深度分析结果列表
        """
        self.logger.info(f"Starting deep analysis for {len(requests)} files")

        # 异步执行所有分析
        results = asyncio.run(self._analyze_files_async(requests))

        successful_count = len([r for r in results if r.success])
        self.logger.info(
            f"Deep analysis completed: {successful_count}/{len(results)} files successful"
        )

        return results

    async def _analyze_files_async(
        self, requests: List[DeepAnalysisRequest]
    ) -> List[DeepAnalysisResult]:
        """异步分析多个文件"""
        # 创建异步任务
        tasks = [self.analyze_file(request) for request in requests]

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # 创建失败结果
                error_result = DeepAnalysisResult(
                    file_path=requests[i].file_path,
                    analysis_type=requests[i].analysis_type,
                    success=False,
                    error=str(result),
                    execution_time=0.0,
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """
        读取文件内容

        Args:
            file_path: 文件路径

        Returns:
            文件内容或None
        """
        try:
            # 检查文件是否存在
            if not file_path.exists():
                self.logger.error(f"File does not exist: {file_path}")
                return None

            # 检查是否为目录
            if file_path.is_dir():
                self.logger.error(f"Path is a directory, not a file: {file_path}")
                return None

            # 检查文件大小
            if file_path.stat().st_size > self.max_file_size:
                self.logger.warning(
                    f"File too large ({file_path.stat().st_size} bytes), truncating to {self.max_file_size} bytes"
                )

            # 读取文件内容
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 如果文件太大，截断内容
            if len(content) > self.max_file_size:
                content = (
                    content[: self.max_file_size]
                    + "\n\n... (content truncated due to size limit)"
                )
                self.logger.warning(f"Truncated content for {file_path}")

            return content

        except UnicodeDecodeError as e:
            self.logger.error(f"File encoding error for {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return None

    def _construct_prompt(
        self, file_content: str, request: DeepAnalysisRequest
    ) -> List[Message]:
        """
        构造分析prompt

        Args:
            file_content: 文件内容
            request: 深度分析请求

        Returns:
            Message对象列表
        """
        try:
            # 获取系统提示
            system_template = self.prompt_manager.get_template("deep_analysis_system")
            if system_template:
                render_result = self.prompt_manager.render_template(
                    "deep_analysis_system", {"analysis_type": request.analysis_type}
                )
                if render_result.success:
                    system_message = render_result.content
                else:
                    system_message = "You are an expert code analysis assistant. Provide comprehensive analysis of the given code."
            else:
                system_message = "You are an expert code analysis assistant. Provide comprehensive analysis of the given code."

            # 获取分析提示
            analysis_template_name = self._get_analysis_template_name(
                request.analysis_type
            )
            analysis_template = self.prompt_manager.get_template(analysis_template_name)

            if analysis_template:
                render_result = self.prompt_manager.render_template(
                    analysis_template_name,
                    {
                        "file_content": file_content,
                        "analysis_type": request.analysis_type,
                        "user_instructions": request.user_instructions or "",
                        "context": request.context or {},
                    },
                )

                if render_result.success:
                    user_message = render_result.content
                else:
                    user_message = self._get_fallback_prompt(file_content, request)
            else:
                user_message = self._get_fallback_prompt(file_content, request)

            messages = [
                Message(role=MessageRole.SYSTEM, content=system_message),
                Message(role=MessageRole.USER, content=user_message),
            ]

            return messages

        except Exception as e:
            self.logger.error(f"Failed to construct prompt: {e}")
            return []

    def _get_analysis_template_name(self, analysis_type: str) -> str:
        """根据分析类型获取模板名称"""
        template_mapping = {
            "comprehensive": "deep_code_analysis",
            "security": "deep_vulnerability_assessment",
            "performance": "deep_performance_analysis",
            "architecture": "deep_architecture_analysis",
            "code_review": "deep_code_review",
            "refactoring": "deep_refactoring_suggestions",
        }
        return template_mapping.get(analysis_type, "deep_code_analysis")

    def _get_fallback_prompt(
        self, file_content: str, request: DeepAnalysisRequest
    ) -> str:
        """获取fallback prompt"""
        prompt = f"""Please analyze the following Python code for {request.analysis_type} issues:

```python
{file_content}
```

Please provide:
1. Overall assessment
2. Key findings and recommendations
3. Specific issues with line numbers
4. Suggestions for improvement

{f'Additional instructions: {request.user_instructions}' if request.user_instructions else ''}"""
        return prompt

    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """
        解析LLM响应

        Args:
            content: LLM响应内容

        Returns:
            解析后的结构化数据
        """
        try:
            # 尝试解析JSON格式响应
            if content.strip().startswith("{") or content.strip().startswith("["):
                return json.loads(content)

            # 尝试提取JSON部分
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_content = content[json_start:json_end]
                return json.loads(json_content)

            # 如果不是JSON格式，返回文本分析
            return {
                "format": "text",
                "summary": content[:500] + "..." if len(content) > 500 else content,
                "analysis_text": content,
                "structured": False,
            }

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON response: {e}")
            # 返回文本格式
            return {
                "format": "text",
                "summary": content[:500] + "..." if len(content) > 500 else content,
                "analysis_text": content,
                "structured": False,
                "parse_error": str(e),
            }
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return {"format": "error", "error": str(e), "raw_content": content}

    def get_supported_analysis_types(self) -> List[str]:
        """获取支持的分析类型"""
        return [
            "comprehensive",
            "security",
            "performance",
            "architecture",
            "code_review",
            "refactoring",
        ]

    def get_analysis_summary(self, results: List[DeepAnalysisResult]) -> Dict[str, Any]:
        """
        获取分析摘要

        Args:
            results: 分析结果列表

        Returns:
            分析摘要
        """
        total_files = len(results)
        successful_files = len([r for r in results if r.success])
        failed_files = total_files - successful_files

        summary = {
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files,
            "success_rate": successful_files / total_files if total_files > 0 else 0,
            "total_execution_time": sum(r.execution_time for r in results),
            "analysis_types": {},
            "models_used": {},
            "average_tokens": 0,
        }

        # 统计分析类型分布
        for result in results:
            analysis_type = result.analysis_type
            summary["analysis_types"][analysis_type] = (
                summary["analysis_types"].get(analysis_type, 0) + 1
            )

        # 统计模型使用
        for result in results:
            model = result.model_used
            summary["models_used"][model] = summary["models_used"].get(model, 0) + 1

        # 计算平均token使用
        total_tokens = sum(
            r.token_usage.get("total_tokens", 0) for r in results if r.token_usage
        )
        if successful_files > 0:
            summary["average_tokens"] = total_tokens / successful_files

        return summary

    def format_analysis_result(
        self, result: DeepAnalysisResult, format_type: str = "text"
    ) -> str:
        """
        格式化分析结果

        Args:
            result: 分析结果
            format_type: 格式类型 (text, json, markdown)

        Returns:
            格式化后的字符串
        """
        if format_type == "json":
            return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)

        elif format_type == "markdown":
            return self._format_as_markdown(result)

        else:  # text format
            return self._format_as_text(result)

    def _format_as_markdown(self, result: DeepAnalysisResult) -> str:
        """格式化为Markdown"""
        lines = []

        # 标题
        lines.append(f"# 深度分析报告")
        lines.append(f"**文件**: `{result.file_path}`")
        lines.append(f"**分析类型**: {result.analysis_type}")
        lines.append(f"**模型**: {result.model_used}")
        lines.append(f"**执行时间**: {result.execution_time:.2f}秒")
        lines.append("")

        # 状态
        status = "✅ 成功" if result.success else "❌ 失败"
        lines.append(f"**状态**: {status}")
        lines.append("")

        if result.error:
            lines.append(f"**错误**: {result.error}")
            lines.append("")

        if result.content:
            lines.append("## 分析内容")
            lines.append("```")
            lines.append(result.content)
            lines.append("```")
            lines.append("")

        if result.structured_analysis and result.structured_analysis.get("structured"):
            lines.append("## 结构化分析结果")
            lines.append("```json")
            lines.append(
                json.dumps(result.structured_analysis, indent=2, ensure_ascii=False)
            )
            lines.append("```")

        return "\n".join(lines)

    def _format_as_text(self, result: DeepAnalysisResult) -> str:
        """格式化为纯文本"""
        lines = []

        lines.append("=" * 60)
        lines.append("深度分析报告")
        lines.append("=" * 60)
        lines.append(f"文件: {result.file_path}")
        lines.append(f"分析类型: {result.analysis_type}")
        lines.append(f"模型: {result.model_used}")
        lines.append(f"执行时间: {result.execution_time:.2f}秒")
        lines.append("")

        # 状态
        status = "成功" if result.success else "失败"
        lines.append(f"状态: {status}")

        if result.error:
            lines.append(f"错误: {result.error}")

        lines.append("")

        if result.content:
            lines.append("分析内容:")
            lines.append("-" * 40)
            lines.append(result.content)
            lines.append("")

        return "\n".join(lines)
