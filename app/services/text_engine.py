from typing import Optional, Dict, Any, Callable

from contract import TicketInput, ReasoningResult, GeneratedText
from app.services.safety import safety_check


def _fmt_amt(v: Any) -> str:
    if v == "" or v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        return str(int(v))
    return str(v)


def _find_transaction(ticket: TicketInput, transaction_id: Optional[str]) -> Optional[Dict[str, Any]]:
    if not transaction_id or not ticket.transaction_history:
        return None
    for tx in ticket.transaction_history:
        if tx.transaction_id == transaction_id:
            return {
                "transaction_id": tx.transaction_id,
                "amount": _fmt_amt(tx.amount),
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



def _wrong_transfer_reply(ctx: Dict[str, Any]) -> str:
    lang = ctx.get("language", "en")
    txn_id = ctx.get("transaction_id", "")
    amt = ctx.get("amount", "")
    cparty = ctx.get("counterparty", "")
    verdict = ctx.get("evidence_verdict", "")
    sev = ctx.get("severity", "low")
    reason_codes = ctx.get("reason_codes", [])
    has_match = bool(txn_id)
    has_amount = bool(amt)
    is_ambiguous = "ambiguous_match" in reason_codes

    if is_ambiguous:
        if lang == "bn":
            return "আমরা আপনার বর্ণনার সাথে মিলে একাধিক লেনদেন পেয়েছি। অনুগ্রহ করে সঠিক লেনদেন আইডি বা আপনার ভাইয়ের নাম্বারটি জানান। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        if lang == "mixed":
            return "Amra apnar description er sathe match kore ekadhik transaction peyechi. Please correct transaction ID or receiver number ta janan. Please do not share your PIN or OTP with anyone."
        return (
            "We found multiple possible transactions matching your description. "
            "Please confirm the exact transaction ID or the recipient's number so we can assist. "
            "Please do not share your PIN or OTP with anyone."
        )

    if lang == "bn":
        if has_match and sev == "critical":
            return f"আমরা {txn_id} ({amt} টাকা) লেনদেনটি জরুরি হিসেবে চিহ্নিত করেছি। আমাদের সিনিয়র দল ২ ঘন্টার মধ্যে আপনার সাথে যোগাযোগ করবে। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        if has_match and verdict == "consistent":
            return f"আমরা {txn_id} ({amt} টাকা) লেনদেনটি সম্পর্কে অবগত হয়েছি। আমাদের বিবাদ নিষ্পত্তি দল তদন্ত করবে এবং অফিসিয়াল চ্যানেলের মাধ্যমে আপনার সাথে যোগাযোগ করবে। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        if has_match and verdict == "inconsistent":
            return f"আমরা {txn_id} ({amt} টাকা) লেনদেনটি পেয়েছি কিন্তু তথ্য পরস্পরবিরোধী। আমাদের দল অতিরিক্ত যাচাই করবে এবং ফলাফল জানাবে। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        if has_match:
            return f"আমরা {txn_id} লেনদেনটি পেয়েছি তবে আরও তথ্য প্রয়োজন। দয়া করে নিশ্চিত করুন এটি সঠিক লেনদেন কিনা। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        if has_amount:
            return f"আমরা {amt} টাকার কোনো লেনদেন খুঁজে পাইনি। অনুগ্রহ করে সঠিক লেনদেন আইডি এবং পরিমাণ দিন। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        return "আমরা আপনার বর্ণনার সাথে মিলে এমন কোনো লেনদেন খুঁজে পাইনি। অনুগ্রহ করে সঠিক লেনদেন আইডি, পরিমাণ এবং প্রাপকের নম্বর দিন। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"

    if lang == "mixed":
        if has_match and sev == "critical":
            return f"Transaction {txn_id} ({amt} BDT) critical hishebe mark kora hoyeche. Amader senior team 2 ghonta er moddhe contact korbe. Please do not share your PIN or OTP with anyone."
        if has_match and verdict == "consistent":
            return f"Apnar {txn_id} ({amt} BDT) transaction er regarding amra obogoto hoyeche. Amader dispute team investigate korbe and official channel er maddhome contact korbe. Please do not share your PIN or OTP with anyone."
        if has_match and verdict == "inconsistent":
            return f"Amra {txn_id} ({amt} BDT) transaction ta peyechi but information contradictory. Amader team extra verify korbe and result janabe. Please do not share your PIN or OTP with anyone."
        if has_match:
            return f"Amra {txn_id} transaction ta peyechi but aro info lagbe. Please confirm ei transaction ki correct. Please do not share your PIN or OTP with anyone."
        if has_amount:
            return f"Amra {amt} BDT er kono transaction khujte pari nai. Please correct transaction ID and amount din. Please do not share your PIN or OTP with anyone."
        return "Amra apnar description er sathe match kore emon kono transaction khujte pari nai. Please correct transaction ID, amount, and receiver number provide korun. Please do not share your PIN or OTP with anyone."

    if has_match and sev == "critical":
        return (
            f"Transaction {txn_id} for {amt} BDT has been flagged as critical. "
            f"Our senior dispute team will contact you within 2 hours. "
            f"Please do not share your PIN or OTP with anyone."
        )
    if has_match and verdict == "consistent":
        return (
            f"We have identified transaction {txn_id} for {amt} BDT sent to {cparty}. "
            f"Our dispute team will investigate and contact you through official channels. "
            f"Please do not share your PIN or OTP with anyone."
        )
    if has_match and verdict == "inconsistent":
        return (
            f"We found transaction {txn_id} for {amt} BDT, but the information is contradictory. "
            f"Our team will conduct additional verification and update you. "
            f"Please do not share your PIN or OTP with anyone."
        )
    if has_match:
        return (
            f"We found transaction {txn_id} for {amt} BDT in your history, but we need more details. "
            f"Please confirm if this is the correct transaction. "
            f"Please do not share your PIN or OTP with anyone."
        )
    if has_amount:
        return (
            f"We searched for a {amt} BDT transaction but could not find an exact match. "
            f"Please provide the transaction ID or verify the amount and try again. "
            f"Please do not share your PIN or OTP with anyone."
        )
    return (
        "We could not locate any transaction matching your description. "
        "Please provide the exact transaction ID, amount, and the recipient's number. "
        "Please do not share your PIN or OTP with anyone."
    )


def _payment_failed_reply(ctx: Dict[str, Any]) -> str:
    lang = ctx.get("language", "en")
    txn_id = ctx.get("transaction_id", "")
    amt = ctx.get("amount", "")
    has_match = bool(txn_id)

    if lang == "bn":
        if has_match:
            return (
                f"আমরা দেখেছি যে {txn_id} ({amt} টাকা) লেনদেনটি ব্যর্থ হয়েছে কিন্তু "
                f"ব্যালেন্স কাটা হতে পারে। আমাদের পেমেন্ট টিম পর্যালোচনা করবে এবং যোগ্য পরিমাণ "
                f"ফেরত দেওয়া হবে। অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
            )
        return (
            "আমরা একটি ব্যর্থ পেমেন্ট পেয়েছি কিন্তু লেনদেন আইডি প্রয়োজন। "
            "অনুগ্রহ করে লেনদেন আইডি এবং পরিমাণ দিন। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        )
    if lang == "mixed":
        if has_match:
            return (
                f"Amra dekhechi je {txn_id} ({amt} BDT) transaction failed hoise but "
                f"balance deduction hoite pare. Amader payments team review korbe and eligible amount "
                f"return kora hobe. Please do not share your PIN or OTP with anyone."
            )
        return (
            "Amra ekta failed payment peyechi but transaction ID lagbe. "
            "Please transaction ID and amount provide korun. "
            "Please do not share your PIN or OTP with anyone."
        )

    if has_match:
        return (
            f"Transaction {txn_id} for {amt} BDT appears to have failed, "
            f"but your balance may have been deducted. Our payments team will review "
            f"and any eligible amount will be returned through official channels. "
            f"Please do not share your PIN or OTP with anyone."
        )
    return (
        "We found a failed payment attempt but need the transaction ID to investigate. "
        "Please provide the transaction ID and amount. "
        "Please do not share your PIN or OTP with anyone."
    )


def _refund_reply(ctx: Dict[str, Any]) -> str:
    lang = ctx.get("language", "en")
    txn_id = ctx.get("transaction_id", "")
    has_match = bool(txn_id)

    if lang == "bn":
        if has_match:
            return (
                f"{txn_id} লেনদেনের রিফান্ড মার্চেন্টের নিজস্ব নীতির উপর নির্ভর করে। "
                f"আমরা মার্চেন্টের সাথে সরাসরি যোগাযোগ করার পরামর্শ দিচ্ছি। "
                f"অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
            )
        return (
            "রিফান্ড অনুরোধের জন্য লেনদেন আইডি প্রয়োজন। "
            "অনুগ্রহ করে লেনদেন আইডি দিন। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        )
    if lang == "mixed":
        if has_match:
            return (
                f"{txn_id} transaction er refund merchant er policy er upor dependent. "
                f"Amra merchant er sathe direct contact korte suggest korchi. "
                f"Please do not share your PIN or OTP with anyone."
            )
        return (
            "Refund request er jonno transaction ID lagbe. "
            "Please transaction ID provide korun. "
            "Please do not share your PIN or OTP with anyone."
        )

    if has_match:
        return (
            f"Refunds for transaction {txn_id} depend on the merchant's own policy. "
            "We recommend contacting the merchant directly. "
            "If you need help reaching them, please reply and we will guide you. "
            "Please do not share your PIN or OTP with anyone."
        )
    return (
        "To process your refund request, we need the transaction ID. "
        "Please provide the transaction ID and amount so we can assist. "
        "Please do not share your PIN or OTP with anyone."
    )


def _duplicate_reply(ctx: Dict[str, Any]) -> str:
    lang = ctx.get("language", "en")
    txn_id = ctx.get("transaction_id", "")
    amt = ctx.get("amount", "")

    if lang == "bn":
        return (
            f"আমরা {txn_id} ({amt} টাকা) লেনদেনের সম্ভাব্য ডুপ্লিকেট পেমেন্ট সম্পর্কে অবগত হয়েছি। "
            f"আমাদের পেমেন্ট টিম বিলারের সাথে যাচাই করবে। যোগ্য পরিমাণ ফেরত দেওয়া হবে। "
            f"অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        )
    if lang == "mixed":
        return (
            f"Amra {txn_id} ({amt} BDT) transaction er possible duplicate payment regarding obogoto hoyeche. "
            f"Amader payments team biller er sathe verify korbe. Eligible amount return kora hobe. "
            f"Please do not share your PIN or OTP with anyone."
        )

    return (
        f"We have noted the possible duplicate payment for transaction {txn_id} ({amt} BDT). "
        f"Our payments team will verify with the biller and any eligible amount will be "
        f"returned through official channels. "
        f"Please do not share your PIN or OTP with anyone."
    )


def _merchant_settlement_reply(ctx: Dict[str, Any]) -> str:
    lang = ctx.get("language", "en")
    txn_id = ctx.get("transaction_id", "")

    if lang == "bn":
        return (
            f"আমরা {txn_id} সেটেলমেন্ট নিয়ে আপনার উদ্বেগ লক্ষ্য করেছি। "
            f"আমাদের মার্চেন্ট অপারেশন্স টিম ব্যাচ স্ট্যাটাস চেক করবে এবং অফিসিয়াল চ্যানেলে জানাবে।"
        )
    if lang == "mixed":
        return (
            f"Amra {txn_id} settlement niye apnar concern note korchi. "
            f"Amader merchant operations team batch status check korbe and official channel e janabe."
        )

    return (
        f"We have noted your concern about settlement {txn_id}. "
        f"Our merchant operations team will check the batch status and update you "
        f"on the expected settlement time through official channels."
    )


def _agent_cash_in_reply(ctx: Dict[str, Any]) -> str:
    lang = ctx.get("language", "en")
    txn_id = ctx.get("transaction_id", "")

    if lang == "bn":
        return (
            f"আপনার {txn_id} লেনদেনটি সম্পর্কে আমরা অবগত হয়েছি। "
            f"আমাদের এজেন্ট অপারেশন্স দল এটি দ্রুত যাচাই করবে এবং অফিসিয়াল চ্যানেলে আপনাকে জানাবে। "
            f"অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        )
    if lang == "mixed":
        return (
            f"Apnar {txn_id} transaction amra note korchi. "
            f"Amader agent operations team eto druto verify korbe and official channel e janabe. "
            f"Please do not share your PIN or OTP with anyone."
        )

    return (
        f"Your transaction {txn_id} has been noted. Our agent operations team "
        f"will verify it promptly and contact you through official channels. "
        f"Please do not share your PIN or OTP with anyone."
    )


def _phishing_reply(ctx: Dict[str, Any]) -> str:
    lang = ctx.get("language", "en")

    if lang == "bn":
        return (
            "কোনো তথ্য শেয়ার করার আগে আমাদের সাথে যোগাযোগ করার জন্য ধন্যবাদ। "
            "আমরা কখনোই আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। "
            "অনুগ্রহ করে এগুলো কারো সাথে শেয়ার করবেন না, এমনকি যদি তারা আমাদের হয়ে দাবি করে। "
            "আমাদের জালিয়াতি দল এই ঘটনা সম্পর্কে অবহিত হয়েছে।"
        )
    if lang == "mixed":
        return (
            "Kono information share korar age amader sathe contact korar jonno dhanyabad. "
            "Amra kokhono apnar PIN, OTP or password chai na. "
            "Please do not share these with anyone, even if they claim to be from us. "
            "Amader fraud team e incident ta notify kora hoyeche."
        )

    return (
        "Thank you for reaching out before sharing any information. "
        "We never ask for your PIN, OTP, or password under any circumstances. "
        "Please do not share these with anyone, even if they claim to be from us. "
        "Our fraud team has been notified of this incident."
    )


def _other_reply(ctx: Dict[str, Any]) -> str:
    lang = ctx.get("language", "en")
    reason_codes = ctx.get("reason_codes", [])
    has_match = bool(ctx.get("transaction_id", ""))
    has_amount = bool(ctx.get("amount", ""))

    vague = any(r in ["vague_complaint", "needs_clarification"] for r in (reason_codes or []))
    ambiguous = any(r in ["ambiguous_match"] for r in (reason_codes or []))

    if lang == "bn":
        if ambiguous:
            return (
                "আমরা একাধিক লেনদেন পেয়েছি যা আপনার বর্ণনার সাথে মিলছে। "
                "অনুগ্রহ করে লেনদেন আইডিটি জানান যাতে আমরা সহায়তা করতে পারি। "
                "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
            )
        if vague:
            return (
                "আমরা আপনার বার্তা পেয়েছি কিন্তু সমস্যা শনাক্ত করতে পারিনি। "
                "অনুগ্রহ করে বিস্তারিত জানান। "
                "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
            )
        return (
            "আপনার যোগাযোগের জন্য ধন্যবাদ। আপনাকে দ্রুত সাহায্য করতে, "
            "অনুগ্রহ করে লেনদেন আইডি এবং পরিমাণ সহ বিস্তারিত জানান। "
            "অনুগ্রহ করে আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        )

    if lang == "mixed":
        if ambiguous:
            return (
                "Amra ekadhik transaction peyechi je apnar description er sathe match kore. "
                "Please transaction ID ta janan jate amra help korte pari. "
                "Please do not share your PIN or OTP with anyone."
            )
        if vague:
            return (
                "Amra apnar message peyechi but problem ta identify korte pari nai. "
                "Please details provide korun. "
                "Please do not share your PIN or OTP with anyone."
            )
        return (
            "Thank you for reaching out. Apnake druto help korte, "
            "please transaction ID and amount shoho aro details share korun. "
            "Please do not share your PIN or OTP with anyone."
        )

    if ambiguous:
        return (
            "We found multiple transactions matching your description. "
            "Please specify the transaction ID so we can assist you further. "
            "Please do not share your PIN or OTP with anyone."
        )
    if vague:
        return (
            "We received your message but could not identify the issue. "
            "Please describe the problem in detail, including the transaction ID and amount. "
            "Please do not share your PIN or OTP with anyone."
        )
    if has_match:
        return (
            f"We found transaction {ctx['transaction_id']} in your history. "
            "Please describe what went wrong so we can assist. "
            "Please do not share your PIN or OTP with anyone."
        )
    return (
        "Thank you for contacting us. To help you faster, please share more details "
        "about the issue, including the transaction ID and amount if possible. "
        "Please do not share your PIN or OTP with anyone."
    )


def _wrong_transfer_agent_summary(ctx: Dict[str, Any]) -> str:
    txn_id = ctx.get("transaction_id", "")
    amt = ctx.get("amount", "")
    cparty = ctx.get("counterparty", "")
    verdict = ctx.get("evidence_verdict", "")
    reason_codes = ctx.get("reason_codes", [])
    is_ambiguous = "ambiguous_match" in reason_codes

    if is_ambiguous:
        return (
            f"Customer reports sending {amt or 'an'} amount to the wrong recipient. "
            "Multiple candidate transactions found - could not confidently identify which one."
        )
    if verdict == "insufficient_data":
        return (
            f"Customer reports sending {amt or 'an'} amount to the wrong recipient. "
            f"No matching transaction could be confidently identified from the history."
        )
    return (
        f"Customer reports sending {amt} BDT via {txn_id} to {cparty}, "
        f"which they now believe was the wrong recipient. Recipient is unresponsive."
    )


def _wrong_transfer_action(ctx: Dict[str, Any]) -> str:
    txn_id = ctx.get("transaction_id", "")
    verdict = ctx.get("evidence_verdict", "")
    reason_codes = ctx.get("reason_codes", [])
    is_ambiguous = "ambiguous_match" in reason_codes

    if is_ambiguous:
        return (
            "Ask the customer which of the multiple matched transactions is theirs "
            "before initiating the dispute workflow."
        )
    if verdict == "insufficient_data":
        return (
            "Request the recipient number or transaction ID from the customer."
        )
    if verdict == "inconsistent":
        return (
            f"Investigate {txn_id} — customer claims wrong recipient but history shows "
            f"established pattern with this counterparty. Verify with customer."
        )
    return (
        f"Verify {txn_id} details with the customer and initiate the "
        f"wrong-transfer dispute workflow per policy."
    )


_TEMPLATES: Dict[str, TemplateSet] = {
    "wrong_transfer": TemplateSet(
        agent_summary=_wrong_transfer_agent_summary,
        recommended_next_action=_wrong_transfer_action,
        customer_reply=_wrong_transfer_reply,
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
        customer_reply=_payment_failed_reply,
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
        customer_reply=_refund_reply,
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
        customer_reply=_duplicate_reply,
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
        customer_reply=_merchant_settlement_reply,
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
        customer_reply=_agent_cash_in_reply,
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
        customer_reply=_phishing_reply,
    ),
    "other": TemplateSet(
        agent_summary=_t(
            "Customer reports an issue. Insufficient detail to identify the relevant transaction."
        ),
        recommended_next_action=_t(
            "Reply to customer asking for specific details: which transaction, "
            "what amount, and a description of what went wrong."
        ),
        customer_reply=_other_reply,
    ),
}


def _get_templates(case_type: str) -> TemplateSet:
    return _TEMPLATES.get(case_type, _TEMPLATES["other"])


def generate(ticket: TicketInput, reasoning: ReasoningResult) -> GeneratedText:
    context = _build_context(ticket, reasoning)
    context["reason_codes"] = reasoning.reason_codes
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
