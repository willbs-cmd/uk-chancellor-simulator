import random
import streamlit as st
import budget
import country
import state
from content_store import load_json

def C(title, humphrey, *args):
    opts = [(args[i], args[i + 1]) for i in range(0, len(args), 2)]
    return dict(title=title, humphrey=humphrey, opts=opts)


CRISES = load_json('crises.json')['crises']


RANDOM_POOL = ['gilt_revolt', 'nhs_walkout', 'energy_bankruptcy', 'pension_hole', 'cyber_attack', 'floods', 'bank_run',
               'steel_closure', 'border_surge', 'student_loans', 'water_collapse', 'winter_flu', 'rating_warning',
               'prison_riot', 'ai_job_crisis', 'grid_blackout', 'farming_collapse', 'flash_crash',
               'global_recession', 'oil_price_spike', 'global_supply_crunch', 'trade_war', 'banking_panic',
               'technology_boom', 'food_price_crisis', 'export_surge', 'climate_disaster', 'sovereign_debt_crisis']

IDEOLOGY_LINKS = {'Hard Left': 'capital_flight', 'Free-Market': 'utility_failure', 'Fiscal Austerity': 'service_collapse'}

DECISION_LINKS = {
    (1, 1, 'Hard Left'): ('gilt_revolt', 0.5), (1, 1, 'Fiscal Austerity'): ('police_revolt', 0.6),
    (1, 2, 'Hard Left'): ('wage_spiral', 0.6), (1, 2, 'Fiscal Austerity'): ('nhs_walkout', 0.7),
    (2, 1, 'Free-Market'): ('rating_warning', 0.5), (2, 1, 'Fiscal Austerity'): ('welfare_rebellion', 0.7),
    (2, 2, 'Free-Market'): ('bank_run', 0.5), (3, 1, 'Fiscal Austerity'): ('council_bankrupt', 0.7),
    (3, 1, 'Free-Market'): ('greenbelt_revolt', 0.6), (3, 2, 'Free-Market'): ('rail_collapse', 0.6),
    (4, 1, 'Fiscal Austerity'): ('energy_bankruptcy', 0.7), (4, 2, 'Hard Left'): ('retaliation', 0.6),
    (5, 1, 'Free-Market'): ('gilt_revolt', 0.6), (5, 2, 'Hard Left'): ('nhs_walkout', 0.7),
}

BUDGET_LINKS = [
    ('nhs_walkout', 'spend', 'health', '<=', -2.0, 0.35), ('school_crisis', 'spend', 'education', '<=', -2.0, 0.35),
    ('defence_scare', 'spend', 'defence', '<=', -2.0, 0.35), ('corp_exodus', 'tax', 'corp', '>=', 30, 0.35),
    ('fuel_protest', 'tax', 'fuel', '>=', 1.0, 0.35), ('brain_drain', 'spend', 'science', '<=', -10.0, 0.35),
]

def get(crisis_id):
    return CRISES.get(crisis_id) if isinstance(crisis_id, str) else None

def _record_crisis(s, crisis_id):
    """Record a selected crisis in a rolling history used to prevent repetitive COBRA events."""
    history = list(s.get('crisis_event_history', []))
    # Older saves have only last_crisis; migrate it before adding the new item.
    previous = s.get('last_crisis')
    if previous and (not history or history[-1] != previous):
        history.append(previous)
    if not history or history[-1] != crisis_id:
        history.append(crisis_id)
    s.crisis_event_history = history[-20:]
    s.last_crisis = crisis_id


def recent_crisis_pool(recent=None, lookback=6, previous=None):
    """Return random crises that have not appeared in the most recent event window."""
    history = list(recent or [])
    if previous and (not history or history[-1] != previous):
        history.append(previous)
    count = max(0, int(lookback))
    blocked = set(history[-count:]) if count else set()
    pool = [crisis_id for crisis_id in RANDOM_POOL if crisis_id not in blocked]
    return pool or list(RANDOM_POOL)


def _budget_link_value(s, applied, section, item):
    """Measure tax triggers against the right baseline, not the displayed tax rate."""
    value = float(applied.get(section, {}).get(item, budget.TAXES[item]['default']))
    if section == 'tax' and item == 'fuel':
        # Fuel duty is stored in pence per litre (52.95 by default), not as a
        # percentage. Only an actual increase from the standard baseline counts.
        return value - float(budget.TAXES[item]['default'])
    return value


