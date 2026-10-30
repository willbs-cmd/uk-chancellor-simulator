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

    for region, nation, wards, lean in REGIONS:
        wins = {p: 0 for p in state.PARTIES}
        regional_votes = {p: 0.0 for p in state.PARTIES}
        for ward in range(wards):
            scores = {}
            for party in state.PARTIES:
                # Stable regional lean plus ward-level noise creates varied local outcomes.
                scores[party] = max(0.1, polls[party] + lean.get(party, 0)
                                    + rng.gauss(0, 5.0))
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
    return {
        "term": int(s.term), "year": int(s.year), "governing_party": governing,
        "total_wards": all_wards, "seats": totals, "vote_share": vote_share,
        "regions": results, "governing_seats": gov_seats,
        "approval_change": approval_change, "winner": ordered[0][0],
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
                 f"{result['governing_seats']} of {result['total_wards']} simulated council seats.")
    state.record()
    return result


def render(widget_namespace='government'):
    s = st.session_state
    st.markdown("## 🗳️ Local elections")
    st.caption("Annual council contests provide a mid-term test of your government's popularity. Council seats are simulated from national polling with regional and ward-level variation.")
    result = s.get("local_election_result")
    if s.get("local_election_due") and (not result or result.get("term") != s.term or result.get("year") != s.year):
        st.info(f"Local election day · Term {s.term}, Year {s.year}. The councils are going to the polls.")
        if st.button("Hold local elections", type="primary", use_container_width=True, key=f"{widget_namespace}_local_elections_hold_button"):
            hold_election()
            st.rerun()
        return
    if not result:
        st.info("Your first local elections will take place after the first financial year.")
        return
    st.markdown(f"### Term {result['term']} · Year {result['year']} results")
    a, b, c, d = st.columns(4)
    a.metric("Council seats won", f"{result['governing_seats']}/{result['total_wards']}")
    b.metric("Estimated turnout", f"{result['turnout']:.1f}%")
    c.metric("National local vote", f"{result['vote_share'].get(result['governing_party'], 0):.1f}%")
    d.metric("Approval impact", f"{result['approval_change']:+.1f} pts")
    st.markdown("### Council seat totals")
    rows = [{"Party": p, "Council seats": n, "Local vote share": f"{result['vote_share'].get(p, 0):.1f}%"}
            for p, n in sorted(result["seats"].items(), key=lambda x: x[1], reverse=True)]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    st.markdown("### Regional results")
    regional = [{"Region": r["region"], "Leading party": r["winner"],
                 "Seats won by leader": r["seats"], "Contested wards": r["wards"]}
                for r in result["regions"]]
    st.dataframe(pd.DataFrame(regional), hide_index=True, use_container_width=True)
    with st.expander("Regional party breakdown", key=f"{widget_namespace}_regional_party_breakdown"):
        for r in result["regions"]:
            st.markdown(f"**{r['region']}**")
            st.caption(" · ".join(f"{p}: {n}" for p, n in sorted(r["party_seats"].items(), key=lambda x: x[1], reverse=True) if n))
    st.caption(result["note"])
    history = s.get("local_election_history", [])
    if len(history) > 1:
        st.markdown("### Previous local elections")
        st.dataframe(pd.DataFrame([{
            "Term": x["term"], "Year": x["year"], "Governing party": x["governing_party"],
            "Governing seats": f"{x['governing_seats']}/{x['total_wards']}",
            "Approval impact": f"{x['approval_change']:+.1f}"
        } for x in reversed(history)]), hide_index=True, use_container_width=True)
