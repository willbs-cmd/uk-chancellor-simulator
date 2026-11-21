"""Optional first-year onboarding for new Chancellor Simulator players."""
import streamlit as st

WORKSPACES = {
    "office": {"title": "Chancellor's Office", "detail": "Your daily briefings and immediate decisions. Start here, read the Treasury in-tray and respond to urgent issues."},
    "budget": {"title": "The Budget", "detail": "Tax, departmental spending, borrowing and fiscal events. Review receipts, spending and the forecast before approving a package."},
    "economy": {"title": "The Economy", "detail": "Growth, inflation, employment, households and the long-term outlook. Forecasts are estimates, not guarantees."},
    "cabinet": {"title": "Cabinet", "detail": "Ministerial performance, departmental delivery and your relationship with Number 10. The PM controls appointments and reshuffles."},
    "parliament": {"title": "Parliament", "detail": "Commons votes, MPs, accountability, local elections and the next general election. A majority does not guarantee every MP's support."},
    "news": {"title": "The News", "detail": "Events, polling, opposition campaigns and public reaction. Polling is a signal of political mood, not the same thing as public approval."},
}

STEP_DEFINITIONS = [
    ("office", "office", "Read your first Treasury briefing", "Open the Office and look through the Treasury in-tray."),
    ("budget", "budget", "Visit the Budget", "Find the tax, spending and fiscal-event controls."),
    ("economy", "economy", "Check the economic outlook", "Review growth, inflation and the forward forecasts."),
    ("first_decision", "first_decision", "Make your first decision", "Resolve a policy, crisis or other in-game decision."),
    ("parliament", "parliament", "Explore Parliament", "See how Commons votes, MPs and political pressure work."),
]


def ensure(s):
    s.setdefault("onboarding_enabled", False)
    s.setdefault("onboarding_completed", True)
    s.setdefault("onboarding_visits", [])
    return s


def note_workspace(s, workspace):
    ensure(s)
    if not s.get("onboarding_enabled") or s.get("onboarding_completed"):
        return
    if workspace in WORKSPACES:
        visits = list(s.get("onboarding_visits", []))
        if workspace not in visits:
            visits.append(workspace)
            s.onboarding_visits = visits
    if checklist(s)["complete"]:
        s.onboarding_completed = True


def checklist(s):
    ensure(s)
    visited = set(s.get("onboarding_visits", []))
    first_decision = int(s.get("steps", 0)) > 0 or any(
        item.get("kind") in {"decision", "crisis", "policy"}
        for item in s.get("history", [])
    )
    done = {
        "office": "office" in visited,
        "budget": "budget" in visited,
        "economy": "economy" in visited,
        "first_decision": first_decision,
        "parliament": "parliament" in visited,
    }
    completed = sum(1 for _, key, _, _ in STEP_DEFINITIONS if done[key])
    return {"completed": completed, "total": len(STEP_DEFINITIONS),
            "complete": completed == len(STEP_DEFINITIONS), "steps": done}


def render(s=None, active_workspace="office"):
    s = s or st.session_state
    ensure(s)
    if not s.get("onboarding_enabled"):
        return
    progress = checklist(s)
    with st.expander(
        f"Getting started · {progress['completed']}/{progress['total']} steps complete",
        expanded=not s.get("onboarding_completed", False),
    ):
        st.markdown("### Welcome to Number 11")
        st.caption("A short guide to your first year. Explore the workspaces in any order; your progress is saved with the game.")
        cols = st.columns(3)
        cols[0].markdown("**Your role**")
        cols[0].caption("You are the Chancellor. You run the Treasury; the Prime Minister leads the Government.")
        cols[1].markdown("**Your main trade-off**")
        cols[1].caption("Policies can improve growth, living standards or services, but may require taxes, spending or borrowing.")
        cols[2].markdown("**Your objective**")
        cols[2].caption("Deliver your five-year mission while retaining economic credibility and political support.")
        st.progress(progress["completed"] / progress["total"], text="Your first steps")
        for workspace, key, title, instruction in STEP_DEFINITIONS:
            complete = progress["steps"][key]
            step_cols = st.columns([0.07, 0.93])
            step_cols[0].markdown("✅" if complete else "⬜")
            step_cols[1].markdown(f"**{title}**" + (" · Complete" if complete else ""))
            if not complete:
                destination = WORKSPACES[workspace]["title"] if workspace in WORKSPACES else "Office"
                step_cols[1].caption(
                    f"Open the {destination} workspace above."
                    if workspace in WORKSPACES else
                    "Resolve one policy, crisis or other decision from the Office."
                )
        if progress["complete"]:
            st.success("You have completed the New Chancellor quick start. The guide remains here as a reference.")
        st.divider()
        current = WORKSPACES.get(active_workspace, WORKSPACES["office"])
        st.markdown(f"**On this screen: {current['title']}**")
        st.caption(current["detail"])
        with st.expander("Understand the key numbers", expanded=False):
            glossary = [
                ("Public approval", "The share of the electorate supporting your Government. It influences your political standing and election prospects."),
                ("Fiscal headroom", "Your safety margin against the fiscal rule. It is not a bank balance or a pot of cash. Negative headroom means the rule is breached."),
                ("Annual deficit", "The amount by which Government spending exceeds receipts over a year. It is a flow, not the total debt."),
                ("National debt", "The accumulated stock of Government debt, shown as a percentage of GDP."),
                ("Economic growth", "The annual rate of change in GDP. Stronger activity can increase tax receipts over time."),
                ("Market confidence", "How confident investors are in the Government's economic management. Weak confidence can make borrowing more expensive."),
                ("PM confidence", "The Prime Minister's assessment of you personally. It is different from public approval and matters to your job security."),
            ]
            for term, definition in glossary:
                st.markdown(f"**{term}**")
                st.caption(definition)
        with st.expander("Five beginner tips", expanded=False):
            st.markdown(
                "1. Deal with urgent Office briefings before taking on optional projects.\n"
                "2. Check the fiscal forecast before promising permanent spending increases.\n"
                "3. Do not confuse debt with the annual deficit, or headroom with cash in the bank.\n"
                "4. Watch PM confidence, party unity and backbench morale as well as public approval.\n"
                "5. You do not need to use every feature immediately. Learn the Budget and economy first, then explore Cabinet and Parliament."
            )
        if not progress["complete"]:
            if st.button("Skip the New Chancellor guide", key="skip_new_chancellor_guide"):
                s.onboarding_enabled = False
                s.onboarding_completed = True
                st.rerun()


