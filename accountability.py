"""National audit, parliamentary scrutiny and election reckoning.

The module turns the Government's delivery, fiscal and public-service record into
an annual audit trail. It is deliberately separate from the Budget ledgers.
"""
import streamlit as st


def _clamp(value):
    return max(0.0, min(100.0, float(value)))


def _project_summary(s):
    projects = list(s.get("national_investment_projects", []))
    if not projects:
        return {"total": 0, "completed": 0, "delayed": 0, "active": 0, "score": 60.0}
    completed = sum(1 for p in projects if p.get("status") == "Completed")
    delayed = sum(1 for p in projects if p.get("status") == "Delayed")
    active = sum(1 for p in projects if p.get("status") in ("Approved", "Under construction", "Delayed"))
    score = _clamp(65 + 18 * completed / len(projects) - 12 * delayed / len(projects))
    return {"total": len(projects), "completed": completed, "delayed": delayed,
            "active": active, "score": round(score, 1)}


def build_audit(s, report=None):
    """Create an auditable annual assessment from the year's realised outcomes."""
    report = report or s.get("latest_annual_report") or {}
    mission = report.get("mission") or s.get("mission_latest") or {}
    mission_score = _clamp(mission.get("score", 55))
    projects = _project_summary(s)
    strategy = None
    try:
        import regional_economy
        strategy = regional_economy.strategy_snapshot(s)
    except Exception:
        strategy = None
    regional_score = 60.0
    if strategy:
        elapsed = max(1, int(strategy.get("elapsed_years", 0)))
        expected = min(100.0, float(strategy.get("target_percent", 20)) * elapsed / 5)
        regional_score = _clamp(65 + (float(strategy.get("progress_percent", 0)) - expected) * 0.8)
    categories = {
        "Government delivery": round(mission_score),
        "Public services": int(report.get("services", 50)),
        "Fiscal credibility": int(report.get("fiscal", 50)),
        "National investment": round(projects["score"]),
        "Regional outcomes": round(regional_score),
        "Economic performance": int(report.get("economic", 50)),
    }
    overall = round(sum(categories.values()) / len(categories))
    findings = []
    if categories["Fiscal credibility"] < 45 or float(report.get("headroom", 0)) < 0:
        findings.append({"code": "fiscal", "title": "Fiscal credibility and value for money",
                         "severity": "High" if float(report.get("headroom", 0)) < 0 else "Moderate",
                         "detail": "The fiscal position or headroom record requires explanation and stronger controls.",
                         "recommendation": "Publish a corrective fiscal plan and subject major new commitments to independent costing."})
    if categories["Public services"] < 45:
        findings.append({"code": "services", "title": "Public-service outcomes",
                         "severity": "High", "detail": "Service outcomes remain weak despite the resources committed.",
                         "recommendation": "Set measurable service recovery milestones and report delivery quarterly."})
    if categories["Government delivery"] < 45:
        findings.append({"code": "delivery", "title": "Government programme delivery",
                         "severity": "High", "detail": "Too many programme commitments have not translated into completed outcomes.",
                         "recommendation": "Require named departmental owners, delivery dates and published progress evidence."})
    if projects["delayed"]:
        findings.append({"code": "investment", "title": "National investment project delays",
                         "severity": "Moderate", "detail": f"{projects['delayed']} national investment project(s) are delayed.",
                         "recommendation": "Publish revised delivery dates, cost-to-complete estimates and recovery plans."})
    if strategy and strategy.get("elapsed_years", 0) >= 2 and categories["Regional outcomes"] < 45:
        findings.append({"code": "regional", "title": "Regional productivity convergence",
                         "severity": "Moderate", "detail": "The regional productivity gap is not narrowing at the pace required by the adopted target.",
                         "recommendation": "Reassess project sequencing and publish region-level productivity milestones."})
    return {
        "term": int(s.get("term", 1)), "year": int(s.get("year", 1)),
        "overall": overall,
        "grade": "A" if overall >= 85 else "B" if overall >= 70 else "C" if overall >= 55 else "D" if overall >= 40 else "F",
        "categories": categories, "findings": findings, "projects": projects,
        "mission_score": round(mission_score), "regional_strategy": strategy,
        "published": True,
    }


