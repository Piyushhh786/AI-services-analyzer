import pytest
import os
from app.ingestion.csv_parser import CSVParser
from app.ingestion.column_mapper import ColumnMapper


def test_column_mapper_detection():
    cols = ["date", "merchant", "amount", "type"]
    mapping = ColumnMapper.detect_columns(cols)
    assert mapping["date"] == "date"
    assert mapping["merchant"] == "merchant"
    assert mapping["amount"] == "amount"
    assert mapping["type"] == "type"


def test_merchant_categorization():
    assert ColumnMapper.categorize_merchant("Swiggy", "", "DEBIT") == "Food"
    assert ColumnMapper.categorize_merchant("Uber India", "", "DEBIT") == "Travel"
    assert ColumnMapper.categorize_merchant("Amazon India", "", "DEBIT") == "Shopping"
    assert ColumnMapper.categorize_merchant("Salary Credit", "", "CREDIT") == "Salary"
    assert ColumnMapper.categorize_merchant("Unknown Merchant XYZ", "", "DEBIT") == "Others"


def test_csv_parser_with_sample_data():
    sample_csv = b"""date,merchant,amount,type
2024-01-01,Salary Credit,85000.00,CREDIT
2024-01-01,Swiggy,450.00,DEBIT
2024-01-02,Uber,280.00,DEBIT
"""
    records, summary = CSVParser.parse(sample_csv, session_id="test-session-1")
    assert len(records) == 3
    assert summary["total_records"] == 3
    assert summary["credit_count"] == 1
    assert summary["debit_count"] == 2
    assert records[0].category == "Salary"
    assert records[1].category == "Food"
    assert records[2].category == "Travel"
