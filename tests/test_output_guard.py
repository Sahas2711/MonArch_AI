import pytest
from guardrails.output_guard import verify_rag_faithfulness


@pytest.mark.asyncio
async def test_verify_rag_faithfulness_no_context():
    is_faithful, reason = await verify_rag_faithfulness(
        user_inp="What is the capital of France?",
        context="",
        output="Paris is the capital of France.",
    )
    assert is_faithful
    assert "No context" in reason


@pytest.mark.asyncio
async def test_verify_rag_faithfulness_empty_marker():
    is_faithful, reason = await verify_rag_faithfulness(
        user_inp="What is Python?",
        context="(no relevant context found)",
        output="Python is a programming language.",
    )
    assert is_faithful

