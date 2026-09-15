"""
MSME Clause Extraction Module.

Extracts structured contractual terms (payment duration, interest penalty,
cancellation terms, buyer type, contract value) using rule-based/regex
parsing with LLM enhancement capability and confidence calibration.
Populates character offsets, estimated page numbers, and clause/section references.
"""

from typing import Any, Dict, List, Optional
import re
from pydantic import BaseModel, Field
from utils.logger import log


class ExtractedClause(BaseModel):
    """Structured representation of a parsed contract clause."""
    clause_id: str = Field(..., description="Unique clause identifier")
    clause_type: str = Field(
        ...,
        description="payment_terms | interest_penalty | cancellation | dispute_resolution | tax_compliance | general"
    )
    raw_text: str = Field(..., description="Exact textual excerpt from the contract")
    payment_days: Optional[int] = Field(None, description="Extracted payment cycle in calendar days")
    has_penalty_interest: Optional[bool] = Field(None, description="Whether contract provides statutory/penalty interest on delayed payments")
    has_unilateral_cancellation: Optional[bool] = Field(None, description="Whether contract permits unilateral buyer cancellation")
    interest_rate_percent: Optional[float] = Field(None, description="Explicitly specified interest rate if any")
    contract_value: Optional[float] = Field(None, description="Contract or order value in INR")
    buyer_type: str = Field("large_enterprise", description="Buyer category (large_enterprise | public_sector | msme)")
    confidence: float = Field(0.85, ge=0.0, le=1.0, description="Extraction confidence score")
    extraction_method: str = Field("regex", description="regex | llm | hybrid")
    start_char: Optional[int] = Field(None, description="Start character offset in source text")
    end_char: Optional[int] = Field(None, description="End character offset in source text")
    page_number: Optional[int] = Field(None, description="Estimated page number")
    clause_reference: Optional[str] = Field(None, description="Clause/section reference identifier")


# Word to number mapping for Indian commercial contract terminology
WORD_TO_DAYS: Dict[str, int] = {
    "fifteen": 15,
    "thirty": 30,
    "forty five": 45,
    "forty-five": 45,
    "sixty": 60,
    "seventy five": 75,
    "seventy-five": 75,
    "ninety": 90,
    "one hundred twenty": 120,
    "one hundred and twenty": 120,
    "one hundred eighty": 180,
}

CLAUSE_REF_PATTERN = r'(?:clause|section|article|§)\s*(\d+(?:\.\d+)*)'


def find_clause_reference(text: str, start_char: Optional[int], end_char: Optional[int]) -> Optional[str]:
    """Finds nearest contract clause/section numbering (e.g. §14.2, Clause 7.1)."""
    if start_char is None:
        m = re.search(CLAUSE_REF_PATTERN, text[:500], re.IGNORECASE)
        return m.group(0).strip() if m else None

    # Search in window around the match
    window_start = max(0, start_char - 150)
    window_end = min(len(text), (end_char or start_char) + 50)
    window = text[window_start:window_end]
    m = re.search(CLAUSE_REF_PATTERN, window, re.IGNORECASE)
    if m:
        return m.group(0).strip()
    return None


