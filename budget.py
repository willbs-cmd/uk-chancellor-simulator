"""The Budget: tax and spending levers, one-off schemes, the Whips' Office, the OBR forecast and the Red Book.

Everything about *how* a Budget changes the numbers lives here (``impact``, ``apply_ongoing``); the Streamlit
drawing code is at the bottom (``render``).
"""
import math

import pandas as pd
import streamlit as st
import altair as alt

import country
import econ
import imf_outlook
import state
from theme import render_chips

# group, label, short name, default rate, slider range, revenue at the default rate (£bn),
# £bn per point of rate, and 'decay' (how fast higher rates stop paying: the Laffer effect)
TAXES = {
    'income':   dict(group='Income & consumption', label='Income tax, basic rate (p in the £)', short='Income tax', default=20, lo=5, hi=45, step=1, base=300.0, per=7.5, decay=0.02),
    'ni':       dict(group='Income & consumption', label='National Insurance rate (%)', short='National Insurance', default=15, lo=0, hi=30, step=1, base=190.0, per=9.0, decay=0.04),
    'vat':      dict(group='Income & consumption', label='VAT (%)', short='VAT', default=20, lo=5, hi=35, step=1, base=170.0, per=8.0, decay=0.04),
    'fuel':     dict(group='Income & consumption', label='Fuel duty (% change)', short='Fuel duty', default=0, lo=-50, hi=50, step=5, base=25.0, per=0.25, decay=0.004),
    'sin':      dict(group='Income & consumption', label='Alcohol & tobacco duty (% change)', short='Alcohol & tobacco', default=0, lo=-30, hi=50, step=5, base=22.0, per=0.22, decay=0.006),
    'corp':     dict(group='Business, wealth & capital', label='Corporation tax (%)', short='Corporation tax', default=25, lo=5, hi=45, step=1, base=90.0, per=2.5, decay=0.04),
    'property': dict(group='Business, wealth & capital', label='Property & wealth taxes (% change)', short='Property taxes', default=0, lo=-50, hi=100, step=5, base=110.0, per=1.1, decay=0.004),
    'cgt':      dict(group='Business, wealth & capital', label='Capital gains tax (%)', short='Capital gains tax', default=24, lo=10, hi=45, step=1, base=16.0, per=0.6, decay=0.05),
    'iht':      dict(group='Business, wealth & capital', label='Inheritance tax (%)', short='Inheritance tax', default=40, lo=0, hi=60, step=1, base=8.0, per=0.2, decay=0.05),
}

# One-off schemes: a flat yield (or cost) every year, plus a one-time hit to approval, markets and growth.
TAX_POLICIES = {
    'vat_private': dict(label='Apply VAT to Private School Fees', yield_bn=1.5, app=1, mkt=-1, gro=0),
    'nondom':      dict(label='Scrap Non-Dom Tax Status', yield_bn=2.5, app=2, mkt=-2, gro=0),
    'windfall':    dict(label='Windfall Tax on Energy Firms', yield_bn=4.0, app=3, mkt=-3, gro=-0.1),
    'wealth':      dict(label='1% Wealth Tax on assets >£10m', yield_bn=9.0, app=4, mkt=-6, gro=-0.2),
    'mansion':     dict(label='Mansion Tax on Homes over £2m', yield_bn=1.8, app=1, mkt=-1, gro=0),
    'digital':     dict(label='Digital Services Tax on Big Tech', yield_bn=2.0, app=2, mkt=-2, gro=-0.05),
    'carbon':      dict(label='Expand Carbon Pricing', yield_bn=3.5, app=-2, mkt=1, gro=-0.05),
    'gambling':    dict(label='Overhaul Gambling Duties', yield_bn=1.5, app=1, mkt=0, gro=0),
}

OTHER_RECEIPTS = 219.0   # everything not broken out above (so total receipts at the defaults stay at £1,150bn)
GDP_BN = 3125.0          # nominal GDP used for the '% of GDP' lines: tax take 36.8%, spending 40.8%, deficit 4.0% at the defaults

SPEND_DEFAULTS = {
    'welfare':   dict(label='Welfare & pensions', short='Welfare & pensions', default=368.0),
    'health':    dict(label='NHS & health', short='NHS & health', default=240.0),
    'education': dict(label='Education', short='Education', default=139.0),
    'defence':   dict(label='Defence', short='Defence', default=69.0),
    'transport': dict(label='Transport & infrastructure', short='Transport & infrastructure', default=53.0),
    'justice':   dict(label='Policing, courts & prisons', short='Policing, courts & prisons', default=50.0),
    'housing':   dict(label='Housing & local government', short='Housing & local government', default=67.0),
    'climate':   dict(label='Climate, energy & industry', short='Climate, energy & industry', default=39.0),
    'science':   dict(label='Science, research & innovation', short='Science & research', default=16.0),
    'aid':       dict(label='Overseas aid', short='Overseas aid', default=15.0),
    'culture':   dict(label='Culture, media & sport', short='Culture, media & sport', default=9.0),
    'other':     dict(label='Other departments & admin', short='Other departments & admin', default=105.0),
}

