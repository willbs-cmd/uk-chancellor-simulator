"""Public services performance: delayed delivery, workforce pressure and annual service outcomes.

All scores are illustrative gameplay indices, not official service statistics. Funding improves
capacity gradually; it does not instantly remove waiting lists or court backlogs.
"""
import random

import pandas as pd
import streamlit as st

import budget
import cabinet_management
import country as country_data

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


def productivity_growth_effect(scores):
    """Small annual growth contribution from the level of productive public services."""
    weights = {
        "Education": 0.30,
        "Transport": 0.25,
        "Local government": 0.20,
        "NHS": 0.15,
        "Justice": 0.10,
    }
    weighted_score = sum(float(scores.get(key, SERVICES[key]["start"])) * weight
                         for key, weight in weights.items())
    return round(_clip((weighted_score - 60.0) * 0.005, -0.12, 0.12), 3)


def employment_unemployment_effect(scores):
    """Annual unemployment change (percentage points) from public-service capability."""
    weights = {
        "Education": 0.30, "NHS": 0.25, "Transport": 0.20,
        "Local government": 0.15, "Justice": 0.10,
    }
    weighted_score = sum(float(scores.get(key, SERVICES[key]["start"])) * weight
                         for key, weight in weights.items())
    # Skills, health, transport and local support make it easier to enter and remain in work.
    return round(_clip((60.0 - weighted_score) * 0.0025, -0.06, 0.06), 3)


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
    s.setdefault("public_service_strike_impact", {})
    s.setdefault("public_service_delivery_latest", {})
    s.setdefault("public_service_delivery_history", [])


def _department_ratio(s, key):
    defaults = budget.SPEND_DEFAULTS
    current = s.get("dept_spend", {})
    if key not in defaults:
        return 0.0
    baseline = max(1.0, float(defaults[key]["default"]))
    actual = float(current.get(key, baseline))
    return max(-0.35, min(0.35, actual / baseline - 1.0))


def delivery_scorecard(previous_scores, current_scores, s=None):
    """Compare annual service outcomes with modest, funding-aware delivery targets."""
    s = s or st.session_state
    rows = []
    for key, spec in SERVICES.items():
        previous = float(previous_scores.get(key, spec["start"]))
        actual = float(current_scores.get(key, previous))
        funding = sum(_department_ratio(s, dep) for dep in spec["departments"]) / len(spec["departments"])
        target_change = max(-0.45, min(0.60, 0.15 + funding * 0.90))
        target = round(_clip(previous + target_change, 10, 95), 1)
        actual_change = round(actual - previous, 1)
        variance = round(actual - target, 1)
        status = "On track" if variance >= -0.2 else ("Slightly behind" if variance >= -0.8 else "Off track")
        rows.append({
            "Service": key, "Previous score": round(previous, 1),
            "Target score": target, "Actual score": round(actual, 1),
            "Change": actual_change, "Against target": variance,
            "Funding position (%)": round(funding * 100, 1), "Status": status,
        })
    return rows


