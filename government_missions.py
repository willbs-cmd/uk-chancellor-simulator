"""Five-year government mandates for the UK Chancellor Simulator.

A mandate gives each government a clear, measurable programme for its term.
Progress is calculated from the existing economic, fiscal, household, service
and regional models; it does not replace or overwrite those systems.
"""
from statistics import mean


MISSIONS = {
    "growth_productivity": {
        "title": "High-Wage Growth Economy",
        "strapline": "Lift productivity, create better-paid work and make growth durable.",
        "description": "A pro-growth mandate focused on stronger output, a healthier labour market and narrowing the productivity gap.",
        "objectives": [
            {"metric": "growth", "label": "Raise annual GDP growth", "delta": 1.0, "unit": "pp", "detail": "Improve annual real GDP growth by one percentage point from the start of the term."},
            {"metric": "unemployment", "label": "Bring unemployment down", "delta": -0.5, "unit": "pp", "detail": "Create a stronger labour market and reduce unemployment."},
            {"metric": "regional_productivity", "label": "Raise regional productivity", "delta": 3.0, "unit": "index pts", "detail": "Lift average productivity across the twelve modelled UK regions."},
        ],
    },
    "living_standards": {
        "title": "A Better Deal for Households",
        "strapline": "Improve real pay, purchasing power and the pressure of everyday bills.",
        "description": "A household-focused mandate. Strong headline GDP is not enough unless families feel the improvement in their pay and finances.",
        "objectives": [
            {"metric": "real_wages", "label": "Restore real wage growth", "delta": 1.0, "unit": "pp", "detail": "Improve annual real wage growth by one percentage point."},
            {"metric": "disposable_income", "label": "Lift household purchasing power", "delta": 4.0, "unit": "index pts", "detail": "Raise the disposable-income index above its opening baseline."},
            {"metric": "household_bills", "label": "Ease household bill pressure", "delta": -8.0, "unit": "pts", "detail": "Reduce the modelled pressure created by energy and other household bills."},
        ],
    },
    "public_services": {
        "title": "Rebuild Public Services",
        "strapline": "Reduce waiting lists, support frontline staff and improve education.",
        "description": "A public-service renewal mandate that measures outcomes, not only the amount of money announced.",
        "objectives": [
            {"metric": "nhs_waiting", "label": "Cut the NHS waiting list", "delta": -0.75, "unit": "million", "detail": "Reduce the modelled waiting list by three-quarters of a million."},
            {"metric": "nhs_morale", "label": "Improve NHS staff morale", "delta": 10.0, "unit": "pts", "detail": "Improve the morale index through pay, workforce and delivery decisions."},
            {"metric": "schools", "label": "Raise school standards", "delta": 5.0, "unit": "pts", "detail": "Improve the school standards index over the five-year term."},
        ],
    },
    "fiscal_repair": {
        "title": "Restore Fiscal Credibility",
        "strapline": "Rebuild headroom, reduce borrowing and reassure the gilt market.",
        "description": "A Treasury-first mandate. Spending choices, tax receipts, growth and debt interest all matter to the final result.",
        "objectives": [
            {"metric": "headroom", "label": "Rebuild fiscal headroom", "delta": 5.0, "unit": "£bn", "detail": "Increase the fiscal safety margin by £5bn."},
            {"metric": "deficit", "label": "Reduce the annual deficit", "delta": -10.0, "unit": "£bn", "detail": "Reduce the annual borrowing shortfall by £10bn."},
            {"metric": "market_conf", "label": "Restore market confidence", "delta": 8.0, "unit": "pts", "detail": "Improve investor confidence in the Government's economic management."},
        ],
    },
    "regional_renewal": {
        "title": "A More Balanced Britain",
        "strapline": "Narrow regional divides and spread opportunity across the UK.",
        "description": "A place-based mandate. National averages can hide persistent regional differences, so the mission measures the gap as well as the mean.",
        "objectives": [
            {"metric": "regional_productivity", "label": "Raise regional productivity", "delta": 3.0, "unit": "index pts", "detail": "Raise average productivity across the twelve regions."},
            {"metric": "regional_gap", "label": "Narrow the productivity gap", "delta": -2.0, "unit": "index pts", "detail": "Reduce the distance between the most and least productive regions."},
            {"metric": "regional_unemployment", "label": "Improve regional employment", "delta": -0.4, "unit": "pp", "detail": "Reduce average unemployment across the regions."},
        ],
    },
    "balanced_renewal": {
        "title": "A Balanced National Renewal",
        "strapline": "Improve public support, deliver growth and protect the public finances.",
        "description": "A broad five-year test of government: economic improvement, a stronger public mandate and a safer fiscal position.",
        "objectives": [
            {"metric": "approval", "label": "Strengthen public approval", "delta": 8.0, "unit": "pts", "detail": "Increase public approval by eight points from the opening baseline."},
            {"metric": "growth", "label": "Lift annual GDP growth", "delta": 0.8, "unit": "pp", "detail": "Improve annual real GDP growth by 0.8 percentage points."},
            {"metric": "headroom", "label": "Protect the fiscal buffer", "delta": 3.0, "unit": "£bn", "detail": "Increase the fiscal safety margin rather than relying on a last-minute correction."},
        ],
    },
}


