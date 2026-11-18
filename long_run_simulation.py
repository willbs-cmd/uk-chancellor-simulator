"""Long-run structural pressures for the Chancellor Simulator.

The model links demographics, housing supply, energy security, climate resilience
and overseas trade into the annual economy. Values are gameplay estimates, not
official forecasts or population projections.
"""
import streamlit as st


POLICY_STOCK_KEYS = ("housing", "energy", "climate", "skills", "trade")


def ensure(s=None):
    s = s or st.session_state
    defaults = {
        "population_millions": 68.5,
        "working_age_share": 62.0,
        "dependency_ratio": 58.0,
        "net_migration_thousands": 170.0,
        "labour_supply_index": 100.0,
        "housing_supply_gap": 170.0,
        "housing_demand_thousands": 225.0,
        "energy_security": 62.0,
        "clean_energy_share": 38.0,
        "grid_capacity_index": 50.0,
        "energy_import_exposure": 55.0,
        "climate_resilience": 45.0,
        "trade_resilience": 50.0,
        "regional_inequality_index": 15.0,
        "long_run_policy_stock": {key: 0.0 for key in POLICY_STOCK_KEYS},
        "long_run_history": [],
        "long_run_last_year": "",
        "long_run_event_history": [],
        "long_run_last_event": None,
    }
    for key, value in defaults.items():
        if key not in s:
            s[key] = dict(value) if isinstance(value, dict) else list(value) if isinstance(value, list) else value
    stock = dict(s.get("long_run_policy_stock", {}))
    for key in POLICY_STOCK_KEYS:
        stock.setdefault(key, 0.0)
    s.long_run_policy_stock = stock
    return s


def _clip(value, low, high):
    return max(float(low), min(float(high), float(value)))


def _country_value(s, key, fallback):
    return float((s.get("country") or {}).get(key, fallback))


def _nudge_country(s, changes):
    country = dict(s.get("country") or {})
    try:
        import country as country_model
        for key, delta in changes.items():
            if key not in country_model.STATS:
                continue
            spec = country_model.STATS[key]
            country[key] = round(_clip(
                float(country.get(key, spec["start"])) + float(delta),
                spec["lo"], spec["hi"]
            ), int(spec.get("dec", 1)))
    except Exception:
        return
    s.country = country


def _world_average(s):
    world = s.get("world_economy") or {}
    values = [float(item.get("growth", 0.0)) for item in world.values() if isinstance(item, dict)]
    return sum(values) / len(values) if values else 1.5


def apply_event_choice(s, event_id, choice_index):
    """Turn a selected long-horizon event response into persistent policy capacity."""
    s = ensure(s)
    impacts = {
        "housing_supply_crunch": {
            0: {"housing": 13.0},
            1: {"housing": 8.0},
            2: {"housing": 2.0},
        },
        "grid_connection_bottleneck": {
            0: {"energy": 14.0},
            1: {"energy": 7.0},
            2: {"energy": -2.0},
        },
        "energy_grid_connections": {
            0: {"energy": 14.0},
            1: {"energy": 7.0},
            2: {"energy": -2.0},
        },
        "climate_resilience_warning": {
            0: {"climate": 13.0},
            1: {"climate": 8.0},
            2: {"climate": 1.0},
        },
        "ageing_workforce_gap": {
            0: {"skills": 12.0},
            1: {"skills": 7.0},
            2: {"skills": 9.0},
        },
        "supply_chain_realign": {
            0: {"trade": 12.0},
            1: {"trade": 8.0},
            2: {"trade": -3.0},
        },
    }
    selected = impacts.get(str(event_id), {}).get(int(choice_index))
    if not selected:
        return None
    stock = dict(s.long_run_policy_stock)
    for key, delta in selected.items():
        stock[key] = round(_clip(float(stock.get(key, 0.0)) + delta, 0.0, 100.0), 2)
    s.long_run_policy_stock = stock
    record = {
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "event": str(event_id),
        "choice": int(choice_index),
        "investment_stock": dict(stock),
    }
    s.long_run_event_history = (list(s.get("long_run_event_history", [])) + [record])[-30:]
    s.long_run_last_event = record
    return record


