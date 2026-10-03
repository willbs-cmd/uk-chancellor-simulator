import streamlit as st
import random
import pandas as pd

from theme import apply_theme, header, crisis_card, news_box, render_polls, humphrey_message
import country
import budget
import decisions
import scenarios as scen

st.set_page_config(page_title='UK Chancellor Simulator - Hardcore', layout='wide')
apply_theme()

# ==================== INITIALIZATION ====================
if 'initialized' not in st.session_state or st.session_state.get('step') is None:
    st.session_state.step = 'setup'
    st.session_state.party = 'Labour'
    st.session_state.year = 1
    st.session_state.block = 1
    st.session_state.term = 1
    st.session_state.active_crisis = None
    st.session_state.last_ideology = None

    # Economic Stats
    st.session_state.approval = 48.0
    st.session_state.market_conf = 65.0
    st.session_state.debt = 98.2
    st.session_state.deficit = 5.4
    st.session_state.inflation = 3.2
    st.session_state.interest_rate = 5.0
    st.session_state.gilt_yield = 4.7
    st.session_state.growth = 0.8
    st.session_state.headroom = 8.5

    # Political Capital Stats
    st.session_state.pm_opinion = 75.0
    st.session_state.cab_opinion = 65.0
    st.session_state.party_opinion = 70.0
    st.session_state.backbench_opinion = 60.0
    st.session_state.media_opinion = 50.0

    # Deltas
    st.session_state.prev_approval = 48.0
    st.session_state.prev_market = 65.0
    st.session_state.prev_growth = 0.8
    st.session_state.prev_headroom = 8.5
    st.session_state.prev_debt = 98.2
    st.session_state.prev_pm = 75.0
    st.session_state.prev_cab = 65.0
    st.session_state.prev_party = 70.0
    st.session_state.prev_backbench = 60.0
    st.session_state.prev_media = 50.0

    st.session_state.poll_history = {
        'Year': [1], 'Labour': [38], 'Conservative': [32], 'Liberal Democrats': [12], 
        'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]
    }

    st.session_state.message = "Welcome to Number 11 Downing Street. The economy is fragile, inflation is sticky, and bond markets are watching."
    st.session_state.initialized = True

# ==================== LOGIC FUNCTIONS ====================
def _clip(val, minimum=0.0, maximum=100.0):
    return max(minimum, min(maximum, val))

def update_political_capital(ideology_chosen, approval_diff, headroom_diff):
    s = st.session_state
    s.prev_pm = s.pm_opinion; s.prev_cab = s.cab_opinion
    s.prev_party = s.party_opinion; s.prev_backbench = s.backbench_opinion
    s.prev_media = s.media_opinion

    purity_map = {
        'Labour': ['Social Democratic', 'Hard Left'],
        'Conservative': ['Free-Market', 'Fiscal Austerity'],
        'Liberal Democrats': ['Centric', 'Social Democratic'],
        'Reform UK': ['Free-Market'],
        'Green Party': ['Hard Left', 'Social Democratic'],
        'SNP': ['Social Democratic', 'Centric'],
        'Plaid Cymru': ['Social Democratic', 'Hard Left']
    }
    
    core = purity_map.get(s.party, ['Centric'])
    
    if ideology_chosen in core:
        s.backbench_opinion += random.uniform(2, 6)
        s.party_opinion += random.uniform(1, 4)
    else:
        s.backbench_opinion -= random.uniform(4, 9)
        s.party_opinion -= random.uniform(2, 5)

    s.pm_opinion += (approval_diff * 1.5) + (headroom_diff * 0.5)
    s.cab_opinion += approval_diff + random.uniform(-2, 3)
    s.media_opinion += (approval_diff * 0.8) + ((s.market_conf - s.prev_market) * 0.5)

    s.pm_opinion = _clip(s.pm_opinion)
    s.cab_opinion = _clip(s.cab_opinion)
    s.party_opinion = _clip(s.party_opinion)
    s.backbench_opinion = _clip(s.backbench_opinion)
    s.media_opinion = _clip(s.media_opinion)

