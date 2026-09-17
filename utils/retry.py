import time
import functools
from utils.logger import log


def llm_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator that retries an LLM call on transient failures with exponential backoff."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt < max_retries:
                        wait = delay * (2 ** (attempt - 1))
                        log.warning(
                            "Attempt %d/%d for %s failed (%s). Retrying in %.1fs...",
                            attempt,
                            max_retries,
                            func.__name__,
                            exc,
                            wait,
                        )
                        time.sleep(wait)
                    else:
                        log.error(
                            "All %d attempts for %s failed. Last error: %s",
                            max_retries,
                            func.__name__,
                            exc,
                        )
            raise last_exc

        return wrapper

    return decorator
