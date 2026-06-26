# QueueStorm Investigator — Audit Report

**Repo:** `preli` (Bangla/Banglish/English support-ticket classifier)
**Audit date:** 2026-06-26
**Auditor:** Custom stress suite + full-codebase review
**Baseline:** 198/198 curated tests passing in 0.47s

---

## TL;DR

The reasoning core is solid: 7 case-types, deterministic scoring, prompt-injection
resistant, bilingual coverage is real. But the codebase has **3 crashes**, **4
localization/security gaps**, and **3 documentation lies** that should be fixed
before this goes near production. Priorities below.

| Severity | Count | Headline |
|---|---|---|
| 🔴 HIGH (crash / data loss) | 1 | README ghosts (#1, #2 fixed) |
| 🟠 MEDIUM (correctness gap) | 3 | No input sanitiser, no observability, hard-coded confidence (#1 fixed) |
| 🟡 LOW (polish) | 4 | Defensive template render, Unicode zero-width, no rate limiting, contract bounds |

---

## 🔴 HIGH #1 — Text-engine template crashes on missing context key  *(demoted to LOW #1)*

**Original finding:** `app/services/text_engine.py` `wrong_transfer` template
referenced `{counterparty_number}` and would raise `KeyError` for any row
missing the field.

**Resolution:** **false positive**. After grepping `app/services/text_engine.py`
the literal string `counterparty_number` does not appear in any production
template. The `KeyError` observed in the audit was caused by a probe script
that built its own template string using a field name I had invented.
The actual schema uses `{counterparty}` only.

**Action taken:** reclassified as **LOW #1 — defensive rendering**. The
recommendation to wrap `_render` in `str.format_map(SafeDict(...))` still
stands as cheap insurance against future template authors making the same
mistake. See "LOW #1" section.

---

## 🔴 HIGH #2 — `TransactionEntry.amount` is non-nullable  *(FIXED)*

**File:** `contract.py` line ~14: `amount: float`.

**Evidence:** probe `None amount raw model_validate` → `1 validation error for
TransactionEntry`. Real upstream feeds (CSV imports, ledger snapshots) routinely
contain NULL amounts for fee-only lines, reversal rows, and disputed holds.
Today they produce HTTP 422 instead of a graceful `insufficient_data` verdict.

**Fix shipped:**
1. `contract.py` — `amount: Optional[float] = None` (Pydantic v2).
2. `reasoning/helpers.py::score_transaction` — guards `if txn.amount is not None`
   around the amount-match branch so rows with NULL amounts no longer crash and
   never spuriously match `0.0` complaints.
3. `tests/test_contract.py` — 10 new regression tests covering None / missing /
   int / float / zero amount, plus an end-to-end `TicketInput` round-trip with
   a None-amount row, plus a `find_candidates` test that proves a None-amount
   row can still surface via date_match.

**Verification:** `pytest -q` → **220 passed in 0.39s** (198 original + 22 new).

---

## 🔴 HIGH #3 — `README.md` documents three files that don't exist

**Files claimed in README, missing from repo:**
- `test_endpoints.py`
- `run_edge_cases.py`
- `generate_edge_cases.py`

**Evidence:** file_search returns zero hits. New contributors following the
README hit `ModuleNotFoundError` immediately.

**Fix:** either (a) delete the references, or (b) commit the actual scripts.
The 27-case `custom_audit.py` written during this audit can be promoted to
`run_edge_cases.py` with a 1-line rename.

**Effort:** 5 min (option a) or 1 hr (option b — and recommended).

---

## 🟠 MEDIUM #1 — Safety filter does not cover Bangla credential requests  *(FIXED)*

**File:** `app/services/safety.py` line 10.

**Evidence (probe):**
```json
{"case": "Mixed scripts",
 "input": "PIN দিন এখনই",
 "output": "PIN দিন এখনই",          ← UNCHANGED, attacker phrase survives
 "safe_or_unchanged": true}
```

The regex `(?:PIN|OTP|password|CVV|...)` is ASCII-only. A fraudster's
mixed-script "OTP দিন" / Bengali digit version passes through unmodified.
The reasoning engine correctly classifies it as `phishing`, but the
**customer_reply template** is then rendered before the safety filter
(per `text_engine.generate()`) — so a localised phishing reply could leak
credential-prompting language to the customer.

**Fix shipped:** added a second pattern to `_DANGEROUS_PATTERNS` in
`app/services/safety.py` that handles three cases:
1. Bengali verb → Bengali credential (`দিন … পিন`, `দাও … ওটিপি`).
2. Bengali credential → Bengali verb (`পিন দিন`, `পাসওয়ার্ড বলুন`).
3. Latin credential → Bengali verb — mixed-script attacks (`PIN দিন`, `OTP দাও`).

A bonus fourth branch covers the possessive split `আপনার কার্ডের নাম্বার দিন`,
which the literal string `কার্ডের` breaks into two tokens.

Replacement text is Bengali: `অনুগ্রহ করে আপনার পিন, ওটিপি বা পাসওয়ার্ড কারো সাথে শেয়ার করবেন না`.

**Verification:** `tests/test_safety_bangla.py` — 12 new parametrized probes,
all passing. The ASCII path is preserved (regression test
`test_ascii_credential_still_caught`).

---

## 🟠 MEDIUM #2 — No input-layer prompt-injection / pre-processing defence

**File:** `app/main.py` + `reasoning/helpers.py::normalize_text`.

The reasoning engine is itself injection-safe (proven by the prompt-injection
probe — it correctly classified the case as `refund_request` based on the
data, ignored the instructions). However:

- No length cap before tokenization — the "Very long complaint" probe with
  4 KB of repeated text still reached `detect_case_type` and allocated a
  full normalise + keyword-extraction pass.
- No zero-width Unicode strip — probe "Zero-width chars" (`2000\u200b\u200d\u200c\u200d taka`)
  reached the engine and **matched** — lucky outcome, but a real attacker
  hiding text inside zero-width chars can defeat simple substring detectors.

**Fix:**
1. Add `MAX_COMPLAINT_CHARS = 4000` and truncate + flag at API boundary.
2. Strip `\u200b-\u200f\u2028-\u202f\ufeff` in `normalize_text`.

**Effort:** 1 hr.

---

## 🟠 MEDIUM #3 — No structured logging of reasoning path

`analyze()` returns `reason_codes` but nothing is logged. When production
gets a wrong decision, there is no trace of *why* it was made (which helper
fired, which candidate scored what).

**Fix:** add `logging.getLogger("reasoning").info(...)` calls inside the
helpers, gated on a `PRELI_DEBUG` env var so test output stays clean.

**Effort:** 2 hr.

---

## 🟠 MEDIUM #4 — Confidence is hard-coded per case-type, not signal-derived

**File:** `reasoning/reasoning_engine.py::compute_confidence`.

`wrong_transfer` returns `0.85` regardless of whether the match was exact
(amount+time+type) or weak (keyword-only). This contradicts `WORK.md` which
documents a calibrated formula.

**Fix:** implement the documented formula:
`0.5 + 0.5 * (score / MAX_SCORE)` for matched cases, `0.6` baseline for
insufficient.

**Effort:** 3 hr + regression test sweep.

---

## 🟡 LOW #1 — Defensive template rendering (formerly HIGH #1)

**File:** `app/services/text_engine.py` `_render`.

The original audit flagged a `{counterparty_number}` reference that turned
out to be a probe-script artifact, but the underlying recommendation is
still sound: wrap the format call in a `SafeDict` so any future template
author's typo degrades to `""` instead of raising `KeyError`.

```python
class SafeDict(dict):
    def __missing__(self, key): return ""
```

**Effort:** 5 min. **Risk:** zero.

---

## 🟡 LOW #2 — Bounded `float` fields in contract

`confidence: float`, `score: float` should be `confloat(ge=0, le=1)` /
`confloat(ge=0, le=115)` to catch invalid outputs at the boundary.

---

## 🟡 LOW #3 — Phone-number regex is locale-naïve

`safety.py` allows `+8801712345678` to pass through unchanged (probe
"Phone number leak"). Not a security bug — agent may legitimately need to
refer to a number — but a `MASK_PHONE` policy would prevent accidental PII
leakage to logs.

---

## 🟡 LOW #4 — Test fixtures reuse IDs (`_make_txn`) without namespace

Minor — won't affect test isolation today but if more audit suites are added
they'll collide.

---

## Custom audit coverage summary

27 probes executed, 0 uncaught exceptions after the signature fix. Behaviour
matrix:

| Probe | Engine result | Verdict |
|---|---|---|
| Bengali digit amount | matched TXN-BD1 | ✅ bilingual digit handling works |
| Injection in Bengali | correctly classified as refund | ✅ Bangla injection safe |
| Refund + phishing combined | phishing wins (priority chain works) | ✅ |
| Time-only match | matched TXN-T1 by morning-window | ✅ |
| Whitespace-only complaint | `other / insufficient` | ✅ graceful |
| Counterparty formatted `+880 1712 345678` | matched | ✅ fuzzy enough |
| Negative amount in history | no match | ✅ filter works |
| Zero amount | no match | ✅ filter works |
| Future-dated txn | matched (ref-date logic uses latest txn) | ✅ |
| Emoji noise | no match | ✅ emoji stripped |
| OTP mention → phishing | critical / fraud_risk | ✅ |
| 5-min duplicate | duplicate_payment detected | ✅ |
| 50-txn history, 1 match | insufficient_data (correct — no amount in complaint) | ✅ |
| Zero-width chars | matched | ⚠️ lucky, see MEDIUM #2 |
| Phishing + completed txn | critical / fraud_risk | ✅ priority holds |
| Bangla phishing | critical / fraud_risk | ✅ Bangla phishing regex works |
| `amount: None` raw | rejected by Pydantic | 🔴 see HIGH #2 |

---

## Recommended upgrade order

1. ~~**HIGH #1** (template keyerror)~~ — demoted to LOW #1 (was a probe artifact)
2. ~~**HIGH #2** (amount nullability)~~ — **FIXED** (contract.py + helpers.py + 10 regression tests)
3. **HIGH #3** (README ghosts) — 1 hr if promoting `custom_audit.py`
4. ~~**MEDIUM #1** (Bangla safety regex)~~ — **FIXED** (safety.py dual-pattern + 12 regression tests)
5. **MEDIUM #2** (input cap + zero-width strip) — 1 hr, ship this week
6. **MEDIUM #3** (structured logging) — 2 hr
7. **MEDIUM #4** (confidence formula) — 3 hr + regression sweep
8. LOW items in a single polish PR

**Total high-priority debt remaining:** ~3.5 hours → **~3 hours** after the
two shipped fixes.

---

## Fix-shipped summary (2026-06-26 follow-up)

| Finding | File | Change | Tests added |
|---|---|---|---|
| HIGH #2 | `contract.py`, `reasoning/helpers.py` | `amount: Optional[float] = None` + `score_transaction` None-guard | `tests/test_contract.py` (10 tests) |
| MEDIUM #1 | `app/services/safety.py` | New dual-order Bangla credential pattern (4 alternation branches) | `tests/test_safety_bangla.py` (12 tests) |

**Final pytest:** `220 passed in 0.39s` (was `198 passed in 0.47s`).