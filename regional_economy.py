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
    for values in s.regional_economies.values():
        values.setdefault("project_jobs_supported", 0)
    if "regional_history" not in s:
        s.regional_history = []
    if "regional_last_year" not in s:
        s.regional_last_year = ""
    if "regional_policy_period" not in s:
        s.regional_policy_period = 0
    if "regional_policy_history" not in s:
        s.regional_policy_history = []
    if "regional_strategy_active" not in s:
        s.regional_strategy_active = False
    if "regional_strategy_regions" not in s:
        s.regional_strategy_regions = []
    if "regional_strategy_baseline_gap" not in s:
        s.regional_strategy_baseline_gap = 0.0
    if "regional_strategy_target_reduction" not in s:
        s.regional_strategy_target_reduction = 0.20
    if "regional_strategy_start_ordinal" not in s:
        s.regional_strategy_start_ordinal = 0
    if "regional_strategy_start_label" not in s:
        s.regional_strategy_start_label = ""
    if "regional_strategy_history" not in s:
        s.regional_strategy_history = []
    return s


def _clip(value, low, high):
    return round(max(low, min(high, float(value))), 2)


def _period_ordinal(s):
    return (max(1, int(s.get("term", 1))) - 1) * 5 + (max(1, int(s.get("year", 1))) - 1)


def inequality_gap(s=None, regions=None):
    """Return the productivity-index gap between priority places and the rest."""
    s = ensure(s)
    data = s.get("regional_economies", {})
    selected = [name for name in (regions if regions is not None else s.get("regional_strategy_regions", []))
                if name in data]
    comparison = [name for name in data if name not in selected]
    if not selected or not comparison:
        return 0.0
    priority_average = sum(float(data[name].get("productivity", 100.0)) for name in selected) / len(selected)
    rest_average = sum(float(data[name].get("productivity", 100.0)) for name in comparison) / len(comparison)
    return round(max(0.0, rest_average - priority_average), 2)


def set_inequality_target(s, regions, target_reduction=0.20):
    """Adopt a five-year, measurable regional productivity-convergence target."""
    ensure(s)
    valid = list(dict.fromkeys(name for name in regions if name in s.regional_economies))
    if not valid or len(valid) > 6 or len(valid) == len(s.regional_economies):
        return False
    gap = inequality_gap(s, valid)
    if gap <= 0:
        return False
    reduction = _clip(target_reduction, 0.05, 0.40)
    s.regional_strategy_active = True
    s.regional_strategy_regions = valid
    s.regional_strategy_baseline_gap = gap
    s.regional_strategy_target_reduction = reduction
    s.regional_strategy_start_ordinal = _period_ordinal(s)
    s.regional_strategy_start_label = f"Term {s.get('term', 1)}, Year {s.get('year', 1)}"
    s.regional_strategy_history = [{
        "Year": s.regional_strategy_start_label,
        "Priority productivity gap": gap,
        "Gap narrowed": "0.0%",
        "Target": f"{reduction:.0%}",
        "Status": "Target adopted",
    }]
    state.log("regional_strategy", "Regional convergence target adopted",
              choice=", ".join(valid),
              note=f"Five-year target: narrow the productivity gap by {reduction:.0%}.")
    s.message = f"Your five-year regional strategy is set. The productivity gap is {gap:.1f} index points; the target is to narrow it by {reduction:.0%}."
    return True


def strategy_snapshot(s=None):
    s = ensure(s)
    if not s.get("regional_strategy_active"):
        return None
    baseline = float(s.get("regional_strategy_baseline_gap", 0.0))
    current = inequality_gap(s)
    narrowed = max(0.0, baseline - current)
    progress = (narrowed / baseline * 100.0) if baseline > 0 else 0.0
    target = float(s.get("regional_strategy_target_reduction", 0.20)) * 100.0
    elapsed = max(0, _period_ordinal(s) - int(s.get("regional_strategy_start_ordinal", 0)))
    return {
        "baseline_gap": round(baseline, 2),
        "current_gap": round(current, 2),
        "narrowed_points": round(narrowed, 2),
        "progress_percent": round(progress, 1),
        "target_percent": round(target, 1),
        "elapsed_years": min(5, elapsed),
        "remaining_years": max(0, 5 - elapsed),
        "achieved": progress >= target,
        "regions": list(s.get("regional_strategy_regions", [])),
    }


