"""
Prompt Injection and Input Security Guard.

Integrates InputSanitizer and PIIMasker to provide robust multi-layer defense.
Preserves original evidence while sanitizing inputs for LLMs and flagging threats.
"""

from typing import Optional, Tuple
from vasooli.domain.errors import PromptInjectionError
from vasooli.security.input_sanitizer import InputSanitizer, SanitizationResult
from vasooli.security.pii_masker import MaskedResult, PIIMasker


class PromptGuard:
    """
    Validates user text inputs for safety, injection vectors, and PII masking.
    """

    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.pii_masker = PIIMasker()

    def check_injection(self, text: str) -> Tuple[bool, Optional[str]]:
        """Checks for prompt injection patterns using multi-layer sanitizer."""
        res = self.sanitizer.sanitize(text)
        if res.has_injection_risk:
            first_flag = res.suspicious_fragments[0]
            return True, f"Blocked prompt injection pattern: '{first_flag.matched_text}'"
        return False, None

    def mask_pii(self, text: str) -> str:
        """Masks emails, phone numbers, PAN, GSTIN, Aadhaar, and API keys."""
        masked_res = self.pii_masker.mask(text)
        return masked_res.sanitized_text

    def mask_pii_with_map(self, text: str) -> MaskedResult:
        """Returns MaskedResult containing sanitized text and reversible mask map."""
        return self.pii_masker.mask(text)

    def validate_and_sanitize(
        self,
        text: str,
        mask_personal_data: bool = True,
        raise_on_injection: bool = True,
    ) -> Tuple[str, SanitizationResult, Optional[MaskedResult]]:
        """
        Validates input safety. Returns clean sanitized text, sanitization result, and mask result.
        """
        san_res = self.sanitizer.sanitize(text)
        if san_res.has_injection_risk and raise_on_injection:
            first_flag = san_res.suspicious_fragments[0]
            raise PromptInjectionError(f"Prompt injection detected: '{first_flag.matched_text}'")

        processed_text = san_res.clean_text
        masked_res: Optional[MaskedResult] = None
        if mask_personal_data:
            masked_res = self.pii_masker.mask(processed_text)
            processed_text = masked_res.sanitized_text

        return processed_text, san_res, masked_res
