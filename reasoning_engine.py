from contract import TicketInput, ReasoningResult


def analyze(ticket: TicketInput) -> ReasoningResult:
    """Stub — Zahin will replace with real logic."""
    return ReasoningResult(
        relevant_transaction_id=None,
        evidence_verdict="insufficient_data",
        case_type="other",
        severity="low",
        department="customer_support",
        human_review_required=False,
    )
