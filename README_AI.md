# QueueStorm AI Text Generation Module

## Overview

The AI Text Generation module is the final stage of the QueueStorm investigation pipeline. It receives a validated `TicketInput` (user complaint + metadata) and a `ReasoningResult` (from the reasoning engine) and produces three safe, professional text outputs:

- **agent_summary** — concise summary for the support agent
- **recommended_next_action** — the single next operational step
- **customer_reply** — safe, language-appropriate reply to the customer

## How `text_engine` works

1. A `TicketInput` and `ReasoningResult` are passed to `generate(ticket, reasoning)`.
2. The engine finds the relevant transaction from `ticket.transaction_history` using `reasoning.relevant_transaction_id`.
3. A template context is built containing transaction details, case metadata, language, and user type.
4. The appropriate template set is selected based on `reasoning.case_type`.
5. Three text outputs are generated: agent_summary, recommended_next_action, customer_reply.
6. **Every output is passed through `safety_check`** before being returned as a `GeneratedText` object.

### Supported case types

| Case Type | Description |
|---|---|
| `wrong_transfer` | Customer sent money to wrong recipient |
| `payment_failed` | Payment failed but balance deducted |
| `refund_request` | Customer requests a refund |
| `duplicate_payment` | Same payment processed twice |
| `merchant_settlement_delay` | Merchant settlement delayed |
| `agent_cash_in_issue` | Cash-in through agent not reflected |
| `phishing_or_social_engineering` | Customer reports phishing attempt |
| `other` | Catch-all for vague/unrecognized cases |

## How `safety_check` works

`safety_check(text: str) -> str` is a mandatory output filter applied to every generated text. It uses regex pattern matching to detect and rewrite dangerous content:

### Detected patterns

| Pattern | Rewritten as |
|---|---|
| Requests for PIN, OTP, password, CVV, or card number | "please do not share your PIN, OTP, or password with anyone" |
| Refund promises ("we will refund", "refund has been processed") | "any eligible amount will be returned through official channels" |
| Reversal promises ("we will reverse", "transaction will be reversed") | "the transaction will be reviewed for possible reversal" |
| Account unblock promises ("we will unblock") | "your account will be reviewed by our team" |
| Third-party contact instructions with phone numbers | "use official support channels for assistance" |

The filter has a secondary safety check: if the matched text is already preceded by a safe prefix (e.g., "please do not", "we never", "under no circumstances"), it is left unchanged.

## Supported languages

| Language code | Description |
|---|---|
| `en` | English (default) |
| `bn` | Bangla — customer_reply is generated in Bengali script |
| `mixed` | Banglish — customer_reply mixes English and Bangla naturally |

Agent summary and recommended next action remain in English regardless of language setting, as they are internal tools for support agents.

## Prompt injection defense

The prompt templates in `prompt_templates.py` are designed for LLM-based text generation and include:

1. **System prompt hardening** — clearly marks the complaint text as untrusted user input
2. **Rule enforcement** — explicit instructions to never follow embedded instructions
3. **Injection resistance** — ignores requests to override rules, change persona, or output system prompts
4. **Safety constraints** — prohibits generating unsafe content (credential requests, refund promises, etc.)

The current implementation is rule-based and does not use an LLM. The prompt templates are provided for future LLM integration.

## Integration instructions

```python
from contract import TicketInput, ReasoningResult
from services.text_engine import generate

# Your reasoning engine produces these
ticket: TicketInput = ...
reasoning: ReasoningResult = ...

# Generate safe text
result = generate(ticket, reasoning)

# result.agent_summary      -> str
# result.recommended_next_action -> str
# result.customer_reply     -> str
```

### Files owned by this module

| File | Purpose |
|---|---|
| `app/services/text_engine.py` | Core text generation with templates |
| `app/services/safety.py` | Safety filter for output sanitization |
| `app/services/prompt_templates.py` | LLM prompt templates with injection defense |
| `tests/test_text_engine.py` | Tests for text generation |
| `tests/test_safety.py` | Tests for safety filter |

### Dependencies

- Python 3.12+
- pydantic (via `contract.py`)

No changes to teammate modules are required. Import `generate` from `services.text_engine` directly.

## Known limitations

- The rule-based template system does not generate dynamic responses; it selects from predefined templates.
- Bangla and Banglish templates are hand-crafted and may not cover all conversational nuances.
- LLM integration requires prompt templates from `prompt_templates.py`; the current implementation is fully rule-based.
- Safety filter uses regex and may have false positives/negatives for edge-case phrasing.
