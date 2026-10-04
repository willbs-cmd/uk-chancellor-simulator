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
    req_keys = ['pm_opinion', 'imf_bailout', 'seats', 'pledges', 'spad', 'sleaze']
    if not all(k in st.session_state for k in req_keys):
        needs_reset = True
        
    if 'budget_applied' in st.session_state:
        tax_d = st.session_state.budget_applied.get('tax', {})
        if 'income' in tax_d or 'inc_basic' not in tax_d or 'cgt' not in tax_d:
            needs_reset = True

    if needs_reset:
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

if 'initialized' not in st.session_state or st.session_state.get('step') is None:
    st.session_state.step = 'setup'
    st.session_state.party = 'Labour'
    st.session_state.year, st.session_state.block, st.session_state.term = 1, 1, 1
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
    st.session_state.whip_votes = 0
    st.session_state.sleaze = 0
    st.session_state.spad = None

    st.session_state.approval, st.session_state.market_conf = 48.0, 65.0
    st.session_state.debt, st.session_state.deficit = 98.2, 125.4
    st.session_state.inflation, st.session_state.interest_rate = 3.2, 5.0
    st.session_state.gilt_yield, st.session_state.growth = 4.7, 0.8
    st.session_state.headroom = 8.5

    st.session_state.pm_opinion, st.session_state.cab_opinion = 75.0, 65.0
    st.session_state.party_opinion, st.session_state.backbench_opinion = 70.0, 60.0
    st.session_state.media_opinion = 50.0

    st.session_state.prev_approval, st.session_state.prev_market = 48.0, 65.0
    st.session_state.prev_growth, st.session_state.prev_headroom, st.session_state.prev_debt = 0.8, 8.5, 98.2
    st.session_state.prev_pm, st.session_state.prev_cab = 75.0, 65.0
    st.session_state.prev_party, st.session_state.prev_backbench, st.session_state.prev_media = 70.0, 60.0, 50.0

    st.session_state.seats = {'Labour': 411, 'Conservative': 121, 'Liberal Democrats': 72, 'SNP': 9, 'Reform UK': 5, 'Green Party': 4, 'Plaid Cymru': 4, 'Others': 24}
    st.session_state.poll_history = {'Year': [1], 'Labour': [38], 'Conservative': [32], 'Liberal Democrats': [12], 'Reform UK': [10], 'Green Party': [4], 'SNP': [3], 'Plaid Cymru': [1]}
    st.session_state.message = ""
    st.session_state.initialized = True

# ==================== LOGIC FUNCTIONS ====================
def _clip(val, minimum=0.0, maximum=None):
    return max(minimum, min(maximum if maximum else st.session_state.get('approval_cap', 100), val))

def enforce_spad_passives():
    s = st.session_state
    if s.get('spad', '').startswith('The City Banker'):
        if s.market_conf < 20.0:
            s.market_conf = 20.0

def check_pledges():
    s = st.session_state
    if 'budget_applied' not in s: return
    b = s.budget_applied
    broken = []
    
    if "Never raise Basic Income Tax" in s.pledges and b['tax']['inc_basic'] > 20 and "Never raise Basic Income Tax" not in s.broken_pledges: broken.append("Never raise Basic Income Tax")
    if "Never raise VAT" in s.pledges and b['tax']['vat'] > 20 and "Never raise VAT" not in s.broken_pledges: broken.append("Never raise VAT")
    if "Never raise Corporation Tax" in s.pledges and b['tax']['corp'] > 25 and "Never raise Corporation Tax" not in s.broken_pledges: broken.append("Never raise Corporation Tax")
    if "Never raise Capital Gains Tax" in s.pledges and b['tax']['cgt'] > 20 and "Never raise Capital Gains Tax" not in s.broken_pledges: broken.append("Never raise Capital Gains Tax")
    if "Protect NHS Funding (No Cuts)" in s.pledges and float(b['spend']['health']) < 0 and "Protect NHS Funding (No Cuts)" not in s.broken_pledges: broken.append("Protect NHS Funding (No Cuts)")
    if "Protect Education (No Cuts)" in s.pledges and float(b['spend']['education']) < 0 and "Protect Education (No Cuts)" not in s.broken_pledges: broken.append("Protect Education (No Cuts)")
    if "Never increase Welfare Spending" in s.pledges and float(b['spend']['welfare']) > 0 and "Never increase Welfare Spending" not in s.broken_pledges: broken.append("Never increase Welfare Spending")
    if "Eliminate the Deficit" in s.pledges and s.deficit > 0 and s.year == 5 and "Eliminate the Deficit" not in s.broken_pledges: broken.append("Eliminate the Deficit")
        
    penalty_mult = 0.5 if s.spad and s.spad.startswith('The Spin Doctor') else 1.0
    for p in broken:
        s.broken_pledges.append(p)
        s.approval_cap -= int(15 * penalty_mult)
        s.approval = _clip(s.approval - int(15 * penalty_mult))
        s.media_opinion = _clip(s.media_opinion - int(25 * penalty_mult), 0, 100)
        s.message += f" 🚨 U-TURN SCANDAL: You broke your manifesto pledge: '{p}'. The press is tearing you apart!"

def shift_macro_cycle():
    s = st.session_state
    cycles = ['Boom', 'Stagnation', 'Recession']
    if random.random() < 0.20:
        s.macro_cycle = random.choice([c for c in cycles if c != s.macro_cycle])
        s.message += f" 🌍 GLOBAL MACRO SHIFT: The world economy has entered a {s.macro_cycle}."

