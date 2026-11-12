"""Game engine: every rule of the simulator, with no UI. app.py drives it; sim.py can drive it headlessly."""
import math
import random
from itertools import combinations

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
import treasury
import world_economy
import weekly_events
import treasury_officials
import performance_report
import economic_management
import household
import regional_economy
import public_services
import devolution
import fiscal_events

SEATS = 650
REQUEST_CHANCE = 0.48

# fiscal credibility, applied once a year: approval gained/lost per £B of headroom (and its cap)
CRED_GAIN, CRED_GAIN_CAP = 0.5, 10.0
CRED_LOSS, CRED_LOSS_CAP = 0.45, 9.0
WIN_MAJORITY = budget.WIN
LEFT_BLOC = ['Labour', 'Liberal Democrats', 'Green Party', 'SNP', 'Plaid Cymru']
RIGHT_BLOC = ['Conservative', 'Reform UK', 'Liberal Democrats']

# which ideologies each party's MPs consider "home territory"
REGIONAL_MANDATES = {'SNP': 12, 'Plaid Cymru': 6}

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
def party_alignment(party, ideology):
    """Return the political fit of a policy without treating every non-core choice as betrayal.

    Parties contain factions and governments routinely make cross-ideological
    compromises. Core policies should be rewarded, centrist deals tolerated,
    and genuinely distant choices carry a modest cost.
    """
    core = PURITY.get(party, ['Centric'])
    if ideology in core:
        return 1.0
    if ideology == 'Centric':
        return 0.55
    return -0.35


def update_political_capital(ideology_chosen, approval_diff, headroom_diff):
    s = st.session_state
    alignment = party_alignment(s.party, ideology_chosen)
    if alignment >= 1.0:
        # Reward a recognisable party programme, without allowing it to dominate
        # public approval or make every party's MPs uniformly obedient.
        s.backbench_opinion += random.uniform(1.2, 2.8)
        s.party_opinion += random.uniform(0.6, 1.8)
    elif alignment > 0:
        # Centrist compromises are usually tolerable, even in ideological parties.
        s.backbench_opinion += random.uniform(0.0, 1.0)
        s.party_opinion += random.uniform(-0.1, 0.6)
    else:
        # A cross-party compromise costs support, but a single vote should not
        # create the same rebellion risk as a sustained ideological betrayal.
        s.backbench_opinion -= random.uniform(0.6, 1.6)
        s.party_opinion -= random.uniform(0.2, 0.8)

    market_diff = s.market_conf - s.prev.get('market_conf', s.market_conf)
    # Political confidence should respond to the direction of the economy,
    # not mechanically collapse because a fiscal forecast moved by several
    # billion pounds. Approval is the strongest signal; headroom is a smaller,
    # capped consideration for the PM and Cabinet.
    fiscal_signal = max(-6.0, min(6.0, float(headroom_diff)))
    s.pm_opinion += (approval_diff * 0.7) + (fiscal_signal * 0.22)
    s.cab_opinion += (approval_diff * 0.65) + random.uniform(-1.5, 2.0)
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
        # Regional parties' national vote share is smaller by definition, but it
        # should still respond to government performance rather than being frozen.
        shift *= 0.55
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
    fiscal_events.maybe_trigger_emergency_budget(s)


# ================================================================ the decision loop
def current_decision():
    s = st.session_state
    return decisions.get_weekly_decision(s.get('seed', 0), s.get('term', 1), s.get('year', 1), s.get('block', 1), s.get('policy_history', []))


def current_options():
    s = st.session_state
    d = current_decision()
    if not d:
        return []
    return decisions.get_options(d, f"{s.seed}-{s.term}-{s.year}-{s.block}", s.show_tags)


def assess_decision(opt):
    """Estimate how deliverable a proposal is in the current political and fiscal climate.

    This is deliberately a modest modifier: policy choice still matters most, but a weak
    Treasury/Commons position makes ambitious promises harder to deliver.
    """
    s = st.session_state
    ideology = opt.get('ideology', 'Centric')
    alignment = party_alignment(s.get('party', 'Labour'), ideology)
    fiscal_pressure = max(0.0, min(1.0, (8.0 - float(s.get('headroom', 0.0))) / 20.0))
    confidence = (
        0.92
        + (float(s.get('cab_opinion', 60)) - 50.0) * 0.0025
        + (float(s.get('market_conf', 60)) - 50.0) * 0.0015
        + (float(s.get('backbench_opinion', 60)) - 50.0) * 0.0015
        + alignment * 0.035
        - fiscal_pressure * 0.10
    )
    confidence = round(max(0.72, min(1.08, confidence)), 2)
    # Keep the assessment resilient if an older saved session or deployment is
    # missing the newer Parliament helper.
    projected_fn = getattr(parliament, "projected_ayes", None)
    if callable(projected_fn):
        try:
            projected = int(projected_fn())
        except (AttributeError, KeyError, TypeError, ValueError):
            projected = int(326 + 0.80 * (float(s.get('backbench_opinion', 60)) - 40)
                            + 0.45 * (float(s.get('party_opinion', 65)) - 50)
                            + 0.12 * (float(s.get('approval', 48)) - 50))
    else:
        projected = int(326 + 0.80 * (float(s.get('backbench_opinion', 60)) - 40)
                        + 0.45 * (float(s.get('party_opinion', 65)) - 50)
                        + 0.12 * (float(s.get('approval', 48)) - 50))
    projected = max(0, min(650, projected))
    if projected >= parliament.CLEAR_PASS:
        vote_label = "Likely clear passage"
        vote_factor = 1.0
    elif projected >= parliament.WIN:
        vote_label = "Likely narrow passage"
        vote_factor = 0.70
    else:
        vote_label = "Bill at risk"
        vote_factor = 0.25
    combined = round(confidence * vote_factor, 2)
    risks = []
    if fiscal_pressure >= 0.45:
        risks.append("Limited fiscal headroom makes funding harder to sustain.")
    if float(s.get('cab_opinion', 60)) < 40:
        risks.append("Cabinet support is weak; delivery may be delayed or diluted.")
    if float(s.get('backbench_opinion', 60)) < 40:
        risks.append("Restive government MPs may demand concessions.")
    if float(s.get('market_conf', 60)) < 35:
        risks.append("Markets may react sharply to unfunded commitments.")
    if alignment < 0:
        risks.append("The proposal cuts across your party's usual instincts.")
    if not risks:
        risks.append("No exceptional delivery obstacle is currently visible.")
    return {
        "confidence": confidence,
        "vote_label": vote_label,
        "projected_ayes": projected,
        "combined_factor": combined,
        "risks": risks,
        "fiscal_pressure": round(fiscal_pressure, 2),
        "alignment": alignment,
    }


