"""
Vasooli Core Domain Models.

Defines the evidence-first data structures that enforce the key architectural rule:
    The LLM may explain facts and draft documents, but it must not invent legal facts,
    calculate financial values, or independently decide whether a clause violates the law.

Hierarchy:
    EvidenceItem → ExtractedFact → PolicyDecision → FinancialCalculation → ComplianceScorecard → AnalysisReport

Every determination is traceable back to source evidence with exact character offsets.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from vasooli.domain.enums import (
    DecisionOutcome,
    ExtractionMethod,
    FactStatus,
    FactType,
    InterestCalculationMethod,
    PaymentBasis,
    RecoveryStage,
    ReviewAction,
    ReviewRouting,
    Severity,
)


# ---------------------------------------------------------------------------
# Evidence Layer — Source-anchored proof for every determination
# ---------------------------------------------------------------------------


class EvidenceItem(BaseModel):
    """
    Verifiable, source-anchored textual evidence supporting a finding.

    Every fact, violation, and determination MUST link to one or more EvidenceItems.
    Never generate a violation without linked source evidence.
    """
    evidence_id: str = Field(..., description="Unique evidence identifier, e.g. 'E-001'")
    source_document_id: str = Field(..., description="Document from which evidence was extracted")
    source_text: str = Field(..., description="Exact textual quote from the contract")
    start_char: int = Field(..., description="Start character offset in source document")
    end_char: int = Field(..., description="End character offset in source document")
    page_number: int = Field(1, description="1-based page number in source document")
    clause_reference: Optional[str] = Field(None, description="Clause/section reference, e.g. 'Clause 14.2'")
    matched_terms: List[str] = Field(default_factory=list, description="Keywords or regex tokens matched")
    extraction_method: str = Field("regex", description="Method used: regex, classifier, llm, hybrid")
    extractor_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence of this extraction")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ---------------------------------------------------------------------------
# Fact Layer — Structured facts, NOT conclusions
# ---------------------------------------------------------------------------


class PaymentTermValue(BaseModel):
    """Structured value for a payment term fact."""
    days: Optional[int] = Field(None, description="Payment period in calendar days")
    basis: PaymentBasis = Field(PaymentBasis.UNSPECIFIED, description="Starting date for payment calculation")
    basis_description: Optional[str] = Field(None, description="Raw text describing payment start date")
    has_written_agreement: Optional[bool] = Field(None, description="Whether a written agreement governs the term")


class InterestClauseValue(BaseModel):
    """Structured value for an interest clause fact."""
    interest_provided: Optional[bool] = Field(None, description="Whether contract provides for interest on delays")
    interest_rate_percent: Optional[float] = Field(None, description="Explicitly stated interest rate if any")
    interest_waived: Optional[bool] = Field(None, description="Whether interest is explicitly waived")
    statutory_reference: Optional[str] = Field(None, description="Reference to statutory interest provisions")


class CancellationClauseValue(BaseModel):
    """Structured value for a cancellation clause fact."""
    is_unilateral: Optional[bool] = Field(None, description="Whether cancellation is one-sided")
    notice_period_days: Optional[int] = Field(None, description="Required notice period in days")
    compensation_required: Optional[bool] = Field(None, description="Whether compensation for completed work is required")
    cancellation_party: Optional[str] = Field(None, description="Which party can cancel: buyer, seller, either, unspecified")


class ExtractedFact(BaseModel):
    """
    A structured fact extracted from contract text.

    KEY RULE: Facts describe WHAT the contract says, not WHETHER it violates the law.
    The determination of violation belongs to the PolicyDecision layer.

    Example of a correct fact:
        fact_type: PAYMENT_TERM
        value: {"days": 90, "basis": "invoice_date"}

    Example of what this must NOT contain:
        legal_violation: True  ← This belongs in PolicyDecision
    """
    fact_id: str = Field(..., description="Unique fact identifier, e.g. 'FACT-001'")
    fact_type: FactType = Field(..., description="Category of extracted fact")
    value: Dict[str, Any] = Field(..., description="Structured fact value (type-specific)")
    evidence: EvidenceItem = Field(..., description="Source evidence anchoring this fact")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence score")
    status: FactStatus = Field(FactStatus.DEFINITIVE, description="Whether this fact is definitive or ambiguous")
    inconclusive_reason: Optional[str] = Field(
        None,
        description="Explanation when status is INCONCLUSIVE or AMBIGUOUS, e.g. "
                    "'The clause refers to buyer approval but does not define an approval deadline.'"
    )
    extractor_version: str = Field("extractor-1.0.0", description="Version of the extraction module")
    extraction_method: ExtractionMethod = Field(ExtractionMethod.REGEX, description="Method used for extraction")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ---------------------------------------------------------------------------
# Policy Layer — Versioned legal rule evaluation
# ---------------------------------------------------------------------------


class PolicyRule(BaseModel):
    """
    A versioned legal policy rule definition.

    Rules are testable, versioned, auditable, and replaceable.
    When laws or rates change, a new version is created — old versions are preserved.
    """
    policy_id: str = Field(..., description="Unique rule identifier, e.g. 'MSMED_SEC15_PAYMENT_LIMIT'")
    statute: str = Field(..., description="Source statute, e.g. 'MSMED Act 2006'")
    section: str = Field(..., description="Section reference, e.g. '15'")
    version: str = Field(..., description="Rule version, e.g. '2026-01-01'")
    effective_from: date = Field(..., description="Date from which this rule version is effective")
    effective_until: Optional[date] = Field(None, description="Date until which this rule version applies (None = current)")
    rule_type: str = Field(..., description="Rule category: payment_period, interest_rate, cancellation, tax_disallowance")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Rule-specific parameters")
    description: str = Field("", description="Human-readable description of the rule")


class PolicyDecision(BaseModel):
    """
    The outcome of evaluating extracted facts against a versioned policy rule.

    This is where legal determinations are made — NOT in the extraction layer.
    Every decision must link to the facts and evidence that produced it.
    """
    decision_id: str = Field(..., description="Unique decision identifier, e.g. 'DEC-001'")
    policy_id: str = Field(..., description="Policy rule that was evaluated")
    decision: DecisionOutcome = Field(..., description="TRIGGERED, NOT_TRIGGERED, or INCONCLUSIVE")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence in this decision")
    facts_used: List[str] = Field(default_factory=list, description="Fact IDs that were evaluated")
    evidence_ids: List[str] = Field(default_factory=list, description="Evidence IDs supporting this decision")
    explanation: str = Field("", description="Human-readable explanation of the decision")
    policy_version: str = Field("", description="Version of the policy rule used")
    statute_ref: str = Field("", description="Formal statute citation")
    severity: Severity = Field(Severity.MEDIUM, description="Severity if triggered")
    review_status: str = Field("pending", description="pending | approved | rejected — no decision is final without review")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ---------------------------------------------------------------------------
# Financial Layer — Decimal arithmetic, versioned rates
# ---------------------------------------------------------------------------


class RateConfig(BaseModel):
    """Versioned RBI bank rate configuration."""
    rbi_bank_rate: Decimal = Field(..., description="Current RBI bank rate as decimal, e.g. 0.065 for 6.5%")
    rate_effective_from: date = Field(..., description="Date from which this rate is effective")
    rate_effective_until: Optional[date] = Field(None, description="Date until which this rate applies")
    multiplier: int = Field(3, description="Statutory multiplier (3x for MSMED Act)")
    source: str = Field("configured_rate_table", description="Source of rate data")

    @property
    def annual_statutory_rate(self) -> Decimal:
        """Computed annual statutory interest rate = rbi_bank_rate * multiplier."""
        return self.rbi_bank_rate * self.multiplier

    @property
    def annual_statutory_rate_percent(self) -> Decimal:
        """Annual statutory rate as percentage, e.g. 19.5 for 19.5%."""
        return self.annual_statutory_rate * 100


class FinancialCalculation(BaseModel):
    """
    Deterministic financial calculation result using Decimal arithmetic.

    All monetary values are serialized as strings to preserve exact precision.
    The LLM must not calculate interest — pass the calculated value into the prompt
    and verify that the output repeats the same value.
    """
    calculation_id: str = Field(..., description="Unique calculation identifier")
    principal: str = Field(..., description="Principal amount as Decimal string")
    delay_start_date: date = Field(..., description="Date from which delay is counted")
    calculation_date: date = Field(..., description="Date of calculation")
    completed_months: int = Field(0, description="Complete calendar months of delay")
    annual_rate: str = Field(..., description="Annual statutory rate as Decimal string")
    monthly_rate: str = Field(..., description="Monthly rate as Decimal string")
    compound_interest: str = Field("0", description="Calculated compound interest as Decimal string")
    total_recoverable: str = Field("0", description="Principal + interest as Decimal string")
    calculation_version: str = Field("interest-2.0.0", description="Version of calculation module")
    rate_config: RateConfig = Field(..., description="Rate configuration used")
    method: InterestCalculationMethod = Field(InterestCalculationMethod.COMPOUND_MONTHLY_RESTS)
    notes: List[str] = Field(default_factory=list, description="Assumptions and caveats")

    class Config:
        json_encoders = {Decimal: str, date: lambda v: v.isoformat()}


class TaxExposureEstimate(BaseModel):
    """
    Estimated buyer tax exposure under Section 43B(h).

    IMPORTANT: This is an ESTIMATE, not a guaranteed value.
    Always label as 'estimated buyer tax impact'.
    """
    estimated_tax_impact: str = Field(..., description="Estimated tax impact as Decimal string")
    assumed_tax_rate: str = Field(..., description="Assumed corporate tax rate as Decimal string")
    buyer_qualifies: Optional[bool] = Field(None, description="Whether the buyer qualifies under the statute")
    payment_qualifies: Optional[bool] = Field(None, description="Whether the payment qualifies under the statute")
    applicable_assessment_year: Optional[str] = Field(None, description="Applicable assessment year")
    is_illustrative: bool = Field(True, description="Whether this is only an illustrative estimate")
    disclaimer: str = Field(
        "This is an estimated tax impact for illustration purposes only. "
        "Actual tax liability depends on the buyer's specific tax situation, applicable deductions, "
        "and assessment by qualified tax professionals.",
        description="Mandatory disclaimer"
    )


# ---------------------------------------------------------------------------
# Scoring Layer — Four separate dimensions
# ---------------------------------------------------------------------------


class ScoreFactor(BaseModel):
    """A single factor contributing to the compliance score."""
    rule: str = Field(..., description="Factor identifier, e.g. 'payment_days_exceeded'")
    points: int = Field(..., description="Points impact (negative for deductions)")
    severity: Severity = Field(Severity.MEDIUM)
    evidence_ids: List[str] = Field(default_factory=list, description="Evidence supporting this factor")
    policy_id: str = Field("", description="Policy rule that produced this factor")
    triggered: bool = Field(False, description="Whether this factor was triggered")
    rationale: str = Field("", description="Why this factor applies or doesn't")


class CategoryConfidence(BaseModel):
    """Breakdown of confidence scores across evaluation dimensions."""
    payment_term_confidence: float = Field(1.0, ge=0.0, le=1.0)
    date_resolution_confidence: float = Field(1.0, ge=0.0, le=1.0)
    policy_match_confidence: float = Field(1.0, ge=0.0, le=1.0)
    financial_input_confidence: float = Field(1.0, ge=0.0, le=1.0)
    min_confidence: float = Field(1.0, ge=0.0, le=1.0)


class ComplianceScorecard(BaseModel):
    """
    Transparent, multi-dimensional compliance scorecard.

    Four separate dimensions — never combine into one number:
    1. compliance_score: Contractual compliance (0-100)
    2. financial_exposure: Rupee amount at risk
    3. confidence_score: Reliability of extraction and decision
    4. recovery_stage: Recommended action stage
    """
    base_score: int = Field(100, description="Base score before deductions")
    final_score: int = Field(100, ge=0, le=100, description="Final compliance score after deductions")
    risk_level: str = Field("low", description="low | medium | high | critical")

    factors: List[ScoreFactor] = Field(default_factory=list, description="All scoring factors")

    # Separate dimensions
    financial_exposure: Optional[FinancialCalculation] = Field(None, description="Financial exposure calculation")
    tax_exposure: Optional[TaxExposureEstimate] = Field(None, description="Tax exposure estimate")
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Pipeline confidence (extraction + policy)")
    category_confidence: Optional[CategoryConfidence] = Field(None, description="Category-specific confidence breakdown")
    recovery_stage: RecoveryStage = Field(RecoveryStage.DEMAND, description="Recommended recovery stage")

    score_version: str = Field("compliance-score-2.1.0", description="Scoring module version")
    score_disclaimer: str = Field(
        "Calculated from flagged statutory violations — not a probability estimate. "
        "No determination is final without reviewer approval.",
        description="Mandatory disclaimer"
    )


# ---------------------------------------------------------------------------
# Review Layer — Human-in-the-loop approval
# ---------------------------------------------------------------------------


class ReviewDecision(BaseModel):
    """Human-in-the-loop review routing and decision."""
    needs_human_review: bool = Field(..., description="Whether human review is required")
    review_reasons: List[str] = Field(default_factory=list, description="Triggers requiring review")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Overall pipeline confidence")
    category_confidence: Optional[CategoryConfidence] = Field(None, description="Category confidence breakdown")
    auto_approved: bool = Field(False, description="Whether it qualifies for automatic sign-off")
    flags: List[str] = Field(default_factory=list, description="Warning flags or ambiguity notices")
    recommended_action: ReviewRouting = Field(ReviewRouting.HUMAN_REVIEW, description="Routing recommendation")


# ---------------------------------------------------------------------------
# Audit Layer — Immutable event records
# ---------------------------------------------------------------------------


class AuditEvent(BaseModel):
    """
    Immutable audit record. INSERT-only, no UPDATE, no DELETE.

    Every state change in the system produces an AuditEvent.
    """
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="analysis_created | review_submitted | fact_modified | contact_logged")
    actor_id: str = Field(..., description="User/system that performed the action")
    org_id: str = Field(..., description="Organization context")
    resource_type: str = Field(..., description="analysis | document | evidence | policy_decision")
    resource_id: str = Field(..., description="ID of the affected resource")
    changes: Dict[str, Any] = Field(default_factory=dict, description="What changed (old_value → new_value)")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ---------------------------------------------------------------------------
# Analysis Report — Complete output with version metadata
# ---------------------------------------------------------------------------


class BuildMetadata(BaseModel):
    """Version metadata embedded in every analysis report for reproducibility."""
    version: str = Field("1.0.0", description="Application version")
    commit_sha: str = Field("dev", description="Git commit SHA")
    policy_pack_version: str = Field("msme-2026.01", description="Policy pack version")
    extractor_version: str = Field("extractor-1.0.0", description="Extractor module version")
    calculation_version: str = Field("interest-2.0.0", description="Financial calculation version")
    build_timestamp: str = Field("", description="Build timestamp")


class AnalysisReportV2(BaseModel):
    """
    Complete evidence-first analysis report.

    Every finding traces back to: Evidence → Fact → PolicyDecision → FinancialCalculation → Score.
    """
    report_id: str = Field(..., description="Unique report identifier")
    report_version: int = Field(1, description="Report version number (never overwrite, create new version)")
    document_id: str = Field(..., description="Source document identifier")
    buyer_name: str = Field(...)
    file_name: Optional[str] = Field("Contract Agreement")

    # Evidence-first outputs
    extracted_facts: List[ExtractedFact] = Field(default_factory=list)
    policy_decisions: List[PolicyDecision] = Field(default_factory=list)
    financial_calculation: Optional[FinancialCalculation] = Field(None)
    tax_exposure: Optional[TaxExposureEstimate] = Field(None)

    # Scorecard
    scorecard: ComplianceScorecard = Field(...)

    # Review
    review_decision: ReviewDecision = Field(...)
    review_status: str = Field("pending", description="pending | approved | rejected | escalated")

    # Generation outputs (LLM-produced, validated by output_guard)
    overall_summary: str = Field("")
    draft_counter_clauses: List[Dict[str, str]] = Field(default_factory=list)
    draft_samadhaan_complaint: Optional[str] = Field(None)

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    build_metadata: BuildMetadata = Field(default_factory=BuildMetadata)
    disclaimer: str = Field(
        "For informational and compliance guidance purposes only. Not formal legal advice. "
        "All determinations are subject to review by qualified legal professionals."
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
