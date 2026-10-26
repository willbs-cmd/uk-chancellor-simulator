"""Additional fiscal calendar and institutions mechanics for the Chancellor Simulator."""
import streamlit as st

def _clip(x, lo=0, hi=100):
    return max(lo, min(hi, x))

def _used():
    s = st.session_state
    key = f"feature_actions_y{s.get('year', 1)}"
    if key not in s:
        s[key] = []
    return key, s[key]

def _act(key, cost, label, effect):
    s = st.session_state
    used_key, used = _used()
    capital = int(s.get("political_capital_points", 5))
    if key in used:
        st.info(f"{label} has already been used this year.")
        return
    if capital < cost:
        st.warning(f"Not enough political capital. {label} costs {cost}; you have {capital}.")
        return
    s.political_capital_points = capital - cost
    s[used_key] = used + [key]
    effect(s)
    s.message = (s.get("message", "") + " " + label + " announced.").strip()
    st.success(f"{label} announced. Political capital remaining: {s.political_capital_points}.")

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
    st.caption("Choose when to spend political capital. Each action can be taken once per year; the same political capital must cover statements, the Bank, pay talks and constitutional bargaining.")
    m1, m2, m3 = st.columns(3)
    m1.metric("Political capital", f"{s.political_capital_points}/5")
    m2.metric("Productivity trend", f"{s.longrun_productivity:.1f}%")
    m3.metric("Pension pressure", f"{s.pension_pressure:.1f} index")
    t1, t2, t3, t4 = st.tabs(["Statements & Budget", "Bank & gilts", "Pay & tax", "Devolution & career"])
    with t1:
        st.markdown("**Fiscal events**")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.caption("Autumn Statement")
            st.write("Set the direction before the main Budget.")
            if st.button("Deliver Autumn Statement", key="feat_autumn", use_container_width=True):
                _act("autumn", 1, "Autumn Statement", lambda x: (setattr(x, "market_conf", _clip(x.market_conf + 2)), setattr(x, "headroom", round(x.headroom - 0.5, 1))))
                st.rerun()
        with c2:
            st.caption("Spring Statement")
            st.write("Refresh the forecast and reassure markets.")
            if st.button("Deliver Spring Statement", key="feat_spring", use_container_width=True):
                _act("spring_statement", 1, "Spring Statement", lambda x: (setattr(x, "market_conf", _clip(x.market_conf + 3)), setattr(x, "approval", _clip(x.approval + 1))))
                st.rerun()
        with c3:
            st.caption("Emergency mini-budget")
            st.write("Act fast, with a risk of market backlash.")
            if st.button("Issue emergency mini-budget", key="feat_mini", use_container_width=True):
                def mini(x):
                    x.headroom = round(x.headroom - 3.0, 1); x.growth = round(x.growth + .3, 2)
                    x.market_conf = _clip(x.market_conf - 5); x.gilt_yield = round(x.gilt_yield + .25, 2)
                _act("mini", 2, "Emergency mini-budget", mini)
                st.rerun()
    with t2:
        st.markdown("**Bank of England and gilt issuance**")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Coordinate quantitative easing", key="feat_qe", use_container_width=True):
                def qe(x):
                    x.gilt_yield = round(max(.1, x.gilt_yield - .3), 2); x.market_conf = _clip(x.market_conf + 2)
                    x.inflation = round(x.inflation + .2, 2); x.debt = round(x.debt + .3, 2)
                _act("qe", 2, "Quantitative easing coordination", qe); st.rerun()
            if st.button("Pressure for lower rates", key="feat_rate", use_container_width=True):
                def rates(x):
                    x.interest_rate = round(max(.1, x.interest_rate - .25), 2); x.growth = round(x.growth + .15, 2)
                    x.market_conf = _clip(x.market_conf - 3); x.pm_opinion = _clip(x.pm_opinion - 2)
                _act("rate_pressure", 2, "Rate-pressure intervention", rates); st.rerun()
            if st.button("Defend Bank independence", key="feat_independence", use_container_width=True):
                def defend(x):
                    x.market_conf = _clip(x.market_conf + 4); x.gilt_yield = round(max(.1, x.gilt_yield - .1), 2)
                _act("bank_independence", 1, "Public defence of Bank independence", defend); st.rerun()
        with b2:
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
        pay = st.radio("Negotiating position", ["Inflation-matching settlement", "Targeted compromise", "Pay cap and arbitration"], key="feature_pay_choice", horizontal=False)
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
        freeze = st.checkbox("Freeze income-tax thresholds (fiscal drag)", key="feature_threshold_freeze")
        triple = st.checkbox("Uprate pensions by the triple lock", key="feature_triple_lock")
        if st.button("Set threshold and pension policy", key="feat_tax_pension", use_container_width=True):
            def tax_fx(x):
                if freeze:
                    x.threshold_freeze_years = int(x.threshold_freeze_years) + 1
                    x.headroom = round(x.headroom + .7, 1); x.approval = _clip(x.approval - 1)
                if triple:
                    x.pension_pressure = round(x.pension_pressure + 1.0, 1)
                    x.headroom = round(x.headroom - 1.2, 1); x.approval = _clip(x.approval + 2)
                x.longrun_productivity = round(x.longrun_productivity + (.1 if not freeze else 0), 2)
            _act("tax_pension", 1, "Tax threshold and pension decision", tax_fx); st.rerun()
        st.caption(f"Threshold freeze duration: {s.threshold_freeze_years} year(s). Pension pressure compounds: {s.pension_pressure:.1f}.")
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
