"""
Payment Basis Date Resolver.

Detects which starting date a payment term is based on:
invoice date, delivery date, acceptance date, buyer approval, etc.

Produces INCONCLUSIVE status when the basis is ambiguous or
when buyer-discretionary terms lack defined deadlines.
"""

import re
from typing import Optional, Tuple

from vasooli.domain.enums import PaymentBasis


# Pattern groups mapping payment basis categories to regex patterns.
# Each pattern is tried against the surrounding text of a payment term match.
PAYMENT_BASIS_PATTERNS: dict[PaymentBasis, list[str]] = {
    PaymentBasis.INVOICE_DATE: [
        r'from\s+(?:the\s+)?(?:date\s+of\s+)?invoice',
        r'from\s+invoice\s+(?:date|submission|receipt)',
        r'(?:upon|on|after)\s+(?:receipt\s+of\s+)?invoice',
        r'after\s+invoicing',
        r'from\s+(?:the\s+)?billing\s+date',
    ],
    PaymentBasis.DELIVERY_DATE: [
        r'(?:after|from|upon)\s+(?:the\s+)?(?:date\s+of\s+)?(?:physical\s+)?delivery',
        r'from\s+(?:the\s+)?(?:date\s+of\s+)?receipt\s+of\s+(?:goods|materials|consignment)',
        r'(?:after|from|upon)\s+(?:the\s+)?(?:date\s+of\s+)?consignment\s+arrival',
        r'from\s+(?:the\s+)?dispatch\s+date',
        r'from\s+(?:the\s+)?(?:date\s+of\s+)?shipment',
    ],
    PaymentBasis.ACCEPTANCE_DATE: [
        r'(?:after|from|upon)\s+(?:the\s+)?(?:date\s+of\s+)?(?:customer\s+|final\s+|client\s+)?acceptance',
        r'from\s+(?:the\s+)?(?:date\s+of\s+)?(?:quality\s+)?(?:inspection|qa)\s+(?:clearance|approval)',
        r'after\s+(?:quality\s+)?acceptance',
        r'from\s+(?:the\s+)?(?:date\s+of\s+)?(?:final\s+)?acceptance\s+(?:of\s+goods|certificate)',
    ],
    PaymentBasis.DEEMED_ACCEPTANCE: [
        r'deemed\s+(?:to\s+(?:be|have\s+been)\s+)?accept(?:ed|ance)',
        r'(?:if|unless)\s+(?:no\s+)?(?:objection|rejection)\s+(?:is\s+)?(?:raised|communicated)',
        r'auto(?:matic)?(?:ally)?\s+accept',
    ],
    PaymentBasis.MILESTONE_DATE: [
        r'from\s+(?:the\s+)?(?:date\s+of\s+)?(?:milestone|project)\s+(?:completion|delivery)',
        r'(?:upon|after)\s+completion\s+of\s+(?:the\s+)?milestone',
        r'from\s+(?:the\s+)?(?:date\s+of\s+)?(?:phase|stage)\s+(?:completion|sign[\-\s]?off)',
    ],
    PaymentBasis.BUYER_APPROVAL: [
        r'(?:buyer|client|purchaser|customer)\s*[\'"]?s?\s+(?:approval|sign[\-\s]?off|confirmation)',
        r'(?:after|upon)\s+(?:the\s+)?(?:buyer|client|purchaser|customer)\s+(?:approves?|confirms?|signs?\s+off)',
        r'subject\s+to\s+(?:the\s+)?(?:buyer|client|purchaser)\s*[\'"]?s?\s+(?:approval|confirmation)',
    ],
    PaymentBasis.RECEIPT_DATE: [
        r'from\s+(?:the\s+)?(?:date\s+of\s+)?receipt',
        r'upon\s+receipt\s+of\s+(?:goods|services)',
        r'after\s+(?:the\s+)?(?:date\s+of\s+)?receipt\s+of\s+(?:goods|work)',
    ],
}

# Patterns that indicate ambiguous or buyer-discretionary payment terms.
AMBIGUOUS_PAYMENT_PATTERNS: list[tuple[str, str]] = [
    (r'(?:upon|after|on)\s+realization', "Payment is contingent on 'realization' — no defined timeline."),
    (r'(?:subject\s+to\s+|at\s+)?(?:buyer|client|purchaser)\s*[\'"]?s?\s+discretion',
     "Payment is subject to buyer's discretion without a defined deadline."),
    (r'at\s+(?:buyer|client|purchaser)\s*[\'"]?s?\s+convenience',
     "Payment timing is at buyer's convenience — no enforceable deadline."),
    (r'(?:after|upon)\s+(?:buyer|client)\s+(?:approval|sign[\-\s]?off)',
     "Payment depends on buyer approval but no approval deadline is defined."),
    (r'(?:when|as\s+and\s+when)\s+(?:funds?\s+(?:are|is)\s+)?(?:available|received)',
     "Payment is contingent on fund availability — no defined timeline."),
    (r'payment\s+terms?\s+(?:to\s+be\s+)?(?:decided|determined|agreed)\s+(?:later|subsequently|mutually)',
     "Payment terms are deferred to a future agreement."),
]


def resolve_payment_basis(
    text: str,
    match_start: int = 0,
    match_end: Optional[int] = None,
    window_chars: int = 200,
) -> Tuple[PaymentBasis, Optional[str], float]:
    """
    Determine the starting-date basis for a payment term.

    Searches a window around the payment term match for basis-indicator patterns.

    Args:
        text: Full contract text (lowercased).
        match_start: Start offset of the payment-days match.
        match_end: End offset of the payment-days match.
        window_chars: Number of characters to search before/after the match.

    Returns:
        Tuple of (PaymentBasis, basis_description, confidence):
        - PaymentBasis enum value
        - Raw matched text describing the basis (or None)
        - Confidence score (0.0 - 1.0)
    """
    end = match_end or match_start
    window_start = max(0, match_start - window_chars)
    window_end = min(len(text), end + window_chars)
    window = text[window_start:window_end]
    window_lower = window.lower()

    # Try each basis category
    for basis, patterns in PAYMENT_BASIS_PATTERNS.items():
        for pat in patterns:
            m = re.search(pat, window_lower)
            if m:
                # Extract the matched description from original (non-lowered) text
                abs_start = window_start + m.start()
                abs_end = window_start + m.end()
                basis_desc = text[abs_start:abs_end].strip()
                return basis, basis_desc, 0.90

    return PaymentBasis.UNSPECIFIED, None, 0.60


def detect_ambiguous_payment(text: str, match_start: int = 0, match_end: Optional[int] = None, window_chars: int = 300) -> Optional[str]:
    """
    Check if the payment term context contains ambiguous or buyer-discretionary language.

    Returns:
        The ambiguity reason string if detected, or None if no ambiguity found.
    """
    end = match_end or match_start
    window_start = max(0, match_start - window_chars)
    window_end = min(len(text), end + window_chars)
    window = text[window_start:window_end].lower()

    for pat, reason in AMBIGUOUS_PAYMENT_PATTERNS:
        if re.search(pat, window):
            return reason

    return None
