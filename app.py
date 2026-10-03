import streamlit as st
import random
import pandas as pd

from theme import apply_theme, header, crisis_card, news_box, render_polls, humphrey_message, render_newspapers, stat_card, render_imf_table
import country
import budget
import decisions
import scenarios as scen

st.set_page_config(page_title='UK Chancellor Simulator - Hardcore', layout='wide')
apply_theme()

# ==================== INITIALIZATION ====================
# SAFETY RESET: If your save file is missing new variables, wipe it to prevent crashes!
required_keys = ['pm_opinion', 'prev_pm', 'imf_bailout']
if 'initialized' in st.session_state and not all(k in st.session_state for k in required_keys):
    st.session_state.clear()
    st.rerun()

if 'initialized' not in st.session_state or st.session_state.get('step') is None:
    st.session_state.step = 'setup'
    st.session_state.party = 'Labour'
    st.session_state.year = 1
    st.session_state.block = 1
    st.session_state.term = 1
    st.session_state.active_crisis = None
    st.session_state.last_ideology = None
    st.session_state.headlines = None
    st.session_state.budget_passed = False
    st.session_state.sacked = False
    st.session_state.imf_bailout = False
    
    st.session_state.pledges = []
    st.session_state.broken_pledges = []
    st.session_state.approval_cap = 100
    st.session_state.macro_cycle = 'Stagnation'

    # Economic Stats (Deficit adjusted to represent actual £ Billions for a ~£2.3T economy)
    st.session_state.approval = 48.0
    st.session_state.market_conf = 65.0
    st.session_state.debt = 98.2
    st.session_state.deficit = 125.4
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

    st.session_state.message = ""
    st.session_state.initialized = True

# ==================== LOGIC FUNCTIONS ====================
def _clip(val, minimum=0.0, maximum=None):
    cap = maximum if maximum else st.session_state.get('approval_cap', 100)
    return max(minimum, min(cap, val))

def check_pledges():
    s = st.session_state
    if 'budget_applied' not in s: return
    b = s.budget_applied
    broken_this_turn = []
    
    if "Never raise Basic Income Tax" in s.pledges and b['tax']['inc_basic'] > 20 and "Never raise Basic Income Tax" not in s.broken_pledges:
        broken_this_turn.append("Never raise Basic Income Tax")
    if "Never raise VAT" in s.pledges and b['tax']['vat'] > 20 and "Never raise VAT" not in s.broken_pledges:
        broken_this_turn.append("Never raise VAT")
    if "Never raise Corporation Tax" in s.pledges and b['tax']['corp'] > 25 and "Never raise Corporation Tax" not in s.broken_pledges:
        broken_this_turn.append("Never raise Corporation Tax")
    if "Protect NHS Funding" in s.pledges and s.dept_spend['health'] < 215.0 and "Protect NHS Funding" not in s.broken_pledges:
        broken_this_turn.append("Protect NHS Funding")
    if "Eliminate the Deficit" in s.pledges and s.deficit > 0 and s.year == 5 and "Eliminate the Deficit" not in s.broken_pledges:
        broken_this_turn.append("Eliminate the Deficit")
        
    for p in broken_this_turn:
        s.broken_pledges.append(p)
        s.approval_cap -= 15
        s.approval = _clip(s.approval - 15)
        s.media_opinion = _clip(s.media_opinion - 25, 0, 100)
        s.message += f" 🚨 U-TURN SCANDAL: You broke your manifesto pledge: '{p}'. The press is tearing you apart!"

def shift_macro_cycle():
    s = st.session_state
    cycles = ['Boom', 'Stagnation', 'Recession']
    if random.random() < 0.20:
        old = s.macro_cycle
        s.macro_cycle = random.choice([c for c in cycles if c != old])
        s.message += f" 🌍 GLOBAL MACRO SHIFT: The world economy has entered a {s.macro_cycle}."

def check_imf_bailout():
    s = st.session_state
    if s.debt > 120 and s.market_conf < 15 and not s.imf_bailout:
        s.imf_bailout = True

