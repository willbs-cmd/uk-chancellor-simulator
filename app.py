import streamlit as st
import random
import pandas as pd

from theme import apply_theme, header, crisis_card, news_box, render_polls, humphrey_message, render_newspapers, stat_card, render_imf_table, render_parliament_bar
import country
import budget
import decisions
import scenarios as scen

st.set_page_config(page_title='UK Chancellor Simulator - Hardcore', layout='wide', initial_sidebar_state="expanded")
apply_theme()

# ==================== INITIALIZATION & SAFETY RESET ====================
if 'initialized' in st.session_state:
    needs_reset = False
    required_keys = ['pm_opinion', 'prev_pm', 'imf_bailout', 'seats', 'pledges']
    if not all(k in st.session_state for k in required_keys):
        needs_reset = True
    if 'budget_applied' in st.session_state:
        tax_dict = st.session_state.budget_applied.get('tax', {})
        if 'income' in tax_dict or 'inc_basic' not in tax_dict or 'cgt' not in tax_dict:
            needs_reset = True
    if needs_reset:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
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

    # Economic Stats
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

    st.session_state.seats = {
        'Labour': 411, 'Conservative': 121, 'Liberal Democrats': 72,
        'SNP': 9, 'Reform UK': 5, 'Green Party': 4, 'Plaid Cymru': 4, 'Others': 24
    }

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
        'Hard Left': (random.choice(["POWER TO THE PEOPLE!", "BOLD REFORMS AT LAST"]), random.choice(["MARKETS JITTERY AFTER RADICAL MOVE", "A COSTLY GAMBLE?"]), random.choice(["MARXIST MADNESS!", "CLASS WAR DECLARED"])),
        'Social Democratic': (random.choice(["A FAIRER DEAL", "INVESTING IN OUR FUTURE"]), random.choice(["A PRAGMATIC COMPROMISE", "MODERATE SPENDING BOOST"]), random.choice(["TAX AND SPEND RETURNS", "NANNY STATE EXPANDS"])),
        'Centric': (random.choice(["STATUS QUO MAINTAINED", "LACK OF AMBITION"]), random.choice(["A STEADY HAND AT THE TILLER", "SENSIBLE GOVERNANCE"]), random.choice(["DULL BUT DUTIFUL", "WHERE IS THE GROWTH PLAN?"])),
        'Free-Market': (random.choice(["FAT CATS REJOICE", "WORKERS THROWN UNDER THE BUS"]), random.choice(["DEREGULATION DRIVE BEGINS", "A ROLL OF THE DICE"]), random.choice(["A BREATH OF FRESH AIR", "BRITAIN IS OPEN FOR BUSINESS"])),
        'Fiscal Austerity': (random.choice(["CRUEL CUTS BITE DEEP", "THE VULNERABLE PAY THE PRICE"]), random.choice(["TOUGH MEDICINE ADMINISTERED", "THE DEFICIT HAWKS RETURN"]), random.choice(["BALANCING THE BOOKS", "FISCAL RESPONSIBILITY AT LAST"]))
    }
    return headlines.get(ideology, headlines['Centric'])

