# QueueStorm Investigator — API Layer (Rifat)

FastAPI service exposing `GET /health` and `POST /analyze-ticket` for the QueueStorm hackathon.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

The port defaults to 8000. Override with the `PORT` environment variable:

```bash
$env:PORT=8080; python -m uvicorn main:app --host 0.0.0.0 --port $env:PORT
```

## Endpoints

| Method | Path              | Description                        |
|--------|-------------------|------------------------------------|
| GET    | `/health`         | Returns `{"status":"ok"}`          |
| POST   | `/analyze-ticket` | Accepts `TicketInput`, returns `FinalResponse` |

Interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs)

## Project Structure

```
main.py                FastAPI app with route handlers
contract.py            Shared Pydantic models (locked with the team)
reasoning_engine.py    Zahin's module — transaction matching + evidence verdict
text_engine.py         Adil's module — text generation + safety filter
```

## Flow

```
POST /analyze-ticket
  → main.py validates input (400 on bad JSON, 422 on empty complaint)
  → reasoning_engine.analyze(ticket)       → ReasoningResult
  → text_engine.generate(ticket, reasoning) → GeneratedText
  → main.py merges into FinalResponse
  → JSON 200 (or 500 {"error":"internal_error"} on unexpected failure)
```

## Dependencies

- `reasoning_engine.py` — Zahin's module (stub until replaced)
- `text_engine.py` — Adil's module (stub until replaced)