def get_imf_projections():
    s = st.session_state
    cycle = s.macro_cycle
    
    g_mod = 1.2 if cycle == 'Boom' else (-1.5 if cycle == 'Recession' else 0.1)
    i_mod = 0.8 if cycle == 'Boom' else (-1.0 if cycle == 'Recession' else -0.2)
    d_mod = -1.5 if cycle == 'Boom' else (3.0 if cycle == 'Recession' else 0.5)
    
    y2_g = round(s.growth + g_mod + random.uniform(-0.2, 0.2), 1)
    y3_g = round(s.growth + (g_mod * 1.5) + random.uniform(-0.3, 0.3), 1)
    
    y2_i = max(0.1, round(s.inflation + i_mod + random.uniform(-0.2, 0.2), 1))
    y3_i = max(0.1, round(s.inflation + (i_mod * 1.5) + random.uniform(-0.3, 0.3), 1))
    
    # Approx convert £B cash deficit back to % GDP for the projection
    y2_d = round(s.debt + (s.deficit / 23.0) + d_mod, 1)
    y3_d = round(y2_d + (s.deficit / 23.0) + (d_mod * 1.5), 1)

    data = {
        "Metric": ["GDP Growth", "Inflation (CPI)", "National Debt (% GDP)"],
        f"Year {s.year} (Current)": [f"{s.growth}%", f"{s.inflation}%", f"{s.debt}%"],
        f"Year {s.year + 1}": [f"{y2_g}%", f"{y2_i}%", f"{y2_d}%"],
        f"Year {s.year + 2}": [f"{y3_g}%", f"{y3_i}%", f"{y3_d}%"]
    }
    return pd.DataFrame(data)

def generate_headlines(ideology, is_budget=False, headroom=0):
    if is_budget:
        if headroom > 2.0: return ("AUSTERITY BUDGET IGNORES THE POOR", "CHANCELLOR BUILDS FISCAL FORTRESS", "A PRUDENT BUDGET AT LAST")
        elif headroom < -2.0: return ("END TO AUSTERITY!", "MARKETS PANIC OVER DEFICIT SPENDING", "RECKLESS BORROWING THREATENS ECONOMY")
        else: return ("A MIXED BAG FOR WORKERS", "CHANCELLOR WALKS THE TIGHTROPE", "PLAYING IT SAFE BEFORE ELECTION")
            
    headlines = {
        'Hard Left': (
            random.choice(["POWER TO THE PEOPLE!", "BOLD REFORMS AT LAST", "CHANCELLOR TAKES ON THE ELITES"]),
            random.choice(["MARKETS JITTERY AFTER RADICAL MOVE", "TREASURY TAKES A SHARP LEFT", "A COSTLY GAMBLE?"]),
            random.choice(["MARXIST MADNESS!", "CLASS WAR DECLARED", "ECONOMY ON THE BRINK"])
        ),
        'Social Democratic': (
            random.choice(["A FAIRER DEAL", "INVESTING IN OUR FUTURE", "FINALLY, SOME COMMON SENSE"]),
            random.choice(["A PRAGMATIC COMPROMISE", "MODERATE SPENDING BOOST", "CHANCELLOR WALKS THE TIGHTROPE"]),
            random.choice(["TAX AND SPEND RETURNS", "NANNY STATE EXPANDS", "WHO IS PAYING FOR THIS?"])
        ),
        'Centric': (
            random.choice(["STATUS QUO MAINTAINED", "LACK OF AMBITION", "A MISSED OPPORTUNITY"]),
            random.choice(["A STEADY HAND AT THE TILLER", "SENSIBLE GOVERNANCE", "CHANCELLOR PLAYS IT SAFE"]),
            random.choice(["DULL BUT DUTIFUL", "WHERE IS THE GROWTH PLAN?", "KICKING THE CAN DOWN THE ROAD"])
        ),
        'Free-Market': (
            random.choice(["FAT CATS REJOICE", "WORKERS THROWN UNDER THE BUS", "SLASH AND BURN ECONOMICS"]),
            random.choice(["DEREGULATION DRIVE BEGINS", "A ROLL OF THE DICE", "MARKETS CHEER, PUBLIC GROANS"]),
            random.choice(["A BREATH OF FRESH AIR", "BRITAIN IS OPEN FOR BUSINESS", "FINALLY, SOME GROWTH!"])
        ),
        'Fiscal Austerity': (
            random.choice(["CRUEL CUTS BITE DEEP", "AUSTERITY 2.0 DECLARED", "THE VULNERABLE PAY THE PRICE"]),
            random.choice(["TOUGH MEDICINE ADMINISTERED", "BELTS TIGHTENED AT THE TREASURY", "THE DEFICIT HAWKS RETURN"]),
            random.choice(["BALANCING THE BOOKS", "FISCAL RESPONSIBILITY AT LAST", "HARD CHOICES, RIGHT DECISIONS"])
        )
    }
    return headlines.get(ideology, headlines['Centric'])

