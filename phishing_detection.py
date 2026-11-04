"""Basic heuristic screening of suspicious messages; not a definitive classifier."""
import re

KEYWORD_GROUPS = {
    "Urgency or threat language": ["urgent", "immediately", "expire today", "blocked", "suspended", "within 24 hours", "last warning"],
    "Banking or KYC language": ["kyc", "bank account", "verify your account", "update your account", "net banking", "upi"],
    "Sensitive information language": ["otp", "pin", "password", "cvv", "card number", "login details"],
    "Unexpected reward language": ["you won", "winner", "claim your prize", "cashback reward"],
}

def analyze_message(message: str) -> dict:
    text = (message or "").lower()
    score, indicators = 0, []
    for group, phrases in KEYWORD_GROUPS.items():
        matches = [phrase for phrase in phrases if phrase in text]
        if matches:
            score += 20 if group == "Sensitive information language" else 15
            indicators.append(f"{group}: matched {', '.join(matches)}.")
    urls = re.findall(r"https?://[^\s<>'\"]+", message or "", flags=re.IGNORECASE)
    if urls:
        score += 15
        indicators.append("A URL is present. Check it independently; URL presence alone does not prove phishing.")
    if any("@" in url or "xn--" in url.lower() for url in urls):
        score += 20
        indicators.append("A URL has a potentially deceptive formatting cue.")
    score = min(score, 100)
    severity = "HIGH" if score >= 60 else "MEDIUM" if score >= 30 else "LOW"
    if not text.strip():
        score, severity = 0, "LOW"
        summary = "No message was provided for analysis."
    elif indicators:
        summary = f"{len(indicators)} suspicious signal(s) matched the demo rules. This is not a definitive phishing verdict."
    else:
        summary = "No configured suspicious signals were detected. This does not prove the message is safe."
    recommendations = [
        "Do not click links or open attachments if you are unsure about the message.",
        "Open the institution's official app or independently verified website instead of following the message link.",
        "Never share OTPs, PINs, passwords, or CVVs in response to a message.",
    ]
    if severity == "HIGH":
        recommendations.insert(0, "Request human review before treating the message as confirmed phishing.")
    return {"score": score, "severity": severity, "indicators": indicators, "summary": summary, "recommendations": recommendations}
