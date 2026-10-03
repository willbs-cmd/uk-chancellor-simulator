import streamlit as st
import random
import pandas as pd

from theme import apply_theme, header, crisis_card, news_box, render_polls
import country

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

    # Store previous values to calculate live deltas
    st.session_state.prev_approval = 48
    st.session_state.prev_market = 65
    st.session_state.prev_growth = 0.8
    st.session_state.prev_headroom = 8.5
    st.session_state.prev_debt = 98.2

    st.session_state.poll_history = {
        'Year': [1],
        'Labour': [38],
        'Conservative': [32],
        'Liberal Democrats': [12],
        'Reform UK': [10],
        'Green Party': [8]
    }

    st.session_state.message = 'Welcome to Number 11 Downing Street. The economy is fragile, inflation is sticky, and bond markets are watching.'
    st.session_state.initialized = True

if st.session_state.step == 'setup':
    st.title('🏛️ The UK Chancellor Simulator (Hardcore Mode)')
    st.markdown('### Step 1: Choose Your Government')
    st.write('Economic headroom is tight (£8.5B) and debt is nearly 100% of GDP. Select which party is forming the government:')

    party_choice = st.selectbox('Select Governing Party:', [
        'Labour',
        'Conservative',
        'Liberal Democrats',
        'Reform UK',
        'Green Party'
    ])

    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button('Enter Number 11', type='primary'):
            st.session_state.party = party_choice
            if party_choice == 'Conservative':
                st.session_state.approval = 46
                st.session_state.market_conf = 70
                st.session_state.poll_history = {'Year': [1], 'Labour': [32], 'Conservative': [38], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [8]}
            elif party_choice == 'Liberal Democrats':
                st.session_state.approval = 49
                st.session_state.market_conf = 60
                st.session_state.poll_history = {'Year': [1], 'Labour': [30], 'Conservative': [30], 'Liberal Democrats': [24], 'Reform UK': [10], 'Green Party': [6]}
            elif party_choice == 'Reform UK':
                st.session_state.approval = 42
                st.session_state.market_conf = 55
                st.session_state.poll_history = {'Year': [1], 'Labour': [28], 'Conservative': [28], 'Liberal Democrats': [10], 'Reform UK': [26], 'Green Party': [8]}
            elif party_choice == 'Green Party':
                st.session_state.approval = 45
                st.session_state.market_conf = 50
                st.session_state.poll_history = {'Year': [1], 'Labour': [28], 'Conservative': [26], 'Liberal Democrats': [12], 'Reform UK': [8], 'Green Party': [26]}
            else:
                st.session_state.approval = 48
                st.session_state.market_conf = 65
                st.session_state.poll_history = {'Year': [1], 'Labour': [38], 'Conservative': [32], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [8]}

            st.session_state.prev_approval = st.session_state.approval
            st.session_state.prev_market = st.session_state.market_conf
            st.session_state.step = 'game'
            st.rerun()
    with col_b:
        if st.button('Reset Session Cache'):
            st.session_state.clear()
            st.rerun()
    st.stop()

header(st.session_state.party, st.session_state.term, st.session_state.year, st.session_state.block)

# Calculate real-time deltas for top metric bar
d_approval = round(st.session_state.approval - st.session_state.prev_approval, 1)
d_market = round(st.session_state.market_conf - st.session_state.prev_market, 1)
d_growth = round(st.session_state.growth - st.session_state.prev_growth, 1)
d_headroom = round(st.session_state.headroom - st.session_state.prev_headroom, 1)
d_debt = round(st.session_state.debt - st.session_state.prev_debt, 1)

# Top Metric Bar with Green/Red Delta Arrows
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('Public Approval', f'{round(st.session_state.approval, 1)}%', f'{d_approval:+}%' if d_approval != 0 else '0%')
col2.metric('Market Confidence', f'{round(st.session_state.market_conf, 1)}%', f'{d_market:+}%' if d_market != 0 else '0%')
col3.metric('Economic Growth', f'{round(st.session_state.growth, 1)}%', f'{d_growth:+}%' if d_growth != 0 else '0%')
col4.metric('OBR Headroom', f'£{round(st.session_state.headroom, 1)}B', f'£{d_headroom:+}B' if d_headroom != 0 else '£0B')
# Note: For debt, inverse color so an increase in debt is red and a decrease is green
col5.metric('National Debt', f'{round(st.session_state.debt, 1)}% of GDP', f'{d_debt:+}%' if d_debt != 0 else '0%', delta_color='inverse')

st.write('')

# ==================== MACROECONOMIC STATS & POLLS ====================
with st.expander('📊 Macroeconomic Dashboard & Voting Intentions'):
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

country.ensure_state()
with st.expander('🇬🇧 State of the Nation', expanded=True):
    country.render()

st.write('')

if st.button('← Back to Party Selection'):
    st.session_state.step = 'setup'
    st.rerun()

