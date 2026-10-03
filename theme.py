import streamlit as st

PARTY_COLOURS = {
    'Labour': '#e4003b',
    'Conservative': '#3b9be0',
    'Liberal Democrats': '#faa61a',
    'Reform UK': '#12B6CF',
    'Green Party': '#6AB023',
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --bench: #0d1f17;      /* Commons bench green, deep */
  --leather: #163326;    /* panels */
  --leather-2: #1d4130;  /* hover / raised */
  --brass: #c9a45c;      /* accent */
  --paper: #efe9da;      /* text */
  --muted: #9fb3a6;
  --alarm: #c8412f;
}

html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: var(--bench); color: var(--paper); }
.block-container { max-width: 1180px; padding-top: 1.5rem; }
header[data-testid="stHeader"] { background: transparent; }

h1, h2, h3, h4 { font-family: 'Newsreader', serif !important; color: var(--paper); letter-spacing: -0.01em; }

[data-testid="stMetric"] {
  background: var(--leather);
  border: 1px solid #2b5440;
  border-top: 3px solid var(--brass);
  border-radius: 6px;
  padding: 14px 16px 12px;
}
[data-testid="stMetricLabel"] p { color: var(--muted); font-size: 0.8rem; }
[data-testid="stMetricValue"] { font-family: 'Newsreader', serif; font-size: 2rem; font-weight: 700; color: var(--paper); }
[data-testid="stMetricDelta"] { font-size: 0.8rem; }