def strategy_in_force(s=None):
    """Whether the five-year target is still active and has not already been met."""
    snapshot = strategy_snapshot(s)
    return bool(snapshot and snapshot["remaining_years"] > 0 and not snapshot["achieved"])


def _record_strategy_year(s, period):
    snapshot = strategy_snapshot(s)
    if not snapshot:
        return
    history = list(s.get("regional_strategy_history", []))
    if history and history[-1].get("Year") == period:
        return
    target = snapshot["target_percent"]
    history.append({
        "Year": period,
        "Priority productivity gap": snapshot["current_gap"],
        "Gap narrowed": f"{snapshot['progress_percent']:.1f}%",
        "Target": f"{target:.0f}%",
        "Status": "Achieved" if snapshot["achieved"] else
                  ("Five-year period ended" if snapshot["remaining_years"] == 0 else "In progress"),
    })
    s.regional_strategy_history = history[-20:]


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
    _record_strategy_year(s, period)
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
            "Project jobs supported": int(values.get("project_jobs_supported", 0)),
        })
    st.markdown("### Regional economies")
    st.caption("Illustrative regional indices, not official ONS data. 100 is the approximate national starting benchmark for wages, jobs and productivity. National projects now feed into the selected regions as work is delivered.")
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

    st.markdown("#### Five-year regional convergence strategy")
    st.caption("Set a measurable target to narrow the productivity gap between selected lower-productivity regions and the rest of the UK. This is a strategic objective, not an unfunded spending commitment.")
    snapshot = strategy_snapshot(s)
    if snapshot:
        st.markdown("**Active strategy** · " + ", ".join(snapshot["regions"]))
        c1, c2, c3 = st.columns(3)
        c1.metric("Productivity gap", f"{snapshot['current_gap']:.1f} points",
                  f"{snapshot['narrowed_points']:+.1f} vs baseline")
        c2.metric("Gap narrowed", f"{snapshot['progress_percent']:.1f}%",
                  f"Target {snapshot['target_percent']:.0f}%")
        c3.metric("Time remaining", f"{snapshot['remaining_years']} years",
                  "Five-year strategy")
        st.progress(min(1.0, snapshot["progress_percent"] / max(1.0, snapshot["target_percent"])))
        if snapshot["achieved"]:
            st.success("Your regional convergence target has been achieved.")
        elif snapshot["remaining_years"] == 0:
            st.warning("The five-year strategy period has ended. Review the results before adopting a new target.")
        else:
            st.info("National investment projects in these regions receive a modest additional regional-impact weighting.")
        with st.expander("Regional convergence scorecard", expanded=False):
            if s.get("regional_strategy_history"):
                st.dataframe(list(reversed(s.regional_strategy_history)), hide_index=True, use_container_width=True)
    else:
        available = sorted(s.regional_economies, key=lambda name: s.regional_economies[name]["productivity"])[:6]
        selected = st.multiselect(
            "Priority regions (up to six)",
            options=available,
            default=available[:4],
            key="regional_strategy_region_picker",
            help="The list is limited to the six regions with the lowest current productivity indices."
        )
        ambition = st.selectbox(
            "Five-year productivity-gap reduction",
            options=[0.10, 0.20, 0.30],
            index=1,
            format_func=lambda value: {0.10: "Modest · 10%", 0.20: "Ambitious · 20%", 0.30: "Stretch · 30%"}[value],
            key="regional_strategy_ambition"
        )
        if st.button("Adopt five-year regional target", type="primary",
                     disabled=not selected, use_container_width=True):
            if set_inequality_target(s, selected, ambition):
                st.rerun()
            else:
                st.warning("Choose at least one lower-productivity region with a measurable gap.")
        st.caption("The target measures the difference between the selected regions' average productivity index and the average across all other regions. It does not automatically change taxes, departmental settlements or approved Budget ledgers.")

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
