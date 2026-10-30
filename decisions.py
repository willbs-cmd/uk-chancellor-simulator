"""Policy decisions: 2 blocks per year, followed by the Budget.

Each decision lists five options in a fixed ideology order (see IDEOLOGIES). The game shuffles them and
hides the ideology tags unless the player turns them on. Some options also queue a DELAYED consequence."""
import random
import re

from content_store import load_json

_CONTENT_DATA = load_json('decisions.json')

BLOCKS_PER_YEAR = 3   
BUDGET_BLOCK = 3
IDEOLOGIES = _CONTENT_DATA['ideologies']

DECISIONS = {}
for _item in _CONTENT_DATA['decisions']:
    _key = (int(_item['year']), int(_item['block']))
    DECISIONS[_key] = dict(_item['decision'])




# ---------------------------------------------------------------------------------------------
# Branching policy storylines. These are unlocked by what the Chancellor actually chose,
# not by a random draw. A branch can appear once per term and changes the next policy agenda.
BRANCHES = {
    'public_services': {
        'title': 'The Public Services Settlement',
        'text': 'Your earlier commitments have raised expectations across the public sector. Unions, NHS leaders and the Treasury now want a clear settlement. The choice will shape the next phase of your government.',
        'humphrey': 'Chancellor, having promised to rebuild public services, we are now faced with the minor inconvenience of having to rebuild public services. The unions have noticed.',
        'trigger': {'Hard Left', 'Social Democratic'},
        'options': [
            '1. (Hard Left) Fund a major multi-year expansion of frontline services.',
            '2. (Social Democratic) Agree a workforce and productivity compact with public services.',
            '3. (Centric) Target extra funding at the worst-performing services.',
            '4. (Free-Market) Expand independent-sector provision to cut waiting times.',
            '5. (Fiscal Austerity) Require departments to absorb costs through efficiency savings.'
        ],
        'effects': [
            {'headroom': -7.0, 'approval': 5.0, 'nhs_morale': 12, 'schools': 4, 'growth': 0.15, 'message': 'A major public-service expansion is underway.'},
            {'headroom': -4.0, 'approval': 4.0, 'nhs_morale': 9, 'unemployment': -0.1, 'message': 'A workforce and productivity compact is agreed.'},
            {'headroom': -2.0, 'approval': 1.5, 'nhs_morale': 4, 'message': 'Funding is concentrated on the services under greatest strain.'},
            {'headroom': -1.0, 'market_conf': 3.0, 'approval': 0.5, 'nhs_morale': 1, 'message': 'Independent providers take on more NHS activity.'},
            {'headroom': 3.5, 'approval': -3.5, 'nhs_morale': -7, 'schools': -3, 'message': 'Departments are ordered to find savings.'}
        ]
    },
    'growth_mission': {
        'title': 'The National Growth Mission',
        'text': 'Your earlier economic choices have created pressure for a long-term growth strategy. Business groups, regional leaders and the OBR are asking what comes next.',
        'humphrey': 'The good news, Chancellor, is that everyone supports growth. The bad news is that they all have rather different ideas about who should pay for it.',
        'trigger': {'Centric', 'Social Democratic'},
        'options': [
            '1. (Hard Left) Create a state-led national investment bank and direct public investment.',
            '2. (Social Democratic) Launch regional investment partnerships and skills guarantees.',
            '3. (Centric) Establish a cross-party infrastructure and planning commission.',
            '4. (Free-Market) Cut business taxes and accelerate deregulation.',
            '5. (Fiscal Austerity) Prioritise debt reduction before new growth spending.'
        ],
        'effects': [
            {'headroom': -6.0, 'growth': 0.35, 'approval': 2.0, 'debt': 0.5, 'message': 'A state-led investment drive begins.'},
            {'headroom': -4.0, 'growth': 0.3, 'unemployment': -0.2, 'approval': 3.0, 'message': 'Regional investment partnerships are launched.'},
            {'headroom': -1.5, 'growth': 0.2, 'homes_built': 10, 'market_conf': 2.0, 'message': 'Planning and infrastructure reform is agreed.'},
            {'headroom': 1.5, 'growth': 0.25, 'market_conf': 4.0, 'approval': -1.0, 'message': 'Business tax and regulatory changes are announced.'},
            {'headroom': 4.0, 'growth': -0.1, 'approval': -2.0, 'market_conf': 2.0, 'message': 'New investment is deferred in favour of fiscal consolidation.'}
        ]
    },
    'market_reform': {
        'title': 'The Market Reform Programme',
        'text': 'Your previous market-oriented decisions have emboldened business leaders and unsettled parts of the governing party. You must now decide how far the reform programme should go.',
        'humphrey': 'The markets are encouraged, Chancellor. Your backbenchers are less so. I believe the technical term is a mixed reception.',
        'trigger': {'Free-Market'},
        'options': [
            '1. (Hard Left) Halt privatisations and restore public ownership safeguards.',
            '2. (Social Democratic) Strengthen regulation while retaining private investment.',
            '3. (Centric) Review each reform against value-for-money tests.',
            '4. (Free-Market) Accelerate competition, outsourcing and tax simplification.',
            '5. (Fiscal Austerity) Use asset sales to reduce borrowing.'
        ],
        'effects': [
            {'approval': 3.0, 'market_conf': -5.0, 'headroom': -2.0, 'message': 'The government pauses the market reform programme.'},
            {'approval': 1.5, 'market_conf': 1.0, 'headroom': -1.0, 'message': 'A stronger regulatory framework is introduced.'},
            {'approval': 0.5, 'market_conf': 1.5, 'headroom': 0.5, 'message': 'Reforms are subjected to value-for-money reviews.'},
            {'approval': -1.5, 'market_conf': 5.0, 'growth': 0.25, 'headroom': 2.0, 'message': 'The market reform programme is accelerated.'},
            {'approval': -2.5, 'market_conf': 3.0, 'headroom': 4.0, 'debt': -0.5, 'message': 'Selected public assets are sold to reduce borrowing.'}
        ]
    },
    'fiscal_reset': {
        'title': 'The Fiscal Credibility Test',
        'text': "Your previous decisions have put fiscal discipline at the centre of the government's identity. The Treasury and bond markets now expect a credible medium-term plan.",
        'humphrey': 'The markets are demanding a plan, Chancellor. Preferably one with numbers in it. They are terribly old-fashioned that way.',
        'trigger': {'Fiscal Austerity'},
        'options': [
            '1. (Hard Left) Reject further cuts and protect household incomes.',
            '2. (Social Democratic) Protect core services but raise targeted revenue.',
            '3. (Centric) Publish a balanced multi-year fiscal framework.',
            '4. (Free-Market) Use supply-side tax reforms to lift receipts over time.',
            '5. (Fiscal Austerity) Set out a tough spending and borrowing reduction plan.'
        ],
        'effects': [
            {'approval': 3.0, 'headroom': -4.0, 'market_conf': -3.0, 'message': 'The government protects household incomes.'},
            {'approval': 1.5, 'headroom': -2.0, 'deficit': -0.3, 'message': 'Targeted revenue measures support core services.'},
            {'headroom': 1.5, 'market_conf': 3.0, 'approval': 0.5, 'message': 'A balanced fiscal framework is published.'},
            {'growth': 0.2, 'market_conf': 3.0, 'headroom': 0.5, 'message': 'Supply-side tax reforms are announced.'},
            {'headroom': 5.0, 'deficit': -0.8, 'approval': -4.0, 'growth': -0.15, 'message': 'A tough consolidation plan is adopted.'}
        ]
    }
}


