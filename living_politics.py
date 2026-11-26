"""Living Britain Phase 2: a persistent political climate across Cabinet factions.

This layer builds on the existing ministerial, Commons and public-opinion systems.
It does not replace their decisions; it records the accumulated mood of factions
and makes that mood relevant to future ministerial dissent.
"""
import streamlit as st


FACTION_LABELS = (
    "Government Mainstream", "Reformist", "Traditionalist", "Soft Left",
    "Socialist Left", "Economic Liberal", "Regional Voices",
)


def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def ensure(s=None):
    if s is None:
        s = st.session_state
    s.setdefault("political_climate", {})
    s.setdefault("political_climate_history", [])
    s.setdefault("political_climate_last_year", "")
    s.setdefault("political_climate_action_period", "")
    s.setdefault("political_climate_action_history", [])
    # Match the existing engine resource default so old saves can use this action
    # before their next annual update.
    s.setdefault("political_capital_points", 5)
    return s


def faction_mood(s, faction):
    ensure(s)
    climate = s.get("political_climate", {})
    row = climate.get(str(faction), {})
    return _clip(row.get("mood", 55.0))


def annual_review(s=None):
    """Record one annual faction review; safe across Streamlit reruns and old saves."""
    if s is None:
        s = st.session_state
    ensure(s)
    period = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    if s.get("political_climate_last_year") == period:
        return s.get("political_climate", {})
    import cabinet_management

    loyalty = s.get("ministerial_loyalty", {})
    competence = s.get("ministerial_competence", {})
    grouped = {}
    for department, minister in s.get("cabinet_ministers", {}).items():
        if not minister or str(minister).startswith(("Vacant", "New appointment")):
            continue
        profile = cabinet_management.profile_for(s, department)
        faction = str(profile.get("faction", "Government Mainstream"))
        grouped.setdefault(faction, []).append((
            float(loyalty.get(department, 60.0)),
            float(competence.get(department, 60.0)),
        ))

    previous = dict(s.get("political_climate", {}))
    climate = {}
    approval = _clip(s.get("approval", 50.0))
    party_unity = _clip(s.get("party_opinion", 60.0))
    backbench = _clip(s.get("backbench_opinion", 60.0))
    cabinet_support = _clip(s.get("cab_opinion", 60.0))
    media = _clip(s.get("media_opinion", 50.0))
    growth = float(s.get("growth", 0.0))
    inflation = float(s.get("inflation", 2.0))
    unemployment = float((s.get("country") or {}).get("unemployment", 4.5))
    for faction in FACTION_LABELS:
        members = grouped.get(faction, [])
        if members:
            ministerial = sum((loy + skill) / 2.0 for loy, skill in members) / len(members)
        else:
            ministerial = 55.0
        # The broad political climate is a pressure indicator, not another approval score.
        economic_mood = _clip(55.0 + growth * 3.0 - max(0.0, inflation - 2.0) * 2.0
                              - max(0.0, unemployment - 4.5) * 1.4)
        base = (0.24 * party_unity + 0.18 * backbench + 0.16 * cabinet_support
                + 0.14 * approval + 0.10 * media + 0.10 * ministerial
                + 0.08 * economic_mood)
        old = previous.get(faction, {})
        old_mood = _clip(old.get("mood", base))
        mood = _clip(old_mood * 0.35 + base * 0.65)
        climate[faction] = {
            "mood": round(mood, 1),
            "ministerial_strength": round(_clip(ministerial), 1),
            "members": len(members),
            "trend": round(mood - old_mood, 1),
        }

    s.political_climate = climate
    s.political_climate_last_year = period
    history = list(s.get("political_climate_history", []))
    history.append({"period": period, "approval": round(approval, 1),
                    "party_unity": round(party_unity, 1),
                    "backbench_morale": round(backbench, 1),
                    "factions": {key: dict(value) for key, value in climate.items()}})
    s.political_climate_history = history[-20:]
    return climate



def hold_faction_meeting(s, faction):
    """Spend political capital on one annual listening meeting with a party faction."""
    ensure(s)
    period = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    if s.get("political_climate_action_period") == period:
        return False, "You have already held a faction meeting this year."
    capital = int(s.get("political_capital_points", 0))
    if capital < 1:
        return False, "You need at least one political capital point to arrange a faction meeting."
    climate = dict(s.get("political_climate", {}))
    if faction not in climate:
        return False, "That faction is not currently recorded in the political climate."
    row = dict(climate[faction])
    before = _clip(row.get("mood", 55.0))
    row["mood"] = round(_clip(before + 5.0), 1)
    row["trend"] = round(float(row.get("trend", 0.0)) + 5.0, 1)
    climate[faction] = row
    s.political_climate = climate
    s.political_capital_points = capital - 1
    s.political_climate_action_period = period
    s.backbench_opinion = round(_clip(float(s.get("backbench_opinion", 60.0)) + 1.0), 1)
    s.party_opinion = round(_clip(float(s.get("party_opinion", 60.0)) + 0.5), 1)
    history = list(s.get("political_climate_action_history", []))
    history.append({"period": period, "faction": faction, "action": "Listening meeting",
                    "mood_change": round(float(row["mood"]) - before, 1)})
    s.political_climate_action_history = history[-30:]
    return True, f"Listening meeting held with {faction}. Faction mood improved by {row['mood'] - before:.1f} points."



