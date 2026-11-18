"""Treasury revenue growth and public investment portfolio.

The tax-base index turns nominal economic expansion into higher recurring receipts.
Public investments are capital outlays that generate annual operating income and
modest asset appreciation; returns are deliberately conservative and sector-specific.
"""
import streamlit as st

import econ

ASSETS = {
    "renewables": {
        "label": "Renewable energy",
        "yield": 0.065,
        "appreciation": 0.018,
        "risk": "Medium",
        "detail": "Grid-scale solar, wind and storage projects; dividends and power revenues.",
    },
    "infrastructure": {
        "label": "Transport & infrastructure",
        "yield": 0.048,
        "appreciation": 0.022,
        "risk": "Low",
        "detail": "Ports, rail and essential infrastructure with steady operating income.",
    },
    "government_property": {
        "label": "Government property",
        "yield": 0.052,
        "appreciation": 0.012,
        "risk": "Low",
        "detail": "Commercial property and long-term public estate leases.",
    },
    "national_fund": {
        "label": "National investment fund",
        "yield": 0.072,
        "appreciation": 0.025,
        "risk": "High",
        "detail": "A diversified strategic fund; higher potential returns with market risk.",
    },
}

def ensure():
    s = st.session_state
    s.setdefault("tax_base_index", 1.0)
    s.setdefault("treasury_assets", {})
    s.setdefault("treasury_income_history", [])
    s.setdefault("treasury_last_tax_uplift", 0.0)
    s.setdefault("treasury_last_investment_income", 0.0)
    s.setdefault("treasury_cumulative_income", 0.0)
    s.setdefault("treasury_cost_pressure_history", [])
    s.setdefault("treasury_last_cost_pressures", {})
    s.setdefault("treasury_notice", "")


def annual_update(nominal_growth):
    """Apply one year's tax-base buoyancy and investment cash income to the fiscal position."""
    import budget

    ensure()
    s = st.session_state
    old_index = float(s.tax_base_index)
    # Tax receipts respond strongly, but not one-for-one, to nominal GDP.
    effective_growth = max(-8.0, min(12.0, float(nominal_growth) * 0.85))
    new_index = max(0.55, old_index * (1.0 + effective_growth / 100.0))
    applied = s.get("budget_applied") or budget.defaults()
    old_receipts = sum(budget.revenues(applied).values())
    s.tax_base_index = round(new_index, 5)
    new_receipts = sum(budget.revenues(applied).values())
    gross_tax_uplift = round(new_receipts - old_receipts, 2)
    # Most extra receipts are absorbed by higher demand, public-service costs and
    # existing spending pressures. Only a conservative share becomes new headroom.
    # In a downturn, however, the full receipts loss feeds through automatically.
    tax_uplift = round(gross_tax_uplift * 0.30 if gross_tax_uplift > 0 else gross_tax_uplift, 2)

    investment_income = 0.0
    asset_growth = 0.0
    market_factor = max(0.55, min(1.15, 0.75 + float(s.get("market_conf", 50.0)) / 200.0))
    for key, amount in list(s.treasury_assets.items()):
        spec = ASSETS.get(key)
        if not spec or amount <= 0:
            continue
        principal = float(amount)
        investment_income += principal * float(spec["yield"]) * market_factor
        asset_growth += principal * float(spec["appreciation"]) * market_factor
        # A small annual management/maintenance charge prevents free money.
        investment_income -= principal * 0.005
        s.treasury_assets[key] = round(principal + principal * float(spec["appreciation"]) * market_factor, 2)

    investment_income = round(max(0.0, investment_income), 2)
    total_extra = round(tax_uplift + investment_income, 2)

    # Recurring public-service cost pressures. These are incremental annual
    # pressures on the fiscal margin, not the full NHS/pay/pension budgets.
    inflation = float(s.get("inflation", 2.0))
    demographic_pressure = float(s.get("demographic_pressure", 0.0))
    nhs_pressure = round(
        0.45 + 0.10 * max(0.0, inflation - 2.0) + 0.025 * demographic_pressure, 2
    )
    public_pay_pressure = round(
        0.40 + 0.12 * max(0.0, inflation - 2.0) + 0.015 * max(0.0, 2.0 - float(s.get("growth", 0.0))), 2
    )
    annual_cost_pressure = round(nhs_pressure + public_pay_pressure, 2)

    net_fiscal_change = round(total_extra - annual_cost_pressure, 2)
    if net_fiscal_change:
        s.headroom = round(float(s.headroom) + net_fiscal_change, 1)
        s.deficit = round(max(0.0, float(s.deficit) - net_fiscal_change), 1)
    s.treasury_last_tax_uplift = tax_uplift
    s.treasury_last_investment_income = investment_income
    s.treasury_last_cost_pressures = {
        "NHS and public services (£bn)": nhs_pressure,
        "Public-sector pay (£bn)": public_pay_pressure,
        "Total recurring pressures (£bn)": annual_cost_pressure,
    }
    s.treasury_cost_pressure_history = s.get("treasury_cost_pressure_history", [])
    s.treasury_cost_pressure_history.append({
        "Year": f"Term {s.term}, Year {s.year}",
        **s.treasury_last_cost_pressures,
    })
    s.treasury_cumulative_income = round(float(s.treasury_cumulative_income) + total_extra, 2)
    s.treasury_income_history.append({
        "Year": f"Term {s.term}, Year {s.year}",
        "Gross extra tax receipts (£bn)": gross_tax_uplift,
        "Net growth dividend to headroom (£bn)": tax_uplift,
        "Investment income (£bn)": investment_income,
        "Recurring cost pressures (£bn)": annual_cost_pressure,
        "Net change to headroom (£bn)": net_fiscal_change,
        "Tax base index": s.tax_base_index,
    })
    s.message += (
        f" Treasury update: economic growth generated £{gross_tax_uplift:.1f}B in extra tax receipts, of which £{tax_uplift:.1f}B improves headroom after spending pressures; "
        f"public investments generated £{investment_income:.1f}B. Recurring NHS and public-sector pay pressures cost £{annual_cost_pressure:.2f}B "
        f"(NHS £{nhs_pressure:.2f}B; pay £{public_pay_pressure:.2f}B)."
    )


