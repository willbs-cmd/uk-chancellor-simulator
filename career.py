"""Playable political career mode: from backbench MP towards senior office."""
import random
import streamlit as st

from content_store import load_json

DATA = load_json("career_content.json")
ROLES = DATA["roles"]
RULES = DATA["promotion_rules"]
ATTRIBUTES = DATA["attributes"]
ACTIONS_PER_SESSION = int(DATA["session_policy"]["actions_per_session"])
SESSIONS_PER_YEAR = int(DATA["session_policy"]["sessions_per_year"])
ELECTION_AFTER = int(DATA["session_policy"]["election_after_years"])


def new_profile(name="Alex Morgan", constituency="Riverside Central", ambition="policy_specialist"):
    """Create the initial MP profile. Effects are from editable career_content.json."""
    stats = {
        "constituency_support": 58,
        "party_trust": 48,
        "parliamentary_influence": 24,
        "public_profile": 25,
        "policy_expertise": 30,
        "integrity": 78,
    }
    ambition_spec = DATA["ambitions"].get(ambition, DATA["ambitions"]["policy_specialist"])
    for key, value in ambition_spec["effects"].items():
        stats[key] = _clip(stats.get(key, 0) + value)
    return {
        "name": (name or "Alex Morgan").strip()[:70],
        "constituency": (constituency or "Riverside Central").strip()[:70],
        "ambition": ambition if ambition in DATA["ambitions"] else "policy_specialist",
        "role": "mp",
        "stats": stats,
        "career_year": 1,
        "career_term": 1,
        "career_session": 1,
        "career_total_years": 0,
        "actions_by_session": {},
        "history": [{
            "year": 1,
            "term": 1,
            "session": 1,
            "title": "Elected to Parliament",
            "text": f"{name or 'Alex Morgan'} begins a career as a backbench MP for {constituency or 'Riverside Central'}.",
        }],
        "last_event": "Welcome to Westminster. You have two action slots this session. Build support, expertise and influence to unlock opportunities.",
        "last_promotion_total_year": 0,
        "game_over": False,
        "election_result": None,
        "seats_won": 1,
        "promotion_log": [],
    }


def _clip(value, low=0, high=100):
    return max(low, min(high, int(round(value))))


def _profile():
    p = st.session_state.get("career_profile")
    if not isinstance(p, dict):
        p = new_profile()
        st.session_state.career_profile = p
    p.setdefault("stats", {})
    for key, value in {
        "constituency_support": 58, "party_trust": 48, "parliamentary_influence": 24,
        "public_profile": 25, "policy_expertise": 30, "integrity": 78
    }.items():
        p["stats"].setdefault(key, value)
    p.setdefault("actions_by_session", {})
    p.setdefault("history", [])
    p.setdefault("promotion_log", [])
    p.setdefault("career_total_years", 0)
    return p


def _session_key(p):
    return f"{p['career_term']}:{p['career_year']}:{p['career_session']}"


def _current_actions(p):
    return p["actions_by_session"].setdefault(_session_key(p), [])


def _record(p, title, text):
    p["history"].append({
        "year": int(p["career_year"]),
        "term": int(p["career_term"]),
        "session": int(p["career_session"]),
        "role": p["role"],
        "title": title,
        "text": text,
    })
    p["history"] = p["history"][-60:]


def _apply_effects(p, effects):
    changed = []
    for key, value in effects.items():
        if key not in ATTRIBUTES:
            continue
        before = int(p["stats"].get(key, 0))
        after = _clip(before + value)
        p["stats"][key] = after
        if after != before:
            changed.append((ATTRIBUTES[key], after - before))
    return changed


def _effect_summary(effects):
    pieces = []
    for key, value in effects.items():
        if key in ATTRIBUTES and value:
            pieces.append(f"{value:+g} {ATTRIBUTES[key].lower()}")
    return " · ".join(pieces)


def _take_action(p, action):
    used = _current_actions(p)
    if len(used) >= ACTIONS_PER_SESSION:
        return
    changes = _apply_effects(p, action["effects"])
    used.append(action["id"])
    summary = _effect_summary(action["effects"])
    narrative = action["description"]
    if summary:
        narrative += " Effects: " + summary + "."
    _record(p, action["label"], narrative)
    p["last_event"] = f"{action['label']}: {summary or 'No lasting career-stat change.'}"
    st.session_state.career_profile = p
    st.rerun()


def _requirements_met(p, spec):
    stats = p["stats"]
    return (
        p["career_total_years"] >= int(spec.get("min_years", 0))
        and p["career_total_years"] > int(p.get("last_promotion_total_year", 0))
        and all(float(stats.get(key, 0)) >= float(value) for key, value in spec.get("requirements", {}).items())
    )


