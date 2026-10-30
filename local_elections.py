"""Annual local election model for the UK Chancellor Simulator.

Council wards are simulated, not historical ward-level results. Results are
deterministic for a given term/year/seed and are intended as a political test
between general elections.
"""
import hashlib
import random

import pandas as pd
import streamlit as st

import state

REGIONS = [
    ("North East", "England", 34, {"Labour": 3, "Conservative": -1, "Reform UK": 1}),
    ("North West", "England", 42, {"Labour": 2, "Conservative": -1, "Reform UK": 1}),
    ("Yorkshire & Humber", "England", 38, {"Labour": 2, "Conservative": 0, "Reform UK": 1}),
    ("East Midlands", "England", 34, {"Conservative": 2, "Labour": -1, "Reform UK": 1}),
    ("West Midlands", "England", 38, {"Conservative": 1, "Labour": 0, "Reform UK": 1}),
    ("East of England", "England", 36, {"Conservative": 3, "Liberal Democrats": 1}),
    ("London", "England", 42, {"Labour": 4, "Green Party": 2, "Conservative": -2}),
    ("South East", "England", 42, {"Conservative": 3, "Liberal Democrats": 2}),
    ("South West", "England", 36, {"Liberal Democrats": 4, "Conservative": 1, "Green Party": 1}),
    ("Scotland", "Scotland", 36, {"SNP": 18, "Labour": 2, "Conservative": -2}),
    ("Wales", "Wales", 34, {"Plaid Cymru": 17, "Labour": 3, "Conservative": -2}),
    ("Northern Ireland", "Northern Ireland", 28, {"SNP": -8, "Plaid Cymru": -8, "Liberal Democrats": -5}),
]


def _seed(term, year, seed):
    raw = f"local:{term}:{year}:{seed}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:12], 16)


def calculate():
    s = st.session_state
    polls = {p: float(s.poll_history[p][-1]) for p in state.PARTIES}
    rng = random.Random(_seed(s.term, s.year, s.seed))
    results = []
    totals = {p: 0 for p in state.PARTIES}
    vote_totals = {p: 0.0 for p in state.PARTIES}
    all_wards = sum(r[2] for r in REGIONS)
    strategy = s.get('local_election_strategy', 'National campaign')
    governing_party = s.party
    campaign_regions = {name for name, nation, wards, lean in REGIONS if abs((polls.get(governing_party, 0) + lean.get(governing_party, 0)) - max((polls[p] + lean.get(p, 0) for p in state.PARTIES if p != governing_party), default=0)) <= 5}

    for region, nation, wards, lean in REGIONS:
        wins = {p: 0 for p in state.PARTIES}
        regional_votes = {p: 0.0 for p in state.PARTIES}
        for ward in range(wards):
            scores = {}
            for party in state.PARTIES:
                # Stable regional lean plus ward-level noise creates varied local outcomes.
                campaign_bonus = 0.0
                if party == governing_party:
                    if strategy == 'National campaign': campaign_bonus = 1.0
                    elif strategy == 'Target marginal councils' and region in campaign_regions: campaign_bonus = 2.4
                    elif strategy == 'Local services message' and region in {'North East', 'North West', 'West Midlands', 'Wales'}: campaign_bonus = 2.0
                scores[party] = max(0.1, polls[party] + lean.get(party, 0) + campaign_bonus + rng.gauss(0, 5.0))
                regional_votes[party] += scores[party]
            winner = max(scores, key=scores.get)
            wins[winner] += 1
            totals[winner] += 1
        denominator = sum(regional_votes.values()) or 1
        for party in state.PARTIES:
            vote_totals[party] += regional_votes[party] / denominator * wards
        leader = max(wins, key=wins.get)
        results.append({
            "region": region, "nation": nation, "wards": wards,
            "winner": leader, "seats": wins[leader],
            "party_seats": wins,
            "vote_share": {p: round(regional_votes[p] / denominator * 100, 1)
                           for p in state.PARTIES},
        })

    vote_share = {p: round(vote_totals[p] / all_wards * 100.0, 1) for p in state.PARTIES}
    governing = s.party
    gov_seats = totals.get(governing, 0)
    gov_share = gov_seats / all_wards
    # Local elections are a political signal, not a second general election.
    approval_change = round(max(-3.0, min(3.0, (gov_share - 0.34) * 7.0)), 1)
    s.approval = round(max(0.0, min(100.0, s.approval + approval_change)), 1)
    s.pm_opinion = round(max(0.0, min(100.0, s.pm_opinion + approval_change * 0.7)), 1)
    s.party_opinion = round(max(0.0, min(100.0, s.party_opinion + approval_change * 0.5)), 1)
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    previous = (s.get('local_election_history') or [])[-1] if s.get('local_election_history') else None
    seat_swing = {p: totals[p] - int(previous.get('seats', {}).get(p, 0)) for p in state.PARTIES} if previous else {p: 0 for p in state.PARTIES}
    vote_swing = {p: round(vote_share[p] - float(previous.get('vote_share', {}).get(p, 0)), 1) for p in state.PARTIES} if previous else {p: 0.0 for p in state.PARTIES}
    verdict = ('A decisive endorsement' if gov_share >= 0.45 else 'A respectable set of results' if gov_share >= 0.34 else 'A difficult night for the government' if gov_share >= 0.24 else 'A local election disaster')
    return {
        "term": int(s.term), "year": int(s.year), "governing_party": governing,
        "total_wards": all_wards, "seats": totals, "vote_share": vote_share,
        "regions": results, "governing_seats": gov_seats,
        "approval_change": approval_change, "winner": ordered[0][0],
        "seat_swing": seat_swing, "vote_swing": vote_swing, "strategy": strategy,
        "verdict": verdict, "majority": gov_seats > all_wards / 2,
        "turnout": round(rng.uniform(30.0, 42.0), 1),
        "note": "Illustrative simulated council contests; not a forecast or reconstruction of real council results.",
    }