def execute_decision(opt):
    """Run one policy decision. ``opt`` is an option dict from ``current_options()``."""
    s = st.session_state
    # Migrate older in-progress saves created before the branching decision system.
    # Streamlit keeps session state alive across code deployments, so new keys
    # must be initialised without resetting the player's existing game.
    s.setdefault('policy_history', [])
    s.setdefault('ideology_counts', {})
    s.setdefault('pending', [])
    s.setdefault('event_cards', [])
    s.setdefault('parliament_history', [])
    s.setdefault('parliament_actions', {})
    s.setdefault('parliament_next_bonus', 0)
    s.setdefault('backbench_opinion', 60.0)
    s.setdefault('party_opinion', 65.0)
    s.setdefault('cab_opinion', 60.0)
    state.checkpoint()
    reseed('decision')
    s.event_cards = []
    before = state.values()
    state.snapshot()
    ideology, effect = opt['ideology'], opt['effect']
    decision = current_decision()

    assessment = assess_decision(opt)
    vote = parliament.review_bill(decision, opt)
    implementation = vote['factor']
    delivery_factor = assessment['confidence']
    combined_factor = implementation * delivery_factor
    applied_effect = parliament.scale_effect(effect, combined_factor)
    s.message = effect.get('message', 'Decision applied.')
    s.last_ideology = ideology
    s.policy_history.append({
        'term': int(s.get('term', 1)),
        'year': int(s.get('year', 1)),
        'block': int(s.get('block', 1)),
        'title': decision.get('title', 'Policy decision'),
        'ideology': ideology,
        'choice': opt.get('label', ''),
        'branch_id': decision.get('branch_id')
    })
    s.headlines = generate_headlines(ideology)
    s.ideology_counts[ideology] = s.ideology_counts.get(ideology, 0) + 1

    # Put each major proposal to a Commons vote before applying its full effects.
    country.apply_decision(ideology, scale=combined_factor)
    treasury_officials.review_policy(decision.get('title', 'Policy decision'), opt.get('label', ''), applied_effect)
    apply_effect(applied_effect)
    parliament.apply_fallout(vote)
    parliament_note = f"Commons vote: {vote['status']} ({vote['ayes']} ayes, {vote['noes']} noes). {vote['explanation']}"
    s.message = (s.message + " " + parliament_note).strip()
    s.event_cards.append({
        'title': f"Commons vote · {vote['status']}",
        'text': f"{decision['title']}: {opt['label']}",
        'summary': f"{vote['ayes']} ayes · {vote['noes']} noes · {combined_factor:.0%} of the proposal delivered (Commons {implementation:.0%} × delivery {delivery_factor:.0%})"
    })

    d_app = s.approval - before['approval']
    d_head = s.headroom - before['headroom']
    update_political_capital(ideology, d_app, d_head)
    s.humphrey_note = decisions.reaction(ideology, d_app, s.market_conf - before['market_conf'], opt['delayed'])
    update_polls(_period_label())

    s.steps += 1
    if opt['delayed']:
        spec = dict(opt['delayed'])
        spec['fx'] = parliament.scale_effect(spec['fx'], combined_factor)
        s.pending.append(dict(due=s.steps + spec['after'], title=spec['title'], text=spec['text'], fx=spec['fx']))
    state.log('decision', decision['title'], choice=opt['label'], ideology=ideology, before=before,
              note=f"{effect.get('message', '')} {parliament_note} Delivery confidence {delivery_factor:.0%}; combined implementation {combined_factor:.0%}.")

    deliver_pending()
    settle()
    s.active_crisis = scen.pick_next(s.year, s.block, ideology)
    if s.active_crisis is None:
        _advance_ongoing_issues()
    if not s.get('active_weekly_event') and s.active_crisis is None and not s.get('active_request') and not s.get('active_dispute'):
        s.active_weekly_event = weekly_events.pick(s.get('seed', 0), s.steps, s.get('last_weekly_event'))
        if s.active_weekly_event:
            s.last_weekly_event = s.active_weekly_event.get('id')
    s.block += 1
    if s.block == 2 and random.random() < REQUEST_CHANCE:
        s.active_request = politics.pick_request()      # a minister wants money before the year's second decision
    state.record()
    check_sacked()




def _advance_ongoing_issues():
    """Age unresolved political disputes and surface their next escalation as a decision."""
    s = st.session_state
    issues = list(s.get('ongoing_issues', []))
    if not issues or s.get('active_weekly_event'):
        return
    for issue in issues:
        issue['weeks_left'] = int(issue.get('weeks_left', 1)) - 1
        if issue['weeks_left'] <= 0:
            if issue['kind'] == 'nhs':
                event = {
                    'id': 'followup_nhs_strike', 'category': 'Escalating dispute',
                    'title': 'NHS strike action spreads',
                    'text': 'The initial dispute has widened. More hospitals face disruption and the Health Secretary warns that waiting lists and public confidence are deteriorating.',
                    'options': [
                        ('Fund an emergency settlement', {'headroom': -2.2, 'deficit': 2.2, 'approval': 1.8, 'cab_opinion': 1}, 'An emergency deal ends the immediate escalation, at a substantial cost.'),
                        ('Appoint an independent mediator', {'headroom': -0.6, 'approval': 0.5, 'media_opinion': 0.5}, 'Mediation pauses further action, but a settlement is not guaranteed.'),
                        ('Refuse to reopen negotiations', {'approval': -2.5, 'growth': -0.08, 'cab_opinion': -1.5}, 'The walkout expands and the Government faces mounting criticism.'),
                    ]}
            elif issue['kind'] == 'teachers':
                event = {
                    'id': 'followup_teachers_strike', 'category': 'Escalating dispute',
                    'title': 'School closures spread across the country',
                    'text': 'Teachers have moved from ballots to coordinated strike days. Parents and school leaders are demanding a settlement.',
                    'options': [
                        ('Offer a funded pay settlement', {'headroom': -1.8, 'deficit': 1.8, 'approval': 1.5}, 'The settlement brings the immediate dispute to an end.'),
                        ('Agree workload reforms and talks', {'headroom': -0.5, 'approval': 0.5, 'growth': 0.03}, 'A package of reforms creates space for negotiations.'),
                        ('Hold the line again', {'approval': -2, 'media_opinion': -1.5, 'growth': -0.05}, 'Disruption continues and the dispute becomes a defining political issue.'),
                    ]}
            elif issue['kind'] == 'union':
                event = {
                    'id': 'followup_union_campaign', 'category': 'Escalating dispute',
                    'title': 'Public-sector unions coordinate walkouts',
                    'text': 'Several unions have aligned their industrial action. The Cabinet is warning that disruption could spread across essential services.',
                    'options': [
                        ('Negotiate a staged pay deal', {'headroom': -1.8, 'deficit': 1.8, 'cab_opinion': 1.5, 'approval': 1}, 'A staged settlement reduces the immediate risk of coordinated strikes.'),
                        ('Offer independent pay review', {'headroom': -0.5, 'approval': 0.4, 'media_opinion': 0.5}, 'The review creates a route to talks, though unions reserve their position.'),
                        ('Reject the unions’ demands', {'approval': -2, 'cab_opinion': -1.5, 'party_opinion': 0.5}, 'The coordinated campaign escalates into widespread industrial action.'),
                    ]}
            else:
                event = {
                    'id': 'followup_boe_dispute', 'category': 'Bank of England',
                    'title': 'The Bank-Treasury dispute deepens',
                    'text': 'The Governor repeats the criticism and markets are questioning whether the Government respects the Bank’s independence.',
                    'options': [
                        ('Issue a joint statement with the Governor', {'market_conf': 2, 'gilt_yield': -0.08, 'pm_opinion': -0.5}, 'A joint statement restores some confidence.'),
                        ('Refer the dispute to the Treasury Committee', {'media_opinion': 0.5, 'market_conf': 0.5, 'pm_opinion': 0.5}, 'Parliamentary scrutiny cools the immediate row.'),
                        ('Escalate the public criticism', {'market_conf': -3, 'gilt_yield': 0.15, 'media_opinion': -1.5}, 'The public row unsettles markets and damages the Bank’s relationship with the Treasury.'),
                    ]}
            s.active_weekly_event = event
            s.ongoing_issues = [x for x in issues if x is not issue]
            return
    s.ongoing_issues = issues


def _schedule_ongoing_issue(event_id, choice_index):
    """Some choices leave a live dispute which can escalate in a later week."""
    mapping = {
        ('nhs_strike', 2): ('nhs', 'NHS industrial dispute'),
        ('teacher_strike', 2): ('teachers', 'Teachers’ industrial dispute'),
        ('union_pay_pressure', 2): ('union', 'Public-sector pay campaign'),
        ('boe_dispute', 1): ('boe', 'Bank of England dispute'),
    }
    item = mapping.get((event_id, choice_index))
    if not item:
        return
    kind, title = item
    issues = list(st.session_state.get('ongoing_issues', []))
    if not any(x.get('kind') == kind for x in issues):
        issues.append({'kind': kind, 'title': title, 'weeks_left': 2})
    st.session_state.ongoing_issues = issues