def _eligible_promotions(p):
    rules = RULES.get(p["role"], {})
    return [(role_id, spec) for role_id, spec in rules.items()
            if role_id in ROLES and _requirements_met(p, spec)]


def _format_requirements(spec):
    bits = []
    for key, threshold in spec.get("requirements", {}).items():
        label = ATTRIBUTES.get(key, key.replace("_", " ").title())
        current = int(_profile()["stats"].get(key, 0))
        bits.append(f"{label} {current}/{threshold}")
    if int(_profile().get("career_total_years", 0)) < int(spec.get("min_years", 0)):
        bits.insert(0, f"Experience {int(_profile().get('career_total_years', 0))}/{spec['min_years']} completed year(s)")
    return " · ".join(bits)


def _accept_promotion(p, role_id, spec):
    old_label = ROLES[p["role"]]["label"]
    new_label = ROLES[role_id]["label"]
    bonus = spec.get("bonus", {})
    bonus_summary = _effect_summary(bonus)
    _apply_effects(p, bonus)
    p["role"] = role_id
    p["last_promotion_total_year"] = int(p["career_total_years"])
    entry = {
        "from": old_label,
        "to": new_label,
        "total_year": int(p["career_total_years"]),
        "term": int(p["career_term"]),
        "year": int(p["career_year"]),
    }
    p["promotion_log"].append(entry)
    p["last_event"] = f"Promotion accepted: {new_label}. Your new responsibilities unlock a different set of actions."
    if bonus_summary:
        p["last_event"] += f" Appointment bonus: {bonus_summary}."
    _record(p, f"Appointed {new_label}", p["last_event"])
    st.session_state.career_profile = p
    st.rerun()


def _hold_election(p):
    stats = p["stats"]
    seed = int(st.session_state.get("seed", 12345))
    rng = random.Random(seed + p["career_total_years"] * 911 + p["career_term"] * 503)
    score = (
        .40 * stats["constituency_support"]
        + .15 * stats["party_trust"]
        + .15 * stats["public_profile"]
        + .10 * stats["policy_expertise"]
        + .10 * stats["integrity"]
        + .10 * stats["parliamentary_influence"]
    )
    margin = round(score + rng.uniform(-8, 8), 1)
    won = margin >= 45
    result = {
        "term": int(p["career_term"]),
        "score": round(score, 1),
        "margin": margin,
        "won": won,
        "threshold": 45,
    }
    p["election_result"] = result
    if won:
        p["seats_won"] = int(p.get("seats_won", 0)) + 1
        p["stats"]["constituency_support"] = _clip(p["stats"]["constituency_support"] + 2)
        p["stats"]["party_trust"] = _clip(p["stats"]["party_trust"] + 1)
        text = f"Re-elected in {p['constituency']}. Your career continues into a new Parliament."
        if p["role"] == "prime_minister":
            government_score = .55 * stats["party_trust"] + .45 * stats["public_profile"] + rng.uniform(-12, 12)
            if government_score < 50:
                p["role"] = "mp"
                p["stats"]["party_trust"] = _clip(p["stats"]["party_trust"] - 8)
                p["stats"]["public_profile"] = _clip(p["stats"]["public_profile"] - 4)
                text += " Your party has lost power nationally; you return to the backbenches and must rebuild your influence."
        p["career_term"] = int(p["career_term"]) + 1
        p["career_year"] = 1
        p["career_session"] = 1
        p["last_event"] = text
        _record(p, "General election · re-elected", text)
    else:
        text = f"You lose {p['constituency']} at the general election. Your parliamentary career ends here."
        p["game_over"] = True
        p["last_event"] = text
        _record(p, "General election · seat lost", text)


def _advance(p):
    used = _current_actions(p)
    if len(used) < ACTIONS_PER_SESSION:
        return
    if int(p["career_session"]) < SESSIONS_PER_YEAR:
        p["career_session"] = int(p["career_session"]) + 1
        p["last_event"] = f"Session {p['career_session']} begins. Choose two actions to advance your career."
        _record(p, f"Parliamentary session {p['career_session']}", p["last_event"])
    elif int(p["career_year"]) < ELECTION_AFTER:
        p["career_total_years"] = int(p["career_total_years"]) + 1
        p["career_year"] = int(p["career_year"]) + 1
        p["career_session"] = 1
        p["stats"]["policy_expertise"] = _clip(p["stats"]["policy_expertise"] + 1)
        p["stats"]["integrity"] = _clip(p["stats"]["integrity"] + 1)
        p["last_event"] = f"Year {p['career_year']} begins. Experience has improved your policy expertise and integrity slightly."
        _record(p, f"Parliamentary year {p['career_year']}", p["last_event"])
    else:
        p["career_total_years"] = int(p["career_total_years"]) + 1
        _hold_election(p)
        if not p["game_over"]:
            # Reset the session action key naturally by changing term/year/session.
            pass
    st.session_state.career_profile = p
    st.rerun()


