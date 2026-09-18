"""
Unit tests for RAGAgentManager (ingestion & retrieval).
"""

import os
import tempfile
from RAG.manager import RAGAgentManager


def test_rag_manager_initial_state():
    manager = RAGAgentManager()
    ctx = manager.retrieve("anything")
    assert ctx == "(no relevant context found)"


def test_rag_manager_text_ingest_and_retrieve():
    manager = RAGAgentManager()
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Monarch platform is a multi-agent framework built with LangGraph and FastAPI.")
        tmp_path = f.name

    try:
        res = manager.ingest(tmp_path, user_id="user_test")
        assert res["status"] == "success"
        assert res["chunks_added"] >= 1

        context = manager.retrieve("What framework is Monarch built with?", user_id="user_test")
        assert "LangGraph" in context
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
