"""Game engine: every rule of the simulator, with no UI. app.py drives it; sim.py can drive it headlessly."""
import math
import random

import streamlit as st

import achievements
import budget
import country
import econ
import decisions
import politics
import parliament
import speech
import scenarios as scen
import state
import world_economy

SEATS = 650
REQUEST_CHANCE = 0.35

# fiscal credibility, applied once a year: approval gained/lost per £B of headroom (and its cap)
CRED_GAIN, CRED_GAIN_CAP = 0.5, 10.0
CRED_LOSS, CRED_LOSS_CAP = 0.45, 9.0
WIN_MAJORITY = budget.WIN
LEFT_BLOC = ['Labour', 'Liberal Democrats', 'Green Party', 'SNP', 'Plaid Cymru']
RIGHT_BLOC = ['Conservative', 'Reform UK', 'Liberal Democrats']

# which ideologies each party's MPs consider "home territory"
PURITY = {
    'Labour': ['Social Democratic', 'Hard Left'],
    'Conservative': ['Free-Market', 'Fiscal Austerity'],
    'Liberal Democrats': ['Centric', 'Social Democratic'],
    'Reform UK': ['Free-Market'],
    'Green Party': ['Hard Left', 'Social Democratic'],
    'SNP': ['Social Democratic', 'Centric'],
    'Plaid Cymru': ['Social Democratic', 'Hard Left'],
}


def _clip(val, lo=0.0, hi=100.0):
    return max(lo, min(hi, val))


def reseed(tag=''):
    """Make every action deterministic for a given seed + step, so runs can be replayed and saves reload exactly."""
    s = st.session_state
    random.seed(f"{s.get('seed', 0)}:{s.get('steps', 0)}:{tag}")


# ================================================================ headlines
def generate_headlines(ideology, is_budget=False, headroom=0):
    if is_budget:
        if headroom > 2.0: return ("AUSTERITY BUDGET IGNORES THE POOR", "CHANCELLOR BUILDS FISCAL FORTRESS", "A PRUDENT BUDGET AT LAST")
        elif headroom < -2.0: return ("END TO AUSTERITY!", "MARKETS PANIC OVER DEFICIT SPENDING", "RECKLESS BORROWING THREATENS ECONOMY")
        else: return ("A MIXED BAG FOR WORKERS", "CHANCELLOR WALKS THE TIGHTROPE", "PLAYING IT SAFE BEFORE ELECTION")

    headlines = {
        'Hard Left': (
            random.choice(["POWER TO THE PEOPLE!", "BOLD REFORMS AT LAST", "CHANCELLOR TAKES ON THE ELITES"]),
            random.choice(["MARKETS JITTERY AFTER RADICAL MOVE", "TREASURY TAKES A SHARP LEFT", "A COSTLY GAMBLE?"]),
            random.choice(["MARXIST MADNESS!", "CLASS WAR DECLARED", "ECONOMY ON THE BRINK"])),
        'Social Democratic': (
            random.choice(["A FAIRER DEAL", "INVESTING IN OUR FUTURE", "FINALLY, SOME COMMON SENSE"]),
            random.choice(["A PRAGMATIC COMPROMISE", "MODERATE SPENDING BOOST", "CHANCELLOR WALKS THE TIGHTROPE"]),
            random.choice(["TAX AND SPEND RETURNS", "NANNY STATE EXPANDS", "WHO IS PAYING FOR THIS?"])),
        'Centric': (
            random.choice(["STATUS QUO MAINTAINED", "LACK OF AMBITION", "A MISSED OPPORTUNITY"]),
            random.choice(["A STEADY HAND AT THE TILLER", "SENSIBLE GOVERNANCE", "CHANCELLOR PLAYS IT SAFE"]),
            random.choice(["DULL BUT DUTIFUL", "WHERE IS THE GROWTH PLAN?", "KICKING THE CAN DOWN THE ROAD"])),
        'Free-Market': (
            random.choice(["FAT CATS REJOICE", "WORKERS THROWN UNDER THE BUS", "SLASH AND BURN ECONOMICS"]),
            random.choice(["DEREGULATION DRIVE BEGINS", "A ROLL OF THE DICE", "MARKETS CHEER, PUBLIC GROANS"]),
            random.choice(["A BREATH OF FRESH AIR", "BRITAIN IS OPEN FOR BUSINESS", "FINALLY, SOME GROWTH!"])),
        'Fiscal Austerity': (
            random.choice(["CRUEL CUTS BITE DEEP", "AUSTERITY 2.0 DECLARED", "THE VULNERABLE PAY THE PRICE"]),
            random.choice(["TOUGH MEDICINE ADMINISTERED", "BELTS TIGHTENED AT THE TREASURY", "THE DEFICIT HAWKS RETURN"]),
            random.choice(["BALANCING THE BOOKS", "FISCAL RESPONSIBILITY AT LAST", "HARD CHOICES, RIGHT DECISIONS"])),
    }
    return headlines.get(ideology, headlines['Centric'])