def create_annual_audit(s=None, report=None):
    s = s or st.session_state
    audits = list(s.get("national_audits", []))
    term, year = int(s.get("term", 1)), int(s.get("year", 1))
    existing = next((a for a in audits if int(a.get("term", -1)) == term and int(a.get("year", -1)) == year), None)
    if existing:
        return existing
    audit = build_audit(s, report)
    audits.append(audit)
    s.national_audits = audits[-25:]
    s.latest_national_audit = audit
    queue = list(s.get("accountability_investigations", []))
    for finding in audit["findings"]:
        sequence = int(s.get("accountability_sequence", 0)) + 1
        s.accountability_sequence = sequence
        queue.append({
            "id": sequence, "term": term, "year": year,
            "title": finding["title"], "code": finding["code"],
            "severity": finding["severity"], "detail": finding["detail"],
            "recommendation": finding["recommendation"], "status": "Open",
            "response": "",
        })
    s.accountability_investigations = queue[-40:]
    if audit["overall"] >= 78:
        s.approval = round(_clamp(s.get("approval", 50) + 0.4), 1)
        audit["public_reaction"] = "The audit gives the Government credit for measurable progress."
    elif audit["overall"] < 45:
        s.approval = round(_clamp(s.get("approval", 50) - 0.6), 1)
        audit["public_reaction"] = "The audit intensifies criticism that Government promises are not being delivered."
    else:
        audit["public_reaction"] = "The public response is mixed: progress is recognised, but weaknesses remain."
    s.latest_national_audit = audit
    return audit


def resolve_investigation(s, investigation_id, response):
    rows = list(s.get("accountability_investigations", []))
    item = next((r for r in rows if int(r.get("id", -1)) == int(investigation_id)), None)
    if not item or item.get("status") != "Open":
        return False
    if response == "Accept recommendations":
        cost = 0.5 if item.get("severity") == "High" else 0.25
        s.headroom = round(float(s.get("headroom", 0)) - cost, 1)
        s.deficit = round(float(s.get("deficit", 0)) + cost, 1)
        s.officials_confidence = round(_clamp(s.get("officials_confidence", 70) + 4), 1)
        s.media_opinion = round(_clamp(s.get("media_opinion", 50) + 2), 1)
        s.approval = round(_clamp(s.get("approval", 50) + 1), 1)
        outcome = f"Recommendations accepted; £{cost:.2f}bn allocated to corrective action."
    elif response == "Publish the evidence":
        s.officials_confidence = round(_clamp(s.get("officials_confidence", 70) + 2), 1)
        s.media_opinion = round(_clamp(s.get("media_opinion", 50) + 1), 1)
        outcome = "Evidence published; transparency improves, but the underlying issue remains under review."
    elif response == "Defend the Government's record":
        s.pm_opinion = round(_clamp(s.get("pm_opinion", 50) + 1), 1)
        s.media_opinion = round(_clamp(s.get("media_opinion", 50) - (3 if item.get("severity") == "High" else 1)), 1)
        outcome = "The Government defended its record; political support is steadied, but scrutiny remains."
    else:
        return False
    item["status"] = "Responded"
    item["response"] = response
    item["outcome"] = outcome
    s.accountability_investigations = rows
    s.accountability_history = list(s.get("accountability_history", [])) + [{
        "term": item["term"], "year": item["year"], "title": item["title"],
        "severity": item["severity"], "response": response, "outcome": outcome,
    }]
    return True