def hold_election():
    s = st.session_state
    result = calculate()
    s.local_election_history = list(s.get("local_election_history", [])) + [result]
    s.local_election_result = result
    s.local_election_due = False
    s.message = (f"Local election results are in. {result['governing_party']} won "
                 f"{result['governing_seats']} of {result['total_wards']} simulated council seats. {result['verdict']}.")
    state.record()
    return result


def render(widget_namespace='government'):
    s = st.session_state
    st.markdown("## 🗳️ Local elections")
    st.caption("A major mid-term political test. Campaign choices shape the contest; results are simulated from national polling with regional and ward-level variation.")
    result = s.get("local_election_result")
    due = bool(s.get("local_election_due")) and (not result or result.get("term") != s.term or result.get("year") != s.year)
    if due:
        st.markdown("<div class='local-election-banner'><span>THE COUNT IS ABOUT TO BEGIN</span><h2>Local election day</h2><p>Term %s · Year %s · 440 simulated wards across the UK</p></div>" % (s.term, s.year), unsafe_allow_html=True)
        st.markdown("### Your campaign strategy")
        st.caption("Choose the message your party takes into the final days of the campaign. It has a modest effect on the simulated result.")
        strategy = st.radio("Campaign approach", ["National campaign", "Target marginal councils", "Local services message"], format_func=lambda x: {"National campaign": "National campaign — a disciplined message across the country", "Target marginal councils": "Target marginal councils — concentrate activists where the race is close", "Local services message": "Local services message — focus on council services and community issues"}[x], key=f"{widget_namespace}_local_campaign_strategy")
        s.local_election_strategy = strategy
        st.markdown("<div class='local-election-countdown'><strong>Polling stations are open.</strong><span>Turnout · Local issues · National mood · Ground campaign</span></div>", unsafe_allow_html=True)
        if st.button("Declare local election results", type="primary", use_container_width=True, key=f"{widget_namespace}_local_elections_hold_button"):
            hold_election()
            st.rerun()
        return
    if not result:
        st.info("Your first local elections will take place after the first financial year.")
        return
    st.markdown("<div class='local-election-banner results'><span>LOCAL ELECTIONS · RESULTS NIGHT</span><h2>%s</h2><p>Term %s · Year %s · %s</p></div>" % (result.get("verdict", "Results declared"), result["term"], result["year"], result.get("strategy", "National campaign")), unsafe_allow_html=True)
    if result.get("majority"):
        st.success(f"{result['governing_party']} finishes the night with a majority of the simulated wards.")
    elif result["winner"] != result["governing_party"]:
        st.error(f"{result['winner']} leads the national council seat tally. A difficult night for the government.")
    else:
        st.warning(f"{result['governing_party']} leads the seat tally but falls short of a majority.")
    a, b, cc, d = st.columns(4)
    has_previous = len(s.get("local_election_history", [])) > 1
    a.metric("Governing party seats", f"{result['governing_seats']}/{result['total_wards']}", delta=f"{result.get('seat_swing', {}).get(result['governing_party'], 0):+d}" if has_previous else None)
    b.metric("Estimated turnout", f"{result['turnout']:.1f}%")
    cc.metric("National local vote", f"{result['vote_share'].get(result['governing_party'], 0):.1f}%", delta=f"{result.get('vote_swing', {}).get(result['governing_party'], 0):+.1f} pts" if has_previous else None)
    d.metric("Approval impact", f"{result['approval_change']:+.1f} pts")
    st.markdown("### The national council picture")
    chart_rows = [{"Party": p, "Council seats": n} for p, n in sorted(result["seats"].items(), key=lambda x: x[1], reverse=True)]
    st.bar_chart(pd.DataFrame(chart_rows).set_index("Party"), horizontal=True, use_container_width=True)
    st.markdown("### Council seat totals")
    rows = [{"Party": p, "Council seats": n, "Seat change": f"{result.get('seat_swing', {}).get(p, 0):+d}" if has_previous else "First contest", "Local vote share": f"{result['vote_share'].get(p, 0):.1f}%", "Vote change": f"{result.get('vote_swing', {}).get(p, 0):+.1f} pts" if has_previous else "—"} for p, n in sorted(result["seats"].items(), key=lambda x: x[1], reverse=True)]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.markdown("### Regional battlegrounds")
    regional = [{"Region": r["region"], "Leading party": r["winner"], "Leader's wards": r["seats"], "Contested wards": r["wards"], "Governing party wards": r["party_seats"].get(result["governing_party"], 0)} for r in result["regions"]]
    st.dataframe(pd.DataFrame(regional), hide_index=True, use_container_width=True)
    with st.expander("Full regional party breakdown", key=f"{widget_namespace}_regional_party_breakdown"):
        for r in result["regions"]:
            st.markdown(f"**{r['region']}**")
            st.caption(" · ".join(f"{p}: {n}" for p, n in sorted(r["party_seats"].items(), key=lambda x: x[1], reverse=True) if n))
    st.caption(result["note"])
    history = s.get("local_election_history", [])
    if len(history) > 1:
        st.markdown("### Previous local elections")
        st.dataframe(pd.DataFrame([{"Term": x["term"], "Year": x["year"], "Governing party": x["governing_party"], "Governing seats": f"{x['governing_seats']}/{x['total_wards']}", "Approval impact": f"{x['approval_change']:+.1f}"} for x in reversed(history)]), hide_index=True, use_container_width=True)
