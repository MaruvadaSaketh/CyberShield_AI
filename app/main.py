import json
import re
import smtplib
from contextlib import asynccontextmanager
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.schemas import (
    AgentWorkflowResponse,
    TransactionRequest,
    PhishingRequest,
    IncidentReport,
)
from app.risk import assess_transaction
from app.phishing import analyze_message
from app.store import add_incident, list_incidents
from app.redaction import redact_text
from app.notifications import (
    check_discord_configuration,
    configured_token_fingerprint,
    send_discord_alert,
)
from app.agent_workflow import is_agent_workflow_configured

redact_sensitive_data = redact_text


# ---------------------------------------------------------------------------
# Rule-based chat engine (no external AI dependency)
# ---------------------------------------------------------------------------

_KNOWLEDGE: list[tuple[list[str], str]] = [
    (
        ["hi", "hello", "hey", "help", "what can you do", "who are you"],
        "👋 I'm **CyberShield AI**, your cybersecurity assistant. I can help you with:\n"
        "- 🔍 Understanding incidents in the database\n"
        "- 💳 Transaction fraud signals\n"
        "- 🎣 Phishing detection\n"
        "- 🛡️ Account protection advice\n\n"
        "Try asking: *show high incidents*, *what is phishing*, *how is risk score calculated*",
    ),
    (
        ["show incidents", "list incidents", "all incidents", "recent incidents", "how many incidents"],
        "__INCIDENTS__",
    ),
    (
        ["high", "high severity", "high incidents", "critical"],
        "__HIGH__",
    ),
    (
        ["medium", "medium severity", "medium incidents"],
        "__MEDIUM__",
    ),
    (
        ["low", "low severity", "low incidents"],
        "__LOW__",
    ),
    (
        ["summary", "overview", "stats", "statistics", "total"],
        "__SUMMARY__",
    ),
    (
        ["phishing", "phishing attack", "what is phishing", "phishing detection"],
        "🎣 **Phishing** is a social-engineering attack where an attacker impersonates a trusted entity to steal credentials or money.\n\n"
        "**CyberShield detects phishing by checking for:**\n"
        "- Urgency keywords (URGENT, expires, verify now)\n"
        "- Suspicious URLs or domains\n"
        "- Requests for OTPs, PINs, or passwords\n"
        "- Impersonation of banks or government bodies\n\n"
        "⚠️ Never click links in suspicious messages. Verify through official channels only.",
    ),
    (
        ["transaction", "fraud", "transaction fraud", "what is fraud", "fraud detection"],
        "💳 **Transaction fraud** occurs when unauthorized or suspicious transactions are made on an account.\n\n"
        "**CyberShield scores transactions based on:**\n"
        "- Amount vs. typical spending (ratio)\n"
        "- Unusual transaction time\n"
        "- Unusual location\n"
        "- Multiple rapid transactions\n"
        "- Related phishing message reported\n\n"
        "A score above 60 is HIGH severity and requires immediate human review.",
    ),
    (
        ["risk score", "score", "how is score calculated", "scoring"],
        "📊 **Risk Score (0–100)** is a rule-based indicator — not a fraud probability.\n\n"
        "**Scoring factors:**\n"
        "- Large amount vs. typical: +30 pts\n"
        "- Unusual time: +15 pts\n"
        "- Unusual location: +20 pts\n"
        "- Multiple rapid transactions: +20 pts\n"
        "- Related phishing reported: +15 pts\n\n"
        "**Severity bands:** LOW < 30 | MEDIUM 30–59 | HIGH ≥ 60\n\n"
        "⚠️ Scores are illustrative signals, not calibrated fraud probabilities.",
    ),
    (
        ["account protection", "protect account", "account recovery", "account safe"],
        "🛡️ **Account Protection Steps:**\n"
        "1. Never share OTPs, PINs, CVVs, or passwords with anyone\n"
        "2. Verify any suspicious contact through official bank numbers\n"
        "3. Enable 2-factor authentication on all accounts\n"
        "4. Report suspicious transactions immediately\n"
        "5. Freeze your card if unauthorized access is suspected\n\n"
        "CyberShield's Account Recovery agent provides advisory steps — all actions require human approval.",
    ),
    (
        ["otp", "pin", "password", "cvv", "credential"],
        "🔒 **Never share** OTPs, PINs, CVVs, or passwords — not even with bank staff or this system.\n\n"
        "CyberShield redacts all credentials from analysis and never stores or transmits them.",
    ),
    (
        ["discord", "alert", "notification"],
        "📢 **Discord Alerts:** CyberShield can send transaction and phishing analysis alerts to a configured Discord channel.\n\n"
        "Set `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` in `.env` to enable. "
        "All alerts are redacted before sending.",
    ),
    (
        ["agent", "ai agent", "workflow", "gemini"],
        "🤖 **AI Agent Workflow:** CyberShield provides a Gemini-assisted account recovery review.\n\n"
        "Configure `GOOGLE_API_KEY` in `.env` to enable AI analysis.\n\n"
        "The agent output is **advisory only** — no account actions are taken automatically.",
    ),
    (
        ["email", "share", "share data", "send email"],
        "📤 **Share Data:** Use the *Share Data* button on the AI Agent Workflow page to email a redacted incident report to the security team.\n\n"
        "Configure `SMTP_USER` and `SMTP_PASSWORD` (Gmail App Password) in `.env` to enable.",
    ),
]