def election_verdict(s=None):
    s = s or st.session_state
    audits = [a for a in s.get("national_audits", []) if int(a.get("term", -1)) == int(s.get("term", 1))]
    if not audits:
        return {"score": 50, "grade": "Not assessed", "audits": 0, "findings": 0,
                "summary": "There is not yet a complete annual audit record for this Government."}
    score = round(sum(float(a.get("overall", 50)) for a in audits) / len(audits))
    findings = sum(len(a.get("findings", [])) for a in audits)
    open_items = sum(1 for i in s.get("accountability_investigations", [])
                     if int(i.get("term", -1)) == int(s.get("term", 1)) and i.get("status") == "Open")
    grade = "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 55 else "D" if score >= 40 else "F"
    summary = (
        "A strong record of delivery and public value." if score >= 75 else
        "A mixed record: some meaningful achievements, alongside visible delivery gaps." if score >= 55 else
        "A poor record, with unresolved weaknesses in delivery, services or fiscal credibility."
    )
    return {"score": score, "grade": grade, "audits": len(audits),
            "findings": findings, "open_investigations": open_items, "summary": summary}


def record_election_reckoning(s=None):
    s = s or st.session_state
    verdict = election_verdict(s)
    archive = list(s.get("accountability_election_archive", []))
    term = int(s.get("term", 1))
    existing = next((r for r in archive if int(r.get("term", -1)) == term), None)
    if existing:
        return existing
    result = dict(verdict, term=term, election_result=dict(s.get("election_result") or {}))
    archive.append(result)
    s.accountability_election_archive = archive[-10:]
    return result


def render(s=None):
    s = s or st.session_state
    st.markdown("### National Performance Audit")
    st.caption("An annual assessment of what the Government delivered, what it cost and whether the public saw better outcomes. Modelled scrutiny, not an official audit.")
    audits = list(s.get("national_audits", []))
    latest = s.get("latest_national_audit")
    if latest:
        cols = st.columns(3)
        cols[0].metric("Audit grade", f"{latest.get('grade', '—')} · {latest.get('overall', 0)}/100")
        cols[1].metric("Findings", str(len(latest.get("findings", []))))
        open_count = sum(1 for item in s.get("accountability_investigations", []) if item.get("status") == "Open")
        cols[2].metric("Open investigations", str(open_count))
        for name, value in latest.get("categories", {}).items():
            st.progress(float(value) / 100.0, text=f"{name} · {value}/100")
        st.info(latest.get("public_reaction", "The audit has been published."))
    else:
        st.info("The first National Performance Audit will be published at the end of the first in-game year.")
    st.divider()
    st.markdown("### Parliamentary and independent scrutiny")
    open_items = [item for item in s.get("accountability_investigations", []) if item.get("status") == "Open"]
    if not open_items:
        st.success("No unresolved audit investigations. New scrutiny can be opened by future annual audits.")
    for item in open_items:
        with st.expander(f"{item['severity']} · {item['title']} · Term {item['term']}, Year {item['year']}", expanded=True):
            st.write(item["detail"])
            st.caption("Committee recommendation: " + item["recommendation"])
            choice = st.radio(
                "Government response",
                ["Publish the evidence", "Accept recommendations", "Defend the Government's record"],
                key=f"accountability_response_{item['id']}",
                horizontal=True,
            )
            cost = 0.5 if item["severity"] == "High" else 0.25
            st.caption(f"Accepting recommendations costs £{cost:.2f}bn and changes the fiscal position transparently.")
            if st.button("Submit formal response", key=f"accountability_submit_{item['id']}"):
                if resolve_investigation(s, item["id"], choice):
                    st.success("Response recorded.")
                    st.rerun()
    with st.expander("Published audit archive", expanded=False):
        for audit in reversed(audits):
            st.markdown(f"**Term {audit['term']}, Year {audit['year']} · Grade {audit['grade']} ({audit['overall']}/100)**")
            st.caption(" · ".join(f"{key}: {value}/100" for key, value in audit.get("categories", {}).items()))
            for finding in audit.get("findings", []):
                st.write(f"• {finding['severity']}: {finding['title']}")
    verdict = election_verdict(s)
    st.divider()
    st.markdown("### Election reckoning")
    st.metric("Current term audit average", f"{verdict['grade']} · {verdict['score']}/100")
    st.write(verdict["summary"])
    st.caption(f"{verdict['audits']} annual audit(s) · {verdict['findings']} findings · {verdict.get('open_investigations', 0)} unresolved investigations. The full reckoning is shown when the electorate votes.")


