import json
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.schemas import TransactionRequest, PhishingRequest, IncidentReport
from app.risk import assess_transaction
from app.phishing import analyze_message
from app.store import add_incident, list_incidents
from app.redaction import redact_text
from app.notifications import send_discord_alert


def seed_demo_incidents() -> None:
    if list_incidents():
        return

    sample_path = Path(__file__).resolve().parent.parent / "data" / "sample_requests.json"
    with sample_path.open(encoding="utf-8") as sample_file:
        samples = json.load(sample_file)

    for sample in samples["transactions"]:
        result = assess_transaction(TransactionRequest.model_validate(sample["payload"]))
        add_incident({
            "event_type": "transaction_risk",
            "severity": result["severity"],
            "risk_score": result["risk_score"],
            "summary": result["summary"],
            "evidence": result["evidence"],
            "source": "synthetic-demo-seed",
            "recommended_next_steps": result["recommended_next_steps"],
        })

    for sample in samples["phishing_messages"]:
        result = analyze_message(sample["payload"]["message"])
        add_incident({
            "event_type": "phishing_text",
            "severity": result["severity"],
            "risk_score": result["risk_score"],
            "summary": result["note"],
            "evidence": result["flags"],
            "source": "synthetic-demo-seed",
        })


@asynccontextmanager
async def lifespan(_: FastAPI):
    seed_demo_incidents()
    yield


app = FastAPI(
    title="CyberShield AI API",
    description=(
        "Synthetic-data demo backend for transaction risk and phishing analysis."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
origins = [x.strip() for x in settings.cors_origins.split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["*"])

@app.get("/")
def root():
    return {"service": "CyberShield AI API", "docs": "/docs", "mode": "synthetic-demo"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "discord_configured": bool(
            settings.discord_bot_token.strip() and settings.discord_channel_id.strip()
        ),
    }

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
    message = (
        f"CyberShield Transaction Alert\n"
        f"Incident: {incident['incident_id']}\n"
        f"Severity: {result['severity']} | Score: {result['risk_score']}/100\n"
        f"{redact_text(result['summary'])}\nEvidence:\n"
        + "\n".join(f"- {redact_text(item)}" for item in result["evidence"])
        + "\nRecommended next steps:\n"
        + "\n".join(
            f"{index}. {redact_text(item)}"
            for index, item in enumerate(result["recommended_next_steps"], start=1)
        )
        + "\nDemo guidance only."
    )
    discord = await send_discord_alert(message)
    return {**result, "incident_id": incident["incident_id"], "discord": discord}

@app.post("/api/phishing/analyze")
@app.post("/api/analyze/phishing", summary="Analyze phishing message (alternate route)")
async def phishing_analysis(req: PhishingRequest):
    result = analyze_message(req.message)
    incident = add_incident({"event_type": "phishing_text", "severity": result["severity"],
        "risk_score": result["risk_score"], "summary": result["note"],
        "evidence": result["flags"], "source": "phishing-analysis"})
    message = (
        f"CyberShield Phishing Review\n"
        f"Incident: {incident['incident_id']}\n"
        f"Severity: {result['severity']} | Score: {result['risk_score']}/100\n"
        f"{redact_text(result['note'])}\nIndicators:\n"
        + "\n".join(f"- {redact_text(item)}" for item in result["flags"])
        + f"\nRecommendation: {redact_text(result['recommendation'])}"
        + f"\nSanitized excerpt: {redact_text(req.message)}"
    )
    discord = await send_discord_alert(message)
    return {**result, "incident_id": incident["incident_id"], "discord": discord}

@app.get("/api/incidents")
def incidents(severity: str | None = Query(
    default=None, pattern="^(?i:LOW|MEDIUM|HIGH)$"
), limit: int = Query(default=50, ge=1, le=200)):
    items = list_incidents(severity)[:limit]
    compatible_items = [
        {
            **item,
            "kind": item.get("kind", item.get("event_type")),
            "score": item.get("score", item.get("risk_score")),
            "recommendations": item.get(
                "recommendations", item.get("recommended_next_steps", [])
            ),
        }
        for item in items
    ]
    return {"items": compatible_items, "count": len(compatible_items)}


@app.get("/api/summary")
def summary():
    items = list_incidents()
    return {
        "total": len(items),
        "high": sum(item["severity"] == "HIGH" for item in items),
        "medium": sum(item["severity"] == "MEDIUM" for item in items),
        "low": sum(item["severity"] == "LOW" for item in items),
    }

@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: str):
    found = next((i for i in list_incidents() if i["incident_id"] == incident_id), None)
    if not found:
        raise HTTPException(status_code=404, detail="Incident not found in this server session")
    return found


@app.post("/api/incidents/send-to-switch")
async def send_incident_to_switch(report: IncidentReport):
    if not 0 <= report.risk_score <= 100:
        raise HTTPException(status_code=400, detail="Invalid risk score")

    required_settings = {
        "SWITCH_BRIDGE_URL": settings.switch_bridge_url,
        "SWITCH_AGENT_ID": settings.switch_agent_id,
        "SWITCH_AGENT_KEY": settings.switch_agent_key,
        "SWITCH_ROOM_ID": settings.switch_room_id,
    }
    missing_settings = [
        name for name, value in required_settings.items() if not value.strip()
    ]
    if missing_settings:
        raise HTTPException(
            status_code=503,
            detail=(
                "Switch incident delivery is not configured; missing "
                + ", ".join(missing_settings)
            ),
        )

    message = (
        f"CyberShield AI — {redact_text(report.incident_id)}\n"
        f"Type: {redact_text(report.incident_type)}\n"
        f"Severity: {report.severity}\n"
        f"Risk score: {report.risk_score}/100\n"
        f"Summary: {redact_text(report.summary)}"
    )
    payload = {
        "room_id": settings.switch_room_id,
        "content": message,
    }
    headers = {
        "Authorization": f"Bearer {settings.switch_agent_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.switch_bridge_url.rstrip('/')}/agents/"
                f"{quote(settings.switch_agent_id, safe='')}/message",
                headers=headers,
                json=payload,
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not reach Switch to submit the incident report",
        ) from exc

    if response.is_error:
        raise HTTPException(
            status_code=response.status_code,
            detail="Switch could not accept the incident report",
        )

    discord = await send_discord_alert(
        f"CyberShield Switch Report Submitted\n{message}"
    )
    return {
        "status": "submitted",
        "incident_id": report.incident_id,
        "discord": discord,
    }


@app.get("/api/agent-workflow")
def agent_workflow():
    return {"room": settings.switch_room_name, "agents": [
        {"name": "Incident Commander", "role": "Coordinate triage and summarize"},
        {"name": "Threat Detection", "role": "Assess event indicators"},
        {"name": "Cross-Account Correlation", "role": "Compare sanitized signals"},
        {"name": "Fraud Risk Analyst", "role": "Explain risk indicators"},
        {"name": "Account Recovery", "role": "Provide safe, user-guided recovery steps"}],
        "human_review_required": True, "switch_enabled": settings.switch_enabled}
