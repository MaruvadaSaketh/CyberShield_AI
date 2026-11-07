import html
import json
import csv
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

from api_client import (
    API_URL,
    analyze_transaction_api,
    analyze_phishing_api,
    get_incidents_api,
    get_overview_api,
    get_agent_workflow_api,
    backend_health,
    run_agent_workflow_api,
    share_incident_api,
    chat_api,
)

st.set_page_config(page_title="CyberShield AI | SOC Dashboard", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root{--bg:#08111f;--panel:#101d30;--line:#263a53;--text:#e8f0fb;--muted:#91a4bc;--cyan:#53e0d0;--blue:#65a9ff;--red:#ff667d;--amber:#ffc66d;}
html,body,.stApp{background:radial-gradient(ellipse at 80% 0%,#132d46 0%,var(--bg) 45%);color:var(--text);font-family:'DM Sans',sans-serif;}
[data-testid="stSidebar"]{background:#091524;border-right:1px solid #1c3048;}
[data-testid="stSidebar"] *{color:#dbe7f7;}
.block-container{max-width:1400px;padding-top:1.2rem;padding-bottom:2rem;}
h1,h2,h3{font-family:'Space Grotesk',sans-serif!important;letter-spacing:-.03em;}
.hero{background:linear-gradient(115deg,rgba(20,43,69,.98),rgba(10,75,83,.85));border:1px solid #2d6572;border-radius:20px;padding:26px 30px;margin-bottom:22px;box-shadow:0 16px 48px rgba(0,0,0,.2);}
.eyebrow{color:var(--cyan);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.16em;}
.hero h1{font-size:36px;margin:4px 0 0;color:#f5f9ff;}
.hero p{color:#b8cbe0;margin:.3rem 0 0;font-size:15px;}
.pill{display:inline-block;border:1px solid #326777;background:#102e3c;color:#7ef1df;border-radius:999px;padding:4px 10px;font-size:11px;font-weight:700;letter-spacing:.04em;margin-top:14px;}
.kpi{background:linear-gradient(145deg,#122239,#0d1a2c);border:1px solid #243b56;border-radius:16px;padding:16px 18px;min-height:110px;}
.kpi-label{color:#9db0c7;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;}
.kpi-value{color:#f3f7ff;font-size:30px;font-weight:700;font-family:'Space Grotesk',sans-serif;margin-top:6px;line-height:1.1;}
.kpi-note{color:#7e96b1;font-size:11px;margin-top:6px;}
.panel{background:rgba(15,29,47,.9);border:1px solid #243951;border-radius:16px;padding:18px 20px;margin-bottom:14px;}
.panel-title{color:#edf5ff;font-size:17px;font-weight:700;margin-bottom:2px;}
.panel-sub{color:#8ea4bd;font-size:12px;margin-bottom:12px;}
.badge{display:inline-block;border-radius:6px;padding:4px 9px;font-size:11px;font-weight:700;letter-spacing:.06em;}
.badge-high{background:#421e2b;border:1px solid #81384b;color:#ff899b;}
.badge-medium{background:#3a2d1b;border:1px solid #75552d;color:#ffd28b;}
.badge-low{background:#12382f;border:1px solid #236a58;color:#78e4c0;}
.small{font-size:12px;color:#91a4bc;}
.muted{color:#91a4bc;}
div[data-testid="stMetric"]{background:linear-gradient(145deg,#122239,#0c192a);border:1px solid #263d57;padding:14px 16px;border-radius:14px;}
div[data-testid="stMetricLabel"]{color:#9db0c7;}
div[data-testid="stMetricValue"]{color:#f3f7ff;font-family:'Space Grotesk',sans-serif;}
.stButton>button,.stDownloadButton>button{border-radius:9px;font-weight:700;border:1px solid #326779;}
.stButton>button[kind="primary"]{background:linear-gradient(90deg,#16a7a1,#227cc0);color:white;border:0;}
[data-testid="stDataFrame"]{border:1px solid #263d57;border-radius:11px;overflow:hidden;}
hr{border-color:#243951;}
footer{visibility:hidden;}
.stExpander{border:1px solid #243951!important;border-radius:12px!important;background:rgba(15,29,47,.7)!important;margin-bottom:8px!important;}
</style>
""", unsafe_allow_html=True)

# ── session state ──────────────────────────────────────────────────────────────
if "incidents" not in st.session_state:
    st.session_state.incidents = []
if "demo_loaded" not in st.session_state:
    st.session_state.demo_loaded = False
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# ── sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<div style='font-family:Space Grotesk;font-size:22px;font-weight:700;padding:4px 0'>🛡️ CyberShield <span style='color:#53e0d0'>AI</span></div>", unsafe_allow_html=True)
    st.caption("SECURITY OPERATIONS CENTER")
    health = backend_health()
    if health.get("online"):
        st.success("Backend connected", icon="🟢")
    else:
        st.warning("Backend offline — start FastAPI", icon="⚠️")
    st.divider()
    page = st.radio("WORKSPACE", [
        "🏠 Security Overview",
        "💳 Transaction Analysis",
        "🎣 Phishing Analysis",
        "🗂️ Incident History",
        "🤖 AI Agent Workflow",
        "💬 AI Chat",
    ], label_visibility="visible")
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
    if st.button("🗑 Clear session incidents", use_container_width=True):
        st.session_state.incidents = []
        st.session_state.demo_loaded = False
        st.rerun()
    st.divider()
    st.markdown("<div class='small'>🔒 Use synthetic or sanitized examples only. Never enter real passwords, OTPs, PINs, CVVs, or account numbers.</div>", unsafe_allow_html=True)
    st.markdown("<div class='small' style='margin-top:10px'>Prototype only • No bank connection • Scores are illustrative signals.</div>", unsafe_allow_html=True)

# ── helpers ────────────────────────────────────────────────────────────────────
def normalize_remote_incident(item):
    details = item.get("details") or {}
    return {
        "id": item.get("id") or item.get("incident_id") or "API-INCIDENT",
        "created_at": item.get("created_at") or item.get("timestamp") or "—",
        "type": item.get("type") or item.get("incident_type") or item.get("event_type") or item.get("category") or "Security event",
        "severity": str(item.get("severity") or "LOW").upper(),
        "score": item.get("score", item.get("risk_score", 0)),
        "summary": item.get("summary") or item.get("explanation") or "Incident received from backend.",
        "details": details,
        "evidence": item.get("evidence") or details.get("evidence") or [],
        "status": item.get("status") or "Pending human review",
        "demo": False,
    }

def badge(severity):
    safe = html.escape(str(severity))
    cls = {"HIGH": "badge-high", "MEDIUM": "badge-medium", "LOW": "badge-low"}.get(safe, "badge-low")
    return f"<span class='badge {cls}'>{safe}</span>"

def kpi(label, value, note, accent="cyan"):
    color = {"cyan":"#53e0d0","red":"#ff667d","amber":"#ffc66d","blue":"#65a9ff"}.get(accent,"#53e0d0")
    st.markdown(f"<div class='kpi'><div class='kpi-label'>{label}</div><div class='kpi-value' style='color:{color}'>{value}</div><div class='kpi-note'>{note}</div></div>", unsafe_allow_html=True)

# ── load backend incidents ─────────────────────────────────────────────────────
backend_incidents = []
backend_error = None
try:
    backend_payload = get_incidents_api(limit=200)
    raw_items = backend_payload.get("items", []) if isinstance(backend_payload, dict) else backend_payload
    backend_incidents = [normalize_remote_incident(i) for i in (raw_items or [])]
except Exception as exc:
    backend_error = str(exc)

incidents = backend_incidents + st.session_state.incidents
high   = sum(x["severity"] == "HIGH"   for x in incidents)
medium = sum(x["severity"] == "MEDIUM" for x in incidents)
low    = sum(x["severity"] == "LOW"    for x in incidents)

# ── hero banner (shown on every page) ─────────────────────────────────────────
st.markdown("""
<div class='hero'>
  <div class='eyebrow'>THREAT INTELLIGENCE • PROTOTYPE</div>
  <h1>🛡️ CyberShield AI</h1>
  <p>Real-Time Fraud Detection &amp; Account Protection — Explainable risk signals. Faster triage. Human-led response.</p>
  <span class='pill'>● SYSTEM READY</span>&nbsp;<span class='pill'>SYNTHETIC DATA</span>&nbsp;<span class='pill'>HUMAN REVIEW REQUIRED</span>
</div>
""", unsafe_allow_html=True)

# strip emoji prefix for matching
_page = page.split(" ", 1)[1] if " " in page else page

# ── Security Overview ──────────────────────────────────────────────────────────
if _page == "Security Overview":
    st.markdown("## Security Overview")
    st.markdown("<p class='muted'>Monitor backend incidents, review flagged activity, and launch an analysis.</p>", unsafe_allow_html=True)
    if backend_error:
        st.warning("Backend is not connected. Start the FastAPI server to load persisted incidents.", icon="⚠️")

    cols = st.columns(4)
    with cols[0]: kpi("Total Incidents", len(incidents), "All severities", "blue")
    with cols[1]: kpi("High Severity", high, "Priority review", "red")
    with cols[2]: kpi("Medium Severity", medium, "Investigate signals", "amber")
    with cols[3]: kpi("Low Severity", low, "Lower-priority signals", "cyan")

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    left, right = st.columns([1.4, 1])

    with left:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>📊 Threat Landscape</div><div class='panel-sub'>Incident count by severity</div>", unsafe_allow_html=True)
        if incidents:
            chart = pd.DataFrame({"Severity": ["HIGH", "MEDIUM", "LOW"], "Incidents": [high, medium, low]}).set_index("Severity")
            st.bar_chart(chart, color="#53e0d0", height=200)
        else:
            st.info("No incidents yet. Load demo incidents from the sidebar or run an analysis.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🕐 Recent Activity</div><div class='panel-sub'>Latest analyzed events</div>", unsafe_allow_html=True)
        if incidents:
            rows = [{"Incident ID": i["id"], "Time": i["created_at"], "Type": i["type"], "Severity": i["severity"], "Score": f"{i['score']}/100", "Status": i["status"]} for i in incidents[:8]]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.markdown("<p class='muted'>Your activity feed will appear here after an analysis.</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🎯 Demo Scenario</div><div class='panel-sub'>Fictional banking-security incident</div>", unsafe_allow_html=True)
        st.markdown("<h3 style='color:#ffc66d;margin:8px 0'>₹25,000 transaction + KYC lure</h3>", unsafe_allow_html=True)
        st.markdown("<p class='muted'>A user receives an urgent KYC message alongside an unusually large transaction compared to their synthetic baseline.</p>", unsafe_allow_html=True)
        st.markdown(f"{badge('HIGH')} &nbsp; <span class='small'>Illustrative scenario</span>", unsafe_allow_html=True)
        st.markdown("<hr style='border-color:#243951;margin:12px 0'>", unsafe_allow_html=True)
        st.markdown("<p><b>1.</b> Run Transaction Analysis</p><p><b>2.</b> Screen the suspicious message</p><p><b>3.</b> Compare indicators in Incident History</p><p><b>4.</b> Review the agent handoff</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("<div class='panel-title'>🔒 Operational Guardrails</div>", unsafe_allow_html=True)
        st.markdown("<p class='small'>✓ Explainable indicators<br>✓ Human review before any action<br>✓ No automatic account changes<br>✓ No real bank integration or customer data</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ── Transaction Analysis ───────────────────────────────────────────────────────
elif _page == "Transaction Analysis":
    st.markdown("## 💳 Transaction Risk Analysis")
    st.markdown("<p class='muted'>Evaluate synthetic transaction signals. Rule-based demo — not a banking-grade fraud model.</p>", unsafe_allow_html=True)

    with st.form("transaction_form"):
        st.markdown("#### Transaction details")
        a, b = st.columns(2)
        with a:
            amount = st.number_input("Transaction amount (₹)", min_value=0.0, value=25000.0, step=500.0)
            usual_amount = st.number_input("Typical amount (₹)", min_value=0.0, value=3000.0, step=500.0)
        with b:
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            unusual_time = st.checkbox("Unusual transaction time")
            unusual_location = st.checkbox("Unusual location")
            rapid_transactions = st.checkbox("Multiple rapid transactions")
            reported_phishing = st.checkbox("Related phishing message reported", value=True)
        submitted = st.form_submit_button("🔍 Analyze Transaction", type="primary", use_container_width=True)

    if submitted:
        payload = {
            "amount": amount,
            "typical_amount": max(usual_amount, 0.01),
            "unusual_transaction_time": unusual_time,
            "unusual_location": unusual_location,
            "multiple_rapid_transactions": rapid_transactions,
            "related_phishing_message_reported": reported_phishing,
        }
        with st.spinner("Analyzing transaction…"):
            try:
                api_response = analyze_transaction_api(payload)
                result = api_response.get("result", api_response)
                result.setdefault("score", result.get("risk_score", 0))
                result.setdefault("severity", result.get("risk_level", "LOW"))
                result.setdefault("indicators", result.get("evidence", result.get("signals", [])))
                result.setdefault("summary", result.get("explanation", "Analysis completed."))
                result.setdefault("recommendations", result.get("recommended_next_steps", []))
            except Exception as exc:
                st.error(f"Could not reach the backend: {exc}")
                st.info(f"Check that the FastAPI server is running at {API_URL}.")
                st.stop()

        x, y = st.columns([1, 2])
        with x:
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>RISK SCORE</div><div class='kpi-value'>{result['score']}<span style='font-size:15px;color:#91a4bc'> / 100</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div style='margin:8px 0'>{badge(result['severity'])}</div>", unsafe_allow_html=True)
            st.progress(int(result["score"]))
            st.markdown("<p class='small' style='margin-top:8px'>Rule-based indicator, not a fraud probability.</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with y:
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.markdown("<div class='panel-title'>Assessment Summary</div>", unsafe_allow_html=True)
            st.write(result["summary"])
            if result["indicators"]:
                st.markdown("**Evidence indicators**")
                for item in result["indicators"]:
                    st.markdown(f"- {item}")
            else:
                st.info("No configured indicators triggered.")
            st.markdown("</div>", unsafe_allow_html=True)

        if result["recommendations"]:
            st.markdown("### ✅ Recommended Next Steps")
            for i, item in enumerate(result["recommendations"], 1):
                st.markdown(f"**{i}.** {item}")

        incident_id = api_response.get("incident_id") or api_response.get("id") or "Saved by backend"
        st.success(f"✅ Analysis complete — Incident: `{incident_id}`")

# ── Phishing Analysis ──────────────────────────────────────────────────────────
elif _page == "Phishing Analysis":
    st.markdown("## 🎣 Phishing Message Analysis")
    st.markdown("<p class='muted'>Screen text for suspicious patterns. The prototype does not open, visit, or verify URLs.</p>", unsafe_allow_html=True)

    _csv_path = Path("data/phishing_messages.csv")
    _samples = []
    if _csv_path.exists():
        with _csv_path.open(encoding="utf-8") as _f:
            _samples = list(csv.DictReader(_f))

    if _samples:
        _col1, _col2 = st.columns(2)
        with _col1:
            _categories = sorted(set(r["category"] for r in _samples))
            _sel_cat = st.selectbox("Filter by category", ["All"] + _categories, key="phish_cat")
        with _col2:
            _sel_label = st.selectbox("Filter by label", ["All", "phishing", "legitimate"], key="phish_label")

        _filtered = [r for r in _samples if (_sel_cat == "All" or r["category"] == _sel_cat) and (_sel_label == "All" or r["label"] == _sel_label)]
        if "phish_msg" not in st.session_state:
            st.session_state["phish_msg"] = _samples[0]["message"]
        st.caption(f"{len(_filtered)} message(s) match the filter.")
    else:
        if "phish_msg" not in st.session_state:
            st.session_state["phish_msg"] = "URGENT: Your SBI KYC will expire today. Click http://example.invalid/kyc to update immediately."

    message = st.text_area("Synthetic or sanitized message", value=st.session_state["phish_msg"], height=130, key="phish_textarea")

    if st.button("🔍 Analyze Message", type="primary", use_container_width=True):
        with st.spinner("Analyzing message…"):
            try:
                api_response = analyze_phishing_api(message)
                result = api_response.get("result", api_response)
                result.setdefault("score", result.get("risk_score", 0))
                result.setdefault("severity", result.get("risk_level", "LOW"))
                result.setdefault("indicators", result.get("flags", result.get("signals", [])))
                result.setdefault("summary", result.get("note", result.get("explanation", "Analysis completed.")))
                result.setdefault("recommendations", result.get("recommended_next_steps", []))
            except Exception as exc:
                st.error(f"Could not reach the backend: {exc}")
                st.info(f"Check that the FastAPI server is running at {API_URL}.")
                st.stop()

        x, y = st.columns([1, 2])
        with x:
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.markdown(f"<div class='kpi-label'>RISK SCORE</div><div class='kpi-value'>{result['score']}<span style='font-size:15px;color:#91a4bc'> / 100</span></div>", unsafe_allow_html=True)
            st.markdown(f"<div style='margin:8px 0'>{badge(result['severity'])}</div>", unsafe_allow_html=True)
            st.progress(int(result["score"]))
            st.markdown("<p class='small' style='margin-top:8px'>Heuristic screening only; not a definitive verdict.</p>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with y:
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.markdown("<div class='panel-title'>Message Assessment</div>", unsafe_allow_html=True)
            st.write(result["summary"])
            if result["indicators"]:
                st.markdown("**Matched signals**")
                for item in result["indicators"]:
                    st.markdown(f"- {item}")
            else:
                st.info("No configured signals detected.")
            st.markdown("</div>", unsafe_allow_html=True)

        if result["recommendations"]:
            st.markdown("### ✅ Suggested Response")
            for i, item in enumerate(result["recommendations"], 1):
                st.markdown(f"**{i}.** {item}")

        incident_id = api_response.get("incident_id") or api_response.get("id") or "Saved by backend"
        st.success(f"✅ Analysis complete — Incident: `{incident_id}`")

# ── Incident History ───────────────────────────────────────────────────────────
elif _page == "Incident History":
    st.markdown("## 🗂️ Incident History")
    st.markdown("<p class='muted'>Review incidents persisted by the FastAPI backend, plus any local demo entries. Latest incidents appear first.</p>", unsafe_allow_html=True)

    if backend_error:
        st.warning(f"Backend incident history unavailable: {backend_error}", icon="⚠️")

    if not incidents:
        st.info("No incidents yet. Load demo incidents from the sidebar or run an analysis.")
    else:
        f_col1, f_col2 = st.columns([3, 1])
        with f_col1:
            sev_filter = st.multiselect("Filter by severity", ["HIGH", "MEDIUM", "LOW"], default=["HIGH", "MEDIUM", "LOW"])
        with f_col2:
            page_size = st.selectbox("Per page", [5, 10, 20, 50], index=1)

        filtered = list(reversed([i for i in incidents if i["severity"] in sev_filter]))
        total = len(filtered)
        total_pages = max(1, -(-total // page_size))

        if "ih_page" not in st.session_state:
            st.session_state.ih_page = 1
        if st.session_state.get("ih_last_filter") != (tuple(sev_filter), page_size):
            st.session_state.ih_page = 1
            st.session_state.ih_last_filter = (tuple(sev_filter), page_size)

        current_page = st.session_state.ih_page
        start = (current_page - 1) * page_size
        page_items = filtered[start: start + page_size]

        st.caption(f"Showing {start + 1}–{min(start + page_size, total)} of {total} incidents")

        for item in page_items:
            sev_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(item["severity"], "⚪")
            with st.expander(f"{sev_icon} {item['id']}  •  {item['type']}  •  Score: {item['score']}/100  •  {item['created_at']}"):
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.markdown(badge(item["severity"]), unsafe_allow_html=True)
                    st.markdown(f"<div class='small' style='margin-top:6px'>{item['status']}</div>", unsafe_allow_html=True)
                with c2:
                    st.write(item["summary"])
                if item.get("details"):
                    st.json(item["details"])

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        p1, p2, p3 = st.columns([1, 2, 1])
        with p1:
            if st.button("← Previous", disabled=current_page <= 1, use_container_width=True):
                st.session_state.ih_page -= 1
                st.rerun()
        with p2:
            st.markdown(f"<div style='text-align:center;padding-top:9px;color:#91a4bc;font-size:13px'>Page {current_page} of {total_pages}</div>", unsafe_allow_html=True)
        with p3:
            if st.button("Next →", disabled=current_page >= total_pages, use_container_width=True):
                st.session_state.ih_page += 1
                st.rerun()

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        st.download_button("⬇️ Download incident history (JSON)", data=json.dumps(incidents, indent=2), file_name="cybershield_incidents.json", mime="application/json")

    st.caption("Backend incidents are stored in SQLite. Demo entries are fictional and remain in this session only.")

# ── AI Agent Workflow ──────────────────────────────────────────────────────────
elif _page == "AI Agent Workflow":
    st.markdown("## 🤖 AI Agent Workflow")
    st.markdown("<p class='muted'>Run a sanitized incident through the account recovery review workflow. Output is advisory and requires human review.</p>", unsafe_allow_html=True)

    stages = [
        ("01", "Fraud Detection", "Scores transaction indicators", "#65a9ff"),
        ("02", "Phishing Investigation", "Screens message patterns without opening URLs", "#53e0d0"),
        ("03", "Account Protection", "Combines evidence and prepares a prioritized response", "#ffc66d"),
        ("04", "Human Reviewer", "Reviews evidence and decides next action", "#ff899b"),
    ]
    cols = st.columns(4)
    for col, (num, title, desc, color) in zip(cols, stages):
        with col:
            st.markdown(f"<div class='panel' style='min-height:180px;text-align:center'><div style='font-size:28px;font-weight:700;color:{color};font-family:Space Grotesk'>{num}</div><div class='panel-title' style='margin-top:10px'>{title}</div><p class='small' style='margin-top:6px'>{desc}</p></div>", unsafe_allow_html=True)

    st.markdown("### Handoff Logic")
    st.code("Incident reported\n    ├── Transaction signal  → Fraud Detection Agent\n    ├── Message signal     → Phishing Investigation Agent\n    └── Evidence summary   → Account Protection Agent\n                               └── Human review & decision", language="text")

    if not incidents:
        st.info("Run an analysis or load the synthetic demo incidents to try the workflow.")
    else:
        st.markdown("### Run Account Recovery Review")
        selected_incident = st.selectbox(
            "Select incident to review",
            incidents,
            format_func=lambda i: f"{i['id']} • {i['severity']} • Score {i['score']}/100 • {i['type']}",
        )
        st.caption("Only the incident ID, type, severity, score, and redacted summary are sent for review.")

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            run_clicked = st.button("▶ Run Account Recovery Review", type="primary", use_container_width=True)
        with btn_col2:
            share_clicked = st.button("📤 Share Data via Email", use_container_width=True, help="Email incident data to the security team")

        if run_clicked:
            with st.spinner("Running account recovery review…"):
                request_payload = {
                    "incident_id": selected_incident["id"],
                    "incident_type": selected_incident["type"],
                    "severity": selected_incident["severity"],
                    "risk_score": selected_incident["score"],
                    "summary": selected_incident["summary"],
                }
                try:
                    st.session_state.agent_workflow_result = run_agent_workflow_api(request_payload)
                    st.session_state.agent_workflow_result_incident_id = selected_incident["id"]
                except requests.RequestException as exc:
                    st.session_state.agent_workflow_result = None
                    st.session_state.agent_workflow_result_incident_id = None
                    detail = None
                    if isinstance(exc, requests.HTTPError) and exc.response is not None:
                        try:
                            detail = exc.response.json().get("detail")
                        except ValueError:
                            pass
                    st.error(f"Could not run the workflow: {detail or exc}")

        if share_clicked:
            with st.spinner("Sending email…"):
                try:
                    share_result = share_incident_api(selected_incident["id"])
                    st.success("📧 Incident shared with: " + ", ".join(share_result.get("recipients", [])))
                except requests.RequestException as exc:
                    detail = None
                    if isinstance(exc, requests.HTTPError) and exc.response is not None:
                        try:
                            detail = exc.response.json().get("detail")
                        except ValueError:
                            pass
                    st.error(f"Could not share incident: {detail or exc}")

        workflow_result = st.session_state.get("agent_workflow_result")
        if workflow_result and st.session_state.get("agent_workflow_result_incident_id") == selected_incident["id"]:
            st.markdown("### 📋 Incident Review")
            st.markdown("<div class='panel'>", unsafe_allow_html=True)
            st.markdown(workflow_result["analysis"])
            st.markdown("</div>", unsafe_allow_html=True)
            st.caption("⚠️ Human review required • No account actions were taken")

    st.divider()
    st.markdown("**Integration checklist**")
    st.markdown("- Send only synthetic or sanitized incident payloads.\n- Treat the agent response as advisory; keep account actions behind human approval.")

# ── AI Chat ────────────────────────────────────────────────────────────────────
elif _page == "AI Chat":
    st.markdown("## 💬 CyberShield AI Chat")
    st.markdown("<p class='muted'>Ask about transaction risk, phishing signals, incident review, or account protection. Responses are advisory and require human review.</p>", unsafe_allow_html=True)

    top_col1, top_col2 = st.columns([6, 1])
    with top_col2:
        if st.session_state.chat_messages and st.button("🗑 Clear", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()

    if not st.session_state.chat_messages:
        st.caption("Try a question:")
        suggestions = [
            "Is a ₹25,000 transaction from an unusual location risky?",
            "How should I verify an urgent KYC message?",
            "What safe steps protect my account after a phishing report?",
        ]
        s_cols = st.columns(3)
        for col, suggestion in zip(s_cols, suggestions):
            with col:
                if st.button(suggestion, key=f"sug_{suggestion}", use_container_width=True):
                    st.session_state._pending_chat = suggestion
                    st.rerun()

    pending_chat_prompt = st.session_state.pop("_pending_chat", None)
    typed_prompt = st.chat_input("Ask CyberShield AI…")
    if typed_prompt:
        pending_chat_prompt = typed_prompt

    if pending_chat_prompt:
        st.session_state.chat_messages.append({"role": "user", "content": pending_chat_prompt})

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if pending_chat_prompt:
        with st.chat_message("assistant"):
            with st.spinner("Analyzing…"):
                try:
                    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages[:-1][-20:]]
                    response = chat_api(pending_chat_prompt, history)
                    reply = response.get("reply")
                except requests.RequestException as exc:
                    reply = None
                    st.error(f"Could not reach the backend: {exc}")
            if reply:
                st.write(reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})
            else:
                st.error("No response received.")

    st.divider()
    st.caption("🔒 Advisory only. Messages are redacted before reaching the AI. Never enter real passwords, OTPs, PINs, CVVs, or account numbers.")

# ── footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.markdown("<div style='display:flex;justify-content:space-between;flex-wrap:wrap;color:#7188a3;font-size:11px'><span>CYBERSHIELD AI • SECURITY OPERATIONS PROTOTYPE</span><span>Educational use only • Not affiliated with any bank</span></div>", unsafe_allow_html=True)
