import asyncio
from app.database.repository import repository
from app.core.config import settings
from app.core.logging import logger

stop_cleanup_event = asyncio.Event()


async def start_cleanup_scheduler():
    """
    Periodically cleans up expired sessions and their associated transactions.
    """
    logger.info(f"Session cleanup scheduler started (runs every {settings.CLEANUP_INTERVAL_MINUTES} minutes).")
    try:
        while not stop_cleanup_event.is_set():
            try:
                await asyncio.wait_for(stop_cleanup_event.wait(), timeout=settings.CLEANUP_INTERVAL_MINUTES * 60)
                break
            except asyncio.TimeoutError:
                pass

            try:
                removed = repository.clean_expired_sessions()
                if removed > 0:
                    logger.info(f"Cleanup scheduler removed {removed} expired session(s).")
            except Exception as e:
                logger.error(f"Error during expired session cleanup: {e}")
    except (asyncio.CancelledError, Exception):
        pass
    logger.info("Session cleanup scheduler task finished.")
