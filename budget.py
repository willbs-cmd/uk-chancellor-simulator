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

# Fictional Cabinet roster used by the simulation.
DEPARTMENT_MINISTERS = {
    "health": ("Dr Eleanor Shaw", "NHS waiting lists and hospital capacity"),
    "education": ("James Whitfield", "school buildings and teacher retention"),
    "welfare": ("Amira Patel", "child poverty and welfare reform"),
    "justice": ("Robert Hales", "prison capacity and court backlogs"),
    "defence": ("Dame Victoria Ashford", "readiness, equipment and NATO commitments"),
    "transport": ("Daniel Mercer", "rail reliability and regional connectivity"),
    "housing": ("Sophie Bennett", "housebuilding and affordable homes"),
    "science": ("Professor Michael Grant", "research funding and productivity"),
    "climate": ("Leila Morgan", "clean energy investment and net zero"),
    "aid": ("Oliver Pembroke", "international development commitments"),
    "culture": ("Catherine Ellis", "museums, arts and national heritage"),
    "other": ("Thomas Reed", "local government and cross-department services"),
    "social_care": ("Helen Foster", "adult social care capacity and support for unpaid carers"),
    "local_government": ("Marcus Bell", "council finances, local services and financial resilience"),
    "public_sector_pay": ("Rachel Okafor", "workforce retention and fair public-sector pay settlements"),
    "skills": ("Dr Peter Lawson", "further education, apprenticeships and technical skills"),
}
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
    s.setdefault("cabinet_ministers", {})
    s.setdefault("ministerial_loyalty", {})
    s.setdefault("ministerial_resignations", [])
    s.setdefault("ministerial_vacancy_year", {})
    for key, (name, priority) in DEPARTMENT_MINISTERS.items():
        s.cabinet_ministers.setdefault(key, name)
        s.ministerial_loyalty.setdefault(key, 65.0)
        # The Prime Minister, not the Chancellor, fills Cabinet vacancies.
        if s.cabinet_ministers.get(key) == "Vacant — awaiting Prime Minister":
            vacancy_year = int(s.ministerial_vacancy_year.get(key, s.get("year", 1)))
            if int(s.get("year", 1)) > vacancy_year:
                s.cabinet_ministers[key] = f"New appointment (PM)"
                s.ministerial_loyalty[key] = 55.0
                s.ministerial_vacancy_year.pop(key, None)
                s.event_cards = list(s.get("event_cards", []))
                s.event_cards.append({
                    "title": f"Prime Minister appoints a new {SPEND_DEFAULTS[key]['label']} Secretary",
                    "text": "The Prime Minister has filled the Cabinet vacancy. As Chancellor, you had no power to appoint the replacement.",
                    "summary": "Cabinet reshuffle · Prime Minister's decision",
                })
    if 'dept_spend' not in s:
        s.dept_spend = {k: v['default'] for k, v in SPEND_DEFAULTS.items()}
    else:
        _migrate_depts(s.dept_spend)

    had_legacy_budget = 'budget_applied' in s and 'tax' in s.get('budget_applied', {})
    if 'budget_applied' not in s or 'tax_pol' not in s.get('budget_applied', {}):
        s.budget_applied = defaults()
        s.budget_applied['_tax_units_version'] = 2
    else:
        _migrate_applied(s.budget_applied)
    # One-time conversion of legacy percentage-adjustment sliders to the new real-world units.
    if had_legacy_budget and int(s.budget_applied.get('_tax_units_version', 0)) < 2:
        conversions = {
            'fuel': (52.95, 0.5), 'sin': (100.0, 1.0), 'property': (0.5, 0.02),
            'council_tax': (2300.0, 10.0), 'carbon_levy': (25.0, 1.0),
            'sugar_duty': (18.0, 0.5), 'business_rates': (50.0, 0.2),
            'stamp_duty': (3.0, 0.05), 'vehicle_excise': (195.0, 2.0),
            'air_passenger': (15.0, 0.5),
        }
        for key, (baseline, scale) in conversions.items():
            old_default = 0.0
            for section in ('tax',):
                old_value = float(s.budget_applied.get(section, {}).get(key, old_default))
                converted = baseline if old_value == old_default else baseline + old_value * scale
                spec = TAXES[key]
                converted = max(float(spec['lo']), min(float(spec['hi']), converted))
                s.budget_applied[section][key] = round(converted, 2)
            old_value = float(s.get('budget_last_tax', {}).get(key, old_default))
            converted = baseline if old_value == old_default else baseline + old_value * scale
            spec = TAXES[key]
            s.budget_last_tax[key] = round(max(float(spec['lo']), min(float(spec['hi']), converted)), 2)
            widget_key = f'bt_{key}'
            if widget_key in s:
                old_value = float(s[widget_key])
                converted = baseline if old_value == old_default else baseline + old_value * scale
                s[widget_key] = round(max(float(spec['lo']), min(float(spec['hi']), converted)), 2)
        s.budget_applied['_tax_units_version'] = 2
    s.setdefault('budget_interest', BASE_INTEREST)
    s.setdefault('budget_last_tax', dict(s.budget_applied['tax']))
    for k in TAXES:
        s.budget_last_tax.setdefault(k, TAXES[k]['default'])
    s.setdefault('budget_last_pol', {'tax_pol': {k: False for k in TAX_POLICIES}, 'spend_pol': {k: False for k in SPEND_POLICIES}})
    s.setdefault('budget_impact', {})
    s.setdefault('budget_scheme_delivery', {'tax': {}, 'spend': {}})
    if not isinstance(s.budget_scheme_delivery, dict):
        s.budget_scheme_delivery = {'tax': {}, 'spend': {}}
    for kind, table in (('tax', TAX_POLICIES), ('spend', SPEND_POLICIES)):
        s.budget_scheme_delivery.setdefault(kind, {})
        for key, active in s.budget_applied.get(f'{kind}_pol', {}).items():
            if active and key not in s.budget_scheme_delivery[kind]:
                # Existing saves pre-date delivery stages; grandfather their schemes at maturity.
                s.budget_scheme_delivery[kind][key] = len(scheme_profile(kind, key, table[key])['ramp']) - 1

    s.setdefault('budget_history', [])
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



def save_budget_alternative(name, draft=None):
    """Save a named, independent copy of the current Budget draft for comparison."""
    s = st.session_state
    draft = draft or read()
    slots = dict(s.get('budget_alternatives', {}))
    slots[name] = {
        'draft': {k: (dict(v) if isinstance(v, dict) else v) for k, v in draft.items()},
        'saved_at': f"Term {int(s.get('term', 1))}, Year {int(s.get('year', 1))}",
    }
    s.budget_alternatives = slots


def resolve_budget_risks():
    """Reveal one possible implementation risk when the Budget is delivered."""
    import random
    s = st.session_state
    draft = s.get('budget_applied', read())
    imp = impact(draft, draft)
    tax_change = sum(abs(float(draft['tax'][k]) - float(TAXES[k]['default'])) for k in TAXES)
    scheme_count = sum(bool(v) for v in draft.get('tax_pol', {}).values()) + sum(bool(v) for v in draft.get('spend_pol', {}).values())
    spend_change = sum(abs(float(v)) for v in draft.get('spend', {}).values())
    risks = []
    if tax_change > 4:
        risks.append(("Revenue underperforms", "Behavioural responses and weaker activity reduce the expected tax yield.", 2.0, 0.0, -1.0))
    delivery = scheme_financials(draft)
    if delivery['load'] > delivery['capacity'] * 1.15:
        risks.append(("Treasury delivery congestion", "The programme list exceeds Whitehall's practical capacity. Departments report delayed procurement, stretched specialist teams and weaker early results.", 1.0 + 0.2 * (delivery['load'] - delivery['capacity']), 0.02, -0.8))
    if spend_change > 30:
        risks.append(("Cost pressures emerge", "Pay, procurement and supplier costs push the package above its initial estimate.", 2.5, 0.0, -0.5))
    if float(imp.get('market', 0)) < -2 or float(s.market_conf) < 40:
        risks.append(("Gilt-market nerves", "Investors demand a small additional premium after scrutinising the financing plan.", 0.0, 0.05, -1.5))
    if not risks:
        risks = [("Delivery risk", "A limited number of departmental programmes cost slightly more to implement.", 0.5, 0.0, 0.0)]
    rng = random.Random(int(s.get('seed', 1)) + int(s.get('year', 1))*701 + int(s.get('term', 1))*997)
    risk = rng.choice(risks)
    label, detail, fiscal_cost, yield_move, confidence = risk
    s.deficit = round(max(0.0, float(s.deficit) + fiscal_cost), 1)
    s.headroom = round(float(s.headroom) - fiscal_cost, 1)
    s.gilt_yield = round(max(0.1, float(s.gilt_yield) + yield_move), 2)
    s.market_conf = round(_clip(float(s.market_conf) + confidence), 1)
    result = {'title': label, 'detail': detail, 'fiscal_cost': fiscal_cost, 'gilt_move': yield_move}
    s.budget_risk_outcome = result
    return result


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



# ---------------------------------------------------------------- scheme design and delivery model
SCHEME_DELIVERY_CAPACITY = 7.0

