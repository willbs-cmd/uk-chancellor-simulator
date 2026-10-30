"""Treasury revenue growth and public investment portfolio.

The tax-base index turns nominal economic expansion into higher recurring receipts.
Public investments are capital outlays that generate annual operating income and
modest asset appreciation; returns are deliberately conservative and sector-specific.
"""
import streamlit as st

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
    if total_extra:
        s.headroom = round(float(s.headroom) + total_extra, 1)
        s.deficit = round(max(0.0, float(s.deficit) - total_extra), 1)
    s.treasury_last_tax_uplift = tax_uplift
    s.treasury_last_investment_income = investment_income
    s.treasury_cumulative_income = round(float(s.treasury_cumulative_income) + total_extra, 2)
    s.treasury_income_history.append({
        "Year": f"Term {s.term}, Year {s.year}",
        "Gross extra tax receipts (£bn)": gross_tax_uplift,
        "Net growth dividend to headroom (£bn)": tax_uplift,
        "Investment income (£bn)": investment_income,
        "Total extra receipts (£bn)": total_extra,
        "Tax base index": s.tax_base_index,
    })
    s.message += (
        f" Treasury update: economic growth generated £{gross_tax_uplift:.1f}B in extra tax receipts, of which £{tax_uplift:.1f}B improves headroom after spending pressures; "
        f"public investments generated £{investment_income:.1f}B."
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


def render():
    """Treasury investment desk and a transparent record of passive receipts."""
    ensure()
    s = st.session_state
    if s.get("treasury_notice"):
        st.success(s.treasury_notice)
        s.treasury_notice = ""
    st.markdown("### 🏦 Treasury investment fund")
    st.caption("Invest available fiscal headroom in public assets. Capital is committed upfront; income and asset values update each spring.")
    total_assets = sum(float(v) for v in s.treasury_assets.values())
    a, b, c = st.columns(3)
    a.metric("Public investment portfolio", f"£{total_assets:.1f}bn")
    b.metric("Latest annual investment income", f"£{float(s.treasury_last_investment_income):.2f}bn")
    c.metric("Extra receipts accumulated", f"£{float(s.treasury_cumulative_income):.1f}bn")

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
