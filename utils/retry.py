from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

RETRYABLE_EXC = (TimeoutError, ConnectionError, OSError)


def llm_retry():
    """Shared retry policy for external LLM/API calls."""
    return retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type(RETRYABLE_EXC),
    )
