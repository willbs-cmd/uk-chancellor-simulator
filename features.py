"""Additional fiscal calendar and institutions mechanics for the Chancellor Simulator."""
import streamlit as st
import state

def _clip(x, lo=0, hi=100):
    return max(lo, min(hi, x))

def _used():
    s = st.session_state
    s.setdefault("feature_actions", {})
    year_key = f"{s.get('term', 1)}:{s.get('year', 1)}"
    s["feature_actions"].setdefault(year_key, [])
    return year_key, s["feature_actions"][year_key]

def _act(key, cost, label, effect):
    s = st.session_state
    year_key, used = _used()
    s.feature_notice_phase = int(s.get("block", 1))
    capital = int(s.get("political_capital_points", 5))
    if key in used:
        s.feature_notice = f"{label} has already been used this year."
        return False
    if capital < cost:
        s.feature_notice = f"Not enough political capital: {label} costs {cost}, but you have {capital}."
        return False
    before = state.values()
    state.snapshot()
    s.political_capital_points = capital - cost
    s.feature_actions[year_key] = used + [key]
    effect(s)
    s.message = (s.get("message", "") + " " + label + " announced.").strip()
    s.feature_notice = f"{label} announced. Political capital remaining: {s.political_capital_points}/5."
    s.feature_notice_phase = int(s.get("block", 1))
    state.log("event", label, before=before, note=s.feature_notice)
    state.record()
    return True

def render_phase_action():
    """Render the fiscal event attached to the current phase of the Chancellor's calendar."""
    s = st.session_state
    _, used = _used()
    if s.get("feature_notice") and int(s.get("feature_notice_phase", 0)) == int(s.block):
        st.info(s.feature_notice)

    if s.block == 1:
        period = f"{int(s.get('term', 1))}-{int(s.get('year', 1))}"
        st.markdown("### Autumn Statement & fiscal update")
        st.caption("A mid-year update to the economic outlook and the Government's fiscal direction. It is smaller than the Spring Budget: choose one limited package, publish the update and face its political and market consequences.")
        metrics = st.columns(4, gap="small")
        metrics[0].metric("Growth", f"{float(s.get('growth', 0.0)):+.1f}%")
        metrics[1].metric("Inflation", f"{float(s.get('inflation', 0.0)):.1f}%")
        metrics[2].metric("Fiscal headroom", f"£{float(s.get('headroom', 0.0)):.1f}bn")
        metrics[3].metric("Gilt yield", f"{float(s.get('gilt_yield', 0.0)):.2f}%")
        if "autumn" in used:
            history = list(s.get("autumn_statement_history", []))
            latest = next((row for row in reversed(history) if row.get("period") == period), None)
            st.success("The Autumn Statement has already been delivered this year.")
            if latest:
                st.caption(f"Published: {latest.get('choice', 'Fiscal update')} · {latest.get('summary', '')}")
        else:
            choices = [
                "Publish the updated forecast and hold course",
                "Fund a targeted cost-of-living package",
                "Announce a tighter spending path",
                "Launch a limited growth and investment package",
            ]
            choice = st.radio(
                "Choose the Government's Autumn Statement:",
                choices, key=f"autumn_statement_choice_{period}",
                label_visibility="collapsed",
            )
            summaries = {
                choices[0]: "A forecast-led update steadies the message and gives investors a clearer view, without changing the fiscal stance.",
                choices[1]: "Targeted support helps households facing high bills, but uses some fiscal room.",
                choices[2]: "A tighter spending path improves the near-term fiscal position, but puts pressure on departments and the governing party.",
                choices[3]: "Targeted investment supports demand and productivity, but adds to borrowing in the short term.",
            }
            st.info(summaries[choice])
            st.caption("This is not a full Budget. New tax rates, thresholds and departmental settlements are reserved for the Spring Budget.")
            if st.button("Publish Autumn Statement", key=f"publish_autumn_statement_{period}",
                         type="primary", use_container_width=True, disabled=s.political_capital_points < 1):
                def autumn_effect(x):
                    if choice == choices[0]:
                        x.market_conf = _clip(x.market_conf + 2.0)
                        x.media_opinion = _clip(x.media_opinion + 1.0)
                        x.pm_opinion = _clip(x.pm_opinion + 1.0)
                    elif choice == choices[1]:
                        x.headroom = round(float(x.headroom) - 1.2, 1)
                        x.deficit = round(float(x.deficit) + 1.2, 1)
                        x.approval = _clip(x.approval + 1.8)
                        x.household_bill_pressure = _clip(float(x.get("household_bill_pressure", 50.0)) - 2.5)
                        x.market_conf = _clip(x.market_conf - 0.5)
                    elif choice == choices[2]:
                        x.headroom = round(float(x.headroom) + 1.5, 1)
                        x.deficit = round(max(0.0, float(x.deficit) - 1.5), 1)
                        x.market_conf = _clip(x.market_conf + 1.0)
                        x.approval = _clip(x.approval - 1.0)
                        x.party_opinion = _clip(x.party_opinion - 1.0)
                    else:
                        x.headroom = round(float(x.headroom) - 1.8, 1)
                        x.deficit = round(float(x.deficit) + 1.8, 1)
                        x.growth = round(float(x.growth) + 0.18, 2)
                        x.market_conf = _clip(x.market_conf - 1.0)
                        x.approval = _clip(x.approval + 0.5)
                    x.autumn_statement_history = list(x.get("autumn_statement_history", []))
                    x.autumn_statement_history.append({
                        "period": period, "choice": choice, "summary": summaries[choice],
                        "headroom_after": round(float(x.headroom), 1),
                        "market_conf_after": round(float(x.market_conf), 1),
                    })
                    x.autumn_statement_history = x.autumn_statement_history[-12:]
                _act("autumn", 1, "Autumn Statement", autumn_effect)
                st.rerun()

    elif s.block == 2:
        st.markdown("### Emergency fiscal watch")
        st.caption("An Emergency Budget is not a routine annual mini-budget. It is called only when serious market, recession, fiscal-rule or government-confidence conditions require a full revised package.")
        market = float(s.get("market_conf", 50.0))
        gilt = float(s.get("gilt_yield", 4.5))
        headroom = float(s.get("headroom", 0.0))
        growth = float(s.get("growth", 0.0))
        severe = (market <= 27 and gilt >= 6.25) or (growth <= -2.5 and market <= 40) or (headroom <= -18 and market <= 32)
        if s.get("active_emergency_budget"):
            st.error("An Emergency Budget has been called. It will appear as a separate event before normal business continues.")
        elif severe:
            st.warning("The fiscal position is approaching emergency territory. The Treasury is monitoring the next market and economic update.")
        else:
            st.info("No Emergency Budget is currently required. The Chancellor can continue with the Government's normal programme.")

