"""Regional economies and place-based Treasury policy.

All regional figures are illustrative gameplay indices, not official regional
statistics. They are designed to create persistent differences and policy trade-offs.
"""
import streamlit as st
import pandas as pd

import state


REGION_START = {
    "North East":       {"growth": 0.6, "wages": 98.0, "jobs": 91.0, "productivity": 88.0, "investment": 42.0, "unemployment": 5.2},
    "North West":       {"growth": 0.9, "wages": 99.0, "jobs": 94.0, "productivity": 94.0, "investment": 48.0, "unemployment": 4.7},
    "Yorkshire & Humber":{"growth": 0.7, "wages": 98.0, "jobs": 92.0, "productivity": 91.0, "investment": 44.0, "unemployment": 4.9},
    "East Midlands":    {"growth": 0.8, "wages": 99.0, "jobs": 94.0, "productivity": 94.0, "investment": 46.0, "unemployment": 4.5},
    "West Midlands":    {"growth": 0.7, "wages": 98.0, "jobs": 92.0, "productivity": 96.0, "investment": 47.0, "unemployment": 5.0},
    "East of England":  {"growth": 1.1, "wages": 103.0, "jobs": 101.0, "productivity": 105.0, "investment": 53.0, "unemployment": 3.8},
    "London":           {"growth": 1.4, "wages": 119.0, "jobs": 111.0, "productivity": 132.0, "investment": 70.0, "unemployment": 4.4},
    "South East":       {"growth": 1.1, "wages": 109.0, "jobs": 105.0, "productivity": 112.0, "investment": 61.0, "unemployment": 3.9},
    "South West":       {"growth": 0.9, "wages": 102.0, "jobs": 99.0, "productivity": 101.0, "investment": 49.0, "unemployment": 4.0},
    "Wales":            {"growth": 0.6, "wages": 96.0, "jobs": 90.0, "productivity": 88.0, "investment": 41.0, "unemployment": 5.1},
    "Scotland":         {"growth": 0.8, "wages": 101.0, "jobs": 96.0, "productivity": 100.0, "investment": 50.0, "unemployment": 4.3},
    "Northern Ireland": {"growth": 0.9, "wages": 95.0, "jobs": 91.0, "productivity": 86.0, "investment": 39.0, "unemployment": 4.6},
}

PROGRAMMES = {
    "north": {
        "title": "Northern Growth & Transport Fund",
        "cost": 5.0,
        "regions": ["North East", "North West", "Yorkshire & Humber"],
        "description": "Rail, ports, skills and town-centre investment across the North.",
        "effects": {"growth": 0.35, "productivity": 2.2, "investment": 9.0, "jobs": 1.8, "unemployment": -0.25},
    },
    "midlands": {
        "title": "Midlands Manufacturing & Skills Deal",
        "cost": 4.0,
        "regions": ["East Midlands", "West Midlands"],
        "description": "Advanced manufacturing, apprenticeships and industrial energy infrastructure.",
        "effects": {"growth": 0.3, "productivity": 2.8, "investment": 8.0, "jobs": 1.5, "unemployment": -0.2},
    },
    "devolved": {
        "title": "Devolved Nations Investment Compact",
        "cost": 4.5,
        "regions": ["Wales", "Scotland", "Northern Ireland"],
        "description": "A negotiated capital package for transport, ports, skills and local economic development.",
        "effects": {"growth": 0.3, "productivity": 2.5, "investment": 8.5, "jobs": 1.5, "unemployment": -0.2},
    },
    "southwest": {
        "title": "South West Connectivity & Clean Energy",
        "cost": 3.5,
        "regions": ["South West"],
        "description": "Rail connectivity, coastal resilience, clean energy and high-skill jobs.",
        "effects": {"growth": 0.35, "productivity": 2.4, "investment": 8.0, "jobs": 1.4, "unemployment": -0.2},
    },
    "national": {
        "title": "National Productivity & Skills Mission",
        "cost": 6.0,
        "regions": list(REGION_START),
        "description": "A country-wide technical skills and business investment programme, with larger gains in lower-productivity areas.",
        "effects": {"growth": 0.18, "productivity": 1.8, "investment": 4.0, "jobs": 1.0, "unemployment": -0.12},
    },
}


def ensure(s=None):
    s = s or st.session_state
    if "regional_economies" not in s or not s.regional_economies:
        s.regional_economies = {name: dict(values) for name, values in REGION_START.items()}
    if "regional_history" not in s:
        s.regional_history = []
    if "regional_last_year" not in s:
        s.regional_last_year = ""
    if "regional_policy_period" not in s:
        s.regional_policy_period = 0
    if "regional_policy_history" not in s:
        s.regional_policy_history = []
    return s


def _clip(value, low, high):
    return round(max(low, min(high, float(value))), 2)