SPEND_POLICIES = {
    'hs2':        dict(label='Revive Full HS2 Rail Project', cost_bn=8.0, app=2, mkt=0, gro=0.2),
    'meals':      dict(label='Universal Free School Meals', cost_bn=2.5, app=3, mkt=0, gro=0),
    'child_cap':  dict(label='Scrap Two-Child Benefit Limit', cost_bn=3.0, app=2, mkt=-1, gro=0),
    'water':      dict(label='Nationalise Water Companies', cost_bn=10.0, app=5, mkt=-4, gro=0),
    'nuclear':    dict(label='Fast-Track New Nuclear Power', cost_bn=6.0, app=1, mkt=1, gro=0.15),
    'childcare':  dict(label='Expand Free Childcare', cost_bn=4.0, app=3, mkt=-0.5, gro=0.1),
    'winterfuel': dict(label='Universal Winter Fuel Payment', cost_bn=1.5, app=2.5, mkt=-0.5, gro=0),
    'potholes':   dict(label='National Pothole & Roads Fund', cost_bn=2.0, app=2, mkt=0, gro=0.05),
}

# what each spending scheme does to the State of the Nation, every spring it stays in the Budget
POLICY_NUDGES = {
    'hs2': {'rail': 4},
    'meals': {'schools': 2},
    'child_cap': {'child_poverty': -4},
    'nuclear': {'netzero': 2.0, 'energy_bills': -20},
    'childcare': {'child_poverty': -0.8, 'unemployment': -0.03},
}

BASE_INTEREST = 105.4

PALETTE = ['#c9a45c', '#6fbf8a', '#4f8fba', '#d6604f', '#9a7fc4', '#e0b0a0', '#7fb8b0', '#c4c46f', '#8aa0a0',
           '#d98cb3', '#5f7f5f', '#b07a3c', '#6c8fd1', '#c97a7a', '#a0a0a0', '#e6d9a8']

# ---------------------------------------------------------------- the Whips' Office
WIN = 326   # a majority of the Commons
ENFORCER_VOTES = 20   # the Enforcer special advisor's guaranteed votes (see politics.py)


def _can_pork(s): return s.headroom >= 2.0
def _can_threat(s): return s.party_opinion >= 25
def _can_dilute(s): return s.market_conf >= 5


WHIPS = {
    'pork':    dict(label='Offer constituency sweeteners', hint='-£2.0B headroom, +15 votes', ayes=15, can=_can_pork),
    'threat':  dict(label='Threaten the rebels', hint='-10 party unity, +15 votes', ayes=15, can=_can_threat),
    'dilute':  dict(label='Water down the reforms', hint='-2 market confidence, +10 votes', ayes=10, can=_can_dilute),
}

LEFT_PARTIES = ('Labour', 'Liberal Democrats', 'Green Party', 'SNP', 'Plaid Cymru')
RIGHT_PARTIES = ('Conservative', 'Reform UK')

# (parties, test(dtax, dspend), stat hit, size, message)  dtax = tax change since the last Budget, dspend = this year's % change
IRRITANTS = [
    (RIGHT_PARTIES, lambda t, p: t['corp'] > 0, 'backbench_opinion', 15, 'Your backbenchers are furious about the Corporation Tax hike.'),
    (RIGHT_PARTIES, lambda t, p: t['iht'] > 0, 'backbench_opinion', 8, 'The shires are up in arms over the inheritance tax rise.'),
    (RIGHT_PARTIES, lambda t, p: t['fuel'] > 0, 'backbench_opinion', 8, 'Rural MPs are livid about the fuel duty rise.'),
    (RIGHT_PARTIES, lambda t, p: p['aid'] > 0, 'backbench_opinion', 8, 'Your backbenchers are incandescent about the rise in foreign aid.'),
    (('Labour', 'Green Party'), lambda t, p: p['welfare'] < 0, 'party_opinion', 15, 'The left wing of your party is in open revolt over welfare cuts.'),
    (('Liberal Democrats',), lambda t, p: p['climate'] < 0, 'party_opinion', 15, 'Your party base is angry about cuts to climate spending.'),
    (('SNP', 'Plaid Cymru'), lambda t, p: p['other'] < 0, 'party_opinion', 15, 'Your regional assembly is furious about cuts to devolved block grants.'),
    (LEFT_PARTIES, lambda t, p: p['aid'] < 0, 'party_opinion', 8, 'Party members are dismayed by the cut to overseas aid.'),
    (('Green Party',), lambda t, p: t['fuel'] < 0, 'party_opinion', 10, 'Green activists are outraged by the fuel duty cut.'),
]


