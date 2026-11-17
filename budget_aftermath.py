"""Delayed stakeholder reactions to an enacted Budget.

Fiscal totals are calculated and applied by budget.py. This module deliberately
handles only second-round confidence effects so the Budget is never charged twice.
"""
def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


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
    headline = f"{event_type}: second-round reactions are now being monitored."
    record = {
        "id": record_id, "period": period, "event_type": str(event_type),
        "headline": headline, "reactions": reactions, "effects": effects,
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
    s.budget_aftermath_pending = []
    s.budget_aftermath_applied = list(applied_ids)[-32:]
    s.budget_aftermath_history = history[-24:]
    s.event_cards = cards[-30:]
    if applied:
        s.budget_aftermath_latest = applied[-1]
        s.message = str(s.get("message", "")) + " The previous Budget's second-round stakeholder reactions have now been incorporated."
    return applied
