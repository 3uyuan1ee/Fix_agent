# Files API routes

import os
import shutil
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models.database import get_db
from ..models.schemas import FileContentResponse, FileUploadResponse

router = APIRouter()


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
):
    """Upload a file to the session workspace."""
    try:
        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.upload_dir) / session_id
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Save file
        file_path = upload_dir / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get file size
        file_size = file_path.stat().st_size

        return FileUploadResponse(
            file_id=1,  # TODO: Add database record
            filename=file.filename,
            original_filename=file.filename,
            file_size=file_size,
            mime_type=file.content_type or "application/octet-stream",
            file_path=str(file_path.relative_to(settings.upload_dir)),
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to upload file: {str(e)}")


@router.get("/{session_id}")
async def list_files(
    session_id: str,
    path: str = "",
):
    """List files in a session workspace."""
    try:
        workspace_dir = Path(settings.workspace_root) / session_id
        if not workspace_dir.exists():
            workspace_dir.mkdir(parents=True, exist_ok=True)

        target_path = workspace_dir / path if path else workspace_dir

        if not target_path.exists():
            return {"files": [], "total_count": 0}

        files = []
        for item in target_path.iterdir():
            if item.is_file():
                files.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(workspace_dir)),
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime,
                        "is_file": True,
                    }
                )
            elif item.is_dir():
                files.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(workspace_dir)),
                        "size": 0,
                        "modified": item.stat().st_mtime,
                        "is_file": False,
                    }
                )

        return {"files": files, "total_count": len(files)}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to list files: {str(e)}")


@router.get("/{session_id}/content")
async def get_file_content(
    session_id: str,
    path: str,
):
    """Get file content."""
    try:
        workspace_dir = Path(settings.workspace_root) / session_id
        file_path = workspace_dir / path

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")

        # Don't read binary files
        if file_path.suffix.lower() in [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".pdf",
            ".zip",
        ]:
            raise HTTPException(status_code=400, detail="Cannot read binary files")

        content = file_path.read_text(encoding="utf-8")
        file_size = file_path.stat().st_size

        return FileContentResponse(
            content=content,
            file_path=path,
            file_size=file_size,
            last_modified=file_path.stat().st_mtime,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")


@router.delete("/{session_id}")
async def delete_file(
    session_id: str,
    path: str,
):
    """Delete a file."""
    try:
        workspace_dir = Path(settings.workspace_root) / session_id
        file_path = workspace_dir / path

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        if file_path.is_file():
            file_path.unlink()
        elif file_path.is_dir():
            shutil.rmtree(file_path)

        return {"success": True, "message": "File deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete file: {str(e)}")
