"""Household economy model for the UK Chancellor Simulator.

The figures are illustrative gameplay indices, not official household statistics.
The model translates wages, prices, housing costs and interest rates into a
readable picture of household financial pressure.
"""
import streamlit as st

import state


def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def ensure(s=None):
    s = s or st.session_state
    defaults = {
        "household_confidence": 52.0,
        "disposable_income_index": 100.0,
        "mortgage_pressure": 48.0,
        "rent_pressure": 50.0,
        "household_bill_pressure": 50.0,
        "household_history": [],
        "household_last_year": "",
        "household_policy_year": 0,
        "household_policy_history": [],
    }
    for key, value in defaults.items():
        if key not in s:
            s[key] = value if not isinstance(value, list) else list(value)
    return s


def calculate(s=None):
    s = ensure(s)
    c = s.get("country") or {}
    bank_rate = float(s.get("interest_rate", 4.5))
    inflation = float(s.get("inflation", 2.0))
    real_wages = float(c.get("real_wages", 0.0))
    unemployment = float(c.get("unemployment", 4.3))
    house_ratio = float(c.get("house_ratio", 8.3))
    homes_built = float(c.get("homes_built", 215.0))
    energy_bill = float(c.get("energy_bills", 1750.0))
    child_poverty = float(c.get("child_poverty", 31.0))

    mortgage = _clip(43 + (bank_rate - 4.0) * 8.5 + (house_ratio - 8.0) * 5.0)
    rent = _clip(45 + (house_ratio - 8.0) * 7.0 - (homes_built - 215.0) * 0.09)
    bills = _clip(35 + (energy_bill - 1750.0) / 18.0 + (inflation - 2.0) * 3.0)
    income = max(70.0, min(130.0, 100.0 + real_wages * 2.4 - max(0.0, inflation - 2.0) * 1.1))
    confidence = _clip(
        55 + real_wages * 5.0 - (unemployment - 4.3) * 3.2
        - (mortgage - 45) * 0.18 - (rent - 50) * 0.16
        - (bills - 50) * 0.13 - max(0.0, child_poverty - 31.0) * 0.45
    )
    return {
        "confidence": round(confidence, 1),
        "income": round(income, 1),
        "mortgage": round(mortgage, 1),
        "rent": round(rent, 1),
        "bills": round(bills, 1),
        "real_wages": round(real_wages, 2),
        "unemployment": round(unemployment, 1),
        "bank_rate": round(bank_rate, 2),
        "inflation": round(inflation, 1),
        "energy_bill": round(energy_bill),
        "house_ratio": round(house_ratio, 1),
    }


def advance(s=None):
    """Refresh the household indicators once per in-game year."""
    s = ensure(s)
    year = f"Term {int(s.get('term', 1))}, Year {int(s.get('year', 1))}"
    if s.get("household_last_year") == year:
        return calculate(s)
    old = float(s.get("household_confidence", 52.0))
    values = calculate(s)
    s.household_confidence = values["confidence"]
    s.disposable_income_index = values["income"]
    s.mortgage_pressure = values["mortgage"]
    s.rent_pressure = values["rent"]
    s.household_bill_pressure = values["bills"]
    s.household_last_year = year
    history = list(s.get("household_history", []))
    history.append({"Year": year, "Household confidence": values["confidence"],
                    "Disposable income index": values["income"],
                    "Mortgage pressure": values["mortgage"],
                    "Rent pressure": values["rent"], "Bills pressure": values["bills"]})
    s.household_history = history[-20:]
    change = values["confidence"] - old
    if abs(change) >= 1.0:
        s.approval = round(_clip(float(s.get("approval", 50.0)) + max(-1.5, min(1.5, change * 0.08)), 0, 100), 1)
        s.message = str(s.get("message", "")) + (
            " Improving household finances are giving the Government a modest approval lift."
            if change > 0 else
            " Household financial pressure is weighing on the Government's approval."
        )
    return values


POLICIES = {
    "rent": {
        "title": "Targeted rent and housing support",
        "cost": 1.5,
        "description": "A temporary, means-tested package for low-income renters and households at risk of homelessness.",
        "effects": {"confidence": 4.0, "rent": -10.0, "income": 1.0},
        "message": "Targeted rent support cushions vulnerable tenants, but adds £1.5bn to annual spending."
    },
    "energy": {
        "title": "Household energy rebate",
        "cost": 2.0,
        "description": "A time-limited rebate focused on households most exposed to high energy bills.",
        "effects": {"confidence": 4.5, "bills": -13.0, "income": 1.5},
        "message": "A targeted energy rebate eases bills for vulnerable households, at a £2bn fiscal cost."
    },
    "mortgage": {
        "title": "Mortgage hardship and refinancing scheme",
        "cost": 1.0,
        "description": "Expand debt advice and temporary support for households facing payment shocks; no blanket mortgage subsidy.",
        "effects": {"confidence": 3.5, "mortgage": -8.0},
        "message": "A mortgage hardship scheme helps households in arrears and costs £1bn."
    },
}


