from fastapi import APIRouter, HTTPException, Path
from app.session.manager import SessionManager
from app.schemas.session import SessionCreateResponse, SessionStatusResponse
from app.core.exceptions import SessionExpiredException

router = APIRouter(prefix="/api/session", tags=["Session"])


@router.post("", response_model=SessionCreateResponse)
def create_session():
    session = SessionManager.create_session()
    return SessionCreateResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        expires_at=session.expires_at,
        status=session.status
    )


@router.get("/{session_id}", response_model=SessionStatusResponse)
def get_session_status(session_id: str = Path(...)):
    try:
        session = SessionManager.validate_session(session_id)
        count = SessionManager.get_session_record_count(session_id)
        return SessionStatusResponse(
            session_id=session.session_id,
            is_active=True,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_activity=session.last_activity,
            record_count=count
        )
    except SessionExpiredException:
        return SessionStatusResponse(
            session_id=session_id,
            is_active=False,
            record_count=0
        )


@router.delete("/{session_id}")
def delete_session(session_id: str = Path(...)):
    SessionManager.delete_session(session_id)
    return {"message": f"Session {session_id} and all related records have been deleted."}
