import json
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contract import TicketInput, FinalResponse
from reasoning.reasoning_engine import analyze
from app.services.text_engine import generate


class BanglaJSONResponse(JSONResponse):
    def render(self, content):
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


app = FastAPI(
    title="QueueStorm Investigator",
    version="1.0.0",
    description="Ticket analysis API for the QueueStorm hackathon preliminary round.",
    default_response_class=BanglaJSONResponse,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post(
    "/analyze-ticket",
    response_model=FinalResponse,
    summary="Analyze a support ticket",
)
def analyze_ticket(ticket: TicketInput):
    if not ticket.complaint.strip():
        return JSONResponse(
            status_code=422,
            content={"error": "complaint must not be empty"},
        )

    try:
        reasoning = analyze(ticket)
        text = generate(ticket, reasoning)
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error"},
        )

    return FinalResponse(
        ticket_id=ticket.ticket_id,
        relevant_transaction_id=reasoning.relevant_transaction_id,
        evidence_verdict=reasoning.evidence_verdict,
        case_type=reasoning.case_type,
        severity=reasoning.severity,
        department=reasoning.department,
        agent_summary=text.agent_summary,
        recommended_next_action=text.recommended_next_action,
        customer_reply=text.customer_reply,
        human_review_required=reasoning.human_review_required,
        confidence=reasoning.confidence,
        reason_codes=reasoning.reason_codes,
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_request"},
    )


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error"},
    )
