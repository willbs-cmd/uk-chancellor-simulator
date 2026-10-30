"""Chancellor's Office: the player's relationships, scrutiny and Treasury negotiations.

The player is the Chancellor, not the Prime Minister. This module gives the player
influence over fiscal negotiations and accountability without allowing them to
appoint ministers, reshuffle the Cabinet or direct the whole government.
"""
import streamlit as st

import engine
import state

def _year_key():
    s = st.session_state
    return f"{int(s.term)}-{int(s.year)}"

def _used(action):
    s = st.session_state
    return f"{_year_key()}:{action}" in s.setdefault("chancellor_actions", [])

def _apply(title, choice, effects, note, action):
    s = st.session_state
    state.checkpoint()
    before = state.values()
    state.snapshot()
    for key, delta in effects.items():
        if key in ("headroom", "growth", "inflation", "gilt_yield", "deficit"):
            s[key] = round(float(s.get(key, 0.0)) + float(delta), 2)
        elif key in state.STAT_KEYS:
            s[key] = round(max(0.0, min(100.0, float(s.get(key, 0.0)) + float(delta))), 1)
    s.chancellor_actions.append(f"{_year_key()}:{action}")
    s.message = note
    s.humphrey_note = ""
    state.log("event", title, choice=choice, before=before, note=note)
    state.record()
    engine.check_sacked()
    st.rerun()

def _action_card(title, description, action, options):
    s = st.session_state
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(description)
        if _used(action):
            st.success("Completed this financial year")
            return
        for idx, option in enumerate(options):
            label, hint, effects, note = option
            with st.container():
                st.markdown(f"**{label}**")
                st.caption(hint)
                if st.button(f"Choose: {label}", key=f"chancellor_{_year_key()}_{action}_{idx}", use_container_width=True):
                    _apply(title, label, effects, note, action)

