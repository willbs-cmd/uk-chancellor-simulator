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
from content_store import load_json
from theme import render_chips
# Game-editable fiscal controls and policy choices live in data/policies.json.
_POLICY_DATA = load_json('policies.json')
TAXES = _POLICY_DATA['taxes']
TAX_POLICIES = _POLICY_DATA['tax_policies']
SPEND_DEFAULTS = _POLICY_DATA['spend_defaults']
SPEND_POLICIES = _POLICY_DATA['spend_policies']
POLICY_NUDGES = _POLICY_DATA['policy_nudges']
OTHER_RECEIPTS = float(_POLICY_DATA['other_receipts'])
GDP_BN = float(_POLICY_DATA['gdp_bn'])
BASE_INTEREST = float(_POLICY_DATA['base_interest'])

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


FISCAL_STRATEGIES = {
    'balanced': {'label':'Balanced books', 'description':'Protect credibility and keep borrowing under control.', 'headroom':0.4,'approval':0.2,'market':0.2,'growth':0.02},
    'investment': {'label':'Investment-led growth', 'description':'Borrow for productive investment and accept weaker near-term headroom.', 'headroom':-1.2,'approval':1.5,'market':-0.5,'growth':0.12},
    'austerity': {'label':'Spending restraint', 'description':'Prioritise deficit reduction, with a political and growth cost.', 'headroom':1.5,'approval':-1.8,'market':0.7,'growth':-0.08},
    'tax_cuts': {'label':'Tax-cutting growth', 'description':'Prioritise household and business incentives at the expense of receipts.', 'headroom':-1.0,'approval':1.0,'market':-0.5,'growth':0.08},
    'redistribution': {'label':'Redistribution & public services', 'description':'Prioritise fairness and frontline services, requiring more revenue or borrowing.', 'headroom':-1.3,'approval':1.8,'market':-0.3,'growth':0.01},
}

