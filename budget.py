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
GDP_BN = 3125.0          # nominal GDP used for the Red Book's '% of GDP' lines (tax take 36.8% at the defaults)

SPEND_DEFAULTS = {
    'welfare':   dict(label='Welfare & pensions', short='Welfare & pensions', default=330.0),
    'health':    dict(label='NHS & health', short='NHS & health', default=215.0),
    'education': dict(label='Education', short='Education', default=125.0),
    'defence':   dict(label='Defence', short='Defence', default=62.0),
    'transport': dict(label='Transport & infrastructure', short='Transport & infrastructure', default=48.0),
    'justice':   dict(label='Policing, courts & prisons', short='Policing, courts & prisons', default=45.0),
    'housing':   dict(label='Housing & local government', short='Housing & local government', default=60.0),
    'climate':   dict(label='Climate, energy & industry', short='Climate, energy & industry', default=35.0),
    'science':   dict(label='Science, research & innovation', short='Science & research', default=14.0),
    'aid':       dict(label='Overseas aid', short='Overseas aid', default=13.0),
    'culture':   dict(label='Culture, media & sport', short='Culture, media & sport', default=8.0),
    'other':     dict(label='Other departments & admin', short='Other departments & admin', default=95.0),
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
        s.budget_interest = BASE_INTEREST
    else:
        _migrate_applied(s.budget_applied)
    s.setdefault('budget_interest', BASE_INTEREST)
    s.setdefault('budget_last_tax', dict(s.budget_applied['tax']))
    for k in TAXES:
        s.budget_last_tax.setdefault(k, TAXES[k]['default'])
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
             approval=round(_clip(s.approval + imp['approval']), 1))
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
                         headroom=v['headroom'], debt=v['debt'], market=v['market_conf'], gilt=v['gilt_yield']))
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
def _pie(data):
    df = pd.DataFrame([{'Category': str(k), 'Value': float(v)} for k, v in data.items() if float(v) > 0])
    if not df.empty:
        chart = alt.Chart(df).mark_arc(innerRadius=65, outerRadius=125, stroke='#0d1f17', strokeWidth=2).encode(
            theta=alt.Theta(field="Value", type="quantitative"),
            color=alt.Color(field="Category", type="nominal", scale=alt.Scale(range=PALETTE),
                            legend=alt.Legend(title=None, orient='right', labelColor='#efe9da', labelFontSize=12, symbolType='square')),
            tooltip=[alt.Tooltip('Category:N', title='Item'), alt.Tooltip('Value:Q', title='Amount (£bn)', format=',.1f')]
        ).properties(height=300, background='transparent').configure_view(strokeWidth=0)
        st.altair_chart(chart, use_container_width=True)


def _tax_row(k, t, s):
    st.markdown(f"**{t['label']}**")
    c1, c2 = st.columns([3, 1])
    with c1:
        # no value= here: the widget's value comes from session state via its key (passing both makes Streamlit warn)
        st.slider(f"{t['label']} slider", t['lo'], t['hi'], step=t['step'], key=f'bt_{k}', label_visibility="collapsed")
    with c2:
        d = s[f'bt_{k}'] - t['default']
        new_rev = t['base'] + t['per'] * d - t['decay'] * t['per'] * max(d, 0) ** 2
        diff_rev = new_rev - t['base']
        color = '#6fbf8a' if diff_rev > 0 else '#e0705d' if diff_rev < 0 else '#9fb3a6'
        st.markdown(f"<div style='text-align:right; font-size:1.1rem; line-height:1.2;'><b>£{new_rev:,.1f}b</b><br>"
                    f"<span style='color:{color}; font-size:0.85rem;'>{diff_rev:+,.1f}b</span></div>", unsafe_allow_html=True)


def _spend_row(k, sp, s):
    base = s.dept_spend[k]
    st.markdown(f"**{sp['label']}** (Current base: £{base:,.1f}bn)")
    c1, c2 = st.columns([3, 1])
    with c1:
        st.slider(f"{sp['label']} slider", -15.0, 15.0, step=0.5, key=f'bs_{k}', format="%+.1f%%", label_visibility="collapsed")
    with c2:
        pct = float(s[f'bs_{k}'])
        new_val = base * (1.0 + pct / 100.0)
        diff = new_val - base
        color = '#e0705d' if diff < 0 else '#6fbf8a' if diff > 0 else '#9fb3a6'
        st.markdown(f"<div style='text-align:right; font-size:1.1rem; line-height:1.2;'><b>£{new_val:,.1f}b</b><br>"
                    f"<span style='color:{color}; font-size:0.85rem;'>{diff:+,.1f}b ({pct:+.1f}%)</span></div>", unsafe_allow_html=True)


def render_whips(cur):
    s = st.session_state
    st.markdown("#### 🏛️ The Whips' Office")
    st.caption('The Budget needs 326 ayes. Upset your own side and morale falls before the vote; the Whips can buy votes at a price.')
    ayes = projected_ayes(cur)
    m1, m2, m3 = st.columns(3)
    m1.metric('Backbench morale', f'{s.backbench_opinion:.0f}/100')
    m2.metric('Projected ayes', f'{ayes}', f'{ayes - WIN:+d} vs the {WIN} needed')
    m3.metric('Whip interventions', f"+{s.get('whip_ayes', 0)} votes")
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
                   disabled=used or not w['can'](s), use_container_width=True)
        col.caption(w['hint'])


