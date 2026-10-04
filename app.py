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

html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: var(--bench); color: var(--paper); }

/* COMPACT LAYOUT - Fits on screen better */
.block-container { max-width: 96%; padding-top: 2rem; padding-bottom: 1rem; }

/* FIX INFO BLOCK OVERLAPPING (Z-INDEX HACK) */
div[data-testid="stColumn"] { z-index: 1; }
div[data-testid="stColumn"]:has(.sc-card:hover) { z-index: 9999 !important; }

/* Elegant Headers */
h1, h2, h3, h4 { font-family: 'Newsreader', serif !important; color: var(--paper); letter-spacing: -0.01em; }
h2, h3 { border-bottom: 1px solid #1f3b2d; padding-bottom: 4px; margin-bottom: 10px; margin-top: 5px; font-size: 1.25rem; }

/* Base text forces */
.stApp p, .stApp li, .stApp label { color: var(--paper) !important; }
[data-testid="stCaptionContainer"] p { color: var(--muted) !important; }

/* Tabs (Compact) */
[data-testid="stTabs"] button { font-size: 1rem; font-weight: 600; padding-bottom: 5px; }

/* Radio Buttons */
[data-testid="stRadio"] label {
  background: linear-gradient(145deg, var(--leather), #0b1a13) !important;
  border: 1px solid #1f3b2d; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; width: 100%;
}
[data-testid="stRadio"] label:hover { border-color: var(--brass); background: linear-gradient(145deg, var(--leather-2), var(--leather)) !important; }
[data-testid="stRadio"] label:has(input:checked) { border-color: var(--brass); box-shadow: inset 4px 0 0 var(--brass); }

/* Buttons */
div.stButton > button { background: linear-gradient(145deg, var(--leather), #0b1a13); border: 1px solid var(--brass); border-radius: 6px; padding: 0.4rem 1rem; }
div.stButton > button:hover { background: var(--brass); color: var(--bench); }
div.stButton > button[kind="primary"] { background: var(--brass); color: var(--bench); }

/* COMPACT STAT CARDS - NO VERTICAL WRAPPING */
.sc-card { 
  position: relative; 
  background: linear-gradient(145deg, var(--leather), #0b1a13); 
  border: 1px solid #1f3b2d; border-top: 3px solid var(--brass);
  border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; 
  box-shadow: 0 4px 6px rgba(0,0,0,0.25);
}
.sc-label { display: flex; align-items: center; justify-content: space-between; color: var(--muted); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sc-info { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; border: 1px solid var(--muted); border-radius: 50%; font-size: 0.7rem; cursor: help; }
.sc-card:hover .sc-info { border-color: var(--brass); color: var(--brass); }
.sc-value { font-family: 'Newsreader', serif; font-size: clamp(1.2rem, 1.8vw, 1.6rem); font-weight: 700; color: var(--paper); white-space: nowrap; margin: 4px 0; }
.sc-delta { display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 2px 6px; border-radius: 8px; white-space: nowrap; }

.sc-good { color: #6fbf8a; background: rgba(111,191,138,.15); }
.sc-bad  { color: #e65c4f; background: rgba(230,92,79,.15); }
.sc-flat { color: var(--muted); background: rgba(163,184,173,.15); }

/* THE FIX FOR THE INFO BLOCK OVERLAPPING */
.sc-tip { 
  position: absolute; left: 0; top: calc(100% + 5px); 
  z-index: 999999 !important; 
  background: #07100c; color: #f4f0e6; 
  border: 1px solid var(--brass); border-radius: 6px; padding: 10px; 
  font-family: 'IBM Plex Sans', sans-serif; font-size: 0.85rem; 
  width: 220px; white-space: normal; 
  box-shadow: 0 8px 20px rgba(0,0,0,0.9); 
  opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .2s; 
}
.sc-card:hover .sc-tip { opacity: 1; visibility: visible; }

/* COMPACT NEWSPAPERS */
.np-container { display: flex; gap: 12px; margin: 15px 0; }
.np-paper { flex: 1; background: #f4f0e6; color: #111; padding: 12px; border-radius: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.4); display: flex; flex-direction: column; }
.np-title { font-family: "Newsreader", serif; font-weight: 900; font-size: 0.85rem; text-align: center; border-bottom: 2px solid #111; margin-bottom: 8px; padding-bottom: 4px; text-transform: uppercase; }
.np-headline { font-family: "IBM Plex Sans", sans-serif; font-weight: 800; font-size: 1rem; text-align: center; line-height: 1.2; display: flex; align-items: center; justify-content: center; flex-grow: 1;}

/* COMPACT PARLIAMENT & MEMOS */
.ch-banner { border-left: 5px solid var(--brass); background: linear-gradient(145deg, var(--leather), #0b1a13); padding: 12px 20px; border-radius: 6px; margin-bottom: 15px; }
.ch-banner h1 { margin: 0; font-size: 1.8rem; }
.ch-banner .sub { color: var(--muted); margin-top: 4px; font-size: 0.9rem; }
.parl-box { background:linear-gradient(145deg, #10261c, #0b1a13); border:1px solid #1f3b2d; border-radius:6px; padding:12px; margin-bottom:12px; }
.parl-title { font-family:"Newsreader",serif; font-size:1.1rem; font-weight:700; color: #d4af37; display:flex; justify-content:space-between; }
.memo-box { background: linear-gradient(145deg, #162a20, #0b1712); border-left: 4px solid var(--brass); padding: 12px 15px; margin: 10px 0; border-radius: 6px; }
.memo-title { color: var(--brass); font-family: "Newsreader", serif; font-weight: 800; font-size: 1.1rem; margin-bottom: 6px; }
.memo-text { font-style: italic; color: #f4f0e6; font-size: 0.95rem; line-height: 1.4; }
.ch-news { background: linear-gradient(145deg, var(--leather), #0b1a13); border-left: 4px solid var(--muted); padding: 10px 15px; border-radius: 6px; font-size: 0.95rem; margin-bottom: 12px; }
.ch-crisis { background: #2a1111; border: 1px solid var(--alarm); border-left: 5px solid var(--alarm); border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; font-family: 'Newsreader', serif; font-size: 1.2rem; }
.ch-crisis small { display: block; font-family: 'IBM Plex Sans', sans-serif; font-size: 0.85rem; color: #e3b3ab; margin-top: 4px; }
hr { margin: 1rem 0; }
</style>
"""

def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)

def header(party, term, year, block):
    st.markdown(f"""
    <div class='ch-banner' style='border-left-color:{PARTY_COLOURS.get(party, '#d4af37')}'>
        <h1>🏛️ {party} Government</h1>
        <div class='sub'>Chancellor Simulator &nbsp;|&nbsp; Term {term} &nbsp;|&nbsp; Year {min(year, 5)} of 5, block {block} of 3</div>
    </div>
    """, unsafe_allow_html=True)

def crisis_card(title):
    st.markdown(f"<div class='ch-crisis'>{title}<small>Emergency intervention required immediately.</small></div>", unsafe_allow_html=True)

def news_box(text):
    st.markdown(f"<div class='ch-news'>{text}</div>", unsafe_allow_html=True)

def render_polls(df):
    latest = df.iloc[-1]
    rows = ''
    for party, val in latest.sort_values(ascending=False).items():
        c = PARTY_COLOURS.get(party, '#888')
        rows += (f"<div style='display:flex; align-items:center; gap:10px; margin:6px 0;'><div style='width:140px; font-weight:600; font-size:0.95rem;'>{party}</div>"
                 f"<div style='flex:1; background:#07100c; border-radius:4px; height:20px; border:1px solid #1f3b2d;'><div style='height:100%; border-radius:3px; width:{min(val * 2.2, 100)}%; background:{c}'></div></div>"
                 f"<div style='width:50px; text-align:right; font-weight:700; color:var(--brass); font-size:0.95rem;'>{val:.0f}%</div></div>")
    st.markdown(rows, unsafe_allow_html=True)

def humphrey_message(text):
    st.markdown(f"""<div class='memo-box'><div class='memo-title'>💼 Memo from Sir Humphrey Appleby</div><div class='memo-text'>"{text}"</div></div>""", unsafe_allow_html=True)

def render_newspapers(left_hl, centre_hl, right_hl):
    st.markdown(f"""
    <div class='np-container'>
        <div class='np-paper' style='border-top: 5px solid #e4003b;'>
            <div class='np-title'>The Clarion (Left)</div>
            <div class='np-headline'>"{left_hl}"</div>
        </div>
        <div class='np-paper' style='border-top: 5px solid #faa61a;'>
            <div class='np-title'>The Statesman (Centre)</div>
            <div class='np-headline'>"{centre_hl}"</div>
        </div>
        <div class='np-paper' style='border-top: 5px solid #0087dc;'>
            <div class='np-title'>Daily Standard (Right)</div>
            <div class='np-headline'>"{right_hl}"</div>
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
    return (f"<div class='sc-card'>"
            f"<div class='sc-label'><span>{label}</span><span class='sc-info'>i</span></div>"
            f"<div class='sc-value'>{value}</div>"
            f"<span class='sc-delta {cls}'>{arrow}{delta_text}</span>"
            f"<div class='sc-tip'>{desc}</div></div>")

def render_imf_table(df):
    html = "<table style='width:100%; border-collapse:collapse; margin-bottom:15px; font-size:0.95rem;'><thead><tr>"
    for col in df.columns:
        html += f"<th style='text-align:left; border-bottom:2px solid var(--brass); padding:8px;'>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for val in row:
            html += f"<td style='padding:8px; border-bottom:1px solid #1f3b2d;'>{val}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

def render_parliament_bar(seats, gov_party):
    total = sum(seats.values()) or 650
    gov_seats = seats.get(gov_party, 0)
    majority = gov_seats - 326
    
    if majority >= 0:
        badge = f"<span style='color:#6fbf8a; background:rgba(111,191,138,0.15); padding:2px 8px; border-radius:12px; font-size:0.8rem; font-weight:700; border:1px solid #6fbf8a;'>Working Majority: +{majority}</span>"
    else:
        badge = f"<span style='color:#e65c4f; background:rgba(230,92,79,0.15); padding:2px 8px; border-radius:12px; font-size:0.8rem; font-weight:700; border:1px solid #e65c4f;'>Minority: {abs(majority)} short of 326</span>"
        
    bar_html = "<div style='display:flex; height:18px; border-radius:4px; overflow:hidden; border:1px solid #1f3b2d; margin:10px 0; background:#07100c;'>"
    for party, count in seats.items():
        if count > 0:
            pct = (count / total) * 100
            c = PARTY_COLOURS.get(party, '#888888')
            bar_html += f"<div style='width:{pct}%; background-color:{c}; border-right:1px solid rgba(0,0,0,0.2);' title='{party}: {count} seats'></div>"
    bar_html += "</div>"
    
    badges_html = "<div style='display:flex; flex-wrap:wrap; gap:8px; font-size:0.8rem;'>"
    for party, count in sorted(seats.items(), key=lambda x: x[1], reverse=True):
        c = PARTY_COLOURS.get(party, '#888888')
        badges_html += f"<span style='background:#10261c; border:1px solid #1f3b2d; border-left:3px solid {c}; padding:2px 8px; border-radius:4px;'><b>{party}</b>: {count}</span>"
    badges_html += "</div>"
    
    st.markdown(f"""
    <div class='parl-box'>
        <div class='parl-title'>
            <span>House of Commons ({gov_seats}/650)</span>
            {badge}
        </div>
        {bar_html}
        {badges_html}
    </div>
    """, unsafe_allow_html=True)