FORMATS = {
    "growth": "{:+.2f}%",
    "unemployment": "{:.1f}%",
    "regional_productivity": "{:.1f}",
    "real_wages": "{:+.1f}%",
    "disposable_income": "{:.1f}",
    "household_bills": "{:.0f}/100",
    "nhs_waiting": "{:.2f}m",
    "nhs_morale": "{:.0f}/100",
    "schools": "{:.0f}/100",
    "headroom": "£{:+.1f}bn",
    "deficit": "£{:.1f}bn",
    "market_conf": "{:.0f}/100",
    "approval": "{:.0f}%",
    "regional_gap": "{:.1f}",
    "regional_unemployment": "{:.1f}%",
}


def metric_values(s):
    """Return a consistent set of live measures from the existing game systems."""
    country = s.get("country", {}) if isinstance(s.get("country", {}), dict) else {}
    regions = s.get("regional_economies", {}) if isinstance(s.get("regional_economies", {}), dict) else {}
    rows = [row for row in regions.values() if isinstance(row, dict)]
    productivity = [float(row.get("productivity", 100.0)) for row in rows]
    unemployment = [float(row.get("unemployment", 4.5)) for row in rows]
    if productivity:
        regional_average = mean(productivity)
        regional_gap = max(productivity) - min(productivity)
        regional_jobless = mean(unemployment) if unemployment else 4.5
    else:
        regional_average, regional_gap, regional_jobless = 100.0, 0.0, 4.5
    return {
        "growth": float(s.get("growth", 0.0)),
        "unemployment": float(country.get("unemployment", 4.3)),
        "regional_productivity": float(regional_average),
        "real_wages": float(country.get("real_wages", 0.0)),
        "disposable_income": float(s.get("disposable_income_index", 100.0)),
        "household_bills": float(s.get("household_bill_pressure", 50.0)),
        "nhs_waiting": float(country.get("nhs_waiting", 7.4)),
        "nhs_morale": float(country.get("nhs_morale", 52.0)),
        "schools": float(country.get("schools", 62.0)),
        "headroom": float(s.get("headroom", 0.0)),
        "deficit": float(s.get("deficit", 0.0)),
        "market_conf": float(s.get("market_conf", 50.0)),
        "approval": float(s.get("approval", 50.0)),
        "regional_gap": float(regional_gap),
        "regional_unemployment": float(regional_jobless),
    }


def format_value(metric, value):
    return FORMATS.get(metric, "{:.1f}").format(float(value))


