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
    'Easy': dict(crisis=0.15, good=1.15, bad=0.85, approval=3, undos=3, blurb='Forgiving markets, fewer crises, ideology tags shown, 3 undos.'),
    'Normal': dict(crisis=0.25, good=1.0, bad=1.0, approval=0, undos=1, blurb='The game as designed, with 1 undo.'),
    'Hardcore': dict(crisis=0.4, good=0.85, bad=1.3, approval=0, undos=0, blurb='Frequent crises and unforgiving markets. No undo.'),
}


# ---------------------------------------------------------------- starting scenarios
# 'set' overrides the opening economy; approval / market are changes to the party's usual start.
SCENARIOS = {
    'fragile': dict(label='2026: The Fragile Present', set={}, approval=0, market=0, cycle='Stagnation',
                    blurb='Debt near 100% of GDP, a 4% deficit and inflation stuck above target.',
                    msg="Good morning, Chancellor. I am Sir Humphrey Appleby."),
    'crash2008': dict(label='2008: The Great Financial Crash', approval=0, market=-25, cycle='Recession',
                      set=dict(debt=60.0, deficit=153.0, inflation=4.0, interest_rate=0.5, gilt_yield=4.0, growth=-2.5, headroom=-20.0),
                      blurb='Very hard. The banks have collapsed, growth is deeply negative and you start in breach of your fiscal rules.',
                      msg="Welcome to 2008, Chancellor. I am Sir Humphrey Appleby, and the global banking sector has collapsed."),
    'winter1978': dict(label='1978: Winter of Discontent', approval=-10, market=-15, cycle='Stagnation',
                       set=dict(debt=55.0, deficit=45.0, inflation=15.5, interest_rate=12.0, gilt_yield=9.0, growth=-1.0, headroom=3.0),
                       blurb='Hard. Rampant inflation, sky-high rates and unions preparing for war.',
                       msg="Welcome to 1978, Chancellor. I am Sir Humphrey Appleby, inflation is rampant and the unions are preparing for war."),
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
         desc="The mood of your MPs. Keep them happy with policies that fit your party's tradition. Below 20 and they will vote down your Budget unless the Whips can find the votes."),
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
    apply_floors()
    for k, v in values().items():
        series = s.stat_hist.setdefault(k, [])
        series.append(round(float(v), 2))
        del series[:-_HIST_LIMIT]
    s.country_hist.append({k: round(float(v), 2) for k, v in s.country.items()})
    del s.country_hist[:-_HIST_LIMIT]


def apply_floors():
    """Rules that must hold after every action (the City Banker's floor on market confidence)."""
    s = st.session_state
    if s.get('spad') == 'banker' and s.market_conf < 20.0:
        s.market_conf = 20.0


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
        approval=48.0, market_conf=65.0, debt=98.2, deficit=125.4, inflation=3.2, interest_rate=5.0,
        gilt_yield=4.7, growth=0.8, headroom=8.5,
        pm_opinion=75.0, cab_opinion=65.0, party_opinion=70.0, backbench_opinion=60.0, media_opinion=50.0,
        prev={}, pending=[], history=[], stat_hist={}, country_hist=[], event_cards=[],
        ideology_counts={}, crises_handled=0, achievements=[], new_achievements=[],
        poll_history={'Period': ['Start'], **{p: [0.0] for p in PARTIES}}, poll_anchor={},
        term_start=None, whip_ayes=0, whip_used=[], vote_ayes=0, scenario='fragile', spad=None, pledges=[], broken_pledges=[],
        macro_cycle='Stagnation', active_request=None, undos_left=0, checkpoint=None, budget_speech=None, budget_impact={},
        political_capital_points=5, longrun_productivity=1.0, pension_pressure=0.0, demographic_pressure=0.0,
        threshold_freeze_years=0, thresholds_frozen=False, personal_allowance=12570.0,
        higher_rate_threshold=50270.0, additional_rate_threshold=125140.0,
        gilt_maturity_years=10, index_linked_share=25,
        feature_actions={}, feature_notice='', feature_notice_phase=0,
        threshold_freeze_scope='Personal allowance and all bands',
        parliament_next_bonus=0, parliament_last_vote=None, parliament_history=[],\n        parliament_actions={}, parliament_last_strategy=None,
        pay_settlement='unsettled', is_prime_minister=False, initialized=True,
    )
    for k, v in base.items():
        s[k] = v if not isinstance(v, (list, dict)) else json.loads(json.dumps(v))
    s.prev = values()


def ensure_init():
    if 'initialized' not in st.session_state:
        _defaults()