def _crisis_weight(crisis_id, s):
    """Bias random crises towards pressures already visible in the country."""
    weight = 1.0
    country_state = s.get('country', {}) if isinstance(s.get('country', {}), dict) else {}
    if crisis_id in ('gilt_revolt', 'rating_warning', 'sovereign_debt_crisis'):
        if float(s.get('market_conf', 60.0)) < 45 or float(s.get('headroom', 5.0)) < 0:
            weight += 1.7
    if crisis_id in ('nhs_walkout', 'winter_flu', 'water_collapse') and float(country_state.get('nhs_waiting', 0.0)) > 8.0:
        weight += 0.8
    if crisis_id in ('energy_bankruptcy', 'oil_price_spike', 'grid_blackout') and float(s.get('inflation', 2.0)) > 4:
        weight += 0.9
    if crisis_id in ('floods', 'climate_disaster', 'farming_collapse') and float(country_state.get('netzero', 40.0)) < 35:
        weight += 0.5
    if crisis_id in ('bank_run', 'flash_crash', 'banking_panic') and float(s.get('financial_stability', 80.0)) < 60:
        weight += 1.0
    if crisis_id in ('ai_job_crisis', 'steel_closure') and float(s.get('growth', 1.0)) < 0:
        weight += 0.8
    return weight


def pick_next(year, block, ideology):
    s = st.session_state
    s.crisis_reason = ''
    last = s.get('last_crisis')
    recent = list(s.get('crisis_event_history', []))
    if last and (not recent or recent[-1] != last):
        recent.append(last)
        s.crisis_event_history = recent[-20:]

    def fresh(crisis_id, lookback=5):
        return crisis_id not in set(recent[-lookback:]) and crisis_id != last

    # Political and fiscal crises take priority, but the same confrontation cannot
    # repeatedly interrupt the game while the underlying pressure is unchanged.
    if s.get('party_opinion', 100) < 40 and fresh('leadership_challenge'):
        s.crisis_reason = "🚨 Your party has lost faith in the government's direction!"
        _record_crisis(s, 'leadership_challenge')
        return 'leadership_challenge'

    if s.get('media_opinion', 100) < 30 and fresh('tabloid_scandal'):
        s.crisis_reason = "🚨 Fleet Street has turned against you!"
        _record_crisis(s, 'tabloid_scandal')
        return 'tabloid_scandal'

    if s.get('market_conf', 100) < 35 and fresh('gilt_revolt') and random.random() < 0.6:
        s.crisis_reason = '🚨 Investors have lost faith in your fiscal credibility!'
        _record_crisis(s, 'gilt_revolt')
        return 'gilt_revolt'

    if s.get('headroom', 0) < -10 and fresh('rating_warning') and random.random() < 0.5:
        s.crisis_reason = '🚨 Your fiscal rules are in tatters and the agencies have noticed.'
        _record_crisis(s, 'rating_warning')
        return 'rating_warning'

    link = DECISION_LINKS.get((year, block, ideology))
    if link and fresh(link[0]) and random.random() < link[1]:
        s.crisis_reason = f'🔗 This follows directly from your last decision ({ideology}).'
        _record_crisis(s, link[0])
        return link[0]

    ideology_crisis = IDEOLOGY_LINKS.get(ideology)
    if ideology_crisis and fresh(ideology_crisis) and random.random() < 0.30:
        s.crisis_reason = f'🔗 Your {ideology} approach is coming back to bite you.'
        _record_crisis(s, ideology_crisis)
        return ideology_crisis

    applied = s.get('budget_applied')
    done = s.setdefault('fallout_done', [])
    if applied and s.get('dept_spend'):
        for cid, section, item, op, limit, chance in BUDGET_LINKS:
            if cid in done or not fresh(cid):
                continue
            if section == 'spend':
                # Cumulative change in this department's baseline since the start.
                base = budget.SPEND_DEFAULTS[item]['default']
                value = (s.dept_spend.get(item, base) / base - 1) * 100
            else:
                value = _budget_link_value(s, applied, section, item)
            hit = value <= limit if op == '<=' else value >= limit
            if hit and random.random() < chance:
                done.append(cid)
                s.crisis_reason = '📒 Your budget choices have consequences.'
                _record_crisis(s, cid)
                return cid

    if year < 5 and random.random() < state.diff()['crisis']:
        options = recent_crisis_pool(recent, lookback=6, previous=last)
        weights = [_crisis_weight(crisis_id, s) for crisis_id in options]
        crisis_id = random.choices(options, weights=weights, k=1)[0]
        _record_crisis(s, crisis_id)
        s.crisis_reason = "🚨 Events, dear boy, events. An unforeseen crisis has struck!"
        return crisis_id

    return None

