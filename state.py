"""Shared session-state helpers: defaults, difficulty, snapshots, history log, save/load.

Nothing in here draws UI. Every other module reads and writes ``st.session_state`` through
these helpers so the whole game can also be driven headlessly (see ``sim.py``).
"""
import json
import random

import streamlit as st

PARTIES = ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru']
REGIONAL = ('SNP', 'Plaid Cymru')

# party: (starting approval, starting market confidence, starting polls)
START = {
    'Labour': (48, 65, dict(zip(PARTIES, [38, 32, 12, 10, 4, 3, 1]))),
    'Conservative': (46, 70, dict(zip(PARTIES, [32, 38, 12, 10, 4, 3, 1]))),
    'Liberal Democrats': (49, 60, dict(zip(PARTIES, [30, 30, 24, 8, 4, 3, 1]))),
    'Reform UK': (42, 55, dict(zip(PARTIES, [28, 28, 10, 26, 4, 3, 1]))),
    'Green Party': (45, 50, dict(zip(PARTIES, [28, 26, 12, 8, 22, 3, 1]))),
    'SNP': (45, 50, dict(zip(PARTIES, [34, 30, 10, 9, 4, 12, 1]))),
    'Plaid Cymru': (45, 50, dict(zip(PARTIES, [34, 30, 10, 9, 4, 3, 10]))),
}

# crisis: chance of a random crisis after each decision; good/bad: multipliers on positive/negative
# approval, market-confidence and headroom swings; approval: starting approval bonus.
DIFFICULTY = {
    'Easy': dict(crisis=0.15, good=1.15, bad=0.85, approval=3, blurb='Forgiving markets, fewer crises, ideology tags shown.'),
    'Normal': dict(crisis=0.25, good=1.0, bad=1.0, approval=0, blurb='The game as designed.'),
    'Hardcore': dict(crisis=0.4, good=0.85, bad=1.3, approval=0, blurb='Frequent crises and unforgiving markets.'),
}

# every stat that can be shown on a dashboard card and tracked over time
STAT_KEYS = ['approval', 'market_conf', 'growth', 'headroom', 'debt', 'deficit', 'inflation', 'interest_rate',
             'gilt_yield', 'pm_opinion', 'cab_opinion', 'party_opinion', 'backbench_opinion', 'media_opinion']

_HIST_LIMIT = 60

# ---------------------------------------------------------------- dashboard card definitions
CARDS_TOP = [
    dict(key='approval', label='Public Approval', fmt='{:.1f}%', dfmt='{:+.1f}%', dec=1,
         desc='The percentage of the electorate that supports your government. High approval boosts PM confidence and helps win elections.'),
    dict(key='market_conf', label='Market Confidence', fmt='{:.1f}%', dfmt='{:+.1f}%', dec=1,
         desc='How much the financial sector trusts your economic management. If this drops too low, borrowing costs spike and trigger a fiscal crisis.'),
    dict(key='growth', label='Economic Growth', fmt='{:.1f}%', dfmt='{:+.2f}%', dec=2,
         desc='The annual rate of GDP growth. Higher growth naturally increases tax revenues over time.'),
    dict(key='headroom', label='OBR Headroom', fmt='£{:.1f}B', dfmt='£{:+.1f}B', dec=1,
         desc='Your fiscal safety margin. Dropping into the negative breaks fiscal rules and panics the markets.'),
    dict(key='debt', label='National Debt', fmt='{:.1f}%', dfmt='{:+.1f}%', dec=1, inverse=True,
         desc='Total government debt as a % of GDP. High debt increases annual interest payments, eating into your budget.'),
]

CARDS_POLITICAL = [
    dict(key='pm_opinion', label="PM's Confidence", fmt='{:.0f}/100', dfmt='{:+.0f}', dec=0,
         desc="The Prime Minister's trust in you. Below 40 on election night you are sacked; below 20 at any time you are sacked on the spot."),
    dict(key='cab_opinion', label='Cabinet Support', fmt='{:.0f}/100', dfmt='{:+.0f}', dec=0,
         desc='The backing of your fellow ministers. Kept high by good public approval and generous budgets.'),
    dict(key='party_opinion', label='Party Unity', fmt='{:.0f}/100', dfmt='{:+.0f}', dec=0,
         desc='Harmony within your party. Below 40 triggers a leadership challenge, below 35 on election night means you are sacked, and below 15 at any time ends your career.'),
    dict(key='backbench_opinion', label='Backbench Morale', fmt='{:.0f}/100', dfmt='{:+.0f}', dec=0,
         desc="The mood of your MPs. Keep them happy with policies that fit your party's tradition. Below 20 and they will vote down your Budget."),
    dict(key='media_opinion', label='Media Sentiment', fmt='{:.0f}/100', dfmt='{:+.0f}', dec=0,
         desc='How the press is reporting on you. Driven by a mix of public approval and market stability.'),
]

