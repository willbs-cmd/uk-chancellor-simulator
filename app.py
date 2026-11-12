"""UK Chancellor Simulator (Hardcore Mode): the Streamlit UI. All game rules live in engine.py."""
import pandas as pd
import streamlit as st

import achievements
import budget
import country
import engine
import features
import imf_outlook
import world_economy
import politics
import parliament
import local_elections
import scenarios as scen
import state
import treasury
import chancellor_office
import devolution
import performance_report
import economic_management
import household
import regional_economy
import public_services
import chancellors_desk
from state import CARDS_ECON, CARDS_POLITICAL, CARDS_TOP
from theme import (apply_theme, crisis_card, event_card, header, humphrey_message, news_box,
                   render_hud, render_newspapers, render_polls, render_scorecard, render_timeline, phase_info)

st.set_page_config(page_title='The Chancellor’s Office', layout='wide', page_icon='🏛️',
                   initial_sidebar_state='expanded')
apply_theme()
state.ensure_init()
s = st.session_state


def restart():
    s.clear()
    st.rerun()


# ==================== PERMANENT CHANCELLOR'S DESK ====================
chancellors_desk.render(restart)


# ==================== SETUP SCREEN ====================
def setup_screen():
    st.markdown("""<div class='setup-hero'><div class='seal'>HM TREASURY · SIMULATION</div><h1>The Chancellor's Office</h1><p>Manage the economy, make policy choices and steer your government through Parliament.</p><span class='stamp'>The Chancellor's Office</span></div>""", unsafe_allow_html=True)
    st.markdown("### Step 1 · Form your government")
    party = st.selectbox("Select Governing Party:", state.PARTIES)
    difficulty = st.radio(
        "Difficulty", list(state.DIFFICULTY), index=2, horizontal=True,
        captions=[d['blurb'] for d in state.DIFFICULTY.values()],
        help='Easy is forgiving; Normal is balanced; Hardcore has frequent crises and no undo.'
    )
    c1, c2, c3 = st.columns([1.4, 1.4, 1], gap='medium')
    with c1:
        scenario = st.selectbox('Starting scenario', list(state.SCENARIOS), format_func=lambda k: state.SCENARIOS[k]['label'])
        st.caption(state.SCENARIOS[scenario]['blurb'])
    with c2:
        spad = st.selectbox('Special Advisor', [None, *politics.SPADS],
                            format_func=lambda k: 'None' if k is None else politics.SPADS[k]['label'])
        st.caption(politics.SPADS[spad]['blurb'] if spad else 'Go it alone, with no help from anyone.')
    with c3:
        seed = st.number_input('Game seed', min_value=1, max_value=999999, value=int(s.seed), step=1,
                               help='The same seed recreates the same random events, making runs comparable.')
    pledges = st.multiselect(
        'Manifesto pledges (optional, up to 3)', list(politics.PLEDGES),
        format_func=lambda k: politics.PLEDGES[k]['label'], max_selections=3,
        help='Each pledge gives +2 starting approval, but it is a promise, not a free bonus: it can constrain future Budgets, and breaking one causes a U-turn scandal (approval, media and party support all fall).'
    )
    tags = st.checkbox(
        'Show ideology tags on policy options',
        value=(difficulty == 'Easy'), key=f'tags_{difficulty}',
        help='Off by default: read the policy, not the label. Your MPs still know what is and is not in your party tradition.'
    )
    if st.button('Enter Number 11', type='primary', use_container_width=True):
        state.new_game(
            party, difficulty, seed, tags,
            scenario=scenario, spad=spad, pledges=pledges,
            game_mode='chancellor'
        )
        st.rerun()

    with st.expander('Load a saved game'):
        up = st.file_uploader('Save file (.json)', type='json')
        if up is not None and st.button('Load game'):
            err = state.import_save(up.getvalue().decode('utf-8', errors='replace'))
            if err:
                st.error(err)
            else:
                st.rerun()


if s.step == 'setup':
    setup_screen()
    st.stop()


# ==================== MAIN HEADER & DASHBOARD ====================
header(s.party, s.term, s.year, s.block)


def hud_note():
    """One quiet line under the key stats: world cycle plus up to three urgent risks."""
    icon = {'Boom': '📈', 'Stagnation': '➖', 'Recession': '📉'}.get(s.get('macro_cycle'), '➖')
    bits = [f"🌍 World economy: <b>{icon} {s.get('macro_cycle', 'Stagnation')}</b>"]
    risks = []
    if float(s.get('market_conf', 50)) < 40:
        risks.append(('danger', '⚠ Markets fragile'))
    if float(s.get('backbench_opinion', 60)) < 40:
        risks.append(('danger', '⚠ Rebellion risk'))
    if float(s.get('headroom', 0)) < 0:
        risks.append(('danger', '⚠ Negative headroom'))
    if float(s.get('inflation', 2)) >= 4.5:
        risks.append(('warning', '↑ Inflation pressure'))
    if float(s.get('approval', 50)) < 30:
        risks.append(('warning', '↓ Public approval'))
    status = ''.join(f"<span class='pulse-flag {kind}'>{label}</span>" for kind, label in risks[:3])
    status_html = f"<div class='pulse-flags'>{status}</div>" if status else ""
    return ''.join(f'<span>{b}</span>' for b in bits) + status_html


# The headline row shows the six numbers a Chancellor checks first; everything else is one click away.
_by_key = {d['key']: d for d in CARDS_TOP + CARDS_ECON + CARDS_POLITICAL}
_KEY_STATS = ['approval', 'market_conf', 'headroom', 'growth', 'inflation', 'pm_opinion']
_on_budget_screen = (s.block == 3 and s.active_crisis is None and s.year <= 5 and not s.get('game_over'))
if _on_budget_screen:
    # The Budget screen shows the projected economy itself, so only political capital is needed here.
    render_hud([('Political capital', CARDS_POLITICAL)], note=hud_note())
else:
    render_hud([(None, [_by_key[k] for k in _KEY_STATS])], note=hud_note())
    with st.expander('All indicators', expanded=False):
        render_hud([('The economy', [d for d in CARDS_TOP + CARDS_ECON if d['key'] not in _KEY_STATS]),
                    ('Political capital', [d for d in CARDS_POLITICAL if d['key'] not in _KEY_STATS])])


def scorecard_block(show_share=True):
    data = engine.scorecard()
    render_scorecard(data)
    st.markdown("### 📚 Your Chancellor's legacy")
    st.write(data.get('legacy', 'Your record is still being written.'))
    c1, c2, c3 = st.columns(3)
    c1.metric("Policies & crises", data.get('actions', 0))
    c2.metric("Commons votes", data.get('commons_votes', 0))
    c3.metric("Bills rejected", data.get('bills_rejected', 0))
    if data.get('chapters'):
        with st.expander("Read the key moments of your term"):
            for item in data['chapters']:
                st.markdown(f"**{item['title']}**")
                st.caption(item['detail'])
    if show_share:
        st.caption('Share your result:')
        st.code(data['share'], language=None)


# ==================== GAME OVER (sacked / lost / resigned) ====================
if s.get('game_over'):
    over = s.game_over
    if over['kind'] == 'resigned':
        humphrey_message("A difficult day, Chancellor. You have left the Treasury by your own decision, rather than wait to be removed.")
        st.info("You resigned following a direct ultimatum from the Prime Minister.")
    elif over['kind'] == 'sacked':
        humphrey_message("I am so sorry, Chancellor. The Prime Minister feels that your continued presence at the Treasury "
                         "is... politically sub-optimal. The removal van is waiting at the back door of Number 11.")
        st.error(s.get('sacked_reason') or 'You have been sacked.')
    elif over['kind'] == 'lost':
        humphrey_message("The electorate has spoken, Chancellor. Or rather, they have shouted. We have been thoroughly "
                         "evicted. I shall miss our little chats.")
    scorecard_block()
    if state.can_undo():
        if st.button(f"↩️ Undo that ({s.get('undos_left', 0)} left)"):
            if state.undo():
                st.rerun()
    if st.button('Start a New Career', type='primary'):
        restart()
    st.stop()


