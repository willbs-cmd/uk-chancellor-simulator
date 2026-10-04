"""Game engine: every rule of the simulator, with no UI. app.py drives it; sim.py can drive it headlessly."""
import random

import streamlit as st

import achievements
import budget
import country
import imf_outlook
import decisions
import scenarios as scen
import state

SEATS = 650

# fiscal credibility, applied once a year: approval gained/lost per £B of headroom (and its cap)
CRED_GAIN, CRED_GAIN_CAP = 0.5, 10.0
CRED_LOSS, CRED_LOSS_CAP = 0.45, 9.0
WIN_MAJORITY = 326
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
    return decisions.DECISIONS.get((s.year, s.block))


def current_options():
    s = st.session_state
    d = current_decision()
    if not d:
        return []
    return decisions.get_options(d, f"{s.seed}-{s.term}-{s.year}-{s.block}", s.show_tags)


def execute_decision(opt):
    """Run one policy decision. ``opt`` is an option dict from ``current_options()``."""
    s = st.session_state
    reseed('decision')
    s.event_cards = []
    before = state.values()
    state.snapshot()
    ideology, effect = opt['ideology'], opt['effect']
    decision = current_decision()

    s.message = effect.get('message', 'Decision applied.')
    s.last_ideology = ideology
    s.headlines = generate_headlines(ideology)
    s.ideology_counts[ideology] = s.ideology_counts.get(ideology, 0) + 1

    country.apply_decision(ideology)
    apply_effect(effect)

    d_app = s.approval - before['approval']
    d_head = s.headroom - before['headroom']
    update_political_capital(ideology, d_app, d_head)
    s.humphrey_note = decisions.reaction(ideology, d_app, s.market_conf - before['market_conf'], opt['delayed'])
    update_polls(_period_label())

    s.steps += 1
    if opt['delayed']:
        spec = opt['delayed']
        s.pending.append(dict(due=s.steps + spec['after'], title=spec['title'], text=spec['text'], fx=spec['fx']))
    state.log('decision', decision['title'], choice=opt['label'], ideology=ideology, before=before,
              note=effect.get('message', ''))

    deliver_pending()
    settle()
    s.active_crisis = scen.pick_next(s.year, s.block, ideology)
    s.block += 1
    state.record()
    check_sacked()


def resolve_crisis(idx):
    s = st.session_state
    reseed('crisis')
    s.event_cards = []
    crisis = scen.get(s.active_crisis)
    before = state.values()
    state.snapshot()
    label, fx = crisis['opts'][idx]
    s.message = scen.resolve(crisis, idx)
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


# ================================================================ the budget & the spring tick
def submit_budget():
    """Submit the Budget. Applies any unapplied slider changes first. Returns 'ok' or 'sacked'."""
    s = st.session_state
    reseed('budget')
    s.event_cards = []
    budget.ensure()
    before = state.values()
    if budget.read() != s.budget_applied:
        budget._apply()
    if s.backbench_opinion < 20:
        s.sacked = True
        s.sacked_reason = ("Your backbenchers completely revolted and voted down your Budget! Losing a budget is treated "
                           "as an automatic vote of no confidence. The Government has collapsed.")
        end_run('sacked')
        return 'sacked'
    if s.approval < 40:
        s.market_conf = round(s.market_conf - 1.0, 1)
    s.budget_passed = True
    s.headlines = generate_headlines(None, True, s.headroom)
    update_polls(_period_label())
    s.steps += 1
    state.log('budget', f'Year {s.year} Budget', note=s.message, before=before)
    deliver_pending()
    state.record()
    return 'ok'