# ================================================================ political capital & polls
def update_political_capital(ideology_chosen, approval_diff, headroom_diff):
    s = st.session_state
    core = PURITY.get(s.party, ['Centric'])
    if ideology_chosen in core:
        s.backbench_opinion += random.uniform(2, 6)
        s.party_opinion += random.uniform(1, 4)
    elif ideology_chosen == 'Centric':
        # centrism upsets nobody much
        s.backbench_opinion -= random.uniform(1, 3)
        s.party_opinion -= random.uniform(0, 2)
    else:
        s.backbench_opinion -= random.uniform(3, 6)
        s.party_opinion -= random.uniform(1, 3)

    market_diff = s.market_conf - s.prev.get('market_conf', s.market_conf)
    s.pm_opinion += (approval_diff * 1.0) + (headroom_diff * 0.8)
    s.cab_opinion += approval_diff + random.uniform(-2, 3)
    s.media_opinion += (approval_diff * 0.8) + (market_diff * 0.5)

    for k in ('pm_opinion', 'cab_opinion', 'party_opinion', 'backbench_opinion', 'media_opinion'):
        s[k] = round(_clip(s[k]), 1)


def update_polls(label):
    """Move the polls one step towards where approval and the state of the nation say they should be."""
    s = st.session_state
    ph, gov = s.poll_history, s.party
    nation = (country._overall(s.country) - 0.5) * 100
    shift = (s.approval - 50) * 0.5 + nation * 0.15
    if s.get('spad') == 'pollster' and s.approval >= 50:
        shift += 1.5
    if gov in state.REGIONAL:
        shift *= 0.2
    last = {p: ph[p][-1] for p in state.PARTIES}
    anchor = s.poll_anchor.get(gov, last[gov])

    new = dict(last)
    new[gov] = last[gov] + 0.35 * (anchor + shift - last[gov]) + random.uniform(-0.6, 0.6)
    rest = [p for p in state.PARTIES if p != gov]
    rest_old = sum(last[p] for p in rest)
    remaining = 100 - new[gov]
    for p in rest:
        new[p] = last[p] / rest_old * remaining + random.uniform(-0.5, 0.5)
    for p in new:
        new[p] = max(1 if p in state.REGIONAL else 4, new[p])
    total = sum(new.values())
    ph['Period'].append(label)
    for p in state.PARTIES:
        ph[p].append(round(new[p] / total * 100, 1))


def _period_label():
    s = st.session_state
    return f"Y{(s.term - 1) * 5 + s.year}.{s.block}"


# ================================================================ applying effects
def apply_effect(effect):
    """Apply a decision's (or delayed consequence's) effects. Good/bad swings are scaled by difficulty."""
    s = st.session_state
    sc = state.scale
    if 'headroom' in effect: s.headroom = round(s.headroom + sc(effect['headroom']), 1)
    if 'approval' in effect: s.approval = round(_clip(s.approval + sc(effect['approval'])), 1)
    if 'market_conf' in effect: s.market_conf = round(_clip(s.market_conf + sc(effect['market_conf'])), 1)
    if 'deficit' in effect: s.deficit = round(s.deficit + effect['deficit'], 1)
    if 'growth' in effect: s.growth = round(s.growth + effect['growth'], 2)
    if 'inflation' in effect: s.inflation = round(s.inflation + effect['inflation'], 2)
    if 'gilt_yield' in effect: s.gilt_yield = round(s.gilt_yield + effect['gilt_yield'], 2)
    country.nudge({k: v for k, v in effect.items() if k in country.STATS}, snapshot=False)


def deliver_pending():
    """Land any delayed consequences that have come due."""
    s = st.session_state
    due = [p for p in s.pending if p['due'] <= s.steps]
    if not due:
        return
    s.pending = [p for p in s.pending if p['due'] > s.steps]
    for p in due:
        before = state.values()
        apply_effect(p['fx'])
        s.event_cards.append(dict(title=p['title'], text=p['text'], summary=state.fmt_fx(p['fx'])))
        state.log('event', p['title'], note=p['text'], before=before)


def settle():
    """Run after every decision or crisis: politics drifts back towards normal, and overspending is punished."""
    s = st.session_state
    s.approval = round(_clip(s.approval + 0.06 * (50 - s.approval)), 1)
    if s.headroom < 0:
        # breaching your fiscal rules spooks the markets a little more with every action
        s.market_conf = round(_clip(s.market_conf - min(3.0, 0.2 * -s.headroom)), 1)


