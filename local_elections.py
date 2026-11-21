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


CAMPAIGN_ACTIONS = {
    1: {
        "Canvass the closest councils": {
            "description": "Put organisers into the most competitive wards in your chosen region.",
            "scope": "region", "vote_bonus": 2.2, "turnout_bonus": 0.5, "approval_effect": 0.0,
        },
        "Launch a council-record campaign": {
            "description": "Take the Government's local record to voters across the country.",
            "scope": "all", "vote_bonus": 0.8, "turnout_bonus": 0.2, "approval_effect": 0.15,
        },
        "Build local volunteer networks": {
            "description": "Recruit community organisers and build a stronger ground operation.",
            "scope": "region", "vote_bonus": 1.0, "turnout_bonus": 0.9, "approval_effect": 0.0,
        },
    },
    2: {
        "Defend frontline council services": {
            "description": "Focus on social care, waste, roads and everyday local services.",
            "scope": "region", "vote_bonus": 1.8, "turnout_bonus": 0.2, "approval_effect": 0.2,
        },
        "Tour town centres and housing schemes": {
            "description": "Make local regeneration, planning and affordable homes the centre of the campaign.",
            "scope": "region", "vote_bonus": 1.6, "turnout_bonus": 0.5, "approval_effect": 0.1,
        },
        "Challenge opposition-run councils": {
            "description": "Highlight local performance and offer an alternative plan.",
            "scope": "region", "vote_bonus": 1.7, "turnout_bonus": 0.3, "approval_effect": 0.0,
        },
    },
    3: {
        "Run a targeted get-out-the-vote operation": {
            "description": "Concentrate polling-day reminders and transport on your chosen battleground.",
            "scope": "region", "vote_bonus": 1.0, "turnout_bonus": 2.0, "approval_effect": 0.0,
        },
        "Mobilise supporters nationwide": {
            "description": "Use volunteers, postal-vote reminders and local organisers across every region.",
            "scope": "all", "vote_bonus": 0.7, "turnout_bonus": 1.5, "approval_effect": 0.0,
        },
        "Send the party leader on a final regional tour": {
            "description": "A high-profile visit can lift local morale and attract undecided voters.",
            "scope": "region", "vote_bonus": 1.6, "turnout_bonus": 0.8, "approval_effect": 0.2,
        },
    },
}


def record_campaign_action(s, action, target_region):
    """Commit one of three campaign rounds without altering the live polling figures."""
    week = max(1, int(s.get("local_campaign_week", 1)))
    config = CAMPAIGN_ACTIONS.get(week, {}).get(action)
    if not config or s.get("local_campaign_done"):
        return False
    valid_regions = [row[0] for row in REGIONS]
    if config["scope"] == "region" and target_region not in valid_regions:
        return False
    entry = {
        "week": week, "action": action,
        "region": target_region if config["scope"] == "region" else "All regions",
        "scope": config["scope"], "vote_bonus": float(config["vote_bonus"]),
        "turnout_bonus": float(config["turnout_bonus"]),
        "approval_effect": float(config["approval_effect"]),
        "description": config["description"],
    }
    s["local_campaign_actions"] = list(s.get("local_campaign_actions", [])) + [entry]
    s["local_campaign_week"] = week + 1
    s["local_campaign_done"] = week >= 3
    s["local_election_strategy"] = action
    s["local_campaign_target_region"] = target_region
    s["message"] = f"Local campaign round {week} complete: {action}."
    return True


