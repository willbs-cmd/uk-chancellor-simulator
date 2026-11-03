"""Public services performance: delayed delivery, workforce pressure and annual service outcomes.

All scores are illustrative gameplay indices, not official service statistics. Funding improves
capacity gradually; it does not instantly remove waiting lists or court backlogs.
"""
import random

import pandas as pd
import streamlit as st

import budget

SERVICES = {
    "NHS": {"label": "NHS access & capacity", "start": 54.0, "departments": ("health", "social_care"),
            "description": "Hospital capacity, access and the ability to meet demand."},
    "Education": {"label": "Schools & education", "start": 62.0, "departments": ("education", "skills"),
                  "description": "School standards, teacher capacity and further-education provision."},
    "Justice": {"label": "Policing & justice", "start": 48.0, "departments": ("justice",),
                "description": "Police capacity, court throughput and prison pressure."},
    "Transport": {"label": "Transport reliability", "start": 61.0, "departments": ("transport",),
                  "description": "Rail, road and local transport reliability."},
    "Local government": {"label": "Councils & local services", "start": 52.0, "departments": ("local_government", "housing"),
                         "description": "Council resilience, housing support and local service capacity."},
}
WORKFORCE = {
    "NHS": {"department": "health", "pay_weight": 0.75, "morale_key": "nhs_morale"},
    "Schools": {"department": "education", "pay_weight": 0.45, "morale_key": None},
    "Public services": {"department": "public_sector_pay", "pay_weight": 1.0, "morale_key": None},
}


def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def ensure(s=None):
    s = s or st.session_state
    scores = dict(s.get("public_service_scores", {}))
    for key, spec in SERVICES.items():
        scores.setdefault(key, float(spec["start"]))
    s.public_service_scores = scores
    s.setdefault("public_service_history", [])
    s.setdefault("public_service_events", [])
    s.setdefault("public_service_last_tick", "")
    s.setdefault("public_service_strikes", [])
    s.setdefault("public_service_resolved", [])
    s.setdefault("public_service_year_notes", [])


def _department_ratio(s, key):
    defaults = budget.SPEND_DEFAULTS
    current = s.get("dept_spend", {})
    if key not in defaults:
        return 0.0
    baseline = max(1.0, float(defaults[key]["default"]))
    actual = float(current.get(key, baseline))
    return max(-0.35, min(0.35, actual / baseline - 1.0))


def advance(s=None):
    """Advance service delivery once per in-game year, using the approved funding baseline."""
    s = s or st.session_state
    ensure(s)
    tick = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    if s.public_service_last_tick == tick:
        return
    s.public_service_last_tick = tick
    scores = dict(s.public_service_scores)
    country = s.get("country", {})
    notes = []

    for key, spec in SERVICES.items():
        funding = sum(_department_ratio(s, dep) for dep in spec["departments"]) / len(spec["departments"])
        # Funding is only one constraint: delivery capacity, workforce and demand matter too.
        change = funding * 2.2
        if key == "NHS":
            change += (float(country.get("nhs_morale", 52.0)) - 52.0) * 0.018
            change -= max(0.0, float(country.get("nhs_waiting", 7.4)) - 7.4) * 0.10
        elif key == "Education":
            change += (float(country.get("schools", 62.0)) - 62.0) * 0.025
        elif key == "Justice":
            change -= max(0.0, float(country.get("prisons", 98.0)) - 98.0) * 0.12
        elif key == "Transport":
            change += (float(country.get("rail", 82.0)) - 82.0) * 0.025
        elif key == "Local government":
            change += _department_ratio(s, "local_government") * 1.0
            change += _department_ratio(s, "housing") * 0.8
        # A little natural improvement is possible, but demand and ageing prevent automatic recovery.
        change += 0.08
        change = max(-1.25, min(1.25, change))
        scores[key] = round(_clip(scores[key] + change, 10, 95), 1)
        notes.append(f"{key} {change:+.1f}")

    s.public_service_scores = scores

    # Pay settlements and staff morale create a separate, visible industrial-relations risk.
    pay_ratio = _department_ratio(s, "public_sector_pay")
    inflation = float(s.get("inflation", 2.0))
    pay_pressure = max(0.0, inflation - (2.0 + pay_ratio * 10.0))
    morale = float(country.get("nhs_morale", 52.0))
    risks = []
    if morale < 43 or (pay_pressure > 1.2 and morale < 58):
        risks.append(("NHS workforce", "NHS staff", "Low morale and pay pressure are increasing the risk of coordinated industrial action."))
    if pay_pressure > 2.0:
        risks.append(("Public-sector pay", "Public-sector unions", "Pay settlements are falling behind inflation and unions are preparing coordinated action."))
    if float(scores.get("Education", 62)) < 48 and pay_pressure > 1.0:
        risks.append(("Education workforce", "Teachers", "Teacher retention is deteriorating amid pay and workload disputes."))

    existing = {x.get("id") for x in s.public_service_strikes}
    rng = random.Random(f"{s.get('seed', 0)}:{tick}:public-services")
    if risks and rng.random() < min(0.82, 0.25 + 0.18 * len(risks)):
        candidate = rng.choice(risks)
        if candidate[0] not in existing:
            s.public_service_strikes = (list(s.public_service_strikes) + [{
                "id": candidate[0], "group": candidate[1], "text": candidate[2],
                "year": tick, "severity": round(min(3.0, 0.8 + pay_pressure * 0.25 + max(0, 50 - morale) * 0.025), 1)
            }])[-5:]
            s.public_service_events = (list(s.public_service_events) + [{
                "year": tick, "title": f"{candidate[1]} announce industrial action",
                "detail": candidate[2]
            }])[-20:]
            notes.append(f"{candidate[1]} industrial action risk has escalated")

    s.public_service_history = (list(s.public_service_history) + [{
        "Year": f"Term {s.get('term', 1)}, Year {s.get('year', 1)}",
        **scores
    }])[-20:]
    s.public_service_year_notes = notes