if st.session_state.year > 5:
    st.subheader('🗳️ GENERAL ELECTION NIGHT: RESULTS')

    score = (st.session_state.approval * 0.65) + (st.session_state.market_conf * 0.35) - (st.session_state.deficit * 1.5)
    multiplier = 4.5
    if st.session_state.party in ['Reform UK', 'Green Party']:
        multiplier = 3.5

    gov_seats = int(max(40, min(450, 326 + (score - 50) * multiplier)))
    opp_seats = 650 - gov_seats
    majority = gov_seats - 326

    if majority >= 0:
        result_text = f'{st.session_state.party} Majority of {majority}'
        box_color = '#e4003b' if st.session_state.party == 'Labour' else ('#0087dc' if st.session_state.party == 'Conservative' else ('#faa61a' if st.session_state.party == 'Liberal Democrats' else ('#12B6CF' if st.session_state.party == 'Reform UK' else '#6AB023')))
    else:
        result_text = f'Hung Parliament (Short by {abs(majority)} seats)'
        box_color = '#555555'

    st.markdown(f'''
    <div style='background-color: {box_color}; padding: 20px; border-radius: 10px; color: white; text-align: center;'>
        <h2>{result_text}</h2>
        <p style='font-size: 18px;'>Government Seats: <b>{gov_seats}</b> | Opposition Seats: <b>{opp_seats}</b> (Majority needed: 326)</p>
    </div>
    ''', unsafe_allow_html=True)

    st.write('')
    c1, c2, c3 = st.columns(3)
    c1.metric('Governing Party Seats', gov_seats)
    c2.metric('Opposition Seats', opp_seats)
    c3.metric('Final OBR Headroom', f'£{round(st.session_state.headroom, 1)}B')

    if gov_seats >= 326:
        st.success('Incredible feat! You survived Hardcore Mode and kept your majority.')
        if st.button('Continue to Next Term'):
            st.session_state.term += 1
            st.session_state.year = 1
            st.session_state.block = 1
            st.session_state.step = 'game'
            st.rerun()
    else:
        st.error('The markets and electorate punished your economic management. You lost your majority.')
        if st.button('Start New Career'):
            st.session_state.clear()
            st.rerun()
    st.stop()

def update_polling_data(current_year):
    gov_party = st.session_state.party
    approval_boost = (st.session_state.approval - 50) * 0.4

    if current_year not in st.session_state.poll_history['Year']:
        st.session_state.poll_history['Year'].append(current_year)

        base_shares = {
            'Labour': 32,
            'Conservative': 30,
            'Liberal Democrats': 14,
            'Reform UK': 14,
            'Green Party': 10
        }

        base_shares[gov_party] += approval_boost

        for p in base_shares:
            if p != gov_party:
                base_shares[p] -= (approval_boost / 4) + random.uniform(-2, 2)
            else:
                base_shares[p] += random.uniform(-1, 1)
            base_shares[p] = max(5, round(base_shares[p], 1))

        for p, val in base_shares.items():
            if len(st.session_state.poll_history[p]) < len(st.session_state.poll_history['Year']):
                st.session_state.poll_history[p].append(val)

def snapshot_metrics():
    # Save current metrics as previous values before updating for the next turn
    st.session_state.prev_approval = st.session_state.approval
    st.session_state.prev_market = st.session_state.market_conf
    st.session_state.prev_growth = st.session_state.growth
    st.session_state.prev_headroom = st.session_state.headroom
    st.session_state.prev_debt = st.session_state.debt