# ================================================================ the decision loop
def current_decision():
    s = st.session_state
    return decisions.get_weekly_decision(s.get('seed', 0), s.get('term', 1), s.get('year', 1), s.get('block', 1))


def current_options():
    s = st.session_state
    d = current_decision()
    if not d:
        return []
    return decisions.get_options(d, f"{s.seed}-{s.term}-{s.year}-{s.block}", s.show_tags)


def execute_decision(opt):
    """Run one policy decision. ``opt`` is an option dict from ``current_options()``."""
    s = st.session_state
    state.checkpoint()
    reseed('decision')
    s.event_cards = []
    before = state.values()
    state.snapshot()
    ideology, effect = opt['ideology'], opt['effect']
    decision = current_decision()

    vote = parliament.review_bill(decision, opt)
    implementation = vote['factor']
    applied_effect = parliament.scale_effect(effect, implementation)
    s.message = effect.get('message', 'Decision applied.')
    s.last_ideology = ideology
    s.headlines = generate_headlines(ideology)
    s.ideology_counts[ideology] = s.ideology_counts.get(ideology, 0) + 1

    # Put each major proposal to a Commons vote before applying its full effects.
    country.apply_decision(ideology, scale=implementation)
    apply_effect(applied_effect)
    parliament.apply_fallout(vote)
    parliament_note = f"Commons vote: {vote['status']} ({vote['ayes']} ayes, {vote['noes']} noes). {vote['explanation']}"
    s.message = (s.message + " " + parliament_note).strip()
    s.event_cards.append({
        'title': f"Commons vote · {vote['status']}",
        'text': f"{decision['title']}: {opt['label']}",
        'summary': f"{vote['ayes']} ayes · {vote['noes']} noes · {implementation:.0%} of the proposal implemented"
    })

    d_app = s.approval - before['approval']
    d_head = s.headroom - before['headroom']
    update_political_capital(ideology, d_app, d_head)
    s.humphrey_note = decisions.reaction(ideology, d_app, s.market_conf - before['market_conf'], opt['delayed'])
    update_polls(_period_label())

    s.steps += 1
    if opt['delayed']:
        spec = dict(opt['delayed'])
        spec['fx'] = parliament.scale_effect(spec['fx'], implementation)
        s.pending.append(dict(due=s.steps + spec['after'], title=spec['title'], text=spec['text'], fx=spec['fx']))
    state.log('decision', decision['title'], choice=opt['label'], ideology=ideology, before=before,
              note=f"{effect.get('message', '')} {parliament_note}")

    deliver_pending()
    settle()
    s.active_crisis = scen.pick_next(s.year, s.block, ideology)
    s.block += 1
    if s.block == 2 and random.random() < REQUEST_CHANCE:
        s.active_request = politics.pick_request()      # a minister wants money before the year's second decision
    state.record()
    check_sacked()


def resolve_crisis(idx):
    s = st.session_state
    state.checkpoint()
    reseed('crisis')
    s.event_cards = []
    crisis = scen.get(s.active_crisis)
    before = state.values()
    state.snapshot()
    label, fx = crisis['opts'][idx]
    s.message = scen.resolve(crisis, idx)
    # Global crises create a temporary second-round macro effect next year.
    shock_profiles = {
        'global_recession': ('Global recession', -0.65, 0.0, -3),
        'oil_price_spike': ('Energy price shock', -0.25, 0.55, -2),
        'global_supply_crunch': ('Supply-chain disruption', -0.45, 0.35, -2),
        'trade_war': ('Trade-war uncertainty', -0.45, 0.1, -3),
        'banking_panic': ('International credit crunch', -0.7, 0.0, -5),
        'technology_boom': ('Global productivity boom', 0.45, 0.0, 1),
        'food_price_crisis': ('Global food-price shock', -0.1, 0.4, -1),
        'export_surge': ('Export-demand surge', 0.45, 0.0, 1),
        'climate_disaster': ('Extreme-weather disruption', -0.35, 0.25, -2),
        'sovereign_debt_crisis': ('Sovereign-debt contagion', -0.35, 0.1, -4),
    }
    if s.active_crisis in shock_profiles:
        shock_label, shock_growth, shock_inflation, shock_market = shock_profiles[s.active_crisis]
        s.temporary_shock = {'label': shock_label, 'growth': shock_growth, 'inflation': shock_inflation,
                             'market': shock_market, 'years_left': 1}
    proxy = scen.proxy_ideology(fx)
    s.headlines = generate_headlines(proxy)
    update_political_capital(proxy, s.approval - before['approval'], s.headroom - before['headroom'])
    s.crises_handled += 1
    s.humphrey_note = ''
    s.steps += 1
    state.log('crisis', crisis['title'].replace('🚨 BREAKING: ', '').replace('🔗 LINKED REACTION: ', '')
              .replace('📒 BUDGET FALLOUT: ', '').split('!')[0],
              choice=label, ideology=proxy, before=before)
    s.active_crisis = None
    deliver_pending()
    settle()
    state.record()
    check_sacked()


