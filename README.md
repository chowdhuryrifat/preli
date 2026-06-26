# QueueStorm Investigator

**Preliminary Round** — A deterministic ticket analysis engine that classifies, investigates, and responds to mobile financial service (MFS) support tickets across English, Bangla, and Banglish.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               Client / Judge                                │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │ POST /analyze-ticket  │ GET /health
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  API Layer (main.py)                                                        │
│  ┌───────────────┐  ┌───────────────────┐  ┌──────────────────────────────┐ │
│  │ Input         │  │ Validation        │  │ Response Assembly            │ │
│  │ (TicketInput) │──▶│ - JSON parse      │──▶│ FinalResponse from          │ │
│  │               │  │ - empty complaint  │  │ reasoning + text outputs     │ │
│  └───────────────┘  │ - Pydantic schema  │  └──────────────┬───────────────┘ │
│                     └───────────────────┘                   │                │
└──────────────────────────────────────────────────────────────┼────────────────┘
                               │                                │
                  ┌────────────▼────────────┐      ┌────────────▼────────────┐
                  │ Reasoning Engine        │      │ Text Generation Engine  │
                  │ (reasoning/)            │      │ (app/services/)         │
                  │                         │      │                         │
                  │ 1. Normalize complaint  │      │ 1. Match case template  │
                  │ 2. Extract amounts/time │      │ 2. Inject context vars  │
                  │ 3. Score transactions   │      │ 3. Select language      │
                  │ 4. Pick relevant txn    │──────│    (en/bn/mixed)        │
                  │ 5. Judge evidence       │      │ 4. Apply safety filter  │
                  │ 6. Detect case type     │      │ 5. Return GeneratedText │
                  │ 7. Classify severity    │      └────────────┬────────────┘
                  │ 8. Map department       │                   │
                  │ 9. Compute confidence   │                   │
                  │ 10. Build reason codes  │                   │
                  └─────────────────────────┘                   │
                               │                                │
                               ▼                                ▼
                  ┌──────────────────────────────────────────────────────────┐
                  │           Safety Filter (app/services/safety.py)         │
                  │   Regex-based sanitizer for credentials, promises,       │
                  │   phone numbers, and unguarded commitments.              │
                  │   Supports English + Bangla + mixed-script attacks.      │
                  └──────────────────────────────────────────────────────────┘
```

## Project Structure

```
├── main.py                     FastAPI application — routes, error handlers, response assembly
├── contract.py                 Shared Pydantic models — TicketInput, ReasoningResult, GeneratedText, FinalResponse
│
├── reasoning/                  Deterministic rule-based reasoning engine
│   ├── reasoning_engine.py     Orchestrator — analyze(ticket) → ReasoningResult
│   ├── helpers.py              20+ pure functions: scoring, classification, evidence judgment
│   └── constants.py            Weights, thresholds, department map, keyword sets
│
├── app/services/               Output generation and safety
│   ├── text_engine.py          Template-based multilingual text generation (8 case types × 3 languages)
│   ├── safety.py               Regex safety filter — detects and neutralises credential requests
│   └── prompt_templates.py     LLM prompt templates for future AI integration
│
├── tests/                      Comprehensive test suite
│   ├── test_reasoning_engine.py    22 tests covering all case types
│   ├── test_text_engine.py         50+ tests across templates and languages
│   ├── test_safety.py              50+ safety pattern tests
│   ├── test_safety_bangla.py       Bangla and mixed-script safety tests
│   └── test_contract.py            Pydantic model validation tests
│
├── Dockerfile                  Production container image (python:3.12-slim)
├── render.yaml                 Render.com hosting configuration
└── requirements.txt            Python dependencies
```

## Case Type Taxonomy

| Case Type | Severity | Department | Description |
|---|---|---|---|
| `wrong_transfer` | low–critical | dispute_resolution | Sent money to wrong recipient |
| `payment_failed` | high | payments_ops | Payment failed but balance deducted |
| `refund_request` | low | customer_support | Customer wants money back |
| `duplicate_payment` | high | payments_ops | Same payment processed twice |
| `merchant_settlement_delay` | medium | merchant_operations | Merchant settlement not received |
| `agent_cash_in_issue` | high | agent_operations | Cash-in not reflected in balance |
| `phishing_or_social_engineering` | critical | fraud_risk | Credential theft attempt |
| `other` | low | customer_support | Vague or unclassifiable complaint |

### Classification Pipeline

```
Complaint text
    │
    ▼