def estimate_page_number(start_char: Optional[int], avg_chars_per_page: int = 3000) -> int:
    """Estimates 1-based page number from character offset."""
    if start_char is None:
        return 1
    return (start_char // avg_chars_per_page) + 1


class ClauseExtractor:
    """
    Extracts MSME payment terms and statutory compliance triggers
    from raw legal contract text.
    """

    def __init__(self, use_llm_fallback: bool = False):
        self.use_llm_fallback = use_llm_fallback

    def extract_from_text(
        self,
        text: str,
        buyer_name: Optional[str] = None,
        contract_value: Optional[float] = None,
    ) -> List[ExtractedClause]:
        """
        Extracts structured clauses from raw contract text.
        Returns a list of ExtractedClause objects.
        """
        if not text or not text.strip():
            return []

        text_lower = text.lower()
        clauses: List[ExtractedClause] = []

        # 1. Extract Payment Terms Clause
        payment_clause = self._extract_payment_terms(text, text_lower, contract_value)
        if payment_clause:
            clauses.append(payment_clause)

        # 2. Extract Interest Penalty Clause
        interest_clause = self._extract_interest_terms(text, text_lower)
        if interest_clause:
            clauses.append(interest_clause)

        # 3. Extract Cancellation Clause
        cancel_clause = self._extract_cancellation_terms(text, text_lower)
        if cancel_clause:
            clauses.append(cancel_clause)

        # 4. If no specific clauses parsed, create a general fallback clause
        if not clauses:
            clauses.append(
                ExtractedClause(
                    clause_id="clause_general_1",
                    clause_type="general",
                    raw_text=text[:500],
                    payment_days=30,
                    has_penalty_interest=True,
                    has_unilateral_cancellation=False,
                    contract_value=contract_value,
                    confidence=0.50,
                    extraction_method="fallback",
                    start_char=0,
                    end_char=min(len(text), 500),
                    page_number=1,
                    clause_reference=find_clause_reference(text, 0, 500),
                )
            )

        log.info("ClauseExtractor parsed %d clauses from text (length %d)", len(clauses), len(text))
        return clauses

    def _extract_payment_terms(
        self,
        text: str,
        text_lower: str,
        contract_value: Optional[float] = None
    ) -> Optional[ExtractedClause]:
        """Extracts payment days and terms from text."""
        payment_days: Optional[int] = None
        confidence = 0.50
        method = "regex"
        matched_text = ""
        start_char: Optional[int] = None
        end_char: Optional[int] = None

        # Check explicit numeric payment days patterns
        patterns = [
            r'(?:within|in|net|after|before)\s+(\d{1,3})\s*(?:calendar\s+|business\s+|working\s+)?(?:days|day)',
            r'payment\s+(?:terms?|period|schedule|timeline|cycle)?\s*(?:is|shall\s+be|of|:)?\s*(\d{1,3})\s*days',
            r'(\d{1,3})\s*(?:days|day)\s+(?:from|after|of)\s+(?:the\s+date\s+of\s+)?(?:invoice|delivery|acceptance|receipt|bill)',
            r'net\s*[-:\s]?\s*(\d{1,3})\b',
            r'credit\s+period\s*(?:of|is|:)?\s*(\d{1,3})\s*days',
        ]

        for pat in patterns:
            match = re.search(pat, text_lower)
            if match:
                val = int(match.group(1))
                if 1 <= val <= 365:
                    payment_days = val
                    confidence = 0.95
                    start_char = match.start()
                    end_char = match.end()
                    start = max(0, match.start() - 30)
                    end = min(len(text), match.end() + 50)
                    matched_text = text[start:end].strip()
                    break

        # Check word-based payment days if no numeric match
        if payment_days is None:
            for word, days in WORD_TO_DAYS.items():
                if word in text_lower and ("day" in text_lower or "payment" in text_lower or "invoice" in text_lower):
                    payment_days = days
                    confidence = 0.85
                    idx = text_lower.find(word)
                    start_char = idx
                    end_char = idx + len(word)
                    start = max(0, idx - 30)
                    end = min(len(text), idx + len(word) + 40)
                    matched_text = text[start:end].strip()
                    break

        # Check payment trigger keywords without explicit days
        if payment_days is None:
            if "immediate" in text_lower or "advance" in text_lower:
                payment_days = 0
                confidence = 0.80
                matched_text = "Advance/Immediate payment term"
                idx = text_lower.find("advance") if "advance" in text_lower else text_lower.find("immediate")
                start_char = idx if idx != -1 else 0
                end_char = start_char + 10
            elif "month" in text_lower and ("end of" in text_lower or "next month" in text_lower):
                payment_days = 45
                confidence = 0.65
                matched_text = "Monthly settlement term"
                idx = text_lower.find("month")
                start_char = idx if idx != -1 else 0
                end_char = start_char + 15

        if payment_days is not None or "payment" in text_lower or "invoice" in text_lower:
            clause_ref = find_clause_reference(text, start_char, end_char)
            page_num = estimate_page_number(start_char)
            return ExtractedClause(
                clause_id="clause_payment_1",
                clause_type="payment_terms",
                raw_text=matched_text or text[:300],
                payment_days=payment_days if payment_days is not None else 30,
                has_penalty_interest=None,
                has_unilateral_cancellation=None,
                contract_value=contract_value,
                confidence=confidence,
                extraction_method=method,
                start_char=start_char,
                end_char=end_char,
                page_number=page_num,
                clause_reference=clause_ref,
            )

        return None

    def _extract_interest_terms(self, text: str, text_lower: str) -> Optional[ExtractedClause]:
        """Extracts penalty and interest rate clauses."""
        has_penalty_interest: Optional[bool] = None
        confidence = 0.50
        matched_text = ""
        start_char: Optional[int] = None
        end_char: Optional[int] = None

        # Negative penalty interest patterns (waived or disallowed)
        no_interest_patterns = [
            r'no\s+interest\s+(?:shall|will|is|may)?\s*(?:accrue|be\s+payable|be\s+paid|be\s+claimed)',
            r'without\s+(?:any\s+)?interest',
            r'waive(?:s)?\s+(?:all\s+|any\s+)?(?:right\s+to\s+)?interest',
            r'interest\s*[-:\s]?\s*free',
            r'no\s+penalty\s+or\s+interest',
            r'interest\s+shall\s+not\s+be\s+applicable',
            r'no\s+claim\s+for\s+interest',
        ]

        for pat in no_interest_patterns:
            match = re.search(pat, text_lower)
            if match:
                has_penalty_interest = False
                confidence = 0.95
                start_char = match.start()
                end_char = match.end()
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 40)
                matched_text = text[start:end].strip()
                break

        # Positive statutory interest patterns (statutory compliant)
        if has_penalty_interest is None:
            positive_patterns = [
                r'3x\s+rbi',
                r'three\s+times\s+the\s+bank\s+rate',
                r'compound\s+interest\s+with\s+monthly\s+rests',
                r'section\s+16\s+of\s+(?:the\s+)?msme',
                r'interest\s+at\s+(\d+(?:\.\d+)?)\s*%\s+per\s+month',
            ]
            for pat in positive_patterns:
                match = re.search(pat, text_lower)
                if match:
                    has_penalty_interest = True
                    confidence = 0.90
                    start_char = match.start()
                    end_char = match.end()
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 40)
                    matched_text = text[start:end].strip()
                    break

        if has_penalty_interest is not None or "interest" in text_lower:
            clause_ref = find_clause_reference(text, start_char, end_char)
            page_num = estimate_page_number(start_char)
            return ExtractedClause(
                clause_id="clause_interest_1",
                clause_type="interest_penalty",
                raw_text=matched_text or "Interest terms clause",
                payment_days=None,
                has_penalty_interest=has_penalty_interest if has_penalty_interest is not None else True,
                has_unilateral_cancellation=None,
                confidence=confidence,
                extraction_method="regex",
                start_char=start_char,
                end_char=end_char,
                page_number=page_num,
                clause_reference=clause_ref,
            )

        return None

    def _extract_cancellation_terms(self, text: str, text_lower: str) -> Optional[ExtractedClause]:
        """Extracts unilateral cancellation clauses."""
        has_unilateral: Optional[bool] = None
        confidence = 0.50
        matched_text = ""
        start_char: Optional[int] = None
        end_char: Optional[int] = None

        cancellation_patterns = [
            r'cancel\s+(?:the\s+order|this\s+agreement|contract)?\s*without\s+(?:any\s+)?notice',
            r'terminate\s+(?:at\s+any\s+time\s+)?at\s+(?:buyer\'?s?|client\'?s?|purchaser\'?s?)\s+sole\s+discretion',
            r'cancel\s+(?:at\s+any\s+time\s+)?at\s+(?:buyer\'?s?|client\'?s?|purchaser\'?s?|sole\s+)?discretion',
            r'unilateral(?:ly)?\s+(?:cancel|terminate|modify)',
            r'without\s+liability\s+(?:or\s+compensation)?',
            r'sole\s+discretion\s+without\s+(?:assigning\s+any\s+)?reason',
            r'sole\s+discretion',
            r'right\s+to\s+cancel\s+at\s+any\s+time',
        ]

        for pat in cancellation_patterns:
            match = re.search(pat, text_lower)
            if match:
                has_unilateral = True
                confidence = 0.92
                start_char = match.start()
                end_char = match.end()
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 40)
                matched_text = text[start:end].strip()
                break

        if has_unilateral is not None or "cancel" in text_lower or "terminate" in text_lower:
            clause_ref = find_clause_reference(text, start_char, end_char)
            page_num = estimate_page_number(start_char)
            return ExtractedClause(
                clause_id="clause_cancel_1",
                clause_type="cancellation",
                raw_text=matched_text or "Cancellation terms clause",
                payment_days=None,
                has_penalty_interest=None,
                has_unilateral_cancellation=has_unilateral if has_unilateral is not None else False,
                confidence=confidence,
                extraction_method="regex",
                start_char=start_char,
                end_char=end_char,
                page_number=page_num,
                clause_reference=clause_ref,
            )

        return None
