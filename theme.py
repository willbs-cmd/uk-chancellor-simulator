import streamlit as st

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
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,500;6..72,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

:root {
  --bench: #0d1f17;      
  --leather: #163326;    
  --leather-2: #1d4130;  
  --brass: #c9a45c;      
  --paper: #efe9da;      
  --muted: #9fb3a6;
  --alarm: #c8412f;
}

html, body, [class*="css"], .stApp { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: var(--bench); color: var(--paper); }
.block-container { max-width: 1250px; padding-top: 1.5rem; }
header[data-testid="stHeader"] { background: transparent; }

h1, h2, h3, h4 { font-family: 'Newsreader', serif !important; color: var(--paper); letter-spacing: -0.01em; }

/* METRIC CARDS */
[data-testid="stMetric"] {
  background: var(--leather);
  border: 1px solid #2b5440;
  border-top: 3px solid var(--brass);
  border-radius: 6px;
  padding: 10px 12px 10px;
  overflow: visible !important;
}

[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] > div, [data-testid="stMetricLabel"] p {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  color: var(--muted) !important; 
  font-size: 0.85rem !important;
  line-height: 1.2 !important;
}

[data-testid="stMetricValue"] { 
  font-family: 'Newsreader', serif; 
  font-size: 1.8rem !important; 
  font-weight: 700; 
  color: var(--paper); 
  white-space: normal !important;
}

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