OPINION_KEYS = ('pm_opinion', 'cab_opinion', 'party_opinion', 'backbench_opinion', 'media_opinion')


def resolve_request(accept):
    """Answer a cabinet minister's request for money: approve it (costs headroom) or refuse (they remember)."""
    s = st.session_state
    req = s.get('active_request')
    if not req:
        return
    state.checkpoint()
    reseed('request')
    s.event_cards = []
    before = state.values()
    state.snapshot()
    fx = req['accept'] if accept else req['refuse']
    if accept:
        s.headroom = round(s.headroom - req['cost'], 1)
        s.deficit = round(s.deficit + req['cost'], 1)
    apply_effect({k: v for k, v in fx.items() if k not in OPINION_KEYS})
    for k in OPINION_KEYS:
        if k in fx:
            s[k] = round(_clip(s[k] + fx[k]), 1)
    verb = f"You approve the {req['minister']}'s request (£{req['cost']:.1f}B)." if accept else f"You refuse the {req['minister']}'s request."
    s.message = verb
    s.headlines = None
    s.active_request = None
    state.log('event', f"{req['minister']}: request for £{req['cost']:.1f}B", choice='Approved' if accept else 'Refused',
              before=before, note=verb)
    state.record()
    check_sacked()


# ================================================================ the budget & the spring tick
def submit_budget():
    """Submit the Budget. Applies any unapplied slider changes, delivers the revolt penalties, then holds the vote.

    Returns 'ok', or 'sacked' if the Commons voted it down (or the fallout ended your career).
    """
    s = st.session_state
    state.checkpoint()
    reseed('budget')
    s.event_cards = []
    budget.ensure()
    before = state.values()
    if budget.read() != s.budget_applied:
        budget._apply()
    elif not str(s.get('message', '')).startswith('Budget delivered'):
        s.message = 'You deliver the Budget unchanged.'
    budget.apply_irritants()
    politics.check_pledges()
    ayes = budget.commons_ayes()
    if ayes < budget.WIN:
        s.sacked = True
        s.sacked_reason = (f"Your backbenchers revolted and the Budget fell by {budget.WIN - ayes} votes ({ayes} ayes). "
                           "Losing a Budget is treated as an automatic vote of no confidence. The Government has collapsed.")
        end_run('sacked')
        return 'sacked'
    if s.approval < 40:
        s.market_conf = round(_clip(s.market_conf - 1.0), 1)
    s.budget_speech = speech.compose()
    budget.commit_budget(ayes)
    s.budget_passed = True
    s.headlines = generate_headlines(None, True, s.headroom)
    update_polls(_period_label())
    s.steps += 1
    state.log('budget', f'Year {s.year} Budget', note=s.message, before=before)
    deliver_pending()
    state.record()
    check_sacked()
    return 'sacked' if s.get('game_over') else 'ok'