def render():
    """Main career-mode screen."""
    p = _profile()
    role = ROLES.get(p["role"], ROLES["mp"])
    used = _current_actions(p)
    remaining = max(0, ACTIONS_PER_SESSION - len(used))
    st.markdown(
        f"<div class='ch-banner'><div class='ch-head'><span class='ch-title'>🏛️ {p['name']}</span>"
        f"<span class='sub'>{role['label'].upper()} · PARLIAMENTARY CAREER</span></div>"
        f"<div class='sub'>{p['constituency']} · Term {p['career_term']} · Year {p['career_year']} of {ELECTION_AFTER} · "
        f"Session {p['career_session']} of {SESSIONS_PER_YEAR}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f"## {role['label']}")
    st.write(role["description"])
    st.caption(f"Career ambition: {DATA['ambitions'][p['ambition']]['label']}. This is a fictionalised career model; promotions depend on your stats and the path you choose.")

    stats = p["stats"]
    st.markdown("### Your political standing")
    columns = st.columns(3, gap="medium")
    for index, (key, label) in enumerate(ATTRIBUTES.items()):
        with columns[index % 3]:
            st.metric(label, f"{int(stats.get(key, 0))}/100",
                      help="A game attribute from 0 to 100. Actions and promotion bonuses change it.")
    st.progress(len(used) / ACTIONS_PER_SESSION, text=f"{len(used)}/{ACTIONS_PER_SESSION} actions used this session")

    if p.get("last_event"):
        st.info(p["last_event"])

    if p.get("game_over"):
        st.error("Career over — you lost your seat at the general election.")
        if st.button("Start a new career", type="primary"):
            st.session_state.step = "setup"
            st.session_state.game_mode = "chancellor"
            st.session_state.career_profile = None
            st.rerun()
        with st.expander("Career record", expanded=True):
            for item in reversed(p["history"][-15:]):
                st.markdown(f"**{item['title']}** · Term {item['term']}, year {item['year']}, session {item['session']}")
                st.caption(item["text"])
        return

    if p.get("election_result"):
        result = p["election_result"]
        if result["won"]:
            st.success(f"Election result: re-elected (career score {result['score']:.1f}, result {result['margin']:.1f}; threshold {result['threshold']}).")
        else:
            st.error(f"Election result: seat lost (career score {result['score']:.1f}, result {result['margin']:.1f}; threshold {result['threshold']}).")

    st.markdown("### Parliamentary business")
    st.caption("Choose two actions per session. Each has benefits and trade-offs; use the details to build the kind of career you want.")
    if remaining:
        actions = role.get("actions", [])
        cols = st.columns(2, gap="medium")
        for index, action in enumerate(actions):
            with cols[index % 2]:
                with st.container(border=True):
                    st.markdown(f"**{action['label']}**")
                    st.write(action["description"])
                    summary = _effect_summary(action["effects"])
                    if summary:
                        st.caption(summary)
                    if st.button("Take this action", key=f"career_act_{p['career_term']}_{p['career_year']}_{p['career_session']}_{p['role']}_{action['id']}",
                                 disabled=action["id"] in used, use_container_width=True):
                        _take_action(p, action)
    else:
        st.success("Session actions complete. You can advance to the next session.")

    if len(used) >= ACTIONS_PER_SESSION:
        if st.button("End session and continue", type="primary", use_container_width=True):
            _advance(p)

    st.markdown("### Promotion opportunities")
    offers = _eligible_promotions(p)
    if offers:
        st.success("You have earned an opportunity. Accept one appointment; you can pursue another later in your career.")
        cols = st.columns(min(2, len(offers)), gap="medium")
        for index, (role_id, spec) in enumerate(offers):
            with cols[index % len(cols)]:
                with st.container(border=True):
                    st.markdown(f"**{ROLES[role_id]['label']}**")
                    st.write(ROLES[role_id]["description"])
                    if st.button(f"Accept promotion", key=f"career_promote_{p['career_term']}_{p['career_year']}_{p['role']}_{role_id}",
                                 use_container_width=True):
                        _accept_promotion(p, role_id, spec)
    else:
        next_rules = RULES.get(p["role"], {})
        if next_rules:
            with st.expander("Promotion requirements", expanded=False):
                for role_id, spec in next_rules.items():
                    st.markdown(f"**Next step: {ROLES[role_id]['label']}**")
                    st.caption(_format_requirements(spec))
        else:
            st.caption("You have reached the top role available in this career path. Focus on retaining power at the next election.")

    with st.expander("Career record & recent decisions", expanded=False):
        for item in reversed(p["history"][-12:]):
            st.markdown(f"**{item['title']}** · Term {item['term']}, year {item['year']}, session {item['session']}")
            st.caption(item["text"])