def update_political_capital(ideology_chosen, approval_diff, headroom_diff):
    s = st.session_state
    s.prev_pm = s.pm_opinion
    s.prev_cab = s.cab_opinion
    s.prev_party = s.party_opinion
    s.prev_backbench = s.backbench_opinion
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

    s.pm_opinion = _clip(s.pm_opinion, 0, 100)
    s.cab_opinion = _clip(s.cab_opinion, 0, 100)
    s.party_opinion = _clip(s.party_opinion, 0, 100)
    s.backbench_opinion = _clip(s.backbench_opinion, 0, 100)
    s.media_opinion = _clip(s.media_opinion, 0, 100)

def update_polling_data(current_year):
    gov_party = st.session_state.party
    nation_score = country._overall(st.session_state.country) * 100
    nation_bonus = (nation_score - 50) * 0.15 
    approval_boost = ((st.session_state.approval - 50) * 0.35) + nation_bonus

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

def process_block_execution(next_year, next_block, chosen_ideology, effect=None):
    snapshot_metrics()
    st.session_state.last_ideology = chosen_ideology
    st.session_state.headlines = generate_headlines(chosen_ideology)
    country.apply_decision(chosen_ideology)

    if effect:
        country_effects = {k: v for k, v in effect.items() if k in country.STATS}
        if country_effects:
            country.nudge(country_effects, snapshot=False)

    if st.session_state.gilt_yield > 4.5: st.session_state.headroom = round(st.session_state.headroom - 0.8, 1)
    if st.session_state.inflation > 3.0: st.session_state.approval = round(st.session_state.approval - 1.5, 1)

    if st.session_state.country['nhs_waiting'] > 7.5:
        st.session_state.growth = round(st.session_state.growth - 0.15, 2)
        st.session_state.message += " The massive NHS backlog is dragging down economic growth."
        
    if st.session_state.country['rail'] < 70:
        st.session_state.market_conf = round(st.session_state.market_conf - 2.0, 1)
        st.session_state.message += " Crumbling rail infrastructure is frustrating investors."

    if st.session_state.country['child_poverty'] > 33.0 or st.session_state.country['homeless'] > 150:
        st.session_state.headroom = round(st.session_state.headroom - 1.0, 1)
        st.session_state.message += " Spiking poverty has forced unbudgeted emergency welfare spending."

    update_political_capital(chosen_ideology, st.session_state.approval - st.session_state.prev_approval, st.session_state.headroom - st.session_state.prev_headroom)
    update_polling_data(next_year)
    check_imf_bailout()
    
    st.session_state.active_crisis = scen.pick_next(st.session_state.year, st.session_state.block, chosen_ideology)
    st.session_state.year = next_year
    st.session_state.block = next_block
    st.rerun()

