import streamlit as st
import random

st.set_page_config(page_title='UK Chancellor Simulator', layout='wide')

if 'initialized' not in st.session_state or st.session_state.get('step') is None:
    st.session_state.step = 'setup'
    st.session_state.party = 'Labour'
    st.session_state.approval = 50
    st.session_state.market_conf = 70
    st.session_state.debt = 95.1
    st.session_state.growth = 1.1
    st.session_state.headroom = 15.0
    st.session_state.year = 1
    st.session_state.block = 1
    st.session_state.term = 1
    st.session_state.active_crisis = None
    st.session_state.message = 'Welcome to Number 11 Downing Street. Your parliamentary term begins.'
    st.session_state.initialized = True

if st.session_state.step == 'setup':
    st.title('🏛️ The UK Chancellor Simulator')
    st.markdown('### Step 1: Choose Your Government')
    st.write('Before taking the reins at Number 11, select which political party is forming the government:')
    
    party_choice = st.selectbox('Select Governing Party:', ['Labour', 'Conservative', 'Liberal Democrats'])
    
    col_a, col_b = st.columns([1, 4])
    with col_a:
        if st.button('Enter Number 11', type='primary'):
            st.session_state.party = party_choice
            if party_choice == 'Conservative':
                st.session_state.approval = 48
                st.session_state.market_conf = 75
            elif party_choice == 'Liberal Democrats':
                st.session_state.approval = 52
                st.session_state.market_conf = 65
            st.session_state.step = 'game'
            st.rerun()
    with col_b:
        if st.button('Reset Session Cache'):
            st.session_state.clear()
            st.rerun()
    st.stop()

st.title(f'🏛️ {st.session_state.party} Government: Chancellor Simulator')
st.markdown(f'### Term {st.session_state.term} | Year {st.session_state.year} of 5 (Decision Block {st.session_state.block} of 3)')

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('Public Approval', f'{st.session_state.approval}%')
col2.metric('Market Confidence', f'{st.session_state.market_conf}%')
col3.metric('National Debt', f'{st.session_state.debt}% of GDP')
col4.metric('Economic Growth', f'{st.session_state.growth}%')
col5.metric('OBR Headroom', f'£{st.session_state.headroom:.1f}B')

st.divider()

if st.button('← Back to Party Selection'):
    st.session_state.step = 'setup'
    st.rerun()

if st.session_state.year > 5:
    st.subheader('🗳️ GENERAL ELECTION NIGHT: RESULTS')
    
    score = (st.session_state.approval * 0.7) + (st.session_state.market_conf * 0.3)
    if st.session_state.party == 'Labour':
        gov_seats = int(max(150, min(450, 326 + (score - 50) * 4)))
    elif st.session_state.party == 'Conservative':
        gov_seats = int(max(120, min(440, 326 + (score - 50) * 4)))
    else:
        gov_seats = int(max(80, min(380, 250 + (score - 50) * 3)))
        
    opp_seats = 650 - gov_seats
    majority = gov_seats - 326
    
    if majority >= 0:
        result_text = f'{st.session_state.party} Majority of {majority}'
        box_color = '#e4003b' if st.session_state.party == 'Labour' else ('#0087dc' if st.session_state.party == 'Conservative' else '#faa61a')
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
    c3.metric('Final OBR Headroom', f'£{st.session_state.headroom:.1f}B')

    if gov_seats >= 326:
        st.success('Landslide or stable victory! You have secured another term in Downing Street.')
        if st.button('Continue to Next Term'):
            st.session_state.term += 1
            st.session_state.year = 1
            st.session_state.block = 1
            st.session_state.step = 'game'
            st.rerun()
    else:
        st.error('You lost your majority at the ballot box! Time to pack your bags.')
        if st.button('Start New Career'):
            st.session_state.clear()
            st.rerun()
    st.stop()

st.info(st.session_state.message)

