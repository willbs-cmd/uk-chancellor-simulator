"""UK Chancellor Simulator (Hardcore Mode): the Streamlit UI. All game rules live in engine.py."""
import pandas as pd
import streamlit as st

import achievements
import budget
import country
import engine
import imf_outlook
import scenarios as scen
import state
from state import CARDS_ECON, CARDS_POLITICAL, CARDS_TOP
from theme import (apply_theme, crisis_card, event_card, header, humphrey_message, news_box, render_cards,
                   render_newspapers, render_polls, render_scorecard, render_timeline)

st.set_page_config(page_title='UK Chancellor Simulator - Hardcore', layout='wide', page_icon='🏛️',
                   initial_sidebar_state='collapsed')
apply_theme()
state.ensure_init()
s = st.session_state


def restart():
    s.clear()
    st.rerun()


# ==================== CHANCELLOR'S OFFICE SIDEBAR ====================
with st.sidebar:
    st.markdown("""
    <div class='office-crest'>
      <div class='crown'>♛</div>
      <div class='title'>The Chancellor's Office</div>
      <div class='sub'>HM Treasury · Private Office</div>
    </div>
    """, unsafe_allow_html=True)

    if s.step == 'game':
        st.markdown('<div class="menu-label">Current government</div>', unsafe_allow_html=True)
        st.markdown(f"**{s.party}**  \nTerm {s.term} · Year {min(s.year,5)}")
        st.caption(f'Difficulty: {s.difficulty} · Cabinet file: #{s.seed}')
        st.markdown('<div class="menu-label">Office files</div>', unsafe_allow_html=True)
        st.info('Use the briefing tabs on the Chancellor’s desk to review the economy, Parliament, intelligence and history.', icon='📁')
        st.markdown('<div class="menu-label">Administration</div>', unsafe_allow_html=True)
        st.download_button('💾 Save current government', state.export_save(), file_name=f'chancellor_{s.party.replace(" ","")}_T{s.term}Y{s.year}.json', mime='application/json', help='Download a JSON save of the current government.')
        if st.button('🚪 Resign / start new career'):
            restart()
    else:
        st.markdown('<div class="menu-label">Incoming Chancellor</div>', unsafe_allow_html=True)
        st.caption('The private office is awaiting your instructions.')


# ==================== SETUP SCREEN ====================
def setup_screen():
    st.title('🏛️ The UK Chancellor Simulator (Hardcore Mode)')
    st.markdown('### Step 1: Choose Your Government')
    party = st.selectbox('Select Governing Party:', state.PARTIES)
    c1, c2 = st.columns([2, 1])
    with c1:
        difficulty = st.radio('Difficulty', list(state.DIFFICULTY), index=2, horizontal=True,
                              captions=[d['blurb'] for d in state.DIFFICULTY.values()])
    with c2:
        seed = st.number_input('Seed (same seed, same crises)', min_value=1, max_value=999999, value=int(s.seed), step=1)
    tags = st.checkbox('Show ideology tags on policy options',
                       value=(difficulty == 'Easy'), key=f'tags_{difficulty}',
                       help='Off by default: read the policy, not the label. Your MPs still know what is and is not '
                            "in your party's tradition.")
    if st.button('Enter Number 11', type='primary'):
        state.new_game(party, difficulty, seed, tags)
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

st.markdown(
    f"<div class='office-section'><div class='office-kicker'>Private Office Briefing</div>"
    f"<div class='office-title'>Good morning, Chancellor.</div>"
    f"<div class='office-note' style='margin-top:9px'>You are in Year {min(s.year,5)} of 5. Decision {s.block} of 3. The briefing below is arranged from immediate priorities to longer-term intelligence.</div></div>",
    unsafe_allow_html=True,
)

with st.expander('📌 Open the Chancellor’s pocket briefing', expanded=True):
    render_cards(CARDS_TOP)
    st.markdown('##### Political Capital')
    render_cards(CARDS_POLITICAL)

st.divider()


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
def budget_screen():
    if s.get('budget_passed'):
        st.subheader('🏛️ Parliamentary Vote Results')
        bb = s.backbench_opinion
        base_ayes = 326 if s.party not in state.REGIONAL else 300
        ayes = min(650, max(0, int(base_ayes + (bb / 1.5) - 20 + (s.year * 2))))
        noes = 650 - ayes
        txt = f'**Ayes:** {ayes} | **Noes:** {noes}'
        if bb > 70:
            st.success(f'**House of Commons:** The Budget passed the Commons with a thumping majority! Your backbenchers cheered you to the rafters.\n\n{txt}')
        elif bb > 40:
            st.info(f'**House of Commons:** The Budget passed the Commons. There was some grumbling from the backbenches, but the whips kept them in line.\n\n{txt}')
        else:
            st.warning(f'**House of Commons:** The Budget barely scraped through the Commons! A massive backbench rebellion nearly brought the government down.\n\n{txt}')

        lords_ayes = min(750, max(0, int(200 + s.approval * 2.5)))
        lords_noes = 750 - lords_ayes
        if s.approval < 40:
            humphrey_message(f"As for the House of Lords, Chancellor, they actually voted against us (**{lords_noes} Not-Contents** to {lords_ayes} Contents). "
                             "I reminded them of the Parliament Act of 1911. They cannot reject a Money Bill. However, seeing your dismal poll numbers, "
                             "they decided to delay it for a month just to be difficult. The markets were briefly irritated.")
        else:
            humphrey_message(f"As for the House of Lords, Chancellor, they supported the bill (**{lords_ayes} Contents** to {lords_noes} Not-Contents). "
                             "Though even if they hadn't, the Parliament Act of 1911 means they cannot vote down a Money Bill. The constitution is a wonderful thing.")
        for ev in s.event_cards:
            event_card(ev['title'], ev['text'], ev['summary'])
        if s.get('headlines'):
            render_newspapers(*s.headlines)
        st.divider()
        if st.button('Proceed to Spring', type='primary'):
            engine.proceed_to_spring()
            st.rerun()
    else:
        st.subheader(f"Year {s.year} - Block 3: The Chancellor's Budget")
        humphrey_message("A budget, Chancellor, is merely a collection of numbers we present to the House to obscure our true intentions. "
                         "Shall we proceed to the dispatch box?")
        budget.render()
        st.divider()
        st.caption('Any slider changes you have not applied are applied automatically when you submit.')
        if st.button('Submit Budget to the Commons & Lords', type='primary'):
            engine.submit_budget()
            st.rerun()


