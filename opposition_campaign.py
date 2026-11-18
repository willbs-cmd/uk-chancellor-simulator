"""Opposition economic campaigns and the Chancellor's response.

Opposition attacks are generated from the simulated economic and public-service
record, use the strongest opposition party in the current Parliament, and create
a once-per-year opportunity for the Chancellor to respond.
"""
import hashlib

import streamlit as st

import state


def ensure(s=None):
    s = s or st.session_state
    s.setdefault("active_opposition_attack", None)
    s.setdefault("opposition_attack_history", [])
    s.setdefault("opposition_attack_last_period", "")
    return s


def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def _roll(s, period):
    raw = f"{s.get('seed', 0)}:{period}:opposition-economic-campaign"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16) % 100


def _opposition_party(s):
    import parliament
    seats = parliament._party_seats(s)
    government = s.get("party", "Labour")
    coalition = set(s.get("government_coalition_partners", [])) if s.get("government_type") == "coalition" else set()
    opposition = [party for party in state.PARTIES if party != government and party not in coalition]
    return max(opposition, key=lambda party: int(seats.get(party, 0))) if opposition else "Opposition"


def _assess_record(s):
    country = s.get("country") or {}
    services = s.get("public_service_scores") or {}
    scores = {
        "growth": max(0.0, (1.5 - float(s.get("growth", 0.0))) * 0.30)
                  + (0.45 if float(s.get("growth", 0.0)) < 0 else 0.0),
        "prices": max(0.0, float(s.get("inflation", 2.0)) - 2.3) * 0.34,
        "jobs": max(0.0, float(country.get("unemployment", 4.5)) - 4.8) * 0.32,
        "fiscal": max(0.0, 4.0 - float(s.get("headroom", 0.0))) * 0.24
                  + max(0.0, float(s.get("debt", 90.0)) - 90.0) * 0.018,
        "services": max(0.0, 66.0 - min(
            [float(v) for v in services.values()] or [60.0]
        )) * 0.055
                    + sum(float(item.get("severity", 1.0)) for item in s.get("public_service_strikes", [])) * 0.14,
        "living_standards": max(0.0, -float(country.get("real_wages", 0.0))) * 0.38
                            + max(0.0, 100.0 - float(s.get("disposable_income_index", 100.0))) * 0.025
                            + max(0.0, float(s.get("household_bill_pressure", 50.0)) - 55.0) * 0.035,
    }
    theme = max(scores, key=scores.get)
    score = float(scores[theme])
    if score < 0.18:
        theme, score = "growth", max(0.18, score)
    return theme, round(score, 2), scores