def _fmt(fx):
    parts = []
    if 'headroom' in fx: parts.append(f"{'-' if fx['headroom'] < 0 else '+'}£{abs(fx['headroom']):g}B Headroom")
    for key, name in (('approval', 'Approval'), ('market', 'Market Conf'), ('growth', 'Growth'),
                      ('inflation', 'Inflation'), ('deficit', 'Deficit'), ('debt', 'Debt'),
                      ('pm_opinion', 'PM'), ('cab_opinion', 'Cabinet'), ('party_opinion', 'Party'),
                      ('backbench_opinion', 'Backbench'), ('media_opinion', 'Media')):
        if key in fx: parts.append(f'{fx[key]:+g} {name}')
    return ', '.join(parts)

def option_labels(crisis):
    return [f'{label} ({_fmt(fx)})' if _fmt(fx) else label for label, fx in crisis['opts']]

def _clip(v):
    return max(0, min(100, v))

def apply_fx(fx):
    s = st.session_state
    sc = state.scale
    if 'headroom' in fx: s.headroom = round(s.headroom + sc(fx['headroom']), 1)
    if 'approval' in fx: s.approval = round(_clip(s.approval + sc(fx['approval'])), 1)
    if 'market' in fx: s.market_conf = round(_clip(s.market_conf + sc(fx['market'])), 1)
    if 'growth' in fx: s.growth = round(s.growth + fx['growth'], 2)
    if 'inflation' in fx: s.inflation = round(s.inflation + fx['inflation'], 2)
    if 'deficit' in fx: s.deficit = round(s.deficit + fx['deficit'], 1)
    if 'debt' in fx: s.debt = round(s.debt + fx['debt'], 1)
    if 'gilt' in fx: s.gilt_yield = round(s.gilt_yield + fx['gilt'], 2)
    # political capital (these keys were previously ignored)
    for key in ('pm_opinion', 'cab_opinion', 'party_opinion', 'backbench_opinion', 'media_opinion'):
        if key in fx:
            s[key] = round(_clip(s[key] + fx[key]), 1)

    # Pass direct effects down to the country file too!
    country.nudge({k: v for k, v in fx.items() if k in country.STATS}, snapshot=False)


def proxy_ideology(fx):
    """Rough ideological flavour of a crisis response, judged by what it does."""
    head, app, mkt = fx.get('headroom', 0), fx.get('approval', 0), fx.get('market', 0)
    if head <= -3 and app > 0:
        return 'Social Democratic' if mkt >= -4 else 'Hard Left'
    if head > 0 and app < 0:
        return 'Fiscal Austerity'
    if mkt > 0 and app < 0:
        return 'Free-Market'
    return 'Centric'


def resolve(crisis, index):
    label, fx = crisis['opts'][index]
    apply_fx(fx)
    
    if 'last_humphrey_quote' not in st.session_state:
        st.session_state.last_humphrey_quote = ""
        
    humphrey_replies = [
        "A very courageous decision, Chancellor.",
        "Quite so, Chancellor. I shall draft a press release meaning absolutely nothing.",
        "I foresee immense administrative complications, but I shall execute your will, Chancellor.",
        "A bold strategy, Chancellor. The exact strategy, in fact, that ruined your predecessor.",
        "Yes, Chancellor. In the fullness of time, this may even prove to have been the right choice.",
        "If you insist, Chancellor. Though I must point out that in government, doing nothing is often the most productive course of action.",
        "Excellent, Chancellor. We shall set up an interdepartmental committee to monitor the implementation. That should delay it indefinitely.",
        "As you wish, Chancellor. I shall instruct the civil service to proceed with all deliberate lack of speed.",
        "A triumph of hope over experience, Chancellor.",
        "To be perfectly frank, Chancellor, the Treasury views this decision with a mixture of horror and profound amusement.",
        "I am fully seized of your instructions, Chancellor, and will implement them with the exact degree of enthusiasm they warrant.",
        "An interesting approach. Usually, when one is in a hole, one stops digging. But you have asked for a larger shovel."
    ]
    
    available_replies = [r for r in humphrey_replies if r != st.session_state.last_humphrey_quote]
    chosen_quote = random.choice(available_replies)
    st.session_state.last_humphrey_quote = chosen_quote
    
    return f"<b>Crisis handled: {label}</b><br><br><i>Sir Humphrey Appleby adds:</i> &ldquo;{chosen_quote}&rdquo;"