def advance(s=None):
    """Apply bounded annual structural trends once per year and record their effects."""
    s = ensure(s)
    period = f"Term {int(s.get('term', 1))}, Year {int(s.get('year', 1))}"
    if s.get("long_run_last_year") == period:
        return s.get("long_run_history", [])[-1] if s.get("long_run_history") else None

    stock = dict(s.long_run_policy_stock)
    # Policy capacity depreciates gradually: a single announcement is not permanent,
    # but a sequence of investments can build a durable national capability.
    for key in POLICY_STOCK_KEYS:
        stock[key] = round(_clip(float(stock.get(key, 0.0)) * 0.97, 0.0, 100.0), 2)
    s.long_run_policy_stock = stock

    business_confidence = float(s.get("business_confidence", 52.0))
    labour_demand = float(s.get("labour_demand", 100.0))
    world_cycle = float(s.get("world_cycle", 0.0))
    world_growth = _world_average(s)
    country = dict(s.get("country") or {})

    # Population change is decomposed into modest natural growth and net migration.
    # Migration responds to labour demand, confidence, housing capacity and skills policy.
    migration = _clip(
        155.0 + (business_confidence - 50.0) * 2.0
        + (labour_demand - 100.0) * 0.65
        - max(0.0, float(s.housing_supply_gap) - 170.0) * 0.045
        + stock["skills"] * 0.75,
        55.0, 330.0
    )
    old_population = float(s.population_millions)
    population_growth_pct = 0.10 + migration / max(1.0, old_population * 10.0)
    s.population_millions = round(_clip(
        old_population * (1.0 + population_growth_pct / 100.0), 60.0, 82.0
    ), 3)
    s.net_migration_thousands = round(migration, 1)
    old_working_age = float(s.working_age_share)
    s.working_age_share = round(_clip(
        old_working_age - 0.105
        + max(0.0, migration - 150.0) * 0.00013
        + stock["skills"] * 0.0009,
        56.0, 64.0
    ), 3)
    old_dependency = float(s.dependency_ratio)
    s.dependency_ratio = round(_clip(
        old_dependency + 0.17 - max(0.0, migration - 150.0) * 0.00012,
        52.0, 78.0
    ), 3)

    old_labour_supply = float(s.labour_supply_index)
    labour_supply_change = (
        (population_growth_pct - 0.25) * 0.45
        + (float(s.working_age_share) - old_working_age) * 0.28
        + stock["skills"] * 0.0015
    )
    s.labour_supply_index = round(_clip(old_labour_supply + labour_supply_change, 88.0, 115.0), 3)

    # Housing supply is a cumulative stock-flow problem. New construction helps,
    # while population and household formation create an ongoing annual demand.
    completions = _country_value(s, "homes_built", 215.0) + stock["housing"] * 0.72
    housing_demand = 210.0 + max(0.0, population_growth_pct - 0.20) * 45.0
    housing_demand += max(0.0, migration - 150.0) * 0.045
    gap_before = float(s.housing_supply_gap)
    gap_change = _clip(housing_demand - completions, -35.0, 55.0)
    s.housing_supply_gap = round(_clip(gap_before + gap_change, 0.0, 900.0), 1)
    s.housing_demand_thousands = round(housing_demand, 1)
    shortage = max(0.0, float(s.housing_supply_gap) - 150.0)
    affordability_change = (
        0.025 + min(0.06, shortage * 0.00025)
        - max(0.0, completions - housing_demand) * 0.0018
        - stock["housing"] * 0.0008
    )
    homelessness_change = (
        max(0.0, shortage) * 0.006
        + max(0.0, housing_demand - completions) * 0.025
        - stock["housing"] * 0.045
    )
    _nudge_country(s, {
        "house_ratio": affordability_change,
        "homeless": homelessness_change,
    })

    # Energy security is a function of clean generation, grid capacity and import
    # dependence. Investment is persistent and slowly compounds rather than
    # granting an immediate permanent reduction in household bills.
    netzero = _country_value(s, "netzero", 38.0)
    s.clean_energy_share = round(_clip(
        float(s.clean_energy_share) + 0.10
        + (netzero - float(s.clean_energy_share)) * 0.045
        + stock["energy"] * 0.025,
        10.0, 90.0
    ), 3)
    s.grid_capacity_index = round(_clip(
        float(s.grid_capacity_index) + 0.12 + stock["energy"] * 0.045,
        35.0, 100.0
    ), 3)
    s.energy_import_exposure = round(_clip(
        55.0 - (float(s.clean_energy_share) - 38.0) * 0.32
        - (float(s.grid_capacity_index) - 50.0) * 0.12
        - stock["trade"] * 0.035,
        12.0, 90.0
    ), 3)
    security = (
        62.0 + (float(s.clean_energy_share) - 38.0) * 0.48
        + (float(s.grid_capacity_index) - 50.0) * 0.22
        - (float(s.energy_import_exposure) - 55.0) * 0.18
    )
    s.energy_security = round(_clip(security, 15.0, 95.0), 2)
    energy_price_pressure = (
        (55.0 - float(s.energy_security)) * 0.40
        + world_cycle * 1.35
        - (float(s.clean_energy_share) - 38.0) * 0.08
    )
    energy_bill_change = _clip(energy_price_pressure * 4.5, -35.0, 55.0)
    _nudge_country(s, {"energy_bills": energy_bill_change})
    s.inflation = round(_clip(
        float(s.get("inflation", 2.0)) + energy_bill_change / 1750.0 * 0.22,
        0.0, 12.0
    ), 2)

    # Climate adaptation lowers the expected annual damage from extreme weather.
    # Decarbonisation alone is not adaptation: both resilience and transition matter.
    s.climate_resilience = round(_clip(
        float(s.climate_resilience) - 0.075
        + max(0.0, netzero - 38.0) * 0.002
        + stock["climate"] * 0.055,
        10.0, 95.0
    ), 3)
    climate_exposure = max(0.0, 52.0 - float(s.climate_resilience))
    climate_growth_drag = min(0.07, climate_exposure * 0.0016)
    climate_fiscal_cost = min(0.35, climate_exposure * 0.008)
    if climate_growth_drag:
        s.growth = round(float(s.get("growth", 0.0)) - climate_growth_drag, 2)

    # External demand is driven by trading partners; trade resilience reduces the
    # damage from weak global activity and makes supply chains less fragile.
    trade_change = _clip(
        (world_growth - 1.45) * 0.025
        + (float(stock["trade"]) - 10.0) * 0.0008,
        -0.12, 0.12
    )
    trade_resilience = _clip(50.0 + stock["trade"] * 0.65, 35.0, 90.0)
    s.trade_resilience = round(trade_resilience, 2)

    # Regional divergence is tracked rather than allowing a strong South East to
    # disguise persistently weak productivity elsewhere.
    try:
        import regional_economy
        regional_economy.ensure(s)
        productivity = [float(row.get("productivity", 100.0))
                       for row in s.regional_economies.values()]
    except Exception:
        productivity = []
    if len(productivity) > 1:
        mean = sum(productivity) / len(productivity)
        spread = (sum((value - mean) ** 2 for value in productivity) / len(productivity)) ** 0.5
    else:
        spread = 15.0
    s.regional_inequality_index = round(_clip(spread, 0.0, 40.0), 2)
    regional_drag = min(0.05, max(0.0, spread - 12.0) * 0.003)

    labour_growth_impulse = _clip(labour_supply_change * 0.045, -0.035, 0.035)
    housing_growth_drag = min(0.055, shortage * 0.000075)
    total_growth_impulse = trade_change + labour_growth_impulse - housing_growth_drag - regional_drag
    s.growth = round(_clip(float(s.get("growth", 0.0)) + total_growth_impulse, -8.0, 8.0), 2)

    # Ageing creates additional health and social-care demand on top of the
    # existing pension model. The cost is small at first and compounds gradually.
    care_cost = min(0.45, max(0.0, float(s.dependency_ratio) - 58.0) * 0.022)
    labour_receipts = _clip(labour_supply_change * 1.15, -0.20, 0.30)
    fiscal_impulse = round(labour_receipts - care_cost - climate_fiscal_cost, 2)
    if abs(fiscal_impulse) >= 0.01:
        s.headroom = round(float(s.get("headroom", 0.0)) + fiscal_impulse, 1)
        s.deficit = round(max(0.0, float(s.get("deficit", 0.0)) - fiscal_impulse), 1)

    s.long_run_last_year = period
    history = list(s.get("long_run_history", []))
    row = {
        "Year": period,
        "Population (m)": s.population_millions,
        "Net migration (000s)": s.net_migration_thousands,
        "Working-age share (%)": s.working_age_share,
        "Dependency ratio": s.dependency_ratio,
        "Housing supply gap (000s)": s.housing_supply_gap,
        "Homes demanded (000s)": s.housing_demand_thousands,
        "Energy security": s.energy_security,
        "Clean energy share (%)": s.clean_energy_share,
        "Climate resilience": s.climate_resilience,
        "Trade resilience": s.trade_resilience,
        "Regional inequality": s.regional_inequality_index,
        "Real growth impulse (pp)": round(total_growth_impulse, 3),
        "Annual care/climate cost (£bn)": round(care_cost + climate_fiscal_cost, 2),
        "Policy stock": dict(stock),
    }
    s.long_run_history = (history + [row])[-30:]
    return row


