"""Delayed stakeholder reactions to an enacted Budget.

The Budget engine owns fiscal arithmetic. This module turns the approved
ledger into a small, deterministic set of stakeholder reactions and applies
only second-round confidence effects at the next Spring.
"""
def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def _number(mapping, key, default=0.0):
    try:
        return float((mapping or {}).get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _event(kind, title, group, text, summary, effects=None):
    return {
        "kind": kind, "title": title, "group": group, "text": text,
        "summary": summary, "effects": dict(effects or {}),
    }


def _specific_reactions(s, previous, draft):
    """Translate material Budget choices into concrete stakeholder developments."""
    old_spend = previous.get("spend", {}) or {}
    spend = draft.get("spend", {}) or {}
    old_tax = previous.get("tax", {}) or {}
    tax = draft.get("tax", {}) or {}
    old_policies = previous.get("spend_pol", {}) or {}
    policies = draft.get("spend_pol", {}) or {}
    events = []

    pay_rate = _number(spend, "public_sector_pay")
    health_rate = _number(spend, "health")
    if pay_rate <= -1.0:
        events.append(_event(
            "industrial_action_risk", "Public-sector unions warn over pay restraint",
            "Public-sector workforce",
            f"With the public-sector pay settlement running at {pay_rate:+.1f}% a year, union leaders warn that real-terms pressure could trigger fresh NHS and wider public-service pay disputes. They are consulting members before deciding whether to escalate.",
            "Industrial action risk · Pay restraint",
            {"household_confidence": -0.25, "officials_confidence": -0.05},
        ))
    elif pay_rate >= 1.5:
        events.append(_event(
            "pay_settlement_welcome", "Unions cautiously welcome the pay settlement",
            "Public-sector workforce",
            f"The {pay_rate:+.1f}% annual public-sector pay allocation gives unions grounds to pause immediate escalation, although they warn that recruitment, retention and inflation will determine whether the settlement is sufficient.",
            "Pay settlement · Workforce relations",
            {"household_confidence": 0.15},
        ))

    if health_rate <= -1.0:
        events.append(_event(
            "nhs_delivery_pressure", "NHS leaders warn that waiting-list targets are at risk",
            "NHS and health",
            f"The NHS budget line is set to change by {health_rate:+.1f}% a year. Trust leaders warn that productivity savings may not fully offset the pressure on staffing, diagnostics and elective capacity.",
            "NHS delivery · Waiting-list pressure",
            {"household_confidence": -0.12, "officials_confidence": -0.08},
        ))
    elif health_rate >= 1.5:
        events.append(_event(
            "nhs_capacity_plan", "NHS leaders prepare a capacity expansion",
            "NHS and health",
            f"The {health_rate:+.1f}% annual NHS funding increase gives trusts scope to plan additional capacity, but workforce shortages and procurement delays could limit how quickly waiting lists fall.",
            "NHS delivery · Capacity expansion",
            {"household_confidence": 0.12},
        ))

    corp_change = _number(tax, "corp") - _number(old_tax, "corp", 25.0)
    business_rates_change = _number(tax, "business_rates") - _number(old_tax, "business_rates", 50.0)
    if corp_change >= 1.0 or business_rates_change >= 0.5:
        events.append(_event(
            "business_tax_review", "Businesses review investment plans after tax changes",
            "Business",
            f"Corporation tax has changed by {corp_change:+.1f} percentage points and business rates by {business_rates_change:+.1f} in the model's rate units. Business groups say firms will reassess hiring, location and investment decisions before committing to new projects.",
            "Business response · Tax competitiveness",
            {"business_confidence": -0.25},
        ))
    elif corp_change <= -1.0 or business_rates_change <= -0.5:
        events.append(_event(
            "business_tax_incentive", "Business groups welcome a lower tax burden",
            "Business",
            f"The Budget reduces corporation tax by {abs(corp_change):.1f} percentage points and business rates by {abs(business_rates_change):.1f} in the model's rate units. Business groups welcome the change but say investment will depend on demand and policy stability.",
            "Business response · Investment incentives",
            {"business_confidence": 0.18},
        ))

    investment_labels = {
        "hs2": "major rail infrastructure", "nuclear": "new nuclear capacity",
        "grid_upgrade": "electricity-grid upgrades", "grid_storage": "grid-scale storage",
        "regional_growth": "regional growth projects", "small_business_fund": "small-business finance",
        "defence_industry": "domestic defence production", "technical_skills": "technical skills and apprenticeships",
        "school_rebuild": "school rebuilding", "nhs_diagnostics": "diagnostic capacity",
        "social_housing": "social housing", "roads_upgrade": "road upgrades",
        "planning_deregulation": "planning reform",
    }
    newly_selected = [
        (key, label) for key, label in investment_labels.items()
        if bool(policies.get(key, False)) and not bool(old_policies.get(key, False))
    ]
    if newly_selected:
        labels = [label for _, label in newly_selected[:3]]
        joined = ", ".join(labels)
        events.append(_event(
            "investment_commitment", "New investment programmes move into delivery planning",
            "Business and infrastructure",
            f"The Budget launches {joined}. Suppliers and investors welcome the pipeline, while warning that planning approvals, skilled labour and procurement capacity will determine how quickly projects become real investment.",
            "Investment response · New project pipeline",
            {"business_confidence": min(0.35, 0.12 * len(newly_selected))},
        ))

    household_tax_changes = []
    for key, label, weight in (
        ("income", "basic-rate income tax", 1.0),
        ("ni", "National Insurance", 0.8),
        ("vat", "VAT", 0.8),
        ("fuel", "fuel duty", 0.025),
        ("council_tax", "council tax", 0.002),
        ("sugar_duty", "sugary-drinks duty", 0.03),
    ):
        change = _number(tax, key) - _number(old_tax, key, _number(tax, key))
        if change > 0.01:
            household_tax_changes.append((label, change * weight))
    household_pressure = sum(value for _, value in household_tax_changes)
    if household_pressure >= 0.8:
        labels = ", ".join(label for label, _ in household_tax_changes[:3])
        events.append(_event(
            "household_tax_squeeze", "Household budgets face a higher tax bill",
            "Households",
            f"Changes to {labels} are expected to squeeze disposable incomes. Consumer groups warn that households may cut non-essential spending if wages do not keep pace with prices.",
            "Cost of living · Household tax pressure",
            {"household_confidence": -min(0.4, 0.12 * household_pressure)},
        ))

    service_lines = {
        "health": "health", "education": "education", "transport": "transport",
        "justice": "justice", "defence": "defence", "social_care": "social_care",
        "local_government": "local_government", "skills": "skills",
    }
    cuts = [(key, _number(spend, key)) for key in service_lines if _number(spend, key) <= -1.5]
    if cuts:
        department, rate = min(cuts, key=lambda item: item[1])
        ministers = s.get("cabinet_ministers", {}) or {}
        minister = ministers.get(department, "The relevant Secretary of State")
        labels = {
            "health": "NHS capacity", "education": "school standards and teacher retention",
            "transport": "rail reliability and infrastructure maintenance",
            "justice": "court backlogs and prison capacity", "defence": "readiness and equipment",
            "social_care": "adult social-care capacity",
            "local_government": "council services and financial resilience",
            "skills": "apprenticeships and technical training",
        }
        priority = labels.get(department, "frontline delivery")
        events.append(_event(
            "ministerial_warning", f"{minister} raises concerns about the settlement",
            "Cabinet",
            f"The {department.replace('_', ' ')} budget is set to change by {rate:+.1f}% a year. {minister} warns privately that {priority} may be put at risk and asks the Treasury to review delivery milestones during the year.",
            "Cabinet reaction · Departmental pressure",
            {"officials_confidence": -0.12},
        ))

    return events


def create(s, previous, draft, impact, event_type="Spring Budget"):
    """Queue one second-round response after a Budget has passed the Commons."""
    s.setdefault("budget_aftermath_pending", [])
    s.setdefault("budget_aftermath_created", [])
    s.setdefault("budget_aftermath_history", [])
    period = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    event_key = str(event_type).strip().lower().replace(" ", "-")
    record_id = f"{period}:{event_key}"
    if record_id in s.budget_aftermath_created:
        return None

    market = float(impact.get("market", 0.0))
    growth = float(impact.get("growth", 0.0))
    approval = float(impact.get("approval", 0.0))
    real_wages = float(impact.get("real_wages", 0.0))
    headroom = float(impact.get("headroom", 0.0))
    effects = {
        "business_confidence": round(_clip(market * 0.22 + growth * 2.0, -2.0, 2.0), 2),
        "household_confidence": round(_clip(approval * 0.12 + real_wages * 1.8, -2.0, 2.0), 2),
        "officials_confidence": round(_clip(headroom * 0.10, -1.5, 1.5), 2),
    }
    specific = _specific_reactions(s, previous or {}, draft or {})
    for event in specific:
        for key, amount in event.get("effects", {}).items():
            effects[key] = round(_clip(effects.get(key, 0.0) + float(amount), -2.0, 2.0), 2)

    reactions = []
    business = effects["business_confidence"]
    household = effects["household_confidence"]
    officials = effects["officials_confidence"]
    reactions.append({
        "group": "Business",
        "text": ("Firms see a modest improvement in the investment climate and are more willing to plan ahead."
                 if business >= 0.35 else "Businesses remain cautious; investment plans are likely to be reviewed against the Budget's tax and growth outlook."
                 if business <= -0.35 else "Business groups are taking a wait-and-see approach while firms assess the new fiscal settlement."),
    })
    reactions.append({
        "group": "Households",
        "text": ("Household confidence receives a small boost as the package is assessed for its effect on incomes and living costs."
                 if household >= 0.35 else "Households are wary of the effect on take-home pay and prices."
                 if household <= -0.35 else "Households are reserving judgement until the changes begin to affect pay packets and bills."),
    })
    reactions.append({
        "group": "Treasury officials",
        "text": ("Officials are more confident that the fiscal plan is deliverable and can be defended in the next forecast."
                 if officials >= 0.25 else "Officials are concerned that the fiscal plan leaves little room for forecast errors."
                 if officials <= -0.25 else "Officials are monitoring delivery risks and the scope for slippage against the fiscal plan."),
    })
    reactions.extend({"group": item["group"], "text": item["text"], "kind": item["kind"]} for item in specific)

    headline = (f"{event_type}: {len(specific)} specific stakeholder development(s) are being monitored."
                if specific else f"{event_type}: second-round reactions are now being monitored.")
    record = {
        "id": record_id, "period": period, "event_type": str(event_type),
        "headline": headline, "reactions": reactions, "specific_events": specific,
        "effects": effects,
        "impact_signals": {"market": round(market, 3), "growth": round(growth, 3),
                           "approval": round(approval, 3), "real_wages": round(real_wages, 3),
                           "headroom": round(headroom, 3)},
        "status": "Awaiting next Spring",
    }
    pending = list(s.get("budget_aftermath_pending", []))
    pending.append(record)
    s.budget_aftermath_pending = pending[-8:]
    s.budget_aftermath_created = (list(s.budget_aftermath_created) + [record_id])[-32:]
    s.budget_aftermath_latest = record
    return record


def advance(s=None):
    """Apply queued confidence responses once at the next Spring transition."""
    if s is None:
        import streamlit as st
        s = st.session_state
    pending = list(s.get("budget_aftermath_pending", []))
    if not pending:
        return []
    applied_ids = set(s.get("budget_aftermath_applied", []))
    history = list(s.get("budget_aftermath_history", []))
    cards = list(s.get("event_cards", []))
    applied = []
    for item in pending:
        record_id = str(item.get("id", ""))
        if not record_id or record_id in applied_ids:
            continue
        effects = item.get("effects", {})
        for key in ("business_confidence", "household_confidence", "officials_confidence"):
            current = float(s.get(key, 50.0))
            s[key] = round(_clip(current + float(effects.get(key, 0.0))), 1)
        completed = dict(item)
        completed["status"] = "Applied at Spring"
        completed["applied_period"] = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
        history.append(completed)
        applied_ids.add(record_id)
        applied.append(completed)
        cards.append({
            "title": "Budget aftermath · second-round reactions",
            "text": "The delayed response to the Budget is now feeding into business, household and Treasury confidence. No tax, spending or debt figures have been applied again.",
            "summary": "Business {:+.1f} · Households {:+.1f} · Officials {:+.1f}".format(
                float(effects.get("business_confidence", 0.0)),
                float(effects.get("household_confidence", 0.0)),
                float(effects.get("officials_confidence", 0.0))),
        })
        for development in item.get("specific_events", []):
            cards.append({
                "title": development.get("title", "Budget stakeholder reaction"),
                "text": development.get("text", ""),
                "summary": development.get("summary", development.get("group", "Budget aftermath")),
            })
    s.budget_aftermath_pending = []
    s.budget_aftermath_applied = list(applied_ids)[-32:]
    s.budget_aftermath_history = history[-24:]
    s.event_cards = cards[-30:]
    if applied:
        s.budget_aftermath_latest = applied[-1]
        s.message = str(s.get("message", "")) + " The previous Budget's second-round stakeholder reactions have now been incorporated."
    return applied
