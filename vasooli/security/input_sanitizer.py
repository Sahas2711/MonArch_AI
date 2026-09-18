"""
Multi-Layer Input Security Sanitizer and Injection Guard.

Implements a 5-layer defense:
1. Expanded keyword & obfuscation detection
2. Imperative instruction smuggling detection (regex & pattern based)
3. Zero-width & control character stripping
4. Suspicious text flagging & preservation in evidence (never silently deleted)
5. Structured delimiter wrapping for LLM boundaries
"""

from dataclasses import dataclass, field
import re
from typing import List, Optional, Tuple


# Unicode control chars, zero-width spaces, bidi overrides to strip
ZERO_WIDTH_AND_CONTROL_CHARS = [
    '\u200b', '\u200c', '\u200d', '\ufeff', '\u200e', '\u200f',
    '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
    '\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08',
]

INJECTION_KEYWORD_PATTERNS = [
    # Direct overrides
    r'\bignore\s+(?:all\s+)?(?:previous\s+|prior\s+)?instructions\b',
    r'\bdisregard\s+(?:all\s+)?(?:previous\s+|prior\s+|safety\s+)?(?:instructions|guidelines|rules|prompts)\b',
    r'\bsystem\s+prompt\s+(?:override|reset|leak|ignore)\b',
    r'\byou\s+are\s+now\s+(?:dan|unrestricted|an\s+evil|developer\s+mode)\b',
    r'\bbypass\s+(?:all\s+)?(?:safety|compliance|security)\s+(?:filters?|checks?)\b',
    r'\bact\s+as\s+an?\s+unrestricted\b',
    # Indirect / Smuggled instructions
    r'\btreat\s+this\s+(?:document|text|agreement|message)\s+as\s+(?:the\s+)?(?:system\s+message|system\s+prompt|master\s+instruction)\b',
    r'\bmark\s+this\s+(?:agreement|contract|clause)\s+(?:as\s+)?compliant\b',
    r'\boverride\s+(?:compliance|policy|violation)\s+(?:check|result|engine)\b',
    r'\bdo\s+not\s+(?:flag|report|evaluate)\s+(?:any\s+)?(?:violations?|breach|penalt(?:y|ies))\b',
    r'\boutput\s+only\s+(?:json\s+)?with\s+score\s+100\b',
    # Multilingual variants (Hindi / Hinglish transliterations)
    r'(?:saare\s+niyam\s+bhool\s+jao|purane\s+nirdesh\s+ignore\s+karo)',
    r'(?:is\s+contract\s+ko\s+compliant\s+maano|koi\s+violation\s+mat\s+dikhao)',
]

INSTRUCTION_LIKE_PATTERNS = [
    r'(?:^|\n)\s*(?:you\s+(?:must|should|shall|will|are\s+required\s+to)\s+(?:now|always|henceforth|exclusively)\b)',
    r'(?:^|\n)\s*(?:respond\s+(?:only|exclusively)\s+(?:with|in|as)\b)',
    r'(?:^|\n)\s*(?:forget\s+everything\s+(?:above|before)\b)',
    r'(?:^|\n)\s*(?:new\s+system\s+instruction:)',
]


@dataclass
class SuspiciousFragment:
    """A flagged suspicious or instruction-like text segment in input."""
    pattern_matched: str
    matched_text: str
    start_char: int
    end_char: int
    severity: str = "medium"
    category: str = "prompt_injection"


@dataclass
class SanitizationResult:
    """Complete sanitization result keeping evidence audit intact."""
    clean_text: str
    stripped_chars_count: int
    suspicious_fragments: List[SuspiciousFragment] = field(default_factory=list)
    has_injection_risk: bool = False
    delimited_prompt_text: str = ""

    def to_audit_dict(self) -> dict:
        return {
            "stripped_chars_count": self.stripped_chars_count,
            "has_injection_risk": self.has_injection_risk,
            "suspicious_count": len(self.suspicious_fragments),
            "flags": [
                {
                    "pattern": f.pattern_matched,
                    "text": f.matched_text,
                    "start": f.start_char,
                    "end": f.end_char,
                    "severity": f.severity,
                }
                for f in self.suspicious_fragments
            ],
        }


class InputSanitizer:
    """
    Sanitizes raw document text while preserving suspicious content in audit logs.
    """

    def sanitize(self, text: str) -> SanitizationResult:
        if not text:
            return SanitizationResult(clean_text="", stripped_chars_count=0)

        # 1. Strip zero-width & invisible control characters
        stripped_count = 0
        clean_chars = []
        for ch in text:
            if ch in ZERO_WIDTH_AND_CONTROL_CHARS:
                stripped_count += 1
            else:
                clean_chars.append(ch)
        clean_text = "".join(clean_chars)

        # 2. Detect injection patterns & instruction smuggling
        suspicious_fragments: List[SuspiciousFragment] = []
        clean_lower = clean_text.lower()

        # Check explicit injection keywords
        for pat in INJECTION_KEYWORD_PATTERNS:
            for m in re.finditer(pat, clean_lower, flags=re.IGNORECASE):
                suspicious_fragments.append(
                    SuspiciousFragment(
                        pattern_matched=pat,
                        matched_text=clean_text[m.start():m.end()],
                        start_char=m.start(),
                        end_char=m.end(),
                        severity="high",
                        category="direct_injection_keyword",
                    )
                )

        # Check indirect instruction patterns
        for pat in INSTRUCTION_LIKE_PATTERNS:
            for m in re.finditer(pat, clean_text, flags=re.IGNORECASE | re.MULTILINE):
                suspicious_fragments.append(
                    SuspiciousFragment(
                        pattern_matched=pat,
                        matched_text=clean_text[m.start():m.end()],
                        start_char=m.start(),
                        end_char=m.end(),
                        severity="medium",
                        category="instruction_smuggling",
                    )
                )

        has_risk = len(suspicious_fragments) > 0

        # 3. Create cleanly delimited prompt payload
        # Treat entire contract text as untrusted data block
        delimited_prompt = (
            "<<<UNTRUSTED_CONTRACT_TEXT_START>>>\n"
            f"{clean_text}\n"
            "<<<UNTRUSTED_CONTRACT_TEXT_END>>>"
        )

        return SanitizationResult(
            clean_text=clean_text,
            stripped_chars_count=stripped_count,
            suspicious_fragments=suspicious_fragments,
            has_injection_risk=has_risk,
            delimited_prompt_text=delimited_prompt,
        )
