"""
Unit & Integration tests for Phase 4 (Enterprise Security, Auth, RBAC, Output Safety, Audit Logging & GDPR Data Erasure).
"""

import pytest
from auth.cognito import verify_jwt_token
from auth.rbac import require_role, Role
from guardrails.input_guard import is_valid_luhn, mask_pii
from guardrails.output_guard import verify_output_safety, GuardrailConfig
from audit.logger import log_audit_event
from audit.data_retention import purge_user_data


def test_jwt_verification_dev():
    ctx = verify_jwt_token("")
    assert ctx.user_id == "dev_user_123"
    assert ctx.role == "admin"


def test_luhn_algorithm():
    # Standard test credit card number (valid Luhn)
    assert is_valid_luhn("4532015112830366")
    # Invalid card number
    assert not is_valid_luhn("4532015112830367")


def test_mask_pii_with_luhn():
    text = "Card: 4532-0151-1283-0366 and Phone: 555-123-4567"
    masked = mask_pii(text)
    assert "[CARD_REDACTED]" in masked
    assert "[PHONE_REDACTED]" in masked


def test_output_safety_guardrail():
    safe, reason = verify_output_safety("This is a clean AI output.")
    assert safe

    leaky_output = "Here is your API key: sk-abcdef12345678901234567890"
    is_safe, reason = verify_output_safety(leaky_output, GuardrailConfig(check_pii_leakage=True))
    assert not is_safe
    assert "leakage" in reason.lower()


def test_gdpr_data_erasure_api(api_client):
    res = api_client.delete("/api/user/test_gdpr_user/data")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["user_id"] == "test_gdpr_user"
