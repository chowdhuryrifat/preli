# QueueStorm Investigator

FastAPI service exposing `GET /health` and `POST /analyze-ticket` for the QueueStorm hackathon preliminary round.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Override port with `$env:PORT=8080` (default 8000).

## Endpoints

| Method | Path              | Description                        |
|--------|-------------------|------------------------------------|
| GET    | `/health`         | Returns `{"status":"ok"}`          |
| POST   | `/analyze-ticket` | Accepts `TicketInput`, returns `FinalResponse` |

Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs)

## Project Structure

```
main.py                    FastAPI app with routes + error handling
contract.py                Shared Pydantic models (locked with team)
reasoning/                 Evidence reasoning engine
├── __init__.py            Exports analyze()
├── constants.py           Weights, thresholds, keywords, mappings
├── helpers.py             12+ pure helper functions
├── reasoning_engine.py    analyze() orchestrator
└── WORK.md                Module docs
app/                       Application package
└── services/              Text generation + safety services
    ├── text_engine.py     Template-based text generation (8 case types, 3 languages)
    ├── safety.py          Regex-based safety filter (credentials, promises, etc.)
    └── prompt_templates.py  LLM prompt templates for future integration
tests/                     Test suite
├── test_reasoning_engine.py    22 tests
├── test_text_engine.py         50+ tests (all case types × languages)
└── test_safety.py              50+ tests (safety patterns, edge cases)
Dockerfile                 Container image
test_endpoints.py          Judge-harness simulation against all 10 sample cases
run_edge_cases.py          40k edge case stress tester
generate_edge_cases.py     Edge case JSON generator
```

## Flow

```
POST /analyze-ticket
  → main.py validates input (400 on bad JSON, 422 on empty complaint)
  → reasoning.reasoning_engine.analyze(ticket)   → ReasoningResult
  → app.services.text_engine.generate(ticket, reasoning) → GeneratedText
  → main.py merges into FinalResponse
  → JSON 200 (or 500 {"error":"internal_error"} on unexpected failure)
```

## Run Tests

```bash
python -m pytest tests/ -v
```

## Simulate Judge Harness

```bash
python test_endpoints.py
```

## Edge Case Stress Test

Generate 40k edge cases, then run against a running server:

```bash
python generate_edge_cases.py
python run_edge_cases.py [--log]   # --log for real-time stdout output
```
