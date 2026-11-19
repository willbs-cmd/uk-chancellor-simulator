"""Fiscal calendar and major Treasury events for the Chancellor Simulator.

The Budget is the annual tax-and-spending package. Spending Reviews set multi-year
departmental baselines. Autumn Statements update the fiscal position. Emergency
Budgets are only opened when serious economic or market conditions justify them.
"""
import streamlit as st

REVIEW_INTERVAL = 2
MAJORITY_TRIGGER_HEADROOM = -18.0


def period_key(s=None):
    s = s or st.session_state
    return f"{int(s.get('term', 1))}-{int(s.get('year', 1))}"


def ensure_state(s=None):
    """Add the fiscal calendar fields to both new games and older save files."""
    s = s or st.session_state
    s.setdefault("spending_review_history", [])
    s.setdefault("spending_review_last_period", "")
    s.setdefault("spending_review_plan", {})
    s.setdefault("spending_review_due", False)
    s.setdefault("autumn_statement_history", [])
    s.setdefault("emergency_budget_history", [])
    s.setdefault("emergency_budget_last_period", "")
    s.setdefault("active_emergency_budget", None)
    s.setdefault("budget_day_type", "annual")
    if s.get("autumn_statement_due") is None:
        year = int(s.get("year", 1))
        action_key = f"{int(s.get('term', 1))}:{year}"
        used_actions = s.get("feature_actions", {}).get(action_key, [])
        s["autumn_statement_due"] = year <= 5 and "autumn" not in used_actions
    s.setdefault("budget_day_draft", None)
    s.setdefault("emergency_replaces_spring_budget", False)
    s.setdefault("fiscal_calendar_initialised", False)
    # Older saves have no explicit calendar flag. Only schedule a review at the
    # start of a review year, and never repeat one already completed in that year.
    if not bool(s.get("fiscal_calendar_initialised", False)):
        year = int(s.get("year", 1))
        due = (year - 1) % REVIEW_INTERVAL == 0 and s.get("spending_review_last_period") != period_key(s)
        s["spending_review_due"] = bool(s.get("spending_review_due", False) or due)
        s["fiscal_calendar_initialised"] = True


def schedule_spending_review(s=None, force=False):
    """Schedule a multi-year departmental review at the start of years 1, 3 and 5."""
    s = s or st.session_state
    ensure_state(s)
    current = period_key(s)
    due_year = (int(s.get("year", 1)) - 1) % REVIEW_INTERVAL == 0
    if force or (due_year and s.get("spending_review_last_period") != current):
        s.spending_review_due = True
        return True
    return False


def open_emergency_budget(reason, source="automatic"):
    """Open the full Budget Day workflow without advancing the Spring calendar."""
    s = st.session_state
    ensure_state(s)
    if s.get("active_emergency_budget"):
        return False
    current = period_key(s)
    if s.get("emergency_budget_last_period") == current:
        return False
    s.active_emergency_budget = {
        "period": current,
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "reason": str(reason),
        "source": str(source),
    }
    # If this is called after the second decision of the year, the emergency
    # package replaces the scheduled Spring Budget rather than causing two Budgets.
    s.emergency_replaces_spring_budget = int(s.get("block", 1)) >= 2
    s.budget_day_type = "emergency"
    s.budget_day_stage = 0
    s.budget_day_draft = None
    s.budget_day_forecast = []
    s.budget_day_speech = None
    s.budget_day_negotiation = ""
    s.budget_pm_priorities = []
    s.budget_pm_assessment = []
    s.budget_passed = False
    s.message = f"Emergency Budget required: {reason}"
    return True


