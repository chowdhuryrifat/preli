"""
Scoring weights, severity thresholds, department mappings,
and keyword sets for the QueueStorm reasoning engine.
"""

# ── Transaction scoring weights ────────────────────────────────────────
AMOUNT_MATCH_WEIGHT = 40
TIME_MATCH_WEIGHT = 30
TYPE_MATCH_WEIGHT = 20
KEYWORD_MATCH_WEIGHT = 10
MAX_SCORE = AMOUNT_MATCH_WEIGHT + TIME_MATCH_WEIGHT + TYPE_MATCH_WEIGHT + KEYWORD_MATCH_WEIGHT

# ── Severity thresholds (BDT) ─────────────────────────────────────────
SEVERITY_LOW_MAX = 5000       # < 5,000   → low
SEVERITY_MEDIUM_MAX = 20000   # 5,000–20,000 → medium
SEVERITY_HIGH_MAX = 100000    # 20,000–100,000 → high
# > 100,000 → critical

# ── Department mapping ────────────────────────────────────────────────
DEPARTMENT_MAP = {
    "wrong_transfer":             "dispute_resolution",
    "payment_failed":             "payments_ops",
    "refund_request":             "customer_support",
    "duplicate_payment":          "payments_ops",
    "merchant_settlement_delay":  "merchant_operations",
    "agent_cash_in_issue":        "agent_operations",
    "phishing_or_social_engineering": "fraud_risk",
    "other":                      "customer_support",
}

# ── Keyword sets per case_type ────────────────────────────────────────
# Keys match the case_type enum values.  Contains English, Bangla, Banglish variants.

WRONG_TRANSFER_KEYWORDS = {
    "wrong number", "wrong recipient", "wrong account", "wrong person",
    "sent to wrong", "transferred to wrong", "typo", "typed wrong",
    "wrong", "vul number", "vul account", "vul recipient",
    "ভুল নাম্বার", "ভুল অ্যাকাউন্ট", "ভুল ব্যক্তি", "ভুল",
}

PAYMENT_FAILED_KEYWORDS = {
    "payment failed", "failed payment", "payment unsuccessful",
    "balance deducted", "money deducted", "amount deducted",
    "failed", "fail", "unsuccessful",
    "পেমেন্ট failed", "টাকা কেটেছে", "কেটেছে", "failed",
}

REFUND_REQUEST_KEYWORDS = {
    "refund", "refund my money", "give me my money back", "money back",
    "change my mind", "changed my mind", "don't want", "cancel",
    "ফেরত", "টাকা ফেরত", "রিফান্ড",
}

DUPLICATE_PAYMENT_KEYWORDS = {
    "duplicate", "deducted twice", "paid twice", "charged twice",
    "double payment", "two times", "same bill",
    "ডুপ্লিকেট", "দুইবার", "দুই বার",
}

MERCHANT_SETTLEMENT_KEYWORDS = {
    "settlement", "not settled", "settlement delay", "sales not settled",
    "merchant settlement", "my sales", "settle",
}

AGENT_CASH_IN_KEYWORDS = {
    "cash in", "cash-in", "agent cash in", "agent er kache", "agent এর কাছে",
    "agent", "ক্যাশ ইন", "ক্যাশইন", "agent এ cash in",
}

PHISHING_KEYWORDS = {
    "otp", "pin", "password", "scam", "scammer", "fake call",
    "verification code", "verification", "block my account",
    "account will be blocked", "call from", "called me",
    "ওটিপি", "পিন", "পাসওয়ার্ড", "স্ক্যাম",
    "otp", "pin", "scam", "fake",
}

# ── Time-related patterns (English / Bangla / Banglish) ──────────────
TIME_KEYWORDS = {
    "today", "ajke", "আজ",
    "yesterday", "kal", "গতকাল",
    "tomorrow", "agami kal", "আগামীকাল",
    "morning", "sokale", "সকালে",
    "afternoon", "dupore", "দুপুরে",
    "evening", "shondha", "সন্ধ্যায়",
    "night", "rate", "রাতে",
}

# ── Amount extraction patterns ────────────────────────────────────────
# Bengali digits 0-9: ০১২৩৪৫৬৭৮৯
BENGALI_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# ── Time hint extraction patterns ─────────────────────────────────────
# Parsed in helpers.py using these markers
RELATIVE_DAY_MAP = {
    "today": 0, "ajke": 0, "আজ": 0,
    "yesterday": -1, "kal": -1, "গতকাল": -1,
    "tomorrow": 1, "agami kal": 1, "আগামীকাল": 1,
}

# 12-hour time patterns
TIME_PATTERNS_12H = [
    r"(\d{1,2})\s*pm",
    r"(\d{1,2})\s*am",
    r"(\d{1,2}):(\d{2})\s*pm",
    r"(\d{1,2}):(\d{2})\s*am",
]

# 24-hour time patterns
TIME_PATTERNS_24H = [
    r"(\d{2}):(\d{2})",
]

# ── Amount extraction regex ───────────────────────────────────────────
# Matches "5000" (bare), "5000 taka" (suffix), and "BDT 5000" (prefix)
AMOUNT_RE = r"(?:(\d[\d,]*)\s*(?:taka|tk|টাকা|bdt)?|(?:bdt|taka|tk|টাকা)\s*(\d[\d,]*))"