def resolve_weekly_event(choice_index):
    """Resolve a dynamic political/economic event and apply its consequences."""
    s = st.session_state
    event = s.get('active_weekly_event')
    if not event:
        return
    options = event.get('options', [])
    if choice_index < 0 or choice_index >= len(options):
        return
    state.checkpoint()
    reseed('weekly_event')
    s.event_cards = []
    before = state.values()
    state.snapshot()
    label, fx, note = options[choice_index]
    _schedule_ongoing_issue(event.get('id'), choice_index)
    apply_effect(fx)
    # A real tax miss is a revenue loss, not just a political headline.
    if event.get('id') in ('tax_shortfall', 'retail_tax_warning'):
        s.deficit = round(float(s.get('deficit', 0)) + max(0.0, -float(fx.get('headroom', 0))), 1)
    s.message = note
    s.event_cards.append({'title': event.get('title', 'Weekly event'), 'text': label, 'summary': state.fmt_fx(fx) or 'Political consequences recorded'})
    state.log('event', event.get('title', 'Weekly event'), choice=label, before=before, note=note)
    s.active_weekly_event = None
    s.steps += 1
    settle()
    _advance_ongoing_issues()
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
    _advance_ongoing_issues()
    state.record()
    check_sacked()


OPINION_KEYS = ('pm_opinion', 'cab_opinion', 'party_opinion', 'backbench_opinion', 'media_opinion')


def resolve_gilt_emergency(choice):
    """Resolve the emergency Treasury meeting triggered by a failed gilt auction."""
    s=st.session_state
    emergency=s.get("active_gilt_emergency")
    if not emergency: return
    state.checkpoint()
    before=state.values()
    state.snapshot()
    if choice==0:
        s.headroom=round(float(s.headroom)+3.0,1)
        s.deficit=round(max(0.0,float(s.deficit)-3.0),1)
        s.market_conf=round(_clip(float(s.market_conf)+5.0),1)
        s.gilt_yield=round(max(0.1,float(s.gilt_yield)-0.12),2)
        s.approval=round(_clip(float(s.approval)-2.5),1)
        s.backbench_opinion=round(_clip(float(s.backbench_opinion)-4.0),1)
        s.pm_opinion=round(_clip(float(s.pm_opinion)+1.0),1)
        label="Announce immediate spending restraint"
        note="The Treasury announces £3bn of immediate restraint. Investors welcome the signal, but public services and backbenchers are angry."
    elif choice==1:
        s.pm_opinion=round(_clip(float(s.pm_opinion)+5.0),1)
        s.market_conf=round(_clip(float(s.market_conf)+1.5),1)
        s.gilt_yield=round(max(0.1,float(s.gilt_yield)-0.04),2)
        s.backbench_opinion=round(_clip(float(s.backbench_opinion)+1.0),1)
        label="Ask the Prime Minister for a united statement"
        note="The PM joins you in promising a credible fiscal plan. The show of unity steadies markets, although it does not solve the borrowing problem."
    elif choice==2:
        label="Call an emergency Budget"
        note="You ask the Treasury to prepare a full emergency fiscal package. The Chancellor must now revise the tax and spending plan, receive a rapid forecast and secure a Commons vote."
    elif choice==3 and emergency.get("pm_pressure"):
        s.headroom=round(float(s.headroom)-1.5,1)
        s.deficit=round(float(s.deficit)+1.5,1)
        s.market_conf=round(_clip(float(s.market_conf)+2.0),1)
        s.pm_opinion=round(_clip(float(s.pm_opinion)+12.0),1)
        s.cab_opinion=round(_clip(float(s.cab_opinion)+3.0),1)
        s.backbench_opinion=round(_clip(float(s.backbench_opinion)-2.0),1)
        s.approval=round(_clip(float(s.approval)-1.0),1)
        label="Accept the Prime Minister's conditions"
        note="You accept Number 10's conditions: a tighter fiscal plan, closer political coordination and a limited concession to the PM's priorities. The Government is publicly united, but the Treasury has less room to manoeuvre."
    else: return
    s.message=note
    s.active_gilt_emergency=None
    s.gilt_emergency_history=(list(s.get("gilt_emergency_history",[]))+[{"year":emergency.get("year"),"response":label,"market_conf":round(float(s.market_conf),1),"gilt_yield":round(float(s.gilt_yield),2)}])[-12:]
    if choice == 2:
        fiscal_events.open_emergency_budget(note, source="failed gilt auction response")
    state.log("gilt_emergency","Emergency Treasury meeting",choice=label,before=before,note=note)
    settle()
    state.record()
    check_sacked()
    if not s.get("game_over") and not s.get("active_pm_ultimatum"):
        pm=float(s.get("pm_opinion",50))
        severe=emergency.get("severity")=="severe"
        if pm<35 or (severe and pm<48):
            s.active_pm_ultimatum={"year":emergency.get("year"),"pm_opinion":round(pm,1),"severity":emergency.get("severity","serious")}
            s.message="The Prime Minister has demanded a private meeting and is questioning whether you can continue as Chancellor."
            state.record()


# ================================================================ Number 10 relationship
PM_MEETING_TOPICS = [
    {"topic":"The spending settlement","prompt":"The Prime Minister wants a visible spending commitment before the next round of polling. The Treasury is concerned about the cost and the effect on fiscal headroom.","pm":"The public needs to see that this Government has priorities. I need you to find room for the commitment.","support":"Back the PM's spending priority","compromise":"Offer a smaller, targeted settlement","stand":"Defend the Treasury's fiscal limits"},
    {"topic":"Tax policy disagreement","prompt":"Number 10 is pressing for a tax cut, while Treasury officials warn that the timing could unsettle the gilt market and leave little room for manoeuvre.","pm":"A tax cut would show ambition. I don't want another lecture about why nothing can be done.","support":"Agree to pursue the tax cut","compromise":"Offer a conditional tax cut if forecasts improve","stand":"Tell the PM the numbers do not add up"},
    {"topic":"Party management","prompt":"The parliamentary party is restless. The Prime Minister wants a united front, but several of your colleagues believe the Treasury is moving too slowly.","pm":"I need you to help keep the party together. A public split between Number 10 and the Treasury would be disastrous.","support":"Publicly back the PM's line","compromise":"Arrange a joint meeting with concerned MPs","stand":"Insist the Treasury must speak frankly"},
    {"topic":"Economic messaging","prompt":"The latest economic figures have created a difficult news cycle. Number 10 wants an optimistic message, but you are wary of promising more than the economy can deliver.","pm":"We need confidence, Chancellor. I want you beside me when we explain the plan.","support":"Echo the PM's optimistic message","compromise":"Agree a joint statement with caveats","stand":"Publish the Treasury's unvarnished assessment"},
    {"topic":"A difficult Budget","prompt":"The Prime Minister is unhappy with parts of your Budget and believes the package does not reflect the Government's political priorities.","pm":"This is our Government's Budget, not simply the Treasury's. I expect you to make the case for it and own the choices.","support":"Accept the PM's requested changes","compromise":"Make limited changes and explain the trade-offs","stand":"Refuse to reopen the Budget"}
]


def open_pm_meeting():
    """Open one annual private meeting with the Prime Minister."""
    s=st.session_state
    if s.get("active_pm_meeting") or int(s.get("pm_meeting_year",0))>=int(s.get("year",1)):
        return False
    topic=random.choice(PM_MEETING_TOPICS)
    s.active_pm_meeting={**topic,"year":int(s.get("year",1))}
    return True