def calculate():
    s = st.session_state
    polls = {p: float(s.poll_history[p][-1]) for p in state.PARTIES}
    rng = random.Random(_seed(s.term, s.year, s.seed))
    totals = {p: 0 for p in state.PARTIES}
    vote_totals = {p: 0.0 for p in state.PARTIES}
    all_wards = sum(r[2] for r in REGIONS)
    governing = s.party
    actions = list(s.get("local_campaign_actions", []))
    legacy_strategy = s.get("local_election_strategy", "National campaign")
    close_regions = {
        name for name, nation, wards, lean in REGIONS
        if abs((polls[governing] + lean.get(governing, 0))
               - max((polls[p] + lean.get(p, 0) for p in state.PARTIES if p != governing), default=0)) <= 5
    }
    regional_results = []
    for region, nation, wards, lean in REGIONS:
        wins = {p: 0 for p in state.PARTIES}
        regional_votes = {p: 0.0 for p in state.PARTIES}
        bonus = sum(
            float(item.get("vote_bonus", 0.0)) for item in actions
            if item.get("scope") == "all" or item.get("region") == region
        )
        if not actions:
            if legacy_strategy == "National campaign":
                bonus += 1.0
            elif legacy_strategy == "Target marginal councils" and region in close_regions:
                bonus += 2.4
            elif legacy_strategy == "Local services message" and region in {"North East", "North West", "West Midlands", "Wales"}:
                bonus += 2.0
        for _ward in range(wards):
            scores = {}
            for party in state.PARTIES:
                party_bonus = bonus if party == governing else 0.0
                score = max(0.1, polls[party] + lean.get(party, 0) + party_bonus + rng.gauss(0, 5.0))
                scores[party] = score
                regional_votes[party] += score
            winner = max(scores, key=scores.get)
            wins[winner] += 1
            totals[winner] += 1
        denominator = sum(regional_votes.values()) or 1.0
        for party in state.PARTIES:
            vote_totals[party] += regional_votes[party] / denominator * wards
        leader = max(wins, key=wins.get)
        regional_results.append({
            "region": region, "nation": nation, "wards": wards,
            "winner": leader, "seats": wins[leader],
            "control": leader if wins[leader] > wards / 2 else "No overall control",
            "party_seats": wins, "campaign_bonus": round(bonus, 2),
            "vote_share": {p: round(regional_votes[p] / denominator * 100, 1) for p in state.PARTIES},
        })

    vote_share = {p: round(vote_totals[p] / all_wards * 100, 1) for p in state.PARTIES}
    gov_seats = totals.get(governing, 0)
    gov_share = gov_seats / all_wards
    previous = (s.get("local_election_history") or [])[-1] if s.get("local_election_history") else None
    seat_swing = {p: totals[p] - int(previous.get("seats", {}).get(p, 0)) for p in state.PARTIES} if previous else {p: 0 for p in state.PARTIES}
    vote_swing = {p: round(vote_share[p] - float(previous.get("vote_share", {}).get(p, 0)), 1) for p in state.PARTIES} if previous else {p: 0.0 for p in state.PARTIES}
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    verdict = ("A decisive endorsement" if gov_share >= 0.45 else
               "A respectable set of results" if gov_share >= 0.34 else
               "A difficult night for the government" if gov_share >= 0.24 else
               "A local election disaster")
    controls = {row["region"]: row["control"] for row in regional_results}
    old_controls = s.get("local_council_control_by_region", {})
    control_changes = {
        region: {"previous": old_controls.get(region, "Not recorded"), "current": control,
                 "changed": bool(old_controls.get(region) and old_controls.get(region) != control)}
        for region, control in controls.items()
    }
    controlled_regions = {p: sum(1 for control in controls.values() if control == p) for p in state.PARTIES}
    no_control = sum(1 for control in controls.values() if control == "No overall control")
    campaign_turnout = sum(float(item.get("turnout_bonus", 0)) for item in actions)
    campaign_approval = sum(float(item.get("approval_effect", 0)) for item in actions)
    approval_change = round(max(-4.0, min(4.0, (gov_share - 0.34) * 7.0 + campaign_approval)), 1)
    majority = gov_seats > all_wards / 2
    party_change = 2.5 if gov_share >= 0.40 else 1.0 if gov_share >= 0.34 else -2.0 if gov_share < 0.24 else -0.75
    backbench_change = 2.0 if gov_share >= 0.40 else 0.5 if gov_share >= 0.34 else -3.0 if gov_share < 0.24 else -1.0
    local_mandate = 2.0 if majority else -2.0 if ordered[0][0] != governing else -0.5
    return {
        "term": int(s.term), "year": int(s.year), "governing_party": governing,
        "total_wards": all_wards, "seats": totals, "vote_share": vote_share,
        "regions": regional_results, "governing_seats": gov_seats,
        "approval_change": approval_change, "winner": ordered[0][0],
        "seat_swing": seat_swing, "vote_swing": vote_swing,
        "strategy": s.get("local_election_strategy", "Local campaign"),
        "campaign_actions": actions, "verdict": verdict, "majority": majority,
        "council_control": dict(totals), "control_swing": {
            p: totals[p] - int(s.get("council_control", {}).get(p, 0)) for p in state.PARTIES
        },
        "council_control_by_region": controls, "regional_control_changes": control_changes,
        "controlled_regions": controlled_regions, "no_overall_control": no_control,
        "party_change": party_change, "backbench_change": backbench_change,
        "local_government_mandate": local_mandate,
        "turnout": round(min(48.0, rng.uniform(30.0, 42.0) + campaign_turnout), 1),
        "note": "Illustrative simulated council wards and regional council-control groupings; not a forecast or reconstruction of real council results.",
    }