def _chat_reply(message: str) -> str:
    msg = message.lower().strip()
    incidents = list_incidents()

    for keywords, response in _KNOWLEDGE:
        if any(kw in msg for kw in keywords):
            if response == "__INCIDENTS__":
                if not incidents:
                    return "📭 No incidents found in the database yet. Run a transaction or phishing analysis first."
                lines = [f"📋 **{len(incidents)} incidents** in the database:\n"]
                for i in incidents[:10]:
                    lines.append(f"- `{i['incident_id']}` | {i['severity']} | Score: {i.get('risk_score', '?')}/100 | {i.get('summary', '')[:60]}...")
                if len(incidents) > 10:
                    lines.append(f"\n_...and {len(incidents) - 10} more. Use Incident History page to see all._")
                return "\n".join(lines)

            if response == "__HIGH__":
                hi = [i for i in incidents if i["severity"] == "HIGH"]
                if not hi:
                    return "✅ No HIGH severity incidents in the database."
                lines = [f"🔴 **{len(hi)} HIGH severity incidents:**\n"]
                for i in hi[:8]:
                    lines.append(f"- `{i['incident_id']}` | Score: {i.get('risk_score', '?')}/100 | {i.get('summary', '')[:70]}...")
                return "\n".join(lines)

            if response == "__MEDIUM__":
                med = [i for i in incidents if i["severity"] == "MEDIUM"]
                if not med:
                    return "✅ No MEDIUM severity incidents in the database."
                lines = [f"🟡 **{len(med)} MEDIUM severity incidents:**\n"]
                for i in med[:8]:
                    lines.append(f"- `{i['incident_id']}` | Score: {i.get('risk_score', '?')}/100 | {i.get('summary', '')[:70]}...")
                return "\n".join(lines)

            if response == "__LOW__":
                lo = [i for i in incidents if i["severity"] == "LOW"]
                if not lo:
                    return "✅ No LOW severity incidents in the database."
                lines = [f"🟢 **{len(lo)} LOW severity incidents:**\n"]
                for i in lo[:8]:
                    lines.append(f"- `{i['incident_id']}` | Score: {i.get('risk_score', '?')}/100 | {i.get('summary', '')[:70]}...")
                return "\n".join(lines)

            if response == "__SUMMARY__":
                high = sum(i["severity"] == "HIGH" for i in incidents)
                medium = sum(i["severity"] == "MEDIUM" for i in incidents)
                low = sum(i["severity"] == "LOW" for i in incidents)
                return (
                    f"📊 **CyberShield Incident Summary**\n\n"
                    f"- 🔴 HIGH: **{high}**\n"
                    f"- 🟡 MEDIUM: **{medium}**\n"
                    f"- 🟢 LOW: **{low}**\n"
                    f"- 📋 Total: **{len(incidents)}**\n\n"
                    f"Use the *Security Overview* page for charts and recent activity."
                )

            return response

    # Check if asking about a specific incident ID
    match = re.search(r"CS-\d{8}-\d{6}-[A-Z0-9]+", message.upper())
    if match:
        iid = match.group()
        found = next((i for i in incidents if i["incident_id"] == iid), None)
        if found:
            return (
                f"🔍 **Incident `{found['incident_id']}`**\n\n"
                f"- Severity: **{found['severity']}**\n"
                f"- Risk Score: **{found.get('risk_score', '?')}/100**\n"
                f"- Type: {found.get('event_type', '—')}\n"
                f"- Summary: {found.get('summary', '—')}\n"
                f"- Recorded: {found.get('created_at', '—')}"
            )
        return f"❌ Incident `{iid}` not found in the database."

    return (
        "🤔 I'm not sure about that. Here's what I can help with:\n\n"
        "- **show incidents** — list all incidents\n"
        "- **high / medium / low** — filter by severity\n"
        "- **summary** — incident statistics\n"
        "- **phishing** — phishing detection info\n"
        "- **transaction fraud** — fraud scoring info\n"
        "- **risk score** — how scoring works\n"
        "- **account protection** — safety steps\n"
        "- Paste an incident ID like `CS-20250101-120000-ABC123`"
    )


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

