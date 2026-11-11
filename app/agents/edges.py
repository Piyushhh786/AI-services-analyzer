from typing import Literal
from app.agents.state import AgentState
from app.core.logging import logger


def route_after_validation(state: AgentState) -> Literal["execute_sql", "correct_sql", "generate_answer"]:
    if state.get("error"):
        if state["retry_count"] < state["max_retries"]:
            return "correct_sql"
        logger.error("Max retries reached after validation error.")
        return "generate_answer"
    return "execute_sql"


def route_after_execution(state: AgentState) -> Literal["generate_answer", "correct_sql"]:
    if state.get("error"):
        if state["retry_count"] < state["max_retries"]:
            return "correct_sql"
        logger.error("Max retries reached after execution error.")
        return "generate_answer"
    return "generate_answer"