_TAX_SCHEME_SECTORS = {
    'hmrc_enforcement':'compliance', 'tax_gap':'compliance', 'vat_compliance':'compliance',
    'online_marketplace':'compliance', 'vat_private':'consumption', 'nondom':'wealth',
    'wealth':'wealth', 'pension_relief_reform':'wealth', 'relief_cap':'wealth',
    'mansion':'property', 'landlord_relief':'property', 'property_empty':'property',
    'stamp_duty_reform':'property', 'digital':'business', 'buyback_levy':'business',
    'bank_surcharge':'business', 'bank_surcharge_reform':'business', 'windfall':'business',
    'carbon':'environment', 'close_fossil_relief':'environment', 'carbon_border':'environment',
    'packaging_levy':'environment', 'aviation_levy':'transport', 'ev_road_pricing':'transport',
    'gambling':'consumption', 'online_gambling':'consumption', 'luxury_goods_levy':'consumption',
}
_SPEND_SCHEME_SECTORS = {
    'meals':'education', 'school_breakfast':'education', 'school_rebuild':'education',
    'child_cap':'family', 'childcare':'family', 'winterfuel':'family', 'youth_opportunity':'family',
    'nhs_workforce':'health', 'primary_care':'health', 'nhs_diagnostics':'health', 'social_care':'health',
    'social_housing':'housing', 'homelessness_prevention':'housing', 'town_deal':'housing',
    'hs2':'transport', 'bus_network':'transport', 'potholes':'transport',
    'nuclear':'energy', 'home_insulation':'energy', 'grid_upgrade':'energy', 'grid_storage':'energy',
    'defence_industry':'defence', 'flood_defences':'resilience', 'prison_capacity':'justice',
    'technical_skills':'skills', 'regional_growth':'regional',
}
_TAX_COMPLIANCE = {'hmrc_enforcement', 'tax_gap', 'vat_compliance', 'online_marketplace'}
_TAX_COMPLEX_REFORM = {'wealth', 'nondom', 'pension_relief_reform', 'relief_cap', 'carbon_border', 'stamp_duty_reform'}
_SPEND_MAJOR_CAPITAL = {'hs2', 'nuclear', 'social_housing', 'school_rebuild', 'grid_upgrade',
                        'grid_storage', 'flood_defences', 'prison_capacity', 'water', 'defence_industry'}
_SPEND_CAPITAL = {'home_insulation', 'regional_growth', 'town_deal', 'homelessness_prevention',
                  'nhs_diagnostics', 'potholes', 'bus_network'}
_SPEND_DIRECT = {'meals', 'school_breakfast', 'winterfuel', 'child_cap'}


def scheme_profile(kind, key, item=None):
    """Return transparent delivery assumptions for a scheme; headline data is steady-state, not instant."""
    item = item or (TAX_POLICIES if kind == 'tax' else SPEND_POLICIES).get(key, {})
    if kind == 'tax':
        if key in _TAX_COMPLIANCE:
            ramp = [0.25, 0.55, 0.82, 1.0]
            admin_rate, admin_min, complexity = 0.12, 0.12, 1.0
            note = "HMRC recruitment, data systems and compliance cases take time to produce receipts."
            risk = "Delivery depends on skilled compliance staff, usable data and successful enforcement."
        elif key in _TAX_COMPLEX_REFORM:
            ramp = [0.40, 0.72, 1.0]
            admin_rate, admin_min, complexity = 0.09, 0.08, 0.9
            note = "Legislation, consultation and behavioural responses delay the full yield."
            risk = "Legal challenge, avoidance and changes in taxpayer behaviour may reduce the yield."
        else:
            ramp = [0.60, 0.86, 1.0]
            admin_rate, admin_min, complexity = 0.055, 0.05, 0.55
            note = "The first-year figure is lower while systems, guidance and collection arrangements bed in."
            risk = "The realised yield may differ from the static estimate as households and firms respond."
        political_ramp = [0.65 + 0.35 * index / max(1, len(ramp) - 1) for index in range(len(ramp))]
        return {
            'ramp': ramp, 'benefit_ramp': ramp, 'political_ramp': political_ramp,
            'admin': max(admin_min, float(item.get('yield_bn', 0.0)) * admin_rate),
            'complexity': complexity, 'sector': _TAX_SCHEME_SECTORS.get(key, 'other revenue'),
            'years': len(ramp), 'note': note, 'risk': risk,
        }

    cost = float(item.get('cost_bn', 0.0))
    if key in _SPEND_MAJOR_CAPITAL:
        ramp = [0.15, 0.35, 0.60, 0.83, 1.0]
        benefit = [0.0, 0.08, 0.25, 0.60, 1.0]
        admin_rate, admin_min, complexity = 0.055, 0.10, 1.35
        note = "A multi-year capital programme: procurement and construction spend build gradually; public benefits arrive later."
        risk = "Planning, procurement, contractor capacity and cost overruns are the principal risks."
    elif key in _SPEND_CAPITAL:
        ramp = [0.30, 0.62, 0.86, 1.0]
        benefit = [0.0, 0.20, 0.65, 1.0]
        admin_rate, admin_min, complexity = 0.05, 0.07, 1.0
        note = "Local delivery and procurement mean the full programme cannot be deployed in its first year."
        risk = "Land, planning, suppliers and local delivery capacity could slow progress."
    elif key in _SPEND_DIRECT:
        ramp = [0.80, 1.0]
        benefit = [0.75, 1.0]
        admin_rate, admin_min, complexity = 0.025, 0.035, 0.45
        note = "Most payments or provision can start quickly, although eligibility and take-up affect the final bill."
        risk = "Take-up may be higher than forecast and create pressure on the annual cost."
    else:
        ramp = [0.45, 0.78, 1.0]
        benefit = [0.18, 0.62, 1.0]
        admin_rate, admin_min, complexity = 0.04, 0.06, 0.8
        note = "Recruitment, training and service capacity mean outcomes build over more than one year."
        risk = "Workforce shortages and implementation capacity may limit the early results."
    political_ramp = [0.65 + 0.35 * index / max(1, len(ramp) - 1) for index in range(len(ramp))]
    return {
        'ramp': ramp, 'benefit_ramp': benefit, 'political_ramp': political_ramp,
        'admin': max(admin_min, cost * admin_rate), 'complexity': complexity,
        'sector': _SPEND_SCHEME_SECTORS.get(key, 'other services'), 'years': len(ramp),
        'note': note, 'risk': risk,
    }


def _scheme_age(kind, key, draft, statuses=None):
    s = st.session_state
    if not draft.get(f'{kind}_pol', {}).get(key, False):
        return 0
    # An explicit status map is used by the annual roll-forward and forecast simulator,
    # including schemes just added to the draft. Respect it before consulting live state.
    if statuses is not None and key in statuses.get(kind, {}):
        return max(0, int(statuses[kind][key]))
    applied = s.get('budget_applied', {})
    if applied.get(f'{kind}_pol', {}).get(key, False):
        current = s.get('budget_scheme_delivery', {}).get(kind, {})
        if key in current:
            return max(0, int(current[key]))
        item = (TAX_POLICIES if kind == 'tax' else SPEND_POLICIES)[key]
        return len(scheme_profile(kind, key, item)['ramp']) - 1
    return 0


def scheme_financials(draft, statuses=None, mature=False):
    """Current-year net receipts and annual costs after ramp-up, administration and capacity pressure."""
    statuses = statuses if statuses is not None else st.session_state.get('budget_scheme_delivery', {})
    selected = []
    for kind, table, field in (('tax', TAX_POLICIES, 'yield_bn'), ('spend', SPEND_POLICIES, 'cost_bn')):
        for key, item in table.items():
            if draft.get(f'{kind}_pol', {}).get(key, False):
                profile = scheme_profile(kind, key, item)
                age = len(profile['ramp']) - 1 if mature else _scheme_age(kind, key, draft, statuses)
                selected.append((kind, key, item, profile, age, float(item.get(field, 0.0))))
    load = sum(row[3]['complexity'] for row in selected)
    delivery_factor = 1.0 if load <= SCHEME_DELIVERY_CAPACITY or load <= 0 else max(0.55, SCHEME_DELIVERY_CAPACITY / load)
    coordination_cost = max(0.0, load - SCHEME_DELIVERY_CAPACITY) * 0.12
    sector_counts = {}
    for kind, key, item, profile, age, amount in selected:
        token = (kind, profile['sector'])
        sector_counts[token] = sector_counts.get(token, 0) + 1

    rows = {}
    tax_gross = tax_admin = tax_net = 0.0
    spend_base = spend_admin = 0.0
    for kind, key, item, profile, age, amount in selected:
        ramp = profile['ramp']
        stage = min(len(ramp) - 1, age)
        current_ramp = 1.0 if mature else ramp[stage]
        overlap = max(0.58, 1.0 - 0.11 * (sector_counts[(kind, profile['sector'])] - 1)) if kind == 'tax' else max(0.68, 1.0 - 0.10 * (sector_counts[(kind, profile['sector'])] - 1))
        cash_factor = current_ramp * delivery_factor
        admin_factor = max(0.72, cash_factor)
        admin = profile['admin'] * admin_factor
        if kind == 'tax':
            gross = amount * cash_factor * overlap
            net = gross - admin
            tax_gross += gross
            tax_admin += admin
            tax_net += net
            mature_gross = amount * delivery_factor * overlap
            first_gross = amount * ramp[0] * delivery_factor * overlap
            rows[(kind, key)] = {
                'age': stage, 'years': len(ramp), 'current_net': net, 'first_year_net': first_gross - profile['admin'] * max(0.72, ramp[0] * delivery_factor),
                'mature_net': mature_gross - profile['admin'] * max(0.72, delivery_factor),
                'gross': gross, 'admin': admin, 'sector': profile['sector'], 'complexity': profile['complexity'],
                'delivery_factor': delivery_factor, 'overlap': overlap, 'profile': profile,
            }
        else:
            base_cost = amount * cash_factor
            annual_cost = base_cost + admin
            spend_base += base_cost
            spend_admin += admin
            first_cost = amount * ramp[0] * delivery_factor + profile['admin'] * max(0.72, ramp[0] * delivery_factor)
            mature_cost = amount * delivery_factor + profile['admin'] * max(0.72, delivery_factor)
            rows[(kind, key)] = {
                'age': stage, 'years': len(ramp), 'current_cost': annual_cost, 'first_year_cost': first_cost,
                'mature_cost': mature_cost, 'admin': admin, 'sector': profile['sector'],
                'complexity': profile['complexity'], 'delivery_factor': delivery_factor, 'overlap': overlap,
                'profile': profile,
            }
    return {
        'tax_gross': tax_gross, 'tax_admin': tax_admin, 'tax_net': tax_net,
        'spend_base': spend_base, 'spend_admin': spend_admin,
        'coordination_cost': coordination_cost, 'spend_cost': spend_base + spend_admin + coordination_cost,
        'load': load, 'capacity': SCHEME_DELIVERY_CAPACITY, 'delivery_factor': delivery_factor,
        'rows': rows,
    }


