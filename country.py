import random
import streamlit as st

from theme import sparkline_svg

# How strongly the state of the nation feeds back into public approval each turn.
APPROVAL_FEEDBACK = 20

# label, start value, bar range (lo..hi), higher_is_better, display format, decimals, and the tooltip description
STATS = {
    'nhs_waiting':   dict(label='NHS waiting list', start=7.4, lo=4.0, hi=10.0, hib=False, fmt='{:.2f}m', dec=2, desc='Total patients waiting for routine hospital treatment. Major driver of public approval.'),
    'nhs_morale':    dict(label='NHS staff morale', start=52, lo=0, hi=100, hib=True, fmt='{:.0f}/100', dec=0, desc='Satisfaction of healthcare workers. Low morale increases the risk of crippling strikes.'),
    'child_poverty': dict(label='Child poverty', start=31.0, lo=15.0, hi=40.0, hib=False, fmt='{:.1f}%', dec=1, desc='Percentage of children living in relative low-income households. High levels cause left-wing backbench revolts.'),
    'homes_built':   dict(label='New homes built', start=215, lo=100, hi=350, hib=True, fmt='{:.0f}k / yr', dec=0, desc='Annual housing completions. Drives economic growth and slowly helps lower the house price ratio.'),
    'house_ratio':   dict(label='House price to income', start=8.3, lo=5.0, hi=11.0, hib=False, fmt='{:.1f}x', dec=1, desc='Affordability of housing. High ratios anger younger voters and drag down public approval.'),
    'homeless':      dict(label='Households in temp housing', start=126, lo=60, hi=200, hib=False, fmt='{:.0f}k', dec=0, desc='Families living in temporary accommodation. Driven by welfare cuts and lack of housing supply.'),
    'unemployment':  dict(label='Unemployment', start=4.3, lo=3.0, hi=8.0, hib=False, fmt='{:.1f}%', dec=1, desc='Percentage of the workforce without jobs. High unemployment drags down growth and approval.'),
    'real_wages':    dict(label='Real wage growth', start=0.6, lo=-3.0, hi=3.0, hib=True, fmt='{:+.1f}%', dec=1, desc='Wage growth adjusted for inflation. The single most important metric for the voter "cost of living" feel factor.'),
    'energy_bills':  dict(label='Average energy bill', start=1750, lo=1200, hi=2500, hib=False, fmt='£{:,.0f}', dec=0, desc='Annual household energy costs. Spikes lead to massive drops in approval and higher inflation.'),
    'rail':          dict(label='Rail punctuality', start=82, lo=60, hi=95, hib=True, fmt='{:.0f}%', dec=0, desc='Reliability of the train network. Poor performance causes regional outrage and dents approval.'),
    'schools':       dict(label='School standards', start=62, lo=30, hi=90, hib=True, fmt='{:.0f}/100', dec=0, desc='Quality of the education system. Underfunding leads to crumbling classrooms and facility crises.'),
    'prisons':       dict(label='Prison capacity used', start=98, lo=80, hi=115, hib=False, fmt='{:.0f}%', dec=0, desc='Overcrowding in the justice system. Hitting >100% causes major scandals and early release programs.'),
    'netzero':       dict(label='Net zero progress', start=38, lo=0, hi=100, hib=True, fmt='{:.0f}%', dec=0, desc='Progress towards decarbonisation. Important for green trade pacts and avoiding climate crises.'),
}

GROUPS = [
    ('🏥 Health & Welfare', ['nhs_waiting', 'nhs_morale', 'child_poverty']),
    ('🏠 Housing', ['homes_built', 'house_ratio', 'homeless']),
    ('💼 Jobs & Living Costs', ['unemployment', 'real_wages', 'energy_bills']),
    ('🏛️ Public Services & Climate', ['rail', 'schools', 'prisons', 'netzero']),
]

