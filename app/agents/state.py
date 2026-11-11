from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    session_id: str
    question: str
    sql: str
    validated_sql: str
    data: List[Dict[str, Any]]
    answer: str
    chart_type: Optional[str]
    error: Optional[str]
    retry_count: int
    max_retries: int