def maybe_trigger_emergency_budget(s=None):
    """Trigger at most one Emergency Budget per in-game year, and only under severe stress."""
    s = s or st.session_state
    ensure_state(s)
    if s.get("active_emergency_budget") or s.get("budget_passed") or s.get("game_over"):
        return False
    if int(s.get("year", 1)) > 5:
        # The term is over; the general-election campaign takes precedence over
        # fiscal events until a new term begins.
        return False
    if int(s.get("block", 1)) >= 3:
        # The scheduled Spring Budget is already the government's full fiscal event.
        return False
    if s.get("emergency_budget_last_period") == period_key(s):
        return False

    market = float(s.get("market_conf", 50.0))
    gilt = float(s.get("gilt_yield", 4.5))
    growth = float(s.get("growth", 0.0))
    headroom = float(s.get("headroom", 0.0))
    stability = float(s.get("financial_stability", 80.0))
    deficit = float(s.get("deficit", 0.0))
    gdp_bn = max(1.0, float(s.get("gdp_trillion", 3.0)) * 1000.0)
    reasons = []

    if market <= 27 and gilt >= 6.25:
        reasons.append("Gilt markets are under severe pressure and government borrowing costs have surged.")
    if growth <= -2.5 and market <= 40:
        reasons.append("The economy has entered a deep recession while investor confidence is weak.")
    if headroom <= MAJORITY_TRIGGER_HEADROOM and market <= 32 and deficit / gdp_bn >= 0.055:
        reasons.append("The fiscal rules have been badly breached and markets are questioning the Government's borrowing plan.")
    if stability <= 24 and s.get("active_financial_crisis"):
        reasons.append("A severe financial-stability crisis requires an immediate revised fiscal package.")
    if (float(s.get("pm_opinion", 50.0)) <= 22 and float(s.get("party_opinion", 50.0)) <= 22
            and headroom < 0):
        reasons.append("A major confidence crisis has left the Government needing an urgent fiscal reset.")

    if not reasons:
        return False
    reason = reasons[0]
    return open_emergency_budget(reason, source="automatic crisis trigger")


def close_emergency_budget():
    """Close the post-vote results screen and record the emergency event."""
    s = st.session_state
    emergency = s.get("active_emergency_budget")
    if not emergency:
        return
    s.emergency_budget_history = list(s.get("emergency_budget_history", []))
    s.emergency_budget_history.append({
        **emergency,
        "ayes": int(s.get("vote_ayes", 0)),
        "headroom_after": round(float(s.get("headroom", 0.0)), 1),
        "gilt_yield_after": round(float(s.get("gilt_yield", 0.0)), 2),
    })
    s.emergency_budget_history = s.emergency_budget_history[-12:]
    s.emergency_budget_last_period = emergency.get("period", period_key(s))
    s.active_emergency_budget = None
    advance_to_spring = bool(s.get("emergency_replaces_spring_budget", False))
    s.emergency_replaces_spring_budget = False
    s.budget_day_type = "annual"
    s.budget_day_stage = 0
    s.budget_day_draft = None
    s.budget_day_forecast = []
    s.budget_day_speech = None
    s.budget_day_negotiation = ""
    s.budget_passed = False
    s.message = "The Emergency Budget has been delivered. The Government returns to its normal programme."
    return advance_to_spring


def release_contingency_reserve(amount, purpose="Emergency intervention"):
    """Release previously ring-fenced funds to meet an authorised emergency cost.

    This restores the reserve allocation to fiscal headroom; it does not create
    new resources or change the departmental spending settlement.
    """
    s = st.session_state
    ensure_state(s)
    balance = max(0.0, float(s.get("budget_contingency_reserve", 0.0)))
    requested = max(0.0, float(amount))
    released = round(min(balance, requested), 1)
    if released <= 0:
        return 0.0
    s.budget_contingency_reserve = round(balance - released, 1)
    s.headroom = round(float(s.get("headroom", 0.0)) + released, 1)
    history = list(s.get("budget_reserve_history", []))
    history.append({"term": int(s.get("term", 1)), "year": int(s.get("year", 1)),
                    "change": -released, "balance": s.budget_contingency_reserve,
                    "purpose": str(purpose)[:100]})
    s.budget_reserve_history = history[-30:]
    s.message = f"£{released:.1f}bn released from the contingency reserve for {purpose.lower()}."
    return released



