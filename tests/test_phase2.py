"""
Unit & Integration tests for Phase 2 (AWS Infrastructure & Document Management Endpoints).
"""

import pytest
from storage.s3_manager import s3_manager
from utils.config import get_secret


def test_s3_manager_local_fallback():
    res = s3_manager.upload_document("non_existent_file.txt", "file.txt", user_id="user_test")
    assert "doc_id" in res
    assert "s3_key" in res


def test_get_secret_fallback():
    secret = get_secret("TEST_SECRET", "PATH")
    assert isinstance(secret, str)


def test_list_and_delete_documents_api(api_client):
    # Test GET documents endpoint
    res_get = api_client.get("/api/documents/test_user_123")
    assert res_get.status_code == 200
    data = res_get.json()
    assert "document_count" in data
    assert data["user_id"] == "test_user_123"

    # Test DELETE documents endpoint
    res_del = api_client.delete("/api/documents/test_user_123")
    assert res_del.status_code == 200
    del_data = res_del.json()
    assert del_data["status"] == "success"
    assert del_data["user_id"] == "test_user_123"
