"""
Main reasoning engine for QueueStorm Investigator.

Entry point::

    result = analyze(ticket)

Returns a `ReasoningResult` with deterministic, rule-based analysis.
"""

from __future__ import annotations

from reasoning.helpers import (
    build_reason_codes,
    classify_severity,
    compute_confidence,
    compute_human_review,
    detect_case_type,
    extract_amounts,
    extract_keywords,
    extract_time_hints,
    find_candidates,
    judge_evidence,
    map_department,
    normalize_text,
    pick_relevant_txn,
)
from contract import ReasoningResult, TicketInput


def _detect_duplicate(
    transactions: list,
    complaint: str,
    amounts: list[float],
) -> tuple[str | None, Any | None, list]:
    """Check if this is a duplicate-payment case per spec §4.5.

    Two transactions to the same counterparty for the same amount (within ±0.01 BDT),
    both of the same type, occurring within 120 seconds of each other.

    Returns (relevant_id, matched_txn, candidates).
    """
    norm = normalize_text(complaint)
    is_dup = ("duplicate" in norm or "twice" in norm or "two" in norm
              or "দুইবার" in norm or "ডুপ্লিকেট" in norm
              or "deducted twice" in norm or "paid twice" in norm)

    if not is_dup:
        return None, None, []

    if len(transactions) < 2:
        return None, None, []

    from datetime import datetime, timezone
    # Find pairs of identical-amount, same-counterparty within 120 seconds
    for i in range(len(transactions) - 1, -1, -1):
        for j in range(i - 1, -1, -1):
            if not (abs(transactions[i].amount - transactions[j].amount) < 0.01
                    and transactions[i].type == transactions[j].type
                    and transactions[i].counterparty == transactions[j].counterparty):
                continue
            # Spec §4.5: within 120 seconds of each other
            try:
                t1 = datetime.fromisoformat(transactions[i].timestamp)
                t2 = datetime.fromisoformat(transactions[j].timestamp)
                if abs((t1 - t2).total_seconds()) <= 120:
                    matched = transactions[i]  # later one is the duplicate
                    candidates = [(matched, 100, {"duplicate_match": 100})]
                    return matched.transaction_id, matched, candidates
            except (ValueError, TypeError):
                # If timestamp is unparseable, still match by amount+type+counterparty
                matched = transactions[i]
                candidates = [(matched, 100, {"duplicate_match": 100})]
                return matched.transaction_id, matched, candidates

    return None, None, []


def analyze(ticket: TicketInput) -> ReasoningResult:
    """Analyse a support ticket and produce a deterministic ReasoningResult.

    Pipeline:
        1. Normalise and extract information from the complaint.
        2. Score and rank candidate transactions.
        3. Pick the relevant transaction (or None if ambiguous).
        4. Judge evidence consistency.
        5. Detect case type.
        6. Classify severity.
        7. Map department.
        8. Decide whether human review is needed.
        9. Compute confidence.
        10. Build reason codes.
    """
    # 1. Extract information from complaint
    complaint = ticket.complaint
    amounts = extract_amounts(complaint)
    time_hints = extract_time_hints(complaint)
    matched_keywords = extract_keywords(complaint)

    transactions = ticket.transaction_history or []

    # 2. Check for duplicate payment first (special case)
    dup_id, dup_txn, dup_candidates = _detect_duplicate(transactions, complaint, amounts)
    if dup_id is not None:
        case_type = "duplicate_payment"
        evidence_verdict = "consistent"
        severity = classify_severity(case_type, dup_txn.amount, evidence_verdict)
        department = map_department(case_type, complaint)
        human_review = True
        confidence = 0.93
        reason_codes = ["duplicate_payment", "biller_verification_required"]

        return ReasoningResult(
            relevant_transaction_id=dup_id,
            evidence_verdict=evidence_verdict,
            case_type=case_type,
            severity=severity,
            department=department,
            human_review_required=human_review,
            confidence=confidence,
            reason_codes=reason_codes,
        )

    # 3. Score and rank candidate transactions
    candidates = find_candidates(transactions, amounts, time_hints, complaint)

    # 4. Determine relevant_transaction_id
    relevant_id = pick_relevant_txn(candidates)

    # 5. Find the matched transaction object
    matched_txn = None
    if relevant_id is not None:
        for txn in transactions:
            if txn.transaction_id == relevant_id:
                matched_txn = txn
                break

    # Detect case type early for evidence judgment
    txn_type = matched_txn.type if matched_txn else None
    case_type = detect_case_type(complaint, txn_type)

    has_multiple = len(candidates) > 1 and pick_relevant_txn(candidates) is None

    # 6. Determine evidence_verdict
    evidence_verdict = judge_evidence(complaint, matched_txn, candidates, transactions)

    # 7. Classify severity (with evidence adjustment per spec §8)
    matched_amount = matched_txn.amount if matched_txn else (amounts[0] if amounts else None)
    severity = classify_severity(case_type, matched_amount, evidence_verdict)

    # 8. Map department (spec §7.1 refund sub-routing)
    department = map_department(case_type, complaint)

    # 9. Determine human review
    human_review = compute_human_review(
        case_type=case_type,
        evidence_verdict=evidence_verdict,
        severity=severity,
        amount=matched_amount,
        matched_txn=matched_txn,
        has_multiple_candidates=has_multiple,
    )

    # 10. Compute confidence
    confidence = compute_confidence(
        matched_txn=matched_txn,
        candidates=candidates,
        evidence_verdict=evidence_verdict,
        case_type=case_type,
        amounts=amounts,
    )

    # 11. Build reason codes (with injection detection per spec §11)
    reason_codes = build_reason_codes(
        evidence_verdict=evidence_verdict,
        case_type=case_type,
        matched_txn=matched_txn,
        candidates=candidates,
        matched_keywords=matched_keywords,
        complaint=complaint,
    )

    return ReasoningResult(
        relevant_transaction_id=relevant_id,
        evidence_verdict=evidence_verdict,
        case_type=case_type,
        severity=severity,
        department=department,
        human_review_required=human_review,
        confidence=confidence,
        reason_codes=reason_codes,
    )
