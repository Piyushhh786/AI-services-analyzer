import pytest
import uuid
from datetime import datetime
from app.database.models import TransactionModel
from app.ingestion.data_loader import DataLoader
from app.session.manager import SessionManager
from app.database.repository import repository


def test_data_loader_insert_and_count():
    session_id = str(uuid.uuid4())
    SessionManager.get_or_create_session(session_id)

    records = [
        TransactionModel(
            session_id=session_id,
            transaction_date=datetime.now(),
            merchant="Swiggy",
            category="Food",
            amount=350.0,
            type="DEBIT"
        ),
        TransactionModel(
            session_id=session_id,
            transaction_date=datetime.now(),
            merchant="Salary Credit",
            category="Salary",
            amount=50000.0,
            type="CREDIT"
        )
    ]

    count = DataLoader.load(records)
    assert count == 2

    stored_count = repository.get_transaction_count(session_id)
    assert stored_count == 2
