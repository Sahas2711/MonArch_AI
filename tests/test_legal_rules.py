"""
Unit tests for Hardened Legal Rules and Cautious Output Wording.
"""

from datetime import date
from vasooli.domain.enums import DecisionOutcome, FactStatus, FactType, PaymentBasis
from vasooli.domain.models import EvidenceItem, ExtractedFact
from vasooli.policy.evaluator import PolicyEvaluator


def _create_mock_evidence(text: str = "Evidence text") -> EvidenceItem:
    return EvidenceItem(
        evidence_id="E-MOCK-01",
        source_document_id="DOC-01",
        source_text=text,
        start_char=0,
        end_char=len(text),
    )


def test_section_15_written_agreement_vs_no_agreement():
    evaluator = PolicyEvaluator()

    # Case 1: Written agreement, 30 days -> compliant
    fact_written_30 = ExtractedFact(
        fact_id="F-01",
        fact_type=FactType.PAYMENT_TERM,
        value={"days": 30, "has_written_agreement": True},
        evidence=_create_mock_evidence(),
        confidence=0.95,
        status=FactStatus.DEFINITIVE,
    )
    decisions = evaluator.evaluate([fact_written_30])
    assert len(decisions) == 1
    assert decisions[0].decision == DecisionOutcome.NOT_TRIGGERED

    # Case 2: No written agreement, 30 days -> breaches 15-day limit
    fact_no_written_30 = ExtractedFact(
        fact_id="F-02",
        fact_type=FactType.PAYMENT_TERM,
        value={"days": 30, "has_written_agreement": False},
        evidence=_create_mock_evidence(),
        confidence=0.95,
        status=FactStatus.DEFINITIVE,
    )
    decisions2 = evaluator.evaluate([fact_no_written_30])
    assert any(d.decision == DecisionOutcome.TRIGGERED for d in decisions2)
    assert any("absence of written agreement" in d.explanation for d in decisions2)


def test_section_15_delayed_buyer_approval_trigger_is_inconclusive():
    evaluator = PolicyEvaluator()
    fact_amb = ExtractedFact(
        fact_id="F-03",
        fact_type=FactType.PAYMENT_TERM,
        value={"days": 30, "basis": PaymentBasis.BUYER_APPROVAL},
        evidence=_create_mock_evidence(),
        confidence=0.70,
        status=FactStatus.AMBIGUOUS,
        inconclusive_reason="Payment subject to buyer signoff without deadline",
    )
    decisions = evaluator.evaluate([fact_amb])
    assert len(decisions) == 1
    assert decisions[0].decision == DecisionOutcome.INCONCLUSIVE
    assert "ambiguous or delayed trigger" in decisions[0].explanation


def test_section_16_below_statutory_rate():
    evaluator = PolicyEvaluator()
    # 6% p.a. provided in contract when 3x RBI rate is 19.5%
    fact_interest_low = ExtractedFact(
        fact_id="F-04",
        fact_type=FactType.INTEREST_CLAUSE,
        value={"interest_provided": True, "interest_rate_percent": 6.0},
        evidence=_create_mock_evidence(),
        confidence=0.90,
        status=FactStatus.DEFINITIVE,
    )
    decisions = evaluator.evaluate([fact_interest_low])
    assert len(decisions) == 1
    assert decisions[0].decision == DecisionOutcome.TRIGGERED
    assert "below statutory minimum" in decisions[0].explanation


def test_contract_act_cautious_wording():
    evaluator = PolicyEvaluator()
    fact_cancel = ExtractedFact(
        fact_id="F-05",
        fact_type=FactType.CANCELLATION_CLAUSE,
        value={"is_unilateral": True},
        evidence=_create_mock_evidence(),
        confidence=0.92,
        status=FactStatus.DEFINITIVE,
    )
    decisions = evaluator.evaluate([fact_cancel])
    assert len(decisions) == 1
    assert decisions[0].decision == DecisionOutcome.TRIGGERED
    assert "Potentially unfair or legally reviewable" in decisions[0].explanation
    assert "legally unenforceable" not in decisions[0].explanation.lower()