def check_imf_bailout():
    s = st.session_state
    enforce_spad_passives()
    if s.debt > 120 and s.market_conf < 15 and not s.imf_bailout:
        s.imf_bailout = True

def get_imf_projections():
    s = st.session_state
    c = s.macro_cycle
    g_mod = 1.2 if c == 'Boom' else (-1.5 if c == 'Recession' else 0.1)
    i_mod = 0.8 if c == 'Boom' else (-1.0 if c == 'Recession' else -0.2)
    d_mod = -1.5 if c == 'Boom' else (3.0 if c == 'Recession' else 0.5)
    
    y2_g = round(s.growth + g_mod + random.uniform(-0.2, 0.2), 1)
    y3_g = round(s.growth + (g_mod * 1.5) + random.uniform(-0.3, 0.3), 1)
    y2_i = max(0.1, round(s.inflation + i_mod + random.uniform(-0.2, 0.2), 1))
    y3_i = max(0.1, round(s.inflation + (i_mod * 1.5) + random.uniform(-0.3, 0.3), 1))
    y2_d = round(s.debt + (s.deficit / 23.0) + d_mod, 1)
    y3_d = round(y2_d + (s.deficit / 23.0) + (d_mod * 1.5), 1)

    return pd.DataFrame({
        "Metric": ["GDP Growth", "Inflation (CPI)", "National Debt (% GDP)"],
        f"Year {s.year} (Current)": [f"{s.growth}%", f"{s.inflation}%", f"{s.debt}%"],
        f"Year {s.year + 1}": [f"{y2_g}%", f"{y2_i}%", f"{y2_d}%"],
        f"Year {s.year + 2}": [f"{y3_g}%", f"{y3_i}%", f"{y3_d}%"]
    })

def generate_headlines(ideology, is_budget=False, headroom=0):
    if is_budget:
        if headroom > 2.0: return ("AUSTERITY BUDGET IGNORES THE POOR", "CHANCELLOR BUILDS FISCAL FORTRESS", "A PRUDENT BUDGET AT LAST")
        elif headroom < -2.0: return ("END TO AUSTERITY!", "MARKETS PANIC OVER DEFICIT SPENDING", "RECKLESS BORROWING THREATENS ECONOMY")
        else: return ("A MIXED BAG FOR WORKERS", "CHANCELLOR WALKS THE TIGHTROPE", "PLAYING IT SAFE BEFORE ELECTION")
    h = {
        'Hard Left': (random.choice(["POWER TO THE PEOPLE!", "BOLD REFORMS AT LAST"]), random.choice(["MARKETS JITTERY", "A COSTLY GAMBLE?"]), random.choice(["MARXIST MADNESS!", "CLASS WAR DECLARED"])),
        'Social Democratic': (random.choice(["A FAIRER DEAL", "INVESTING IN OUR FUTURE"]), random.choice(["A PRAGMATIC COMPROMISE", "MODERATE SPENDING BOOST"]), random.choice(["TAX AND SPEND RETURNS", "NANNY STATE EXPANDS"])),
        'Centric': (random.choice(["STATUS QUO MAINTAINED", "LACK OF AMBITION"]), random.choice(["A STEADY HAND", "SENSIBLE GOVERNANCE"]), random.choice(["DULL BUT DUTIFUL", "WHERE IS THE GROWTH PLAN?"])),
        'Free-Market': (random.choice(["FAT CATS REJOICE", "WORKERS THROWN UNDER THE BUS"]), random.choice(["DEREGULATION DRIVE", "A ROLL OF THE DICE"]), random.choice(["A BREATH OF FRESH AIR", "BRITAIN OPEN FOR BUSINESS"])),
        'Fiscal Austerity': (random.choice(["CRUEL CUTS BITE DEEP", "VULNERABLE PAY THE PRICE"]), random.choice(["TOUGH MEDICINE", "THE DEFICIT HAWKS RETURN"]), random.choice(["BALANCING THE BOOKS", "FISCAL RESPONSIBILITY"]))
    }
    return h.get(ideology, h['Centric'])

def update_political_capital(ideo, app_diff, hdr_diff):
    s = st.session_state
    s.prev_pm, s.prev_cab, s.prev_party, s.prev_backbench, s.prev_media = s.pm_opinion, s.cab_opinion, s.party_opinion, s.backbench_opinion, s.media_opinion
    core = {'Labour': ['Social Democratic', 'Hard Left'], 'Conservative': ['Free-Market', 'Fiscal Austerity'], 'Liberal Democrats': ['Centric', 'Social Democratic'], 'Reform UK': ['Free-Market'], 'Green Party': ['Hard Left', 'Social Democratic'], 'SNP': ['Social Democratic', 'Centric'], 'Plaid Cymru': ['Social Democratic', 'Hard Left']}.get(s.party, ['Centric'])
    
    if ideo in core:
        s.backbench_opinion += random.uniform(2, 6)
        s.party_opinion += random.uniform(1, 4)
    else:
        s.backbench_opinion -= random.uniform(4, 9)
        s.party_opinion -= random.uniform(2, 5)

    s.pm_opinion += (app_diff * 1.5) + (hdr_diff * 0.5)
    s.cab_opinion += app_diff + random.uniform(-2, 3)
    s.media_opinion += (app_diff * 0.8) + ((s.market_conf - s.prev_market) * 0.5)

    s.pm_opinion = _clip(s.pm_opinion, 0, 100)
    s.cab_opinion = _clip(s.cab_opinion, 0, 100)
    s.party_opinion = _clip(s.party_opinion, 0, 100)
    s.backbench_opinion = _clip(s.backbench_opinion, 0, 100)
    s.media_opinion = _clip(s.media_opinion, 0, 100)
    enforce_spad_passives()