def advance(s=None):
    """Advance service delivery once per in-game year, using the approved funding baseline."""
    s = s or st.session_state
    ensure(s)
    tick = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    if s.public_service_last_tick == tick:
        return
    s.public_service_last_tick = tick
    scores = dict(s.public_service_scores)
    previous_scores = dict(scores)
    country = dict(s.get("country", {}))
    notes = []

    # An unresolved dispute becomes real industrial action in the following year.
    # This is deliberately separate from the initial warning and is idempotent
    # because the annual tick guard above is set before any consequences apply.
    active_strikes = []
    strike_pressure = 0.0
    for strike in list(s.public_service_strikes):
        if strike.get("paused"):
            strike = dict(strike)
            strike["paused"] = False
            strike["text"] = strike.get("text", "") + " The mediation period has expired without a lasting agreement."
        strike = dict(strike)
        severity = min(3.0, float(strike.get("severity", 1.0)) + 0.35)
        duration = int(strike.get("duration_years", 0)) + 1
        strike["severity"] = round(severity, 1)
        strike["duration_years"] = duration
        strike["last_escalated"] = tick
        pressure = severity * min(1.6, 1.0 + 0.2 * max(0, duration - 1))
        strike_pressure += pressure
        strike_id = strike.get("id")
        disruption = 0.35 + severity * 0.30
        if strike_id == "NHS workforce":
            affected = ("NHS",)
            country["nhs_morale"] = _clip(float(country.get("nhs_morale", 52.0)) - 2.0 - severity * 0.45)
            country["nhs_waiting"] = max(0.0, float(country.get("nhs_waiting", 7.4)) + 0.12 + severity * 0.06)
        elif strike_id == "Education workforce":
            affected = ("Education",)
            country["schools"] = _clip(float(country.get("schools", 62.0)) - 0.7 - severity * 0.15)
        elif strike_id == "Public-sector pay":
            affected = tuple(SERVICES)
            country["schools"] = _clip(float(country.get("schools", 62.0)) - 0.25 - severity * 0.05)
            country["nhs_morale"] = _clip(float(country.get("nhs_morale", 52.0)) - 0.6 - severity * 0.15)
        else:
            affected = ("Local government",)
            country["rail"] = _clip(float(country.get("rail", 82.0)) - 0.7 - severity * 0.15)
        for service_key in affected:
            service_disruption = disruption if len(affected) == 1 else disruption * 0.42
            scores[service_key] = round(_clip(scores.get(service_key, 60.0) - service_disruption, 10, 95), 1)
        s.approval = round(_clip(float(s.get("approval", 50.0)) - 0.25 - severity * 0.12), 1)
        active_strikes.append(strike)
        notes.append(f"{strike.get('group', strike.get('id', 'Public-sector'))} strike disruption worsened")
        s.public_service_events = (list(s.get("public_service_events", [])) + [{
            "year": tick, "title": f"{strike.get('group', 'Public-sector workers')} action escalates",
            "detail": f"Industrial action has reduced {', '.join(x.lower() for x in affected)} performance; disruption has now lasted {duration} year(s)."
        }])[-20:]
    s.public_service_strikes = active_strikes
    s.country = country

    # Industrial action also carries a wider economic cost. Lost working time,
    # delayed treatment and interrupted education weaken output and demand;
    # prolonged disputes compound the drag, but hard caps prevent runaway effects.
    growth_drag = round(min(0.18, strike_pressure * 0.025), 3)
    receipts_drag = round(min(0.65, strike_pressure * 0.09), 2)
    market_drag = round(min(1.2, strike_pressure * 0.35), 2)
    confidence_drag = round(min(1.0, strike_pressure * 0.25), 2)
    investment_drag = round(min(0.6, strike_pressure * 0.12), 2)
    spending_drag = round(min(0.4, strike_pressure * 0.08), 2)
    if strike_pressure:
        s.growth = round(float(s.get("growth", 0.8)) - growth_drag, 2)
        s.headroom = round(float(s.get("headroom", 0.0)) - receipts_drag, 1)
        s.deficit = round(float(s.get("deficit", 0.0)) + receipts_drag, 1)
        s.market_conf = round(_clip(float(s.get("market_conf", 55.0)) - market_drag), 1)
        if "business_confidence" in s:
            s.business_confidence = round(_clip(float(s.business_confidence) - confidence_drag, 5, 95), 1)
        if "business_investment" in s:
            s.business_investment = round(_clip(float(s.business_investment) - investment_drag, 55, 150), 1)
        if "consumer_spending" in s:
            s.consumer_spending = round(_clip(float(s.consumer_spending) - spending_drag, 65, 140), 1)
        notes.append(f"Industrial action reduced annual growth by {growth_drag:.2f}pp and receipts by £{receipts_drag:.2f}bn")
    s.public_service_strike_impact = {
        "year": tick, "active_disputes": len(active_strikes),
        "pressure": round(strike_pressure, 2), "growth_drag_pp": growth_drag,
        "receipts_drag_bn": receipts_drag, "market_drag": market_drag,
        "confidence_drag": confidence_drag, "investment_drag": investment_drag,
        "spending_drag": spending_drag,
    }

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
        # Ministerial delivery skill is a small additional influence, not a substitute for funding.
        change += cabinet_management.service_effect(s, key)
        change += 0.08
        change = max(-1.25, min(1.25, change))
        scores[key] = round(_clip(scores[key] + change, 10, 95), 1)
        notes.append(f"{key} {change:+.1f}")

    s.public_service_scores = scores
    scorecard = delivery_scorecard(previous_scores, scores, s)
    s.public_service_delivery_latest = {"year": tick, "rows": scorecard}
    s.public_service_delivery_history = (list(s.get("public_service_delivery_history", [])) + [{
        "year": tick, "on_track": sum(1 for row in scorecard if row["Status"] == "On track"),
        "behind": sum(1 for row in scorecard if row["Status"] != "On track"),
        "average_variance": round(sum(row["Against target"] for row in scorecard) / max(1, len(scorecard)), 2),
    }])[-20:]
    # Better-performing schools, transport, local services and healthcare support
    # skills, labour participation and the reliability of the wider economy.
    s.public_service_productivity_effect = productivity_growth_effect(scores)

    # A separate, small labour-supply channel: service capability affects how easily
    # people can gain or retain work. The tax-receipt effect follows through the
    # existing living-economy update in the next year.
    employment_effect = employment_unemployment_effect(scores)
    country_stats = dict(s.get("country", {}))
    if "unemployment" in country_stats:
        bounds = country_data.STATS["unemployment"]
        country_stats["unemployment"] = round(_clip(
            float(country_stats["unemployment"]) + employment_effect,
            bounds["lo"], bounds["hi"]), 2)
        s.country = country_stats
    s.public_service_employment_effect = employment_effect

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
        **scores,
        "Employment effect (pp unemployment)": employment_effect,
        "Productivity growth effect (pp)": s.public_service_productivity_effect,
    }])[-20:]
    s.public_service_year_notes = notes


