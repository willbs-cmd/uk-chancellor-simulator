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

/* FORCE DARK MODE OVERRIDE */
.stApp, .main, .block-container { background-color: #07100c !important; color: #f4f0e6 !important; }
p, span, div, label, li, h1, h2, h3, h4 { font-family: 'IBM Plex Sans', sans-serif; color: #f4f0e6 !important; }
h1, h2, h3, h4 { font-family: 'Newsreader', serif !important; }

/* SIDEBAR FIX */
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background-color: #0a1410 !important; border-right: 1px solid #1f3b2d !important; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { color: #a3b8ad !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #d4af37 !important; }

/* LAYOUT COMPRESSION */
.block-container { max-width: 96%; padding-top: 2rem; padding-bottom: 1rem; }
div[data-testid="stColumn"] { z-index: 1; }
div[data-testid="stColumn"]:has(.sc-card:hover) { z-index: 9999 !important; }

/* TABS */
[data-testid="stTabs"] button { font-size: 1rem; font-weight: 600; padding-bottom: 5px; color: #a3b8ad !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #d4af37 !important; border-bottom-color: #d4af37 !important; }

/* RADIO BUTTONS */
[data-testid="stRadio"] label { background: linear-gradient(145deg, #10261c, #0b1a13) !important; border: 1px solid #1f3b2d !important; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; width: 100%; }
[data-testid="stRadio"] label:hover { border-color: #d4af37 !important; }
[data-testid="stRadio"] label:has(input:checked) { border-color: #d4af37 !important; box-shadow: inset 4px 0 0 #d4af37 !important; }

/* MAIN BUTTONS */
div.stButton > button { background: linear-gradient(145deg, #10261c, #0b1a13) !important; border: 1px solid #d4af37 !important; border-radius: 6px; padding: 0.4rem 1rem; color: #f4f0e6 !important; }
div.stButton > button:hover { background: #d4af37 !important; color: #07100c !important; }
div.stButton > button * { color: inherit !important; }
div.stButton > button:hover * { color: #07100c !important; }

/* COMPACT STAT CARDS */
.sc-card { position: relative; background: linear-gradient(145deg, #10261c, #0b1a13) !important; border: 1px solid #1f3b2d !important; border-top: 3px solid #d4af37 !important; border-radius: 6px; padding: 10px 12px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.25); }
.sc-label { display: flex; align-items: center; justify-content: space-between; color: #a3b8ad !important; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sc-info { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; border: 1px solid #a3b8ad !important; border-radius: 50%; font-size: 0.7rem; cursor: help; color: #a3b8ad !important; }
.sc-card:hover .sc-info { border-color: #d4af37 !important; color: #d4af37 !important; }
.sc-value { font-family: 'Newsreader', serif !important; font-size: clamp(1.2rem, 1.8vw, 1.6rem); font-weight: 700; color: #f4f0e6 !important; white-space: nowrap; margin: 4px 0; }
.sc-delta { display: inline-block; font-size: 0.75rem; font-weight: 600; padding: 2px 6px; border-radius: 8px; white-space: nowrap; color: #f4f0e6 !important; }
.sc-good { background: rgba(111,191,138,.3) !important; color: #6fbf8a !important; border: 1px solid #6fbf8a !important; }
.sc-bad  { background: rgba(230,92,79,.3) !important; color: #e65c4f !important; border: 1px solid #e65c4f !important; }
.sc-flat { background: rgba(163,184,173,.3) !important; color: #a3b8ad !important; border: 1px solid #a3b8ad !important; }

/* TOOLTIP FIX */
.sc-tip { position: absolute; left: 0; top: calc(100% + 5px); z-index: 999999 !important; background: #07100c !important; color: #f4f0e6 !important; border: 1px solid #d4af37 !important; border-radius: 6px; padding: 10px; width: 220px; white-space: normal; box-shadow: 0 8px 20px rgba(0,0,0,0.9); opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .2s; }
.sc-card:hover .sc-tip { opacity: 1; visibility: visible; }

/* HUMPHREY MEMO */
.memo-box { background: linear-gradient(145deg, #162a20, #0b1712) !important; border-left: 4px solid #d4af37 !important; padding: 12px 15px; margin: 10px 0; border-radius: 6px; }
.memo-title { color: #d4af37 !important; font-family: "Newsreader", serif !important; font-weight: 800; font-size: 1.1rem; margin-bottom: 6px; }
.memo-text { font-style: italic; color: #f4f0e6 !important; font-size: 0.95rem; line-height: 1.4; }

/* BANNERS & PARLIAMENT */
.ch-banner { border-left: 5px solid #d4af37; background: linear-gradient(145deg, #10261c, #0b1a13) !important; padding: 12px 20px; border-radius: 6px; margin-bottom: 15px; }
.ch-banner h1 { margin: 0; font-size: 1.8rem; color: #f4f0e6 !important; }
.ch-banner .sub { color: #a3b8ad !important; margin-top: 4px; font-size: 0.9rem; }
.parl-box { background:linear-gradient(145deg, #10261c, #0b1a13) !important; border:1px solid #1f3b2d !important; border-radius:6px; padding:12px; margin-bottom:12px; }
.parl-title { font-family:"Newsreader",serif !important; font-size:1.1rem; font-weight:700; color: #d4af37 !important; display:flex; justify-content:space-between; }

.ch-news { background: linear-gradient(145deg, #10261c, #0b1a13) !important; border-left: 4px solid #a3b8ad !important; padding: 10px 15px; border-radius: 6px; font-size: 0.95rem; margin-bottom: 12px; color: #f4f0e6 !important; }
.ch-crisis { background: #2a1111 !important; border: 1px solid #e65c4f !important; border-left: 5px solid #e65c4f !important; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px; font-family: 'Newsreader', serif !important; font-size: 1.2rem; color: #f4f0e6 !important; }

/* NEWSPAPERS: class-based so the global 'div { color: cream !important }' rule can't wash out the ink */
.np-row { display: flex; flex-wrap: wrap; gap: 14px; margin: 15px 0; }
.np-paper { flex: 1 1 200px; background: #f4f0e6 !important; border-radius: 3px; box-shadow: 0 6px 14px rgba(0,0,0,0.55); display: flex; flex-direction: column; overflow: hidden; }
.np-paper .np-mast { background: var(--np); padding: 7px 10px 5px; text-align: center; border-bottom: 3px double rgba(0,0,0,0.45); }
.np-paper .np-name { font-family: 'Newsreader', serif !important; font-weight: 800; font-size: 1.05rem; letter-spacing: 0.04em; text-transform: uppercase; color: #ffffff !important; }
.np-paper .np-lean { font-size: 0.65rem; letter-spacing: 0.18em; text-transform: uppercase; color: rgba(255,255,255,0.85) !important; }
.np-paper .np-body { flex-grow: 1; display: flex; align-items: center; justify-content: center; padding: 18px 12px; min-height: 90px; }
.np-paper .np-hl { font-family: 'Newsreader', serif !important; font-weight: 800; font-size: 1.15rem; line-height: 1.2; text-align: center; text-transform: uppercase; color: #15110a !important; }

hr { border-bottom: 1px solid #1f3b2d !important; margin: 1rem 0; }
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
        rows += (f"<div style='display:flex; align-items:center; gap:10px; margin:6px 0;'><div style='width:140px; font-weight:600; font-size:0.95rem; color:#f4f0e6;'>{party}</div>"
                 f"<div style='flex:1; background:#07100c; border-radius:4px; height:20px; border:1px solid #1f3b2d;'><div style='height:100%; border-radius:3px; width:{min(val * 2.2, 100)}%; background:{c}'></div></div>"
                 f"<div style='width:50px; text-align:right; font-weight:700; color:#d4af37; font-size:0.95rem;'>{val:.0f}%</div></div>")
    st.markdown(rows, unsafe_allow_html=True)

def humphrey_message(text):
    st.markdown(f"""<div class='memo-box'><div class='memo-title'>💼 Memo from Sir Humphrey Appleby</div><div class='memo-text'>"{text}"</div></div>""", unsafe_allow_html=True)

def render_newspapers(left_hl, centre_hl, right_hl):
    from html import escape
    papers = [
        ('The Clarion', 'Left', '#b3002d', left_hl),
        ('The Statesman', 'Centre', '#b8730a', centre_hl),
        ('Daily Standard', 'Right', '#0b5cab', right_hl),
    ]
    html = "<div class='np-row'>"
    for name, lean, colour, hl in papers:
        html += (f"<div class='np-paper' style='--np:{colour}'>"
                 f"<div class='np-mast'><div class='np-name'>{escape(name)}</div><div class='np-lean'>{lean}</div></div>"
                 f"<div class='np-body'><div class='np-hl'>{escape(str(hl))}</div></div></div>")
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

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
        html += f"<th style='text-align:left; border-bottom:2px solid #d4af37; padding:8px; color:#d4af37 !important;'>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for val in row:
            html += f"<td style='padding:8px; border-bottom:1px solid #1f3b2d; color:#f4f0e6 !important;'>{val}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    st.markdown(html, unsafe_allow_html=True)

def render_parliament_bar(seats, gov_party):
    total = sum(seats.values()) or 650
    gov_seats = seats.get(gov_party, 0)
    majority = gov_seats - 326
    
    if majority >= 0:
        badge = f"<span style='color:#6fbf8a !important; background:rgba(111,191,138,0.15) !important; padding:2px 8px; border-radius:12px; font-size:0.8rem; font-weight:700; border:1px solid #6fbf8a !important;'>Working Majority: +{majority}</span>"
    else:
        badge = f"<span style='color:#e65c4f !important; background:rgba(230,92,79,0.15) !important; padding:2px 8px; border-radius:12px; font-size:0.8rem; font-weight:700; border:1px solid #e65c4f !important;'>Minority: {abs(majority)} short of 326</span>"
        
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
        badges_html += f"<span style='background:#10261c !important; border:1px solid #1f3b2d !important; border-left:3px solid {c} !important; padding:2px 8px; border-radius:4px; color:#f4f0e6 !important;'><b>{party}</b>: {count}</span>"
    badges_html += "</div>"
    
    st.markdown(f"""
    <div class='parl-box'>
        <div class='parl-title'>
            <span style='color:#d4af37 !important;'>House of Commons ({gov_seats}/650)</span>
            {badge}
        </div>
        {bar_html}
        {badges_html}
    </div>
    """, unsafe_allow_html=True)