def seed_demo_incidents() -> None:
    if list_incidents():
        return
    sample_path = Path(__file__).resolve().parent.parent / "data" / "sample_requests.json"
    with sample_path.open(encoding="utf-8") as f:
        samples = json.load(f)
    for sample in samples["transactions"]:
        result = assess_transaction(TransactionRequest.model_validate(sample["payload"]))
        add_incident({"event_type": "transaction_risk", "severity": result["severity"],
            "risk_score": result["risk_score"], "summary": result["summary"],
            "evidence": result["evidence"], "source": "synthetic-demo-seed",
            "recommended_next_steps": result["recommended_next_steps"]})
    for sample in samples["phishing_messages"]:
        result = analyze_message(sample["payload"]["message"])
        add_incident({"event_type": "phishing_text", "severity": result["severity"],
            "risk_score": result["risk_score"], "summary": result["note"],
            "evidence": result["flags"], "source": "synthetic-demo-seed"})


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_demo_incidents()
    yield


app = FastAPI(title="CyberShield AI API", version="1.0.0", lifespan=lifespan)
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.get("/")
def root():
    return {"service": "CyberShield AI API", "docs": "/docs", "mode": "synthetic-demo"}


@app.get("/health")
def health():
    return {"status": "ok", "discord_configured": bool(
        settings.discord_bot_token.strip() and settings.discord_channel_id.strip()),
        "discord_token_fingerprint": configured_token_fingerprint()}


@app.get("/api/discord/status")
async def discord_status():
    """Check the bot token and channel access without sending a message."""
    return await check_discord_configuration()


@app.get("/api/security/overview")
def overview():
    items = list_incidents()
    return {"total_incidents": len(items),
            "high": sum(i["severity"] == "HIGH" for i in items),
            "medium": sum(i["severity"] == "MEDIUM" for i in items),
            "low": sum(i["severity"] == "LOW" for i in items),
            "note": "Incident history is stored in SQLite; at most 500 incidents are retained."}


@app.post("/api/transactions/analyze")
async def transaction_analysis(req: TransactionRequest):
    result = assess_transaction(req)
    incident = add_incident({"event_type": "transaction_risk", "severity": result["severity"],
        "risk_score": result["risk_score"], "summary": result["summary"],
        "evidence": result["evidence"], "source": "transaction-analysis",
        "recommended_next_steps": result["recommended_next_steps"]})
    msg = (f"CyberShield Transaction Alert\nIncident: {incident['incident_id']}\n"
           f"Severity: {result['severity']} | Score: {result['risk_score']}/100\n"
           f"{redact_text(result['summary'])}\nEvidence:\n"
           + "\n".join(f"- {redact_text(i)}" for i in result["evidence"])
           + "\nRecommended next steps:\n"
           + "\n".join(f"{n}. {redact_text(s)}" for n, s in enumerate(result["recommended_next_steps"], 1))
           + "\nDemo guidance only.")
    discord = await send_discord_alert(msg)
    return {**result, "incident_id": incident["incident_id"], "discord": discord}