def defaults():
    return {
        'tax': {k: v['default'] for k, v in TAXES.items()},
        'spend': {k: 0.0 for k in SPEND_DEFAULTS},
        'tax_pol': {k: False for k in TAX_POLICIES},
        'spend_pol': {k: False for k in SPEND_POLICIES},
    }


def _migrate_applied(applied):
    """Old save files predate some levers: fill the gaps with the defaults so nothing raises a KeyError."""
    for section, dflt in defaults().items():
        got = applied.setdefault(section, {})
        for k, v in dflt.items():
            got.setdefault(k, v)


def _migrate_depts(dept):
    """Old saves had no Science / Aid / Culture lines: carve them out of 'Other' so total spending is unchanged."""
    new = [k for k in SPEND_DEFAULTS if k not in dept]
    for k in new:
        dept[k] = SPEND_DEFAULTS[k]['default']
    if new and 'other' in dept:
        dept['other'] = round(max(0.0, dept['other'] - sum(SPEND_DEFAULTS[k]['default'] for k in new)), 1)


def ensure():
    s = st.session_state
    if 'dept_spend' not in s:
        s.dept_spend = {k: v['default'] for k, v in SPEND_DEFAULTS.items()}
    else:
        _migrate_depts(s.dept_spend)

    if 'budget_applied' not in s or 'tax_pol' not in s.get('budget_applied', {}):
        s.budget_applied = defaults()
    else:
        _migrate_applied(s.budget_applied)
    s.setdefault('budget_interest', BASE_INTEREST)
    s.setdefault('budget_last_tax', dict(s.budget_applied['tax']))
    for k in TAXES:
        s.budget_last_tax.setdefault(k, TAXES[k]['default'])
    s.setdefault('budget_last_pol', {'tax_pol': {k: False for k in TAX_POLICIES}, 'spend_pol': {k: False for k in SPEND_POLICIES}})
    s.setdefault('budget_impact', {})
    s.setdefault('whip_ayes', 0)
    s.setdefault('whip_used', [])

    for k, v in s.budget_applied['tax'].items(): s.setdefault(f'bt_{k}', v)
    for k, v in s.budget_applied['spend'].items(): s.setdefault(f'bs_{k}', float(v))
    for k, v in s.budget_applied['tax_pol'].items(): s.setdefault(f'btp_{k}', v)
    for k, v in s.budget_applied['spend_pol'].items(): s.setdefault(f'bsp_{k}', v)


def read():
    s = st.session_state
    return {
        'tax': {k: s[f'bt_{k}'] for k in TAXES},
        'spend': {k: float(s[f'bs_{k}']) for k in SPEND_DEFAULTS},
        'tax_pol': {k: s[f'btp_{k}'] for k in TAX_POLICIES},
        'spend_pol': {k: s[f'bsp_{k}'] for k in SPEND_POLICIES},
    }


def revenues(b):
    out = {}
    for k, t in TAXES.items():
        d = b['tax'][k] - t['default']
        out[k] = t['base'] + t['per'] * d - t['decay'] * t['per'] * max(d, 0) ** 2
    return out


def interest_for(gilt_yield, debt):
    return BASE_INTEREST * (1 + 0.4 * (gilt_yield / 4.7 - 1) + (debt / 98.2 - 1))


def interest():
    s = st.session_state
    return interest_for(s.gilt_yield, s.debt)


def _policy_sum(b, key, table, field):
    return sum(table[k][field] for k, on in b[key].items() if on and k in table)


def revenue_pie(b):
    r = revenues(b)
    data = {TAXES[k]['short']: round(v, 1) for k, v in r.items()}
    data['Other receipts'] = OTHER_RECEIPTS
    pol_rev = _policy_sum(b, 'tax_pol', TAX_POLICIES, 'yield_bn')
    if pol_rev > 0: data['Special Tax Schemes'] = round(pol_rev, 1)
    return data


def spending_pie(b):
    s = st.session_state
    ensure()
    data = {SPEND_DEFAULTS[k]['short']: round(s.dept_spend[k] * (1.0 + b['spend'][k] / 100.0), 1) for k in SPEND_DEFAULTS}
    data['Debt interest'] = round(interest(), 1)
    pol_spend = _policy_sum(b, 'spend_pol', SPEND_POLICIES, 'cost_bn')
    if pol_spend > 0: data['Special Spending Pledges'] = round(pol_spend, 1)
    return data


def totals(b):
    """(receipts, spending) in £bn for a Budget draft, at today's debt interest."""
    s = st.session_state
    ensure()
    rev = sum(revenues(b).values()) + OTHER_RECEIPTS + _policy_sum(b, 'tax_pol', TAX_POLICIES, 'yield_bn')
    spend = (sum(s.dept_spend[k] * (1.0 + b['spend'][k] / 100.0) for k in SPEND_DEFAULTS) + interest()
             + _policy_sum(b, 'spend_pol', SPEND_POLICIES, 'cost_bn'))
    return rev, spend


