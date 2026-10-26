"""UK Chancellor Simulator (Hardcore Mode): the Streamlit UI. All game rules live in engine.py."""
import pandas as pd
import streamlit as st

import achievements
import budget
import country
import engine
import features
import imf_outlook
import politics
import scenarios as scen
import state
from state import CARDS_ECON, CARDS_POLITICAL, CARDS_TOP
from theme import (apply_theme, crisis_card, event_card, header, humphrey_message, news_box,
                   render_hud, render_newspapers, render_polls, render_scorecard, render_timeline, phase_info)

st.set_page_config(page_title='UK Chancellor Simulator - Hardcore', layout='wide', page_icon='🏛️',
                   initial_sidebar_state='collapsed')
apply_theme()
state.ensure_init()
s = st.session_state


def restart():
    s.clear()
    st.rerun()


# ==================== SIDEBAR: SAVE / NEW GAME ====================
with st.sidebar:
    st.markdown('### 💾 Game')
    if s.step == 'game':
        st.download_button('Download save file', state.export_save(), file_name=f'chancellor_{s.party.replace(" ", "")}_T{s.term}Y{s.year}.json',
                           mime='application/json', help='Save your progress and load it again from the start screen.')
        st.caption(f'{s.party} · {s.difficulty} · seed {s.seed}')
        st.caption(f"📅 {state.SCENARIOS[s.get('scenario', 'fragile')]['label']}")
        if state.diff().get('undos', 0) > 0:
            if st.button(f"↩️ Undo last action ({s.get('undos_left', 0)} left)", disabled=not state.can_undo(),
                         help='Roll back your last decision, crisis, request, Budget or spring. Same seed, so only a different choice changes what happens.'):
                if state.undo():
                    st.rerun()
        if st.button('Abandon run & start over'):
            restart()
        if s.get('spad') in politics.SPADS:
            st.markdown('### 🧑‍💼 Special Advisor')
            st.caption(f"**{politics.SPADS[s.spad]['label']}**: {politics.SPADS[s.spad]['blurb']}")
        if s.get('pledges'):
            st.markdown('### 📜 Manifesto pledges')
            for k in s.pledges:
                broken = k in s.get('broken_pledges', [])
                st.caption(f"{'❌ ~~' if broken else '✅ '}{politics.PLEDGES[k]['label']}{'~~' if broken else ''}")
    else:
        st.caption('Start a game to enable saving.')


# ==================== SETUP SCREEN ====================
def setup_screen():
    st.markdown("""<div class='setup-hero'><div class='seal'>HM Treasury · Cabinet Office Simulation</div><h1>🏛️ The Chancellor's Office</h1><p>Take the red box, manage the economy, survive Parliament and shape Britain's next five years. Every decision has a price.</p><span class='stamp'>Official business · Start a new term</span></div>""", unsafe_allow_html=True)
    st.markdown('### Step 1 · Form your government')
    party = st.selectbox('Select Governing Party:', state.PARTIES)
    difficulty = st.radio('Difficulty', list(state.DIFFICULTY), index=2, horizontal=True,
                          captions=[d['blurb'] for d in state.DIFFICULTY.values()],
                          help='Easy is forgiving; Normal is balanced; Hardcore has frequent crises and no undo.')
    c3, c4, c5 = st.columns([1.4, 1.4, 1], gap='medium')
    with c3:
        scenario = st.selectbox('Starting scenario', list(state.SCENARIOS), format_func=lambda k: state.SCENARIOS[k]['label'])
        st.caption(state.SCENARIOS[scenario]['blurb'])
    with c4:
        spad = st.selectbox('Special Advisor', [None, *politics.SPADS],
                            format_func=lambda k: 'None' if k is None else politics.SPADS[k]['label'])
        st.caption(politics.SPADS[spad]['blurb'] if spad else 'Go it alone, with no help from anyone.')
    with c5:
        seed = st.number_input('Game seed', min_value=1, max_value=999999, value=int(s.seed), step=1,
                               help='The same seed recreates the same random events, making runs comparable.')
    pledges = st.multiselect('Manifesto pledges (optional, up to 3)', list(politics.PLEDGES),
                             format_func=lambda k: politics.PLEDGES[k]['label'], max_selections=3,
                             help='Each pledge gives you +2 starting approval. Break one and you take a U-turn scandal: '
                                  'approval, media and party support all fall.')
    tags = st.checkbox('Show ideology tags on policy options',
                       value=(difficulty == 'Easy'), key=f'tags_{difficulty}',
                       help='Off by default: read the policy, not the label. Your MPs still know what is and is not '
                            "in your party's tradition.")
    if st.button('Enter Number 11', type='primary'):
        state.new_game(party, difficulty, seed, tags, scenario=scenario, spad=spad, pledges=pledges)
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
    """The small status line at the end of the dashboard strip: world cycle, advisor and pledges."""
    icon = {'Boom': '📈', 'Stagnation': '➖', 'Recession': '📉'}.get(s.get('macro_cycle'), '➖')
    bits = [f"🌍 World economy: <b>{icon} {s.get('macro_cycle', 'Stagnation')}</b>"]
    if s.get('spad') in politics.SPADS:
        bits.append(f"🧑‍💼 <b>{politics.SPADS[s.spad]['label']}</b>")
    if s.get('pledges'):
        kept = len([k for k in s.pledges if k not in s.get('broken_pledges', [])])
        bits.append(f"📜 Pledges kept: <b>{kept}/{len(s.pledges)}</b>")
    return ' '.join(f'<span>{b}</span>' for b in bits)


