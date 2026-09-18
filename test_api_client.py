import requests
import json
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://localhost:8000"

def test_analyse():
    url = f"{BASE_URL}/api/analyse"
    payload = {
        "contract_text": "Clause 14.2: Payment shall be released within 90 days from the invoice date. Supplier agrees that no interest shall accrue on delayed payments. The buyer reserves the right to terminate the agreement unilaterally without compensation.",
        "buyer_name": "Tata Mega Projects Ltd",
        "contract_value": 1500000.0,
        "payment_date": "2026-09-15"
    }
    headers = {
        "Content-Type": "application/json",
        "X-Org-ID": "org_default"
    }
    
    print(f"📡 Sending POST request to {url} ...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        print(f"✅ Response Status: {response.status_code}")
        data = response.json()
        
        print("\n📊 Compliance Analysis Results:")
        print(f"  • Report ID: {data.get('report_id')}")
        print(f"  • Compliance Score: {data.get('compliance_score')} / 100")
        print(f"  • Risk Level: {str(data.get('risk_level')).upper()}")
        print(f"  • Violations Detected: {len(data.get('violations', []))}")
        
        # Financial Breakdown
        fin = data.get("financial_breakdown") or data.get("financial_summary") or {}
        principal = fin.get("principal") or fin.get("principal_amount", 0)
        interest = fin.get("interest_amount") or fin.get("estimated_interest_exposure", 0)
        rate = fin.get("statutory_rate") or fin.get("statutory_interest_rate_percent", 0)
        total = fin.get("total_recoverable", principal + interest)
        
        print("\n💰 Statutory Financial Calculation (MSMED Act Section 16):")
        print(f"  • Principal Invoice Amount: ₹{principal:,.2f}")
        print(f"  • Statutory Compound Interest: ₹{interest:,.2f}")
        print(f"  • Applicable Interest Rate: {rate}% p.a. (3x RBI Bank Rate)")
        print(f"  • Total Amount Recoverable: ₹{total:,.2f}")
        print(f"  • Section 43B(h) Tax Risk: {fin.get('tax_disallowance_risk', True)}")

        # Recommended Escalation Actions
        actions = data.get("recommended_actions", [])
        if actions:
            print("\n⚖️ Recommended Escalation Ladder (Decision Support):")
            for a in actions:
                rec_badge = "⭐ [RECOMMENDED]" if a.get("is_recommended") else "  [STAGE]"
                print(f"  {rec_badge} {a.get('label')} (Action: {a.get('action_id')}, Effort: {a.get('effort_level')})")
                print(f"     Why: {a.get('reason')}")

        return data
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection Error: The server is not running on {BASE_URL}.")
        print("👉 Start the server first with: .\\.venv\\Scripts\\uvicorn.exe api:app --host 0.0.0.0 --port 8000 --reload")
        return None

def test_negotiate():
    url = f"{BASE_URL}/api/negotiate"
    payload = {
        "clause_text": "Clause 14.2: Payment shall be released within 90 days from invoice date. Supplier waives any statutory interest on late payments.",
        "buyer_name": "Tata Mega Projects Ltd",
        "contract_value": 1500000.0
    }
    headers = {
        "Content-Type": "application/json",
        "X-Org-ID": "org_default"
    }
    print(f"\n📡 Sending POST request to {url} (Pre-Signature Negotiation) ...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        print(f"✅ Response Status: {response.status_code}")
        data = response.json()
        print("\n📝 Pre-Signature Negotiation Redlines Generated:")
        if isinstance(data, list):
            for idx, item in enumerate(data, 1):
                print(f"\n  [{idx}] Violation: {item.get('violation_type')}")
                print(f"      • Compliant Replacement:")
                print(f"        \"{item.get('compliant_replacement')}\"")
                print(f"      • Statutory & Commercial Rationale:")
                print(f"        {item.get('risk_explanation')}")
        else:
            print(f"  {data}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Server not reachable at {BASE_URL}.")

if __name__ == "__main__":
    print("=" * 60)
    print("👑 Monarch / Vasooli — End-to-End API Test")
    print("=" * 60)
    report = test_analyse()
    if report:
        test_negotiate()
