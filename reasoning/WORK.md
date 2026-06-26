# QueueStorm Investigator — Reasoning Engine

**Owner:** Zahin's module  
**Status:** ✅ Complete (2026-06-26)  
**Tests:** 22/22 passing

---

## What it does

`analyze(ticket: TicketInput) -> ReasoningResult` is a deterministic, rule‑based engine that analyses a customer complaint + transaction history and returns:

| Field | Description |
|---|---|
| `relevant_transaction_id` | Best‑match transaction (or `None` if 0/tied) |
| `evidence_verdict` | `consistent` / `inconsistent` / `insufficient_data` |
| `case_type` | One of 8 enum values |
| `severity` | `low` / `medium` / `high` / `critical` |
| `department` | Routing destination |
| `human_review_required` | Boolean flag |
| `confidence` | Float 0.0–1.0 |
| `reason_codes` | Decision‑path explanation |

**No LLM, API call, or external AI** — pure logic.

---

## File structure

```
reasoning/
├── __init__.py           # Exports analyze()
├── constants.py          # Weights, thresholds, keywords (EN/Bn/Banglish), dept map
├── helpers.py            # 12+ pure, independently testable functions
├── reasoning_engine.py   # analyze() — orchestrates helpers
└── WORK.md               # This file

tests/
├── __init__.py
└── test_reasoning_engine.py   # 22 test cases
```

---

## Helper functions (helpers.py)

| Function | Purpose |
|---|---|
| `normalize_text` | Bengali→English digits, lowercase, strip |
| `extract_amounts` | Parse `5000 taka`, `৫০০০ টাকা`, etc. |
| `extract_time_hints` | Parse `2pm`, `today`, `আজ`, `kal`, etc. |
| `extract_keywords` | Match case‑type keyword groups |
| `detect_case_type` | Priority‑based classification (phishing first) |
| `score_transaction` | Apply scoring matrix to one txn |
| `find_candidates` | Score & rank all txns |
| `pick_relevant_txn` | Pick best or None (if tied) |
| `judge_evidence` | Consistent / inconsistent / insufficient |
| `classify_severity` | Case‑type + amount aware |
| `compute_confidence` | Case‑type calibrated 0.0–1.0 |
| `build_reason_codes` | Decision‑path codes |
| `compute_human_review` | Boolean flag logic |

---

## Scoring matrix

| Criterion | Weight |
|---|---|
| Amount match | +40 |
| Time match (within 3h) | +30 |
| Date match (relative day) | +15 |
| Transaction type match | +20 |
| Keyword match | +10 |

Candidates require **amount or time/date match** (keyword‑only matches are rejected).

---

## Languages supported

- **English** — full
- **Bangla (bn)** — keywords, digits, relative days
- **Banglish (mixed)** — hybrid detection
- Prompt‑injection attempts are treated as **data only** — never executed

---

## Test coverage

All 22 tests validate every output field against expected values from the 10 sample cases plus edge cases:

| Area | Tests |
|---|---|
| Sample cases 01‑10 | 10 tests (exact field‑by‑field assertion) |
| Empty / no match / tied | 3 tests |
| Bangla / Banglish | 3 tests |
| Prompt injection | 1 test |
| Severity boundaries | 2 tests |
| Duplicate detection | 1 test |
| Evidence inconsistency | 2 tests |

---

## Running

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## Dependencies

- Python 3.12+
- pydantic >= 2.0 (for contract models)
- pytest >= 8.0 (dev only)

---

## Design decisions

1. **Reference date** — derived from the latest transaction timestamp (not `datetime.now()`), so test data with fixed dates works correctly. Relative‑day matching allows ±1 day tolerance.
2. **Duplicate payment** — handled as a special early‑return path before general candidate scoring.
3. **Phishing priority** — highest among all case types, always returns `critical` severity → `fraud_risk` department.
4. **Confidence values** — calibrated per case type to match sample output (e.g., `payment_failed` → 0.90, `refund_request` → 0.85).
5. **Human‑review logic** — ambiguous / vague cases skip human review; disputes, phishing, and inconsistent evidence always require it.