def advance(s=None):
    """Advance each regional economy once per in-game year."""
    s = ensure(s)
    period = f"Term {int(s.get('term', 1))}, Year {int(s.get('year', 1))}"
    if s.get("regional_last_year") == period:
        return
    national_growth = float(s.get("growth", 0.8))
    c = s.get("country") or {}
    wage_growth = float(c.get("real_wages", 0.6))
    national_unemployment = float(c.get("unemployment", 4.3))
    regions = {name: dict(values) for name, values in s.regional_economies.items()}
    for name, row in regions.items():
        productivity_gap = max(-1.5, min(1.5, (100.0 - row["productivity"]) / 30.0))
        regional_growth = national_growth + (row["productivity"] - 100.0) * 0.012 + productivity_gap * 0.12
        row["growth"] = _clip(regional_growth, -4.0, 5.0)
        row["wages"] = _clip(row["wages"] + wage_growth * 0.55 + (row["productivity"] - 100.0) * 0.004, 75, 140)
        row["jobs"] = _clip(row["jobs"] + (4.5 - row["unemployment"]) * 0.12 + (row["growth"] - 0.8) * 0.18, 70, 130)
        row["productivity"] = _clip(row["productivity"] + (row["investment"] - 50.0) * 0.018 + 0.12, 70, 145)
        row["investment"] = _clip(row["investment"] + (national_growth - 0.8) * 0.35, 20, 100)
        row["unemployment"] = _clip(row["unemployment"] + (national_unemployment - row["unemployment"]) * 0.16 - (row["growth"] - 0.8) * 0.08, 2.5, 12)
    s.regional_economies = regions
    s.regional_last_year = period
    history = list(s.get("regional_history", []))
    history.append({
        "Year": period,
        **{name: round(row["growth"], 2) for name, row in regions.items()},
    })
    s.regional_history = history[-20:]


def apply_programme(key):
    s = ensure()
    programme = PROGRAMMES.get(key)
    period = int(s.get("term", 1)) * 10 + int(s.get("year", 1))
    if not programme or int(s.get("regional_policy_period", 0)) >= period:
        return False
    cost = float(programme["cost"])
    if float(s.get("headroom", 0.0)) < cost:
        return False
    state.checkpoint()
    state.snapshot()
    s.headroom = round(float(s.get("headroom", 0.0)) - cost, 1)
    s.deficit = round(float(s.get("deficit", 0.0)) + cost, 1)
    regions = {name: dict(values) for name, values in s.regional_economies.items()}
    for name in programme["regions"]:
        row = regions[name]
        effects = programme["effects"]
        multiplier = 1.0 + max(0.0, (100.0 - row["productivity"]) / 100.0) * 0.45
        for metric in ("productivity", "investment", "jobs"):
            row[metric] = _clip(row[metric] + effects[metric] * multiplier, 2, 150)
        row["growth"] = _clip(row["growth"] + effects["growth"] * multiplier, -4, 5)
        row["unemployment"] = _clip(row["unemployment"] + effects["unemployment"] * multiplier, 2.5, 12)
    s.regional_economies = regions
    s.regional_policy_period = period
    entry = {"Year": f"Term {s.get('term', 1)}, Year {s.get('year', 1)}",
             "Programme": programme["title"], "Cost (£bn)": cost,
             "Areas": ", ".join(programme["regions"])}
    s.regional_policy_history = (list(s.get("regional_policy_history", [])) + [entry])[-20:]
    s.approval = _clip(float(s.get("approval", 50.0)) + 0.7, 0, 100)
    s.message = f"{programme['title']} announced. The £{cost:.1f}bn package is now committed; regional benefits will build over time."
    state.log("regional_investment", "Regional investment programme", choice=programme["title"], note=s.message)
    return True


def render():
    s = ensure()
    advance(s)
    rows = []
    for name, values in s.regional_economies.items():
        rows.append({
            "Region": name,
            "Growth": f"{values['growth']:+.2f}%",
            "Wage index": round(values["wages"], 1),
            "Jobs index": round(values["jobs"], 1),
            "Productivity": round(values["productivity"], 1),
            "Investment": round(values["investment"], 1),
            "Unemployment": f"{values['unemployment']:.1f}%",
        })
    st.markdown("### Regional economies")
    st.caption("Illustrative regional indices, not official ONS data. 100 is the approximate national starting benchmark for wages, jobs and productivity.")
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)
    weakest = min(s.regional_economies.items(), key=lambda item: item[1]["productivity"])
    strongest = max(s.regional_economies.items(), key=lambda item: item[1]["productivity"])
    left, right = st.columns(2)
    left.metric("Lowest productivity", weakest[0], f"{weakest[1]['productivity']:.1f} index")
    right.metric("Highest productivity", strongest[0], f"{strongest[1]['productivity']:.1f} index")
    if s.get("regional_history"):
        with st.expander("Regional growth history"):
            st.dataframe(list(reversed(s.regional_history)), hide_index=True, use_container_width=True)

    st.markdown("#### Place-based Treasury programmes")
    current_period = int(s.get("term", 1)) * 10 + int(s.get("year", 1))
    if int(s.get("regional_policy_period", 0)) >= current_period:
        st.info("You have already announced one regional programme this year. Further programmes become available next year.")
    else:
        st.caption("Choose one programme per year. Investment is targeted, costs are deducted from fiscal headroom, and lower-productivity areas can receive a larger boost.")
        for key, programme in PROGRAMMES.items():
            with st.container(border=True):
                st.markdown(f"**{programme['title']} · £{programme['cost']:.1f}bn**")
                st.caption(programme["description"])
                st.caption("Coverage: " + ", ".join(programme["regions"]))
                affordable = float(s.get("headroom", 0.0)) >= float(programme["cost"])
                if st.button("Commit investment", key=f"regional_programme_{key}", disabled=not affordable, use_container_width=True):
                    apply_programme(key)
                    st.rerun()
        if float(s.get("headroom", 0.0)) < min(p["cost"] for p in PROGRAMMES.values()):
            st.warning("Your current fiscal headroom is too low to fund any of these packages. Improve the fiscal position before committing new spending.")
    if s.get("regional_policy_history"):
        with st.expander("Previous regional investment programmes"):
            st.dataframe(list(reversed(s.regional_policy_history)), hide_index=True, use_container_width=True)