# ==================== GENERAL ELECTION CAMPAIGN ====================
if s.year > 5 and not s.get('election_campaign_done', False):
    s.setdefault('election_campaign_week', 1)
    s.setdefault('election_campaign_actions', [])
    week = int(s.election_campaign_week)
    total_weeks = 4
    current_polls = {p: float(s.poll_history[p][-1]) for p in state.PARTIES}
    opponents = [p for p in state.PARTIES if p != s.party]
    main_rival = max(opponents, key=lambda p: current_polls[p]) if opponents else s.party
    st.markdown("# 🗳️ General Election Campaign")
    st.caption(f"Term {s.term} · Campaign week {min(week, total_weeks)} of {total_weeks} · Campaign headquarters")
    st.markdown(f"""
    <div class='general-election-hero'>
      <div class='campaign-eyebrow'>THE COUNTRY GOES TO THE POLLS</div>
      <h2>Four weeks to make your case.</h2>
      <p>Rallies, debates, manifesto launches and marginal-seat campaigning will shape the final result. Every week you must choose where to spend your political capital and campaign time.</p>
    </div>
    """, unsafe_allow_html=True)
    poll_cols = st.columns(len(state.PARTIES))
    for col, party in zip(poll_cols, state.PARTIES):
        delta = None
        if len(s.poll_history[party]) > 1:
            delta = round(float(s.poll_history[party][-1]) - float(s.poll_history[party][-2]), 1)
        col.metric(party, f"{current_polls[party]:.1f}%", delta=(f"{delta:+.1f} pts" if delta is not None else None))
    projected_seats = engine.compute_seats(current_polls)
    projection_party = max(projected_seats, key=projected_seats.get)
    projection_cols = st.columns(3)
    projection_cols[0].metric("Your projected seats", projected_seats.get(s.party, 0))
    projection_cols[1].metric("Largest party in projection", projection_party)
    projection_cols[2].metric("Projected Commons majority", max(0, projected_seats.get(s.party, 0) - engine.WIN_MAJORITY))
    st.caption("Illustrative seat projection from the game's constituency model. It updates as national polls and campaign choices change; it is not a real-world forecast.")
    st.progress(min(1.0, (week - 1) / total_weeks), text=f"Campaign progress · {week - 1}/{total_weeks} weeks completed")
    week_briefings = {
        1: ("The campaign launch", "Set the tone with a major announcement and the first national visits."),
        2: ("The national debate", f"The televised debate is approaching. {main_rival} is currently your strongest polling rival."),
        3: ("The manifesto week", "Voters want to know what the next Parliament would actually deliver."),
        4: ("The final weekend", "The last days are about turnout, tactical visits and answering late campaign controversies."),
    }
    heading, briefing = week_briefings.get(week, week_briefings[4])
    st.markdown(f"### Week {week}: {heading}")
    st.write(briefing)
    action_pool = {
        1: {
            "Launch a cost-of-living tour": ("Visit towns and announce a focused household-cost package.", 0.65, 0.6, 0.2),
            "Hold a major rally": ("Energise party members and volunteers with a high-profile rally.", 0.45, 1.0, 0.1),
            "Target marginal constituencies": ("Put campaign resources into seats where small swings decide MPs.", 0.8, 1.1, 0.0),
        },
        2: {
            "Prepare for the televised debate": ("A strong performance can shift undecided voters; a poor one can hand momentum to your rival.", 0.9 if s.approval >= 45 else 0.25, 0.25, 0.25 if s.approval >= 45 else -0.2),
            "Go on a regional media tour": ("Reach voters outside the Westminster bubble and explain your record.", 0.55, 0.45, 0.15),
            "Confront the opposition leader": ("Make a direct contrast with the leading rival. It is high-profile but can look negative.", 0.7, 0.1, -0.1),
        },
        3: {
            "Launch a fully costed manifesto": ("Set out spending, tax and public-service commitments. Credibility matters.", 0.8 if s.headroom >= 0 else 0.25, 0.2, 0.35 if s.headroom >= 0 else -0.25),
            "Focus on the NHS and public services": ("Put service performance and waiting times at the centre of the campaign.", 0.6, 0.3, 0.25 if s.approval >= 45 else -0.05),
            "Make a major economic speech": ("Argue that your economic record offers stability and growth.", 0.65 if s.growth >= 0 else 0.3, 0.15, 0.2),
        },
        4: {
            "Get out the vote operation": ("Mobilise supporters and concentrate on the closest seats.", 0.45, 1.8, 0.0),
            "Final leader's rally": ("End the campaign with a high-energy national rally.", 0.55, 1.0, 0.1),
            "Respond to a late campaign controversy": ("Take questions, publish evidence and try to stop a damaging story spreading.", 0.35 if s.approval < 50 else 0.6, 0.3, 0.25),
        },
    }
    actions = action_pool.get(week, action_pool[4])
    chosen = st.radio("This week's campaign decision", list(actions), format_func=lambda k: f"{k} — {actions[k][0]}", key=f"election_campaign_action_{week}")
    if st.button("Commit campaign team to this week's plan", type="primary", use_container_width=True):
        description, raw_swing, turnout, approval_change = actions[chosen]
        # A campaign action moves support towards the incumbent government party;
        # the size of the movement is deliberately modest and shared across rivals.
        swing = max(-0.35, min(1.1, raw_swing + (float(s.approval) - 50.0) * 0.008))
        old = {p: float(s.poll_history[p][-1]) for p in state.PARTIES}
        new = dict(old)
        new[s.party] = max(0.5, new[s.party] + swing)
        rivals = [p for p in state.PARTIES if p != s.party]
        rival_pool = sum(old[p] for p in rivals)
        for party in rivals:
            new[party] = max(0.5, old[party] - swing * old[party] / rival_pool) if rival_pool else old[party]
        total = sum(new.values()) or 100.0
        for party in state.PARTIES:
            s.poll_history[party][-1] = round(new[party] / total * 100.0, 1)
        s.election_campaign_actions.append({"week": week, "action": chosen, "effect": round(swing, 2)})
        s.election_campaign_turnout = float(s.get('election_campaign_turnout', 0.0)) + float(turnout)
        s.election_campaign_approval = float(s.get('election_campaign_approval', 0.0)) + float(approval_change)
        s.approval = round(engine._clip(float(s.approval) + float(approval_change)), 1)
        s.election_campaign_strategy = chosen
        if week >= total_weeks:
            s.election_campaign_done = True
            s.message = "The four-week campaign is complete. The country now goes to the polls."
        else:
            s.election_campaign_week = week + 1
            s.message = f"Campaign week {week} complete. The next phase of the election campaign begins."
        st.rerun()
    if s.get('election_campaign_actions'):
        st.markdown("#### Campaign diary")
        for item in s.election_campaign_actions:
            st.write(f"**Week {item['week']}:** {item['action']} · polling movement {item['effect']:+.2f} pts")
    st.stop()

if s.year > 5 and s.get('election_campaign_done', False) and not s.get('election_night_started', False):
    st.markdown("# 🗳️ Election Day")
    st.markdown("### The campaign is over. The country is voting.")
    st.info(f"Your campaign strategy: **{s.get('election_campaign_strategy', 'Not recorded')}**. Polling-day turnout effect: +{s.get('election_campaign_turnout', 0):.1f} percentage points.")
    st.markdown("The result will now be calculated constituency by constituency using the final polling position, local variation and incumbency.")
    if st.button("🔔 Open the exit poll and declare the result", type="primary", use_container_width=True):
        s.election_night_started = True
        st.rerun()
    st.stop()


