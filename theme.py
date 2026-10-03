import streamlit as st
import pandas as pd

PARTY_COLOURS = {
    'Labour': '#e4003b',
    'Conservative': '#3b9be0',
    'Liberal Democrats': '#faa61a',
    'Reform UK': '#12B6CF',
    'Green Party': '#6AB023',
    'SNP': '#FDF38E',
    'Plaid Cymru': '#005B54',
    'Others': '#777777',
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,700;6..72,800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --bench: #07100c;      
  --leather: #10261c;    
  --leather-2: #163628;  
  --brass: #d4af37;      
  --paper: #f4f0e6;      
  --muted: #a3b8ad;
  --alarm: #e65c4f;
}

/* Global Background & Typography */
html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: var(--bench); color: var(--paper); }
.block-container { max-width: 1350px; padding-top: 2rem; padding-bottom: 3rem; }
header[data-testid="stHeader"] { background: transparent; }

/* Custom Scrollbar */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--bench); }
::-webkit-scrollbar-thumb { background: var(--leather-2); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--brass); }

/* Elegant Headers */
h1, h2, h3, h4 { 
    font-family: 'Newsreader', serif !important; 
    color: var(--paper); 
    letter-spacing: -0.01em; 
}
h2, h3 { border-bottom: 1px solid #1f3b2d; padding-bottom: 8px; margin-bottom: 16px; margin-top: 10px; }

/* Sidebar */
[data-testid="stSidebar"] { background: #0a1410 !important; border-right: 1px solid #1f3b2d; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: var(--brass) !important; border-bottom: none; }

/* Base text forces */
.stApp, .stApp p, .stApp li, .stApp label, [data-testid="stMarkdownContainer"] p, 
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, 
[data-testid="stRadio"] label p { color: var(--paper) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }

/* Tabs */
[data-testid="stTabs"] button {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--muted) !important;
    border-bottom-color: #1f3b2d !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--brass) !important;
    border-bottom-color: var(--brass) !important;
}

/* Radio Buttons (Policy Choices) */
[data-testid="stRadio"] label, [data-testid="stRadio"] label[data-baseweb="radio"] {
  background: linear-gradient(145deg, var(--leather), #0b1a13) !important;
  border: 1px solid #1f3b2d;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 12px;
  width: 100%;
  box-shadow: 0 4px 6px rgba(0,0,0,0.2);
  transition: all 0.2s ease;
}
[data-testid="stRadio"] label:hover { 
  border-color: var(--brass); 
  background: linear-gradient(145deg, var(--leather-2), var(--leather)) !important;
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0,0,0,0.4);
}
[data-testid="stRadio"] label:has(input:checked) {
  border-color: var(--brass); 
  background: linear-gradient(145deg, var(--leather-2), var(--leather)) !important; 
  box-shadow: inset 4px 0 0 var(--brass), 0 4px 8px rgba(0,0,0,0.4);
}

/* Buttons */
div.stButton > button {
  border-radius: 6px; font-weight: 600; padding: 0.6rem 1.5rem;
  background: linear-gradient(145deg, var(--leather), #0b1a13); 
  color: var(--paper); border: 1px solid var(--brass);
  box-shadow: 0 2px 4px rgba(0,0,0,0.3);
  transition: all 0.2s ease;
}
div.stButton > button:hover { 
  background: var(--brass); color: var(--bench); 
  border-color: var(--brass); 
  transform: translateY(-2px);
  box-shadow: 0 4px 10px rgba(212,175,55,0.3);
}
div.stButton > button[kind="primary"] { 
  background: var(--brass); color: var(--bench); 
}

/* Tooltips */
[data-testid="stTooltipContent"], [data-testid="stTooltipContent"] *,
div[data-baseweb="tooltip"], div[data-baseweb="tooltip"] * {
  background-color: #0b1712 !important;
  color: #efe9da !important;
}
div[data-baseweb="tooltip"] { border: 1px solid var(--brass) !important; border-radius: 6px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.8) !important; }

/* Custom Stat Cards */
.sc-card { 
  position: relative; 
  background: linear-gradient(145deg, var(--leather), #0b1a13); 
  border: 1px solid #1f3b2d; 
  border-top: 3px solid var(--brass);
  border-radius: 8px; 
  padding: 14px 16px; 
  margin-bottom: 16px; 
  min-height: 110px; 
  box-shadow: 0 6px 10px rgba(0,0,0,0.25);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.sc-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 15px rgba(0,0,0,0.4);
  border-color: #3b6b52;
}
.sc-label { display: flex; align-items: center; justify-content: space-between; color: var(--muted); font-size: .88rem; font-weight: 600; line-height: 1.2; text-transform: uppercase; letter-spacing: 0.5px; }
.sc-info { display: inline-flex; align-items: center; justify-content: center; width: 18px; height: 18px; flex: none; border: 1px solid var(--muted); border-radius: 50%; font-size: .75rem; font-style: normal; cursor: help; color: var(--muted); transition: all 0.2s ease; }
.sc-card:hover .sc-info, .sc-card:focus-within .sc-info { border-color: var(--brass); color: var(--brass); background: rgba(212,175,55,0.1); }
.sc-value { font-family: 'Newsreader', serif; font-size: 2.2rem; font-weight: 700; color: var(--paper); line-height: 1.1; margin: 8px 0 6px; }
.sc-delta { display: inline-block; font-size: .85rem; font-weight: 600; padding: 2px 8px; border-radius: 12px; }
.sc-good { color: #6fbf8a; background: rgba(111,191,138,.15); }
.sc-bad  { color: #e65c4f; background: rgba(230,92,79,.15); }
.sc-flat { color: var(--muted); background: rgba(163,184,173,.15); }
.sc-tip { position: absolute; left: 0; right: 0; top: calc(100% + 8px); z-index: 9999; background: #07100c; color: #f4f0e6; border: 1px solid var(--brass); border-radius: 6px; padding: 12px 14px; font-family: 'IBM Plex Sans', sans-serif; font-size: .9rem; font-weight: 400; line-height: 1.5; box-shadow: 0 8px 20px rgba(0,0,0,.8); opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .2s; }
.sc-card:hover .sc-tip, .sc-card:focus-within .sc-tip { opacity: 1; visibility: visible; }
div[data-testid="stColumn"]:has(.sc-card:hover), div[data-testid="stElementContainer"]:has(.sc-card:hover) { position: relative; z-index: 1000; }

/* Custom Tables */
.ch-table { width: 100%; border-collapse: collapse; margin-top: 10px; margin-bottom: 20px; background: linear-gradient(145deg, var(--leather), #0b1a13); border-radius: 8px; overflow: hidden; box-shadow: 0 6px 12px rgba(0,0,0,0.3); border: 1px solid #1f3b2d; }
.ch-table th { background: #07100c; color: var(--brass); font-family: 'Newsreader', serif; padding: 14px 16px; text-align: left; border-bottom: 2px solid var(--brass); font-size: 1.15rem; font-weight: 700; }
.ch-table td { padding: 12px 16px; border-bottom: 1px solid #1f3b2d; color: var(--paper); font-variant-numeric: tabular-nums; }
.ch-table tr:last-child td { border-bottom: none; }
.ch-table tr:hover td { background: rgba(255,255,255,0.02); }

/* Banner */
.ch-banner { border-left: 6px solid var(--brass); background: linear-gradient(145deg, var(--leather), #0b1a13); padding: 20px 26px; border-radius: 8px; margin-bottom: 24px; box-shadow: 0 6px 12px rgba(0,0,0,0.3); }
.ch-banner h1 { margin: 0; font-size: 2.6rem; letter-spacing: -0.02em; }
.ch-banner .sub { color: var(--muted); margin-top: 6px; font-weight: 500; font-size: 1.1rem; }
.ch-pips { display: flex; gap: 8px; margin-top: 16px; }
.ch-pip { height: 8px; flex: 1; border-radius: 4px; background: #1f3b2d; }
.ch-pip.done { background: var(--brass); }
.ch-pip.now { background: var(--paper); box-shadow: 0 0 8px rgba(244, 240, 230, 0.6); }

/* News & Crises */
.ch-crisis { background: #2a1111; border: 1px solid var(--alarm); border-left: 6px solid var(--alarm); border-radius: 8px; padding: 18px 22px; margin: 8px 0 18px; font-family: 'Newsreader', serif; font-size: 1.4rem; box-shadow: 0 6px 12px rgba(0,0,0,0.4); }
.ch-crisis small { display: block; font-family: 'IBM Plex Sans', sans-serif; font-size: .95rem; color: #e3b3ab; margin-top: 8px; }
.ch-news { background: linear-gradient(145deg, var(--leather), #0b1a13); border-left: 4px solid var(--muted); padding: 14px 20px; border-radius: 6px; color: var(--paper); margin-bottom: 18px; box-shadow: 0 4px 8px rgba(0,0,0,0.25); font-size: 1.05rem; }

/* Polls Bar Chart */
.ch-bar { display: flex; align-items: center; gap: 14px; margin: 10px 0; }
.ch-bar .name { width: 160px; color: var(--paper); font-weight: 600; font-size: 1.05rem; }
.ch-bar .track { flex: 1; background: #07100c; border-radius: 6px; height: 26px; overflow: hidden; border: 1px solid #1f3b2d; box-shadow: inset 0 2px 4px rgba(0,0,0,0.6); }
.ch-bar .fill { height: 100%; border-radius: 5px; background-image: linear-gradient(90deg, rgba(255,255,255,0.15), transparent); transition: width 0.5s ease; }
.ch-bar .val { width: 60px; text-align: right; font-variant-numeric: tabular-nums; font-weight: 700; font-size: 1.05rem; color: var(--brass); }
</style>
"""

def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)

def header(party, term, year, block):
    done = (year - 1) * 3 + (block - 1)
    pips = ''.join(
        f"<div class='ch-pip {'done' if i < done else ('now' if i == done else '')}'></div>"
        for i in range(15)
    )
    colour = PARTY_COLOURS.get(party, '#d4af37')
    st.markdown(
        f"""<div class='ch-banner' style='border-left-color:{colour}'>
        <h1>🏛️ {party} Government</h1>
        <div class='sub'>Chancellor Simulator, Hardcore Mode &nbsp;|&nbsp; Term {term} &nbsp;|&nbsp; Year {min(year, 5)} of 5, block {block} of 3</div>
        <div class='ch-pips'>{pips}</div></div>""",
        unsafe_allow_html=True,
    )

def crisis_card(title):
    st.markdown(f"<div class='ch-crisis'>{title}<small>Emergency intervention required immediately.</small></div>", unsafe_allow_html=True)

def news_box(text):
    st.markdown(f"<div class='ch-news'>{text}</div>", unsafe_allow_html=True)

def render_polls(df):
    latest = df.iloc[-1]
    rows = ''
    for party, val in latest.sort_values(ascending=False).items():
        c = PARTY_COLOURS.get(party, '#888')
        rows += (f"<div class='ch-bar'><div class='name'>{party}</div>"
                 f"<div class='track'><div class='fill' style='width:{min(val * 2.2, 100)}%;background-color:{c}'></div></div>"
                 f"<div class='val'>{val:.0f}%</div></div>")
    st.markdown(rows, unsafe_allow_html=True)

def humphrey_message(text):
    st.markdown(f"""
    <div style='background: linear-gradient(145deg, #162a20, #0b1712); border-left: 5px solid #d4af37; padding: 20px; margin: 15px 0px 25px 0px; border-radius: 8px; box-shadow: 0 6px 12px rgba(0,0,0,0.3);'>
        <div style='color: #d4af37; font-family: "Newsreader", serif; font-weight: 800; font-size: 1.3rem; margin-bottom: 10px; display: flex; align-items: center;'>
            <span style='font-size: 1.6rem; margin-right: 10px;'>💼</span> Memo from Sir Humphrey Appleby
        </div>
        <div style='font-style: italic; color: #f4f0e6; font-size: 1.1rem; line-height: 1.6;'>
            "{text}"
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_newspapers(left_hl, centre_hl, right_hl):
    st.markdown(f"""
    <div style='display: flex; gap: 20px; margin: 25px 0;'>
        <div style='flex: 1; background: #f4f0e6; color: #111; padding: 18px; border-radius: 6px; border-top: 8px solid #e4003b; box-shadow: 0 8px 16px rgba(0,0,0,0.5); display: flex; flex-direction: column;'>
            <div style='font-family: "Newsreader", serif; font-weight: 900; font-size: 1.2rem; text-align: center; border-bottom: 2px solid #111; margin-bottom: 12px; padding-bottom: 6px; text-transform: uppercase;'>The Clarion (Left)</div>
            <div style='font-family: "IBM Plex Sans", sans-serif; font-weight: 800; font-size: 1.2rem; text-align: center; line-height: 1.3; flex-grow: 1; display: flex; align-items: center; justify-content: center;'>"{left_hl}"</div>
        </div>
        <div style='flex: 1; background: #f4f0e6; color: #111; padding: 18px; border-radius: 6px; border-top: 8px solid #faa61a; box-shadow: 0 8px 16px rgba(0,0,0,0.5); display: flex; flex-direction: column;'>
            <div style='font-family: "Newsreader", serif; font-weight: 900; font-size: 1.2rem; text-align: center; border-bottom: 2px solid #111; margin-bottom: 12px; padding-bottom: 6px; text-transform: uppercase;'>The Statesman (Centre)</div>
            <div style='font-family: "IBM Plex Sans", sans-serif; font-weight: 800; font-size: 1.2rem; text-align: center; line-height: 1.3; flex-grow: 1; display: flex; align-items: center; justify-content: center;'>"{centre_hl}"</div>
        </div>
        <div style='flex: 1; background: #f4f0e6; color: #111; padding: 18px; border-radius: 6px; border-top: 8px solid #0087dc; box-shadow: 0 8px 16px rgba(0,0,0,0.5); display: flex; flex-direction: column;'>
            <div style='font-family: "Newsreader", serif; font-weight: 900; font-size: 1.2rem; text-align: center; border-bottom: 2px solid #111; margin-bottom: 12px; padding-bottom: 6px; text-transform: uppercase;'>Daily Standard (Right)</div>
            <div style='font-family: "IBM Plex Sans", sans-serif; font-weight: 800; font-size: 1.2rem; text-align: center; line-height: 1.3; flex-grow: 1; display: flex; align-items: center; justify-content: center;'>"{right_hl}"</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def stat_card(label, value, delta_text, desc, delta_num=0.0, inverse=False):
    if abs(delta_num) < 1e-9:
        cls = 'sc-flat'; arrow = ''
    else:
        good = (delta_num > 0) != inverse
        cls = 'sc-good' if good else 'sc-bad'
        arrow = '▲ ' if delta_num > 0 else '▼ '
    return (f"<div class='sc-card' tabindex='0'>"
            f"<div class='sc-label'><span>{label}</span><span class='sc-info'>i</span></div>"
            f"<div class='sc-value'>{value}</div>"
            f"<span class='sc-delta {cls}'>{arrow}{delta_text}</span>"
            f"<div class='sc-tip'>{desc}</div></div>")

def render_imf_table(df):
    html = "<table class='ch-table'><thead><tr>"
    for col in df.columns:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for val in row:
            html += f"<td>{val}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

def render_parliament_bar(seats, gov_party):
    total = sum(seats.values()) or 650
    gov_seats = seats.get(gov_party, 0)
    majority = gov_seats - 326
    
    if majority >= 0:
        badge = f"<span style='color:#6fbf8a; background:rgba(111,191,138,0.15); padding:4px 12px; border-radius:12px; font-size:0.9rem; font-weight:700; border:1px solid #6fbf8a;'>Working Majority: +{majority}</span>"
    else:
        badge = f"<span style='color:#e65c4f; background:rgba(230,92,79,0.15); padding:4px 12px; border-radius:12px; font-size:0.9rem; font-weight:700; border:1px solid #e65c4f;'>Minority: {abs(majority)} short of 326</span>"
        
    bar_html = "<div style='display:flex; height:24px; border-radius:8px; overflow:hidden; border:1px solid #1f3b2d; margin:14px 0; background:#07100c; box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);'>"
    for party, count in seats.items():
        if count > 0:
            pct = (count / total) * 100
            c = PARTY_COLOURS.get(party, '#888888')
            bar_html += f"<div style='width:{pct}%; background-color:{c}; border-right:1px solid rgba(0,0,0,0.2);' title='{party}: {count} seats'></div>"
    bar_html += "</div>"
    
    badges_html = "<div style='display:flex; flex-wrap:wrap; gap:10px; font-size:0.85rem;'>"
    for party, count in sorted(seats.items(), key=lambda x: x[1], reverse=True):
        c = PARTY_COLOURS.get(party, '#888888')
        badges_html += f"<span style='background:#10261c; border:1px solid #1f3b2d; border-left:4px solid {c}; padding:4px 10px; border-radius:6px; box-shadow:0 2px 4px rgba(0,0,0,0.2);'><b>{party}</b>: {count}</span>"
    badges_html += "</div>"
    
    st.markdown(f"""
    <div style='background:linear-gradient(145deg, #10261c, #0b1a13); border:1px solid #1f3b2d; border-radius:8px; padding:18px; margin-bottom:18px; box-shadow:0 6px 12px rgba(0,0,0,0.3);'>
        <div style='display:flex; justify-content:space-between; align-items:center;'>
            <span style='font-family:"Newsreader",serif; font-size:1.3rem; font-weight:700; color: #d4af37;'>House of Commons ({gov_seats}/650 seats)</span>
            {badge}
        </div>
        {bar_html}
        {badges_html}
    </div>
    """, unsafe_allow_html=True)
