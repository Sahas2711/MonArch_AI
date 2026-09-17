import re
from utils.logger import log


# Patterns that indicate potentially malicious or unsafe input
_BLOCKED_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)you\s+are\s+now\s+",
    r"(?i)system\s*:\s*",
    r"(?i)act\s+as\s+",
    r"(?i)pretend\s+you\s+are",
    r"(?i)disregard\s+",
    r"<script[^>]*>",
    r"javascript:",
    r"(?i)drop\s+table",
    r"(?i)delete\s+from",
    r"(?i)exec\s*\(",
    r"(?i)eval\s*\(",
]

_MAX_INPUT_LENGTH = 10000


def sanitize_and_validate_input(raw_input: str) -> tuple[str, bool, str]:
    """
    Sanitize and validate user input.

    Returns:
        (sanitized_input, is_safe, reason)
        - sanitized_input: cleaned version of the input
        - is_safe: True if input passed all checks
        - reason: explanation if blocked, empty string otherwise
    """
    if not raw_input or not raw_input.strip():
        return "", False, "Empty input provided."

    text = raw_input.strip()

    # Length check
    if len(text) > _MAX_INPUT_LENGTH:
        return text[:_MAX_INPUT_LENGTH], False, f"Input exceeds maximum length of {_MAX_INPUT_LENGTH} characters."

    # Pattern-based injection detection
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, text):
            log.warning("Input blocked by guardrail pattern: %s", pattern)
            return text, False, "Input contains potentially unsafe content."

    # Basic sanitization: strip null bytes and control characters
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    return sanitized, True, ""