[data-baseweb="select"] > div { background: var(--leather) !important; border-color: #2b5440 !important; }
[data-baseweb="popover"] li, [data-baseweb="menu"] li { background: var(--leather) !important; color: var(--paper) !important; }

/* READABLE NATIVE TOOLTIPS (any remaining help= icons) */
[data-testid="stTooltipContent"], [data-testid="stTooltipContent"] *,
div[data-baseweb="tooltip"], div[data-baseweb="tooltip"] * {
  background-color: #0b1712 !important;
  color: #efe9da !important;
}
div[data-baseweb="tooltip"] { border: 1px solid var(--brass) !important; border-radius: 6px !important; }

/* STAT CARDS WITH HOVER TOOLTIP (one at a time: only the hovered card shows its tip) */
.sc-card { position: relative; background: var(--leather); border: 1px solid #2b5440; border-top: 3px solid var(--brass);
  border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; min-height: 108px; }
.sc-label { display: flex; align-items: center; justify-content: space-between; color: var(--muted); font-size: .85rem; line-height: 1.2; }
.sc-info { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; flex: none;
  border: 1px solid var(--muted); border-radius: 50%; font-size: .68rem; font-style: normal; cursor: help; color: var(--muted); }
.sc-card:hover .sc-info, .sc-card:focus-within .sc-info { border-color: var(--brass); color: var(--brass); }
.sc-value { font-family: 'Newsreader', serif; font-size: 1.8rem; font-weight: 700; color: var(--paper); line-height: 1.25; margin: 2px 0 6px; }
.sc-delta { display: inline-block; font-size: .8rem; font-weight: 600; padding: 1px 8px; border-radius: 10px; }
.sc-good { color: #6fbf8a; background: rgba(111,191,138,.14); }
.sc-bad  { color: #e0705d; background: rgba(224,112,93,.14); }
.sc-flat { color: var(--muted); background: rgba(159,179,166,.12); }
.sc-spark { display: block; width: 100%; height: 22px; margin-top: 8px; opacity: .9; }
.sc-tip { position: absolute; left: 0; right: 0; top: calc(100% + 6px); z-index: 9999;
  background: #0b1712; color: #efe9da; border: 1px solid var(--brass); border-radius: 6px; padding: 10px 12px;
  font-family: 'IBM Plex Sans', sans-serif; font-size: .88rem; font-weight: 400; line-height: 1.45;
  box-shadow: 0 6px 16px rgba(0,0,0,.6); opacity: 0; visibility: hidden; pointer-events: none; transition: opacity .15s; }
.sc-card:hover .sc-tip, .sc-card:focus-within .sc-tip { opacity: 1; visibility: visible; }
div[data-testid="stColumn"]:has(.sc-card:hover), div[data-testid="stElementContainer"]:has(.sc-card:hover),
div[data-testid="stColumn"]:has(.sc-card:focus-within), div[data-testid="stElementContainer"]:has(.sc-card:focus-within) {
  position: relative; z-index: 1000; }

/* NEWSPAPERS (stack on narrow screens) */
.np-strip { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 16px 0; }
.np-card { background: var(--paper); color: #111; padding: 14px; border-radius: 4px; border-top: 6px solid #888;
  box-shadow: 0 4px 6px rgba(0,0,0,.3); display: flex; flex-direction: column; }
.np-name { font-family: 'Newsreader', serif; font-weight: 700; font-size: 1.05rem; text-align: center; border-bottom: 2px solid #111;
  margin-bottom: 10px; padding-bottom: 5px; text-transform: uppercase; color: #111; }
.np-name span { font-weight: 500; font-size: .8rem; text-transform: none; }
.np-head { font-weight: 800; font-size: 1.05rem; text-align: center; line-height: 1.3; flex-grow: 1; display: flex;
  align-items: center; justify-content: center; color: #111; }

/* EVENT / DELAYED-CONSEQUENCE CARDS */
.ch-event { background: #14283a; border: 1px solid #2f5d86; border-left: 6px solid #4f8fba; border-radius: 6px; padding: 12px 16px; margin: 8px 0; }
.ch-event b { font-family: 'Newsreader', serif; font-size: 1.1rem; }
.ch-event small { display: block; color: #9cc3e0; margin-top: 4px; }

/* TIMELINE */
.tl-item { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid #1d4130; }
.tl-dot { flex: none; width: 12px; height: 12px; border-radius: 50%; margin-top: 6px; background: var(--brass); }
.tl-dot.crisis { background: var(--alarm); } .tl-dot.budget { background: #6fbf8a; } .tl-dot.event { background: #4f8fba; }
.tl-when { color: var(--muted); font-size: .78rem; }
.tl-title { font-family: 'Newsreader', serif; font-size: 1.05rem; color: var(--paper); }
.tl-choice { color: var(--paper); font-size: .9rem; opacity: .9; }
.tl-chip { display: inline-block; font-size: .75rem; font-weight: 600; padding: 0 7px; margin: 3px 4px 0 0; border-radius: 9px; }
.tl-chip.good { color: #6fbf8a; background: rgba(111,191,138,.14); } .tl-chip.bad { color: #e0705d; background: rgba(224,112,93,.14); }
.tl-soon { background: var(--leather); border: 1px dashed #2f5d86; border-radius: 6px; padding: 8px 12px; margin: 6px 0; color: var(--paper); }

/* SCORECARD */
.sk-wrap { background: var(--leather); border: 1px solid #2b5440; border-left: 6px solid var(--brass); border-radius: 6px; padding: 20px 24px; margin-bottom: 14px; }
.sk-title { font-family: 'Newsreader', serif; font-size: 2rem; font-weight: 700; margin: 0; }
.sk-sub { color: var(--muted); margin-bottom: 12px; }
.sk-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 10px; margin: 12px 0; }
.sk-stat { background: #10281d; border-radius: 6px; padding: 10px 12px; }
.sk-stat .n { color: var(--muted); font-size: .8rem; } .sk-stat .v { font-family: 'Newsreader', serif; font-size: 1.15rem; }
.sk-badge { display: inline-block; background: #10281d; border: 1px solid var(--brass); border-radius: 14px; padding: 3px 12px; margin: 3px 6px 3px 0; font-size: .85rem; }
.sk-grade { font-family: 'Newsreader', serif; font-size: 3.2rem; font-weight: 700; line-height: 1; }

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

/* ================= CHANCELLOR'S OFFICE OVERHAUL ================= */
.stApp { background: radial-gradient(circle at 50% -20%, #234b39 0%, #0d1f17 48%, #08130e 100%); }
.block-container { max-width: 1380px; padding-top: 1rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { background: #0a1811 !important; border-right: 1px solid #2b5440; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
[data-testid="stSidebar"] .stMarkdown h3 { color: var(--brass) !important; text-transform: uppercase; letter-spacing: .08em; font-size: .8rem; }
.office-crest { text-align:center; padding: 8px 4px 18px; border-bottom:1px solid #2b5440; margin-bottom:14px; }
.office-crest .crown { font-size:2.1rem; }
.office-crest .title { font-family:'Newsreader',serif; font-size:1.35rem; color:var(--paper); }
.office-crest .sub { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.12em; }
.office-section { background:rgba(22,51,38,.72); border:1px solid #2b5440; border-left:3px solid var(--brass); border-radius:7px; padding:14px 16px; margin:10px 0 16px; }
.office-kicker { color:var(--brass); text-transform:uppercase; letter-spacing:.12em; font-size:.72rem; font-weight:700; margin-bottom:4px; }
.office-title { font-family:'Newsreader',serif; color:var(--paper); font-size:1.55rem; line-height:1.1; }
.office-rule { height:1px; background:linear-gradient(90deg,var(--brass),transparent); margin:10px 0 16px; }
.office-note { background:#111d18; border:1px solid #294637; border-radius:6px; padding:11px 13px; color:var(--muted); font-size:.88rem; }
.menu-label { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.12em; margin:12px 0 5px; }
[data-testid="stSidebar"] div.stButton > button { width:100%; justify-content:flex-start; border-color:#294637; background:#10281d; }
[data-testid="stSidebar"] div.stButton > button:hover { background:var(--leather-2); }
[data-testid="stTabs"] [role="tablist"] { gap:3px; border-bottom:1px solid #2b5440; }
[data-testid="stTabs"] button[role="tab"] { color:var(--muted); background:#10281d; border:1px solid #2b5440; border-bottom:none; border-radius:6px 6px 0 0; padding:9px 16px; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color:var(--paper); background:#1d4130; border-color:var(--brass); box-shadow:inset 0 -3px 0 var(--brass); }
.office-decision { background:linear-gradient(135deg,#17392a,#10271d); border:1px solid #3a624e; border-top:3px solid var(--brass); border-radius:8px; padding:18px 20px; margin:8px 0 16px; box-shadow:0 10px 28px rgba(0,0,0,.18); }
.office-decision h2 { margin:0 0 5px; }
.office-alert { background:#321814; border:1px solid #9b4436; border-left:5px solid var(--alarm); border-radius:7px; padding:14px 16px; margin:10px 0 16px; }
.office-alert .kicker { color:#e0705d; text-transform:uppercase; letter-spacing:.1em; font-size:.72rem; font-weight:700; }
@media (max-width: 900px) { .block-container { padding-left:1rem; padding-right:1rem; } }

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

def polls_chart(df):
    """Altair line chart in party colours with direct labels instead of a legend."""
    import altair as alt
    labels = [str(i) for i in df.index]
    long = df.copy()
    long.index = labels
    long = long.reset_index(names='Period').melt('Period', var_name='Party', value_name='Share')
    scale = alt.Scale(domain=list(PARTY_COLOURS), range=list(PARTY_COLOURS.values()))
    ymax = max(10, int(long['Share'].max() // 5 * 5 + 10))
    axis_kw = dict(labelColor='#9fb3a6', domainColor='#2b5440', tickColor='#2b5440', title=None)
    x = alt.X('Period:O', sort=labels, axis=alt.Axis(labelAngle=0, grid=False, labelOverlap='parity', **axis_kw))
    y = alt.Y('Share:Q', scale=alt.Scale(domain=[0, ymax]), axis=alt.Axis(gridColor='#1d4130', **axis_kw))
    colour = alt.Color('Party:N', scale=scale, legend=None)
    lines = alt.Chart(long).mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=28)).encode(
        x=x, y=y, color=colour,
        tooltip=[alt.Tooltip('Party:N'), alt.Tooltip('Period:O'), alt.Tooltip('Share:Q', format='.1f')])
    last = long[(long['Period'] == labels[-1]) & (long['Share'] >= 3.5)]
    names = alt.Chart(last).mark_text(align='left', dx=8, fontSize=11, fontWeight='bold').encode(
        x=x, y=y, text='Party:N', color=colour)
    chart = (lines + names).properties(height=260, background='transparent',
                                       padding={'left': 5, 'right': 110, 'top': 10, 'bottom': 5}
                                       ).configure_view(strokeWidth=0)
    st.altair_chart(chart, use_container_width=True)


def render_polls(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest
    top = max(float(latest.max()), 1.0)
    rows = ''
    for party, val in latest.sort_values(ascending=False).items():
        c = PARTY_COLOURS.get(party, '#888')
        d = float(val - prev[party])
        arrow = '' if abs(d) < 0.05 else (f"<span style='color:#6fbf8a'>&#9650;{d:.1f}</span>" if d > 0
                                         else f"<span style='color:#e0705d'>&#9660;{abs(d):.1f}</span>")
        rows += (f"<div class='ch-bar'><div class='name'>{party}</div>"
                 f"<div class='track'><div class='fill' style='width:{val / top * 100:.0f}%;background:{c}'></div></div>"
                 f"<div class='val'>{val:.0f}%</div><div style='width:48px;font-size:.78rem'>{arrow}</div></div>")
    st.markdown(rows, unsafe_allow_html=True)
    if len(df) >= 2:
        try:
            polls_chart(df)
        except Exception:  # never let a chart problem break the game
            plot = df.copy()
            plot.index = [str(i) for i in plot.index]
            st.line_chart(plot, color=[PARTY_COLOURS[c] for c in plot.columns])


def humphrey_message(text, title='Memo from Sir Humphrey Appleby'):
    st.markdown(f"""
    <div style='background-color: #1a221f; border-left: 5px solid #c9a45c; padding: 18px; margin: 15px 0px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <div style='color: #c9a45c; font-family: "Newsreader", serif; font-weight: bold; font-size: 1.2rem; margin-bottom: 8px;'>
            <span style='font-size: 1.4rem; margin-right: 8px;'>&#128188;</span>{title}
        </div>
        <div style='font-style: italic; color: #efe9da; font-size: 1.05rem; line-height: 1.5;'>
            "{text}"
        </div>
    </div>
    """, unsafe_allow_html=True)


PAPERS = [('The Clarion', 'Left', '#e4003b'), ('The Statesman', 'Centre', '#faa61a'), ('Daily Standard', 'Right', '#0087dc')]


def render_newspapers(left_hl, centre_hl, right_hl):
    cards = ''.join(
        f"<div class='np-card' style='border-top-color:{colour}'><div class='np-name'>{name} <span>({lean})</span></div>"
        f"<div class='np-head'>&ldquo;{hl}&rdquo;</div></div>"
        for (name, lean, colour), hl in zip(PAPERS, (left_hl, centre_hl, right_hl)))
    st.markdown(f"<div class='np-strip'>{cards}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- stat cards
def sparkline_svg(series, colour='#c9a45c', w=100, h=22):
    """Tiny inline trend line. Returns '' until there are at least two points."""
    if not series or len(series) < 2:
        return ''
    lo, hi = min(series), max(series)
    span = hi - lo
    n = len(series) - 1
    pts = ' '.join(f"{i / n * w:.1f},{(h / 2 if span == 0 else h - 2 - (v - lo) / span * (h - 4)):.1f}"
                   for i, v in enumerate(series))
    return (f"<svg class='sc-spark' viewBox='0 0 {w} {h}' preserveAspectRatio='none'>"
            f"<polyline points='{pts}' fill='none' stroke='{colour}' stroke-width='1.6' "
            f"vector-effect='non-scaling-stroke' stroke-linejoin='round'/></svg>")


def stat_card(label, value, delta_text, desc, delta_num=0.0, inverse=False, series=None):
    """HTML stat card with a hover tooltip. delta_num sets the colour; inverse=True means lower is better."""
    if abs(delta_num) < 1e-9:
        cls, arrow = 'sc-flat', ''
    else:
        good = (delta_num > 0) != inverse
        cls = 'sc-good' if good else 'sc-bad'
        arrow = '\u25b2 ' if delta_num > 0 else '\u25bc '
    return (f"<div class='sc-card' tabindex='0'>"
            f"<div class='sc-label'><span>{label}</span><span class='sc-info'>i</span></div>"
            f"<div class='sc-value'>{value}</div>"
            f"<span class='sc-delta {cls}'>{arrow}{delta_text}</span>"
            f"{sparkline_svg(series)}"
            f"<div class='sc-tip'>{desc}</div></div>")


def render_cards(defs, per_row=None):
    """Draw a row (or rows) of stat cards from definitions in state.CARDS_*."""
    s = st.session_state
    per_row = per_row or len(defs)
    for i in range(0, len(defs), per_row):
        chunk = defs[i:i + per_row]
        for col, d in zip(st.columns(len(chunk)), chunk):
            key = d['key']
            v = s[key]
            delta = v - s.get('prev', {}).get(key, v)
            flat = abs(delta) < 0.5 * 10 ** -d['dec']
            col.markdown(stat_card(d['label'], d['fmt'].format(v), 'no change' if flat else d['dfmt'].format(delta),
                                   d['desc'], 0.0 if flat else delta, d.get('inverse', False),
                                   s.get('stat_hist', {}).get(key)), unsafe_allow_html=True)


# ---------------------------------------------------------------- event log, event cards, scorecard
def event_card(title, text, summary=''):
    extra = f'<small>{summary}</small>' if summary else ''
    st.markdown(f"<div class='ch-event'>&#128236; <b>{title}</b><br>{text}{extra}</div>", unsafe_allow_html=True)


def render_timeline(entries, pending=()):
    if pending:
        for p in pending:
            st.markdown(f"<div class='tl-soon'>&#9203; <b>On the horizon:</b> {p['title']}</div>", unsafe_allow_html=True)
    if not entries:
        st.caption('Nothing has happened yet. Make your first decision.')
        return
    names = {'approval': 'Approval', 'market_conf': 'Markets', 'headroom': 'Headroom'}
    rows = ''
    for h in reversed(entries):
        chips = ''
        for k, name in names.items():
            v = h['d'].get(k, 0)
            if abs(v) >= 0.05:
                unit = '£' if k == 'headroom' else ''
                suffix = 'B' if k == 'headroom' else ''
                chips += f"<span class='tl-chip {'good' if v > 0 else 'bad'}'>{name} {unit}{v:+.1f}{suffix}</span>"
        tag = f" <span class='tl-when'>&middot; you chose: {h['ideology']}</span>" if h['ideology'] else ''
        choice = f"<div class='tl-choice'>{h['choice']}</div>" if h['choice'] else (f"<div class='tl-choice'>{h['note']}</div>" if h['note'] else '')
        rows += (f"<div class='tl-item'><div class='tl-dot {h['kind']}'></div><div>"
                 f"<div class='tl-when'>Term {h['term']} &middot; Year {h['year']}, block {h['block']}{tag}</div>"
                 f"<div class='tl-title'>{h['title']}</div>{choice}<div>{chips}</div></div></div>")
    st.markdown(rows, unsafe_allow_html=True)


def render_scorecard(data):
    """End-of-term / end-of-run scorecard. ``data`` comes from engine.scorecard()."""
    stats = ''.join(
        f"<div class='sk-stat'><div class='n'>{r['label']}</div><div class='v'>{r['start']} &rarr; {r['end']}</div></div>"
        for r in data['rows'])
    best, worst = data.get('best'), data.get('worst')
    moves = ''
    if best:
        moves += f"<div class='sk-stat'><div class='n'>Best move</div><div class='v'>{best['title']}</div></div>"
    if worst and worst is not best:
        moves += f"<div class='sk-stat'><div class='n'>Worst move</div><div class='v'>{worst['title']}</div></div>"
    badges = ''.join(f"<span class='sk-badge'>&#127941; {n}</span>" for n in data['badges']) or "<span class='tl-when'>None yet</span>"
    new = ''.join(f"<span class='sk-badge' style='background:#3a2f12'>&#10024; New: {n}</span>" for n in data['new_badges'])
    st.markdown(f"""
    <div class='sk-wrap'>
      <div style='display:flex;justify-content:space-between;align-items:center;gap:16px'>
        <div><div class='sk-title'>{data['title']}</div><div class='sk-sub'>{data['subtitle']}</div></div>
        <div style='text-align:center'><div class='sk-grade' style='color:{data['grade_colour']}'>{data['grade']}</div>
        <div class='tl-when'>State of the Nation<br>{data['overall']:.0f}/100</div></div>
      </div>
      <div class='sk-grid'>{stats}{moves}</div>
      <div>{new}{badges}</div>
    </div>""", unsafe_allow_html=True)
