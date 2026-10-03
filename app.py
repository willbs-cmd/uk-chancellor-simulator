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

if 'initialized' not in st.session_state or st.session_state.get('step') is None:
    st.session_state.step = 'setup'
    st.session_state.party = 'Labour'
    st.session_state.approval = 48
    st.session_state.market_conf = 65
    st.session_state.debt = 98.2
    st.session_state.deficit = 5.4
    st.session_state.inflation = 3.2
    st.session_state.interest_rate = 5.0
    st.session_state.gilt_yield = 4.7
    st.session_state.growth = 0.8
    st.session_state.headroom = 8.5
    st.session_state.year = 1
    st.session_state.block = 1
    st.session_state.term = 1
    st.session_state.active_crisis = None
    st.session_state.last_ideology = None

    st.session_state.prev_approval = 48
    st.session_state.prev_market = 65
    st.session_state.prev_growth = 0.8
    st.session_state.prev_headroom = 8.5
    st.session_state.prev_debt = 98.2

    # Poll history now includes the regional parties!
    st.session_state.poll_history = {
        'Year': [1], 'Labour': [38], 'Conservative': [32], 'Liberal Democrats': [12], 
        'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]
    }

    st.session_state.message = 'Welcome to Number 11 Downing Street. The economy is fragile, inflation is sticky, and bond markets are watching.'
    st.session_state.initialized = True