def update_polling_data(current_year):
    gov_party = st.session_state.party
    approval_boost = (st.session_state.approval - 50) * 0.35

    if current_year not in st.session_state.poll_history['Year']:
        st.session_state.poll_history['Year'].append(current_year)
        base_shares = {p: st.session_state.poll_history[p][-1] for p in ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru']}
        
        if gov_party in ['SNP', 'Plaid Cymru']: base_shares[gov_party] += (approval_boost * 0.2)
        else: base_shares[gov_party] += approval_boost

        for p in base_shares:
            if p != gov_party: base_shares[p] -= (approval_boost / 5) + random.uniform(-1, 1)
            else: base_shares[p] += random.uniform(-1, 1)
            floor = 1 if p in ['SNP', 'Plaid Cymru'] else 4
            base_shares[p] = max(floor, round(base_shares[p], 1))

        total = sum(base_shares.values())
        for p in base_shares:
            base_shares[p] = round((base_shares[p] / total) * 100, 1)
            st.session_state.poll_history[p].append(base_shares[p])

def snapshot_metrics():
    s = st.session_state
    s.prev_approval = s.approval
    s.prev_market = s.market_conf
    s.prev_growth = s.growth
    s.prev_headroom = s.headroom
    s.prev_debt = s.debt

def process_block_execution(next_year, next_block, chosen_ideology):
    snapshot_metrics()
    st.session_state.last_ideology = chosen_ideology
    country.apply_decision(chosen_ideology)

    if st.session_state.gilt_yield > 4.5: st.session_state.headroom = round(st.session_state.headroom - 0.8, 1)
    if st.session_state.inflation > 3.0: st.session_state.approval = round(st.session_state.approval - 1.5, 1)

    update_political_capital(chosen_ideology, st.session_state.approval - st.session_state.prev_approval, st.session_state.headroom - st.session_state.prev_headroom)
    update_polling_data(next_year)
    
    st.session_state.active_crisis = scen.pick_next(st.session_state.year, st.session_state.block, chosen_ideology)
    st.session_state.year = next_year
    st.session_state.block = next_block
    st.rerun()

# ==================== SETUP SCREEN ====================
if st.session_state.step == 'setup':
    st.title('🏛️ The UK Chancellor Simulator (Hardcore Mode)')
    st.markdown('### Step 1: Choose Your Government')
    
    party_choice = st.selectbox('Select Governing Party:', ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru'])

    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button('Enter Number 11', type='primary'):
            st.session_state.party = party_choice
            
            if party_choice == 'Conservative':
                st.session_state.approval = 46; st.session_state.market_conf = 70
                st.session_state.poll_history = {'Year': [1], 'Labour': [32], 'Conservative': [38], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
            elif party_choice == 'Liberal Democrats':
                st.session_state.approval = 49; st.session_state.market_conf = 60
                st.session_state.poll_history = {'Year': [1], 'Labour': [30], 'Conservative': [30], 'Liberal Democrats': [24], 'Reform UK': [8], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
            elif party_choice == 'Reform UK':
                st.session_state.approval = 42; st.session_state.market_conf = 55
                st.session_state.poll_history = {'Year': [1], 'Labour': [28], 'Conservative': [28], 'Liberal Democrats': [10], 'Reform UK': [26], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
            elif party_choice == 'Green Party':
                st.session_state.approval = 45; st.session_state.market_conf = 50
                st.session_state.poll_history = {'Year': [1], 'Labour': [28], 'Conservative': [26], 'Liberal Democrats': [12], 'Reform UK': [8], 'Green Party': [22], 'SNP': [3], 'Plaid Cymru': [1]}
            elif party_choice == 'SNP':
                st.session_state.approval = 45; st.session_state.market_conf = 50
                st.session_state.poll_history = {'Year': [1], 'Labour': [34], 'Conservative': [30], 'Liberal Democrats': [10], 'Reform UK': [9], 'Green Party': [4], 'SNP': [12], 'Plaid Cymru': [1]}
            elif party_choice == 'Plaid Cymru':
                st.session_state.approval = 45; st.session_state.market_conf = 50
                st.session_state.poll_history = {'Year': [1], 'Labour': [34], 'Conservative': [30], 'Liberal Democrats': [10], 'Reform UK': [9], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [10]}
            else:
                st.session_state.approval = 48; st.session_state.market_conf = 65
                st.session_state.poll_history = {'Year': [1], 'Labour': [38], 'Conservative': [32], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}

            st.session_state.step = 'game'
            st.session_state.message = "Good morning, Chancellor. I am Sir Humphrey Appleby. My job is to protect you from the press, the public, and most importantly, your own backbenchers."
            st.rerun()
    with col_b:
        if st.button('Reset Session Cache'):
            st.session_state.clear()
            st.rerun()
    st.stop()

# ==================== MAIN HEADER & DASHBOARD ====================
header(st.session_state.party, st.session_state.term, st.session_state.year, st.session_state.block)

# Row 1: Economic Dashboard
d_approval = round(st.session_state.approval - st.session_state.prev_approval, 1)
d_market = round(st.session_state.market_conf - st.session_state.prev_market, 1)
d_growth = round(st.session_state.growth - st.session_state.prev_growth, 1)
d_headroom = round(st.session_state.headroom - st.session_state.prev_headroom, 1)
d_debt = round(st.session_state.debt - st.session_state.prev_debt, 1)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric('Public Approval', f"{st.session_state.approval:.1f}%", f"{d_approval:+}%" if d_approval != 0 else '0%')
c2.metric('Market Confidence', f"{st.session_state.market_conf:.1f}%", f"{d_market:+}%" if d_market != 0 else '0%')
c3.metric('Economic Growth', f"{st.session_state.growth:.1f}%", f"{d_growth:+}%" if d_growth != 0 else '0%')
c4.metric('OBR Headroom', f"£{st.session_state.headroom:.1f}B", f"£{d_headroom:+}B" if d_headroom != 0 else '£0B')
c5.metric('National Debt', f"{st.session_state.debt:.1f}%", f"{d_debt:+}%" if d_debt != 0 else '0%', delta_color='inverse')

# Row 2: Political Capital Dashboard
st.markdown("#### 🏛️ Political Capital")
p1, p2, p3, p4, p5 = st.columns(5)
p1.metric("PM's Confidence", f"{st.session_state.pm_opinion:.0f}/100", f"{st.session_state.pm_opinion - st.session_state.prev_pm:+.0f}")
p2.metric('Cabinet Support', f"{st.session_state.cab_opinion:.0f}/100", f"{st.session_state.cab_opinion - st.session_state.prev_cab:+.0f}")
p3.metric('Party Unity', f"{st.session_state.party_opinion:.0f}/100", f"{st.session_state.party_opinion - st.session_state.prev_party:+.0f}")
p4.metric('Backbench Morale', f"{st.session_state.backbench_opinion:.0f}/100", f"{st.session_state.backbench_opinion - st.session_state.prev_backbench:+.0f}")
p5.metric('Media Sentiment', f"{st.session_state.media_opinion:.0f}/100", f"{st.session_state.media_opinion - st.session_state.prev_media:+.0f}")

st.divider()

# ==================== ELECTION NIGHT ENGINE ====================
if st.session_state.year > 5:
    st.subheader('🗳️ GENERAL ELECTION NIGHT: RESULTS')

    latest_polls = {p: st.session_state.poll_history[p][-1] for p in ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru']}
    
    seats = {}
    seats['Labour'] = int((latest_polls['Labour'] / 100) * 650 * (1.1 if latest_polls['Labour'] > 30 else 0.8))
    seats['Conservative'] = int((latest_polls['Conservative'] / 100) * 650 * (1.1 if latest_polls['Conservative'] > 30 else 0.8))
    seats['Liberal Democrats'] = int(max(5, (latest_polls['Liberal Democrats'] / 100) * 650 * 0.6))
    seats['Reform UK'] = int(max(0, (latest_polls['Reform UK'] / 100) * 650 * 0.3))
    seats['Green Party'] = int(max(1, (latest_polls['Green Party'] / 100) * 650 * 0.2))
    seats['SNP'] = int(min(57, max(4, (latest_polls['SNP'] / 100) * 650 * 3.5))) 
    seats['Plaid Cymru'] = int(min(32, max(2, (latest_polls['Plaid Cymru'] / 100) * 650 * 3.0)))

    total_alloc = sum(seats.values())
    diff = 650 - total_alloc
    largest = max(seats, key=seats.get)
    seats[largest] += diff

    player_seats = seats[st.session_state.party]
    is_regional = st.session_state.party in ['SNP', 'Plaid Cymru']
    
    sacked = False
    sacked_msg = ""
    if st.session_state.pm_opinion < 40 or st.session_state.party_opinion < 35:
        sacked = True
        sacked_msg = "Your relationship with the Prime Minister and your own backbenches collapsed. Regardless of the election result, you have been sacked and banished to the backbenches."

    coalition_formed = False
    coalition_partner = None
    minority_gov = False
    win = False

    if is_regional:
        target = 40 if st.session_state.party == 'SNP' else 15
        max_reg = 57 if st.session_state.party == 'SNP' else 32
        if player_seats >= target:
            result_title = f"{st.session_state.party} Regional Dominance ({player_seats}/{max_reg})"
            win = True
            gov_type = "Holding the Balance of Power in Westminster" if seats[largest] < 326 else "Strong Regional Opposition"
        else:
            result_title = f"{st.session_state.party} Regional Defeat ({player_seats} seats)"
            gov_type = "Loss of Regional Mandate"
    else:
        if player_seats >= 326:
            result_title = f"{st.session_state.party} Majority Government"
            gov_type = f"Working Majority of {player_seats - 326}"
            win = True
        else:
            result_title = "Hung Parliament"
            left_bloc = ['Labour', 'Liberal Democrats', 'Green Party', 'SNP', 'Plaid Cymru']
            right_bloc = ['Conservative', 'Reform UK', 'Liberal Democrats']
            my_bloc = left_bloc if st.session_state.party in left_bloc else right_bloc
            
            for partner in my_bloc:
                if partner != st.session_state.party:
                    if player_seats + seats[partner] >= 326:
                        coalition_formed = True
                        coalition_partner = partner
                        break
            
            if coalition_formed:
                gov_type = f"Formal Coalition with {coalition_partner}"
                win = True
            elif player_seats == seats[largest]:
                minority_gov = True
                gov_type = "Fragile Minority Government"
                win = True
            else:
                gov_type = "Sent to the Opposition Benches"

    box_color = '#111111'
    if win and not sacked: box_color = '#2b5440'
    elif sacked: box_color = '#8b0000'

    st.markdown(f'''
    <div style='background-color: {box_color}; padding: 20px; border-radius: 10px; color: white; text-align: center; border: 2px solid #c9a45c;'>
        <h2>{result_title}</h2>
        <h4 style='color: #c9a45c;'>{gov_type}</h4>
        <p style='font-size: 18px;'>Your Seats: <b>{player_seats}</b> | Target for UK Majority: 326</p>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown("### 🏛️ The New Parliament")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("LAB", seats['Labour'])
    col2.metric("CON", seats['Conservative'])
    col3.metric("LDEM", seats['Liberal Democrats'])
    col4.metric("REF", seats['Reform UK'])
    col5.metric("GRN", seats['Green Party'])
    col6.metric("SNP", seats['SNP'])
    col7.metric("PC", seats['Plaid Cymru'])

    st.divider()

    if sacked:
        humphrey_message("I am so sorry, Chancellor. The Prime Minister feels that your continued presence at the Treasury is... politically sub-optimal. The removal van is waiting at the back door of Number 11.")
        st.error(sacked_msg)
        if st.button('Resign & Start New Career'):
            st.session_state.clear()
            st.rerun()
    elif win:
        humphrey_message(f"Congratulations, Chancellor. We have survived the electorate. {'Managing a coalition partner will be tedious' if coalition_formed else 'A minority government will be a legislative nightmare'}, but you remain at the Treasury.")
        st.success("You retained power and survived the election!")
        if st.button('Continue as Chancellor'):
            st.session_state.term += 1
            st.session_state.year = 1
            st.session_state.block = 1
            st.session_state.step = 'game'
            st.rerun()
    else:
        humphrey_message("The electorate has spoken, Chancellor. Or rather, they have shouted. We have been thoroughly evicted. I shall miss our little chats.")
        st.error('Your party lost power.')
        if st.button('Start New Career'):
            st.session_state.clear()
            st.rerun()
    st.stop()


# ==================== MAIN GAMEPLAY LAYOUT ====================

# If it's budget time, let it take up the full width.
if st.session_state.block == 4:
    st.subheader(f"Year {st.session_state.year} - Block 4: The Chancellor's Budget")
    humphrey_message("A budget, Chancellor, is merely a collection of numbers we present to the House to obscure our true intentions. I have taken the liberty of drafting some 'Special Schemes' to distract the press. Shall we proceed?")
    
    budget.render()
    
    st.divider()
    if st.button('End Year & Advance to Spring', type='primary'):
        snapshot_metrics() 
        budget.apply_ongoing()
        
        if st.session_state.headroom > 0: st.session_state.pm_opinion = min(100, st.session_state.pm_opinion + 5)
        else: st.session_state.pm_opinion -= 5
        
        st.session_state.year += 1
        st.session_state.block = 1
        st.rerun()

# Otherwise, split the screen! (Left = Gameplay, Right = Dashboard Tabs)
else:
    col_game, col_dash = st.columns([1.4, 1.0], gap="large")
    
    with col_dash:
        tab_econ, tab_nation = st.tabs(['📊 Economy & Polls', '🇬🇧 State of the Nation'])
        with tab_econ:
            m1, m2 = st.columns(2)
            m1.metric('Annual Deficit', f'£{round(st.session_state.deficit, 1)}B')
            m2.metric('Inflation Rate', f'{round(st.session_state.inflation, 1)}%')
            m3, m4 = st.columns(2)
            m3.metric('Bank Rate', f'{round(st.session_state.interest_rate, 1)}%')
            m4.metric('10-Yr Gilt Yield', f'{round(st.session_state.gilt_yield, 1)}%')

            st.markdown('### 📈 Voting Intention')
            df_polls = pd.DataFrame(st.session_state.poll_history).set_index('Year')
            render_polls(df_polls)
            
            st.write('')
            st.caption("Press 'Resign' below to clear your save data and select a new party.")
            if st.button('Resign & Start New Career'):
                st.session_state.clear()
                st.rerun()
                
        with tab_nation:
            country.render()
            
    with col_game:
        # Display the news from the last turn at the top of the desk
        if st.session_state.get('message'):
            news_box(st.session_state.message)
            
        if st.session_state.active_crisis is not None:
            crisis = scen.get(st.session_state.active_crisis)
            if crisis is None:
                st.session_state.active_crisis = None
                st.rerun()
                
            crisis_card(crisis['title'])
            humphrey_message(crisis['humphrey'])
            if st.session_state.get('crisis_reason'): st.caption(st.session_state.crisis_reason)
                
            labels = scen.option_labels(crisis)
            crisis_choice = st.radio('Choose emergency response:', labels)
            
            if st.button('Resolve Crisis', type="primary"):
                snapshot_metrics()
                idx = labels.index(crisis_choice)
                st.session_state.message = scen.resolve(crisis, idx)
                
                ideology_proxy = ['Hard Left', 'Centric', 'Free-Market', 'Centric'] 
                proxy = ideology_proxy[idx] if idx < len(ideology_proxy) else 'Centric'
                update_political_capital(proxy, st.session_state.approval - st.session_state.prev_approval, st.session_state.headroom - st.session_state.prev_headroom)

                st.session_state.active_crisis = None
                st.rerun()

        else:
            decision_data = decisions.DECISIONS.get((st.session_state.year, st.session_state.block))
            
            if decision_data:
                st.subheader(f"Block {st.session_state.block}: {decision_data['title']}")
                st.write(decision_data['text'])
                humphrey_message(decision_data['humphrey'])
                
                choice = st.radio('Select strategy:', decision_data['options'])
                
                if st.button(f'Execute Policy', type="primary"):
                    idx = decision_data['options'].index(choice)
                    effect = decision_data['effects'][idx]
                    
                    st.session_state.message = effect.get('message', 'Decision applied.')
                    if 'headroom' in effect: st.session_state.headroom = round(st.session_state.headroom + effect['headroom'], 1)
                    if 'approval' in effect: st.session_state.approval = round(st.session_state.approval + effect['approval'], 1)
                    if 'market_conf' in effect: st.session_state.market_conf = round(st.session_state.market_conf + effect['market_conf'], 1)
                    if 'deficit' in effect: st.session_state.deficit = round(st.session_state.deficit + effect['deficit'], 1)
                    if 'growth' in effect: st.session_state.growth = round(st.session_state.growth + effect['growth'], 2)
                    if 'inflation' in effect: st.session_state.inflation = round(st.session_state.inflation + effect['inflation'], 2)
                    if 'gilt_yield' in effect: st.session_state.gilt_yield = round(st.session_state.gilt_yield + effect['gilt_yield'], 2)

                    ideologies = ['Hard Left', 'Social Democratic', 'Centric', 'Free-Market', 'Fiscal Austerity']
                    selected_type = ideologies[idx]
                    
                    process_block_execution(st.session_state.year, st.session_state.block + 1, selected_type)
            else:
                st.write("No decision data found for this block.")
                if st.button("Skip Block"): process_block_execution(st.session_state.year, st.session_state.block + 1, 'Centric')