CARDS_ECON = [
    dict(key='deficit', label='Annual Deficit', fmt='£{:.1f}B', dfmt='£{:+.1f}B', dec=1, inverse=True,
         desc='Shortfall between revenues and spending.'),
    dict(key='inflation', label='Inflation Rate', fmt='{:.1f}%', dfmt='{:+.1f}%', dec=1, inverse=True,
         desc='Rate at which prices are rising. Drifts back towards the 2% target over time, but sticky inflation above 3% erodes approval every year.'),
    dict(key='interest_rate', label='Bank Rate', fmt='{:.1f}%', dfmt='{:+.1f}%', dec=1, inverse=True,
         desc='BoE base interest rate. It follows inflation, with a lag.'),
    dict(key='gilt_yield', label='10-Yr Gilt Yield', fmt='{:.1f}%', dfmt='{:+.1f}%', dec=1, inverse=True,
         desc='Government borrowing cost. Driven by the Bank Rate, market confidence and the debt stock; it feeds straight into debt interest.'),
]

# human labels for effect summaries (value format, name)
FX_LABELS = {
    'headroom': ('Headroom', '£{:+g}B'), 'approval': ('Approval', '{:+g}'), 'market_conf': ('Market conf', '{:+g}'),
    'market': ('Market conf', '{:+g}'), 'growth': ('Growth', '{:+g}pp'), 'inflation': ('Inflation', '{:+g}pp'),
    'deficit': ('Deficit', '£{:+g}B'), 'debt': ('Debt', '{:+g}pp'), 'gilt_yield': ('Gilt yield', '{:+g}pp'),
    'gilt': ('Gilt yield', '{:+g}pp'), 'pm_opinion': ('PM confidence', '{:+g}'), 'cab_opinion': ('Cabinet', '{:+g}'),
    'party_opinion': ('Party unity', '{:+g}'), 'backbench_opinion': ('Backbench', '{:+g}'),
    'media_opinion': ('Media', '{:+g}'),
}


def fmt_fx(fx, include_country=True):
    """Short human summary of an effects dict, e.g. '£-4B Headroom, -3 Market conf'."""
    parts = []
    for key, val in fx.items():
        if key in FX_LABELS:
            name, f = FX_LABELS[key]
            parts.append(f'{f.format(val)} {name}')
        elif include_country and key != 'message':
            import country
            if key in country.STATS:
                parts.append(f"{val:+g} {country.STATS[key]['label']}")
    return ', '.join(parts)


# ---------------------------------------------------------------- difficulty helpers
def diff():
    return DIFFICULTY[st.session_state.get('difficulty', 'Hardcore')]


def scale(delta):
    """Scale a good/bad swing by the difficulty setting (positive = good for the player)."""
    d = diff()
    return delta * (d['good'] if delta > 0 else d['bad'])


# ---------------------------------------------------------------- snapshots & history
def values():
    s = st.session_state
    return {k: s[k] for k in STAT_KEYS}


def snapshot():
    """Remember the current numbers so dashboard cards can show what changed."""
    st.session_state.prev = values()


def snapshot_all():
    s = st.session_state
    import country
    return dict(values=values(), country=dict(s.country), overall=country._overall(s.country) * 100)


def record():
    """Append the current numbers to the history used for card sparklines."""
    s = st.session_state
    for k, v in values().items():
        series = s.stat_hist.setdefault(k, [])
        series.append(round(float(v), 2))
        del series[:-_HIST_LIMIT]
    s.country_hist.append({k: round(float(v), 2) for k, v in s.country.items()})
    del s.country_hist[:-_HIST_LIMIT]


def log(kind, title, choice='', ideology='', before=None, note=''):
    """Add an entry to the event log. ``before`` is a ``values()`` dict taken before the action."""
    s = st.session_state
    d = {}
    if before:
        for k in ('approval', 'market_conf', 'headroom', 'growth'):
            d[k] = round(s[k] - before[k], 2)
    score = d.get('approval', 0) + 0.5 * d.get('market_conf', 0) + 0.7 * d.get('headroom', 0)
    s.history.append(dict(n=len(s.history) + 1, term=s.term, year=s.year, block=s.block, kind=kind, title=title,
                          choice=choice, ideology=ideology, d=d, score=round(score, 2), note=note))


