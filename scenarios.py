import random
import streamlit as st
import budget
import country
import state
from content_store import load_json

def C(title, humphrey, *args):
    opts = [(args[i], args[i+1]) for i in range(0, len(args), 2)]
    return dict(title=tiCRISES = load_json('crises.json')['crises']
om=-1.0, market=2, approval=1)),
}


RANDOM_POOL = ['gilt_revolt', 'nhs_walkout', 'energy_bankruptcy', 'pension_hole', 'cyber_attack', 'floods', 'bank_run',
               'steel_closure', 'border_surge', 'student_loans', 'water_collapse', 'winter_flu', 'rating_warning',
               'prison_riot', 'ai_job_crisis', 'grid_blackout', 'farming_collapse', 'flash_crash']

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
    ('fuel_protest', 'tax', 'fuel', '>=', 20, 0.35), ('brain_drain', 'spend', 'science', '<=', -10.0, 0.35),
]

def get(crisis_id):
    return CRISES.get(crisis_id) if isinstance(crisis_id, str) else None

def pick_next(year, block, ideology):
    s = st.session_state
    s.crisis_reason = ''
    last = s.get('last_crisis')

    # 1. NEW: Check Political Capital Crises FIRST
    if s.get('party_opinion', 100) < 40 and last != 'leadership_challenge':
        s.crisis_reason = "🚨 Your party has lost faith in the government's direction!"
        s.last_crisis = 'leadership_challenge'
        return 'leadership_challenge'
        
    if s.get('media_opinion', 100) < 30 and last != 'tabloid_scandal':
        s.crisis_reason = "🚨 Fleet Street has turned against you!"
        s.last_crisis = 'tabloid_scandal'
        return 'tabloid_scandal'

    if s.get('market_conf', 100) < 35 and last != 'gilt_revolt' and random.random() < 0.6:
        s.crisis_reason = '🚨 Investors have lost faith in your fiscal credibility!'
        s.last_crisis = 'gilt_revolt'
        return 'gilt_revolt'

    if s.get('headroom', 0) < -10 and last != 'rating_warning' and random.random() < 0.5:
        s.crisis_reason = '🚨 Your fiscal rules are in tatters and the agencies have noticed.'
        s.last_crisis = 'rating_warning'
        return 'rating_warning'

    link = DECISION_LINKS.get((year, block, ideology))
    if link and random.random() < link[1]:
        s.crisis_reason = f'🔗 This follows directly from your last decision ({ideology}).'
        s.last_crisis = link[0]
        return link[0]

    if ideology in IDEOLOGY_LINKS and random.random() < 0.30:
        s.crisis_reason = f'🔗 Your {ideology} approach is coming back to bite you.'
        s.last_crisis = IDEOLOGY_LINKS[ideology]
        return IDEOLOGY_LINKS[ideology]

    applied = s.get('budget_applied')
    done = s.setdefault('fallout_done', [])
    if applied and s.get('dept_spend'):
        for cid, section, item, op, limit, chance in BUDGET_LINKS:
            if cid in done:
                continue
            if section == 'spend':
                # cumulative change in this department's baseline since the start, in %
                base = budget.SPEND_DEFAULTS[item]['default']
                value = (s.dept_spend.get(item, base) / base - 1) * 100
            else:
                value = applied[section].get(item, budget.TAXES[item]['default'])
            hit = value <= limit if op == '<=' else value >= limit
            if hit and random.random() < chance:
                done.append(cid)
                s.crisis_reason = '📒 Your budget choices have consequences.'
                s.last_crisis = cid
                return cid

    if year < 5 and random.random() < state.diff()['crisis']:
        options = [c for c in RANDOM_POOL if c != last] or RANDOM_POOL
        s.last_crisis = random.choice(options)
        s.crisis_reason = "🚨 Events, dear boy, events. An unforeseen crisis has struck!"
        return s.last_crisis
        
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
