import re

PATTERNS = [
    (re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}'), "[EMAIL_REDACTED]"),
    (re.compile(r'(?<!\w)(?:\+?\d[\d ()-]{8,}\d)(?!\w)'), "[PHONE_REDACTED]"),
    (re.compile(r'(?<!\d)\d{12,19}(?!\d)'), "[ACCOUNT_OR_CARD_REDACTED]"),
    (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), "[IP_REDACTED]"),
    (re.compile(r'\b(password|passwd|pwd|otp|pin|cvv|cvc)\s*[:=]\s*[^,\s;]+', re.I), r'\1=[SECRET_REDACTED]'),
]

def redact_text(value: str) -> str:
    result = value
    for pattern, replacement in PATTERNS:
        result = pattern.sub(replacement, result)
    return result

def redact_event(value):
    if isinstance(value, dict):
        return {str(k): redact_event(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_event(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value