def hold_election():
    s = st.session_state
    current = s.get("local_election_result")
    if current and int(current.get("term", -1)) == int(s.get("term", 1)) and int(current.get("year", -1)) == int(s.get("year", 1)):
        return current
    result = calculate()
    s.local_election_history = list(s.get("local_election_history", [])) + [result]
    s.local_election_result = result
    s.local_election_due = False
    s.local_campaign_done = True
    s.council_control = dict(result["council_control"])
    s.local_council_control_by_region = dict(result["council_control_by_region"])
    s.approval = round(max(0.0, min(100.0, float(s.get("approval", 50)) + result["approval_change"])), 1)
    s.pm_opinion = round(max(0.0, min(100.0, float(s.get("pm_opinion", 75)) + result["approval_change"] * 0.7)), 1)
    s.party_opinion = round(max(0.0, min(100.0, float(s.get("party_opinion", 65)) + result["approval_change"] * 0.5 + result["party_change"])), 1)
    s.backbench_opinion = round(max(0.0, min(100.0, float(s.get("backbench_opinion", 60)) + result["backbench_change"])), 1)
    s.local_government_mandate = round(float(result["local_government_mandate"]), 1)
    capital = int(s.get("political_capital_points", 5))
    if result["majority"]:
        s.political_capital_points = min(5, capital + 1)
    elif result["verdict"] == "A local election disaster":
        s.political_capital_points = max(0, capital - 1)
    s.message = (f"Local election results are in. {result['governing_party']} won "
                 f"{result['governing_seats']} of {result['total_wards']} simulated council wards. {result['verdict']}.")
    state.record()
    return result


