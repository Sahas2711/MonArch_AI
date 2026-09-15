"""
MSME Confidence Gate & Human-in-the-Loop Review Module.

Assesses determination confidence across extraction accuracy, policy matching,
and statutory citations to prevent hallucinated compliance determinations.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from pipeline.extractor import ExtractedClause
from utils.logger import log


class ReviewDecision(BaseModel):
    """Human-in-the-loop review routing decision with calibrated confidence."""
    needs_human_review: bool = Field(..., description="Whether determination requires human verification")
    review_reasons: List[str] = Field(default_factory=list, description="Specific triggers requiring human review")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Overall pipeline determination confidence (0-1)")
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
    """

    def __init__(
        self,
        extraction_threshold: float = 0.70,
        determination_threshold: float = 0.80,
        auto_approve_threshold: float = 0.95,
    ):
        self.extraction_threshold = extraction_threshold
        self.determination_threshold = determination_threshold
        self.auto_approve_threshold = auto_approve_threshold

    def evaluate(
        self,
        clauses: List[ExtractedClause],
        violations: List[Dict[str, Any]],
        rag_faithfulness: Optional[float] = None,
    ) -> ReviewDecision:
        """
        Evaluates extraction confidence and statutory findings.
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

        # 3. Grounding / RAG Faithfulness integration
        faithfulness_conf = rag_faithfulness if rag_faithfulness is not None else 0.90
        if faithfulness_conf < 0.75:
            reasons.append(
                f"RAG statutory grounding score ({faithfulness_conf:.2f}) is below reliable threshold."
            )
            flags.append("Potential hallucination risk in statutory citations.")

        # 4. Composite Confidence Score Calculation
        # Weights: 40% extraction, 35% rule matching, 25% statutory grounding
        composite_confidence = (
            (0.40 * avg_extraction_conf)
            + (0.35 * avg_rule_conf)
            + (0.25 * faithfulness_conf)
        )
        composite_confidence = round(max(0.0, min(1.0, composite_confidence)), 3)

        # 5. Review Decision Routing
        needs_review = False
        auto_approved = False
        recommended_action = "auto_approve"

        if composite_confidence < self.determination_threshold or len(reasons) > 0:
            needs_review = True
            if composite_confidence < 0.60:
                recommended_action = "escalate_legal"
                flags.append("Low overall confidence: legal counsel consultation strongly recommended.")
            else:
                recommended_action = "human_review"
        elif composite_confidence >= self.auto_approve_threshold and not flags:
            auto_approved = True
            recommended_action = "auto_approve"
        else:
            recommended_action = "auto_approve"

        log.info(
            "ConfidenceGate: conf=%.3f, needs_review=%s, action=%s, reasons_count=%d",
            composite_confidence, needs_review, recommended_action, len(reasons)
        )

        return ReviewDecision(
            needs_human_review=needs_review,
            review_reasons=reasons,
            confidence_score=composite_confidence,
            auto_approved=auto_approved,
            flags=flags,
            recommended_action=recommended_action,
        )
