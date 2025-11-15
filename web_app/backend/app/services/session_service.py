"""Session management service."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..core.ai_adapter import AIAdapter
from ..core.config import settings
from ..models.database import Message
from ..models.database import Session as DBSession
from ..models.database import UploadedFile
from ..models.schemas import SessionCreate, SessionResponse


class SessionService:
    """Service for managing user sessions."""

    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self, session_data: SessionCreate, user_id: int = 1
    ) -> SessionResponse:
        """Create a new session."""
        session_id = str(uuid.uuid4())

        # Create workspace directory
        workspace_path = (
            session_data.workspace_path or f"{settings.workspace_root}/{session_id}"
        )
        workspace = Path(workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)

        # Create database record
        db_session = DBSession(
            session_id=session_id,
            user_id=user_id,
            title=session_data.title,
            workspace_path=str(workspace),
            is_active=True,
        )

        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)

        # Initialize AI adapter for this session
        ai_adapter = AIAdapter(session_id, str(workspace))

        return self._to_response(db_session)

    def get_session(self, session_id: str) -> Optional[SessionResponse]:
        """Get session by ID."""
        db_session = (
            self.db.query(DBSession)
            .filter(DBSession.session_id == session_id, DBSession.is_active == True)
            .first()
        )

        if not db_session:
            return None

        return self._to_response(db_session)

    def get_user_sessions(self, user_id: int) -> List[SessionResponse]:
        """Get all sessions for a user."""
        db_sessions = (
            self.db.query(DBSession)
            .filter(DBSession.user_id == user_id, DBSession.is_active == True)
            .order_by(DBSession.updated_at.desc())
            .all()
        )

        return [self._to_response(session) for session in db_sessions]

    def update_session_title(
        self, session_id: str, title: str
    ) -> Optional[SessionResponse]:
        """Update session title."""
        db_session = (
            self.db.query(DBSession).filter(DBSession.session_id == session_id).first()
        )

        if not db_session:
            return None

        db_session.title = title
        db_session.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(db_session)

        return self._to_response(db_session)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        db_session = (
            self.db.query(DBSession).filter(DBSession.session_id == session_id).first()
        )

        if not db_session:
            return False

        # Mark as inactive (soft delete)
        db_session.is_active = False
        db_session.updated_at = datetime.utcnow()
        self.db.commit()

        # Optionally clean up files
        try:
            workspace = Path(db_session.workspace_path)
            if workspace.exists() and workspace.is_dir():
                import shutil

                shutil.rmtree(workspace)
        except Exception:
            pass  # Ignore cleanup errors

        return True

    def add_message(
        self, session_id: str, content: str, role: str, metadata: Dict[str, Any] = None
    ) -> Message:
        """Add a message to the session."""
        message = Message(
            session_id=session_id, content=content, role=role, extra_data=metadata or {}
        )

        self.db.add(message)

        # Update session timestamp
        db_session = (
            self.db.query(DBSession).filter(DBSession.session_id == session_id).first()
        )
        if db_session:
            db_session.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(message)

        return message

    def get_session_messages(self, session_id: str, limit: int = 100) -> List[Message]:
        """Get messages for a session."""
        return (
            self.db.query(Message)
            .filter(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_ai_adapter(self, session_id: str) -> Optional[AIAdapter]:
        """Get AI adapter for a session."""
        db_session = (
            self.db.query(DBSession)
            .filter(DBSession.session_id == session_id, DBSession.is_active == True)
            .first()
        )

        if not db_session:
            return None

        return AIAdapter(session_id, db_session.workspace_path)

    def _to_response(self, db_session: DBSession) -> SessionResponse:
        """Convert database model to response schema."""
        message_count = (
            self.db.query(Message)
            .filter(Message.session_id == db_session.session_id)
            .count()
        )

        return SessionResponse(
            session_id=db_session.session_id,
            title=db_session.title,
            workspace_path=db_session.workspace_path,
            is_active=db_session.is_active,
            created_at=db_session.created_at,
            updated_at=db_session.updated_at,
            message_count=message_count,
        )
