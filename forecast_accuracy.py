"""Treasury forecast vintages, realised outcomes and Chancellor review decisions.

Forecasts are captured once before the annual Spring transition. They are compared
with the realised economy after the full annual update, not on Streamlit reruns.
"""
import streamlit as st


TOLERANCES = {
    "real_growth": 0.85,
    "inflation": 0.70,
    "bank_rate": 0.65,
    "gilt_yield": 0.45,
    "debt_interest": 1.00,
    "deficit": 5.0,
    "headroom": 4.0,
    "debt_to_gdp": 1.25,
    "unemployment": 0.55,
    "real_wage_growth": 0.50,
    "productivity_growth": 0.10,
}
LABELS = {
    "real_growth": "Real GDP growth",
    "inflation": "Inflation",
    "bank_rate": "Bank Rate",
    "gilt_yield": "10-year gilt yield",
    "debt_interest": "Annual debt interest",
    "deficit": "Annual deficit",
    "headroom": "Fiscal headroom",
    "debt_to_gdp": "Debt-to-GDP",
    "unemployment": "Unemployment",
    "real_wage_growth": "Real wage growth",
    "productivity_growth": "Productivity growth",
}


def ensure(s=None):
    s = s or st.session_state
    s.setdefault("forecast_accuracy_vintages", [])
    s.setdefault("forecast_accuracy_history", [])
    s.setdefault("forecast_accuracy_latest", None)
    s.setdefault("active_forecast_review", None)
    s.setdefault("forecast_accuracy_last_settled", "")
    s.setdefault("forecast_reliability", 70.0)
    return s


def _period(term, year):
    return f"{int(term)}-{int(year)}"


def _clamp(value, low, high):
    return max(low, min(high, float(value)))


def record_vintage(s=None):
    """Capture the Treasury's one-year baseline forecast exactly once."""
    s = ensure(s)
    target_term = int(s.get("term", 1))
    target_year = int(s.get("year", 1)) + 1
    key = _period(target_term, target_year)
    if any(item.get("key") == key for item in s.forecast_accuracy_vintages):
        return next(item for item in s.forecast_accuracy_vintages if item.get("key") == key)

    import treasury
    rows = treasury.fiscal_outlook(1)
    baseline = next((row for row in rows if row.get("Scenario") == "Baseline"), None)
    if baseline is None:
        return None
    country = s.get("country") or {}
    forecast = {
        "real_growth": float(baseline.get("Real growth (%)", s.get("growth", 0.0))),
        "inflation": float(baseline.get("Inflation (%)", s.get("inflation", 2.0))),
        "bank_rate": float(baseline.get("Bank Rate (%)", s.get("interest_rate", 4.5))),
        "gilt_yield": float(baseline.get("Gilt yield (%)", s.get("gilt_yield", 4.5))),
        "debt_interest": float(baseline.get("Debt interest (£bn)", s.get("debt_interest_bill", 10.7))),
        "deficit": float(baseline.get("Annual deficit (£bn)", s.get("deficit", 0.0))),
        "headroom": float(baseline.get("Fiscal headroom (£bn)", s.get("headroom", 0.0))),
        "debt_to_gdp": float(baseline.get("Debt-to-GDP (%)", s.get("debt", 0.0))),
        "unemployment": float(baseline.get("Unemployment (%)", country.get("unemployment", 4.5))),
        "real_wage_growth": float(baseline.get("Real wage growth (%)", country.get("real_wages", 0.0))),
        "productivity_growth": float(baseline.get("Productivity growth (pp)", s.get("productivity_growth", 0.0))),
    }
    vintage = {
        "key": key,
        "term": target_term,
        "year": target_year,
        "prepared_term": int(s.get("term", 1)),
        "prepared_year": int(s.get("year", 1)),
        "forecast": forecast,
    }
    s.forecast_accuracy_vintages = (list(s.forecast_accuracy_vintages) + [vintage])[-8:]
    return vintage


def _actual(s):
    country = s.get("country") or {}
    return {
        "real_growth": float(s.get("growth", 0.0)),
        "inflation": float(s.get("inflation", 0.0)),
        "bank_rate": float(s.get("interest_rate", 0.0)),
        "gilt_yield": float(s.get("gilt_yield", 0.0)),
        "debt_interest": float(s.get("debt_interest_bill", 0.0)),
        "deficit": float(s.get("deficit", 0.0)),
        "headroom": float(s.get("headroom", 0.0)),
        "debt_to_gdp": float(s.get("debt", 0.0)),
        "unemployment": float(country.get("unemployment", 4.5)),
        "real_wage_growth": float(country.get("real_wages", 0.0)),
        "productivity_growth": float(s.get("productivity_growth", 0.0)),
    }