# On the Budget screen the economy numbers appear as the *projected* summary instead, so only political capital is shown here.
_on_budget_screen = (s.block == 3 and s.active_crisis is None and s.year <= 5 and not s.get('game_over'))
_hud = [('Political capital', CARDS_POLITICAL)]
if not _on_budget_screen:
    _hud.insert(0, ('The economy', CARDS_TOP + CARDS_ECON))
render_hud(_hud, note=hud_note())

with st.expander('🗓️ How the annual cycle works', expanded=False):
    g1, g2, g3 = st.columns(3, gap='medium')
    for col, num in zip((g1, g2, g3), (1, 2, 3)):
        phase = phase_info(num)
        with col:
            st.markdown(f"**Phase {num} · {phase['title']}**")
            st.caption(phase['guide'])
    st.caption('You get two major policy decisions per year and then a Budget vote. Political capital is limited: use it only for the interventions that matter most. The next financial year begins after the Budget passes and you proceed to spring.')


def scorecard_block(show_share=True):
    data = engine.scorecard()
    render_scorecard(data)
    if show_share:
        st.caption('Share your result:')
        st.code(data['share'], language=None)


# ==================== GAME OVER (sacked / lost / resigned) ====================
if s.get('game_over'):
    over = s.game_over
    if over['kind'] == 'sacked':
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


# ==================== ELECTION NIGHT ====================
if s.year > 5:
    r = engine.compute_election()
    if s.get('game_over'):
        st.rerun()
    st.subheader('🗳️ GENERAL ELECTION NIGHT: RESULTS')
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
    st.divider()

    extra = ('Managing a coalition partner will be tedious' if r['coalition'] else
             'A minority government will be a legislative nightmare' if r['kind'] == 'minority' else
             'The numbers are in your favour')
    humphrey_message(f"Congratulations, Chancellor. We have survived the electorate. {extra}, but you remain at the Treasury.")
    boost = round(min(15.0, max(5.0, r['margin'] / 10.0)), 1)
    st.success(f"**YOU SURVIVED!** You retained power.\n\n🎉 **HONEYMOON PERIOD:** +**{boost}%** to Public Approval and all Political Capital if you continue.")
    scorecard_block()
    if st.button('Continue as Chancellor', type='primary'):
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


def budget_screen():
    if s.get('budget_passed'):
        left, right = st.columns([3, 2], gap='large')
        with left:
            st.markdown("<div class='pane-title'>Parliamentary vote</div>", unsafe_allow_html=True)
            ayes = s.get('vote_ayes') or budget.commons_ayes()
            txt = f'**Ayes:** {ayes} | **Noes:** {650 - ayes}'
            if ayes >= budget.WIN + 40:
                st.success(f'**House of Commons:** The Budget passed with a thumping majority! Your backbenchers cheered you to the rafters.\n\n{txt}')
            elif ayes >= budget.WIN + 15:
                st.info(f'**House of Commons:** The Budget passed. There was some grumbling from the backbenches, but the whips kept them in line.\n\n{txt}')
            else:
                st.warning(f'**House of Commons:** The Budget barely scraped through! A massive backbench rebellion nearly brought the government down.\n\n{txt}')
            if st.button('Proceed to Spring', type='primary'):
                engine.proceed_to_spring()
                st.rerun()
            speech = s.get('budget_speech')
            if speech:
                with st.expander('🎙️ The Budget speech and the morning-after reactions', expanded=True):
                    st.markdown('> ' + speech['text'])
                    for who, quote in speech['reactions']:
                        st.markdown(f'**{who}:** {quote}')
        with right:
            st.markdown("<div class='pane-title'>The morning after</div>", unsafe_allow_html=True)
            for ev in s.event_cards:
                event_card(ev['title'], ev['text'], ev['summary'])
            lords_memo()
            if s.get('headlines'):
                render_newspapers(*s.headlines)
    else:
        st.markdown(f"<div class='dc-eyebrow'>Block 3 · Year {s.year}</div><div class='dc-title'>The Chancellor's Budget</div>", unsafe_allow_html=True)
        budget.ensure()

        def submit():
            if st.button('Submit Budget to the Commons & Lords', type='primary',
                         help='Any slider changes you have not applied are applied automatically when you submit.'):
                engine.submit_budget()
                st.rerun()

        budget.render(submit=submit, after_summary=lambda: politics.render_pledges(budget.read()))


