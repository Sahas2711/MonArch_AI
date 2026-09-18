"""
Pytest Fixtures for Monarch Agent & API Test Suite.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
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