# ==================== ELECTION NIGHT ====================
if s.year > 5:
    r = engine.compute_election()
    if s.get('game_over'):
        st.rerun()
    # A staged broadcast: reveal the regional declarations one at a time.
    s.setdefault('election_broadcast_stage', 0)
    stage = int(s.election_broadcast_stage)
    nation_order = ['England', 'Scotland', 'Wales', 'Northern Ireland']
    local_results = r.get('constituency_results', [])
    if stage < len(nation_order):
        st.markdown("# 🗳️ ELECTION NIGHT LIVE")
        st.caption("The national count is under way · Results are declared in stages")
        st.markdown(f"## Declaration {stage + 1} of {len(nation_order)}")
        st.markdown(f"### {nation_order[stage]} results")
        for prior_nation in nation_order[:stage]:
            rows = [row for row in local_results if row.get('nation') == prior_nation]
            tally = {p: sum(1 for row in rows if row.get('winner') == p) for p in state.PARTIES}
            declared = len(rows)
            leading = max(tally, key=tally.get) if declared else "No declarations"
            st.success(f"**{prior_nation}:** {declared} seats declared · largest party: **{leading}**")
            st.caption(" · ".join(f"{p} {n}" for p, n in sorted(tally.items(), key=lambda item: item[1], reverse=True) if n))
        current_rows = [row for row in local_results if row.get('nation') == nation_order[stage]]
        current_tally = {p: sum(1 for row in current_rows if row.get('winner') == p) for p in state.PARTIES}
        declared = len(current_rows)
        leader = max(current_tally, key=current_tally.get) if declared else "No declarations"
        st.markdown(f"**{declared} constituencies declared**")
        st.metric("Leading party in this declaration", leader, f"{current_tally.get(leader, 0)} seats")
        if current_rows:
            close = sorted(current_rows, key=lambda row: float(row.get('margin', 999)), reverse=False)[:3]
            st.markdown("**Closest contests in this region**")
            for row in close:
                st.write(f"• {row.get('name', 'Constituency')} — {row.get('winner', 'Unknown')} holds/wins by {float(row.get('margin', 0)):.1f} points")
        st.info("National seat tally is being held back until the regional declarations are complete. The count is modelled for gameplay; it is not a live or official forecast.")
        if st.button(f"Declare {nation_order[stage]} results", type="primary", use_container_width=True):
            s.election_broadcast_stage = stage + 1
            st.rerun()
        st.stop()
    st.markdown("# 🗳️ GENERAL ELECTION NIGHT")
    st.caption(f"National broadcast · Campaign: {s.get('election_campaign_strategy', '—')} · Turnout {r.get('turnout', 65.0):.1f}%")
    st.markdown("### The regional declarations are complete. Here is the national result.")
    st.caption(f"Official simulated count · Campaign: {s.get('election_campaign_strategy', '—')} · Turnout includes campaign mobilisation")
    st.subheader('The results are in')
    box = '#2b5440' if r['win'] else '#111111'
    st.markdown(f"""
    <div style='background-color: {box}; padding: 20px; border-radius: 10px; color: white; text-align: center; border: 2px solid #c9a45c;'>
        <h2>{r['title']}</h2>
        <h4 style='color: #c9a45c;'>{r['gov_type']}</h4>
        <p style='font-size: 18px;'>Your Seats: <b>{r['player_seats']}</b> | Target for UK Majority: {engine.WIN_MAJORITY}</p>
    </div>""", unsafe_allow_html=True)

    st.markdown('### 🏛️ The New Parliament')
    labels = {'Labour': 'LAB', 'Conservative': 'CON', 'Liberal Democrats': 'LDEM', 'Reform UK': 'REF',
              'Green Party': 'GRN', 'SNP': 'SNP', 'Plaid Cymru': 'PC'}
    for col, party in zip(st.columns(7), state.PARTIES):
        col.metric(labels[party], r['seats'][party])
    st.markdown("### 📊 The national result")
    st.info("This is a simulated result, not a forecast. Constituency outcomes reflect the game's polling, local variation and incumbency model.")
    e1, e2, e3 = st.columns(3, gap="small")
    # Count coalition partners when displaying the government's parliamentary strength.
    coalition_partners = r.get('coalition_partners') or ([r['coalition']] if r.get('coalition') in r['seats'] else [])
    coalition_seats = sum(r['seats'].get(p, 0) for p in coalition_partners)
    government_seats = r['player_seats'] + coalition_seats
    government_majority = government_seats - engine.WIN_MAJORITY
    e1.metric("Estimated turnout", f"{r.get('turnout', 65.0):.1f}%")
    e2.metric("Government seats", f"{government_seats}/650")
    majority_label = (f"Coalition +{government_majority}" if r.get('coalition') and government_majority >= 0
                      else f"+{government_majority}" if government_majority >= 0
                      else "Hung / minority")
    e3.metric("Working majority", majority_label)
    st.markdown(f"### 🗳️ Government mandate · {r.get('mandate_label', 'Election result')}" )
    st.caption(f"The next term begins with a modelled working majority of {r.get('working_majority', 0):+d} seats. A larger majority makes it easier to pass legislation; coalition and minority governments receive a more cautious mandate.")
    election_rows = []
    for party in sorted(state.PARTIES, key=lambda p: r['seats'][p], reverse=True):
        election_rows.append({
            "Party": party,
            "Vote share": f"{r['polls'][party]:.1f}%",
            "Change": f"{r.get('swings', {}).get(party, 0):+.1f}pp",
            "Seats": r['seats'][party],
            "Seat change": (f"{r.get('seat_changes', {}).get(party, 0):+d}" if r.get('seat_changes') and s.get('term', 1) > 1 else "—"),
        })
    st.dataframe(pd.DataFrame(election_rows), hide_index=True, use_container_width=True)
    vote_total = sum(r['polls'].values())
    st.caption(f"Vote shares are normalised to {vote_total:.1f}%. The UK uses first-past-the-post: seats depend on constituency-level pluralities, not national vote share alone.")
    # Constituency-level result: every seat is decided independently by the
    # simulated local vote model, with a nation-by-nation breakdown.
    local_results = r.get('constituency_results', [])
    if local_results:
        st.markdown("### 🗺️ Constituency results")
        nation_order = ['England', 'Scotland', 'Wales', 'Northern Ireland']
        nation_columns = st.columns(4)
        for col, nation in zip(nation_columns, nation_order):
            nation_rows = [row for row in local_results if row.get('nation') == nation]
            counts = {}
            for row in nation_rows:
                counts[row['winner']] = counts.get(row['winner'], 0) + 1
            leading = max(counts, key=counts.get) if counts else '—'
            col.metric(nation, f"{len(nation_rows)} seats", f"{leading} leads" if counts else "No results")
        with st.expander("Explore all 650 constituency results"):
            local_frame = pd.DataFrame(local_results)
            if not local_frame.empty:
                nation_filter = st.selectbox("Filter by nation", ["All nations"] + nation_order, key="election_nation_filter")
                party_filter = st.selectbox("Filter by winning party", ["All parties"] + state.PARTIES, key="election_party_filter")
                if nation_filter != "All nations":
                    local_frame = local_frame[local_frame["nation"] == nation_filter]
                if party_filter != "All parties":
                    local_frame = local_frame[local_frame["winner"] == party_filter]
                st.dataframe(local_frame.rename(columns={
                    "name": "Constituency", "nation": "Nation", "winner": "Winning party",
                    "margin": "Modelled lead (pp)"
                }), hide_index=True, use_container_width=True)
        st.caption("Constituency winners use simulated local voting leanings, not historical constituency vote totals.")
    if r.get('coalition'):
        partner_text = ' + '.join(coalition_partners)
        st.success(f"Coalition majority: {r['player_seats']} {s.party} MPs + {coalition_seats} partner MPs ({partner_text}) = {government_seats} seats. That is {government_majority} above the 326-seat majority threshold.")
    elif r['player_seats'] < engine.WIN_MAJORITY and r['win']:
        st.warning("Minority government: you remain in office but need support from other parties on confidence and supply.")
    elif not r['win']:
        st.error(f"The largest party is {max(r['seats'], key=r['seats'].get)}. You do not have the numbers to remain in government.")
    st.divider()

    extra = ('Managing a coalition partner will be tedious' if r['coalition'] else
             'A minority government will be a legislative nightmare' if r['kind'] == 'minority' else
             'The numbers are in your favour')
    humphrey_message(f"Congratulations, Chancellor. We have survived the electorate. {extra}, but you remain at the Treasury.")
    boost = round(min(15.0, max(5.0, r['margin'] / 10.0)), 1)
    st.success(f"**YOU SURVIVED!** You retained power.\n\n🎉 **HONEYMOON PERIOD:** +**{boost}%** to Public Approval and all Political Capital if you continue.")
    scorecard_block()
    st.markdown("### 📺 Reactions from the party leaders")
    largest_party = max(r['seats'], key=r['seats'].get)
    for party in sorted(state.PARTIES, key=lambda p: r['seats'][p], reverse=True)[:3]:
        if party == s.party and r['win']:
            reaction = "The party celebrates the result and promises to deliver its programme."
        elif party == largest_party:
            reaction = "The leader claims a mandate to form the next government and begins consultations."
        elif r['seats'][party] >= 50:
            reaction = "The leader says the result gives the party a stronger voice in the new Parliament."
        else:
            reaction = "The leader acknowledges a difficult night and promises to reflect on the result."
        st.write(f"**{party}:** {reaction}")
    st.markdown("### 🏛️ Government formation")
    if r.get('kind') == 'coalition':
        partners = ' + '.join(r.get('coalition_partners', []))
        st.warning(f"Hung Parliament: negotiations are required with **{partners}**. A coalition agreement would need policy compromises and a shared programme.")
        st.caption("In this simulator the coalition is modelled as a viable parliamentary agreement; detailed ministerial portfolios and policy bargaining are simplified.")
    elif r.get('kind') == 'minority':
        st.warning("You can attempt to govern as a minority administration, but confidence votes and the Budget will be difficult.")
    elif r.get('win'):
        st.success("Your party has secured a Commons majority. The next administration can proceed with its mandate.")
    else:
        st.error("You have not secured a viable government. Your administration ends after the result.")
    if st.button('Confirm result and continue as Chancellor', type='primary', disabled=not r['win']):
        engine.continue_term()
        st.rerun()
    st.stop()


