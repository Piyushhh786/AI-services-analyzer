import pytest
from app.services.sql_generator import SQLGenerator


def test_heuristic_sql_generation():
    sid = "test-session-id"
    
    sql_top = SQLGenerator._heuristic_sql(sid, "Show my top merchants")
    assert "ORDER BY total_spend DESC" in sql_top
    assert sid in sql_top

    sql_food = SQLGenerator._heuristic_sql(sid, "How much did I spend on food and dining?")
    assert "Food" in sql_food
    assert sid in sql_food

    sql_salary = SQLGenerator._heuristic_sql(sid, "What was my salary or income?")
    assert "CREDIT" in sql_salary
    assert sid in sql_salary