def economy_tick():
    """Once a year the economy moves on by itself: inflation, rates, gilts, growth and the knock-on drags."""
    s = st.session_state
    keys = ('inflation', 'interest_rate', 'gilt_yield', 'growth', 'debt', 'deficit', 'headroom', 'market_conf', 'approval')
    v = {k: s[k] for k in keys}
    v['cycle'] = s.get('macro_cycle')
    out = econ.step(v, econ.game_year(s.term, s.year) + 1)   # +1: the year we are moving into
    for k in ('inflation', 'interest_rate', 'gilt_yield', 'growth', 'debt', 'deficit', 'headroom', 'market_conf'):
        s[k] = out[k]

    # fiscal credibility: markets and voters punish a breached fiscal rule far harder than they reward prudence
    cred = out['cred']
    if cred < 0:
        s.approval = round(_clip(s.approval + max(-CRED_LOSS_CAP, CRED_LOSS * cred)), 1)
        s.message += ' Your fiscal rules are breached and voters notice the squeeze.'
    elif cred > 0:
        s.approval = round(_clip(s.approval + min(CRED_GAIN_CAP, CRED_GAIN * cred)), 1)
    if s.market_conf < 45:
        s.approval = round(_clip(s.approval - (45 - s.market_conf) * 0.1), 1)

    # Adviser effects applied during the annual spring update.
    if s.get('spad') == 'economist':
        s.growth = round(s.growth + 0.08, 2)
        s.backbench_opinion = round(_clip(s.backbench_opinion - 1.0), 1)
        s.message += ' The growth adviser has launched a productivity programme; some MPs are uneasy.'
    if s.get('spad') == 'organiser':
        s.party_opinion = round(_clip(s.party_opinion + 4.0), 1)
        s.media_opinion = round(_clip(s.media_opinion - 2.0), 1)
        s.message += ' The party organiser has tightened internal discipline, while media opinion slips.'

    # political capital drifts back towards normal over a year
    s.backbench_opinion = round(_clip(s.backbench_opinion + 0.2 * (60 - s.backbench_opinion)), 1)
    s.party_opinion = round(_clip(s.party_opinion + 0.15 * (65 - s.party_opinion)), 1)
    s.pm_opinion = round(_clip(s.pm_opinion + 0.1 * (70 - s.pm_opinion)), 1)
    s.cab_opinion = round(_clip(s.cab_opinion + 0.15 * (60 - s.cab_opinion)), 1)
    s.media_opinion = round(_clip(s.media_opinion + 0.2 * (50 - s.media_opinion)), 1)

    # knock-on drags (these used to fire after every single decision)
    # A major external shock has a one-year second-round effect after the response.
    shock = s.get('temporary_shock') or {}
    if shock.get('years_left', 0) > 0:
        s.growth = round(s.growth + float(shock.get('growth', 0.0)), 2)
        s.inflation = round(max(-1.0, s.inflation + float(shock.get('inflation', 0.0))), 2)
        s.market_conf = round(_clip(s.market_conf + float(shock.get('market', 0.0))), 1)
        s.message += " External shock continues: " + str(shock.get('label', 'global disruption')) + "."
        shock['years_left'] -= 1
        if shock['years_left'] <= 0:
            s.temporary_shock = {}

    if s.inflation > 3.0:
        s.approval = round(_clip(s.approval - 2.0), 1)
        s.message += ' Sticky inflation is eroding your support.'
    c = s.country
    if c['nhs_waiting'] > 7.5:
        s.growth = round(s.growth - 0.15, 2)
        s.message += ' The massive NHS backlog is dragging down economic growth.'
    if c['rail'] < 70:
        s.market_conf = round(_clip(s.market_conf - 2.0), 1)
        s.message += ' Crumbling rail infrastructure is frustrating investors.'
    if c['child_poverty'] > 33.0 or c['homeless'] > 150:
        s.headroom = round(s.headroom - 1.0, 1)
        s.message += ' Spiking poverty has forced unbudgeted emergency welfare spending.'


def proceed_to_spring():
    s = st.session_state
    state.checkpoint()
    reseed('spring')
    s.event_cards = []
    state.snapshot()
    before = state.values()
    s.message = 'Spring arrives and a new financial year begins.'
    budget.apply_ongoing()
    if s.get('spad') == 'hawk':
        s.headroom = round(s.headroom + politics.HAWK_SAVING, 1)
        s.message += f' Your Fiscal Hawk finds £{politics.HAWK_SAVING:.1f}B of efficiency savings.'
    s.pm_opinion = round(_clip(s.pm_opinion + (5 if s.headroom > 0 else -5)), 1)
    # Trading partners evolve each year; their cycle spills into UK exports and confidence.
    world_economy.ensure(s)
    world_economy.advance(s)
    economy_tick()
    world_drag = float(s.get('world_cycle', 0.0))
    s.growth = round(s.growth + world_drag * 0.12, 2)
    s.market_conf = round(_clip(s.market_conf + world_drag * 0.8), 1)
    # Track nominal GDP in £ trillions using real growth and inflation.
    nominal_growth = ((1 + s.growth / 100.0) * (1 + s.inflation / 100.0) - 1) * 100
    s.gdp_trillion = round(float(s.get('gdp_trillion', 3.0)) * (1 + nominal_growth / 100.0), 3)
    s.setdefault('gdp_history', []).append({
        'Year': f"Term {s.term}, Year {s.year}",
        'Real GDP growth (%)': round(float(s.growth), 2),
        'Inflation (%)': round(float(s.inflation), 2),
        'Nominal GDP growth (%)': round(nominal_growth, 2),
        'GDP (£tn)': float(s.gdp_trillion),
    })
    politics.shift_macro_cycle()
    # Long-run pressures compound annually rather than arriving as isolated crises.
    s.setdefault('longrun_productivity', 1.0)
    s.setdefault('pension_pressure', 0.0)
    s.setdefault('threshold_freeze_years', 0)
    s.setdefault('political_capital_points', 5)
    s.growth = round(s.growth + (s.longrun_productivity - 1.0) * 0.04, 2)
    if s.get('thresholds_frozen', False):
        s.threshold_freeze_years = float(s.get('threshold_freeze_years', 0)) + 1.0
        scope = s.get('threshold_freeze_scope', 'Personal allowance and all bands')
        drag_receipts = min(1.5, (0.35 if scope == 'Personal allowance and all bands' else 0.25) * s.threshold_freeze_years)
        s.headroom = round(s.headroom + drag_receipts, 1)
        s.deficit = round(max(0.0, s.deficit - drag_receipts), 1)
        s.approval = round(_clip(s.approval - min(2.0, 0.25 * s.threshold_freeze_years)), 1)
        s.message += f' Frozen income-tax thresholds create fiscal drag: approximately £{drag_receipts:.1f}B of extra receipts, but take-home pay is squeezed.'
        if scope == 'Higher and additional thresholds only':
            s.personal_allowance = round(s.personal_allowance * 1.025 / 10) * 10
    else:
        s.threshold_freeze_years = 0
        # In this simplified model thresholds rise with nominal earnings unless frozen.
        s.personal_allowance = round(s.personal_allowance * 1.025 / 10) * 10
        s.higher_rate_threshold = round(s.higher_rate_threshold * 1.025 / 10) * 10
        s.additional_rate_threshold = round(s.additional_rate_threshold * 1.025 / 10) * 10
    # Demographic ageing adds a gradual pension cost every year; the triple lock magnifies it.
    s.demographic_pressure = round(float(s.get('demographic_pressure', 0.0)) + 0.6, 1)
    s.pension_pressure = round(float(s.get('pension_pressure', 0.0)) + 0.2 * s.demographic_pressure, 2)
    annual_pension_cost = round(0.25 * s.pension_pressure, 2)
    if annual_pension_cost:
        s.headroom = round(s.headroom - annual_pension_cost, 1)
        s.deficit = round(s.deficit + annual_pension_cost, 1)
        s.message += f' Demographic ageing adds about £{annual_pension_cost:.2f}B in modeled annual pension pressure.'
    s.political_capital_points = 5
    s.feature_notice = ''
    s.feature_notice_phase = 0
    s.year += 1
    s.block = 1
    s.budget_passed = False
    s.headlines = None
    s.steps += 1
    state.log('event', f'Spring, year {s.year}', note=s.message, before=before)
    deliver_pending()
    state.record()
    check_sacked()


