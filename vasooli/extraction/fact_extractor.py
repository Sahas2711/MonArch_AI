"""
Vasooli Fact Extractor Module.

Extracts structured contractual facts from contract text with exact evidence anchors.

KEY ARCHITECTURAL RULE:
    Facts describe WHAT the contract says, not WHETHER it violates the law.
    The determination of violation belongs exclusively to the Policy Engine.

Hierarchy:
    Source Text → EvidenceItem → ExtractedFact
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from vasooli.domain.enums import (
    ExtractionMethod,
    FactStatus,
    FactType,
    PaymentBasis,
)
from vasooli.domain.models import (
    CancellationClauseValue,
    EvidenceItem,
    ExtractedFact,
    InterestClauseValue,
    PaymentTermValue,
)
from vasooli.extraction.date_resolver import (
    detect_ambiguous_payment,
    resolve_payment_basis,
)


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


class FactExtractor:
    """
    Deterministic, rule-based extractor producing source-anchored ExtractedFact objects.
    """

    EXTRACTOR_VERSION = "fact-extractor-2.0.0"

    def __init__(self, chars_per_page: int = 3000):
        self.chars_per_page = chars_per_page

    def extract_facts(
        self,
        document_text: str,
        document_id: str = "DOC-DEFAULT",
        contract_value: Optional[float] = None,
        buyer_type: Optional[str] = None,
    ) -> List[ExtractedFact]:
        """
        Extracts all structured contractual facts from document text.
        """
        if not document_text or not document_text.strip():
            return []

        facts: List[ExtractedFact] = []
        text_lower = document_text.lower()

        # 1. Payment Terms Fact
        payment_fact = self._extract_payment_term_fact(document_text, text_lower, document_id)
        if payment_fact:
            facts.append(payment_fact)

        # 2. Interest Clause Fact
        interest_fact = self._extract_interest_clause_fact(document_text, text_lower, document_id)
        if interest_fact:
            facts.append(interest_fact)

        # 3. Cancellation Clause Fact
        cancellation_fact = self._extract_cancellation_clause_fact(document_text, text_lower, document_id)
        if cancellation_fact:
            facts.append(cancellation_fact)

        # 4. Dispute Resolution Fact
        dispute_fact = self._extract_dispute_clause_fact(document_text, text_lower, document_id)
        if dispute_fact:
            facts.append(dispute_fact)

        # 5. Contract Value / Metadata Fact (if provided or found in text)
        meta_fact = self._extract_metadata_fact(document_text, text_lower, document_id, contract_value, buyer_type)
        if meta_fact:
            facts.append(meta_fact)

        return facts

    def _find_clause_ref(self, text: str, start_char: int, end_char: int) -> Optional[str]:
        """Locates clause numbering in the vicinity of the character offsets."""
        window_start = max(0, start_char - 150)
        window_end = min(len(text), end_char + 50)
        window = text[window_start:window_end]
        m = re.search(CLAUSE_REF_PATTERN, window, re.IGNORECASE)
        return m.group(0).strip() if m else None

    def _calc_page(self, start_char: int) -> int:
        return (start_char // self.chars_per_page) + 1

    def _extract_payment_term_fact(
        self, text: str, text_lower: str, doc_id: str
    ) -> Optional[ExtractedFact]:
        """
        Extracts payment duration, payment start trigger, and ambiguity status.
        """
        payment_days: Optional[int] = None
        start_char: int = 0
        end_char: int = 0
        matched_tokens: List[str] = []
        confidence = 0.50

        patterns = [
            (r'(?:within|in|net|after|before)\s+(\d{1,3})\s*(?:calendar\s+|business\s+|working\s+)?(?:days|day)', "numeric_period"),
            (r'payment\s+(?:terms?|period|schedule|timeline|cycle)?\s*(?:is|shall\s+be|of|:)?\s*(\d{1,3})\s*days', "payment_schedule"),
            (r'(\d{1,3})\s*(?:calendar\s+|business\s+|working\s+)?(?:days|day)\s+(?:from|after|of)\s+(?:the\s+date\s+of\s+)?(?:invoice|delivery|acceptance|receipt|bill|consignment)', "days_after_event"),
            (r'credit\s+(?:period|terms?)[^.\n]{0,80}?(?:is|shall\s+be|of|:)?\s*(\d{1,3})\s*days', "credit_period"),
            (r'net\s*[-:\s]?\s*(\d{1,3})\b', "net_days"),
            (r'(\d{1,3})\s*days\s+credit', "days_credit"),
        ]

        for pat, tag in patterns:
            match = re.search(pat, text_lower)
            if match:
                val = int(match.group(1))
                if 1 <= val <= 365:
                    payment_days = val
                    start_char = match.start()
                    end_char = match.end()
                    matched_tokens = [match.group(0), tag]
                    confidence = 0.95
                    break

        if payment_days is None:
            # Sort by longest phrase first to match "one hundred twenty" before "twenty"
            sorted_words = sorted(WORD_TO_DAYS.items(), key=lambda x: len(x[0]), reverse=True)
            for word, days in sorted_words:
                if word in text_lower and any(kw in text_lower for kw in ["day", "payment", "invoice", "credit", "terms"]):
                    payment_days = days
                    idx = text_lower.find(word)
                    start_char = idx
                    end_char = idx + len(word)
                    matched_tokens = [word, "word_days"]
                    confidence = 0.85
                    break

        if payment_days is None:
            if "immediate" in text_lower or "advance" in text_lower:
                payment_days = 0
                idx = text_lower.find("advance") if "advance" in text_lower else text_lower.find("immediate")
                start_char = idx if idx != -1 else 0
                end_char = start_char + 9
                matched_tokens = ["advance/immediate"]
                confidence = 0.80
            elif "month" in text_lower and ("end of" in text_lower or "next month" in text_lower):
                payment_days = 45
                idx = text_lower.find("month")
                start_char = idx if idx != -1 else 0
                end_char = start_char + 10
                matched_tokens = ["month_end"]
                confidence = 0.65

        # If no explicit days or triggers found and no mention of payment, return None
        if payment_days is None and not any(kw in text_lower for kw in ["payment", "invoice", "credit period"]):
            return None

        # Resolve payment basis (date trigger)
        window_start = max(0, start_char - 100)
        window_end = min(len(text), end_char + 150)
        surrounding_text = text[window_start:window_end]
        basis, basis_desc, _ = resolve_payment_basis(surrounding_text)

        # Check for ambiguity
        ambiguous_matches = detect_ambiguous_payment(surrounding_text)
        fact_status = FactStatus.DEFINITIVE
        inconclusive_reason = None

        if ambiguous_matches:
            fact_status = FactStatus.AMBIGUOUS
            inconclusive_reason = (
                f"Payment trigger contains ambiguous conditioning: {ambiguous_matches} "
                "The clause conditions payment on events without a defined statutory baseline."
            )
        elif payment_days is None:
            fact_status = FactStatus.INCONCLUSIVE
            inconclusive_reason = "Payment is mentioned but no specific day count or duration was identified."

        evidence_snippet = text[max(0, start_char - 30): min(len(text), end_char + 50)].strip()
        if not evidence_snippet:
            evidence_snippet = text[:200]

        evidence = EvidenceItem(
            evidence_id=f"E-PAY-{uuid.uuid4().hex[:6]}",
            source_document_id=doc_id,
            source_text=evidence_snippet,
            start_char=start_char,
            end_char=end_char if end_char > start_char else start_char + len(evidence_snippet),
            page_number=self._calc_page(start_char),
            clause_reference=self._find_clause_ref(text, start_char, end_char),
            matched_terms=matched_tokens,
            extraction_method="regex",
            extractor_confidence=confidence,
        )

        val = PaymentTermValue(
            days=payment_days,
            basis=basis,
            basis_description=basis_desc,
            has_written_agreement=True,
        )

        return ExtractedFact(
            fact_id=f"FACT-PAY-{uuid.uuid4().hex[:6]}",
            fact_type=FactType.PAYMENT_TERM,
            value=val.dict(),
            evidence=evidence,
            confidence=confidence,
            status=fact_status,
            inconclusive_reason=inconclusive_reason,
            extractor_version=self.EXTRACTOR_VERSION,
            extraction_method=ExtractionMethod.REGEX,
        )

    def _extract_interest_clause_fact(
        self, text: str, text_lower: str, doc_id: str
    ) -> Optional[ExtractedFact]:
        """
        Extracts interest clause facts: whether waived, rate percentage, statutory terms.
        """
        interest_provided: Optional[bool] = None
        interest_waived: Optional[bool] = None
        interest_rate_percent: Optional[float] = None
        statutory_ref: Optional[str] = None
        confidence = 0.50
        start_char: int = 0
        end_char: int = 0
        matched_tokens: List[str] = []

        # 1. Check for explicit interest waiver / denial
        waiver_patterns = [
            r'no\s+interest\s+(?:shall|will|is|may)?\s*(?:accrue|be\s+payable|be\s+paid|be\s+claimed)',
            r'shall\s+interest\s+(?:accrue|be\s+payable|be\s+paid|be\s+claimed)',
            r'without\s+(?:any\s+)?interest',
            r'waive(?:s)?\s+(?:all\s+|any\s+)?(?:right\s+to\s+)?interest',
            r'interest\s*[-:\s]?\s*free',
            r'no\s+penalty\s+or\s+interest',
            r'interest\s+shall\s+not\s+be\s+applicable',
            r'no\s+claim\s+for\s+interest',
            r'not\s+entitled\s+to\s+(?:any\s+)?interest',
        ]
        for pat in waiver_patterns:
            m = re.search(pat, text_lower)
            if m:
                interest_provided = False
                interest_waived = True
                confidence = 0.95
                start_char = m.start()
                end_char = m.end()
                matched_tokens = [m.group(0), "interest_waiver"]
                break

        # 2. Check for explicit statutory / MSMED interest terms
        if interest_provided is None:
            statutory_patterns = [
                (r'3x\s+rbi', "3x RBI rate"),
                (r'three\s+times\s+the\s+bank\s+rate', "3x bank rate"),
                (r'compound\s+interest\s+with\s+monthly\s+rests', "monthly compound rests"),
                (r'section\s+16\s+of\s+(?:the\s+)?msme', "Section 16 MSMED Act"),
            ]
            for pat, desc in statutory_patterns:
                m = re.search(pat, text_lower)
                if m:
                    interest_provided = True
                    interest_waived = False
                    statutory_ref = desc
                    confidence = 0.92
                    start_char = m.start()
                    end_char = m.end()
                    matched_tokens = [m.group(0), "statutory_rate"]
                    break

        # 3. Check for specific numeric interest rate percentage
        rate_match = re.search(r'interest\s+(?:at|of|rate\s+of)?\s*(\d+(?:\.\d+)?)\s*%\s*(?:per\s+annum|p\.a\.|per\s+month)?', text_lower)
        if rate_match:
            try:
                interest_rate_percent = float(rate_match.group(1))
                if interest_provided is None:
                    interest_provided = True
                    interest_waived = False
                    start_char = rate_match.start()
                    end_char = rate_match.end()
                    matched_tokens = [rate_match.group(0), "numeric_interest_rate"]
                    confidence = 0.90
            except ValueError:
                pass

        if interest_provided is None and not any(kw in text_lower for kw in ["interest", "penalty"]):
            return None

        evidence_snippet = text[max(0, start_char - 30): min(len(text), end_char + 50)].strip()
        if not evidence_snippet:
            evidence_snippet = "Interest clause context"

        evidence = EvidenceItem(
            evidence_id=f"E-INT-{uuid.uuid4().hex[:6]}",
            source_document_id=doc_id,
            source_text=evidence_snippet,
            start_char=start_char,
            end_char=end_char if end_char > start_char else start_char + len(evidence_snippet),
            page_number=self._calc_page(start_char),
            clause_reference=self._find_clause_ref(text, start_char, end_char),
            matched_terms=matched_tokens,
            extraction_method="regex",
            extractor_confidence=confidence,
        )

        val = InterestClauseValue(
            interest_provided=interest_provided,
            interest_rate_percent=interest_rate_percent,
            interest_waived=interest_waived,
            statutory_reference=statutory_ref,
        )

        return ExtractedFact(
            fact_id=f"FACT-INT-{uuid.uuid4().hex[:6]}",
            fact_type=FactType.INTEREST_CLAUSE,
            value=val.dict(),
            evidence=evidence,
            confidence=confidence,
            status=FactStatus.DEFINITIVE if interest_provided is not None else FactStatus.INCONCLUSIVE,
            inconclusive_reason=None if interest_provided is not None else "Interest is mentioned but terms are unspecified.",
            extractor_version=self.EXTRACTOR_VERSION,
            extraction_method=ExtractionMethod.REGEX,
        )

    def _extract_cancellation_clause_fact(
        self, text: str, text_lower: str, doc_id: str
    ) -> Optional[ExtractedFact]:
        """
        Extracts cancellation terms: unilateral rights, notice period, compensation.
        """
        is_unilateral: Optional[bool] = None
        notice_period_days: Optional[int] = None
        compensation_required: Optional[bool] = None
        confidence = 0.50
        start_char: int = 0
        end_char: int = 0
        matched_tokens: List[str] = []

        unilateral_patterns = [
            r'cancel\s+(?:the\s+order|this\s+agreement|contract)?\s*without\s+(?:any\s+)?notice',
            r'terminate\s+(?:at\s+any\s+time\s+)?at\s+(?:buyer\'?s?|client\'?s?|purchaser\'?s?)\s+sole\s+discretion',
            r'cancel\s+(?:at\s+any\s+time\s+)?at\s+(?:buyer\'?s?|client\'?s?|purchaser\'?s?|sole\s+)?discretion',
            r'unilateral(?:ly)?\s+(?:cancel|terminate|modify)',
            r'without\s+liability\s+(?:or\s+compensation)?',
            r'sole\s+discretion\s+without\s+(?:assigning\s+any\s+)?reason',
            r'sole\s+discretion',
            r'right\s+to\s+cancel\s+at\s+any\s+time',
        ]
        for pat in unilateral_patterns:
            m = re.search(pat, text_lower)
            if m:
                is_unilateral = True
                confidence = 0.92
                start_char = m.start()
                end_char = m.end()
                matched_tokens = [m.group(0), "unilateral_cancellation"]
                break

        # Check notice period
        notice_m = re.search(r'(\d{1,3})\s*(?:days|day)\s+(?:written\s+)?notice', text_lower)
        if notice_m:
            notice_period_days = int(notice_m.group(1))

        # Check compensation
        if "without compensation" in text_lower or "no compensation" in text_lower or "without liability" in text_lower:
            compensation_required = False
        elif "compensate for work done" in text_lower or "payment for completed milestones" in text_lower:
            compensation_required = True

        if is_unilateral is None and not any(kw in text_lower for kw in ["cancel", "terminate", "termination"]):
            return None

        evidence_snippet = text[max(0, start_char - 30): min(len(text), end_char + 50)].strip()
        if not evidence_snippet:
            evidence_snippet = "Cancellation clause context"

        evidence = EvidenceItem(
            evidence_id=f"E-CAN-{uuid.uuid4().hex[:6]}",
            source_document_id=doc_id,
            source_text=evidence_snippet,
            start_char=start_char,
            end_char=end_char if end_char > start_char else start_char + len(evidence_snippet),
            page_number=self._calc_page(start_char),
            clause_reference=self._find_clause_ref(text, start_char, end_char),
            matched_terms=matched_tokens,
            extraction_method="regex",
            extractor_confidence=confidence,
        )

        val = CancellationClauseValue(
            is_unilateral=is_unilateral if is_unilateral is not None else False,
            notice_period_days=notice_period_days,
            compensation_required=compensation_required,
            cancellation_party="buyer" if is_unilateral else "either",
        )

        return ExtractedFact(
            fact_id=f"FACT-CAN-{uuid.uuid4().hex[:6]}",
            fact_type=FactType.CANCELLATION_CLAUSE,
            value=val.dict(),
            evidence=evidence,
            confidence=confidence,
            status=FactStatus.DEFINITIVE if is_unilateral is not None else FactStatus.INCONCLUSIVE,
            inconclusive_reason=None if is_unilateral is not None else "Termination terms present but unilateral status unclear.",
            extractor_version=self.EXTRACTOR_VERSION,
            extraction_method=ExtractionMethod.REGEX,
        )

    def _extract_dispute_clause_fact(
        self, text: str, text_lower: str, doc_id: str
    ) -> Optional[ExtractedFact]:
        """
        Extracts dispute resolution provisions (MSME Facilitation Council, Arbitration, Jurisdiction).
        """
        has_msefc = "msefc" in text_lower or "facilitation council" in text_lower or "section 18" in text_lower
        has_arbitration = "arbitration" in text_lower or "arbitrator" in text_lower
        
        if not (has_msefc or has_arbitration or "jurisdiction" in text_lower or "dispute" in text_lower):
            return None

        start_char = 0
        end_char = 0
        matched = []
        if has_msefc:
            m = re.search(r'(?:msefc|facilitation\s+council|section\s+18)', text_lower)
            if m:
                start_char, end_char = m.start(), m.end()
                matched.append(m.group(0))
        elif has_arbitration:
            m = re.search(r'arbitration', text_lower)
            if m:
                start_char, end_char = m.start(), m.end()
                matched.append(m.group(0))

        evidence_snippet = text[max(0, start_char - 30): min(len(text), end_char + 60)].strip()
        evidence = EvidenceItem(
            evidence_id=f"E-DISP-{uuid.uuid4().hex[:6]}",
            source_document_id=doc_id,
            source_text=evidence_snippet or text[:200],
            start_char=start_char,
            end_char=end_char if end_char > start_char else len(evidence_snippet),
            page_number=self._calc_page(start_char),
            clause_reference=self._find_clause_ref(text, start_char, end_char),
            matched_terms=matched,
            extraction_method="regex",
            extractor_confidence=0.85,
        )

        return ExtractedFact(
            fact_id=f"FACT-DISP-{uuid.uuid4().hex[:6]}",
            fact_type=FactType.DISPUTE_RESOLUTION,
            value={
                "has_msefc_reference": has_msefc,
                "has_arbitration": has_arbitration,
                "overrides_statutory_council": has_arbitration and not has_msefc,
            },
            evidence=evidence,
            confidence=0.85,
            status=FactStatus.DEFINITIVE,
            extractor_version=self.EXTRACTOR_VERSION,
            extraction_method=ExtractionMethod.REGEX,
        )

    def _extract_metadata_fact(
        self,
        text: str,
        text_lower: str,
        doc_id: str,
        contract_value: Optional[float] = None,
        buyer_type: Optional[str] = None,
    ) -> Optional[ExtractedFact]:
        """
        Extracts contract metadata like value, buyer type, currency.
        """
        val_amount = contract_value
        if val_amount is None:
            # Try to find currency amount in text (e.g., INR 5,00,000 or Rs. 10,00,000)
            cur_match = re.search(r'(?:inr|rs\.?|₹)\s*([\d,]+(?:\.\d{2})?)', text_lower)
            if cur_match:
                try:
                    cleaned_num = cur_match.group(1).replace(",", "")
                    val_amount = float(cleaned_num)
                except ValueError:
                    pass

        if val_amount is None and buyer_type is None:
            return None

        evidence = EvidenceItem(
            evidence_id=f"E-META-{uuid.uuid4().hex[:6]}",
            source_document_id=doc_id,
            source_text=text[:150],
            start_char=0,
            end_char=min(len(text), 150),
            page_number=1,
            clause_reference=None,
            matched_terms=["contract_value", "buyer_type"] if val_amount else ["metadata"],
            extraction_method="regex",
            extractor_confidence=0.90,
        )

        return ExtractedFact(
            fact_id=f"FACT-META-{uuid.uuid4().hex[:6]}",
            fact_type=FactType.CONTRACT_METADATA,
            value={
                "contract_value": val_amount,
                "buyer_type": buyer_type or "large_enterprise",
                "currency": "INR",
            },
            evidence=evidence,
            confidence=0.90,
            status=FactStatus.DEFINITIVE,
            extractor_version=self.EXTRACTOR_VERSION,
            extraction_method=ExtractionMethod.REGEX,
        )