def fiscal_calendar_snapshot(s=None):
    """Return a read-only five-year fiscal calendar and multi-year settlement summary."""
    s = s or st.session_state
    ensure_state(s)
    term = int(s.get("term", 1))
    current_year = int(s.get("year", 1))
    autumn = {str(row.get("period", "")) for row in s.get("autumn_statement_history", [])}
    reviews = {str(row.get("period", "")) for row in s.get("spending_review_history", [])}
    budgets = {
        f"{int(row.get('term', 1))}-{int(row.get('year', 1))}": row
        for row in s.get("budget_history", [])
        if str(row.get("event_type", "Spring Budget")).lower() not in ("emergency budget", "emergency")
    }
    emergency_count = len(s.get("emergency_budget_history", []))
    rows = []
    for year in range(1, 6):
        period = f"{term}-{year}"
        is_current = year == current_year
        autumn_status = ("Delivered" if period in autumn else
                         "Due now" if is_current and s.get("autumn_statement_due") else
                         "Scheduled" if year >= current_year else "No record")
        budget_status = ("Passed" if period in budgets else
                         "Passed" if is_current and s.get("budget_passed") else
                         "Due now" if is_current and int(s.get("block", 1)) >= 3 else
                         "Scheduled" if year >= current_year else "No record")
        review_due_year = (year - 1) % REVIEW_INTERVAL == 0
        if review_due_year:
            review_status = ("Approved" if period in reviews else
                             "Due now" if is_current and s.get("spending_review_due") else
                             "Scheduled" if year >= current_year else "Not held")
        else:
            review_status = "Not scheduled"
        rows.append({
            "Government year": year,
            "Autumn Statement": autumn_status,
            "Spring Budget": budget_status,
            "Spending Review": review_status,
        })
    plan = s.get("spending_review_plan") or {}
    allocations = plan.get("allocations", {}) if isinstance(plan, dict) else {}
    baseline = sum(float(value) for value in allocations.values()) if allocations else sum(
        float(value) for value in s.get("dept_spend", {}).values()
    )
    year2 = float(plan.get("year2_uplift", 0.0)) if plan else 0.0
    year3 = float(plan.get("year3_uplift", 0.0)) if plan else 0.0
    has_plan = bool(allocations)
    return {
        "calendar": rows,
        "emergency_budgets": emergency_count,
        "spending_plan": {
            "approved": has_plan,
            "year1": round(baseline, 1),
            "year2": round(baseline * (1 + year2 / 100.0), 1),
            "year3": round(baseline * (1 + year2 / 100.0) * (1 + year3 / 100.0), 1),
            "year2_uplift": year2,
            "year3_uplift": year3,
            "approved_year": int(plan.get("approved_year", 0)) if plan else 0,
        },
        "next_review_year": next((year for year in range(current_year, 6)
                                  if (year - 1) % REVIEW_INTERVAL == 0 and f"{term}-{year}" not in reviews), None),
    }


def render_fiscal_events_centre():
    """Central command view for the fiscal calendar, Spending Review and past events."""
    s = st.session_state
    snapshot = fiscal_calendar_snapshot(s)
    render_treasury_overview()
    st.markdown("### Five-year fiscal programme")
    st.caption("A single view of the Government's annual fiscal statements, formal Budgets and multi-year spending settlements.")
    rows = snapshot["calendar"]
    st.dataframe(rows, hide_index=True, use_container_width=True)
    due_items = []
    if s.get("active_emergency_budget"):
        due_items.append("Emergency Budget")
    if s.get("spending_review_due"):
        due_items.append("Spending Review")
    if s.get("autumn_statement_due"):
        due_items.append("Autumn Statement")
    if int(s.get("block", 1)) >= 3 and not s.get("budget_passed"):
        due_items.append("Spring Budget")
    if due_items:
        st.warning("Awaiting action: " + " · ".join(due_items) + ". Open the current fiscal event from the Budget workspace.")
    else:
        st.caption("No formal fiscal event is currently awaiting approval. The next event will open automatically when the in-game calendar reaches it.")
    plan = snapshot["spending_plan"]
    st.markdown("### Multi-year spending settlement")
    if plan["approved"]:
        cols = st.columns(3, gap="medium")
        cols[0].metric(f"Year {plan['approved_year']} approved baseline", f"£{plan['year1']:,.1f}bn")
        cols[1].metric("Following year", f"£{plan['year2']:,.1f}bn", f"{plan['year2_uplift']:+.1f}%")
        cols[2].metric("Third year", f"£{plan['year3']:,.1f}bn", f"{plan['year3_uplift']:+.1f}%")
        st.caption("The approved departmental cash path is applied once at each annual Spring transition. It does not overwrite the Budget's approved tax rates or departmental percentage settings.")
    else:
        st.info("No multi-year Spending Review settlement has been approved in this term. The first review is scheduled for Government Year 1.")
    st.markdown("### Fiscal event record")
    records = []
    for row in s.get("budget_history", [])[-8:]:
        records.append({
            "Period": f"Year {row.get('year', '?')}",
            "Event": row.get("event_type", "Spring Budget"),
            "Commons Ayes": int(row.get("ayes", 0)),
            "Headroom after": f"£{float(row.get('headroom_after', 0.0)):.1f}bn",
            "Outcome": "Delivered",
        })
    for row in s.get("autumn_statement_history", [])[-8:]:
        records.append({
            "Period": row.get("period", ""),
            "Event": "Autumn Statement",
            "Commons Ayes": "—",
            "Headroom after": f"£{float(row.get('headroom_after', 0.0)):.1f}bn",
            "Outcome": str(row.get("choice", "Published")),
        })
    for row in s.get("emergency_budget_history", [])[-8:]:
        records.append({
            "Period": row.get("period", ""),
            "Event": "Emergency Budget",
            "Commons Ayes": int(row.get("ayes", 0)),
            "Headroom after": f"£{float(row.get('headroom_after', 0.0)):.1f}bn",
            "Outcome": str(row.get("reason", "Delivered")),
        })
    if records:
        st.dataframe(list(reversed(records[-15:])), hide_index=True, use_container_width=True)
    else:
        st.caption("Formal fiscal decisions will be recorded here as your Government progresses.")


