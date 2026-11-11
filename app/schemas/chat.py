from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ChatRequest(BaseModel):
    session_id: str
    message: str
    include_sql: bool = True


class ChatResponse(BaseModel):
    session_id: str
    message: str
    answer: str
    sql: Optional[str] = None
    data: Optional[List[Dict[str, Any]]] = None
    chart_type: Optional[str] = None  # 'bar', 'pie', 'line', 'card', None
    confidence: Optional[float] = 1.0
    error: Optional[str] = None