def resolve_strike(strike_id, choice):
    """Manage a live dispute through staged offers or mediation."""
    s = st.session_state
    ensure(s)
    strikes = list(s.public_service_strikes)
    strike = next((x for x in strikes if x.get("id") == strike_id), None)
    if not strike:
        return
    severity = float(strike.get("severity", 1.0))
    demand = round(float(strike.get("demand_bn", 0.7 + severity * 0.45)), 2)
    scores = dict(s.public_service_scores)
    affected_services = (
        ("NHS",) if strike_id == "NHS workforce" else
        ("Education",) if strike_id == "Education workforce" else
        tuple(SERVICES) if strike_id == "Public-sector pay" else
        ("Local government",)
    )

    if choice in ("offer", "improve", "final_offer"):
        round_no = int(strike.get("negotiation_round", 0)) + 1
        fraction = {"offer": 0.55, "improve": 0.80, "final_offer": 1.0}[choice]
        if choice == "offer" and round_no > 1:
            return
        if choice == "improve" and round_no < 2:
            return
        if choice == "final_offer" and round_no < 2:
            return
        amount = round(demand * fraction, 2)
        country = s.get("country", {})
        morale_key = "nhs_morale" if strike_id == "NHS workforce" else None
        morale = float(country.get(morale_key, 52.0)) if morale_key else 52.0
        # Acceptance is deterministic: a better offer and constructive workforce
        # relations help, while severe disputes make unions harder to satisfy.
        acceptance_score = fraction * 100 + max(-8.0, min(8.0, (morale - 52.0) * 0.35))
        acceptance_threshold = 68.0 + severity * 5.0
        accepted = choice == "final_offer" or acceptance_score >= acceptance_threshold
        if accepted:
            s.headroom = round(float(s.get("headroom", 0.0)) - amount, 1)
            s.deficit = round(float(s.get("deficit", 0.0)) + amount, 1)
            for service_key in affected_services:
                scores[service_key] = _clip(scores.get(service_key, SERVICES[service_key]["start"]) + 1.4 + severity * 0.25, 10, 95)
            if strike_id == "NHS workforce":
                c = dict(country); c["nhs_morale"] = _clip(c.get("nhs_morale", 52) + 5); s.country = c
            outcome = (f"Unions accept your {round(fraction * 100)}% offer. The settlement costs "
                       f"£{amount:.2f}bn a year and industrial action is called off.")
            s.public_service_strikes = [x for x in strikes if x.get("id") != strike_id]
            decision = "Settlement accepted"
        else:
            updated_strikes = []
            for item in strikes:
                if item.get("id") == strike_id:
                    item = {**item, "demand_bn": demand,
                            "negotiation_round": round_no,
                            "last_offer_bn": amount,
                            "last_offer_fraction": fraction,
                            "severity": round(min(3.0, severity + 0.1), 1),
                            "negotiation_message": (
                                f"Unions reject the £{amount:.2f}bn offer. They say it falls short "
                                "of what is needed to resolve pay and retention pressures."
                            )}
                updated_strikes.append(item)
            s.public_service_strikes = updated_strikes
            s.approval = _clip(float(s.get("approval", 50.0)) - 0.25)
            outcome = (f"Unions reject your £{amount:.2f}bn offer. The dispute remains active; "
                       "you can improve the offer, make a final offer or hold the line.")
            decision = f"{round(fraction * 100)}% offer rejected"
    elif choice == "settle":
        amount = demand
        s.headroom = round(float(s.get("headroom", 0.0)) - amount, 1)
        s.deficit = round(float(s.get("deficit", 0.0)) + amount, 1)
        for service_key in affected_services:
            scores[service_key] = _clip(scores.get(service_key, SERVICES[service_key]["start"]) + 1.4 + severity * 0.25, 10, 95)
        if strike_id == "NHS workforce":
            c = dict(s.get("country", {})); c["nhs_morale"] = _clip(c.get("nhs_morale", 52) + 5); s.country = c
        s.public_service_strikes = [x for x in strikes if x.get("id") != strike_id]
        outcome = f"You agree the full £{amount:.2f}bn-a-year union demand. Industrial action is called off."
        decision = "Full settlement"
    elif choice == "mediate":
        mediation_cost = round(demand * 0.25, 2)
        s.headroom = round(float(s.get("headroom", 0.0)) - mediation_cost, 1)
        s.deficit = round(float(s.get("deficit", 0.0)) + mediation_cost, 1)
        s.approval = _clip(float(s.get("approval", 50.0)) + 0.3)
        s.public_service_strikes = [
            ({**x, "paused": True, "severity": round(max(0.5, float(x.get("severity", 1.0)) - 0.25), 1)})
            if x.get("id") == strike_id else x for x in strikes
        ]
        outcome = f"You appoint an independent mediator, spending £{mediation_cost:.2f}bn on a temporary package. The dispute is paused; unions will return if no lasting agreement is reached."
        decision = "Mediation"
    elif choice == "hold":
        for service_key in affected_services:
            scores[service_key] = _clip(scores.get(service_key, SERVICES[service_key]["start"]) - 1.5 - severity * 0.4, 10, 95)
        s.approval = _clip(float(s.get("approval", 50.0)) - 0.7 - severity * 0.2)
        if strike_id == "NHS workforce":
            c = dict(s.get("country", {})); c["nhs_morale"] = _clip(c.get("nhs_morale", 52) - 4); s.country = c
        s.public_service_strikes = [
            ({**x, "severity": round(min(3.0, float(x.get("severity", 1.0)) + 0.25), 1),
              "text": x.get("text", "") + " The Chancellor has refused further funding; unions maintain their action."})
            if x.get("id") == strike_id else x for x in strikes
        ]
        outcome = "You refuse extra funding. The Treasury avoids the immediate bill, but the strike continues, morale deteriorates and disruption is likely to deepen."
        decision = "Held the line"
    else:
        return

    s.public_service_scores = scores
    s.public_service_resolved = (list(s.get("public_service_resolved", [])) + [{
        "year": f"Term {s.get('term', 1)}, Year {s.get('year', 1)}",
        "group": strike.get("group", strike_id), "decision": decision, "outcome": outcome
    }])[-20:]
    s.message = outcome
    s.event_cards = list(s.get("event_cards", [])) + [{
        "title": f"Industrial dispute: {strike.get('group', strike_id)}",
        "text": outcome, "summary": f"Decision: {decision}"
    }]