def update_polling_data(current_year):
    s = st.session_state
    gov = s.party
    score = country._overall(s.country) * 100
    boost = ((s.approval - 50) * 0.35) + ((score - 50) * 0.15)

    if current_year not in s.poll_history['Year']:
        s.poll_history['Year'].append(current_year)
        base = {p: s.poll_history[p][-1] for p in ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru']}
        if gov in ['SNP', 'Plaid Cymru']: base[gov] += (boost * 0.2)
        else: base[gov] += boost

        for p in base:
            if p != gov: base[p] -= (boost / 5) + random.uniform(-1, 1)
            else: base[p] += random.uniform(-1, 1)
            base[p] = max(1 if p in ['SNP', 'Plaid Cymru'] else 4, round(base[p], 1))

        tot = sum(base.values())
        for p in base:
            base[p] = round((base[p] / tot) * 100, 1)
            s.poll_history[p].append(base[p])

def snapshot_metrics():
    s = st.session_state
    s.prev_approval, s.prev_market, s.prev_growth, s.prev_headroom, s.prev_debt = s.approval, s.market_conf, s.growth, s.headroom, s.debt

def process_block_execution(next_year, next_block, chosen_ideology, effect=None):
    snapshot_metrics()
    s = st.session_state
    s.last_ideology = chosen_ideology
    s.headlines = generate_headlines(chosen_ideology)
    country.apply_decision(chosen_ideology)

    if effect:
        cx = {k: v for k, v in effect.items() if k in country.STATS}
        if cx: country.nudge(cx, snapshot=False)

    if s.gilt_yield > 4.5: s.headroom = round(s.headroom - 0.8, 1)
    if s.inflation > 3.0: s.approval = round(s.approval - 1.5, 1)
    if s.country['nhs_waiting'] > 7.5:
        s.growth = round(s.growth - 0.15, 2)
        s.message += " The massive NHS backlog is dragging down economic growth."
    if s.country['rail'] < 70:
        s.market_conf = round(s.market_conf - 2.0, 1)
        s.message += " Crumbling rail infrastructure is frustrating investors."
    if s.country['child_poverty'] > 33.0 or s.country['homeless'] > 150:
        s.headroom = round(s.headroom - 1.0, 1)
        s.message += " Spiking poverty has forced unbudgeted emergency welfare spending."

    opposition = 'Conservative' if s.party in ['Labour', 'Liberal Democrats', 'Green Party', 'SNP', 'Plaid Cymru'] else 'Labour'
    if s.backbench_opinion < 35 and random.random() < 0.4 and s.seats[s.party] > 0:
        s.seats[s.party] -= 1
        s.seats[opposition] += 1
        s.message += f" 🚨 DEFECTION! A furious MP has crossed the floor to join the {opposition} party!"
        
    if next_block == 2 and random.random() < 0.4:
        if s.approval < 45.0 and s.seats[s.party] > 0:
            s.seats[s.party] -= 1
            s.seats[opposition] += 1
            s.message += f" 🗳️ BY-ELECTION DEFEAT: You lost a seat to the {opposition} party due to poor national polling."
        elif s.approval >= 50.0 and s.seats[opposition] > 0:
            s.seats[s.party] += 1
            s.seats[opposition] -= 1
            s.message += f" 🗳️ BY-ELECTION VICTORY: Your high approval won you a seat from the {opposition} party!"

    update_political_capital(chosen_ideology, s.approval - s.prev_approval, s.headroom - s.prev_headroom)
    update_polling_data(next_year)
    enforce_spad_passives()
    check_imf_bailout()
    
    s.year, s.block = next_year, next_block
    s.active_crisis = scen.pick_next(s.year, s.block, chosen_ideology)
    st.rerun()

# ==================== SETUP SCREEN ====================
if st.session_state.step == 'setup':
    st.title('🏛️ The UK Chancellor Simulator (Hardcore Mode)')
    st.markdown('### Step 1: Form Your Government')
    
    col1, col2 = st.columns([1, 1])
    with col1:
        party_choice = st.selectbox('Select Governing Party:', ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru'])
        scenario = st.selectbox('Historical Scenario:', ["2026: The Fragile Present", "2008: The Great Financial Crash", "1978: Winter of Discontent"])
        
        spad_options = [
            "The Spin Doctor (Halves penalties from broken pledges/scandals)",
            "The Fiscal Hawk (+£2.0B Headroom generated every year)",
            "The Enforcer (+20 guaranteed votes in Parliament)",
            "The City Banker (Market Confidence cannot drop below 20%)"
        ]
        spad_choice = st.selectbox('Hire a Special Advisor (SpAd):', spad_options)
        
        game_seed = st.number_input('Seed (same seed, same crises):', value=68739, step=1)
        
    with col2:
        pledge_options = [
            "Never raise Basic Income Tax", 
            "Never raise VAT", 
            "Never raise Corporation Tax",
            "Never raise Capital Gains Tax",
            "Protect NHS Funding (No Cuts)",
            "Protect Education (No Cuts)",
            "Never increase Welfare Spending",
            "Eliminate the Deficit"
        ]
        pledge_choices = st.multiselect('Select exactly 3 Core Manifesto Pledges:', pledge_options, max_selections=3)

    if len(pledge_choices) != 3:
        st.warning("⚠️ You must select exactly 3 Manifesto Pledges to enter Number 11.")
    else:
        st.markdown("<br>", unsafe_allow_html=True)
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            if st.button('Enter Number 11', type='primary', use_container_width=True):
                random.seed(int(game_seed))
                s = st.session_state
                s.party = party_choice
                s.pledges = pledge_choices
                s.spad = spad_choice
                s.whip_votes = 0
                s.sleaze = 0
                
                if scenario == "2008: The Great Financial Crash":
                    s.debt, s.deficit, s.inflation, s.interest_rate = 60.0, 153.0, 4.0, 0.5
                    s.market_conf, s.headroom, s.growth = 35.0, -35.0, -2.5
                    s.macro_cycle = 'Recession'
                    msg = "Welcome to 2008, Chancellor. The global banking sector has collapsed."
                elif scenario == "1978: Winter of Discontent":
                    s.debt, s.deficit, s.inflation, s.interest_rate = 55.0, 45.0, 15.5, 12.0
                    s.gilt_yield, s.approval, s.market_conf, s.growth = 14.0, 35.0, 40.0, -1.0
                    s.macro_cycle = 'Stagnation'
                    msg = "Welcome to the 1970s, Chancellor. Inflation is rampant, and the unions are preparing for war."
                else:
                    s.macro_cycle = 'Stagnation'
                    msg = "Good morning, Chancellor. I am Sir Humphrey Appleby. The economy is fragile."

                seats_map = {
                    'Conservative': {'Conservative': 365, 'Labour': 202, 'Liberal Democrats': 11, 'SNP': 48, 'Reform UK': 1, 'Green Party': 1, 'Plaid Cymru': 4, 'Others': 18},
                    'Liberal Democrats': {'Liberal Democrats': 335, 'Labour': 160, 'Conservative': 120, 'SNP': 15, 'Reform UK': 4, 'Green Party': 2, 'Plaid Cymru': 4, 'Others': 10},
                    'Reform UK': {'Reform UK': 330, 'Conservative': 150, 'Labour': 120, 'Liberal Democrats': 30, 'SNP': 10, 'Green Party': 1, 'Plaid Cymru': 2, 'Others': 7},
                    'Green Party': {'Green Party': 330, 'Labour': 180, 'Liberal Democrats': 60, 'Conservative': 50, 'SNP': 15, 'Reform UK': 5, 'Plaid Cymru': 4, 'Others': 6},
                    'SNP': {'SNP': 50, 'Labour': 310, 'Conservative': 210, 'Liberal Democrats': 55, 'Reform UK': 10, 'Green Party': 4, 'Plaid Cymru': 4, 'Others': 7},
                    'Plaid Cymru': {'Plaid Cymru': 25, 'Labour': 315, 'Conservative': 220, 'Liberal Democrats': 60, 'Reform UK': 15, 'SNP': 10, 'Green Party': 2, 'Others': 3},
                    'Labour': {'Labour': 411, 'Conservative': 121, 'Liberal Democrats': 72, 'SNP': 9, 'Reform UK': 5, 'Green Party': 4, 'Plaid Cymru': 4, 'Others': 24}
                }
                s.seats = seats_map[party_choice]
                
                polls_map = {
                    'Conservative': [38, 32, 12, 10, 4, 3, 1], 'Liberal Democrats': [30, 30, 24, 8, 4, 3, 1],
                    'Reform UK': [28, 28, 10, 26, 4, 3, 1], 'Green Party': [28, 26, 12, 8, 22, 3, 1],
                    'SNP': [34, 30, 10, 9, 4, 12, 1], 'Plaid Cymru': [34, 30, 10, 9, 4, 3, 10],
                    'Labour': [38, 32, 12, 10, 4, 3, 1]
                }
                p_arr = polls_map[party_choice]
                s.poll_history = {'Year': [1], 'Labour': [p_arr[0]], 'Conservative': [p_arr[1]], 'Liberal Democrats': [p_arr[2]], 'Reform UK': [p_arr[3]], 'Green Party': [p_arr[4]], 'SNP': [p_arr[5]], 'Plaid Cymru': [p_arr[6]]}

                s.start_debt, s.start_growth = s.debt, s.growth
                snapshot_metrics()
                enforce_spad_passives()
                s.step, s.message = 'game', msg
                st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button('Hard Reset Cache (Fix Errors)'):
        st.session_state.clear()
        st.rerun()
    st.stop()


# ==================== PERSISTENT SIDEBAR ====================
s = st.session_state
with st.sidebar:
    st.markdown("### 💼 Chancellor's Briefcase")
    st.markdown(f"**🌍 Macro Cycle:**")
    m_color = "#6fbf8a" if s.macro_cycle == "Boom" else ("#e65c4f" if s.macro_cycle == "Recession" else "#a3b8ad")
    st.markdown(f"<span style='color:{m_color}; font-weight:bold; font-size:1.1rem;'>{s.macro_cycle.upper()}</span>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"**🕵️ Special Advisor:**")
    st.markdown(f"<span>{s.spad.split(' (')[0] if s.spad else 'None'}</span>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"**💷 Sleaze Level:** {s.sleaze}%")
    st.progress(min(100, s.sleaze) / 100.0)
    st.markdown("---")
    st.markdown("**📜 Manifesto Pledges:**")
    for pledge in s.pledges:
        if pledge in s.broken_pledges:
            st.markdown(f"❌ ~~*{pledge}*~~")
        else:
            st.markdown(f"✅ {pledge}")
            
    if s.broken_pledges:
        st.error(f"U-Turn Penalty: Max Approval capped at {s.approval_cap}%.")
        
    st.markdown("---")
    if st.button('Resign & Start New Career', use_container_width=True):
        st.session_state.clear()
        st.rerun()


# ==================== MAIN DASHBOARD ====================
header(s.party, s.term, s.year, s.block)

d_app = round(s.approval - s.prev_approval, 1)
d_mkt = round(s.market_conf - s.prev_market, 1)
d_gro = round(s.growth - s.prev_growth, 1)
d_hdr = round(s.headroom - s.prev_headroom, 1)
d_dbt = round(s.debt - s.prev_debt, 1)

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown(stat_card('Public Approval', f"{s.approval:.1f}%", f"{d_app:+}%" if d_app != 0 else '0%', "Support for you.", d_app), unsafe_allow_html=True)
c2.markdown(stat_card('Market Confidence', f"{s.market_conf:.1f}%", f"{d_mkt:+}%" if d_mkt != 0 else '0%', "Drops to 0% = IMF Bailout.", d_mkt), unsafe_allow_html=True)
c3.markdown(stat_card('Economic Growth', f"{s.growth:.1f}%", f"{d_gro:+}%" if d_gro != 0 else '0%', "Annual GDP growth.", d_gro), unsafe_allow_html=True)
c4.markdown(stat_card('OBR Headroom', f"£{s.headroom:.1f}B", f"£{d_hdr:+}B" if d_hdr != 0 else '£0B', "Keep above £0.", d_hdr), unsafe_allow_html=True)
c5.markdown(stat_card('National Debt', f"{s.debt:.1f}%", f"{d_dbt:+}%" if d_dbt != 0 else '0%', "High debt triggers bailouts.", d_dbt, inverse=True), unsafe_allow_html=True)

# ==================== END GAME & EVENT CHECKS ====================
if s.get('imf_bailout'):
    st.subheader('🚨 IMF BAILOUT TRIGGERED: GAME OVER')
    humphrey_message("Chancellor, the markets have completely lost faith in our ability to govern. The IMF is dictating policy.")
    st.error("You bankrupted the country.")
    if st.button('Start New Career'): st.session_state.clear(); st.rerun()
    st.stop()

if s.get('sacked'):
    st.subheader("🚨 SACKED FROM THE TREASURY")
    humphrey_message("I am so sorry, Chancellor. The Prime Minister feels that your continued presence is sub-optimal.")
    st.error(s.get('sacked_reason', "You have been sacked."))
    if st.button('Resign'): st.session_state.clear(); st.rerun()
    st.stop()

if s.sleaze >= 100:
    st.subheader("🚨 POLICE INVESTIGATION INTO NUMBER 11")
    humphrey_message("Chancellor, the Metropolitan Police are at the door. Your 'unconventional' fundraising and backroom deals have triggered a full-blown corruption inquiry. We need a scapegoat, immediately.")
    st.error("Sleaze has reached 100%. You must make a choice.")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Throw a Junior Minister Under the Bus\n(-40 Cabinet, -30 PM)", use_container_width=True):
            s.cab_opinion = max(0, s.cab_opinion - 40)
            s.pm_opinion = max(0, s.pm_opinion - 30)
            s.sleaze = 0
            s.message = "🚔 A junior minister has been arrested. You survive, but the Cabinet is terrified of you."
            st.rerun()
    with col2:
        if st.button("Resign in Disgrace (Game Over)", use_container_width=True):
            s.sacked = True
            s.sacked_reason = "You resigned in disgrace amid a massive corruption and sleaze scandal."
            s.sleaze = 0 
            st.rerun()
    st.stop()

if s.year > 5:
    st.subheader('🗳️ GENERAL ELECTION NIGHT: RESULTS')
    latest_polls = {p: s.poll_history[p][-1] for p in ['Labour', 'Conservative', 'Liberal Democrats', 'Reform UK', 'Green Party', 'SNP', 'Plaid Cymru']}
    seats = {}
    seats['Labour'] = int((latest_polls['Labour'] / 100) * 650 * (1.1 if latest_polls['Labour'] > 30 else 0.8))
    seats['Conservative'] = int((latest_polls['Conservative'] / 100) * 650 * (1.1 if latest_polls['Conservative'] > 30 else 0.8))
    seats['Liberal Democrats'] = int(max(5, (latest_polls['Liberal Democrats'] / 100) * 650 * 0.6))
    seats['Reform UK'] = int(max(0, (latest_polls['Reform UK'] / 100) * 650 * 0.3))
    seats['Green Party'] = int(max(1, (latest_polls['Green Party'] / 100) * 650 * 0.2))
    seats['SNP'] = int(min(57, max(4, (latest_polls['SNP'] / 100) * 650 * 3.5)))
    seats['Plaid Cymru'] = int(min(32, max(2, (latest_polls['Plaid Cymru'] / 100) * 650 * 3.0)))

    diff = 650 - sum(seats.values())
    seats[max(seats, key=seats.get)] += diff
    s.seats = seats
    player_seats = seats[s.party]

    win = False
    if player_seats >= 326:
        result_title, gov_type, win = f"{s.party} Majority", f"Working Majority of {player_seats - 326}", True
    else:
        my_bloc = ['Labour', 'Liberal Democrats', 'Green Party', 'SNP', 'Plaid Cymru'] if s.party in ['Labour', 'Green Party', 'SNP', 'Plaid Cymru'] else ['Conservative', 'Reform UK', 'Liberal Democrats']
        partner = next((p for p in my_bloc if p != s.party and player_seats + seats[p] >= 326), None)
        if partner: result_title, gov_type, win = "Hung Parliament", f"Coalition with {partner}", True
        elif player_seats == seats[max(seats, key=seats.get)]: result_title, gov_type, win = "Hung Parliament", "Minority Government", True
        else: result_title, gov_type, win = "Hung Parliament", "Sent to Opposition", False

    st.markdown(f"<div style='background-color: {'#2b5440' if win else '#8b0000'}; padding: 20px; border-radius: 10px; color: white; text-align: center; border: 2px solid #c9a45c;'><h2>{result_title}</h2><h4 style='color: #c9a45c;'>{gov_type}</h4><p style='font-size: 18px;'>Your Seats: <b>{player_seats}</b></p></div>", unsafe_allow_html=True)
    render_parliament_bar(seats, s.party)

    st.markdown("### 📜 The Treasury Record (Legacy Report)")
    l1, l2, l3, l4 = st.columns(4)
    l1.metric("Debt Inherited vs Now", f"{s.debt:.1f}%", f"{s.debt - s.start_debt:+.1f}%", delta_color='inverse')
    l2.metric("Growth Inherited vs Now", f"{s.growth:.1f}%", f"{s.growth - s.start_growth:+.1f}%")
    l3.metric("Total Homes Built", f"{st.session_state.country['homes_built'] * 5:.0f}k")
    l4.metric("Manifesto U-Turns", f"{len(s.broken_pledges)}")

    if win:
        humphrey_message("We have survived the electorate. You remain at the Treasury.")
        if st.button('Continue as Chancellor'):
            s.term += 1; s.year = 1; s.block = 1
            st.rerun()
    else:
        humphrey_message("The electorate has spoken. We have been thoroughly evicted.")
        if st.button('Start New Career'): st.session_state.clear(); st.rerun()
    st.stop()

# ==================== BUDGET BLOCK ====================
if s.block == 3:
    if s.get('budget_passed'):
        st.subheader("🏛 Parliamentary Vote Results")
        
        bb = s.backbench_opinion
        commons_ayes = int(326 + (bb / 1.5) - 20 + (s.year * 2) + s.get('whip_votes', 0))
        if s.spad and s.spad.startswith('The Enforcer'): commons_ayes += 20
        commons_ayes = min(650, max(0, commons_ayes))
        
        if bb > 70: st.success(f"**House of Commons:** Passed with a thumping majority! (Ayes: {commons_ayes})")
        elif bb > 40: st.info(f"**House of Commons:** Passed with some grumbling. (Ayes: {commons_ayes})")
        else: st.warning(f"**House of Commons:** Barely scraped through! (Ayes: {commons_ayes})")
            
        humphrey_message("As for the House of Lords, they supported the bill. Though the Parliament Act of 1911 means they cannot vote down a Money Bill anyway.")
        if s.get('headlines'): render_newspapers(*s.headlines)
        st.markdown('### 🌐 IMF Article IV Projections')
        render_imf_table(get_imf_projections())
        
        st.divider()
        if st.button('Proceed to Spring', type='primary', use_container_width=True):
            snapshot_metrics() 
            budget.apply_ongoing()
            check_pledges()
            shift_macro_cycle()
            s.pm_opinion = min(100, s.pm_opinion + (5 if s.headroom > 0 else -5))
            if s.spad and s.spad.startswith('The Fiscal Hawk'):
                s.headroom += 2.0
                s.message = "🦅 Your Fiscal Hawk SpAd magically found £2.0B in 'efficiency savings'."
            s.year += 1; s.block = 1; s.budget_passed = False; s.headlines = None
            s.whip_votes = 0
            enforce_spad_passives()
            check_imf_bailout()
            st.rerun()
    else:
        st.subheader(f"Year {s.year} - Block 3: The Chancellor's Budget")
        humphrey_message("A budget, Chancellor, is merely a collection of numbers we present to the House to obscure our true intentions.")
        
        st.markdown("### 📜 Active Manifesto Pledges")
        st.caption("Do not violate these promises in your budget below, or the press will crucify you for a U-Turn.")
        p_cols = st.columns(3)
        for i, p in enumerate(s.pledges):
            if p in s.broken_pledges:
                p_cols[i%3].markdown(f"<div style='background:#2a1111; border:1px solid #e65c4f; padding:10px; border-radius:6px; color:#e3b3ab; text-align:center;'>❌ <s>{p}</s></div>", unsafe_allow_html=True)
            else:
                p_cols[i%3].markdown(f"<div style='background:#10261c; border:1px solid #6fbf8a; padding:10px; border-radius:6px; color:#6fbf8a; text-align:center; font-weight:bold;'>✅ {p}</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
            
        if 'budget_applied' not in s: budget.ensure()
        budget.render()
        
        st.markdown("---")
        st.markdown("### 🏛️ The Whips' Office: Parliamentary Arithmetic")
        draft = budget.read()
        
        s.whip_votes = s.get('whip_votes', 0)
        
        revolt_warning = ""
        if s.party in ['Conservative', 'Reform UK'] and (draft['tax']['corp'] - budget.TAXES['corp']['default']) > 0: revolt_warning = "🚨 WHIP WARNING: MPs threatening to rebel over Corp Tax hikes!"
        if s.party in ['Labour', 'Green Party'] and float(draft['spend']['welfare']) < 0: revolt_warning = "🚨 WHIP WARNING: Left wing preparing to rebel over welfare cuts!"
        if revolt_warning: st.error(revolt_warning)

        bb = s.backbench_opinion
        commons_ayes = int(326 + (bb / 1.5) - 20 + (s.year * 2) + s.whip_votes)
        if s.spad and s.spad.startswith('The Enforcer'): commons_ayes += 20
        if revolt_warning: commons_ayes -= 35
        commons_ayes = min(650, max(0, commons_ayes))
        
        if commons_ayes < 326: st.error(f"🚨 PROJECTED DEFEAT: Only {commons_ayes} votes in favour. You need 326.")
        else: st.success(f"✅ PROJECTED PASS: {commons_ayes} votes in favour.")

        st.markdown(f"**Current Backbench Morale:** {bb:.0f}/100 &nbsp;|&nbsp; **Whip Interventions Applied:** +{s.whip_votes} Votes")

        col_w1, col_w2, col_w3 = st.columns(3)
        with col_w1:
            if st.button("🥓 Offer Pork-Barrel Funds\n(-£2B Headroom, +15 Votes, +15 Sleaze)", disabled=s.headroom < 2.0, use_container_width=True): 
                st.session_state.headroom -= 2.0
                st.session_state.whip_votes += 15
                st.session_state.sleaze += 15
                st.rerun()
        with col_w2:
            if st.button("🗡️ Threaten Rebels\n(-15 Unity, +15 Votes, +10 Sleaze)", use_container_width=True, disabled=s.party_opinion < 15): 
                st.session_state.party_opinion = max(0, s.party_opinion - 15)
                st.session_state.whip_votes += 15
                st.session_state.sleaze += 10
                st.rerun()
        with col_w3:
            if st.button("🤝 Water Down Reforms\n(-2 Market Conf, +10 Votes)", use_container_width=True, disabled=s.market_conf < 2): 
                st.session_state.market_conf = max(0, s.market_conf - 2.0)
                st.session_state.whip_votes += 10
                st.rerun()

        st.divider()
        if st.button('Submit Budget to the Commons', type='primary'):
            if commons_ayes < 326:
                s.sacked = True
                s.sacked_reason = "You failed to secure the votes. The budget was defeated in the House of Commons, collapsing the Government."
                st.rerun()
            else:
                if s.approval < 40: s.market_conf -= 1.0
                s.budget_passed = True
                s.headlines = generate_headlines(None, True, s.headroom)
                st.rerun()

# ==================== STANDARD BLOCK ====================
else:
    col_game, col_dash = st.columns([1.3, 1.0], gap="large")
    with col_dash:
        tab_econ, tab_pol, tab_nation = st.tabs(['📊 Economy', '🏛 Politics', '🇬🇧 Nation'])
        with tab_econ:
            debt_servicing = round(budget.interest(), 1)
            gbp_usd = round(1.27 * (1.0 + 0.15 * (s.market_conf / 65.0 - 1.0) - 0.05 * (s.inflation / 3.0 - 1.0)), 2)
            b_tax = s.get('budget_applied', {}).get('tax', {})
            tax_burden = round(36.8 + 0.1 * (b_tax.get('inc_basic', 20) - 20) + 0.08 * (b_tax.get('corp', 25) - 25), 1)

            e1, e2 = st.columns(2)
            e1.markdown(stat_card('Annual Deficit', f'£{round(s.deficit, 1)}B', 'current', "Shortfall this year."), unsafe_allow_html=True)
            e2.markdown(stat_card('Debt Servicing', f'£{debt_servicing}B/yr', f'{debt_servicing - 105.4:+.1f}B', "Interest paid.", debt_servicing - 105.4, inverse=True), unsafe_allow_html=True)
            
            e3, e4 = st.columns(2)
            e3.markdown(stat_card('Inflation Rate', f'{round(s.inflation, 1)}%', 'current', "CPI Inflation."), unsafe_allow_html=True)
            e4.markdown(stat_card('Bank Rate', f'{round(s.interest_rate, 1)}%', 'current', "BoE base rate."), unsafe_allow_html=True)
            
            e5, e6 = st.columns(2)
            e5.markdown(stat_card('10-Yr Gilt Yield', f'{round(s.gilt_yield, 1)}%', 'current', "Government borrowing cost."), unsafe_allow_html=True)
            e6.markdown(stat_card('GBP/USD', f'${gbp_usd:.2f}', f'{gbp_usd - 1.27:+.2f}', "Strength of Sterling.", gbp_usd - 1.27), unsafe_allow_html=True)

            st.markdown(f"<div style='text-align:right; font-size:0.85rem; color:#a3b8ad; margin-bottom:12px;'>Overall UK Tax Burden: <b>{tax_burden}% of GDP</b></div>", unsafe_allow_html=True)
            render_parliament_bar(s.seats, s.party)

        with tab_pol:
            p1, p2 = st.columns(2)
            p1.markdown(stat_card("PM's Confidence", f"{s.pm_opinion:.0f}/100", f"{s.pm_opinion - s.prev_pm:+.0f}", "Below 40 = Sacked", (s.pm_opinion - s.prev_pm)), unsafe_allow_html=True)
            p2.markdown(stat_card('Cabinet Support', f"{s.cab_opinion:.0f}/100", f"{s.cab_opinion - s.prev_cab:+.0f}", "Ministers' backing.", (s.cab_opinion - s.prev_cab)), unsafe_allow_html=True)
            
            p3, p4 = st.columns(2)
            p3.markdown(stat_card('Party Unity', f"{s.party_opinion:.0f}/100", f"{s.party_opinion - s.prev_party:+.0f}", "Below 40 = Rebellion", (s.party_opinion - s.prev_party)), unsafe_allow_html=True)
            p4.markdown(stat_card('Backbench Morale', f"{s.backbench_opinion:.0f}/100", f"{s.backbench_opinion - s.prev_backbench:+.0f}", "Below 20 = Defeat", (s.backbench_opinion - s.prev_backbench)), unsafe_allow_html=True)
            
            st.markdown(stat_card('Media Sentiment', f"{s.media_opinion:.0f}/100", f"{s.media_opinion - s.prev_media:+.0f}", "Below 30 = Scandals", (s.media_opinion - s.prev_media)), unsafe_allow_html=True)

            st.markdown('### 🏛️ Political Actions')
            col_pa1, col_pa2 = st.columns(2)
            with col_pa1:
                if st.button("🔄 Reshuffle Cabinet", help="Spend 15 PM Opinion and 20 Cabinet Support to purge rebels, restoring 25 Party Unity and 25 Backbench Morale.", use_container_width=True):
                    if s.pm_opinion > 30:
                        s.pm_opinion -= 15; s.cab_opinion -= 20
                        s.party_opinion = min(100, s.party_opinion + 25); s.backbench_opinion = min(100, s.backbench_opinion + 25)
                        s.message = "🔄 The PM has brutally reshuffled the Cabinet! Rebels purged."
                        st.rerun()
                    else: st.error("The PM is too weak to survive a reshuffle!")
                
                if st.button("🎙️ PM Broadcast", help="Spend 10 Cabinet Support to bypass the press (+10 Approval, -15 Media).", use_container_width=True):
                    if s.cab_opinion > 20:
                        s.cab_opinion -= 10
                        s.approval = min(s.approval_cap, s.approval + 10); s.media_opinion = max(0, s.media_opinion - 15)
                        s.message = "🎙️ You delivered a direct broadcast. The public loved it, but the media pundits are furious about being bypassed!"
                        st.rerun()
                    else: st.error("The Cabinet refuses to endorse a broadcast.")

            with col_pa2:
                if st.button("🍷 Court Media Barons", help="Schmooze newspaper owners (+20 Media Sentiment, -15 Party Unity, +20 Sleaze).", use_container_width=True, disabled=s.party_opinion < 15):
                    s.media_opinion = min(100, s.media_opinion + 20); s.party_opinion = max(0, s.party_opinion - 15)
                    s.sleaze += 20
                    s.message = "🍷 You attended private dinners with media barons. Fleet Street is glowing, but your grassroots are disgusted by the sleaze."
                    st.rerun()
                if st.button("💰 Solicit Mega-Donors", help="Secure funding to pacify the party machine (+20 Party Unity, -10 Approval, +25 Sleaze).", use_container_width=True, disabled=s.approval < 10):
                    s.party_opinion = min(100, s.party_opinion + 20); s.approval = max(0, s.approval - 10)
                    s.sleaze += 25
                    s.message = "💰 You secured massive donations. The party machine is well-oiled, but the public sees it as cash-for-access."
                    st.rerun()

            st.markdown('### 📈 Voting Intention')
            render_polls(pd.DataFrame(s.poll_history).set_index('Year'))
                
        with tab_nation:
            country.render()
            
    with col_game:
        if s.get('message'): news_box(s.message)
        if s.get('headlines'): render_newspapers(*s.headlines)
            
        if s.active_crisis is not None:
            crisis = scen.get(s.active_crisis)
            if crisis is None: s.active_crisis = None; st.rerun()
            crisis_card(crisis['title'])
            humphrey_message(crisis['humphrey'])
            if s.get('crisis_reason'): st.caption(s.crisis_reason)
                
            labels = scen.option_labels(crisis)
            choice = st.radio('Choose emergency response:', labels)
            
            if st.button('Resolve Crisis', type="primary"):
                snapshot_metrics()
                idx = labels.index(choice)
                s.message = scen.resolve(crisis, idx)
                proxy = ['Hard Left', 'Centric', 'Free-Market', 'Centric'][idx] if idx < 4 else 'Centric'
                s.headlines = generate_headlines(proxy)
                update_political_capital(proxy, s.approval - s.prev_approval, s.headroom - s.prev_headroom)
                s.active_crisis = None
                enforce_spad_passives()
                check_imf_bailout()
                st.rerun()
        else:
            decision_data = decisions.get_decision(s.term, s.year, s.block)
            if decision_data:
                st.subheader(f"Block {s.block}: {decision_data['title']}")
                st.write(decision_data['text'])
                humphrey_message(decision_data['humphrey'])
                choice = st.radio('Select strategy:', decision_data['options'])
                
                if st.button(f'Execute Policy', type="primary"):
                    idx = decision_data['options'].index(choice)
                    effect = decision_data['effects'][idx]
                    s.message = effect.get('message', 'Decision applied.')
                    for key in ['headroom', 'approval', 'market_conf', 'deficit', 'growth', 'inflation', 'gilt_yield']:
                        if key in effect: s[key] = round(s[key] + effect[key], 2 if key in ['growth', 'inflation', 'gilt_yield'] else 1)
                    process_block_execution(s.year, s.block + 1, ['Hard Left', 'Social Democratic', 'Centric', 'Free-Market', 'Fiscal Austerity'][idx], effect)
            else:
                st.write("No decision data found for this block.")
                if st.button("Skip Block"): process_block_execution(s.year, s.block + 1, 'Centric')
