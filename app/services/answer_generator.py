import json
from typing import List, Dict, Any, Tuple
from app.llm.groq_client import groq_client
from app.llm.prompts import ANSWER_GENERATION_SYSTEM_PROMPT
from app.utils.sql_helpers import format_currency_inr
from app.core.logging import logger

try:
    from langchain_core.messages import SystemMessage, HumanMessage
except ImportError:
    pass


class AnswerGenerator:
    @staticmethod
    def generate_answer(question: str, sql: str, data: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        Generates natural language explanation and determines suggested chart type ('bar', 'pie', 'line', 'card', or None).
        Returns (answer, chart_type).
        """
        chart_type = AnswerGenerator._determine_chart_type(question, data)

        llm = groq_client.get_llm()
        if groq_client.is_active and llm:
            try:
                data_preview = json.dumps(data[:15], default=str)
                prompt = (
                    f"User Question: {question}\n"
                    f"Executed SQL: {sql}\n"
                    f"Result Data (up to 15 rows):\n{data_preview}\n\n"
                    f"Provide a clear, engaging, conversational financial answer in Indian Rupees (₹)."
                )
                messages = [
                    SystemMessage(content=ANSWER_GENERATION_SYSTEM_PROMPT),
                    HumanMessage(content=prompt)
                ]
                resp = llm.invoke(messages)
                return resp.content.strip(), chart_type
            except Exception as e:
                logger.warning(f"Groq answer generation failed: {e}")

        # Built-in heuristic answer generator
        answer = AnswerGenerator._heuristic_answer(question, data)
        return answer, chart_type

    @staticmethod
    def _determine_chart_type(question: str, data: List[Dict[str, Any]]) -> str:
        if not data or len(data) <= 1:
            return "card"
        q = question.lower()
        if any(w in q for w in ["category", "breakdown", "distribution", "share"]):
            return "pie"
        if any(w in q for w in ["trend", "over time", "monthly", "daily"]):
            return "line"
        if any(w in q for w in ["top", "merchant", "highest", "most", "compare"]):
            return "bar"
        return "bar"

    @staticmethod
    def _heuristic_answer(question: str, data: List[Dict[str, Any]]) -> str:
        if not data:
            return "I couldn't find any transaction records matching your query."

        # If single aggregate result
        if len(data) == 1:
            row = data[0]
            items = []
            for k, v in row.items():
                if isinstance(v, (int, float)):
                    items.append(f"{k.replace('_', ' ').title()}: {format_currency_inr(v) if 'spend' in k or 'amount' in k or 'income' in k or 'total' in k else v}")
                elif v is not None:
                    items.append(f"{k.replace('_', ' ').title()}: {v}")
            return "Here is the summary based on your data: " + ", ".join(items) + "."

        # Multiple rows: Top items
        lines = ["Here are the results from your transactions:"]
        for idx, row in enumerate(data[:5], start=1):
            name = row.get("merchant") or row.get("category") or f"Item {idx}"
            amount = row.get("total_spend") or row.get("amount") or row.get("total_income")
            if amount is not None:
                amt_str = format_currency_inr(float(amount))
                count_str = f" ({row.get('txn_count', '')} txns)" if "txn_count" in row else ""
                lines.append(f"{idx}. **{name}**: {amt_str}{count_str}")
            else:
                lines.append(f"{idx}. **{name}**")

        if len(data) > 5:
            lines.append(f"_...and {len(data) - 5} more records._")

        return "\n".join(lines)