def render_treasury_overview():
    """Read-only Treasury dashboard; major fiscal events are launched from the game calendar."""
    s = st.session_state
    ensure_state(s)
    period = period_key(s)
    current_year = int(s.get("year", 1))
    next_review_year = current_year
    if (current_year - 1) % REVIEW_INTERVAL == 0 and s.get("spending_review_last_period") == period:
        next_review_year += 1
    while next_review_year <= 5 and (next_review_year - 1) % REVIEW_INTERVAL != 0:
        next_review_year += 1
    if s.get("spending_review_due"):
        next_review = "Due now"
    elif next_review_year > 5:
        next_review = "Next term · Year 1"
    else:
        next_review = f"Term {s.get('term', 1)} · Year {next_review_year}"

    st.markdown("### Treasury position")
    st.caption("A live view of the public finances and the fiscal events that shape the Government's economic programme.")
    cols = st.columns(4)
    cols[0].metric("Fiscal headroom", f"£{float(s.get('headroom', 0.0)):.1f}bn")
    cols[1].metric("Annual deficit", f"£{float(s.get('deficit', 0.0)):.1f}bn")
    cols[2].metric("10-year gilt yield", f"{float(s.get('gilt_yield', 0.0)):.2f}%")
    cols[3].metric("Next Spending Review", next_review)

    st.markdown("#### Fiscal calendar")
    calendar = [
        {"Event": "Autumn Statement", "Timing": "Every year · opening event before policy decisions", "Purpose": "Update forecasts and announce limited fiscal measures"},
        {"Event": "Spring Budget", "Timing": "Every year · Phase 3", "Purpose": "Set taxes, thresholds, spending measures and policy programmes; Commons vote"},
        {"Event": "Spending Review", "Timing": "Every two years · starts in Years 1, 3 and 5", "Purpose": "Set departmental baselines and a multi-year spending path"},
        {"Event": "Emergency Budget", "Timing": "Only after severe economic, market or government-confidence stress", "Purpose": "A full revised package, rapid forecast, speech and Commons vote"},
    ]
    st.dataframe(calendar, hide_index=True, use_container_width=True)
    # Current agenda: make the next actionable event obvious without opening Decisions.
    if s.get("active_emergency_budget"):
        emergency = s.get("active_emergency_budget") or {}
        st.error(f"**Emergency Budget awaiting delivery.** {emergency.get('reason', 'A severe fiscal event has been called.')}")
        reserve_balance = max(0.0, float(s.get("budget_contingency_reserve", 0.0)))
        if reserve_balance > 0:
            st.markdown("##### Emergency funding from the contingency reserve")
            st.caption("Release money previously ring-fenced in the Budget to help fund this intervention. Released funds return to fiscal headroom and reduce the reserve balance pound-for-pound.")
            st.metric("Available reserve", f"£{reserve_balance:.1f}bn")
            release = st.slider("Release for this emergency (£bn)", 0.0, float(reserve_balance),
                                min(0.0, float(reserve_balance)), step=0.5,
                                key="emergency_reserve_release_amount")
            if st.button("Release reserve into emergency funding", key="release_emergency_contingency"):
                released = release_contingency_reserve(release, "Emergency Budget")
                if released > 0:
                    st.success(f"£{released:.1f}bn released. The reserve is now £{float(s.get('budget_contingency_reserve', 0.0)):.1f}bn.")
                    st.rerun()
    elif s.get("spending_review_due"):
        st.warning("**Spending Review due now.** Agree departmental cash baselines and the local-government settlement before normal policy decisions.")
    elif s.get("autumn_statement_due"):
        st.info("**Autumn Statement due now.** Publish a limited fiscal update or proceed without one before the first policy decision.")
    elif int(s.get("block", 1)) == 3 and not s.get("budget_passed"):
        st.warning("**Spring Budget due.** Finalise the tax-and-spending package and take it to the Commons.")
    elif s.get("budget_passed"):
        st.success("The Budget has passed. Proceed to the Spring update to apply the annual economic and fiscal effects.")
    elif int(s.get("year", 1)) <= 5:
        st.caption("No major fiscal event is awaiting action. Monitor borrowing, fiscal headroom and market conditions while completing the current policy phase.")

    st.markdown("#### Recent fiscal decisions")
    budget_rows = list(s.get("budget_history", []))[-5:]
    if budget_rows:
        st.dataframe([
            {"Period": row.get("label", f"Term {row.get('term', 1)} · Year {row.get('year', 1)}"),
             "Type": row.get("event_type", "Spring Budget"),
             "Ayes": row.get("ayes", 0),
             "Headroom after": f"£{float(row.get('headroom_after', 0.0)):.1f}bn"}
            for row in reversed(budget_rows)
        ], hide_index=True, use_container_width=True)
    else:
        st.caption("Your delivered Budgets will be recorded here.")

    reviews = list(s.get("spending_review_history", []))
    if reviews:
        st.markdown("#### Recent Spending Reviews")
        st.dataframe([
            {"Period": row.get("period", ""), "Departmental total": f"£{float(row.get('departmental_total', 0.0)):.1f}bn",
             "Annual change": f"£{float(row.get('annual_change', 0.0)):+.1f}bn",
             "Local grant uplift": f"£{float(row.get('local_settlement', {}).get('local_grant_uplift_bn', 0.0)):.1f}bn"}
            for row in reversed(reviews[-5:])
        ], hide_index=True, use_container_width=True)

    # Make the approved multi-year settlement visible between formal review rounds.
    plan = s.get("spending_review_plan") or {}
    if isinstance(plan, dict) and plan.get("allocations"):
        approved_term = int(plan.get("term", s.get("term", 1)))
        approved_year = int(plan.get("approved_year", 1))
        year2 = float(plan.get("year2_uplift", 0.0))
        year3 = float(plan.get("year3_uplift", 0.0))
        current_term = int(s.get("term", 1))
        current_year = int(s.get("year", 1))
        last_applied = int(plan.get("last_applied_year", approved_year))
        st.markdown("#### Approved multi-year spending path")
        path_cols = st.columns(3)
        path_cols[0].metric("Year 2 planned uplift", f"{year2:+.1f}%")
        path_cols[1].metric("Year 3 planned uplift", f"{year3:+.1f}%")
        if current_term == approved_term and current_year == approved_year + 1:
            path_status = "Year 2 settlement applied" if last_applied >= current_year else "Year 2 settlement awaiting Spring"
        elif current_term == approved_term and current_year == approved_year + 2:
            path_status = "Year 3 settlement applied" if last_applied >= current_year else "Year 3 settlement awaiting Spring"
        elif current_term == approved_term and current_year == approved_year:
            path_status = "Year 1 baseline approved"
        else:
            path_status = f"Approved in Term {approved_term}, Year {approved_year}"
        path_cols[2].metric("Settlement status", path_status)
        st.caption("These uplifts are applied once to departmental cash baselines at the annual Spring transition. The next Spending Review replaces this plan.")

    autumn = list(s.get("autumn_statement_history", []))
    emergency = list(s.get("emergency_budget_history", []))
    with st.expander("Statement and emergency-event history", expanded=False):
        if autumn:
            st.markdown("**Autumn Statements**")
            st.dataframe([
                {"Period": row.get("period", ""),
                 "Decision": row.get("choice", ""),
                 "Headroom after": f"£{float(row.get('headroom_after', 0.0)):.1f}bn",
                 "Market confidence": f"{float(row.get('market_conf_after', 0.0)):.0f}/100"}
                for row in reversed(autumn[-5:])
            ], hide_index=True, use_container_width=True)
        else:
            st.caption("No Autumn Statement has been delivered or skipped yet.")
        if emergency:
            st.markdown("**Emergency Budgets**")
            st.dataframe([
                {"Period": row.get("period", ""),
                 "Reason": row.get("reason", ""),
                 "Commons Ayes": row.get("ayes", 0),
                 "Headroom after": f"£{float(row.get('headroom_after', 0.0)):.1f}bn",
                 "Gilt yield after": f"{float(row.get('gilt_yield_after', 0.0)):.2f}%"}
                for row in reversed(emergency[-5:])
            ], hide_index=True, use_container_width=True)
        else:
            st.caption("No Emergency Budget has been required.")