def impact(old, new):
    """What moving from Budget ``old`` to Budget ``new`` does to the headline numbers (applied once, when delivered)."""
    s = st.session_state
    ensure()
    ro, rn = revenues(old), revenues(new)
    d = {k: rn[k] - ro[k] for k in ro}
    ds = {k: s.dept_spend[k] * ((new['spend'][k] - old['spend'][k]) / 100.0) for k in SPEND_DEFAULTS}

    tax_pol_diff = (_policy_sum(new, 'tax_pol', TAX_POLICIES, 'yield_bn') - _policy_sum(old, 'tax_pol', TAX_POLICIES, 'yield_bn'))
    spend_pol_diff = (_policy_sum(new, 'spend_pol', SPEND_POLICIES, 'cost_bn') - _policy_sum(old, 'spend_pol', SPEND_POLICIES, 'cost_bn'))
    bal = sum(d.values()) - sum(ds.values()) + tax_pol_diff - spend_pol_diff

    household = d['income'] + d['ni'] + d['vat'] + d['fuel'] + d['sin']
    wealth = d['property'] + d['cgt'] + d['iht']
    vat_pts = new['tax']['vat'] - old['tax']['vat']

    approval = (-0.10 * household - 0.03 * wealth
                + 0.05 * (ds['health'] + ds['education']) + 0.03 * ds['welfare']
                + 0.02 * (ds['justice'] + ds['housing'] + ds['transport']) + 0.01 * ds['defence']
                + 0.01 * (ds['science'] + ds['culture']) - 0.01 * ds['aid'])
    market = (max(-8, min(8, 0.10 * bal)) - 0.25 * d['corp'] - 0.12 * d['property']
              - 0.10 * d['cgt'] - 0.05 * d['iht'])
    growth = (-0.012 * d['corp'] - 0.006 * d['ni'] - 0.004 * d['income'] - 0.008 * d['cgt']
              + 0.008 * (ds['transport'] + ds['housing'] + ds['climate']) + 0.012 * ds['science']
              + 0.002 * (ds['health'] + ds['education'] + ds['other'] + ds['welfare'] + ds['culture'])
              + 0.001 * ds['defence'])

    for key, table in (('tax_pol', TAX_POLICIES), ('spend_pol', SPEND_POLICIES)):
        for k, p in table.items():
            if new[key][k] and not old[key][k]:
                approval += p['app']; market += p['mkt']; growth += p['gro']
            elif not new[key][k] and old[key][k]:
                approval -= p['app']; market -= p['mkt']; growth -= p['gro']

    inflation = 0.12 * vat_pts + 0.003 * sum(ds.values()) + 0.015 * d['fuel'] + 0.005 * d['sin']

    return dict(headroom=bal, deficit=-bal, approval=approval, market=market,
                growth=growth, inflation=inflation,
                real_wages=-0.010 * d['income'] - 0.006 * d['ni'] - 0.004 * d['fuel'],
                unemployment=0.010 * d['ni'] + 0.004 * d['corp'])


def _clip(v): return max(0, min(100, v))


def _apply():
    s = st.session_state
    new, old = read(), s.budget_applied
    if new == old:
        s.message = 'Budget unchanged.'
        return
    imp = impact(old, new)

    state.snapshot()

    s.headroom = round(s.headroom + imp['headroom'], 1)
    s.deficit = round(s.deficit + imp['deficit'], 1)
    s.approval = round(_clip(s.approval + imp['approval']), 1)
    s.market_conf = round(_clip(s.market_conf + imp['market']), 1)
    s.growth = round(s.growth + imp['growth'], 2)
    s.inflation = round(s.inflation + imp['inflation'], 2)
    country.nudge({'real_wages': imp['real_wages'], 'unemployment': imp['unemployment']})
    s.budget_applied = new
    acc = dict(s.get('budget_impact') or {})
    for k, v in imp.items():
        acc[k] = round(acc.get(k, 0.0) + v, 4)
    s.budget_impact = acc
    verb = 'improves' if imp['headroom'] >= 0 else 'worsens'
    s.message = f"Budget delivered. It {verb} public finances by £{abs(imp['headroom']):.1f}B a year."


def _reset():
    s = st.session_state
    for k, v in s.budget_applied['tax'].items(): s[f'bt_{k}'] = v
    for k, v in s.budget_applied['spend'].items(): s[f'bs_{k}'] = float(v)
    for k, v in s.budget_applied['tax_pol'].items(): s[f'btp_{k}'] = v
    for k, v in s.budget_applied['spend_pol'].items(): s[f'bsp_{k}'] = v


# ---------------------------------------------------------------- the Commons vote
def rebel_risks(b):
    """Who your own side will be angry about in Budget ``b``: a list of (stat, size, message)."""
    s = st.session_state
    ensure()
    last = s.budget_last_tax
    dtax = {k: b['tax'][k] - last.get(k, TAXES[k]['default']) for k in TAXES}
    dspend = b['spend']
    return [(stat, size, msg) for parties, test, stat, size, msg in IRRITANTS
            if s.party in parties and test(dtax, dspend)]


