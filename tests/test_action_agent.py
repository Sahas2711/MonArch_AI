import pytest
from Agents.action import action_node


@pytest.mark.asyncio
async def test_action_node_generates_drafts():
    state = {
        "fairness_violations": [
            {
                "clause_id": "clause_1",
                "clause_text": "Payment shall be released within 90 days.",
                "cited_law": "MSME Development Act 2006, Section 15",
            }
        ]
    }
    result = await action_node(state)
    drafts = result.get("action_drafts", [])
    assert len(drafts) == 1
    assert "Section 18" in drafts[0] or "MSMED Act" in drafts[0] or "Form 1" in drafts[0] or "Payment" in drafts[0]


@pytest.mark.asyncio
async def test_action_node_empty_violations():
    state = {"fairness_violations": []}
    result = await action_node(state)
    drafts = result.get("action_drafts", [])
    assert len(drafts) == 0
    assert "No violations" in result.get("output", "")
