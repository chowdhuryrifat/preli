from typing import Optional, Dict, Any, Callable

from contract import TicketInput, ReasoningResult, GeneratedText
from app.services.safety import safety_check


def _find_transaction(ticket: TicketInput, transaction_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not transaction_id or not ticket.transaction_history:
        return None
    for tx in ticket.transaction_history:
        if tx.transaction_id == transaction_id:
            return {
                "transaction_id": tx.transaction_id,
                "amount": tx.amount,
                "counterparty": tx.counterparty,
                "status": tx.status,
                "type": tx.type,
            }
    return None


def _build_context(ticket: TicketInput, reasoning: ReasoningResult) -> Dict[str, Any]:
    transaction = _find_transaction(ticket, reasoning.relevant_transaction_id)
    context = {
        "transaction_id": reasoning.relevant_transaction_id or "",
        "amount": transaction["amount"] if transaction else "",
        "counterparty": transaction["counterparty"] if transaction else "",
        "status": transaction["status"] if transaction else "",
        "tx_type": transaction["type"] if transaction else "",
        "case_type": reasoning.case_type,
        "department": reasoning.department,
        "severity": reasoning.severity,
        "evidence_verdict": reasoning.evidence_verdict,
        "human_review_required": reasoning.human_review_required,
        "confidence": reasoning.confidence,
        "language": ticket.language or "en",
        "user_type": ticket.user_type or "customer",
        "channel": ticket.channel or "in_app_chat",
        "ticket_id": ticket.ticket_id,
    }
    return context


TemplateFunc = Callable[[Dict[str, Any]], str]


class TemplateSet:
    def __init__(
        self,
        agent_summary: TemplateFunc,
        recommended_next_action: TemplateFunc,
        customer_reply: TemplateFunc,
    ) -> None:
        self.agent_summary = agent_summary
        self.recommended_next_action = recommended_next_action
        self.customer_reply = customer_reply


def _t(template: str) -> TemplateFunc:
    def fmt(ctx: Dict[str, Any]) -> str:
        return template.format(**ctx)
    return fmt


def _t_bn(template_en: str, template_bn: str, template_mixed: str) -> TemplateFunc:
    def fmt(ctx: Dict[str, Any]) -> str:
        lang = ctx.get("language", "en")
        if lang == "bn":
            return template_bn.format(**ctx)
        elif lang == "mixed":
            return template_mixed.format(**ctx)
        return template_en.format(**ctx)
    return fmt


_TEMPLATES: Dict[str, TemplateSet] = {
    "wrong_transfer": TemplateSet(
        agent_summary=_t(
            "Customer reports sending {amount} BDT via {transaction_id} to {counterparty}, "
            "which they now believe was the wrong recipient. Recipient is unresponsive."
        ),
        recommended_next_action=_t(
            "Verify {transaction_id} details with the customer and initiate the "
            "wrong-transfer dispute workflow per policy."
        ),
        customer_reply=_t_bn(
            "We have noted your concern about transaction {transaction_id}. "
            "Please do not share your PIN or OTP with anyone. "
            "Our dispute team will review the case and contact you through official support channels.",
            "আপনার {transaction_id} লেনদেনটি সম্পর্কে আমরা অবগত হয়েছি। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না। "
            "আমাদের বিবাদ নিষ্পত্তি দল কেসটি পর্যালোচনা করবে এবং অফিসিয়াল চ্যানেলের মাধ্যমে আপনার সাথে যোগাযোগ করবে।",
            "Apnar {transaction_id} transaction er regarding amra obogoto hoyeche. "
            "Please do not share your PIN or OTP with anyone. "
            "Amader dispute team case ta review korbe and official channel er maddhome contact korbe."
        ),
    ),
    "payment_failed": TemplateSet(
        agent_summary=_t(
            "Customer attempted a {amount} BDT payment ({transaction_id}) which failed, "
            "but reports balance was deducted. Requires payments operations investigation."
        ),
        recommended_next_action=_t(
            "Investigate {transaction_id} ledger status. If balance was deducted on a "
            "failed payment, initiate the automatic reversal flow within standard SLA."
        ),
        customer_reply=_t_bn(
            "We have noted that transaction {transaction_id} may have caused an unexpected "
            "balance deduction. Our payments team will review the case and any eligible amount "
            "will be returned through official channels. "
            "Please do not share your PIN or OTP with anyone.",
            "আমরা লক্ষ্য করেছি যে {transaction_id} লেনদেনটিতে অপ্রত্যাশিত ব্যালেন্স কাটা "
            "হতে পারে। আমাদের পেমেন্ট টিম কেসটি পর্যালোচনা করবে এবং যোগ্য কোন পরিমাণ "
            "অফিসিয়াল চ্যানেলের মাধ্যমে ফেরত দেওয়া হবে। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।",
            "Amra notice korchi je {transaction_id} transaction e unexpected balance deduction "
            "hoite pare. Amader payments team case ta review korbe and eligible amount "
            "official channel er maddhome return kora hobe. "
            "Please do not share your PIN or OTP with anyone."
        ),
    ),
    "refund_request": TemplateSet(
        agent_summary=_t(
            "Customer requests refund of {amount} BDT for {transaction_id} (merchant payment) "
            "due to change of mind. Not a service failure."
        ),
        recommended_next_action=_t(
            "Inform the customer that refund eligibility depends on the merchant's own policy. "
            "Provide guidance on contacting the merchant directly for a refund."
        ),
        customer_reply=_t_bn(
            "Thank you for reaching out. Refunds for completed merchant payments depend on "
            "the merchant's own policy. We recommend contacting the merchant directly. "
            "If you need help reaching them, please reply and we will guide you. "
            "Please do not share your PIN or OTP with anyone.",
            "আপনার যোগাযোগের জন্য ধন্যবাদ। সম্পূর্ণ মার্চেন্ট পেমেন্টের রিফান্ড "
            "মার্চেন্টের নিজস্ব নীতির উপর নির্ভর করে। আমরা মার্চেন্টের সাথে সরাসরি "
            "যোগাযোগ করার পরামর্শ দিচ্ছি। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।",
            "Thank you for reaching out. Completed merchant payment er refund merchant er "
            "policy er upor dependent. Amra merchant er sathe direct contact korte suggest korchi. "
            "Please do not share your PIN or OTP with anyone."
        ),
    ),
    "duplicate_payment": TemplateSet(
        agent_summary=_t(
            "Customer reports duplicate payment. Two {amount} BDT payments to {counterparty} "
            "found. The second ({transaction_id}) is likely the duplicate."
        ),
        recommended_next_action=_t(
            "Verify the duplicate with payments_ops. If the biller confirms only one payment "
            "was received, initiate reversal of {transaction_id}."
        ),
        customer_reply=_t_bn(
            "We have noted the possible duplicate payment for transaction {transaction_id}. "
            "Our payments team will verify with the biller and any eligible amount will be "
            "returned through official channels. "
            "Please do not share your PIN or OTP with anyone.",
            "আমরা {transaction_id} লেনদেনের সম্ভাব্য ডুপ্লিকেট পেমেন্ট সম্পর্কে অবগত হয়েছি। "
            "আমাদের পেমেন্ট টিম বিলারের সাথে যাচাই করবে এবং যোগ্য কোন পরিমাণ "
            "অফিসিয়াল চ্যানেলের মাধ্যমে ফেরত দেওয়া হবে। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।",
            "Amra {transaction_id} transaction er possible duplicate payment regarding obogoto hoyeche. "
            "Amader payments team biller er sathe verify korbe and eligible amount "
            "official channel er maddhome return kora hobe. "
            "Please do not share your PIN or OTP with anyone."
        ),
    ),
    "merchant_settlement_delay": TemplateSet(
        agent_summary=_t(
            "Merchant reports {amount} BDT settlement ({transaction_id}) is delayed beyond "
            "the standard next-day window. Settlement status is pending."
        ),
        recommended_next_action=_t(
            "Route to merchant_operations to verify settlement batch status. "
            "If the batch is delayed, communicate a revised ETA to the merchant."
        ),
        customer_reply=_t_bn(
            "We have noted your concern about settlement {transaction_id}. "
            "Our merchant operations team will check the batch status and update you "
            "on the expected settlement time through official channels.",
            "আমরা {transaction_id} সেটেলমেন্ট সম্পর্কে আপনার উদ্বেগ লক্ষ্য করেছি। "
            "আমাদের মার্চেন্ট অপারেশন্স টিম ব্যাচ স্ট্যাটাস চেক করবে এবং "
            "অফিসিয়াল চ্যানেলের মাধ্যমে আপনাকে জানাবে।",
            "Amra {transaction_id} settlement niye apnar concern note korchi. "
            "Amader merchant operations team batch status check korbe and "
            "official channel er maddhome janabe."
        ),
    ),
    "agent_cash_in_issue": TemplateSet(
        agent_summary=_t(
            "Customer reports {amount} BDT cash-in via {counterparty} ({transaction_id}) "
            "not reflected in balance. Transaction status is {status}."
        ),
        recommended_next_action=_t(
            "Investigate {transaction_id} pending status with agent operations. "
            "Confirm settlement state and resolve within the standard cash-in SLA."
        ),
        customer_reply=_t_bn(
            "Your transaction {transaction_id} has been noted. Our agent operations team "
            "will verify it promptly and contact you through official channels. "
            "Please do not share your PIN or OTP with anyone.",
            "আপনার {transaction_id} লেনদেনটি সম্পর্কে আমরা অবগত হয়েছি। "
            "আমাদের এজেন্ট অপারেশন্স দল এটি দ্রুত যাচাই করবে এবং "
            "অফিসিয়াল চ্যানেলে আপনাকে জানাবে। "
            "অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না।",
            "Apnar {transaction_id} transaction amra note korchi. "
            "Amader agent operations team eto druto verify korbe and "
            "official channel e janabe. "
            "Please do not share your PIN or OTP with anyone."
        ),
    ),
    "phishing_or_social_engineering": TemplateSet(
        agent_summary=_t(
            "Customer reports an unsolicited communication claiming to be from the company "
            "and asking for credentials. Customer has not yet shared any information."
        ),
        recommended_next_action=_t(
            "Escalate to fraud_risk team immediately. Confirm to customer that the company "
            "never asks for OTP. Log the reported details for fraud pattern analysis."
        ),
        customer_reply=_t_bn(
            "Thank you for reaching out before sharing any information. "
            "We never ask for your PIN, OTP, or password under any circumstances. "
            "Please do not share these with anyone, even if they claim to be from us. "
            "Our fraud team has been notified of this incident.",
            "কোনো তথ্য শেয়ার করার আগে আমাদের সাথে যোগাযোগ করার জন্য ধন্যবাদ। "
            "আমরা কখনোই আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। "
            "অনুগ্রহ করে এগুলো কারো সাথে শেয়ার করবেন না, এমনকি যদি তারা আমাদের হয়ে দাবি করে। "
            "আমাদের জালিয়াতি দল এই ঘটনা সম্পর্কে অবহিত হয়েছে।",
            "Kono information share korar age amader sathe contact korar jonno dhanyabad. "
            "Amra kokhono apnar PIN, OTP or password chai na. "
            "Please do not share these with anyone, even if they claim to be from us. "
            "Amader fraud team e incident ta notify kora hoyeche."
        ),
    ),
    "other": TemplateSet(
        agent_summary=_t(
            "Customer reports an issue. Insufficient detail to identify the relevant transaction."
        ),
        recommended_next_action=_t(
            "Reply to customer asking for specific details: which transaction, "
            "what amount, and a description of what went wrong."
        ),
        customer_reply=_t_bn(
            "Thank you for reaching out. To help you faster, please share more details "
            "about the issue, including the transaction ID and amount if possible. "
            "Please do not share your PIN or OTP with anyone.",
            "আপনার যোগাযোগের জন্য ধন্যবাদ। আপনাকে আরও দ্রুত সাহায্য করতে, "
            "অনুগ্রহ করে সমস্যা সম্পর্কে আরও বিস্তারিত জানান। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।",
            "Thank you for reaching out. Apnake druto help korte, please share koro "
            "transaction ID and amount shoho aro details. "
            "Please do not share your PIN or OTP with anyone."
        ),
    ),
}


def _get_templates(case_type: str) -> TemplateSet:
    return _TEMPLATES.get(case_type, _TEMPLATES["other"])


def generate(ticket: TicketInput, reasoning: ReasoningResult) -> GeneratedText:
    context = _build_context(ticket, reasoning)
    templates = _get_templates(context["case_type"])

    agent_summary = templates.agent_summary(context)
    recommended_next_action = templates.recommended_next_action(context)
    customer_reply = templates.customer_reply(context)

    agent_summary = safety_check(agent_summary)
    recommended_next_action = safety_check(recommended_next_action)
    customer_reply = safety_check(customer_reply)

    return GeneratedText(
        agent_summary=agent_summary,
        recommended_next_action=recommended_next_action,
        customer_reply=customer_reply,
    )
