"""HTTP client for the CyberShield FastAPI backend."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_URL = os.getenv("CYBERSHIELD_API_URL", "http://127.0.0.1:8000").rstrip("/")
TIMEOUT = 15

def _request(method, path, **kwargs):
    response = requests.request(method, f"{API_URL}{path}", timeout=TIMEOUT, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else {}

def backend_health():
    try:
        data = _request("GET", "/health")
        return {"online": True, "data": data}
    except requests.RequestException as exc:
        return {"online": False, "error": str(exc)}

def analyze_transaction_api(payload):
    return _request("POST", "/api/transactions/analyze", json=payload)

def analyze_phishing_api(message):
    return _request("POST", "/api/phishing/analyze", json={"message": message})

def get_incidents_api(limit=50):
    return _request("GET", "/api/incidents", params={"limit": limit})

def get_overview_api():
    return _request("GET", "/api/security/overview")

def get_discord_status():
    return _request("GET", "/api/discord/status")

def run_agent_workflow_api(payload):
    return _request("POST", "/api/agent-workflow/run", json=payload)

def get_agent_workflow_api():
    return _request("GET", "/api/agent-workflow")

def share_incident_api(incident_id: str):
    return _request("POST", f"/api/incidents/{incident_id}/share")

def chat_api(message: str, history: list):
    return _request("POST", "/api/chat", json={"message": message, "history": history})
