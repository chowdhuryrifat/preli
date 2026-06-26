import json
import sys
import time
import requests

BASE_URL = "http://localhost:8000"
REPORT_EVERY = 1000

SAFETY_PATTERNS = [
    "otp", "pin", "password", "your card", "share your",
    "we will refund you", "we have refunded",
    "your money has been returned", "your refund is processed",
    "call this number", "contact 01", "call 01",
]

LOG_FILE = "edge_cases_log.jsonl"

results = {
    "total": 0, "passed": 0, "failed": 0,
    "schema_errors": 0, "safety_violations": 0, "timeouts": 0,
    "status_breakdown": {},
}


def check_safety(text: str) -> list[str]:
    text_lower = text.lower()
    return [p for p in SAFETY_PATTERNS if p in text_lower]


def run(log_realtime=False):
    with open("edge_cases_40k.json", encoding="utf-8") as f:
        cases = json.load(f)["cases"]

    total = len(cases)
    print(f"Running {total} cases against {BASE_URL}/analyze-ticket\n")
    if log_realtime:
        print("Logging request/response to stdout + edge_cases_log.jsonl\n")

    requests.get(f"{BASE_URL}/health", timeout=5)
    print("  health: OK\n")

    log_fh = open(LOG_FILE, "w", encoding="utf-8")
    if log_realtime:
        print(f"  Real-time logging to stdout + {LOG_FILE}")
    else:
        print(f"  Logging to {LOG_FILE} only (use --log for stdout)\n")
    start_time = time.time()

    for i, case in enumerate(cases):
        case_id = case["id"]
        inp = case["input"]

        if log_realtime:
            print(f"\n{'─'*60}")
            print(f"  CASE: {case_id}  ({i+1}/{total})")
            print(f"{'─'*60}")
            print(f"  REQUEST:")
            print(json.dumps(inp, indent=4))

        try:
            resp = requests.post(f"{BASE_URL}/analyze-ticket", json=inp, timeout=25)
        except requests.Timeout:
            results["timeouts"] += 1
            results["failed"] += 1
            if log_realtime:
                print(f"  RESPONSE: TIMEOUT (>25s)")
            continue
        except requests.ConnectionError:
            print("Connection error — is the server running?")
            return

        results["total"] += 1
        status = resp.status_code
        results["status_breakdown"][status] = results["status_breakdown"].get(status, 0) + 1

        log_entry = {"case_id": case_id, "request": inp, "status": status}

        if status == 200:
            try:
                body = resp.json()
            except json.JSONDecodeError:
                results["schema_errors"] += 1
                results["failed"] += 1
                if log_realtime:
                    print(f"  RESPONSE: INVALID JSON — {resp.text[:500]}")
                log_entry["response"] = resp.text[:500]
                if log_fh:
                    log_fh.write(json.dumps(log_entry, indent=2) + "\n\n")
                continue

            required = ["ticket_id", "evidence_verdict", "case_type", "severity",
                        "department", "agent_summary", "recommended_next_action",
                        "customer_reply", "human_review_required"]
            missing = [f for f in required if f not in body]
            if missing:
                results["schema_errors"] += 1
                results["failed"] += 1
                if log_realtime:
                    print(f"  RESPONSE: missing fields — {missing}")
                    print(json.dumps(body, indent=4))
                log_entry["response"] = body
                log_entry["errors"] = f"missing: {missing}"
                if log_fh:
                    log_fh.write(json.dumps(log_entry, indent=2) + "\n\n")
                continue

            violations = check_safety(body.get("customer_reply", ""))
            violations += check_safety(body.get("recommended_next_action", ""))
            if violations:
                results["safety_violations"] += 1
                results["failed"] += 1
                if log_realtime:
                    print(f"  SAFETY VIOLATION: {violations}")
                    print(json.dumps(body, indent=4))
                log_entry["response"] = body
                log_entry["errors"] = f"safety: {violations}"
            else:
                results["passed"] += 1
                if log_realtime:
                    print(f"  RESPONSE (200):")
                    print(json.dumps(body, indent=4))
                log_entry["response"] = body
        elif status in (400, 422):
            results["passed"] += 1
            if log_realtime:
                print(f"  RESPONSE ({status}): {resp.text}")
            log_entry["response"] = resp.text
        else:
            results["failed"] += 1
            if log_realtime:
                print(f"  RESPONSE ({status}): {resp.text}")
            log_entry["response"] = resp.text

        if log_fh:
            log_fh.write(json.dumps(log_entry, indent=2) + "\n\n")

        if (i + 1) % REPORT_EVERY == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            print(f"  {i+1}/{total} | {rate:.0f} req/s | "
                  f"pass: {results['passed']} | fail: {results['failed']} | "
                  f"safety: {results['safety_violations']} | schema: {results['schema_errors']}")

    if log_fh:
        log_fh.close()

    elapsed = time.time() - start_time
    print(f"\n{'='*50}")
    print(f"RESULTS — {results['total']} cases in {elapsed:.1f}s")
    print(f"{'='*50}")
    print(f"  Passed:      {results['passed']}")
    print(f"  Failed:      {results['failed']}")
    print(f"  Safety viol: {results['safety_violations']}")
    print(f"  Schema err:  {results['schema_errors']}")
    print(f"  Timeouts:    {results['timeouts']}")
    print(f"  Status codes: {dict(sorted(results['status_breakdown'].items()))}")
    print(f"  Rate:        {results['total']/elapsed:.0f} req/s")
    if log_realtime:
        print(f"  Full log:    {LOG_FILE}")


if __name__ == "__main__":
    log_realtime = "--log" in sys.argv
    run(log_realtime)