_HEADLINES = {
    "growth": "OPPOSITION: WHERE IS THE GROWTH PLAN?",
    "prices": "FAMILIES STILL FEEL THE SQUEEZE",
    "jobs": "CHANCELLOR HAS NO ANSWER FOR WORKING TOWNS",
    "fiscal": "TREASURY PROMISES FACE A BORROWING TEST",
    "services": "PUBLIC SERVICES LEFT TO CARRY THE COST",
    "living_standards": "LIVING STANDARDS BECOME THE POLITICAL BATTLEGROUND",
}
_LINES = {
    "growth": {
        "Conservative": "The Chancellor talks about stability, but output is weak and firms still want a credible plan to lift investment.",
        "Labour": "Ministers promised renewal. Communities are entitled to ask why growth and opportunity remain so uneven.",
        "Liberal Democrats": "The Government has not shown how its economic choices will deliver growth in every part of the country.",
        "Reform UK": "Westminster's economic establishment is failing working communities and has no convincing growth answer.",
        "Green Party": "The Treasury is still measuring success too narrowly instead of building a resilient, clean economy.",
        "SNP": "Westminster's economic decisions are not delivering the investment Scotland needs.",
        "Plaid Cymru": "The Chancellor has yet to show how the growth strategy will reach Welsh communities.",
    },
    "prices": {
        "Conservative": "Households are still paying the price through stubborn inflation and pressure on everyday budgets.",
        "Labour": "Working people need living standards to improve, not another explanation for why bills remain high.",
        "Liberal Democrats": "The Government has not done enough to protect families from the continued cost-of-living squeeze.",
        "Reform UK": "Families are still worse off and the Chancellor is asking them to be patient again.",
        "Green Party": "The Government must tackle expensive energy and insecure household finances together.",
        "SNP": "The cost-of-living response is not matching the pressure facing households across Scotland.",
        "Plaid Cymru": "Welsh families need more than a Westminster announcement while household costs remain high.",
    },
    "jobs": {
        "Conservative": "Weak labour-market conditions show why the country needs a more serious private-sector growth strategy.",
        "Labour": "The Government must explain why too many towns still feel the absence of secure, well-paid work.",
        "Liberal Democrats": "Local employers need practical support, not another round of Westminster slogans.",
        "Reform UK": "Working people want jobs and opportunity. The Chancellor is not delivering enough of either.",
        "Green Party": "A fair transition should create secure jobs in every region, and ministers must show where they are.",
        "SNP": "Scotland's employers need a stronger plan for jobs, skills and investment.",
        "Plaid Cymru": "The economic plan must reach Welsh workers and businesses beyond the largest cities.",
    },
    "fiscal": {
        "Conservative": "The Chancellor's fiscal promises are vulnerable to weaker growth, higher borrowing costs and another forecast downgrade.",
        "Labour": "The Treasury's rules cannot become an excuse for failing to invest in the services people rely on.",
        "Liberal Democrats": "The public deserves honest costings and a credible plan that does not leave local services exposed.",
        "Reform UK": "Borrowing, taxes and weak growth are a warning that the Government has lost control of its economic priorities.",
        "Green Party": "Fiscal choices should be transparent about who pays and whether long-term investment is being sacrificed.",
        "SNP": "Westminster's fiscal choices continue to constrain the investment and funding Scotland requires.",
        "Plaid Cymru": "The Chancellor must explain the implications of the Treasury settlement for Wales.",
    },
    "services": {
        "Conservative": "The Government cannot hide weak public-service performance behind the language of long-term reform.",
        "Labour": "Patients, pupils and council users need to see improvements, not just hear that the plan is working.",
        "Liberal Democrats": "Local services are under pressure and the Treasury must explain its priorities.",
        "Reform UK": "The public sees stretched services and a Government that keeps asking for more time.",
        "Green Party": "Public services need dependable funding and a plan that addresses the pressures on communities.",
        "SNP": "The Westminster approach risks leaving devolved services and local communities exposed.",
        "Plaid Cymru": "The Government must show how its decisions support Welsh public services and local councils.",
    },
    "living_standards": {
        "Conservative": "Real household finances remain under strain, and ministers have not made the recovery convincing.",
        "Labour": "The test of economic policy is whether families feel better off. Too many still do not.",
        "Liberal Democrats": "The Government needs to explain how its decisions will improve ordinary household finances.",
        "Reform UK": "People are tired of being told the economy is improving when their own budgets remain squeezed.",
        "Green Party": "A secure economy should mean affordable energy, housing and stronger household resilience.",
        "SNP": "Households across Scotland need a response that reflects local costs and conditions.",
        "Plaid Cymru": "The Chancellor must show how the plan will improve living standards in Wales.",
    },
}