# ==================== BUDGET ====================
def lords_memo():
    lords_ayes = min(750, max(0, int(200 + s.approval * 2.5)))
    lords_noes = 750 - lords_ayes
    if s.approval < 40:
        humphrey_message(f"As for the House of Lords, Chancellor, they actually voted against us (<b>{lords_noes} Not-Contents</b> to {lords_ayes} Contents). "
                         "I reminded them of the Parliament Act of 1911. They cannot reject a Money Bill. However, seeing your dismal poll numbers, "
                         "they decided to delay it for a month just to be difficult. The markets were briefly irritated.")
    else:
        humphrey_message(f"As for the House of Lords, Chancellor, they supported the bill (<b>{lords_ayes} Contents</b> to {lords_noes} Not-Contents). "
                         "Though even if they hadn't, the Parliament Act of 1911 means they cannot vote down a Money Bill. The constitution is a wonderful thing.")


def budget_day_scorecard(draft, heading="Budget impact & announcements"):
    """Readable, live summary of the draft using the same calculations as delivery."""
    old = s.get('budget_applied') or budget.defaults()
    impact = budget.impact(old, draft)
    old_revenue, old_spending = budget.totals(old)
    new_revenue, new_spending = budget.totals(draft)

    st.markdown(f"### {heading}")
    st.caption("Illustrative game estimates against the last delivered Budget. Figures are not official OBR costings.")
    cols = st.columns(4)
    cols[0].metric("Annual receipts", f"£{new_revenue:,.1f}bn", f"£{new_revenue-old_revenue:+,.1f}bn")
    cols[1].metric("Annual spending", f"£{new_spending:,.1f}bn", f"£{new_spending-old_spending:+,.1f}bn")
    cols[2].metric("Fiscal headroom impact", f"£{impact['headroom']:+,.1f}bn")
    cols[3].metric("Market confidence impact", f"{impact['market']:+.1f} pts")

    cols2 = st.columns(4)
    cols2[0].metric("Growth impact", f"{impact['growth']:+.2f}pp")
    cols2[1].metric("Inflation impact", f"{impact['inflation']:+.2f}pp")
    cols2[2].metric("Real-wage impact", f"{impact['real_wages']:+.2f}")
    cols2[3].metric("Unemployment pressure", f"{impact['unemployment']:+.2f}")

    announcements = []
    for key, spec in budget.TAXES.items():
        before = float(old.get('tax', {}).get(key, spec.get('default', 0.0)))
        after = float(draft.get('tax', {}).get(key, spec.get('default', 0.0)))
        delta = after - before
        if abs(delta) >= 0.001:
            unit = spec.get('unit', 'percentage points')
            announcements.append({"Announcement": f"Tax · {spec.get('short', key)}", "Change": f"{delta:+.2f} {unit}"})
    old_thresholds = old.get('thresholds', {})
    new_thresholds = draft.get('thresholds', {})
    threshold_labels = {
        'personal_allowance': 'Personal allowance',
        'higher_rate_threshold': 'Higher-rate threshold',
        'additional_rate_threshold': 'Additional-rate threshold',
        'inheritance_nil_rate_band': 'Inheritance tax nil-rate band',
        'vat_registration_threshold': 'VAT registration threshold',
    }
    for key, label in threshold_labels.items():
        before = float(old_thresholds.get(key, {'personal_allowance':12570,'higher_rate_threshold':50270,'additional_rate_threshold':125140,'inheritance_nil_rate_band':325000,'vat_registration_threshold':90000}[key]))
        after = float(new_thresholds.get(key, before))
        if abs(after - before) >= 0.001:
            announcements.append({"Announcement": f"Tax threshold · {label}", "Change": f"£{before:,.0f} → £{after:,.0f}"})
    for key, label in (('thresholds_frozen', 'Freeze income-tax thresholds'), ('council_tax_revaluation', 'Revalue council tax bands')):
        before, after = bool(old_thresholds.get(key, False)), bool(new_thresholds.get(key, False))
        if before != after:
            announcements.append({"Announcement": label, "Change": "Introduced" if after else "Withdrawn"})
    for key, spec in budget.SPEND_DEFAULTS.items():
        before = float(old.get('spend', {}).get(key, 0.0))
        after = float(draft.get('spend', {}).get(key, 0.0))
        delta_pct = after - before
        if abs(delta_pct) >= 0.001:
            annual = float(s.dept_spend.get(key, 0.0)) * delta_pct / 100.0
            announcements.append({"Announcement": f"Spending · {spec.get('label', key)}", "Change": f"{delta_pct:+.1f}% · £{annual:+.2f}bn"})
    for kind, table, label in (
        ("tax_pol", budget.TAX_POLICIES, "New tax measure"),
        ("spend_pol", budget.SPEND_POLICIES, "New spending commitment"),
    ):
        for key, selected in draft.get(kind, {}).items():
            if selected and not old.get(kind, {}).get(key, False) and key in table:
                announcements.append({"Announcement": label, "Change": table[key].get("label", key)})
    if announcements:
        with st.expander(f"Individual Budget announcements · {len(announcements)} changes", expanded=True):
            st.dataframe(pd.DataFrame(announcements), hide_index=True, use_container_width=True)
    else:
        st.info("No tax rates, departmental settlements or new schemes have changed from the previous Budget.")
    return impact


