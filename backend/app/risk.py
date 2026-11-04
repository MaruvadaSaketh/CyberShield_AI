from app.schemas import TransactionRequest

def assess_transaction(req: TransactionRequest) -> dict:
    score, evidence = 0, []
    if req.amount >= 3 * req.typical_amount and req.amount >= 10000:
        score += 30
        evidence.append("Amount is at least 3x typical and at least ₹10,000.")
    if req.unusual_transaction_time:
        score += 15
        evidence.append("Transaction time is outside the user's usual pattern.")
    if req.unusual_location:
        score += 20
        evidence.append("Transaction location is unusual.")
    if req.multiple_rapid_transactions:
        score += 20
        evidence.append("Multiple rapid transactions were reported.")
    if req.related_phishing_message_reported:
        score += 20
        evidence.append("A suspicious message was reported alongside the transaction.")
    score = min(score, 100)
    severity = "HIGH" if score >= 70 else "MEDIUM" if score >= 35 else "LOW"
    return {
        "risk_score": score, "severity": severity,
        "evidence": evidence or ["No configured risk indicators were triggered."],
        "summary": "This is a rule-based risk signal, not confirmation or probability of fraud.",
        "recommended_next_steps": [
            "Verify the transaction in the bank's official app or through a contact method you independently verify.",
            "If you do not recognize it, contact the bank promptly using its official channel.",
            "Never share an OTP, PIN, password, or CVV.",
        ],
        "human_review_required": True,
    }