# ==================== EXPANDED BREAKING CRISIS CHECK ====================
if st.session_state.active_crisis is None and random.random() < 0.40 and st.session_state.year < 5:
    crises_pool = [
        ('🚨 BREAKING: Bond Market Panic! Yields on UK gilts are spiking rapidly following international rumors.', 
         'Bail out gilt markets with a £5B treasury backstop (-£5B Headroom, +10 Market Conf)', 'Ignore and let bond vigilantes test the currency (-15 Market Conf, +1 Debt)'),
        ('🚨 BREAKING: Major Hospital Cyberattack! Core NHS patient databases locked down across trusts.', 
         'Approve emergency private cybersecurity contractors (-£3B Headroom, +5 Approval)', 'Refuse extra funds and rely on internal IT teams (-8 Approval, -5 Market Conf)'),
        ('🚨 BREAKING: Severe Flash Flooding Hits Regional Towns! Hundreds of homes submerged.', 
         'Deploy an immediate £4B emergency flood-defence relief package (-£4B Headroom, +8 Approval)', 'Offer standard insurance support only (-10 Approval)'),
        ('🚨 BREAKING: Historic Steelworks Threatens Immediate Closure! Thousands of jobs on the line.', 
         'Provide a state nationalization rescue bridge loan (-£6B Headroom, +6 Approval, -5 Market Conf)', 'Let market forces decide and allow plant closure (-12 Approval, +2 Growth)'),
        ('🚨 BREAKING: National Rail Network Strikes Loom! Train drivers announce indefinite walkouts.', 
         'Bust the strike with above-inflation pay concessions (-£5B Headroom, +8 Approval)', 'Stand firm against union demands and endure travel chaos (-10 Approval, -4 Growth)'),
        ('🚨 BREAKING: Energy Supplier Collapse! A major household energy provider goes bust overnight.', 
         'Inject emergency taxpayer funds to absorb customer accounts (-£4B Headroom, +6 Approval)', 'Let customers transfer automatically with higher standing charges (-8 Approval)')
    ]
    st.session_state.active_crisis = random.choice(crises_pool)

if st.session_state.active_crisis is not None:
    c_title, c_opt1, c_opt2 = st.session_state.active_crisis
    st.error(c_title)
    crisis_choice = st.radio('Choose emergency response:', [c_opt1, c_opt2])
    if st.button('Resolve Crisis'):
        if c_opt1 in crisis_choice:
            st.session_state.headroom -= 4.5
            st.session_state.approval += 6
            st.session_state.market_conf += 4
            st.session_state.message = 'Crisis Handled: Swift intervention stabilized the situation.'
        else:
            st.session_state.approval -= 10
            st.session_state.market_conf -= 8
            st.session_state.message = 'Crisis Handled: Ignored intervention to save cash. Trust takes a hit.'
        st.session_state.active_crisis = None
        st.rerun()
    st.stop()

# ==================== REGULAR BLOCK PROGRESSION ====================
if st.session_state.year == 1:
    if st.session_state.block == 1:
        st.subheader('Year 1 - Block 1: The Spring Emergency Statement')
        st.write('The NHS and police demand an immediate cash injection to clear backlogs.')
        choice = st.radio('Select strategy:', [
            '1. Raid Defence spending to cover the immediate shortfall.',
            '2. Borrow directly and expand the deficit.',
            '3. Raise Income Tax by 2% immediately.'
        ])
        if st.button('Execute Block 1'):
            if '1.' in choice:
                st.session_state.headroom -= 4.0
                st.session_state.approval += 2
                st.session_state.message = 'Defence raided. Hawks are angry, but markets are steady.'
            elif '2.' in choice:
                st.session_state.headroom -= 10.0
                st.session_state.market_conf -= 10
                st.session_state.message = 'Borrowed cash. Headroom takes a major hit.'
            else:
                st.session_state.approval -= 12
                st.session_state.market_conf += 5
                st.session_state.message = 'Tax hiked. Public trust plunges.'
            st.session_state.block = 2
            st.rerun()

    elif st.session_state.block == 2:
        st.subheader('Year 1 - Block 2: Public Sector Pay & Cabinet Pressure')
        st.write('Public sector unions are threatening widespread strikes over pay freezes.')
        choice = st.radio('Select strategy:', [
            '1. Give teachers and nurses a full inflation-matching pay rise.',
            '2. Offer a sub-inflation settlement and risk targeted strikes.',
            '3. Stand firm with a total pay freeze and invoke emergency anti-strike laws.'
        ])
        if st.button('Execute Block 2'):
            if '1.' in choice:
                st.session_state.headroom -= 6.0
                st.session_state.approval += 10
                st.session_state.message = 'Pay rise funded! Unions appeased, headroom shrinks.'
            elif '2.' in choice:
                st.session_state.approval -= 4
                st.session_state.message = 'Compromise offer made. Disruptive strikes continue.'
            else:
                st.session_state.approval -= 10
                st.session_state.market_conf += 8
                st.session_state.message = 'Pay frozen. Markets love the discipline; workforce furious.'
            st.session_state.block = 3
            st.rerun()

    elif st.session_state.block == 3:
        st.subheader('Year 1 - Block 3: The Autumn Budget & Fiscal Forecast')
        st.write('The OBR releases its full annual economic and fiscal outlook.')
        choice = st.radio('Select strategy:', [
            '1. Announce capital investment incentives to juice business confidence.',
            '2. Implement spending cuts across government departments to rebuild headroom.',
            '3. Do nothing and let current tax and spend trajectories run.'
        ])
        if st.button('Execute Block 3 (End of Year 1)'):
            if '1.' in choice:
                st.session_state.growth += 0.3
                st.session_state.headroom -= 3.0
                st.session_state.message = 'Investment incentives launched! Growth ticks up.'
            elif '2.' in choice:
                st.session_state.headroom += 6.0
                st.session_state.approval -= 6
                st.session_state.message = 'Departments squeezed. Headroom restored.'
            else:
                st.session_state.debt += 1.0
                st.session_state.message = 'Maintained course. Deficit edges higher.'
            st.session_state.year = 2
            st.session_state.block = 1
            st.rerun()

