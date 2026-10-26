"""Additional fiscal calendar and institutions mechanics for the Chancellor Simulator."""
import streamlit as st

def _clip(x, lo=0, hi=100):
    return max(lo, min(hi, x))

def _used():
    s = st.session_state
    s.setdefault("feature_actions", {})
    year_key = str(s.get("year", 1))
    s["feature_actions"].setdefault(year_key, [])
    return year_key, s["feature_actions"][year_key]

def _act(key, cost, label, effect):
    s = st.session_state
    year_key, used = _used()
    capital = int(s.get("political_capital_points", 5))
    if key in used:
        s.feature_notice = f"{label} has already been used this year."
        return False
    if capital < cost:
        s.feature_notice = f"Not enough political capital: {label} costs {cost}, but you have {capital}."
        return False
    s.political_capital_points = capital - cost
    s.feature_actions[year_key] = used + [key]
    effect(s)
    s.message = (s.get("message", "") + " " + label + " announced.").strip()
    s.feature_notice = f"{label} announced. Political capital remaining: {s.political_capital_points}/5."
    s.feature_notice_phase = int(s.get("block", 1))
    return True

def render_phase_action():
    """Show the fiscal event that belongs to the current annual phase."""
    s = st.session_state
    _, used = _used()
    if s.get("feature_notice") and int(s.get("feature_notice_phase", 0)) == int(s.block):
        st.info(s.feature_notice)
    if s.block == 1:
        with st.expander("💷 Optional Autumn Statement · costs 1 political capital", expanded=False):
            st.write("Set out the government's fiscal direction before winter. It can reassure investors, but uses some fiscal headroom.")
            st.caption("If announced: +2 market confidence and −£0.5bn headroom. Once per year.")
            if st.button("Deliver Autumn Statement", key="phase_autumn_statement",
                         disabled="autumn" in used, use_container_width=True):
                _act("autumn", 1, "Autumn Statement",
                     lambda x: (setattr(x, "market_conf", _clip(x.market_conf + 2)),
                                setattr(x, "headroom", round(x.headroom - 0.5, 1))))
                st.rerun()
    elif s.block == 2:
        with st.expander("🚨 Optional emergency mini-budget · costs 2 political capital", expanded=False):
            st.write("A fast package can stimulate activity, but if it looks unfunded markets may demand higher borrowing costs.")
            st.caption("If announced: +0.3 percentage points growth, −£3bn headroom, −5 market confidence and +0.25 points gilt yield.")
            if st.button("Issue emergency mini-budget", key="phase_mini_budget",
                         disabled="mini" in used, use_container_width=True):
                def mini(x):
                    x.headroom = round(x.headroom - 3.0, 1)
                    x.growth = round(x.growth + 0.3, 2)
                    x.market_conf = _clip(x.market_conf - 5)
                    x.gilt_yield = round(x.gilt_yield + 0.25, 2)
                _act("mini", 2, "Emergency mini-budget", mini)
                st.rerun()

