import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from contract import TicketInput, FinalResponse
from reasoning.reasoning_engine import analyze
from app.services.text_engine import generate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

MAX_COMPLAINT_LENGTH = 5000
MAX_TRANSACTIONS = 100

app = FastAPI(
    title="QueueStorm Investigator",
    version="1.0.0",
    description="Ticket analysis API for the QueueStorm hackathon preliminary round.",
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
    complaint = ticket.complaint.strip()
    if not complaint:
        return JSONResponse(
            status_code=422,
            content={"error": "complaint must not be empty"},
        )
    if len(complaint) > MAX_COMPLAINT_LENGTH:
        return JSONResponse(
            status_code=422,
            content={"error": f"complaint exceeds {MAX_COMPLAINT_LENGTH} characters"},
        )
    if ticket.transaction_history and len(ticket.transaction_history) > MAX_TRANSACTIONS:
        return JSONResponse(
            status_code=422,
            content={"error": f"transaction_history exceeds {MAX_TRANSACTIONS} entries"},
        )

    try:
        reasoning = analyze(ticket)
        text = generate(ticket, reasoning)
    except Exception as exc:
        logger.exception("analyze_ticket failed for ticket_id=%s", ticket.ticket_id)
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
