"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

import uvicorn
from app.api import config, memory, sessions
from app.core.config import settings
from app.models.database import Base, engine
from app.services.session_service import SessionService
from app.websocket.chat_handler import ChatHandler
from app.websocket.connection_manager import manager
from fastapi import (Depends, FastAPI, File, Form, HTTPException, UploadFile,
                     WebSocket, WebSocketDisconnect)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Fix Agent Web Server...")

    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    # Load environment variables from CLI project
    from dotenv import load_dotenv

    load_dotenv()

    logger.info("Server startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Fix Agent Web Server...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered code analysis and fixing tool",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
app.include_router(config.router, prefix="/api", tags=["config"])

# Serve static files (uploads, workspaces)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount(
    "/workspaces", StaticFiles(directory=settings.workspace_root), name="workspaces"
)


# WebSocket endpoint for real-time chat
@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    user_id: int = None,  # TODO: Add authentication
):
    """WebSocket endpoint for real-time chat."""
    try:
        # Create session service instance
        from app.models.database import SessionLocal

        db = SessionLocal()
        session_service = SessionService(db)

        # Create chat handler
        chat_handler = ChatHandler(session_service)

        # Handle connection
        await chat_handler.handle_connection(websocket, session_id, user_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.close(code=1000)
    finally:
        db.close()


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "timestamp": "2024-01-01T00:00:00Z",  # TODO: Use actual timestamp
        "services": {
            "database": "connected",
            "websocket": "available",
            "ai_models": "configured",
        },
    }


# Root endpoint - serve the web interface
@app.get("/")
async def root():
    """Root endpoint - serve the web interface."""
    from fastapi.responses import FileResponse

    return FileResponse("../index.html")


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "success": False,
        "message": "Internal server error",
        "details": str(exc) if settings.debug else None,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )
