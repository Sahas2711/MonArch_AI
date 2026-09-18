"""
Tests for ComplianceScorer and ConfidenceGate.
"""

import pytest
from pipeline.extractor import ExtractedClause
from pipeline.scorer import ComplianceScorer
from pipeline.confidence import ConfidenceGate


def test_compliance_scorer_full_violation():
    scorer = ComplianceScorer()
    violations = [
        {"violation_type": "payment_cycle"},
        {"violation_type": "interest_penalty"},
        {"violation_type": "tax_disallowance"},
        {"violation_type": "unilateral_cancellation"},
    ]
    clauses = [
        ExtractedClause(
            clause_id="c1",
            clause_type="payment_terms",
            raw_text="Payment in 90 days",
            payment_days=90,
            confidence=0.95,
        )
    ]
    res = scorer.calculate_score(violations=violations, clauses=clauses, contract_value=1000000.0)
    assert res.score == 30
    assert res.risk_level == "critical"
    assert res.tax_disallowance_applicable is True
    assert res.statutory_exposure_estimate > 0


def test_compliance_scorer_compliant():
    scorer = ComplianceScorer()
    violations = []
    clauses = [
        ExtractedClause(
            clause_id="c1",
            clause_type="payment_terms",
            raw_text="Payment in 30 days",
            payment_days=30,
            has_penalty_interest=True,
            confidence=0.95,
        )
    ]
    res = scorer.calculate_score(violations=violations, clauses=clauses, contract_value=1000000.0)
    assert res.score == 100
    assert res.risk_level == "low"
    assert res.tax_disallowance_applicable is False
    assert res.statutory_exposure_estimate == 0.0


def test_confidence_gate_high_confidence():
    gate = ConfidenceGate()
    clauses = [
        ExtractedClause(
            clause_id="c1",
            clause_type="payment_terms",
            raw_text="Payment within 90 days",
            payment_days=90,
            confidence=0.95,
        )
    ]
    violations = [{"violation_type": "payment_cycle", "confidence": 0.95}]
    res = gate.evaluate(clauses=clauses, violations=violations, rag_faithfulness=0.95)
    assert res.confidence_score >= 0.90
    assert res.needs_human_review is False
    assert res.recommended_action == "auto_approve"


def test_confidence_gate_low_confidence_triggers_review():
    gate = ConfidenceGate()
    clauses = [
        ExtractedClause(
            clause_id="c1",
            clause_type="general",
            raw_text="Payment as agreed separately",
            confidence=0.45,
        )
    ]
    violations = []
    res = gate.evaluate(clauses=clauses, violations=violations, rag_faithfulness=0.60)
    assert res.needs_human_review is True
    assert len(res.review_reasons) > 0