def budget_risk_faction(message):
    """Map common Budget flashpoints to the party faction most likely to lead resistance."""
    text = str(message).lower()
    if any(term in text for term in ("welfare", "disabled", "poverty", "trade-union")):
        return "Socialist Left"
    if any(term in text for term in ("climate", "green activists", "environment")):
        return "Soft Left"
    if any(term in text for term in ("inheritance", "fuel duty", "rural", "shires")):
        return "Traditionalist"
    if any(term in text for term in ("corporation tax", "business", "market", "enterprise")):
        return "Economic Liberal"
    if any(term in text for term in ("devolved", "regional", "assembly", "block grants")):
        return "Regional Voices"
    if any(term in text for term in ("foreign aid", "overseas aid", "international")):
        return "Reformist"
    return "Government Mainstream"


def budget_risk_multiplier(s, message):
    """Translate the linked faction's mood into a modest Budget rebellion modifier."""
    faction = budget_risk_faction(message)
    climate = s.get("political_climate", {}) or {}
    if faction not in climate:
        return faction, 1.0
    mood = _clip(climate[faction].get("mood", 55.0))
    # A discontented faction is harder to contain; a content faction is more willing
    # to tolerate a difficult Budget. Keep the modifier bounded and secondary.
    multiplier = _clip(1.0 + (55.0 - mood) * 0.006, 0.75, 1.30)
    return faction, round(multiplier, 3)


def render(s=None):
    if s is None:
        s = st.session_state
    ensure(s)
    st.markdown("#### Political climate")
    st.caption("An annual reading of internal party factions, combining ministerial reliability, party unity, backbench morale and the wider national mood.")
    climate = s.get("political_climate", {})
    if not climate:
        st.info("The first political-climate review will be recorded at the next annual update.")
        return
    rows = []
    for faction, data in sorted(climate.items(), key=lambda item: float(item[1].get("mood", 0)), reverse=True):
        mood = float(data.get("mood", 50.0))
        status = "Content" if mood >= 65 else "Restless" if mood < 45 else "Manageable"
        rows.append({"Faction": faction, "Mood": f"{mood:.0f}/100", "Position": status,
                     "Ministers": int(data.get("members", 0)),
                     "Ministerial strength": f"{float(data.get('ministerial_strength', 0)):.0f}/100",
                     "Annual change": f"{float(data.get('trend', 0)):+.1f}"})
    st.dataframe(rows, hide_index=True, use_container_width=True)
    weakest = min(climate.items(), key=lambda item: float(item[1].get("mood", 50.0)))
    st.caption(f"Faction requiring most attention: {weakest[0]} ({float(weakest[1].get('mood', 50.0)):.0f}/100). This is an advisory indicator, not an automatic rebellion.")
    st.markdown("#### Manage party relationships")
    st.caption("You can spend one political capital point each year to hold a listening meeting with one faction. It improves that faction's mood and slightly strengthens party unity.")
    period = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    capital = int(s.get("political_capital_points", 0))
    used = s.get("political_climate_action_period") == period
    st.write(f"Political capital available: **{capital}**")
    choices = sorted(climate, key=lambda key: float(climate[key].get("mood", 50.0)))
    for faction in choices:
        mood = float(climate[faction].get("mood", 50.0))
        label = f"Hold listening meeting with {faction} ({mood:.0f}/100)"
        if st.button(label, key=f"living_politics_meeting_{faction.lower().replace(' ', '_')}",
                     disabled=used or capital < 1, use_container_width=True):
            ok, message = hold_faction_meeting(s, faction)
            if ok:
                st.success(message)
            else:
                st.warning(message)
            st.rerun()
    action_history = list(s.get("political_climate_action_history", []))
    if action_history:
        st.markdown("#### Recent party-management actions")
        recent = []
        for item in reversed(action_history[-5:]):
            recent.append({
                "Period": f"Term {item.get('period', '?').split(':')[0]}, Year {item.get('period', '?').split(':')[-1]}",
                "Action": item.get("action", "Party-management action"),
                "Faction": item.get("faction", "Party"),
                "Mood change": f"{float(item.get('mood_change', 0.0)):+.1f}",
            })
        st.dataframe(recent, hide_index=True, use_container_width=True)
