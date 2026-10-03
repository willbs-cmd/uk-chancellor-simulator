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
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,700;6..72,800&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --bench: #0b1712;      
  --leather: #142e22;    
  --leather-2: #1b3d2d;  
  --brass: #c9a45c;      
  --paper: #efe9da;      
  --muted: #9fb3a6;
  --alarm: #d6604f;
}

/* Global Background & Typography */
html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: var(--bench); color: var(--paper); }
.block-container { max-width: 1250px; padding-top: 1.5rem; }
header[data-testid="stHeader"] { background: transparent; }

/* Elegant Headers */
h1, h2, h3, h4 { 
    font-family: 'Newsreader', serif !important; 
    color: var(--paper); 
    letter-spacing: -0.01em; 
}
h2, h3 { 
    border-bottom: 1px solid #2b5440; 
    padding-bottom: 8px; 
    margin-bottom: 16px; 
}

/* Base text forces */
.stApp, .stApp p, .stApp li, .stApp label, [data-testid="stMarkdownContainer"] p, 
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label, 
[data-testid="stRadio"] label p { color: var(--paper) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }

/* Beautiful Radio Buttons (Policy Choices) */
[data-testid="stRadio"] label, [data-testid="stRadio"] label[data-baseweb="radio"] {
  background: linear-gradient(145deg, var(--leather), #10261c) !important;
  border: 1px solid #2b5440;
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 10px;
  width: 100%;
  box-shadow: 0 4px 6px rgba(0,0,0,0.15);
  transition: all 0.2s ease;
}
[data-testid="stRadio"] label:hover { 
  border-color: var(--brass); 
  background: linear-gradient(145deg, var(--leather-2), #142e22) !important;
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0,0,0,0.3);
}
[data-testid="stRadio"] label:has(input:checked) {
  border-color: var(--brass); 
  background: linear-gradient(145deg, var(--leather-2), var(--leather)) !important; 
  box-shadow: inset 4px 0 0 var(--brass), 0 4px 8px rgba(0,0,0,0.3);
}

/* Polished Buttons */
div.stButton > button {
  border-radius: 6px; font-weight: 600; padding: 0.6rem 1.5rem;
  background: linear-gradient(145deg, var(--leather), #10261c); 
  color: var(--paper); border: 1px solid var(--brass);
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
  transition: all 0.2s ease;
}
div.stButton > button:hover { 
  background: var(--brass); color: var(--bench); 
  border-color: var(--brass); 
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.4);
}
div.stButton > button[kind="primary"] { 
  background: var(--brass); color: var(--bench); 
}

/* Native Tooltips */
[data-testid="stTooltipContent"], [data-testid="stTooltipContent"] *,
div[data-baseweb="tooltip"], div[data-baseweb="tooltip"] * {
  background-color: #0b1712 !important;
  color: #efe9da !important;
}
div[data-baseweb="tooltip"] { border: 1px solid var(--brass) !important; border-radius: 6px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.6) !important; }

