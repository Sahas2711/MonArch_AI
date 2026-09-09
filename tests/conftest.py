"""
Pytest Fixtures for Monarch Agent & API Test Suite.
"""

import pytest
from fastapi.testclient import TestClient
from api import app
from Agents.state import State


@pytest.fixture
def api_client():
    """FastAPI TestClient fixture."""
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