def defaults():
    return {
        'strategy': 'balanced',
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
    s.setdefault('budget_message', '')
    s.setdefault('whip_ayes', 0)
    s.setdefault('whip_used', [])

    for k, v in s.budget_applied['tax'].items(): s.setdefault(f'bt_{k}', v)
    for k, v in s.budget_applied['spend'].items(): s.setdefault(f'bs_{k}', float(v))
    for k, v in s.budget_applied['tax_pol'].items(): s.setdefault(f'btp_{k}', v)
    for k, v in s.budget_applied['spend_pol'].items(): s.setdefault(f'bsp_{k}', v)


def read():
    s = st.session_state
    return {
        'strategy': s.get('budget_strategy', s.budget_applied.get('strategy', 'balanced')),
        'tax': {k: s[f'bt_{k}'] for k in TAXES},
        'spend': {k: float(s[f'bs_{k}']) for k in SPEND_DEFAULTS},
        'tax_pol': {k: s[f'btp_{k}'] for k in TAX_POLICIES},
        'spend_pol': {k: s[f'bsp_{k}'] for k in SPEND_POLICIES},
    }


def revenues(b):
    out = {}
    for k, t in TAXES.items():
        d = b['tax'][k] - t['default']
        base_receipt = t['base'] + t['per'] * d - t['decay'] * t['per'] * max(d, 0) ** 2
        # A larger nominal economy expands the underlying income, profits and spending tax bases.
        out[k] = base_receipt * float(st.session_state.get('tax_base_index', 1.0))
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
    # Frozen thresholds create extra receipts through fiscal drag; this is separate from changing a tax rate.
    if s.get('thresholds_frozen', False):
        drag_rate = 0.35 if s.get('threshold_freeze_scope', 'Personal allowance and all bands') == 'Personal allowance and all bands' else 0.25
        rev += min(1.5, drag_rate * float(s.get('threshold_freeze_years', 0)))
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
    old_st = FISCAL_STRATEGIES.get(old.get('strategy', 'balanced'), FISCAL_STRATEGIES['balanced'])
    new_st = FISCAL_STRATEGIES.get(new.get('strategy', 'balanced'), FISCAL_STRATEGIES['balanced'])
    sd = {k: new_st[k] - old_st[k] for k in ('headroom','approval','market','growth')}
    bal += sd['headroom']

    household = (d['income'] + d['income_higher'] + d['income_additional'] + d['ni'] + d['vat'] + d['fuel'] + d['sin']
                 + d['council_tax'] + d['sugar_duty'])
    wealth = d['property'] + d['cgt'] + d['iht'] + d['land_value'] + d['financial_transaction']
    vat_pts = new['tax']['vat'] - old['tax']['vat']

    approval = (-0.10 * household - 0.03 * wealth
                + 0.05 * (ds['health'] + ds['education']) + 0.03 * ds['welfare']
                + 0.02 * (ds['justice'] + ds['housing'] + ds['transport']) + 0.01 * ds['defence']
                + 0.01 * (ds['science'] + ds['culture']) - 0.01 * ds['aid'])
    market = (max(-8, min(8, 0.10 * bal)) - 0.25 * d['corp'] - 0.12 * d['property']
              - 0.10 * d['cgt'] - 0.05 * d['iht']
              - 0.08 * d['land_value'] - 0.06 * d['financial_transaction'] - 0.04 * d['carbon_levy'])
    growth = (-0.012 * d['corp'] - 0.006 * d['ni'] - 0.004 * d['income'] - 0.003 * d['income_higher'] - 0.002 * d['income_additional'] - 0.008 * d['cgt'] - 0.003 * d['land_value']
              - 0.012 * d['financial_transaction'] - 0.015 * d['carbon_levy'] - 0.001 * d['sugar_duty'] - 0.002 * d['council_tax']
              + 0.008 * (ds['transport'] + ds['housing'] + ds['climate']) + 0.012 * ds['science']
              + 0.002 * (ds['health'] + ds['education'] + ds['other'] + ds['welfare'] + ds['culture'])
              + 0.001 * ds['defence'])

    for key, table in (('tax_pol', TAX_POLICIES), ('spend_pol', SPEND_POLICIES)):
        for k, p in table.items():
            if new[key][k] and not old[key][k]:
                approval += p['app']; market += p['mkt']; growth += p['gro']
            elif not new[key][k] and old[key][k]:
                approval -= p['app']; market -= p['mkt']; growth -= p['gro']

    inflation = (0.12 * vat_pts + 0.003 * sum(ds.values()) + 0.015 * d['fuel'] + 0.005 * d['sin']
                 + 0.004 * d['carbon_levy'] + 0.002 * d['sugar_duty'])

    return dict(headroom=bal, deficit=-bal, approval=approval + sd['approval'], market=market + sd['market'],
                growth=growth + sd['growth'], inflation=inflation,
                real_wages=-0.010 * d['income'] - 0.006 * d['ni'] - 0.004 * d['fuel'] - 0.002 * d['council_tax'] - 0.001 * d['sugar_duty'],
                unemployment=0.010 * d['ni'] + 0.004 * d['corp'] + 0.001 * d['financial_transaction'])


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
    s.budget_strategy = new.get('strategy', 'balanced')
    acc = dict(s.get('budget_impact') or {})
    for k, v in imp.items():
        acc[k] = round(acc.get(k, 0.0) + v, 4)
    s.budget_impact = acc
    verb = 'improves' if imp['headroom'] >= 0 else 'worsens'
    s.message = f"Budget delivered. It {verb} public finances by £{abs(imp['headroom']):.1f}B a year."


def _reset():
    s = st.session_state
    s.budget_strategy = s.budget_applied.get('strategy', 'balanced')
    s.budget_message = ''
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
             approval=round(_clip(s.approval + imp['approval']), 1), cycle=s.get('macro_cycle', 'Stagnation'),
             gdp_trillion=float(s.get('gdp_trillion', 3.0)))
    booked = s.get('budget_interest', BASE_INTEREST)
    now = econ.game_year(s.term, s.year)
    tax_index = float(s.get('tax_base_index', 1.0))
    tax_receipts_base = sum(revenues(b).values()) / max(0.01, tax_index)
    portfolio = {k: float(v) for k, v in s.get('treasury_assets', {}).items()}
    demographic_pressure = float(s.get('demographic_pressure', 0.0))
    pension_pressure = float(s.get('pension_pressure', 0.0))
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
        nominal_growth = ((1 + v['growth'] / 100.0) * (1 + v['inflation'] / 100.0) - 1) * 100
        next_index = max(0.55, tax_index * (1 + max(-8.0, min(12.0, nominal_growth * 0.85)) / 100.0))
        gross_growth_receipts = tax_receipts_base * (next_index - tax_index)
        # Mirror the live Treasury rule: only 30% of positive buoyancy is free
        # fiscal space after baseline spending pressures; recession losses pass through fully.
        growth_receipts = gross_growth_receipts * 0.30 if gross_growth_receipts > 0 else gross_growth_receipts
        tax_index = next_index
        market_factor = max(0.55, min(1.15, 0.75 + v['market_conf'] / 200.0))
        investment_income = 0.0
        from treasury import ASSETS
        for key, amount in list(portfolio.items()):
            spec = ASSETS.get(key)
            if spec and amount > 0:
                investment_income += amount * (spec['yield'] * market_factor - 0.005)
                portfolio[key] = amount * (1 + spec['appreciation'] * market_factor)
        investment_income = max(0.0, investment_income)
        extra_receipts = growth_receipts + investment_income
        # Match the annual Treasury and demographic costs applied in the live spring tick.
        nhs_pressure = round(0.45 + 0.10 * max(0.0, v['inflation'] - 2.0) + 0.025 * demographic_pressure, 2)
        public_pay_pressure = round(0.40 + 0.12 * max(0.0, v['inflation'] - 2.0)
                                    + 0.015 * max(0.0, 2.0 - v['growth']), 2)
        demographic_pressure = round(demographic_pressure + 0.6, 1)
        pension_pressure = round(pension_pressure + 0.2 * demographic_pressure, 2)
        pension_cost = round(0.25 * pension_pressure, 2)
        recurring_costs = round(nhs_pressure + public_pay_pressure + pension_cost, 2)
        net_fiscal_change = round(extra_receipts - recurring_costs, 2)
        v['headroom'] = round(v['headroom'] + net_fiscal_change, 1)
        v['deficit'] = round(max(0.0, v['deficit'] - net_fiscal_change), 1)
        rows.append(dict(year=imf_outlook.year_for_game(now + i), growth=v['growth'], inflation=v['inflation'],
                         headroom=v['headroom'], deficit=v['deficit'], debt=v['debt'], market=v['market_conf'],
                         gilt=v['gilt_yield'], gilt_risk_premium=v.get('gilt_risk_premium', 0.0),
                         debt_interest=round(interest_for(v['gilt_yield'], v['debt']), 1),
                         growth_receipts=round(growth_receipts, 2),
                         investment_income=round(investment_income, 2), nhs_pressure=nhs_pressure,
                         public_pay_pressure=public_pay_pressure, pension_cost=pension_cost,
                         recurring_costs=recurring_costs, net_fiscal_change=net_fiscal_change))
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


