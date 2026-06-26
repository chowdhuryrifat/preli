import re
from typing import List, Tuple


_DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
    (
        r"(?:please\s+)?"
        r"(?:provide|enter|share|give|send|tell|need|require|want)\s+"
        r"(?:us|me)\s+(?:the\s+)?(?:\w+(?:'s)?\s+)?(?:your\s+)?"
        r"(?:PIN|OTP|password|CVV|card\s+number|16[- ]?digit\s+card\s+number)"
        r"|"
        r"(?:please\s+)?"
        r"(?:provide|enter|share|give|send|tell|need|require|want)\s+"
        r"(?:the\s+)?(?:\w+(?:'s)?\s+)?(?:your\s+)?"
        r"(?:PIN|OTP|password|CVV|card\s+number|16[- ]?digit\s+card\s+number)",
        "please do not share your PIN, OTP, or password with anyone"
    ),
    # Bangla equivalents: দিন / দাও / শেয়ার করুন + পিন / ওটিপি / পাসওয়ার্ড / সিভিভি /
    # কার্ড নাম্বার — both word orders, plus Latin credentials in mixed-script attacks.
    (
        r"(?:দয়া\s+করে\s+)?"
        r"(?:দিন|দাও|শেয়ার\s*করুন|বলুন|পাঠান|জানান|চান|চাই)\s+"
        r"(?:আপনার\s+(?:কার্ডের\s+)?|কার্ডের\s+)?"
        r"(?:পিন|ওটিপি|পাসওয়ার্ড|সিভিভি|কার্ড\s*নাম্বার|কার্ড\s*নম্বর)"
        r"|"
        r"(?:আপনার\s+(?:কার্ডের\s+)?|কার্ডের\s+)?"
        r"(?:পিন|ওটিপি|পাসওয়ার্ড|সিভিভি|কার্ড\s*নাম্বার|কার্ড\s*নম্বর)"
        r"\s+(?:দিন|দাও|শেয়ার\s*করুন|বলুন|পাঠান|জানান|চান|চাই)"
        r"|"
        # Possessive split: "আপনার কার্ডের নাম্বার দিন" — কার্ডের splits the compound
        r"(?:আপনার\s+)?কার্ডের\s+(?:নাম্বার|নম্বর)\s+(?:দিন|দাও|শেয়ার\s*করুন|বলুন|পাঠান|জানান|চান|চাই)"
        r"|"
        # Mixed-script: Latin credential keyword + Bengali verb
        r"(?:PIN|OTP|password|CVV)\s+(?:দিন|দাও|শেয়ার\s*করুন|বলুন|পাঠান|জানান|চান|চাই)",
        "অনুগ্রহ করে আপনার পিন, ওটিপি বা পাসওয়ার্ড কারো সাথে শেয়ার করবেন না"
    ),
    (
        r"we\s+will\s+(?:give\s+you\s+)?(?:a\s+)?refund\b(?!\s+policy)",
        "any eligible amount will be returned through official channels"
    ),
    (
        r"(?:your\s+)?refund\s+(?:has\s+been|is\s+being|will\s+be)\s+(?:processed|issued|approved)",
        "any eligible amount will be returned through official channels"
    ),
    (
        r"we\s+will\s+reverse\b(?!\s+(?:policy|workflow|flow))",
        "the transaction will be reviewed for possible reversal"
    ),
    (
        r"(?:the\s+)?transaction\s+(?:will\s+be|is\s+being)\s+reversed",
        "the transaction will be reviewed for possible reversal"
    ),
    (
        r"(?:we\s+will|your\s+account\s+(?:will\s+be|has\s+been))\s+unblock",
        "your account will be reviewed by our team"
    ),
    (
        r"(?:call|contact|reach)\s+(?:this\s+)?(?:number|phone|hotline)[:\s]*[\d\s\(\),\.\-]{7,}",
        "use official support channels for assistance"
    ),
    (
        r"(?:contact|call|reach\s+out\s+to)\s+"
        r"(?!us|our|you|the\s+company|support|customer\s+support|official\s+channels)"
        r"\s*(?:\w+\s+){0,3}"
        r"(?:support|team|department|help|assistance|service)"
        r"(?:\s+at\s+[\d\s\(\),\.\-]{7,})?",
        "use official support channels for assistance"
    ),
    (
        r"(?:contact|call|reach)\s+(?:\w+\s+){0,5}[\d\s\(\),\.\-]{7,}",
        "use official support channels for assistance"
    ),
    # ── Spec §10 expanding to Bangla variants ──────────────────────────
    # S1: Credential — Bangla card number / CVV / PIN variants
    (
        r"(?:আপনার\s+)?(?:কার্ডের\s+)?(?:১৬\s*ডিজিটের?\s*)?"
        r"(?:কার্ড\s*নাম্বার|কার্ড\s*নম্বর|ক্রেডিট\s*কার্ড)"
        r"(?:\s+(?:দিন|দাও|শেয়ার\s*করুন|বলুন|পাঠান|জানান))?"
        r"|"
        r"(?:CVV|সিভিভি|cvv)\s+(?:দিন|দাও|শেয়ার\s*করুন|বলুন|পাঠান|জানান)",
        "অনুগ্রহ করে আপনার পিন, ওটিপি বা পাসওয়ার্ড কারো সাথে শেয়ার করবেন না"
    ),
    # S1: 16-digit card number pattern (consecutive or grouped digits)
    (
        r"(?:card\s+(?:number|no|#)\s*[:\-]?\s*)?"
        r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"
        r"|"
        r"\b\d{16}\b"
        r"|"
        r"(?:কার্ডের?\s*)?(?:নাম্বার|নম্বর)\s*[:\-]?\s*\d{16}",
        "please do not share your card details with anyone"
    ),
    # S2: Refund promise — Bangla
    (
        r"(?:আমরা\s+)?(?:আপনাকে\s+)?(?:টাকা\s+)?ফেরত\s+(?:দেব|দিব|দেওয়া\s+হবে|পাবেন)"
        r"|"
        r"(?:আপনার\s+)?(?:রিফান্ড|রিফ্যান্ড)\s+(?:প্রক্রিয়াধীন|প্রক্রিয়া\s+হচ্ছে|হয়ে\s+গেছে)"
        r"|"
        r"(?:টাকা\s+)?ফেরত\s+(?:পাবেন|পাবে|পাওয়া\s+যাবে)",
        "যে কোনও যোগ্য পরিমাণ অফিসিয়াল চ্যানেলের মাধ্যমে ফেরত দেওয়া হবে"
    ),
    # S3: Third-party contact — Bangla
    (
        r"(?:কল\s+করুন|যোগাযোগ\s+করুন|ফোন\s+করুন)\s+"
        r"(?:এই\s+)?(?:নম্বরে|নাম্বারে|ফোনে)[:\s]*[\d\s\(\),\.\-]{7,}"
        r"|"
        r"(?:আমাদের\s+)?(?:সাপোর্ট|হেল্প|সাহায্য)\s+(?:টিম|দল)\s*[:\s]*[\d\s\(\),\.\-]{7,}",
        "সাহায্যের জন্য অফিসিয়াল সাপোর্ট চ্যানেল ব্যবহার করুন"
    ),
    # S2: Additional English refund promise — "you will receive a refund"
    (
        r"(?:you\s+will\s+receive|you'll\s+get|we\s+will\s+issue)\s+(?:a\s+)?"
        r"(?:full\s+)?refund",
        "any eligible amount will be returned through official channels"
    ),
    # S3: "reach out to our agent at" variant
    (
        r"(?:reach\s+out\s+to|get\s+in\s+touch\s+with)\s+(?:our\s+)?"
        r"(?:agent|representative|team)"
        r"(?:\s+(?:at|on|via)\s+[\d\s\(\),\.\-]{7,})?",
        "use official support channels for assistance"
    ),
]


