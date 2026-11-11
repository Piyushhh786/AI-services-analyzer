from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.session.manager import SessionManager
from app.services.analytics_service import AnalyticsService
from app.core.exceptions import AppException

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("")
def get_analytics(
    session_id: str = Query(..., description="Active session ID"),
    time_range: Optional[str] = Query("all", description="Time filter: 7d, 30d, 90d, 180d, all"),
    category: Optional[str] = Query(None, description="Category filter (Food, Travel, etc.)"),
    type: Optional[str] = Query(None, description="Transaction type filter (DEBIT, CREDIT, ALL)"),
    merchant: Optional[str] = Query(None, description="Merchant search term"),
    start_date: Optional[str] = Query(None, description="Custom start date YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="Custom end date YYYY-MM-DD")
):
    try:
        # Validate that session exists and is active
        SessionManager.validate_session(session_id)

        data = AnalyticsService.get_spending_analytics(
            session_id=session_id,
            time_range=time_range,
            category=category,
            tx_type=type,
            merchant_search=merchant,
            start_date=start_date,
            end_date=end_date
        )
        return data

    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics: {str(e)}")