def legacy_assessment(s=None):
    """Score structural outcomes for the Chancellor's five-year legacy report."""
    s = ensure(s)
    country = s.get("country") or {}
    house_ratio = float(country.get("house_ratio", 8.3))
    housing_gap = float(s.get("housing_supply_gap", 170.0))
    housing = _clip(100.0 - max(0.0, house_ratio - 6.5) * 11.0
                    - max(0.0, housing_gap - 100.0) * 0.045, 0.0, 100.0)
    demographic = _clip(
        100.0 - max(0.0, float(s.dependency_ratio) - 58.0) * 1.8
        + (float(s.working_age_share) - 61.0) * 1.2
        + (float(s.labour_supply_index) - 100.0) * 0.7
    )
    energy = _clip(
        float(s.energy_security) * 0.52 + float(s.clean_energy_share) * 0.48
    )
    climate = _clip(float(s.climate_resilience))
    regional = _clip(100.0 - max(0.0, float(s.regional_inequality_index) - 12.0) * 3.0)
    trade = _clip(float(s.trade_resilience))
    overall = round(
        housing * 0.22 + demographic * 0.18 + energy * 0.18
        + climate * 0.14 + regional * 0.14 + trade * 0.14
    )
    return {
        "overall": overall,
        "housing": round(housing),
        "demographic": round(demographic),
        "energy": round(energy),
        "climate": round(climate),
        "regional": round(regional),
        "trade": round(trade),
    }