def render():
    s = st.session_state
    ensure(s)
    st.markdown("### Public Services & Government Performance")
    st.caption("Service outcomes evolve gradually from funding, workforce capacity and demand. Stronger education, transport, health and local services also support long-run productivity. Scores are illustrative gameplay indices, not official statistics.")
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
        impact = s.get("public_service_strike_impact", {})
        if impact.get("active_disputes"):
            m1, m2, m3 = st.columns(3)
            m1.metric("Annual growth drag", f"-{float(impact.get('growth_drag_pp', 0.0)):.2f}pp")
            m2.metric("Lost Treasury receipts", f"£{float(impact.get('receipts_drag_bn', 0.0)):.2f}bn")
            m3.metric("Market confidence impact", f"-{float(impact.get('market_drag', 0.0)):.2f}")
            st.caption("These are additional annual effects from unresolved action; they are applied once per year and are separate from the cost of any pay settlement.")
        for strike in list(s.public_service_strikes):
            with st.container(border=True):
                st.markdown(f"**{strike.get('group', 'Public-sector unions')}**")
                st.write(strike.get("text", "Industrial action is threatened."))
                demand = float(strike.get("demand_bn", 0.7 + float(strike.get("severity", 1.0)) * 0.45))
                round_no = int(strike.get("negotiation_round", 0))
                st.caption(f"Severity: {strike.get('severity', 1.0):.1f}/3 · Unresolved: {int(strike.get('duration_years', 0))} year(s) · Raised {strike.get('year', 'this year')} · Indicative union demand: £{demand:.2f}bn a year")
                if round_no:
                    st.info(strike.get("negotiation_message", f"Negotiation round {round_no}: last offer £{float(strike.get('last_offer_bn', 0.0)):.2f}bn a year."))
                c1, c2, c3 = st.columns(3)
                if round_no == 0:
                    if c1.button("Make opening offer (55%)", key=f"ps_offer_{strike['id']}"):
                        resolve_strike(strike["id"], "offer"); st.rerun()
                else:
                    if c1.button("Improve offer (80%)", key=f"ps_improve_{strike['id']}"):
                        resolve_strike(strike["id"], "improve"); st.rerun()
                if c2.button("Final offer (100%)", key=f"ps_final_{strike['id']}"):
                    resolve_strike(strike["id"], "final_offer" if round_no else "settle"); st.rerun()
                if c3.button("Hold the line", key=f"ps_hold_{strike['id']}"):
                    resolve_strike(strike["id"], "hold"); st.rerun()
                st.button("Appoint a mediator", key=f"ps_mediate_{strike['id']}", on_click=resolve_strike,
                          args=(strike["id"], "mediate"))
    else:
        st.info("No major public-sector industrial dispute is currently active.")
    latest_delivery = s.get("public_service_delivery_latest", {})
    if latest_delivery.get("rows"):
        with st.expander("Spending Review delivery scorecard", expanded=False):
            st.caption("Annual targets reflect the approved departmental funding position. They are performance benchmarks, not guaranteed results; workforce, demand and delivery capacity still matter.")
            st.dataframe(pd.DataFrame(latest_delivery["rows"]), hide_index=True, use_container_width=True)
            history = list(s.get("public_service_delivery_history", []))
            if history:
                st.caption(f"Latest review: {latest_delivery.get('year', 'current year')} · "
                           f"{history[-1].get('on_track', 0)} services on track · "
                           f"{history[-1].get('behind', 0)} behind target.")

    if s.public_service_history:
        with st.expander("Service performance history"):
            st.line_chart(pd.DataFrame(s.public_service_history).set_index("Year"), use_container_width=True)
    if s.public_service_resolved:
        with st.expander("Industrial relations history"):
            st.dataframe(list(reversed(s.public_service_resolved)), hide_index=True, use_container_width=True)
    employment_effect = float(s.get("public_service_employment_effect", 0.0))
    productivity_effect = float(s.get("public_service_productivity_effect", 0.0))
    st.caption(
        f"Annual economic spillover: public-service capability changes unemployment by "
        f"{employment_effect:+.2f} percentage points and contributes {productivity_effect:+.2f} "
        f"percentage points to productivity growth. These are gradual, bounded effects; "
        "workforce shortages, inflation, demand and delivery capacity can delay or dilute improvements."
    )
