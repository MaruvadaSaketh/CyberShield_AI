import os
import requests
import streamlit as st

API = os.getenv("CYBERSHIELD_API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="CyberShield AI", page_icon="🛡️", layout="wide")
st.title("🛡️ CyberShield AI")
st.caption("Synthetic security-event demo • Human review required")
tabs = st.tabs(["Transaction Analysis", "Phishing Analysis", "Incident History", "AI Agent Workflow"])

with tabs[0]:
    st.subheader("Analyze a simulated transaction")
    c1, c2 = st.columns(2)
    amount = c1.number_input("Transaction amount (₹)", min_value=0.0, value=25000.0, step=1000.0)
    typical = c2.number_input("Typical transaction amount (₹)", min_value=1.0, value=3000.0, step=500.0)
    c1, c2 = st.columns(2)
    unusual_time = c1.checkbox("Unusual transaction time")
    unusual_location = c2.checkbox("Unusual location")
    rapid = c1.checkbox("Multiple rapid transactions")
    phishing = c2.checkbox("Related phishing message reported")
    if st.button("Analyze transaction", type="primary"):
        payload = {"amount": amount, "typical_amount": typical, "unusual_transaction_time": unusual_time,
                   "unusual_location": unusual_location, "multiple_rapid_transactions": rapid,
                   "related_phishing_message_reported": phishing}
        try:
            data = requests.post(f"{API}/api/transactions/analyze", json=payload, timeout=15).json()
            st.metric("Illustrative risk score", f'{data["risk_score"]}/100', data["severity"])
            st.info(data["summary"])
            st.write("**Evidence indicators**")
            for item in data["evidence"]: st.write(f"• {item}")
            st.write("**Recommended next steps**")
            for item in data["recommended_next_steps"]: st.write(f"• {item}")
            st.caption(f'Incident: {data["incident_id"]}')
        except requests.RequestException as e:
            st.error(f"API request failed: {e}")

with tabs[1]:
    message = st.text_area("Message text", height=180, placeholder="Use synthetic/sanitized text only; do not include real credentials.")
    if st.button("Analyze message", type="primary"):
        try:
            data = requests.post(f"{API}/api/phishing/analyze", json={"message": message}, timeout=15).json()
            st.metric("Illustrative risk score", f'{data["risk_score"]}/100', data["severity"])
            for flag in data["flags"]: st.write(f"• {flag}")
            st.warning(data["recommendation"])
            st.caption(data["note"])
        except requests.RequestException as e:
            st.error(f"API request failed: {e}")

with tabs[2]:
    severity = st.selectbox("Severity", ["All", "HIGH", "MEDIUM", "LOW"])
    if st.button("Refresh incident history"):
        params = {} if severity == "All" else {"severity": severity}
        try:
            data = requests.get(f"{API}/api/incidents", params=params, timeout=10).json()
            st.dataframe(data["items"], use_container_width=True)
        except requests.RequestException as e:
            st.error(f"API request failed: {e}")

with tabs[3]:
    try:
        data = requests.get(f"{API}/api/agent-workflow", timeout=10).json()
        st.write(f'Room: **{data["room"]}**')
        for agent in data["agents"]: st.write(f'**{agent["name"]}** — {agent["role"]}')
        st.caption("Switch messaging requires configuration for your installed protocol version.")
    except requests.RequestException as e:
        st.error(f"API request failed: {e}")
