"""Individual constituency MPs and local priorities for Commons votes.

The register uses official 2024 Westminster constituency names and codes, but MP
names and personal profiles are fictional simulation data, not real elected MPs.
"""
import hashlib
import json
from pathlib import Path

import streamlit as st
import state

_FIRST_NAMES = (
    "Alex", "Amira", "Ben", "Beth", "Callum", "Catherine", "Daniel", "Eleanor",
    "Ella", "Emily", "Farah", "George", "Hannah", "Harriet", "Imran", "Jack",
    "James", "Jasmine", "Leah", "Liam", "Lucy", "Maya", "Michael", "Nadia",
    "Nathan", "Oliver", "Peter", "Rachel", "Rebecca", "Rhys", "Robert",
    "Sam", "Sarah", "Sophie", "Thomas", "Victoria", "Yasmin", "Zac",
)
_LAST_NAMES = (
    "Abbott", "Ahmed", "Barker", "Bennett", "Brooks", "Campbell", "Clarke",
    "Cole", "Davies", "Dawson", "Edwards", "Ellis", "Evans", "Fletcher",
    "Foster", "Gardner", "Gibson", "Graham", "Grant", "Gray", "Hall",
    "Harris", "Hughes", "Jackson", "James", "Khan", "Lewis", "Marshall",
    "Mason", "Morgan", "Morris", "Murphy", "Owen", "Patel", "Pritchard",
    "Reed", "Rees", "Roberts", "Shah", "Shaw", "Singh", "Taylor",
    "Thomas", "Turner", "Walker", "Watson", "White", "Williams", "Wilson",
    "Wood", "Wright", "Young",
)
PRIORITIES = (
    "public_services", "cost_of_living", "jobs_growth", "rural_transport",
    "housing", "environment", "devolution", "defence",
)
PRIORITY_LABELS = {
    "public_services": "NHS and public services",
    "cost_of_living": "Cost of living",
    "jobs_growth": "Jobs and economic growth",
    "rural_transport": "Rural communities and transport",
    "housing": "Housing and planning",
    "environment": "Climate and energy",
    "devolution": "Local and devolved funding",
    "defence": "Defence and security",
}
FACTION_IDEOLOGIES = {
    "Party Mainstream": ("Centric", "Social Democratic"),
    "Labour Right": ("Social Democratic", "Centric"),
    "Soft Left": ("Social Democratic", "Hard Left"),
    "Socialist Left": ("Hard Left",),
    "One Nation": ("Centric", "Social Democratic"),
    "Thatcherite Right": ("Free-Market", "Fiscal Austerity"),
    "New Right": ("Free-Market", "Fiscal Austerity"),
    "Social Liberal": ("Centric", "Social Democratic"),
    "Economic Liberal": ("Centric", "Free-Market"),
    "Federalist": ("Centric", "Social Democratic"),
    "Populist": ("Free-Market", "Fiscal Austerity"),
    "National Conservative": ("Fiscal Austerity", "Centric"),
    "Green Pragmatist": ("Social Democratic", "Centric"),
    "Eco-Socialist": ("Hard Left", "Social Democratic"),
    "Decentralist": ("Social Democratic", "Centric"),
    "SNP Mainstream": ("Social Democratic", "Centric"),
    "Independence Pragmatist": ("Centric", "Social Democratic"),
    "Civic Nationalist": ("Centric", "Social Democratic"),
    "Welsh Social Democrat": ("Social Democratic", "Centric"),
    "Welsh Socialist": ("Hard Left", "Social Democratic"),
}


def _hash_int(*parts):
    return int(hashlib.sha256(":".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:8], 16)


def _load_constituencies():
    path = Path(__file__).resolve().parent / "data" / "constituencies_2024.json"
    with path.open(encoding="utf-8") as handle:
        rows = json.load(handle).get("constituencies", [])
    if len(rows) != 650:
        raise ValueError("The 2024 Westminster constituency register must contain 650 seats.")
    return rows


