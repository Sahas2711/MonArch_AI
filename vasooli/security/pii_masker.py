"""
PII Masker and Dual Evidence Sanitizer Module.

Provides bidirectional PII masking with character-offset preservation.
Ensures original evidence remains intact for legal audits while sanitizing
sensitive identifiers (PAN, Aadhaar, GSTIN, emails, phones, API keys) before LLM calls.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Dict, List, Tuple


# Indian Specific and Standard Identifier Regexes
PAN_REGEX = r'\b[A-Z]{5}[0-9]{4}[A-Z]\b'
AADHAAR_REGEX = r'\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b'
GSTIN_REGEX = r'\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}\b'
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
API_KEY_REGEX = r'(?:sk-[a-zA-Z0-9]{20,}|gsk_[a-zA-Z0-9]{20,}|AIzaSy[a-zA-Z0-9_-]{33})'
PHONE_REGEX = r'\b(?:\+?91[-.\s]?)?[6-9]\d{9}\b|\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'


@dataclass
class MaskReplacement:
    """Record of a single PII replacement in original text."""
    original: str
    replacement: str
    start_char: int
    end_char: int
    pii_type: str


@dataclass
class MaskedResult:
    """Result containing original text, sanitized text, and replacement map."""
    original_text: str
    sanitized_text: str
    mask_map: List[MaskReplacement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_text": self.original_text,
            "sanitized_text": self.sanitized_text,
            "mask_map": [
                {
                    "original": r.original,
                    "replacement": r.replacement,
                    "start_char": r.start_char,
                    "end_char": r.end_char,
                    "pii_type": r.pii_type,
                }
                for r in self.mask_map
            ],
        }


class PIIMasker:
    """
    Bidirectional PII Masker preserving character-level evidence mapping.
    """

    PATTERNS: List[Tuple[str, str, str]] = [
        (API_KEY_REGEX, "[API_KEY_REDACTED]", "api_key"),
        (GSTIN_REGEX, "[GSTIN_REDACTED]", "gstin"),
        (PAN_REGEX, "[PAN_REDACTED]", "pan"),
        (AADHAAR_REGEX, "[AADHAAR_REDACTED]", "aadhaar"),
        (EMAIL_REGEX, "[EMAIL_REDACTED]", "email"),
        (PHONE_REGEX, "[PHONE_REDACTED]", "phone"),
    ]

    def mask(self, text: str) -> MaskedResult:
        """
        Masks PII patterns in text while preserving start/end character offsets
        and mapping needed to reverse the transformation.
        """
        if not text:
            return MaskedResult(original_text="", sanitized_text="", mask_map=[])

        matches: List[Tuple[int, int, str, str, str]] = []

        # Find all matches for each pattern
        for pattern, replacement, pii_type in self.PATTERNS:
            for m in re.finditer(pattern, text, flags=re.IGNORECASE):
                matches.append((m.start(), m.end(), m.group(0), replacement, pii_type))

        # Sort matches by start character ascending (and longer match first on tie)
        matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

        # Filter out overlapping matches
        filtered_matches: List[Tuple[int, int, str, str, str]] = []
        last_end = -1
        for start, end, orig, rep, pii_type in matches:
            if start >= last_end:
                filtered_matches.append((start, end, orig, rep, pii_type))
                last_end = end

        # Construct sanitized text and mask map
        sanitized_parts: List[str] = []
        mask_map: List[MaskReplacement] = []
        current_pos = 0

        for start, end, orig, rep, pii_type in filtered_matches:
            sanitized_parts.append(text[current_pos:start])
            sanitized_parts.append(rep)
            mask_map.append(
                MaskReplacement(
                    original=orig,
                    replacement=rep,
                    start_char=start,
                    end_char=end,
                    pii_type=pii_type,
                )
            )
            current_pos = end

        sanitized_parts.append(text[current_pos:])
        sanitized_text = "".join(sanitized_parts)

        return MaskedResult(
            original_text=text,
            sanitized_text=sanitized_text,
            mask_map=mask_map,
        )

    def unmask(self, sanitized_text: str, mask_map: List[MaskReplacement]) -> str:
        """
        Reverses the sanitization using the recorded mask_map.
        """
        result = sanitized_text
        for item in reversed(mask_map):
            result = result.replace(item.replacement, item.original, 1)
        return result
