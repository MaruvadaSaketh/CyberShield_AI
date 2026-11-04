"""Illustrative, explainable transaction risk rules for synthetic demo data."""

def analyze_transaction(amount: float, usual_amount: float, unusual_time: bool = False,
                        unusual_location: bool = False, rapid_transactions: bool = False,
                        reported_phishing: bool = False) -> dict:
    score = 0
    indicators = []
    if usual_amount > 0 and amount >= 3 * usual_amount and amount >= 10000:
        score += 25
        indicators.append("Amount is at least 3× the typical amount and at least ₹10,000.")
    if unusual_time:
        score += 10
        indicators.append("Transaction was reported at an unusual time.")
    if unusual_location:
        score += 20
        indicators.append("Location differs from the synthetic normal pattern.")
    if rapid_transactions:
        score += 20
        indicators.append("Multiple transactions were reported in a short period.")
    if reported_phishing:
        score += 25
        indicators.append("A suspicious message was reported with this transaction.")
    score = min(score, 100)
    severity = "HIGH" if score >= 70 else "MEDIUM" if score >= 40 else "LOW"
    summary = (f"{len(indicators)} configured risk indicator(s) were triggered. This is a risk signal, not confirmation of fraud."
               if indicators else "No configured risk indicators were triggered. This does not prove the transaction is legitimate.")
    recommendations = [
        "Verify the transaction in the bank's official app or through a contact method you independently verify.",
        "If you do not recognize it, contact the bank promptly using its official channel.",
        "Never share an OTP, PIN, password, or CVV.",
    ]
    if severity == "HIGH":
        recommendations.insert(0, "Escalate for urgent human review; this prototype cannot block transactions.")
    return {"score": score, "severity": severity, "indicators": indicators, "summary": summary, "recommendations": recommendations}
