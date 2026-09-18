"""
Pytest Fixtures for Monarch Agent & API Test Suite.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from Agents.state import State


@pytest.fixture
def api_client():
    """FastAPI TestClient fixture (lazy import)."""
    from fastapi.testclient import TestClient
    from api import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_state() -> State:
    """Sample state dictionary for testing agent nodes."""
    from Agents.state import State as _State  # noqa: F811

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
