import pytest
import uuid
from datetime import datetime
from app.agents.graph import sql_agent
from app.database.models import TransactionModel
from app.database.repository import repository
from app.session.manager import SessionManager


def test_sql_agent_execution_flow():
    sid = str(uuid.uuid4())
    SessionManager.get_or_create_session(sid)

    # Insert sample transactions
    repository.insert_transactions([
        TransactionModel(
            session_id=sid,
            transaction_date=datetime.now(),
            merchant="Swiggy",
            category="Food",
            amount=500.0,
            type="DEBIT"
        ),
        TransactionModel(
            session_id=sid,
            transaction_date=datetime.now(),
            merchant="Uber",
            category="Travel",
            amount=250.0,
            type="DEBIT"
        )
    ])

    result = sql_agent.run(session_id=sid, question="Where did I spend most money?")
    assert result is not None
    assert "answer" in result
    assert result["answer"] != ""
    assert result["data"] is not None
    assert len(result["data"]) > 0
