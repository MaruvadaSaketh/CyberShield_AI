import re
from urllib.parse import urlparse

URGENCY = re.compile(r'\b(urgent|immediately|account blocked|suspended|verify now|act now)\b', re.I)
CREDENTIALS = re.compile(r'\b(otp|password|pin|cvv|card number|bank details)\b', re.I)
LINK = re.compile(r'https?://[^\s<>]+', re.I)
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "rb.gy"}

def analyze_message(message: str) -> dict:
    flags, urls = [], LINK.findall(message)
    if URGENCY.search(message):
        flags.append("Urgent or threatening language")
    if CREDENTIALS.search(message):
        flags.append("Requests sensitive credentials or payment details")
    for raw in urls:
        host = (urlparse(raw).hostname or "").lower()
        if host in SHORTENERS:
            flags.append("URL shortener detected")
        if host and not (host.endswith("sbi.co.in") or host.endswith("onlinesbi.sbi")):
            flags.append("Link domain is not an identified official SBI domain")
    score = min(100, len(set(flags)) * 30)
    return {
        "risk_score": score,
        "severity": "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW",
        "flags": list(dict.fromkeys(flags)) or ["No configured text indicators were detected."],
        "urls_found": len(urls),
        "recommendation": "Do not open links or reply with sensitive information. Verify independently using the official bank app or a known official channel.",
        "note": "Text-only heuristic screening; URLs are not opened or verified and this is not a definitive phishing verdict.",
    }