def invest(key, amount):
    """Make an upfront capital investment, funded from available fiscal headroom."""
    ensure()
    s = st.session_state
    if key not in ASSETS:
        return False, "Choose a valid investment."
    amount = round(float(amount), 1)
    if amount <= 0:
        return False, "Enter an investment greater than £0.0bn."
    if amount > max(0.0, float(s.get("headroom", 0.0))):
        return False, "The investment exceeds available OBR headroom. Improve the fiscal position or choose a smaller amount."
    s.headroom = round(float(s.headroom) - amount, 1)
    s.deficit = round(float(s.deficit) + amount, 1)
    s.treasury_assets[key] = round(float(s.treasury_assets.get(key, 0.0)) + amount, 2)
    s.message = f" Treasury investment approved: £{amount:.1f}B allocated to {ASSETS[key]['label']}. Returns begin at the next annual update."
    s.treasury_notice = s.message.strip()
    return True, s.message



def fiscal_outlook(years=3):
    """Project the public finances using the same macro/debt stock-flow engine as the live annual tick.

    Scenarios are illustrative and non-mutating. Positive tax buoyancy is only partly
    available to the Treasury; downturn receipt losses pass through in full.
    """
    s = st.session_state
    years = max(1, min(5, int(years)))
    starting_gdp = max(0.5, float(s.get("gdp_trillion", 3.0)))
    base_growth = float(s.get("growth", 1.0))
    base_inflation = float(s.get("inflation", 2.0))
    starting_tax_index = max(0.55, float(s.get("tax_base_index", 1.0)))
    applied = s.get("budget_applied", {})
    try:
        import budget
        tax_receipts_base = sum(budget.revenues(applied or budget.defaults()).values()) / starting_tax_index
    except Exception:
        tax_receipts_base = starting_gdp * 160.0
    recurring = float(s.get("treasury_last_cost_pressures", {}).get("Total recurring pressures (£bn)", 0.85))
    demographic = float(s.get("demographic_pressure", 0.0))
    scenarios = {
        "Baseline": {"growth": 0.0, "inflation": 0.0, "gilt": 0.0, "market": 0.0},
        "Stronger growth": {"growth": 1.0, "inflation": -0.2, "gilt": -0.10, "market": 1.0},
        "Downturn": {"growth": -1.5, "inflation": 0.8, "gilt": 0.65, "market": -2.5},
    }
    rows = []
    for label, shock in scenarios.items():
        v = {
            "inflation": base_inflation, "interest_rate": float(s.get("interest_rate", 4.5)),
            "gilt_yield": float(s.get("gilt_yield", 4.5)), "growth": base_growth,
            "debt": float(s.get("debt", 90.0)), "deficit": max(0.0, float(s.get("deficit", 0.0))),
            "headroom": float(s.get("headroom", 0.0)), "market_conf": float(s.get("market_conf", 50.0)),
            "approval": float(s.get("approval", 50.0)), "cycle": s.get("macro_cycle", "Stagnation"),
            "gdp_trillion": starting_gdp,
        }
        tax_index = starting_tax_index
        for year in range(1, years + 1):
            v["growth"] = round(v["growth"] + shock["growth"], 2)
            v["inflation"] = round(max(0.0, v["inflation"] + shock["inflation"]), 2)
            v["gilt_yield"] = max(0.5, v["gilt_yield"] + shock["gilt"])
            v["market_conf"] = max(0.0, min(100.0, v["market_conf"] + shock["market"]))
            v = econ.step(v, None)
            nominal_growth = ((1.0 + v["growth"] / 100.0) * (1.0 + v["inflation"] / 100.0) - 1.0) * 100.0
            next_index = max(0.55, tax_index * (1.0 + max(-8.0, min(12.0, nominal_growth * 0.85)) / 100.0))
            gross_receipts = tax_receipts_base * (next_index - tax_index)
            growth_receipts = gross_receipts * 0.30 if gross_receipts > 0 else gross_receipts
            tax_index = next_index
            inflation_pressure = max(0.0, v["inflation"] - 2.0)
            nhs_pressure = 0.45 + 0.10 * inflation_pressure + 0.025 * demographic
            pay_pressure = 0.40 + 0.12 * inflation_pressure + 0.015 * max(0.0, 2.0 - v["growth"])
            annual_costs = max(0.0, recurring) + max(0.0, nhs_pressure + pay_pressure - 0.85)
            net_change = growth_receipts - annual_costs
            v["headroom"] = round(v["headroom"] + net_change, 1)
            v["deficit"] = round(max(0.0, v["deficit"] - net_change), 1)
            v["gdp_trillion"] = round(float(v["gdp_trillion"]) * (1.0 + nominal_growth / 100.0), 5)
        debt_stock = float(v.get("debt_stock_bn", v["gdp_trillion"] * 1000.0 * v["debt"] / 100.0))
        rows.append({
            "Scenario": label,
            "GDP after 3 years (£tn)": round(float(v["gdp_trillion"]), 2),
            "Real growth (%)": round(float(v["growth"]), 2),
            "Inflation (%)": round(float(v["inflation"]), 2),
            "Annual deficit (£bn)": round(float(v["deficit"]), 1),
            "Fiscal headroom (£bn)": round(float(v["headroom"]), 1),
            "Debt (£bn)": round(debt_stock, 1),
            "Debt-to-GDP (%)": round(float(v["debt"]), 1),
            "Debt interest (£bn)": round(float(v.get("debt_interest_bill", 10.7)), 1),
            "Gilt yield (%)": round(float(v["gilt_yield"]), 2),
        })
    return rows