def render():
    s = st.session_state
    # Backward-compatible defaults for games saved before this feature existed.
    s.setdefault("political_capital_points", 5)
    s.setdefault("longrun_productivity", 1.0)
    s.setdefault("pension_pressure", 0.0)
    s.setdefault("threshold_freeze_years", 0)
    s.setdefault("gilt_maturity_years", 10)
    s.setdefault("index_linked_share", 25)
    s.setdefault("pay_settlement", "unsettled")
    st.markdown("### Fiscal calendar & institutions")
    st.caption("Choose when to spend political capital. Each action can be taken once per year; the same limited pool covers statements, the Bank, pay talks and constitutional bargaining.")
    if s.get("feature_notice"):
        st.info(s.feature_notice)
    m1, m2, m3 = st.columns(3)
    m1.metric("Political capital", f"{s.political_capital_points}/5")
    m2.metric("Productivity trend", f"{s.longrun_productivity:.1f}%")
    m3.metric("Pension pressure", f"{s.pension_pressure:.1f} index")
    t1, t2, t3, t4 = st.tabs(["Statements", "Bank & gilts", "Pay & tax", "Devolution"])
    with t1:
        st.markdown("**Spring Statement**")
        st.write("Before delivering the Budget, publish an updated view of the economy and reassure markets. This is a forecast statement, not the full tax-and-spending package.")
        st.caption("If announced: +3 market confidence and +1 point public approval. Costs 1 political capital.")
        _, used = _used()
        if "spring_statement" in used:
            st.success("Spring Statement already delivered this year.")
        elif st.button("Deliver Spring Statement", key="feat_spring_statement", use_container_width=True):
            def spring_statement(x):
                x.market_conf = _clip(x.market_conf + 3)
                x.approval = _clip(x.approval + 1)
            _act("spring_statement", 1, "Spring Statement", spring_statement)
            st.rerun()
        st.divider()
        st.markdown("**Fiscal-year checklist**")
        _, used = _used()
        statuses = [
            ("Autumn Statement", "autumn", "Phase 1 · Autumn"),
            ("Emergency mini-budget", "mini", "Phase 2 · Winter"),
            ("Spring Statement", "spring_statement", "Phase 3 · Spring"),
        ]
        for label, key, timing in statuses:
            st.markdown(f"{'✅' if key in used else '◯'} **{label}** — {timing}")
        st.caption("Statements are optional. Political capital spent here cannot be used for Bank interventions, pay talks or regional bargaining.")

    with t2:
        st.markdown("**Bank of England and gilt issuance**")
        b1, b2 = st.columns(2, gap="medium")
        with b1:
            st.caption("QE costs 2 capital: it lowers gilt yields and may support markets, but can lift inflation and debt.")
            if st.button("Coordinate quantitative easing", key="feat_qe", use_container_width=True):
                def qe(x):
                    x.gilt_yield = round(max(.1, x.gilt_yield - .3), 2); x.market_conf = _clip(x.market_conf + 2)
                    x.inflation = round(x.inflation + .2, 2); x.debt = round(x.debt + .3, 2)
                _act("qe", 2, "Quantitative easing coordination", qe); st.rerun()
            st.caption("Rate pressure costs 2 capital: it may lift growth in the short term but damages confidence in Bank independence and market trust.")
            if st.button("Pressure for lower rates", key="feat_rate", use_container_width=True):
                def rates(x):
                    x.interest_rate = round(max(.1, x.interest_rate - .25), 2); x.growth = round(x.growth + .15, 2)
                    x.market_conf = _clip(x.market_conf - 3); x.pm_opinion = _clip(x.pm_opinion - 2)
                _act("rate_pressure", 2, "Rate-pressure intervention", rates); st.rerun()
            st.caption("Defending independence costs 1 capital and is designed to reassure investors.")
            if st.button("Defend Bank independence", key="feat_independence", use_container_width=True):
                def defend(x):
                    x.market_conf = _clip(x.market_conf + 4); x.gilt_yield = round(max(.1, x.gilt_yield - .1), 2)
                _act("bank_independence", 1, "Public defence of Bank independence", defend); st.rerun()
        with b2:
            st.caption("Choose how long the government borrows for. Long maturities lock in financing for longer; short maturities need refinancing sooner.")
            s.gilt_maturity_years = st.select_slider("New gilt maturity", options=[2, 5, 10, 20, 30], value=int(s.gilt_maturity_years))
            s.index_linked_share = st.slider("Index-linked share (%)", 0, 100, int(s.index_linked_share), 5)
            if st.button("Hold gilt auction", key="feat_auction", use_container_width=True):
                def auction(x):
                    maturity = int(x.gilt_maturity_years)
                    x.debt = round(x.debt + (0.2 if maturity >= 20 else 0.1), 2)
                    if maturity <= 5: x.gilt_yield = round(x.gilt_yield + .12, 2)
                    else: x.gilt_yield = round(max(.1, x.gilt_yield - .04), 2)
                    if int(x.index_linked_share) > 40:
                        x.headroom = round(x.headroom - .6, 1)
                    x.message = f"Gilt auction: {maturity}-year issuance; {x.index_linked_share}% index-linked."
                _act("gilt_auction", 1, "Gilt auction", auction); st.rerun()
            st.caption("Short maturities refinance sooner; long maturities lock in yields. Index-linked debt exposes the Treasury to inflation.")
    with t3:
        st.markdown("**Public-sector pay round**")
        pay = st.radio("Negotiating position", ["Inflation-matching settlement", "Targeted compromise", "Pay cap and arbitration"], key="feature_pay_choice", horizontal=False, help="An inflation-matching deal costs more but improves morale; a pay cap saves money but increases strike and morale risks.")
        if st.button("Conclude annual pay round", key="feat_pay", use_container_width=True):
            def pay_fx(x):
                if pay == "Inflation-matching settlement":
                    x.headroom = round(x.headroom - 2.0, 1); x.approval = _clip(x.approval + 3)
                    x.country["nhs_morale"] = _clip(x.country["nhs_morale"] + 8)
                    x.backbench_opinion = _clip(x.backbench_opinion + 2)
                elif pay == "Targeted compromise":
                    x.headroom = round(x.headroom - .8, 1); x.approval = _clip(x.approval + 1)
                    x.country["nhs_morale"] = _clip(x.country["nhs_morale"] + 3)
                else:
                    x.headroom = round(x.headroom + .8, 1); x.approval = _clip(x.approval - 3)
                    x.country["nhs_morale"] = _clip(x.country["nhs_morale"] - 10)
                    x.backbench_opinion = _clip(x.backbench_opinion - 3)
                x.pay_settlement = pay
            _act("pay_round", 2, "Public-sector pay round", pay_fx); st.rerun()
        st.markdown("**Tax thresholds and pensions**")
        freeze = st.checkbox("Freeze income-tax thresholds (fiscal drag)", key="feature_threshold_freeze", help="Frozen thresholds can raise revenue as nominal earnings rise, but gradually squeeze take-home pay.")
        freeze_scope = st.radio("Threshold freeze scope", ["Personal allowance and higher-rate threshold", "Higher-rate threshold only"], key="feature_threshold_scope", horizontal=False)
        council_tax = st.checkbox("Revalue council tax bands", key="feature_council_tax", help="A simplified revaluation raises receipts but can anger households whose bills increase.")
        pension_relief = st.checkbox("Reduce higher-rate pension tax relief", key="feature_pension_relief", help="Raises revenue but makes pension saving less attractive to some higher-rate taxpayers.")
        triple = st.checkbox("Uprate pensions by the triple lock", key="feature_triple_lock", help="Improves pensioner incomes but increases the long-run pension bill.")
        productivity_plan = st.checkbox("Fund skills, research and infrastructure for productivity", key="feature_productivity_plan", help="Costs £0.5bn of headroom now and improves the long-run productivity trend.")
        if st.button("Set threshold and pension policy", key="feat_tax_pension", use_container_width=True):
            def tax_fx(x):
                if freeze:
                    x.threshold_freeze_years = round(float(x.threshold_freeze_years) + (1 if freeze_scope == "Personal allowance and higher-rate threshold" else 0.6), 1)
                    x.headroom = round(x.headroom + (.7 if freeze_scope == "Personal allowance and higher-rate threshold" else .4), 1)
                    x.approval = _clip(x.approval - (1.5 if freeze_scope == "Personal allowance and higher-rate threshold" else .8))
                if council_tax:
                    x.headroom = round(x.headroom + .5, 1); x.approval = _clip(x.approval - 1.5)
                    x.message = (x.get("message", "") + " Council tax band revaluation sparks local controversy.").strip()
                if pension_relief:
                    x.headroom = round(x.headroom + .8, 1); x.approval = _clip(x.approval - 1)
                    x.party_opinion = _clip(x.party_opinion - 1)
                if triple:
                    x.pension_pressure = round(x.pension_pressure + 1.0, 1)
                    x.headroom = round(x.headroom - 1.2, 1); x.approval = _clip(x.approval + 2)
                if productivity_plan:
                    x.longrun_productivity = round(x.longrun_productivity + .15, 2)
                    x.headroom = round(x.headroom - .5, 1)
            _act("tax_pension", 1, "Tax threshold and pension decision", tax_fx); st.rerun()
        st.caption(f"Threshold freeze duration: {s.threshold_freeze_years} year(s). Pension pressure compounds: {s.pension_pressure:.1f}.")
    with st.expander("📖 Glossary: what these controls mean", expanded=False):
        st.markdown("**Political capital** is a limited annual resource for interventions; spend it on the most important priorities. **Market confidence** is a simplified investor sentiment score, not a direct market price.")
        st.markdown("**Quantitative easing (QE)** means a central bank buys assets to loosen financial conditions; it can support demand but may add inflation risk. **Gilts** are UK government bonds. Maturity is how long until they must be repaid; index-linked gilts rise with inflation.")
        st.markdown("**Fiscal drag** occurs when tax thresholds stay frozen while earnings rise, bringing more income into tax or higher bands. **Triple lock** means the state pension rises by the highest of earnings growth, inflation or 2.5%; this game uses an abstract pension-pressure index.")
        st.markdown("**Productivity** is output per hour worked. **Pension pressure** represents long-run costs from an ageing population and pension commitments. **Block-grant bargaining** models negotiations between Westminster and devolved governments.")
        st.markdown("**Leadership challenge** is a simplified political gamble: success depends on party and Cabinet support; failure risks your job. These are game abstractions, not real economic forecasts.")
    with t4:
        if s.party in ("SNP", "Plaid Cymru"):
            st.markdown("**Devolution negotiation**")
            st.write("Negotiate a larger block grant using a Barnett-formula settlement, or accept a fiscal package from Westminster.")
            deal = st.radio("Negotiating stance", ["Demand a larger block grant", "Accept a compromise", "Reject Westminster's offer"], key="feature_devolution")
            if st.button("Negotiate block grant", key="feat_devolution", use_container_width=True):
                def dev(x):
                    if deal == "Demand a larger block grant":
                        x.headroom = round(x.headroom - 1.5, 1); x.approval = _clip(x.approval + 4)
                        x.party_opinion = _clip(x.party_opinion + 4)
                    elif deal == "Accept a compromise":
                        x.headroom = round(x.headroom - .5, 1); x.approval = _clip(x.approval + 2)
                    else:
                        x.pm_opinion = _clip(x.pm_opinion - 4); x.party_opinion = _clip(x.party_opinion + 1)
                _act("devolution", 2, "Barnett block-grant negotiation", dev); st.rerun()
        else:
            st.info("Choose SNP or Plaid Cymru at game setup to unlock the regional block-grant negotiation.")
        st.markdown("**Political ladder**")
        if st.button("Challenge a weakened Prime Minister", key="feat_challenge", use_container_width=True,
                     disabled=(s.get("pm_opinion", 100) > 45 or s.get("political_capital_points", 5) < 3)):
            def challenge(x):
                if x.party_opinion >= 50 and x.cab_opinion >= 45:
                    x.pm_opinion = _clip(x.pm_opinion + 20); x.political_capital_points = max(0, x.political_capital_points - 2)
                    x.message = "The party backs your challenge. You become Prime Minister and remain Chancellor during the transition."
                    x.is_prime_minister = True
                else:
                    x.pm_opinion = _clip(x.pm_opinion - 15); x.party_opinion = _clip(x.party_opinion - 8)
                    x.message = "Your leadership challenge collapses. The PM moves to remove you."
                x.game_over = {"kind": "leadership", "title": "Leadership challenge", "text": x.message} if not x.get("is_prime_minister") else x.get("game_over")
            _act("leadership_challenge", 3, "Leadership challenge", challenge); st.rerun()
        st.markdown("**Long-run pressure**")
        st.caption(f"Productivity index: {s.longrun_productivity:.1f}%. Pension pressure: {s.pension_pressure:.1f}.")
        if s.threshold_freeze_years:
            st.warning("Fiscal drag is raising receipts gradually, but frozen thresholds squeeze take-home pay.")
