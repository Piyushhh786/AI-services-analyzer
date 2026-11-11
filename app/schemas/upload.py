from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class ColumnMappingRequest(BaseModel):
    date_column: str = "date"
    merchant_column: str = "merchant"
    amount_column: str = "amount"
    type_column: Optional[str] = "type"
    category_column: Optional[str] = None
    description_column: Optional[str] = None


class TransactionRecord(BaseModel):
    id: Optional[int] = None
    session_id: str
    transaction_date: datetime
    merchant: str
    category: str
    description: Optional[str] = None
    amount: float
    type: str  # 'DEBIT' or 'CREDIT'
    extra_data: Optional[Dict[str, Any]] = None


class UploadSummaryResponse(BaseModel):
    session_id: str
    filename: str
    total_records: int
    debit_count: int
    credit_count: int
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    columns_detected: List[str]
    sample_preview: List[Dict[str, Any]]