def resolve_strike(strike_id, choice):
    """Resolve a live industrial dispute with a fiscal and service-delivery trade-off."""
    s = st.session_state
    ensure(s)
    strike = next((x for x in s.public_service_strikes if x.get("id") == strike_id), None)
    if not strike:
        return
    severity = float(strike.get("severity", 1.0))
    cost = 0.7 + severity * 0.45
    scores = dict(s.public_service_scores)
    if choice == "settle":
        s.headroom = round(float(s.headroom) - cost, 1)
        s.deficit = round(float(s.deficit) + cost, 1)
        scores["NHS" if strike_id == "NHS workforce" else ("Education" if strike_id == "Education workforce" else "Local government")] = _clip(
            scores.get("NHS", 50) + 1.4 + severity * 0.25, 10, 95)
        if strike_id == "NHS workforce":
            c = dict(s.get("country", {})); c["nhs_morale"] = _clip(c.get("nhs_morale", 52) + 5); s.country = c
        outcome = f"You agree a funded settlement costing £{cost:.1f}bn a year. Industrial action is called off, but the Treasury has less headroom."
    elif choice == "mediate":
        mediation_cost = round(cost * 0.25, 1)
        s.headroom = round(float(s.headroom) - mediation_cost, 1)
        s.deficit = round(float(s.deficit) + mediation_cost, 1)
        s.approval = _clip(float(s.approval) + 0.3)
        outcome = f"You appoint an independent mediator, spending £{mediation_cost:.1f}bn on a temporary package. The dispute is paused, not permanently settled."
    elif choice == "hold":
        scores["NHS" if strike_id == "NHS workforce" else ("Education" if strike_id == "Education workforce" else "Local government")] = _clip(
            scores.get("NHS", 50) - 1.5 - severity * 0.4, 10, 95)
        s.approval = _clip(float(s.approval) - 0.7 - severity * 0.2)
        if strike_id == "NHS workforce":
            c = dict(s.get("country", {})); c["nhs_morale"] = _clip(c.get("nhs_morale", 52) - 4); s.country = c
        outcome = "You refuse extra funding. The Treasury avoids the immediate bill, but disruption and staff morale worsen."
    else:
        return
    s.public_service_scores = scores
    s.public_service_strikes = [x for x in s.public_service_strikes if x.get("id") != strike_id]
    s.public_service_resolved = (list(s.public_service_resolved) + [{
        "year": f"Term {s.get('term', 1)}, Year {s.get('year', 1)}",
        "group": strike.get("group", strike_id), "decision": choice.title(), "outcome": outcome
    }])[-20:]
    s.message = outcome
    s.event_cards = list(s.get("event_cards", [])) + [{
        "title": f"Industrial dispute: {strike.get('group', strike_id)}",
        "text": outcome, "summary": f"Decision: {choice.title()}"
    }]


def render():
    s = st.session_state
    ensure(s)
    st.markdown("### Public Services & Government Performance")
    st.caption("Service outcomes evolve gradually from funding, workforce capacity and demand. Scores are illustrative gameplay indices, not official statistics.")
    scores = s.public_service_scores
    cols = st.columns(5)
    for col, (key, spec) in zip(cols, SERVICES.items()):
        value = float(scores[key])
        col.metric(spec["label"], f"{value:.0f}/100", help=spec["description"])
        col.progress(int(value))
    st.markdown("#### What is driving performance?")
    rows = []
    for key, spec in SERVICES.items():
        deps = ", ".join(budget.SPEND_DEFAULTS[d]["short"] for d in spec["departments"])
        rows.append({"Service": key, "Performance": scores[key], "Main funding lines": deps, "Current pressure": spec["description"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    if s.public_service_strikes:
        st.markdown("#### Industrial relations")
        for strike in list(s.public_service_strikes):
            with st.container(border=True):
                st.markdown(f"**{strike.get('group', 'Public-sector unions')}**")
                st.write(strike.get("text", "Industrial action is threatened."))
                st.caption(f"Severity: {strike.get('severity', 1.0):.1f}/3 · Raised {strike.get('year', 'this year')}")
                c1, c2, c3 = st.columns(3)
                if c1.button("Negotiate a settlement", key=f"ps_settle_{strike['id']}"):
                    resolve_strike(strike["id"], "settle"); st.rerun()
                if c2.button("Appoint a mediator", key=f"ps_mediate_{strike['id']}"):
                    resolve_strike(strike["id"], "mediate"); st.rerun()
                if c3.button("Hold the line", key=f"ps_hold_{strike['id']}"):
                    resolve_strike(strike["id"], "hold"); st.rerun()
    else:
        st.info("No major public-sector industrial dispute is currently active.")
    if s.public_service_history:
        with st.expander("Service performance history"):
            st.line_chart(pd.DataFrame(s.public_service_history).set_index("Year"), use_container_width=True)
    if s.public_service_resolved:
        with st.expander("Industrial relations history"):
            st.dataframe(list(reversed(s.public_service_resolved)), hide_index=True, use_container_width=True)
    st.caption("More funding improves the odds of better outcomes, but workforce shortages, inflation, demand and delivery capacity can delay or dilute the benefit.")
