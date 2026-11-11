from typing import Dict, Any
from app.agents.state import AgentState
from app.agents.nodes import (
    generate_sql_node,
    validate_sql_node,
    execute_sql_node,
    correct_sql_node,
    generate_answer_node,
)
from app.agents.edges import (
    route_after_validation,
    route_after_execution,
)
from app.core.logging import logger

try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


class SQLAgentWorkflow:
    def __init__(self):
        self.workflow = None
        if LANGGRAPH_AVAILABLE:
            try:
                graph = StateGraph(AgentState)
                graph.add_node("generate_sql", generate_sql_node)
                graph.add_node("validate_sql", validate_sql_node)
                graph.add_node("execute_sql", execute_sql_node)
                graph.add_node("correct_sql", correct_sql_node)
                graph.add_node("generate_answer", generate_answer_node)

                graph.add_edge(START, "generate_sql")
                graph.add_edge("generate_sql", "validate_sql")

                graph.add_conditional_edges(
                    "validate_sql",
                    route_after_validation,
                    {
                        "execute_sql": "execute_sql",
                        "correct_sql": "correct_sql",
                        "generate_answer": "generate_answer"
                    }
                )

                graph.add_conditional_edges(
                    "execute_sql",
                    route_after_execution,
                    {
                        "generate_answer": "generate_answer",
                        "correct_sql": "correct_sql"
                    }
                )

                graph.add_edge("correct_sql", "validate_sql")
                graph.add_edge("generate_answer", END)

                self.workflow = graph.compile()
                logger.info("LangGraph SQL workflow compiled successfully.")
            except Exception as e:
                logger.warning(f"Could not compile LangGraph: {e}. Using deterministic pipeline runner.")
                self.workflow = None

    def run(self, session_id: str, question: str) -> AgentState:
        initial_state: AgentState = {
            "session_id": session_id,
            "question": question,
            "sql": "",
            "validated_sql": "",
            "data": [],
            "answer": "",
            "chart_type": None,
            "error": None,
            "retry_count": 0,
            "max_retries": 2
        }

        if self.workflow:
            try:
                return self.workflow.invoke(initial_state)
            except Exception as e:
                logger.error(f"LangGraph invocation error: {e}. Running direct fallback.")

        # Deterministic pipeline runner
        state = generate_sql_node(initial_state)
        while state["retry_count"] <= state["max_retries"]:
            state = validate_sql_node(state)
            if state.get("error"):
                if state["retry_count"] < state["max_retries"]:
                    state = correct_sql_node(state)
                    continue
                else:
                    break

            state = execute_sql_node(state)
            if state.get("error"):
                if state["retry_count"] < state["max_retries"]:
                    state = correct_sql_node(state)
                    continue
                else:
                    break
            break

        state = generate_answer_node(state)
        return state


sql_agent = SQLAgentWorkflow()