def _estimated_results(s):
    import engine
    history = s.get("poll_history", {})
    polls = {
        party: float(history.get(party, [0.0])[-1]) if history.get(party) else 0.0
        for party in state.PARTIES
    }
    _, results = engine.compute_seats(polls, return_details=True)
    opening = s.get("opening_parliament_seats", {})
    if opening and sum(int(opening.get(party, 0)) for party in state.PARTIES) == 650:
        targets = {party: int(opening.get(party, 0)) for party in state.PARTIES}
        counts = {party: sum(1 for row in results if row.get("winner") == party)
                  for party in state.PARTIES}
        # Match the actual opening Commons arithmetic exactly, while preserving
        # the closest local contests as the seats most likely to change hands.
        while any(counts[p] != targets[p] for p in state.PARTIES):
            deficits = [p for p in state.PARTIES if counts[p] < targets[p]]
            surpluses = {p for p in state.PARTIES if counts[p] > targets[p]}
            if not deficits or not surpluses:
                break
            moved = False
            for receiving_party in deficits:
                candidates = sorted(
                    (row for row in results if row.get("winner") in surpluses),
                    key=lambda row: (
                        0 if row.get("runner_up") == receiving_party else 1,
                        float(row.get("margin", 0.0)), row.get("code", ""),
                    ),
                )
                if not candidates:
                    continue
                row = candidates[0]
                losing_party = row.get("winner")
                row["winner"], row["runner_up"] = receiving_party, losing_party
                row["margin"] = max(0.1, float(row.get("margin", 0.0)))
                row["is_marginal"] = True
                counts[losing_party] -= 1
                counts[receiving_party] += 1
                moved = True
                if counts[receiving_party] >= targets[receiving_party]:
                    break
            if not moved:
                break
    return {str(row.get("code", "")): row for row in results}


def _local_issue(seat):
    name, nation = str(seat.get("name", "")).lower(), str(seat.get("nation", "England"))
    if any(word in name for word in ("shire", "vale", "moor", "coast", "dales", "downs")):
        return "rural_transport"
    if any(word in name for word in ("university", "cambridge", "oxford", "edinburgh", "durham")):
        return "jobs_growth"
    if any(word in name for word in ("port", "dock", "harbour", "island")):
        return "jobs_growth"
    if any(word in name for word in ("city", "central", "inner")):
        return "cost_of_living"
    if nation in ("Scotland", "Wales", "Northern Ireland"):
        return "devolution"
    return PRIORITIES[_hash_int("local-issue", seat.get("code", "")) % len(PRIORITIES)]


def _make_profile(s, seat, party, margin):
    import cabinet_management
    code, term, seed = str(seat.get("code", seat.get("name", ""))), int(s.get("term", 1)), int(s.get("seed", 0))
    digest = _hash_int(seed, term, code, party, "mp-profile")
    factions = cabinet_management.PARTY_FACTIONS.get(party, ["Party Mainstream", "Government Mainstream"])
    faction = factions[digest % len(factions)]
    first = _FIRST_NAMES[_hash_int(seed, code, party, "first") % len(_FIRST_NAMES)]
    last = _LAST_NAMES[_hash_int(seed, code, party, "last") % len(_LAST_NAMES)]
    priorities = {item: 28 + (_hash_int(seed, code, party, item) % 68) for item in PRIORITIES}
    local_issue = _local_issue(seat)
    priorities[local_issue] = max(priorities[local_issue], 78)
    order = sorted(PRIORITIES, key=lambda item: priorities[item], reverse=True)
    margin = max(0.1, float(margin))
    return {
        "code": code, "constituency": str(seat.get("name", "Unknown constituency")),
        "nation": str(seat.get("nation", "England")), "party": party,
        "name": f"{first} {last}", "faction": faction, "priorities": priorities,
        "top_priority": order[0], "second_priority": order[1],
        "local_issue": local_issue, "margin": round(margin, 1),
        "is_marginal": margin < 5.0,
    }


def ensure(s=None):
    s = s or st.session_state
    profiles = dict(s.get("mp_profiles", {}))
    seats = _load_constituencies()
    result = s.get("election_result") or {}
    rows = result.get("constituency_results", []) if isinstance(result, dict) else []
    result_map = {
        str(row.get("code", "")): row for row in rows
        if isinstance(row, dict) and row.get("code")
    }
    incumbents = s.get("constituency_incumbents", {})
    if not result_map and not incumbents:
        result_map = _estimated_results(s)

    updated = {}
    for seat in seats:
        code = str(seat.get("code", seat.get("name", "")))
        old = profiles.get(code, {})
        row = result_map.get(code, {})
        party = row.get("winner") or incumbents.get(code) or old.get("party") or s.get("party", "Labour")
        if party not in state.PARTIES:
            party = s.get("party", "Labour")
        margin = row.get("margin", old.get("margin", 8.0))
        if not old or old.get("party") != party:
            updated[code] = _make_profile(s, seat, party, margin)
        else:
            profile = dict(old)
            profile.update({
                "constituency": str(seat.get("name", profile.get("constituency", ""))),
                "nation": str(seat.get("nation", profile.get("nation", "England"))),
                "margin": round(max(0.1, float(margin)), 1),
                "is_marginal": float(margin) < 5.0,
            })
            updated[code] = profile
    s.mp_profiles = updated
    s.mp_roster_term = int(s.get("term", 1))
    s.mp_roster_count = len(updated)
    return updated


