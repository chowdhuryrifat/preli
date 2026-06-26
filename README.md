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
reasoning/                 Zahin's module — evidence reasoning engine
├── __init__.py            Exports analyze()
├── constants.py           Weights, thresholds, keywords, mappings
├── helpers.py             12+ pure helper functions
├── reasoning_engine.py    analyze() orchestrator
└── WORK.md                Module docs
text_engine.py             Adil's module — text generation + safety filter
tests/                     Test suite
├── test_reasoning_engine.py    22 tests
Dockerfile                 Container image
test_endpoints.py          Judge-harness simulation against all 10 sample cases
```

## Flow

```
POST /analyze-ticket
  → main.py validates input (400 on bad JSON, 422 on empty complaint)
  → reasoning.reasoning_engine.analyze(ticket)   → ReasoningResult
  → text_engine.generate(ticket, reasoning)       → GeneratedText
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