def resolve_pm_meeting(choice):
    """Apply the political and policy consequences of the Chancellor's annual Number 10 meeting."""
    s=st.session_state
    meeting=s.get("active_pm_meeting")
    if not meeting or choice not in ("support","compromise","stand"):
        return
    state.checkpoint(); state.snapshot()
    before={k:float(s.get(k,0.0)) for k in ("pm_opinion","pm_trust","cab_opinion","party_opinion","backbench_opinion","market_conf","headroom")}
    if choice=="support":
        s.pm_trust=round(_clip(float(s.get("pm_trust",70))+10),1)
        s.pm_opinion=round(_clip(float(s.pm_opinion)+6),1)
        s.cab_opinion=round(_clip(float(s.cab_opinion)+3),1)
        s.party_opinion=round(_clip(float(s.party_opinion)+2),1)
        s.backbench_opinion=round(_clip(float(s.backbench_opinion)-2),1)
        s.headroom=round(float(s.headroom)-1.0,1)
        outcome="You back the Prime Minister's position. Number 10 is pleased, but the Treasury has accepted a £1bn policy commitment and some MPs question the concession."
        label="Back the Prime Minister"
    elif choice=="compromise":
        s.pm_trust=round(_clip(float(s.get("pm_trust",70))+5),1)
        s.pm_opinion=round(_clip(float(s.pm_opinion)+3),1)
        s.cab_opinion=round(_clip(float(s.cab_opinion)+3),1)
        s.party_opinion=round(_clip(float(s.party_opinion)+1),1)
        s.market_conf=round(_clip(float(s.market_conf)+1),1)
        outcome="You broker a compromise. The PM gets a political win, while the Treasury retains some control over the timing and cost."
        label="Negotiate a compromise"
    else:
        s.pm_trust=round(_clip(float(s.get("pm_trust",70))-9),1)
        s.pm_opinion=round(_clip(float(s.pm_opinion)-6),1)
        s.cab_opinion=round(_clip(float(s.cab_opinion)-2),1)
        s.backbench_opinion=round(_clip(float(s.backbench_opinion)+3),1)
        s.market_conf=round(_clip(float(s.market_conf)+1),1)
        outcome="You stand firm. Treasury independence and fiscal credibility are protected, but the PM sees you as increasingly difficult to work with."
        label="Defend the Treasury's position"
    s.pm_meeting_year=int(meeting.get("year",s.year))
    s.pm_meeting_history=(list(s.get("pm_meeting_history",[]))+[{
        "year":int(meeting.get("year",s.year)),"topic":meeting.get("topic","Number 10 meeting"),
        "decision":label,"pm_trust":float(s.pm_trust),"pm_confidence":float(s.pm_opinion),
        "cabinet_support":float(s.cab_opinion)}])[-15:]
    s.active_pm_meeting=None
    s.message=f"NUMBER 10 MEETING — {meeting.get('topic','Private meeting')}. {outcome}"
    s.humphrey_note="The Prime Minister will remember how you handled that conversation, Chancellor. Number 10 has a long memory, particularly when it is inconvenient."
    state.log("politics","Private meeting with the Prime Minister",choice=label,note=outcome,before=before)
    check_sacked()
    if not s.get("game_over") and float(s.pm_trust)<22 and float(s.pm_opinion)<38 and not s.get("active_pm_ultimatum"):
        s.active_pm_ultimatum={"year":meeting.get("year"),"pm_opinion":round(float(s.pm_opinion),1),"severity":"serious"}
        s.message+=" The Prime Minister has requested an urgent follow-up meeting and is considering your future."
    return outcome


def resolve_pm_ultimatum(choice):
    """Resolve a direct ultimatum from Number 10 after a serious loss of confidence."""
    s=st.session_state
    ultimatum=s.get('active_pm_ultimatum')
    if not ultimatum: return
    state.checkpoint()
    before=state.values()
    state.snapshot()
    if choice==0:
        s.active_pm_ultimatum=None
        s.message="You have tendered your resignation as Chancellor. The Prime Minister has accepted."
        state.log("pm_ultimatum","Resigned after PM ultimatum",choice="Tender resignation",before=before,note=s.message)
        end_run("resigned")
        state.record()
        return
    if choice==1:
        cabinet=float(s.get("cab_opinion",50))
        pm=float(s.get("pm_opinion",50))
        s.active_pm_ultimatum=None
        if cabinet>=45 or pm>=30:
            s.pm_opinion=round(_clip(pm+5.0),1)
            s.cab_opinion=round(_clip(cabinet+2.0),1)
            s.backbench_opinion=round(_clip(float(s.get("backbench_opinion",50))-2.0),1)
            s.message="You refuse to resign and secure enough Cabinet backing to remain at the Treasury. The PM gives you one final chance, but your authority is badly weakened."
            state.log("pm_ultimatum","Survived PM ultimatum",choice="Refuse to resign",before=before,note=s.message)
            settle()
            state.record()
            check_sacked()
        else:
            s.sacked=True
            s.sacked_reason="You refused the Prime Minister's ultimatum but could not command enough Cabinet support. You were dismissed from the Treasury."
            s.message=s.sacked_reason
            state.log("pm_ultimatum","Dismissed after PM ultimatum",choice="Refuse to resign",before=before,note=s.message)
            end_run("sacked")
            state.record()
        return
    return

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
    # Ministers remember whether the Treasury backed their department.
    loyalty = dict(s.get('ministerial_loyalty', {}))
    minister = str(req.get('minister', 'Cabinet minister'))
    loyalty[minister] = round(_clip(float(loyalty.get(minister, 50.0)) + (8.0 if accept else -12.0)), 1)
    s.ministerial_loyalty = loyalty
    refusal_counts = dict(s.get('ministerial_refusals', {}))
    if accept:
        refusal_counts[minister] = 0
    else:
        refusal_counts[minister] = int(refusal_counts.get(minister, 0)) + 1
    s.ministerial_refusals = refusal_counts
    apply_effect({k: v for k, v in fx.items() if k not in OPINION_KEYS})
    for k in OPINION_KEYS:
        if k in fx:
            s[k] = round(_clip(s[k] + fx[k]), 1)
    verb = (f"You approve the {req['minister']}'s request (£{req['cost']:.1f}B). The minister is now more likely to back your next difficult decision."
            if accept else f"You refuse the {req['minister']}'s request. The minister will lobby colleagues and may brief against the Treasury.")
    s.message = verb
    s.headlines = None
    s.active_request = None
    # A minister with low loyalty, or who has been refused repeatedly, escalates the dispute.
    if not accept and (loyalty[minister] <= 38 or refusal_counts[minister] >= 2) and not s.get('active_dispute'):
        s.active_dispute = {
            'minister': minister, 'cost': float(req['cost']),
            'text': f"{minister} is furious after repeated Treasury refusals. They are threatening to brief the press and challenge your spending priorities unless you offer a compromise.",
            'loyalty': loyalty[minister], 'refusals': refusal_counts[minister],
        }
    state.log('event', f"{req['minister']}: request for £{req['cost']:.1f}B", choice='Approved' if accept else 'Refused',
              before=before, note=verb)
    state.record()
    check_sacked()


def request_ministerial_reshuffle(department):
    """Ask the Prime Minister to replace a Cabinet minister; only the PM can appoint or dismiss."""
    s = st.session_state
    term = int(s.get("term", 1))
    used = list(s.get("cabinet_reshuffle_terms", []))
    if term in used:
        s.message = "You have already made a Cabinet reshuffle request this term. Number 10 will not entertain another."
        return
    if department not in budget.DEPARTMENT_MINISTERS:
        return
    current = str(s.get("cabinet_ministers", {}).get(department, ""))
    if not current or current.startswith("Vacant") or current.startswith("New appointment"):
        s.message = "There is no established minister in that post to recommend for replacement."
        return

    state.checkpoint()
    before = state.values()
    state.snapshot()
    loyalty = float(s.get("ministerial_loyalty", {}).get(department, 55.0))
    pm = float(s.get("pm_opinion", 50.0))
    cabinet = float(s.get("cab_opinion", 50.0))
    dispute = s.get("active_dispute") or {}
    dispute_pressure = 12.0 if dispute.get("minister") == current else 0.0
    score = 0.45 * pm + 0.25 * cabinet + 0.30 * (100.0 - loyalty) + dispute_pressure
    accepted = score >= 58.0
    used.append(term)
    s.cabinet_reshuffle_terms = used[-10:]
    history = list(s.get("cabinet_reshuffle_history", []))
    if accepted:
        cabinet = dict(s.get("cabinet_ministers", {}))
        cabinet[department] = "Vacant — awaiting Prime Minister"
        s.cabinet_ministers = cabinet
        vacancies = dict(s.get("ministerial_vacancy_year", {}))
        vacancies[department] = int(s.get("year", 1))
        s.ministerial_vacancy_year = vacancies
        s.ministerial_loyalty[department] = 50.0
        resignations = list(s.get("ministerial_resignations", []))
        resignations.append({
            "minister": current, "year": int(s.get("year", 1)),
            "term": term, "reason": "Replaced after the Chancellor's recommendation was accepted by the Prime Minister"
        })
        s.ministerial_resignations = resignations[-20:]
        s.cab_opinion = round(_clip(float(s.get("cab_opinion", 50.0)) + 1.5), 1)
        s.pm_opinion = round(_clip(pm + 1.0), 1)
        outcome = (
            f"The Prime Minister accepts your recommendation. {current} leaves the Cabinet; "
            "the post is vacant until Number 10 appoints a successor. Your intervention has strengthened "
            "your standing with the PM, though colleagues will notice that you have challenged a minister."
        )
    else:
        s.pm_opinion = round(_clip(pm - 2.5), 1)
        s.cab_opinion = round(_clip(cabinet - 1.5), 1)
        outcome = (
            f"The Prime Minister rejects your recommendation to replace {current}. Number 10 says the "
            "minister retains its confidence and warns you not to undermine Cabinet colleagues."
        )
    history.append({
        "term": term, "year": int(s.get("year", 1)), "department": department,
        "minister": current, "accepted": accepted, "score": round(score, 1), "outcome": outcome
    })
    s.cabinet_reshuffle_history = history[-20:]
    s.message = outcome
    s.humphrey_note = (
        "A reshuffle is, constitutionally speaking, a matter for the Prime Minister. "
        "Your role was to make a recommendation; Number 10 has now made its position clear."
    )
    state.log("politics", f"Cabinet reshuffle request: {current}",
              choice="Accepted by PM" if accepted else "Rejected by PM",
              before=before, note=outcome)
    state.record()
    check_sacked()