def update_political_capital(ideology_chosen, approval_diff, headroom_diff):
    s = st.session_state
    s.prev_pm, s.prev_cab, s.prev_party, s.prev_backbench, s.prev_media = s.pm_opinion, s.cab_opinion, s.party_opinion, s.backbench_opinion, s.media_opinion

    purity_map = {
        'Labour': ['Social Democratic', 'Hard Left'], 'Conservative': ['Free-Market', 'Fiscal Austerity'],
        'Liberal Democrats': ['Centric', 'Social Democratic'], 'Reform UK': ['Free-Market'],
        'Green Party': ['Hard Left', 'Social Democratic'], 'SNP': ['Social Democratic', 'Centric'],
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
    s.prev_approval, s.prev_market, s.prev_growth, s.prev_headroom, s.prev_debt = s.approval, s.market_conf, s.growth, s.headroom, s.debt

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
    
    col1, col2 = st.columns([1, 1])
    with col1:
        party_choice = st.selectbox('Select Governing Party:', ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru'])
        scenario = st.selectbox('Historical Scenario:', ["2026: The Fragile Present", "2008: The Great Financial Crash", "1978: Winter of Discontent"])
    with col2:
        pledge_choices = st.multiselect('Select exactly 3 Core Manifesto Pledges (Breaking these will permanently cap your approval):', 
                                        ["Never raise Basic Income Tax", "Never raise VAT", "Never raise Corporation Tax", "Protect NHS Funding", "Eliminate the Deficit"],
                                        max_selections=3)

    if len(pledge_choices) != 3:
        st.warning("⚠️ You must select exactly 3 Manifesto Pledges to enter Number 11.")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            if st.button('Enter Number 11', type='primary', use_container_width=True):
                st.session_state.party = party_choice
                st.session_state.pledges = pledge_choices
                
                # Apply Scenarios
                if scenario == "2008: The Great Financial Crash":
                    st.session_state.debt, st.session_state.deficit, st.session_state.inflation, st.session_state.interest_rate = 60.0, 153.0, 4.0, 0.5
                    st.session_state.market_conf, st.session_state.headroom, st.session_state.growth = 35.0, -35.0, -2.5
                    st.session_state.macro_cycle = 'Recession'
                    msg = "Welcome to 2008, Chancellor. The global banking sector has collapsed, revenues are in freefall, and the deficit is terrifying. Good luck."
                elif scenario == "1978: Winter of Discontent":
                    st.session_state.debt, st.session_state.deficit, st.session_state.inflation, st.session_state.interest_rate = 55.0, 45.0, 15.5, 12.0
                    st.session_state.gilt_yield, st.session_state.approval, st.session_state.market_conf, st.session_state.growth = 14.0, 35.0, 40.0, -1.0
                    st.session_state.macro_cycle = 'Stagnation'
                    msg = "Welcome to the 1970s, Chancellor. Inflation is rampant, borrowing costs are lethal, and the unions are preparing for war."
                else:
                    st.session_state.macro_cycle = 'Stagnation'
                    msg = "Good morning, Chancellor. I am Sir Humphrey Appleby. The economy is fragile and the bond markets are watching closely."

                # Starting Seats & Polls
                if party_choice == 'Conservative':
                    st.session_state.seats = {'Conservative': 365, 'Labour': 202, 'Liberal Democrats': 11, 'SNP': 48, 'Reform UK': 1, 'Green Party': 1, 'Plaid Cymru': 4, 'Others': 18}
                    st.session_state.poll_history = {'Year': [1], 'Labour': [32], 'Conservative': [38], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
                elif party_choice == 'Liberal Democrats':
                    st.session_state.seats = {'Liberal Democrats': 335, 'Labour': 160, 'Conservative': 120, 'SNP': 15, 'Reform UK': 4, 'Green Party': 2, 'Plaid Cymru': 4, 'Others': 10}
                    st.session_state.poll_history = {'Year': [1], 'Labour': [30], 'Conservative': [30], 'Liberal Democrats': [24], 'Reform UK': [8], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
                elif party_choice == 'Reform UK':
                    st.session_state.seats = {'Reform UK': 330, 'Conservative': 150, 'Labour': 120, 'Liberal Democrats': 30, 'SNP': 10, 'Green Party': 1, 'Plaid Cymru': 2, 'Others': 7}
                    st.session_state.poll_history = {'Year': [1], 'Labour': [28], 'Conservative': [28], 'Liberal Democrats': [10], 'Reform UK': [26], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
                elif party_choice == 'Green Party':
                    st.session_state.seats = {'Green Party': 330, 'Labour': 180, 'Liberal Democrats': 60, 'Conservative': 50, 'SNP': 15, 'Reform UK': 5, 'Plaid Cymru': 4, 'Others': 6}
                    st.session_state.poll_history = {'Year': [1], 'Labour': [28], 'Conservative': [26], 'Liberal Democrats': [12], 'Reform UK': [8], 'Green Party': [22], 'SNP': [3], 'Plaid Cymru': [1]}
                elif party_choice == 'SNP':
                    st.session_state.seats = {'SNP': 50, 'Labour': 310, 'Conservative': 210, 'Liberal Democrats': 55, 'Reform UK': 10, 'Green Party': 4, 'Plaid Cymru': 4, 'Others': 7}
                    st.session_state.poll_history = {'Year': [1], 'Labour': [34], 'Conservative': [30], 'Liberal Democrats': [10], 'Reform UK': [9], 'Green Party': [4], 'SNP': [12], 'Plaid Cymru': [1]}
                elif party_choice == 'Plaid Cymru':
                    st.session_state.seats = {'Plaid Cymru': 25, 'Labour': 315, 'Conservative': 220, 'Liberal Democrats': 60, 'Reform UK': 15, 'SNP': 10, 'Green Party': 2, 'Others': 3}
                    st.session_state.poll_history = {'Year': [1], 'Labour': [34], 'Conservative': [30], 'Liberal Democrats': [10], 'Reform UK': [9], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [10]}
                else:
                    st.session_state.seats = {'Labour': 411, 'Conservative': 121, 'Liberal Democrats': 72, 'SNP': 9, 'Reform UK': 5, 'Green Party': 4, 'Plaid Cymru': 4, 'Others': 24}
                    st.session_state.poll_history = {'Year': [1], 'Labour': [38], 'Conservative': [32], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}

                st.session_state.start_debt = st.session_state.debt
                st.session_state.start_growth = st.session_state.growth
                
                snapshot_metrics()
                st.session_state.step = 'game'
                st.session_state.message = msg
                st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button('Hard Reset Cache (Fix Errors)'):
        st.session_state.clear()
        st.rerun()
    st.stop()


# ==================== PERSISTENT SIDEBAR ====================
with st.sidebar:
    st.markdown("### 💼 Chancellor's Briefcase")
    
    st.markdown(f"**🌍 Global Macro Cycle:**")
    m_color = "#6fbf8a" if st.session_state.macro_cycle == "Boom" else ("#e65c4f" if st.session_state.macro_cycle == "Recession" else "#a3b8ad")
    st.markdown(f"<span style='color:{m_color}; font-weight:bold; font-size:1.1rem;'>{st.session_state.macro_cycle.upper()}</span>", unsafe_allow_html=True)
    st.caption("Alters baseline tax receipts.")
    
    st.markdown("---")
    st.markdown("**📜 Manifesto Pledges:**")
    for pledge in st.session_state.pledges:
        if pledge in st.session_state.broken_pledges:
            st.markdown(f"❌ ~~*{pledge}*~~")
        else:
            st.markdown(f"✅ {pledge}")
            
    if st.session_state.broken_pledges:
        st.error(f"U-Turn Penalty: Maximum Approval capped at {st.session_state.approval_cap}%.")
        
    st.markdown("---")
    if st.button('Resign & Start New Career', use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ==================== MAIN GAMEPLAY LAYOUT ====================
header(st.session_state.party, st.session_state.term, st.session_state.year, st.session_state.block)

# --- THE BIG 5 KPI BAR ---
d_app = round(st.session_state.approval - st.session_state.prev_approval, 1)
d_mkt = round(st.session_state.market_conf - st.session_state.prev_market, 1)
d_gro = round(st.session_state.growth - st.session_state.prev_growth, 1)
d_hdr = round(st.session_state.headroom - st.session_state.prev_headroom, 1)
d_dbt = round(st.session_state.debt - st.session_state.prev_debt, 1)

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(stat_card('Public Approval', f"{st.session_state.approval:.1f}%", f"{d_app:+}%" if d_app != 0 else '0%', "Percentage of the electorate that supports you.", d_app), unsafe_allow_html=True)
c2.markdown(stat_card('Market Confidence', f"{st.session_state.market_conf:.1f}%", f"{d_mkt:+}%" if d_mkt != 0 else '0%', "Trust from the financial sector. Drops to 0% = IMF Bailout.", d_mkt), unsafe_allow_html=True)
c3.markdown(stat_card('Economic Growth', f"{st.session_state.growth:.1f}%", f"{d_gro:+}%" if d_gro != 0 else '0%', "Annual GDP growth.", d_gro), unsafe_allow_html=True)
c4.markdown(stat_card('OBR Headroom', f"£{st.session_state.headroom:.1f}B", f"£{d_hdr:+}B" if d_hdr != 0 else '£0B', "Fiscal safety margin. Keep it above £0.", d_hdr), unsafe_allow_html=True)
c5.markdown(stat_card('National Debt', f"{st.session_state.debt:.1f}%", f"{d_dbt:+}%" if d_dbt != 0 else '0%', "Debt as % of GDP.", d_dbt, inverse=True), unsafe_allow_html=True)


# ==================== END GAME CHECKS ====================
if st.session_state.get('imf_bailout'):
    st.subheader('🚨 IMF BAILOUT TRIGGERED: GAME OVER')
    humphrey_message("Chancellor, the markets have completely lost faith in our ability to govern. The Pound is in freefall, we cannot sell our gilts, and the National Debt is unsustainable. The Prime Minister has just signed an emergency bailout package with the International Monetary Fund. They are now dictating our fiscal policy. You have been relieved of your duties.")
    st.error("You bankrupted the country. The IMF has forced massive austerity and your government is expected to be wiped out at the next election.")
    st.stop()

if st.session_state.get('sacked'):
    st.subheader("🚨 SACKED FROM THE TREASURY")
    humphrey_message("I am so sorry, Chancellor. The Prime Minister feels that your continued presence at the Treasury is... politically sub-optimal. The removal van is waiting at the back door of Number 11.")
    st.error(st.session_state.get('sacked_reason', "You have been sacked."))
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

    st.session_state.seats = seats
    player_seats = seats[st.session_state.party]
    
    sacked = False
    sacked_msg = ""
    if st.session_state.pm_opinion < 40 or st.session_state.party_opinion < 35:
        sacked = True
        sacked_msg = "Your relationship with the Prime Minister and your own backbenches collapsed. Regardless of the election result, you have been sacked and banished to the backbenches."

    win = False
    if player_seats >= 326:
        result_title, gov_type, win = f"{st.session_state.party} Majority Government", f"Working Majority of {player_seats - 326}", True
    else:
        left_bloc = ['Labour', 'Liberal Democrats', 'Green Party', 'SNP', 'Plaid Cymru']
        right_bloc = ['Conservative', 'Reform UK', 'Liberal Democrats']
        my_bloc = left_bloc if st.session_state.party in left_bloc else right_bloc
        
        coalition_partner = None
        for partner in my_bloc:
            if partner != st.session_state.party and player_seats + seats[partner] >= 326:
                coalition_partner = partner
                break
                
        if coalition_partner:
            result_title, gov_type, win = "Hung Parliament", f"Formal Coalition with {coalition_partner}", True
        elif player_seats == seats[largest]:
            result_title, gov_type, win = "Hung Parliament", "Fragile Minority Government", True
        else:
            result_title, gov_type, win = "Hung Parliament", "Sent to the Opposition Benches", False

    box_color = '#2b5440' if win and not sacked else '#8b0000'
    st.markdown(f'''
    <div style='background-color: {box_color}; padding: 20px; border-radius: 10px; color: white; text-align: center; border: 2px solid #c9a45c;'>
        <h2>{result_title}</h2><h4 style='color: #c9a45c;'>{gov_type}</h4><p style='font-size: 18px;'>Your Seats: <b>{player_seats}</b></p>
    </div>
    ''', unsafe_allow_html=True)

    render_parliament_bar(seats, st.session_state.party)

    st.markdown("### 📜 The Treasury Record (Legacy Report)")
    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Debt Inherited vs Now", f"{st.session_state.debt:.1f}%", f"{st.session_state.debt - st.session_state.start_debt:+.1f}%", delta_color='inverse')
    l2.metric("Growth Inherited vs Now", f"{st.session_state.growth:.1f}%", f"{st.session_state.growth - st.session_state.start_growth:+.1f}%")
    l3.metric("Total Homes Built", f"{st.session_state.country['homes_built'] * 5:.0f}k")
    l4.metric("Manifesto U-Turns", f"{len(st.session_state.broken_pledges)}")

    if sacked:
        humphrey_message("I am so sorry, Chancellor. The Prime Minister feels that your continued presence at the Treasury is politically sub-optimal.")
        st.error(sacked_msg)
    elif win:
        humphrey_message("Congratulations, Chancellor. We have survived the electorate. You remain at the Treasury.")
        if st.button('Continue as Chancellor'):
            st.session_state.term += 1
            st.session_state.year = 1
            st.session_state.block = 1
            st.session_state.step = 'game'
            st.rerun()
    else:
        humphrey_message("The electorate has spoken. We have been thoroughly evicted. I shall miss our little chats.")
    st.stop()


# ==================== BUDGET BLOCK (FULL WIDTH) ====================
if st.session_state.block == 3:
    if st.session_state.get('budget_passed'):
        st.subheader("🏛 Parliamentary Vote Results")
        bb = st.session_state.backbench_opinion
        commons_ayes = min(650, max(0, int(326 + (bb / 1.5) - 20 + (st.session_state.year * 2))))
        
        if bb > 70: st.success(f"**House of Commons:** The Budget passed with a thumping majority! (Ayes: {commons_ayes})")
        elif bb > 40: st.info(f"**House of Commons:** The Budget passed, though with some grumbling. (Ayes: {commons_ayes})")
        else: st.warning(f"**House of Commons:** The Budget barely scraped through! A massive backbench rebellion. (Ayes: {commons_ayes})")
            
        if st.session_state.approval < 40:
            humphrey_message("As for the House of Lords, Chancellor, they voted against us. I reminded them of the Parliament Act of 1911. They cannot reject a Money Bill. However, seeing your dismal poll numbers, they delayed it to be difficult.")
        else:
            humphrey_message("The House of Lords supported the bill. Though even if they hadn't, the Parliament Act of 1911 means they cannot vote down a Money Bill. The constitution is a wonderful thing.")
            
        if st.session_state.get('headlines'):
            render_newspapers(*st.session_state.headlines)
        
        st.divider()
        if st.button('Proceed to Spring', type='primary', use_container_width=True):
            snapshot_metrics() 
            budget.apply_ongoing()
            check_pledges()
            shift_macro_cycle()
            
            st.session_state.pm_opinion = min(100, st.session_state.pm_opinion + (5 if st.session_state.headroom > 0 else -5))
            st.session_state.year += 1
            st.session_state.block = 1
            st.session_state.budget_passed = False
            st.session_state.headlines = None
            check_imf_bailout()
            st.rerun()
            
    else:
        st.subheader(f"Year {st.session_state.year} - Block 3: The Chancellor's Budget")
        humphrey_message("A budget, Chancellor, is merely a collection of numbers we present to the House to obscure our true intentions. Shall we proceed to the dispatch box?")
        
        if 'budget_applied' not in st.session_state: budget.ensure()
        budget.render()
        
        st.markdown("---")
        st.markdown("### 🏛️ The Whips' Office: Parliamentary Arithmetic")
        
        draft = budget.read()
        party = st.session_state.party
        corp_change = draft['tax']['corp'] - budget.TAXES['corp']['default']
        welfare_change = float(draft['spend']['welfare'])
        climate_change = float(draft['spend']['climate'])
        other_change = float(draft['spend']['other'])

        revolt_warning = ""
        if party in ['Conservative', 'Reform UK'] and corp_change > 0: revolt_warning = "🚨 WHIP WARNING: MPs threatening to rebel over Corporation Tax hikes!"
        if party in ['Labour', 'Green Party'] and welfare_change < 0: revolt_warning = "🚨 WHIP WARNING: Left wing preparing to rebel over welfare cuts!"
        if party == 'Liberal Democrats' and climate_change < 0: revolt_warning = "🚨 WHIP WARNING: Base will revolt over cuts to climate spending!"
        if party in ['SNP', 'Plaid Cymru'] and other_change < 0: revolt_warning = "🚨 WHIP WARNING: Regional MPs will rebel over devolved block grants!"
        if revolt_warning: st.error(revolt_warning)

        bb = st.session_state.backbench_opinion
        commons_ayes = min(650, max(0, int(326 + (bb / 1.5) - 20 + (st.session_state.year * 2))))
        if revolt_warning: commons_ayes -= 35
        
        if commons_ayes < 326: st.error(f"🚨 PROJECTED DEFEAT: Only {commons_ayes} votes in favour. You need 326.")
        elif commons_ayes < 340: st.warning(f"⚠️ PROJECTED PASS (TIGHT): {commons_ayes} votes. Dangerously close to a rebellion.")
        else: st.success(f"✅ PROJECTED PASS: {commons_ayes} votes in favour.")

        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            if st.button("🥓 Offer Pork-Barrel Funds\n(-£2.0B Headroom, +15 Backbench)", disabled=st.session_state.headroom < 2.0):
                st.session_state.headroom -= 2.0; st.session_state.backbench_opinion = min(100, st.session_state.backbench_opinion + 15); st.rerun()
        with col_w2:
            if st.button("🗡️ Threaten Rebels with Deselection\n(-15 Party Unity, +10 Backbench)"):
                st.session_state.party_opinion -= 15; st.session_state.backbench_opinion = min(100, st.session_state.backbench_opinion + 10); st.rerun()
        with col_w3:
            if st.button("🤝 Water Down Controversial Reforms\n(+10 Backbench, -2 Market Conf)"):
                st.session_state.market_conf = max(0, st.session_state.market_conf - 2.0); st.session_state.backbench_opinion = min(100, st.session_state.backbench_opinion + 10); st.rerun()

        st.divider()
        if st.button('Submit Budget to the Commons & Lords', type='primary'):
            if commons_ayes < 326:
                st.session_state.sacked = True
                st.session_state.sacked_reason = "You failed to secure the votes. The budget was defeated in the House of Commons, collapsing the Government."
                st.rerun()
            else:
                if st.session_state.approval < 40: st.session_state.market_conf -= 1.0
                st.session_state.budget_passed = True
                st.session_state.headlines = generate_headlines(None, True, st.session_state.headroom)
                st.rerun()

# ==================== STANDARD BLOCK (SPLIT SCREEN) ====================
else:
    col_game, col_dash = st.columns([1.3, 1.0], gap="large")
    
    with col_dash:
        tab_econ, tab_pol, tab_nation = st.tabs(['📊 Economy', '🏛️ Politics', '🇬🇧 Nation'])
        
        with tab_econ:
            debt_servicing = round(budget.interest(), 1)
            gbp_usd = round(1.27 * (1.0 + 0.15 * (st.session_state.market_conf / 65.0 - 1.0) - 0.05 * (st.session_state.inflation / 3.0 - 1.0)), 2)
            
            b_tax = st.session_state.get('budget_applied', {}).get('tax', {})
            tax_burden = round(36.8 + 0.1 * (b_tax.get('inc_basic', 20) - 20) + 0.08 * (b_tax.get('corp', 25) - 25), 1)

            e1, e2 = st.columns(2)
            e1.markdown(stat_card('Annual Deficit', f'£{round(st.session_state.deficit, 1)}B', 'current', "Adds directly to the national debt."), unsafe_allow_html=True)
            e2.markdown(stat_card('Debt Servicing', f'£{debt_servicing}B/yr', f'{debt_servicing - 105.4:+.1f}B', "Interest paid on debt.", debt_servicing - 105.4, inverse=True), unsafe_allow_html=True)
            
            e3, e4 = st.columns(2)
            e3.markdown(stat_card('Inflation Rate', f'{round(st.session_state.inflation, 1)}%', 'current', "Consumer Price Index.", unsafe_allow_html=True), unsafe_allow_html=True)
            e4.markdown(stat_card('Bank Rate', f'{round(st.session_state.interest_rate, 1)}%', 'current', "BoE base policy rate."), unsafe_allow_html=True)
            
            e5, e6 = st.columns(2)
            e5.markdown(stat_card('10-Yr Gilt Yield', f'{round(st.session_state.gilt_yield, 1)}%', 'current', "Borrowing cost of the UK government."), unsafe_allow_html=True)
            e6.markdown(stat_card('GBP/USD', f'${gbp_usd:.2f}', f'{gbp_usd - 1.27:+.2f}', "Strength of Sterling.", gbp_usd - 1.27), unsafe_allow_html=True)

            st.markdown(f"<div style='text-align:right; font-size:0.85rem; color:#a3b8ad; margin-bottom:12px;'>Overall UK Tax Burden: <b>{tax_burden}% of GDP</b></div>", unsafe_allow_html=True)

            st.markdown('### 🌐 IMF Article IV Projections')
            render_imf_table(get_imf_projections())

        with tab_pol:
            p1, p2 = st.columns(2)
            p1.markdown(stat_card("PM's Confidence", f"{st.session_state.pm_opinion:.0f}/100", f"{st.session_state.pm_opinion - st.session_state.prev_pm:+.0f}", "Below 40 = Sacked", (st.session_state.pm_opinion - st.session_state.prev_pm)), unsafe_allow_html=True)
            p2.markdown(stat_card('Cabinet Support', f"{st.session_state.cab_opinion:.0f}/100", f"{st.session_state.cab_opinion - st.session_state.prev_cab:+.0f}", "Ministers' backing.", (st.session_state.cab_opinion - st.session_state.prev_cab)), unsafe_allow_html=True)
            
            p3, p4 = st.columns(2)
            p3.markdown(stat_card('Party Unity', f"{st.session_state.party_opinion:.0f}/100", f"{st.session_state.party_opinion - st.session_state.prev_party:+.0f}", "Below 40 = Rebellion", (st.session_state.party_opinion - st.session_state.prev_party)), unsafe_allow_html=True)
            p4.markdown(stat_card('Backbench Morale', f"{st.session_state.backbench_opinion:.0f}/100", f"{st.session_state.backbench_opinion - st.session_state.prev_backbench:+.0f}", "Below 20 = Budget Defeat", (st.session_state.backbench_opinion - st.session_state.prev_backbench)), unsafe_allow_html=True)
            
            st.markdown(stat_card('Media Sentiment', f"{st.session_state.media_opinion:.0f}/100", f"{st.session_state.media_opinion - st.session_state.prev_media:+.0f}", "Below 30 = Scandals", (st.session_state.media_opinion - st.session_state.prev_media)), unsafe_allow_html=True)

            render_parliament_bar(st.session_state.seats, st.session_state.party)

            if st.button("🔄 Reshuffle Cabinet", help="Spend PM & Cabinet support to purge rebels and restore unity.", use_container_width=True):
                if st.session_state.pm_opinion > 30:
                    st.session_state.pm_opinion -= 15; st.session_state.cab_opinion -= 20
                    st.session_state.party_opinion = min(100, st.session_state.party_opinion + 25)
                    st.session_state.backbench_opinion = min(100, st.session_state.backbench_opinion + 25)
                    st.session_state.message = "🔄 The PM has brutally reshuffled the Cabinet! Rebels purged."
                    st.rerun()
                else:
                    st.error("The PM is too weak to survive a reshuffle!")

            st.markdown('### 📈 Voting Intention')
            df_polls = pd.DataFrame(st.session_state.poll_history).set_index('Year')
            render_polls(df_polls)
                
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
