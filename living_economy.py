"""Annual feedback loops for firms, households, jobs and the public finances.

All figures are illustrative gameplay indices, not official forecasts. The module
uses bounded adjustments so the economy responds to policy without runaway feedback.
"""
import streamlit as st
import country


def ensure(s=None):
    s = s or st.session_state
    # Persistent transmission indicators. setdefault safely migrates existing saves.
    s.setdefault("household_confidence", 55.0)
    s.setdefault("household_debt_stress", 24.0)
    s.setdefault("credit_conditions", 100.0)
    s.setdefault("export_demand", 100.0)
    s.setdefault("business_confidence", 52.0)
    s.setdefault("business_investment", 100.0)
    s.setdefault("consumer_spending", 100.0)
    s.setdefault("labour_demand", 100.0)
    s.setdefault("productivity_index", 100.0)
    s.setdefault("productivity_growth", 0.0)
    s.setdefault("living_economy_history", [])
    s.setdefault("living_economy_last_year", "")
    return s


def _clip(value, low, high):
    return max(low, min(high, float(value)))


def advance(s=None):
    """Apply one annual, bounded economic feedback step; safe to call more than once."""
    s = ensure(s)
    period = f"Term {int(s.get('term', 1))}, Year {int(s.get('year', 1))}"
    if s.get("living_economy_last_year") == period:
        return
    c = s.get("country") or {}
    growth = float(s.get("growth", 0.8))
    inflation = float(s.get("inflation", 2.0))
    rate = float(s.get("interest_rate", 4.5))
    market = float(s.get("market_conf", 55.0))
    approval = float(s.get("approval", 50.0))
    real_wages = float(c.get("real_wages", 0.6))
    unemployment = float(c.get("unemployment", 4.3))

    # Credit conditions transmit Bank Rate and sovereign-market stress into
    # mortgage, consumer-credit and business-finance availability.
    gilt = float(s.get("gilt_yield", 4.5))
    credit_change = ((market - 55.0) * 0.025
                     - max(0.0, rate - 4.0) * 0.55
                     - max(0.0, gilt - 4.5) * 0.35)
    s.credit_conditions = round(_clip(s.credit_conditions + credit_change, 55, 115), 1)

    # Household balance-sheet stress builds when rates, prices and unemployment
    # rise, and eases when real pay improves. It is a pressure index, not debt data.
    energy_bill = float(c.get("energy_bills", 1750.0))
    debt_stress_change = (max(0.0, rate - 3.5) * 0.55
                          + max(0.0, inflation - 2.0) * 0.32
                          + max(0.0, unemployment - 4.5) * 0.38
                          + max(0.0, energy_bill - 1750.0) / 500.0 * 0.25
                          - max(0.0, real_wages) * 0.30)
    s.household_debt_stress = round(_clip(s.household_debt_stress + debt_stress_change, 0, 100), 1)

    # Household confidence is distinct from headline government approval: it
    # reflects purchasing power, job security, borrowing costs and household strain.
    household_change = (real_wages * 0.75
                        + (4.5 - unemployment) * 0.55
                        - max(0.0, inflation - 2.0) * 0.65
                        + (s.credit_conditions - 100.0) * 0.06
                        - (s.household_debt_stress - 24.0) * 0.035
                        + (approval - 50.0) * 0.025)
    s.household_confidence = round(_clip(s.household_confidence + household_change, 5, 95), 1)

    # Overseas demand feeds UK exporters. Use the already-simulated trading
    # partners; if a legacy save has no world roster, the neutral baseline applies.
    partners = s.get("world_economy") or {}
    partner_growth = [float(item.get("growth", 1.2)) for item in partners.values()
                      if isinstance(item, dict)]
    external_growth = sum(partner_growth) / len(partner_growth) if partner_growth else 1.2
    export_change = _clip((external_growth - 1.2) * 0.035
                          + (market - 55.0) * 0.004, -0.18, 0.18)
    s.export_demand = round(_clip(s.export_demand + export_change, 65, 140), 1)

    # Firms respond to demand, financing costs, overseas orders and policy stability.
    confidence_change = ((market - 55.0) * 0.035
                         + (growth - 1.0) * 0.22
                         + (s.export_demand - 100.0) * 0.012
                         + (s.credit_conditions - 100.0) * 0.025
                         - max(0.0, rate - 4.0) * 0.16
                         - max(0.0, inflation - 3.0) * 0.12)
    s.business_confidence = round(_clip(s.business_confidence + confidence_change, 5, 95), 1)
    investment_change = ((s.business_confidence - 52.0) * 0.035
                         + (growth - 1.0) * 0.12
                         + (s.export_demand - 100.0) * 0.018
                         + (s.credit_conditions - 100.0) * 0.035
                         - max(0.0, rate - 4.0) * 0.10)
    s.business_investment = round(_clip(s.business_investment + investment_change, 55, 150), 1)

    # Household demand responds to confidence and real pay, but debt stress,
    # inflation and borrowing costs restrain discretionary spending.
    spending_change = (real_wages * 0.30
                       + (s.household_confidence - 55.0) * 0.045
                       - max(0.0, inflation - 2.0) * 0.20
                       - max(0.0, rate - 4.0) * 0.10
                       - (s.household_debt_stress - 24.0) * 0.018
                       + (s.credit_conditions - 100.0) * 0.025)
    s.consumer_spending = round(_clip(s.consumer_spending + spending_change, 65, 140), 1)

    demand_signal = ((s.consumer_spending - 100.0) * 0.018
                     + (s.business_investment - 100.0) * 0.014
                     + (s.business_confidence - 52.0) * 0.006
                     + (s.export_demand - 100.0) * 0.012)
    growth_impulse = _clip(demand_signal, -0.45, 0.55)
    # Investment and confidence gradually build productive capacity; unlike a demand
    # boost, this persists as a small supply-side contribution to future output.
    productivity_change = _clip(
        (s.business_investment - 100.0) * 0.0015 + (s.business_confidence - 52.0) * 0.0008,
        -0.12, 0.16
    )
    s.productivity_growth = round(productivity_change, 3)
    s.productivity_index = round(_clip(s.productivity_index * (1.0 + productivity_change / 100.0), 85, 125), 3)
    s.growth = round(_clip(growth + growth_impulse + productivity_change, -8.0, 8.0), 2)

    # Jobs react with a lag; pay improves when demand is strong and unemployment is low.
    job_change = (growth_impulse * 0.20
                  + (s.business_investment - 100.0) * 0.004
                  - (unemployment - 4.5) * 0.025)
    new_unemployment = round(_clip(unemployment - job_change, 2.0, 15.0), 2)
    wage_impulse = _clip((growth_impulse * 0.22) + ((4.5 - new_unemployment) * 0.035), -0.12, 0.16)
    if "unemployment" in c:
        c["unemployment"] = round(_clip(new_unemployment, country.STATS["unemployment"]["lo"],
                                        country.STATS["unemployment"]["hi"]), 2)
    if "real_wages" in c:
        c["real_wages"] = round(_clip(real_wages + wage_impulse, country.STATS["real_wages"]["lo"],
                                      country.STATS["real_wages"]["hi"]), 2)
    # Pay growth above productivity and a tight labour market can feed prices;
    # weak pay growth or spare capacity eases pressure. Keep this second-round
    # effect small because the Bank-rate/inflation response is handled by econ.step.
    wage_price_pressure = _clip(
        (float(c.get("real_wages", real_wages)) - s.productivity_growth) * 0.035
        + (4.5 - new_unemployment) * 0.012, -0.10, 0.10
    )
    s.inflation = round(_clip(float(s.get("inflation", inflation)) + wage_price_pressure, 0.0, 12.0), 2)
    s.labour_demand = round(_clip(100.0 + (4.5 - new_unemployment) * 5.0
                                  + (s.business_investment - 100.0) * 0.25, 60, 140), 1)

    # Tax receipts respond automatically to the size of the nominal economy and
    # the strength of consumption/employment. Keep this a modest annual dividend.
    nominal_gdp_bn = max(500.0, float(s.get("gdp_trillion", 3.0)) * 1000.0)
    demand_receipts = _clip(
        ((s.consumer_spending - 100.0) * 0.025)
        + ((s.business_investment - 100.0) * 0.018)
        + ((s.export_demand - 100.0) * 0.012)
        + ((4.5 - new_unemployment) * 0.16), -1.8, 2.8
    )
    s.headroom = round(float(s.get("headroom", 0.0)) + demand_receipts, 1)
    s.deficit = round(max(0.0, float(s.get("deficit", 0.0)) - demand_receipts), 1)
    s.living_economy_last_year = period
    row = {
        "Year": period,
        "Business confidence": s.business_confidence,
        "Business investment index": s.business_investment,
        "Consumer spending index": s.consumer_spending,
        "Household confidence": s.household_confidence,
        "Household debt stress": s.household_debt_stress,
        "Credit conditions": s.credit_conditions,
        "Export demand index": s.export_demand,
        "Unemployment": new_unemployment,
        "Real wage growth": c.get("real_wages", real_wages),
        "Growth impulse (pp)": round(growth_impulse, 2),
        "Productivity growth (pp)": s.productivity_growth,
        "Wage-price pressure (pp)": round(wage_price_pressure, 3),
        "Productivity index": s.productivity_index,
        "Tax receipt effect (£bn)": round(demand_receipts, 2),
    }
    s.living_economy_history = (list(s.living_economy_history) + [row])[-25:]


