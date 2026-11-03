"""Annual feedback loops for firms, households, jobs and the public finances.

All figures are illustrative gameplay indices, not official forecasts. The module
uses bounded adjustments so the economy responds to policy without runaway feedback.
"""
import streamlit as st
import country


def ensure(s=None):
    s = s or st.session_state
    s.setdefault("business_confidence", 52.0)
    s.setdefault("business_investment", 100.0)
    s.setdefault("consumer_spending", 100.0)
    s.setdefault("labour_demand", 100.0)
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

    # Firms respond to demand, financing costs, policy stability and expected sales.
    confidence_change = (
        (market - 55.0) * 0.035
        + (growth - 1.0) * 0.22
        - max(0.0, rate - 4.0) * 0.16
        - max(0.0, inflation - 3.0) * 0.12
    )
    s.business_confidence = round(_clip(s.business_confidence + confidence_change, 5, 95), 1)
    investment_change = ((s.business_confidence - 52.0) * 0.035
                         + (growth - 1.0) * 0.12 - max(0.0, rate - 4.0) * 0.10)
    s.business_investment = round(_clip(s.business_investment + investment_change, 55, 150), 1)

    # Household demand is driven by real pay and employment, but squeezed by prices/rates.
    spending_change = (real_wages * 0.42 - max(0.0, inflation - 2.0) * 0.20
                      - max(0.0, rate - 4.0) * 0.10
                      + (approval - 50.0) * 0.012)
    s.consumer_spending = round(_clip(s.consumer_spending + spending_change, 65, 140), 1)

    demand_signal = ((s.consumer_spending - 100.0) * 0.018
                     + (s.business_investment - 100.0) * 0.014
                     + (s.business_confidence - 52.0) * 0.006)
    growth_impulse = _clip(demand_signal, -0.35, 0.45)
    s.growth = round(_clip(growth + growth_impulse, -8.0, 8.0), 2)

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
    s.labour_demand = round(_clip(100.0 + (4.5 - new_unemployment) * 5.0
                                  + (s.business_investment - 100.0) * 0.25, 60, 140), 1)

    # Tax receipts respond automatically to the size of the nominal economy and
    # the strength of consumption/employment. Keep this a modest annual dividend.
    nominal_gdp_bn = max(500.0, float(s.get("gdp_trillion", 3.0)) * 1000.0)
    demand_receipts = _clip(
        ((s.consumer_spending - 100.0) * 0.025)
        + ((s.business_investment - 100.0) * 0.018)
        + ((4.5 - new_unemployment) * 0.16), -1.5, 2.5
    )
    s.headroom = round(float(s.get("headroom", 0.0)) + demand_receipts, 1)
    s.deficit = round(max(0.0, float(s.get("deficit", 0.0)) - demand_receipts), 1)
    s.living_economy_last_year = period
    row = {
        "Year": period,
        "Business confidence": s.business_confidence,
        "Business investment index": s.business_investment,
        "Consumer spending index": s.consumer_spending,
        "Unemployment": new_unemployment,
        "Real wage growth": c.get("real_wages", real_wages),
        "Growth impulse (pp)": round(growth_impulse, 2),
        "Tax receipt effect (£bn)": round(demand_receipts, 2),
    }
    s.living_economy_history = (list(s.living_economy_history) + [row])[-25:]


def render():
    s = ensure()
    st.markdown("### Living economy")
    st.caption("Illustrative simulation indices, not official ONS statistics. Business investment, household demand and employment now feed back into annual GDP growth and Treasury receipts.")
    cols = st.columns(4)
    cols[0].metric("Business confidence", f"{s.business_confidence:.0f}/100")
    cols[1].metric("Business investment", f"{s.business_investment:.1f}", "Index · 100 at start")
    cols[2].metric("Consumer spending", f"{s.consumer_spending:.1f}", "Index · 100 at start")
    cols[3].metric("Labour demand", f"{s.labour_demand:.1f}", "Index · 100 at start")
    if s.get("living_economy_history"):
        with st.expander("Living economy history"):
            st.dataframe(list(reversed(s.living_economy_history)), hide_index=True, use_container_width=True)
