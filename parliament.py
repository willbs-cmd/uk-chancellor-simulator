"""Parliamentary votes and player-controlled Commons strategy.

Every major policy choice is put to a simulated Commons vote. The player's
parliamentary strategy can help secure passage or influence the result.
This is a game model, not a seat-by-seat election forecast.
"""
import math
import streamlit as st

import state

WIN = 326
CLEAR_PASS = 346


def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def _phase_key(s=None):
    s = s or st.session_state
    return f"{int(s.get('term', 1))}:{int(s.get('year', 1))}:{int(s.get('block', 1))}"


def _phase_actions(s=None):
    s = s or st.session_state
    s.setdefault("parliament_actions", {})
    return s["parliament_actions"]


def projected_ayes(bonus=None):
    """Estimate Commons votes from backbench discipline, party unity and approval."""
    s = st.session_state
    if bonus is None:
        bonus = int(s.get("parliament_next_bonus", 0))
    votes = (
        WIN
        + 0.80 * (float(s.get("backbench_opinion", 60)) - 40)
        + 0.45 * (float(s.get("party_opinion", 65)) - 50)
        + 0.12 * (float(s.get("approval", 48)) - 50)
        + int(bonus)
    )
    if s.get("spad") == "enforcer":
        votes += 8
    if s.get("spad") == "negotiator":
        votes += 10
    return max(0, min(650, int(math.floor(votes + 0.5))))


def scale_effect(effect, factor):
    """Scale numeric effects when Parliament amends or blocks a bill."""
    scaled = {}
    for key, value in effect.items():
        if isinstance(value, bool):
            scaled[key] = value
        elif isinstance(value, (int, float)):
            scaled[key] = round(value * factor, 4)
        else:
            scaled[key] = value
    return scaled


def review_bill(decision, option):
    """Vote on the selected policy before applying its effects."""
    s = st.session_state
    bonus = int(s.get("parliament_next_bonus", 0))
    s.parliament_next_bonus = 0
    votes = projected_ayes(bonus=bonus)
    if votes >= CLEAR_PASS:
        status, factor = "Passed", 1.0
        explanation = "The Commons backs the bill without a substantial amendment."
    elif votes >= WIN:
        status, factor = "Passed with amendments", 0.70
        explanation = "The bill passes narrowly. Parliament waters down its effects to reflect negotiated amendments."
    else:
        status, factor = "Rejected", 0.25
        explanation = "The Commons rejects the proposal. Only a limited pilot or administrative part is implemented."
    record = {
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "phase": int(s.get("block", 1)),
        "title": decision.get("title", "Policy bill"),
        "choice": option.get("label", "Government proposal"),
        "ideology": option.get("ideology", "Centric"),
        "ayes": int(votes),
        "noes": int(650 - votes),
        "status": status,
        "factor": factor,
        "bonus": bonus,
        "explanation": explanation,
    }
    s.parliament_last_vote = record
    s.setdefault("parliament_history", [])
    s.parliament_history = (list(s.parliament_history) + [record])[-15:]
    return record


def apply_fallout(record):
    """Political consequences after the Commons has passed, amended or rejected a bill."""
    s = st.session_state
    status = record["status"]
    if status == "Passed":
        s.backbench_opinion = round(_clip(s.backbench_opinion + 0.5), 1)
    elif status == "Passed with amendments":
        s.backbench_opinion = round(_clip(s.backbench_opinion + 1.5), 1)
        s.party_opinion = round(_clip(s.party_opinion + 0.5), 1)
    else:
        s.backbench_opinion = round(_clip(s.backbench_opinion - 4), 1)
        s.party_opinion = round(_clip(s.party_opinion - 3), 1)
        s.approval = round(_clip(s.approval - 1.5), 1)
        s.market_conf = round(_clip(s.market_conf - 1), 1)


