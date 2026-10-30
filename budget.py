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
        if not isinstance(dflt, dict):
            applied.setdefault(section, dflt)
            continue
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



def _reset_spending_draft():
    """Discard only departmental draft changes and restore the last approved allocation."""
    s = st.session_state
    ensure()
    for k in SPEND_DEFAULTS:
        s[f'bs_{k}'] = float(s.budget_applied.get('spend', {}).get(k, 0.0))


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

    # A Budget's tax settings and policy choices are recurring settings. Department
    # percentages are annual changes, so compound them once and then start the next
    # year's draft at zero against the newly approved departmental baseline.
    for k in SPEND_DEFAULTS:
        pct_change = float(s.budget_applied['spend'].get(k, 0.0))
        s.dept_spend[k] = round(float(s.dept_spend[k]) * (1.0 + pct_change / 100.0), 1)
        s[f'bs_{k}'] = 0.0
        s.budget_applied['spend'][k] = 0.0

    # Preserve the approved tax rates, strategy and policy selections across years.
    # Only reset one-off whip interventions and the cumulative delivery ledger.
    s.budget_strategy = s.budget_applied.get('strategy', s.get('budget_strategy', 'balanced'))
    s.budget_impact = {}
    s.budget_message = ''

    # Rebuild the next-year widget state from the approved ledger. This prevents
    # stale Streamlit widget values from overwriting the approved settings.
    for k, value in s.budget_applied['tax'].items():
        s[f'bt_{k}'] = value
    for k, value in s.budget_applied['tax_pol'].items():
        s[f'btp_{k}'] = bool(value)
    for k, value in s.budget_applied['spend_pol'].items():
        s[f'bsp_{k}'] = bool(value)

    # 2. Update country metrics from the approved departmental funding levels.
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

    # 3. Interest check: reprice debt interest only against the last recorded bill.
    new_interest = interest()
    drift = new_interest - float(s.get('budget_interest', BASE_INTEREST))
    if abs(drift) > 0.05:
        s.deficit = round(s.deficit + drift, 1)
        s.headroom = round(s.headroom - drift, 1)
        s.budget_interest = new_interest
    if s.headroom < 0:
        s.market_conf = round(_clip(s.market_conf - min(4, 0.15 * -s.headroom)), 1)
        s.message += " ⚠️ Negative OBR headroom: markets punish the breach of your fiscal rules."