def resolve_ministerial_dispute(choice):
    """Resolve an escalating Cabinet dispute: compromise, stand firm, or let the minister go public."""
    s = st.session_state
    dispute = s.get('active_dispute')
    if not dispute:
        return
    state.checkpoint()
    reseed('ministerial_dispute')
    s.event_cards = []
    before = state.values()
    state.snapshot()
    minister = str(dispute.get('minister', 'Cabinet minister'))
    cost = float(dispute.get('cost', 1.0))
    loyalty = dict(s.get('ministerial_loyalty', {}))
    current = float(loyalty.get(minister, dispute.get('loyalty', 35.0)))
    if choice == 'compromise':
        concession = round(cost * 0.5, 1)
        s.headroom = round(s.headroom - concession, 1)
        s.deficit = round(s.deficit + concession, 1)
        s.cab_opinion = round(_clip(s.cab_opinion + 3.0), 1)
        s.pm_opinion = round(_clip(s.pm_opinion + 1.0), 1)
        loyalty[minister] = round(_clip(current + 18.0), 1)
        outcome = f"You agree a £{concession:.1f}B compromise with the {minister}. The dispute is contained, but the Treasury has conceded ground."
    elif choice == 'stand_firm':
        loyalty[minister] = round(_clip(current - 10.0), 1)
        s.cab_opinion = round(_clip(s.cab_opinion - 3.0), 1)
        s.pm_opinion = round(_clip(s.pm_opinion + 1.0), 1)
        outcome = f"You refuse to change course. The {minister} remains in Cabinet for now, but relations have deteriorated."
    elif choice == 'public':
        loyalty[minister] = round(_clip(current - 18.0), 1)
        s.media_opinion = round(_clip(s.media_opinion - 5.0), 1)
        s.approval = round(_clip(s.approval - 1.5), 1)
        s.cab_opinion = round(_clip(s.cab_opinion - 4.0), 1)
        s.pm_opinion = round(_clip(s.pm_opinion - 2.0), 1)
        outcome = f"The {minister} publicly attacks the Treasury's approach. The row dominates the political news cycle."
        if loyalty[minister] <= 15:
            resignations = list(s.get('ministerial_resignations', []))
            resignations.append({'minister': minister, 'year': int(s.get('year', 1)), 'term': int(s.get('term', 1)), 'reason': 'Resigned after a public dispute with the Chancellor'})
            s.ministerial_resignations = resignations[-20:]
            outcome += f" The {minister} resigns from Cabinet."
    else:
        return
    s.ministerial_loyalty = loyalty
    s.active_dispute = None
    s.message = outcome
    state.log('event', f'Cabinet dispute: {minister}', choice=choice.replace('_', ' ').title(), before=before, note=outcome)
    state.record()
    check_sacked()