def budget_screen():
    stage = int(s.get('budget_day_stage', 0))
    if s.get('budget_passed'):
        left, right = st.columns([3, 2], gap='large')
        with left:
            st.markdown("<div class='pane-title'>Parliamentary vote</div>", unsafe_allow_html=True)
            ayes = s.get('vote_ayes') or budget.commons_ayes()
            txt = f'**Ayes:** {ayes} | **Noes:** {650 - ayes}'
            if ayes >= budget.WIN + 40: st.success(f'**House of Commons:** The Budget passed with a thumping majority!\n\n{txt}')
            elif ayes >= budget.WIN + 15: st.info(f'**House of Commons:** The Budget passed.\n\n{txt}')
            else: st.warning(f'**House of Commons:** The Budget barely scraped through!\n\n{txt}')
            speech_data=s.get('budget_speech') or {}
            st.markdown("#### Budget speech")
            if speech_data.get('text'): st.markdown('> '+speech_data['text'])
            st.markdown("#### The Budget Day timeline")
            for clock,title,detail in speech_data.get('budget_day',[]): st.markdown(f"**{clock} · {title}**  \n{detail}")
            st.markdown("#### Opposition amendments")
            for item in speech_data.get('amendments',[]): st.markdown(f"**{item['title']}** — {item['detail']}  \nAyes: {item['ayes']} · Noes: {650-item['ayes']} · {item['result']}")
            risk=s.get('budget_risk_outcome') or {}
            if risk: st.warning(f"**Treasury implementation surprise: {risk.get('title','Delivery risk')}** — {risk.get('detail','')}")
            move=float(speech_data.get('market_move',0))
            st.metric("Opening 10-year gilt yield",f"{float(speech_data.get('market_after',s.gilt_yield)):.2f}%",f"{move:+.2f} percentage points")
            for who,quote in speech_data.get('reactions',[]): st.write(f"**{who}:** {quote}")
            if st.button('Proceed to Spring',type='primary'):
                engine.proceed_to_spring(); st.rerun()
        with right:
            st.markdown("#### The morning after")
            for ev in s.event_cards: event_card(ev['title'],ev['text'],ev['summary'])
            lords_memo()
            if s.get('headlines'): render_newspapers(*s.headlines)
        return

    st.markdown(f"<div class='dc-eyebrow'>Year {s.year} · Phase 3 · Spring Budget</div><div class='dc-title'>The Chancellor's Budget</div>", unsafe_allow_html=True)
    budget.ensure()
    stages=['Number 10 negotiations','OBR forecast','Budget speech','Commons vote & markets']
    st.progress(min(stage,3)/3, text=f"Budget Day · Stage {min(stage+1,4)} of 4: {stages[min(stage,3)]}")
    if stage == 0:
        with st.expander("Number 10 · private Budget negotiations", expanded=False):
            st.caption("The Prime Minister's political priorities are requests, not automatic changes to your fiscal plan. You remain the Chancellor and retain control of the Budget.")
            priorities = s.get('budget_pm_priorities', [])
            if priorities:
                pcols = st.columns(min(2, len(priorities)), gap="small")
                for idx, item in enumerate(priorities, 1):
                    with pcols[(idx - 1) % len(pcols)]:
                        st.markdown(f"**{idx}. {item['title']}**")
                        st.caption(item['detail'])
            st.info("Choose whether to accept, compromise or stand firm. This affects the PM relationship and political atmosphere, not the Budget arithmetic.")
            choices = ["Accept the Prime Minister’s priorities","Compromise with the Prime Minister","Stand firm on the Treasury plan"]
            current_choice = s.get('budget_pm_choice','Compromise with the Prime Minister')
            s.budget_pm_choice=st.radio("Negotiating position", choices, index=choices.index(current_choice) if current_choice in choices else 1, horizontal=True)
            st.markdown("**Number 10 assessment of your current draft**")
            live_assessment = budget.assess_pm_priorities()
            assessment_cols = st.columns(min(2, max(1, len(live_assessment))), gap="small")
            for idx, item in enumerate(live_assessment):
                with assessment_cols[idx % len(assessment_cols)]:
                    (st.success if item['met'] else st.warning)(f"**{'Met' if item['met'] else 'Not yet met'} · {item['title']}**")
                    st.caption(item['detail'])
        def submit():
            if st.button("Conclude negotiations",type="primary",use_container_width=True):
                thresholds = budget.read().get('thresholds', {})
                if (float(thresholds.get('personal_allowance', 12570)) >= float(thresholds.get('higher_rate_threshold', 50270))
                        or float(thresholds.get('higher_rate_threshold', 50270)) >= float(thresholds.get('additional_rate_threshold', 125140))):
                    st.error("The Budget cannot proceed: income-tax thresholds must be ordered from personal allowance to higher-rate and additional-rate thresholds.")
                else:
                    s.budget_day_draft = budget.read()
                    engine.submit_budget(); st.rerun()
        budget.render(submit=submit,after_summary=lambda: politics.render_pledges(budget.read()))
        st.caption(f"{sum(1 for item in live_assessment if item['met'])} of {len(live_assessment)} priorities currently met. This assessment updates as you change the Budget.")

    elif stage == 1:
        st.markdown("### Review your Budget before the OBR forecast")
        st.info(s.get('budget_day_negotiation',''))
        draft = s.get('budget_day_draft') or budget.read()
        budget_day_scorecard(draft, "Your negotiated Budget draft")
        if draft == s.get('budget_applied'):
            st.warning("This draft is identical to your last delivered Budget. Your tax rates, departmental percentages or policy programmes have not changed. Return to the controls if you intended to make changes.")
        else:
            st.success("Your draft contains changes. They are not enacted yet; they will take effect only after the Budget passes the Commons.")
        back_col, next_col = st.columns(2)
        if back_col.button("← Return to Budget controls", use_container_width=True):
            s.budget_day_stage = 0; st.rerun()
        if next_col.button("Receive the OBR forecast",type="primary",use_container_width=True):
            engine.submit_budget(); st.rerun()
    elif stage == 2:
        st.markdown("### The Chancellor prepares the statement")
        draft_budget = budget.read()
        draft_budget = s.get('budget_day_draft') or draft_budget
        budget_day_scorecard(draft_budget, "The Budget at a glance")
        rows=s.get('budget_day_forecast') or []
        if rows:
            st.markdown("#### Three-year economic and fiscal outlook")
            forecast_frame = pd.DataFrame(rows)
            visible = [c for c in ("year", "growth", "inflation", "headroom", "deficit", "debt", "gilt", "debt_interest") if c in forecast_frame.columns]
            st.dataframe(forecast_frame[visible],hide_index=True,use_container_width=True)
            if len(rows) >= 3:
                first, last = rows[0], rows[-1]
                st.caption(f"By {last.get('year', 'year three')}, projected headroom is £{float(last.get('headroom', 0)):.1f}bn and growth is {float(last.get('growth', 0)):.1f}%. This is a central gameplay scenario, not a guarantee.")
        st.caption("The forecast reflects the current draft and simplified model assumptions. You can still return to the Budget controls and revise the package before delivering it.")
        if st.button("← Return to Budget controls", use_container_width=True):
            s.budget_day_stage = 0; st.rerun()
        if st.button("Prepare the Budget speech",type="primary"):
            engine.submit_budget(); st.rerun()
    elif stage == 3:
        st.markdown("### Deliver the Budget to Parliament")
        draft=s.get('budget_day_speech') or {}
        if draft.get('text'):
            st.markdown("> "+draft['text'])
        final_draft = s.get("budget_day_draft") or budget.read()
        budget_day_scorecard(final_draft, "Final Budget announcement sheet")
        st.warning("Once delivered, the Budget is put to the Commons. A failed vote ends the Chancellor’s career.")
        if st.button("← Return to Budget controls", use_container_width=True):
            s.budget_day_stage = 0; st.rerun()
        if st.button("Deliver Budget & open the markets",type="primary"):
            engine.submit_budget(); st.rerun()