def legacy_summary(s=None):
    s = ensure(s)
    assessment = legacy_assessment(s)
    score = assessment["overall"]
    if score >= 80:
        verdict = "You leave behind stronger long-term foundations: housing, energy security and national resilience have improved."
    elif score >= 65:
        verdict = "The country is better prepared for some future pressures, although important structural weaknesses remain."
    elif score >= 50:
        verdict = "Your record on long-term resilience is mixed. The next Chancellor inherits both progress and unresolved structural problems."
    else:
        verdict = "The next administration inherits serious long-term pressures in housing, demographics, energy or climate resilience."
    return f"{verdict} Structural legacy score: {score}/100."


def render(s=None):
    s = ensure(s)
    st.markdown("### Long-term national pressures")
    st.caption("Illustrative game indices, not official population forecasts. These trends compound over time and influence the annual economy.")
    values = [
        ("Population", f"{float(s.population_millions):.2f}m"),
        ("Net migration", f"{float(s.net_migration_thousands):.0f}k"),
        ("Working-age share", f"{float(s.working_age_share):.1f}%"),
        ("Dependency ratio", f"{float(s.dependency_ratio):.1f}"),
        ("Housing supply gap", f"{float(s.housing_supply_gap):.0f}k"),
        ("Energy security", f"{float(s.energy_security):.0f}/100"),
        ("Clean energy share", f"{float(s.clean_energy_share):.1f}%"),
        ("Climate resilience", f"{float(s.climate_resilience):.0f}/100"),
    ]
    for start in range(0, len(values), 4):
        cols = st.columns(4)
        for col, (label, value) in zip(cols, values[start:start + 4]):
            col.metric(label, value)
    assessment = legacy_assessment(s)
    st.caption(
        f"Structural resilience: **{assessment['overall']}/100** · "
        f"Housing {assessment['housing']} · Demographics {assessment['demographic']} · "
        f"Energy {assessment['energy']} · Climate {assessment['climate']} · "
        f"Regional balance {assessment['regional']} · Trade {assessment['trade']}"
    )
    with st.expander("Long-term trend history", expanded=False):
        if s.get("long_run_history"):
            import pandas as pd
            rows = []
            for item in reversed(s.long_run_history[-10:]):
                rows.append({key: value for key, value in item.items() if key != "Policy stock"})
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        else:
            st.caption("The structural history builds as each financial year passes.")
    with st.expander("Policy capacity built over time", expanded=False):
        stock = s.get("long_run_policy_stock", {})
        for key, label in (
            ("housing", "Housing construction and planning"),
            ("energy", "Grid and clean-energy infrastructure"),
            ("climate", "Flood and climate adaptation"),
            ("skills", "Skills and labour-force participation"),
            ("trade", "Supply-chain and trade resilience"),
        ):
            st.progress(float(stock.get(key, 0.0)) / 100.0, text=f"{label} · {float(stock.get(key, 0.0)):.0f}/100")
