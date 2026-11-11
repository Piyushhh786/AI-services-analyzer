import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.session.manager import SessionManager
from app.database.repository import repository


def test_session_creation_and_deletion():
    sid = str(uuid.uuid4())
    session = SessionManager.create_session()
    assert session.session_id is not None
    assert session.status == "active"

    # Delete session
    deleted = SessionManager.delete_session(session.session_id)
    assert deleted is True

    # Check it's gone
    assert repository.get_session(session.session_id) is None
