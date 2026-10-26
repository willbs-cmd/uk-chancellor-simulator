"""Politics: special advisors, manifesto pledges, cabinet requests and the global economic cycle."""
import copy
import random

import streamlit as st

import budget
import econ

# ---------------------------------------------------------------- special advisors
HAWK_SAVING = 2.0       # £bn of 'efficiency savings' found every spring
ENFORCER_VOTES = 20     # extra ayes in every Budget vote
BANKER_FLOOR = 20.0     # market confidence can never fall below this

SPADS = {
    'spin':     dict(label='The Spin Doctor', blurb='Halves the penalties for breaking a manifesto pledge.'),
    'hawk':     dict(label='The Fiscal Hawk', blurb=f'Finds £{HAWK_SAVING:.1f}B of efficiency savings every spring.'),
    'enforcer': dict(label='The Enforcer', blurb=f'+{ENFORCER_VOTES} guaranteed votes whenever your Budget goes to the Commons.'),
    'banker':   dict(label='The City Banker', blurb=f'Market confidence can never fall below {BANKER_FLOOR:.0f}%.'),
}


# ---------------------------------------------------------------- manifesto pledges
def _no_rise(key):
    return lambda b, s: b['tax'][key] > budget.TAXES[key]['default']


def _no_cut(key):
    return lambda b, s: b['spend'][key] < 0


def _deficit_not_cut(b, s):
    """The deficit pledge is judged in the Budget of year 5, against where the term started."""
    if s.year != 5:
        return False
    start = (s.get('term_start') or {}).get('values', {}).get('deficit', s.deficit)
    return s.deficit + budget.impact(s.budget_applied, b)['deficit'] >= start


PLEDGES = {
    'income':  dict(label='Never raise Basic Income Tax', test=_no_rise('income')),
    'vat':     dict(label='Never raise VAT', test=_no_rise('vat')),
    'corp':    dict(label='Never raise Corporation Tax', test=_no_rise('corp')),
    'cgt':     dict(label='Never raise Capital Gains Tax', test=_no_rise('cgt')),
    'nhs':     dict(label='Protect NHS Funding (No Cuts)', test=_no_cut('health')),
    'edu':     dict(label='Protect Education (No Cuts)', test=_no_cut('education')),
    'welfare': dict(label='Never Increase Welfare Spending', test=lambda b, s: b['spend']['welfare'] > 0),
    'deficit': dict(label='Cut the Deficit (lower than at the start of the term by Year 5)', test=_deficit_not_cut),
}


def broken_by(draft):
    """Pledges that Budget ``draft`` would break (and that are not already broken)."""
    s = st.session_state
    return [k for k in s.get('pledges', []) if k in PLEDGES and k not in s.get('broken_pledges', [])
            and PLEDGES[k]['test'](draft, s)]


def check_pledges():
    """Called when a Budget is delivered: break any pledge it violates and take the political damage."""
    s = st.session_state
    hits = broken_by(s.budget_applied)
    mult = 0.5 if s.get('spad') == 'spin' else 1.0
    notes = []
    for k in hits:
        s.broken_pledges = list(s.get('broken_pledges', [])) + [k]
        s.approval = round(max(0.0, s.approval - 12 * mult), 1)
        s.media_opinion = round(max(0.0, s.media_opinion - 20 * mult), 1)
        s.party_opinion = round(max(0.0, s.party_opinion - 8 * mult), 1)
        notes.append(f"🚨 U-TURN SCANDAL: you broke your manifesto pledge to '{PLEDGES[k]['label']}'.")
    if notes:
        s.message = (s.get('message') or '') + ' ' + ' '.join(notes)
    return hits


def render_pledges(draft):
    """One line of chips: green = kept so far, amber = this Budget would break it, red = already broken."""
    s = st.session_state
    pledges = [k for k in s.get('pledges', []) if k in PLEDGES]
    if not pledges:
        return
    risky, broken = set(broken_by(draft)), set(s.get('broken_pledges', []))
    chips = []
    for k in pledges:
        label = PLEDGES[k]['label']
        if k in broken:
            chips.append(f"<span class='pl pl-broken'>❌ {label}</span>")
        elif k in risky:
            chips.append(f"<span class='pl pl-risk'>⚠️ {label}: this Budget breaks it</span>")
        else:
            chips.append(f"<span class='pl pl-ok'>✅ {label}</span>")
    st.markdown(f"<div class='pl-row'><b>📜 Pledges</b> {' '.join(chips)}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- cabinet requests
CABINET_REQUESTS = [
    dict(minister='Health Secretary', cost=2.0, text='Winter pressures are crippling hospitals. I need £2.0B for emergency capacity or we face a catastrophic winter.',
         accept={'nhs_waiting': -0.3, 'cab_opinion': 5, 'approval': 1}, refuse={'cab_opinion': -5, 'media_opinion': -5, 'approval': -1}),
    dict(minister='Defence Secretary', cost=3.0, text='Allies are demanding we step up. I need £3.0B of emergency procurement to keep our commitments.',
         accept={'cab_opinion': 6, 'market_conf': 1}, refuse={'cab_opinion': -6, 'market_conf': -1, 'media_opinion': -3}),
    dict(minister='Education Secretary', cost=1.5, text='School buildings are literally crumbling. I need £1.5B for urgent repairs before there is a tragedy.',
         accept={'schools': 1.0, 'cab_opinion': 4, 'media_opinion': 3}, refuse={'cab_opinion': -4, 'media_opinion': -4, 'approval': -1}),
    dict(minister='Transport Secretary', cost=2.5, text='A key rail line is failing and the unions are circling. I need £2.5B for emergency upgrades.',
         accept={'rail': 3.0, 'cab_opinion': 4, 'approval': 1}, refuse={'cab_opinion': -4, 'media_opinion': -4}),
    dict(minister='Home Secretary', cost=1.5, text='The prison system is at capacity and disorder is spreading. I need £1.5B immediately.',
         accept={'prisons': -3.0, 'cab_opinion': 4, 'media_opinion': 3}, refuse={'cab_opinion': -4, 'media_opinion': -5, 'approval': -1}),
    dict(minister='Foreign Secretary', cost=1.0, text='A major trade deal hinges on a symbolic aid commitment. I need £1.0B to close it.',
         accept={'market_conf': 2, 'cab_opinion': 3, 'growth': 0.03}, refuse={'cab_opinion': -3, 'market_conf': -1}),
    dict(minister='Science Secretary', cost=1.5, text='A flagship national laboratory will lose its best researchers without a funding top-up. I need £1.5B.',
         accept={'growth': 0.05, 'cab_opinion': 4, 'approval': 1}, refuse={'cab_opinion': -4, 'media_opinion': -4, 'market_conf': -1}),
    dict(minister='Culture Secretary', cost=0.8, text="Britain's national museums will cut their opening days without £0.8B. The press is already writing the headlines.",
         accept={'approval': 1, 'cab_opinion': 3}, refuse={'media_opinion': -6, 'cab_opinion': -3}),
]


def pick_request():
    return copy.deepcopy(random.choice(CABINET_REQUESTS))


# ---------------------------------------------------------------- the global economic cycle
SHIFT_CHANCE = 0.20


def shift_macro_cycle():
    """Each spring the world economy may tip from one phase of the cycle into another."""
    s = st.session_state
    if random.random() < SHIFT_CHANCE:
        s.macro_cycle = random.choice([c for c in econ.CYCLES if c != s.get('macro_cycle')])
        s.message += f" 🌍 GLOBAL SHIFT: the world economy has entered a {s.macro_cycle.lower()} phase."