def _signal(effect, keys, inverted=()):
    total, inverted = 0.0, set(inverted)
    for key in keys:
        try:
            value = float(effect.get(key, 0.0))
        except (TypeError, ValueError):
            value = 0.0
        total += -value if key in inverted else value
    return max(-1.0, min(1.0, total / 3.0))


def _policy_signals(option):
    effect = option.get("effect", option.get("fx", {})) or {}
    return {
        "public_services": _signal(effect, (
            "health", "education", "welfare", "nhs_morale", "nhs_waiting",
            "schools", "prisons", "local_service_delivery", "social_care",
        ), inverted=("nhs_waiting",)),
        "cost_of_living": _signal(effect, (
            "real_wages", "household_confidence", "disposable_income_index",
            "mortgage_pressure", "rent_pressure", "household_bill_pressure", "inflation",
        ), inverted=("mortgage_pressure", "rent_pressure", "household_bill_pressure", "inflation")),
        "jobs_growth": _signal(effect, (
            "growth", "business_confidence", "business_investment", "employment", "productivity",
        ), inverted=("unemployment",)),
        "rural_transport": _signal(effect, (
            "rail", "transport", "local_government", "rural_support",
        ), inverted=("fuel_duty",)),
        "housing": _signal(effect, ("homes_built", "housing", "affordable_homes"),
                           inverted=("rent_pressure",)),
        "environment": _signal(effect, ("netzero", "climate", "clean_energy", "carbon")),
        "devolution": _signal(effect, ("local_grant", "barnett", "devolution", "local_government")),
        "defence": _signal(effect, ("defence", "military", "security", "nato")),
    }


def simulate_vote(option, party_votes, s=None):
    """Vary each MP's vote around the party baseline using individual local priorities."""
    s = s or st.session_state
    roster = ensure(s)
    if not roster:
        total = sum(int(row.get("ayes", 0)) for row in party_votes.values())
        return total, party_votes, {"mp_count": 0, "rebels": [], "marginal_mps": 0}
    government = s.get("party", "Labour")
    coalition = set(s.get("government_coalition_partners", [])) if s.get("government_type") == "coalition" else set()
    ideology = str(option.get("ideology", "Centric"))
    signals = _policy_signals(option)
    approval = float(s.get("approval", 50.0))
    seed = int(s.get("seed", 0))
    term, year, block = int(s.get("term", 1)), int(s.get("year", 1)), int(s.get("block", 1))
    title = str(option.get("label", option.get("title", "Policy bill")))
    counts = {
        party: {"seats": 0, "ayes": 0, "noes": 0, "rebels": 0, "line": row.get("line", "")}
        for party, row in party_votes.items()
    }
    rebel_examples, marginal_count = [], 0
    for mp in roster.values():
        party = mp.get("party")
        if party not in counts:
            continue
        row = party_votes[party]
        base_probability = float(row.get("ayes", 0)) / max(1, int(row.get("seats", 0)))
        compatible = ideology in FACTION_IDEOLOGIES.get(mp.get("faction"), ("Centric",))
        faction_adjustment = 0.045 if compatible else -0.035
        priorities = mp.get("priorities", {})
        total_priority = sum(float(priorities.get(key, 0)) for key in PRIORITIES) or 1.0
        priority_alignment = sum(
            float(priorities.get(key, 0)) * float(signals.get(key, 0.0))
            for key in PRIORITIES
        ) / total_priority
        local_alignment = float(signals.get(mp.get("local_issue"), 0.0))
        constituency_adjustment = priority_alignment * 0.075 + local_alignment * 0.025
        marginal = bool(mp.get("is_marginal"))
        if marginal:
            marginal_count += 1
        mood_adjustment = (approval - 50.0) * (0.0012 if marginal else 0.00045)
        government_side = party == government or party in coalition
        adjustment = (
            faction_adjustment + constituency_adjustment + mood_adjustment
            if government_side else 0.55 * faction_adjustment + 0.70 * constituency_adjustment
        )
        probability = max(0.02, min(0.98, base_probability + adjustment))
        roll = _hash_int(seed, term, year, block, title, mp.get("code")) / 0xFFFFFFFF
        aye = roll < probability
        counts[party]["seats"] += 1
        counts[party]["ayes" if aye else "noes"] += 1
        rebel = (not aye) if government_side else aye
        if rebel:
            counts[party]["rebels"] += 1
            if len(rebel_examples) < 14:
                reason = (
                    f"{mp.get('faction')} faction" if not compatible else
                    f"{PRIORITY_LABELS.get(mp.get('local_issue'), 'local priorities')} constituency concern"
                    if abs(local_alignment) > 0.15 else "individual judgement"
                )
                rebel_examples.append({
                    "MP": mp.get("name", "Simulated MP"),
                    "Constituency": mp.get("constituency", ""),
                    "Party": party, "Reason": reason, "Vote": "Aye" if aye else "No",
                })

    total_ayes, updated = 0, {}
    for party, row in counts.items():
        if row["seats"] == 0:
            row = dict(party_votes[party])
        else:
            row["noes"] = row["seats"] - row["ayes"]
        total_ayes += int(row.get("ayes", 0))
        updated[party] = row
    summary = {
        "mp_count": len(roster), "rebels": rebel_examples,
        "rebel_count": sum(int(row.get("rebels", 0)) for row in updated.values()),
        "marginal_mps": marginal_count, "priority_signals": signals,
    }
    return max(0, min(650, total_ayes)), updated, summary


