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
        action_key = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
        used_actions = s.get("feature_actions", {}).get(action_key, [])
        s["autumn_statement_due"] = "autumn" not in used_actions
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
    if s.get("spending_review_due"):
        st.info("A Spending Review is due. It will appear in Decisions before the next policy submission.")
    if s.get("active_emergency_budget"):
        st.error("An Emergency Budget has been called and is awaiting delivery.")

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

    autumn = list(s.get("autumn_statement_history", []))
    emergency = list(s.get("emergency_budget_history", []))
    with st.expander("Statement and emergency-event history", expanded=False):
        if autumn:
            st.markdown("**Autumn Statements**")
            st.dataframe(list(reversed(autumn[-5:])), hide_index=True, use_container_width=True)
        else:
            st.caption("No Autumn Statement has been delivered yet.")
        if emergency:
            st.markdown("**Emergency Budgets**")
            st.dataframe(list(reversed(emergency[-5:])), hide_index=True, use_container_width=True)
        else:
            st.caption("No Emergency Budget has been required.")