def economy_tick():
    """Once a year the economy moves on by itself: inflation, rates, gilts, growth and the knock-on drags."""
    s = st.session_state
    gap = 2.0 - s.inflation
    s.inflation = round(_clip(s.inflation + 0.25 * gap - 0.08 * (s.interest_rate - (s.inflation + 1.5)), 0, 12), 2)
    target_rate = s.inflation + 1.8
    s.interest_rate = round(_clip(s.interest_rate + max(-0.5, min(0.5, 0.6 * (target_rate - s.interest_rate))), 0.5, 9), 2)
    gilt_target = s.interest_rate - 0.3 + (65 - s.market_conf) * 0.03 + (s.debt - 98.2) * 0.02
    s.gilt_yield = round(_clip(s.gilt_yield + 0.5 * (gilt_target - s.gilt_yield), 1, 9), 2)
    s.growth = round(s.growth + 0.2 * (1.2 - s.growth) - 0.08 * (s.interest_rate - 4.5), 2)

    # IMF baseline anchor: the player's decisions still dominate, but the
    # underlying economy gently converges toward a current external forecast.
    # This avoids the simulator becoming detached from the real-world UK cycle.
    imf = imf_outlook.get(s.year)
    if imf:
        s.growth = round(s.growth + 0.20 * (imf['gdp'] - s.growth), 2)
        s.inflation = round(s.inflation + 0.15 * (imf['inflation'] - s.inflation), 2)

    s.debt = round(s.debt + 0.034 * (s.deficit + max(0.0, -s.headroom) * 0.5) - 0.25 * (s.growth - 1.0), 1)
    s.headroom = round(s.headroom + 2.0 * (s.growth - 1.0), 1)

    # fiscal credibility: markets and voters punish a breached fiscal rule far harder than they reward prudence
    cred = _clip(s.headroom, -30, 20)
    mkt_target = 55 + (cred if cred > 0 else 2.0 * cred) + (s.approval - 50) * 0.1
    s.market_conf = round(_clip(s.market_conf + 0.25 * (mkt_target - s.market_conf)), 1)
    if cred < 0:
        s.approval = round(_clip(s.approval + max(-CRED_LOSS_CAP, CRED_LOSS * cred)), 1)
        s.message += ' Your fiscal rules are breached and voters notice the squeeze.'
    elif cred > 0:
        s.approval = round(_clip(s.approval + min(CRED_GAIN_CAP, CRED_GAIN * cred)), 1)
    if s.market_conf < 45:
        s.approval = round(_clip(s.approval - (45 - s.market_conf) * 0.1), 1)

    # political capital drifts back towards normal over a year
    s.backbench_opinion = round(_clip(s.backbench_opinion + 0.2 * (60 - s.backbench_opinion)), 1)
    s.party_opinion = round(_clip(s.party_opinion + 0.15 * (65 - s.party_opinion)), 1)
    s.pm_opinion = round(_clip(s.pm_opinion + 0.1 * (70 - s.pm_opinion)), 1)
    s.cab_opinion = round(_clip(s.cab_opinion + 0.15 * (60 - s.cab_opinion)), 1)
    s.media_opinion = round(_clip(s.media_opinion + 0.2 * (50 - s.media_opinion)), 1)

    # knock-on drags (these used to fire after every single decision)
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
    reseed('spring')
    s.event_cards = []
    state.snapshot()
    before = state.values()
    s.message = 'Spring arrives and a new financial year begins.'
    budget.apply_ongoing()
    s.pm_opinion = round(_clip(s.pm_opinion + (5 if s.headroom > 0 else -5)), 1)
    economy_tick()
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
    seats = {}
    lab, con = polls['Labour'], polls['Conservative']
    seats['Labour'] = int((lab / 100) * SEATS * (1.1 if lab > 30 else 0.8))
    seats['Conservative'] = int((con / 100) * SEATS * (1.1 if con > 30 else 0.8))
    seats['Liberal Democrats'] = int(max(5, (polls['Liberal Democrats'] / 100) * SEATS * 0.6))
    seats['Reform UK'] = int(max(0, (polls['Reform UK'] / 100) * SEATS * 0.3))
    seats['Green Party'] = int(max(1, (polls['Green Party'] / 100) * SEATS * 0.2))
    seats['SNP'] = int(min(57, max(4, (polls['SNP'] / 100) * SEATS * 3.5)))
    seats['Plaid Cymru'] = int(min(32, max(2, (polls['Plaid Cymru'] / 100) * SEATS * 3.0)))
    largest = max(seats, key=seats.get)
    seats[largest] += SEATS - sum(seats.values())
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
    r = dict(seats=seats, player_seats=mine, regional=regional, win=False, kind='loss', margin=0,
             coalition=None, sacked=sacked, polls=polls,
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
    return dict(
        title=title, subtitle=subtitle, rows=rows, best=best, worst=worst, overall=overall,
        grade=grade(overall), grade_colour=colour,
        badges=[ach[a][0] for a in s.achievements if a in ach],
        new_badges=[ach[a][0] for a in s.new_achievements if a in ach],
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