def scheme_effect_totals(draft, statuses=None):
    """Political effects phase in after announcement; productivity and service effects arrive later."""
    financials = scheme_financials(draft, statuses=statuses)
    effects = {'approval': 0.0, 'market': 0.0, 'growth': 0.0}
    for (kind, key), row in financials['rows'].items():
        item = (TAX_POLICIES if kind == 'tax' else SPEND_POLICIES)[key]
        profile = row['profile']
        age = row['age']
        political = profile['political_ramp'][min(age, len(profile['political_ramp']) - 1)] * row['delivery_factor'] * row['overlap']
        benefits = profile['benefit_ramp'][min(age, len(profile['benefit_ramp']) - 1)] * row['delivery_factor'] * row['overlap']
        effects['approval'] += float(item.get('app', 0.0)) * political
        effects['market'] += float(item.get('mkt', 0.0)) * political
        effects['growth'] += float(item.get('gro', 0.0)) * benefits
    return effects


def _set_scheme_delivery_after_budget(old, new):
    statuses = st.session_state.get('budget_scheme_delivery', {'tax': {}, 'spend': {}})
    updated = {'tax': {}, 'spend': {}}
    for kind, table in (('tax', TAX_POLICIES), ('spend', SPEND_POLICIES)):
        for key in table:
            if new.get(f'{kind}_pol', {}).get(key, False):
                if old.get(f'{kind}_pol', {}).get(key, False):
                    updated[kind][key] = int(statuses.get(kind, {}).get(key, len(scheme_profile(kind, key, table[key])['ramp']) - 1))
                else:
                    updated[kind][key] = 0
    st.session_state.budget_scheme_delivery = updated


def _policy_sum(b, key, table, field):
    return sum(table[k][field] for k, on in b[key].items() if on and k in table)


def revenue_pie(b):
    r = revenues(b)
    data = {TAXES[k]['short']: round(v, 1) for k, v in r.items()}
    data['Other receipts'] = OTHER_RECEIPTS
    scheme_data = scheme_financials(b)
    pol_rev = float(scheme_data['tax_net'])
    if abs(pol_rev) > 0.05: data['Special Tax Schemes · net'] = round(pol_rev, 1)
    return data


def spending_pie(b):
    s = st.session_state
    ensure()
    data = {SPEND_DEFAULTS[k]['short']: round(s.dept_spend[k] * (1.0 + b['spend'][k] / 100.0), 1) for k in SPEND_DEFAULTS}
    data['Debt interest'] = round(interest(), 1)
    scheme_data = scheme_financials(b)
    pol_spend = float(scheme_data['spend_cost'])
    if pol_spend > 0.05: data['Policy programmes · including delivery overhead'] = round(pol_spend, 1)
    return data


def totals(b):
    """(receipts, spending) in £bn for a Budget draft, at today's debt interest."""
    s = st.session_state
    ensure()
    scheme_data = scheme_financials(b)
    rev = sum(revenues(b).values()) + OTHER_RECEIPTS + float(scheme_data['tax_net'])
    # Frozen thresholds create extra receipts through fiscal drag; this is separate from changing a tax rate.
    if s.get('thresholds_frozen', False):
        drag_rate = 0.35 if s.get('threshold_freeze_scope', 'Personal allowance and all bands') == 'Personal allowance and all bands' else 0.25
        rev += min(1.5, drag_rate * float(s.get('threshold_freeze_years', 0)))
    spend = (sum(s.dept_spend[k] * (1.0 + b['spend'][k] / 100.0) for k in SPEND_DEFAULTS) + interest()
             + float(scheme_data['spend_cost']))
    return rev, spend



def assess_pm_priorities(draft=None):
    """Compare the live Budget draft with the last delivered Budget against Number 10's requests."""
    stt = st.session_state
    draft = draft or read()
    old = stt.get('budget_applied') or defaults()
    priorities = stt.get('budget_pm_priorities') or []
    results = []
    for item in priorities:
        tag = item.get('tag', '')
        met, detail = False, "The draft does not yet provide a clear response to this request."
        if tag == 'health':
            delta = float(draft['spend'].get('health', 0)) - float(old['spend'].get('health', 0))
            care = float(draft['spend'].get('social_care', 0)) - float(old['spend'].get('social_care', 0))
            met = delta >= 1 or (delta + care) >= 1.5
            detail = f"NHS spending change: {delta:+.1f} percentage points; adult social care: {care:+.1f}."
        elif tag == 'income_tax':
            keys = ('income', 'income_higher', 'income_additional', 'ni')
            changes = {k: float(draft['tax'].get(k, 0)) - float(old['tax'].get(k, 0)) for k in keys}
            met = all(v <= 0.001 for v in changes.values())
            detail = "Income tax and employee NI rates are " + ("held or cut." if met else "increased in at least one band.")
        elif tag == 'investment':
            keys = ('transport', 'housing', 'science', 'skills')
            delta = sum(float(draft['spend'].get(k, 0)) - float(old['spend'].get(k, 0)) for k in keys)
            met = delta >= 2
            detail = f"Transport, housing, science and skills spending change: {delta:+.1f} percentage points combined."
        elif tag == 'defence':
            delta = float(draft['spend'].get('defence', 0)) - float(old['spend'].get('defence', 0))
            met = delta >= 1
            detail = f"Defence spending change: {delta:+.1f} percentage points."
        elif tag == 'spending':
            fiscal = impact(old, draft)
            met = float(fiscal.get('headroom', 0)) >= 0
            detail = f"Estimated change to fiscal headroom: £{float(fiscal.get('headroom', 0)):+.1f}bn."
        elif tag == 'fair_tax':
            keys = ('income', 'ni', 'vat')
            changes = [float(draft['tax'].get(k, 0)) - float(old['tax'].get(k, 0)) for k in keys]
            met = all(v <= 0.001 for v in changes)
            detail = "Basic income tax, employee NI and VAT are " + ("held or cut." if met else "not all held or cut.")
        elif tag == 'local':
            keys = ('housing', 'local_government', 'transport')
            delta = sum(float(draft['spend'].get(k, 0)) - float(old['spend'].get(k, 0)) for k in keys)
            met = delta >= 2
            detail = f"Housing, councils and transport spending change: {delta:+.1f} percentage points combined."
        elif tag == 'green':
            delta = float(draft['spend'].get('climate', 0)) - float(old['spend'].get('climate', 0))
            met = delta >= 1
            detail = f"Climate and clean-energy spending change: {delta:+.1f} percentage points."
        results.append({'title': item.get('title', 'PM priority'), 'met': bool(met), 'detail': detail})
    return results

