"""Persistent left-hand Chancellor's Desk sidebar."""
import html
import streamlit as st

import engine
import politics
import budget
import state
import cabinet_management
import political_pressure
from theme import phase_info


def _safe(value):
    return html.escape(str(value))


def _tile(label, value, detail="", tone="neutral", progress=None):
    meter = ""
    if progress is not None:
        amount = max(0.0, min(100.0, float(progress)))
        meter = (
            "<div class='desk-meter' role='img' "
            f"aria-label='{amount:.0f} out of 100'>"
            f"<span style='width:{amount:.1f}%'></span></div>"
        )
    return (
        f"<div class='desk-tile {tone}'>"
        f"<span class='desk-tile-label'>{_safe(label)}</span>"
        f"<strong>{_safe(value)}</strong>"
        f"<small>{_safe(detail)}</small>"
        f"{meter}</div>"
    )


def _priority_items(s):
    """Compact inbox of decisions that are live in the current game state."""
    items = []
    checks = (
        ("active_pm_ultimatum", "NOW", "Prime Minister's ultimatum · respond before your position collapses", "urgent"),
        ("active_pm_intervention", "NOW", "Number 10 intervention · decide how to handle the economic strategy committee", "urgent"),
        ("active_gilt_emergency", "NOW", "Gilt-market emergency · stabilise market confidence", "urgent"),
        ("active_forecast_review", "NOW", "Treasury forecast review · respond to the revised outlook", "urgent"),
        ("active_financial_crisis", "NOW", "Financial stability crisis · decide the Government response", "urgent"),
        ("active_crisis", "NOW", "Emergency decision · resolve the active crisis", "urgent"),
        ("active_emergency_budget", "NOW", "Emergency Budget · complete the fiscal response", "urgent"),
        ("spending_review_due", "NOW", "Spending Review · agree departmental settlements", "urgent"),
        ("autumn_statement_due", "NOW", "Autumn Statement · publish the fiscal update or proceed without one", "urgent"),
        ("active_weekly_event", "ACTION", "Treasury briefing · respond to this week's event", "caution"),
        ("local_election_due", "ACTION", "Local elections · review the results and political consequences", "caution"),
        ("active_dispute", "ACTION", "Cabinet dispute · settle the ministerial disagreement", "caution"),
        ("active_request", "ACTION", "Ministerial request · decide whether to support the proposal", "caution"),
        ("active_pm_meeting", "PENDING", "Private meeting with the Prime Minister", "neutral"),
        ("active_opposition_attack", "PENDING", "Opposition economic attack · a response is available", "neutral"),
    )
    for key, tag, label, tone in checks:
        if s.get(key):
            items.append((tag, label, tone))
    if not items and int(s.get("block", 1)) == 3 and not s.get("budget_passed"):
        items.append(("CURRENT", "Spring Budget · prepare the package and secure the Commons vote", "caution"))
    return items


def _score_tone(value, urgent_below=30, caution_below=45):
    value = float(value)
    if value < urgent_below:
        return "urgent", "Critical"
    if value < caution_below:
        return "caution", "Under pressure"
    return "good", "Holding up"


def _warnings(s):
    items = []
    if float(s.get("headroom", 0)) < 0:
        items.append(("urgent", "Fiscal headroom is negative"))
    elif float(s.get("headroom", 0)) < 3:
        items.append(("caution", "Fiscal headroom is narrow"))
    if float(s.get("market_conf", 50)) < 40:
        items.append(("urgent", "Gilt markets are fragile"))
    if float(s.get("inflation", 2)) >= 4.5:
        items.append(("caution", "Inflation is above 4.5%"))
    if float(s.get("backbench_opinion", 60)) < 40:
        items.append(("urgent", "Backbench rebellion risk"))
    if float(s.get("pm_opinion", 50)) < 35:
        items.append(("caution", "Prime Minister's confidence is low"))
    if float(s.get("cab_opinion", 50)) < 35:
        items.append(("caution", "Cabinet support is critically low"))
    if float(s.get("party_opinion", 50)) < 35:
        items.append(("caution", "Party unity is critically low"))
    if float(s.get("backbench_opinion", 60)) < 30:
        items.append(("urgent", "Backbench rebellion risk is acute"))
    if s.get("active_crisis"):
        items.append(("urgent", "An immediate crisis needs a decision"))
    if s.get("active_dispute"):
        items.append(("caution", "A ministerial dispute is unresolved"))
    if s.get("active_weekly_event"):
        items.append(("caution", "A new Treasury event needs your response"))
    return items