def start_mission(s, mission_id="balanced_renewal", preserve_history=False):
    """Start a five-year mandate and take a fresh baseline without changing game stats."""
    if mission_id not in MISSIONS:
        mission_id = "balanced_renewal"
    if preserve_history:
        archive = list(s.get("mission_archive", []))
        previous = s.get("mission_latest")
        if previous:
            previous_id = s.get("government_mission", mission_id)
            archive.append({
                "term": int(previous.get("term", s.get("term", 1))),
                "mission": previous_id,
                "title": MISSIONS.get(previous_id, MISSIONS[mission_id])["title"],
                "score": float(previous.get("score", 0.0)),
                "result": previous.get("result", "Term ended"),
            })
        s["mission_archive"] = archive[-10:]
    try:
        import regional_economy
        regional_economy.ensure(s)
    except (ImportError, AttributeError, TypeError):
        pass
    s["government_mission"] = mission_id
    s["mission_term"] = int(s.get("term", 1))
    s["mission_baseline"] = metric_values(s)
    s["mission_history"] = []
    s["mission_milestones"] = []
    s["mission_latest"] = None
    s["mission_finalised"] = False
    return s["mission_baseline"]


def ensure(s):
    """Migrate an in-progress save which predates the mandate system."""
    if s.get("government_mission") not in MISSIONS:
        s["government_mission"] = "balanced_renewal"
    if not isinstance(s.get("mission_archive"), list):
        s["mission_archive"] = []
    if not isinstance(s.get("mission_history"), list):
        s["mission_history"] = []
    if not isinstance(s.get("mission_milestones"), list):
        s["mission_milestones"] = []
    if not isinstance(s.get("mission_baseline"), dict) or not s.get("mission_baseline"):
        start_mission(s, s.get("government_mission", "balanced_renewal"), preserve_history=True)
    s.setdefault("mission_term", int(s.get("term", 1)))
    s.setdefault("mission_latest", None)
    s.setdefault("mission_finalised", False)
    return s


def get_progress(s):
    """Calculate live mission progress against the start-of-term baseline."""
    ensure(s)
    mission_id = s.get("government_mission", "balanced_renewal")
    mission = MISSIONS[mission_id]
    baseline = s["mission_baseline"]
    current = metric_values(s)
    goals = []
    for item in mission["objectives"]:
        key = item["metric"]
        start = float(baseline.get(key, current[key]))
        now = float(current[key])
        change = float(item["delta"])
        target = start + change
        ratio = 1.0 if abs(change) < 1e-9 else (now - start) / change
        ratio = max(0.0, min(1.0, ratio))
        goals.append({
            "metric": key,
            "label": item["label"],
            "detail": item["detail"],
            "baseline": start,
            "current": now,
            "target": target,
            "unit": item["unit"],
            "progress": round(ratio * 100.0, 1),
            "achieved": ratio >= 1.0,
        })
    score = round(mean(goal["progress"] for goal in goals)) if goals else 0
    return {
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "mission_id": mission_id,
        "title": mission["title"],
        "description": mission["description"],
        "score": score,
        "goals": goals,
    }


def _outcome(score):
    if score >= 85:
        return "Mandate exceeded"
    if score >= 70:
        return "Mandate delivered"
    if score >= 50:
        return "Partially delivered"
    return "Mandate missed"