def render():
    s = st.session_state
    st.markdown("## 🏛️ The Chancellor's Office")
    st.caption("You control the Treasury and negotiate with the Prime Minister, Cabinet and Parliament. The Prime Minister retains control of ministerial appointments and Cabinet reshuffles.")

    st.markdown("### 📥 The Treasury in-tray")
    st.caption("Your private office has prepared the latest submissions. Briefings update as the economy and political situation change.")
    growth = float(s.get("growth", 0.0))
    inflation = float(s.get("inflation", 2.0))
    headroom = float(s.get("headroom", 0.0))
    gilt = float(s.get("gilt_yield", 4.5))
    market = float(s.get("market_conf", 50.0))
    briefs = [
        ("📊 OBR — Fiscal outlook", f"Growth is {growth:.1f}%, inflation is {inflation:.1f}% and forecast headroom is £{headroom:.1f}bn. " + ("The fiscal buffer is thin; new commitments need robust costings." if headroom < 5 else "There is some room for carefully targeted measures.")),
        ("🏦 Bank of England — Monetary conditions", f"Market confidence is {market:.0f}/100 and the 10-year gilt yield is {gilt:.2f}%. " + ("Investors are demanding a higher return; fiscal credibility is under scrutiny." if gilt >= 5 else "Financing conditions are relatively contained, but monetary policy remains independent.")),
        ("🏥 Departments — Spending pressures", "The NHS, local government and public services are seeking settlements. Any additional funding must be balanced against the fiscal rules."),
        ("🏢 Business — Investment climate", "Employers are watching borrowing costs, skills availability, energy prices and the stability of the tax system."),
    ]
    for title, body in briefs:
        with st.container(border=True):
            st.markdown(f"**{title}**")
            st.write(body)

    st.markdown("### Your performance as Chancellor")
    credibility = max(0, min(100, 50 + headroom * 2.2 + (market - 50) * 0.35 - max(0, gilt - 4.5) * 5))
    economic_competence = max(0, min(100, 55 + growth * 4 - max(0, inflation - 2) * 5))
    business_confidence = max(0, min(100, market * 0.65 + (100 - max(0, gilt - 3) * 12) * 0.35))
    public_standing = max(0, min(100, float(s.get("approval", 50)) * 0.65 + float(s.get("media_opinion", 50)) * 0.35))
    cabinet_standing = max(0, min(100, float(s.get("pm_opinion", 50)) * 0.45 + float(s.get("cab_opinion", 50)) * 0.4 + float(s.get("party_opinion", 50)) * 0.15))
    ratings = st.columns(5)
    for col, label, value in zip(ratings, ["Fiscal credibility", "Economic competence", "Business confidence", "Public standing", "Cabinet confidence"], [credibility, economic_competence, business_confidence, public_standing, cabinet_standing]):
        col.metric(label, f"{value:.0f}/100")
    st.caption("These are simulated performance indicators, not official economic statistics. The Bank of England remains operationally independent.")


    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PM's confidence", f"{float(s.pm_opinion):.0f}/100")
    c2.metric("Cabinet support", f"{float(s.cab_opinion):.0f}/100")
    c3.metric("Party unity", f"{float(s.party_opinion):.0f}/100")
    c4.metric("Political capital", f"{int(s.get('political_capital_points', 0))}")

    pm = float(s.pm_opinion)
    if pm >= 70:
        st.success("The Prime Minister trusts your judgement. You have room to shape the Budget.")
    elif pm >= 45:
        st.info("Your position is workable, but major disagreements with the Prime Minister could become dangerous.")
    elif pm >= 20:
        st.warning("Your position is vulnerable. A Budget dispute or public disagreement could put your job at risk.")
    else:
        st.error("The Prime Minister has lost confidence in you. Your career is at risk.")

    st.markdown("### Negotiations and scrutiny")
    st.caption(f"These actions are available once per financial year. Current period: Term {s.term}, Year {s.year}.")

    _action_card(
        "🤝 Pre-Budget meeting with the Prime Minister",
        "Make the case for your fiscal priorities. The PM can accept your approach, but will expect you to balance growth with fiscal credibility.",
        "pm_meeting",
        [
            ("Present a credible fiscal plan", "Prioritise stability, costings and the fiscal rules.",
             {"pm_opinion": 5 if s.headroom >= 0 and s.market_conf >= 45 else 2,
              "cab_opinion": 1, "market_conf": 1 if s.headroom >= 0 else 0},
             "You present the Prime Minister with a costed fiscal plan. The meeting is constructive and your relationship with Number 10 improves."),
            ("Argue for a growth-first Budget", "Ask the PM to back targeted investment, accepting some short-term fiscal pressure.",
             {"headroom": -1.5, "growth": 0.15, "pm_opinion": 2 if s.market_conf >= 55 else -2,
              "cab_opinion": 2, "backbench_opinion": 1},
             "You persuade the Prime Minister to give growth-enhancing investment more room in the Budget. The Treasury accepts a modest near-term cost."),
            ("Insist on tight spending control", "Protect the fiscal position, even if departmental colleagues are frustrated.",
             {"headroom": 2.0, "pm_opinion": 3, "cab_opinion": -2, "backbench_opinion": -1,
              "market_conf": 1},
             "You secure a tougher spending settlement. Investors welcome the discipline, although some Cabinet colleagues are unhappy."),
        ],
    )

    _action_card(
        "🏛️ Treasury Select Committee hearing",
        "Answer MPs' questions about the economy, public finances and the decisions made at the Treasury.",
        "committee_hearing",
        [
            ("Give a candid account", "Acknowledge risks and explain the trade-offs openly.",
             {"media_opinion": 4, "approval": 1, "pm_opinion": 1 if s.headroom >= 0 else -1,
              "market_conf": 1 if s.market_conf >= 45 else 0},
             "Your evidence is judged relatively candid and credible. The committee still challenges your assumptions, but the public response is broadly positive."),
            ("Defend the government's record", "Emphasise progress and challenge the committee's criticism.",
             {"media_opinion": -1, "backbench_opinion": 2, "pm_opinion": 2,
              "market_conf": -1 if s.headroom < 0 else 0},
             "You mount a robust defence of the government's economic record. Your party appreciates the fight, though some observers find the answers evasive."),
            ("Publish extra Treasury analysis", "Offer more detailed costings and independent scrutiny, at a small administrative cost.",
             {"headroom": -0.2, "media_opinion": 3, "market_conf": 2, "pm_opinion": 1},
             "The Treasury publishes additional analysis and costings. Scrutiny is intense, but the extra transparency reassures markets."),
        ],
    )

    _action_card(
        "📑 Departmental spending negotiations",
        "Negotiate with Cabinet colleagues over the overall spending envelope. You cannot appoint or dismiss ministers, but you can set the Treasury's negotiating position.",
        "spending_negotiation",
        [
            ("Hold the line on spending", "Require departments to find efficiencies and reprioritise existing budgets.",
             {"headroom": 1.5, "cab_opinion": -2, "backbench_opinion": -1, "market_conf": 1},
             "The Treasury holds firm in spending negotiations. The fiscal position improves, but departmental ministers warn that difficult choices lie ahead."),
            ("Protect frontline services", "Allow a limited amount of extra departmental spending.",
             {"headroom": -1.0, "cab_opinion": 2, "approval": 1, "backbench_opinion": 1},
             "You agree a limited settlement to protect frontline services. Cabinet relations improve, at a modest cost to headroom."),
            ("Agree targeted productivity deals", "Exchange tightly targeted funding for measurable efficiency and reform commitments.",
             {"headroom": -0.5, "growth": 0.10, "cab_opinion": 1, "market_conf": 1},
             "You secure targeted productivity agreements with departments. The upfront cost is modest and the expected benefit is better public-service efficiency."),
        ],
    )

    st.markdown("### Further Treasury business")
    _action_card(
        "📈 OBR forecast challenge",
        "Decide how to respond to the latest independent fiscal assessment. You cannot dictate the OBR forecast, but you can choose how transparent the Treasury is.",
        "obr_response",
        [
            ("Accept the central forecast and publish the risks", "Protect credibility by acknowledging uncertainty and setting out contingencies.", {"market_conf": 3, "media_opinion": 2, "pm_opinion": 1}, "You publish the OBR central forecast alongside a candid account of the risks. The markets welcome the transparency."),
            ("Commission a Treasury growth plan", "Set out reforms intended to lift productivity, while accepting that benefits will take time.", {"headroom": -0.4, "growth": 0.12, "cab_opinion": 1, "market_conf": 1}, "You commission a targeted growth plan. It costs a little fiscal room now, with potential productivity benefits over time."),
            ("Push back publicly on the assumptions", "Challenge the forecast while risking a perception that the Treasury is avoiding scrutiny.", {"media_opinion": -3, "market_conf": -2, "pm_opinion": 1}, "You publicly challenge the OBR assumptions. Some colleagues appreciate the defence, but independent scrutiny becomes a political flashpoint."),
        ],
    )
    _action_card(
        "🏦 Meeting with the Governor of the Bank of England",
        "Discuss inflation, financial stability and borrowing costs while respecting the Bank’s operational independence.",
        "boe_meeting",
        [
            ("Respect the Bank’s independence", "Keep the discussion private and focus on the shared economic outlook.", {"market_conf": 2, "media_opinion": 1, "pm_opinion": 1}, "The meeting is professional. You reaffirm the Bank’s independence and coordinate on financial stability."),
            ("Coordinate a public cost-of-living response", "Agree to explain the different roles of fiscal and monetary policy.", {"approval": 2, "media_opinion": 2, "market_conf": 1}, "You announce a coordinated explanation of the cost-of-living response without directing interest-rate decisions."),
            ("Complain about the pace of rate cuts", "Voice frustration about the effect of high rates on households and firms.", {"media_opinion": 1, "market_conf": -2, "pm_opinion": 1}, "You express frustration about borrowing costs. The Bank reiterates that rate decisions are independent, and markets dislike the public pressure."),
        ],
    )
    _action_card(
        "🏢 Business and investment council",
        "Hear from employers and investors about the conditions needed to expand, hire and invest in the UK.",
        "business_council",
        [
            ("Prioritise stability and predictable taxes", "Offer businesses a stable policy environment rather than short-term giveaways.", {"market_conf": 2, "growth": 0.08, "business_confidence": 2}, "You commit to predictable tax policy and a stable investment environment. Business confidence improves modestly."),
            ("Offer targeted investment allowances", "Encourage capital spending at a cost to the public finances.", {"headroom": -0.8, "growth": 0.18, "market_conf": 1}, "You introduce a targeted investment incentive. The measure costs headroom but could support capital formation."),
            ("Launch a skills and apprenticeships compact", "Work with employers to address shortages and improve workforce productivity.", {"headroom": -0.5, "growth": 0.15, "approval": 1, "cab_opinion": 1}, "You agree a skills compact with employers. It requires upfront funding but supports the long-term workforce."),
        ],
    )
    with st.expander("📜 Your record at the Treasury"):
        history = [x for x in s.get("history", []) if x.get("kind") == "event" and any(k in x.get("title", "") for k in ("Prime Minister", "Treasury Select", "Departmental spending"))]
        if history:
            for item in reversed(history[-8:]):
                st.markdown(f"**Term {item.get('term')}, Year {item.get('year')} — {item.get('title')}**")
                st.caption(f"{item.get('choice', '')}. {item.get('note', '')}")
        else:
            st.caption("Your negotiations and committee appearances will be recorded here.")
