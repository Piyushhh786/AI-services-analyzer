from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from app.core.logging import logger


def log_retry_attempt(retry_state):
    logger.warning(
        f"Retrying {retry_state.fn.__name__} due to {retry_state.outcome.exception()} (attempt {retry_state.attempt_number})"
    )


# Retry decorator for external API calls like Groq or MCP
network_retry = retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
    before_sleep=log_retry_attempt
)
