"""Devolved funding and local-government finance for the Chancellor Simulator.

The Chancellor controls central grants and the framework around local taxation,
not individual council tax bills. All values are illustrative gameplay estimates.
"""
import streamlit as st

BASELINE_GRANT_UPLIFT = 0.0
DEFAULTS = {
    "local_grant_uplift_bn": BASELINE_GRANT_UPLIFT,
    "barnett_pass_through_pct": 100,
    "council_tax_referendum_threshold": 5.0,
    "social_care_precept_cap": 2.0,
    "regional_growth_fund_bn": 1.0,
    "local_finance_pressure": 42.0,
    "local_service_delivery": 62.0,
    "local_finance_history": [],
    "local_finance_last_update": None,
    "local_finance_notice": "",
}


def ensure():
    s = st.session_state
    for key, value in DEFAULTS.items():
        if key not in s:
            s[key] = list(value) if isinstance(value, list) else value


def annual_update():
    """Apply the current central-grant and local-finance framework once per Spring."""
    ensure()
    s = st.session_state
    inflation = max(-2.0, min(15.0, float(s.get("inflation", 2.0))))
    grant_uplift = float(s.get("local_grant_uplift_bn", 0.0))
    regional_fund = float(s.get("regional_growth_fund_bn", 1.0))
    barnett_factor = max(0.5, min(1.5, float(s.get("barnett_pass_through_pct", 100)) / 100.0))
    # Approximate devolved consequentials on the regional growth allocation.
    devolved_consequentials = regional_fund * 0.19 * barnett_factor
    annual_cost = round(grant_uplift + regional_fund + devolved_consequentials, 2)

    if annual_cost:
        s.headroom = round(float(s.get("headroom", 0.0)) - annual_cost, 1)
        s.deficit = round(max(0.0, float(s.get("deficit", 0.0)) + annual_cost), 1)

    precept = float(s.get("social_care_precept_cap", 2.0))
    referendum = float(s.get("council_tax_referendum_threshold", 5.0))
    # Funding pressure rises with inflation and grant restraint. More local
    # revenue flexibility eases pressure but transfers some cost to households.
    pressure_change = (
        max(0.0, inflation - 2.0) * 1.15
        - grant_uplift * 0.75
        - regional_fund * 0.55
        - precept * 0.28
        + max(0.0, 4.0 - referendum) * 0.35
    )
    pressure = max(0.0, min(100.0, float(s.local_finance_pressure) + pressure_change))
    delivery_change = -pressure_change * 0.42
    delivery = max(0.0, min(100.0, float(s.local_service_delivery) + delivery_change))
    s.local_finance_pressure = round(pressure, 1)
    s.local_service_delivery = round(delivery, 1)

    if pressure >= 78:
        s.approval = round(max(0.0, float(s.get("approval", 50.0)) - 1.0), 1)
        s.pm_opinion = round(max(0.0, float(s.get("pm_opinion", 60.0)) - 0.5), 1)
        notice = "Local-government finances are approaching a breaking point. More councils are warning of service cuts and possible Section 114 notices."
    elif pressure >= 62:
        notice = "Council leaders warn that social care, libraries and local services are under growing financial pressure."
    elif pressure <= 28:
        notice = "A stronger local-government settlement is easing pressure on council services and social care."
    else:
        notice = "Local-government finances remain manageable, although councils continue to face competing service demands."

    record = {
        "year": f"Term {int(s.get('term', 1))}, Year {int(s.get('year', 1))}",
        "grant_uplift_bn": round(grant_uplift, 2),
        "regional_growth_fund_bn": round(regional_fund, 2),
        "devolved_consequentials_bn": round(devolved_consequentials, 2),
        "annual_cost_bn": annual_cost,
        "funding_pressure": s.local_finance_pressure,
        "service_delivery": s.local_service_delivery,
        "notice": notice,
    }
    s.local_finance_history = (list(s.get("local_finance_history", [])) + [record])[-12:]
    s.local_finance_last_update = record
    s.local_finance_notice = notice
    s.message = (str(s.get("message", "")) + f" Local finance settlement: £{annual_cost:.2f}bn annual cost; "
                 f"council funding pressure is {s.local_finance_pressure:.0f}/100.").strip()


