"""
MSME Confidence Gate & Human-in-the-Loop Review Module.

Assesses determination confidence across extraction accuracy, policy matching,
and statutory citations to prevent hallucinated compliance determinations.
Enforces hard category minimums and ensures ambiguous dates block auto-approval.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pipeline.extractor import ExtractedClause
from utils.logger import log


class CategoryBreakdown(BaseModel):
    extraction_conf: float
    rule_conf: float
    grounding_conf: float
    min_category_conf: float


class ReviewDecision(BaseModel):
    """Human-in-the-loop review routing decision with calibrated confidence."""
    needs_human_review: bool = Field(..., description="Whether determination requires human verification")
    review_reasons: List[str] = Field(default_factory=list, description="Specific triggers requiring human review")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall pipeline determination confidence (0-1)")
    category_breakdown: Optional[CategoryBreakdown] = None
    auto_approved: bool = Field(..., description="Whether determination qualifies for automatic sign-off")
    flags: List[str] = Field(default_factory=list, description="Warning flags or ambiguity notices")
    recommended_action: str = Field(
        "auto_approve",
        description="auto_approve | human_review | escalate_legal"
    )


class ConfidenceGate:
    """
    Evaluates confidence across extraction, rule evaluation, and grounding
    to determine whether human-in-the-loop sign-off is required.
    Enforces category-specific hard minimums (no simple average masking).
    """

    def __init__(
        self,
        extraction_threshold: float = 0.70,
        determination_threshold: float = 0.80,
        auto_approve_threshold: float = 0.95,
        min_category_floor: float = 0.85,
    ):
        self.extraction_threshold = extraction_threshold
        self.determination_threshold = determination_threshold
        self.auto_approve_threshold = auto_approve_threshold
        self.min_category_floor = min_category_floor

    def evaluate(
        self,
        clauses: List[ExtractedClause],
        violations: List[Dict[str, Any]],
        rag_faithfulness: Optional[float] = None,
        has_ambiguous_dates: bool = False,
    ) -> ReviewDecision:
        """
        Evaluates extraction confidence, statutory findings, and date ambiguities.
        Returns a ReviewDecision indicating if human-in-the-loop review is required.
        """
        reasons: List[str] = []
        flags: List[str] = []

        # 1. Extraction confidence calculation
        if clauses:
            clause_confidences = [c.confidence for c in clauses]
            avg_extraction_conf = sum(clause_confidences) / len(clause_confidences)
            min_extraction_conf = min(clause_confidences)
        else:
            avg_extraction_conf = 0.50
            min_extraction_conf = 0.50
            flags.append("No explicit payment clauses could be parsed from input text.")

        if min_extraction_conf < self.extraction_threshold:
            reasons.append(
                f"Low extraction confidence ({min_extraction_conf:.2f} < {self.extraction_threshold:.2f}) on key clauses."
            )
            flags.append("Ambiguous contract phrasing detected during clause extraction.")

        # 2. Rule match and statutory grounding evaluation
        rule_confidences: List[float] = []
        for v in violations:
            v_conf = v.get("confidence", 0.90)
            rule_confidences.append(v_conf)
            if v.get("severity") == "high" and v_conf < 0.85:
                reasons.append(
                    f"High-severity statutory violation '{v.get('violation_type', 'rule')}' has marginal confidence ({v_conf:.2f})."
                )

        avg_rule_conf = (sum(rule_confidences) / len(rule_confidences)) if rule_confidences else 0.90
        min_rule_conf = min(rule_confidences) if rule_confidences else 0.90

        # 3. Grounding / RAG Faithfulness integration
        faithfulness_conf = rag_faithfulness if rag_faithfulness is not None else 0.90
        if faithfulness_conf < 0.75:
            reasons.append(
                f"RAG statutory grounding score ({faithfulness_conf:.2f}) is below reliable threshold."
            )
            flags.append("Potential hallucination risk in statutory citations.")

        # 4. Check for Date Ambiguity (Hard Block)
        if has_ambiguous_dates:
            flags.append("Ambiguous date/trigger phrasing detected: blocks automated sign-off.")
            reasons.append("Date trigger or payment schedule contains ambiguous phrasing requiring reviewer validation.")

        # 5. Composite & Category-Gated Confidence
        composite_confidence = (
            (0.40 * avg_extraction_conf)
            + (0.35 * avg_rule_conf)
            + (0.25 * faithfulness_conf)
        )
        composite_confidence = round(max(0.0, min(1.0, composite_confidence)), 3)
        min_cat_conf = min(min_extraction_conf, min_rule_conf, faithfulness_conf)

        breakdown = CategoryBreakdown(
            extraction_conf=round(avg_extraction_conf, 3),
            rule_conf=round(avg_rule_conf, 3),
            grounding_conf=round(faithfulness_conf, 3),
            min_category_conf=round(min_cat_conf, 3),
        )

        # 6. Review Decision Routing with Hard Minimums
        needs_review = False
        auto_approved = False
        recommended_action = "auto_approve"

        # Gating rules:
        # - Composite confidence below threshold
        # - Any category below hard floor
        # - Any ambiguity flag or reason present
        # - Date ambiguity explicitly blocks auto-approval
        if (
            composite_confidence < self.determination_threshold
            or min_cat_conf < self.min_category_floor
            or len(reasons) > 0
            or has_ambiguous_dates
        ):
            needs_review = True
            if composite_confidence < 0.60 or min_cat_conf < 0.50:
                recommended_action = "escalate_legal"
                flags.append("Low confidence across key categories: legal counsel consultation strongly recommended.")
            else:
                recommended_action = "human_review"
        elif (
            composite_confidence >= self.auto_approve_threshold
            and min_cat_conf >= self.min_category_floor
            and not flags
            and not has_ambiguous_dates
        ):
            auto_approved = True
            recommended_action = "auto_approve"
        else:
            recommended_action = "auto_approve"

        log.info(
            "ConfidenceGate: conf=%.3f, min_cat=%.3f, needs_review=%s, action=%s, reasons_count=%d",
            composite_confidence, min_cat_conf, needs_review, recommended_action, len(reasons)
        )

        return ReviewDecision(
            needs_human_review=needs_review,
            review_reasons=reasons,
            confidence_score=composite_confidence,
            category_breakdown=breakdown,
            auto_approved=auto_approved,
            flags=flags,
            recommended_action=recommended_action,
        )