# ==================== DECISIONS & CRISES ====================
def crisis_screen():
    crisis = scen.get(s.active_crisis)
    if crisis is None:
        s.active_crisis = None
        st.rerun()
    st.markdown(
        f"<div class='briefing-kicker'><span class='briefing-alert-dot'></span> COBRA · EMERGENCY DECISION</div><div class='briefing-heading'>{crisis['title']}</div>",
        unsafe_allow_html=True,
    )
    if s.get('crisis_reason'):
        st.markdown(f"<div class='briefing-context'>{s.crisis_reason}</div>", unsafe_allow_html=True)
    humphrey_message(crisis['humphrey'])
    labels = scen.option_labels(crisis)
    st.markdown("<div class='choice-instruction'>SELECT YOUR RESPONSE <span>One decision · Consequences may be immediate or delayed</span></div>", unsafe_allow_html=True)
    with st.container(key='policy_options'):
        choice = st.radio('Choose emergency response:', labels, index=None, key=f'crisis_{s.steps}', label_visibility='collapsed')
    if choice is not None:
        st.markdown(f"<div class='choice-confirm'><span>SELECTED RESPONSE</span><strong>{choice}</strong><small>Confirm to put this emergency measure into effect.</small></div>", unsafe_allow_html=True)
    if st.button('Authorise emergency response', type='primary', disabled=choice is None, use_container_width=True):
        engine.resolve_crisis(labels.index(choice))
        st.rerun()



def pm_meeting_screen():
    meeting=s.get("active_pm_meeting") or {}
    st.markdown("<div class='briefing-kicker'>NUMBER 10 · PRIVATE MEETING</div><div class='briefing-heading'>A conversation with the Prime Minister</div>",unsafe_allow_html=True)
    st.markdown(f"**{meeting.get('topic','Private meeting')}**")
    st.write(meeting.get("prompt","The Prime Minister has asked to discuss the direction of the Government."))
    humphrey_message(meeting.get("pm","The Prime Minister is waiting for your response, Chancellor."))
    st.markdown("### How will you handle it?")
    options=[
      ("support","Back the Prime Minister","Build trust and Cabinet unity, but you may have to accept political commitments."),
      ("compromise","Negotiate a compromise","Balance Number 10's priorities with the Treasury's judgement."),
      ("stand","Defend the Treasury's position","Protect your independence and fiscal credibility, but risk damaging the relationship.")
    ]
    for key,title,detail in options:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(detail)
            if st.button("Confirm position",key=f"pm_meeting_{key}",type="primary" if key=="compromise" else "secondary",use_container_width=True):
                engine.resolve_pm_meeting(key)
                st.rerun()


def pm_ultimatum_screen():
    ultimatum=s.get("active_pm_ultimatum") or {}
    st.markdown("<div class='briefing-kicker'><span class='briefing-alert-dot'></span> NUMBER 10 · PRIVATE MEETING</div><div class='briefing-heading'>The Prime Minister's ultimatum</div>",unsafe_allow_html=True)
    st.error("The Prime Minister has told you that confidence in your handling of the economy has collapsed. Your position as Chancellor is no longer secure.")
    st.markdown(f"**PM confidence:** {float(ultimatum.get('pm_opinion',s.get('pm_opinion',0))):.0f}/100")
    humphrey_message("Chancellor, the Prime Minister has been quite direct. They want to know whether you intend to offer your resignation. I would advise choosing your words very carefully.")
    st.markdown("### You must decide")
    with st.container(border=True):
        st.markdown("**Tender your resignation**")
        st.caption("Leave the Treasury with immediate effect. Your career as Chancellor ends, but you avoid being publicly dismissed.")
        if st.button("Offer my resignation",type="secondary",use_container_width=True):
            engine.resolve_pm_ultimatum(0)
            st.rerun()
    with st.container(border=True):
        st.markdown("**Refuse to resign and fight for your position**")
        st.caption("You need sufficient Cabinet or PM support to survive. If you lack it, the PM will dismiss you.")
        if st.button("Refuse to resign",type="primary",use_container_width=True):
            engine.resolve_pm_ultimatum(1)
            st.rerun()


def gilt_emergency_screen():
    emergency=s.get("active_gilt_emergency") or {}
    st.markdown("<div class='briefing-kicker'><span class='briefing-alert-dot'></span> TREASURY · EMERGENCY MEETING</div><div class='briefing-heading'>The gilt market is in crisis</div>",unsafe_allow_html=True)
    bid=float(emergency.get('bid_cover',0)); move=float(emergency.get('yield_move_pp',0))
    severe=emergency.get('severity')=="severe"
    pressure=bool(emergency.get('pm_pressure'))
    st.error(f'The latest DMO auction attracted only {bid:.2f} bids for every £1 of debt offered. Yields jumped {move:.2f} percentage points.')
    if severe:
        st.warning("This is a severe market event. The Prime Minister has called an urgent meeting with the Cabinet and is demanding visible action.")
    elif pressure:
        st.warning("The Prime Minister is losing patience with the Treasury and wants a clear plan before the markets open again.")
    else:
        st.info("The Prime Minister is concerned but has not yet issued an ultimatum. Your handling of this meeting will shape the relationship.")
    humphrey_message("Chancellor, the markets have delivered their verdict. Number 10 is waiting on the telephone, the Treasury Board is assembled, and the press has already discovered the word crisis.")
    st.markdown("### Choose your response")
    st.caption("Each option trades off fiscal credibility, political support and market confidence.")
    choices=[("Announce immediate spending restraint","Improve headroom and reassure investors, but anger public services and backbench MPs."),("Ask the Prime Minister for a united statement","Gain political cover and modestly steady markets, without major fiscal changes."),("Call an emergency Budget","Announce a limited consolidation package and promise revised forecasts. Markets may settle, but the PM faces another Budget.")]
    if pressure:
        choices.append(("Accept the Prime Minister's conditions","Make a costly political concession to restore Number 10's confidence and avoid an immediate leadership confrontation."))
    for i,(title,detail) in enumerate(choices):
        with st.container(border=True):
            st.markdown(f"**{i+1}. {title}**")
            st.caption(detail)
            if st.button("Choose this response",key=f"gilt_emergency_{i}",type="primary" if i==2 else "secondary",use_container_width=True):
                engine.resolve_gilt_emergency(i)
                st.rerun()

def financial_crisis_screen():
    crisis=s.get("active_financial_crisis") or {}
    stress=float(crisis.get("stress",100.0))
    severe=crisis.get("severity")=="severe"
    st.markdown("<div class='briefing-kicker'><span class='briefing-alert-dot'></span> TREASURY · FINANCIAL STABILITY COMMITTEE</div><div class='briefing-heading'>Credit markets are under pressure</div>",unsafe_allow_html=True)
    st.error(f"Financial stability has fallen to {float(s.get('financial_stability',100.0)):.1f}/100. Credit spreads are around {float(s.get('credit_spread_bps',0)):.0f} basis points.")
    if severe:
        st.warning("The stress is severe. Banks are restricting lending, investors are nervous and the Prime Minister wants an immediate plan.")
    else:
        st.warning("The Bank and Treasury are monitoring deteriorating credit conditions. A decisive response may prevent a wider crisis.")
    humphrey_message("Chancellor, this is no longer just a matter of gilt traders having a difficult morning. Credit is tightening across the economy. We need to decide whether the taxpayer, the Bank, or private investors should carry the burden.")
    st.markdown("### Choose the Treasury response")
    choices=[("Introduce a temporary deposit guarantee","Cost: £3bn. Reassure depositors and prevent panic, while creating a contingent fiscal exposure."),("Provide a capital backstop for key lenders","Cost: £7bn. Strongest stabilisation option; protects lending but uses fiscal headroom."),("Coordinate a Bank-led liquidity response","No direct fiscal outlay. The Bank leads on liquidity; monetary policy remains independent."),("Allow a private-sector-led resolution","No immediate taxpayer rescue. Risks a deeper credit squeeze and weaker growth.")]
    for i,(title,detail) in enumerate(choices):
        with st.container(border=True):
            st.markdown(f"**{i+1}. {title}**")
            st.caption(detail)
            if st.button("Choose this response",key=f"financial_crisis_{i}",type="primary" if i==2 else "secondary",use_container_width=True):
                economic_management.resolve_financial_crisis(i)
                st.rerun()


