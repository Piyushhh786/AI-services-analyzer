import re
from typing import Optional
from app.llm.groq_client import groq_client
from app.llm.prompts import SQL_GENERATION_SYSTEM_PROMPT, SQL_CORRECTION_PROMPT
from app.utils.sql_helpers import clean_sql_markdown
from app.core.logging import logger

try:
    from langchain_core.messages import SystemMessage, HumanMessage
except ImportError:
    pass


class SQLGenerator:
    @staticmethod
    def generate_sql(session_id: str, question: str) -> str:
        llm = groq_client.get_llm()
        if groq_client.is_active and llm:
            try:
                system_prompt = SQL_GENERATION_SYSTEM_PROMPT.format(session_id=session_id)
                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=f"User question: {question}")
                ]
                response = llm.invoke(messages)
                sql = clean_sql_markdown(response.content)
                logger.info(f"Groq generated SQL: {sql}")
                return sql
            except Exception as e:
                logger.warning(f"Groq SQL generation failed ({e}). Falling back to heuristic generator.")

        # Built-in heuristic generator
        return SQLGenerator._heuristic_sql(session_id, question)

    @staticmethod
    def correct_sql(session_id: str, sql: str, error: str) -> str:
        llm = groq_client.get_llm()
        if groq_client.is_active and llm:
            try:
                prompt = SQL_CORRECTION_PROMPT.format(sql=sql, error=error, session_id=session_id)
                messages = [HumanMessage(content=prompt)]
                response = llm.invoke(messages)
                return clean_sql_markdown(response.content)
            except Exception as e:
                logger.warning(f"Groq SQL correction failed: {e}")

        # Fallback query
        return f"SELECT merchant, amount, category, transaction_date FROM transactions WHERE session_id = '{session_id}' AND type = 'DEBIT' ORDER BY amount DESC LIMIT 10"

    @staticmethod
    def _heuristic_sql(session_id: str, question: str) -> str:
        q = question.lower().strip()

        # Highest expense / where did I spend most money / biggest
        if any(w in q for w in ["most money", "highest expense", "highest spend", "biggest expense", "largest"]):
            return f"SELECT merchant, amount, category, transaction_date FROM transactions WHERE session_id = '{session_id}' AND type = 'DEBIT' ORDER BY amount DESC LIMIT 5"

        # Top merchants (with or without numbers like "top 5 merchants", "top merchants", "frequent")
        if ("merchant" in q and any(w in q for w in ["top", "frequent", "favorite", "spend most", "highest"])) or "merchants" in q:
            # Check if a specific limit was asked
            match_num = re.search(r"\b(\d+)\b", q)
            lim = int(match_num.group(1)) if match_num and int(match_num.group(1)) <= 20 else 5
            return f"SELECT merchant, SUM(amount) as total_spend, COUNT(*) as txn_count FROM transactions WHERE session_id = '{session_id}' AND type = 'DEBIT' GROUP BY merchant ORDER BY total_spend DESC LIMIT {lim}"

        # Food / dining expenses
        if any(w in q for w in ["food", "dining", "zomato", "swiggy", "eating", "restaurant"]):
            return f"SELECT merchant, SUM(amount) as total_spend, COUNT(*) as txn_count FROM transactions WHERE session_id = '{session_id}' AND (category = 'Food' OR LOWER(merchant) LIKE '%swiggy%' OR LOWER(merchant) LIKE '%zomato%' OR LOWER(merchant) LIKE '%mcdonald%') AND type = 'DEBIT' GROUP BY merchant ORDER BY total_spend DESC"

        # Travel / commute
        if any(w in q for w in ["travel", "cab", "uber", "ola", "rapido", "commute", "fuel", "petrol", "fastag"]):
            return f"SELECT merchant, SUM(amount) as total_spend, COUNT(*) as txn_count FROM transactions WHERE session_id = '{session_id}' AND (category = 'Travel' OR LOWER(merchant) LIKE '%uber%' OR LOWER(merchant) LIKE '%ola%' OR LOWER(merchant) LIKE '%rapido%' OR LOWER(merchant) LIKE '%fuel%') AND type = 'DEBIT' GROUP BY merchant ORDER BY total_spend DESC"

        # Shopping
        if any(w in q for w in ["shopping", "amazon", "flipkart", "myntra"]):
            return f"SELECT merchant, SUM(amount) as total_spend, COUNT(*) as txn_count FROM transactions WHERE session_id = '{session_id}' AND (category = 'Shopping' OR LOWER(merchant) LIKE '%amazon%' OR LOWER(merchant) LIKE '%myntra%' OR LOWER(merchant) LIKE '%flipkart%') AND type = 'DEBIT' GROUP BY merchant ORDER BY total_spend DESC"

        # Bills / Utilities
        if any(w in q for w in ["bill", "utility", "electricity", "recharge", "airtel", "credit card"]):
            return f"SELECT merchant, SUM(amount) as total_spend, COUNT(*) as txn_count FROM transactions WHERE session_id = '{session_id}' AND (category = 'Bills' OR LOWER(merchant) LIKE '%bill%' OR LOWER(merchant) LIKE '%recharge%') AND type = 'DEBIT' GROUP BY merchant ORDER BY total_spend DESC"

        # Entertainment
        if any(w in q for w in ["entertainment", "movie", "bookmyshow", "hotstar", "netflix", "spotify"]):
            return f"SELECT merchant, SUM(amount) as total_spend, COUNT(*) as txn_count FROM transactions WHERE session_id = '{session_id}' AND (category = 'Entertainment' OR LOWER(merchant) LIKE '%netflix%' OR LOWER(merchant) LIKE '%hotstar%') AND type = 'DEBIT' GROUP BY merchant ORDER BY total_spend DESC"

        # Salary / Income / Savings
        if any(w in q for w in ["salary", "income", "credit", "received", "earned", "savings"]):
            return f"SELECT merchant, SUM(amount) as total_income, COUNT(*) as txn_count FROM transactions WHERE session_id = '{session_id}' AND type = 'CREDIT' GROUP BY merchant ORDER BY total_income DESC"

        # Category breakdown
        if any(w in q for w in ["category", "categories", "breakdown"]):
            return f"SELECT category, SUM(amount) as total_spend, COUNT(*) as txn_count FROM transactions WHERE session_id = '{session_id}' AND type = 'DEBIT' GROUP BY category ORDER BY total_spend DESC"

        # Unusual or outlier expenses
        if any(w in q for w in ["unusual", "outlier", "anomaly", "high value"]):
            return f"SELECT merchant, amount, category, transaction_date FROM transactions WHERE session_id = '{session_id}' AND type = 'DEBIT' ORDER BY amount DESC LIMIT 10"

        # Default query
        return f"SELECT merchant, amount, category, type, transaction_date FROM transactions WHERE session_id = '{session_id}' ORDER BY transaction_date DESC LIMIT 10"
