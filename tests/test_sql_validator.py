import pytest
from app.services.sql_validator import SQLValidator


def test_sql_validator_allows_select():
    sid = "test-uuid"
    sql = "SELECT merchant, amount FROM transactions WHERE type = 'DEBIT'"
    is_valid, safe_sql, error = SQLValidator.validate_and_sanitize(sql, sid)
    assert is_valid is True
    assert sid in safe_sql
    assert "error" not in error.lower()


def test_sql_validator_blocks_forbidden_dml():
    sid = "test-uuid"
    sql = "DELETE FROM transactions WHERE amount > 100"
    is_valid, _, error = SQLValidator.validate_and_sanitize(sql, sid)
    assert is_valid is False
    assert "Forbidden" in error or "SELECT" in error


def test_sql_validator_blocks_drop_table():
    sid = "test-uuid"
    sql = "DROP TABLE transactions"
    is_valid, _, error = SQLValidator.validate_and_sanitize(sql, sid)
    assert is_valid is False