def apply_policy(key):
    s = ensure()
    policy = POLICIES.get(key)
    year = int(s.get("year", 1))
    period = int(s.get("term", 1)) * 10 + year
    if not policy or int(s.get("household_policy_year", 0)) >= period:
        return False
    state.checkpoint()
    state.snapshot()
    cost = float(policy["cost"])
    s.headroom = round(float(s.get("headroom", 0.0)) - cost, 1)
    s.deficit = round(float(s.get("deficit", 0.0)) + cost, 1)
    s.household_confidence = round(_clip(float(s.get("household_confidence", 52.0)) + policy["effects"]["confidence"]), 1)
    s.disposable_income_index = round(_clip(float(s.get("disposable_income_index", 100.0)) + policy["effects"].get("income", 0.0), 70, 130), 1)
    s.rent_pressure = round(_clip(float(s.get("rent_pressure", 50.0)) + policy["effects"].get("rent", 0.0)), 1)
    s.household_bill_pressure = round(_clip(float(s.get("household_bill_pressure", 50.0)) + policy["effects"].get("bills", 0.0)), 1)
    s.mortgage_pressure = round(_clip(float(s.get("mortgage_pressure", 48.0)) + policy["effects"].get("mortgage", 0.0)), 1)
    s.approval = round(_clip(float(s.get("approval", 50.0)) + 1.0), 1)
    s.household_policy_year = period
    entry = {"Year": f"Term {s.get('term', 1)}, Year {year}", "Policy": policy["title"], "Cost (£bn)": cost}
    s.household_policy_history = (list(s.get("household_policy_history", [])) + [entry])[-20:]
    s.message = policy["message"]
    state.log("household_policy", "Household support package", choice=policy["title"], note=policy["message"])
    return True


def render():
    s = ensure()
    values = calculate(s)
    # Show the saved annual reading, while the caption explains the live drivers.
    confidence = float(s.get("household_confidence", values["confidence"]))
    income = float(s.get("disposable_income_index", values["income"]))
    mortgage = float(s.get("mortgage_pressure", values["mortgage"]))
    rent = float(s.get("rent_pressure", values["rent"]))
    bills = float(s.get("household_bill_pressure", values["bills"]))

    st.markdown("### Household economy")
    st.caption("A simplified model of how the economy feels to households. Indices are gameplay estimates, not official ONS statistics.")
    cols = st.columns(4)
    cols[0].metric("Household confidence", f"{confidence:.0f}/100")
    cols[1].metric("Disposable income index", f"{income:.1f}", help="100 is the opening baseline; higher means stronger estimated real purchasing power.")
    cols[2].metric("Mortgage pressure", f"{mortgage:.0f}/100")
    cols[3].metric("Rent pressure", f"{rent:.0f}/100")
    cols = st.columns(3)
    cols[0].metric("Household bills pressure", f"{bills:.0f}/100")
    cols[1].metric("Real wage growth", f"{values['real_wages']:+.1f}%")
    cols[2].metric("Unemployment", f"{values['unemployment']:.1f}%")
    st.caption(f"Current drivers: Bank Rate {values['bank_rate']:.2f}%, inflation {values['inflation']:.1f}%, average annual energy bill £{values['energy_bill']:,.0f}, house-price-to-income ratio {values['house_ratio']:.1f}x.")
    if confidence >= 65:
        st.success("Households are broadly optimistic. Real pay and employment are outweighing housing and bills pressure.")
    elif confidence >= 45:
        st.info("Household finances are mixed. Many voters feel the squeeze even if headline GDP is growing.")
    else:
        st.warning("Households are under significant pressure. Weak purchasing power, housing costs or unemployment are feeding into public discontent.")

    st.markdown("#### Treasury household support")
    current_period = int(s.get("term", 1)) * 10 + int(s.get("year", 1))
    if int(s.get("household_policy_year", 0)) >= current_period:
        st.caption("You have already announced one household support package this year. Another will be available next year.")
    else:
        st.caption("You may introduce one targeted package each year. Each costs money and improves a different pressure point.")
        for key, policy in POLICIES.items():
            with st.container(border=True):
                st.markdown(f"**{policy['title']} · £{policy['cost']:.1f}bn**")
                st.caption(policy["description"])
                if st.button("Announce package", key=f"household_policy_{key}", use_container_width=True):
                    apply_policy(key)
                    st.rerun()
    if s.get("household_history"):
        with st.expander("Household trends"):
            st.dataframe(list(reversed(s.household_history)), hide_index=True, use_container_width=True)
    if s.get("household_policy_history"):
        with st.expander("Previous household support packages"):
            st.dataframe(list(reversed(s.household_policy_history)), hide_index=True, use_container_width=True)