elif st.session_state.year == 2:
    if st.session_state.block == 1:
        st.subheader('Year 2 - Block 1: Welfare & Long-Term Sickness Reform')
        st.write('Welfare expenditure is spiraling out of control due to rising health claims.')
        choice = st.radio('Select strategy:', [
            '1. Overhaul disability benefits and restrict eligibility criteria.',
            '2. Increase employment support funding without cutting benefits.',
            '3. Leave the welfare system untouched.'
        ])
        if st.button('Execute Block 1'):
            if '1.' in choice:
                st.session_state.headroom += 7.0
                st.session_state.approval -= 12
                st.session_state.message = 'Benefits tightened. Significant savings achieved.'
            elif '2.' in choice:
                st.session_state.headroom -= 4.0
                st.session_state.approval += 6
                st.session_state.message = 'Support expanded. Long-term outlook improves.'
            else:
                st.session_state.debt += 1.5
                st.session_state.message = 'Welfare left untouched.'
            st.session_state.block = 2
            st.rerun()

    elif st.session_state.block == 2:
        st.subheader('Year 2 - Block 2: Financial Regulation & The City')
        st.write('London financial institutions demand deregulation to compete globally.')
        choice = st.radio('Select strategy:', [
            '1. Deregulate banking rules and lower corporation tax for financial firms.',
            '2. Maintain strict consumer protections and anti-money laundering controls.',
            '3. Impose a temporary windfall tax on banking profits.'
        ])
        if st.button('Execute Block 2'):
            if '1.' in choice:
                st.session_state.market_conf += 12
                st.session_state.approval -= 5
                st.session_state.message = 'City rules loosened! Markets rejoice.'
            elif '2.' in choice:
                st.session_state.market_conf += 3
                st.session_state.message = 'Regulations upheld.'
            else:
                st.session_state.market_conf -= 15
                st.session_state.headroom += 5.0
                st.session_state.message = 'Windfall tax levied!'
            st.session_state.block = 3
            st.rerun()

    elif st.session_state.block == 3:
        st.subheader('Year 2 - Block 3: Mid-Term Spending Review')
        st.write('Local government services face severe funding shortages.')
        choice = st.radio('Select strategy:', [
            '1. Decentralize tax-raising powers to local metro mayors.',
            '2. Provide targeted central government bailout grants.',
            '3. Force councils to handle cuts locally through asset sales.'
        ])
        if st.button('Execute Block 3 (End of Year 2)'):
            if '1.' in choice:
                st.session_state.approval += 6
                st.session_state.growth += 0.2
                st.session_state.message = 'Devolution empowered!'
            elif '2.' in choice:
                st.session_state.headroom -= 4.0
                st.session_state.message = 'Bailouts issued.'
            else:
                st.session_state.approval -= 8
                st.session_state.message = 'Councils forced to sell assets.'
            st.session_state.year = 3
            st.session_state.block = 1
            st.rerun()