def settle_vintage(s=None):
    """Compare the next-year forecast with the fully realised Spring outcome once."""
    s = ensure(s)
    key = _period(int(s.get("term", 1)), int(s.get("year", 1)) + 1)
    if s.get("forecast_accuracy_last_settled") == key:
        return s.get("forecast_accuracy_latest")
    vintage = next((item for item in reversed(s.forecast_accuracy_vintages)
                    if item.get("key") == key), None)
    if vintage is None:
        return None

    forecast = dict(vintage.get("forecast", {}))
    actual = _actual(s)
    rows = []
    severity = 0.0
    for metric, tolerance in TOLERANCES.items():
        expected = float(forecast.get(metric, actual[metric]))
        realised = float(actual[metric])
        error = round(realised - expected, 3)
        ratio = abs(error) / tolerance
        severity = max(severity, ratio)
        rows.append({
            "metric": metric,
            "label": LABELS[metric],
            "forecast": round(expected, 2),
            "actual": round(realised, 2),
            "variance": error,
            "tolerance": tolerance,
        })

    severity = round(severity, 2)
    accuracy = round(_clamp(100.0 - min(65.0, severity * 13.0), 35.0, 100.0), 1)
    old_reliability = float(s.get("forecast_reliability", 70.0))
    reliability = round(_clamp(old_reliability * 0.75 + accuracy * 0.25, 0.0, 100.0), 1)
    material = [row for row in rows if abs(row["variance"]) >= row["tolerance"] * 0.55]
    material.sort(key=lambda row: abs(row["variance"]) / row["tolerance"], reverse=True)
    largest = material[0] if material else None
    record = {
        "key": key,
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)) + 1,
        "forecast": forecast,
        "actual": actual,
        "rows": rows,
        "material_misses": material[:5],
        "severity": severity,
        "accuracy": accuracy,
        "reliability_before": old_reliability,
        "reliability_after": reliability,
        "review_required": severity >= 1.0,
        "headline": (
            f"Treasury forecast missed on {largest['label'].lower()}"
            if largest else "Treasury forecast broadly on track"
        ),
        "resolution": "",
    }
    s.forecast_accuracy_history = (list(s.forecast_accuracy_history) + [record])[-20:]
    s.forecast_accuracy_latest = record
    s.forecast_accuracy_last_settled = key
    s.forecast_reliability = reliability

    if record["review_required"] and not s.get("active_forecast_review"):
        direction = "worse" if largest and largest["variance"] < 0 and largest["metric"] in {
            "real_growth", "headroom"
        } else "materially different"
        message = (
            f"The year-ahead central forecast was materially {direction} than the outcome. "
            f"The largest variance was {largest['label'].lower()}: forecast {largest['forecast']:+.2f}, "
            f"actual {largest['actual']:+.2f} (variance {largest['variance']:+.2f}). "
            "The Treasury must decide how to respond before the next policy programme proceeds."
        )
        issue = {
            "key": key,
            "headline": record["headline"],
            "message": message,
            "severity": severity,
            "misses": material[:5],
        }
        s.active_forecast_review = issue
        cards = list(s.get("event_cards", []))
        cards.append({
            "title": "Treasury forecast materially missed",
            "text": message,
            "summary": f"Forecast accuracy {accuracy:.0f}/100 · Treasury reliability {reliability:.0f}/100",
        })
        s.event_cards = cards[-12:]
        s.message = (str(s.get("message", "")) + " A Treasury forecast review is now awaiting your decision.").strip()
    return record


def resolve_review(choice, s=None):
    """Resolve a material forecast miss without repeating the realised fiscal effects."""
    s = ensure(s)
    issue = s.get("active_forecast_review")
    if not issue:
        return False, "There is no Treasury forecast review awaiting a decision."
    if choice not in {"accept", "commission", "ignore"}:
        return False, "Choose a valid Treasury response."

    if choice == "accept":
        s.officials_confidence = round(_clamp(float(s.get("officials_confidence", 70.0)) + 2.5, 0, 100), 1)
        s.market_conf = round(_clamp(float(s.get("market_conf", 50.0)) + 0.4, 0, 100), 1)
        s.pm_trust = round(_clamp(float(s.get("pm_trust", 70.0)) + 0.5, 0, 100), 1)
        outcome = "Accepted the revised forecast and instructed officials to update the fiscal baseline."
        message = "You accept the revised outlook. Publishing a clear update modestly restores confidence in the Treasury's handling of the miss."
    elif choice == "commission":
        capital = int(s.get("political_capital_points", 0))
        if capital < 1:
            return False, "You need one political-capital point to commission an independent review."
        s.political_capital_points = capital - 1
        s.headroom = round(float(s.get("headroom", 0.0)) - 0.35, 1)
        s.deficit = round(max(0.0, float(s.get("deficit", 0.0)) + 0.35), 1)
        s.officials_confidence = round(_clamp(float(s.get("officials_confidence", 70.0)) + 5.0, 0, 100), 1)
        s.market_conf = round(_clamp(float(s.get("market_conf", 50.0)) + 1.0, 0, 100), 1)
        outcome = "Commissioned an independent review of the forecast assumptions and Treasury methodology."
        message = "An independent review is commissioned. It costs £0.35bn and one political-capital point, but reassures officials and markets that the miss will be examined."
    else:
        s.officials_confidence = round(_clamp(float(s.get("officials_confidence", 70.0)) - 4.5, 0, 100), 1)
        s.market_conf = round(_clamp(float(s.get("market_conf", 50.0)) - 1.2, 0, 100), 1)
        s.pm_opinion = round(_clamp(float(s.get("pm_opinion", 50.0)) - 0.6, 0, 100), 1)
        outcome = "Chose not to respond to the forecast miss or commission further scrutiny."
        message = "You move on without a review. It avoids an immediate cost, but Treasury officials and markets question whether the warning has been taken seriously."

    s.active_forecast_review = None
    latest = dict(s.get("forecast_accuracy_latest") or {})
    latest["resolution"] = outcome
    latest["resolved_choice"] = choice
    s.forecast_accuracy_latest = latest
    history = list(s.get("forecast_accuracy_history", []))
    if history and history[-1].get("key") == latest.get("key"):
        history[-1] = latest
    s.forecast_accuracy_history = history[-20:]
    log = list(s.get("officials_log", []))
    log.append({
        "period": f"Term {issue.get('key', '').replace('-', ', Year ')}",
        "source": "Permanent Secretary",
        "title": "Annual forecast review",
        "choice": choice,
        "view": "Chancellor's decision",
        "note": outcome,
    })
    s.officials_log = log[-30:]
    s.message = message
    return True, message


