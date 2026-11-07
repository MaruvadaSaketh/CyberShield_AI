import json
import logging
import re
import time

import httpx
from fastapi import HTTPException
from google import genai

from app.config import settings
from app.redaction import redact_text
from app.schemas import ChatMessage, IncidentReport

_logger = logging.getLogger(__name__)
_agent_client = None
_RETRYABLE_UPSTREAM_CODES = {429, 500, 502, 503, 504}
_AGENT_RETRY_DELAYS_SECONDS = (0.5,)
CHAT_SYSTEM_INSTRUCTION = (
    "You are CyberShield AI, a defensive security assistant inside a synthetic "
    "security operations demo. Answer questions within CyberShield AI's capabilities: "
    "synthetic transaction risk analysis, phishing message screening, incident review, "
    "and safe account protection. Provide advisory guidance only; every assessment "
    "requires human review, and no account actions are taken automatically. Use "
    "synthetic or sanitized examples and never solicit or repeat real credentials "
    "such as passwords, OTPs, PINs, CVVs, or account numbers. Refuse requests for "
    "credential theft, unauthorized access, malware creation, exploit development, "
    "or any abusive use. Keep answers concise."
)


def get_agent_client():
    global _agent_client

    if _agent_client is not None:
        return _agent_client

    if not settings.google_api_key.strip():
        raise HTTPException(
            status_code=503,
            detail="AI workflow is not configured; set GOOGLE_API_KEY in .env.",
        )

    try:
        _agent_client = genai.Client(api_key=settings.google_api_key)
    except Exception as exc:
        _logger.warning("Gemini client initialization failed.")
        raise HTTPException(
            status_code=503,
            detail="Unable to initialize the Gemini client.",
        ) from exc
    return _agent_client


def is_agent_workflow_configured() -> bool:
    return bool(settings.google_api_key.strip())


def redact_sensitive_data(text: str) -> str:
    text = redact_text(text)
    return re.sub(
        r"\b(?:OTP|PIN|PASSWORD|PASSWD|PWD|TOKEN|CVV|CVC)\s*[:=]\s*\S+",
        "[REDACTED_CREDENTIAL]",
        text,
        flags=re.IGNORECASE,
    )


def _local_triage(incident: dict[str, object]) -> dict[str, object]:
    severity = incident["severity"]
    risk_score = incident["risk_score"]
    priority = "urgent" if severity == "HIGH" else "prompt" if severity == "MEDIUM" else "routine"
    analysis = (
        "Gemini is unavailable, so this is deterministic local triage, not an AI-generated assessment.\n\n"
        f"Priority: {priority} human review. The submitted score is {risk_score}/100 "
        f"with severity {severity}. Reported summary: {incident['summary']}\n\n"
        "Recommended safe steps:\n"
        "1. Verify the event through a trusted, independently obtained channel.\n"
        "2. Review related activity and escalate according to your organization's process.\n"
        "3. Never share passwords, PINs, CVVs, or one-time codes; do not take account action based on this triage alone."
    )
    return {
        "incident_id": incident["incident_id"],
        "agent_name": "CyberShield local triage",
        "analysis": analysis,
        "analysis_source": "local_rule_based_fallback",
        "human_review_required": True,
    }


def _upstream_status_code(exc: Exception) -> int | None:
    code = getattr(exc, "code", None)
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
    try:
        return int(code) if code is not None else None
    except (TypeError, ValueError):
        return None


