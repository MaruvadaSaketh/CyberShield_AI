# CyberShield AI — Integrated Streamlit Frontend

This folder contains your existing Streamlit dashboard connected to the separate FastAPI backend.

## 1. Folder arrangement

Keep this folder alongside the cloned backend folder:

```text
CyberShield-AI/
├── app.py
├── api_client.py
├── requirements.txt
└── backend/
    ├── app/
    ├── requirements.txt
    └── .env.example
```

## 2. Install frontend dependencies

Open a terminal in the folder containing this `app.py`:

```cmd
py -m pip install -r requirements.txt
```

## 3. Start backend (Terminal 1)

```cmd
cd backend
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

Keep this terminal running. API docs: http://127.0.0.1:8000/docs

## 4. Start frontend (Terminal 2)

Return to the folder containing the integrated `app.py`:

```cmd
cd ..
py -m streamlit run app.py
```

If Terminal 2 is already at the project root, do not run `cd ..`.

## Notes

- The Streamlit UI now sends transaction and phishing analyses to FastAPI.
- Incident History loads persisted backend incidents; demo entries remain local.
- Use synthetic or sanitized examples only. Never enter real credentials, OTPs, PINs, CVVs, or account numbers.
- This is an educational prototype. Scores are illustrative and are not calibrated fraud probabilities.
- The dashboard's AI Agent Workflow remains a proposed workflow unless you separately configure and verify the actual agent/Switch integration.