def request_screen():
    req = s.active_request
    st.markdown(f"<div class='dc-eyebrow'>Urgent request</div><div class='dc-title'>From the {req['minister']}</div>", unsafe_allow_html=True)
    st.info(req['text'])
    humphrey_message('A Cabinet colleague with their hand out, Chancellor. Refuse, and they will remember it. '
                     'Approve, and every other minister will notice that you can be persuaded.')
    c1, c2, _ = st.columns([1, 1, 2])
    with c1:
        if st.button(f"Approve (-£{req['cost']:.1f}B headroom)", type='primary'):
            engine.resolve_request(True)
            st.rerun()
    with c2:
        if st.button('Refuse Request'):
            engine.resolve_request(False)
            st.rerun()



def weekly_event_screen():
    event = s.get('active_weekly_event') or {}
    st.markdown(f"<div class='briefing-kicker'>WEEKLY TREASURY BRIEFING · {event.get('category', 'Government')}</div><div class='briefing-heading'>{event.get('title', 'An unexpected development')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='briefing-context'>{event.get('text', '')}</div>", unsafe_allow_html=True)
    humphrey_message("An awkward development, Chancellor. None of these options is entirely painless. The consequences will be felt in the Treasury and beyond.")
    options = event.get('options', [])
    labels = [item[0] for item in options]
    choice = st.radio("Choose your response:", labels, index=None, key=f"weekly_event_{s.steps}", label_visibility="collapsed")
    if choice is not None:
        st.caption(options[labels.index(choice)][2])
    if st.button("Confirm response", type="primary", disabled=choice is None, use_container_width=True):
        engine.resolve_weekly_event(labels.index(choice))
        st.rerun()


def ministerial_dispute_screen():
    dispute = s.get('active_dispute') or {}
    minister = dispute.get('minister', 'Cabinet minister')
    st.markdown("<div class='dc-eyebrow'>Cabinet confrontation</div><div class='dc-title'>A minister is threatening to go public</div>", unsafe_allow_html=True)
    st.warning(dispute.get('text', 'A Cabinet minister is challenging the Treasury.'))
    st.metric("Ministerial loyalty", f"{float(dispute.get('loyalty', 35)):.0f}/100")
    humphrey_message("A Cabinet row is the last thing the Government needs, Chancellor. You can buy peace, hold the line, or let the disagreement spill into public.")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1:
        st.markdown("**Offer a compromise**")
        st.caption(f"Concede half the original request (£{float(dispute.get('cost', 1.0)) * 0.5:.1f}B). Restore some Cabinet support.")
        if st.button("Negotiate a settlement", key="dispute_compromise", type="primary", use_container_width=True):
            engine.resolve_ministerial_dispute('compromise')
            st.rerun()
    with c2:
        st.markdown("**Stand firm**")
        st.caption("Protect the fiscal position, but risk losing the minister's support.")
        if st.button("Reject the demand", key="dispute_stand", use_container_width=True):
            engine.resolve_ministerial_dispute('stand_firm')
            st.rerun()
    with c3:
        st.markdown("**Let them go public**")
        st.caption("Refuse further concessions. Expect damaging headlines and a possible resignation.")
        if st.button("Hold your ground publicly", key="dispute_public", use_container_width=True):
            engine.resolve_ministerial_dispute('public')
            st.rerun()


def decision_screen():
    decision = engine.current_decision()
    if not decision:
        st.write('No decision data found for this block.')
        return
    options = engine.current_options()
    title = decision['title']
    phase = phase_info(s.block)
    st.markdown(f"<div class='briefing-kicker'>CABINET OFFICE · POLICY SUBMISSION <span>YEAR {s.year} / PHASE {s.block}</span></div><div class='briefing-heading'>{title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='briefing-context'>{decision['text']}</div>", unsafe_allow_html=True)
    humphrey_message(decision['humphrey'])
    features.render_phase_action()
    labels = [o['label'] for o in options]
    st.markdown("<div class='decision-section-head'><span>THE CABINET OPTIONS</span><small>Five competing approaches · Select one to open its assessment</small></div>", unsafe_allow_html=True)
    with st.container(key='policy_options'):
        choice = st.radio('Select policy approach:', labels, index=None, key=f'dec_{s.term}_{s.year}_{s.block}',
                          label_visibility='collapsed',
                          help='Each approach has different economic, political and delivery trade-offs.')
    if choice is not None:
        selected = options[labels.index(choice)]
        assessment = engine.assess_decision(selected)
        effect_text = state.fmt_fx(selected.get('effect', {}))
        st.markdown("<div class='decision-brief-label'>TREASURY & CABINET ASSESSMENT</div>", unsafe_allow_html=True)
        with st.container(key='decision_brief', border=True):
            st.markdown(f"**{choice}**")
            m1, m2, m3 = st.columns(3, gap='small')
            m1.metric("Delivery confidence", f"{assessment['confidence']:.0%}", help="A live estimate based on Cabinet support, party discipline, market confidence and fiscal headroom.")
            m2.metric("Projected Commons", f"{assessment['projected_ayes']}/650", help="A bill needs 326 votes to pass. 346 votes is treated as a clear passage.")
            m3.metric("Likely vote", assessment['vote_label'])
            st.caption("MODELLED POLICY EFFECTS · Before delivery and Commons adjustments")
            st.markdown(f"<div class='decision-impact'>{effect_text or 'No immediate numerical effect is listed.'}</div>", unsafe_allow_html=True)
            st.markdown("**Delivery risks & constraints**")
            for risk in assessment['risks']:
                st.markdown(f"- {risk}")
            delayed = selected.get('delayed')
            if delayed:
                st.markdown(f"**Later consequence — {delayed.get('title', 'Follow-up event')}**")
                st.caption(f"{delayed.get('text', 'A later consequence may follow.')} Expected timing: about {delayed.get('after', 1)} action(s) later.")
            st.caption(f"Estimated combined implementation: {assessment['combined_factor']:.0%}. The final result depends on the Commons vote and your government's ability to deliver.")
        st.markdown("<div class='decision-authority'>DECISION PENDING · Your selection has no effect until authorised.</div>", unsafe_allow_html=True)
    with st.container(key='decision_authorise'):
        if st.button('Take this decision to Cabinet & Commons', type='primary', disabled=choice is None, use_container_width=True):
            engine.execute_decision(options[labels.index(choice)])
            st.rerun()


def briefing():
    """What just happened (the feedback loop of the game) plus the full timeline, in one place."""
    if s.event_cards or s.get('message') or s.get('humphrey_note') or s.get('headlines'):
        for ev in s.event_cards:
            event_card(ev['title'], ev['text'], ev['summary'])
        if s.get('message'):
            news_box(s.message)
        if s.get('humphrey_note'):
            humphrey_message(s.humphrey_note, title='Sir Humphrey on your last decision')
        if s.get('headlines'):
            render_newspapers(*s.headlines)
    else:
        st.info('No new briefings yet. Headlines and consequences will appear here after decisions.')
    with st.expander('Decision history', expanded=False):
        render_timeline(s.history, sorted(s.pending, key=lambda p: p['due']))