# ---------------------------------------------------------------- new game / defaults
_WIPE_PREFIXES = ('bt_', 'bs_', 'btp_', 'bsp_')


def _defaults():
    s = st.session_state
    base = dict(
        step='setup', party='Labour', year=1, block=1, term=1, steps=0,
        active_crisis=None, last_ideology=None, last_crisis=None, crisis_reason='', headlines=None,
        budget_passed=False, sacked=False, sacked_reason='', game_over=None, election_result=None,
        message='', humphrey_note='', last_humphrey_quote='', fallout_done=[],
        difficulty='Hardcore', seed=random.randint(1000, 99999), show_tags=False,
        approval=48.0, market_conf=65.0, debt=98.2, deficit=5.4, inflation=3.2, interest_rate=5.0,
        gilt_yield=4.7, growth=0.8, headroom=8.5,
        pm_opinion=75.0, cab_opinion=65.0, party_opinion=70.0, backbench_opinion=60.0, media_opinion=50.0,
        prev={}, pending=[], history=[], stat_hist={}, country_hist=[], event_cards=[],
        ideology_counts={}, crises_handled=0, achievements=[], new_achievements=[],
        poll_history={'Period': ['Start'], **{p: [0.0] for p in PARTIES}}, poll_anchor={},
        term_start=None, initialized=True,
    )
    for k, v in base.items():
        s[k] = v if not isinstance(v, (list, dict)) else json.loads(json.dumps(v))
    s.prev = values()


def ensure_init():
    if 'initialized' not in st.session_state:
        _defaults()


def new_game(party, difficulty, seed, show_tags):
    import country
    s = st.session_state
    s.clear()
    _defaults()
    approval, market, polls = START[party]
    s.party, s.difficulty, s.seed, s.show_tags = party, difficulty, int(seed), bool(show_tags)
    s.approval = float(approval + DIFFICULTY[difficulty]['approval'])
    s.market_conf = float(market)
    s.poll_history = {'Period': ['Start'], **{p: [float(v)] for p, v in polls.items()}}
    s.poll_anchor = {p: float(v) for p, v in polls.items()}
    s.step = 'game'
    s.message = ("Good morning, Chancellor. I am Sir Humphrey Appleby. My job is to protect you from the press, "
                 "the public, and most importantly, your own backbenchers.")
    country.ensure_state()
    s.prev = values()
    s.term_start = snapshot_all()
    record()


# ---------------------------------------------------------------- save / load
SAVE_KEYS = [
    'step', 'party', 'year', 'block', 'term', 'steps', 'active_crisis', 'last_ideology', 'last_crisis',
    'crisis_reason', 'headlines', 'budget_passed', 'sacked', 'sacked_reason', 'game_over', 'election_result',
    'message', 'humphrey_note', 'last_humphrey_quote', 'fallout_done', 'difficulty', 'seed', 'show_tags',
    'prev', 'pending', 'history', 'stat_hist', 'country_hist', 'event_cards', 'ideology_counts',
    'crises_handled', 'achievements', 'new_achievements', 'poll_history', 'poll_anchor', 'term_start',
    'country', 'country_prev', 'dept_spend', 'budget_applied', 'budget_interest', 'initialized',
] + STAT_KEYS


def export_save():
    s = st.session_state
    data = {k: s[k] for k in SAVE_KEYS if k in s}
    data['widgets'] = {k: s[k] for k in list(s.keys()) if str(k).startswith(_WIPE_PREFIXES)}
    data['format'] = 1
    return json.dumps(data, default=str, indent=1)


def import_save(text):
    """Load a save file. Returns an error string, or None on success."""
    try:
        data = json.loads(text)
        if data.get('format') != 1 or 'party' not in data:
            return 'That does not look like a Chancellor Simulator save file.'
    except (ValueError, AttributeError):
        return 'Could not read that file.'
    s = st.session_state
    s.clear()
    _defaults()
    widgets = data.pop('widgets', {})
    data.pop('format', None)
    for k, v in data.items():
        s[k] = v
    for k, v in widgets.items():
        s[k] = v
    if s.get('headlines'):
        s.headlines = tuple(s.headlines)
    s.step = 'game'
    return None