# ================================================================ sacking, elections, ending a run
def check_sacked():
    s = st.session_state
    if s.get('game_over'):
        return
    if s.pm_opinion < 20 or s.party_opinion < 15:
        s.sacked = True
        s.sacked_reason = ('Your relationship with the Prime Minister and your own party collapsed. '
                           'You have been sacked and banished to the backbenches.')
        end_run('sacked')


def end_run(kind, result=None):
    """Finish the run: evaluate achievements and store the ending shown on the game-over screen."""
    s = st.session_state
    result = result or dict(win=False, sacked=(kind == 'sacked'), kind=kind, margin=0, seats=0)
    achievements.evaluate(result)
    title, text = achievements.ending_for(result) if kind != 'resigned' else achievements.ENDINGS['resigned']
    s.game_over = dict(kind=kind, title=title, text=text)


def compute_seats(polls):
    """Convert national vote shares into a stylised FPTP seat result.

    Regional parties receive a constituency-concentration bonus; national parties
    receive different vote-to-seat efficiencies. Largest-remainder allocation
    guarantees exactly 650 seats without handing every rounding error to one party.
    This is a game model, not a constituency-level forecast.
    """
    # Effective seat weights approximate geographic concentration under FPTP.
    weights = {
        'Labour': 1.12,
        'Conservative': 1.12,
        'Liberal Democrats': 0.72,
        'Reform UK': 0.48,
        'Green Party': 0.32,
        'SNP': 3.20,
        'Plaid Cymru': 3.00,
    }
    regional_caps = {'SNP': 57, 'Plaid Cymru': 32}
    seats = {p: 0 for p in state.PARTIES}
    # Regional parties are concentrated in their home nations, but cannot exceed
    # their approximate Westminster constituency totals.
    for party, cap in regional_caps.items():
        share = max(0.0, float(polls.get(party, 0)))
        seats[party] = min(cap, int(round(SEATS * share / 100 * weights[party])))
    remaining = SEATS - sum(seats.values())
    national = [p for p in state.PARTIES if p not in regional_caps]
    raw = {p: max(0.0, float(polls.get(p, 0))) * weights[p] for p in national}
    total = sum(raw.values())
    if total <= 0:
        raw = {p: 1.0 for p in national}
        total = float(len(national))
    exact = {p: remaining * raw[p] / total for p in national}
    for p in national:
        seats[p] = int(math.floor(exact[p]))
    leftovers = remaining - sum(seats[p] for p in national)
    for p in sorted(national, key=lambda party: exact[party] - seats[party], reverse=True)[:leftovers]:
        seats[p] += 1
    return seats