@app.post("/api/phishing/analyze")
@app.post("/api/analyze/phishing", summary="Analyze phishing message (alternate route)")
async def phishing_analysis(req: PhishingRequest):
    result = analyze_message(req.message)
    incident = add_incident({"event_type": "phishing_text", "severity": result["severity"],
        "risk_score": result["risk_score"], "summary": result["note"],
        "evidence": result["flags"], "source": "phishing-analysis"})
    msg = (f"CyberShield Phishing Review\nIncident: {incident['incident_id']}\n"
           f"Severity: {result['severity']} | Score: {result['risk_score']}/100\n"
           f"{redact_text(result['note'])}\nIndicators:\n"
           + "\n".join(f"- {redact_text(i)}" for i in result["flags"])
           + f"\nRecommendation: {redact_text(result['recommendation'])}"
           + f"\nSanitized excerpt: {redact_text(req.message)}")
    discord = await send_discord_alert(msg)
    return {**result, "incident_id": incident["incident_id"], "discord": discord}


@app.get("/api/incidents")
def incidents(severity: str | None = Query(default=None, pattern="^(?i:LOW|MEDIUM|HIGH)$"),
              limit: int = Query(default=50, ge=1, le=200)):
    items = list_incidents(severity)[:limit]
    compatible_items = [{**item,
        "kind": item.get("kind", item.get("event_type")),
        "score": item.get("score", item.get("risk_score")),
        "recommendations": item.get("recommendations", item.get("recommended_next_steps", []))}
        for item in items]
    return {"items": compatible_items, "count": len(compatible_items)}


@app.get("/api/summary")
def summary():
    items = list_incidents()
    return {"total": len(items),
            "high": sum(i["severity"] == "HIGH" for i in items),
            "medium": sum(i["severity"] == "MEDIUM" for i in items),
            "low": sum(i["severity"] == "LOW" for i in items)}


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: str):
    found = next((i for i in list_incidents() if i["incident_id"] == incident_id), None)
    if not found:
        raise HTTPException(status_code=404, detail="Incident not found in this server session")
    return found


SHARE_RECIPIENTS = [
    "ruchiisingh2003@gmail.com",
    "msakethckp25@gmail.com",
    "akashraj.iti@gmail.com",
    "karsourin17@gmail.com",
]


@app.post("/api/incidents/{incident_id}/share")
def share_incident(incident_id: str):
    if not (settings.smtp_user.strip() and settings.smtp_password.strip()):
        raise HTTPException(status_code=503, detail="Email not configured. Set SMTP_USER and SMTP_PASSWORD in .env.")
    found = next((i for i in list_incidents() if i["incident_id"] == incident_id), None)
    if not found:
        raise HTTPException(status_code=404, detail="Incident not found")
    body = (
        f"CyberShield AI — Incident Report\n\n"
        f"Incident ID : {found['incident_id']}\n"
        f"Type        : {found.get('event_type', '—')}\n"
        f"Severity    : {found['severity']}\n"
        f"Risk Score  : {found.get('risk_score', '—')}/100\n"
        f"Summary     : {redact_text(found.get('summary', ''))}\n\n"
        "Evidence:\n" + "\n".join(f"  - {redact_text(e)}" for e in found.get("evidence", [])) + "\n\n"
        "Recommended next steps:\n" + "\n".join(f"  {n}. {redact_text(s)}" for n, s in enumerate(found.get("recommended_next_steps", []), 1)) + "\n\n"
        f"Recorded at : {found.get('created_at', '—')}\n\nSynthetic demo data only. Human review required."
    )
    msg = MIMEMultipart()
    msg["From"] = settings.smtp_user
    msg["To"] = ", ".join(SHARE_RECIPIENTS)
    msg["Subject"] = f"[CyberShield AI] Incident {incident_id} — {found['severity']}"
    msg.attach(MIMEText(body, "plain"))
    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_user, SHARE_RECIPIENTS, msg.as_string())
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                server.ehlo(); server.starttls(); server.ehlo()
                server.login(settings.smtp_user, settings.smtp_password)
                server.sendmail(settings.smtp_user, SHARE_RECIPIENTS, msg.as_string())
    except smtplib.SMTPAuthenticationError:
        raise HTTPException(status_code=502, detail="Email delivery failed: Authentication error. Use a Gmail App Password.")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Email delivery failed: {exc}")
    return {"shared": True, "recipients": SHARE_RECIPIENTS, "incident_id": incident_id}