PROFILES = {
    'Hard Left': dict(nhs_waiting=-0.35, nhs_morale=6, child_poverty=-1.5, homes_built=12, house_ratio=-0.15, homeless=-6,
                      unemployment=0.15, real_wages=0.4, energy_bills=-60, rail=3, schools=3, prisons=0, netzero=2),
    'Social Democratic': dict(nhs_waiting=-0.30, nhs_morale=5, child_poverty=-1.2, homes_built=9, house_ratio=-0.10, homeless=-4,
                              unemployment=-0.05, real_wages=0.3, energy_bills=-45, rail=2.5, schools=3, prisons=-1, netzero=3),
    'Centric': dict(nhs_waiting=-0.15, nhs_morale=1.5, child_poverty=-0.4, homes_built=5, house_ratio=-0.05, homeless=-1.5,
                    unemployment=0, real_wages=0.15, energy_bills=-18, rail=1, schools=1.5, prisons=-0.5, netzero=1),
    'Free-Market': dict(nhs_waiting=0.0, nhs_morale=-3, child_poverty=0.6, homes_built=9, house_ratio=-0.08, homeless=2,
                        unemployment=-0.15, real_wages=0.2, energy_bills=0, rail=0.5, schools=-0.5, prisons=0.5, netzero=-2),
    'Fiscal Austerity': dict(nhs_waiting=0.4, nhs_morale=-7, child_poverty=1.5, homes_built=-6, house_ratio=0.05, homeless=6,
                             unemployment=0.2, real_wages=-0.3, energy_bills=30, rail=-3, schools=-4, prisons=2.5, netzero=-2),
}

TOPICS = {
    (1, 1): ['nhs_waiting', 'nhs_morale', 'prisons'],
    (1, 2): ['nhs_morale', 'real_wages', 'unemployment', 'schools'],
    (1, 3): ['unemployment', 'real_wages', 'netzero'],
    (2, 1): ['child_poverty', 'unemployment', 'homeless', 'nhs_waiting'],
    (2, 2): ['unemployment', 'real_wages', 'house_ratio'],
    (2, 3): ['homeless', 'schools', 'prisons', 'homes_built'],
    (3, 1): ['rail', 'netzero', 'unemployment'],
    (3, 2): ['homes_built', 'house_ratio', 'homeless'],
    (3, 3): ['energy_bills', 'netzero', 'real_wages'],
    (4, 1): ['energy_bills', 'netzero', 'child_poverty'],
    (4, 2): ['real_wages', 'unemployment', 'energy_bills'],
    (4, 3): ['unemployment', 'child_poverty', 'real_wages'],
    (5, 1): ['nhs_waiting', 'nhs_morale'],
    (5, 2): ['child_poverty', 'real_wages', 'homeless'],
    (5, 3): None,
}

CRISIS_EFFECTS = {
    'National Health Service': {'nhs_morale': (8, -10), 'nhs_waiting': (-0.1, 0.4)},
    'Energy Retailer': {'energy_bills': (-40, 120)},
    'Pension': {'schools': (1, -3), 'nhs_morale': (1, -3)},
    'Capital Flight': {'unemployment': (0, 0.3), 'real_wages': (0, -0.2)},
    'Private Utility Failure': {'energy_bills': (-20, 60), 'netzero': (0, -2)},
    'Public Service Collapse': {'schools': (4, -5), 'prisons': (-3, 4)},
}

def _clamp(key, value):
    s = STATS[key]
    return max(s['lo'], min(s['hi'], value))

def _score(key, value):
    s = STATS[key]
    x = (value - s['lo']) / (s['hi'] - s['lo'])
    x = max(0.0, min(1.0, x))
    return x if s['hib'] else 1 - x

def _overall(state):
    return sum(_score(k, v) for k, v in state.items()) / len(state)

def ensure_state():
    if 'country' not in st.session_state:
        st.session_state.country = {k: s['start'] for k, s in STATS.items()}
        st.session_state.country_prev = dict(st.session_state.country)

def apply_decision(ideology):
    ensure_state()
    state = st.session_state.country
    before = _overall(state)
    st.session_state.country_prev = dict(state)

    profile = PROFILES.get(ideology, PROFILES['Centric'])
    primary = TOPICS.get((st.session_state.year, st.session_state.block))
    for key, base in profile.items():
        weight = 0.7 if primary is None else (1.0 if key in primary else 0.3)
        state[key] = _clamp(key, state[key] + base * weight * random.uniform(0.85, 1.15))

    if APPROVAL_FEEDBACK:
        bump = max(-3, min(3, (_overall(state) - before) * APPROVAL_FEEDBACK))
        st.session_state.approval = round(st.session_state.approval + bump, 1)

def nudge(effects, snapshot=True):
    ensure_state()
    state = st.session_state.country
    if snapshot:
        st.session_state.country_prev = dict(state)
    for key, delta in effects.items():
        if key in state:
            state[key] = _clamp(key, state[key] + delta)

