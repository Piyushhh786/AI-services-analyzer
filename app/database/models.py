from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class UploadSessionModel:
    session_id: str
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    status: str = "active"


@dataclass
class TransactionModel:
    session_id: str
    transaction_date: datetime
    merchant: str
    category: str
    amount: float
    type: str  # DEBIT or CREDIT
    description: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