def render_register(s=None, last_vote=None):
    import pandas as pd
    s = s or st.session_state
    roster = ensure(s)
    st.markdown("### MPs and constituencies")
    st.caption("650 simulated MPs mapped to the official 2024 Westminster constituency register. MP names, factions and political priorities are fictional game profiles, not real MPs.")
    counts = {party: 0 for party in state.PARTIES}
    for mp in roster.values():
        counts[mp["party"]] = counts.get(mp["party"], 0) + 1
    a, b, c = st.columns(3)
    a.metric("Constituencies represented", f"{len(roster)}/650")
    b.metric("Government MPs", str(counts.get(s.get("party"), 0)))
    c.metric("Marginal MPs", str(sum(1 for mp in roster.values() if mp.get("is_marginal"))))

    party_filter = st.selectbox("Filter by parliamentary party", ["All parties"] + state.PARTIES,
                                key="mp_register_party_filter")
    search = st.text_input("Find an MP or constituency", key="mp_register_search",
                           placeholder="Search constituency or simulated MP name").strip().lower()
    filtered = [
        mp for mp in roster.values()
        if (party_filter == "All parties" or mp["party"] == party_filter)
        and (not search or search in f"{mp['name']} {mp['constituency']} {mp['nation']} {mp['party']}".lower())
    ]
    rows = [{
        "MP": mp["name"], "Constituency": mp["constituency"], "Party": mp["party"],
        "Faction": mp["faction"], "Priority": PRIORITY_LABELS[mp["top_priority"]],
        "Local issue": PRIORITY_LABELS[mp["local_issue"]],
        "Seat": "Marginal" if mp.get("is_marginal") else "Safer",
    } for mp in filtered]
    rows.sort(key=lambda row: (row["Party"], row["Constituency"]))
    if rows:
        st.dataframe(pd.DataFrame(rows[:40]), hide_index=True, use_container_width=True)
    else:
        st.caption("No MPs match that search.")
    if len(rows) > 40:
        st.caption(f"Showing 40 of {len(rows)} matches. Refine the search for a specific constituency.")
    if filtered:
        options = {f"{mp['name']} · {mp['constituency']}": mp for mp in filtered}
        label = st.selectbox("MP profile", list(options), key="mp_register_detail")
        selected = options[label]
        st.caption(f"{selected['name']} represents {selected['constituency']} ({selected['nation']}) for {selected['party']}. Simulated faction: {selected['faction']}.")
        priorities = sorted(selected["priorities"].items(), key=lambda item: item[1], reverse=True)
        st.write("**Political priorities:** " + ", ".join(
            f"{PRIORITY_LABELS[key]} ({value}/100)" for key, value in priorities[:4]
        ))

    summary = (last_vote or {}).get("mp_summary", {})
    if summary:
        st.markdown("#### Named rebellion sample · latest Commons vote")
        st.caption(f"{summary.get('rebel_count', 0)} individual MPs broke their party's assumed line; {summary.get('marginal_mps', 0)} MPs sit in simulated marginal constituencies.")
        if summary.get("rebels"):
            st.dataframe(pd.DataFrame(summary["rebels"]), hide_index=True, use_container_width=True)
