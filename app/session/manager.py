import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from app.database.repository import repository
from app.database.models import UploadSessionModel
from app.core.config import settings
from app.core.exceptions import SessionExpiredException
from app.core.logging import logger


def _parse_and_normalize_dt(val: Any) -> datetime:
    if isinstance(val, str):
        try:
            val = datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            try:
                val = datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                val = datetime.now(timezone.utc)
    elif not isinstance(val, datetime):
        return datetime.now(timezone.utc)

    if val.tzinfo is None:
        val = val.replace(tzinfo=timezone.utc)
    return val


class SessionManager:
    @staticmethod
    def create_session() -> UploadSessionModel:
        session_id = str(uuid.uuid4())
        session = repository.create_session(session_id, ttl_minutes=settings.SESSION_TTL_MINUTES)
        logger.info(f"Created new session: {session_id} (TTL: {settings.SESSION_TTL_MINUTES} mins)")
        return session

    @staticmethod
    def get_or_create_session(session_id: Optional[str] = None) -> UploadSessionModel:
        if session_id:
            session = repository.get_session(session_id)
            if session:
                now = datetime.now(timezone.utc)
                exp = _parse_and_normalize_dt(session.expires_at)
                if exp > now:
                    repository.update_session_activity(session_id, ttl_minutes=settings.SESSION_TTL_MINUTES)
                    return session

        return SessionManager.create_session()

    @staticmethod
    def validate_session(session_id: str) -> UploadSessionModel:
        session = repository.get_session(session_id)
        if not session:
            raise SessionExpiredException(f"Session '{session_id}' not found.")

        now = datetime.now(timezone.utc)
        exp = _parse_and_normalize_dt(session.expires_at)

        if exp <= now:
            repository.delete_session(session_id)
            raise SessionExpiredException(f"Session '{session_id}' has expired.")

        repository.update_session_activity(session_id, ttl_minutes=settings.SESSION_TTL_MINUTES)
        return session

    @staticmethod
    def delete_session(session_id: str) -> bool:
        logger.info(f"Deleting session: {session_id}")
        return repository.delete_session(session_id)

    @staticmethod
    def get_session_record_count(session_id: str) -> int:
        return repository.get_transaction_count(session_id)
