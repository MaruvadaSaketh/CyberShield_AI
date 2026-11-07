# CyberShield AI FastAPI backend

## Run on Windows PowerShell
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

## Run the sample Streamlit UI (second terminal)
```powershell
pip install streamlit requests
$env:CYBERSHIELD_API_URL="http://127.0.0.1:8000"
streamlit run streamlit_example.py
```

## Endpoints
- `GET /health`
- `GET /api/security/overview`
- `POST /api/transactions/analyze`
- `POST /api/analyze/transaction` (alias)
- `POST /api/phishing/analyze`
- `POST /api/analyze/phishing` (alias)
- `GET /api/incidents?severity=HIGH` (severity accepts any letter case)
- `GET /api/incidents?limit=50` (limit 1–200)
- `GET /api/incidents/{incident_id}`
- `GET /api/summary`
- `GET /api/agent-workflow`

## Local sample data and incident storage

`data/sample_requests.json` contains synthetic transaction and phishing request
payloads that can be sent to the corresponding analysis endpoints. The examples
are for local testing only; do not replace them with real credentials or
personal data.

Incidents created by the analysis endpoints are stored in SQLite in
`cybershield.db` by default, so they remain available after the server restarts.
Set `DATABASE_PATH` in `.env` to choose another database file. The API retains
the newest 500 incidents.
On startup, the six examples are analyzed and added as synthetic incidents only
when the incident database is empty. They appear in the overview and incident
list/detail endpoints; subsequent restarts do not duplicate them.
The incident-list response keeps its existing `items` and `count` fields and
adds `kind`, `score`, and `recommendations` aliases to each item for clients
using the alternate incident schema. `/api/summary` reports severity totals
for the retained incident history.

## Discord alerts

Set `DISCORD_BOT_TOKEN` and `DISCORD_CHANNEL_ID` in the local `.env` file to
send transaction and phishing analysis alerts to a Discord channel. The
analysis endpoints continue to return the analysis result if Discord is
unconfigured, unreachable, or rejects an alert. The response's `discord` field
reports `sent: false` and a reason/status code, and the server logs the failure.
Alerts disable automatic mentions, redact recognized email, phone,
account-number, and credential patterns, and are limited to Discord's message
size. Keep the bot token private; do not put it in `.env.example` or commit it.

## Scope

Synthetic hackathon demo only. Risk scores are rule-based signals, not fraud
probabilities. Regex redaction is not guaranteed anonymization; validate it
before production.
