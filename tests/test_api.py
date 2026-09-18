"""
Integration tests for FastAPI REST API endpoints.
"""

def test_health_check(api_client):
    response = api_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model" in data


def test_get_memories(api_client):
    response = api_client.get("/api/memories/test_user_999")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_add_memory(api_client):
    payload = {"user_id": "test_user_999", "content": "Prefers concise bullet points"}
    response = api_client.post("/api/memories", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "memory_id" in data
