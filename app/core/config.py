import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Automatically locate .env in ai-service/ or workspace root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_paths = [
    BASE_DIR / ".env",
    BASE_DIR.parent / ".env",
    Path(".env")
]

for p in env_paths:
    if p.exists():
        load_dotenv(dotenv_path=p, override=False)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(p) for p in env_paths if p.exists()] or ".env",
        extra="ignore"
    )

    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    DATABASE_URL: Optional[str] = "postgresql://neondb_owner:npg_svjMH6Vl2cWb@ep-rough-fire-b3jz45fd-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

    POSTGRES_MCP_URL: Optional[str] = None
    MCP_API_KEY: Optional[str] = None

    SESSION_TTL_MINUTES: int = 30
    MAX_UPLOAD_SIZE_MB: int = 10
    CLEANUP_INTERVAL_MINUTES: int = 10


settings = Settings()
