from typing import Optional, Any
from app.core.config import settings
from app.core.logging import logger

try:
    from langchain_groq import ChatGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class GroqClient:
    def __init__(self):
        self.client: Optional[Any] = None
        self.is_active = False
        self._initialize()

    def _initialize(self):
        if settings.GROQ_API_KEY and GROQ_AVAILABLE:
            try:
                model_name = settings.GROQ_MODEL or "openai/gpt-oss-120b"
                if model_name.startswith("gpt-oss-"):
                    model_name = f"openai/{model_name}"

                self.client = ChatGroq(
                    api_key=settings.GROQ_API_KEY,
                    model_name=model_name,
                    temperature=0.2,
                    max_tokens=1024
                )
                self.is_active = True
                logger.info(f"Initialized Groq LLM with model: {model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")
                self.is_active = False
        else:
            logger.info("GROQ_API_KEY not configured. Running in built-in heuristic NL-to-SQL mode.")
            self.is_active = False

    def get_llm(self):
        return self.client


groq_client = GroqClient()
