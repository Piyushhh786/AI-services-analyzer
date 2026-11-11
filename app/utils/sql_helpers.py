import re
from typing import Dict, Any, List


def format_currency_inr(amount: float) -> str:
    """Formats a float as Indian Rupee string, e.g. ₹50,000.00"""
    return f"₹{amount:,.2f}"


def clean_sql_markdown(sql: str) -> str:
    """Extracts raw SQL from code blocks if LLM output includes markdown formatting."""
    sql = sql.strip()
    if sql.startswith("```"):
        lines = sql.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        sql = "\n".join(lines).strip()
    return sql
