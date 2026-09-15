import pytest
from Agents.fairness import fairness_node


@pytest.mark.asyncio
async def test_flags_payment_cycle_over_45_days():
    state = {
        "extracted_clauses": [
            {
                "id": "clause_1",
                "raw_text": "Payment shall be made within 90 days from delivery.",
                "payment_days": 90,
                "has_penalty_interest": True,
                "has_unilateral_cancellation": False,
                "buyer_type": "large_enterprise",
            }
        ],
        "active_policy_pack": "msme_payment_terms",
    }
    result = await fairness_node(state)
    violations = result.get("fairness_violations", [])
    assert len(violations) >= 1
    assert violations[0]["clause_id"] == "clause_1"


@pytest.mark.asyncio
async def test_flags_missing_penalty_clause():
    state = {
        "extracted_clauses": [
            {
                "id": "clause_2",
                "raw_text": "Payment within 30 days. No penalty interest shall be charged.",
                "payment_days": 30,
                "has_penalty_interest": False,
                "has_unilateral_cancellation": False,
                "buyer_type": "large_enterprise",
            }
        ],
        "active_policy_pack": "msme_payment_terms",
    }
    result = await fairness_node(state)
    violations = result.get("fairness_violations", [])
    assert len(violations) >= 1


@pytest.mark.asyncio
async def test_flags_unilateral_cancellation():
    state = {
        "extracted_clauses": [
            {
                "id": "clause_3",
                "raw_text": "Buyer reserves right to cancel order without notice.",
                "payment_days": 30,
                "has_penalty_interest": True,
                "has_unilateral_cancellation": True,
                "buyer_type": "large_enterprise",
            }
        ],
        "active_policy_pack": "msme_payment_terms",
    }
    result = await fairness_node(state)
    violations = result.get("fairness_violations", [])
    assert len(violations) >= 1


@pytest.mark.asyncio
async def test_does_not_flag_compliant_clause():
    state = {
        "extracted_clauses": [
            {
                "id": "clause_4",
                "raw_text": "Payment in 30 days with interest per MSME Act.",
                "payment_days": 30,
                "has_penalty_interest": True,
                "has_unilateral_cancellation": False,
                "buyer_type": "large_enterprise",
            }
        ],
        "active_policy_pack": "msme_payment_terms",
    }
    result = await fairness_node(state)
    violations = result.get("fairness_violations", [])
    assert len(violations) == 0