def _economic_advice(s):
    growth = float(s.get("growth", 0))
    inflation = float(s.get("inflation", 2))
    headroom = float(s.get("headroom", 0))
    if headroom < 0:
        return "The fiscal rules are under pressure. Avoid permanent unfunded commitments and prepare a credible correction."
    if inflation >= 4.5:
        return "Inflation remains elevated. Broad demand stimulus could complicate the Bank of England's task."
    if growth < 0:
        return "The economy is contracting. Protect high-value investment while checking the affordability of temporary support."
    if growth < 1:
        return "Growth is subdued. Prioritise productivity, skills and investment with credible delivery plans."
    return "Growth is holding up. Preserve the fiscal buffer and focus on measures that strengthen long-term productivity."


def _permanent_secretary_advice(s):
    log = list(s.get("officials_log", []))
    if log:
        latest = log[-1]
        return f"{latest.get('view', 'Private advice')}: {latest.get('note', '')}"
    headroom = float(s.get("headroom", 0))
    if headroom < 3:
        return "I recommend retaining a reserve against forecast revisions. A small amount of headroom can disappear quickly."
    return "The Treasury recommends transparent costings, a prudent margin against forecast errors and a clear distinction between temporary and permanent spending."


def render(on_restart):
    s = st.session_state
    with st.sidebar:
        st.markdown(
            "<div class='desk-brand'><div class='desk-monogram'>£</div>"
            "<div><div class='desk-kicker'>HM TREASURY · PRIVATE OFFICE</div>"
            "<div class='desk-title'>Chancellor's Desk</div></div></div>",
            unsafe_allow_html=True,
        )
        if s.get("step") != "game":
            st.caption("Start a simulation to open your permanent Treasury briefing panel.")
            return

        phase = phase_info(int(s.get("block", 1)))
        year = int(s.get("year", 1))
        term = int(s.get("term", 1))
        if year > 5:
            period = f"Term {term} · General election"
            phase_name = "Election period"
        else:
            period = f"Term {term} · Year {year} of 5"
            phase_name = phase["name"]
        st.markdown(
            f"<div class='desk-period'><span>{_safe(period)}</span><strong>{_safe(phase_name)}</strong>"
            f"<small>{_safe(s.get('party', 'Government'))} · {_safe(s.get('difficulty', 'Normal'))}</small></div>",
            unsafe_allow_html=True,
        )

        # Resolve registries before assembling the at-a-glance Cabinet briefing.
        budget.ensure()
        cabinet_management.ensure(s)
        cabinet_health = cabinet_management.cabinet_health(s)
        ministers = s.get("cabinet_ministers", {})
        active_posts = [
            (key, name) for key, name in ministers.items()
            if key in budget.DEPARTMENT_MINISTERS
            and name
            and not str(name).startswith(("Vacant", "New appointment"))
        ]

        priorities = _priority_items(s)
        warnings = _warnings(s)
        if priorities:
            first_tag, first_label, first_tone = priorities[0]
            brief_status = "ACTION REQUIRED" if first_tag == "NOW" else "ATTENTION"
            brief_detail = first_label
            brief_class = first_tone
        elif warnings:
            brief_status = "WATCH"
            brief_detail = warnings[0][1]
            brief_class = "caution"
        else:
            brief_status = "STABLE"
            brief_detail = f"No immediate decision is waiting. Current phase: {phase_name}."
            brief_class = "good"
        st.markdown(
            "<div class='desk-command-card " + brief_class + "'>"
            "<div class='desk-command-top'><span>PRIVATE OFFICE BRIEFING</span>"
            f"<strong>{_safe(brief_status)}</strong></div>"
            f"<div class='desk-command-main'>{_safe(brief_detail)}</div>"
            f"<div class='desk-command-foot'>{len(priorities)} live task(s) · {len(warnings)} watch item(s)</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        with st.expander(f"Priority inbox · {len(priorities)}", expanded=bool(priorities and priorities[0][0] == "NOW")):
            if priorities:
                for tag, label, tone in priorities[:7]:
                    st.markdown(
                        f"<div class='desk-action-item {tone}'>"
                        f"<span>{_safe(tag)}</span><strong>{_safe(label)}</strong></div>",
                        unsafe_allow_html=True,
                    )
                if len(priorities) > 7:
                    st.caption(f"{len(priorities) - 7} more item(s) are waiting in the main workspace.")
            else:
                st.markdown(
                    "<div class='desk-clear'><span>✓</span> No immediate decisions are waiting.</div>",
                    unsafe_allow_html=True,
                )

        # Political standing: the four relationships a Chancellor must monitor.
        st.markdown("<div class='desk-section-title'>POLITICAL STANDING</div>", unsafe_allow_html=True)
        approval = float(s.get("approval", 0))
        pm_confidence = float(s.get("pm_opinion", 0))
        cabinet_support = float(s.get("cab_opinion", 0))
        party_unity = float(s.get("party_opinion", 0))
        political_tiles = []
        for label, value, thresholds in (
            ("Public approval", approval, (30, 45)),
            ("PM confidence", pm_confidence, (35, 50)),
            ("Cabinet support", cabinet_support, (35, 50)),
            ("Party unity", party_unity, (35, 50)),
        ):
            tone, status = _score_tone(value, *thresholds)
            shown = f"{value:.0f}%" if label == "Public approval" else f"{value:.0f}/100"
            political_tiles.append(_tile(label, shown, status, tone, progress=value))
        st.markdown("<div class='desk-grid'>" + "".join(political_tiles) + "</div>", unsafe_allow_html=True)
        with st.expander("Political and parliamentary position", expanded=False):
            p1, p2 = st.columns(2)
            p1.metric("Personal PM trust", f"{float(s.get('pm_trust', 0)):.0f}/100")
            p2.metric("Backbench support", f"{float(s.get('backbench_opinion', 0)):.0f}/100")
            p1, p2 = st.columns(2)
            p1.metric("Political capital", f"{int(s.get('political_capital_points', 0))}/5")
            p2.metric("Active ministerial posts", f"{len(active_posts)}")

        # Economic watch: keep the values compact and always visible.
        st.markdown("<div class='desk-section-title'>TREASURY WATCH</div>", unsafe_allow_html=True)
        headroom = float(s.get("headroom", 0))
        growth = float(s.get("growth", 0))
        inflation = float(s.get("inflation", 0))
        bank_rate = float(s.get("interest_rate", 0))
        headroom_tone = "urgent" if headroom < 0 else ("caution" if headroom < 3 else "good")
        headroom_label = "Fiscal gap" if headroom < 0 else ("Thin buffer" if headroom < 3 else "Buffer available")
        growth_tone = "urgent" if growth < 0 else ("caution" if growth < 1 else "good")
        growth_label = "Contracting" if growth < 0 else ("Subdued" if growth < 1 else "Expanding")
        inflation_tone = "urgent" if inflation >= 4.5 else ("caution" if inflation >= 3 else "good")
        inflation_label = "High pressure" if inflation >= 4.5 else ("Above preferred range" if inflation >= 3 else "Contained")
        economic_tiles = [
            _tile("Fiscal headroom", f"£{headroom:.1f}bn", headroom_label, headroom_tone),
            _tile("GDP growth", f"{growth:+.1f}%", growth_label, growth_tone),
            _tile("Inflation", f"{inflation:.1f}%", inflation_label, inflation_tone),
            _tile("Bank Rate", f"{bank_rate:.2f}%", "Central-bank policy rate", "neutral"),
        ]
        st.markdown("<div class='desk-grid'>" + "".join(economic_tiles) + "</div>", unsafe_allow_html=True)
        with st.expander("Fiscal and market detail", expanded=False):
            a, b = st.columns(2)
            a.metric("Annual deficit", f"£{float(s.get('deficit', 0)):.1f}bn")
            b.metric("Debt / GDP", f"{float(s.get('debt', 0)):.1f}%")
            a, b = st.columns(2)
            market_conf = float(s.get("market_conf", 0))
            a.metric("Market confidence", f"{market_conf:.0f}/100")
            b.metric("10-year gilt yield", f"{float(s.get('gilt_yield', 0)):.2f}%")
            a, b = st.columns(2)
            a.metric("Political capital", f"{int(s.get('political_capital_points', 0))}/5")
            b.metric("Contingency reserve", f"£{float(s.get('contingency_reserve', 0)):.1f}bn")
            forecast = s.get("obr_latest") or {}
            if forecast:
                st.markdown("**Latest forecast revision**")
                f1, f2 = st.columns(2)
                f1.metric("Forecast growth", f"{float(forecast.get('growth', growth)):+.2f}%")
                f2.metric("Forecast headroom", f"£{float(forecast.get('headroom', headroom)):.1f}bn")


        # Detailed Cabinet controls remain available on demand.
        reshuffle_used = int(s.get("term", 1)) in s.get("cabinet_reshuffle_terms", [])
        weak_count = len(cabinet_health.get("weak_ministers", [])) + int(cabinet_health.get("low_loyalty", 0))
        with st.expander(f"Cabinet at a glance · {len(active_posts)} ministers · {weak_count} at risk", expanded=False):
            c1, c2 = st.columns(2)
            c1.metric("Average competence", f"{float(cabinet_health.get('competence', 0)):.0f}/100")
            c2.metric("Average loyalty", f"{float(cabinet_health.get('loyalty', 0)):.0f}/100")
            if cabinet_health.get("weak_ministers"):
                names_at_risk = ", ".join(item.get("minister", "Minister") for item in cabinet_health["weak_ministers"][:4])
                st.warning("Performance concerns: " + names_at_risk)
            elif weak_count:
                st.warning("Some ministerial relationships are at risk. Open Cabinet management for the detail.")
            else:
                st.caption("No ministers currently meet the low-performance or low-loyalty warning thresholds.")
        cabinet_label = f"Cabinet management · {len(active_posts)} ministers"
        with st.expander(cabinet_label, expanded=bool(s.get("active_dispute"))):
            if active_posts:
                health = cabinet_management.cabinet_health(s)
                h1, h2, h3 = st.columns(3)
                h1.metric("Average competence", str(round(health["competence"])) + "/100")
                h2.metric("Average loyalty", str(round(health["loyalty"])) + "/100")
                h3.metric("At-risk ministers", str(len(health["weak_ministers"]) + health["low_loyalty"]))
                if health["weak_ministers"] or health["low_loyalty"]:
                    st.caption("Persistent ministerial weakness now contributes to leadership pressure as well as departmental delivery and Cabinet relationships.")
                service_scores = s.get("public_service_scores", {})
                service_for = cabinet_management.SERVICE_FOR_DEPARTMENT
                roster = []
                for key, name in active_posts:
                    service = service_for.get(key, "")
                    roster.append({
                        "Department": budget.SPEND_DEFAULTS.get(key, {}).get("label", key.replace("_", " ").title()),
                        "Minister": name,
                        "Faction": cabinet_management.profile_for(s, key).get("faction", "Government"),
                        "Temperament": cabinet_management.profile_for(s, key).get("personality", "Pragmatist"),
                        "Competence": f"{float(s.ministerial_competence.get(key, 60)):.0f}/100",
                        "Loyalty": f"{float(s.get('ministerial_loyalty', {}).get(key, 60)):.0f}/100",
                        "Service": f"{float(service_scores.get(service, 0)):.0f}/100" if service else "Strategic",
                    })
                st.dataframe(roster, hide_index=True, use_container_width=True)
                appraisals = list(s.get("ministerial_latest_appraisals", []))
                if appraisals:
                    st.markdown("**Annual ministerial appraisals**")
                    appraisal_rows = [{
                        "Minister": row.get("minister", row.get("department", "")),
                        "Portfolio": budget.SPEND_DEFAULTS.get(row.get("department", ""), {}).get("label", row.get("department", "").replace("_", " ").title()),
                        "Grade": row.get("grade", "Not rated"),
                        "Score": f'{float(row.get("appraisal_score", 0)):.0f}/100',
                        "Review status": row.get("warning", "No formal concern"),
                        "Recommended action": row.get("recommendation", ""),
                    } for row in appraisals]
                    st.dataframe(appraisal_rows, hide_index=True, use_container_width=True)
                    at_risk = [row for row in appraisals if int(row.get("poor_years", 0)) >= 2]
                    if at_risk:
                        st.warning("Repeated underperformance: " + ", ".join(row.get("minister", row.get("department", "")) for row in at_risk) + ". Number 10 has been advised to review these portfolios; only the Prime Minister can decide on appointments.")
                    else:
                        st.caption("Appraisals combine ministerial competence, departmental service performance and the direction of travel. A first poor year triggers a private warning; repeated poor reviews prompt advice to Number 10.")
                st.caption("Faction and temperament are simulated game profiles, not claims about real ministers' personal beliefs. Temperament influences delivery, lobbying and rivalry; faction alignment affects loyalty after policy decisions.")
                rivalry_history = list(s.get("ministerial_rivalry_history", []))
                latest_rivalries = rivalry_history[-1].get("rows", []) if rivalry_history else []
                rivalry_rows = [
                    {"Portfolio rivalry": row["label"], "Ministers": row["ministers"], "Tension": f'{row["tension"]:.0f}/100'}
                    for row in latest_rivalries
                ]
                if rivalry_rows:
                    st.markdown("**Overlapping portfolio tensions**")
                    st.dataframe(rivalry_rows, hide_index=True, use_container_width=True)
                    st.caption("Tension rises when overlapping ministers diverge in competence, loyalty or repeated Treasury disputes. Serious rivalries can weaken Cabinet unity.")
                alliances = dict(s.get("ministerial_alliances", {}))
                if alliances:
                    alliance_rows = []
                    for pair, strength in sorted(alliances.items(), key=lambda item: float(item[1]), reverse=True):
                        departments = str(pair).split("|")
                        if len(departments) != 2:
                            continue
                        left_name = str(ministers.get(departments[0], departments[0].replace("_", " ").title()))
                        right_name = str(ministers.get(departments[1], departments[1].replace("_", " ").title()))
                        alliance_rows.append({
                            "Cabinet alliance": f"{left_name} + {right_name}",
                            "Strength": f"{float(strength):.0f}/100",
                        })
                    if alliance_rows:
                        st.markdown("**Ministerial alliances and co-signatories**")
                        st.dataframe(alliance_rows, hide_index=True, use_container_width=True)
                        st.caption("Alliances formed through joint amendment campaigns provide a small continuing support bonus in future Cabinet policy reviews.")
                pressure_issue = s.get("political_pressure_issue")
                if pressure_issue:
                    st.markdown("**Political pressure · Response required**")
                    st.warning(pressure_issue.get("text", "A political dispute needs your attention."))
                    if pressure_issue.get("leaked"):
                        st.caption("A briefing has reached the press. Media sentiment and public approval have already been affected.")
                    cols = st.columns(3)
                    with cols[0]:
                        if st.button("Stand firm", key="political_pressure_stand", use_container_width=True):
                            political_pressure.resolve_issue("stand_firm")
                            st.rerun()
                    with cols[1]:
                        if st.button("Negotiate", key="political_pressure_negotiate", use_container_width=True, disabled=int(s.get("political_capital_points", 0)) < 1):
                            political_pressure.resolve_issue("negotiate")
                            st.rerun()
                    with cols[2]:
                        if st.button("Allow briefing", key="political_pressure_briefing", use_container_width=True):
                            political_pressure.resolve_issue("briefing")
                            st.rerun()
                    if pressure_issue.get("kind") == "parliamentary_bloc":
                        st.caption(f"Parliamentary faction: {pressure_issue.get('party', 'Government')} · {pressure_issue.get('rebel_count', 0)} rebels from {pressure_issue.get('seats', 0)} seats. Negotiating may secure support for later votes; standing firm risks wider party discontent.")
                    else:
                        st.caption("Negotiation costs one political-capital point and £0.3bn of headroom. Standing firm risks Cabinet relations; allowing a briefing damages the Government's public image.")
                relationship_issue = s.get("ministerial_relationship_issue")
                if relationship_issue:
                    st.markdown("**A private Cabinet approach**")
                    st.info(relationship_issue.get("text", "A minister wants to speak to the Chancellor."))
                    kind = relationship_issue.get("kind")
                    if kind == "lobbying":
                        cols = st.columns(3)
                        with cols[0]:
                            if st.button("Agree funding", key="cabinet_issue_fund", use_container_width=True):
                                cabinet_management.resolve_relationship_issue("fund")
                                st.rerun()
                        with cols[1]:
                            if st.button("Request a plan", key="cabinet_issue_plan", use_container_width=True):
                                cabinet_management.resolve_relationship_issue("plan")
                                st.rerun()
                        with cols[2]:
                            if st.button("Refuse", key="cabinet_issue_refuse", use_container_width=True):
                                cabinet_management.resolve_relationship_issue("refuse")
                                st.rerun()
                    elif kind == "briefing":
                        cols = st.columns(3)
                        with cols[0]:
                            if st.button("Mediate", key="cabinet_issue_mediate", use_container_width=True):
                                cabinet_management.resolve_relationship_issue("mediate")
                                st.rerun()
                        with cols[1]:
                            if st.button("Back the minister", key="cabinet_issue_back", use_container_width=True):
                                cabinet_management.resolve_relationship_issue("back")
                                st.rerun()
                        with cols[2]:
                            if st.button("Warn both", key="cabinet_issue_warn", use_container_width=True):
                                cabinet_management.resolve_relationship_issue("warn")
                                st.rerun()
                    elif kind == "resignation":
                        cols = st.columns(2)
                        with cols[0]:
                            if st.button("Offer a compromise", key="cabinet_issue_compromise", use_container_width=True):
                                cabinet_management.resolve_relationship_issue("compromise")
                                st.rerun()
                        with cols[1]:
                            if st.button("Stand firm", key="cabinet_issue_stand", use_container_width=True):
                                cabinet_management.resolve_relationship_issue("stand")
                                st.rerun()
                meeting_tick = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
                if s.get("ministerial_meeting_year") != meeting_tick:
                    meeting_dept = st.selectbox(
                        "Private meeting with a minister", [key for key, _ in active_posts],
                        format_func=lambda key: f"{ministers.get(key, key)} · {budget.SPEND_DEFAULTS.get(key, {}).get('label', key)}",
                        key="desk_ministerial_meeting_department",
                    )
                    meet_a, meet_b = st.columns(2)
                    with meet_a:
                        if st.button("Back their priorities", key="desk_minister_back", use_container_width=True):
                            cabinet_management.hold_private_meeting(meeting_dept, "back")
                            st.rerun()
                    with meet_b:
                        if st.button("Demand a delivery plan", key="desk_minister_challenge", use_container_width=True):
                            cabinet_management.hold_private_meeting(meeting_dept, "challenge")
                            st.rerun()
                else:
                    st.caption("Your annual private Cabinet meeting has been used.")
                if reshuffle_used:
                    st.caption("You have already made your one reshuffle recommendation this term.")
                else:
                    dept = st.selectbox(
                        "Minister to recommend for replacement",
                        [key for key, _ in active_posts],
                        format_func=lambda key: f"{ministers.get(key, key)} · {budget.SPEND_DEFAULTS.get(key, {}).get('label', key.replace('_', ' ').title())}",
                        key="desk_reshuffle_department",
                    )
                    assessment = cabinet_management.reshuffle_assessment(s, dept)
                    st.caption(
                        f"Number 10's current receptiveness: {assessment['band']} · "
                        f"Ministerial competence {assessment.get('competence', 60):.0f}/100 · "
                        f"Department performance {assessment.get('service_score', 60):.0f}/100 · "
                        f"Loyalty {assessment.get('loyalty', 50):.0f}/100."
                    )
                    st.caption(
                        "The Prime Minister weighs their own confidence, Cabinet unity, ministerial loyalty, "
                        "competence, departmental results and any active dispute. A recommendation can still be rejected."
                    )
                    if st.button("Recommend minister replacement", use_container_width=True, help="Recommend a Cabinet replacement to the Prime Minister."):
                        engine.request_ministerial_reshuffle(dept)
                        st.rerun()
            else:
                st.caption("No established Cabinet appointments are currently available to review.")
            review_history = list(s.get("ministerial_review_history", []))
            if review_history:
                st.markdown("**Recent private meetings**")
                for item in reversed(review_history[-2:]):
                    st.caption(f"Term/year {item.get('year', '')} · {item.get('minister', '')} · {item.get('approach', '').title()}")
                    st.write(item.get("outcome", ""))
            recent_reshuffles = list(s.get("cabinet_reshuffle_history", []))
            if recent_reshuffles:
                st.markdown("**Recent reshuffle correspondence**")
                for item in reversed(recent_reshuffles[-3:]):
                    result = "Accepted" if item.get("accepted") else "Rejected"
                    st.caption(f"Term {item.get('term')} · {item.get('minister')} · PM {result}")
                    st.write(item.get("outcome", ""))

        # Private advisers: one-click expanders rather than more navigation tabs.
        st.markdown("<div class='desk-section-title'>YOUR ADVISERS</div>", unsafe_allow_html=True)
        with st.expander("Permanent Secretary · Fiscal advice", expanded=False):
            st.caption(_permanent_secretary_advice(s))
            st.caption(f"Officials' confidence: {float(s.get('officials_confidence', 70)):.0f}/100")
            recent_advice = list(s.get("officials_log", []))
            if recent_advice:
                st.markdown("**Recent advice record**")
                for item in reversed(recent_advice[-3:]):
                    st.caption(f"{item.get('period', '')} · {item.get('source', 'Treasury')} · {item.get('view', '')}")
                    st.write(item.get("note", ""))
            else:
                st.caption("Formal advice and disagreements will be recorded here as you make decisions.")
        with st.expander("Chief Economic Adviser · Outlook", expanded=False):
            forecast = s.get("obr_latest")
            if forecast:
                st.caption(
                    f"Latest central projection: growth {float(forecast.get('growth', 0)):+.2f}%, "
                    f"inflation {float(forecast.get('inflation', 0)):.2f}%."
                )
                st.caption(
                    f"Receipts revision £{float(forecast.get('receipts_revision', 0)):+.1f}bn · "
                    f"headroom estimate £{float(forecast.get('headroom', 0)):.1f}bn."
                )
            else:
                st.caption(f"Current conditions: growth {float(s.get('growth', 0)):+.1f}%, inflation {float(s.get('inflation', 0)):.1f}%.")
                st.caption("A full OBR-style revision will appear at the next annual update.")
            st.caption(_economic_advice(s))
        with st.expander("Special Adviser · Political strategy", expanded=False):
            spad = s.get("spad")
            if spad in politics.SPADS:
                adviser = politics.SPADS[spad]
                st.markdown(f"**{_safe(adviser['label'])}**")
                st.caption(adviser["blurb"])
            else:
                st.caption("No special adviser appointed. Your private office is handling political preparation.")
            if s.get("officials_last_advice"):
                st.caption(f"Last political briefing: {s.officials_last_advice}")

        # Live risks and events.
        warnings = _warnings(s)
        with st.expander(f"Watchlist · {len(warnings)} alerts", expanded=bool(warnings)):
            if warnings:
                for kind, message in warnings:
                    st.markdown(
                        f"<div class='desk-warning {kind}'><span></span>{_safe(message)}</div>",
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    "<div class='desk-clear'><span>✓</span> No immediate warnings</div>",
                    unsafe_allow_html=True,
                )

        # The diary reflects queued decisions and the revised fiscal-event calendar.
        diary = []
        # Match the actual Decisions-screen priority so the diary never suggests
        # a fiscal event is actionable ahead of an urgent parliamentary or crisis event.
        if s.get("local_election_due"):
            diary.append(("NOW", "Local elections"))
        if s.get("active_pm_ultimatum"):
            diary.append(("NOW", "Prime Minister's ultimatum"))
        if s.get("active_pm_meeting"):
            diary.append(("PENDING", "Private meeting with the PM"))
        if s.get("active_gilt_emergency"):
            diary.append(("NOW", "Gilt-market emergency"))
        if s.get("active_forecast_review"):
            diary.append(("NOW", "Treasury forecast review · response required"))
        if s.get("active_opposition_attack"):
            diary.append(("PENDING", "Opposition economic attack · response available"))
        if s.get("active_financial_crisis"):
            diary.append(("NOW", "Financial stability response"))
        if s.get("active_crisis"):
            diary.append(("NOW", "Emergency decision"))
        if s.get("active_dispute"):
            diary.append(("PENDING", "Cabinet dispute"))
        if s.get("active_weekly_event"):
            diary.append(("NOW", "Treasury event response"))
        if s.get("active_request"):
            diary.append(("PENDING", "Ministerial request"))
        if s.get("active_emergency_budget"):
            diary.append(("NOW", "Deliver Emergency Budget"))
        if s.get("spending_review_due"):
            diary.append(("NOW", "Spending Review · agree departmental settlements"))
        if s.get("autumn_statement_due"):
            diary.append(("NOW", "Autumn Statement · publish or skip"))
        if s.get("budget_passed"):
            diary.append(("NEXT", "Proceed to Spring"))
        elif int(s.get("block", 1)) == 3 and not s.get("active_emergency_budget"):
            diary.append(("CURRENT", "Spring Budget and Commons vote"))
        elif not s.get("active_emergency_budget"):
            diary.append(("NEXT", phase_info(min(3, int(s.get("block", 1)) + 1))["title"]))
        if year >= 5:
            diary.append(("TERM END", "General election preparations"))
        if len(diary) < 6 and not s.get("spending_review_due"):
            next_review_year = next((yr for yr in (1, 3, 5) if yr > year), None)
            if next_review_year:
                diary.append(("PLANNED", f"Next Spending Review · Year {next_review_year}"))
            elif year <= 5:
                diary.append(("PLANNED", "Next Spending Review · next term"))
        with st.expander(f"Diary & next steps · {len(diary)} items", expanded=bool(diary and diary[0][0] == "NOW")):
            for status, item in diary[:6]:
                st.markdown(
                    f"<div class='desk-diary'><span>{_safe(status)}</span><strong>{_safe(item)}</strong></div>",
                    unsafe_allow_html=True,
                )

        if s.get("pledges"):
            kept = [key for key in s.pledges if key not in s.get("broken_pledges", [])]
            with st.expander(f"Manifesto pledges · {len(kept)}/{len(s.pledges)} kept", expanded=False):
                for key in s.pledges:
                    broken = key in s.get("broken_pledges", [])
                    label = politics.PLEDGES.get(key, {}).get("label", key)
                    st.caption(f"{'✕' if broken else '✓'} {label}")

        st.divider()
        st.markdown("<div class='desk-section-title'>RUN CONTROLS</div>", unsafe_allow_html=True)
        if state.diff().get("undos", 0) > 0:
            if st.button(
                f"Undo last action · {int(s.get('undos_left', 0))} left",
                disabled=not state.can_undo(),
                use_container_width=True,
                help="Roll back your last decision, crisis, request, Budget or Spring."
            ):
                if state.undo():
                    st.rerun()
        st.download_button(
            "Download save file",
            state.export_save(),
            use_container_width=True,
            file_name=f"chancellor_{str(s.party).replace(' ', '')}_T{s.term}Y{s.year}.json",
            mime="application/json",
            help="Save your progress and load it again from the start screen."
        )
        with st.expander("Annual cycle guide", expanded=False):
            st.markdown("**Autumn Statement**")
            st.caption("A standalone opening event. Publish a limited fiscal update or proceed without one.")
            st.markdown("**Spending Review**")
            st.caption("Held at the start of Years 1, 3 and 5. Agree departmental cash baselines and a multi-year spending path.")
            for num in (1, 2, 3):
                item = phase_info(num)
                st.markdown(f"**{item['title']}**")
                st.caption(item["guide"])
            st.markdown("**Spring Budget**")
            st.caption("The annual tax-and-spending package, followed by a Commons vote and market reaction.")
            st.markdown("**Emergency Budget**")
            st.caption("Only called when severe fiscal, market or economic stress requires a full revised package.")
        with st.expander("End this run", expanded=False):
            st.caption("Resigning ends your career and shows your scorecard. Abandoning discards this run.")
            if st.button("Resign as Chancellor", use_container_width=True):
                engine.resign()
                st.rerun()
            if st.button("Abandon run & start over", use_container_width=True):
                on_restart()
