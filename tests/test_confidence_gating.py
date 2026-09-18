"""
Unit tests for Category-Gated Confidence and Ambiguity Blocking.
"""

from pipeline.confidence import ConfidenceGate
from pipeline.extractor import ExtractedClause


def test_ambiguous_date_blocks_auto_approval():
    gate = ConfidenceGate()
    clauses = [
        ExtractedClause(
            clause_id="C1",
            clause_type="payment_terms",
            raw_text="Payment within 30 days of client approval.",
            confidence=0.98,
        )
    ]
    decision = gate.evaluate(clauses, violations=[], has_ambiguous_dates=True)
    assert decision.auto_approved is False
    assert decision.needs_human_review is True
    assert any("Ambiguous date" in f for f in decision.flags)


def test_high_average_with_one_low_category_blocks_auto_approval():
    gate = ConfidenceGate()
    clauses = [
        ExtractedClause(
            clause_id="C1",
            clause_type="payment_terms",
            raw_text="Payment in 90 days.",
            confidence=0.99,
        )
    ]
    decision = gate.evaluate(clauses, violations=[], rag_faithfulness=0.40)
    assert decision.auto_approved is False
    assert decision.needs_human_review is True
    assert decision.category_breakdown.min_category_conf <= 0.40


def test_clean_compliant_auto_approves():
    gate = ConfidenceGate()
    clauses = [
        ExtractedClause(
            clause_id="C1",
            clause_type="payment_terms",
            raw_text="Payment in 30 days.",
            confidence=0.99,
        )
    ]
    decision = gate.evaluate(clauses, violations=[], rag_faithfulness=0.98, has_ambiguous_dates=False)
    assert decision.auto_approved is True
    assert decision.needs_human_review is False
    assert decision.recommended_action == "auto_approve"