def compute_election():
    """Work out (once) the general election result. Stored in session state so reruns don't change it."""
    s = st.session_state
    if s.get('election_result'):
        return s.election_result
    reseed('election')
    polls = {p: s.poll_history[p][-1] for p in state.PARTIES}
    seats = compute_seats(polls)
    largest = max(seats, key=seats.get)
    party = s.party
    mine = seats[party]
    regional = party in state.REGIONAL

    sacked = s.pm_opinion < 40 or s.party_opinion < 35
    history = s.get('poll_history', {})
    previous = {p: (history.get(p, [polls[p]])[-2] if len(history.get(p, [])) > 1 else polls[p]) for p in state.PARTIES}
    swings = {p: round(float(polls[p]) - float(previous[p]), 1) for p in state.PARTIES}
    turnout = round(max(55.0, min(78.0, 65.0 + random.uniform(-2.5, 2.5) + (float(s.approval) - 50) * 0.04)), 1)
    r = dict(seats=seats, player_seats=mine, regional=regional, win=False, kind='loss', margin=0,
             coalition=None, sacked=sacked, polls=polls, swings=swings, turnout=turnout,
             sacked_msg=('Your relationship with the Prime Minister and your own backbenches collapsed. Regardless of the '
                         'election result, you have been sacked and banished to the backbenches.') if sacked else '')

    if regional:
        target = 40 if party == 'SNP' else 15
        cap = 57 if party == 'SNP' else 32
        if mine >= target:
            r.update(win=True, kind='regional', margin=mine - target,
                     title=f'{party} Regional Dominance ({mine}/{cap})',
                     gov_type='Holding the Balance of Power in Westminster' if seats[largest] < WIN_MAJORITY else 'Strong Regional Opposition')
        else:
            r.update(title=f'{party} Regional Defeat ({mine} seats)', gov_type='Loss of Regional Mandate')
    elif mine >= WIN_MAJORITY:
        r.update(win=True, kind='majority', margin=mine - WIN_MAJORITY, title=f'{party} Majority Government',
                 gov_type=f'Working Majority of {mine - WIN_MAJORITY}')
    else:
        r['title'] = 'Hung Parliament'
        bloc = LEFT_BLOC if party in LEFT_BLOC else RIGHT_BLOC
        partner = next((p for p in bloc if p != party and mine + seats[p] >= WIN_MAJORITY), None)
        if partner:
            r.update(win=True, kind='coalition', coalition=partner, margin=mine + seats[partner] - WIN_MAJORITY,
                     gov_type=f'Formal Coalition with {partner}')
        elif mine == seats[largest]:
            r.update(win=True, kind='minority', gov_type='Fragile Minority Government')
        else:
            r['gov_type'] = 'Sent to the Opposition Benches'

    if sacked:
        r['win'] = False
    s.election_result = r
    if sacked:
        s.sacked = True
        s.sacked_reason = r['sacked_msg']
        end_run('sacked', r)
    elif not r['win']:
        end_run('lost', r)
    else:
        achievements.evaluate(r)
    return r


def continue_term():
    """Win the election and carry on for another term, with a honeymoon bump."""
    s = st.session_state
    r = s.election_result
    boost = round(min(15.0, max(5.0, r['margin'] / 10.0)), 1)
    for k in ('approval', 'pm_opinion', 'party_opinion', 'cab_opinion', 'backbench_opinion'):
        s[k] = round(_clip(s[k] + boost), 1)
    s.honeymoon = boost
    s.term += 1
    s.year, s.block = 1, 1
    s.political_capital_points = 5
    s.feature_notice = ''
    s.feature_notice_phase = 0
    s.budget_passed = False
    s.election_result = None
    s.active_crisis = None
    s.headlines = None
    s.pending = []
    s.fallout_done = []
    s.ideology_counts = {}
    s.crises_handled = 0
    s.new_achievements = []
    s.poll_anchor = {p: s.poll_history[p][-1] for p in state.PARTIES}
    s.message = f'A new term begins. The honeymoon is worth +{boost} to approval and every measure of political capital.'
    state.snapshot()
    s.term_start = state.snapshot_all()
    state.record()


def resign():
    end_run('resigned')


# ================================================================ scorecard
_GRADES = [(70, 'A'), (60, 'B'), (50, 'C'), (40, 'D'), (0, 'F')]


def grade(overall):
    return next(g for lim, g in _GRADES if overall >= lim)