def _tax_slider_spec(t):
    """Return compatible numeric types for the slider's min/max/step arguments."""
    step = t['step']
    if isinstance(step, float) and not step.is_integer():
        return float(t['lo']), float(t['hi']), float(step)
    return int(t['lo']), int(t['hi']), int(step)


def _tax_row(k, t, s):
    c1, c2, c3 = st.columns([2.2, 3, 1.4], gap='small')
    with c1:
        st.markdown(f"<div class='lv'>{t['label']}</div>", unsafe_allow_html=True)
    with c2:
        lo, hi, step = _tax_slider_spec(t)
        key = f'bt_{k}'
        if isinstance(step, float) and key in s and not isinstance(s[key], float):
            # Cast saved/default values before creating the slider widget.
            s[key] = float(s[key])
        st.slider(
            f"{t['label']} slider", min_value=lo, max_value=hi, step=step,
            key=key, label_visibility="collapsed",
            help=t.get('help', 'Changing this rate changes estimated annual receipts. Higher rates can reduce the tax base or discourage activity.')
        )
    with c3:
        d = float(s[f'bt_{k}']) - float(t['default'])
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
        'Net growth dividend': f"£{r['growth_receipts']:.1f}B", 'Investment income': f"£{r['investment_income']:.1f}B",
        'Headroom': f"£{r['headroom']:.1f}B", 'Deficit': f"£{r['deficit']:.0f}B", 'Debt': f"{r['debt']:.1f}%",
        'Gilts': f"{r['gilt']:.1f}%", 'Risk premium': f"+{r['gilt_risk_premium']:.2f}pp",
        'Debt interest': f"£{r['debt_interest']:.1f}B", 'Markets': f"{r['market']:.0f}%"} for r in rows])
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
    s.budget_strategy = cur.get('strategy', 'balanced')

    rev_now, spend_now = totals(cur)
    rev_app, spend_app = totals(applied)
    bal_now, bal_app = rev_now - spend_now, rev_app - spend_app
    deficit_now = s.deficit + (bal_app - bal_now)     # the running deficit, adjusted for the draft
    imp = impact(applied, cur)
    ayes = projected_ayes(cur)

    def delta(v, unit=''):
        return f'{v:+,.1f}{unit}' if changed else '\u2014'

    st.markdown(
        f"<div class='budget-command-line'><div><span class='budget-kicker'>THE RED BOOK · FISCAL STATEMENT</span><strong>Budget control panel</strong><small>Annual forecast · £ billions · Draft figures update as you change policy</small></div><span class='budget-state {'is-draft' if changed else 'is-baseline'}'>{'● UNSAVED DRAFT' if changed else '● BASELINE'}</span></div>",
        unsafe_allow_html=True,
    )
    render_chips([
        dict(label='Income', value=f'£{rev_now:,.0f}bn', delta=delta(rev_now - rev_app, 'bn'), num=(rev_now - rev_app) if changed else 0,
             desc='Estimated annual tax and other receipts received by the government.'),
        dict(label='Spending', value=f'£{spend_now:,.0f}bn', delta=delta(spend_now - spend_app, 'bn'), num=(spend_now - spend_app) if changed else 0,
             inverse=True, desc='Estimated annual outgoings across departments, welfare, pensions, debt interest and selected schemes.'),
        dict(label='Deficit' if deficit_now > 0 else 'Surplus', value=f'£{abs(deficit_now):,.0f}bn', delta=f'{deficit_now / GDP_BN * 100:.1f}% GDP',
             num=(bal_app - bal_now) if changed else 0, inverse=True, desc='The gap between annual spending and income. A surplus means income exceeds spending.'),
        dict(label='Approval', value=f"{_clip(s.approval + imp['approval']):.1f}%", delta=delta(imp['approval']), num=imp['approval'] if changed else 0,
             desc='Estimated public support for the government. It affects polling and political survival.'),
        dict(label='Market conf.', value=f"{_clip(s.market_conf + imp['market']):.1f}%", delta=delta(imp['market']), num=imp['market'] if changed else 0,
             desc='Investor confidence. Weak confidence can raise government borrowing costs and make new debt more expensive.'),
        dict(label='Growth', value=f"{s.growth + imp['growth']:.1f}%", delta=(f"{imp['growth']:+.2f}" if changed else '\u2014'),
             num=imp['growth'] if changed else 0, desc='The annual rate at which the economy produces more goods and services, after adjusting for inflation.'),
        dict(label='Inflation', value=f"{s.inflation + imp['inflation']:.1f}%", delta=(f"{imp['inflation']:+.2f}" if changed else '\u2014'),
             num=imp['inflation'] if changed else 0, inverse=True, desc='How quickly prices are rising. High inflation squeezes household budgets and can keep interest rates elevated.'),
        dict(label='OBR headroom', value=f"£{s.headroom + imp['headroom']:.1f}B", delta=delta(imp['headroom']), num=imp['headroom'] if changed else 0,
             desc='The amount of fiscal room left before your chosen fiscal rule is breached. Negative headroom means the rule is missed.'),
        dict(label='Projected ayes', value=str(ayes), delta=f'{ayes - WIN:+d} vs {WIN}', num=ayes - WIN,
             desc='Votes for the Budget in the Commons. You need 326.'),
    ])

    st.markdown('### Choose your fiscal strategy')
    strategy_keys = list(FISCAL_STRATEGIES)
    st.selectbox('Overall approach', strategy_keys, format_func=lambda k: FISCAL_STRATEGIES[k]['label'], index=strategy_keys.index(s.budget_strategy), key='budget_strategy')
    st.caption(FISCAL_STRATEGIES[s.budget_strategy]['description'] + ' Its effects feed into the draft and forecast.')
    st.text_input("Chancellor's message to the country (optional)", key='budget_message', max_chars=180, placeholder='e.g. A fair deal for working people and a stronger economy')
    with st.expander('ℹ️ Budget glossary: what the figures mean', expanded=False):
        g1, g2, g3 = st.columns(3, gap='medium')
        with g1:
            st.markdown('**Income** — money government expects to collect. **Spending** — money paid across services, benefits, pensions and debt interest.')
            st.markdown('**Deficit / surplus** — deficit means spending is higher than income; surplus means income is higher.')
            st.markdown('**Fiscal headroom** — the safety margin against the fiscal rule. Below £0B means the forecast breaks that rule.')
        with g2:
            st.markdown('**Public approval** — a simplified measure of voters’ support; it feeds into polls and political stability.')
            st.markdown('**Market confidence** — a simplified investor-confidence score. Falling confidence can make government borrowing more expensive.')
            st.markdown('**Growth** — change in real economic output. **Inflation** — the rate prices rise; high inflation reduces purchasing power.')
        with g3:
            st.markdown('**Projected ayes** — estimated MPs voting for the Budget. The model uses 326 as the majority threshold.')
            st.markdown('**OBR forecast** — a central-case projection, not a guarantee; it assumes no new crisis or surprise.')
            st.markdown('**Laffer effect** — raising a tax rate can eventually reduce extra revenue if behaviour changes or activity falls.')

    with st.container(key="budget_actions"):
        apply_col, reset_col = st.columns(2, gap="medium")
        apply_col.button(
            "Apply Budget", type="primary", on_click=_apply,
            disabled=not changed, use_container_width=True,
            help="Apply the current slider values to the draft forecast."
        )
        reset_col.button(
            "Reset sliders", on_click=_reset,
            disabled=not changed, use_container_width=True,
            help="Return tax rates, spending changes and schemes to the previously applied draft."
        )
        # Submission sits on its own full-width row so the label never gets clipped
        # by a narrow third column, especially on mobile.
        if submit:
            submit()
    if after_summary:
        after_summary()

    t_tax, t_spend, t_schemes, t_whips, t_charts = st.tabs(
        ['Taxes', 'Spending', 'Schemes', 'Whips & forecast', 'Charts & Red Book'])

    with t_tax:
        st.caption('Income-tax rates are marginal: each rate applies only to income inside its band. Threshold freezes are controlled in Fiscal tools. Each group opens separately to keep the Budget usable on smaller screens.')
        groups = {}
        for k, tx in TAXES.items():
            groups.setdefault(tx['group'], []).append((k, tx))
        for ix, (group, items) in enumerate(groups.items()):
            with st.expander(f"{group} · {len(items)} controls", expanded=(ix == 0)):
                for k, tx in items:
                    _tax_row(k, tx, s)
        st.caption(f'Tax take {rev_now / GDP_BN * 100:.1f}% of GDP. The Laffer effect is a simplified game rule: very high rates may raise less extra revenue than expected.')

    with t_spend:
        st.caption(f"Adjust department budgets against today's baseline. The draft changes compound into next year's baseline. Total draft spending is {spend_now / GDP_BN * 100:.1f}% of GDP; debt interest is £{interest():,.1f}bn ({interest() / rev_now * 100:.1f}% of receipts).")
        spend_groups = [
            ("People & frontline services", ["welfare", "health", "education", "justice", "defence"]),
            ("Infrastructure & transition", ["transport", "housing", "climate"]),
            ("Science, culture & other", ["science", "aid", "culture", "other"]),
        ]
        for group, keys in spend_groups:
            with st.expander(f"{group} · {len(keys)} departments", expanded=False):
                for k in keys:
                    if k in SPEND_DEFAULTS:
                        _spend_row(k, SPEND_DEFAULTS[k], s)

    with t_schemes:
        with st.expander(f"Revenue-raising schemes · {len(TAX_POLICIES)} options", expanded=False):
            st.caption("Select policy ideas that affect annual receipts. Hover over an option for the simplified approval, market and growth effects.")
            for k, p in TAX_POLICIES.items():
                st.checkbox(f"{p['label']} (+£{p['yield_bn']}bn)", key=f"btp_{k}",
                            help=f"Estimated annual yield: £{p['yield_bn']:.1f}bn. Approval {p['app']:+g}, market confidence {p['mkt']:+g}, growth {p['gro']:+g}pp.")
        with st.expander(f"Spending pledges · {len(SPEND_POLICIES)} options", expanded=False):
            st.caption("Choose programmes that add recurring costs to the Budget. These are stylised scenario costs, not official costings.")
            for k, p in SPEND_POLICIES.items():
                st.checkbox(f"{p['label']} (-£{p['cost_bn']}bn)", key=f"bsp_{k}",
                            help=f"Annual cost: £{p['cost_bn']:.1f}bn. Approval {p['app']:+g}, market confidence {p['mkt']:+g}, growth {p['gro']:+g}pp.")

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

    
