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
    "regional_growth_fund_bn": 0.0,
    "local_finance_pressure": 42.0,
    "local_service_delivery": 62.0,
    "local_finance_history": [],
    "local_finance_last_update": None,
    "local_finance_last_period": "",
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
    period = f"{int(s.get('term', 1))}-{int(s.get('year', 1))}"
    if s.get("local_finance_last_period") == period:
        return False
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
        "council_tax_referendum_threshold_pct": round(referendum, 2),
        "social_care_precept_flexibility_pct": round(precept, 2),
        "barnett_pass_through_pct": round(float(s.get("barnett_pass_through_pct", 100)), 1),
        "notice": notice,
    }
    s.local_finance_history = (list(s.get("local_finance_history", [])) + [record])[-12:]
    s.local_finance_last_update = record
    s.local_finance_last_period = period
    s.local_finance_notice = notice
    s.message = (str(s.get("message", "")) + f" Local finance settlement: £{annual_cost:.2f}bn annual cost; "
                 f"council funding pressure is {s.local_finance_pressure:.0f}/100.").strip()
    return True


def review_settlement_keys(period):
    """Return the namespaced widget keys used by a Spending Review."""
    return {
        "local_grant_uplift_bn": f"sr_{period}_local_grant_uplift_bn",
        "barnett_pass_through_pct": f"sr_{period}_barnett_pass_through_pct",
        "regional_growth_fund_bn": f"sr_{period}_regional_growth_fund_bn",
        "council_tax_referendum_threshold": f"sr_{period}_council_tax_referendum_threshold",
        "social_care_precept_cap": f"sr_{period}_social_care_precept_cap",
    }


def render_spending_review_controls(period):
    """Let the Chancellor agree the local-government settlement as part of a Spending Review."""
    ensure()
    s = st.session_state
    keys = review_settlement_keys(period)
    st.markdown("#### Local government & devolved funding settlement")
    st.caption("Agree the central grant, regional growth fund and local-tax framework alongside departmental bids. These settings take effect with the next Spring update.")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        st.slider("Local government grant uplift (£bn per year)", -5.0, 10.0, 0.5,
                  value=float(s.get(keys["local_grant_uplift_bn"], s.local_grant_uplift_bn)),
                  key=keys["local_grant_uplift_bn"])
        st.slider("Regional growth and town-centre fund (£bn per year)", 0.0, 5.0, 0.25,
                  value=float(s.get(keys["regional_growth_fund_bn"], s.regional_growth_fund_bn)),
                  key=keys["regional_growth_fund_bn"])
        st.slider("Devolved funding pass-through (%)", 50, 150, 5,
                  value=int(s.get(keys["barnett_pass_through_pct"], s.barnett_pass_through_pct)),
                  key=keys["barnett_pass_through_pct"])
    with c2:
        st.slider("Council tax referendum threshold (%)", 0.0, 10.0, 0.5,
                  value=float(s.get(keys["council_tax_referendum_threshold"], s.council_tax_referendum_threshold)),
                  key=keys["council_tax_referendum_threshold"])
        st.slider("Adult social-care precept flexibility (%)", 0.0, 5.0, 0.25,
                  value=float(s.get(keys["social_care_precept_cap"], s.social_care_precept_cap)),
                  key=keys["social_care_precept_cap"])
        grant = float(s[keys["local_grant_uplift_bn"]])
        regional = float(s[keys["regional_growth_fund_bn"]])
        barnett = float(s[keys["barnett_pass_through_pct"]])
        cost = grant + regional + regional * 0.19 * barnett / 100.0
        st.metric("Recurring annual local settlement cost", f"£{cost:.2f}bn")
    return {field: s[key] for field, key in keys.items()}


def apply_spending_review_settlement(period):
    """Commit the local settlement controls only after the Spending Review is approved."""
    ensure()
    s = st.session_state
    for field, key in review_settlement_keys(period).items():
        if key in s:
            s[field] = float(s[key])
    s.local_finance_notice = (
        "Your local-government and devolved funding settlement has been approved through the Spending Review. "
        "Its fiscal and service effects begin at the next Spring update."
    )
    return current_settlement()


def current_settlement(s=None):
    ensure()
    s = s or st.session_state
    return {
        "local_grant_uplift_bn": round(float(s.local_grant_uplift_bn), 2),
        "barnett_pass_through_pct": round(float(s.barnett_pass_through_pct), 1),
        "regional_growth_fund_bn": round(float(s.regional_growth_fund_bn), 2),
        "council_tax_referendum_threshold": round(float(s.council_tax_referendum_threshold), 2),
        "social_care_precept_cap": round(float(s.social_care_precept_cap), 2),
    }


def render():
    """Read-only local-government and devolution monitor; policy is set in Spending Reviews."""
    ensure()
    s = st.session_state
    st.markdown("### Local government & devolution")
    st.caption("Monitor council finances, devolved funding and the effects of the latest Spending Review. New settlements are agreed through the scheduled Spending Review event.")
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

    st.markdown("#### Current approved settlement")
    settings = current_settlement(s)
    st.dataframe([
        {"Setting": "Local government grant uplift", "Approved value": f"£{settings['local_grant_uplift_bn']:.2f}bn/year"},
        {"Setting": "Regional growth fund", "Approved value": f"£{settings['regional_growth_fund_bn']:.2f}bn/year"},
        {"Setting": "Barnett-style pass-through", "Approved value": f"{settings['barnett_pass_through_pct']:.0f}%"},
        {"Setting": "Council tax referendum threshold", "Approved value": f"{settings['council_tax_referendum_threshold']:.1f}%"},
        {"Setting": "Adult social-care precept flexibility", "Approved value": f"{settings['social_care_precept_cap']:.2f}%"},
    ], hide_index=True, use_container_width=True)
    st.caption("The devolved funding calculation is a simplified game estimate, not an official Barnett formula. Councils and devolved governments retain their own spending responsibilities.")

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