def process_block_execution(next_year, next_block, chosen_ideology):
    snapshot_metrics()
    st.session_state.last_ideology = chosen_ideology
    country.apply_decision(chosen_ideology)

    if st.session_state.gilt_yield > 4.5:
        st.session_state.headroom = round(st.session_state.headroom - 0.8, 1)
    if st.session_state.inflation > 3.0:
        st.session_state.approval = round(st.session_state.approval - 1.5, 1)

    update_polling_data(next_year)

    crises_pool = [
        ('🚨 BREAKING: Severe Gilt Market Revolt! Foreign investors dump UK debt as yields surge past 5.5%.',
         'Deploy emergency Bank of England intervention (-£7B Headroom, +8 Market Conf)', 'Refuse intervention and let bond vigilantes feast (-18 Market Conf, +2.5 Debt)'),
        ('🚨 BREAKING: National Health Service Staff Walkout! Nurses and junior doctors launch coordinated strikes.',
         'Meet pay demands in full to avoid collapse (-£6B Headroom, +10 Approval, +0.4 Inflation)', 'Stand firm and invoke emergency service minimums (-12 Approval, -3 Growth)'),
        ('🚨 BREAKING: Major Energy Retailer Bankruptcy! State bailout required to keep lights on.',
         'Absorb company liabilities into public balance sheet (-£5B Headroom, +6 Approval)', 'Let customers scatter to higher tariffs (-9 Approval, +0.5 Inflation)'),
        ('🚨 BREAKING: Public Sector Pension Black Hole Discovered! OBR mandates immediate funding correction.',
         'Inject emergency cash reserves to plug shortfall (-£5.5B Headroom, +5 Market Conf)', 'Cut departmental budgets across the board (-10 Approval, +4 Market Conf)')
    ]

    if st.session_state.last_ideology == 'Hard Left' and random.random() < 0.50:
        linked_crisis = ('🔗 LINKED REACTION (Capital Flight): Your aggressive socialist policies have sparked a sudden flight of millionaires and corporate HQs to Dublin and Frankfurt!',
                         'Offer tax exemptions for multinational executives (-£4B Headroom, +10 Market Conf)',
                         'Double down with emergency capital export controls (-15 Market Conf, +6 Approval)')
        crises_pool.insert(0, linked_crisis)
    elif st.session_state.last_ideology == 'Free-Market' and random.random() < 0.50:
        linked_crisis = ('🔗 LINKED REACTION (Private Utility Failure): Your recent deregulation has caused private water and energy providers to suffer major infrastructure leaks and sewage scandals!',
                         'Bail out the private operators with state emergency grants (-£5B Headroom, -6 Approval)',
                         'Threaten forcible public receivership (-12 Market Conf, +8 Approval)')
        crises_pool.insert(0, linked_crisis)
    elif st.session_state.last_ideology == 'Fiscal Austerity' and random.random() < 0.50:
        linked_crisis = ('🔗 LINKED REACTION (Public Service Collapse): Your deep departmental spending cuts have resulted in crumbling school roofs and prison overcrowding emergencies!',
                         'Issue emergency capital grants to patch facilities (-£4.5B Headroom, +5 Approval)',
                         'Maintain strict budget caps and ride out the public backlash (-10 Approval, +5 Market Conf)')
        crises_pool.insert(0, linked_crisis)

    if random.random() < 0.45 and st.session_state.year < 5:
        st.session_state.active_crisis = random.choice(crises_pool)

    st.session_state.year = next_year
    st.session_state.block = next_block
    st.rerun()

# ==================== ACTIVE CRISIS SCREEN ====================
if st.session_state.active_crisis is not None:
    c_title, c_opt1, c_opt2 = st.session_state.active_crisis
    crisis_card(c_title)
    crisis_choice = st.radio('Choose emergency response:', [c_opt1, c_opt2])
    if st.button('Resolve Crisis'):
        snapshot_metrics()
        country.apply_crisis(c_title, c_opt1 in crisis_choice)
        if c_opt1 in crisis_choice:
            st.session_state.headroom = round(st.session_state.headroom - 6.0, 1)
            st.session_state.approval = round(st.session_state.approval + 5, 1)
            st.session_state.market_conf = round(st.session_state.market_conf + 5, 1)
            st.session_state.gilt_yield = round(st.session_state.gilt_yield - 0.3, 1)
            st.session_state.message = 'Crisis Handled: Expensive intervention stabilized markets.'
        else:
            st.session_state.approval = round(st.session_state.approval - 12, 1)
            st.session_state.market_conf = round(st.session_state.market_conf - 12, 1)
            st.session_state.gilt_yield = round(st.session_state.gilt_yield + 0.7, 1)
            st.session_state.deficit = round(st.session_state.deficit + 0.8, 1)
            st.session_state.message = 'Crisis Handled: Ignored warning signs. Markets and public punish you.'
        st.session_state.active_crisis = None
        st.rerun()
    st.stop()

news_box(st.session_state.message)