def _use_strategy(key, label, cost, bonus, effect):
    s = st.session_state
    phase_key = _phase_key(s)
    actions = _phase_actions(s)
    if actions.get(phase_key):
        st.info(f"You have already used a parliamentary intervention in this phase: {actions[phase_key]}.")
        return False
    capital = int(s.get("political_capital_points", 5))
    if capital < cost:
        st.warning(f"This strategy costs {cost} political-capital point(s); you have {capital}.")
        return False

    state.checkpoint()
    before = state.values()
    state.snapshot()
    s.political_capital_points = capital - cost
    actions[phase_key] = label
    s.parliament_next_bonus = int(s.get("parliament_next_bonus", 0)) + bonus
    effect(s)
    s.parliament_last_strategy = {
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "phase": int(s.get("block", 1)),
        "label": label,
        "bonus": bonus,
    }
    note = f"{label}: +{bonus} votes to the next policy bill. Political capital remaining: {s.political_capital_points}/5."
    s.message = (s.get("message", "") + " " + note).strip()
    state.log("parliament", label, before=before, note=note)
    state.record()
    return True


def render():
    """Draw a Parliament dashboard and three optional strategies for the next policy vote."""
    s = st.session_state
    capital = int(s.get("political_capital_points", 5))
    used = _phase_actions(s).get(_phase_key(s))
    votes = projected_ayes()
    st.markdown("## 🏛️ The House of Commons")
    st.caption("Every major policy decision is put to a vote. Party unity, backbench morale and public approval determine support; you can spend political capital to influence the next bill. The Budget has a separate vote in the Whips & forecast tab.")

    st.markdown("### 📰 Parliamentary update")
    approval = float(s.get("approval", 48))
    backbench = float(s.get("backbench_opinion", 60))
    unity = float(s.get("party_opinion", 65))
    headroom = float(s.get("headroom", 0))
    deficit = float(s.get("deficit", 0))
    update_items = []
    if backbench < 35:
        update_items.append(("🔴 Backbench pressure", "Discontent is high among government MPs. Expect amendments, public letters and a greater risk of rebellion on the next major vote."))
    elif backbench < 55:
        update_items.append(("🟠 Whips face a difficult week", "Some government MPs are uneasy. The whips may need concessions or a stronger case before the next vote."))
    else:
        update_items.append(("🟢 Government benches broadly holding", "Backbench morale is relatively steady, giving ministers more room to negotiate legislation."))
    if unity < 40:
        update_items.append(("🔴 Party unity under strain", "Disagreement inside the governing party is making it harder to present a united front. A compromise could cost money or dilute policy."))
    elif unity > 70:
        update_items.append(("🟢 Party discipline holding", "The parliamentary party is comparatively cohesive, although individual bills can still trigger dissent."))
    else:
        update_items.append(("🟡 Internal negotiations continue", "The leadership needs to keep different wings of the parliamentary party on board."))
    if approval < 30:
        update_items.append(("📉 Opposition sees an opening", "Low public approval is giving opposition parties more room to challenge the government's economic record."))
    elif approval > 60:
        update_items.append(("📈 Government claims political momentum", "Stronger public approval is helping ministers defend their agenda, but it does not guarantee votes in the Commons."))
    else:
        update_items.append(("🎙️ Opposition presses ministers", "Opposition parties are challenging the government on delivery, public services and the cost of its economic choices."))
    if headroom < 0 or deficit > 5:
        update_items.append(("💷 Fiscal scrutiny intensifies", "The Treasury's limited headroom and borrowing position are likely to feature in committee questions and opposition attacks."))
    else:
        update_items.append(("🏦 Treasury plan under scrutiny", "MPs are watching whether the government's fiscal plans match its growth and public-service commitments."))
    for headline, detail in update_items:
        with st.container(border=True):
            st.markdown(f"**{headline}**")
            st.caption(detail)
    st.caption(f"Simulated parliamentary calendar · Term {int(s.get('term', 1))}, Year {int(s.get('year', 1))}, Phase {int(s.get('block', 1))}. These headlines react to your game state; they are not real-world news.")

    m1, m2, m3 = st.columns(3, gap="medium")
    m1.metric("Projected ayes", f"{votes}/650", help="A bill needs 326 votes to pass. A result of 346 or more is treated as a clear passage.")
    m2.metric("Backbench morale", f"{float(s.get('backbench_opinion', 60)):.0f}/100", help="Measures willingness among your own MPs to support government legislation.")
    m3.metric("Party unity", f"{float(s.get('party_opinion', 65)):.0f}/100", help="Measures whether the parliamentary party is staying behind the government.")

    if votes >= CLEAR_PASS:
        st.success(f"Projected result: clear passage ({votes} ayes).")
    elif votes >= WIN:
        st.warning(f"Projected result: narrow passage ({votes} ayes). Parliament may demand amendments.")
    else:
        st.error(f"Projected result: bill at risk ({votes} ayes). The government needs {WIN - votes} more votes.")
    if int(s.get("parliament_next_bonus", 0)):
        st.info(f"Parliamentary strategy has banked +{s.parliament_next_bonus} votes for the next policy bill.")

    with st.expander("📜 Choose a parliamentary strategy for the next bill", expanded=(not bool(used) and int(s.get("block", 1)) < 3)):
        st.caption("You can use one intervention per policy phase. It shares the same five annual political-capital points as the fiscal toolkit.")
        if int(s.get("block", 1)) >= 3:
            st.info("The current business is the Budget. Use Whips & forecast to negotiate its separate Commons vote.")
        elif used:
            st.success(f"Intervention used this phase: {used}. You can prepare again in the next phase.")
        else:
            c1, c2, c3 = st.columns(3, gap="medium")
            with c1:
                st.markdown("**Issue a three-line whip**")
                st.caption("Cost 1 political capital · +14 votes · backbench morale −1")
                if st.button("Enforce party discipline", key="parl_whip", disabled=capital < 1, use_container_width=True):
                    _use_strategy("whip", "Three-line whip", 1, 14,
                                  lambda x: (setattr(x, "backbench_opinion", _clip(x.backbench_opinion - 1)),
                                             setattr(x, "party_opinion", _clip(x.party_opinion + 1))))
                    st.rerun()
            with c2:
                st.markdown("**Offer a cross-party compromise**")
                st.caption("Cost 1 political capital · +18 votes · costs £0.8bn of headroom")
                if st.button("Negotiate an amendment", key="parl_compromise", disabled=capital < 1, use_container_width=True):
                    def compromise(x):
                        x.headroom = round(x.headroom - 0.8, 1)
                        x.deficit = round(x.deficit + 0.8, 1)
                        x.approval = round(_clip(x.approval + 1), 1)
                    _use_strategy("compromise", "Cross-party compromise", 1, 18, compromise)
                    st.rerun()
            with c3:
                st.markdown("**Publish committee evidence**")
                st.caption("Cost 1 political capital · +8 votes · market confidence +2")
                if st.button("Release committee report", key="parl_committee", disabled=capital < 1, use_container_width=True):
                    def committee(x):
                        x.market_conf = round(_clip(x.market_conf + 2), 1)
                        x.approval = round(_clip(x.approval + 0.5), 1)
                    _use_strategy("committee", "Committee evidence report", 1, 8, committee)
                    st.rerun()

    if int(s.get("block", 1)) >= 3:
        st.caption("The Budget vote is controlled by Parliament through the Whips & forecast tab.")

    last = s.get("parliament_last_vote")
    if last:
        st.markdown("### Last Commons vote")
        text = (f"**{last['status']}** · {last['ayes']} ayes, {last['noes']} noes · "
                f"{last['choice']} · {last['term']}/{last['year']} phase {last['phase']}")
        if last["status"] == "Passed":
            st.success(text)
        elif last["status"] == "Passed with amendments":
            st.warning(text)
        else:
            st.error(text)
        st.caption(last["explanation"])

    history = list(s.get("parliament_history", []))[-5:]
    if history:
        with st.expander("Recent parliamentary business", expanded=False):
            for item in reversed(history):
                st.markdown(f"**{item['status']}** · {item['ayes']}–{item['noes']} · {item['choice']}")
                st.caption(f"{item['title']} — year {item['year']}, phase {item['phase']}. {item['explanation']}")

    with st.expander("📖 Parliament glossary", expanded=False):
        st.markdown("**Ayes / noes** are votes for and against. **Whips** organise party voting. A **three-line whip** signals that MPs are expected to vote with the party. A **select committee** scrutinises policy and can publish evidence. A **cross-party compromise** trades concessions for support.")
        st.markdown("**Clear passage (346+)** means the government has a working margin. **Narrow passage (326–345)** means the policy is modelled as amended. **Below 326** means the bill is rejected and only a small pilot or administrative element goes ahead.")