def impact(old, new):
    """What moving from Budget ``old`` to Budget ``new`` does to the headline numbers (applied once, when delivered)."""
    s = st.session_state
    ensure()
    ro, rn = revenues(old), revenues(new)
    d = {k: rn[k] - ro[k] for k in ro}
    ds = {k: s.dept_spend[k] * ((new['spend'][k] - old['spend'][k]) / 100.0) for k in SPEND_DEFAULTS}

    old_schemes = scheme_financials(old)
    new_schemes = scheme_financials(new)
    tax_pol_diff = float(new_schemes['tax_net']) - float(old_schemes['tax_net'])
    spend_pol_diff = float(new_schemes['spend_cost']) - float(old_schemes['spend_cost'])
    bal = sum(d.values()) - sum(ds.values()) + tax_pol_diff - spend_pol_diff
    old_st = FISCAL_STRATEGIES.get(old.get('strategy', 'balanced'), FISCAL_STRATEGIES['balanced'])
    new_st = FISCAL_STRATEGIES.get(new.get('strategy', 'balanced'), FISCAL_STRATEGIES['balanced'])
    sd = {k: new_st[k] - old_st[k] for k in ('headroom','approval','market','growth')}
    bal += sd['headroom']

    household = (d['income'] + d['income_higher'] + d['income_additional'] + d['ni'] + d['vat'] + d['fuel'] + d['sin']
                 + d['council_tax'] + d['sugar_duty'] + d['vehicle_excise'] + d['air_passenger'])
    wealth = d['property'] + d['cgt'] + d['iht'] + d['land_value'] + d['financial_transaction'] + d['stamp_duty']
    vat_pts = new['tax']['vat'] - old['tax']['vat']

    approval = (-0.10 * household - 0.03 * wealth
                + 0.05 * (ds['health'] + ds['education']) + 0.03 * ds['welfare']
                + 0.02 * (ds['justice'] + ds['housing'] + ds['transport']) + 0.01 * ds['defence']
                + 0.01 * (ds['science'] + ds['culture']) - 0.01 * ds['aid']
                + 0.025 * ds['social_care'] + 0.015 * ds['local_government'] + 0.015 * ds['public_sector_pay'] + 0.02 * ds['skills'])
    market = (max(-8, min(8, 0.10 * bal)) - 0.25 * d['corp'] - 0.12 * d['property']
              - 0.10 * d['cgt'] - 0.05 * d['iht']
              - 0.08 * d['land_value'] - 0.06 * d['financial_transaction'] - 0.04 * d['carbon_levy'] - 0.05 * d['business_rates'])
    growth = (-0.012 * d['corp'] - 0.006 * d['ni'] - 0.004 * d['income'] - 0.003 * d['income_higher'] - 0.002 * d['income_additional'] - 0.008 * d['cgt'] - 0.003 * d['land_value']
              - 0.012 * d['financial_transaction'] - 0.015 * d['carbon_levy'] - 0.001 * d['sugar_duty'] - 0.002 * d['council_tax']
              - 0.002 * d['business_rates'] - 0.003 * d['stamp_duty'] - 0.001 * d['vehicle_excise'] - 0.002 * d['air_passenger']
              + 0.008 * (ds['transport'] + ds['housing'] + ds['climate']) + 0.012 * ds['science']
              + 0.002 * (ds['health'] + ds['education'] + ds['other'] + ds['welfare'] + ds['culture'] + ds['social_care'] + ds['local_government'] + ds['public_sector_pay'])
              + 0.010 * ds['skills']
              + 0.001 * ds['defence'])

    old_scheme_effects = scheme_effect_totals(old)
    new_scheme_effects = scheme_effect_totals(new)
    approval += new_scheme_effects['approval'] - old_scheme_effects['approval']
    market += new_scheme_effects['market'] - old_scheme_effects['market']
    growth += new_scheme_effects['growth'] - old_scheme_effects['growth']

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
    _set_scheme_delivery_after_budget(old, new)
    s.budget_applied = new
    # budget_strategy is a Streamlit widget key. Its value already came from read();
    # assigning it here after widget creation raises StreamlitWidgetAlreadyInstantiatedError.
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
    """Archive the delivered Budget so the Chancellor can inspect previous decisions."""
    s = st.session_state
    s.vote_ayes = ayes
    delivered = s.budget_applied
    tax_names = {k: TAXES[k]['short'] for k in TAXES}
    spending_names = {k: SPEND_DEFAULTS[k]['label'] for k in SPEND_DEFAULTS}
    revenue_schemes = [TAX_POLICIES[k]['label'] for k, on in delivered.get('tax_pol', {}).items() if on and k in TAX_POLICIES]
    spending_schemes = [SPEND_POLICIES[k]['label'] for k, on in delivered.get('spend_pol', {}).items() if on and k in SPEND_POLICIES]
    s.budget_history = list(s.get('budget_history', []))
    s.budget_history.append({
        'term': int(s.get('term', 1)), 'year': int(s.get('year', 1)),
        'label': f"Term {int(s.get('term', 1))} · Year {int(s.get('year', 1))}",
        'strategy': delivered.get('strategy', 'balanced'),
        'tax': dict(delivered.get('tax', {})), 'tax_names': tax_names,
        'spend': dict(delivered.get('spend', {})), 'spend_names': spending_names,
        'revenue_schemes': revenue_schemes, 'spending_schemes': spending_schemes,
        'scheme_delivery': {
            'current_net_receipts': round(float(scheme_financials(delivered)['tax_net']), 2),
            'current_programme_cost': round(float(scheme_financials(delivered)['spend_cost']), 2),
            'delivery_load': round(float(scheme_financials(delivered)['load']), 2),
            'mature_net_balance': round(float(scheme_financials(delivered, mature=True)['tax_net']) - float(scheme_financials(delivered, mature=True)['spend_cost']), 2),
        },
        'ayes': int(ayes), 'headroom_after': round(float(s.get('headroom', 0)), 1),
        'deficit_after': round(float(s.get('deficit', 0)), 1),
        'impact': dict(s.get('budget_impact', {})),
        'message': str(s.get('budget_message', '')),
        'risk': dict(s.get('budget_risk_outcome') or {}),
    })
    s.budget_history = s.budget_history[-12:]
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
    projected_status = {'tax': {}, 'spend': {}}
    current_status = s.get('budget_scheme_delivery', {'tax': {}, 'spend': {}})
    for kind, table in (('tax', TAX_POLICIES), ('spend', SPEND_POLICIES)):
        for key, item in table.items():
            if not b.get(f'{kind}_pol', {}).get(key, False):
                continue
            if s.budget_applied.get(f'{kind}_pol', {}).get(key, False):
                projected_status[kind][key] = int(current_status.get(kind, {}).get(key, len(scheme_profile(kind, key, item)['ramp']) - 1))
            else:
                projected_status[kind][key] = 0
    demographic_pressure = float(s.get('demographic_pressure', 0.0))
    pension_pressure = float(s.get('pension_pressure', 0.0))
    rows = []
    for i in range(1, years + 1):
        # A scheme moves forward one delivery stage each year. Only the change in its
        # annual net cashflow and economic effect alters the forecast from last year.
        before_fin = scheme_financials(b, statuses=projected_status)
        before_effects = scheme_effect_totals(b, statuses=projected_status)
        next_status = {'tax': {}, 'spend': {}}
        for kind, table in (('tax', TAX_POLICIES), ('spend', SPEND_POLICIES)):
            for key, item in table.items():
                if b.get(f'{kind}_pol', {}).get(key, False):
                    age = int(projected_status.get(kind, {}).get(key, len(scheme_profile(kind, key, item)['ramp']) - 1))
                    next_status[kind][key] = min(len(scheme_profile(kind, key, item)['ramp']) - 1, age + 1)
        after_fin = scheme_financials(b, statuses=next_status)
        after_effects = scheme_effect_totals(b, statuses=next_status)
        scheme_cash_delta = (
            float(after_fin['tax_net']) - float(before_fin['tax_net'])
            - (float(after_fin['spend_cost']) - float(before_fin['spend_cost']))
        )
        v['headroom'] = round(v['headroom'] + scheme_cash_delta, 1)
        v['deficit'] = round(max(0.0, v['deficit'] - scheme_cash_delta), 1)
        v['growth'] = round(v['growth'] + after_effects['growth'] - before_effects['growth'], 2)
        v['market_conf'] = round(_clip(v['market_conf'] + after_effects['market'] - before_effects['market']), 1)
        v['approval'] = round(_clip(v['approval'] + after_effects['approval'] - before_effects['approval']), 1)
        projected_status = next_status

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

    # Mature active schemes one stage at the start of each financial year.
    # Their extra receipts/costs and economic effects arrive only as delivery progresses.
    previous_status = {
        'tax': dict(s.budget_scheme_delivery.get('tax', {})),
        'spend': dict(s.budget_scheme_delivery.get('spend', {})),
    }
    applied_schemes = s.budget_applied
    previous_financials = scheme_financials(applied_schemes, statuses=previous_status)
    previous_effects = scheme_effect_totals(applied_schemes, statuses=previous_status)
    next_status = {'tax': {}, 'spend': {}}
    newly_maturing = []
    for kind, table in (('tax', TAX_POLICIES), ('spend', SPEND_POLICIES)):
        for key, item in table.items():
            if not applied_schemes.get(f'{kind}_pol', {}).get(key, False):
                continue
            profile = scheme_profile(kind, key, item)
            old_age = int(previous_status.get(kind, {}).get(key, len(profile['ramp']) - 1))
            new_age = min(len(profile['ramp']) - 1, old_age + 1)
            next_status[kind][key] = new_age
            if new_age > old_age:
                newly_maturing.append(item['label'])
    next_financials = scheme_financials(applied_schemes, statuses=next_status)
    next_effects = scheme_effect_totals(applied_schemes, statuses=next_status)
    cash_improvement = (
        float(next_financials['tax_net']) - float(previous_financials['tax_net'])
        - (float(next_financials['spend_cost']) - float(previous_financials['spend_cost']))
    )
    if abs(cash_improvement) > 0.001:
        s.headroom = round(float(s.headroom) + cash_improvement, 1)
        s.deficit = round(max(0.0, float(s.deficit) - cash_improvement), 1)
    s.approval = round(_clip(float(s.approval) + next_effects['approval'] - previous_effects['approval']), 1)
    s.market_conf = round(_clip(float(s.market_conf) + next_effects['market'] - previous_effects['market']), 1)
    s.growth = round(float(s.growth) + next_effects['growth'] - previous_effects['growth'], 2)
    s.budget_scheme_delivery = next_status
    if newly_maturing:
        s.message = str(s.get('message', '')) + f" Scheme delivery advanced this year: {', '.join(newly_maturing[:3])}{' and other programmes' if len(newly_maturing) > 3 else ''}."
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
    delivery = scheme_financials(s.budget_applied)
    for (kind, pk), row in delivery['rows'].items():
        if kind != 'spend':
            continue
        effects = POLICY_NUDGES.get(pk, {})
        profile = row['profile']
        benefit_factor = profile['benefit_ramp'][min(row['age'], len(profile['benefit_ramp']) - 1)]
        effective = benefit_factor * row['delivery_factor'] * row['overlap']
        for stat, val in effects.items():
            nudges[stat] = nudges.get(stat, 0.0) + float(val) * effective
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
        display_label = "Business rates · change to existing receipts" if k == "business_rates" else t['label']
        st.markdown(f"<div class='lv'>{display_label}</div>", unsafe_allow_html=True)
    with c2:
        lo, hi, step = _tax_slider_spec(t)
        key = f'bt_{k}'
        if isinstance(step, float) and key in s and not isinstance(s[key], float):
            # Cast saved/default values before creating the slider widget.
            s[key] = float(s[key])
        st.slider(
            f"{t['label']} slider", min_value=lo, max_value=hi, step=step,
            key=key, format="%g%%", label_visibility="collapsed",
            help=("This is a percentage change in business-rates receipts from the existing system, not the business-rates tax rate. 0% keeps the current baseline." if k == "business_rates" else t.get('help', 'Set this tax or duty rate as a percentage. The Treasury estimates the annual receipts; higher rates can reduce the tax base or discourage activity.'))
        )
    with c3:
        d = float(s[f'bt_{k}']) - float(t['default'])
        rate = float(s[f'bt_{k}'])
        new_rev = t['base'] + t['per'] * d - t['decay'] * t['per'] * max(d, 0) ** 2
        if k == "business_rates":
            rate_label = "No change" if abs(rate) < 0.001 else f"{rate:+g}% receipts"
            st.markdown(_value_html(f'{rate_label} · £{new_rev:,.1f}bn', new_rev - t['base']), unsafe_allow_html=True)
        else:
            st.markdown(_value_html(f'{rate:g}% · £{new_rev:,.1f}bn', new_rev - t['base']), unsafe_allow_html=True)