# ==================== REGULAR BLOCK PROGRESSION ====================
if st.session_state.year == 1:
    if st.session_state.block == 1:
        st.subheader('Year 1 - Block 1: The Spring Emergency Statement')
        st.write('The NHS and police demand an immediate cash injection to clear backlogs.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left / Socialist) Nationalize key utilities and impose steep wealth taxes.',
            '2. (Social Democratic) Borrow heavily to fund public infrastructure and NHS staff.',
            '3. (Centric) Raid defense spending slightly and implement targeted efficiency savings.',
            '4. (Free-Market / Right) Cut red tape, freeze public spending, and rely on private healthcare.',
            '5. (Fiscal Austerity) Enforce immediate spending freezes and departmental cuts.'
        ])
        if st.button('Execute Block 1'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.headroom = round(st.session_state.headroom + 1.5, 1)
                st.session_state.approval = round(st.session_state.approval + 5, 1)
                st.session_state.market_conf = round(st.session_state.market_conf - 16, 1)
                st.session_state.gilt_yield = round(st.session_state.gilt_yield + 0.6, 1)
                st.session_state.message = 'Wealth taxes enacted! City bond vigilantes trigger a sell-off.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.headroom = round(st.session_state.headroom - 7.0, 1)
                st.session_state.approval = round(st.session_state.approval + 7, 1)
                st.session_state.deficit = round(st.session_state.deficit + 1.2, 1)
                st.session_state.message = 'Keynesian stimulus deployed, but deficit expands.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.headroom = round(st.session_state.headroom - 3.5, 1)
                st.session_state.approval = round(st.session_state.approval + 2, 1)
                st.session_state.message = 'Pragmatic compromise found.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 8, 1)
                st.session_state.approval = round(st.session_state.approval - 7, 1)
                st.session_state.growth = round(st.session_state.growth + 0.2, 1)
                st.session_state.message = 'Deregulation path chosen.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.headroom = round(st.session_state.headroom + 5.0, 1)
                st.session_state.approval = round(st.session_state.approval - 12, 1)
                st.session_state.deficit = round(st.session_state.deficit - 0.9, 1)
                st.session_state.message = 'Austerity applied. Headroom recovered, public outraged.'
            process_block_execution(1, 2, selected_type)

    elif st.session_state.block == 2:
        st.subheader('Year 1 - Block 2: Public Sector Pay & Cabinet Pressure')
        st.write('Public sector unions are threatening widespread strikes over pay freezes.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Meet all union pay demands in full, funded by borrowing.',
            '2. (Social Democratic) Negotiate a generous inflation-matching pay rise linked to tax reforms.',
            '3. (Centric) Offer a balanced compromise settlement to minimize strike disruption.',
            '4. (Free-Market) De-unionize public sectors and introduce competitive private contractor bidding.',
            '5. (Fiscal Austerity) Enforce a strict statutory pay cap and invoke emergency anti-strike laws.'
        ])
        if st.button('Execute Block 2'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.headroom = round(st.session_state.headroom - 8.0, 1)
                st.session_state.approval = round(st.session_state.approval + 10, 1)
                st.session_state.deficit = round(st.session_state.deficit + 1.4, 1)
                st.session_state.inflation = round(st.session_state.inflation + 0.4, 1)
                st.session_state.message = 'Unions appeased, but inflation ticks upward.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.headroom = round(st.session_state.headroom - 4.5, 1)
                st.session_state.approval = round(st.session_state.approval + 6, 1)
                st.session_state.message = 'Fair pay settlement reached.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.approval = round(st.session_state.approval - 4, 1)
                st.session_state.message = 'Compromise struck with minor disruption.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 9, 1)
                st.session_state.approval = round(st.session_state.approval - 10, 1)
                st.session_state.message = 'Private contracting introduced.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.approval = round(st.session_state.approval - 14, 1)
                st.session_state.market_conf = round(st.session_state.market_conf + 10, 1)
                st.session_state.inflation = round(st.session_state.inflation - 0.3, 1)
                st.session_state.message = 'Pay cap enforced. Markets pleased, workforce furious.'
            process_block_execution(1, 3, selected_type)

    elif st.session_state.block == 3:
        st.subheader('Year 1 - Block 3: The Autumn Budget & Fiscal Forecast')
        st.write('The OBR releases its full annual economic and fiscal outlook.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Implement a massive wealth tax and capital controls.',
            '2. (Social Democratic) Invest heavily in green industrial strategy and public R&D.',
            '3. (Centric) Balance tax adjustments with targeted business incentives.',
            '4. (Free-Market) Cut corporation tax to 15% to attract international investment.',
            '5. (Fiscal Austerity) Freeze all departmental budgets in real terms.'
        ])
        if st.button('Execute Block 3 (End of Year 1)'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.headroom = round(st.session_state.headroom + 7.0, 1)
                st.session_state.market_conf = round(st.session_state.market_conf - 20, 1)
                st.session_state.gilt_yield = round(st.session_state.gilt_yield + 0.8, 1)
                st.session_state.message = 'Wealth tax causes capital flight and gilt sell-off.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.growth = round(st.session_state.growth + 0.4, 1)
                st.session_state.headroom = round(st.session_state.headroom - 4.5, 1)
                st.session_state.message = 'Green industrial strategy launched.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.growth = round(st.session_state.growth + 0.2, 1)
                st.session_state.message = 'Pragmatic budget delivered.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 12, 1)
                st.session_state.headroom = round(st.session_state.headroom - 5.5, 1)
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.message = 'Corporation tax slashed.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.headroom = round(st.session_state.headroom + 5.0, 1)
                st.session_state.deficit = round(st.session_state.deficit - 1.0, 1)
                st.session_state.approval = round(st.session_state.approval - 6, 1)
                st.session_state.message = 'Budgets frozen.'
            process_block_execution(2, 1, selected_type)

elif st.session_state.year == 2:
    if st.session_state.block == 1:
        st.subheader('Year 2 - Block 1: Welfare & Long-Term Sickness Reform')
        st.write('Welfare expenditure is spiraling out of control due to rising health claims.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Expand universal credit and eliminate benefit sanctions.',
            '2. (Social Democratic) Increase wrap-around employment support and health coaching.',
            '3. (Centric) Streamline welfare administration with moderate criteria checks.',
            '4. (Free-Market) Privatize employment support services and enforce strict work search rules.',
            '5. (Fiscal Austerity) Severely restrict disability benefits to achieve immediate savings.'
        ])
        if st.button('Execute Block 1'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.headroom = round(st.session_state.headroom - 6.0, 1)
                st.session_state.approval = round(st.session_state.approval + 7, 1)
                st.session_state.message = 'Welfare expanded.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.headroom = round(st.session_state.headroom - 3.5, 1)
                st.session_state.approval = round(st.session_state.approval + 5, 1)
                st.session_state.message = 'Health coaching deployed.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.headroom = round(st.session_state.headroom + 2.0, 1)
                st.session_state.message = 'Moderate welfare checks.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.headroom = round(st.session_state.headroom + 3.5, 1)
                st.session_state.market_conf = round(st.session_state.market_conf + 4, 1)
                st.session_state.approval = round(st.session_state.approval - 7, 1)
                st.session_state.message = 'Employment support outsourced.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.headroom = round(st.session_state.headroom + 7.5, 1)
                st.session_state.approval = round(st.session_state.approval - 16, 1)
                st.session_state.deficit = round(st.session_state.deficit - 1.1, 1)
                st.session_state.message = 'Benefits slashed. Massive public backlash.'
            process_block_execution(2, 2, selected_type)

    elif st.session_state.block == 2:
        st.subheader('Year 2 - Block 2: Financial Regulation & The City')
        st.write('London financial institutions demand deregulation to compete globally.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Impose strict capital controls and break up high-street mega banks.',
            '2. (Social Democratic) Enforce rigorous ethical and green lending standards on banks.',
            '3. (Centric) Maintain balanced international regulatory standards.',
            '4. (Free-Market) Abolish bankers bonus caps and deregulate financial trading rules.',
            '5. (Fiscal Austerity) Levy an emergency banking sector surcharge to clear debt.'
        ])
        if st.button('Execute Block 2'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.market_conf = round(st.session_state.market_conf - 22, 1)
                st.session_state.gilt_yield = round(st.session_state.gilt_yield + 0.7, 1)
                st.session_state.approval = round(st.session_state.approval + 6, 1)
                st.session_state.message = 'Mega banks broken up! Markets plummet.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.market_conf = round(st.session_state.market_conf + 2, 1)
                st.session_state.approval = round(st.session_state.approval + 4, 1)
                st.session_state.message = 'Green lending mandates enacted.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.market_conf = round(st.session_state.market_conf + 3, 1)
                st.session_state.message = 'Regulations maintained.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 14, 1)
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.approval = round(st.session_state.approval - 9, 1)
                st.session_state.message = 'Bonus caps scrapped.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.headroom = round(st.session_state.headroom + 5.5, 1)
                st.session_state.market_conf = round(st.session_state.market_conf - 12, 1)
                st.session_state.message = 'Emergency banking surcharge levied.'
            process_block_execution(2, 3, selected_type)

    elif st.session_state.block == 3:
        st.subheader('Year 2 - Block 3: Mid-Term Spending Review')
        st.write('Local government services face severe funding shortages.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Direct central state funding to municipal councils for direct public housing builds.',
            '2. (Social Democratic) Empower metro mayors with universal local tax-raising and transport powers.',
            '3. (Centric) Provide targeted central bailout grants to struggling councils.',
            '4. (Free-Market) Force councils to privatize municipal assets and services.',
            '5. (Fiscal Austerity) Mandate a 10% across-the-board council spending reduction.'
        ])
        if st.button('Execute Block 3 (End of Year 2)'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.headroom = round(st.session_state.headroom - 5.5, 1)
                st.session_state.approval = round(st.session_state.approval + 7, 1)
                st.session_state.message = 'State council housing funded.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.approval = round(st.session_state.approval + 6, 1)
                st.session_state.growth = round(st.session_state.growth + 0.2, 1)
                st.session_state.message = 'Metro devolution empowered.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.headroom = round(st.session_state.headroom - 4.0, 1)
                st.session_state.message = 'Bailout grants issued.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 6, 1)
                st.session_state.approval = round(st.session_state.approval - 7, 1)
                st.session_state.message = 'Municipal assets privatized.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.headroom = round(st.session_state.headroom + 4.5, 1)
                st.session_state.approval = round(st.session_state.approval - 10, 1)
                st.session_state.message = 'Councils forced into deep cuts.'
            process_block_execution(3, 1, selected_type)

elif st.session_state.year == 3:
    if st.session_state.block == 1:
        st.subheader('Year 3 - Block 1: Regional Transport & Infrastructure')
        st.write('Major regional rail and bus links require strategic capital investment.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Fully public-own and nationalize the entire UK railway network.',
            '2. (Social Democratic) Fund universal bus franchising and regional rail integration.',
            '3. (Centric) Proceed with balanced regional transit upgrades.',
            '4. (Free-Market) Privatize remaining rail infrastructure and invite global private consortia.',
            '5. (Fiscal Austerity) Freeze all major capital transport projects indefinitely.'
        ])
        if st.button('Execute Block 1'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.headroom = round(st.session_state.headroom - 6.5, 1)
                st.session_state.approval = round(st.session_state.approval + 8, 1)
                st.session_state.message = 'Railways fully nationalized.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.approval = round(st.session_state.approval + 6, 1)
                st.session_state.headroom = round(st.session_state.headroom - 4.0, 1)
                st.session_state.message = 'Bus networks integrated.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.growth = round(st.session_state.growth + 0.2, 1)
                st.session_state.headroom = round(st.session_state.headroom - 3.0, 1)
                st.session_state.message = 'Transit upgrades funded.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 8, 1)
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.message = 'Private rail consortia contracted.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.headroom = round(st.session_state.headroom + 4.0, 1)
                st.session_state.approval = round(st.session_state.approval - 6, 1)
                st.session_state.message = 'Infrastructure projects frozen.'
            process_block_execution(3, 2, selected_type)

    elif st.session_state.block == 2:
        st.subheader('Year 3 - Block 2: Housing Supply & Planning Reform')
        st.write('A severe housing shortage is crippling affordability for younger voters.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Implement rent controls and launch a state housebuilding blitz.',
            '2. (Social Democratic) Mandate high social housing quotas on all private developments.',
            '3. (Centric) Overhaul planning laws to streamline local housing approvals.',
            '4. (Free-Market) Abolish planning restrictions and greenbelt protections entirely.',
            '5. (Fiscal Austerity) Protect greenbelt land and offer no state housing intervention.'
        ])
        if st.button('Execute Block 2'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.approval = round(st.session_state.approval + 9, 1)
                st.session_state.market_conf = round(st.session_state.market_conf - 12, 1)
                st.session_state.headroom = round(st.session_state.headroom - 5.5, 1)
                st.session_state.message = 'Rent controls enacted.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.approval = round(st.session_state.approval + 7, 1)
                st.session_state.growth = round(st.session_state.growth + 0.2, 1)
                st.session_state.message = 'Social housing quotas mandated.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.approval = round(st.session_state.approval + 5, 1)
                st.session_state.message = 'Planning laws streamlined.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.growth = round(st.session_state.growth + 0.5, 1)
                st.session_state.approval = round(st.session_state.approval - 9, 1)
                st.session_state.message = 'Greenbelt abolished.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.approval = round(st.session_state.approval - 6, 1)
                st.session_state.message = 'Greenbelt protected.'
            process_block_execution(3, 3, selected_type)

    elif st.session_state.block == 3:
        st.subheader('Year 3 - Block 3: Year 3 Autumn Statement')
        st.write('Mid-term economic check-in with international markets.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Institute a maximum wage cap and steep corporate excess profit taxes.',
            '2. (Social Democratic) Issue sovereign green bonds for nationwide renewable grids.',
            '3. (Centric) Provide balanced R&D tax incentives for technology and AI.',
            '4. (Free-Market) Deregulate energy markets and abolish green levies.',
            '5. (Fiscal Austerity) Maintain rigid spending caps and strict debt reduction targets.'
        ])
        if st.button('Execute Block 3 (End of Year 3)'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.approval = round(st.session_state.approval + 5, 1)
                st.session_state.market_conf = round(st.session_state.market_conf - 16, 1)
                st.session_state.headroom = round(st.session_state.headroom + 4.5, 1)
                st.session_state.message = 'Excess profit taxes levied.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.market_conf = round(st.session_state.market_conf + 9, 1)
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.headroom = round(st.session_state.headroom - 4.0, 1)
                st.session_state.message = 'Green bonds issued.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.message = 'Tech incentives established.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 7, 1)
                st.session_state.approval = round(st.session_state.approval - 5, 1)
                st.session_state.message = 'Green levies abolished.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.headroom = round(st.session_state.headroom + 5.0, 1)
                st.session_state.deficit = round(st.session_state.deficit - 0.8, 1)
                st.session_state.message = 'Spending caps maintained.'
            process_block_execution(4, 1, selected_type)

