# contract.py — the shared interface. Lock this in the first 20 minutes.
from pydantic import BaseModel
from typing import Optional, List
class TransactionEntry(BaseModel):
    transaction_id: str
    timestamp: str
    type: str           # transfer | payment | cash_in | cash_out | settlement |  refund
    amount: float
    counterparty: str
    status: str          # completed | failed | pending | reversed
class TicketInput(BaseModel):
    ticket_id: str
    complaint: str
    language: Optional[str] = None
    channel: Optional[str] = None
    user_type: Optional[str] = None
    campaign_context: Optional[str] = None
    transaction_history: Optional[List[TransactionEntry]] = []
    metadata: Optional[dict] = None
class ReasoningResult(BaseModel):
    # Owned by Zahin's module
    relevant_transaction_id: Optional[str]
    evidence_verdict: str        # consistent | inconsistent | insufficient_data
    case_type: str
    severity: str                # low | medium | high | critical
    department: str
    human_review_required: bool
    confidence: Optional[float] = None
    reason_codes: Optional[List[str]] = []
class GeneratedText(BaseModel):
    # Owned by Adil's module — already safety-checked before it's returned
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
class FinalResponse(BaseModel):
    # Assembled by Rifat's API layer
    ticket_id: str
    relevant_transaction_id: Optional[str]
    evidence_verdict: str
    case_type: str
    severity: str
    department: str
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: Optional[float] = None
    reason_codes: Optional[List[str]] = []