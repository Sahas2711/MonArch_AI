"""
Pytest Fixtures for Monarch Agent & API Test Suite.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from Agents.state import State


# ---------------------------------------------------------------------------
# LLM / Graph mock – prevents real API key requirement in CI.
# Applied automatically to every test that requests `api_client`.
# ---------------------------------------------------------------------------

def _make_mock_llm():
    """Return a MagicMock that satisfies common LangChain LLM call patterns."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="mock response"))
    mock.invoke = MagicMock(return_value=MagicMock(content="mock response"))
    mock.bind_tools = MagicMock(return_value=mock)
    mock.with_structured_output = MagicMock(return_value=mock)
    mock.stream = MagicMock(return_value=iter([MagicMock(content="mock")]))
    return mock


def _make_mock_graph():
    """Return a MagicMock that satisfies LangGraph compiled-graph call patterns."""
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value={"output": "mock graph output", "route": "planner"})
    mock.invoke = MagicMock(return_value={"output": "mock graph output", "route": "planner"})
    mock.astream = AsyncMock(return_value=iter([{"output": "mock"}]))
    return mock


@pytest.fixture(autouse=False)
def mock_llm_and_graph():
    """
    Stub out the LLM singleton and compiled graph so tests that spin up
    the FastAPI app via TestClient don't require live API keys in CI.
    """
    _mock_llm = _make_mock_llm()
    _mock_graph = _make_mock_graph()
    with (
        patch("utils.config._llm_instance", _mock_llm),
        patch("utils.config._active_model_name", "mock-model"),
        patch("Agents.graph._graph_instance", _mock_graph),
        patch("Agents.planner._planner_llm", _mock_llm),
        patch("Agents.router._router_llm", _mock_llm),
        patch("Agents.vision._vision_llm", _mock_llm),
    ):
        yield _mock_llm, _mock_graph


@pytest.fixture
def api_client(mock_llm_and_graph):
    """FastAPI TestClient fixture – LLM & graph are mocked for CI safety."""
    from fastapi.testclient import TestClient
    from api import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_state() -> State:
    """Sample state dictionary for testing agent nodes."""
    return {
        "messages": [],
        "user_inp": "What is Python?",
        "user_id": "test_user_123",
        "image_data": None,
        "output": "",
        "context": "",
        "route": "planner",
        "retry_count": 0,
        "reflection_feedback": None,
        "user_memories": ["User is a Senior Python Developer"],
    }
