# CyberShield AI
**Real-Time Fraud Detection & Account Protection** — hackathon prototype.

## Features
- Streamlit dashboard with overview, transaction analysis, phishing analysis, incident history, and agent-workflow plan.
- Explainable heuristic checks using synthetic demo data.
- Export of current-session incident history as JSON.
- Switch collaboration integration is a separate implementation step.

## Run locally
1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. In the terminal, run:

   ```bash
   python -m venv .venv
   ```

4. Activate the environment:
   - Windows PowerShell: `.\.venv\Scripts\Activate.ps1`
   - Windows Command Prompt: `.venv\Scripts\activate.bat`

5. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

6. Start the app:

   ```bash
   python -m streamlit run app.py
   ```

## Safety and limitations
- Uses synthetic demo data and illustrative heuristics, not a validated bank fraud model.
- Scores are not probabilities of fraud.
- Not connected to SBI or any bank; it does not block transactions or change accounts.
- Never enter real account numbers, passwords, OTPs, PINs, CVVs, or other sensitive data.
- The agent-workflow page is a plan, not a live Switch integration. Configure and test actual agents through Switch before claiming integration.
