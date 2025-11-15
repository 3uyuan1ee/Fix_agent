# Configuration API routes

from fastapi import APIRouter

from ..core.config import settings
from ..models.schemas import ConfigurationResponse, HealthCheckResponse

router = APIRouter()


@router.get("/config", response_model=ConfigurationResponse)
async def get_configuration():
    """Get application configuration."""
    # Get available models from environment
    available_models = []
    if settings.openai_api_key:
        available_models.append(settings.openai_model)
    if settings.anthropic_api_key:
        available_models.append(settings.anthropic_model)

    return ConfigurationResponse(
        available_models=available_models,
        default_model=(
            settings.openai_model
            if settings.openai_api_key
            else settings.anthropic_model
        ),
        available_tools=[
            "analyze_code_defects",
            "compile_project",
            "run_and_monitor",
            "run_tests_with_error_capture",
            "explore_project_structure",
            "analyze_code_complexity",
            "http_request",
            "web_search",
        ],
        system_info={
            "app_name": settings.app_name,
            "app_version": settings.app_version,
            "debug": settings.debug,
            "workspace_root": settings.workspace_root,
        },
    )


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    from datetime import datetime

    return HealthCheckResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.utcnow().isoformat(),
        services={
            "database": "connected",
            "websocket": "available",
            "ai_models": (
                "configured"
                if (settings.openai_api_key or settings.anthropic_api_key)
                else "not_configured"
            ),
        },
    )
