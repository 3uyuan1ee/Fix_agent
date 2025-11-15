"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# Base schemas
class BaseResponse(BaseModel):
    """Base response schema."""

    success: bool = True
    message: Optional[str] = None


# Session schemas
class SessionCreate(BaseModel):
    """Create session request."""

    title: Optional[str] = "New Session"
    workspace_path: Optional[str] = None


class SessionResponse(BaseResponse):
    """Session response."""

    session_id: str
    title: str
    workspace_path: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class SessionList(BaseModel):
    """List of sessions."""

    sessions: List[SessionResponse]
    total: int


# Message schemas
class MessageCreate(BaseModel):
    """Create message request."""

    content: str
    session_id: str
    file_references: Optional[List[str]] = []


class MessageResponse(BaseResponse):
    """Message response."""

    id: int
    session_id: str
    content: str
    role: str
    metadata: Optional[Dict[str, Any]]
    created_at: datetime


class ChatStreamChunk(BaseModel):
    """WebSocket streaming chunk."""

    type: str  # message, tool_call, todos, error, status
    content: Optional[str] = None
    session_id: str
    metadata: Optional[Dict[str, Any]] = None
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    todos: Optional[List[Dict[str, Any]]] = None


# File schemas
class FileUploadResponse(BaseResponse):
    """File upload response."""

    file_id: int
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    file_path: str


class FileListResponse(BaseResponse):
    """List files in workspace."""

    files: List[Dict[str, Any]]
    total_count: int


class FileContentResponse(BaseResponse):
    """File content response."""

    content: str
    file_path: str
    file_size: int
    last_modified: datetime


# Project schemas
class ProjectCreate(BaseModel):
    """Create project request."""

    name: str
    description: Optional[str] = None
    project_path: str


class ProjectResponse(BaseResponse):
    """Project response."""

    id: int
    name: str
    description: Optional[str]
    project_path: str
    project_type: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    analysis_count: int = 0


class ProjectAnalysisRequest(BaseModel):
    """Request project analysis."""

    analysis_type: str = "defect_analysis"
    file_patterns: Optional[List[str]] = [
        "**/*.py",
        "**/*.js",
        "**/*.ts",
        "**/*.java",
        "**/*.cpp",
    ]


class AnalysisResultResponse(BaseResponse):
    """Analysis result response."""

    analysis_id: int
    project_id: int
    analysis_type: str
    file_path: str
    status: str
    result_data: Dict[str, Any]
    created_at: datetime


# Memory schemas
class MemoryFileList(BaseResponse):
    """Memory files list."""

    files: List[str]


class MemoryFileContent(BaseResponse):
    """Memory file content."""

    content: str
    file_path: str


class MemoryFileUpdate(BaseModel):
    """Update memory file request."""

    content: str


# User schemas
class UserCreate(BaseModel):
    """Create user request."""

    email: str
    password: str
    full_name: Optional[str] = None


class UserResponse(BaseResponse):
    """User response."""

    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime


class UserLogin(BaseModel):
    """User login request."""

    email: str
    password: str


class TokenResponse(BaseResponse):
    """Authentication token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Configuration schemas
class ConfigurationResponse(BaseResponse):
    """Configuration response."""

    available_models: List[str]
    default_model: str
    available_tools: List[str]
    system_info: Dict[str, Any]


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]