def _spend_row(k, sp, s):
    base = float(s.dept_spend[k])
    pct = float(s.get(f'bs_{k}', s.budget_applied.get('spend', {}).get(k, 0.0)))
    c1, c2, c3 = st.columns([2.0, 3.2, 1.35], gap='small')
    with c1:
        st.markdown(f"<div class='lv'><b>{sp['short']}</b><br><small>Baseline £{base:,.1f}bn</small></div>", unsafe_allow_html=True)
    with c2:
        st.slider(
            f"{sp['label']} slider", min_value=-15.0, max_value=15.0,
            step=0.5, key=f'bs_{k}', format="%+.1f%%",
            label_visibility="collapsed",
            help="Change this department's annual budget relative to today's approved baseline. Negative values are cuts; positive values are increases."
        )
    with c3:
        pct = float(s[f'bs_{k}'])
        new_val = base * (1.0 + pct / 100.0)
        st.markdown(_value_html(f'£{new_val:,.1f}bn', new_val - base, good_when_positive=True, extra=f' ({pct:+.1f}%)'),
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
    st.caption('Illustrative sensitivity range, not an official OBR confidence interval. It shows how weaker growth and higher borrowing costs could alter the central forecast.')
    risk_rows = []
    for i, row in enumerate(rows):
        growth_margin = 0.35 + 0.1 * i
        headroom_margin = 2.0 + i
        risk_rows.append({'Year': row['year'], 'Growth downside': round(row['growth'] - growth_margin, 1), 'Growth upside': round(row['growth'] + growth_margin, 1), 'Headroom downside (£bn)': round(row['headroom'] - headroom_margin, 1), 'Headroom upside (£bn)': round(row['headroom'] + headroom_margin * 0.75, 1)})
    st.dataframe(pd.DataFrame(risk_rows), hide_index=True, use_container_width=True)
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
        dict(label='Income', value=f'£{rev_now:,.0f}bn', delta=delta(rev_now - rev_app, 'bn'),
             num=(rev_now - rev_app) if changed else 0, desc='Estimated annual tax and other government receipts.'),
        dict(label='Spending', value=f'£{spend_now:,.0f}bn', delta=delta(spend_now - spend_app, 'bn'),
             num=(spend_now - spend_app) if changed else 0, inverse=True, desc='Estimated annual government spending.'),
        dict(label='Deficit', value=f'£{max(0, deficit_now):,.0f}bn', delta=f'{deficit_now / GDP_BN * 100:.1f}% GDP',
             num=(bal_app - bal_now) if changed else 0, inverse=True, desc='The gap between annual spending and receipts.'),
        dict(label='Fiscal headroom', value=f"£{s.headroom + imp['headroom']:.1f}bn", delta=delta(imp['headroom']),
             num=imp['headroom'] if changed else 0, desc='Your remaining margin against the fiscal rule.'),
        dict(label='Projected Ayes', value=str(ayes), delta=f'{ayes - WIN:+d} vs majority',
             num=ayes - WIN, desc='Estimated MPs supporting the Budget. 326 votes are required.'),
        dict(label='Market confidence', value=f"{_clip(s.market_conf + imp['market']):.0f}/100",
             delta=delta(imp['market']), num=imp['market'] if changed else 0,
             desc='Investor confidence and the likely market reception.'),
    ])

    with st.expander('Treasury briefing · three-year outlook', expanded=False):
        briefing_rows = forecast(cur, years=3)
        lowest_headroom = min(float(row['headroom']) for row in briefing_rows)
        end_debt = float(briefing_rows[-1]['debt'])
        market_outlook = _clip(float(s.market_conf) + float(imp.get('market', 0.0)))
        if lowest_headroom < 0:
            obr_verdict = "Fiscal rules at risk"
            obr_detail = f"The central forecast falls to £{lowest_headroom:.1f}bn of headroom. A weaker economy could make the breach worse."
        elif lowest_headroom < 5:
            obr_verdict = "Very little fiscal room"
            obr_detail = f"The lowest projected headroom is £{lowest_headroom:.1f}bn. A small forecast downgrade could wipe it out."
        else:
            obr_verdict = "Fiscal rule met"
            obr_detail = f"The central forecast retains at least £{lowest_headroom:.1f}bn of headroom over the three-year horizon."
        if ayes < WIN:
            commons_verdict = "Budget likely to fall"
            commons_detail = f"Only {ayes} MPs are projected to support the package; {WIN} are needed. The Government would face a confidence crisis."
        elif ayes < WIN + 15:
            commons_verdict = "Knife-edge majority"
            commons_detail = f"{ayes} projected Ayes. A modest rebellion could defeat the Budget."
        else:
            commons_verdict = "Likely to pass"
            commons_detail = f"{ayes} projected Ayes, a working margin of {ayes - WIN} over the majority threshold."
        if market_outlook < 35:
            market_verdict = "Investors deeply uneasy"
            market_detail = "The package is being judged against already weak confidence. Borrowing costs could rise quickly."
        elif market_outlook < 55:
            market_verdict = "Markets cautious"
            market_detail = "Investors will look for credible funding and a believable path for debt."
        else:
            market_verdict = "Markets relatively confident"
            market_detail = "There is some room for a positive reception, provided the fiscal arithmetic holds."
        st.markdown("### The private Treasury briefing")
        st.caption("A pre-delivery assessment for the Chancellor. These are modelled forecasts and political estimates, not official OBR or market statements.")
        brief_cols = st.columns(3, gap="medium")
        with brief_cols[0]:
            st.markdown("**OBR · Fiscal outlook**")
            st.markdown(f"**{obr_verdict}**")
            st.caption(obr_detail)
        with brief_cols[1]:
            st.markdown("**Commons · Parliamentary arithmetic**")
            st.markdown(f"**{commons_verdict}**")
            st.caption(commons_detail)
        with brief_cols[2]:
            st.markdown("**City · Market reaction**")
            st.markdown(f"**{market_verdict}**")
            st.caption(market_detail)
        debt_direction = "falling" if end_debt < float(s.debt) else "rising"
        st.caption(f"Three-year debt trajectory: {float(s.debt):.1f}% now → {end_debt:.1f}% of GDP ({debt_direction}). The final decision remains yours, Chancellor.")


    with st.expander('Compare alternative Budgets', expanded=False):
        st.caption("Save up to three alternative packages, then compare their fiscal and political outlook before choosing which one to deliver.")
        slots = dict(s.get('budget_alternatives', {}))
        alt_name = st.selectbox("Save this draft as", ["Growth Budget", "Investment Budget", "Fiscal consolidation", "Alternative 1", "Alternative 2"], key="budget_alt_name")
        save_col, clear_col = st.columns([1, 1])
        if save_col.button("Save current package", key="save_budget_alternative", use_container_width=True):
            if alt_name not in slots and len(slots) >= 3:
                st.warning("You can keep three alternatives. Replace or delete one before saving another.")
            else:
                save_budget_alternative(alt_name, cur)
                st.success(f"{alt_name} saved. It is a separate snapshot; later slider changes will not overwrite it.")
                st.rerun()
        if slots:
            if clear_col.button("Delete selected package", key="delete_budget_alternative", use_container_width=True):
                slots.pop(alt_name, None); s.budget_alternatives = slots; st.rerun()
            comparison = []
            for name, item in slots.items():
                package = item.get('draft', {})
                totals_rev, totals_spend = totals(package)
                package_impact = impact(s.budget_applied, package)
                package_ayes = projected_ayes(package)
                comparison.append({"Package": name, "Income (£bn)": round(totals_rev,1), "Spending (£bn)": round(totals_spend,1),
                    "Net balance (£bn)": round(totals_rev-totals_spend,1), "Projected headroom (£bn)": round(float(s.headroom)+package_impact.get('headroom',0),1),
                    "Approval impact": round(package_impact.get('approval',0),1), "Projected Ayes": package_ayes})
            st.dataframe(pd.DataFrame(comparison), hide_index=True, use_container_width=True)
            if st.button("Load selected package into live draft", key="load_budget_alternative", use_container_width=True):
                selected = slots.get(alt_name)
                if selected:
                    _reset()
                    for key, value in selected['draft'].get('tax', {}).items(): st.session_state[f'bt_{key}'] = value
                    for key, value in selected['draft'].get('spend', {}).items(): st.session_state[f'bs_{key}'] = value
                    for key, value in selected['draft'].get('tax_pol', {}).items(): st.session_state[f'btp_{key}'] = value
                    for key, value in selected['draft'].get('spend_pol', {}).items(): st.session_state[f'bsp_{key}'] = value
                    s.budget_strategy = selected['draft'].get('strategy', 'balanced')
                    st.success(f"{alt_name} loaded into the live draft.")
                    st.rerun()
        st.divider()


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

    # A read-only record of the last delivered settlement, separate from the live draft.
    history = list(s.get('budget_history', []))
    if history:
        last = history[-1]
        with st.expander(f"📜 Last delivered Budget · {last.get('label', 'Previous Budget')}", expanded=False):
            st.caption(f"Strategy: {FISCAL_STRATEGIES.get(last.get('strategy'), FISCAL_STRATEGIES['balanced'])['label']} · Commons: {last.get('ayes', 0)} ayes · Headroom after delivery: £{last.get('headroom_after', 0):.1f}bn")
            scheme_record = last.get('scheme_delivery', {})
            if scheme_record:
                st.caption(
                    f"Scheme portfolio: £{float(scheme_record.get('current_net_receipts', 0)):.2f}bn net receipts · "
                    f"£{float(scheme_record.get('current_programme_cost', 0)):.2f}bn current costs · "
                    f"£{float(scheme_record.get('mature_net_balance', 0)):+.2f}bn at maturity · "
                    f"Delivery load {float(scheme_record.get('delivery_load', 0)):.1f}/{SCHEME_DELIVERY_CAPACITY:.1f}"
                )
            h1, h2 = st.columns(2)
            with h1:
                st.markdown("**Tax decisions**")
                for key, value in last.get('tax', {}).items():
                    name = last.get('tax_names', {}).get(key, key.replace('_', ' ').title())
                    st.write(f"• {name}: {value:g}")
                st.markdown("**Revenue schemes**")
                for name in last.get('revenue_schemes', []):
                    st.write(f"• {name}")
                if not last.get('revenue_schemes'): st.caption("No revenue schemes selected.")
            with h2:
                st.markdown("**Departmental spending changes**")
                for key, value in last.get('spend', {}).items():
                    name = last.get('spend_names', {}).get(key, key.replace('_', ' ').title())
                    st.write(f"• {name}: {float(value):+g}%")
                st.markdown("**Spending pledges**")
                for name in last.get('spending_schemes', []):
                    st.write(f"• {name}")
                if not last.get('spending_schemes'): st.caption("No spending pledges selected.")
            if last.get('message'):
                st.caption(f"Chancellor's message: {last['message']}")
    else:
        st.info("Your previous Budget decisions will be recorded here after your first Budget passes the Commons.")

    t_tax, t_spend, t_schemes, t_whips, t_charts = st.tabs(
        ['Taxes', 'Spending', 'Schemes', 'Whips & forecast', 'Charts & Red Book'])

    with t_tax:
        st.caption('Set tax rates where the control represents a rate, or adjust receipts where the control is a percentage change to an existing tax. Business rates are already included in baseline receipts: 0% means no change, not that the tax is abolished. Income-tax rates are marginal: each rate applies only to income inside its band. The £bn figure beside each slider is estimated annual revenue. Threshold freezes are controlled in Fiscal tools. Each group opens separately to keep the Budget usable on smaller screens.')
        groups = {}
        for k, tx in TAXES.items():
            groups.setdefault(tx['group'], []).append((k, tx))
        for ix, (group, items) in enumerate(groups.items()):
            with st.expander(f"{group} · {len(items)} controls", expanded=(ix == 0)):
                for k, tx in items:
                    _tax_row(k, tx, s)
        st.caption(f'Tax take {rev_now / GDP_BN * 100:.1f}% of GDP. The Laffer effect is a simplified game rule: very high rates may raise less extra revenue than expected.')

    with t_spend:
        spend_values = {k: float(cur['spend'].get(k, 0.0)) for k in SPEND_DEFAULTS}
        cut_count = sum(1 for v in spend_values.values() if v < -0.05)
        rise_count = sum(1 for v in spend_values.values() if v > 0.05)
        net_change = sum(float(s.dept_spend[k]) * spend_values[k] / 100.0 for k in SPEND_DEFAULTS)
        st.caption(f"Set each department's spending change as a percentage of its approved budget: negative percentages cut funding and positive percentages increase it. Changes take effect only when the Budget is delivered and compound into next year's baseline. Total draft spending is {spend_now / GDP_BN * 100:.1f}% of GDP; debt interest is £{interest():,.1f}bn ({interest() / max(rev_now, 1):.1f}% of receipts).")
        control_cols = st.columns([2.2, 1, 1], gap='small')
        control_cols[0].markdown(f"<div class='spend-draft-summary'><strong>{cut_count} departments cut · {rise_count} increased</strong><small>Net annual departmental change: £{net_change:+,.1f}bn</small></div>", unsafe_allow_html=True)
        control_cols[1].button("Restore approved", key="restore_spend_draft", on_click=_reset_spending_draft,
                               use_container_width=True, help="Discard all departmental draft changes and restore the last approved settings.")
        control_cols[2].button("Reset all draft", key="reset_budget_draft", on_click=_reset,
                               use_container_width=True, help="Discard all tax, spending and scheme changes in this Budget draft.")
        if cut_count == len(SPEND_DEFAULTS) and all(v <= -14.5 for v in spend_values.values()):
            st.warning("Every department is currently set to a 15% cut. These are saved draft slider values, not automatic game behaviour. Use Restore approved to discard them.")
        elif cut_count:
            st.info(f"This draft cuts funding for {cut_count} of {len(SPEND_DEFAULTS)} departments. Check the service and political consequences before delivering it.")
        spend_groups = [
            ("People & frontline services", ["welfare", "health", "education", "justice", "defence", "social_care", "public_sector_pay"]),
            ("Infrastructure & transition", ["transport", "housing", "climate", "local_government"]),
            ("Science, culture & other", ["science", "aid", "culture", "other", "skills"]),
        ]
        for group, keys in spend_groups:
            with st.expander(f"{group} · {len(keys)} departments", expanded=False):
                for k in keys:
                    if k in SPEND_DEFAULTS:
                        _spend_row(k, SPEND_DEFAULTS[k], s)

    with t_schemes:
        delivery = scheme_financials(cur)
        mature_delivery = scheme_financials(cur, mature=True)
        revenue_selected = [k for k, p in TAX_POLICIES.items() if cur['tax_pol'].get(k, False)]
        spending_selected = [k for k, p in SPEND_POLICIES.items() if cur['spend_pol'].get(k, False)]
        current_net = float(delivery['tax_net']) - float(delivery['spend_cost'])
        mature_net = float(mature_delivery['tax_net']) - float(mature_delivery['spend_cost'])
        st.markdown("### Policy programmes")
        st.caption("Schemes are now modelled as programmes with real implementation periods, administrative overheads and limits on how much Whitehall can deliver at once. Headline figures are mature annual estimates, not instant cash.")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Programmes selected", f"{len(revenue_selected) + len(spending_selected)}", f"{len(revenue_selected)} revenue · {len(spending_selected)} spending")
        m2.metric("Delivery capacity", f"{delivery['load']:.1f}/{delivery['capacity']:.1f}", f"{delivery['delivery_factor']*100:.0f}% effective rollout")
        m3.metric("Current-year net impact", f"£{current_net:+.1f}bn", "receipts less programme costs")
        m4.metric("At full maturity", f"£{mature_net:+.1f}bn", "steady-state annual impact")
        if delivery['load'] > delivery['capacity']:
            st.warning(f"Your programme list exceeds Treasury delivery capacity. Recruitment, procurement and oversight are stretched; effective rollout is reduced to {delivery['delivery_factor']*100:.0f}% and coordination adds about £{delivery['coordination_cost']:.2f}bn a year.")
        else:
            st.caption(f"Portfolio capacity is within the modelled limit. Current annual administration and coordination costs: £{delivery['tax_admin'] + delivery['spend_admin'] + delivery['coordination_cost']:.2f}bn.")
        st.markdown("#### Current programme commitments")
        selected_left, selected_right = st.columns(2)
        with selected_left:
            st.markdown("**Revenue measures**")
            if revenue_selected:
                for k in revenue_selected:
                    row = delivery['rows'][('tax', k)]
                    st.write(f"• {TAX_POLICIES[k]['label']} · £{row['current_net']:+.2f}bn net this year")
            else:
                st.caption("No revenue schemes selected.")
        with selected_right:
            st.markdown("**Spending programmes**")
            if spending_selected:
                for k in spending_selected:
                    row = delivery['rows'][('spend', k)]
                    st.write(f"• {SPEND_POLICIES[k]['label']} · £{row['current_cost']:.2f}bn this year")
            else:
                st.caption("No spending commitments selected.")
        st.divider()

        def render_scheme_choice(kind, key, item):
            selected = bool(cur.get(f'{kind}_pol', {}).get(key, False))
            candidate = {
                'tax_pol': dict(cur.get('tax_pol', {})),
                'spend_pol': dict(cur.get('spend_pol', {})),
            }
            candidate[f'{kind}_pol'][key] = True
            candidate_delivery = scheme_financials(candidate)
            row = candidate_delivery['rows'][(kind, key)]
            profile = row['profile']
            if kind == 'tax':
                amount_line = (
                    f"Estimated net receipts: £{row['current_net']:.2f}bn this year · "
                    f"£{row['mature_net']:.2f}bn at maturity"
                )
            else:
                amount_line = (
                    f"Estimated cost: £{row['current_cost']:.2f}bn this year · "
                    f"£{row['mature_cost']:.2f}bn annually at maturity"
                )
            years = int(profile['years'])
            stage = int(row['age']) + 1
            stage_line = f"Delivery stage {stage}/{years}" if selected else f"{years}-year implementation"
            admin_label = "collection and compliance" if kind == 'tax' else "programme management"
            st.checkbox(item['label'], key=f"{'btp' if kind == 'tax' else 'bsp'}_{key}")
            st.caption(f"{amount_line} · {stage_line} · £{profile['admin']:.2f}bn annual {admin_label}")
            st.caption(profile['note'] + " " + profile['risk'])

        revenue_groups = {
            "Households & wealth": ["vat_private", "nondom", "wealth", "mansion", "pension_relief_reform", "relief_cap", "landlord_relief", "property_empty", "luxury_goods_levy"],
            "Business, banks & digital economy": ["windfall", "digital", "buyback_levy", "bank_surcharge", "bank_surcharge_reform", "vat_compliance", "online_marketplace", "tax_gap", "hmrc_enforcement"],
            "Environment, transport & consumption": ["carbon", "close_fossil_relief", "aviation_levy", "ev_road_pricing", "gambling", "online_gambling", "packaging_levy", "carbon_border", "stamp_duty_reform"],
        }
        st.markdown("#### Revenue-raising schemes")
        for group, keys in revenue_groups.items():
            available = [(k, TAX_POLICIES[k]) for k in keys if k in TAX_POLICIES]
            if not available: continue
            with st.expander(f"{group} · {sum(1 for k, p in available if cur['tax_pol'].get(k, False))}/{len(available)} selected", expanded=False):
                for k, p in available:
                    render_scheme_choice('tax', k, p)
        st.markdown("#### Spending commitments")
        spending_groups = {
            "NHS, education & family support": ["meals", "child_cap", "childcare", "winterfuel", "nhs_workforce", "primary_care", "nhs_diagnostics", "school_rebuild", "school_breakfast", "social_care"],
            "Housing, communities & transport": ["hs2", "social_housing", "bus_network", "potholes", "regional_growth", "town_deal", "homelessness_prevention"],
            "Energy, industry & national resilience": ["nuclear", "home_insulation", "grid_upgrade", "grid_storage", "defence_industry", "flood_defences", "technical_skills", "youth_opportunity", "prison_capacity", "water"],
        }
        for group, keys in spending_groups.items():
            available = [(k, SPEND_POLICIES[k]) for k in keys if k in SPEND_POLICIES]
            if not available: continue
            with st.expander(f"{group} · {sum(1 for k, p in available if cur['spend_pol'].get(k, False))}/{len(available)} selected", expanded=False):
                for k, p in available:
                    render_scheme_choice('spend', k, p)
        # Keep any future data-file options visible rather than silently omitting them.
        grouped_tax = {k for keys in revenue_groups.values() for k in keys}
        other_tax = [(k, p) for k, p in TAX_POLICIES.items() if k not in grouped_tax]
        if other_tax:
            with st.expander(f"Other revenue schemes · {len(other_tax)} options", expanded=False):
                for k, p in other_tax:
                    render_scheme_choice('tax', k, p)
        grouped_spend = {k for keys in spending_groups.values() for k in keys}
        other_spend = [(k, p) for k, p in SPEND_POLICIES.items() if k not in grouped_spend]
        if other_spend:
            with st.expander(f"Other spending pledges · {len(other_spend)} options", expanded=False):
                for k, p in other_spend:
                    render_scheme_choice('spend', k, p)

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

    