# ==================== DASHBOARD TABS ====================
def dashboard():
    tab_polls, tab_nation, tab_imf, tab_hist = st.tabs(['📊 Polls', '🧭 State of the Nation', '🌍 IMF Outlook', '📜 History'])
    with tab_polls:
        render_polls(pd.DataFrame(s.poll_history).set_index('Period'), chart_in_expander=True)
    with tab_nation:
        country.render()
    with tab_imf:
        st.caption(f'External baseline: {imf_outlook.IMF_SOURCE}. The annual economy tick gently pulls growth and inflation '
                   'towards these figures; it is not a forecast of your own playthrough.')
        st.dataframe(pd.DataFrame(imf_outlook.rows()), hide_index=True, use_container_width=True)
    with tab_hist:
        pending = sorted(s.pending, key=lambda p: p['due'])
        render_timeline(s.history, pending)
        if st.button('Resign & Start New Career'):
            engine.resign()
            st.rerun()


def last_turn():
    """What just happened: always visible (it is the feedback loop of the game), but compact."""
    if not (s.event_cards or s.get('message') or s.get('humphrey_note') or s.get('headlines')):
        return
    st.markdown("<div class='pane-title'>Last turn</div>", unsafe_allow_html=True)
    for ev in s.event_cards:
        event_card(ev['title'], ev['text'], ev['summary'])
    if s.get('message'):
        news_box(s.message)
    if s.get('humphrey_note'):
        humphrey_message(s.humphrey_note, title='Sir Humphrey on your last decision')
    if s.get('headlines'):
        render_newspapers(*s.headlines)


# ==================== DECISIONS & CRISES ====================
def crisis_screen():
    crisis = scen.get(s.active_crisis)
    if crisis is None:
        s.active_crisis = None
        st.rerun()
    crisis_card(crisis['title'])
    humphrey_message(crisis['humphrey'])
    if s.get('crisis_reason'):
        st.caption(s.crisis_reason)
    labels = scen.option_labels(crisis)
    choice = st.radio('Choose emergency response:', labels, index=None, key=f'crisis_{s.steps}', label_visibility='collapsed')
    if st.button('Resolve Crisis', type='primary', disabled=choice is None):
        engine.resolve_crisis(labels.index(choice))
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


def decision_screen():
    decision = engine.current_decision()
    if not decision:
        st.write('No decision data found for this block.')
        return
    options = engine.current_options()
    title = decision['title']
    phase = phase_info(s.block)
    st.markdown(f"<div class='dc-eyebrow'>Year {s.year} · Phase {s.block} · {phase['name']}</div><div class='dc-title'>{title}</div>", unsafe_allow_html=True)
    st.write(decision['text'])
    st.caption(phase['guide'])
    humphrey_message(decision['humphrey'])
    features.render_phase_action()
    labels = [o['label'] for o in options]
    choice = st.radio('Select strategy:', labels, index=None, key=f'dec_{s.term}_{s.year}_{s.block}', label_visibility='collapsed')
    if st.button('Execute Policy', type='primary', disabled=choice is None):
        engine.execute_decision(options[labels.index(choice)])
        st.rerun()


if s.block == 3 and s.active_crisis is None:
    budget_screen()
else:
    # Focused workspace: keep the active decision uncluttered and put supporting
    # information behind clear tabs rather than squeezing it into a narrow column.
    tab_decision, tab_dashboard, tab_briefing = st.tabs(
        ['⚖️ Current decision', '📊 National dashboard', '📰 Briefing & consequences']
    )
    with tab_decision:
        if s.active_crisis is not None:
            crisis_screen()
        elif s.get('active_request'):
            request_screen()
        else:
            decision_screen()
    with tab_dashboard:
        dashboard()
    with tab_briefing:
        has_briefing = bool(s.event_cards or s.get('message') or s.get('humphrey_note') or s.get('headlines'))
        if has_briefing:
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