/* Custom Stat Cards (The Country/Economy Metrics) */
.sc-card { 
  position: relative; 
  background: linear-gradient(145deg, var(--leather), #10261c); 
  border: 1px solid #2b5440; 
  border-top: 3px solid var(--brass);
  border-radius: 8px; 
  padding: 12px 16px; 
  margin-bottom: 12px; 
  min-height: 108px; 
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}
.sc-label { display: flex; align-items: center; justify-content: space-between; color: var(--muted); font-size: .85rem; line-height: 1.2; }
.sc-info { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; flex: none; border: 1px solid var(--muted); border-radius: 50%; font-size: .68rem; font-style: normal; cursor: help; color: var(--muted); transition: all 0.2s ease; }
.sc-card:hover .sc-info, .sc-card:focus-within .sc-info { border-color: var(--brass); color: var(--brass); }
.sc-value { font-family: 'Newsreader', serif; font-size: 1.9rem; font-weight: 700; color: var(--paper); line-height: 1.25; margin: 4px 0 6px; }
.sc-delta { display: inline-block; font-size: .8rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; }
.sc-good { color: #6fbf8a; background: rgba(111,191,138,.14); }
.sc-bad  { color: #e0705d; background: rgba(224,112,93,.14); }
.sc-flat { color: var(--muted); background: rgba(159,179,166,.12); }
.sc-tip { position: absolute; left: 0; right: 0; top: calc(100% + 6px); z-index: 9999; background: #0b1712; color: #efe9da; border: 1px solid var(--brass); border-radius: 6px; padding: 10px 12px; font-family: 'IBM Plex Sans', sans-serif; font-size: .88rem; font-weight: 400; line-height: 1.45; box-shadow: 0 6px 16px rgba(0,0,0,.6); opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .15s; }
.sc-card:hover .sc-tip, .sc-card:focus-within .sc-tip { opacity: 1; visibility: visible; }
div[data-testid="stColumn"]:has(.sc-card:hover), div[data-testid="stElementContainer"]:has(.sc-card:hover) { position: relative; z-index: 1000; }

/* Custom HTML Data Tables (Fixes the ugly white Streamlit Dataframe) */
.ch-table { width: 100%; border-collapse: collapse; margin-top: 10px; background: linear-gradient(145deg, var(--leather), #10261c); border-radius: 8px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.2); border: 1px solid #2b5440; }
.ch-table th { background: #0b1712; color: var(--brass); font-family: 'Newsreader', serif; padding: 12px 16px; text-align: left; border-bottom: 2px solid var(--brass); font-size: 1.1rem; font-weight: 700; }
.ch-table td { padding: 12px 16px; border-bottom: 1px solid #1a3a2a; color: var(--paper); font-variant-numeric: tabular-nums; }
.ch-table tr:last-child td { border-bottom: none; }

/* Banner & Misc Elements */
.ch-banner { border-left: 6px solid var(--brass); background: linear-gradient(145deg, var(--leather), #10261c); padding: 18px 22px; border-radius: 8px; margin-bottom: 14px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }
.ch-banner h1 { margin: 0; font-size: 2.2rem; }
.ch-banner .sub { color: var(--muted); margin-top: 4px; font-weight: 500; }
.ch-pips { display: flex; gap: 6px; margin-top: 14px; }
.ch-pip { height: 6px; flex: 1; border-radius: 3px; background: #1a3a2a; }
.ch-pip.done { background: var(--brass); }
.ch-pip.now { background: var(--paper); box-shadow: 0 0 5px rgba(239, 233, 218, 0.5); }

.ch-crisis { background: #2a1111; border: 1px solid var(--alarm); border-left: 6px solid var(--alarm); border-radius: 8px; padding: 16px 20px; margin: 8px 0 14px; font-family: 'Newsreader', serif; font-size: 1.3rem; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
.ch-crisis small { display: block; font-family: 'IBM Plex Sans', sans-serif; font-size: .9rem; color: #e3b3ab; margin-top: 6px; }

.ch-news { background: linear-gradient(145deg, var(--leather), #10261c); border-left: 4px solid var(--muted); padding: 12px 18px; border-radius: 6px; color: var(--paper); margin-bottom: 14px; box-shadow: 0 2px 5px rgba(0,0,0,0.15); }

.ch-bar { display: flex; align-items: center; gap: 12px; margin: 8px 0; }
.ch-bar .name { width: 150px; color: var(--paper); font-weight: 500; }
.ch-bar .track { flex: 1; background: #0b1712; border-radius: 6px; height: 22px; overflow: hidden; border: 1px solid #1a3a2a; box-shadow: inset 0 1px 3px rgba(0,0,0,0.5); }
.ch-bar .fill { height: 100%; border-radius: 5px; background-image: linear-gradient(90deg, rgba(255,255,255,0.1), transparent); }
.ch-bar .val { width: 52px; text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }
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
    colour = PARTY_COLOURS.get(party, '#c9a45c')
    st.markdown(
        f"""<div class='ch-banner' style='border-left-color:{colour}'>
        <h1>🏛️ {party} Government</h1>
        <div class='sub'>Chancellor Simulator, Hardcore Mode &nbsp;|&nbsp; Term {term} &nbsp;|&nbsp; Year {min(year, 5)} of 5, decision {block} of 3</div>
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
    <div style='background: linear-gradient(145deg, #16241e, #0e1713); border-left: 5px solid #c9a45c; padding: 18px; margin: 15px 0px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);'>
        <div style='color: #c9a45c; font-family: "Newsreader", serif; font-weight: 800; font-size: 1.25rem; margin-bottom: 8px; display: flex; align-items: center;'>
            <span style='font-size: 1.4rem; margin-right: 8px;'>💼</span> Memo from Sir Humphrey Appleby
        </div>
        <div style='font-style: italic; color: #efe9da; font-size: 1.05rem; line-height: 1.6;'>
            "{text}"
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_newspapers(left_hl, centre_hl, right_hl):
    st.markdown(f"""
    <div style='display: flex; gap: 15px; margin: 20px 0;'>
        <div style='flex: 1; background: #efe9da; color: #111; padding: 15px; border-radius: 6px; border-top: 6px solid #e4003b; box-shadow: 0 4px 8px rgba(0,0,0,0.4); display: flex; flex-direction: column;'>
            <div style='font-family: "Newsreader", serif; font-weight: 900; font-size: 1.1rem; text-align: center; border-bottom: 2px solid #111; margin-bottom: 10px; padding-bottom: 5px; text-transform: uppercase;'>The Clarion (Left)</div>
            <div style='font-family: "IBM Plex Sans", sans-serif; font-weight: 800; font-size: 1.15rem; text-align: center; line-height: 1.3; flex-grow: 1; display: flex; align-items: center; justify-content: center;'>"{left_hl}"</div>
        </div>
        <div style='flex: 1; background: #efe9da; color: #111; padding: 15px; border-radius: 6px; border-top: 6px solid #faa61a; box-shadow: 0 4px 8px rgba(0,0,0,0.4); display: flex; flex-direction: column;'>
            <div style='font-family: "Newsreader", serif; font-weight: 900; font-size: 1.1rem; text-align: center; border-bottom: 2px solid #111; margin-bottom: 10px; padding-bottom: 5px; text-transform: uppercase;'>The Statesman (Centre)</div>
            <div style='font-family: "IBM Plex Sans", sans-serif; font-weight: 800; font-size: 1.15rem; text-align: center; line-height: 1.3; flex-grow: 1; display: flex; align-items: center; justify-content: center;'>"{centre_hl}"</div>
        </div>
        <div style='flex: 1; background: #efe9da; color: #111; padding: 15px; border-radius: 6px; border-top: 6px solid #0087dc; box-shadow: 0 4px 8px rgba(0,0,0,0.4); display: flex; flex-direction: column;'>
            <div style='font-family: "Newsreader", serif; font-weight: 900; font-size: 1.1rem; text-align: center; border-bottom: 2px solid #111; margin-bottom: 10px; padding-bottom: 5px; text-transform: uppercase;'>Daily Standard (Right)</div>
            <div style='font-family: "IBM Plex Sans", sans-serif; font-weight: 800; font-size: 1.15rem; text-align: center; line-height: 1.3; flex-grow: 1; display: flex; align-items: center; justify-content: center;'>"{right_hl}"</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def stat_card(label, value, delta_text, desc, delta_num=0.0, inverse=False):
    if abs(delta_num) < 1e-9:
        cls = 'sc-flat'; arrow = ''
    else:
        good = (delta_num > 0) != inverse
        cls = 'sc-good' if good else 'sc-bad'
        arrow = '\u25b2 ' if delta_num > 0 else '\u25bc '
    return (f"<div class='sc-card' tabindex='0'>"
            f"<div class='sc-label'><span>{label}</span><span class='sc-info'>i</span></div>"
            f"<div class='sc-value'>{value}</div>"
            f"<span class='sc-delta {cls}'>{arrow}{delta_text}</span>"
            f"<div class='sc-tip'>{desc}</div></div>")

def render_imf_table(df):
    """Converts a pandas DataFrame into our beautiful custom HTML table."""
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
