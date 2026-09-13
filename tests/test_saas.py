"""
Integration and Unit Tests for SaaS Multi-Tenant Compliance Platform (Vasooli / Wemboo).
Tests:
- Database initialization (SaaS tables)
- Quota middleware enforcement & HTTP 429 limit check
- POST /api/analyse contract audit & structured AnalysisReport
- GET /api/analyses history retrieval
- POST /api/org/create & GET /api/org/{id}/usage
- Developer API key management (/api/keys)
- Razorpay webhook HMAC-SHA256 signature verification
"""

import hashlib
import hmac
import json
import pytest
from SQL.db import get_sqlite_connection, init_sqlite_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database tables are initialized before each test and reset quota."""
    init_sqlite_db("monarch.db")
    conn = get_sqlite_connection("monarch.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE organizations SET current_usage = 0")
    cursor.execute("DELETE FROM usage_events")
    conn.commit()
    conn.close()


def test_saas_database_schema():
    """Verify that all SaaS multi-tenant tables exist in local SQLite schema."""
    conn = get_sqlite_connection("monarch.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    expected_tables = {
        "organizations",
        "org_members",
        "usage_events",
        "api_keys",
        "plan_limits",
        "analyses_history",
    }
    assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"


def test_analyse_contract_violations(api_client):
    """Test POST /api/analyse correctly detects Section 15 & 16 violations."""
    payload = {
        "message": "Clause 14: Payment shall be disbursed in 90 days. No interest will be paid on delayed amounts.",
        "buyer_name": "Test Reliance Logistics",
        "contract_value": 2500000.0,
        "msme_type": "Small"
    }
    response = api_client.post("/api/analyse", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "report_id" in data
    assert data["buyer_name"] == "Test Reliance Logistics"
    assert data["compliance_score"] < 50  # High risk due to 90-day & no-interest clauses
    assert len(data["violations"]) >= 2

    # Check for Section 15 violation citation
    has_sec15 = any("Section 15" in v["cited_law"] for v in data["violations"])
    assert has_sec15, "Section 15 (45-day cap) violation must be cited"

    # Check for Section 16 violation citation
    has_sec16 = any("Section 16" in v["cited_law"] for v in data["violations"])
    assert has_sec16, "Section 16 (3x RBI Bank Rate interest) violation must be cited"

    # Check draft Samadhaan complaint
    assert data["draft_samadhaan_complaint"] is not None
    assert "SECTION 18 OF MSMED ACT" in data["draft_samadhaan_complaint"]


def test_list_analyses_history(api_client):
    """Test GET /api/analyses returns recent audit history."""
    response = api_client.get("/api/analyses")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_review_analysis_endpoint(api_client):
    """Test POST /api/analyses/{report_id}/review updates review status."""
    # 1. First create an analysis
    payload = {
        "message": "Payment within 90 days. No interest.",
        "buyer_name": "Review Test Corp",
        "contract_value": 500000.0,
    }
    create_res = api_client.post("/api/analyse", json=payload)
    assert create_res.status_code == 200
    report_id = create_res.json()["report_id"]

    # 2. Submit human review
    review_payload = {
        "action": "approved",
        "reviewer_name": "Senior Legal Counsel",
        "notes": "Verified against Section 15 and 16 requirements.",
    }
    review_res = api_client.post(f"/api/analyses/{report_id}/review", json=review_payload)
    assert review_res.status_code == 200
    review_data = review_res.json()
    assert review_data["review_decision"]["needs_human_review"] is False
    assert review_data["review_decision"]["recommended_action"] == "approved"
    assert any("Senior Legal Counsel" in flag for flag in review_data["review_decision"]["flags"])



def test_org_usage_endpoint(api_client):
    """Test GET /api/org/me/usage returns quota and plan info."""
    response = api_client.get("/api/org/me/usage")
    assert response.status_code == 200
    data = response.json()
    assert "plan" in data
    assert "monthly_quota" in data
    assert "current_usage" in data
    assert "plan_info" in data


def test_api_keys_lifecycle(api_client):
    """Test generating, listing, and revoking API keys."""
    # 1. Create key
    create_res = api_client.post("/api/keys", json={"name": "Test ERP Key"})
    assert create_res.status_code == 200
    key_data = create_res.json()
    assert key_data["status"] == "success"
    assert "key" in key_data
    assert key_data["key"].startswith("wm_live_")
    key_id = key_data["key_id"]

    # 2. List keys
    list_res = api_client.get("/api/keys")
    assert list_res.status_code == 200
    keys = list_res.json()
    assert any(k["id"] == key_id for k in keys)

    # 3. Revoke key
    del_res = api_client.delete(f"/api/keys/{key_id}")
    assert del_res.status_code == 200

    # 4. Confirm not in active list
    list_res2 = api_client.get("/api/keys")
    keys2 = list_res2.json()
    assert not any(k["id"] == key_id for k in keys2)


def test_billing_checkout(api_client):
    """Test POST /api/billing/checkout generates order metadata."""
    response = api_client.post("/api/billing/checkout", json={"plan": "pro"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "order_id" in data
    assert data["amount"] == 99900  # ₹999 in paise


def test_razorpay_webhook_hmac_verification(api_client):
    """Test Razorpay webhook rejects invalid signature and accepts valid signature."""
    secret = "sample_secret_key_123"
    payload = {
        "event": "payment.captured",
        "payload": {
            "order": {
                "entity": {
                    "notes": {"org_id": "org_default", "plan": "enterprise"}
                }
            }
        }
    }
    raw_body = json.dumps(payload).encode()

    # 1. Invalid signature should be rejected (HTTP 400)
    invalid_res = api_client.post(
        "/api/billing/webhook",
        content=raw_body,
        headers={"X-Razorpay-Signature": "invalid_signature_hex", "Content-Type": "application/json"}
    )
    assert invalid_res.status_code == 400

    # 2. Valid signature should be accepted (HTTP 200)
    valid_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    valid_res = api_client.post(
        "/api/billing/webhook",
        content=raw_body,
        headers={"X-Razorpay-Signature": valid_sig, "Content-Type": "application/json"}
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["status"] == "ok"


def test_quota_enforcement_and_pluralization(api_client):
    """
    Test that quota check correctly maps 'analysis' -> 'analyses' (5 limit on Free tier)
    and strictly raises HTTP 429 when the limit is exceeded.
    """
    from auth.cognito import UserContext
    from middleware.quota import check_quota, log_usage_event, get_user_org
    import asyncio

    test_user = UserContext(user_id="quota_test_user_777", email="quota@test.com", role="user")

    async def run_quota_test():
        org_id, plan = await get_user_org(test_user)
        assert plan == "free"

        # Log 5 usage events (the max free limit)
        for _ in range(5):
            await log_usage_event(org_id, test_user.user_id, "analysis")

        # 6th attempt MUST raise HTTPException 429
        with pytest.raises(Exception) as exc_info:
            await check_quota(test_user, "analysis")
        assert "429" in str(exc_info.value)

    asyncio.run(run_quota_test())


def test_idor_protection_on_org_endpoints(api_client):
    """
    Test IDOR protection: A user cannot access or invite members to an org they don't belong to.
    """
    from auth.cognito import UserContext
    from middleware.quota import verify_org_access
    import asyncio

    user_a = UserContext(user_id="user_alice_111", email="alice@test.com", role="user")
    user_b = UserContext(user_id="user_bob_222", email="bob@test.com", role="user")

    async def run_idor_test():
        # User A gets provisioned their own org
        org_a, _, _ = await verify_org_access(user_a)

        # User B attempts to access User A's org -> MUST be rejected with HTTP 403 Forbidden
        with pytest.raises(Exception) as exc_info:
            await verify_org_access(user_b, org_id=org_a)
        assert "403" in str(exc_info.value)

    asyncio.run(run_idor_test())


def test_smoothness_features_in_analysis(api_client):
    """Verify all 5 smoothness features are populated on POST /api/analyse report."""
    payload = {
        "message": "Clause 7.1: Payment within 90 days. No interest shall accrue. Buyer may cancel at sole discretion.",
        "buyer_name": "Mega Retail Ltd",
        "contract_value": 1000000.0,
    }
    res = api_client.post("/api/analyse", json=payload)
    assert res.status_code == 200
    data = res.json()

    # 1. Risk Score breakdown & disclaimer
    assert "risk_score_breakdown" in data and data["risk_score_breakdown"] is not None
    assert len(data["risk_score_breakdown"]) == 4
    assert data["risk_score_disclaimer"] == "Calculated from flagged statutory violations — not a probability estimate."
    assert data["compliance_score"] <= 35  # All deductions triggered

    # 2. Decision ladder
    assert "recommended_actions" in data and data["recommended_actions"] is not None
    assert len(data["recommended_actions"]) == 3
    assert data["contact_attempts"] == 0
    rec = [a for a in data["recommended_actions"] if a["is_recommended"]]
    assert len(rec) == 1
    assert rec[0]["action_id"] == "send_demand"

    # 3. Evidence offsets, page number & clause reference
    for v in data["violations"]:
        ev = v.get("evidence")
        if ev:
            assert "start_char" in ev
            assert "end_char" in ev
            assert ev["page_number"] is not None
            assert ev["page_number"] >= 1

    # 4. Financial compound breakdown
    assert "financial_breakdown" in data and data["financial_breakdown"] is not None
    assert data["financial_breakdown"]["calculation_method"] == "compound_monthly_rests"
    assert data["financial_breakdown"]["statutory_rate"] == 19.5

    # 5. Pre-signature negotiation recommendations
    assert "negotiation_recommendations" in data and data["negotiation_recommendations"] is not None
    assert len(data["negotiation_recommendations"]) >= 1
    for neg in data["negotiation_recommendations"]:
        assert "original_clause" in neg
        assert "compliant_replacement" in neg
        assert "risk_explanation" in neg


def test_contact_attempt_escalation(api_client):
    """Test POST /api/analyses/{report_id}/contact increments attempts and updates recommendation."""
    # Create analysis first
    payload = {
        "message": "Clause 3: Payment in 60 days.",
        "buyer_name": "Fast Delivery Corp",
        "contract_value": 500000.0,
    }
    create_res = api_client.post("/api/analyse", json=payload)
    assert create_res.status_code == 200
    report_id = create_res.json()["report_id"]

    # First contact attempt -> escalates from send_demand to formal_notice
    c1 = api_client.post(f"/api/analyses/{report_id}/contact")
    assert c1.status_code == 200
    c1_data = c1.json()
    assert c1_data["report_id"] == report_id
    assert c1_data["contact_attempts"] == 1
    assert c1_data["first_contact_date"] is not None
    rec1 = [a for a in c1_data["recommended_actions"] if a["is_recommended"]]
    assert len(rec1) == 1
    assert rec1[0]["action_id"] == "formal_notice"

    # Second contact attempt -> still formal notice since within 30 days
    c2 = api_client.post(f"/api/analyses/{report_id}/contact")
    assert c2.status_code == 200
    c2_data = c2.json()
    assert c2_data["contact_attempts"] == 2


def test_negotiate_endpoint(api_client):
    """Test POST /api/negotiate rewrites offending clause to compliant clause."""
    payload = {
        "clause_text": "Clause 12: Buyer shall make payment within 90 days. No interest shall accrue.",
        "buyer_name": "Acme Industries",
        "contract_value": 2000000.0,
    }
    res = api_client.post("/api/negotiate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check that payment or interest rewrite was produced
    types = [item["violation_type"] for item in data]
    assert "payment_cycle" in types or "interest_penalty" in types
    for item in data:
        assert len(item["compliant_replacement"]) > 20
        assert len(item["risk_explanation"]) > 10


