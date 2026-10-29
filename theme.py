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
.stApp { background: radial-gradient(ellipse at 50% -18%, #244a36 0%, var(--bench) 54%); color: var(--paper); }
.block-container { max-width: 1600px; padding-top: .65rem; padding-bottom: 1rem; padding-left: clamp(1rem, 2vw, 2rem); padding-right: clamp(1rem, 2vw, 2rem); }
[data-testid='stVerticalBlock'] { gap: .65rem; }
[data-testid='stHorizontalBlock'] { gap: 1rem; }
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

div[role="radiogroup"] { gap: 0.35rem; }
/* Policy options form a compact two-column grid on desktop. */
@media (min-width: 900px) {
  [data-testid="stRadio"] div[role="radiogroup"] { display: grid !important; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .4rem; }
}
@media (max-width: 899px) {
  .block-container { padding-top: .5rem; }
  .ch-banner h1 { font-size: 1.45rem; }
}
div[role="radiogroup"] > label {
  background: var(--leather);
  border: 1px solid #2b5440;
  border-radius: 6px;
  padding: 8px 10px;
  width: 100%;
  transition: border-color .15s, background .15s;
}
div[role="radiogroup"] > label:hover { border-color: var(--brass); background: var(--leather-2); }
div[role="radiogroup"] > label:has(input:checked) { border-color: var(--brass); background: var(--leather-2); box-shadow: inset 4px 0 0 var(--brass); }
div[role="radiogroup"] > label p { font-size: .9rem; line-height: 1.3; margin-bottom: 0; }

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
  padding: 8px 10px; width: 100%; margin-bottom: 3px; transition: border-color .15s, background .15s;
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
  border-radius: 6px; padding: 8px 10px; margin-bottom: 4px; min-height: 82px; }
.sc-label { display: flex; align-items: center; justify-content: space-between; color: var(--muted); font-size: .85rem; line-height: 1.2; }
.sc-info { display: inline-flex; align-items: center; justify-content: center; width: 16px; height: 16px; flex: none;
  border: 1px solid var(--muted); border-radius: 50%; font-size: .68rem; font-style: normal; cursor: help; color: var(--muted); }
.sc-card:hover .sc-info, .sc-card:focus-within .sc-info { border-color: var(--brass); color: var(--brass); }
.sc-value { font-family: 'Newsreader', serif; font-size: 1.55rem; font-weight: 700; color: var(--paper); line-height: 1.25; margin: 2px 0 6px; }
.sc-delta { display: inline-block; font-size: .8rem; font-weight: 600; padding: 1px 8px; border-radius: 10px; }
.sc-good { color: #6fbf8a; background: rgba(111,191,138,.14); }
.sc-bad  { color: #e0705d; background: rgba(224,112,93,.14); }
.sc-flat { color: var(--muted); background: rgba(159,179,166,.12); }
.sc-spark { display: block; width: 100%; height: 16px; margin-top: 4px; opacity: .9; }
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

.ch-banner { position: relative; overflow: hidden; border: 1px solid #355a45; border-left: 5px solid var(--brass); background: linear-gradient(110deg, rgba(29,65,48,.98), rgba(13,31,23,.97)); padding: 15px 20px 13px; border-radius: 10px; margin: 0 0 12px; box-shadow: 0 8px 24px rgba(0,0,0,.16); }
.ch-banner:after { content: 'TREASURY'; position: absolute; right: 18px; top: 10px; color: rgba(201,164,92,.13); font-family: 'Newsreader', serif; font-size: clamp(2.8rem, 6vw, 5.5rem); font-weight: 700; letter-spacing: .08em; pointer-events: none; }
.ch-banner .eyebrow { color: var(--brass); font-size: .7rem; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; margin-bottom: 3px; }
.ch-banner h1 { position: relative; z-index: 1; margin: 0; font-size: clamp(1.45rem, 2.4vw, 2.05rem); }
.ch-banner .sub { position: relative; z-index: 1; color: #bdcabe; margin-top: 5px; font-size: .88rem; }
.ch-banner .ch-pips { position: relative; z-index: 1; max-width: 760px; }

.setup-hero { position: relative; overflow: hidden; padding: 26px 28px 24px; border: 1px solid #355a45; border-radius: 12px; background: linear-gradient(115deg, #1d4130 0%, #10271c 62%, #0d1f17 100%); box-shadow: 0 12px 30px rgba(0,0,0,.2); margin-bottom: 18px; }
.setup-hero .seal { color: var(--brass); font-size: .72rem; font-weight: 700; letter-spacing: .2em; text-transform: uppercase; }
.setup-hero h1 { margin: 7px 0 8px; font-size: clamp(1.8rem, 4vw, 2.8rem); line-height: 1.05; }
.setup-hero p { max-width: 720px; color: #bdcabe; margin: 0; line-height: 1.55; }
.setup-hero .stamp { display: inline-block; margin-top: 16px; border: 1px solid rgba(201,164,92,.6); border-radius: 4px; padding: 5px 9px; color: var(--brass); font-size: .72rem; letter-spacing: .1em; text-transform: uppercase; }
/* Cabinet Office finish: quiet borders, clear surfaces, consistent controls. */
[data-testid='stSidebar'] { background: linear-gradient(180deg, #10271c, #0b1912); border-right: 1px solid #2b5440; }
[data-testid='stSidebar'] [data-testid='stMarkdownContainer'] h3 { color: var(--brass) !important; }
[data-testid='stTabs'] [role='tablist'] { gap: 5px; border-bottom: 1px solid #2b5440; }
[data-testid='stTabs'] button[role='tab'] { border-radius: 7px 7px 0 0; padding: .55rem .9rem; color: var(--muted) !important; }
[data-testid='stTabs'] button[role='tab'][aria-selected='true'] { color: var(--paper) !important; background: #1a3b2a; border-bottom: 2px solid var(--brass); }
[data-testid='stTextInput'] input, [data-testid='stNumberInput'] input, [data-testid='stTextArea'] textarea { background: #10271c !important; color: var(--paper) !important; border-color: #355a45 !important; border-radius: 7px !important; }
[data-testid='stSelectbox'] [data-baseweb='select'] > div, [data-testid='stMultiSelect'] [data-baseweb='select'] > div { border-radius: 7px !important; }
[data-testid='stAlert'] { border-radius: 8px; }
hr { border-color: #2b5440 !important; }
/* Annual programme indicator: three clear phases instead of Streamlit's oversized default bar. */
.annual-progress { background: rgba(22,51,38,.72); border: 1px solid #2b5440; border-radius: 8px; padding: 9px 12px 10px; margin: 3px 0 8px; }
.annual-progress-heading { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; font-size: .78rem; color: var(--muted); line-height: 1.25; }
.annual-progress-heading > span:first-child { color: var(--paper); font-weight: 600; }
.annual-phase { color: var(--brass); font-weight: 600; }
.annual-phase-name { color: var(--muted); font-weight: 400; }
.annual-track { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 5px; margin-top: 8px; }
.annual-segment { height: 5px; border-radius: 99px; background: #294536; }
.annual-segment.complete { background: #c9a45c; }
.annual-segment.current { background: linear-gradient(90deg, #c9a45c, #efe9da); box-shadow: 0 0 0 1px rgba(201,164,92,.28); }
@media (max-width: 650px) { .annual-progress { padding: 8px 10px; } .annual-phase-name { display: none; } }
.stButton > button, [data-testid='stDownloadButton'] button { min-height: 2.5rem; border-radius: 7px; transition: transform .15s ease, box-shadow .15s ease, background .15s ease; }
.stButton > button:hover, [data-testid='stDownloadButton'] button:hover { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(0,0,0,.18); }
[data-testid='stMetric'] { border-radius: 9px; box-shadow: 0 4px 14px rgba(0,0,0,.1); }
[data-testid='stExpander'] { border-radius: 9px; }
@media (max-width: 650px) { .ch-banner { padding: 12px 14px; } .ch-banner:after { right: 8px; top: 15px; font-size: 2rem; } .ch-banner .sub { max-width: 80%; font-size: .78rem; } }
.ch-pips { display: flex; gap: 4px; margin-top: 8px; }
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

/* ================= COMPACT LAYOUT: see more, scroll less ================= */
.block-container { padding-top: 3rem !important; padding-bottom: 1rem !important; }
[data-testid='stVerticalBlock'] { gap: .55rem; }

/* one slim banner line (the TREASURY watermark stays, but no longer sets the height) */
.ch-banner { padding: 8px 16px 9px !important; margin-bottom: 2px !important; }
.ch-banner:after { font-size: clamp(1.6rem, 3.2vw, 2.6rem) !important; top: 6px !important; }
.ch-banner .eyebrow { display: none; }
.ch-head { position: relative; z-index: 1; display: flex; flex-wrap: wrap; align-items: baseline; gap: 0 18px; }
.ch-title { font-family: 'Newsreader', serif; font-size: 1.4rem; font-weight: 700; color: var(--paper); }
.ch-banner .sub { margin-top: 0 !important; font-size: .78rem !important; letter-spacing: .07em; }
.ch-banner .ch-pips { margin-top: 6px !important; gap: 3px !important; max-width: 420px !important; }
.ch-pip { height: 4px !important; }
@media (max-width: 650px) { .ch-banner:after { display: none !important; } }

/* the dashboard strip: every headline number in two thin rows, always visible */
.hud { display: flex; flex-direction: column; gap: 2px; margin: 6px 0 10px; }
.hud-title { color: var(--brass); font-size: .64rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; margin: 2px 0 1px 2px; }
.hud-row { display: grid; grid-template-columns: repeat(9, minmax(0, 1fr)); gap: 6px; }
.hud-note { grid-column: span 4; display: flex; flex-wrap: wrap; align-items: center; gap: 2px 16px; padding: 4px 12px;
  border: 1px dashed #2b5440; border-radius: 6px; color: var(--muted); font-size: .8rem; line-height: 1.3; }
.hud-note b { color: var(--paper); }
@media (max-width: 1300px) { .hud-row { grid-template-columns: repeat(5, minmax(0, 1fr)); } .hud-note { grid-column: 1 / -1; } }
@media (max-width: 760px) { .hud-row { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
.chip-row { display: grid; grid-template-columns: repeat(9, minmax(0, 1fr)); gap: 6px; margin: 2px 0 4px; }
@media (max-width: 1300px) { .chip-row { grid-template-columns: repeat(5, minmax(0, 1fr)); } }
@media (max-width: 760px) { .chip-row { grid-template-columns: repeat(3, minmax(0, 1fr)); } }

/* compact stat card: label on top, value and change on one line */
.sc-card.compact { min-height: 0; padding: 5px 9px 6px; margin: 0; border-top-width: 2px; cursor: help; }
.sc-card.compact .sc-label { font-size: .68rem; line-height: 1.15; display: block; }
.sc-card.compact .sc-row { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 0 6px; }
.sc-card.compact .sc-value { font-size: 1.25rem; line-height: 1.2; margin: 0; }
.sc-card.compact .sc-delta { font-size: .66rem; padding: 0 6px; }
.sc-card.compact .sc-tip { left: 0; right: auto; width: 230px; }
.hud-row .sc-card.compact:nth-child(n+6) .sc-tip, .chip-row .sc-card.compact:nth-child(n+6) .sc-tip { left: auto; right: 0; }

/* Budget screen: one line per slider */
.lv { font-size: .86rem; line-height: 1.2; padding-top: .45rem; }
.lv small { color: var(--muted); }
.lv-val { text-align: right; font-size: .98rem; line-height: 1.15; padding-top: .15rem; }
.lv-val span { font-size: .76rem; }

/* manifesto pledge chips */
.pl-row { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; font-size: .8rem; margin: 0; }
.pl { border-radius: 12px; padding: 1px 10px; border: 1px solid; }
.pl-ok { color: #6fbf8a; border-color: #2b5440; background: rgba(111,191,138,.10); }
.pl-risk { color: #e6b14a; border-color: #8a6a22; background: rgba(230,177,74,.12); }
.pl-broken { color: #e0705d; border-color: #7a2f25; background: rgba(224,112,93,.12); text-decoration: line-through; }

/* decision card */
.dc-eyebrow { color: var(--brass); font-size: .68rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.dc-title { font-family: 'Newsreader', serif; font-size: 1.55rem; font-weight: 700; line-height: 1.15; margin: 1px 0 4px; color: var(--paper); }
.pane-title { color: var(--brass); font-size: .68rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; margin: 0 0 2px; }

/* controls: the radio's own heading is no longer drawn as if it were an option */
[data-testid="stRadio"] [data-testid="stWidgetLabel"] { background: none !important; border: 0 !important; box-shadow: none !important; padding: 0 !important; margin: 0 0 2px !important; width: auto !important; }
[data-testid="stExpander"] summary p { font-size: .95rem !important; }
[data-testid="stExpander"] summary { padding: .4rem .8rem !important; }
div.stButton > button { padding: .4rem 1.1rem; }

/* tighter polls, papers, memos, feedback */
.ch-bar { margin: 4px 0; gap: 10px; }
.ch-bar .name { width: 125px; font-size: .9rem; }
.ch-bar .track { height: 14px; }
.np-strip { margin: 6px 0; gap: 8px; }
.np-card { padding: 9px 10px; }
.np-name { font-size: .9rem; margin-bottom: 6px; padding-bottom: 3px; }
.np-head { font-size: .88rem; line-height: 1.25; }
.ch-news { margin-bottom: 4px; padding: 8px 14px; }
.ch-event { margin: 4px 0; padding: 8px 14px; }

/* Focused, less cluttered workspace */
.block-container {
  max-width: 1540px;
  padding-top: 1.25rem !important;
  padding-bottom: .8rem !important;
  padding-left: clamp(.8rem, 1.5vw, 1.5rem) !important;
  padding-right: clamp(.8rem, 1.5vw, 1.5rem) !important;
}
[data-testid='stVerticalBlock'] { gap: .45rem !important; }
[data-testid='stHorizontalBlock'] { gap: .75rem !important; }
[data-testid='stTabs'] [role='tablist'] {
  gap: .25rem;
  border-bottom: 1px solid #2b5440;
  margin-bottom: .25rem;
}
[data-testid='stTabs'] button[role='tab'] {
  padding: .45rem .8rem !important;
  min-height: 2.4rem;
}
[data-testid='stTabs'] [data-baseweb='tab-panel'] { padding-top: .65rem !important; }
[data-testid='stMetric'] {
  padding: 7px 10px 8px !important;
  margin-bottom: 0 !important;
}
[data-testid='stMetricValue'] { font-size: clamp(1.25rem, 1.7vw, 1.65rem) !important; }
.sc-card { min-height: 68px; padding: 7px 9px; margin-bottom: 0; }
.sc-value { font-size: clamp(1.25rem, 1.7vw, 1.5rem); margin: 2px 0 4px; }
.ch-banner { margin-bottom: 8px !important; }
.dc-title { margin: .15rem 0 .35rem !important; line-height: 1.15 !important; }
.dc-eyebrow { margin-bottom: .15rem !important; }
[data-testid='stRadio'] div[role='radiogroup'] { gap: .45rem !important; }
div[role='radiogroup'] > label,
[data-testid='stRadio'] label {
  padding: 8px 10px !important;
  margin-bottom: 0 !important;
}
[data-testid='stRadio'] label p { font-size: .9rem !important; line-height: 1.28 !important; }
[data-testid='stButton'] button { min-height: 2.45rem; padding: .45rem 1rem !important; }
[data-testid='stDataFrame'] { margin-top: .2rem; }
[data-testid='stAlert'] { padding: .65rem .85rem; }
h1, h2, h3 { line-height: 1.15 !important; }
hr { margin: .6rem 0 !important; }
@media (max-width: 900px) {
  .block-container { padding-top: .7rem !important; }
  [data-testid='stTabs'] [role='tablist'] { flex-wrap: wrap; }
  [data-testid='stTabs'] button[role='tab'] { padding: .35rem .5rem !important; }
}


/* Budget action row: consistent widths, no touching or overlapping buttons */
[data-testid="stHorizontalBlock"]:has([data-testid="stButton"] button) { align-items: stretch; }
[data-testid="stButton"] button {
  white-space: normal !important;
  line-height: 1.25 !important;
  min-height: 2.65rem !important;
  padding: .55rem .85rem !important;
  margin: .12rem 0 .3rem !important;
  width: 100%;
}
[data-testid="stTabs"] [role="tablist"] { flex-wrap: wrap; row-gap: .25rem; }
[data-testid="stTabs"] button[role="tab"] { white-space: normal; line-height: 1.2; }


/* Final colour and spacing overrides — keep all controls inside the Treasury palette. */
:root {
  --bench: #0d1f17;
  --leather: #163326;
  --leather-2: #1d4130;
  --brass: #c9a45c;
  --paper: #efe9da;
  --muted: #9fb3a6;
  --alarm: #c8412f;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div,
[data-testid="stNumberInput"] input,
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input {
  background: #10271c !important;
  background-color: #10271c !important;
  color: #efe9da !important;
  border: 1px solid #355a45 !important;
  border-radius: 7px !important;
  -webkit-text-fill-color: #efe9da !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] *,
[data-testid="stMultiSelect"] [data-baseweb="select"] * {
  color: #efe9da !important;
  -webkit-text-fill-color: #efe9da !important;
}
[data-baseweb="popover"], [data-baseweb="menu"], [role="listbox"],
[data-baseweb="popover"] ul, [data-baseweb="popover"] li,
[data-baseweb="menu"] ul, [data-baseweb="menu"] li,
[role="option"] {
  background: #10271c !important;
  color: #efe9da !important;
}
[role="option"]:hover, [aria-selected="true"][role="option"] {
  background: #1d4130 !important;
  color: #efe9da !important;
}
[data-testid="stNumberInput"] button {
  background: #1d4130 !important;
  color: #efe9da !important;
  border-color: #355a45 !important;
}
[data-testid="stButton"] button,
[data-testid="stDownloadButton"] button {
  box-sizing: border-box !important;
  min-height: 2.6rem !important;
  padding: .55rem .8rem !important;
  margin: 0 !important;
  white-space: normal !important;
  overflow-wrap: anywhere;
  line-height: 1.25 !important;
  text-align: center !important;
  background: #163326 !important;
  color: #efe9da !important;
  border: 1px solid #c9a45c !important;
  border-radius: 7px !important;
  box-shadow: none !important;
}
[data-testid="stButton"] button:hover,
[data-testid="stDownloadButton"] button:hover {
  background: #c9a45c !important;
  color: #0d1f17 !important;
  border-color: #e0bd70 !important;
}
[data-testid="stButton"] button[kind="primary"],
[data-testid="stDownloadButton"] button[kind="primary"] {
  background: #c9a45c !important;
  color: #0d1f17 !important;
  border-color: #c9a45c !important;
}
[data-testid="stButton"] button[kind="primary"]:hover {
  background: #e0bd70 !important;
}
[data-testid="stButton"] button:disabled,
[data-testid="stDownloadButton"] button:disabled {
  background: #20372b !important;
  color: #83998b !important;
  -webkit-text-fill-color: #83998b !important;
  border-color: #2b5440 !important;
  opacity: 1 !important;
  cursor: not-allowed !important;
}
[data-testid="stButton"] button[kind="primary"]:disabled {
  background: #796744 !important;
  color: #e4d7b8 !important;
  border-color: #796744 !important;
}
[data-testid="stTabs"] [role="tablist"] {
  display: flex !important;
  flex-wrap: wrap !important;
  gap: .4rem !important;
  align-items: stretch !important;
  border-bottom: 1px solid #2b5440 !important;
}
[data-testid="stTabs"] button[role="tab"] {
  flex: 0 1 auto !important;
  min-height: 2.5rem !important;
  padding: .5rem .85rem !important;
  background: #10271c !important;
  border: 1px solid #2b5440 !important;
  border-radius: 7px 7px 0 0 !important;
  color: #bdcabe !important;
  white-space: normal !important;
  line-height: 1.2 !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
  background: #1d4130 !important;
  color: #efe9da !important;
  border-color: #c9a45c !important;
  border-bottom: 3px solid #c9a45c !important;
}
.st-key-budget_actions { margin-top: .2rem !important; width: 100% !important; }
.st-key-budget_actions [data-testid="stHorizontalBlock"] {
  display: flex !important;
  flex-direction: row !important;
  gap: .8rem !important;
  width: 100% !important;
  align-items: stretch !important;
}
.st-key-budget_actions [data-testid="column"] {
  width: calc(50% - .4rem) !important;
  min-width: 0 !important;
  flex: 1 1 0% !important;
}
.st-key-budget_actions [data-testid="stButton"] { width: 100% !important; }
.st-key-budget_actions [data-testid="stButton"] button {
  width: 100% !important;
  min-height: 2.8rem !important;
  white-space: normal !important;
  overflow-wrap: normal !important;
  word-break: normal !important;
  padding: .65rem 1rem !important;
}
[data-testid="stRadio"] [data-testid="stWidgetLabel"] {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}
[data-testid="stRadio"] div[role="radiogroup"] { gap: .5rem !important; }
@media (max-width: 760px) {
  .st-key-budget_actions [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    gap: .45rem !important;
  }
  .st-key-budget_actions [data-testid="column"] {
    width: 100% !important;
    min-width: 100% !important;
  }
  [data-testid="stTabs"] [role="tablist"] { gap: .25rem !important; }
  [data-testid="stTabs"] button[role="tab"] { padding: .4rem .55rem !important; }
}


/* Keep general radio choices responsive; only policy cards use a forced two-column grid. */
[data-testid="stRadio"] div[role="radiogroup"] {
  display: flex !important;
  flex-flow: row wrap !important;
  gap: .45rem !important;
}
[data-testid="stRadio"] div[role="radiogroup"] > label {
  flex: 1 1 190px !important;
  width: auto !important;
  min-width: 0 !important;
  margin: 0 !important;
}
.st-key-policy_options div[role="radiogroup"] {
  display: grid !important;
  grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  gap: .5rem !important;
}
.st-key-policy_options div[role="radiogroup"] > label {
  width: 100% !important;
  min-width: 0 !important;
}
@media (max-width: 620px) {
  .st-key-policy_options div[role="radiogroup"] {
    grid-template-columns: minmax(0, 1fr) !important;
  }
}


[data-testid="stMultiSelect"] [data-baseweb="tag"] {
  background: #1d4130 !important;
  color: #efe9da !important;
  border: 1px solid #355a45 !important;
}
[data-testid="stMultiSelect"] [data-baseweb="tag"] * {
  color: #efe9da !important;
  -webkit-text-fill-color: #efe9da !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div:focus-within,
[data-testid="stNumberInput"] input:focus,
[data-testid="stTextInput"] input:focus {
  outline: 2px solid #c9a45c !important;
  outline-offset: 1px;
}


[data-testid="stCheckbox"] input[type="checkbox"],
[data-testid="stRadio"] input[type="radio"] {
  accent-color: #c9a45c !important;
}
[data-testid="stCheckbox"] [role="checkbox"] {
  background: #10271c !important;
  border-color: #c9a45c !important;
}
[data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"] {
  background: #c9a45c !important;
  border-color: #c9a45c !important;
}
[data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"] svg {
  color: #0d1f17 !important;
  fill: #0d1f17 !important;
}


/* Real spacing for nested fiscal-tool tabs and collapsed Budget sections. */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: stretch !important;
  gap: .55rem !important;
  padding: .25rem .1rem .55rem !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"] {
  flex: 0 1 auto !important;
  min-width: max-content !important;
  min-height: 2.55rem !important;
  padding: .55rem .9rem !important;
  margin: 0 .1rem .15rem 0 !important;
  border-radius: 7px 7px 0 0 !important;
  line-height: 1.25 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
  padding-top: .8rem !important;
}
[data-testid="stExpander"] > details > summary {
  min-height: 2.8rem !important;
  padding: .65rem .9rem !important;
}
[data-testid="stExpander"] > details > summary p {
  line-height: 1.25 !important;
}
[data-testid="stCaptionContainer"] p {
  line-height: 1.3 !important;
  margin-bottom: .15rem !important;
}
@media (max-width: 760px) {
  [data-testid="stTabs"] [data-baseweb="tab-list"] { gap: .3rem !important; }
  [data-testid="stTabs"] button[data-baseweb="tab"] {
    min-width: 0 !important;
    padding: .45rem .6rem !important;
    white-space: normal !important;
  }
}


/* Global rhythm: keep captions, cards and sections from visually colliding. */
[data-testid="stVerticalBlock"] { gap: .8rem !important; }
[data-testid="stHorizontalBlock"] { gap: .85rem !important; }
[data-testid="stTabs"] [data-baseweb="tab-panel"] { padding-top: .9rem !important; }
[data-testid="stExpander"] > details > summary { margin-bottom: .15rem !important; }
[data-testid="stCaptionContainer"] { margin-top: .1rem !important; margin-bottom: .25rem !important; }
[data-testid="stMetric"] { margin-top: .15rem !important; margin-bottom: .2rem !important; }
@media (max-width: 760px) {
  [data-testid="stVerticalBlock"] { gap: .65rem !important; }
  [data-testid="stHorizontalBlock"] { gap: .6rem !important; }
}


.fiscal-section-gap { height: .45rem; width: 100%; }
.st-key-budget_actions [data-testid="stButton"] button {
  max-width: 100% !important;
  text-overflow: clip !important;
}

</style>
"""

def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)

PHASES = {
    1: dict(name='Autumn agenda', title='Autumn · Set the agenda',
            guide='Choose the policy direction for the year. This is where you set priorities and signal your governing style.'),
    2: dict(name='Winter pressure', title='Winter · Handle the pressure',
            guide='Take a second major decision while managing crises, ministerial requests and political consequences.'),
    3: dict(name='Spring Budget', title='Spring · Budget and Parliament',
            guide='Set tax and spending, check the OBR forecast, manage your MPs and submit the Budget for a Commons vote.'),
}

def phase_info(block):
    return PHASES.get(int(block), PHASES[1])

def header(party, term, year, block):
    election_night = int(year) > 5
    phase = (dict(name='General election', title='General election night',
                  guide='Your five-year term is complete. The electorate decides whether you stay in government.')
             if election_night else phase_info(block))
    done = 15 if election_night else (year - 1) * 3 + (block - 1)
    pips = ''.join(
        f"<div class='ch-pip {'done' if i < done else ('now' if i == done else '')}'></div>"
        for i in range(15)
    )
    colour = PARTY_COLOURS.get(party, '#c9a45c')
    period = (f"TERM {term} &nbsp;·&nbsp; GENERAL ELECTION" if election_night else
              f"TERM {term} &nbsp;·&nbsp; YEAR {min(year, 5)} OF 5 &nbsp;·&nbsp; {phase['name'].upper()} &nbsp;·&nbsp; PHASE {block} OF 3")
    st.markdown(
        f"""<div class='ch-banner' style='border-left-color:{colour}'>
        <div class='ch-head'><span class='ch-title'>🏛️ {party} Government</span>
        <span class='sub'>{period}</span></div>
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

def polls_chart(df, height=260):
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
    chart = (lines + names).properties(height=height, background='transparent',
                                       padding={'left': 5, 'right': 110, 'top': 10, 'bottom': 5}
                                       ).configure_view(strokeWidth=0)
    st.altair_chart(chart, use_container_width=True)


def render_polls(df, chart_height=185, chart_in_expander=False):
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
        def draw():
            try:
                polls_chart(df, chart_height)
            except Exception:  # never let a chart problem break the game
                plot = df.copy()
                plot.index = [str(i) for i in plot.index]
                st.line_chart(plot, color=[PARTY_COLOURS[c] for c in plot.columns])
        if chart_in_expander:
            with st.expander('📈 Poll history', expanded=False):
                draw()
        else:
            draw()


def humphrey_message(text, title='Memo from Sir Humphrey Appleby'):
    st.markdown(f"""
    <div style='background-color: #1a221f; border-left: 5px solid #c9a45c; padding: 10px 14px; margin: 4px 0px; border-radius: 6px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
        <div style='color: #c9a45c; font-family: "Newsreader", serif; font-weight: bold; font-size: 1rem; margin-bottom: 3px;'>
            <span style='font-size: 1.15rem; margin-right: 6px;'>&#128188;</span>{title}
        </div>
        <div style='font-style: italic; color: #efe9da; font-size: .95rem; line-height: 1.4;'>
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


def stat_card(label, value, delta_text, desc, delta_num=0.0, inverse=False, series=None, compact=False):
    """HTML stat card with a hover tooltip. delta_num sets the colour; inverse=True means lower is better.
    compact=True is the small version used in the dashboard strip and Budget summary (value and change share a line)."""
    if abs(delta_num) < 1e-9:
        cls, arrow = 'sc-flat', ''
    else:
        good = (delta_num > 0) != inverse
        cls = 'sc-good' if good else 'sc-bad'
        arrow = '\u25b2 ' if delta_num > 0 else '\u25bc '
    tip = f"<div class='sc-tip'>{desc}</div>" if desc else ''
    if compact:
        return (f"<div class='sc-card compact' tabindex='0'><span class='sc-label'>{label}</span>"
                f"<div class='sc-row'><span class='sc-value'>{value}</span>"
                f"<span class='sc-delta {cls}'>{arrow}{delta_text}</span></div>{tip}</div>")
    return (f"<div class='sc-card' tabindex='0'>"
            f"<div class='sc-label'><span>{label}</span><span class='sc-info'>i</span></div>"
            f"<div class='sc-value'>{value}</div>"
            f"<span class='sc-delta {cls}'>{arrow}{delta_text}</span>"
            f"{sparkline_svg(series)}"
            f"<div class='sc-tip'>{desc}</div></div>")


def _card_html(d, compact=False):
    s = st.session_state
    key = d['key']
    v = s[key]
    delta = v - s.get('prev', {}).get(key, v)
    flat = round(delta, d['dec']) == 0        # anything that would print as +0 / -0 counts as no change
    text = ('\u2014' if compact else 'no change') if flat else d['dfmt'].format(delta)
    return stat_card(d['label'], d['fmt'].format(v), text, d['desc'], 0.0 if flat else delta,
                     d.get('inverse', False), s.get('stat_hist', {}).get(key), compact=compact)


def render_cards(defs, per_row=None):
    """Draw a row (or rows) of full-size stat cards (with sparklines) from definitions in state.CARDS_*."""
    per_row = per_row or len(defs)
    for i in range(0, len(defs), per_row):
        chunk = defs[i:i + per_row]
        for col, d in zip(st.columns(len(chunk)), chunk):
            col.markdown(_card_html(d), unsafe_allow_html=True)


def render_hud(groups, note=''):
    """The dashboard strip: ``groups`` is a list of (title, card definitions), one thin row each. ``note`` (HTML) fills the
    spare cells at the end of the last row. One markdown call, so it costs one element, not twenty."""
    rows = []
    for i, (title, defs) in enumerate(groups):
        cards = ''.join(_card_html(d, compact=True) for d in defs)
        extra = f"<div class='hud-note'>{note}</div>" if (note and i == len(groups) - 1) else ''
        head = f"<div class='hud-title'>{title}</div>" if title else ''
        rows.append(f"{head}<div class='hud-row'>{cards}{extra}</div>")
    st.markdown(f"<div class='hud'>{''.join(rows)}</div>", unsafe_allow_html=True)


def render_chips(items):
    """A row of compact summary cards. Each item: label, value, delta (text), num (colour), inverse, desc."""
    html = ''.join(stat_card(i['label'], i['value'], i.get('delta', '\u2014'), i.get('desc', ''),
                             i.get('num', 0.0), i.get('inverse', False), compact=True) for i in items)
    st.markdown(f"<div class='chip-row'>{html}</div>", unsafe_allow_html=True)


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
                 f"<div class='tl-when'>Term {h['term']} &middot; Year {h['year']} &middot; {phase_info(h.get('block', 1))['name']}{tag}</div>"
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