def _unlocked_branch(policy_history):
    history = policy_history or []
    used = {item.get('branch_id') for item in history if item.get('branch_id')}
    counts = {}
    for item in history:
        if item.get('ideology'):
            counts[item['ideology']] = counts.get(item['ideology'], 0) + 1
    eligible = []
    for branch_id, branch in BRANCHES.items():
        if branch_id not in used and any(counts.get(ideology, 0) for ideology in branch['trigger']):
            strength = sum(counts.get(ideology, 0) for ideology in branch['trigger'])
            eligible.append((strength, branch_id, branch))
    if not eligible:
        return None
    _, branch_id, branch = sorted(eligible, key=lambda row: (-row[0], list(BRANCHES).index(row[1])))[0]
    item = {k: branch[k] for k in ('title', 'text', 'humphrey', 'options', 'effects')}
    item['branch_id'] = branch_id
    item['_key'] = None
    return item



def get_weekly_decision(seed, term, year, block, policy_history=None):
    """Draw a varied, non-repeating set of 10 policy topics for each five-year term."""
    if block not in (1, 2) or year < 1:
        return None
    slot = (year - 1) * 2 + (block - 1)
    # Keep the opening policy as a reliable tutorial. Later, choices can unlock a bespoke branch.
    opening = DECISIONS[(1, 1)]
    if slot == 0:
        return opening
    branch = _unlocked_branch(policy_history)
    if branch:
        return branch
    pool = [d for d in DECISIONS.values() if d is not opening]
    random.Random(f'{seed}-{term}-weekly-policy-variety').shuffle(pool)
    if slot - 1 >= len(pool):
        return None
    return pool[slot - 1]


# ---------------------------------------------------------------------------------------------
# Delayed consequences: (year, block) -> {option index: spec}. 'after' counts player actions
# (decisions, crises, budgets) before it lands. Not every option has one; some are rewards.
# ---------------------------------------------------------------------------------------------
DELAYED = {}
for _item in _CONTENT_DATA['delayed']:
    _key = (int(_item['year']), int(_item['block']))
    DELAYED[_key] = {int(_option): _spec for _option, _spec in _item['options'].items()}

REACTIONS = _CONTENT_DATA['reactions']

_TAG = re.compile(r'^\d+\.\s*\(([^)]+)\)\s*')


def strip_tag(text):
    """Remove the leading '1. (Hard Left) ' from an option."""
    return _TAG.sub('', text)


def get_options(decision, shuffle_key, show_tags=False):
    """Return the decision's options as dicts, shuffled deterministically by ``shuffle_key``.

    Each dict has: label (what the player reads), ideology, effect, delayed (spec or None).
    """
    key = decision.get('_key')
    delayed = DELAYED.get(key, {})
    options = []
    for i, (text, fx) in enumerate(zip(decision['options'], decision['effects'])):
        body = strip_tag(text)
        ideology = IDEOLOGIES[i]
        options.append(dict(label=f'({ideology}) {body}' if show_tags else body, ideology=ideology,
                            effect=fx, delayed=delayed.get(i)))
    random.Random(shuffle_key).shuffle(options)
    return options


def reaction(ideology, d_approval, d_market, delayed=None):
    """Sir Humphrey's comment on what the player just did."""
    pool = REACTIONS.get(ideology, REACTIONS['Centric'])
    if d_approval + 0.5 * d_market >= 8:
        pool = REACTIONS['triumph']
    elif d_approval + 0.5 * d_market <= -10:
        pool = REACTIONS['disaster']
    text = random.choice(pool)
    if delayed:
        text += f" (A word of caution, Chancellor: {delayed['warn']})"
    return text


for _k, _d in DECISIONS.items():
    _d['_key'] = _k
