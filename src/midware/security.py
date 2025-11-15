"""安全检查中间件 - 提供全面的安全防护和合规性检查"""

import hashlib
import os
import re
import subprocess
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

if TYPE_CHECKING:
    from langgraph.runtime import Runtime

from deepagents.backends.protocol import BackendProtocol
from langchain.agents.middleware.types import (AgentMiddleware, AgentState,
                                               ModelRequest, ModelResponse)
from typing_extensions import NotRequired, TypedDict


@dataclass
class SecurityViolation:
    """安全违规记录"""

    violation_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    suggested_action: str
    timestamp: float
    context: str = ""


class SecurityState(AgentState):
    """安全检查中间件的状态"""

    security_violations: NotRequired[List[SecurityViolation]]
    """安全违规记录"""

    security_settings: NotRequired[Dict[str, Any]]
    """安全设置"""

    blocked_operations: NotRequired[List[str]]
    """被阻止的操作"""

    allowed_paths: NotRequired[List[str]]
    """允许的路径"""

    security_level: NotRequired[str]
    """安全级别: "low", "medium", "high", "strict"""


class SecurityMiddleware(AgentMiddleware):
    """安全检查中间件

    提供多层次的安全防护：
    - 文件操作安全检查
    - 命令注入防护
    - 敏感信息保护
    - 路径遍历防护
    - 恶意代码检测
    - 资源访问控制
    """

    state_schema = SecurityState

    def __init__(
        self,
        *,
        backend: BackendProtocol,
        security_level: str = "medium",
        workspace_root: str = None,
        enable_file_security: bool = True,
        enable_command_security: bool = True,
        enable_content_security: bool = True,
        allow_path_traversal: bool = False,
        blocked_extensions: List[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        audit_log_path: str = "/security/audit.log",
    ) -> None:
        """初始化安全检查中间件"""
        self.backend = backend
        self.security_level = security_level
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.enable_file_security = enable_file_security
        self.enable_command_security = enable_command_security
        self.enable_content_security = enable_content_security
        self.allow_path_traversal = allow_path_traversal
        self.max_file_size = max_file_size
        self.audit_log_path = audit_log_path

        # 危险文件扩展名
        self.blocked_extensions = blocked_extensions or [
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".pif",
            ".scr",
            ".vbs",
            ".js",
            ".jar",
            ".app",
            ".deb",
            ".rpm",
            ".dmg",
            ".pkg",
            ".msi",
            ".sh",
            ".ps1",
        ]

        # 敏感信息模式
        self.sensitive_patterns = {
            "api_key": re.compile(
                r'(api[_-]?key|apikey)\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?',
                re.IGNORECASE,
            ),
            "password": re.compile(
                r'(password|pwd)\s*[:=]\s*["\']?[^\s"\']{6,}["\']?', re.IGNORECASE
            ),
            "secret": re.compile(
                r'(secret|token)\s*[:=]\s*["\']?[a-zA-Z0-9]{20,}["\']?', re.IGNORECASE
            ),
            "private_key": re.compile(
                r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", re.IGNORECASE
            ),
            "aws_access_key": re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
            "credit_card": re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),
            "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
        }

        # 危险命令模式
        self.dangerous_commands = {
            "rm": re.compile(r"\brm\s+-rf?\s+/"),
            "dd": re.compile(r"\bdd\s+if=/dev/"),
            "format": re.compile(r"\b(format|mkfs)\s+/dev/"),
            "sudo": re.compile(r"\bsudo\s+"),
            "su": re.compile(r"\bsu\s+"),
            "chmod": re.compile(r"\bchmod\s+777"),
            "chown": re.compile(r"\bchown\s+root:root"),
            "iptables": re.compile(r"\biptables\s+-F"),
            "systemctl": re.compile(r"\bsystemctl\s+(stop|disable|poweroff|reboot)"),
            "shutdown": re.compile(r"\bshutdown\s+"),
            "reboot": re.compile(r"\breboot\s+"),
        }

        # 初始化安全设置
        self._init_security_settings()

    def _init_security_settings(self) -> None:
        """初始化安全设置"""
        security_configs = {
            "low": {
                "enable_file_check": False,
                "enable_command_check": False,
                "enable_content_check": False,
                "max_file_size": 100 * 1024 * 1024,  # 100MB
            },
            "medium": {
                "enable_file_check": True,
                "enable_command_check": True,
                "enable_content_check": True,
                "max_file_size": 10 * 1024 * 1024,  # 10MB
            },
            "high": {
                "enable_file_check": True,
                "enable_command_check": True,
                "enable_content_check": True,
                "max_file_size": 1 * 1024 * 1024,  # 1MB
            },
            "strict": {
                "enable_file_check": True,
                "enable_command_check": True,
                "enable_content_check": True,
                "max_file_size": 100 * 1024,  # 100KB
                "require_explicit_approval": True,
            },
        }

        config = security_configs.get(self.security_level, security_configs["medium"])
        for key, value in config.items():
            setattr(self, key, value)

    def _log_security_event(self, violation: SecurityViolation) -> None:
        """记录安全事件"""
        try:
            log_entry = {
                "timestamp": violation.timestamp,
                "type": violation.violation_type,
                "severity": violation.severity,
                "description": violation.description,
                "suggested_action": violation.suggested_action,
                "context": violation.context,
            }

            log_content = f"[SECURITY] {violation.timestamp}: {violation.severity.upper()} - {violation.description}\n"

            # 记录到后端存储
            self.backend.write(self.audit_log_path, log_content, mode="a")
        except Exception as e:
            print(f"Warning: Failed to log security event: {e}")

    def _check_file_security(
        self, file_path: str, operation: str = "read"
    ) -> Optional[SecurityViolation]:
        """检查文件操作安全性"""
        if not self.enable_file_security:
            return None

        try:
            path = Path(file_path).resolve()

            # 1. 路径遍历检查
            if not self.allow_path_traversal:
                try:
                    path.relative_to(self.workspace_root)
                except ValueError:
                    return SecurityViolation(
                        violation_type="path_traversal",
                        severity="high",
                        description=f"路径遍历尝试: {file_path}",
                        suggested_action="拒绝访问工作区外的文件",
                        timestamp=time.time(),
                        context=f"操作: {operation}, 文件: {file_path}",
                    )

            # 2. 文件扩展名检查
            if path.suffix.lower() in self.blocked_extensions:
                return SecurityViolation(
                    violation_type="blocked_file_type",
                    severity="medium",
                    description=f"尝试访问危险文件类型: {path.suffix}",
                    suggested_action="拒绝访问可执行文件",
                    timestamp=time.time(),
                    context=f"文件: {file_path}",
                )

            # 3. 文件大小检查（对于写操作）
            if operation in ["write", "append"]:
                if path.exists():
                    file_size = path.stat().st_size
                    if file_size > self.max_file_size:
                        return SecurityViolation(
                            violation_type="file_size_limit",
                            severity="medium",
                            description=f"文件过大: {file_size} bytes",
                            suggested_action=f"限制文件大小为 {self.max_file_size} bytes",
                            timestamp=time.time(),
                            context=f"文件: {file_path}, 大小: {file_size}",
                        )

            # 4. 敏感文件检查
            sensitive_files = [
                ".env",
                ".env.local",
                ".env.production",
                "id_rsa",
                "id_rsa.pub",
                "known_hosts",
                "config",
                ".git/config",
            ]

            if path.name in sensitive_files:
                return SecurityViolation(
                    violation_type="sensitive_file_access",
                    severity="high",
                    description=f"尝试访问敏感文件: {path.name}",
                    suggested_action="需要明确批准才能访问敏感配置文件",
                    timestamp=time.time(),
                    context=f"文件: {file_path}",
                )

        except Exception as e:
            return SecurityViolation(
                violation_type="file_check_error",
                severity="low",
                description=f"文件安全检查错误: {str(e)}",
                suggested_action="继续操作但记录错误",
                timestamp=time.time(),
                context=f"文件: {file_path}",
            )

        return None

    def _check_command_security(self, command: str) -> Optional[SecurityViolation]:
        """检查命令安全性"""
        if not self.enable_command_security:
            return None

        command_lower = command.lower().strip()

        # 1. 危险命令检查
        for cmd_name, pattern in self.dangerous_commands.items():
            if pattern.search(command_lower):
                severity = (
                    "high"
                    if cmd_name in ["rm", "dd", "format", "shutdown", "reboot"]
                    else "medium"
                )
                return SecurityViolation(
                    violation_type="dangerous_command",
                    severity=severity,
                    description=f"检测到危险命令: {cmd_name}",
                    suggested_action=f"禁止执行 {cmd_name} 命令或要求明确批准",
                    timestamp=time.time(),
                    context=f"命令: {command}",
                )

        # 2. 管道和重定向检查
        if any(
            char in command for char in ["|", "&", ";", "`", "$()"]
        ) and self.security_level in ["high", "strict"]:
            return SecurityViolation(
                violation_type="command_injection",
                severity="medium",
                description="检测到可能的命令注入字符",
                suggested_action="检查命令是否安全",
                timestamp=time.time(),
                context=f"命令: {command}",
            )

        # 3. 网络操作检查（在严格模式下）
        if self.security_level == "strict":
            network_commands = ["wget", "curl", "nc", "netcat", "telnet", "ftp", "ssh"]
            if any(cmd in command_lower for cmd in network_commands):
                return SecurityViolation(
                    violation_type="network_command",
                    severity="medium",
                    description="检测到网络相关命令",
                    suggested_action="在严格模式下限制网络操作",
                    timestamp=time.time(),
                    context=f"命令: {command}",
                )

        return None

    def _check_content_security(self, content: str) -> List[SecurityViolation]:
        """检查内容安全性"""
        violations = []

        if not self.enable_content_security:
            return violations

        # 1. 敏感信息检查
        for info_type, pattern in self.sensitive_patterns.items():
            matches = pattern.findall(content)
            if matches:
                severity = (
                    "high"
                    if info_type in ["private_key", "credit_card", "aws_access_key"]
                    else "medium"
                )

                # 遮蔽敏感信息用于日志
                masked_matches = [
                    match[:4] + "***" + match[-4:] if len(match) > 8 else "***"
                    for match in matches
                ]

                violations.append(
                    SecurityViolation(
                        violation_type="sensitive_information",
                        severity=severity,
                        description=f"检测到敏感信息 ({info_type}): {len(matches)} 个",
                        suggested_action="移除或遮蔽敏感信息",
                        timestamp=time.time(),
                        context=f"发现: {info_type}, 数量: {len(matches)}",
                    )
                )

        return violations

    def _validate_tool_call(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> Optional[SecurityViolation]:
        """验证工具调用安全性"""
        if tool_name == "write_file":
            file_path = tool_args.get("file_path", "")
            if file_path:
                return self._check_file_security(file_path, "write")

        elif tool_name == "read_file":
            file_path = tool_args.get("file_path", "")
            if file_path:
                return self._check_file_security(file_path, "read")

        elif tool_name == "shell":
            command = tool_args.get("command", "")
            if command:
                return self._check_command_security(command)

        return None

    def before_agent(
        self,
        state: SecurityState,
        runtime,
    ) -> SecurityState:
        """在代理执行前初始化安全设置"""
        security_settings = {
            "security_level": self.security_level,
            "workspace_root": str(self.workspace_root),
            "enable_file_security": self.enable_file_security,
            "enable_command_security": self.enable_command_security,
            "enable_content_security": self.enable_content_security,
            "max_file_size": self.max_file_size,
        }

        return {
            "security_settings": security_settings,
            "security_violations": [],
            "blocked_operations": [],
            "allowed_paths": [str(self.workspace_root)],
            "security_level": self.security_level,
        }

    async def abefore_agent(
        self,
        state: SecurityState,
        runtime,
    ) -> SecurityState:
        """异步：在代理执行前初始化安全设置"""
        return self.before_agent(state, runtime)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """包装模型调用，进行安全检查"""

        # 1. 检查请求内容的安全性
        if hasattr(request, "content") and request.content:
            content_violations = self._check_content_security(request.content)
            for violation in content_violations:
                self._log_security_event(violation)
                # 更新状态中的违规记录
                current_violations = request.state.get("security_violations", [])
                current_violations.append(violation)

        elif hasattr(request, "messages") and request.messages:
            all_content = " ".join(
                [
                    msg.content if hasattr(msg, "content") else msg.get("content", "")
                    for msg in request.messages
                    if hasattr(msg, "content") or hasattr(msg, "get")
                ]
            )
            content_violations = self._check_content_security(all_content)
            for violation in content_violations:
                self._log_security_event(violation)
                current_violations = request.state.get("security_violations", [])
                current_violations.append(violation)

        # 2. 执行模型调用
        response = handler(request)

        # 3. 检查响应中的工具调用
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})

                violation = self._validate_tool_call(tool_name, tool_args)
                if violation:
                    self._log_security_event(violation)
                    current_violations = request.state.get("security_violations", [])
                    current_violations.append(violation)

        return response

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """异步：包装模型调用，进行安全检查"""

        # 1. 检查请求内容的安全性
        if hasattr(request, "content") and request.content:
            content_violations = self._check_content_security(request.content)
            for violation in content_violations:
                self._log_security_event(violation)
                current_violations = request.state.get("security_violations", [])
                current_violations.append(violation)

        elif hasattr(request, "messages") and request.messages:
            all_content = " ".join(
                [
                    msg.content if hasattr(msg, "content") else msg.get("content", "")
                    for msg in request.messages
                    if hasattr(msg, "content") or hasattr(msg, "get")
                ]
            )
            content_violations = self._check_content_security(all_content)
            for violation in content_violations:
                self._log_security_event(violation)
                current_violations = request.state.get("security_violations", [])
                current_violations.append(violation)

        # 2. 执行模型调用
        response = await handler(request)

        # 3. 检查响应中的工具调用
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name", "")
                tool_args = tool_call.get("args", {})

                violation = self._validate_tool_call(tool_name, tool_args)
                if violation:
                    self._log_security_event(violation)
                    current_violations = request.state.get("security_violations", [])
                    current_violations.append(violation)

        return response

    def get_security_report(self) -> Dict[str, Any]:
        """获取安全报告"""
        try:
            audit_log = self.backend.read(self.audit_log_path)
            lines = audit_log.strip().split("\n") if audit_log else []

            violations_by_type = {}
            violations_by_severity = {"low": 0, "medium": 0, "high": 0, "critical": 0}

            for line in lines:
                if "[SECURITY]" in line:
                    parts = line.split(" - ")
                    if len(parts) >= 2:
                        severity = parts[0].split(" ")[1].lower()
                        description = parts[1]

                        violations_by_severity[severity] = (
                            violations_by_severity.get(severity, 0) + 1
                        )

                        # 提取违规类型
                        if "path_traversal" in description:
                            violations_by_type["path_traversal"] = (
                                violations_by_type.get("path_traversal", 0) + 1
                            )
                        elif "dangerous_command" in description:
                            violations_by_type["dangerous_command"] = (
                                violations_by_type.get("dangerous_command", 0) + 1
                            )
                        elif "sensitive_information" in description:
                            violations_by_type["sensitive_information"] = (
                                violations_by_type.get("sensitive_information", 0) + 1
                            )

            return {
                "total_violations": len(
                    [line for line in lines if "[SECURITY]" in line]
                ),
                "violations_by_type": violations_by_type,
                "violations_by_severity": violations_by_severity,
                "security_level": self.security_level,
                "workspace_root": str(self.workspace_root),
                "last_audit_entry": lines[-1] if lines else None,
            }
        except Exception as e:
            return {
                "error": f"Failed to generate security report: {e}",
                "security_level": self.security_level,
                "workspace_root": str(self.workspace_root),
            }


# 添加缺少的import
import time