def analyze_incident_with_agent(report: IncidentReport) -> dict[str, object]:
    client = get_agent_client()
    incident = report.model_dump()
    incident["incident_id"] = redact_sensitive_data(incident["incident_id"])
    incident["incident_type"] = redact_sensitive_data(incident["incident_type"])
    incident["summary"] = redact_sensitive_data(incident["summary"])

    for attempt in range(len(_AGENT_RETRY_DELAYS_SECONDS) + 1):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=json.dumps(incident),
            )
            analysis = response.text
            if not analysis:
                raise HTTPException(
                    status_code=502,
                    detail="The agent returned an empty response.",
                )
            return {
                "incident_id": incident["incident_id"],
                "agent_name": settings.agent_name,
                "analysis": analysis,
                "analysis_source": "gemini",
                "human_review_required": True,
            }
        except HTTPException:
            raise
        except Exception as exc:
            upstream_code = _upstream_status_code(exc)
            if upstream_code in _RETRYABLE_UPSTREAM_CODES:
                if attempt < len(_AGENT_RETRY_DELAYS_SECONDS):
                    _logger.warning(
                        "Gemini returned retryable status %s; retrying once.",
                        upstream_code,
                    )
                    time.sleep(_AGENT_RETRY_DELAYS_SECONDS[attempt])
                    continue
                _logger.warning(
                    "Gemini remains unavailable (upstream status %s); using local triage.",
                    upstream_code,
                )
                return _local_triage(incident)
            if upstream_code in {401, 403}:
                _logger.warning("Agent authentication or authorization was rejected.")
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Gemini rejected credentials. "
                        "Check GOOGLE_API_KEY in the backend environment."
                    ),
                ) from exc
            if upstream_code == 404:
                _logger.warning(
                    "Configured Gemini model was not found; using local triage."
                )
                return _local_triage(incident)
            _logger.warning(
                "Agent analysis failed (%s; upstream code=%s)",
                type(exc).__name__,
                upstream_code,
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to analyze the incident. Check the backend logs and verify "
                    "the Gemini model and GOOGLE_API_KEY."
                ),
            ) from exc

    raise HTTPException(
        status_code=503,
        detail="Gemini is temporarily unavailable and local triage could not complete.",
    )


def run_chat_with_agent(messages: list[ChatMessage]) -> dict[str, object]:
    client = get_agent_client()
    contents = [
        genai.types.Content(
            role="model" if message.role == "assistant" else "user",
            parts=[genai.types.Part(text=redact_sensitive_data(message.content))],
        )
        for message in messages
    ]
    for attempt in range(len(_AGENT_RETRY_DELAYS_SECONDS) + 1):
        try:
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=genai.types.GenerateContentConfig(
                    system_instruction=CHAT_SYSTEM_INSTRUCTION
                ),
            )
            reply = response.text
            if not reply:
                raise HTTPException(
                    status_code=502,
                    detail="The agent returned an empty response.",
                )
            return {"reply": reply}
        except HTTPException:
            raise
        except Exception as exc:
            upstream_code = _upstream_status_code(exc)
            if upstream_code in _RETRYABLE_UPSTREAM_CODES:
                if attempt < len(_AGENT_RETRY_DELAYS_SECONDS):
                    _logger.warning(
                        "Gemini returned retryable status %s; retrying once.",
                        upstream_code,
                    )
                    time.sleep(_AGENT_RETRY_DELAYS_SECONDS[attempt])
                    continue
                _logger.warning(
                    "Gemini remains unavailable (upstream status %s).",
                    upstream_code,
                )
                raise HTTPException(
                    status_code=502,
                    detail="The AI chat is temporarily unavailable. Try again shortly.",
                ) from exc
            if upstream_code in {401, 403}:
                _logger.warning("Agent authentication or authorization was rejected.")
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Gemini rejected credentials. "
                        "Check GOOGLE_API_KEY in the backend environment."
                    ),
                ) from exc
            if upstream_code == 404:
                _logger.warning("Configured Gemini model was not found.")
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "The configured Gemini model was not found. "
                        "Check the Gemini model setting in the backend config."
                    ),
                ) from exc
            _logger.warning(
                "AI chat failed (%s; upstream code=%s)",
                type(exc).__name__,
                upstream_code,
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Unable to run the AI chat. Check the backend logs and verify "
                    "the Gemini model and GOOGLE_API_KEY."
                ),
            ) from exc

    raise HTTPException(
        status_code=503,
        detail="The AI chat is temporarily unavailable.",
    )
