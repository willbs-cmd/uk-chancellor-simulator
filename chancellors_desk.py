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


def _tile(label, value, detail=""):
    return (
        "<div class='desk-tile'>"
        f"<span class='desk-tile-label'>{_safe(label)}</span>"
        f"<strong>{_safe(value)}</strong>"
        f"<small>{_safe(detail)}</small>"
        "</div>"
    )


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

        # Political standing: the four relationships a Chancellor must monitor.
        st.markdown("<div class='desk-section-title'>POLITICAL STANDING</div>", unsafe_allow_html=True)
        political = [
            ("Public approval", f"{float(s.get('approval', 0)):.0f}%"),
            ("PM confidence", f"{float(s.get('pm_opinion', 0)):.0f}/100"),
            ("Cabinet support", f"{float(s.get('cab_opinion', 0)):.0f}/100"),
            ("Party unity", f"{float(s.get('party_opinion', 0)):.0f}/100"),
        ]
        st.markdown(
            "<div class='desk-grid'>" + "".join(_tile(k, v) for k, v in political) + "</div>",
            unsafe_allow_html=True,
        )

        # Economic watch: keep the values compact and always visible.
        st.markdown("<div class='desk-section-title'>TREASURY WATCH</div>", unsafe_allow_html=True)
        economic = [
            ("Fiscal headroom", f"£{float(s.get('headroom', 0)):.1f}bn"),
            ("GDP growth", f"{float(s.get('growth', 0)):+.1f}%"),
            ("Inflation", f"{float(s.get('inflation', 0)):.1f}%"),
            ("Bank Rate", f"{float(s.get('interest_rate', 0)):.2f}%"),
        ]
        st.markdown(
            "<div class='desk-grid'>" + "".join(_tile(k, v) for k, v in economic) + "</div>",
            unsafe_allow_html=True,
        )
        with st.expander("More fiscal indicators", expanded=False):
            a, b = st.columns(2)
            a.metric("Deficit", f"£{float(s.get('deficit', 0)):.1f}bn")
            b.metric("Debt", f"{float(s.get('debt', 0)):.1f}% GDP")
            a, b = st.columns(2)
            a.metric("Market confidence", f"{float(s.get('market_conf', 0)):.0f}/100")
            b.metric("Political capital", f"{int(s.get('political_capital_points', 0))}/5")

        # Ensure the Cabinet roster is available on every phase, not only after opening the Budget screen.
        budget.ensure()
        cabinet_management.ensure(s)

        # Cabinet management: keep the live desk compact; open this only when making a recommendation.
        ministers = s.get("cabinet_ministers", {})
        active_posts = [
            (key, name) for key, name in ministers.items()
            if key in budget.DEPARTMENT_MINISTERS
            and name
            and not str(name).startswith(("Vacant", "New appointment"))
        ]
        reshuffle_used = int(s.get("term", 1)) in s.get("cabinet_reshuffle_terms", [])
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
