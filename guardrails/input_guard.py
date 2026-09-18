"""
Input Guardrail for Monarch.

Sanitizes user input, masks sensitive PII (Emails, API Keys, Credit Cards, Phones),
and detects prompt injection or malicious override attempts.
"""

import re
from typing import Dict, Tuple
from utils.logger import log

# Common PII Regex Patterns
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
API_KEY_REGEX = r'(?:sk-[a-zA-Z0-9]{20,}|gsk_[a-zA-Z0-9]{20,}|AIzaSy[a-zA-Z0-9_-]{33})'
PHONE_REGEX = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
CREDIT_CARD_REGEX = r'\b(?:\d[ -]*?){13,16}\b'

# Common Injection Patterns
INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard safety guidelines",
    "system prompt override",
    "you are now DAN",
    "bypass safety filters",
]


def sanitize_and_validate_input(user_inp: str) -> Tuple[str, bool, str]:
    """
    Sanitizes user prompt, masks PII, and checks for prompt injection.
    
    Returns:
      (sanitized_text, is_safe, reason)
    """
    if not user_inp or not user_inp.strip():
        return user_inp, True, "Empty input"

    query_lower = user_inp.lower()

    # 1. Prompt Injection Detection
    for pattern in INJECTION_KEYWORDS:
        if pattern in query_lower:
            log.warning("Prompt injection pattern detected in input: %r", pattern)
            return user_inp, False, f"Input blocked due to restricted system override phrase: '{pattern}'"

    # 2. PII Masking
    sanitized = user_inp
    sanitized = re.sub(EMAIL_REGEX, "[REDACTED_EMAIL]", sanitized)
    sanitized = re.sub(API_KEY_REGEX, "[REDACTED_API_KEY]", sanitized)
    sanitized = re.sub(PHONE_REGEX, "[REDACTED_PHONE]", sanitized)
    sanitized = re.sub(CREDIT_CARD_REGEX, "[REDACTED_CARD]", sanitized)

    if sanitized != user_inp:
        log.info("PII masking applied to user input.")

    return sanitized, True, "Passed input guardrails"