def render():
    s = st.session_state
    # Backward-compatible defaults for games saved before this feature existed.
    s.setdefault("political_capital_points", 5)
    s.setdefault("longrun_productivity", 1.0)
    s.setdefault("pension_pressure", 0.0)
    s.setdefault("demographic_pressure", 0.0)
    s.setdefault("threshold_freeze_years", 0)
    s.setdefault("thresholds_frozen", False)
    s.setdefault("personal_allowance", 12570.0)
    s.setdefault("higher_rate_threshold", 50270.0)
    s.setdefault("additional_rate_threshold", 125140.0)
    s.setdefault("threshold_freeze_scope", "Personal allowance and all bands")
    s.setdefault("gilt_maturity_years", 10)
    s.setdefault("index_linked_share", 25)
    s.setdefault("pay_settlement", "unsettled")
    st.markdown("### Fiscal calendar & institutions")
    st.caption("Choose when to spend political capital. Each action can be taken once per year; the same limited pool covers statements, the Bank, pay talks and constitutional bargaining.")
    st.markdown("<div class='fiscal-section-gap'></div>", unsafe_allow_html=True)
    if s.get("feature_notice") and int(s.get("feature_notice_phase", 0)) == int(s.block):
        st.info(s.feature_notice)
    m1, m2, m3, m4 = st.columns(4, gap="small")
    m1.metric("Political capital", f"{s.political_capital_points}/5", help="Points available for this year’s political interventions.")
    m2.metric("Productivity trend", f"{s.longrun_productivity:.2f} index", help="A long-run driver of growth. Skills, research and infrastructure spending can improve it.")
    m3.metric("Ageing pressure", f"{s.demographic_pressure:.1f} index", help="Rises each year to represent an older population and greater demand for retirement-related spending.")
    m4.metric("Pension pressure", f"{s.pension_pressure:.2f} index", help="A cumulative pressure on the public finances from demographic ageing and pension uprating decisions.")
    t1, t2, t3, t4 = st.tabs(["Statements", "Bank & gilts", "Pay & tax", "Devolution"])
    with t1:
        st.markdown("**Spring Statement**")
        st.write("Before delivering the Budget, publish an updated view of the economy and reassure markets. This is a forecast statement, not the full tax-and-spending package.")
        st.caption("If announced: +3 market confidence and +1 point public approval. Costs 1 political capital.")
        _, used = _used()
        if s.block != 3:
            st.info("Available in Phase 3 · Spring Budget. You can still use Bank, pay or devolution actions during the current phase.")
        elif "spring_statement" in used:
            st.success("Spring Statement already delivered this year.")
        elif st.button("Deliver Spring Statement", key="feat_spring_statement", use_container_width=True, disabled=s.political_capital_points < 1):
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
            ("Spring Statement", "spring_statement", "Phase 3 · before the Spring Budget"),
        ]
        for label, key, timing in statuses:
            st.markdown(f"{'✅' if key in used else '◯'} **{label}** — {timing}")
        emergency_period = f"{int(s.get('term', 1))}-{int(s.get('year', 1))}"
        emergency_done = any(row.get("period") == emergency_period for row in s.get("emergency_budget_history", []))
        st.markdown(f"{'✅' if emergency_done else '◯'} **Emergency Budget** — only when triggered by severe conditions")
        st.caption("Statements are optional. Political capital spent here cannot be used for Bank interventions, pay talks or regional bargaining.")

    with t2:
        st.markdown("**What this tab is for**")
        st.caption("A gilt is a UK government bond — essentially an IOU issued by the Treasury. Selling gilts raises money to fund borrowing or replace debt that is coming due. This is a simplified game model, not a full Debt Management Office forecast.")

        with st.expander("🏦 Bank of England choices", expanded=False):
            st.caption("The Bank sets interest rates independently. These are political choices about pressure or public support, with simplified effects on growth, inflation and investor confidence.")
            c1, c2, c3 = st.columns(3, gap="small")
            _, used = _used()
            with c1:
                st.markdown("**Quantitative easing (QE)**")
                st.caption("Cost: 2 political capital")
                if st.button("Coordinate QE", key="feat_qe", use_container_width=True,
                             disabled=("qe" in used or s.political_capital_points < 2),
                             help="Gilt yield −0.30 points; market confidence +2; inflation +0.20 points; debt ratio +0.3 points."):
                    def qe(x):
                        x.gilt_yield = round(max(.1, x.gilt_yield - .3), 2)
                        x.market_conf = _clip(x.market_conf + 2)
                        x.inflation = round(x.inflation + .2, 2)
                        x.debt = round(x.debt + .3, 2)
                    _act("qe", 2, "Quantitative easing coordination", qe)
                    st.rerun()
            with c2:
                st.markdown("**Pressure for lower rates**")
                st.caption("Cost: 2 political capital")
                if st.button("Pressure the Bank", key="feat_rate", use_container_width=True,
                             disabled=("rate_pressure" in used or s.political_capital_points < 2),
                             help="Growth +0.15 points; Bank Rate −0.25 points; market confidence −3; PM confidence −2."):
                    def rates(x):
                        x.interest_rate = round(max(.1, x.interest_rate - .25), 2)
                        x.growth = round(x.growth + .15, 2)
                        x.market_conf = _clip(x.market_conf - 3)
                        x.pm_opinion = _clip(x.pm_opinion - 2)
                    _act("rate_pressure", 2, "Rate-pressure intervention", rates)
                    st.rerun()
            with c3:
                st.markdown("**Defend Bank independence**")
                st.caption("Cost: 1 political capital")
                if st.button("Defend independence", key="feat_independence", use_container_width=True,
                             disabled=("bank_independence" in used or s.political_capital_points < 1),
                             help="Market confidence +4 and gilt yield −0.10 points."):
                    def defend(x):
                        x.market_conf = _clip(x.market_conf + 4)
                        x.gilt_yield = round(max(.1, x.gilt_yield - .1), 2)
                    _act("bank_independence", 1, "Public defence of Bank independence", defend)
                    st.rerun()

        with st.expander("📉 Gilt auction — choose how the government borrows", expanded=True):
            st.write("**Maturity** means how long until the bond is repaid. A 2-year gilt needs refinancing sooner; a 30-year gilt locks in borrowing for much longer. **Index-linked gilts** adjust payments with inflation, so they can become more expensive when prices rise.")
            st.caption("Choose the proposed mix, then hold one auction per year. Only clicking the auction button applies the modelled effects.")
            s.gilt_maturity_years = st.select_slider(
                "Term of the new government borrowing",
                options=[2, 5, 10, 20, 30],
                value=int(s.gilt_maturity_years),
                help="Years until the bond matures and must be repaid or refinanced."
            )
            s.index_linked_share = st.slider(
                "Share of this issuance linked to inflation",
                0, 100, int(s.index_linked_share), 5,
                help="Percentage of this new bond issuance whose payments rise with inflation."
            )
            if int(s.gilt_maturity_years) <= 5:
                st.info("Short-dated choice: in this model, the auction raises the gilt yield by 0.12 percentage points and the debt ratio by 0.1 points.")
            else:
                debt_add = 0.2 if int(s.gilt_maturity_years) >= 20 else 0.1
                st.info(f"Longer-dated choice: in this model, the auction lowers the gilt yield by 0.04 percentage points and the debt ratio rises by {debt_add:.1f} points.")
            if int(s.index_linked_share) > 40:
                st.warning("Because more than 40% is index-linked, this model deducts £0.6bn from fiscal headroom.")
            else:
                st.caption("At 40% index-linked or less, this model applies no extra headroom penalty.")
            _, used = _used()
            if st.button("Issue gilts in auction", key="feat_auction", use_container_width=True,
                         disabled=("gilt_auction" in used or s.political_capital_points < 1),
                         help="Costs 1 political capital. Applies the maturity and index-linked effects described above."):
                def auction(x):
                    maturity = int(x.gilt_maturity_years)
                    x.debt = round(x.debt + (0.2 if maturity >= 20 else 0.1), 2)
                    if maturity <= 5:
                        x.gilt_yield = round(x.gilt_yield + .12, 2)
                    else:
                        x.gilt_yield = round(max(.1, x.gilt_yield - .04), 2)
                    if int(x.index_linked_share) > 40:
                        x.headroom = round(x.headroom - .6, 1)
                    x.message = f"Gilt auction: {maturity}-year issuance; {x.index_linked_share}% index-linked."
                _act("gilt_auction", 1, "Gilt auction", auction)
                st.rerun()
            st.caption("Important limitation: the prototype does not yet model a full schedule of maturing debt, coupon payments or refinancing by year; the auction affects only the listed headline indicators.")
    with t3:
        st.markdown("**Public-sector pay round**")
        pay = st.radio("Negotiating position", ["Inflation-matching settlement", "Targeted compromise", "Pay cap and arbitration"], key="feature_pay_choice", horizontal=False, help="An inflation-matching deal costs more but improves morale; a pay cap saves money but increases strike and morale risks.")
        if st.button("Conclude annual pay round", key="feat_pay", use_container_width=True, disabled=("pay_round" in _used()[1] or s.political_capital_points < 2)):
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
        st.markdown("**Current tax thresholds · Budget-controlled**")
        st.caption(
            f"Personal allowance £{float(s.get('personal_allowance', 12570)):,.0f} · "
            f"Higher-rate threshold £{float(s.get('higher_rate_threshold', 50270)):,.0f} · "
            f"Additional-rate threshold £{float(s.get('additional_rate_threshold', 125140)):,.0f}"
        )
        st.caption(
            f"Inheritance tax nil-rate band £{float(s.get('inheritance_nil_rate_band', 325000)):,.0f} · "
            f"VAT registration threshold £{float(s.get('vat_registration_threshold', 90000)):,.0f} · "
            + ("Income-tax thresholds currently frozen." if s.get('thresholds_frozen', False) else "Income-tax thresholds currently uprate annually.")
        )
        st.caption("These figures are read-only here. Propose changes in the Budget's Tax & revenue section; they take effect only when the Budget is delivered.")
        st.markdown("**State pension & retirement age**")
        s.setdefault("retirement_age", 66)
        s.setdefault("retirement_age_annual_saving", 0.0)
        s.setdefault("state_pension_weekly", 230.25)
        s.setdefault("state_pension_uprating", "Triple lock")
        with st.expander("State pension & retirement age", expanded=True):
            retirement_age = st.slider("State pension age (years)", 60, 75, int(s.retirement_age), 1, key="draft_retirement_age", help="Raising the pension age reduces the number of people eligible at a given time, but is politically difficult and can disadvantage people in physically demanding work.")
            pension_weekly = st.number_input("Full new State Pension (£ per week)", min_value=100.0, max_value=400.0, value=float(s.state_pension_weekly), step=1.0, key="draft_state_pension_weekly")
            uprating = st.selectbox("Annual State Pension uprating rule", ["Triple lock", "Earnings growth", "CPI inflation", "Freeze"], index=["Triple lock", "Earnings growth", "CPI inflation", "Freeze"].index(s.state_pension_uprating) if s.state_pension_uprating in ["Triple lock", "Earnings growth", "CPI inflation", "Freeze"] else 0, key="draft_pension_uprating")
            st.caption("The triple lock uses the highest of earnings growth, CPI inflation or 2.5%. Tax threshold changes are now proposed and approved through the annual Budget.")
        productivity_plan = st.checkbox("Fund skills, research and infrastructure for productivity", key="feature_productivity_plan", help="Costs £0.5bn of headroom now and improves the long-run productivity trend.")
        if st.button("Enact pension, retirement & productivity package", key="feat_tax_pension", use_container_width=True,
                      disabled=("tax_pension" in _used()[1] or s.political_capital_points < 1)):
            def pension_fx(x):
                old_age = int(x.retirement_age)
                old_age_saving = float(x.retirement_age_annual_saving)
                old_weekly = float(x.state_pension_weekly)
                new_age_saving = (retirement_age - 66) * 5.0
                pension_cost = (pension_weekly - old_weekly) * 0.6
                x.headroom = round(x.headroom + (new_age_saving - old_age_saving) - pension_cost, 1)
                x.deficit = round(x.deficit - (new_age_saving - old_age_saving) + pension_cost, 1)
                x.retirement_age = int(retirement_age)
                x.retirement_age_annual_saving = float(new_age_saving)
                x.state_pension_weekly = float(pension_weekly)
                x.state_pension_uprating = uprating
                if uprating == "Triple lock":
                    x.pension_pressure = round(x.pension_pressure + .5, 1)
                if retirement_age > old_age:
                    x.approval = _clip(x.approval - 2.5)
                    x.party_opinion = _clip(x.party_opinion - 2)
                    x.message += " Raising the State Pension age provokes a backlash from unions and older voters."
                elif retirement_age < old_age:
                    x.approval = _clip(x.approval + 1.5)
                if pension_weekly > old_weekly:
                    x.approval = _clip(x.approval + 1.5)
                elif pension_weekly < old_weekly:
                    x.approval = _clip(x.approval - 3)
                    x.party_opinion = _clip(x.party_opinion - 2)
                if productivity_plan:
                    x.longrun_productivity = round(x.longrun_productivity + .15, 2)
                    x.headroom = round(x.headroom - .5, 1)
            _act("tax_pension", 1, "State pension, retirement and productivity package", pension_fx); st.rerun()
        st.caption(f"State Pension: £{s.state_pension_weekly:.2f} weekly; pension age {s.retirement_age}.")
    with st.expander("📖 Glossary: what these controls mean", expanded=False):
        st.markdown("**Political capital** is a limited annual resource for interventions; spend it on the most important priorities. **Market confidence** is a simplified investor sentiment score, not a direct market price.")
        st.markdown("**Quantitative easing (QE)** means a central bank buys assets to loosen financial conditions; it can support demand but may add inflation risk. **Gilts** are UK government bonds. Maturity is how long until they must be repaid; index-linked gilts rise with inflation.")
        st.markdown("**Fiscal drag** occurs when tax thresholds stay frozen while earnings rise, bringing more income into tax or higher bands. **Triple lock** means the state pension rises by the highest of earnings growth, inflation or 2.5%; this game uses an abstract pension-pressure index.")
        st.markdown("**Productivity** is output per hour worked. **Ageing pressure** rises over time as the population gets older; **pension pressure** accumulates the resulting spending burden and the effect of pension uprating. **Block-grant bargaining** models negotiations between Westminster and devolved governments.")
        st.markdown("**Leadership challenge** is a simplified political gamble: success depends on party and Cabinet support; failure risks your job. These are game abstractions, not real economic forecasts.")
    with t4:
        if s.party in ("SNP", "Plaid Cymru"):
            st.markdown("**Devolution negotiation**")
            st.write("Negotiate a larger block grant using a Barnett-formula settlement, or accept a fiscal package from Westminster.")
            deal = st.radio("Negotiating stance", ["Demand a larger block grant", "Accept a compromise", "Reject Westminster's offer"], key="feature_devolution")
            if st.button("Negotiate block grant", key="feat_devolution", use_container_width=True, disabled=("devolution" in _used()[1] or s.political_capital_points < 2)):
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
                     disabled=("leadership_challenge" in _used()[1] or s.get("pm_opinion", 100) > 45 or s.get("political_capital_points", 5) < 3)):
            def challenge(x):
                if x.party_opinion >= 50 and x.cab_opinion >= 45:
                    x.pm_opinion = _clip(x.pm_opinion + 20)
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