def render():
    s = ensure()
    st.markdown("### Living economy")
    st.caption("Illustrative simulation indices, not official ONS statistics. Business investment, household demand and employment now feed back into annual GDP growth and Treasury receipts.")
    cols = st.columns(4)
    cols[0].metric("Household confidence", f"{s.household_confidence:.0f}/100")
    cols[1].metric("Business confidence", f"{s.business_confidence:.0f}/100")
    cols[2].metric("Credit conditions", f"{s.credit_conditions:.0f}/100")
    cols[3].metric("Export demand", f"{s.export_demand:.1f}", "Index · 100 at start")
    extra = st.columns(4)
    extra[0].metric("Business investment", f"{s.business_investment:.1f}", "Index · 100 at start")
    extra[1].metric("Consumer spending", f"{s.consumer_spending:.1f}", "Index · 100 at start")
    extra[2].metric("Household debt stress", f"{s.household_debt_stress:.0f}/100")
    extra[3].metric("Labour demand", f"{s.labour_demand:.1f}", "Index · 100 at start")
    labour = st.columns(3)
    labour[0].metric("Unemployment", f"{float((s.get('country') or {}).get('unemployment', 4.3)):.1f}%")
    labour[1].metric("Productivity index", f"{s.productivity_index:.2f}", f"{s.productivity_growth:+.2f}pp annual growth")
    labour[2].metric("Real wage growth", f"{float((s.get('country') or {}).get('real_wages', 0.0)):+.1f}%")
    if s.get("living_economy_history"):
        with st.expander("Living economy history"):
            st.dataframe(list(reversed(s.living_economy_history)), hide_index=True, use_container_width=True)
