from contract import TicketInput, ReasoningResult, GeneratedText


def generate(ticket: TicketInput, reasoning: ReasoningResult) -> GeneratedText:
    """Stub — Adil will replace with real implementation."""
    return GeneratedText(
        agent_summary="No analysis available.",
        recommended_next_action="Review the ticket manually.",
        customer_reply="We have received your query. Our team will review it and get back to you through official channels. Please do not share your PIN or OTP with anyone.",
    )