def review_after_decision(s=None, decision=None, option=None):
    """Create at most one evidence-led opposition attack in each in-game year."""
    s = ensure(s)
    period = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    if int(s.get("block", 1)) != 1 or s.get("opposition_attack_last_period") == period:
        return None
    if s.get("active_opposition_attack"):
        return None
    theme, severity, scores = _assess_record(s)
    chance = min(92, 55 + int(severity * 12))
    s.opposition_attack_last_period = period
    if _roll(s, period) >= chance:
        return None
    party = _opposition_party(s)
    line = _LINES.get(theme, {}).get(
        party, "The opposition says the Chancellor's economic record does not match the Government's promises."
    )
    country = s.get("country") or {}
    evidence = {
        "growth": f"Real GDP growth is {float(s.get('growth', 0.0)):+.2f}%.",
        "prices": f"Inflation is {float(s.get('inflation', 2.0)):.2f}%.",
        "jobs": f"Unemployment is {float(country.get('unemployment', 4.5)):.2f}%.",
        "fiscal": f"Headroom is £{float(s.get('headroom', 0.0)):.1f}bn and debt is {float(s.get('debt', 0.0)):.1f}% of GDP.",
        "services": f"There are {len(s.get('public_service_strikes', []))} unresolved public-sector disputes; service scores remain under scrutiny.",
        "living_standards": f"Real wage growth is {float(country.get('real_wages', 0.0)):+.2f}% and the disposable-income index is {float(s.get('disposable_income_index', 100.0)):.1f}.",
    }.get(theme, "The opposition is challenging the Government's economic record.")
    issue = {
        "period": period,
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "party": party,
        "theme": theme,
        "headline": _HEADLINES.get(theme, "OPPOSITION PUTS THE ECONOMY UNDER THE MICROSCOPE"),
        "line": line,
        "evidence": evidence,
        "severity": severity,
        "source": "Opposition Treasury team",
        "trigger_decision": (decision or {}).get("title", "Recent Government decisions"),
        "resolved": False,
    }
    s.active_opposition_attack = issue
    s.opposition_attack_history = (list(s.get("opposition_attack_history", [])) + [dict(issue)])[-20:]
    cards = list(s.get("event_cards", []))
    cards.append({
        "title": f"Opposition attack · {party}",
        "text": line,
        "summary": f"{issue['headline']} · Your response is available in the Briefing tab.",
    })
    s.event_cards = cards[-12:]
    return issue


def _facts_are_defensible(s, theme):
    country = s.get("country") or {}
    if theme == "growth":
        return float(s.get("growth", 0.0)) >= 1.0
    if theme == "prices":
        return float(s.get("inflation", 2.0)) <= 2.8
    if theme == "jobs":
        return float(country.get("unemployment", 4.5)) <= 5.0
    if theme == "fiscal":
        return float(s.get("headroom", 0.0)) >= 3.0 and float(s.get("debt", 90.0)) <= 100.0
    if theme == "services":
        scores = s.get("public_service_scores") or {}
        return (not s.get("public_service_strikes")
                and (not scores or min(float(v) for v in scores.values()) >= 62.0))
    if theme == "living_standards":
        return (float(country.get("real_wages", 0.0)) >= 0.4
                and float(s.get("disposable_income_index", 100.0)) >= 100.0)
    return False


