import json
from datetime import datetime

import pandas as pd
import streamlit as st

from api_client import (analyze_transaction_api, analyze_phishing_api, get_incidents_api, get_overview_api, backend_health)

st.set_page_config(page_title="CyberShield AI | SOC Dashboard", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --bg:#08111f; --panel:#101d30; --panel2:#13243a; --line:#263a53; --text:#e8f0fb; --muted:#91a4bc; --cyan:#53e0d0; --blue:#65a9ff; --red:#ff667d; --amber:#ffc66d; }
.stApp { background:radial-gradient(ellipse at 80% 0%, #132d46 0%, var(--bg) 45%); color:var(--text); font-family:'DM Sans',sans-serif; }
[data-testid="stSidebar"] { background:#091524; border-right:1px solid #1c3048; }
[data-testid="stSidebar"] * { color:#dbe7f7; }
.block-container { max-width:1500px; padding-top:1.3rem; padding-bottom:2.5rem; }
h1,h2,h3 { font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.03em; }
.hero { background:linear-gradient(115deg,rgba(20,43,69,.98),rgba(10,75,83,.85)); border:1px solid #2d6572; border-radius:22px; padding:28px 32px; margin-bottom:20px; box-shadow:0 18px 60px rgba(0,0,0,.18); }
.eyebrow { color:var(--cyan); font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:.16em; }
.hero h1 { font-size:40px; margin:4px 0 0; color:#f5f9ff; }
.hero p { color:#b8cbe0; margin:.35rem 0 0; }
.pill { display:inline-block; border:1px solid #326777; background:#102e3c; color:#7ef1df; border-radius:999px; padding:5px 10px; font-size:11px; font-weight:700; letter-spacing:.04em; }
.kpi { background:linear-gradient(145deg,#122239,#0d1a2c); border:1px solid #243b56; border-radius:17px; padding:17px 18px; min-height:120px; }
.kpi-label { color:#9db0c7; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:.08em; }
.kpi-value { color:#f3f7ff; font-size:32px; font-weight:700; font-family:'Space Grotesk',sans-serif; margin-top:7px; line-height:1.1; }
.kpi-note { color:#7e96b1; font-size:12px; margin-top:8px; }
.panel { background:rgba(15,29,47,.86); border:1px solid #243951; border-radius:18px; padding:20px 22px; margin-bottom:16px; }
.panel-title { color:#edf5ff; font-size:18px; font-weight:700; margin-bottom:3px; }
.panel-sub { color:#8ea4bd; font-size:12px; margin-bottom:15px; }
.muted { color:var(--muted); }
.badge { display:inline-block; border-radius:7px; padding:5px 9px; font-size:11px; font-weight:700; letter-spacing:.07em; }
.badge-high { background:#421e2b; border:1px solid #81384b; color:#ff899b; }
.badge-medium { background:#3a2d1b; border:1px solid #75552d; color:#ffd28b; }
.badge-low { background:#12382f; border:1px solid #236a58; color:#78e4c0; }
.small { font-size:12px; color:#91a4bc; }
div[data-testid="stMetric"] { background:linear-gradient(145deg,#122239,#0c192a); border:1px solid #263d57; padding:15px 17px; border-radius:15px; }
div[data-testid="stMetricLabel"] { color:#9db0c7; }
div[data-testid="stMetricValue"] { color:#f3f7ff; font-family:'Space Grotesk',sans-serif; }
.stButton>button, .stDownloadButton>button { border-radius:10px; font-weight:700; border:1px solid #326779; }
.stButton>button[kind="primary"] { background:linear-gradient(90deg,#16a7a1,#227cc0); color:white; border:0; }
[data-testid="stDataFrame"] { border:1px solid #263d57; border-radius:12px; overflow:hidden; }
hr { border-color:#243951; }
footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

if "incidents" not in st.session_state:
    st.session_state.incidents = []
if "demo_loaded" not in st.session_state:
    st.session_state.demo_loaded = False

with st.sidebar:
    st.markdown("<div style='font-family:Space Grotesk;font-size:23px;font-weight:700'>🛡️ CyberShield <span style='color:#53e0d0'>AI</span></div>", unsafe_allow_html=True)
    st.caption("SECURITY OPERATIONS CENTER")
    health = backend_health()
    if health.get("online"):
        st.success("Backend connected", icon="🟢")
    else:
        st.warning("Backend offline — start FastAPI", icon="⚠️")
    st.divider()
    page = st.radio("WORKSPACE", ["Security Overview", "Transaction Analysis", "Phishing Analysis", "Incident History", "AI Agent Workflow"], label_visibility="visible")
    st.divider()
    st.markdown("**DEMO CONTROLS**")
    if st.button("↻ Load demo incidents", use_container_width=True):
        st.session_state.incidents = [
            {"id":"DEMO-1042","created_at":"Demo • 09:42","type":"Phishing message","severity":"HIGH","score":80,"summary":"Urgent KYC message with suspicious link","details":{"message_excerpt":"URGENT: KYC expires today. Verify account using a link."},"status":"Needs human review","demo":True},
            {"id":"DEMO-1041","created_at":"Demo • 09:18","type":"Transaction","severity":"HIGH","score":70,"summary":"Large transaction with multiple risk signals","details":{"amount_inr":25000,"typical_amount_inr":3000},"status":"Escalated for review","demo":True},
            {"id":"DEMO-1040","created_at":"Demo • 08:56","type":"Transaction","severity":"MEDIUM","score":40,"summary":"Transaction outside usual pattern","details":{"amount_inr":9000,"typical_amount_inr":4000},"status":"Monitoring","demo":True},
            {"id":"DEMO-1039","created_at":"Demo • 08:21","type":"Phishing message","severity":"LOW","score":15,"summary":"Message contains a URL for manual checking","details":{"message_excerpt":"Your monthly statement is ready."},"status":"Reviewed","demo":True},
        ]
        st.session_state.demo_loaded = True
        st.rerun()
    if st.button("Clear session incidents", use_container_width=True):
        st.session_state.incidents = []
        st.session_state.demo_loaded = False
        st.rerun()
    st.divider()
    st.markdown("<div class='small'>🔒 Use synthetic or sanitized examples only. Never enter real passwords, OTPs, PINs, CVVs, or account numbers.</div>", unsafe_allow_html=True)
    st.markdown("<div class='small' style='margin-top:12px'>Prototype only • No bank connection • Scores are illustrative, not calibrated probabilities.</div>", unsafe_allow_html=True)



def normalize_remote_incident(item):
    """Map backend incident fields to the dashboard's display format."""
    details = item.get("details") or {}
    return {
        "id": item.get("id") or item.get("incident_id") or "API-INCIDENT",
        "created_at": item.get("created_at") or item.get("timestamp") or "—",
        "type": item.get("type") or item.get("incident_type") or item.get("category") or "Security event",
        "severity": str(item.get("severity") or "LOW").upper(),
        "score": item.get("score", item.get("risk_score", 0)),
        "summary": item.get("summary") or item.get("explanation") or "Incident received from backend.",
        "details": details,
        "status": item.get("status") or "Pending human review",
        "demo": False,
    }

def badge(severity):
    cls = {"HIGH":"badge-high","MEDIUM":"badge-medium","LOW":"badge-low"}.get(severity,"badge-low")
    return f"<span class='badge {cls}'>{severity}</span>"


def kpi(label, value, note, accent="cyan"):
    color = {"cyan":"#53e0d0","red":"#ff667d","amber":"#ffc66d","blue":"#65a9ff"}.get(accent,"#53e0d0")
    st.markdown(f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value' style='color:{color}'>{value}</div><div class='kpi-note'>{note}</div></div>", unsafe_allow_html=True)

# Backend incidents are the source of truth; demo incidents remain local and fictional.
backend_incidents = []
backend_error = None
try:
    backend_payload = get_incidents_api(limit=100)
    raw_items = backend_payload.get("items", []) if isinstance(backend_payload, dict) else backend_payload
    backend_incidents = [normalize_remote_incident(item) for item in (raw_items or [])]
except Exception as exc:
    backend_error = str(exc)

incidents = backend_incidents + st.session_state.incidents
high = sum(x["severity"] == "HIGH" for x in incidents)
medium = sum(x["severity"] == "MEDIUM" for x in incidents)
low = sum(x["severity"] == "LOW" for x in incidents)

st.markdown("<div class='hero'><div class='eyebrow'>THREAT INTELLIGENCE • PROTOTYPE</div><h1>🛡️ CyberShield AI</h1><p style='font-size:18px'>Real-Time Fraud Detection & Account Protection</p><p>Explainable risk signals. Faster triage. Human-led response.</p><div style='margin-top:17px'><span class='pill'>● SYSTEM READY</span> &nbsp; <span class='pill'>SYNTHETIC DATA</span> &nbsp; <span class='pill'>HUMAN REVIEW REQUIRED</span></div></div>", unsafe_allow_html=True)

if page == "Security Overview":
    st.markdown("## Security overview")
    st.markdown("Monitor backend incidents, review flagged activity, and launch an analysis.")
    if backend_error:
        st.warning("Backend is not connected. Start the API server to load persisted incidents and run analyses.")
    cols = st.columns(4)
    with cols[0]: kpi("Incidents tracked", len(incidents), "Current session", "blue")
    with cols[1]: kpi("High severity", high, "Priority review", "red")
    with cols[2]: kpi("Medium severity", medium, "Investigate signals", "amber")
    with cols[3]: kpi("Low severity", low, "Lower-priority signals", "cyan")
    left, right = st.columns([1.35, 1])
    with left:
        st.markdown("<div class='panel'><div class='panel-title'>Threat landscape</div><div class='panel-sub'>Incident count grouped by illustrative severity</div>", unsafe_allow_html=True)
        if incidents:
            chart = pd.DataFrame({"Severity":["HIGH","MEDIUM","LOW"],"Incidents":[high,medium,low]}).set_index("Severity")
            st.bar_chart(chart, color="#53e0d0", height=220)
        else:
            st.info("No session incidents yet. Load demo incidents from the sidebar or analyze a sample.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("<div class='panel'><div class='panel-title'>Recent activity</div><div class='panel-sub'>Latest synthetic or manually analyzed events</div>", unsafe_allow_html=True)
        if incidents:
            rows = [{"Incident ID":i["id"],"Time":i["created_at"],"Signal type":i["type"],"Severity":i["severity"],"Score":f"{i['score']}/100","Status":i["status"]} for i in incidents[:8]]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.markdown("<p class='muted'>Your activity feed will appear here after an analysis.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown("<div class='panel'><div class='panel-title'>Recommended demo scenario</div><div class='panel-sub'>A fictional banking-security incident</div><h3 style='color:#ffc66d'>₹25,000 transaction + KYC lure</h3><p class='muted'>A user receives an urgent KYC message and reports a transaction that is unusually large compared with their synthetic baseline.</p>", unsafe_allow_html=True)
        st.markdown(f"{badge('HIGH')} &nbsp; <span class='small'>Illustrative scenario</span>", unsafe_allow_html=True)
        st.markdown("<hr><p><b>1.</b> Run Transaction Analysis</p><p><b>2.</b> Screen the suspicious message</p><p><b>3.</b> Compare indicators in Incident History</p><p><b>4.</b> Review the proposed agent handoff</p></div>", unsafe_allow_html=True)
        st.markdown("<div class='panel'><div class='panel-title'>Operational guardrails</div><p class='small'>✓ Explainable indicators<br>✓ Human review before action<br>✓ No automatic account changes<br>✓ No bank integration or real customer data</p></div>", unsafe_allow_html=True)

elif page == "Transaction Analysis":
    st.markdown("## 💳 Transaction risk analysis")
    st.markdown("<p class='muted'>Evaluate synthetic transaction signals. This is a rule-based demo, not a banking-grade fraud model.</p>", unsafe_allow_html=True)
    with st.form("transaction_form"):
        a,b = st.columns(2)
        with a:
            amount = st.number_input("Transaction amount (₹)", min_value=0.0, value=25000.0, step=500.0)
            usual_amount = st.number_input("Typical amount (₹)", min_value=0.0, value=3000.0, step=500.0)
        with b:
            unusual_time = st.checkbox("Unusual transaction time")
            unusual_location = st.checkbox("Unusual location")
            rapid_transactions = st.checkbox("Multiple rapid transactions")
            reported_phishing = st.checkbox("Related phishing message reported", value=True)
        submitted = st.form_submit_button("Analyze transaction →", type="primary", use_container_width=True)
    if submitted:
        payload = {
            "amount": amount,
            "typical_amount": max(usual_amount, 0.01),
            "unusual_transaction_time": unusual_time,
            "unusual_location": unusual_location,
            "multiple_rapid_transactions": rapid_transactions,
            "related_phishing_message_reported": reported_phishing,
        }
        try:
            api_response = analyze_transaction_api(payload)
            result = api_response.get("result", api_response)
            result.setdefault("score", result.get("risk_score", 0))
            result.setdefault("severity", result.get("risk_level", "LOW"))
            result.setdefault("indicators", result.get("signals", []))
            result.setdefault("summary", result.get("explanation", "Analysis completed by backend."))
            result.setdefault("recommendations", [])
        except Exception as exc:
            st.error(f"Could not reach the backend or analyze the transaction: {exc}")
            st.info("Check that the FastAPI server is running at http://127.0.0.1:8000.")
            st.stop()
        x,y = st.columns([1,2])
        with x:
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>ILLUSTRATIVE RISK SCORE</div><div class='kpi-value'>{result['score']}<span style='font-size:16px;color:#91a4bc'> / 100</span></div>{badge(result['severity'])}", unsafe_allow_html=True)
            st.progress(result["score"])
            st.markdown("<p class='small'>Score is a rule-based indicator, not a probability of fraud.</p></div>", unsafe_allow_html=True)
        with y:
            st.markdown("<div class='panel'><div class='panel-title'>Assessment summary</div>", unsafe_allow_html=True)
            st.write(result["summary"])
            st.markdown("**Evidence indicators**")
            if result["indicators"]:
                for item in result["indicators"]: st.markdown(f"- {item}")
            else: st.info("No configured indicators triggered; that does not prove legitimacy.")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("### Recommended next steps")
        for i,item in enumerate(result["recommendations"],1): st.markdown(f"**{i}.** {item}")
        incident_id = api_response.get("incident_id") or api_response.get("id") or "Saved by backend"
        st.success(f"Backend analysis completed. Incident: {incident_id}")

elif page == "Phishing Analysis":
    st.markdown("## 🎣 Phishing message analysis")
    st.markdown("<p class='muted'>Screen text for suspicious patterns. The prototype does not open, visit, or verify URLs.</p>", unsafe_allow_html=True)
    message = st.text_area("Synthetic or sanitized message", value="URGENT: Your SBI KYC will expire today. Click http://example.invalid/kyc to update immediately.", height=150)
    if st.button("Analyze message →", type="primary", use_container_width=True):
        try:
            api_response = analyze_phishing_api(message)
            result = api_response.get("result", api_response)
            result.setdefault("score", result.get("risk_score", 0))
            result.setdefault("severity", result.get("risk_level", "LOW"))
            result.setdefault("indicators", result.get("signals", []))
            result.setdefault("summary", result.get("explanation", "Analysis completed by backend."))
            result.setdefault("recommendations", [])
        except Exception as exc:
            st.error(f"Could not reach the backend or analyze the message: {exc}")
            st.info("Check that the FastAPI server is running at http://127.0.0.1:8000.")
            st.stop()
        x,y = st.columns([1,2])
        with x:
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>ILLUSTRATIVE RISK SCORE</div><div class='kpi-value'>{result['score']}<span style='font-size:16px;color:#91a4bc'> / 100</span></div>{badge(result['severity'])}", unsafe_allow_html=True)
            st.progress(result["score"])
            st.markdown("<p class='small'>Heuristic screening only; not a definitive verdict.</p></div>", unsafe_allow_html=True)
        with y:
            st.markdown("<div class='panel'><div class='panel-title'>Message assessment</div>", unsafe_allow_html=True)
            st.write(result["summary"])
            st.markdown("**Matched signals**")
            if result["indicators"]:
                for item in result["indicators"]: st.markdown(f"- {item}")
            else: st.info("No configured signals detected; this does not prove the message is safe.")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("### Suggested response")
        for i,item in enumerate(result["recommendations"],1): st.markdown(f"**{i}.** {item}")
        incident_id = api_response.get("incident_id") or api_response.get("id") or "Saved by backend"
        st.success(f"Backend analysis completed. Incident: {incident_id}")

elif page == "Incident History":
    st.markdown("## 🗂️ Incident history")
    st.markdown("Review incidents persisted by the FastAPI backend, plus any local demo entries.")
    if not incidents:
        st.info("No incidents yet. Load demo incidents from the sidebar or run an analysis.")
    else:
        sev_filter = st.multiselect("Filter by severity", ["HIGH","MEDIUM","LOW"], default=["HIGH","MEDIUM","LOW"])
        filtered = [i for i in incidents if i["severity"] in sev_filter]
        st.caption(f"Showing {len(filtered)} of {len(incidents)} incidents")
        for item in filtered:
            with st.expander(f"{item['id']}  •  {item['type']}  •  {item['severity']}  •  {item['score']}/100"):
                st.markdown(f"{badge(item['severity'])} &nbsp; **{item['status']}**", unsafe_allow_html=True)
                st.write(item["summary"])
                st.caption(f"Recorded: {item['created_at']}")
                if item.get("details"): st.json(item["details"])
        st.download_button("Download incident history (JSON)", data=json.dumps(incidents, indent=2), file_name="cybershield_incidents.json", mime="application/json")
    st.caption("Backend incidents are stored by the API. Demo entries are fictional and remain in this Streamlit session only.")
    if backend_error:
        st.warning(f"Backend incident history is unavailable: {backend_error}")

elif page == "AI Agent Workflow":
    st.markdown("## 🤖 AI agent collaboration")
    st.markdown("<p class='muted'>Proposed multi-agent handoff for the hackathon. The agents are not connected or running in this starter build.</p>", unsafe_allow_html=True)
    stages = [
        ("01", "Fraud Detection Agent", "Scores transaction indicators", "#65a9ff"),
        ("02", "Phishing Investigation Agent", "Screens message patterns and URLs without opening them", "#53e0d0"),
        ("03", "Account Protection Agent", "Combines evidence and prepares a prioritized response", "#ffc66d"),
        ("04", "Human Reviewer", "Reviews evidence and decides next action", "#ff899b"),
    ]
    cols = st.columns(4)
    for col,(num,title,desc,color) in zip(cols,stages):
        with col:
            st.markdown(f"<div class='panel' style='min-height:210px'><div style='font-size:30px;font-weight:700;color:{color};font-family:Space Grotesk'>{num}</div><div class='panel-title' style='margin-top:12px'>{title}</div><p class='small'>{desc}</p></div>", unsafe_allow_html=True)
    st.markdown("### Handoff logic")
    st.code("Incident reported\n    ├── Transaction signal → Fraud Detection Agent\n    ├── Message signal → Phishing Investigation Agent\n    └── Evidence summary → Account Protection Agent\n                           └── Human review and decision", language="text")
    st.warning("Switch integration is not configured in this version. These are workflow roles, not live agents. Do not claim automated protection or bank integration in a demo.")
    st.markdown("### Integration checklist")
    st.markdown("- [ ] Configure agents in the Switch environment and verify the actual API/SDK contract.\n- [ ] Send only synthetic incident payloads during development.\n- [ ] Define structured agent outputs and error handling.\n- [ ] Show source indicators and uncertainty in the UI.\n- [ ] Keep all account actions behind a human approval step.")

st.divider()
st.markdown("<div style='display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:#7188a3;font-size:11px'><span>CYBERSHIELD AI • SECURITY OPERATIONS PROTOTYPE</span><span>Educational use only • Not affiliated with SBI or any bank</span></div>", unsafe_allow_html=True)
