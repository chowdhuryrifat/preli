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
        r"(?!us|our|the\s+company|support|customer\s+support|official\s+channels)"
        r"\s*(?:\w+\s+){0,3}"
        r"(?:support|team|department|help|assistance|service)"
        r"(?:\s+at\s+[\d\s\(\),\.\-]{7,})?",
        "use official support channels for assistance"
    ),
    (
        r"(?:contact|call|reach)\s+(?:\w+\s+){0,5}[\d\s\(\),\.\-]{7,}",
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