elif st.session_state.year == 3:
    if st.session_state.block == 1:
        st.subheader('Year 3 - Block 1: Regional Transport & Infrastructure')
        st.write('Major regional rail and bus links require strategic capital investment.')
        choice = st.radio('Select strategy:', [
            '1. Fund universal bus franchising and local transit integration.',
            '2. Prioritize high-speed intercity rail lines.',
            '3. Freeze major capital infrastructure projects to save cash.'
        ])
        if st.button('Execute Block 1'):
            if '1.' in choice:
                st.session_state.approval += 7
                st.session_state.headroom -= 3.5
                st.session_state.message = 'Bus networks integrated!'
            elif '2.' in choice:
                st.session_state.growth += 0.4
                st.session_state.headroom -= 7.0
                st.session_state.message = 'Rail investment backed!'
            else:
                st.session_state.headroom += 4.0
                st.session_state.approval -= 5
                st.session_state.message = 'Projects frozen.'
            st.session_state.block = 2
            st.rerun()

    elif st.session_state.block == 2:
        st.subheader('Year 3 - Block 2: Housing Supply & Planning Reform')
        st.write('A severe housing shortage is crippling affordability for younger voters.')
        choice = st.radio('Select strategy:', [
            '1. Overhaul planning laws to mandate local housing targets.',
            '2. Provide government-backed first-time buyer mortgages.',
            '3. Protect greenbelt land and leave planning controls as they are.'
        ])
        if st.button('Execute Block 2'):
            if '1.' in choice:
                st.session_state.approval += 8
                st.session_state.growth += 0.3
                st.session_state.message = 'Planning reformed!'
            elif '2.' in choice:
                st.session_state.approval += 4
                st.session_state.market_conf -= 5
                st.session_state.message = 'Mortgages backed!'
            else:
                st.session_state.approval -= 4
                st.session_state.message = 'Greenbelt protected.'
            st.session_state.block = 3
            st.rerun()

    elif st.session_state.block == 3:
        st.subheader('Year 3 - Block 3: Year 3 Autumn Statement')
        st.write('Mid-term economic check-in with international markets.')
        choice = st.radio('Select strategy:', [
            '1. Introduce tax incentives for artificial intelligence and tech research.',
            '2. Implement broad public sector efficiency targets.',
            '3. Maintain current fiscal settings.'
        ])
        if st.button('Execute Block 3 (End of Year 3)'):
            if '1.' in choice:
                st.session_state.growth += 0.4
                st.session_state.market_conf += 5
                st.session_state.message = 'Tech incentives launched!'
            elif '2.' in choice:
                st.session_state.headroom += 5.0
                st.session_state.approval -= 3
                st.session_state.message = 'Efficiency targets set.'
            else:
                st.session_state.message = 'Fiscal settings maintained.'
            st.session_state.year = 4
            st.session_state.block = 1
            st.rerun()

elif st.session_state.year == 4:
    if st.session_state.block == 1:
        st.subheader('Year 4 - Block 1: Global Energy Shock')
        st.write('Geopolitical tensions cause international gas prices to surge dramatically.')
        choice = st.radio('Select strategy:', [
            '1. Launch a massive state-backed green retrofitting drive.',
            '2. Fast-track new North Sea oil and gas drilling licenses.',
            '3. Cap household energy bills via direct government borrowing.'
        ])
        if st.button('Execute Block 1'):
            if '1.' in choice:
                st.session_state.growth += 0.3
                st.session_state.headroom -= 5.0
                st.session_state.message = 'Green retrofit launched!'
            elif '2.' in choice:
                st.session_state.market_conf += 8
                st.session_state.approval -= 6
                st.session_state.message = 'Drilling approved!'
            else:
                st.session_state.debt += 2.5
                st.session_state.approval += 10
                st.session_state.message = 'Bills capped!'
            st.session_state.block = 2
            st.rerun()

    elif st.session_state.block == 2:
        st.subheader('Year 4 - Block 2: Trade & International Tariffs')
        st.write('Major trading partners propose new tariff barriers affecting British exporters.')
        choice = st.radio('Select strategy:', [
            '1. Negotiate a comprehensive digital and green trade alignment pact.',
            '2. Retaliate with counter-tariffs to protect domestic manufacturing.',
            '3. Absorb trade friction without policy intervention.'
        ])
        if st.button('Execute Block 2'):
            if '1.' in choice:
                st.session_state.market_conf += 8
                st.session_state.growth += 0.2
                st.session_state.message = 'Trade pact secured!'
            elif '2.' in choice:
                st.session_state.market_conf -= 6
                st.session_state.approval += 4
                st.session_state.message = 'Counter-tariffs applied.'
            else:
                st.session_state.growth -= 0.2
                st.session_state.message = 'Trade friction ignored.'
            st.session_state.block = 3
            st.rerun()

    elif st.session_state.block == 3:
        st.subheader('Year 4 - Block 3: Year 4 Autumn Statement')
        st.write('Preparing the economy for the final year leading to the general election.')
        choice = st.radio('Select strategy:', [
            '1. Target R&D tax credits toward green energy startups.',
            '2. Build up fiscal buffers and treasury reserves.',
            '3. Cut stamp duty to stimulate the property market.'
        ])
        if st.button('Execute Block 3 (End of Year 4)'):
            if '1.' in choice:
                st.session_state.growth += 0.3
                st.session_state.headroom -= 3.0
                st.session_state.message = 'Green startups boosted!'
            elif '2.' in choice:
                st.session_state.headroom += 5.0
                st.session_state.market_conf += 10
                st.session_state.message = 'Fiscal buffers strengthened.'
            else:
                st.session_state.approval += 4
                st.session_state.headroom -= 2.0
                st.session_state.message = 'Stamp duty cut!'
            st.session_state.year = 5
            st.session_state.block = 1
            st.rerun()