class _ChatRequest(BaseModel):
    message: str
    history: list = []


@app.post("/api/chat")
def chat(req: _ChatRequest):
    reply = _chat_reply(req.message)
    return {"reply": reply}


@app.get("/api/agent-workflow")
def agent_workflow():
    return {"agents": [
        {"name": "Incident Commander", "role": "Coordinate triage and summarize"},
        {"name": "Threat Detection", "role": "Assess event indicators"},
        {"name": "Fraud Risk Analyst", "role": "Explain risk indicators"},
        {"name": "Account Recovery", "role": "Provide safe, user-guided recovery steps"},
    ], "human_review_required": True,
       "discord_configured": bool(settings.discord_bot_token.strip() and settings.discord_channel_id.strip()),
       "ai_workflow_enabled": is_agent_workflow_configured()}


@app.post("/api/agent-workflow/run", response_model=AgentWorkflowResponse,
          summary="Run account recovery review for an incident")
async def run_agent_workflow(report: IncidentReport) -> AgentWorkflowResponse:
    # Look up full incident data from the store
    incident_data = next(
        (i for i in list_incidents() if i["incident_id"] == report.incident_id), None
    )

    severity = report.severity
    risk_score = report.risk_score
    summary = redact_sensitive_data(report.summary)
    evidence = incident_data.get("evidence", []) if incident_data else []
    steps = incident_data.get("recommended_next_steps", []) if incident_data else []
    event_type = incident_data.get("event_type", report.incident_type) if incident_data else report.incident_type
    created_at = incident_data.get("created_at", "—") if incident_data else "—"

    priority = "🔴 Urgent" if severity == "HIGH" else "🟡 Prompt" if severity == "MEDIUM" else "🟢 Routine"
    evidence_lines = "\n".join(f"• {e}" for e in evidence) if evidence else "No evidence indicators recorded."
    steps_lines = "\n".join(f"{n}. {s}" for n, s in enumerate(steps, 1)) if steps else "No recommended steps recorded."

    analysis = (
        f"**Incident ID:** {redact_sensitive_data(report.incident_id)}  \n"
        f"**Type:** {event_type}  \n"
        f"**Severity:** {severity} — {priority} review  \n"
        f"**Risk Score:** {risk_score}/100  \n"
        f"**Recorded:** {created_at}  \n\n"
        f"**Summary**  \n{summary}  \n\n"
        f"**Evidence Indicators**  \n{evidence_lines}  \n\n"
        f"**Recommended Next Steps**  \n{steps_lines}"
    )

    discord_msg = (
        f"CyberShield Account Recovery Review\n"
        f"Incident: {redact_sensitive_data(report.incident_id)}\n"
        f"Type: {event_type} | Severity: {severity} | Score: {risk_score}/100\n"
        f"Summary: {summary}\n"
        f"Evidence:\n{evidence_lines}\n"
        f"Steps:\n{steps_lines}\n"
        "Human review required; no account actions were taken."
    )
    discord = await send_discord_alert(discord_msg)

    return AgentWorkflowResponse(
        incident_id=redact_sensitive_data(report.incident_id),
        agent_name="Account Recovery Review",
        analysis=analysis,
        analysis_source="incident_store",
        human_review_required=True,
        discord=discord,
    )