# ==================== SETUP SCREEN ====================
if st.session_state.step == 'setup':
    st.title('🏛️ The UK Chancellor Simulator (Hardcore Mode)')
    st.markdown('### Step 1: Form Your Government')
    
    party_choice = st.selectbox('Select Governing Party:', ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru'])
    scenario = st.selectbox('Historical Scenario:', ["2026: The Fragile Present", "2008: The Great Financial Crash", "1978: Winter of Discontent"])
    pledge_choices = st.multiselect('Select 3 Core Manifesto Pledges (Breaking these will cap your approval permanently):', 
                                    ["Never raise Basic Income Tax", "Never raise VAT", "Never raise Corporation Tax", "Protect NHS Funding", "Eliminate the Deficit"],
                                    max_selections=3)

    if len(pledge_choices) != 3:
        st.warning("⚠️ You must select exactly 3 Manifesto Pledges to enter Number 11.")
    else:
        col_a, col_b = st.columns([1, 4])
        with col_a:
            if st.button('Enter Number 11', type='primary'):
                st.session_state.party = party_choice
                st.session_state.pledges = pledge_choices
                
                # Apply Scenario Modifiers (Fixed cash deficits)
                if scenario == "2008: The Great Financial Crash":
                    st.session_state.debt = 60.0; st.session_state.deficit = 153.0; st.session_state.inflation = 4.0; st.session_state.interest_rate = 0.5
                    st.session_state.market_conf = 35.0; st.session_state.headroom = -35.0; st.session_state.growth = -2.5
                    st.session_state.macro_cycle = 'Recession'
                    msg = "Welcome to 2008, Chancellor. The global banking sector has collapsed, revenues are in freefall, and the deficit is terrifying. Good luck."
                elif scenario == "1978: Winter of Discontent":
                    st.session_state.debt = 55.0; st.session_state.deficit = 45.0; st.session_state.inflation = 15.5; st.session_state.interest_rate = 12.0
                    st.session_state.gilt_yield = 14.0; st.session_state.approval = 35.0; st.session_state.market_conf = 40.0; st.session_state.growth = -1.0
                    st.session_state.macro_cycle = 'Stagnation'
                    msg = "Welcome to the 1970s, Chancellor. Inflation is rampant, borrowing costs are lethal, and the unions are preparing for war."
                else:
                    st.session_state.macro_cycle = 'Stagnation'
                    msg = "Good morning, Chancellor. I am Sir Humphrey Appleby. The economy is fragile and the bond markets are watching closely."

                # Set Starting Polls
                if party_choice == 'Conservative':
                    st.session_state.poll_history = {'Year': [1], 'Labour': [32], 'Conservative': [38], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
                elif party_choice == 'Liberal Democrats':
                    st.session_state.poll_history = {'Year': [1], 'Labour': [30], 'Conservative': [30], 'Liberal Democrats': [24], 'Reform UK': [8], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
                elif party_choice == 'Reform UK':
                    st.session_state.poll_history = {'Year': [1], 'Labour': [28], 'Conservative': [28], 'Liberal Democrats': [10], 'Reform UK': [26], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
                elif party_choice == 'Green Party':
                    st.session_state.poll_history = {'Year': [1], 'Labour': [28], 'Conservative': [26], 'Liberal Democrats': [12], 'Reform UK': [8], 'Green Party': [22], 'SNP': [3], 'Plaid Cymru': [1]}
                elif party_choice == 'SNP':
                    st.session_state.poll_history = {'Year': [1], 'Labour': [34], 'Conservative': [30], 'Liberal Democrats': [10], 'Reform UK': [9], 'Green Party': [4], 'SNP': [12], 'Plaid Cymru': [1]}
                elif party_choice == 'Plaid Cymru':
                    st.session_state.poll_history = {'Year': [1], 'Labour': [34], 'Conservative': [30], 'Liberal Democrats': [10], 'Reform UK': [9], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [10]}
                else:
                    st.session_state.poll_history = {'Year': [1], 'Labour': [38], 'Conservative': [32], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}

                # Legacy Trackers
                st.session_state.start_debt = st.session_state.debt
                st.session_state.start_growth = st.session_state.growth
                
                snapshot_metrics()
                st.session_state.step = 'game'
                st.session_state.message = msg
                st.rerun()
        with col_b:
            if st.button('Reset Session Cache'):
                st.session_state.clear()
                st.rerun()
    st.stop()

# ==================== MAIN HEADER & DASHBOARD ====================
header(st.session_state.party, st.session_state.term, st.session_state.year, st.session_state.block)

d_approval = round(st.session_state.approval - st.session_state.prev_approval, 1)
d_market = round(st.session_state.market_conf - st.session_state.prev_market, 1)
d_growth = round(st.session_state.growth - st.session_state.prev_growth, 1)
d_headroom = round(st.session_state.headroom - st.session_state.prev_headroom, 1)
d_debt = round(st.session_state.debt - st.session_state.prev_debt, 1)

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(stat_card('Public Approval', f"{st.session_state.approval:.1f}%", f"{d_approval:+}%" if d_approval != 0 else '0%', "The percentage of the electorate that supports your government.", d_approval), unsafe_allow_html=True)
c2.markdown(stat_card('Market Confidence', f"{st.session_state.market_conf:.1f}%", f"{d_market:+}%" if d_market != 0 else '0%', "How much the financial sector trusts your economic management. If this hits 0 and Debt >120%, the IMF takes over.", d_market), unsafe_allow_html=True)
c3.markdown(stat_card('Economic Growth', f"{st.session_state.growth:.1f}%", f"{d_growth:+}%" if d_growth != 0 else '0%', "The annual rate of GDP growth.", d_growth), unsafe_allow_html=True)
c4.markdown(stat_card('OBR Headroom', f"£{st.session_state.headroom:.1f}B", f"£{d_headroom:+}B" if d_headroom != 0 else '£0B', "Your fiscal safety margin. Dropping into the negative breaks fiscal rules.", d_headroom), unsafe_allow_html=True)
c5.markdown(stat_card('National Debt', f"{st.session_state.debt:.1f}%", f"{d_debt:+}%" if d_debt != 0 else '0%', "Total government debt as a % of GDP. High debt triggers IMF bailouts.", d_debt, inverse=True), unsafe_allow_html=True)

st.markdown("#### 🏛️ Political Capital")
p1, p2, p3, p4, p5 = st.columns(5)
p1.markdown(stat_card("PM's Confidence", f"{st.session_state.pm_opinion:.0f}/100", f"{st.session_state.pm_opinion - st.session_state.prev_pm:+.0f}", "The Prime Minister's trust in you. If this drops below 40, you will be sacked!", (st.session_state.pm_opinion - st.session_state.prev_pm)), unsafe_allow_html=True)
p2.markdown(stat_card('Cabinet Support', f"{st.session_state.cab_opinion:.0f}/100", f"{st.session_state.cab_opinion - st.session_state.prev_cab:+.0f}", "The backing of your fellow ministers. Kept high by good public approval and generous budgets.", (st.session_state.cab_opinion - st.session_state.prev_cab)), unsafe_allow_html=True)
p3.markdown(stat_card('Party Unity', f"{st.session_state.party_opinion:.0f}/100", f"{st.session_state.party_opinion - st.session_state.prev_party:+.0f}", "Overall harmony within your party. Below 40 triggers Leadership Challenges.", (st.session_state.party_opinion - st.session_state.prev_party)), unsafe_allow_html=True)
p4.markdown(stat_card('Backbench Morale', f"{st.session_state.backbench_opinion:.0f}/100", f"{st.session_state.backbench_opinion - st.session_state.prev_backbench:+.0f}", "The mood of your MPs. Below 20 causes them to vote down your budget and collapse the government.", (st.session_state.backbench_opinion - st.session_state.prev_backbench)), unsafe_allow_html=True)
p5.markdown(stat_card('Media Sentiment', f"{st.session_state.media_opinion:.0f}/100", f"{st.session_state.media_opinion - st.session_state.prev_media:+.0f}", "How the press is reporting on you. Below 30 triggers Tabloid Scandals.", (st.session_state.media_opinion - st.session_state.prev_media)), unsafe_allow_html=True)

st.divider()

# ==================== ELECTION NIGHT ENGINE & IMF BAILOUT ====================

if st.session_state.get('imf_bailout'):
    st.subheader('🚨 IMF BAILOUT TRIGGERED: GAME OVER')
    humphrey_message("Chancellor, the markets have completely lost faith in our ability to govern. The Pound is in freefall, we cannot sell our gilts, and the National Debt is unsustainable. The Prime Minister has just signed an emergency bailout package with the International Monetary Fund. They are now dictating our fiscal policy. You have been relieved of your duties.")
    st.error("You bankrupted the country. The IMF has forced massive austerity and your government is expected to be wiped out at the next election.")
    if st.button('Start New Career'):
        st.session_state.clear()
        st.rerun()
    st.stop()

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
    win = False
    majority_margin = 0

    if is_regional:
        target = 40 if st.session_state.party == 'SNP' else 15
        max_reg = 57 if st.session_state.party == 'SNP' else 32
        if player_seats >= target:
            result_title = f"{st.session_state.party} Regional Dominance ({player_seats}/{max_reg})"
            win = True
            majority_margin = player_seats - target
            gov_type = "Holding the Balance of Power in Westminster" if seats[largest] < 326 else "Strong Regional Opposition"
        else:
            result_title = f"{st.session_state.party} Regional Defeat ({player_seats} seats)"
            gov_type = "Loss of Regional Mandate"
    else:
        if player_seats >= 326:
            result_title = f"{st.session_state.party} Majority Government"
            majority_margin = player_seats - 326
            gov_type = f"Working Majority of {majority_margin}"
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
                majority_margin = (player_seats + seats[coalition_partner]) - 326
                win = True
            elif player_seats == seats[largest]:
                gov_type = "Fragile Minority Government"
                majority_margin = 0
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

    # LEGACY REPORT CARD
    st.markdown("### 📜 The Treasury Record (Legacy Report)")
    l1, l2, l3, l4 = st.columns(4)
    debt_diff = st.session_state.debt - st.session_state.start_debt
    growth_diff = st.session_state.growth - st.session_state.start_growth
    l1.metric("Debt Inherited vs Now", f"{st.session_state.debt:.1f}%", f"{debt_diff:+.1f}%", delta_color='inverse')
    l2.metric("Growth Inherited vs Now", f"{st.session_state.growth:.1f}%", f"{growth_diff:+.1f}%")
    l3.metric("Total Homes Built", f"{st.session_state.country['homes_built'] * 5:.0f}k")
    l4.metric("Manifesto U-Turns", f"{len(st.session_state.broken_pledges)}")

    st.divider()

    if sacked:
        humphrey_message("I am so sorry, Chancellor. The Prime Minister feels that your continued presence at the Treasury is... politically sub-optimal. The removal van is waiting at the back door of Number 11.")
        st.error(sacked_msg)
        if st.button('Resign & Start New Career'):
            st.session_state.clear()
            st.rerun()
    elif win:
        boost = round(min(15.0, max(5.0, majority_margin / 10.0)), 1)
        st.session_state.approval = _clip(st.session_state.approval + boost)
        st.session_state.pm_opinion = _clip(st.session_state.pm_opinion + boost)
        st.session_state.party_opinion = _clip(st.session_state.party_opinion + boost)
        st.session_state.cab_opinion = _clip(st.session_state.cab_opinion + boost)
        st.session_state.backbench_opinion = _clip(st.session_state.backbench_opinion + boost)
        
        humphrey_message(f"Congratulations, Chancellor. We have survived the electorate. {'Managing a coalition partner will be tedious' if coalition_formed else 'A minority government will be a legislative nightmare'}, but you remain at the Treasury.")
        st.success(f"**YOU SURVIVED!** You retained power and kept your job at Number 11.\n\n🎉 **HONEYMOON PERIOD:** The public and party have granted you a honeymoon period (**+{boost}%** to Public Approval and all Political Capital).")
        
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

else:
    if st.session_state.get('sacked'):
        st.subheader("🚨 SACKED FROM THE TREASURY")
        humphrey_message("I am so sorry, Chancellor. The Prime Minister feels that your continued presence at the Treasury is... politically sub-optimal. The removal van is waiting at the back door of Number 11.")
        st.error(st.session_state.get('sacked_reason', "You have been sacked."))
        if st.button('Resign & Start New Career'):
            st.session_state.clear()
            st.rerun()
        st.stop()

    if st.session_state.block == 3:
        if st.session_state.get('budget_passed'):
            st.subheader("🏛 Parliamentary Vote Results")
            bb = st.session_state.backbench_opinion
            
            base_ayes = 326 if st.session_state.party not in ['SNP', 'Plaid Cymru'] else 300
            commons_ayes = int(base_ayes + (bb / 1.5) - 20 + (st.session_state.year * 2))
            commons_ayes = min(650, max(0, commons_ayes))
            commons_noes = 650 - commons_ayes
            commons_str = f"**Ayes:** {commons_ayes} | **Noes:** {commons_noes}"
            
            if bb > 70: st.success(f"**House of Commons:** The Budget passed the Commons with a thumping majority! Your backbenchers cheered you to the rafters.\n\n{commons_str}")
            elif bb > 40: st.info(f"**House of Commons:** The Budget passed the Commons. There was some grumbling from the backbenches, but the whips kept them in line.\n\n{commons_str}")
            else: st.warning(f"**House of Commons:** The Budget barely scraped through the Commons! A massive backbench rebellion nearly brought the government down.\n\n{commons_str}")
                
            lords_ayes = int(200 + (st.session_state.approval * 2.5))
            lords_ayes = min(750, max(0, lords_ayes))
            lords_noes = 750 - lords_ayes
            
            if st.session_state.approval < 40:
                humphrey_message(f"As for the House of Lords, Chancellor, they actually voted against us (**{lords_noes} Not-Contents** to {lords_ayes} Contents). I reminded them of the Parliament Act of 1911. They cannot reject a Money Bill. However, seeing your dismal poll numbers, they decided to delay it for a month just to be difficult. The markets were briefly irritated.")
            else:
                humphrey_message(f"As for the House of Lords, Chancellor, they supported the bill (**{lords_ayes} Contents** to {lords_noes} Not-Contents). Though even if they hadn't, the Parliament Act of 1911 means they cannot vote down a Money Bill. The constitution is a wonderful thing.")
                
            if st.session_state.get('headlines'):
                render_newspapers(*st.session_state.headlines)
            
            # --- IMF PROJECTIONS ON BUDGET TURN ---
            st.write('')
            st.markdown('### 🌐 IMF Article IV Projections')
            st.caption(f"The IMF's baseline forecast for the UK economy, factoring in the current **{st.session_state.macro_cycle}** global cycle.")
            render_imf_table(get_imf_projections())
            
            st.divider()
            if st.button('Proceed to Spring', type='primary'):
                snapshot_metrics() 
                budget.apply_ongoing()
                check_pledges()
                shift_macro_cycle()
                
                if st.session_state.headroom > 0: st.session_state.pm_opinion = min(100, st.session_state.pm_opinion + 5)
                else: st.session_state.pm_opinion -= 5
                
                st.session_state.year += 1
                st.session_state.block = 1
                st.session_state.budget_passed = False
                st.session_state.headlines = None
                check_imf_bailout()
                st.rerun()
        else:
            st.subheader(f"Year {st.session_state.year} - Block 3: The Chancellor's Budget")
            humphrey_message("A budget, Chancellor, is merely a collection of numbers we present to the House to obscure our true intentions. Shall we proceed to the dispatch box?")
            
            budget.render()
            
            st.divider()
            if st.button('Submit Budget to the Commons & Lords', type='primary'):
                if st.session_state.backbench_opinion < 20:
                    st.session_state.sacked = True
                    st.session_state.sacked_reason = "Your backbenchers completely revolted and voted down your Budget! Losing a budget is treated as an automatic vote of no confidence. The Government has collapsed."
                    st.rerun()
                else:
                    if st.session_state.approval < 40: st.session_state.market_conf -= 1.0
                    st.session_state.budget_passed = True
                    st.session_state.headlines = generate_headlines(None, True, st.session_state.headroom)
                    st.rerun()

    else:
        col_game, col_dash = st.columns([1.0, 1.0], gap="large")
        
        with col_dash:
            tab_econ, tab_nation = st.tabs(['📊 Economy & Polls', '🇬🇧 State of the Nation'])
            with tab_econ:
                
                # Active Pledges & Macro Cycle Display
                st.markdown(f"**🌍 Global Macro Cycle:** {st.session_state.macro_cycle}")
                if st.session_state.broken_pledges:
                    st.markdown(f"**🚨 Broken Pledges (U-Turns):** {', '.join(st.session_state.broken_pledges)}")
                
                m1, m2 = st.columns(2)
                m1.markdown(stat_card('Annual Deficit', f'£{round(st.session_state.deficit, 1)}B', 'current', "Shortfall between revenues and spending."), unsafe_allow_html=True)
                m2.markdown(stat_card('Inflation Rate', f'{round(st.session_state.inflation, 1)}%', 'current', "Rate at which prices are rising."), unsafe_allow_html=True)
                m3, m4 = st.columns(2)
                m3.markdown(stat_card('Bank Rate', f'{round(st.session_state.interest_rate, 1)}%', 'current', "BoE base interest rate."), unsafe_allow_html=True)
                m4.markdown(stat_card('10-Yr Gilt Yield', f'{round(st.session_state.gilt_yield, 1)}%', 'current', "Government borrowing cost."), unsafe_allow_html=True)

                # --- IMF PROJECTIONS ON NORMAL TURNS ---
                st.write('')
                st.markdown('### 🌐 IMF Article IV Projections')
                st.caption(f"The IMF's baseline forecast for the UK economy, factoring in the current **{st.session_state.macro_cycle}** global cycle.")
                render_imf_table(get_imf_projections())

                st.markdown('### 📈 Voting Intention')
                df_polls = pd.DataFrame(st.session_state.poll_history).set_index('Year')
                render_polls(df_polls)
                
                st.write('')
                
                # The Reshuffle Button!
                if st.button("🔄 Reshuffle Cabinet", help="Spend 15 PM Opinion and 20 Cabinet Support to purge rebels, restoring 25 Party Unity and 25 Backbench Morale."):
                    if st.session_state.pm_opinion > 30:
                        st.session_state.pm_opinion -= 15
                        st.session_state.cab_opinion -= 20
                        st.session_state.party_opinion = min(100, st.session_state.party_opinion + 25)
                        st.session_state.backbench_opinion = min(100, st.session_state.backbench_opinion + 25)
                        st.session_state.message = "🔄 The Prime Minister has brutally reshuffled the Cabinet! Rebels have been purged to the backbenches. Party Unity is restored, but the Cabinet is terrified."
                        st.rerun()
                    else:
                        st.error("The PM is too weak to survive a reshuffle!")
                
                st.write('')
                if st.button('Resign & Start New Career'):
                    st.session_state.clear()
                    st.rerun()
                    
            with tab_nation:
                country.render()
                
        with col_game:
            if st.session_state.get('message'):
                news_box(st.session_state.message)
                
            if st.session_state.get('headlines'):
                render_newspapers(*st.session_state.headlines)
                
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
                    
                    st.session_state.headlines = generate_headlines(proxy)
                    update_political_capital(proxy, st.session_state.approval - st.session_state.prev_approval, st.session_state.headroom - st.session_state.prev_headroom)

                    st.session_state.active_crisis = None
                    check_imf_bailout()
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
                        
                        process_block_execution(st.session_state.year, st.session_state.block + 1, selected_type, effect)
                else:
                    st.write("No decision data found for this block.")
                    if st.button("Skip Block"): process_block_execution(st.session_state.year, st.session_state.block + 1, 'Centric')
