"""Private Treasury advice, fiscal risk warnings and political strategy briefings."""
import streamlit as st
import state


def ensure():
    s = st.session_state
    s.setdefault("officials_confidence", 70.0)
    s.setdefault("officials_log", [])
    s.setdefault("officials_last_advice", "")
    s.setdefault("officials_actions", [])


def _period():
    s = st.session_state
    return f"{int(s.get('term', 1))}-{int(s.get('year', 1))}"


def review_policy(title, choice, effect):
    """Record whether senior officials support a major policy decision."""
    ensure()
    s = st.session_state
    risks = []
    if float(s.get("headroom", 0)) < 0 and float(effect.get("headroom", 0)) < 0:
        risks.append("The proposal adds to spending while the Chancellor is already outside the fiscal rule.")
    if float(effect.get("headroom", 0)) < -2:
        risks.append("The costing leaves little protection against forecast revisions or economic shocks.")
    if float(effect.get("growth", 0)) < -0.15:
        risks.append("The policy may weaken investment, productivity or the tax base.")
    if float(effect.get("inflation", 0)) > 0.25:
        risks.append("The measure risks adding to inflationary pressure.")
    if float(s.get("market_conf", 50)) < 35:
        risks.append("Market confidence is fragile; the financing assumptions need particular care.")
    if risks:
        note = "Permanent Secretary: " + " ".join(risks)
        s.officials_confidence = max(0.0, float(s.officials_confidence) - min(6.0, 1.5 * len(risks)))
        s.officials_log.append({
            "period": f"Term {s.term}, Year {s.year}", "source": "Permanent Secretary",
            "title": title, "choice": choice, "view": "Formal concern", "note": note,
        })
        s.officials_log = s.officials_log[-30:]
        s.event_cards.append({"title": "Treasury officials raise concerns", "text": note,
                              "summary": f"Officials' confidence: {s.officials_confidence:.0f}/100"})
    elif float(effect.get("headroom", 0)) > 0 or float(effect.get("growth", 0)) > 0.15:
        note = "The Permanent Secretary considers the proposal deliverable, but advises close monitoring of its cost and implementation."
        s.officials_log.append({
            "period": f"Term {s.term}, Year {s.year}", "source": "Permanent Secretary",
            "title": title, "choice": choice, "view": "Qualified support", "note": note,
        })
        s.officials_log = s.officials_log[-30:]


def render():
    ensure()
    s = st.session_state
    st.markdown("### 🏛️ Treasury officials")
    st.caption("Private advice from the permanent civil service, fiscal risk assessments and political counsel from your special advisers.")
    growth = float(s.get("growth", 0))
    inflation = float(s.get("inflation", 2))
    headroom = float(s.get("headroom", 0))
    gilt = float(s.get("gilt_yield", 4.5))
    market = float(s.get("market_conf", 50))
    officials = []
    if headroom < 0:
        officials.append(("HIGH RISK", "The fiscal rules are already breached. The Permanent Secretary advises against unfunded permanent commitments and recommends a credible medium-term correction."))
    elif headroom < 3:
        officials.append(("CAUTION", "Headroom is narrow. The Permanent Secretary recommends keeping a reserve for forecast errors rather than spending the entire margin."))
    else:
        officials.append(("ASSESSMENT", "The fiscal position provides some room for manoeuvre, but the Permanent Secretary advises retaining a prudent margin against shocks."))
    if inflation >= 4:
        officials.append(("INFLATION", "Officials warn that broad demand-side stimulus could complicate the Bank of England's effort to return inflation to target."))
    if gilt >= 5 or market < 40:
        officials.append(("MARKETS", "Debt Management Office and fiscal teams warn that borrowing costs and market confidence need close attention."))
    if growth < 0:
        officials.append(("GROWTH", "The economy is contracting. Officials advise protecting high-value investment while checking whether temporary support can be afforded."))
    for label, advice in officials:
        with st.container(border=True):
            st.caption(f"PERMANENT SECRETARY · {label}")
            st.write(advice)

    spad = s.get("spad")
    spad_label = "Your special adviser" if not spad else str(spad).replace("_", " ").title()
    if spad == "pollster":
        strategy = "The political team recommends protecting household confidence: announce a tightly targeted cost-of-living measure and explain who benefits."
    elif spad:
        strategy = "Your political adviser recommends choosing one clear economic message, anticipating the opposition's attack and securing the Prime Minister's backing before going public."
    else:
        strategy = "No special adviser is appointed. Your private office recommends a clear message, early engagement with Number 10 and careful preparation for the next Commons vote."
    with st.container(border=True):
        st.caption(f"🧑‍💼 SPECIAL ADVISER · {spad_label.upper()}")
        st.write(strategy)
        if st.button("Ask the political team for a campaign line", key="officials_spad_brief"):
            state.checkpoint()
            s.officials_last_advice = strategy
            s.officials_log.append({"period": f"Term {s.term}, Year {s.year}", "source": "Special adviser",
                                    "title": "Political strategy briefing", "choice": "Requested advice",
                                    "view": "Recommendation", "note": strategy})
            s.officials_log = s.officials_log[-30:]
            st.success("The advice has been added to your private briefing record.")

    with st.expander("📂 Permanent Secretary's private note", expanded=False):
        advice = ("My advice, Chancellor, is to preserve fiscal credibility, distinguish temporary shocks from permanent spending, "
                  "and ensure every commitment has a transparent costing. The figures are uncertain; the judgement is yours.")
        st.write(advice)
        st.caption(f"Officials' confidence in the Treasury's current direction: {float(s.officials_confidence):.0f}/100")
        if st.button("Record that you have heard the advice", key="officials_acknowledge"):
            s.officials_last_advice = advice
            st.success("Private advice acknowledged. You remain responsible for the decision.")

    with st.expander("🗃️ Officials' record of advice and disagreements", expanded=False):
        log = list(s.get("officials_log", []))
        if log:
            for item in reversed(log[-12:]):
                st.markdown(f"**{item.get('period', '')} · {item.get('source', 'Treasury')} — {item.get('view', '')}**")
                st.caption(f"{item.get('title', '')} · {item.get('choice', '')}")
                st.write(item.get("note", ""))
        else:
            st.caption("Advice and disagreements will be recorded as you make decisions.")