# ================================================================ the budget & the spring tick
def submit_budget():
    """Submit the Budget. Applies any unapplied slider changes, delivers the revolt penalties, then holds the vote.

    Returns 'ok', or 'sacked' if the Commons voted it down (or the fallout ended your career).
    """
    s = st.session_state
    stage = int(s.get('budget_day_stage', 0))
    if stage == 0:
        priorities = s.get('budget_pm_priorities') or []
        if not priorities and s.get('budget_day_type') == 'emergency':
            priorities = [
                dict(title="Restore confidence in the public finances", detail="Set out a credible response to the emergency and explain how borrowing will be brought under control.", tag="spending"),
                dict(title="Protect essential public services", detail="Avoid making the crisis worse by undermining core health, education and security services.", tag="health"),
                dict(title="Provide targeted support where it is most urgent", detail="Prioritise households and firms most exposed to the shock, rather than broad unfunded giveaways.", tag="local"),
                dict(title="Show a deliverable plan to Parliament", detail="The package must be costed, deliverable and capable of securing enough Commons support.", tag="investment"),
            ]
            s.budget_pm_priorities = priorities
        if not priorities:
            party = str(s.get('party', 'Labour'))
            pools = {
                'Labour': [
                    ('Protect NHS funding', 'Increase health spending and reduce waiting lists.', 'health'),
                    ('No rises in basic income tax', 'Avoid increasing the basic, higher or additional income tax rates.', 'income_tax'),
                    ('Boost housebuilding and infrastructure', 'Prioritise capital investment, transport and new homes.', 'investment'),
                    ('Keep defence spending on an upward path', 'Provide a credible multi-year settlement for defence.', 'defence'),
                ],
                'Conservative': [
                    ('Keep taxes on working people down', 'Avoid increases to income tax and employee National Insurance.', 'income_tax'),
                    ('Control public spending', 'Show a credible path to lower borrowing and departmental restraint.', 'spending'),
                    ('Increase defence readiness', 'Protect defence capability and equipment budgets.', 'defence'),
                    ('Support business investment', 'Prioritise capital allowances, skills and infrastructure.', 'investment'),
                ],
                'Liberal Democrats': [
                    ('Improve NHS and social care', 'Provide additional support for health and care services.', 'health'),
                    ('Fairer taxation', 'Avoid shifting the burden onto lower and middle earners.', 'fair_tax'),
                    ('Invest in local communities', 'Support councils, housing and local transport.', 'local'),
                    ('Accelerate climate investment', 'Back clean energy and low-carbon infrastructure.', 'green'),
                ],
                'Reform UK': [
                    ('Cut taxes on work and small businesses', 'Prioritise lower taxes on earnings, employers and enterprise.', 'income_tax'),
                    ('Reduce wasteful public spending', 'Find savings while protecting core public services.', 'spending'),
                    ('Increase border and national security capacity', 'Fund enforcement and defence priorities.', 'defence'),
                    ('Scrap costly green levies', 'Reduce energy and motoring costs for households and firms.', 'green'),
                ],
                'Green Party': [
                    ('Accelerate the green transition', 'Prioritise clean energy, public transport and home insulation.', 'green'),
                    ('Fund the NHS and social care', 'Expand frontline services and workforce capacity.', 'health'),
                    ('Make taxation fairer', 'Shift more of the burden towards wealth and high incomes.', 'fair_tax'),
                    ('Build affordable, warm homes', 'Invest in social housing and energy efficiency.', 'local'),
                ],
                'SNP': [
                    ('Protect Scotland’s public services', 'Avoid cuts to health, education and devolved services.', 'health'),
                    ('Secure fair funding for the nations', 'Protect devolved and local-government budgets.', 'local'),
                    ('Invest in Scottish infrastructure', 'Support transport, energy and regional growth.', 'investment'),
                    ('Support household incomes', 'Avoid tax and spending decisions that squeeze working families.', 'income_tax'),
                ],
                'Plaid Cymru': [
                    ('Protect Welsh public services', 'Avoid cuts to health, education and devolved services.', 'health'),
                    ('Fair funding for Wales', 'Protect local government and devolved budgets.', 'local'),
                    ('Invest in Welsh jobs and infrastructure', 'Support transport, skills and regional growth.', 'investment'),
                    ('Strengthen communities and the Welsh language', 'Back local services and cultural investment.', 'green'),
                ],
                'default': [
                    ('Protect public services', 'Avoid real-terms cuts to frontline services.', 'health'),
                    ('Keep household taxes stable', 'Avoid increasing taxes on ordinary working households.', 'income_tax'),
                    ('Support growth and investment', 'Prioritise infrastructure, skills and business investment.', 'investment'),
                    ('Maintain fiscal credibility', 'Avoid a large unfunded increase in borrowing.', 'spending'),
                ],
            }
            priorities = [dict(title=x[0], detail=x[1], tag=x[2]) for x in pools.get(party, pools['default'])]
            s.budget_pm_priorities = priorities
        choice = s.get('budget_pm_choice', 'Compromise with the Prime Minister')

        assessment = budget.assess_pm_priorities()
        met_count = sum(1 for item in assessment if item['met'])
        total_count = len(assessment)
        s.budget_pm_assessment = assessment
        if choice == 'Accept the Prime Minister’s priorities':
            s.pm_opinion = round(_clip(s.pm_opinion + (5 if met_count == total_count else 1)), 1)
            s.approval = round(_clip(s.approval + 0.5), 1)
        elif choice == 'Stand firm on the Treasury plan':
            s.pm_opinion = round(_clip(s.pm_opinion - (5 if met_count < total_count else 1)), 1)
            s.backbench_opinion = round(_clip(s.backbench_opinion + 1), 1)
        else:
            s.pm_opinion = round(_clip(s.pm_opinion + (2 if met_count >= max(1, total_count // 2) else -1)), 1)
        s.budget_pm_met_count = met_count

        event_name = "Emergency Budget" if s.get('budget_day_type') == 'emergency' else "Spring Budget"
        s.budget_day_negotiation = f"Your {event_name.lower()} draft meets {met_count} of {total_count} Prime Ministerial priorities. " + ("Number 10 welcomes the package." if met_count == total_count else "The PM's team has identified gaps that will need explaining.")
        s.budget_day_stage = 1
        s.message = s.budget_day_negotiation
        return 'negotiated'
    if stage == 1:
        draft = s.get('budget_day_draft') or budget.read()
        s.budget_day_forecast = budget.forecast(draft, years=3)
        s.budget_day_stage = 2
        return 'forecast'
    if stage == 2:
        draft = s.get('budget_day_draft') or budget.read()
        s.budget_day_draft = draft
        s.budget_day_speech = speech.compose(draft)
        s.budget_day_stage = 3
        return 'speech'
    state.checkpoint()
    reseed('budget')
    s.event_cards = []
    budget.ensure()
    before = state.values()
    draft = s.get('budget_day_draft') or budget.read()
    if draft != s.budget_applied:
        budget._apply(draft)
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
    s.vote_ayes = ayes
    s.budget_speech = speech.compose(draft)
    market_impulse = float((s.get('budget_impact') or {}).get('market', 0.0))
    gilt_move = max(-0.12, min(0.12, -0.035 * market_impulse))
    if float((s.get('budget_impact') or {}).get('headroom', 0.0)) < -5:
        gilt_move += 0.04
    s.gilt_yield = round(max(0.1, s.gilt_yield + gilt_move), 2)
    s.budget_speech['market_move'] = gilt_move
    s.budget_speech['market_after'] = s.gilt_yield
    budget.resolve_budget_risks()
    event_type = 'Emergency Budget' if s.get('budget_day_type') == 'emergency' else 'Spring Budget'
    budget.commit_budget(ayes, event_type=event_type)
    s.budget_passed = True
    s.budget_day_stage = 4
    s.headlines = generate_headlines(None, True, s.headroom)
    update_polls(_period_label())
    s.steps += 1
    state.log('budget', f'Year {s.year} {event_type}', note=s.message, before=before)
    deliver_pending()
    state.record()
    check_sacked()
    return 'sacked' if s.get('game_over') else 'ok'


def economy_tick():
    """Once a year the economy moves on by itself: inflation, rates, gilts, growth and the knock-on drags."""
    s = st.session_state
    keys = ('inflation', 'interest_rate', 'gilt_yield', 'growth', 'debt', 'deficit', 'headroom', 'market_conf', 'approval')
    # GDP provides the denominator for the sovereign deficit-risk calculation.
    
    v = {k: s[k] for k in keys}
    v['cycle'] = s.get('macro_cycle')
    v['gdp_trillion'] = float(s.get('gdp_trillion', 3.0))
    out = econ.step(v, econ.game_year(s.term, s.year) + 1)   # +1: the year we are moving into
    for k in ('inflation', 'interest_rate', 'gilt_yield', 'growth', 'debt', 'deficit', 'headroom', 'market_conf'):
        s[k] = out[k]
    s.gilt_risk_premium = float(out.get('gilt_risk_premium', 0.0))
    s.debt_interest_bill = float(out.get('debt_interest_bill', s.get('debt_interest_bill', 10.7)))

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

    # Labour-market automatic stabilisers: weak growth and high borrowing costs
    # raise unemployment; a stronger expansion gradually creates jobs.
    # Real wages respond to estimated nominal pay growth less inflation.
    labour_growth = float(s.growth)
    labour_rate_drag = max(0.0, float(s.interest_rate) - 4.5)
    unemployment_change = -0.10 * (labour_growth - 1.2) + 0.025 * labour_rate_drag
    nominal_pay_growth = 2.6 + 0.22 * (labour_growth - 1.2) - 0.08 * labour_rate_drag
    real_wage_target = nominal_pay_growth - float(s.inflation)
    real_wage_change = 0.25 * (real_wage_target - float(c.get('real_wages', 0.0)))
    previous_country = dict(c)
    country.nudge({
        'unemployment': round(unemployment_change, 2),
        'real_wages': round(real_wage_change, 2),
    }, snapshot=False)

    # Economic transmission: the state of public services and household finances
    # feeds back into productivity, demand and the public finances each spring.
    current_country = s.get('country', {})
    unemployment_delta = float(current_country.get('unemployment', 4.3)) - float(previous_country.get('unemployment', 4.3))
    wage_delta = float(current_country.get('real_wages', 0.0)) - float(previous_country.get('real_wages', 0.0))

    # A worsening labour market raises benefit spending and reduces income-tax
    # receipts; falling unemployment provides a modest automatic-stabiliser dividend.
    stabiliser_cost = round(max(-2.0, min(2.0, unemployment_delta * 1.35)), 2)
    if abs(stabiliser_cost) >= 0.05:
        s.deficit = round(max(0.0, float(s.deficit) + stabiliser_cost), 1)
        s.headroom = round(float(s.headroom) - stabiliser_cost, 1)
        if stabiliser_cost > 0:
            s.message += f' Higher unemployment adds around £{stabiliser_cost:.2f}B to welfare costs and lost receipts.'
        else:
            s.message += f' Falling unemployment improves the fiscal position by around £{-stabiliser_cost:.2f}B.'

    # Real wage gains support household demand; falling real pay weakens it.
    demand_impulse = max(-0.08, min(0.08, wage_delta * 0.035))
    if abs(demand_impulse) >= 0.01:
        s.growth = round(float(s.growth) + demand_impulse, 2)
        s.message += (' Stronger real pay is supporting consumer demand.' if demand_impulse > 0
                      else ' Falling real pay is weighing on household demand.')

    # Education, transport, housing supply and clean-energy infrastructure
    # influence the productive capacity of the economy over several years.
    service_levels = s.get('country', {})
    productivity_signal = (
        (float(service_levels.get('schools', 62.0)) - 62.0) * 0.0015
        + (float(service_levels.get('rail', 82.0)) - 82.0) * 0.0012
        + (float(service_levels.get('homes_built', 215.0)) - 215.0) * 0.00045
        + (float(service_levels.get('netzero', 38.0)) - 38.0) * 0.0005
    )
    productivity_impulse = round(max(-0.12, min(0.18, productivity_signal)), 3)
    if abs(productivity_impulse) >= 0.01:
        s.growth = round(float(s.growth) + productivity_impulse, 2)
        s.message += (f' Long-term investment and infrastructure add {productivity_impulse:+.2f} percentage points to productive capacity.'
                      if productivity_impulse > 0 else
                      f' Weak infrastructure and skills subtract {abs(productivity_impulse):.2f} percentage points from productive capacity.')
    if unemployment_change > 0.12:
        s.message += ' A weak labour market is pushing unemployment higher.'
    elif unemployment_change < -0.12:
        s.message += ' Stronger economic activity is creating jobs and easing unemployment.'


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
    import living_economy
    living_economy.advance(s)
    economic_management.annual_update()
    economic_management.run_gilt_auction()
    economic_management.advance_financial_stability()
    household.advance(s)
    regional_economy.advance(s)
    public_services.advance(s)
    devolution.annual_update()
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
    # Higher nominal GDP expands the tax base; public assets add recurring income.
    treasury.annual_update(nominal_growth)
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
    # Keep the approved Budget ledger and its widgets aligned with automatic annual uprating.
    budget.ensure()
    approved_thresholds = dict(s.budget_applied.get('thresholds', {}))
    for key in ('personal_allowance', 'higher_rate_threshold', 'additional_rate_threshold'):
        approved_thresholds[key] = float(s.get(key, approved_thresholds.get(key, 0.0)))
        s[f'bt_threshold_{key}'] = approved_thresholds[key]
    s.budget_applied['thresholds'] = approved_thresholds
    # State Pension uprating: each £1/week change adds an estimated £0.6bn annual cost.
    s.setdefault('state_pension_weekly', 230.25)
    uprating = s.get('state_pension_uprating', 'Triple lock')
    if uprating == 'Triple lock':
        pension_growth = max(float(s.growth), float(s.inflation), 2.5)
    elif uprating == 'Earnings growth':
        pension_growth = max(0.0, float(s.growth))
    elif uprating == 'CPI inflation':
        pension_growth = max(0.0, float(s.inflation))
    else:
        pension_growth = 0.0
    old_weekly = float(s.state_pension_weekly)
    s.state_pension_weekly = round(old_weekly * (1.0 + pension_growth / 100.0), 2)
    pension_uprating_cost = (s.state_pension_weekly - old_weekly) * 0.6
    if abs(pension_uprating_cost) > 0.001:
        s.headroom = round(s.headroom - pension_uprating_cost, 1)
        s.deficit = round(s.deficit + pension_uprating_cost, 1)
        s.message += f' State Pension uprating ({uprating.lower()}) changes the modelled annual bill by £{pension_uprating_cost:.2f}bn.'
    # Retirement-age savings persist as a recurring annual effect, not just a one-off bonus.
    age_saving = float(s.get('retirement_age_annual_saving', 0.0))
    if age_saving:
        s.headroom = round(s.headroom + age_saving, 1)
        s.deficit = round(s.deficit - age_saving, 1)
        s.message += f' The State Pension age setting changes annual spending by £{age_saving:+.1f}bn.'
    # Demographic ageing adds a gradual pension cost every year; the uprating rule affects the size of the bill.
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
    performance_report.create_report()
    s.year += 1
    fiscal_events.schedule_spending_review(s)
    budget.apply_spending_review_rollforward(s, s.year)
    # Annual local contests take place after the first full year in office.
    s.local_election_due = s.year > 1
    s.block = 1
    s.budget_passed = False
    s.budget_day_stage = 0
    s.budget_pm_choice = 'Compromise with the Prime Minister'
    s.budget_day_negotiation = ''
    s.budget_day_forecast = []
    s.budget_day_speech = None
    s.budget_risk_outcome = None
    s.budget_day_type = 'annual'
    s.budget_day_draft = None
    s.headlines = None
    s.steps += 1
    state.log('event', f'Spring, year {s.year}', note=s.message, before=before)
    deliver_pending()
    state.record()
    fiscal_events.maybe_trigger_emergency_budget(s)
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


def compute_seats(polls, return_details=False):
    """Model all 650 FPTP contests using stable local lean, national swings and campaign targeting.

    This is an illustrative game model, not an official constituency forecast. Local
    variation is deliberately substantial so a national lead does not translate into
    an implausible sweep of almost every seat.
    """
    s = st.session_state
    import json
    from pathlib import Path

    data_path = Path(__file__).resolve().parent / 'data' / 'constituencies_2024.json'
    with data_path.open(encoding='utf-8') as handle:
        constituencies = json.load(handle).get('constituencies', [])
    if len(constituencies) != SEATS:
        return _legacy_compute_seats(polls)

    parties = list(state.PARTIES)
    nation_effects = {
        'England': {},
        'Scotland': {'SNP': 15.0, 'Labour': 1.0, 'Conservative': -1.0},
        'Wales': {'Plaid Cymru': 15.0, 'Labour': 2.0, 'Conservative': -1.0},
        'Northern Ireland': {'SNP': -8.0, 'Plaid Cymru': -8.0,
                             'Liberal Democrats': -3.0, 'Green Party': -2.0},
    }
    incumbents = s.get('constituency_incumbents', {})
    player = s.get('party')
    campaign_actions = s.get('election_campaign_actions', [])
    target_marginals = any(x.get('action') == 'Target marginal constituencies' for x in campaign_actions)
    gotv = any(x.get('action') == 'Get out the vote operation' for x in campaign_actions)
    scored_seats = []

    for seat in constituencies:
        code = str(seat.get('code', seat.get('name', '')))
        nation = seat.get('nation', 'England')
        scores = {}
        for party in parties:
            # Stable local political geography, with enough variation to create
            # safe seats, marginals and geographically concentrated challengers.
            rng = random.Random(f"seat-lean:{code}:{party}")
            local_lean = rng.gauss(0.0, 12.5)
            regional = nation_effects.get(nation, {}).get(party, 0.0)
            concentration = 0.0
            if party == 'Liberal Democrats' and random.Random('libdem-target:' + code).random() < 0.20:
                concentration = 25.0
            elif party == 'Green Party' and random.Random('green-target:' + code).random() < 0.10:
                concentration = 20.0
            incumbent_party = incumbents.get(code)
            incumbency = 3.5 if incumbent_party == party else 0.0
            national = max(0.1, float(polls.get(party, 0.0)))
            scores[party] = max(0.01, national + local_lean + regional + concentration + incumbency)
        ranked = sorted(scores, key=scores.get, reverse=True)
        scored_seats.append({
            'seat': seat, 'code': code, 'nation': nation, 'scores': scores,
            'margin': scores[ranked[0]] - scores[ranked[1]],
        })

    # Campaign resources have a constituency-level effect as well as the small
    # national polling effect already applied by the campaign screen.
    if player in parties and (target_marginals or gotv):
        closest = sorted(scored_seats, key=lambda row: row['margin'])
        if target_marginals:
            for row in closest[:70]:
                row['scores'][player] += 3.0
        if gotv:
            for row in closest[:100]:
                row['scores'][player] += 1.6

    seats = {p: 0 for p in parties}
    results = []
    for row in scored_seats:
        scores = row['scores']
        winner = max(parties, key=scores.get)
        seats[winner] += 1
        runner_up = max((p for p in parties if p != winner), key=lambda p: scores[p])
        results.append({
            'name': row['seat'].get('name', 'Unknown constituency'),
            'code': row['code'],
            'nation': row['nation'],
            'winner': winner,
            'runner_up': runner_up,
            'margin': round(scores[winner] - scores[runner_up], 1),
            'is_marginal': (scores[winner] - scores[runner_up]) < 5.0,
        })

    return (seats, results) if return_details else seats

def _legacy_compute_seats(polls):
    """Fallback allocation for a missing or invalid constituency register."""
    weights = {
        'Labour': 1.12, 'Conservative': 1.12, 'Liberal Democrats': 0.72,
        'Reform UK': 0.48, 'Green Party': 0.32, 'SNP': 3.20, 'Plaid Cymru': 3.00,
    }
    regional_caps = {'SNP': 57, 'Plaid Cymru': 32}
    seats = {p: 0 for p in state.PARTIES}
    for party, cap in regional_caps.items():
        seats[party] = min(cap, int(round(SEATS * max(0.0, float(polls.get(party, 0))) / 100 * weights[party])))
    remaining = SEATS - sum(seats.values())
    national = [p for p in state.PARTIES if p not in regional_caps]
    raw = {p: max(0.0, float(polls.get(p, 0))) * weights[p] for p in national}
    total = sum(raw.values()) or float(len(national))
    exact = {p: remaining * (raw[p] if sum(raw.values()) else 1.0) / total for p in national}
    for p in national:
        seats[p] = int(math.floor(exact[p]))
    leftovers = remaining - sum(seats[p] for p in national)
    for p in sorted(national, key=lambda party: exact[party] - seats[party], reverse=True)[:leftovers]:
        seats[p] += 1
    return seats


def party_is_nonregional(party):
    return party in state.PARTIES and party not in state.REGIONAL


def compute_election():
    """Work out (once) the general election result. Stored in session state so reruns don't change it."""
    s = st.session_state
    if s.get('election_result'):
        return s.election_result
    reseed('election')
    polls = {p: s.poll_history[p][-1] for p in state.PARTIES}
    seats, constituency_results = compute_seats(polls, return_details=True)
    # The selected non-regional party begins the game with a comfortable first-term mandate.
    # Preserve that opening premise through the first election, then return to the normal FPTP model.
    if s.get('opening_mandate_pending') and party_is_nonregional(s.get('party')):
        player_party = s.party
        target_seats = 365
        current = int(seats.get(player_party, 0))
        if current < target_seats:
            available = sorted(
                (row for row in constituency_results if row.get('winner') != player_party),
                key=lambda row: (float(row.get('margin', 0.0)), row.get('code', ''))
            )
            for row in available[:target_seats - current]:
                displaced = row.get('winner')
                seats[displaced] = max(0, int(seats.get(displaced, 0)) - 1)
                seats[player_party] = int(seats.get(player_party, 0)) + 1
                row['winner'], row['runner_up'] = player_party, displaced
                row['margin'] = max(0.1, float(row.get('margin', 0.0)))
                row['is_marginal'] = True
        s.opening_mandate_pending = False
    previous_seats = s.get('previous_election_seats', {})
    seat_changes = {p: int(seats.get(p, 0)) - int(previous_seats.get(p, seats.get(p, 0))) for p in state.PARTIES}
    # Store this parliament's results and winners for the next general election.
    s.previous_election_seats = dict(seats)
    s.constituency_incumbents = {str(row.get('code', '')): row.get('winner') for row in constituency_results}
    largest = max(seats, key=seats.get)
    party = s.party
    mine = seats[party]
    regional = party in state.REGIONAL

    sacked = s.pm_opinion < 40 or s.party_opinion < 35
    history = s.get('poll_history', {})
    previous = {p: (history.get(p, [polls[p]])[-2] if len(history.get(p, [])) > 1 else polls[p]) for p in state.PARTIES}
    swings = {p: round(float(polls[p]) - float(previous[p]), 1) for p in state.PARTIES}
    turnout = round(max(55.0, min(82.0, 65.0 + random.uniform(-1.8, 1.8) + (float(s.approval) - 50) * 0.04 + float(s.get('election_campaign_turnout', 0.0)))), 1)
    r = dict(seats=seats, player_seats=mine, regional=regional, win=False, kind='loss', margin=0,
             coalition=None, sacked=sacked, polls=polls, swings=swings, turnout=turnout,
             constituency_results=constituency_results, seat_changes=seat_changes,
             sacked_msg=('Your relationship with the Prime Minister and your own backbenches collapsed. Regardless of the '
                         'election result, you have been sacked and banished to the backbenches.') if sacked else '')

    if regional:
        # A regional party does not need to win almost every seat in its nation
        # to retain a meaningful mandate. These thresholds represent a credible
        # Westminster bloc, not outright control of the devolved nation.
        target = REGIONAL_MANDATES[party]
        cap = 57 if party == 'SNP' else 32
        if mine >= target:
            r.update(win=True, kind='regional', margin=mine - target,
                     title=f'{party} Regional Mandate ({mine}/{cap})',
                     gov_type='Holding the Balance of Power in Westminster' if seats[largest] < WIN_MAJORITY else 'Strong Regional Opposition')
        else:
            r.update(title=f'{party} Regional Defeat ({mine} seats)', gov_type='Loss of Regional Mandate')
    elif mine >= WIN_MAJORITY:
        r.update(win=True, kind='majority', margin=mine - WIN_MAJORITY, title=f'{party} Majority Government',
                 gov_type=f'Working Majority of {mine - WIN_MAJORITY}')
    else:
        r['title'] = 'Hung Parliament'
        bloc = LEFT_BLOC if party in LEFT_BLOC else RIGHT_BLOC
        eligible = [p for p in bloc if p != party and seats.get(p, 0) > 0]
        coalition_partners = []
        # Search the smallest viable coalition first, then choose the combination
        # with the narrowest surplus. This supports multi-party agreements without
        # automatically giving the player every ideologically compatible party.
        for count in range(1, len(eligible) + 1):
            viable = [
                group for group in combinations(eligible, count)
                if mine + sum(seats[p] for p in group) >= WIN_MAJORITY
            ]
            if viable:
                coalition_partners = list(min(
                    viable,
                    key=lambda group: mine + sum(seats[p] for p in group) - WIN_MAJORITY
                ))
                break
        if coalition_partners:
            government_seats = mine + sum(seats[p] for p in coalition_partners)
            coalition_label = ' + '.join(coalition_partners)
            r.update(win=True, kind='coalition', coalition=coalition_label,
                     coalition_partners=coalition_partners,
                     margin=government_seats - WIN_MAJORITY,
                     gov_type=f'Coalition with {coalition_label}')
        elif mine == seats[largest]:
            r.update(win=True, kind='minority', gov_type='Fragile Minority Government')
        else:
            r['gov_type'] = 'Sent to the Opposition Benches'

    if r.get('win'):
        government_seats = mine + sum(seats.get(p, 0) for p in (r.get('coalition_partners') or []))
        majority = government_seats - WIN_MAJORITY
        r['government_seats'] = government_seats
        r['working_majority'] = majority
        if r.get('kind') == 'majority':
            r['mandate_strength'] = max(0, min(12, int(round(majority / 12))))
            r['mandate_label'] = ('Strong mandate' if majority >= 80 else 'Working mandate' if majority >= 20 else 'Narrow mandate')
        elif r.get('kind') == 'coalition':
            # Coalition authority is real, but shared: it should never create a
            # negative mandate merely because the largest party lacks 326 seats.
            r['mandate_strength'] = max(0, min(2, int(round(max(0, majority) / 20))))
            r['mandate_label'] = 'Coalition mandate'
        elif r.get('kind') == 'minority':
            r['mandate_strength'] = 0
            r['mandate_label'] = 'Minority mandate'
        else:  # Regional mandate: not a Westminster government majority.
            r['mandate_strength'] = 0
            r['mandate_label'] = 'Regional mandate'
    else:
        r['government_seats'] = mine
        r['working_majority'] = mine - WIN_MAJORITY
        r['mandate_strength'] = 0
        r['mandate_label'] = 'No governing mandate'
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
    s.general_election_mandate = int(r.get('mandate_strength', 0))
    if r.get('kind') in ('coalition', 'minority'):
        s.general_election_mandate = min(s.general_election_mandate, 2)
    s.term += 1
    s.year, s.block = 1, 1
    s.political_capital_points = 5
    s.feature_notice = ''
    s.feature_notice_phase = 0
    s.budget_passed = False
    s.election_result = None
    s.spending_review_due = True
    s.fiscal_calendar_initialised = True
    s.budget_day_type = 'annual'
    s.active_emergency_budget = None
    s.active_crisis = None
    s.headlines = None
    s.pending = []
    s.fallout_done = []
    s.ideology_counts = {}
    s.crises_handled = 0
    s.new_achievements = []
    s.poll_anchor = {p: s.poll_history[p][-1] for p in state.PARTIES}
    s.election_campaign_done = False
    s.election_night_started = False
    s.election_campaign_strategy = ''
    s.election_campaign_turnout = 0.0
    s.election_campaign_approval = 0.0
    s.election_campaign_week = 1
    s.election_campaign_actions = []
    s.election_broadcast_stage = 0
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
