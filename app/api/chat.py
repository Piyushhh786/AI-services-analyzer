from fastapi import APIRouter, HTTPException
from app.session.manager import SessionManager
from app.agents.graph import sql_agent
from app.schemas.chat import ChatRequest, ChatResponse
from app.core.exceptions import AppException
from app.core.logging import logger

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
def ask_question(req: ChatRequest):
    try:
        # Verify session is valid
        SessionManager.validate_session(req.session_id)

        # Run AI LangGraph workflow
        result = sql_agent.run(session_id=req.session_id, question=req.message)

        return ChatResponse(
            session_id=req.session_id,
            message=req.message,
            answer=result.get("answer") or "I could not generate an answer.",
            sql=result.get("validated_sql") or result.get("sql") if req.include_sql else None,
            data=result.get("data"),
            chart_type=result.get("chart_type"),
            error=result.get("error")
        )

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")
