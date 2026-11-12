"""Persistent left-hand Chancellor's Desk sidebar."""
import html
import streamlit as st

import engine
import politics
import budget
import state
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

        # Cabinet management: the Chancellor can recommend; only the PM can appoint or dismiss.
        st.markdown("<div class='desk-section-title'>CABINET MANAGEMENT</div>", unsafe_allow_html=True)
        ministers = s.get("cabinet_ministers", {})
        active_posts = [
            (key, name) for key, name in ministers.items()
            if key in budget.DEPARTMENT_MINISTERS
            and name
            and not str(name).startswith(("Vacant", "New appointment"))
        ]
        reshuffle_used = int(s.get("term", 1)) in s.get("cabinet_reshuffle_terms", [])
        if active_posts:
            if reshuffle_used:
                st.caption("You have already made your one reshuffle recommendation this term.")
            else:
                dept = st.selectbox(
                    "Minister to recommend for replacement",
                    [key for key, _ in active_posts],
                    format_func=lambda key: f"{ministers.get(key, key)} · {budget.SPEND_DEFAULTS.get(key, {}).get('label', key.replace('_', ' ').title())}",
                    key="desk_reshuffle_department",
                )
                st.caption(
                    f"Current ministerial loyalty: {float(s.get('ministerial_loyalty', {}).get(dept, 50.0)):.0f}/100. "
                    "A weak relationship or active dispute makes Number 10 more receptive."
                )
                if st.button("Recommend a Cabinet replacement to the PM", use_container_width=True):
                    engine.request_ministerial_reshuffle(dept)
                    st.rerun()
        else:
            st.caption("No established Cabinet appointments are currently available to review.")
        recent_reshuffles = list(s.get("cabinet_reshuffle_history", []))
        if recent_reshuffles:
            with st.expander("Reshuffle correspondence", expanded=False):
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
        st.markdown(
            f"<div class='desk-section-title'>WATCHLIST <span class='desk-count'>{len(warnings)}</span></div>",
            unsafe_allow_html=True,
        )
        if warnings:
            for kind, message in warnings[:4]:
                st.markdown(
                    f"<div class='desk-warning {kind}'><span></span>{_safe(message)}</div>",
                    unsafe_allow_html=True,
                )
            if len(warnings) > 4:
                st.caption(f"+ {len(warnings) - 4} further items need attention.")
        else:
            st.markdown(
                "<div class='desk-clear'><span>✓</span> No immediate warnings</div>",
                unsafe_allow_html=True,
            )

        # The diary reflects the current phase and any queued events.
        st.markdown("<div class='desk-section-title'>DIARY & NEXT STEPS</div>", unsafe_allow_html=True)
        diary = []
        if s.get("active_crisis"):
            diary.append(("NOW", "Emergency decision"))
        if s.get("active_weekly_event"):
            diary.append(("NOW", "Treasury event response"))
        if s.get("active_request"):
            diary.append(("PENDING", "Ministerial request"))
        if s.get("active_dispute"):
            diary.append(("PENDING", "Cabinet dispute"))
        if s.get("local_election_due"):
            diary.append(("UPCOMING", "Local elections"))
        if s.get("budget_passed"):
            diary.append(("NEXT", "Proceed to Spring"))
        elif int(s.get("block", 1)) == 3:
            diary.append(("CURRENT", "Spring Budget and Commons vote"))
        else:
            diary.append(("NEXT", phase_info(min(3, int(s.get("block", 1)) + 1))["title"]))
        if year >= 5:
            diary.append(("TERM END", "General election preparations"))
        for status, item in diary[:5]:
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
            for num in (1, 2, 3):
                item = phase_info(num)
                st.markdown(f"**{item['title']}**")
                st.caption(item["guide"])
            st.caption("Two policy decisions lead into a Budget vote each year.")
        with st.expander("End this run", expanded=False):
            st.caption("Resigning ends your career and shows your scorecard. Abandoning discards this run.")
            if st.button("Resign as Chancellor", use_container_width=True):
                engine.resign()
                st.rerun()
            if st.button("Abandon run & start over", use_container_width=True):
                on_restart()
