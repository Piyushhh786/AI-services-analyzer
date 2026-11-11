from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SessionCreateResponse(BaseModel):
    session_id: str
    created_at: datetime
    expires_at: datetime
    status: str = "active"


class SessionStatusResponse(BaseModel):
    session_id: str
    is_active: bool
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    record_count: int = 0
