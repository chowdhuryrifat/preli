import json
import sys
import time
import requests

BASE_URL = "http://localhost:8000"

ALLOWED_EVIDENCE_VERDICT = {"consistent", "inconsistent", "insufficient_data"}
ALLOWED_CASE_TYPE = {
    "wrong_transfer", "payment_failed", "refund_request", "duplicate_payment",
    "merchant_settlement_delay", "agent_cash_in_issue", "phishing_or_social_engineering", "other",
}
ALLOWED_SEVERITY = {"low", "medium", "high", "critical"}
ALLOWED_DEPARTMENT = {
    "customer_support", "dispute_resolution", "payments_ops",
    "merchant_operations", "agent_operations", "fraud_risk",
}
REQUIRED_FIELDS = [
    "ticket_id", "relevant_transaction_id", "evidence_verdict", "case_type",
    "severity", "department", "agent_summary", "recommended_next_action",
    "customer_reply", "human_review_required",
]


def test_health():
    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    assert resp.status_code == 200, f"health: expected 200, got {resp.status_code}"
    assert resp.json() == {"status": "ok"}, f"health: unexpected body: {resp.text}"
    print("  PASS  /health")


def test_analyze_ticket(case):
    case_id = case.get("id", "?")
    label = case.get("label", "")
    inp = case["input"]

    start = time.time()
    resp = requests.post(f"{BASE_URL}/analyze-ticket", json=inp, timeout=30)
    elapsed = time.time() - start
    data = resp.json()

    fail = []

    if resp.status_code != 200:
        fail.append(f"status {resp.status_code}")

    for field in REQUIRED_FIELDS:
        if field not in data:
            fail.append(f"missing field: {field}")

    for field in ["evidence_verdict", "case_type", "severity", "department"]:
        val = data.get(field)
        allowed = {
            "evidence_verdict": ALLOWED_EVIDENCE_VERDICT,
            "case_type": ALLOWED_CASE_TYPE,
            "severity": ALLOWED_SEVERITY,
            "department": ALLOWED_DEPARTMENT,
        }[field]
        if val not in allowed:
            fail.append(f"invalid {field}: {val!r}")

    if fail:
        print(f"  FAIL  {case_id} ({label}): {', '.join(fail)} ({elapsed:.2f}s)")
    else:
        print(f"  PASS  {case_id} ({label}) ({elapsed:.2f}s)")


def main():
    print(f"Testing against {BASE_URL}\n")

    try:
        test_health()
    except Exception as e:
        print(f"  FAIL  /health: {e}")
        sys.exit(1)

    print()

    with open("docs/SUST_Preli_Sample_Cases.json", encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    for case in cases:
        test_analyze_ticket(case)

    print("\nDone.")


if __name__ == "__main__":
    main()