_SAFE_IMMEDIATE_PREFIX_PATTERNS: List[re.Pattern] = [
    re.compile(r, re.IGNORECASE)
    for r in [
        r"do\s+not\s+",
        r"don't\s+",
        r"never\s+",
        r"under\s+no\s+circumstances\s+",
    ]
]


def _is_already_safe(text: str, idx: int) -> bool:
    start = max(0, idx - 45)
    window = text[start:idx]

    if not window:
        return False

    last_segment = window.lower()

    for prefix_pattern in _SAFE_IMMEDIATE_PREFIX_PATTERNS:
        if prefix_pattern.search(last_segment):
            return True

    if any(
        phrase in last_segment
        for phrase in [
            "please do not",
            "we never",
            "you must never",
            " do not ",
            " don't ",
            " will never ",
            "under no circumstances",
        ]
    ):
        return True

    return False


def safety_check(text: str) -> str:
    if not text:
        return text

    result = text
    for pattern_str, replacement in _DANGEROUS_PATTERNS:
        pattern = re.compile(pattern_str, re.IGNORECASE)
        new_result: List[str] = []
        last_end = 0

        for match in pattern.finditer(result):
            start, end = match.start(), match.end()
            new_result.append(result[last_end:start])

            if _is_already_safe(result, start):
                new_result.append(match.group())
            else:
                new_result.append(replacement)
            last_end = end

        new_result.append(result[last_end:])
        result = "".join(new_result)

    return result
