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



def get_weekly_decision(seed, term, year, block):
    """Draw a varied, non-repeating set of 10 policy topics for each five-year term."""
    if block not in (1, 2) or year < 1:
        return None
    slot = (year - 1) * 2 + (block - 1)
    # Keep the opening policy as a reliable tutorial and preserve its delayed-consequence example.
    opening = DECISIONS[(1, 1)]
    if slot == 0:
        return opening
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
