"""
Unit & Integration tests for Phase 3 (Advanced Agent Intelligence: Tools, ReAct Planner, Agentic RAG, Code Executor, Parallel Fan-Out).
"""

import pytest
from Agents.tools.calculator import calculator_tool
from Agents.tools.code_executor import code_executor_tool
from Agents.tools.datetime_tool import datetime_tool
from Agents.tools.memory_tool import add_memory_tool, search_memories_tool
from RAG.query_engine import decompose_query, hypothetical_answer, rewrite_query


def test_calculator_tool():
    res = calculator_tool.invoke({"expression": "(10 + 20) * 3"})
    assert "90" in res


def test_datetime_tool():
    res = datetime_tool.invoke({})
    assert "UTC Time" in res


def test_memory_tools():
    add_res = add_memory_tool.invoke({"user_id": "test_phase3_user", "fact": "User prefers TypeScript"})
    assert "Successfully stored" in add_res

    search_res = search_memories_tool.invoke({"user_id": "test_phase3_user"})
    assert "TypeScript" in search_res


def test_code_executor_tool():
    res = code_executor_tool.invoke({"code": "print(2 + 2)"})
    assert "4" in res


@pytest.mark.asyncio
async def test_query_engine_functions():
    decomposed = await decompose_query("Compare the methodology in section 3 with the experimental results in section 5")
    assert isinstance(decomposed, list)
    assert len(decomposed) >= 1

    hypo = await hypothetical_answer("How does LangGraph state checkpointing work?")
    assert isinstance(hypo, str)
    assert len(hypo) > 5

    rewritten = await rewrite_query("What is Python?", "Previous answer lacked depth.")
    assert isinstance(rewritten, str)