def apply_irritants():
    """Deliver the revolt penalties for the Budget just applied (before the vote, so they can sink it)."""
    s = st.session_state
    hits = rebel_risks(s.budget_applied)
    for stat, size, _ in hits:
        s[stat] = round(_clip(s[stat] - size), 1)
    if hits:
        s.message = (s.get('message') or '') + ' ' + ' '.join(msg for _, _, msg in hits)
    return [msg for _, _, msg in hits]


def commons_ayes(backbench=None, whip=None):
    """Ayes for the Budget. Crosses 326 exactly at backbench morale 20; whip interventions add votes on top."""
    s = st.session_state
    bb = s.backbench_opinion if backbench is None else backbench
    extra = s.get('whip_ayes', 0) if whip is None else whip
    if s.get('spad') == 'enforcer':
        extra += ENFORCER_VOTES
    return int(min(650, max(0, math.floor(WIN + 0.75 * (bb - 20)) + extra)))


def projected_ayes(draft):
    s = st.session_state
    bb = s.backbench_opinion - sum(size for stat, size, _ in rebel_risks(draft) if stat == 'backbench_opinion')
    return commons_ayes(max(0.0, bb))


def _whip(key):
    s = st.session_state
    w = WHIPS[key]
    if key in s.get('whip_used', []) or not w['can'](s):
        return
    state.snapshot()
    if key == 'pork':
        s.headroom = round(s.headroom - 2.0, 1)
    elif key == 'threat':
        s.party_opinion = round(_clip(s.party_opinion - 10), 1)
    elif key == 'dilute':
        s.market_conf = round(_clip(s.market_conf - 2.0), 1)
    s.whip_ayes = s.get('whip_ayes', 0) + w['ayes']
    s.whip_used = list(s.get('whip_used', [])) + [key]


def commit_budget(ayes):
    """Called once a Budget has passed the Commons: remember the vote and this year's tax rates, reset the whips."""
    s = st.session_state
    s.vote_ayes = ayes
    s.budget_last_tax = dict(s.budget_applied['tax'])
    s.budget_last_pol = {'tax_pol': dict(s.budget_applied['tax_pol']), 'spend_pol': dict(s.budget_applied['spend_pol'])}
    s.budget_impact = {}
    s.whip_ayes = 0
    s.whip_used = []


# ---------------------------------------------------------------- the OBR forecast
def forecast(b, years=3):
    """A central forecast of the next few springs if you deliver draft ``b`` and nothing else happens.

    Uses the same macro rules as the real spring tick (``econ.step``) and the spring debt-interest re-pricing, but
    leaves out crises, random events and the political drags, so treat it as the OBR does: a central case, not a promise.
    """
    s = st.session_state
    ensure()
    imp = impact(s.budget_applied, b)
    v = dict(inflation=round(s.inflation + imp['inflation'], 2), interest_rate=s.interest_rate, gilt_yield=s.gilt_yield,
             growth=round(s.growth + imp['growth'], 2), debt=s.debt, deficit=round(s.deficit + imp['deficit'], 1),
             headroom=round(s.headroom + imp['headroom'], 1), market_conf=round(_clip(s.market_conf + imp['market']), 1),
             approval=round(_clip(s.approval + imp['approval']), 1), cycle=s.get('macro_cycle', 'Stagnation'))
    booked = s.get('budget_interest', BASE_INTEREST)
    now = econ.game_year(s.term, s.year)
    rows = []
    for i in range(1, years + 1):
        new_int = interest_for(v['gilt_yield'], v['debt'])          # spring: debt interest is re-priced...
        drift = new_int - booked
        if abs(drift) > 0.05:
            v['deficit'] = round(v['deficit'] + drift, 1)
            v['headroom'] = round(v['headroom'] - drift, 1)
            booked = new_int
        if v['headroom'] < 0:                                       # ...and a breached rule spooks the markets
            v['market_conf'] = round(_clip(v['market_conf'] - min(4, 0.15 * -v['headroom'])), 1)
        v = econ.step(v, now + i)                                   # ...then the economy moves on
        rows.append(dict(year=imf_outlook.year_for_game(now + i), growth=v['growth'], inflation=v['inflation'],
                         headroom=v['headroom'], deficit=v['deficit'], debt=v['debt'], market=v['market_conf'],
                         gilt=v['gilt_yield']))
    return rows