# ==================== DASHBOARD TABS ====================
def dashboard():
    st.markdown(
        "<div class='office-kicker'>Chancellor's Desk</div><div class='office-title'>Government Briefing Room</div>",
        unsafe_allow_html=True,
    )
    tab_overview, tab_econ, tab_parliament, tab_imf, tab_history = st.tabs(
        ['🗂️ Overview', '📊 Economy', '🏛️ Parliament', '🌐 IMF Outlook', '📜 History']
    )

    with tab_overview:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('#### Immediate position')
            render_cards(CARDS_ECON, per_row=2)
        with c2:
            st.markdown('#### Political position')
            render_cards(CARDS_POLITICAL, per_row=2)
        st.markdown('#### Today’s intelligence')
        if s.get('message'):
            news_box(s.message)
        else:
            st.info('No urgent intelligence has reached the private office.')

    with tab_econ:
        render_cards(CARDS_ECON, per_row=2)
        st.markdown('### 📈 Voting intention')
        df = pd.DataFrame(s.poll_history).set_index('Period')
        render_polls(df)

    with tab_parliament:
        st.markdown('#### Parliamentary & political capital')
        render_cards(CARDS_POLITICAL, per_row=2)
        st.markdown('#### Cabinet / parliamentary history')
        pending = sorted(s.pending, key=lambda p: p['due'])
        render_timeline(s.history, pending)

    with tab_imf:
        st.markdown('#### 🌐 Three-Year UK Economic Outlook')
        st.caption('IMF staff baseline — July 2026. Your policies can move the simulated economy above or below this path.')
        current_year = imf_outlook.year_for_game(s.year)
        imf = imf_outlook.get(s.year)
        if imf:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric('IMF real GDP growth', f"{imf['gdp']:.1f}%")
            c2.metric('IMF CPI inflation', f"{imf['inflation']:.1f}%")
            c3.metric('IMF unemployment', f"{imf['unemployment']:.1f}%")
            c4.metric('IMF public balance', f"{imf['deficit']:.1f}% GDP")
            st.markdown(f"**Your {current_year} simulation:** GDP growth **{s.growth:.1f}%** ({s.growth-imf['gdp']:+.1f}pp vs IMF) · inflation **{s.inflation:.1f}%** ({s.inflation-imf['inflation']:+.1f}pp vs IMF).")
        else:
            st.info('The IMF three-year baseline ends here; later years use the simulator’s own macro model.')
        st.dataframe(pd.DataFrame(imf_outlook.rows()), hide_index=True, use_container_width=True)
        st.caption('Source: IMF, United Kingdom 2026 Article IV Consultation, July 2026. PSNFL is not directly comparable with the simulator’s national-debt variable.')

    with tab_history:
        pending = sorted(s.pending, key=lambda p: p['due'])
        render_timeline(s.history, pending)
        if st.button('Resign & Start New Career'):
            engine.resign()
            st.rerun()


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
    choice = st.radio('Choose emergency response:', labels, index=None, key=f'crisis_{s.steps}')
    if st.button('Resolve Crisis', type='primary', disabled=choice is None):
        engine.resolve_crisis(labels.index(choice))
        st.rerun()


def decision_screen():
    decision = engine.current_decision()
    if not decision:
        st.write('No decision data found for this block.')
        return
    options = engine.current_options()
    st.subheader(f"Block {s.block}: {decision['title']}")
    st.write(decision['text'])
    humphrey_message(decision['humphrey'])
    labels = [o['label'] for o in options]
    choice = st.radio('Select strategy:', labels, index=None, key=f'dec_{s.term}_{s.year}_{s.block}')
    if st.button('Execute Policy', type='primary', disabled=choice is None):
        engine.execute_decision(options[labels.index(choice)])
        st.rerun()


if s.block == 3 and s.active_crisis is None:
    budget_screen()
else:
    # The desk is deliberately arranged as: decision -> advice -> briefing.
    # This keeps the player's immediate task visually separate from reference information.
    st.markdown("<div class='office-decision'>", unsafe_allow_html=True)
    if s.active_crisis is not None:
        crisis_screen()
    else:
        decision_screen()
    st.markdown('</div>', unsafe_allow_html=True)

    if s.get('humphrey_note'):
        humphrey_message(s.humphrey_note, title='Sir Humphrey — Private Office Advice')

    if s.event_cards:
        with st.expander(f'🗞️ Open dispatches ({len(s.event_cards)})', expanded=True):
            for ev in s.event_cards:
                event_card(ev['title'], ev['text'], ev['summary'])

    if s.get('headlines'):
        with st.expander('📰 Press review', expanded=False):
            render_newspapers(*s.headlines)

    st.divider()
    dashboard()