CSS = """
<style>
.cs-grade { display:flex; align-items:center; gap:18px; background:var(--leather,#163326); border:1px solid #2b5440;
  border-left:6px solid var(--brass,#c9a45c); border-radius:6px; padding:14px 20px; margin-bottom:10px; }
.cs-grade .letter { font-family:'Newsreader',serif; font-size:2.6rem; font-weight:700; line-height:1; }
.cs-grade .txt { color:var(--muted,#9fb3a6); }
.cs-card { background:var(--leather,#163326); border:1px solid #2b5440; border-radius:6px; padding:12px 14px; margin-bottom:8px; position: relative; }
.cs-label { color:var(--muted,#9fb3a6); font-size:.82rem; display: flex; align-items: center; justify-content: space-between; }
.cs-icon { font-size: 1rem; color: #c9a45c; cursor: help; }
.cs-value { font-family:'Newsreader',serif; font-size:1.5rem; font-weight:700; line-height:1.2; margin:2px 0 8px; }
.cs-delta { font-family:'IBM Plex Sans',sans-serif; font-size:.78rem; font-weight:600; margin-left:6px; }
.cs-good { color:#6fbf8a; } .cs-bad { color:#e0705d; } .cs-flat { color:#9fb3a6; }
.cs-track { background:#10281d; border-radius:4px; height:7px; overflow:hidden; }
.cs-fill { height:100%; border-radius:4px; }

/* Custom Tooltip Styling */
.cs-card .tooltiptext {
  visibility: hidden;
  width: 90%;
  background-color: #1a221f;
  color: #efe9da;
  text-align: left;
  border-radius: 6px;
  padding: 10px;
  border: 1px solid #c9a45c;
  position: absolute;
  z-index: 999;
  top: 105%;
  left: 5%;
  opacity: 0;
  transition: opacity 0.2s;
  font-family: 'IBM Plex Sans', sans-serif;
  font-size: 0.85rem;
  font-weight: 400;
  line-height: 1.4;
  box-shadow: 0 4px 8px rgba(0,0,0,0.5);
  pointer-events: none;
}
.cs-card:hover .tooltiptext {
  visibility: visible;
  opacity: 1;
}
</style>
"""

def _card(key, state, prev, series=None):
    s = STATS[key]
    v, p = state[key], prev.get(key, state[key])
    d = v - p
    colour = '#6fbf8a' if _score(key, v) >= 0.6 else ('#d9b45a' if _score(key, v) >= 0.4 else '#d6604f')
    if abs(d) < 0.5 * 10 ** -s['dec']:
        delta = "<span class='cs-delta cs-flat'>no change</span>"
    else:
        good = (d > 0) == s['hib']
        arrow = '▲' if d > 0 else '▼'
        delta = f"<span class='cs-delta {'cs-good' if good else 'cs-bad'}'>{arrow} {d:+.{s['dec']}f}</span>"
    width = _score(key, v) * 100
    
    # Render card with the tooltiptext div hidden inside it
    return (f"<div class='cs-card'>"
            f"<div class='tooltiptext'>{s.get('desc', '')}</div>"
            f"<div class='cs-label'><span>{s['label']}</span> <span class='cs-icon'>ⓘ</span></div>"
            f"<div class='cs-value'>{s['fmt'].format(v)}{delta}</div>"
            f"<div class='cs-track'><div class='cs-fill' style='width:{width:.0f}%;background:{colour}'></div></div>"
            f"{sparkline_svg(series, colour)}</div>")

def render():
    ensure_state()
    state, prev = st.session_state.country, st.session_state.country_prev
    st.markdown(CSS, unsafe_allow_html=True)

    overall = _overall(state) * 100
    change = overall - _overall(prev) * 100
    letter = 'A' if overall >= 70 else 'B' if overall >= 60 else 'C' if overall >= 50 else 'D' if overall >= 40 else 'F'
    colour = '#6fbf8a' if overall >= 60 else ('#d9b45a' if overall >= 45 else '#d6604f')
    trend = 'unchanged since your last decision' if abs(change) < 0.05 else f"{change:+.1f} since your last decision"
    
    st.markdown(
        f"<div class='cs-grade'>"
        f"<div class='letter' style='color:{colour}'>{letter}</div>"
        f"<div><b>State of the Nation: {overall:.0f}/100</b><div class='txt'>{trend}</div></div></div>",
        unsafe_allow_html=True,
    )

    for title, keys in GROUPS:
        st.markdown(f'#### {title}')
        for col, key in zip(st.columns(len(keys)), keys):
            hist = [h[key] for h in st.session_state.get('country_hist', []) if key in h]
            col.markdown(_card(key, state, prev, hist), unsafe_allow_html=True)

    if APPROVAL_FEEDBACK:
        st.caption('A rising or falling state of the nation also nudges public approval after each decision.')