# ---------------------------------------------------------------- Spring: what carries over into next year
def apply_ongoing():
    s = st.session_state
    ensure()

    # 1. Compound this year's % decisions into permanent baselines
    for k in SPEND_DEFAULTS:
        pct_change = s.budget_applied['spend'].get(k, 0.0)
        s.dept_spend[k] = round(s.dept_spend[k] * (1.0 + pct_change / 100.0), 1)
        s[f'bs_{k}'] = 0.0
        s.budget_applied['spend'][k] = 0.0

    # 2. Update country metrics from departmental funding levels and the schemes still in the Budget
    dv = {k: s.dept_spend[k] - SPEND_DEFAULTS[k]['default'] for k in SPEND_DEFAULTS}
    nudges = {
        'nhs_waiting': -0.004 * dv['health'],
        'nhs_morale': 0.05 * dv['health'],
        'schools': 0.04 * dv['education'],
        'child_poverty': -0.012 * dv['welfare'],
        'homeless': -0.03 * dv['welfare'] - 0.02 * dv['housing'],
        'homes_built': 0.6 * dv['housing'],
        'prisons': -0.05 * dv['justice'],
        'rail': 0.08 * dv['transport'],
        'netzero': 0.06 * dv['climate'],
        'energy_bills': -1.5 * dv['climate'],
    }
    for pk, effects in POLICY_NUDGES.items():
        if s.budget_applied['spend_pol'].get(pk):
            for stat, val in effects.items():
                nudges[stat] = nudges.get(stat, 0.0) + val
    country.nudge(nudges, snapshot=False)

    # 3. Interest check: debt interest re-prices as gilt yields and the debt stock move
    new_interest = interest()
    drift = new_interest - s.get('budget_interest', BASE_INTEREST)
    if abs(drift) > 0.05:
        s.deficit = round(s.deficit + drift, 1)
        s.headroom = round(s.headroom - drift, 1)
        s.budget_interest = new_interest
    if s.headroom < 0:
        s.market_conf = round(_clip(s.market_conf - min(4, 0.15 * -s.headroom)), 1)
        s.message += " ⚠️ Negative OBR headroom: markets punish the breach of your fiscal rules."


# ================================================================ drawing
# Layout: a row of summary chips and the Apply / Reset / Submit buttons stay at the top; the levers live in tabs with
# one line per slider, so the whole Budget fits on screen without scrolling the page.
def _pie(data):
    df = pd.DataFrame([{'Category': str(k), 'Value': float(v)} for k, v in data.items() if float(v) > 0])
    if not df.empty:
        chart = alt.Chart(df).mark_arc(innerRadius=55, outerRadius=105, stroke='#0d1f17', strokeWidth=2).encode(
            theta=alt.Theta(field="Value", type="quantitative"),
            color=alt.Color(field="Category", type="nominal", scale=alt.Scale(range=PALETTE),
                            legend=alt.Legend(title=None, orient='right', labelColor='#efe9da', labelFontSize=11, symbolType='square')),
            tooltip=[alt.Tooltip('Category:N', title='Item'), alt.Tooltip('Value:Q', title='Amount (£bn)', format=',.1f')]
        ).properties(height=240, background='transparent').configure_view(strokeWidth=0)
        st.altair_chart(chart, use_container_width=True)


def _value_html(text, diff, good_when_positive=True, extra=''):
    if abs(diff) < 1e-9:
        colour = '#9fb3a6'
    else:
        colour = '#6fbf8a' if (diff > 0) == good_when_positive else '#e0705d'
    return (f"<div class='lv-val'><b>{text}</b><br>"
            f"<span style='color:{colour}'>{diff:+,.1f}b{extra}</span></div>")


def _tax_row(k, t, s):
    c1, c2, c3 = st.columns([2.2, 3, 1.4])
    with c1:
        st.markdown(f"<div class='lv'>{t['label']}</div>", unsafe_allow_html=True)
    with c2:
        # no value= here: the widget's value comes from session state via its key (passing both makes Streamlit warn)
        st.slider(f"{t['label']} slider", t['lo'], t['hi'], step=t['step'], key=f'bt_{k}', label_visibility="collapsed")
    with c3:
        d = s[f'bt_{k}'] - t['default']
        new_rev = t['base'] + t['per'] * d - t['decay'] * t['per'] * max(d, 0) ** 2
        st.markdown(_value_html(f'£{new_rev:,.1f}b', new_rev - t['base']), unsafe_allow_html=True)


def _spend_row(k, sp, s):
    base = s.dept_spend[k]
    c1, c2, c3 = st.columns([2.2, 3, 1.4])
    with c1:
        st.markdown(f"<div class='lv'>{sp['short']}<br><small>base £{base:,.1f}bn</small></div>", unsafe_allow_html=True)
    with c2:
        st.slider(f"{sp['label']} slider", -15.0, 15.0, step=0.5, key=f'bs_{k}', format="%+.1f%%", label_visibility="collapsed")
    with c3:
        pct = float(s[f'bs_{k}'])
        new_val = base * (1.0 + pct / 100.0)
        st.markdown(_value_html(f'£{new_val:,.1f}b', new_val - base, good_when_positive=True, extra=f' ({pct:+.1f}%)'),
                    unsafe_allow_html=True)