def scorecard():
    """Data for the end-of-term / end-of-run scorecard."""
    s = st.session_state
    start = s.get('term_start') or state.snapshot_all()
    now = state.snapshot_all()
    r = s.get('election_result')
    over = s.get('game_over')
    if over:
        title, subtitle = over['title'], over['text']
    elif r:
        title, subtitle = achievements.ending_for(r)
    else:
        title, subtitle = 'Term in progress', ''
    rows = []
    for label, key, fmt in (('Public approval', 'approval', '{:.0f}%'), ('Market confidence', 'market_conf', '{:.0f}%'),
                            ('OBR headroom', 'headroom', '£{:.1f}B'), ('National debt', 'debt', '{:.1f}%'),
                            ('Inflation', 'inflation', '{:.1f}%')):
        rows.append(dict(label=label, start=fmt.format(start['values'][key]), end=fmt.format(now['values'][key])))
    for label, key, fmt in (('NHS waiting list', 'nhs_waiting', '{:.1f}m'), ('Child poverty', 'child_poverty', '{:.1f}%'),
                            ('New homes / yr', 'homes_built', '{:.0f}k'), ('Unemployment', 'unemployment', '{:.1f}%')):
        rows.append(dict(label=label, start=fmt.format(start['country'][key]), end=fmt.format(now['country'][key])))
    moves = [h for h in s.history if h['term'] == s.term and h['kind'] in ('decision', 'crisis')]
    best = max(moves, key=lambda h: h['score'], default=None)
    worst = min(moves, key=lambda h: h['score'], default=None)
    ach = achievements.ACHIEVEMENTS
    overall = now['overall']
    colour = '#6fbf8a' if overall >= 60 else ('#d9b45a' if overall >= 45 else '#d6604f')
    seats = f" ({r['player_seats']} seats)" if r else ''
    term_history = [h for h in s.history if h.get('term') == s.term]
    decisions_made = [h for h in term_history if h.get('kind') in ('decision', 'crisis', 'budget', 'parliament', 'event')]
    votes = [h for h in s.get('parliament_history', []) if h.get('term') == s.term]
    rejected = [v for v in votes if v.get('status') == 'Rejected']
    chapters = []
    if best:
        chapters.append({'title': 'The high point', 'detail': f"{best.get('title', 'A key decision')}: {best.get('choice', 'your response') or 'your response'}. It was your strongest recorded turn by the model's combined approval, market-confidence and headroom score."})
    if worst:
        chapters.append({'title': 'The low point', 'detail': f"{worst.get('title', 'A difficult decision')}: {worst.get('choice', 'your response') or 'your response'}. This was the most damaging recorded turn by the same simplified score."})
    approval_change = now['values']['approval'] - start['values']['approval']
    headroom_change = now['values']['headroom'] - start['values']['headroom']
    if approval_change >= 8:
        public_verdict = 'You leave office with a stronger public mandate.'
    elif approval_change <= -8:
        public_verdict = 'Public patience has worn thin; the next leader inherits a difficult political climate.'
    else:
        public_verdict = 'Public opinion has changed little overall, leaving your record open to interpretation.'
    if headroom_change >= 5:
        fiscal_verdict = 'You built a larger fiscal buffer for your successor.'
    elif headroom_change <= -5:
        fiscal_verdict = 'You leave a thinner fiscal safety margin and less room for the next crisis.'
    else:
        fiscal_verdict = 'Your fiscal room is broadly similar to where you started.'
    legacy = f"{public_verdict} {fiscal_verdict} Your term receives a {grade(overall)} for the state of the nation ({overall:.0f}/100)."
    if r and r.get('win'):
        legacy += ' You also secured another term at the ballot box.'
    elif r:
        legacy += ' The election result ended your time in office.'
    elif over and over.get('kind') == 'sacked':
        legacy += ' Your premiership ended before the electorate could deliver its verdict.'
    return dict(
        title=title, subtitle=subtitle, rows=rows, best=best, worst=worst, overall=overall,
        grade=grade(overall), grade_colour=colour,
        badges=[ach[a][0] for a in s.achievements if a in ach],
        new_badges=[ach[a][0] for a in s.new_achievements if a in ach],
        legacy=legacy, actions=len(decisions_made), commons_votes=len(votes), bills_rejected=len(rejected),
        chapters=chapters,
        share=_share_text(title, seats, overall, start, now),
    )


def _share_text(title, seats, overall, start, now):
    s = st.session_state
    lines = [
        '🏛️ UK Chancellor Simulator',
        f"{s.party} · {s.difficulty} · seed {s.seed}",
        f"Term {s.term}: {title}{seats}",
        f"State of the Nation: {grade(overall)} ({overall:.0f}/100)",
        f"Approval {start['values']['approval']:.0f}% → {now['values']['approval']:.0f}% | "
        f"Headroom £{start['values']['headroom']:.1f}B → £{now['values']['headroom']:.1f}B",
    ]
    badges = [achievements.ACHIEVEMENTS[a][0] for a in s.achievements if a in achievements.ACHIEVEMENTS]
    if badges:
        lines.append('🏅 ' + ', '.join(badges))
    return '\n'.join(lines)
