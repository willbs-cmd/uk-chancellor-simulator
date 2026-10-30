"""The Budget speech and the morning-after reactions, written from what you actually changed."""
import random

import streamlit as st

import budget

RATE_TAXES = ('income', 'ni', 'vat', 'corp', 'cgt', 'iht')   # taxes quoted as a rate; the rest are '% change' levers
MAX_ITEMS = 4


def _pts(n):
    n = abs(n)
    return f"{n:g} point{'s' if n != 1 else ''}"


def _tax_changes():
    s = st.session_state
    last = s.get('budget_last_tax', {})
    out = []
    for k, t in budget.TAXES.items():
        d = s.budget_applied['tax'][k] - last.get(k, t['default'])
        if d == 0:
            continue
        up = d > 0
        if k in RATE_TAXES:
            out.append((k, up, f"{t['short']} will {'rise' if up else 'fall'} by {_pts(d)} to {s.budget_applied['tax'][k]:g}%"))
        else:
            out.append((k, up, f"{t['short']} will {'rise' if up else 'fall'} by {abs(d):g}%"))
    return out


def _spend_changes():
    s = st.session_state
    out = []
    for k, sp in budget.SPEND_DEFAULTS.items():
        pct = s.budget_applied['spend'].get(k, 0.0)
        if pct:
            out.append((k, pct > 0, f"{sp['short']} funding will {'rise' if pct > 0 else 'fall'} by {abs(pct):g}%"))
    return out


def _new_schemes():
    s = st.session_state
    last = s.get('budget_last_pol') or {}
    out = []
    for key, table in (('tax_pol', budget.TAX_POLICIES), ('spend_pol', budget.SPEND_POLICIES)):
        for k, p in table.items():
            if s.budget_applied[key].get(k) and not last.get(key, {}).get(k):
                out.append(p['label'])
    return out


def _join(items):
    items = items[:MAX_ITEMS] + (['and more besides'] if len(items) > MAX_ITEMS else [])
    return '; '.join(items)


def compose():
    """Returns {'text': speech, 'reactions': [(who, quote), ...]}. Uses the session's seeded RNG."""
    s = st.session_state
    imp = s.get('budget_impact') or {}
    head = imp.get('headroom', 0.0)
    taxes, spends, schemes = _tax_changes(), _spend_changes(), _new_schemes()

    if head >= 3:
        opener = random.choice(['Mr Speaker, this is a Budget of fiscal responsibility.',
                                'Mr Speaker, today I put the public finances on a sound footing.'])
    elif head <= -3:
        opener = random.choice(['Mr Speaker, this is a Budget for investment and renewal.',
                                'Mr Speaker, I will not apologise for choosing to invest in Britain.'])
    else:
        opener = random.choice(['Mr Speaker, this is a Budget that balances ambition with prudence.',
                                'Mr Speaker, this is a steady Budget for uncertain times.'])

    strategy = budget.FISCAL_STRATEGIES.get(s.get('budget_strategy', 'balanced'), budget.FISCAL_STRATEGIES['balanced'])
    parts = [opener, f"Our fiscal approach is {strategy['label'].lower()}: {strategy['description']}"]
    if s.get('budget_message'):
        parts.append(s.budget_message.strip())
    if taxes:
        parts.append('On tax: ' + _join([t[2] for t in taxes]) + '.')
    if spends:
        parts.append('On public services: ' + _join([t[2] for t in spends]) + '.')
    if schemes:
        parts.append('And I can announce: ' + _join(schemes) + '.')
    if not (taxes or spends or schemes):
        parts.append('I am making no changes to tax or spending this year.')
    within = 'within' if s.headroom >= 0 else 'outside'
    parts.append(f'The OBR confirms the Government remains {within} its fiscal rules, with headroom of £{s.headroom:.1f} billion.')

    reactions = _reactions(imp, taxes, spends)
    ayes = int(s.get('vote_ayes') or budget.commons_ayes())
    amendments = [
        {"title": "Opposition amendment: reverse the headline tax changes", "detail": "The Shadow Chancellor argues that the tax package hits households and businesses.", "ayes": max(80, min(320, int(ayes * 0.58 + random.randint(-12, 12)))), "result": "Defeated"},
        {"title": "Opposition amendment: increase funding for public services", "detail": "The Opposition demands additional funding and challenges the Government's priorities.", "ayes": max(90, min(320, int(ayes * 0.63 + random.randint(-10, 10)))), "result": "Defeated"},
    ]
    if imp.get('headroom', 0) < -3:
        market_line = "Investors demand a higher risk premium after a borrowing-heavy statement."
    elif imp.get('market', 0) > 1:
        market_line = "Investors welcome the fiscal package; gilt demand strengthens."
    elif imp.get('market', 0) < -1:
        market_line = "Investors are uneasy; sterling and gilts come under pressure."
    else:
        market_line = "Markets show a muted response as investors digest the detail."
    day = [
        ("08:00", "The Red Box arrives", "The final Budget papers are delivered to the House of Commons."),
        ("12:30", "The Chancellor rises", "The Budget speech begins and the main tax and spending measures are announced."),
        ("14:00", "Opposition response", "The Shadow Chancellor attacks the Government's choices and tables amendments."),
        ("15:30", "The House divides", "MPs vote on the Opposition amendments before the main Budget motion."),
        ("16:00", "The markets react", market_line),
        ("18:00", "The evening headlines", "Broadcasters and newspapers deliver their verdict on the Chancellor's package."),
    ]
    return dict(text=' '.join(parts), reactions=reactions, amendments=amendments, budget_day=day, market_line=market_line)


def _reactions(imp, taxes, spends):
    s = st.session_state
    head, mkt, growth = imp.get('headroom', 0.0), imp.get('market', 0.0), imp.get('growth', 0.0)
    raised = any(up for _, up, _ in taxes)
    quiet = not (taxes or spends)

    if quiet:
        shadow = "A Budget of absolutely nothing. The Chancellor has run out of ideas."
    elif head < -3:
        shadow = random.choice(["Reckless borrowing that our children will have to pay for.",
                                "The Chancellor is spending money we simply do not have."])
    elif raised:
        shadow = random.choice(["Working families will pay the price for this Chancellor's failures.",
                                "Another Budget, another raid on people's pockets."])
    else:
        shadow = "Too little, too late. Britain deserves better than this."

    if mkt >= 1:
        city = "Investors welcomed the Budget, and gilts rallied as the City breathed a sigh of relief."
    elif mkt <= -1:
        city = "Gilts wobbled and sterling slipped as the City absorbed the Budget with open dismay."
    else:
        city = "The City shrugged. Markets were little changed by a Budget with few surprises."

    protected = [k for k, up, _ in spends if up and k in ('health', 'education', 'welfare')]
    cut = [k for k, up, _ in spends if not up and k in ('health', 'education', 'welfare')]
    if cut:
        tuc = "Cuts to our public services will be paid for in human misery. Unions are already preparing to respond."
    elif protected:
        tuc = "We welcome the extra money for frontline services. It is a start, but there is a long way to go."
    else:
        tuc = "Nothing here for the workers who keep this country running."

    verdict = 'inside' if s.headroom >= 0 else 'outside'
    ifs = f"The Chancellor is {verdict} the fiscal rules, with £{s.headroom:.1f}bn of headroom."
    if growth >= 0.1:
        ifs += ' Some measures should give growth a modest boost.'
    elif growth <= -0.1:
        ifs += ' Some measures are likely to weigh on growth.'

    return [('Shadow Chancellor', shadow), ('The City', city), ('The TUC', tuc), ('Institute for Fiscal Studies', ifs)]