Normalize (Bengali digits → Latin, lowercase, collapse spaces)
    │
    ├── Phishing keywords?                  ═══▶ phishing_or_social_engineering
    ├── Wrong-transfer phrases?             ═══▶ wrong_transfer
    ├── Agent cash-in context?              ═══▶ agent_cash_in_issue
    ├── Merchant settlement context?        ═══▶ merchant_settlement_delay
    ├── Duplicate payment keywords?         ═══▶ duplicate_payment
    ├── Payment failed indicators?          ═══▶ payment_failed
    ├── Refund context?                     ═══▶ refund_request
    ├── Transfer context?                   ═══▶ wrong_transfer
    ├── Matched transaction type fallback   ═══▶ mapped by type
    └── No match                            ═══▶ other
```

## API

### `POST /analyze-ticket`

**Request**

```json
{
  "ticket_id": "TKT-001",
  "complaint": "I sent 5000 taka to the wrong number yesterday at 2pm",
  "language": "en",
  "channel": "in_app_chat",
  "user_type": "customer",
  "transaction_history": [
    {
      "transaction_id": "TXN-101",
      "timestamp": "2026-06-25T14:05:00Z",
      "type": "transfer",
      "amount": 5000.0,
      "counterparty": "019XXXXXXXX",
      "status": "completed"
    }
  ]
}
```

**Response**

```json
{
  "ticket_id": "TKT-001",
  "relevant_transaction_id": "TXN-101",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "medium",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports sending 5000 BDT via TXN-101 to 019XXXXXXXX, which they now believe was the wrong recipient. Recipient is unresponsive.",
  "recommended_next_action": "Verify TXN-101 details with the customer and initiate the wrong-transfer dispute workflow per policy.",
  "customer_reply": "We have noted your concern about transaction TXN-101. Please do not share your PIN or OTP with anyone. Our dispute team will review the case and contact you through official support channels.",
  "human_review_required": true,
  "confidence": 0.9,
  "reason_codes": ["wrong_transfer", "transaction_match", "dispute_initiated"]
}
```

### `GET /health`

```json
{ "status": "ok" }
```

## Transaction Scoring

Each candidate transaction is scored against the complaint using four weighted criteria:

| Criterion | Weight | Description |
|---|---|---|
| Amount match | 40 | Transaction amount matches complaint amount (±0.01) |
| Time/Date match | 30 | Transaction timestamp aligns with complaint time hints |
| Type match | 20 | Transaction type matches implied operation in complaint |
| Keyword match | 10 | Complaint contains case-type keywords |

Max score: **100**. Tied top scores are treated as ambiguous (`relevant_transaction_id: null`).

## Safety Filter

The `safety_check` function applies 10 regex patterns to sanitize generated text:

| Pattern | Replacement |
|---|---|
| Credential requests (en) | `"please do not share your PIN, OTP, or password with anyone"` |
| Credential requests (bn) | `"অনুগ্রহ করে আপনার পিন, ওটিপি বা পাসওয়ার্ড কারো সাথে শেয়ার করবেন না"` |
| Absolute refund promises | `"any eligible amount will be returned through official channels"` |
| Absolute reversal promises | `"the transaction will be reviewed for possible reversal"` |
| Unblock promises | `"your account will be reviewed by our team"` |
| Direct phone numbers | `"use official support channels for assistance"` |
| Third-party contact info | `"use official support channels for assistance"` |

Text already prefixed with a safety advisory (`"do not"`, `"never"`, `"please do not"`) is left untouched.

## Setup & Run

```bash
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Override port: `$env:PORT=8080` (default 8000).

## Test

```bash
python -m pytest tests/ -v
```

## Deploy

### Docker

```bash
docker build -t queuestorm-investigator .
docker run -p 8000:8000 queuestorm-investigator
```

### Render

The included `render.yaml` deploys via Docker. Create a **Blueprint** from this repo on Render.com — the service auto-builds and serves on port 8000 with `/health` monitoring.