def scenario_exposure(outlook):
    """Summarise the extra fiscal and debt-interest exposure in the downturn case."""
    by_name = {row["Scenario"]: row for row in outlook}
    if "Baseline" not in by_name or "Downturn" not in by_name:
        raise ValueError("Outlook must contain Baseline and Downturn scenarios.")
    baseline = by_name["Baseline"]
    downturn = by_name["Downturn"]
    return {
        "baseline_headroom": float(baseline["Fiscal headroom (£bn)"]),
        "downturn_headroom": float(downturn["Fiscal headroom (£bn)"]),
        "headroom_at_risk": round(
            float(baseline["Fiscal headroom (£bn)"]) - float(downturn["Fiscal headroom (£bn)"]), 1
        ),
        "extra_debt_interest": round(
            float(downturn["Debt interest (£bn)"]) - float(baseline["Debt interest (£bn)"]), 1
        ),
        "debt_ratio_increase": round(
            float(downturn["Debt-to-GDP (%)"]) - float(baseline["Debt-to-GDP (%)"]), 1
        ),
    }


def render():
    """Treasury investment desk and a transparent record of passive receipts."""
    ensure()
    s = st.session_state
    if s.get("treasury_notice"):
        st.success(s.treasury_notice)
        s.treasury_notice = ""
    st.markdown("### Treasury dashboard")
    st.caption("A consolidated view of the public finances. Figures are gameplay estimates, not official forecasts.")
    debt_bn = max(0.0, float(s.get("gdp_trillion", 3.0)) * 1000.0 * float(s.get("debt", 0.0)) / 100.0)
    snap = st.columns(4)
    snap[0].metric("Fiscal headroom", f"£{float(s.get('headroom', 0.0)):.1f}bn", help="Current buffer against the game's fiscal rule.")
    snap[1].metric("Annual deficit", f"£{float(s.get('deficit', 0.0)):.1f}bn")
    snap[2].metric("Debt-to-GDP", f"{float(s.get('debt', 0.0)):.1f}%")
    snap[3].metric("Debt interest", f"£{float(s.get('debt_interest_bill', 10.7)):.1f}bn")
    if float(s.get("headroom", 0.0)) < 0:
        st.error("The fiscal buffer is already in deficit. New permanent commitments will make the position harder to restore.")
    elif float(s.get("headroom", 0.0)) < 5:
        st.warning("The fiscal buffer is thin. A modest forecast downgrade could eliminate it.")
    else:
        st.success("There is a positive fiscal buffer. Stress-test it before committing to permanent spending.")
    with st.expander("Three-year fiscal outlook", expanded=True):
        st.caption("Illustrative scenario model using current growth, inflation, debt and recurring spending pressures. It is a planning aid, not an OBR forecast; it does not alter your live finances.")
        outlook = fiscal_outlook(3)
        st.dataframe(outlook, hide_index=True, use_container_width=True)
        base = next(row for row in outlook if row["Scenario"] == "Baseline")
        downside = next(row for row in outlook if row["Scenario"] == "Downturn")
        exposure = scenario_exposure(outlook)
        oc = st.columns(4)
        oc[0].metric("Baseline headroom · year 3", f"£{exposure['baseline_headroom']:.1f}bn")
        oc[1].metric("Downturn headroom · year 3", f"£{exposure['downturn_headroom']:.1f}bn")
        oc[2].metric("Headroom at risk", f"£{exposure['headroom_at_risk']:.1f}bn",
                     help="Baseline year-three headroom minus downturn year-three headroom.")
        oc[3].metric("Extra annual debt interest", f"£{exposure['extra_debt_interest']:.1f}bn",
                     help="Downturn debt-interest bill minus the baseline bill in year three.")
        st.caption(
            f"Under the downturn, debt-to-GDP is {exposure['debt_ratio_increase']:+.1f} percentage points "
            f"higher than the baseline by year three. These are scenario differences, not extra costs "
            "that have been applied to the live Budget."
        )
        if exposure["downturn_headroom"] < 0:
            st.warning("The downturn scenario pushes the year-three fiscal position into negative headroom. Consider rebuilding the buffer or reducing exposure to permanent commitments.")
        elif exposure["headroom_at_risk"] > 0:
            st.info(f"The downside shock puts £{exposure['headroom_at_risk']:.1f}bn of the projected year-three fiscal buffer at risk.")
        else:
            st.success("The downturn scenario does not reduce year-three headroom against the baseline in this projection.")
    st.divider()
    st.markdown("### 🏦 Treasury investment fund")
    st.caption("Invest available fiscal headroom in public assets. Capital is committed upfront; income and asset values update each spring.")
    total_assets = sum(float(v) for v in s.treasury_assets.values())
    a, b, c = st.columns(3)
    a.metric("Public investment portfolio", f"£{total_assets:.1f}bn")
    b.metric("Latest annual investment income", f"£{float(s.treasury_last_investment_income):.2f}bn")
    c.metric("Extra receipts accumulated", f"£{float(s.treasury_cumulative_income):.1f}bn")

    st.markdown("#### 🏦 Gilt markets and debt interest")
    d1, d2, d3 = st.columns(3)
    d1.metric("Estimated annual debt interest", f"£{float(s.get('debt_interest_bill', 10.7)):.1f}bn")
    d2.metric("Sovereign risk premium", f"+{float(s.get('gilt_risk_premium', 0.0)):.2f}pp")
    d3.metric("10-year gilt yield", f"{float(s.get('gilt_yield', 4.7)):.2f}%")
    premium = float(s.get("gilt_risk_premium", 0.0))
    if premium >= 1.25:
        st.error("Gilt investors are demanding a substantial extra return for holding government debt. New borrowing and refinancing are becoming expensive.")
    elif premium >= 0.60:
        st.warning("Investors are pricing in additional fiscal risk. A credible medium-term plan could bring the premium down.")
    else:
        st.caption("The risk premium is contained. It rises when debt, the deficit or weak market confidence make the public finances look less sustainable.")

    pressures = s.get("treasury_last_cost_pressures", {})
    if pressures:
        st.markdown("#### Annual spending pressures")
        p1, p2, p3 = st.columns(3)
        p1.metric("NHS & public services", f"£{float(pressures.get('NHS and public services (£bn)', 0)):.2f}bn")
        p2.metric("Public-sector pay", f"£{float(pressures.get('Public-sector pay (£bn)', 0)):.2f}bn")
        p3.metric("Combined annual pressure", f"£{float(pressures.get('Total recurring pressures (£bn)', 0)):.2f}bn")
        st.caption("These are additional annual pressures on the fiscal margin, not the total budgets for the NHS or public-sector wages. Pension costs are modelled separately; debt-interest repricing is included in the Budget forecast.")

    with st.expander("Make a new public investment", expanded=False):
        keys = list(ASSETS)
        labels = {k: f"{ASSETS[k]['label']} · {ASSETS[k]['yield']*100:.1f}% indicative yield · {ASSETS[k]['risk']} risk" for k in keys}
        chosen = st.selectbox("Investment", keys, format_func=lambda k: labels[k], key="treasury_asset_choice")
        spec = ASSETS[chosen]
        st.write(spec["detail"])
        st.caption(f"Indicative annual yield: {spec['yield']*100:.1f}% · Estimated asset appreciation: {spec['appreciation']*100:.1f}% · Risk: {spec['risk']}. Returns are game estimates, not guaranteed.")
        amount = st.number_input("Capital investment (£bn)", min_value=0.0, max_value=100.0, value=1.0, step=0.5, key="treasury_invest_amount")
        st.caption(f"Available OBR headroom: £{float(s.headroom):.1f}bn. Investment reduces headroom immediately and is treated as capital spending.")
        if st.button("Approve investment", type="primary", key="treasury_invest_button"):
            ok, message = invest(chosen, amount)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    if total_assets:
        rows = []
        for key, amount in s.treasury_assets.items():
            if key in ASSETS:
                spec = ASSETS[key]
                rows.append({
                    "Public asset": spec["label"],
                    "Portfolio value": f"£{float(amount):.2f}bn",
                    "Indicative annual yield": f"{spec['yield']*100:.1f}%",
                    "Risk": spec["risk"],
                })
        st.dataframe(rows, hide_index=True, use_container_width=True)
    with st.expander("How the automatic revenue system works"):
        st.markdown(
            "- **Growth dividend:** nominal GDP growth expands the tax base; tax receipts respond at 85% of nominal GDP growth.\n"
            "- **Investment income:** public assets generate annual operating income, adjusted for market confidence and a 0.5% upkeep charge.\n"
            "- **Asset appreciation:** portfolio values grow gradually; appreciation is not counted as spendable cash.\n"
            "- **Fiscal treatment:** additional receipts improve headroom and reduce the annual deficit. Investments require upfront headroom."
        )
    if s.get("treasury_income_history"):
        st.markdown("**Annual Treasury income history**")
        st.dataframe(list(reversed(s.treasury_income_history[-5:])), hide_index=True, use_container_width=True)
