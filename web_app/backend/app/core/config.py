"""Core configuration for the web application."""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # App settings
    app_name: str = "Fix Agent Web"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = "sqlite:///./fix_agent_web.db"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30 * 24 * 60  # 30 days

    # File storage
    upload_dir: str = "uploads"
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # AI Model settings (复用CLI配置)
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-5-mini"

    anthropic_api_key: Optional[str] = None
    anthropic_base_url: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    tavily_api_key: Optional[str] = None

    # Model parameters
    model_temperature: float = 0.3
    model_max_tokens: Optional[int] = None
    model_timeout: Optional[int] = None
    model_max_retries: int = 3

    # Workspace settings
    workspace_root: str = "./workspaces"

    class Config:
        env_file = ".env"
        case_sensitive = False


# 全局设置实例
settings = Settings()


# 确保必要的目录存在
def ensure_directories():
    """Create necessary directories if they don't exist."""
    directories = [
        settings.upload_dir,
        settings.workspace_root,
        Path(settings.workspace_root) / "sessions",
        Path(settings.workspace_root) / "memories",
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


# 在模块加载时创建目录
ensure_directories()