def resolve(choice, s=None):
    """Respond to opposition scrutiny; factual claims and remedies have distinct risks."""
    s = ensure(s)
    issue = s.get("active_opposition_attack")
    if not issue:
        return False, "There is no opposition attack awaiting a response."
    if choice not in {"facts", "plan", "counter", "ignore"}:
        return False, "Choose a valid response."
    state.checkpoint()
    before = state.values()
    state.snapshot()
    theme = issue.get("theme", "growth")
    if choice == "facts":
        if _facts_are_defensible(s, theme):
            s.approval = round(_clip(float(s.get("approval", 50.0)) + 0.45), 1)
            s.media_opinion = round(_clip(float(s.get("media_opinion", 50.0)) + 1.0), 1)
            s.market_conf = round(_clip(float(s.get("market_conf", 50.0)) + 0.35), 1)
            outcome = "You publish the latest figures and successfully challenge the opposition's central criticism."
        else:
            s.approval = round(_clip(float(s.get("approval", 50.0)) - 0.35), 1)
            s.media_opinion = round(_clip(float(s.get("media_opinion", 50.0)) - 0.7), 1)
            s.officials_confidence = round(_clip(float(s.get("officials_confidence", 70.0)) + 0.4), 1)
            outcome = "You publish the figures, but they underline the weakness the opposition identified. Officials welcome the transparency."
    elif choice == "plan":
        cost = 0.45 if float(s.get("headroom", 0.0)) >= 0 else 0.25
        s.headroom = round(float(s.get("headroom", 0.0)) - cost, 1)
        s.deficit = round(float(s.get("deficit", 0.0)) + cost, 1)
        s.approval = round(_clip(float(s.get("approval", 50.0)) + 0.7), 1)
        s.media_opinion = round(_clip(float(s.get("media_opinion", 50.0)) + 0.6), 1)
        s.pm_trust = round(_clip(float(s.get("pm_trust", 70.0)) + 0.5), 1)
        if float(s.get("headroom", 0.0)) < 2:
            s.market_conf = round(_clip(float(s.get("market_conf", 50.0)) - 0.35), 1)
        outcome = f"You announce a targeted corrective plan. It uses £{cost:.2f}bn of headroom but shows the Government is responding."
    elif choice == "counter":
        if (float(s.get("approval", 50.0)) >= 47
                and float(s.get("growth", 0.0)) >= 0
                and float(s.get("inflation", 2.0)) < 4.5):
            s.media_opinion = round(_clip(float(s.get("media_opinion", 50.0)) + 0.8), 1)
            s.approval = round(_clip(float(s.get("approval", 50.0)) + 0.25), 1)
            outcome = "Your counterattack lands. The opposition is forced to defend its own economic record."
        else:
            s.media_opinion = round(_clip(float(s.get("media_opinion", 50.0)) - 1.0), 1)
            s.approval = round(_clip(float(s.get("approval", 50.0)) - 0.4), 1)
            outcome = "The counterattack looks evasive while the figures remain weak. The opposition keeps the story alive."
    else:
        s.media_opinion = round(_clip(float(s.get("media_opinion", 50.0)) - 0.8), 1)
        s.approval = round(_clip(float(s.get("approval", 50.0)) - 0.4), 1)
        s.party_opinion = round(_clip(float(s.get("party_opinion", 50.0)) - 0.25), 1)
        outcome = "You ignore the opposition line. It avoids a public row today, but the criticism continues to circulate."

    record = dict(issue)
    record.update({"resolved": True, "response": choice, "outcome": outcome})
    history = list(s.get("opposition_attack_history", []))
    if history and history[-1].get("period") == issue.get("period"):
        history[-1] = record
    s.opposition_attack_history = history[-20:]
    s.active_opposition_attack = None
    s.message = outcome

    import engine
    engine.reseed("opposition-response")
    engine.update_polls(f"Y{(int(s.get('term', 1)) - 1) * 5 + int(s.get('year', 1))}.Opposition")
    state.log("politics", f"Opposition attack: {issue.get('headline', 'Economic record')}",
              choice=choice, before=before, note=outcome)
    state.record()
    return True, outcome


def render(s=None):
    """Render the latest opposition line and the Chancellor's four response options."""
    s = ensure(s)
    issue = s.get("active_opposition_attack")
    if issue:
        st.markdown("### Opposition campaign · response available")
        with st.container(border=True):
            st.caption(f"{issue.get('party', 'Opposition')} · Opposition Treasury team · {issue.get('source', '')}")
            st.markdown(f"**{issue.get('headline', 'The economy under scrutiny')}**")
            st.write(issue.get("line", "The opposition is challenging your economic record."))
            st.caption("Evidence they cite: " + issue.get("evidence", "The latest economic indicators."))
            st.caption("Choose how to handle the criticism. Your response changes media sentiment, polling and political confidence.")
            c1, c2 = st.columns(2)
            c3, c4 = st.columns(2)
            if c1.button("Publish the figures", key="opposition_response_facts", use_container_width=True):
                resolve("facts", s)
                st.rerun()
            if c2.button("Announce a corrective plan", key="opposition_response_plan", use_container_width=True):
                resolve("plan", s)
                st.rerun()
            if c3.button("Counterattack", key="opposition_response_counter", use_container_width=True):
                resolve("counter", s)
                st.rerun()
            if c4.button("Ignore the criticism", key="opposition_response_ignore", use_container_width=True):
                resolve("ignore", s)
                st.rerun()
    else:
        history = list(s.get("opposition_attack_history", []))
        if history:
            latest = history[-1]
            st.markdown("### Opposition campaign")
            st.caption(f"Latest attack · {latest.get('party', 'Opposition')} · {latest.get('headline', '')}")
            if latest.get("outcome"):
                st.write(latest["outcome"])
            with st.expander("Previous opposition attacks", expanded=False):
                for item in reversed(history[-5:]):
                    st.markdown(f"**Term {item.get('term', 1)} · Year {item.get('year', 1)} — {item.get('party', 'Opposition')}**")
                    st.caption(item.get("headline", ""))
                    st.write(item.get("outcome", item.get("line", "")))