def render_forecast(cur):
    s = st.session_state
    st.markdown('#### 🔭 OBR Forecast')
    st.caption('A central forecast of the next three springs if you deliver this Budget and nothing else happens: no crises, '
               'no surprises. The real thing will be bumpier.')
    rows = forecast(cur)
    df = pd.DataFrame([{
        'Year': r['year'], 'GDP growth': f"{r['growth']:.1f}%", 'Inflation': f"{r['inflation']:.1f}%",
        'OBR headroom': f"£{r['headroom']:.1f}B", 'National debt': f"{r['debt']:.1f}% GDP",
        'Gilt yield': f"{r['gilt']:.1f}%", 'Market confidence': f"{r['market']:.0f}%"} for r in rows])
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
    with st.expander('📕 The Red Book: departmental budgets'):
        rows = []
        for k, sp in SPEND_DEFAULTS.items():
            base, start = s.dept_spend[k], sp['default']
            prop = base * (1.0 + cur['spend'][k] / 100.0)
            rows.append({'Department': sp['short'], 'Start of term (£bn)': round(start, 1), 'Baseline now (£bn)': round(base, 1),
                         'This Budget (£bn)': round(prop, 1), 'Change since start': f"{(prop / start - 1) * 100:+.1f}%"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption('Percentage changes compound into next year\'s baseline when spring arrives.')


def render():
    ensure()
    s = st.session_state
    applied, cur = s.budget_applied, read()
    changed = cur != applied

    rev_now, spend_now = totals(cur)
    rev_app, spend_app = totals(applied)
    bal_now, bal_app = rev_now - spend_now, rev_app - spend_app

    m1, m2, m3 = st.columns(3)
    m1.metric('Total income', f'£{rev_now:,.0f}bn', f'{rev_now - rev_app:+,.1f}bn' if changed else None)
    m2.metric('Total spending', f'£{spend_now:,.0f}bn', f'{spend_now - spend_app:+,.1f}bn' if changed else None, delta_color='inverse')
    label = 'Surplus' if bal_now >= 0 else 'Deficit'
    m3.metric(f'Budget {label.lower()}', f'£{abs(bal_now):,.1f}bn', f'{bal_now - bal_app:+,.1f}bn' if changed else None)

    r1, r2, r3 = st.columns(3)
    r1.metric('Tax take', f'{rev_now / GDP_BN * 100:.1f}% of GDP', f'{(rev_now - rev_app) / GDP_BN * 100:+.1f}pp' if changed else None, delta_color='off')
    r2.metric('Public spending', f'{spend_now / GDP_BN * 100:.1f}% of GDP', f'{(spend_now - spend_app) / GDP_BN * 100:+.1f}pp' if changed else None, delta_color='off')
    r3.metric('Interest as a share of receipts', f'{interest() / rev_now * 100:.1f}%')

    left, right = st.columns(2)

    with left:
        st.markdown('#### Taxes')
        group = None
        for k, t in TAXES.items():
            if t['group'] != group:
                group = t['group']
                st.caption(group)
            _tax_row(k, t, s)

        st.markdown("---")
        st.markdown('#### Revenue Raising Schemes')
        for k, p in TAX_POLICIES.items():
            st.checkbox(f"{p['label']} (+£{p['yield_bn']}bn)", key=f"btp_{k}",
                        help=f"Approval {p['app']:+g}, market confidence {p['mkt']:+g}, growth {p['gro']:+g}pp")

    with right:
        st.markdown('#### Department Spending (Annual % Change)')
        st.caption('Set annual spending growth or cuts (-15% to +15%). Changes compound into baseline budgets each year.')
        for k, sp in SPEND_DEFAULTS.items():
            _spend_row(k, sp, s)

        st.markdown("---")
        st.markdown('#### Spending Pledges')
        for k, p in SPEND_POLICIES.items():
            st.checkbox(f"{p['label']} (-£{p['cost_bn']}bn)", key=f"bsp_{k}",
                        help=f"Approval {p['app']:+g}, market confidence {p['mkt']:+g}, growth {p['gro']:+g}pp")

    st.caption(f'Debt interest (£{interest():,.1f}bn) is set by gilt yields and total debt stock, not by departmental budgets.')

    imp = impact(applied, cur)
    st.markdown('#### Projected impact' if changed else '#### Impact of your current budget')
    c = st.columns(6)
    c[0].metric('Public Approval', f"{_clip(s.approval + imp['approval']):.1f}%", f"{imp['approval']:+.1f}")
    c[1].metric('Market Confidence', f"{_clip(s.market_conf + imp['market']):.1f}%", f"{imp['market']:+.1f}")
    c[2].metric('Economic Growth', f"{s.growth + imp['growth']:.1f}%", f"{imp['growth']:+.2f}")
    c[3].metric('Inflation', f"{s.inflation + imp['inflation']:.1f}%", f"{imp['inflation']:+.2f}", delta_color='inverse')
    c[4].metric('OBR Headroom', f"£{s.headroom + imp['headroom']:.1f}B", f"{imp['headroom']:+.1f}")
    c[5].metric('Annual Deficit', f"£{s.deficit + imp['deficit']:.1f}B", f"{imp['deficit']:+.1f}", delta_color='inverse')

    b1, b2, _ = st.columns([1, 1, 3])
    b1.button('Apply Budget', type='primary', on_click=_apply, disabled=not changed)
    b2.button('Reset sliders', on_click=_reset, disabled=not changed)

    st.caption('Departmental funding levels also nudge the State of the Nation indicators across turns.')

    render_forecast(cur)
    render_whips(cur)
    render_red_book(cur)

    p1, p2 = st.columns(2)
    with p1:
        st.markdown('#### Where the money comes from')
        _pie(revenue_pie(cur))
    with p2:
        st.markdown('#### Where the money goes')
        _pie(spending_pie(cur))
