"""Regression tests for Bangla credential-request handling in safety.py.

These tests pin the AUDIT_REPORT.md MEDIUM #1 fix:
    safety.py must catch Bengali-script credential requests like
    "আপনার পিন দিন" or "OTP দাও" — not just ASCII PIN/OTP/password.
"""

from __future__ import annotations

import pytest

from app.services.safety import safety_check


def _assert_replaced(result: str, original: str) -> None:
    assert result != original, (
        f"Expected Bangla credential phrase to be replaced, "
        f"but got: {result!r}"
    )


class TestBanglaCredentialRequests:
    """Each attack phrase uses a Bengali verb + Bengali credential keyword."""

    @pytest.mark.parametrize("text", [
        # Direct credential requests
        "আপনার পিন দিন",
        "আপনার ওটিপি দিন",
        "আপনার পাসওয়ার্ড দিন",
        "আপনার সিভিভি দিন",
        # Verb variations
        "আপনার পিন দাও",
        "আপনার ওটিপি শেয়ার করুন",
        "আপনার পাসওয়ার্ড বলুন",
        "কার্ড নাম্বার দিন",
        "কার্ড নম্বর দিন",
        "আপনার কার্ডের নাম্বার দিন",
        # Mixed-script (Latin credential + Bengali verb)
        "PIN দিন",
        "OTP দাও",
    ])
    def test_bangla_credential_phrase_replaced(self, text: str) -> None:
        result = safety_check(text)
        _assert_replaced(result, text)
        # Replacement must contain a safe instruction in Bengali
        result_lower = result.lower()
        assert any(
            marker in result_lower
            for marker in ["করবেন না", "করো না", "do not", "share"]
        ), f"Safe replacement missing for {text!r} → got {result!r}"

    def test_bangla_credential_does_not_crash_on_unrelated_text(self) -> None:
        """Adding the Bangla regex must NOT change behavior for safe Bengali."""
        text = "আমি গতকাল ৫০০ টাকা পাঠিয়েছি ভুল নাম্বারে।"
        result = safety_check(text)
        assert result == text, f"Safe Bengali text changed: {result!r}"

    def test_ascii_credential_still_caught(self) -> None:
        """Original ASCII path must still work — no regression."""
        result = safety_check("Please share your PIN to continue.")
        assert result != "Please share your PIN to continue."
