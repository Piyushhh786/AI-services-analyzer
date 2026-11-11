from app.agents.state import AgentState
from app.services.sql_generator import SQLGenerator
from app.services.sql_validator import SQLValidator
from app.services.sql_executor import SQLExecutor
from app.mcp.tools import DatabaseTools
from app.services.answer_generator import AnswerGenerator
from app.core.logging import logger


def generate_sql_node(state: AgentState) -> AgentState:
    logger.info(f"Node: generate_sql for question: {state['question']}")
    sql = SQLGenerator.generate_sql(state["session_id"], state["question"])
    return {**state, "sql": sql, "error": None}


def validate_sql_node(state: AgentState) -> AgentState:
    logger.info("Node: validate_sql")
    is_valid, safe_sql, error = SQLValidator.validate_and_sanitize(state["sql"], state["session_id"])
    if not is_valid:
        logger.warning(f"Validation failed: {error}")
        return {**state, "error": error}
    return {**state, "validated_sql": safe_sql, "error": None}


def execute_sql_node(state: AgentState) -> AgentState:
    logger.info("Node: execute_sql via MCP/DatabaseTools")
    sql_to_run = state.get("validated_sql") or state["sql"]
    try:
        rows = DatabaseTools.query_database(state["session_id"], sql_to_run)
        return {**state, "data": rows, "error": None}
    except Exception as e:
        logger.warning(f"Execution error: {e}")
        return {**state, "error": str(e)}


def correct_sql_node(state: AgentState) -> AgentState:
    logger.info(f"Node: correct_sql (attempt {state['retry_count'] + 1})")
    corrected = SQLGenerator.correct_sql(state["session_id"], state["sql"], state["error"] or "Unknown error")
    return {
        **state,
        "sql": corrected,
        "retry_count": state["retry_count"] + 1,
        "error": None
    }


def generate_answer_node(state: AgentState) -> AgentState:
    logger.info("Node: generate_answer")
    answer, chart_type = AnswerGenerator.generate_answer(
        question=state["question"],
        sql=state.get("validated_sql") or state.get("sql", ""),
        data=state.get("data", [])
    )
    return {**state, "answer": answer, "chart_type": chart_type}
