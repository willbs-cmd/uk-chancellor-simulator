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

    profiles = s.get("ministerial_profiles", {})
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