elif st.session_state.year == 4:
    if st.session_state.block == 1:
        st.subheader('Year 4 - Block 1: Global Energy Shock')
        st.write('Geopolitical tensions cause international gas prices to surge dramatically.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Emergency nationalization of energy producers and price freezes.',
            '2. (Social Democratic) Massive state-backed green retrofitting and insulation drive.',
            '3. (Centric) Targeted energy support grants for vulnerable households.',
            '4. (Free-Market) Fast-track North Sea oil and gas drilling licenses.',
            '5. (Fiscal Austerity) Refuse government intervention and let global markets settle.'
        ])
        if st.button('Execute Block 1'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.approval = round(st.session_state.approval + 10, 1)
                st.session_state.market_conf = round(st.session_state.market_conf - 18, 1)
                st.session_state.headroom = round(st.session_state.headroom - 6.5, 1)
                st.session_state.message = 'Energy sector nationalized.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.headroom = round(st.session_state.headroom - 4.5, 1)
                st.session_state.message = 'Green retrofit drive launched.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.headroom = round(st.session_state.headroom - 3.5, 1)
                st.session_state.approval = round(st.session_state.approval + 4, 1)
                st.session_state.message = 'Energy grants issued.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 9, 1)
                st.session_state.approval = round(st.session_state.approval - 7, 1)
                st.session_state.message = 'Drilling licenses approved.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.approval = round(st.session_state.approval - 14, 1)
                st.session_state.market_conf = round(st.session_state.market_conf - 6, 1)
                st.session_state.message = 'No intervention.'
            process_block_execution(4, 2, selected_type)

    elif st.session_state.block == 2:
        st.subheader('Year 4 - Block 2: Trade & International Tariffs')
        st.write('Major trading partners propose new tariff barriers affecting British exporters.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Retaliate with strict protectionist tariffs and import controls.',
            '2. (Social Democratic) Negotiate comprehensive digital and green trade alignment pacts.',
            '3. (Centric) Pursue standard diplomatic trade negotiations.',
            '4. (Free-Market) Unilateral free trade approach with zero tariffs on all imports.',
            '5. (Fiscal Austerity) Absorb trade friction without policy or budget changes.'
        ])
        if st.button('Execute Block 2'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.approval = round(st.session_state.approval + 4, 1)
                st.session_state.market_conf = round(st.session_state.market_conf - 12, 1)
                st.session_state.inflation = round(st.session_state.inflation + 0.5, 1)
                st.session_state.message = 'Protectionist tariffs applied.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.market_conf = round(st.session_state.market_conf + 7, 1)
                st.session_state.growth = round(st.session_state.growth + 0.2, 1)
                st.session_state.message = 'Trade pact secured.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.growth = round(st.session_state.growth + 0.1, 1)
                st.session_state.message = 'Diplomatic trade talks held.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 10, 1)
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.approval = round(st.session_state.approval - 6, 1)
                st.session_state.message = 'Unilateral free trade adopted.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.growth = round(st.session_state.growth - 0.2, 1)
                st.session_state.message = 'Trade friction ignored.'
            process_block_execution(4, 3, selected_type)

    elif st.session_state.block == 3:
        st.subheader('Year 4 - Block 3: Year 4 Autumn Statement')
        st.write('Preparing the economy for the final year leading to the general election.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Announce a universal basic income pilot funded by wealth taxes.',
            '2. (Social Democratic) Provide universal retraining vouchers and green startup grants.',
            '3. (Centric) Build up fiscal buffers and moderate treasury reserves.',
            '4. (Free-Market) Cut income tax by 2p across the board to stimulate consumer spending.',
            '5. (Fiscal Austerity) Deliver strict spending reductions to lock in fiscal surpluses.'
        ])
        if st.button('Execute Block 3 (End of Year 4)'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.approval = round(st.session_state.approval + 9, 1)
                st.session_state.headroom = round(st.session_state.headroom - 7.5, 1)
                st.session_state.message = 'UBI pilot launched.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.approval = round(st.session_state.approval + 6, 1)
                st.session_state.growth = round(st.session_state.growth + 0.2, 1)
                st.session_state.headroom = round(st.session_state.headroom - 3.5, 1)
                st.session_state.message = 'Retraining vouchers funded.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.headroom = round(st.session_state.headroom + 4.5, 1)
                st.session_state.market_conf = round(st.session_state.market_conf + 7, 1)
                st.session_state.message = 'Fiscal buffers strengthened.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.approval = round(st.session_state.approval + 9, 1)
                st.session_state.headroom = round(st.session_state.headroom - 5.5, 1)
                st.session_state.message = 'Income tax cut.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.headroom = round(st.session_state.headroom + 6.0, 1)
                st.session_state.deficit = round(st.session_state.deficit - 1.0, 1)
                st.session_state.message = 'Surpluses locked in.'
            process_block_execution(5, 1, selected_type)

elif st.session_state.year == 5:
    if st.session_state.block == 1:
        st.subheader('Year 5 - Block 1: Pre-Election Healthcare Push')
        st.write('Waiting lists remain a major electoral vulnerability as the election approaches.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Rebuild NHS capacity strictly via state funding and ban private contractors.',
            '2. (Social Democratic) Launch a massive frontline staff recruitment drive and fund weekend clinics.',
            '3. (Centric) Partner with private healthcare providers to clear backlogs quickly.',
            '4. (Free-Market) Introduce an insurance-based healthcare model with copays.',
            '5. (Fiscal Austerity) Rely on existing NHS efficiencies with no extra funding.'
        ])
        if st.button('Execute Block 1'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.approval = round(st.session_state.approval + 7, 1)
                st.session_state.headroom = round(st.session_state.headroom - 5.5, 1)
                st.session_state.message = 'Private contractors banned.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.approval = round(st.session_state.approval + 8, 1)
                st.session_state.headroom = round(st.session_state.headroom - 4.5, 1)
                st.session_state.message = 'Staff recruitment funded.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.approval = round(st.session_state.approval + 5, 1)
                st.session_state.headroom = round(st.session_state.headroom - 3.5, 1)
                st.session_state.message = 'Private capacity utilized.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.market_conf = round(st.session_state.market_conf + 9, 1)
                st.session_state.approval = round(st.session_state.approval - 16, 1)
                st.session_state.message = 'Insurance model introduced. Major backlash.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.approval = round(st.session_state.approval - 7, 1)
                st.session_state.message = 'No extra NHS funds.'
            process_block_execution(5, 2, selected_type)

    elif st.session_state.block == 2:
        st.subheader('Year 5 - Block 2: Final Pre-Election Tax & Spend Adjustments')
        st.write('Special interest groups lobby heavily ahead of the final manifesto commitments.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Implement a wealth tax and fund universal public services.',
            '2. (Social Democratic) Deliver targeted cost-of-living cash support to low-income families.',
            '3. (Centric) Increase defense spending to 2.5% of GDP and protect pensions.',
            '4. (Free-Market) Abolish stamp duty and inheritance tax.',
            '5. (Fiscal Austerity) Hold firm on spending caps and protect fiscal rules.'
        ])
        if st.button('Execute Block 2'):
            selected_type = 'Centric'
            if '1.' in choice:
                selected_type = 'Hard Left'
                st.session_state.approval = round(st.session_state.approval + 8, 1)
                st.session_state.headroom = round(st.session_state.headroom - 4.5, 1)
                st.session_state.message = 'Wealth taxes pledged.'
            elif '2.' in choice:
                selected_type = 'Social Democratic'
                st.session_state.approval = round(st.session_state.approval + 9, 1)
                st.session_state.headroom = round(st.session_state.headroom - 4.5, 1)
                st.session_state.message = 'Cost-of-living support delivered.'
            elif '3.' in choice:
                selected_type = 'Centric'
                st.session_state.approval = round(st.session_state.approval + 5, 1)
                st.session_state.headroom = round(st.session_state.headroom - 3.5, 1)
                st.session_state.message = 'Defense and pensions secured.'
            elif '4.' in choice:
                selected_type = 'Free-Market'
                st.session_state.approval = round(st.session_state.approval + 7, 1)
                st.session_state.market_conf = round(st.session_state.market_conf + 7, 1)
                st.session_state.headroom = round(st.session_state.headroom - 5.5, 1)
                st.session_state.message = 'Taxes abolished.'
            else:
                selected_type = 'Fiscal Austerity'
                st.session_state.market_conf = round(st.session_state.market_conf + 9, 1)
                st.session_state.message = 'Spending caps held firm.'
            process_block_execution(5, 3, selected_type)

    elif st.session_state.block == 3:
        st.subheader('Year 5 - Block 3: The General Election Budget & Manifesto Pitch')
        st.write('The final moment. Deliver your pre-election budget pitch to the country.')
        choice = st.radio('Select strategy:', [
            '1. (Hard Left) Radical socialist transformation (Public ownership, wealth taxes, universal services).',
            '2. (Social Democratic) Social democratic renewal (Green investment, NHS expansion, fair taxes).',
            '3. (Centric) Pragmatic center-ground platform (Balanced budgets, moderate reforms, steady growth).',
            '4. (Free-Market) Free-market revolution (Massive tax cuts, deregulation, lean state).',
            '5. (Fiscal Austerity) Uncompromising fiscal orthodoxy (Zero deficit, strict debt reduction).'
        ])
        if st.button('Face the Electorate & Vote'):
            if '1.' in choice:
                st.session_state.approval = round(st.session_state.approval + 10, 1)
                st.session_state.headroom = max(0, st.session_state.headroom - 5.0)
                st.session_state.message = 'Manifesto pitched.'
            elif '2.' in choice:
                st.session_state.approval = round(st.session_state.approval + 10, 1)
                st.session_state.growth = round(st.session_state.growth + 0.3, 1)
                st.session_state.message = 'Social democratic platform set.'
            elif '3.' in choice:
                st.session_state.approval = round(st.session_state.approval + 7, 1)
                st.session_state.market_conf = round(st.session_state.market_conf + 7, 1)
                st.session_state.message = 'Pragmatic platform set.'
            elif '4.' in choice:
                st.session_state.market_conf = round(st.session_state.market_conf + 12, 1)
                st.session_state.approval = round(st.session_state.approval + 3, 1)
                st.session_state.message = 'Free-market platform set.'
            else:
                st.session_state.market_conf = round(st.session_state.market_conf + 16, 1)
                st.session_state.approval = round(st.session_state.approval - 10, 1)
                st.session_state.message = 'Austerity platform set.'
            st.session_state.year = 6
            st.rerun()