def render_dashboard(s=None):
    """Show forecast credibility and recent differences on the Treasury position page."""
    s = ensure(s)
    st.markdown("#### Treasury forecast record")
    latest = s.get("forecast_accuracy_latest")
    reliability = float(s.get("forecast_reliability", 70.0))
    cols = st.columns(3)
    cols[0].metric("Forecast reliability", f"{reliability:.0f}/100")
    cols[1].metric("Forecasts assessed", str(len(s.get("forecast_accuracy_history", []))))
    cols[2].metric("Review status", "Decision due" if s.get("active_forecast_review") else "Up to date")
    if s.get("active_forecast_review"):
        st.warning("A material forecast miss is awaiting your response in the Decisions tab.")
    if latest:
        st.caption(f"Latest assessment · Term {latest.get('term', 1)}, Year {latest.get('year', 1)} · {latest.get('headline', '')}")
        st.dataframe([
            {
                "Measure": row["label"],
                "Treasury forecast": row["forecast"],
                "Realised": row["actual"],
                "Variance": f"{row['variance']:+.2f}",
            }
            for row in latest.get("rows", [])
        ], hide_index=True, use_container_width=True)
        if latest.get("resolution"):
            st.caption("Chancellor's response: " + latest["resolution"])
    else:
        st.caption("The first year-ahead forecast will be assessed at the next Spring transition.")
    history = list(s.get("forecast_accuracy_history", []))
    if history:
        with st.expander("Previous forecast assessments", expanded=False):
            st.dataframe([
                {
                    "Period": f"Term {item.get('term', 1)} · Year {item.get('year', 1)}",
                    "Accuracy": f"{float(item.get('accuracy', 0)):.0f}/100",
                    "Largest variance": item.get("headline", ""),
                    "Response": item.get("resolved_choice", "No material review"),
                }
                for item in reversed(history[-10:])
            ], hide_index=True, use_container_width=True)


def render_review(s=None):
    """Present the required Chancellor response to a material annual forecast miss."""
    s = ensure(s)
    issue = s.get("active_forecast_review")
    if not issue:
        st.info("No forecast review is awaiting a decision.")
        return
    st.markdown("# Treasury forecast review")
    st.caption(f"Term {int(s.get('term', 1))} · Year {int(s.get('year', 1))} · Annual economic update")
    st.warning(issue.get("message", "The Treasury's central forecast materially differed from the outcome."))
    misses = issue.get("misses", [])
    if misses:
        st.markdown("#### Largest forecast variances")
        st.dataframe([
            {
                "Measure": row["label"],
                "Forecast": row["forecast"],
                "Realised": row["actual"],
                "Variance": f"{row['variance']:+.2f}",
            }
            for row in misses
        ], hide_index=True, use_container_width=True)
    st.markdown("#### Your response as Chancellor")
    st.caption("The realised economic effects have already been applied. These choices change credibility and scrutiny, not the Budget ledger or last year's figures.")
    a, b, c = st.columns(3)
    with a:
        if st.button("Accept the revised forecast", type="primary", use_container_width=True):
            resolve_review("accept", s)
            st.rerun()
    with b:
        capital = int(s.get("political_capital_points", 0))
        if st.button("Commission independent review · £0.35bn + 1 capital",
                      disabled=capital < 1, use_container_width=True):
            resolve_review("commission", s)
            st.rerun()
    with c:
        if st.button("Ignore the warning", use_container_width=True):
            resolve_review("ignore", s)
            st.rerun()