[data-testid="stExpander"] { background: var(--leather); border: 1px solid #2b5440; border-radius: 6px; }
[data-testid="stExpander"] summary p { font-family: 'Newsreader', serif; font-size: 1.1rem; }

div[role="radiogroup"] { gap: 0.5rem; }
div[role="radiogroup"] > label {
  background: var(--leather);
  border: 1px solid #2b5440;
  border-radius: 6px;
  padding: 12px 16px;
  width: 100%;
  transition: border-color .15s, background .15s;
}
div[role="radiogroup"] > label:hover { border-color: var(--brass); background: var(--leather-2); }
div[role="radiogroup"] > label:has(input:checked) { border-color: var(--brass); background: var(--leather-2); box-shadow: inset 4px 0 0 var(--brass); }
div[role="radiogroup"] > label p { font-size: 1rem; line-height: 1.45; }

div.stButton > button {
  border-radius: 6px; font-weight: 600; padding: 0.6rem 1.5rem;
  background: transparent; color: var(--paper); border: 1px solid var(--brass);
}
div.stButton > button:hover { background: var(--brass); color: var(--bench); border-color: var(--brass); }
div.stButton > button[kind="primary"] { background: var(--brass); color: var(--bench); }
div.stButton > button:focus-visible { outline: 2px solid var(--paper); outline-offset: 2px; }

.stApp, .stApp p, .stApp li, .stApp label, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"] p, [data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label, [data-testid="stRadio"] label p,
[data-testid="stSelectbox"] div, [data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span { color: var(--paper) !important; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }
[data-testid="stMetricLabel"] p { color: var(--muted) !important; }
[data-testid="stMetricDelta"] svg { fill: currentColor; }

[data-testid="stExpander"] details, [data-testid="stExpander"] details > summary {
  background: var(--leather) !important; border-radius: 6px;
}
[data-testid="stExpander"] details > summary:hover { background: var(--leather-2) !important; }
[data-testid="stExpander"] summary svg { fill: var(--brass); color: var(--brass); }

[data-testid="stRadio"] label, [data-testid="stRadio"] label[data-baseweb="radio"] {
  background: var(--leather) !important; border: 1px solid #2b5440; border-radius: 6px;
  padding: 12px 16px; width: 100%; margin-bottom: 6px; transition: border-color .15s, background .15s;
}
[data-testid="stRadio"] label:hover { border-color: var(--brass); background: var(--leather-2) !important; }
[data-testid="stRadio"] label:has(input:checked) {
  border-color: var(--brass); background: var(--leather-2) !important; box-shadow: inset 4px 0 0 var(--brass);
}
[data-testid="stRadio"] label p { font-size: 1rem; line-height: 1.45; }
[data-testid="stRadio"] label > div:first-child { border-color: var(--brass) !important; }
[data-testid="stRadio"] label:has(input:checked) > div:first-child { background-color: var(--brass) !important; }

[data-baseweb="select"] > div { background: var(--leather) !important; border-color: #2b5440 !important; }
[data-baseweb="popover"] li, [data-baseweb="menu"] li { background: var(--leather) !important; color: var(--paper) !important; }

[data-testid="stMetric"] { overflow: hidden; min-width: 0; box-sizing: border-box; }
[data-testid="stMetric"] > div, [data-testid="stMetricValue"] { max-width: 100%; min-width: 0; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
  white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
  overflow-wrap: anywhere; word-break: normal;
  font-size: clamp(1.15rem, 1.7vw, 1.6rem) !important; line-height: 1.15;
}

.ch-banner { border-left: 6px solid var(--brass); background: var(--leather); padding: 18px 22px; border-radius: 6px; margin-bottom: 14px; }
.ch-banner h1 { margin: 0; font-size: 2.1rem; }
.ch-banner .sub { color: var(--muted); margin-top: 4px; }
.ch-pips { display: flex; gap: 5px; margin-top: 14px; }
.ch-pip { height: 6px; flex: 1; border-radius: 3px; background: #2b5440; }
.ch-pip.done { background: var(--brass); }
.ch-pip.now { background: var(--paper); }

.ch-crisis { background: #3a1511; border: 1px solid var(--alarm); border-left: 6px solid var(--alarm); border-radius: 6px; padding: 16px 20px; margin: 8px 0 14px; font-family: 'Newsreader', serif; font-size: 1.25rem; }
.ch-crisis small { display: block; font-family: 'IBM Plex Sans', sans-serif; font-size: .9rem; color: #e3b3ab; margin-top: 6px; }

.ch-news { background: var(--leather); border-left: 4px solid var(--muted); padding: 10px 16px; border-radius: 4px; color: var(--paper); margin-bottom: 14px; }

.ch-bar { display: flex; align-items: center; gap: 12px; margin: 7px 0; }
.ch-bar .name { width: 150px; color: var(--paper); }
.ch-bar .track { flex: 1; background: #10281d; border-radius: 4px; height: 20px; overflow: hidden; }
.ch-bar .fill { height: 100%; border-radius: 4px; }
.ch-bar .val { width: 52px; text-align: right; font-variant-numeric: tabular-nums; }
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
    st.markdown(
        f"<div class='ch-crisis'>{title}<small>Emergency intervention required immediately.</small></div>",
        unsafe_allow_html=True,
    )

def news_box(text):
    st.markdown(f"<div class='ch-news'>{text}</div>", unsafe_allow_html=True)

def render_polls(df):
    latest = df.iloc[-1]
    rows = ''
    for party, val in latest.sort_values(ascending=False).items():
        c = PARTY_COLOURS.get(party, '#888')
        rows += (f"<div class='ch-bar'><div class='name'>{party}</div>"
                 f"<div class='track'><div class='fill' style='width:{min(val * 2.2, 100)}%;background:{c}'></div></div>"
                 f"<div class='val'>{val:.0f}%</div></div>")
    st.markdown(rows, unsafe_allow_html=True)
    if len(df) >= 2:
        plot = df.copy()
        plot.index = plot.index.astype(int)
        st.line_chart(plot, color=[PARTY_COLOURS[c] for c in plot.columns])

# --- NEW HUMPHREY COMPONENT ---
def humphrey_message(text):
    st.markdown(f"""
    <div style='background-color: #1a221f; border-left: 5px solid #c9a45c; padding: 18px; margin: 15px 0px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <div style='color: #c9a45c; font-family: "Newsreader", serif; font-weight: bold; font-size: 1.2rem; margin-bottom: 8px; display: flex; align-items: center;'>
            <span style='font-size: 1.4rem; margin-right: 8px;'>💼</span> Memo from Sir Humphrey Appleby
        </div>
        <div style='font-style: italic; color: #efe9da; font-size: 1.05rem; line-height: 1.5;'>
            "{text}"
        </div>
    </div>
    """, unsafe_allow_html=True)
