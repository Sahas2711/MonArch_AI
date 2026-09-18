"""
MSME Compliance Scoring Module.

Computes rule-based, auditable Compliance Risk Score (0-100),
statutory financial exposure with compound monthly interest under Section 16,
and Section 43B(h) tax disallowance impact.
"""

from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pipeline.extractor import ExtractedClause
from pipeline.financial import calculate_statutory_interest
from models.schemas import RiskScoreBreakdown
from utils.logger import log


class ComplianceScore(BaseModel):
    """Detailed compliance score with statutory financial exposure breakdown."""
    score: int = Field(..., ge=0, le=100, description="Compliance Risk Score (Rule-Based Risk Index)")
    risk_level: str = Field(..., description="low | medium | high | critical")
    breakdown: Dict[str, float] = Field(default_factory=dict, description="Point deductions by category")
    breakdown_items: List[RiskScoreBreakdown] = Field(default_factory=list, description="Line-item deduction breakdown")
    score_label: str = Field("Compliance Risk Score", description="Auditable metric label")
    score_disclaimer: str = Field(
        "Calculated from flagged statutory violations — not a probability estimate.",
        description="Mandatory labeling disclaimer"
    )
    max_score: int = Field(100, description="Base score before statutory deductions")
    statutory_exposure_estimate: float = Field(0.0, description="Estimated total financial risk in INR")
    interest_daily_rate: float = Field(0.0, description="Applicable daily statutory interest rate")
    annual_statutory_interest_rate: float = Field(19.5, description="3x RBI bank rate (3 * 6.5% = 19.5%)")
    tax_disallowance_applicable: bool = Field(False, description="Whether Sec 43B(h) disallowance applies")
    tax_exposure_estimate: float = Field(0.0, description="Estimated corporate tax disallowance exposure in INR")


# Explicit, defensible statutory risk deductions
RISK_DEDUCTIONS: Dict[str, tuple] = {
    "payment_days_breach": (35, "Payment-term breach is weighted highest because it's the statute's core protection"),
    "no_penalty_interest_clause": (20, "Missing penalty interest removes the statutory deterrent against delayed payments"),
    "unilateral_cancellation": (15, "One-sided cancellation exposes the MSME to uncompensated losses"),
    "low_evidence_confidence": (10, "Low extraction confidence means the determination may be unreliable"),
}

DEFAULT_RBI_RATE = 6.5  # RBI Repo Rate benchmark
DEFAULT_CORPORATE_TAX_RATE = 0.25  # 25% effective corporate tax rate