# ---------------------------------------------------------------- Spending Review: multi-year departmental settlements

def apply_spending_review_rollforward(s, target_year):
    """Apply the approved year-two/year-three departmental settlement once per year."""
    plan = s.get('spending_review_plan', {})
    if not isinstance(plan, dict) or not plan.get('allocations'):
        return 0.0
    if int(plan.get('term', -1)) != int(s.get('term', 1)):
        return 0.0
    approved_year = int(plan.get('approved_year', target_year))
    offset = int(target_year) - approved_year
    # Year 2 starts one simulated year after approval; Year 3 starts two years after.
    if offset not in (1, 2) or int(plan.get('last_applied_year', approved_year)) >= int(target_year):
        return 0.0
    uplift_key = 'year2_uplift' if offset == 1 else 'year3_uplift'
    uplift = float(plan.get(uplift_key, 0.0))
    before = sum(float(s.dept_spend.get(k, 0.0)) for k in SPEND_DEFAULTS)
    for key in SPEND_DEFAULTS:
        s.dept_spend[key] = round(float(s.dept_spend.get(key, 0.0)) * (1.0 + uplift / 100.0), 1)
    after = sum(float(s.dept_spend.get(k, 0.0)) for k in SPEND_DEFAULTS)
    change = round(after - before, 1)
    s.deficit = round(float(s.get('deficit', 0.0)) + change, 1)
    s.headroom = round(float(s.get('headroom', 0.0)) - change * 0.22, 1)
    if change > 0:
        s.market_conf = round(_clip(float(s.get('market_conf', 50.0)) - min(3.0, change * 0.02)), 1)
    elif change < 0:
        s.market_conf = round(_clip(float(s.get('market_conf', 50.0)) + min(1.5, -change * 0.015)), 1)
    plan['last_applied_year'] = int(target_year)
    s.spending_review_plan = plan
    s.message = str(s.get('message', '')) + f" The year {offset} Spending Review settlement applies a {uplift:+.1f}% departmental uplift (annual cost £{change:+.1f}bn)."
    return change

