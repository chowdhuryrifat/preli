"""Regression tests for contract.py schema flexibility.

These tests pin the contract changes made for HIGH #2 in AUDIT_REPORT.md:
    TransactionEntry.amount must accept None (upstream NULL amounts for
    fee/reversal rows must not crash the pipeline).
"""

from __future__ import annotations

import pytest

from contract import TransactionEntry, TicketInput


def _base_kwargs() -> dict:
    return {
        "transaction_id": "TXN-1",
        "timestamp": "2025-11-15T10:00:00Z",
        "type": "transfer",
        "counterparty": "Alice",
        "status": "completed",
    }


class TestAmountNullability:
    def test_amount_none_is_accepted(self) -> None:
        """amount=None must NOT raise ValidationError."""
        txn = TransactionEntry(**_base_kwargs(), amount=None)
        assert txn.amount is None

    def test_amount_missing_is_accepted(self) -> None:
        """amount omitted entirely must default to None."""
        txn = TransactionEntry(**_base_kwargs())
        assert txn.amount is None

    def test_amount_float_passes_through(self) -> None:
        txn = TransactionEntry(**_base_kwargs(), amount=1500.0)
        assert txn.amount == 1500.0

    def test_amount_int_coerced_to_float(self) -> None:
        """Pydantic v2 coerces int → float by default for float fields."""
        txn = TransactionEntry(**_base_kwargs(), amount=1500)
        assert txn.amount == 1500.0
        assert isinstance(txn.amount, float)

    def test_amount_zero_preserved(self) -> None:
        """Explicit 0.0 is a real amount, NOT a sentinel — must be preserved."""
        txn = TransactionEntry(**_base_kwargs(), amount=0.0)
        assert txn.amount == 0.0


class TestHelpersHandleNoneAmount:
    """The reasoning helpers must NOT crash when a transaction has amount=None."""

    def test_score_transaction_skips_amount_when_none(self) -> None:
        from reasoning.helpers import score_transaction, extract_amounts, extract_time_hints
        from datetime import date

        txn = TransactionEntry(**_base_kwargs(), amount=None)
        amounts = extract_amounts("I sent 500 taka")
        hints = extract_time_hints("nothing")

        score, breakdown = score_transaction(
            txn, amounts, hints, "I sent 500 taka", date(2025, 11, 15)
        )

        # No crash, and amount_match must NOT be awarded for a None row.
        assert "amount_match" not in breakdown
        assert isinstance(score, int)

    def test_find_candidates_includes_none_amount_row(self) -> None:
        """A row with amount=None but a date/time match should still surface."""
        from reasoning.helpers import find_candidates, extract_amounts, extract_time_hints

        txn = TransactionEntry(**_base_kwargs(), amount=None)
        amounts = extract_amounts("nothing")
        # Use a relative-day hint that matches the txn timestamp
        hints = extract_time_hints("yesterday")

        candidates = find_candidates([txn], amounts, hints, "yesterday problem")
        # The row has a date_match → should be included
        assert len(candidates) >= 1
        assert "date_match" in candidates[0][2]


class TestTicketWithNoneAmountRow:
    """A TicketInput containing a None-amount TransactionEntry must round-trip."""

    def test_ticket_with_none_amount_history(self) -> None:
        ticket = TicketInput(
            ticket_id="TKT-NULL-AMT",
            complaint="Yesterday a fee was charged but I don't know the amount.",
            language="en",
            channel="app",
            user_type="customer",
            transaction_history=[
                TransactionEntry(**_base_kwargs(), amount=None),
            ],
        )
        assert ticket.transaction_history is not None
        assert ticket.transaction_history[0].amount is None
