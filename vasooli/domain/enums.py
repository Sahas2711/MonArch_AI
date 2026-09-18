"""
Vasooli Domain Enumerations.

Defines all controlled vocabularies used across the evidence-first pipeline:
fact types, payment basis categories, extraction statuses, severities,
review actions, and policy decision outcomes.
"""

from enum import Enum


class FactType(str, Enum):
    """Type of structured fact extracted from a contract."""
    PAYMENT_TERM = "payment_term"
    INTEREST_CLAUSE = "interest_clause"
    CANCELLATION_CLAUSE = "cancellation_clause"
    ACCEPTANCE_MECHANISM = "acceptance_mechanism"
    DISPUTE_RESOLUTION = "dispute_resolution"
    TAX_COMPLIANCE = "tax_compliance"
    CONTRACT_METADATA = "contract_metadata"
    GENERAL = "general"


class PaymentBasis(str, Enum):
    """Starting-date basis for payment term calculation."""
    INVOICE_DATE = "invoice_date"
    DELIVERY_DATE = "delivery_date"
    ACCEPTANCE_DATE = "acceptance_date"
    DEEMED_ACCEPTANCE = "deemed_acceptance"
    MILESTONE_DATE = "milestone_date"
    BUYER_APPROVAL = "buyer_approval"
    RECEIPT_DATE = "receipt_date"
    UNSPECIFIED = "unspecified"


class FactStatus(str, Enum):
    """Confidence classification of an extracted fact."""
    DEFINITIVE = "DEFINITIVE"       # High-confidence, unambiguous extraction
    INCONCLUSIVE = "INCONCLUSIVE"   # Ambiguous clause, requires human review
    AMBIGUOUS = "AMBIGUOUS"         # Multiple conflicting interpretations found


class DecisionOutcome(str, Enum):
    """Outcome of a policy rule evaluation against extracted facts."""
    TRIGGERED = "TRIGGERED"         # Statutory violation detected
    NOT_TRIGGERED = "NOT_TRIGGERED" # No violation found
    INCONCLUSIVE = "INCONCLUSIVE"   # Cannot determine — insufficient evidence


class Severity(str, Enum):
    """Risk severity classification for violations and findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewAction(str, Enum):
    """Actions available to a human reviewer."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    ESCALATED = "escalated"


class ReviewRouting(str, Enum):
    """Confidence-based routing recommendation for a determination."""
    AUTO_APPROVE = "auto_approve"
    HUMAN_REVIEW = "human_review"
    ESCALATE_LEGAL = "escalate_legal"


class RecoveryStage(str, Enum):
    """Current stage in the MSME payment recovery lifecycle."""
    PREVENTIVE_REVISE = "preventive_revise"
    DEMAND = "demand"
    FORMAL_NOTICE = "formal_notice"
    LEGAL_NOTICE = "legal_notice"
    SAMADHAAN_FILING = "samadhaan_filing"


class ExtractionMethod(str, Enum):
    """Method used to extract a fact from contract text."""
    REGEX = "regex"
    CLASSIFIER = "classifier"
    LLM = "llm"
    HYBRID = "hybrid"
    REGEX_CLASSIFIER = "regex+classifier"
    FALLBACK = "fallback"


class InterestCalculationMethod(str, Enum):
    """Method used for statutory interest computation."""
    COMPOUND_MONTHLY_RESTS = "compound_monthly_rests"
    SIMPLE_INTEREST = "simple_interest"
    STATUTORY_DISALLOWANCE = "statutory_disallowance"