def render_whips(cur):
    s = st.session_state
    st.markdown("**🏛️ The Whips' Office**")
    ayes = projected_ayes(cur)
    st.markdown(f"Backbench morale **{s.backbench_opinion:.0f}/100** · Projected ayes **{ayes}** ({ayes - WIN:+d} vs the {WIN} needed)"
                f" · Whip votes **+{s.get('whip_ayes', 0)}**")
    for _, size, msg in rebel_risks(cur):
        st.warning(f'{msg} (-{size} when the Budget is delivered)')
    if ayes < WIN:
        st.error(f'🚨 PROJECTED DEFEAT: {ayes} votes. A defeated Budget is a vote of no confidence. Soften it, or call in the Whips.')
    elif ayes < WIN + 15:
        st.warning(f'⚠️ A knife-edge: {ayes} votes. A rebellion could sink you.')
    else:
        st.success(f'✅ Projected to pass with {ayes} votes.')
    cols = st.columns(len(WHIPS))
    for col, (k, w) in zip(cols, WHIPS.items()):
        used = k in s.get('whip_used', [])
        col.button('✔ ' + w['label'] if used else w['label'], key=f'whip_{k}', on_click=_whip, args=(k,),
                   disabled=used or not w['can'](s), use_container_width=True, help=w['hint'])
        col.caption(w['hint'])


def render_forecast(cur):
    s = st.session_state
    st.markdown('**🔭 OBR forecast** (a central case: no crises, no surprises)')
    rows = forecast(cur)
    df = pd.DataFrame([{
        'Year': r['year'], 'Growth': f"{r['growth']:.1f}%", 'Inflation': f"{r['inflation']:.1f}%",
        'Headroom': f"£{r['headroom']:.1f}B", 'Deficit': f"£{r['deficit']:.0f}B", 'Debt': f"{r['debt']:.1f}%",
        'Gilts': f"{r['gilt']:.1f}%", 'Markets': f"{r['market']:.0f}%"} for r in rows])
    st.dataframe(df, hide_index=True, use_container_width=True)
    worst = min(r['headroom'] for r in rows)
    if worst < 0:
        st.error(f'❌ Fiscal rule at risk: headroom falls to £{worst:.1f}B. Markets and voters will punish a breach.')
    else:
        st.success(f'✅ Fiscal rule met in every forecast year (lowest headroom £{worst:.1f}B).')
    if rows[-1]['debt'] < s.debt:
        st.success(f"✅ Debt is falling: {s.debt:.1f}% of GDP now, {rows[-1]['debt']:.1f}% by {rows[-1]['year']}.")
    else:
        st.warning(f"⚠️ Debt is not falling: {s.debt:.1f}% of GDP now, {rows[-1]['debt']:.1f}% by {rows[-1]['year']}.")


