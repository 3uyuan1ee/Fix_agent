# Sessions API routes

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..models.schemas import MessageResponse, SessionCreate, SessionResponse
from ..services.session_service import SessionService

router = APIRouter()


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    return SessionService(db)


@router.post("/", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    session_service: SessionService = Depends(get_session_service),
):
    """Create a new session."""
    try:
        return session_service.create_session(session_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[SessionResponse])
async def get_sessions(session_service: SessionService = Depends(get_session_service)):
    """Get all sessions for the current user."""
    try:
        # For now, return all sessions (TODO: add user authentication)
        return session_service.get_user_sessions(user_id=1)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str, session_service: SessionService = Depends(get_session_service)
):
    """Get a specific session."""
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session_title(
    session_id: str,
    title: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Update session title."""
    try:
        updated_session = session_service.update_session_title(session_id, title)
        if not updated_session:
            raise HTTPException(status_code=404, detail="Session not found")
        return updated_session
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(
    session_id: str, session_service: SessionService = Depends(get_session_service)
):
    """Delete a session."""
    try:
        success = session_service.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True, "message": "Session deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{session_id}/messages", response_model=List[MessageResponse])
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    session_service: SessionService = Depends(get_session_service),
):
    """Get messages for a session."""
    try:
        messages = session_service.get_session_messages(session_id, limit)
        return [
            MessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                content=msg.content,
                role=msg.role,
                metadata=msg.extra_data,
                created_at=msg.created_at,
            )
            for msg in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