class ComplianceScorer:
    """
    Evaluates extracted clauses and statutory violations to produce
    rule-based compliance scores and financial impact projections.
    """

    def __init__(
        self,
        rbi_bank_rate: float = DEFAULT_RBI_RATE,
        corporate_tax_rate: float = DEFAULT_CORPORATE_TAX_RATE,
    ):
        self.rbi_bank_rate = rbi_bank_rate
        self.statutory_interest_rate = rbi_bank_rate * 3.0  # MSMED Act Sec 16 mandates 3x RBI rate
        self.corporate_tax_rate = corporate_tax_rate

    def calculate_score(
        self,
        violations: List[Dict[str, Any]],
        clauses: Optional[List[ExtractedClause]] = None,
        contract_value: float = 1500000.0,
    ) -> ComplianceScore:
        """
        Calculates rule-based compliance risk score (0-100) and compound interest financial exposure.
        """
        clauses = clauses or []
        deductions: Dict[str, float] = {}
        breakdown_items: List[RiskScoreBreakdown] = []

        # Map violation types
        violation_types = set()
        violation_confidences = []
        for v in violations:
            v_type = v.get("violation_type") or v.get("type", "")
            if not v_type:
                cited = str(v.get("cited_law", "")) + str(v.get("matched_rules", ""))
                if "15" in cited or "45" in cited or "payment" in cited.lower():
                    v_type = "payment_cycle"
                elif "16" in cited or "interest" in cited.lower() or "rbi" in cited.lower():
                    v_type = "interest_penalty"
                elif "43b" in cited.lower() or "tax" in cited.lower():
                    v_type = "tax_disallowance"
                elif "cancellation" in cited.lower() or "unilateral" in cited.lower():
                    v_type = "unilateral_cancellation"
            if v_type:
                violation_types.add(v_type)
            if "confidence" in v and v["confidence"] is not None:
                violation_confidences.append(float(v["confidence"]))

        # Inspect extracted clauses directly
        payment_days = 30
        clause_confidences = []
        for c in clauses:
            if c.confidence is not None:
                clause_confidences.append(float(c.confidence))
            if c.payment_days is not None:
                payment_days = c.payment_days
                if c.payment_days > 45:
                    violation_types.add("payment_cycle")
            if c.has_penalty_interest is False:
                violation_types.add("interest_penalty")
            if c.has_unilateral_cancellation is True:
                violation_types.add("unilateral_cancellation")

        # Determine average confidence
        all_confidences = clause_confidences or violation_confidences
        avg_confidence = (sum(all_confidences) / len(all_confidences)) if all_confidences else 1.0

        # Evaluate the 4 core statutory deductions
        has_payment_breach = payment_days > 45 or "payment_cycle" in violation_types
        has_no_interest = "interest_penalty" in violation_types or any(c.has_penalty_interest is False for c in clauses)
        has_cancellation = "unilateral_cancellation" in violation_types or any(c.has_unilateral_cancellation is True for c in clauses)
        has_low_conf = avg_confidence < 0.7

        triggers = {
            "payment_days_breach": has_payment_breach,
            "no_penalty_interest_clause": has_no_interest,
            "unilateral_cancellation": has_cancellation,
            "low_evidence_confidence": has_low_conf,
        }

        score = 100
        for factor, (pts, rationale) in RISK_DEDUCTIONS.items():
            triggered = bool(triggers.get(factor, False))
            pts_deducted = pts if triggered else 0
            if triggered:
                score -= pts
                deductions[factor] = float(pts)

            breakdown_items.append(
                RiskScoreBreakdown(
                    deduction_name=factor,
                    points_deducted=pts_deducted,
                    rationale=rationale,
                    triggered=triggered,
                )
            )

        final_score = max(0, min(100, score))

        # Risk band mapping: >= 70 low, 40-69 medium, < 40 high/critical
        if final_score >= 70:
            risk_level = "low"
        elif final_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "critical"

        # Financial exposure calculations using Section 16 compound monthly interest
        delayed_days = max(0, payment_days - 45)
        effective_delay_days = delayed_days if delayed_days > 0 else (60 if has_payment_breach else 0)

        today = date.today()
        due_date = today - timedelta(days=effective_delay_days) if effective_delay_days > 0 else today
        interest_res = calculate_statutory_interest(
            principal=contract_value,
            due_date=due_date,
            payment_date=today,
            rbi_rate=self.rbi_bank_rate,
        )
        interest_exposure = interest_res.interest_amount

        # Tax disallowance exposure under Section 43B(h)
        tax_applicable = has_payment_breach or "tax_disallowance" in violation_types
        tax_exposure = (contract_value * self.corporate_tax_rate) if tax_applicable else 0.0

        total_exposure = interest_exposure + tax_exposure
        daily_interest_rate = (self.statutory_interest_rate / 100.0) / 365.0

        log.info(
            "ComplianceScorer: score=%d, risk=%s, total_exposure=INR %.2f, deductions=%s",
            final_score, risk_level, total_exposure, deductions
        )

        return ComplianceScore(
            score=final_score,
            risk_level=risk_level,
            breakdown=deductions,
            breakdown_items=breakdown_items,
            score_label="Compliance Risk Score (Rule-Based Risk Index)",
            score_disclaimer="Calculated from flagged statutory violations — not a probability estimate.",
            max_score=100,
            statutory_exposure_estimate=round(total_exposure, 2),
            interest_daily_rate=round(daily_interest_rate, 6),
            annual_statutory_interest_rate=self.statutory_interest_rate,
            tax_disallowance_applicable=tax_applicable,
            tax_exposure_estimate=round(tax_exposure, 2),
        )
