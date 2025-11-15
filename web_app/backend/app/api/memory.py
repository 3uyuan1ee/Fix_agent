# Memory API routes

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..models.database import get_db
from ..models.schemas import MemoryFileContent, MemoryFileList
from ..services.session_service import SessionService

router = APIRouter()


def get_session_service(db: Session = Depends(get_db)) -> SessionService:
    return SessionService(db)


@router.get("/{session_id}/files", response_model=MemoryFileList)
async def get_memory_files(
    session_id: str, session_service: SessionService = Depends(get_session_service)
):
    """Get memory files for a session."""
    try:
        ai_adapter = session_service.get_ai_adapter(session_id)
        if not ai_adapter:
            raise HTTPException(status_code=404, detail="Session not found")

        files = ai_adapter.get_memory_files()
        return MemoryFileList(files=files)

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to get memory files: {str(e)}"
        )


@router.get("/{session_id}/files/{file_path:path}", response_model=MemoryFileContent)
async def get_memory_file_content(
    session_id: str,
    file_path: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Get memory file content."""
    try:
        ai_adapter = session_service.get_ai_adapter(session_id)
        if not ai_adapter:
            raise HTTPException(status_code=404, detail="Session not found")

        content = ai_adapter.read_memory_file(file_path)
        return MemoryFileContent(content=content, file_path=file_path)

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to read memory file: {str(e)}"
        )


@router.put("/{session_id}/files/{file_path:path}")
async def update_memory_file(
    session_id: str,
    file_path: str,
    content: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Update memory file content."""
    try:
        ai_adapter = session_service.get_ai_adapter(session_id)
        if not ai_adapter:
            raise HTTPException(status_code=404, detail="Session not found")

        ai_adapter.write_memory_file(file_path, content)
        return {"success": True, "message": "Memory file updated successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to update memory file: {str(e)}"
        )
