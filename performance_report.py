"""End-of-year Chancellor performance reports."""
import streamlit as st


def _clamp(x):
    return max(0.0, min(100.0, float(x)))


def create_report():
    s = st.session_state
    year = int(s.get("year", 1))
    reports = list(s.get("annual_reports", []))
    if any(int(r.get("year", -1)) == year and int(r.get("term", -1)) == int(s.get("term", 1)) for r in reports):
        return None

    growth = float(s.get("growth", 0))
    inflation = float(s.get("inflation", 2))
    market = float(s.get("market_conf", 50))
    headroom = float(s.get("headroom", 0))
    deficit = float(s.get("deficit", 0))
    debt = float(s.get("debt", 0))
    approval = float(s.get("approval", 50))
    pm = float(s.get("pm_opinion", 50))
    party = float(s.get("party_opinion", 50))
    cabinet = float(s.get("cab_opinion", 50))

    economic = _clamp(55 + growth * 7 - abs(inflation - 2) * 5 + (market - 50) * 0.18)
    try:
        import country
        service = _clamp(country._overall(s.get("country", {})) * 100)
    except Exception:
        service = 50.0
    fiscal = _clamp(55 + headroom * 2.2 - max(0, deficit - 80) * 0.10 - max(0, debt - 90) * 0.12)
    political = _clamp(0.35 * approval + 0.25 * pm + 0.20 * party + 0.20 * cabinet)
    overall = round(0.25 * economic + 0.25 * service + 0.25 * fiscal + 0.25 * political)
    grade = "A+" if overall >= 90 else "A" if overall >= 80 else "B" if overall >= 70 else "C" if overall >= 60 else "D" if overall >= 50 else "E" if overall >= 40 else "F"

    report = {
        "term": int(s.get("term", 1)), "year": year,
        "economic": round(economic), "services": round(service),
        "fiscal": round(fiscal), "political": round(political),
        "overall": overall, "grade": grade,
        "growth": round(growth, 2), "inflation": round(inflation, 2),
        "headroom": round(headroom, 1), "deficit": round(deficit, 1),
        "debt": round(debt, 1), "approval": round(approval, 1),
        "market_conf": round(market, 1),
        "summary": (
            "A strong all-round year, with the Treasury balancing growth, services and political authority."
            if overall >= 80 else
            "A respectable year, although there are areas where the Chancellor needs to improve."
            if overall >= 65 else
            "A mixed year. The Chancellor has made progress in some areas but weaknesses are becoming clear."
            if overall >= 50 else
            "A difficult year. Economic, fiscal or political problems have undermined the Chancellor's record."
        ),
    }
    reports.append(report)
    s.annual_reports = reports[-20:]
    s.latest_annual_report = report
    return report


def render():
    s = st.session_state
    st.markdown('### Annual performance reports')
    st.caption("An annual assessment of your record as Chancellor. Each category is scored out of 100; the overall rating weights all four equally.")
    reports = list(s.get("annual_reports", []))
    if not reports:
        st.info("Your first report will be produced at the end of your first in-game year.")
        return
    latest = reports[-1]
    st.markdown(f"## {latest['grade']} · {latest['overall']}/100")
    st.write(latest["summary"])
    cols = st.columns(4)
    for col, (label, key) in zip(cols, [("Economy", "economic"), ("Public services", "services"), ("Fiscal record", "fiscal"), ("Political standing", "political")]):
        col.metric(label, f"{latest[key]}/100")
    st.divider()
    st.markdown("#### Year-end figures")
    a, b, c = st.columns(3)
    a.metric("Real GDP growth", f"{latest['growth']:+.2f}%")
    b.metric("Inflation", f"{latest['inflation']:.2f}%")
    c.metric("Market confidence", f"{latest['market_conf']:.1f}/100")
    a, b, c = st.columns(3)
    a.metric("Fiscal headroom", f"£{latest['headroom']:.1f}bn")
    b.metric("Deficit", f"£{latest['deficit']:.1f}bn")
    c.metric("Debt", f"{latest['debt']:.1f}% GDP")
    with st.expander("📚 Previous annual reports", expanded=False):
        for item in reversed(reports[:-1]):
            st.markdown(f"**Term {item['term']}, Year {item['year']} — {item['grade']} ({item['overall']}/100)**")
            st.caption(f"Economy {item['economic']} · Services {item['services']} · Fiscal {item['fiscal']} · Political {item['political']}")
