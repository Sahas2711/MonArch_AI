"""
Pydantic Schemas for MSME Payment Compliance & Risk Pipeline.

Defines structured compliance audit models including:
- Extracted terms & clauses
- Statutory violations & citations
- Verifiable textual evidence
- Statutory financial exposure & interest liability
- Human-in-the-loop review decisions & actions
- Risk score breakdown and disclaimers
- Escalation decision ladder & contact tracking
- Pre-signature negotiation recommendations
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceItem(BaseModel):
    """Verifiable textual and statutory evidence supporting a determination."""
    source_text: str = Field(..., description="Exact textual quote from the audited contract")
    start_char: Optional[int] = Field(None, description="Start character offset in contract")
    end_char: Optional[int] = Field(None, description="End character offset in contract")
    matched_keywords: List[str] = Field(default_factory=list, description="Keywords or regex tokens matched")
    rag_chunk_id: Optional[str] = Field(None, description="RAG knowledge base statutory chunk reference")
    statute_ref: Optional[str] = Field(None, description="Exact statutory section citation")
    page_number: Optional[int] = Field(None, description="Estimated or Textract-derived page number in source document")
    clause_reference: Optional[str] = Field(None, description="Contract clause reference (e.g. §14.2, Clause 7.1)")


class FinancialImpact(BaseModel):
    """Calculated financial exposure under MSMED Act and Income Tax Act."""
    estimated_delay_days: int = Field(0, description="Payment days exceeding 45-day statutory limit")
    statutory_interest_rate_percent: float = Field(19.5, description="3x RBI bank rate compound interest")
    estimated_interest_exposure: float = Field(0.0, description="Compound interest liability in INR")
    tax_disallowance_risk: bool = Field(False, description="Whether Section 43B(h) deduction disallowance applies")
    estimated_tax_exposure: float = Field(0.0, description="Estimated corporate tax disallowance impact in INR")
    total_financial_exposure: float = Field(0.0, description="Total projected financial risk in INR")
    months_overdue: Optional[int] = Field(None, description="Complete calendar months of overdue payment")
    monthly_compound_rate: Optional[float] = Field(None, description="Monthly compound interest rate applied (%)")
    rbi_bank_rate: Optional[float] = Field(None, description="RBI bank rate used for calculation")
    principal_amount: Optional[float] = Field(None, description="Invoice/contract principal amount")
    total_recoverable: Optional[float] = Field(None, description="Principal + compound interest = total claim")
    calculation_method: str = Field("compound_monthly_rests", description="Interest compounding method used")


class ViolationItem(BaseModel):
    """Individual statutory violation flagged during compliance audit."""
    clause_text: str = Field(..., description="The offending contractual clause")
    violation_type: str = Field(..., description="payment_cycle | interest_penalty | tax_disallowance | dispute_resolution | unilateral_cancellation")
    cited_law: str = Field(..., description="The specific Indian statute or section violated")
    cited_chunk_id: Optional[str] = Field(None, description="RAG chunk reference identifier")
    severity: str = Field("high", description="critical | high | medium | low")
    draft_counter_clause: str = Field(..., description="Legally sound substitute clause compliant with MSME Act")
    samadhaan_ready: bool = Field(True, description="Whether this violation qualifies for MSME Samadhaan dispute filing")
    evidence: Optional[EvidenceItem] = Field(None, description="Structured textual and statutory evidence")
    financial_impact: Optional[FinancialImpact] = Field(None, description="Financial risk associated with this violation")
    confidence: float = Field(0.90, ge=0.0, le=1.0, description="Confidence in this violation determination")
    needs_human_review: bool = Field(False, description="Flagged for human legal review")
    reviewer_action: Optional[str] = Field(None, description="Reviewer action: approved | dismissed | modified")


class ReviewDecisionSchema(BaseModel):
    """Confidence gate decision for human-in-the-loop review."""
    needs_human_review: bool = Field(..., description="Whether human review is required")
    review_reasons: List[str] = Field(default_factory=list, description="Reasons triggering human review")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall pipeline confidence (0-1)")
    auto_approved: bool = Field(..., description="Whether determination was automatically approved")
    flags: List[str] = Field(default_factory=list, description="Warning flags")
    recommended_action: str = Field("auto_approve", description="auto_approve | human_review | escalate_legal")


class RiskScoreBreakdown(BaseModel):
    """Auditable line-item deduction for rule-based risk score."""
    deduction_name: str = Field(..., description="Identifier of the risk factor")
    points_deducted: int = Field(..., description="Points deducted from base 100")
    rationale: str = Field(..., description="Statutory defense/justification for the deduction")
    triggered: bool = Field(..., description="Whether this deduction fired")


class RecommendedActionSchema(BaseModel):
    """Action step in the MSME recovery decision ladder."""
    action_id: str = Field(..., description="send_demand | formal_notice | file_samadhaan")
    label: str = Field(..., description="Human-readable action title")
    effort_level: str = Field(..., description="low | medium | high")
    is_recommended: bool = Field(..., description="Whether this step is currently the primary recommendation")
    reason: str = Field(..., description="Contextual rationale based on contact history")
    escalation_order: int = Field(..., description="Ladder sequence order (1, 2, 3)")


class CaseTrackingFields(BaseModel):
    """Contact attempt tracking for dispute escalation."""
    contact_attempts: int = Field(0, description="Number of contact attempts made for this case")
    first_contact_date: Optional[str] = Field(None, description="ISO date of first contact attempt")


class NegotiationRecommendation(BaseModel):
    """Pre-signature clause rewrite recommendation."""
    original_clause: str = Field(..., description="The original offending clause from draft contract")
    violation_type: str = Field(..., description="Category of violation")
    cited_law: str = Field(..., description="Indian statute violated")
    compliant_replacement: str = Field(..., description="MSME Act Section 15/16 compliant replacement text")
    risk_explanation: str = Field(..., description="Plain-language explanation of commercial/legal risk")
    confidence: float = Field(0.90, ge=0.0, le=1.0, description="Confidence of recommendation")


class AnalysisReport(BaseModel):
    """Complete MSME Contract Compliance Audit Report."""
    report_id: str
    buyer_name: str
    file_name: Optional[str] = "Contract Agreement"
    compliance_score: int = Field(..., description="Compliance Risk Score (Rule-Based Risk Index, 0-100)")
    risk_level: str = Field("medium", description="low | medium | high | critical")
    violations: List[ViolationItem] = []
    overall_summary: str
    draft_samadhaan_complaint: Optional[str] = None
    analyzed_at: str
    financial_summary: Optional[FinancialImpact] = None
    review_decision: Optional[ReviewDecisionSchema] = None
    disclaimer: str = "For informational and compliance guidance purposes only. Not formal legal advice."
    risk_score_breakdown: Optional[List[RiskScoreBreakdown]] = Field(None, description="Per-deduction breakdown of the Compliance Risk Score")
    risk_score_disclaimer: str = Field(
        "Calculated from flagged statutory violations — not a probability estimate.",
        description="Mandatory labeling disclaimer for the risk score"
    )
    recommended_actions: Optional[List[RecommendedActionSchema]] = Field(None, description="Recommended action ladder")
    contact_attempts: int = Field(0, description="Number of contact attempts made for this case")
    first_contact_date: Optional[str] = Field(None, description="ISO date of first contact attempt")
    negotiation_recommendations: Optional[List[NegotiationRecommendation]] = Field(None, description="Pre-signature negotiation recommendations")
    financial_breakdown: Optional[Dict[str, Any]] = Field(None, description="Detailed statutory interest calculation breakdown")


# Structured Audit Output alias for standard decision-support representation
AuditOutput = AnalysisReport


class ReviewActionPayload(BaseModel):
    """Payload for submitting human reviewer decision on an audit report."""
    action: str = Field(..., description="approved | rejected | modified | escalated")
    reviewer_name: Optional[str] = "Compliance Officer"
    notes: Optional[str] = None
    modified_violations: Optional[List[ViolationItem]] = None