def render():
    """Policy workspace for central grants, Barnett consequentials and local tax flexibility."""
    ensure()
    s = st.session_state
    st.markdown("### Local government & devolution")
    st.caption(
        "Set the central-government funding settlement and the framework for local tax flexibility. "
        "Councils retain responsibility for setting their own council tax bills; these controls model the national framework."
    )

    pressure = float(s.local_finance_pressure)
    delivery = float(s.local_service_delivery)
    annual_cost = (
        float(s.local_grant_uplift_bn)
        + float(s.regional_growth_fund_bn)
        + float(s.regional_growth_fund_bn) * 0.19 * float(s.barnett_pass_through_pct) / 100.0
    )
    a, b, c, d = st.columns(4)
    a.metric("Council funding pressure", f"{pressure:.0f}/100")
    b.metric("Local service delivery", f"{delivery:.0f}/100")
    c.metric("Annual settlement cost", f"£{annual_cost:.2f}bn")
    d.metric("Devolved pass-through", f"{float(s.barnett_pass_through_pct):.0f}%")

    if pressure >= 78:
        st.error("Local finance is in the danger zone. Expect service reductions, council tax pressure and Section 114 warnings.")
    elif pressure >= 62:
        st.warning("Councils are under sustained financial pressure. Social care and statutory services are competing for limited funds.")
    elif pressure <= 28:
        st.success("Local authority finances are comparatively resilient.")
    else:
        st.info("Local finances are under manageable pressure.")

    st.markdown("#### Set the next annual settlement")
    st.caption("Changes are saved as policy settings and feed through at the next Spring update. A positive grant uplift is a recurring annual commitment.")
    with st.form("devolution_policy_form"):
        grant = st.slider(
            "Local government grant uplift (£bn per year)", -5.0, 10.0,
            float(s.local_grant_uplift_bn), 0.5,
            help="A negative figure represents a real-terms or cash reduction against the game's baseline settlement."
        )
        barnett = st.slider(
            "Devolved funding pass-through (%)", 50, 150,
            int(s.barnett_pass_through_pct), 5,
            help="A simplified Barnett-style multiplier for the devolved consequentials generated by comparable English spending changes."
        )
        regional = st.slider(
            "Regional growth and town-centre fund (£bn per year)", 0.0, 5.0,
            float(s.regional_growth_fund_bn), 0.25
        )
        referendum = st.slider(
            "Council tax referendum threshold (%)", 0.0, 10.0,
            float(s.council_tax_referendum_threshold), 0.5,
            help="A lower threshold constrains council tax rises; a higher threshold gives councils more flexibility but can increase household bills."
        )
        precept = st.slider(
            "Adult social-care precept flexibility (%)", 0.0, 5.0,
            float(s.social_care_precept_cap), 0.25,
            help="More flexibility helps councils fund social care but shifts more of the cost onto local taxpayers."
        )
        projected_cost = grant + regional + regional * 0.19 * barnett / 100.0
        st.info(f"Estimated recurring annual cost: £{projected_cost:.2f}bn. This is applied at the next Spring update.")
        submitted = st.form_submit_button("Approve local government settlement", type="primary", use_container_width=True)

    if submitted:
        s.local_grant_uplift_bn = float(grant)
        s.barnett_pass_through_pct = int(barnett)
        s.regional_growth_fund_bn = float(regional)
        s.council_tax_referendum_threshold = float(referendum)
        s.social_care_precept_cap = float(precept)
        s.local_finance_notice = "Your local-government and devolved funding framework has been agreed. Its recurring fiscal and service effects begin at the next Spring update."
        s.message = s.local_finance_notice
        st.success(s.local_finance_notice)
        st.rerun()

    st.markdown("#### How the settlement is distributed")
    consequentials = float(s.regional_growth_fund_bn) * 0.19 * float(s.barnett_pass_through_pct) / 100.0
    distribution = [
        {"Funding stream": "Local authority grant uplift", "Annual amount": f"£{float(s.local_grant_uplift_bn):.2f}bn", "Purpose": "Core council services and statutory responsibilities"},
        {"Funding stream": "Regional growth fund", "Annual amount": f"£{float(s.regional_growth_fund_bn):.2f}bn", "Purpose": "Town centres, local transport and regional investment"},
        {"Funding stream": "Devolved consequentials", "Annual amount": f"£{consequentials:.2f}bn", "Purpose": "Additional funding for devolved administrations"},
    ]
    st.dataframe(distribution, hide_index=True, use_container_width=True)
    st.caption("The devolved consequentials are a deliberately simplified game estimate, not an official Barnett calculation.")

    if s.get("local_finance_last_update"):
        last = s.local_finance_last_update
        st.markdown("#### Latest annual local-finance report")
        st.write(last.get("notice", "No report available."))
        x, y, z = st.columns(3)
        x.metric("Annual fiscal effect", f"£{float(last.get('annual_cost_bn', 0)):.2f}bn")
        y.metric("Funding pressure", f"{float(last.get('funding_pressure', 0)):.0f}/100")
        z.metric("Service delivery", f"{float(last.get('service_delivery', 0)):.0f}/100")
    if s.get("local_finance_history"):
        with st.expander("Local finance history"):
            st.dataframe(list(reversed(s.local_finance_history)), hide_index=True, use_container_width=True)

    with st.expander("What the Chancellor can and cannot control"):
        st.markdown(
            "- **Can control:** the central grant settlement, regional growth funds and the broad framework for council tax flexibility.\n"
            "- **Can influence:** devolved block-grant consequentials through changes in comparable spending in England.\n"
            "- **Cannot directly set:** individual council tax bills, council budgets or the spending choices of devolved governments.\n"
            "- **Trade-off:** tighter settlements improve the Treasury's annual balance but can weaken local services and increase political pressure."
        )