def render_spending_review():
    """Annual multi-year Spending Review. Approved settlements change the live departmental baselines."""
    ensure()
    s = st.session_state
    period = f"{s.get('term', 1)}-{s.get('year', 1)}"
    s.setdefault('spending_review_history', [])
    s.setdefault('spending_review_last_period', '')
    s.setdefault('spending_review_plan', {})
    done = s.spending_review_last_period == period

    st.markdown("## 🏛️ The Spending Review")
    st.caption("Set departmental budgets for the year ahead and publish a three-year spending path. Settlements change the live Treasury baseline, not just a forecast.")
    if done:
        st.markdown(
            "<div class='treasury-notice success'><div><strong>Spending Review approved</strong>"
            "The settlement for this year is final. You can review it below, but cannot issue a second round in the same year.</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='treasury-notice info'><div><strong>Spending round open</strong>"
            "Departmental Secretaries have submitted their bids. Review the requests and set the final settlements.</div></div>",
            unsafe_allow_html=True,
        )

    departments = list(SPEND_DEFAULTS.keys())
    groups = [
        ("Public services & security", ["health", "education", "welfare", "justice", "defence", "social_care", "public_sector_pay"]),
        ("Growth & infrastructure", ["transport", "housing", "science", "climate", "local_government", "skills"]),
        ("Other services", ["aid", "culture", "other"]),
    ]
    draft = {}
    # Secretaries submit politically and operationally differentiated bids each year.
    bid_rates = {
        "health": 5.0, "education": 4.0, "welfare": 3.0, "justice": 4.5,
        "defence": 6.0, "transport": 7.0, "housing": 8.0, "science": 9.0,
        "climate": 6.5, "aid": 2.0, "culture": 3.5, "other": 2.5,
        "social_care": 5.0, "local_government": 3.5, "public_sector_pay": 4.0, "skills": 6.0,
    }
    st.markdown("### Departmental bids · Year 1")
    st.caption("Each Secretary of State has submitted a funding request. Negotiate the settlement: generous awards improve ministerial support but cost more, while rejecting bids risks cabinet tension and service pressure.")
    with st.expander("Read the Secretaries' submissions", expanded=False):
        for key in departments:
            base = float(s.dept_spend[key])
            request = bid_rates.get(key, 3.0)
            minister = s.cabinet_ministers.get(key, DEPARTMENT_MINISTERS[key][0])
            loyalty = float(s.ministerial_loyalty.get(key, 65.0))
            st.write(f"**{minister}, {SPEND_DEFAULTS[key]['label']} Secretary** · Ministerial confidence {loyalty:.0f}/100")
            st.caption(f"Priority: {DEPARTMENT_MINISTERS[key][1]}. Requests a {request:+.1f}% uplift (£{base * request / 100.0:+.1f}bn).")
    for group, keys in groups:
        with st.expander(group, expanded=(group == groups[0][0])):
            cols = st.columns(2)
            for i, key in enumerate(keys):
                if key not in SPEND_DEFAULTS:
                    continue
                base = float(s.dept_spend[key])
                widget_key = f"sr_{period}_{key}"
                # Each department begins at its submitted bid; the Chancellor can negotiate a lower or higher settlement.
                requested_pct = bid_rates.get(key, 3.0)
                default_pct = requested_pct
                if widget_key not in s:
                    s[widget_key] = default_pct
                with cols[i % 2]:
                    if done:
                        pct = 0.0
                        st.metric(SPEND_DEFAULTS[key]['label'], f"£{base:,.1f}bn", "Approved baseline")
                    else:
                        pct = st.slider(
                            f"{SPEND_DEFAULTS[key]['label']} · £{base:,.1f}bn baseline",
                            min_value=-8.0, max_value=15.0, step=0.5,
                            key=widget_key,
                            help=f"Secretary requested {requested_pct:+.1f}%. Your settlement is applied to the departmental baseline when approved."
                        )
                    draft[key] = round(base * (1 + pct / 100.0), 1)

    current_total = sum(float(s.dept_spend[k]) for k in departments)
    proposed_total = sum(draft.values()) if draft else current_total
    annual_change = proposed_total - current_total
    c1, c2, c3 = st.columns(3)
    c1.metric("Current departmental spend", f"£{current_total:,.1f}bn")
    c2.metric("Proposed settlement", f"£{proposed_total:,.1f}bn", f"£{annual_change:+,.1f}bn")
    c3.metric("Change in spending", f"{(annual_change / max(current_total, 1)) * 100:+.2f}%")

    st.markdown("### Three-year spending path")
    st.caption("Set the planned annual uplift for years two and three. Once approved, these increases automatically flow into future departmental baselines and the fiscal position.")
    c_y2, c_y3 = st.columns(2)
    with c_y2:
        year2_uplift = st.slider("Year 2 annual uplift (%)", -2.0, 6.0, 1.5, 0.5, key=f"sr_y2_{period}")
    with c_y3:
        year3_uplift = st.slider("Year 3 annual uplift (%)", -2.0, 6.0, 2.5, 0.5, key=f"sr_y3_{period}")
    path_rows = [
        {"Spending year": "Year 1 · agreed settlement", "Annual departmental budgets": f"£{proposed_total:,.1f}bn", "Annual change": f"£{annual_change:+,.1f}bn"},
        {"Spending year": "Year 2 · planned", "Annual departmental budgets": f"£{proposed_total * (1 + year2_uplift / 100):,.1f}bn", "Annual change": f"{year2_uplift:+.1f}%"},
        {"Spending year": "Year 3 · planned", "Annual departmental budgets": f"£{proposed_total * (1 + year2_uplift / 100) * (1 + year3_uplift / 100):,.1f}bn", "Annual change": f"{year3_uplift:+.1f}%"},
    ]
    st.dataframe(pd.DataFrame(path_rows), hide_index=True, use_container_width=True)

    with st.expander("What the settlement means", expanded=False):
        st.write("Higher allocations improve the capacity of services over time but increase the annual spending baseline. Large unfunded settlements can worsen borrowing, reduce fiscal headroom and unsettle markets.")
        st.write("This review excludes welfare demand changes and debt interest, which continue to be modelled separately.")

    if not done:
        if st.button("Approve Spending Review", type="primary", use_container_width=True, key="approve_spending_review"):
            # Calculate frontline changes against the old baselines before applying the settlement.
            frontline = sum(draft.get(k, s.dept_spend[k]) - float(s.dept_spend[k]) for k in ("health", "education", "justice"))
            # Apply a single annual settlement to the actual departmental baselines.
            s.checkpoint = None
            for key, amount in draft.items():
                s.dept_spend[key] = amount
                s[f"bs_{key}"] = 0.0
                s.budget_applied.setdefault("spend", {})[key] = 0.0
            # An unfunded increase worsens the annual deficit and uses fiscal room.
            s.deficit = round(float(s.deficit) + annual_change, 1)
            s.headroom = round(float(s.headroom) - annual_change * 0.22, 1)
            if annual_change > 0:
                s.market_conf = round(_clip(float(s.market_conf) - min(4.0, annual_change * 0.025)), 1)
            elif annual_change < 0:
                s.market_conf = round(_clip(float(s.market_conf) + min(2.0, -annual_change * 0.02)), 1)
            s.approval = round(_clip(float(s.approval) + max(-2.0, min(2.0, frontline * 0.025 - max(0.0, annual_change) * 0.008))), 1)
            # Department-by-department loyalty remembers whether ministers repeatedly lose their bids.
            bid_satisfaction = []
            resignations = []
            for key in departments:
                requested = float(bid_rates.get(key, 3.0))
                settled = float(s.get(f"sr_{period}_{key}", 0.0))
                gap = settled - requested
                loyalty = float(s.ministerial_loyalty.get(key, 65.0))
                loyalty_change = max(-8.0, min(3.0, gap * 0.75))
                loyalty = round(_clip(loyalty + loyalty_change), 1)
                s.ministerial_loyalty[key] = loyalty
                if loyalty <= 15.0:
                    minister = s.cabinet_ministers.get(key, DEPARTMENT_MINISTERS[key][0])
                    resignations.append((key, minister))
                    s.cabinet_ministers[key] = "Vacant — awaiting Prime Minister"
                    s.ministerial_vacancy_year[key] = int(s.get("year", 1))
                    s.ministerial_loyalty[key] = 0.0
            if resignations:
                s.ministerial_resignations.extend([
                    {"period": period, "department": key, "minister": minister}
                    for key, minister in resignations
                ])
                s.cab_opinion = round(_clip(float(s.get("cab_opinion", 65.0)) - 4.0 * len(resignations)), 1)
                s.media_opinion = round(_clip(float(s.get("media_opinion", 50.0)) - 2.0 * len(resignations)), 1)
                s.event_cards = list(s.get("event_cards", []))
                for key, minister in resignations:
                    s.event_cards.append({
                        "title": f"{minister} resigns from Cabinet",
                        "text": f"The {SPEND_DEFAULTS[key]['label']} Secretary has resigned after repeated disputes over departmental funding. The post is vacant. The Prime Minister will decide who replaces them; the Chancellor cannot appoint a successor.",
                        "summary": "Cabinet crisis · Prime Minister to appoint",
                    })
            for key in departments:
                requested = float(bid_rates.get(key, 3.0))
                settled = float(s.get(f"sr_{period}_{key}", 0.0))
                bid_satisfaction.append(max(-1.0, min(1.0, (settled - requested) / max(abs(requested), 2.0))))
            cabinet_effect = sum(bid_satisfaction) / max(1, len(bid_satisfaction)) * 5.0
            s.cab_opinion = round(_clip(float(s.get("cab_opinion", 65.0)) + cabinet_effect), 1)
            s.spending_review_plan = {
                "term": int(s.get("term", 1)), "approved_year": int(s.get("year", 1)),
                "year2_uplift": float(year2_uplift), "year3_uplift": float(year3_uplift),
                "last_applied_year": int(s.get("year", 1)),
                "allocations": {k: float(v) for k, v in draft.items()},
            }
            s.spending_review_last_period = period
            s.spending_review_history.append({
                "period": period, "annual_change": round(annual_change, 1),
                "departmental_total": round(proposed_total, 1),
                "allocations": {k: round(v, 1) for k, v in draft.items()},
                "cabinet_effect": round(cabinet_effect, 1),
            })
            s.event_cards = list(s.get("event_cards", []))
            s.event_cards.append({
                "title": "Spending Review approved",
                "text": f"You approved departmental settlements worth £{proposed_total:,.1f}bn a year. The annual spending change is £{annual_change:+,.1f}bn.",
                "summary": f"Headroom £{-annual_change * 0.22:+.1f}bn · Deficit £{annual_change:+.1f}bn",
            })
            s.message = f"Spending Review approved. Departmental budgets change by £{annual_change:+,.1f}bn a year."
            st.rerun()

    if s.spending_review_history:
        with st.expander("Previous Spending Reviews", expanded=False):
            rows = [{"Period": x["period"], "Departmental total (£bn)": x["departmental_total"], "Annual change (£bn)": x["annual_change"]} for x in reversed(s.spending_review_history)]
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
            latest = s.spending_review_history[-1]
            st.caption("Latest settlement: " + ", ".join(f"{SPEND_DEFAULTS[k]['short']} £{v:,.1f}bn" for k, v in latest["allocations"].items()))

