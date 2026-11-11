import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api import upload, chat, session, analytics
from app.session.cleanup import start_cleanup_scheduler, stop_cleanup_event
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_task = None
    if settings.APP_ENV != "test":
        try:
            cleanup_task = asyncio.create_task(start_cleanup_scheduler())
            logger.info("Transaction Analyzer AI Service started successfully.")
        except Exception as e:
            logger.warning(f"Could not start background cleanup scheduler: {e}")
    try:
        yield
    finally:
        if cleanup_task:
            stop_cleanup_event.set()
            cleanup_task.cancel()
            try:
                await asyncio.wait_for(cleanup_task, timeout=0.5)
            except Exception:
                pass
            logger.info("Transaction Analyzer AI Service shut down cleanly.")


app = FastAPI(
    title="Transaction Analyzer AI Service",
    description="Session-based transaction analytics, Groq NL-to-SQL, and LangGraph workflow",
    version="1.0.0",
    lifespan=lifespan
)

# Explicit allowed origins and regex for frontend local and production environments
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers ensuring clean JSON responses with CORS headers intact
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Include API Routers
app.include_router(upload.router)
app.include_router(chat.router)
app.include_router(session.router)
app.include_router(analytics.router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Transaction Analyzer AI Service",
        "version": "1.0.0",
        "app_env": settings.APP_ENV
    }


@app.get("/")
def root():
    return {
        "name": "Transaction Analyzer AI Service",
        "docs": "/docs",
        "health": "/health"
    }
