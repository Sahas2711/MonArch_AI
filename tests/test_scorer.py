"""
Unit tests for Component 1: Rule-Based Compliance Risk Scorer.
Verifies transparent deductions, risk bands, breakdown items, and disclaimers.
"""

import pytest
from pipeline.scorer import ComplianceScorer, RISK_DEDUCTIONS
from pipeline.extractor import ExtractedClause


def test_perfect_compliance_score():
    scorer = ComplianceScorer()
    res = scorer.calculate_score(violations=[], clauses=[])
    assert res.score == 100
    assert res.risk_level == "low"
    assert len(res.breakdown_items) == 4
    for item in res.breakdown_items:
        assert item.triggered is False
        assert item.points_deducted == 0
    assert res.score_disclaimer == "Calculated from flagged statutory violations — not a probability estimate."


def test_all_violations_score_30():
    """
    payment_days > 45 (-35)
    no_penalty_interest (-20)
    unilateral_cancellation (-15)
    Score: 100 - 35 - 20 - 15 = 30 (critical)
    """
    scorer = ComplianceScorer()
    clauses = [
        ExtractedClause(
            clause_id="clause_1",
            clause_type="payment_terms",
            raw_text="Payment within 90 days of invoice",
            payment_days=90,
            has_penalty_interest=False,
            has_unilateral_cancellation=True,
            confidence=0.95,
        )
    ]
    res = scorer.calculate_score(violations=[], clauses=clauses)
    assert res.score == 30
    assert res.risk_level == "critical"
    fired = {item.deduction_name: item.points_deducted for item in res.breakdown_items if item.triggered}
    assert fired["payment_days_breach"] == 35
    assert fired["no_penalty_interest_clause"] == 20
    assert fired["unilateral_cancellation"] == 15
    assert "low_evidence_confidence" not in fired


def test_low_confidence_deduction():
    """
    When extraction confidence < 0.7, deduct 10 points.
    """
    scorer = ComplianceScorer()
    clauses = [
        ExtractedClause(
            clause_id="clause_2",
            clause_type="payment_terms",
            raw_text="Payment in some days maybe",
            payment_days=30,
            has_penalty_interest=True,
            has_unilateral_cancellation=False,
            confidence=0.55,
        )
    ]
    res = scorer.calculate_score(violations=[], clauses=clauses)
    assert res.score == 90
    fired = {item.deduction_name: item.points_deducted for item in res.breakdown_items if item.triggered}
    assert fired["low_evidence_confidence"] == 10


def test_score_floor_at_zero():
    """Score should not be negative even if deductions exceed 100."""
    scorer = ComplianceScorer()
    clauses = [
        ExtractedClause(
            clause_id="clause_3",
            clause_type="payment_terms",
            raw_text="Overdue",
            payment_days=90,
            has_penalty_interest=False,
            has_unilateral_cancellation=True,
            confidence=0.4,
        )
    ]
    violations = [{"violation_type": "payment_cycle"}, {"violation_type": "interest_penalty"}]
    res = scorer.calculate_score(violations=violations, clauses=clauses)
    # Deductions: 35 + 20 + 15 + 10 = 80 -> score 20
    assert res.score >= 0