elif st.session_state.year == 5:
    if st.session_state.block == 1:
        st.subheader('Year 5 - Block 1: Pre-Election Healthcare Push')
        st.write('Waiting lists remain a major electoral vulnerability as the election approaches.')
        choice = st.radio('Select strategy:', [
            '1. Fund weekend NHS clinics using private sector capacity.',
            '2. Launch a major recruitment drive for frontline medical staff.',
            '3. Rely on existing efficiency measures within the health service.'
        ])
        if st.button('Execute Block 1'):
            if '1.' in choice:
                st.session_state.approval += 7
                st.session_state.headroom -= 4.0
                st.session_state.message = 'Weekend clinics funded!'
            elif '2.' in choice:
                st.session_state.approval += 5
                st.session_state.headroom -= 5.0
                st.session_state.message = 'Staff recruitment backed!'
            else:
                st.session_state.approval -= 4
                st.session_state.message = 'No extra funds deployed.'
            st.session_state.block = 2
            st.rerun()

    elif st.session_state.block == 2:
        st.subheader('Year 5 - Block 2: Final Pre-Election Tax & Spend Adjustments')
        st.write('Special interest groups lobby heavily ahead of the final manifesto commitments.')
        choice = st.radio('Select strategy:', [
            '1. Increase defense spending to 2.5% of GDP.',
            '2. Provide targeted cost-of-living cash support to low-income households.',
            '3. Hold firm on spending caps to protect fiscal headroom.'
        ])
        if st.button('Execute Block 2'):
            if '1.' in choice:
                st.session_state.approval += 4
                st.session_state.market_conf += 6
                st.session_state.headroom -= 4.0
                st.session_state.message = 'Defense commitment strengthened!'
            elif '2.' in choice:
                st.session_state.approval += 9
                st.session_state.headroom -= 5.0
                st.session_state.message = 'Cost-of-living support delivered!'
            else:
                st.session_state.market_conf += 8
                st.session_state.message = 'Spending caps held firm.'
            st.session_state.block = 3
            st.rerun()

    elif st.session_state.block == 3:
        st.subheader('Year 5 - Block 3: The General Election Budget & Manifesto Pitch')
        st.write('The final moment. Deliver your pre-election budget pitch to the country.')
        choice = st.radio('Select strategy:', [
            '1. Unfreeze income tax thresholds and deliver a voter-friendly middle-class tax cut.',
            '2. Establish a landmark Sovereign Wealth Fund funded by carbon dividends.',
            '3. Deliver strict, orthodox fiscal austerity to prove uncompromising financial discipline.'
        ])
        if st.button('Face the Electorate & Vote'):
            if '1.' in choice:
                st.session_state.approval += 12
                st.session_state.headroom = max(0, st.session_state.headroom - 6.0)
                st.session_state.message = 'Final Budget Delivered: Tax cuts energize the voting base.'
            elif '2.' in choice:
                st.session_state.approval += 10
                st.session_state.market_conf += 12
                st.session_state.growth += 0.4
                st.session_state.message = 'Final Budget Delivered: Sovereign Wealth Fund launched.'
            else:
                st.session_state.market_conf += 18
                st.session_state.approval -= 10
                st.session_state.message = 'Final Budget Delivered: Austerity budget delivered.'
            st.session_state.year = 6
            st.rerun()