if st.session_state.step == 'setup':
    st.title('🏛️ The UK Chancellor Simulator (Hardcore Mode)')
    st.markdown('### Step 1: Choose Your Government')
    st.write('Economic headroom is tight (£8.5B) and debt is nearly 100% of GDP. Select which party is forming the government:')

    party_choice = st.selectbox('Select Governing Party:', ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru'])

    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button('Enter Number 11', type='primary'):
            st.session_state.party = party_choice
            
            # Setup initial state based on party chosen
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

            st.session_state.prev_approval = st.session_state.approval
            st.session_state.prev_market = st.session_state.market_conf
            st.session_state.step = 'game'
            st.session_state.message = "Good morning, Chancellor. I am Sir Humphrey Appleby, your Permanent Secretary. I am here to ensure that your radical new policies cause as little disruption to the smooth running of the Treasury as possible."
            st.rerun()
    with col_b:
        if st.button('Reset Session Cache'):
            st.session_state.clear()
            st.rerun()
    st.stop()

header(st.session_state.party, st.session_state.term, st.session_state.year, st.session_state.block)

d_approval = round(st.session_state.approval - st.session_state.prev_approval, 1)
d_market = round(st.session_state.market_conf - st.session_state.prev_market, 1)
d_growth = round(st.session_state.growth - st.session_state.prev_growth, 1)
d_headroom = round(st.session_state.headroom - st.session_state.prev_headroom, 1)
d_debt = round(st.session_state.debt - st.session_state.prev_debt, 1)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('Public Approval', f'{round(st.session_state.approval, 1)}%', f'{d_approval:+}%' if d_approval != 0 else '0%')
col2.metric('Market Confidence', f'{round(st.session_state.market_conf, 1)}%', f'{d_market:+}%' if d_market != 0 else '0%')
col3.metric('Economic Growth', f'{round(st.session_state.growth, 1)}%', f'{d_growth:+}%' if d_growth != 0 else '0%')
col4.metric('OBR Headroom', f'£{round(st.session_state.headroom, 1)}B', f'£{d_headroom:+}B' if d_headroom != 0 else '£0B')
col5.metric('National Debt', f'{round(st.session_state.debt, 1)}% of GDP', f'{d_debt:+}%' if d_debt != 0 else '0%', delta_color='inverse')

st.write('')

tab_econ, tab_nation, tab_budget = st.tabs(['📊 Economy & Polls', '🇬🇧 State of the Nation', '💷 The Budget'])
with tab_econ:
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric('National Debt', f'{round(st.session_state.debt, 1)}% of GDP')
    m2.metric('Annual Deficit', f'£{round(st.session_state.deficit, 1)}B')
    m3.metric('Inflation Rate', f'{round(st.session_state.inflation, 1)}%')
    m4.metric('Bank Rate (Interest)', f'{round(st.session_state.interest_rate, 1)}%')
    m5.metric('10-Year Gilt Yield', f'{round(st.session_state.gilt_yield, 1)}%')

    st.markdown('### 📈 Voting Intention Tracker (% Share)')
    df_polls = pd.DataFrame(st.session_state.poll_history).set_index('Year')
    render_polls(df_polls)
    st.caption('Track how public opinion shifts across years based on your economic performance and policy choices.')

with tab_nation:
    country.render()
    
with tab_budget:
    if st.session_state.block == 4:
        budget.render()
    else:
        st.info("💷 The Chancellor's Budget is only delivered in Block 4 (The Autumn Statement) of each year.")

st.write('')

if st.button('← Back to Party Selection'):
    st.session_state.step = 'setup'
    st.rerun()

# ==================== ELECTION NIGHT ENGINE ====================
if st.session_state.year > 5:
    st.subheader('🗳️ GENERAL ELECTION NIGHT: RESULTS')

    score = (st.session_state.approval * 0.65) + (st.session_state.market_conf * 0.35) - (max(-5, min(15, st.session_state.deficit)) * 1.5)
    is_regional = st.session_state.party in ['SNP', 'Plaid Cymru']
    
    # Calculate Seats based on party type!
    if st.session_state.party == 'SNP':
        gov_seats = int(max(9, min(57, 35 + (score - 45) * 1.5)))
        target_seats = 40
        max_possible = 57
        box_color = '#FDF38E'
        text_color = '#000000'
    elif st.session_state.party == 'Plaid Cymru':
        gov_seats = int(max(2, min(32, 10 + (score - 45) * 1.0)))
        target_seats = 15
        max_possible = 32
        box_color = '#005B54'
        text_color = 'white'
    else:
        multiplier = 4.5
        if st.session_state.party in ['Reform UK', 'Green Party']: multiplier = 3.5
        gov_seats = int(max(40, min(450, 326 + (score - 50) * multiplier)))
        target_seats = 326
        max_possible = 650
        
        if st.session_state.party == 'Labour': box_color = '#e4003b'
        elif st.session_state.party == 'Conservative': box_color = '#0087dc'
        elif st.session_state.party == 'Liberal Democrats': box_color = '#faa61a'
        elif st.session_state.party == 'Reform UK': box_color = '#12B6CF'
        else: box_color = '#6AB023'
        text_color = 'white'

    opp_seats = 650 - gov_seats
    
    # Different win conditions for Regional vs National parties
    if is_regional:
        if gov_seats >= target_seats:
            result_text = f'{st.session_state.party} Regional Dominance ({gov_seats}/{max_possible} seats)'
            success_msg = f'Incredible feat! You dominated your region with {gov_seats} seats and hold the balance of power in Westminster.'
            won = True
        else:
            result_text = f'{st.session_state.party} Regional Defeat (Only {gov_seats} seats)'
            box_color = '#555555'
            text_color = 'white'
            won = False
            
        st.markdown(f'''
        <div style='background-color: {box_color}; padding: 20px; border-radius: 10px; color: {text_color}; text-align: center;'>
            <h2>{result_text}</h2>
            <p style='font-size: 18px;'>Your Seats: <b>{gov_seats}</b> | Other UK Seats: <b>{opp_seats}</b> (Regional Target: {target_seats})</p>
        </div>
        ''', unsafe_allow_html=True)
    
    else:
        majority = gov_seats - 326
        if majority >= 0:
            result_text = f'{st.session_state.party} Majority of {majority}'
            success_msg = 'Incredible feat! You survived Hardcore Mode and kept your majority.'
            won = True
        else:
            result_text = f'Hung Parliament (Short by {abs(majority)} seats)'
            box_color = '#555555'
            text_color = 'white'
            won = False

        st.markdown(f'''
        <div style='background-color: {box_color}; padding: 20px; border-radius: 10px; color: {text_color}; text-align: center;'>
            <h2>{result_text}</h2>
            <p style='font-size: 18px;'>Government Seats: <b>{gov_seats}</b> | Opposition Seats: <b>{opp_seats}</b> (Majority needed: 326)</p>
        </div>
        ''', unsafe_allow_html=True)

    st.write('')
    c1, c2, c3 = st.columns(3)
    if is_regional:
        c1.metric('Your Regional Seats', gov_seats)
        c2.metric('Target Seats', target_seats)
    else:
        c1.metric('Governing Party Seats', gov_seats)
        c2.metric('Opposition Seats', opp_seats)
    c3.metric('Final OBR Headroom', f'£{round(st.session_state.headroom, 1)}B')

    if won:
        st.success(success_msg)
        if st.button('Continue to Next Term'):
            st.session_state.term += 1
            st.session_state.year = 1
            st.session_state.block = 1
            st.session_state.step = 'game'
            st.rerun()
    else:
        st.error('The markets and electorate punished your economic management. You lost your mandate.')
        if st.button('Start New Career'):
            st.session_state.clear()
            st.rerun()
    st.stop()


def update_polling_data(current_year):
    gov_party = st.session_state.party
    approval_boost = (st.session_state.approval - 50) * 0.4

    if current_year not in st.session_state.poll_history['Year']:
        st.session_state.poll_history['Year'].append(current_year)
        base_shares = {'Labour': 32, 'Conservative': 30, 'Liberal Democrats': 14, 'Reform UK': 14, 'Green Party': 6, 'SNP': 3, 'Plaid Cymru': 1}
        
        # If the user is a regional party, their national vote share stays small, so we dampen the boost
        if gov_party in ['SNP', 'Plaid Cymru']:
            base_shares[gov_party] += approval_boost * 0.3
        else:
            base_shares[gov_party] += approval_boost

        for p in base_shares:
            if p != gov_party: base_shares[p] -= (approval_boost / 5) + random.uniform(-1, 1)
            else: base_shares[p] += random.uniform(-1, 1)
            
            # Floor limits: Regionals bottom out at 1, Nationals at 5
            floor = 1 if p in ['SNP', 'Plaid Cymru'] else 5
            base_shares[p] = max(floor, round(base_shares[p], 1))

        for p, val in base_shares.items():
            if len(st.session_state.poll_history[p]) < len(st.session_state.poll_history['Year']):
                st.session_state.poll_history[p].append(val)

def snapshot_metrics():
    st.session_state.prev_approval = st.session_state.approval
    st.session_state.prev_market = st.session_state.market_conf
    st.session_state.prev_growth = st.session_state.growth
    st.session_state.prev_headroom = st.session_state.headroom
    st.session_state.prev_debt = st.session_state.debt

def process_block_execution(next_year, next_block, chosen_ideology):
    snapshot_metrics()
    st.session_state.last_ideology = chosen_ideology
    country.apply_decision(chosen_ideology)

    if st.session_state.gilt_yield > 4.5: st.session_state.headroom = round(st.session_state.headroom - 0.8, 1)
    if st.session_state.inflation > 3.0: st.session_state.approval = round(st.session_state.approval - 1.5, 1)

    update_polling_data(next_year)
    st.session_state.active_crisis = scen.pick_next(st.session_state.year, st.session_state.block, chosen_ideology)

    st.session_state.year = next_year
    st.session_state.block = next_block
    st.rerun()

# ==================== ACTIVE CRISIS SCREEN ====================
if st.session_state.active_crisis is not None:
    crisis = scen.get(st.session_state.active_crisis)
    if crisis is None:
        st.session_state.active_crisis = None
        st.rerun()
    crisis_card(crisis['title'])
    
    humphrey_message(crisis['humphrey'])
    
    if st.session_state.get('crisis_reason'):
        st.caption(st.session_state.crisis_reason)
        
    labels = scen.option_labels(crisis)
    crisis_choice = st.radio('Choose emergency response:', labels)
    if st.button('Resolve Crisis'):
        snapshot_metrics()
        st.session_state.message = scen.resolve(crisis, labels.index(crisis_choice))
        st.session_state.active_crisis = None
        st.rerun()
    st.stop()

# ==================== DYNAMIC BLOCK PROGRESSION ====================
if st.session_state.block < 4:
    decision_data = decisions.DECISIONS.get((st.session_state.year, st.session_state.block))
    
    if decision_data:
        st.subheader(f"Year {st.session_state.year} - Block {st.session_state.block}: {decision_data['title']}")
        st.write(decision_data['text'])
        
        humphrey_message(decision_data['humphrey'])
        
        choice = st.radio('Select strategy:', decision_data['options'])
        
        if st.button(f'Execute Block {st.session_state.block}'):
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
        if st.button("Skip Block"):
            process_block_execution(st.session_state.year, st.session_state.block + 1, 'Centric')

elif st.session_state.block == 4:
    st.subheader(f"Year {st.session_state.year} - Block 4: The Chancellor's Budget")
    humphrey_message("A budget, Chancellor, is merely a collection of numbers we present to the House to obscure our true intentions. I have taken the liberty of drafting some 'Special Schemes' to distract the press. Shall we proceed?")
    
    st.info("Head to the '💷 The Budget' tab above to finalize your tax and spending plans for the year.")
    
    if st.button('End Year & Advance to Spring', type='primary'):
        snapshot_metrics() 
        budget.apply_ongoing()
        st.session_state.year += 1
        st.session_state.block = 1
        st.rerun()

news_box(st.session_state.message)
