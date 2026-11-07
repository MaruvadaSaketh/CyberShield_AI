"""Dark SOC dashboard rendering for CyberShield AI.

Builds the HTML/SVG for the security-operations dashboard. All numbers come
from the caller; nothing here invents metrics.
"""

import math

import streamlit as st

SOC_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{--soc-bg:#05080f;--soc-panel:#080e1a;--soc-panel2:#0b1424;--soc-line:#132239;
--soc-text:#dbe9f7;--soc-muted:#6b8299;--soc-dim:#42586e;--soc-cyan:#2ee6f6;
--soc-blue:#3b9dff;--soc-red:#ff3b5c;--soc-amber:#ffb020;--soc-green:#22c55e;}
.stApp{background:var(--soc-bg);color:var(--soc-text);font-family:'Inter',sans-serif;}
header[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbar"]{display:none;}
#MainMenu,footer{visibility:hidden;}
.block-container{max-width:1620px;padding-top:.4rem;padding-bottom:1.6rem;}
[data-testid="stSidebar"]{background:#060b14;border-right:1px solid var(--soc-line);}
[data-testid="stSidebar"] *{color:#c3d5e8;}
h1,h2,h3,h4{font-family:'Inter',sans-serif!important;letter-spacing:-.02em;color:#eaf3ff;}
.st-key-nav [data-testid="stRadio"]>div{gap:2px;}
.st-key-nav [role="radiogroup"]{gap:2px;flex-wrap:wrap;}
.st-key-nav label{background:transparent!important;border:0!important;border-radius:0!important;
padding:9px 13px!important;border-bottom:2px solid transparent!important;}
.st-key-nav label p{font-size:11px!important;font-weight:600!important;letter-spacing:.11em!important;
text-transform:uppercase;color:#7d93aa!important;}
.st-key-nav label:hover p{color:#cfe3f5!important;}
.st-key-nav label:has(input:checked){border-bottom-color:var(--soc-cyan)!important;}
.st-key-nav label:has(input:checked) p{color:var(--soc-cyan)!important;}
.st-key-nav [data-testid="stWidgetLabel"]{display:none;}
.st-key-nav [data-testid="stRadio"]{margin-bottom:0;}
.st-key-nav [role="radiogroup"] label>div:first-child{display:none!important;}
.st-key-nav [data-testid="stRadioOption"]>div>div:first-child{display:none!important;}
.st-key-nav{background:linear-gradient(180deg,#070d18,#070d18);border:1px solid var(--soc-line);
border-top:0;border-radius:0 0 12px 12px;padding:0 10px;margin-bottom:10px;}
div[data-testid="stVerticalBlock"]{gap:.55rem;}
.stButton>button,.stDownloadButton>button{border-radius:8px;font-weight:600;font-size:12px;
border:1px solid #1d3350;background:#0c1728;color:#cfe3f5;}
.stButton>button:hover{border-color:var(--soc-cyan);color:var(--soc-cyan);}
.stButton>button[kind="primary"]{background:linear-gradient(90deg,#0e8f9e,#1c6fd0);border:0;color:#fff;}
[data-testid="stMetric"]{background:var(--soc-panel);border:1px solid var(--soc-line);
border-radius:10px;padding:12px 14px;}
[data-testid="stMetricLabel"] p{color:var(--soc-muted)!important;font-size:11px!important;
letter-spacing:.08em;text-transform:uppercase;}
[data-testid="stMetricValue"]{color:#eaf3ff;font-family:'JetBrains Mono',monospace;}
[data-testid="stDataFrame"]{border:1px solid var(--soc-line);border-radius:8px;overflow:hidden;}
.stTextArea textarea,.stNumberInput input,.stTextInput input{background:#0a1424!important;
border-color:#1d3350!important;color:#dbe9f7!important;}
[data-testid="stExpander"]{background:var(--soc-panel);border:1px solid var(--soc-line);
border-radius:10px;}
hr{border-color:var(--soc-line);}
.soc-top{display:flex;align-items:center;justify-content:space-between;gap:16px;
background:linear-gradient(180deg,#0a1424,#070d18);border:1px solid var(--soc-line);
border-radius:12px 12px 0 0;padding:12px 18px;border-bottom:0;}
.soc-brand{display:flex;align-items:center;gap:11px;}
.soc-brand-name{font-size:17px;font-weight:700;color:#f2f8ff;letter-spacing:-.01em;line-height:1.15;}
.soc-brand-name span{color:var(--soc-cyan);}
.soc-brand-sub{font-size:9.5px;color:var(--soc-dim);letter-spacing:.14em;text-transform:uppercase;margin-top:2px;}
.soc-clock{text-align:right;font-family:'JetBrains Mono',monospace;}
.soc-time{font-size:13px;color:#cfe3f5;letter-spacing:.04em;}
.soc-date{font-size:10px;color:var(--soc-dim);margin-top:2px;}
.soc-grid{display:grid;grid-template-columns:296px minmax(0,1fr) 296px;gap:12px;align-items:start;margin-top:12px;}
.soc-col{display:flex;flex-direction:column;gap:12px;min-width:0;}
.card{background:linear-gradient(180deg,#0a1220,#070d18);border:1px solid var(--soc-line);
border-radius:10px;padding:13px 14px;position:relative;overflow:hidden;}
.card-h{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:2px;}
.card-t{font-size:10.5px;font-weight:700;letter-spacing:.13em;text-transform:uppercase;color:#9fb6cc;}
.card-s{font-size:9.5px;color:var(--soc-dim);letter-spacing:.04em;margin-bottom:10px;}
.dot-live{width:6px;height:6px;border-radius:50%;background:var(--soc-green);
box-shadow:0 0 8px var(--soc-green);display:inline-block;}
.kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:10px;}
.kpi-i{border-left:1px solid var(--soc-line);padding-left:7px;}
.kpi-i:first-child{border-left:0;padding-left:0;}
.kpi-k{font-size:8.5px;letter-spacing:.09em;text-transform:uppercase;color:var(--soc-dim);}
.kpi-v{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:600;color:#eaf3ff;margin-top:3px;}
.kpi-d{font-size:8.5px;margin-top:2px;font-weight:600;}
.up{color:var(--soc-red);}.down{color:var(--soc-green);}.flat{color:var(--soc-dim);}
.legend{display:flex;flex-direction:column;gap:7px;font-size:10.5px;color:#a9c0d6;}
.legend-row{display:flex;align-items:center;gap:7px;justify-content:space-between;}
.legend-l{display:flex;align-items:center;gap:7px;}
.sw{width:8px;height:8px;border-radius:2px;display:inline-block;}
.legend-v{font-family:'JetBrains Mono',monospace;color:#dbe9f7;font-size:11px;}
.feed{display:flex;flex-direction:column;gap:9px;}
.feed-i{display:grid;grid-template-columns:52px 1fr;gap:8px;align-items:start;
padding-bottom:8px;border-bottom:1px solid #0d1828;}
.feed-i:last-child{border-bottom:0;padding-bottom:0;}
.sev{font-size:8px;font-weight:700;letter-spacing:.06em;text-align:center;padding:3px 0;
border-radius:4px;text-transform:uppercase;}
.sev-high{background:rgba(255,59,92,.14);color:#ff7b93;border:1px solid rgba(255,59,92,.35);}
.sev-medium{background:rgba(255,176,32,.13);color:#ffc45c;border:1px solid rgba(255,176,32,.32);}
.sev-low{background:rgba(34,197,94,.12);color:#5ee08c;border:1px solid rgba(34,197,94,.3);}
.feed-t{font-size:11px;color:#dbe9f7;line-height:1.3;}
.feed-m{font-size:9.5px;color:var(--soc-dim);margin-top:3px;font-family:'JetBrains Mono',monospace;}
.map-wrap{position:relative;border-radius:8px;overflow:hidden;
background:radial-gradient(ellipse at 50% 55%,#0a1c30 0%,#060c16 70%);}
.map-overlay{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
pointer-events:none;}
.shield-badge{text-align:center;}
.shield-ring{width:150px;height:150px;border-radius:50%;display:flex;align-items:center;
justify-content:center;margin:0 auto;
background:radial-gradient(circle,rgba(46,230,246,.14) 0%,rgba(46,230,246,.02) 62%,transparent 70%);
border:1px solid rgba(46,230,246,.28);box-shadow:0 0 42px rgba(46,230,246,.18) inset,0 0 30px rgba(46,230,246,.12);}
.protected{margin-top:10px;display:inline-block;border:1px solid rgba(34,197,94,.45);
background:rgba(34,197,94,.08);border-radius:6px;padding:6px 14px;}
.protected b{display:block;font-size:11px;letter-spacing:.16em;color:#5ee08c;font-weight:700;}
.protected span{display:block;font-size:8px;letter-spacing:.12em;color:#3f8f63;margin-top:2px;}
.triple{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
.mini-v{font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:600;color:#eaf3ff;margin-top:6px;}
.mini-k{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--soc-dim);margin-top:2px;}
.mini-r{font-size:9.5px;color:#ff7b93;margin-top:4px;font-family:'JetBrains Mono',monospace;}
.engine{display:flex;gap:12px;align-items:center;}
.engine-list{flex:1;display:flex;flex-direction:column;gap:8px;min-width:0;}
.engine-i{display:flex;align-items:center;gap:7px;font-size:9.5px;color:#a9c0d6;
line-height:1.25;}
.engine-i svg{flex:0 0 auto;}
.engine-i span{white-space:normal;overflow-wrap:anywhere;}
.scan{color:var(--soc-dim);font-family:'JetBrains Mono',monospace;font-size:8px;
margin-left:auto;text-align:right;flex:0 0 78px;}
.bar-row{margin-bottom:9px;}
.bar-top{display:flex;justify-content:space-between;font-size:10px;color:#a9c0d6;margin-bottom:4px;}
.bar-top b{font-family:'JetBrains Mono',monospace;color:#dbe9f7;font-weight:500;}
.bar-track{height:5px;border-radius:3px;background:#0e1a2b;overflow:hidden;}
.bar-fill{height:100%;border-radius:3px;}
.rings{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;text-align:center;}
.ring-l{font-size:8px;letter-spacing:.05em;color:#8fa8bf;margin-top:5px;line-height:1.25;}
.ring-s{font-size:7.5px;color:var(--soc-dim);letter-spacing:.06em;text-transform:uppercase;}
.q-head,.q-row{display:grid;grid-template-columns:104px 1fr 52px 1fr 30px;gap:8px;
align-items:center;}
.q-head{font-size:8px;letter-spacing:.09em;text-transform:uppercase;color:#42586e;
padding-bottom:6px;border-bottom:1px solid #0d1828;margin-bottom:6px;}
.q-row{padding:5px 0;border-bottom:1px solid #0b1524;font-size:10px;color:#c3d5e8;}
.q-row:last-child{border-bottom:0;}
.q-id{font-family:'JetBrains Mono',monospace;font-size:9px;color:#7d93aa;
white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.q-type{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:#a9c0d6;}
.q-bar{height:4px;border-radius:2px;background:#0e1a2b;overflow:hidden;display:block;}
.q-bar>span{display:block;height:100%;border-radius:2px;}
.q-score{font-family:'JetBrains Mono',monospace;font-size:10px;text-align:right;}
.soc-foot{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:#3f5468;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;margin-top:14px;
border-top:1px solid var(--soc-line);padding-top:10px;}
@media(max-width:1250px){.soc-grid{grid-template-columns:1fr;}}
"""


def _pts(points, w, h):
    out = []
    for lon, lat in points:
        x = (lon + 180.0) / 360.0 * w
        y = (90.0 - lat) / 180.0 * h
        out.append((x, y))
    return out


_CONTINENTS = [
    [(-168, 65), (-160, 71), (-140, 70), (-125, 70), (-110, 68), (-95, 70), (-80, 73),
     (-62, 60), (-55, 50), (-65, 45), (-70, 42), (-75, 35), (-81, 25), (-97, 26),
     (-105, 20), (-115, 30), (-125, 40), (-125, 48), (-135, 58), (-150, 60)],
    [(-105, 20), (-97, 26), (-88, 21), (-83, 15), (-77, 8), (-83, 8), (-92, 14)],
    [(-77, 8), (-70, 12), (-60, 10), (-50, 0), (-35, -5), (-38, -15), (-48, -25),
     (-58, -35), (-62, -40), (-65, -50), (-70, -55), (-75, -45), (-72, -30),
     (-70, -18), (-78, -5), (-80, 0)],
    [(-45, 60), (-20, 70), (-20, 82), (-45, 83), (-58, 78), (-55, 68)],
    [(-10, 36), (0, 44), (3, 43), (12, 38), (20, 40), (28, 41), (30, 45), (40, 48),
     (30, 60), (25, 65), (15, 68), (5, 58), (-5, 48)],
    [(-17, 15), (-16, 22), (-5, 32), (10, 37), (25, 32), (35, 30), (43, 12), (51, 12),
     (42, -2), (40, -15), (35, -25), (25, -34), (18, -34), (12, -18), (9, -1),
     (5, 5), (-8, 5)],
    [(30, 45), (40, 48), (60, 45), (75, 42), (90, 45), (105, 45), (120, 45), (130, 42),
     (140, 45), (145, 55), (160, 60), (180, 65), (180, 72), (140, 73), (100, 78),
     (70, 72), (60, 68), (40, 68), (30, 60)],
    [(68, 24), (72, 20), (78, 8), (80, 13), (88, 22), (92, 22), (88, 26), (78, 30), (70, 28)],
    [(95, 20), (105, 10), (110, 0), (120, -5), (130, -5), (140, -8), (135, -2),
     (120, 5), (105, 20)],
    [(113, -22), (115, -33), (130, -32), (140, -38), (150, -37), (153, -28),
     (145, -15), (135, -12), (125, -14)],
    [(130, 32), (140, 36), (145, 44), (142, 45), (135, 35)],
    [(-6, 50), (-2, 58), (0, 54), (-5, 50)],
    [(43, -12), (50, -15), (47, -25), (43, -20)],
    [(166, -46), (174, -41), (178, -38), (173, -35), (168, -44)],
]

_HOTSPOTS = [
    (-74.0, 40.7), (-118.2, 34.0), (-46.6, -23.5), (-0.1, 51.5), (13.4, 52.5),
    (37.6, 55.7), (77.2, 28.6), (116.4, 39.9), (139.7, 35.7), (151.2, -33.9),
    (28.0, -26.2), (55.3, 25.3), (-99.1, 19.4), (103.8, 1.35),
]


def _inside(x, y, poly):
    hit = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            if x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
                hit = not hit
    return hit


@st.cache_data(show_spinner=False)
def world_map_svg(width=760, height=360, cols=118, rows=56):
    """Dotted world map built by rasterising coarse continent outlines."""
    polys = [_pts(p, width, height) for p in _CONTINENTS]
    dots = []
    for r in range(rows):
        y = (r + 0.5) * height / rows
        for c in range(cols):
            x = (c + 0.5) * width / cols
            if any(_inside(x, y, poly) for poly in polys):
                dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.15"/>')
    nodes = []
    for lon, lat in _HOTSPOTS:
        x, y = _pts([(lon, lat)], width, height)[0]
        nodes.append(
            f'<g><circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="rgba(255,59,92,.10)"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="rgba(255,59,92,.28)"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.9" fill="#ff5c78"/></g>'
        )
    arcs = []
    for i in range(0, len(_HOTSPOTS) - 1, 2):
        x1, y1 = _pts([_HOTSPOTS[i]], width, height)[0]
        x2, y2 = _pts([_HOTSPOTS[i + 1]], width, height)[0]
        mx, my = (x1 + x2) / 2, min(y1, y2) - abs(x2 - x1) * 0.22 - 14
        arcs.append(
            f'<path d="M{x1:.1f},{y1:.1f} Q{mx:.1f},{my:.1f} {x2:.1f},{y2:.1f}" '
            f'fill="none" stroke="rgba(255,59,92,.30)" stroke-width=".9" '
            f'stroke-dasharray="3 5"/>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" aria-label="Illustrative global threat map">'
        f'<g fill="#2a5f8f" opacity=".9">{"".join(dots)}</g>'
        f'<g>{"".join(arcs)}</g>{"".join(nodes)}</svg>'
    )


def sparkline_svg(values, color="#ff3b5c", width=260, height=52, fill=True, uid="sp"):
    """Area/line sparkline from a numeric series."""
    vals = [float(v) for v in values] or [0.0]
    if len(vals) == 1:
        vals = vals * 2
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    step = width / (len(vals) - 1)
    pts = [
        (i * step, height - 4 - (v - lo) / span * (height - 10))
        for i, v in enumerate(vals)
    ]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = f"0,{height} {line} {width},{height}"
    grad = (
        f'<defs><linearGradient id="{uid}" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{color}" stop-opacity=".38"/>'
        f'<stop offset="100%" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
    )
    body = f'<polygon points="{area}" fill="url(#{uid})"/>' if fill else ""
    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none" aria-hidden="true">{grad}{body}'
        f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.6" '
        f'stroke-linejoin="round"/></svg>'
    )


def donut_svg(segments, center_value, center_label, size=118, thickness=13):
    """Donut chart. segments = [(label, value, color), ...]."""
    total = sum(v for _, v, _ in segments) or 1
    radius = (size - thickness) / 2
    circumference = 2 * math.pi * radius
    offset = 0.0
    arcs = []
    for _, value, color in segments:
        length = circumference * (value / total)
        arcs.append(
            f'<circle cx="{size/2}" cy="{size/2}" r="{radius}" fill="none" '
            f'stroke="{color}" stroke-width="{thickness}" '
            f'stroke-dasharray="{max(length - 2.5, 0):.2f} {circumference:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" stroke-linecap="butt"/>'
        )
        offset += length
    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        f'role="img" aria-label="Active threats by severity">'
        f'<circle cx="{size/2}" cy="{size/2}" r="{radius}" fill="none" '
        f'stroke="#0e1a2b" stroke-width="{thickness}"/>'
        f'<g transform="rotate(-90 {size/2} {size/2})">{"".join(arcs)}</g>'
        f'<text x="{size/2}" y="{size/2 - 2}" text-anchor="middle" fill="#eaf3ff" '
        f'font-family="JetBrains Mono,monospace" font-size="19" font-weight="600">'
        f'{center_value}</text>'
        f'<text x="{size/2}" y="{size/2 + 13}" text-anchor="middle" fill="#42586e" '
        f'font-family="Inter,sans-serif" font-size="7.5" letter-spacing="1.2">'
        f'{center_label}</text></svg>'
    )


def shield_svg(size=62):
    return (
        f'<svg viewBox="0 0 64 64" width="{size}" height="{size}" aria-hidden="true">'
        f'<defs><linearGradient id="shg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="#7df3ff"/><stop offset="100%" stop-color="#1f9fd8"/>'
        f'</linearGradient></defs>'
        f'<path d="M32 4 L56 13 V31 C56 45 45 55 32 60 C19 55 8 45 8 31 V13 Z" '
        f'fill="rgba(46,230,246,.10)" stroke="url(#shg)" stroke-width="2"/>'
        f'<rect x="23" y="29" width="18" height="14" rx="3" fill="none" '
        f'stroke="#7df3ff" stroke-width="2"/>'
        f'<path d="M27 29 v-4 a5 5 0 0 1 10 0 v4" fill="none" stroke="#7df3ff" '
        f'stroke-width="2" stroke-linecap="round"/></svg>'
    )


def brain_svg(size=104):
    return (
        f'<svg viewBox="0 0 120 120" width="{size}" height="{size}" aria-hidden="true">'
        f'<defs><radialGradient id="brg"><stop offset="0%" stop-color="rgba(59,157,255,.22)"/>'
        f'<stop offset="100%" stop-color="rgba(59,157,255,0)"/></radialGradient></defs>'
        f'<circle cx="60" cy="60" r="56" fill="url(#brg)"/>'
        f'<path d="M60 26 C48 20 34 24 32 38 C22 42 22 56 30 62 C24 72 32 84 44 84 '
        f'C48 92 60 92 60 84" fill="none" stroke="#3b9dff" stroke-width="1.6" opacity=".9"/>'
        f'<path d="M60 26 C72 20 86 24 88 38 C98 42 98 56 90 62 C96 72 88 84 76 84 '
        f'C72 92 60 92 60 84" fill="none" stroke="#3b9dff" stroke-width="1.6" opacity=".9"/>'
        f'<path d="M60 26 V84" stroke="#2ee6f6" stroke-width="1.1" opacity=".55"/>'
        f'<path d="M38 44 C46 48 46 56 40 60 M82 44 C74 48 74 56 80 60 '
        f'M42 70 C50 66 52 74 48 78 M78 70 C70 66 68 74 72 78" fill="none" '
        f'stroke="#2ee6f6" stroke-width="1.1" opacity=".55"/>'
        f'<circle cx="60" cy="26" r="2.4" fill="#7df3ff"/>'
        f'<circle cx="60" cy="84" r="2.4" fill="#7df3ff"/></svg>'
    )


def ring_svg(pct, color, size=44, label="", sub=""):
    radius = (size - 6) / 2
    circ = 2 * math.pi * radius
    dash = circ * max(0.0, min(pct, 100)) / 100.0
    return (
        f'<div><svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        f'role="img" aria-label="{label} {pct:.0f} percent">'
        f'<circle cx="{size/2}" cy="{size/2}" r="{radius}" fill="none" stroke="#0e1a2b" '
        f'stroke-width="3.5"/>'
        f'<circle cx="{size/2}" cy="{size/2}" r="{radius}" fill="none" stroke="{color}" '
        f'stroke-width="3.5" stroke-linecap="round" '
        f'stroke-dasharray="{dash:.2f} {circ:.2f}" '
        f'transform="rotate(-90 {size/2} {size/2})"/>'
        f'<text x="{size/2}" y="{size/2 + 3.5}" text-anchor="middle" fill="#dbe9f7" '
        f'font-family="JetBrains Mono,monospace" font-size="9">{pct:.0f}</text></svg>'
        f'<div class="ring-l">{label}</div><div class="ring-s">{sub}</div></div>'
    )


_SEV_COLOR = {"HIGH": "#ff3b5c", "MEDIUM": "#ffb020", "LOW": "#22c55e"}
_SEV_CLASS = {"HIGH": "sev-high", "MEDIUM": "sev-medium", "LOW": "sev-low"}


def _fmt_time(value):
    text = str(value or "")
    if "T" in text:
        return text.split("T")[1][:8]
    return text[-8:] if len(text) >= 8 else (text or "--:--:--")


def _hourly_series(incidents, buckets=12):
    """Incident counts per bucket across the recorded time span."""
    from datetime import datetime, timezone

    stamps = []
    for item in incidents:
        raw = str(item.get("created_at") or "")
        try:
            stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        stamps.append(stamp)
    if not stamps:
        return [0] * buckets
    if len(stamps) == 1:
        return [0] * (buckets - 1) + [1]
    start, end = min(stamps), max(stamps)
    span = (end - start).total_seconds()
    width = max(span / buckets, 1.0)
    counts = [0] * buckets
    for stamp in stamps:
        idx = int((stamp - start).total_seconds() / width)
        counts[min(max(idx, 0), buckets - 1)] += 1
    return counts


def _delta(series):
    if not series:
        return 0.0
    half = max(len(series) // 2, 1)
    first, second = sum(series[:half]), sum(series[half:])
    if first == 0:
        return 100.0 if second else 0.0
    return (second - first) / first * 100.0


def _delta_html(pct):
    if abs(pct) < 0.05:
        return '<div class="kpi-d flat">0.0%</div>'
    cls = "up" if pct > 0 else "down"
    arrow = "&#9650;" if pct > 0 else "&#9660;"
    return f'<div class="kpi-d {cls}">{arrow} {abs(pct):.1f}%</div>'


def _left_column(incidents, total, high, medium, low, series):
    feed = []
    for item in incidents[:6]:
        sev = str(item.get("severity") or "LOW").upper()
        feed.append(
            f'<div class="feed-i"><div class="sev {_SEV_CLASS.get(sev, "sev-low")}">{sev}</div>'
            f'<div><div class="feed-t">{item.get("summary") or item.get("type") or "Security event"}</div>'
            f'<div class="feed-m">{_fmt_time(item.get("created_at"))} &middot; '
            f'{item.get("id") or "n/a"}</div></div></div>'
        )
    if not feed:
        feed.append('<div class="feed-m">No incidents recorded yet.</div>')

    donut = donut_svg(
        [("Critical", high, "#ff3b5c"), ("Medium", medium, "#ffb020"), ("Low", low, "#22c55e")],
        total,
        "TOTAL",
    )
    legend = "".join(
        f'<div class="legend-row"><div class="legend-l"><span class="sw" style="background:{c}"></span>'
        f'{label}</div><span class="legend-v">{value}</span></div>'
        for label, value, c in (
            ("High", high, "#ff3b5c"),
            ("Medium", medium, "#ffb020"),
            ("Low", low, "#22c55e"),
        )
    )
    return f"""
<div class="soc-col">
  <section class="card">
    <div class="card-h"><div class="card-t">Threat Overview</div><span class="dot-live"></span></div>
    <div class="card-s">Real-time summary</div>
    {sparkline_svg(series, "#ff3b5c", 268, 54, uid="ov")}
    <div class="kpi-row">
      <div class="kpi-i"><div class="kpi-k">Total</div><div class="kpi-v">{total}</div>{_delta_html(_delta(series))}</div>
      <div class="kpi-i"><div class="kpi-k">High</div><div class="kpi-v">{high}</div><div class="kpi-d up">&#9650; {high}</div></div>
      <div class="kpi-i"><div class="kpi-k">Medium</div><div class="kpi-v">{medium}</div><div class="kpi-d up">&#9650; {medium}</div></div>
      <div class="kpi-i"><div class="kpi-k">Low</div><div class="kpi-v">{low}</div><div class="kpi-d down">&#9660; {low}</div></div>
    </div>
  </section>
  <section class="card">
    <div class="card-h"><div class="card-t">Active Threats</div><span class="dot-live"></span></div>
    <div class="card-s">By severity</div>
    <div style="display:flex;gap:14px;align-items:center">
      {donut}<div class="legend" style="flex:1">{legend}</div>
    </div>
  </section>
  <section class="card">
    <div class="card-h"><div class="card-t">Threat Activity Feed</div><span class="dot-live"></span></div>
    <div class="card-s">Live updates</div>
    <div class="feed">{"".join(feed)}</div>
  </section>
</div>"""


def _center_column(incidents, backend_online, discord_status, series):
    txn = sum(1 for i in incidents if "transaction" in str(i.get("type") or i.get("event_type") or "").lower())
    phish = sum(1 for i in incidents if "phish" in str(i.get("type") or i.get("event_type") or "").lower())
    high = sum(1 for i in incidents if str(i.get("severity")).upper() == "HIGH")
    txn_high = sum(
        1 for i in incidents
        if "transaction" in str(i.get("type") or i.get("event_type") or "").lower()
        and str(i.get("severity")).upper() == "HIGH"
    )
    phish_high = sum(
        1 for i in incidents
        if "phish" in str(i.get("type") or i.get("event_type") or "").lower()
        and str(i.get("severity")).upper() == "HIGH"
    )
    if discord_status.get("valid") and discord_status.get("channel_accessible"):
        alert_value, alert_note, alert_color = "Live", "Discord channel reachable", "#22c55e"
    elif discord_status.get("configured"):
        alert_value, alert_note, alert_color = "Degraded", "Discord rejected the token", "#ff3b5c"
    else:
        alert_value, alert_note, alert_color = "Off", "Discord not configured", "#ffb020"

    status_text = "SYSTEM PROTECTED" if backend_online else "BACKEND OFFLINE"
    status_sub = "AI THREAT DETECTION ACTIVE" if backend_online else "START THE FASTAPI SERVER"
    status_color = "#5ee08c" if backend_online else "#ff7b93"
    status_border = "rgba(34,197,94,.45)" if backend_online else "rgba(255,59,92,.45)"
    status_bg = "rgba(34,197,94,.08)" if backend_online else "rgba(255,59,92,.08)"

    queue_rows = []
    for item in incidents[:5]:
        sev = str(item.get("severity") or "LOW").upper()
        color = _SEV_COLOR.get(sev, "#22c55e")
        score = item.get("score") or 0
        try:
            score = int(float(score))
        except (TypeError, ValueError):
            score = 0
        queue_rows.append(
            f'<div class="q-row"><span class="q-id">{item.get("id") or "n/a"}</span>'
            f'<span class="q-type">{str(item.get("type") or "Security event")[:26]}</span>'
            f'<span class="sev {_SEV_CLASS.get(sev, "sev-low")}" style="width:52px">{sev}</span>'
            f'<span class="q-bar"><span style="width:{max(0, min(score, 100))}%;'
            f'background:{color}"></span></span>'
            f'<span class="q-score" style="color:{color}">{score}</span></div>'
        )
    if not queue_rows:
        queue_rows.append('<div class="feed-m">No incidents queued yet.</div>')

    return f"""
<div class="soc-col">
  <section class="card" style="padding:13px 14px 10px">
    <div class="card-h"><div class="card-t">Global Threat Map</div>
      <span style="font-size:9px;color:#42586e;letter-spacing:.1em">ILLUSTRATIVE</span></div>
    <div class="card-s">Real-time attack visualisation</div>
    <div class="map-wrap">
      {world_map_svg(760, 372)}
      <div class="map-overlay"><div class="shield-badge">
        <div class="shield-ring">{shield_svg(64)}</div>
        <div class="protected" style="border-color:{status_border};background:{status_bg}">
          <b style="color:{status_color}">{status_text}</b><span>{status_sub}</span>
        </div>
      </div></div>
    </div>
  </section>
  <div class="triple">
    <section class="card">
      <div class="card-h"><div class="card-t">Transaction Signals</div><span class="dot-live"></span></div>
      <div class="mini-v">{txn}</div><div class="mini-k">Incidents scored</div>
      <div class="mini-r">High risk {txn_high}</div>
      {sparkline_svg(series, "#3b9dff", 240, 30, uid="tx")}
    </section>
    <section class="card">
      <div class="card-h"><div class="card-t">Phishing Signals</div><span class="dot-live"></span></div>
      <div class="mini-v">{phish}</div><div class="mini-k">Messages screened</div>
      <div class="mini-r">High risk {phish_high}</div>
      {sparkline_svg(series, "#2ee6f6", 240, 30, uid="ph")}
    </section>
    <section class="card">
      <div class="card-h"><div class="card-t">Alert Delivery</div><span class="dot-live"></span></div>
      <div class="mini-v" style="color:{alert_color}">{alert_value}</div>
      <div class="mini-k">Discord channel</div>
      <div class="mini-r" style="color:{alert_color}">{alert_note}</div>
      {sparkline_svg(series, alert_color, 240, 30, uid="al")}
    </section>
  </div>
  <section class="card">
    <div class="card-h"><div class="card-t">Incident Queue</div>
      <span style="font-size:9px;color:#42586e;letter-spacing:.1em">LATEST 5</span></div>
    <div class="card-s">Risk score per incident</div>
    <div class="q-head"><span>Incident</span><span>Signal</span><span>Severity</span>
      <span>Risk score</span><span></span></div>
    {"".join(queue_rows)}
  </section>
</div>"""


def _right_column(incidents, backend_online):
    detectors = [
        ("Behavior Analysis", "Amount vs baseline"),
        ("Anomaly Detection", "Time and location"),
        ("Rule Classification", "Weighted evidence"),
        ("Threat Correlation", "Phishing + transaction"),
    ]
    rows = "".join(
        f'<div class="engine-i"><svg width="11" height="11" viewBox="0 0 12 12" aria-hidden="true">'
        f'<circle cx="6" cy="6" r="5" fill="none" stroke="#2ee6f6" stroke-width="1" opacity=".7"/>'
        f'<circle cx="6" cy="6" r="1.8" fill="#2ee6f6"/></svg>'
        f'<span>{name}<br><span class="scan" style="flex:none;margin:0">{note}</span></span></div>'
        for name, note in detectors
    )
    progress = 100 if backend_online else 0

    counts = {}
    for item in incidents:
        flags = item.get("evidence") or (item.get("details") or {}).get("evidence") or []
        for flag in flags:
            key = str(flag).rstrip(".")
            counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    peak = top[0][1] if top else 1
    palette = ["#ff3b5c", "#ff7a4d", "#ffb020", "#3b9dff", "#22c55e"]
    if top:
        bars = "".join(
            f'<div class="bar-row"><div class="bar-top"><span>{label[:46]}</span>'
            f'<b>{value}</b></div><div class="bar-track">'
            f'<div class="bar-fill" style="width:{value / peak * 100:.1f}%;'
            f'background:{palette[i % len(palette)]}"></div></div></div>'
            for i, (label, value) in enumerate(top)
        )
    else:
        bars = '<div class="feed-m">No evidence indicators recorded yet.</div>'

    rings = "".join(
        ring_svg(pct, color, 44, label, sub)
        for pct, color, label, sub in (
            (100, "#22c55e", "Human review", "enforced"),
            (100, "#2ee6f6", "Redaction", "active"),
            (0, "#ffb020", "Bank link", "none"),
            (100 if backend_online else 0, "#3b9dff", "API", "online" if backend_online else "down"),
        )
    )
    return f"""
<div class="soc-col">
  <section class="card">
    <div class="card-h"><div class="card-t">Threat Detection Engine</div><span class="dot-live"></span></div>
    <div class="card-s">Rule-based analysis</div>
    <div class="engine">{brain_svg(96)}<div class="engine-list">{rows}</div></div>
    <div style="display:flex;justify-content:space-between;font-size:9px;color:#42586e;
      letter-spacing:.1em;margin-top:10px"><span>PROCESSING</span><span>{progress}%</span></div>
    <div class="bar-track" style="margin-top:5px"><div class="bar-fill"
      style="width:{progress}%;background:linear-gradient(90deg,#2ee6f6,#3b9dff)"></div></div>
  </section>
  <section class="card">
    <div class="card-h"><div class="card-t">Top Signal Types</div></div>
    <div class="card-s">By evidence frequency</div>
    {bars}
  </section>
  <section class="card">
    <div class="card-h"><div class="card-t">Control Status</div></div>
    <div class="card-s">Guardrails in this prototype</div>
    <div class="rings">{rings}</div>
  </section>
</div>"""


def top_bar(backend_online, now=None):
    from datetime import datetime

    stamp = now or datetime.now()
    return f"""
<div class="soc-top">
  <div class="soc-brand">
    {shield_svg(30)}
    <div>
      <div class="soc-brand-name">CyberShield <span>AI</span></div>
      <div class="soc-brand-sub">Real-time Threat Intelligence</div>
    </div>
  </div>
  <div class="soc-clock">
    <div class="soc-time">{stamp.strftime("%H:%M:%S")} UTC</div>
    <div class="soc-date">{stamp.strftime("%b %d, %Y")} &middot;
      {"API ONLINE" if backend_online else "API OFFLINE"}</div>
  </div>
</div>"""


def render_dashboard(incidents, backend_online, discord_status):
    """Assemble the full SOC dashboard HTML from real incident data."""
    total = len(incidents)
    high = sum(1 for i in incidents if str(i.get("severity")).upper() == "HIGH")
    medium = sum(1 for i in incidents if str(i.get("severity")).upper() == "MEDIUM")
    low = sum(1 for i in incidents if str(i.get("severity")).upper() == "LOW")
    series = _hourly_series(incidents)
    return (
        '<div class="soc-grid">'
        + _left_column(incidents, total, high, medium, low, series)
        + _center_column(incidents, backend_online, discord_status, series)
        + _right_column(incidents, backend_online)
        + "</div>"
        + '<div class="soc-foot"><span>CyberShield AI &middot; Security Operations Prototype</span>'
        + "<span>Educational use only &middot; Not affiliated with any bank</span></div>"
    )
