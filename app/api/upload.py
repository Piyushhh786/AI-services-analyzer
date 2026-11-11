import os
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from app.session.manager import SessionManager
from app.ingestion.csv_parser import CSVParser
from app.ingestion.data_loader import DataLoader
from app.schemas.upload import UploadSummaryResponse
from app.core.exceptions import AppException
from app.core.logging import logger

router = APIRouter(prefix="/api/upload", tags=["Upload"])


@router.post("", response_model=UploadSummaryResponse)
async def upload_csv(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form(None)
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Get active session or create a new one
    session = SessionManager.get_or_create_session(session_id)
    sid = session.session_id

    try:
        content = await file.read()
        records, summary = CSVParser.parse(content, session_id=sid)
        DataLoader.load(records)

        # Generate preview
        sample_preview = [
            {
                "date": str(r.transaction_date)[:10],
                "merchant": r.merchant,
                "category": r.category,
                "amount": r.amount,
                "type": r.type,
                "description": r.description
            }
            for r in records[:5]
        ]

        return UploadSummaryResponse(
            session_id=sid,
            filename=file.filename,
            total_records=summary["total_records"],
            debit_count=summary["debit_count"],
            credit_count=summary["credit_count"],
            date_range_start=summary["date_range_start"],
            date_range_end=summary["date_range_end"],
            columns_detected=summary["columns_detected"],
            sample_preview=sample_preview
        )

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error during CSV upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")


@router.post("/sample", response_model=UploadSummaryResponse)
async def load_sample_csv(session_id: Optional[str] = Form(None)):
    """
    Convenient 1-click loading of sample transactions (transactions_6mo.csv).
    """
    # Look for transactions_6mo.csv in workspace root
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    sample_path = os.path.join(base_dir, "transactions_6mo.csv")
    if not os.path.exists(sample_path):
        # Check current working dir
        sample_path = os.path.abspath("transactions_6mo.csv")

    if not os.path.exists(sample_path):
        raise HTTPException(status_code=404, detail="Sample dataset transactions_6mo.csv not found.")

    with open(sample_path, "rb") as f:
        content = f.read()

    session = SessionManager.get_or_create_session(session_id)
    sid = session.session_id

    records, summary = CSVParser.parse(content, session_id=sid)
    DataLoader.load(records)

    sample_preview = [
        {
            "date": str(r.transaction_date)[:10],
            "merchant": r.merchant,
            "category": r.category,
            "amount": r.amount,
            "type": r.type,
            "description": r.description
        }
        for r in records[:5]
    ]

    return UploadSummaryResponse(
        session_id=sid,
        filename="transactions_6mo.csv",
        total_records=summary["total_records"],
        debit_count=summary["debit_count"],
        credit_count=summary["credit_count"],
        date_range_start=summary["date_range_start"],
        date_range_end=summary["date_range_end"],
        columns_detected=summary["columns_detected"],
        sample_preview=sample_preview
    )