def render(widget_namespace="government"):
    s = st.session_state
    st.markdown("## 🗳️ Local elections")
    st.caption("Three-round local campaigns now shape council ward contests. Results affect approval, party confidence and the spread of council control.")
    s.setdefault("local_campaign_week", 1)
    s.setdefault("local_campaign_actions", [])
    s.setdefault("local_campaign_done", False)
    s.setdefault("local_campaign_target_region", "North West")
    result = s.get("local_election_result")
    due = bool(s.get("local_election_due")) and (
        not result or int(result.get("term", -1)) != int(s.get("term", 1))
        or int(result.get("year", -1)) != int(s.get("year", 1))
    )
    if due:
        st.markdown("<div class='local-election-banner'><span>THE COUNT IS APPROACHING</span><h2>Local election campaign</h2><p>Three rounds · 440 simulated wards · 12 regional contests</p></div>", unsafe_allow_html=True)
        if not s.get("local_campaign_done"):
            week = min(3, max(1, int(s.local_campaign_week)))
            st.progress((week - 1) / 3, text=f"Campaign progress · round {week} of 3")
            st.markdown(f"### Round {week} · {['Build the ground operation', 'Make the local case', 'Polling-day mobilisation'][week - 1]}")
            target_options = ["All regions"] + [row[0] for row in REGIONS]
            saved_target = s.get("local_campaign_target_region", "North West")
            target_index = target_options.index(saved_target) if saved_target in target_options else 1
            target_region = st.selectbox("Campaign focus region", target_options, index=target_index,
                key=f"{widget_namespace}_local_campaign_region_{week}",
                help="Regional actions concentrate support in one area. Nationwide actions ignore this selection.")
            action_keys = list(CAMPAIGN_ACTIONS[week])
            chosen = st.radio("Campaign operation", action_keys,
                format_func=lambda key: f"{key} — {CAMPAIGN_ACTIONS[week][key]['description']}",
                key=f"{widget_namespace}_local_campaign_action_{week}")
            st.caption("Campaign decisions do not change the approved Budget, tax or spending ledgers.")
            if s.get("local_campaign_actions"):
                with st.expander("Campaign diary", expanded=False):
                    for item in s.local_campaign_actions:
                        st.write(f"**Round {item['week']}:** {item['action']} · {item['region']}")
            if st.button("Commit this campaign operation", type="primary", use_container_width=True, key=f"{widget_namespace}_local_campaign_commit_{week}"):
                if record_campaign_action(s, chosen, target_region):
                    st.rerun()
        else:
            st.success("The three-round campaign is complete. Your operations are now reflected in the election model.")
            if st.button("Declare local election results", type="primary", use_container_width=True, key=f"{widget_namespace}_local_elections_hold_button"):
                hold_election()
                st.rerun()
        st.stop()
    if not result:
        st.info("Your first local elections will take place after the first financial year.")
        return
    st.markdown(f"### {result.get('verdict', 'Results declared')} · Term {result['term']}, Year {result['year']}")
    if result.get("majority"):
        st.success(f"{result['governing_party']} finishes the night with a majority of simulated council wards.")
    elif result["winner"] != result["governing_party"]:
        st.error(f"{result['winner']} leads the council ward tally. A difficult night for the government.")
    else:
        st.warning(f"{result['governing_party']} leads the ward tally but falls short of a majority.")
    a, b, c, d = st.columns(4)
    has_previous = len(s.get("local_election_history", [])) > 1
    a.metric("Governing party wards", f"{result['governing_seats']}/{result['total_wards']}",
             delta=f"{result.get('seat_swing', {}).get(result['governing_party'], 0):+d}" if has_previous else None)
    b.metric("Estimated turnout", f"{result['turnout']:.1f}%")
    c.metric("National local vote", f"{result['vote_share'].get(result['governing_party'], 0):.1f}%",
             delta=f"{result.get('vote_swing', {}).get(result['governing_party'], 0):+.1f} pts" if has_previous else None)
    d.metric("Approval impact", f"{result['approval_change']:+.1f} pts")
    st.markdown("### Council control")
    control_rows = [{
        "Party": p, "Council wards": n,
        "Change": f"{result.get('control_swing', {}).get(p, 0):+d}",
        "Regional groupings controlled": result.get("controlled_regions", {}).get(p, 0),
    } for p, n in sorted(result["seats"].items(), key=lambda item: item[1], reverse=True)]
    st.dataframe(pd.DataFrame(control_rows), hide_index=True, use_container_width=True)
    st.caption(f"No overall control in {result.get('no_overall_control', 0)} of {len(REGIONS)} regional council groupings.")
    st.markdown("### Regional council control")
    control_changes = result.get("regional_control_changes", {})
    region_rows = [{
        "Region": row["region"], "Leader": row["winner"],
        "Overall control": row.get("control", "No overall control"),
        "Ward majority": f"{row['seats']}/{row['wards']}",
        "Control change": "Changed hands" if control_changes.get(row["region"], {}).get("changed") else "—",
    } for row in result["regions"]]
    st.dataframe(pd.DataFrame(region_rows), hide_index=True, use_container_width=True)
    st.markdown("### Ward totals by party")
    chart_rows = [{"Party": p, "Council wards": n} for p, n in sorted(result["seats"].items(), key=lambda item: item[1], reverse=True)]
    st.bar_chart(pd.DataFrame(chart_rows).set_index("Party"), horizontal=True, use_container_width=True)
    st.markdown("### Regional battlegrounds")
    regional = [{
        "Region": row["region"], "Leading party": row["winner"],
        "Leading party wards": row["seats"], "Contested wards": row["wards"],
        "Governing party wards": row["party_seats"].get(result["governing_party"], 0),
        "Campaign advantage": row.get("campaign_bonus", 0.0),
    } for row in result["regions"]]
    st.dataframe(pd.DataFrame(regional), hide_index=True, use_container_width=True)
    with st.expander("Full regional party breakdown", expanded=False):
        for row in result["regions"]:
            st.markdown(f"**{row['region']}**")
            st.caption(" · ".join(f"{p}: {n}" for p, n in sorted(row["party_seats"].items(), key=lambda item: item[1], reverse=True) if n))
    st.caption(result["note"])
    history = s.get("local_election_history", [])
    if len(history) > 1:
        st.markdown("### Previous local elections")
        hist_rows = [{
            "Term": item["term"], "Year": item["year"], "Governing party": item["governing_party"],
            "Governing wards": f"{item['governing_seats']}/{item['total_wards']}",
            "Ward swing": item.get("seat_swing", {}).get(item["governing_party"], 0),
            "Approval impact": f"{item['approval_change']:+.1f}",
        } for item in reversed(history)]
        st.dataframe(pd.DataFrame(hist_rows), hide_index=True, use_container_width=True)