def economy():
    """State of the nation and the IMF baseline."""
    gdp = float(s.get('gdp_trillion', 3.0))
    nominal_growth = ((1 + float(s.growth) / 100.0) * (1 + float(s.inflation) / 100.0) - 1) * 100
    g1, g2, g3 = st.columns(3)
    g1.metric('Estimated GDP', f'£{gdp:.3f} trillion',
              help='A simulated starting estimate, updated each in-game spring using real growth and inflation. Not a live official statistic.')
    g2.metric('Real GDP growth', f'{float(s.growth):+.2f}%')
    g3.metric('Nominal GDP growth', f'{nominal_growth:+.2f}%',
              help='Approximate growth in the money value of output, including inflation. GDP figures are gameplay estimates, not live forecasts.')
    shock = s.get('temporary_shock') or {}
    if shock:
        st.warning(f"Temporary shock in play: **{shock.get('label', 'Global disruption')}** — about {shock.get('years_left', 0)} annual tick(s) remaining.")

    st.markdown('#### Global economy')
    st.caption('Cumulative real growth since you took office. Output index starts at 100; GDP values are illustrative game estimates.')
    world_economy.ensure(s)
    uk_index = 100.0
    for item in s.get('gdp_history', []):
        try:
            uk_index *= 1 + float(item.get('Real GDP growth (%)', 0)) / 100.0
        except (TypeError, ValueError):
            pass
    league_rows = [{
        '#': 0, 'Economy': '🇬🇧  United Kingdom  🟠 You',
        'Output idx': round(uk_index, 1), 'Growth': f'{float(s.growth):+.1f}%',
        'GDP ($tn)': round(float(s.get('gdp_trillion', 3.0)) * 1.27, 2), '_sort': uk_index
    }]
    for row in world_economy.rows(s):
        league_rows.append({
            '#': 0, 'Economy': row['Flag'] + '  ' + row['Economy'],
            'Output idx': row['Output index'], 'Growth': row['Growth'],
            'GDP ($tn)': row['GDP ($tn)'], '_sort': row['Output index']
        })
    league_rows.sort(key=lambda row: row['_sort'], reverse=True)
    for rank, row in enumerate(league_rows, 1):
        row['#'] = rank
    league = pd.DataFrame(league_rows).drop(columns=['_sort'])
    st.dataframe(league, hide_index=True, use_container_width=True,
                 column_config={
                     '#': st.column_config.NumberColumn('#', format='%d'),
                     'Output idx': st.column_config.NumberColumn('OUTPUT IDX', format='%.1f'),
                     'Growth': st.column_config.TextColumn('GROWTH'),
                     'GDP ($tn)': st.column_config.NumberColumn('GDP ($TN)', format='%.2f')
                 })
    with st.expander('Economic history'):
        if s.get('gdp_history'):
            st.caption('Your GDP over time')
            st.dataframe(pd.DataFrame(s.gdp_history), hide_index=True, use_container_width=True)
        if s.get('world_history'):
            st.caption('World economy history')
            st.dataframe(pd.DataFrame(s.world_history), hide_index=True, use_container_width=True)
        if not (s.get('gdp_history') or s.get('world_history')):
            st.caption('History builds up as the years pass.')
    with st.expander('IMF baseline and assumptions'):
        st.markdown(
            f"[{imf_outlook.IMF_SOURCE}]({imf_outlook.IMF_SOURCE_URL}) · vintage published {imf_outlook.IMF_PUBLISHED}. "
            "A fixed data-file vintage: the annual tick nudges growth and inflation towards it, but it does not forecast your playthrough."
        )
        st.caption("Debt here means general government gross debt (% of GDP), not PSNFL and not the simulator's National Debt stat.")
        st.dataframe(pd.DataFrame(imf_outlook.rows()), hide_index=True, use_container_width=True)
    country.render()
    import living_economy
    living_economy.render()


# ==================== MAIN NAVIGATION ====================
# Keep the core action visible in one place; supporting information is separated
# into compact workspaces so the player does not have to scroll through everything.
_has_briefing = bool(s.event_cards or s.get('message') or s.get('humphrey_note') or s.get('headlines'))
_is_budget_phase = (s.block == 3 and s.active_crisis is None and not s.get('active_request') and not s.get('active_dispute'))

tab_action, tab_briefing, tab_economy, tab_government, tab_treasury, tab_household, tab_regions, tab_services = st.tabs([
    'Decisions' + (' •' if _is_budget_phase else ''),
    'Briefing' + (' •' if _has_briefing else ''),
    'Economy',
    'Government',
    'Treasury',
    'Households',
    'Regions',
    'Public Services'
])

with tab_action:
    if s.get('local_election_due'):
        local_elections.render(widget_namespace='action')
    elif s.get('active_pm_ultimatum'):
        pm_ultimatum_screen()
    elif s.get('active_pm_meeting'):
        pm_meeting_screen()
    elif s.get('active_gilt_emergency'):
        gilt_emergency_screen()
    elif s.get('active_financial_crisis'):
        financial_crisis_screen()
    elif s.active_crisis is not None:
        crisis_screen()
    elif s.get('active_dispute'):
        ministerial_dispute_screen()
    elif s.get('active_weekly_event'):
        weekly_event_screen()
    elif s.get('active_request'):
        request_screen()
    elif _is_budget_phase:
        budget_screen()
    else:
        decision_screen()

with tab_briefing:
    briefing()

with tab_economy:
    economy()

with tab_government:
    st.markdown('### Government')
    st.caption('Political support, parliamentary scrutiny, local elections and your record in office.')
    gov_polls, gov_parliament, gov_local, gov_office, gov_number10, gov_reports = st.tabs(['Polling', 'Commons', 'Local', 'Chancellor’s Office', 'Number 10', 'Annual reports'])
    with gov_polls:
        if s.get('poll_history'):
            render_polls(pd.DataFrame(s.poll_history).set_index('Period'), chart_in_expander=True)
        else:
            st.info('Polling history will appear after the first update.')
    with gov_parliament:
        parliament.render()
    with gov_local:
        local_elections.render(widget_namespace='government')
    with gov_office:
        chancellor_office.render()
    with gov_number10:
        st.markdown("#### Your relationship with the Prime Minister")
        pmc=st.columns(3)
        pmc[0].metric("PM confidence",f"{float(s.pm_opinion):.0f}/100")
        pmc[1].metric("Personal trust",f"{float(s.get('pm_trust',70)):.0f}/100")
        pmc[2].metric("Cabinet support",f"{float(s.cab_opinion):.0f}/100")
        trust=float(s.get('pm_trust',70))
        if trust>=70:
            st.success("Number 10 broadly trusts you. The PM is likely to give you room to manage the economy.")
        elif trust>=45:
            st.info("The relationship is workable, but disagreements are beginning to matter.")
        elif trust>=25:
            st.warning("Relations are strained. The PM may start bypassing the Treasury or questioning your judgement.")
        else:
            st.error("The relationship is close to breaking point. A serious disagreement could put your job at risk.")
        if s.get('pm_meeting_history'):
            with st.expander("Previous Number 10 meetings"):
                st.dataframe(list(reversed(s.pm_meeting_history)),hide_index=True,use_container_width=True)
        if s.get('active_pm_meeting'):
            st.warning("A private meeting is waiting in the Decisions tab.")
        elif int(s.get('pm_meeting_year',0))>=int(s.year):
            st.caption("You have already held your private meeting with the PM this year. Another will be available next year.")
        else:
            st.caption("You can request one formal private meeting with the PM each year. The topic will reflect the political and economic pressures facing the Government.")
            if st.button("Request a private meeting with the PM",type="primary",use_container_width=True):
                engine.open_pm_meeting()
                st.rerun()
    with gov_reports:
        performance_report.render()

with tab_treasury:
    st.markdown('### Treasury')
    st.caption('Budgets, spending settlements, public investments and the cost of government borrowing.')
    treasury_tabs = st.tabs(['Spending review', 'Investments & gilts', 'Fiscal tools', 'OBR & markets', 'Local government'])
    with treasury_tabs[0]:
        budget.render_spending_review()
    with treasury_tabs[1]:
        treasury.render()
    with treasury_tabs[2]:
        features.render()
    with treasury_tabs[3]:
        economic_management.render()
    with treasury_tabs[4]:
        devolution.render()


with tab_household:
    household.render()


with tab_regions:
    regional_economy.render()


with tab_services:
    public_services.render()