def record_year(s):
    """Record an annual mandate checkpoint; apply a small political consequence in Year 5."""
    ensure(s)
    term = int(s.get("term", 1))
    year = int(s.get("year", 1))
    history = list(s.get("mission_history", []))
    if any(int(item.get("term", -1)) == term and int(item.get("year", -1)) == year for item in history):
        return None
    progress = get_progress(s)
    progress["goals"] = [dict(goal) for goal in progress["goals"]]
    history.append(progress)
    s["mission_history"] = history[-10:]

    reached = {int(item.get("threshold", 0)) for item in s.get("mission_milestones", [])}
    for threshold in (25, 50, 75, 100):
        if progress["score"] >= threshold and threshold not in reached:
            milestone = {
                "term": term,
                "year": year,
                "threshold": threshold,
                "label": f"{threshold}% of the mandate",
            }
            s["mission_milestones"] = list(s.get("mission_milestones", [])) + [milestone]
            s.setdefault("event_cards", []).append({
                "title": "Government mandate milestone",
                "text": milestone["label"] + " reached.",
                "summary": f"{progress['score']}/100 overall mission progress",
            })

    if year >= 5 and not s.get("mission_finalised", False):
        result = _outcome(progress["score"])
        progress["result"] = result
        s["mission_finalised"] = True
        if progress["score"] >= 85:
            s["approval"] = round(max(0.0, min(100.0, float(s.get("approval", 50.0)) + 1.5)), 1)
            s["pm_opinion"] = round(max(0.0, min(100.0, float(s.get("pm_opinion", 50.0)) + 1.0)), 1)
            note = "The Government has exceeded its five-year mandate. The Prime Minister publicly backs the Chancellor's record."
        elif progress["score"] < 35:
            s["approval"] = round(max(0.0, min(100.0, float(s.get("approval", 50.0)) - 1.5)), 1)
            s["pm_opinion"] = round(max(0.0, min(100.0, float(s.get("pm_opinion", 50.0)) - 1.0)), 1)
            note = "The Government has missed most of its five-year mandate. Number 10 questions the record."
        else:
            note = f"The five-year mandate is complete: {result.lower()}."
        s["message"] = (str(s.get("message", "")).strip() + " " + note).strip()
    s["mission_latest"] = progress
    return progress


def render(s=None):
    """Render the live mandate dashboard inside the Government workspace."""
    import streamlit as st
    s = s or st.session_state
    ensure(s)
    progress = s.get("mission_latest") if s.get("mission_finalised") and s.get("mission_latest") else get_progress(s)
    mission = MISSIONS[progress["mission_id"]]

    st.markdown("### Five-year government mandate")
    st.caption("Your chosen programme is measured against the opening position of each five-year term. Progress uses the existing game models; it is not a separate economic bonus.")
    st.markdown(f"## {mission['title']}")
    st.write(mission["description"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Mandate progress", f"{progress['score']}/100")
    c2.metric("Term", f"{progress['term']} of 5 years")
    c3.metric("Objectives delivered", f"{sum(1 for g in progress['goals'] if g['achieved'])}/3")
    st.progress(progress["score"] / 100.0, text=f"Overall mandate progress · {progress['score']}%")

    st.markdown("#### Your three objectives")
    cols = st.columns(len(progress["goals"]))
    for col, goal in zip(cols, progress["goals"]):
        with col:
            st.markdown(f"**{goal['label']}**")
            st.progress(goal["progress"] / 100.0)
            st.caption(f"Opening: {format_value(goal['metric'], goal['baseline'])}")
            st.caption(f"Current: **{format_value(goal['metric'], goal['current'])}**")
            st.caption(f"Target: {format_value(goal['metric'], goal['target'])}")
            if goal["achieved"]:
                st.success("Target achieved")
            else:
                st.caption(goal["detail"])

    latest = s.get("mission_latest")
    if latest and latest.get("result"):
        st.divider()
        st.markdown(f"**Final mandate result: {latest['result']} · {latest['score']}/100**")
    elif latest:
        st.caption(f"Last year-end checkpoint: Year {latest['year']} · {latest['score']}/100")

    milestones = list(s.get("mission_milestones", []))
    if milestones:
        st.markdown("#### Mandate milestones")
        for item in reversed(milestones[-4:]):
            st.caption(f"Term {item['term']} · Year {item['year']} · {item['label']}")

    history = list(s.get("mission_history", []))
    if history:
        with st.expander("Annual mandate progress", expanded=False):
            st.dataframe([
                {"Year": f"Term {item['term']}, Year {item['year']}",
                 "Progress": f"{item['score']}%",
                 "Objectives achieved": f"{sum(1 for goal in item['goals'] if goal['achieved'])}/3"}
                for item in reversed(history)
            ], hide_index=True, use_container_width=True)

    archive = list(s.get("mission_archive", []))
    if archive:
        with st.expander("Previous five-year mandates", expanded=False):
            st.dataframe([
                {"Term": item["term"], "Programme": item["title"],
                 "Result": item["result"], "Score": f"{item['score']:.0f}/100"}
                for item in reversed(archive)
            ], hide_index=True, use_container_width=True)