def render_red_book(cur):
    s = st.session_state
    with st.expander('📕 The Red Book: departmental budgets and tax changes'):
        rows = []
        for k, sp in SPEND_DEFAULTS.items():
            base, start = s.dept_spend[k], sp['default']
            prop = base * (1.0 + cur['spend'][k] / 100.0)
            rows.append({'Department': sp['short'], 'Start of term (£bn)': round(start, 1), 'Baseline now (£bn)': round(base, 1),
                         'This Budget (£bn)': round(prop, 1), 'Change since start': f"{(prop / start - 1) * 100:+.1f}%"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption('Percentage changes compound into next year\'s baseline when spring arrives.')
        last = s.get('budget_last_tax', {})
        trows = []
        for k, tx in TAXES.items():
            was, now = last.get(k, tx['default']), cur['tax'][k]
            trows.append({'Tax': tx['short'], 'Last Budget': f'{was:g}', 'This draft': f'{now:g}',
                          'Change': f'{now - was:+g}', 'Revenue (£bn)': round(revenues(cur)[k], 1)})
        st.markdown('**Taxes: last Budget vs this draft**')
        st.dataframe(pd.DataFrame(trows), hide_index=True, use_container_width=True)


def render(submit=None, after_summary=None):
    """Draw the whole Budget screen. ``submit`` draws the Submit button (it lives in engine land, so app.py passes it in);
    ``after_summary`` draws anything that should sit just under the summary (the manifesto pledge chips)."""
    ensure()
    s = st.session_state
    applied, cur = s.budget_applied, read()
    changed = cur != applied

    rev_now, spend_now = totals(cur)
    rev_app, spend_app = totals(applied)
    bal_now, bal_app = rev_now - spend_now, rev_app - spend_app
    deficit_now = s.deficit + (bal_app - bal_now)     # the running deficit, adjusted for the draft
    imp = impact(applied, cur)
    ayes = projected_ayes(cur)

    def delta(v, unit=''):
        return f'{v:+,.1f}{unit}' if changed else '\u2014'

    render_chips([
        dict(label='Income', value=f'£{rev_now:,.0f}bn', delta=delta(rev_now - rev_app, 'bn'), num=(rev_now - rev_app) if changed else 0,
             desc='Total annual receipts under this draft.'),
        dict(label='Spending', value=f'£{spend_now:,.0f}bn', delta=delta(spend_now - spend_app, 'bn'), num=(spend_now - spend_app) if changed else 0,
             inverse=True, desc='Total annual spending under this draft, including debt interest and pledges.'),
        dict(label='Deficit' if deficit_now > 0 else 'Surplus', value=f'£{abs(deficit_now):,.0f}bn', delta=f'{deficit_now / GDP_BN * 100:.1f}% GDP',
             num=(bal_app - bal_now) if changed else 0, inverse=True, desc='The projected annual deficit (the running figure, adjusted for this draft).'),
        dict(label='Approval', value=f"{_clip(s.approval + imp['approval']):.1f}%", delta=delta(imp['approval']), num=imp['approval'] if changed else 0),
        dict(label='Market conf.', value=f"{_clip(s.market_conf + imp['market']):.1f}%", delta=delta(imp['market']), num=imp['market'] if changed else 0),
        dict(label='Growth', value=f"{s.growth + imp['growth']:.1f}%", delta=(f"{imp['growth']:+.2f}" if changed else '\u2014'),
             num=imp['growth'] if changed else 0),
        dict(label='Inflation', value=f"{s.inflation + imp['inflation']:.1f}%", delta=(f"{imp['inflation']:+.2f}" if changed else '\u2014'),
             num=imp['inflation'] if changed else 0, inverse=True),
        dict(label='OBR headroom', value=f"£{s.headroom + imp['headroom']:.1f}B", delta=delta(imp['headroom']), num=imp['headroom'] if changed else 0,
             desc='How far you are inside your fiscal rules. Below zero is a breach.'),
        dict(label='Projected ayes', value=str(ayes), delta=f'{ayes - WIN:+d} vs {WIN}', num=ayes - WIN,
             desc='Votes for the Budget in the Commons. You need 326.'),
    ])

    b1, b2, b3 = st.columns([1, 1, 3])
    b1.button('Apply Budget', type='primary', on_click=_apply, disabled=not changed)
    b2.button('Reset sliders', on_click=_reset, disabled=not changed)
    with b3:
        if submit:
            submit()
    if after_summary:
        after_summary()

    t_tax, t_spend, t_schemes, t_whips, t_charts = st.tabs(
        ['💷 Taxes', '🏥 Spending', '📜 Schemes', '🏛️ Whips & forecast', '📊 Charts & Red Book'])

    with t_tax:
        groups = {}
        for k, tx in TAXES.items():
            groups.setdefault(tx['group'], []).append((k, tx))
        for col, (group, items) in zip(st.columns(len(groups)), groups.items()):
            with col:
                st.caption(group)
                for k, tx in items:
                    _tax_row(k, tx, s)
        st.caption(f'Tax take {rev_now / GDP_BN * 100:.1f}% of GDP. Raise a rate too far and it stops paying (the Laffer effect).')

    with t_spend:
        items = list(SPEND_DEFAULTS.items())
        half = (len(items) + 1) // 2
        left, right = st.columns(2)
        with left:
            st.caption('Annual change in each budget (-15% to +15%). Changes compound into next year\'s baseline.')
            for k, sp in items[:half]:
                _spend_row(k, sp, s)
        with right:
            st.caption(f'Spending {spend_now / GDP_BN * 100:.1f}% of GDP. Debt interest (£{interest():,.1f}bn, '
                       f'{interest() / rev_now * 100:.1f}% of receipts) follows gilt yields, not departments.')
            for k, sp in items[half:]:
                _spend_row(k, sp, s)

    with t_schemes:
        left, right = st.columns(2)
        with left:
            st.markdown('**Revenue raising schemes**')
            for k, p in TAX_POLICIES.items():
                st.checkbox(f"{p['label']} (+£{p['yield_bn']}bn)", key=f"btp_{k}",
                            help=f"Approval {p['app']:+g}, market confidence {p['mkt']:+g}, growth {p['gro']:+g}pp")
        with right:
            st.markdown('**Spending pledges**')
            for k, p in SPEND_POLICIES.items():
                st.checkbox(f"{p['label']} (-£{p['cost_bn']}bn)", key=f"bsp_{k}",
                            help=f"Approval {p['app']:+g}, market confidence {p['mkt']:+g}, growth {p['gro']:+g}pp")

    with t_whips:
        left, right = st.columns(2)
        with left:
            render_forecast(cur)
        with right:
            render_whips(cur)

    with t_charts:
        p1, p2 = st.columns(2)
        with p1:
            st.markdown('**Where the money comes from**')
            _pie(revenue_pie(cur))
        with p2:
            st.markdown('**Where the money goes**')
            _pie(spending_pie(cur))
        render_red_book(cur)
    