def new_game(party, difficulty, seed, show_tags, scenario='fragile', spad=None, pledges=()):
    import budget
    import country
    import politics
    s = st.session_state
    s.clear()
    _defaults()
    approval, market, polls = START[party]
    sc = SCENARIOS.get(scenario) or SCENARIOS['fragile']
    s.scenario = scenario if scenario in SCENARIOS else 'fragile'
    s.party, s.difficulty, s.seed, s.show_tags = party, difficulty, int(seed), bool(show_tags)
    for k, v in sc['set'].items():
        s[k] = v
    s.pledges = [p for p in list(pledges)[:3] if p in politics.PLEDGES]
    s.spad = spad if spad in politics.SPADS else None
    s.macro_cycle = sc['cycle']
    # every pledge you make is a promise voters like to hear (and hold you to)
    s.approval = float(approval + DIFFICULTY[difficulty]['approval'] + sc['approval'] + 2.0 * len(s.pledges))
    s.market_conf = float(market + sc['market'])
    s.undos_left = DIFFICULTY[difficulty]['undos']
    s.budget_interest = budget.interest()          # so a scenario's opening gilt yield doesn't cause a phantom spring shock
    s.poll_history = {'Period': ['Start'], **{p: [float(v)] for p, v in polls.items()}}
    s.poll_anchor = {p: float(v) for p, v in polls.items()}
    s.step = 'game'
    s.message = (sc['msg'] + " My job is to protect you from the press, the public, and most importantly, your own "
                 "backbenchers.")
    country.ensure_state()
    s.prev = values()
    s.term_start = snapshot_all()
    record()


# ---------------------------------------------------------------- undo
def checkpoint():
    """Remember the game as it is now, so the next action can be undone (only when this difficulty allows undos)."""
    s = st.session_state
    if diff().get('undos', 0) > 0 and s.get('undos_left', 0) > 0:
        s.checkpoint = export_save()


def can_undo():
    s = st.session_state
    return bool(s.get('checkpoint')) and s.get('undos_left', 0) > 0


def undo():
    """Roll back to before the last action. Returns True if it worked."""
    s = st.session_state
    raw, left = s.get('checkpoint'), s.get('undos_left', 0)
    if not raw or left <= 0:
        return False
    if import_save(raw) is not None:
        return False
    s.undos_left = left - 1
    s.checkpoint = None
    return True


# ---------------------------------------------------------------- save / load
SAVE_KEYS = [
    'step', 'party', 'year', 'block', 'term', 'steps', 'active_crisis', 'last_ideology', 'last_crisis',
    'crisis_reason', 'headlines', 'budget_passed', 'sacked', 'sacked_reason', 'game_over', 'election_result',
    'message', 'humphrey_note', 'last_humphrey_quote', 'fallout_done', 'difficulty', 'seed', 'show_tags',
    'prev', 'pending', 'history', 'stat_hist', 'country_hist', 'event_cards', 'ideology_counts',
    'crises_handled', 'achievements', 'new_achievements', 'poll_history', 'poll_anchor', 'term_start',
    'country', 'country_prev', 'dept_spend', 'budget_applied', 'budget_interest', 'budget_last_tax',
    'whip_ayes', 'whip_used', 'vote_ayes', 'scenario', 'spad', 'pledges', 'broken_pledges', 'macro_cycle', 'active_request',
    'undos_left', 'budget_speech', 'budget_impact', 'budget_last_pol', 'initialized',
    'political_capital_points', 'longrun_productivity', 'pension_pressure', 'demographic_pressure', 'threshold_freeze_years',
    'feature_actions', 'feature_notice', 'feature_notice_phase',
    'gilt_maturity_years', 'index_linked_share', 'pay_settlement', 'is_prime_minister',
    'thresholds_frozen', 'personal_allowance', 'higher_rate_threshold', 'additional_rate_threshold',
    'threshold_freeze_scope',
    'parliament_next_bonus', 'parliament_last_vote', 'parliament_history',\n    'parliament_actions', 'parliament_last_strategy',
] + STAT_KEYS


SAVE_FORMAT = 2


def export_save():
    s = st.session_state
    data = {k: s[k] for k in SAVE_KEYS if k in s}
    data['widgets'] = {k: s[k] for k in list(s.keys()) if str(k).startswith(_WIPE_PREFIXES)}
    data['format'] = SAVE_FORMAT
    return json.dumps(data, default=str, indent=1)


def import_save(text):
    """Load a save file. Returns an error string, or None on success."""
    try:
        data = json.loads(text)
        if 'party' not in data or 'format' not in data:
            return 'That does not look like a Chancellor Simulator save file.'
        if data.get('format') != SAVE_FORMAT:
            return 'That save was made by an older version of the game and cannot be loaded.'
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
