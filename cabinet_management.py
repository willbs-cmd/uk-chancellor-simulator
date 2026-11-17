"""Cabinet performance and ministerial relationships for the Chancellor Simulator.

The player is Chancellor, not Prime Minister: they can review delivery, build
working relationships and recommend changes, but only Number 10 appoints or
removes Cabinet ministers.
"""
import streamlit as st
import budget
import random
import hashlib

OPENING_COMPETENCE = {
    "health": 66.0, "education": 63.0, "welfare": 61.0, "justice": 58.0,
    "defence": 69.0, "transport": 62.0, "housing": 60.0, "science": 72.0,
    "climate": 64.0, "aid": 62.0, "culture": 65.0, "other": 60.0,
    "social_care": 61.0, "local_government": 59.0,
    "public_sector_pay": 63.0, "skills": 67.0,
}
PARTY_FACTIONS = {
    "Labour": ["Party Mainstream", "Labour Right", "Soft Left", "Socialist Left"],
    "Conservative": ["Party Mainstream", "One Nation", "Thatcherite Right", "New Right"],
    "Liberal Democrats": ["Social Liberal", "Economic Liberal", "Federalist", "Party Mainstream"],
    "Reform UK": ["Populist", "Free-Market", "National Conservative"],
    "Green Party": ["Green Pragmatist", "Eco-Socialist", "Decentralist"],
    "SNP": ["SNP Mainstream", "Social Democratic", "Independence Pragmatist"],
    "Plaid Cymru": ["Civic Nationalist", "Welsh Social Democrat", "Welsh Socialist"],
}
PERSONALITIES = {
    "Technocratic manager": {"delivery": 0.35, "loyalty": 0.0, "ambition": 0.0, "lobbying": 0.65},
    "Party loyalist": {"delivery": 0.0, "loyalty": 0.35, "ambition": -0.15, "lobbying": 0.0},
    "Ambitious operator": {"delivery": -0.05, "loyalty": -0.10, "ambition": 0.65, "lobbying": 0.15},
    "Public campaigner": {"delivery": 0.0, "loyalty": 0.10, "ambition": 0.15, "lobbying": 0.70},
    "Fiscal hawk": {"delivery": 0.10, "loyalty": 0.05, "ambition": -0.05, "lobbying": -0.60},
}
PERSONALITY_NAMES = tuple(PERSONALITIES)
FACTION_IDEOLOGIES = {
    "Party Mainstream": ["Centric", "Social Democratic"],
    "Labour Right": ["Social Democratic", "Centric"],
    "Soft Left": ["Social Democratic", "Hard Left"],
    "Socialist Left": ["Hard Left"],
    "One Nation": ["Centric", "Social Democratic"],
    "Thatcherite Right": ["Free-Market", "Fiscal Austerity"],
    "New Right": ["Free-Market", "Fiscal Austerity"],
    "Social Liberal": ["Centric", "Social Democratic"],
    "Economic Liberal": ["Centric", "Free-Market"],
    "Federalist": ["Centric", "Social Democratic"],
    "Populist": ["Free-Market", "Fiscal Austerity"],
    "National Conservative": ["Fiscal Austerity", "Centric"],
    "Green Pragmatist": ["Social Democratic", "Centric"],
    "Eco-Socialist": ["Hard Left", "Social Democratic"],
    "Decentralist": ["Social Democratic", "Centric"],
    "SNP Mainstream": ["Social Democratic", "Centric"],
    "Independence Pragmatist": ["Centric", "Social Democratic"],
    "Civic Nationalist": ["Centric", "Social Democratic"],
    "Welsh Social Democrat": ["Social Democratic", "Centric"],
    "Welsh Socialist": ["Hard Left", "Social Democratic"],
    "Government Mainstream": ["Centric", "Social Democratic"],
    "Reformist": ["Social Democratic", "Free-Market"],
    "Traditionalist": ["Centric", "Fiscal Austerity"],
}
SERVICE_FOR_DEPARTMENT = {
    "health": "NHS", "social_care": "NHS", "education": "Education",
    "skills": "Education", "justice": "Justice", "transport": "Transport",
    "local_government": "Local government", "housing": "Local government",
}


def ensure(s=None):
    s = s or st.session_state
    s.setdefault("ministerial_competence", {})
    s.setdefault("ministerial_delivery_history", [])
    s.setdefault("ministerial_review_year", "")
    s.setdefault("ministerial_meeting_year", "")
    s.setdefault("ministerial_review_history", [])
    s.setdefault("ministerial_delivery_commitments", {})
    s.setdefault("ministerial_rivalries", {})
    s.setdefault("ministerial_rivalry_history", [])
    s.setdefault("ministerial_relationship_issue", None)
    s.setdefault("ministerial_relationship_issue_year", "")
    s.setdefault("ministerial_relationship_history", [])
    s.setdefault("ministerial_profiles", {})
    s.setdefault("ministerial_latest_appraisals", [])
    s.setdefault("ministerial_appraisal_history", [])
    s.setdefault("ministerial_poor_review_years", {})
    ensure_profiles(s)
    competence = dict(s.get("ministerial_competence", {}))
    for key in budget.DEPARTMENT_MINISTERS:
        competence.setdefault(key, OPENING_COMPETENCE.get(key, 60.0))
    s.ministerial_competence = competence


def ensure_profiles(s=None):
    """Assign stable simulated faction/personality profiles to current ministers."""
    s = s or st.session_state
    profiles = dict(s.get("ministerial_profiles", {}))
    party = str(s.get("party", ""))
    factions = PARTY_FACTIONS.get(party, ["Government Mainstream", "Reformist", "Traditionalist"])
    seed = str(s.get("seed", 0))
    for department, name in s.get("cabinet_ministers", {}).items():
        name = str(name or "")
        if not name or name.startswith(("Vacant", "New appointment")):
            continue
        existing = profiles.get(department, {})
        if existing.get("minister") == name and existing.get("party") == party:
            continue
        digest = hashlib.sha256(f"{seed}:{party}:{department}:{name}".encode("utf-8")).hexdigest()
        profiles[department] = {
            "minister": name, "party": party,
            "faction": factions[int(digest[:8], 16) % len(factions)],
            "personality": PERSONALITY_NAMES[int(digest[8:16], 16) % len(PERSONALITY_NAMES)],
        }
    s.ministerial_profiles = profiles


def profile_for(s, department):
    ensure_profiles(s)
    return dict(s.get("ministerial_profiles", {}).get(department, {}))


def cabinet_health(s=None):
    """Return a compact, derived picture of active ministerial capability and loyalty."""
    s = s or st.session_state
    ensure(s)
    active = [(key, str(name)) for key, name in s.get("cabinet_ministers", {}).items()
              if name and not str(name).startswith(("Vacant", "New appointment"))]
    if not active:
        return {"count": 0, "competence": 60.0, "loyalty": 60.0, "weak_ministers": [], "low_loyalty": 0}
    competence = s.get("ministerial_competence", {})
    loyalty = s.get("ministerial_loyalty", {})
    comp_values = [float(competence.get(key, 60.0)) for key, _ in active]
    loyalty_values = [float(loyalty.get(key, 60.0)) for key, _ in active]
    weak = [{"department": key, "minister": name, "competence": float(competence.get(key, 60.0)),
             "loyalty": float(loyalty.get(key, 60.0))}
            for key, name in active if float(competence.get(key, 60.0)) < 45.0]
    return {"count": len(active), "competence": round(sum(comp_values) / len(comp_values), 1),
            "loyalty": round(sum(loyalty_values) / len(loyalty_values), 1),
            "weak_ministers": weak, "low_loyalty": sum(1 for value in loyalty_values if value < 35.0)}

def service_effect(s, service):
    """Small annual service-delivery adjustment from relevant ministerial skill."""
    ensure(s)
    departments = [key for key, linked in SERVICE_FOR_DEPARTMENT.items() if linked == service]
    if not departments:
        return 0.0
    active = [key for key in departments
              if not str(s.get("cabinet_ministers", {}).get(key, "")).startswith("Vacant")]
    if not active:
        return -0.04
    average = sum(float(s.ministerial_competence.get(key, 60.0)) for key in active) / len(active)
    return round(max(-0.18, min(0.18, (average - 60.0) * 0.006)), 3)


def annual_review(s=None):
    """Update ministers' delivery records once per in-game year, without duplicate ticks."""
    s = s or st.session_state
    ensure(s)
    tick = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    if s.get("ministerial_review_year") == tick:
        return
    s.ministerial_review_year = tick
    scores = dict(s.get("public_service_scores", {}))
    service_history = list(s.get("public_service_history", []))
    previous = service_history[-2] if len(service_history) >= 2 else (service_history[-1] if service_history else {})
    competence = dict(s.get("ministerial_competence", {}))
    loyalty = dict(s.get("ministerial_loyalty", {}))
    commitments = dict(s.get("ministerial_delivery_commitments", {}))
    rows = []
    for department, service in SERVICE_FOR_DEPARTMENT.items():
        minister_name = str(s.get("cabinet_ministers", {}).get(department, "") or "").strip()
        # Do not appraise portfolios that have no appointed minister.
        if not minister_name or minister_name.startswith(("Vacant", "New appointment")):
            continue
        score = float(scores.get(service, 60.0))
        old_score = float(previous.get(service, score))
        change = score - old_score
        delta = 0.25 if score >= 68 and change >= 0 else (-0.25 if score < 42 and change < 0 else 0.0)
        profile = profile_for(s, department)
        traits = PERSONALITIES.get(profile.get("personality"), {})
        delta += float(traits.get("delivery", 0.0))
        commitment = commitments.get(department)
        if commitment and commitment != tick:
            delta += 0.25 if change >= 0 else -0.25
            commitments.pop(department, None)
        competence[department] = round(max(20.0, min(95.0, float(competence.get(department, 60.0)) + delta)), 1)
        loyalty_delta = 1.0 if change >= 0.8 else (-1.0 if change <= -0.8 else 0.0)
        loyalty_delta += float(traits.get("loyalty", 0.0))
        faction_ideologies = FACTION_IDEOLOGIES.get(profile.get("faction"), ["Centric"])
        latest_ideology = str(s.get("last_ideology", "Centric"))
        loyalty_delta += 0.2 if latest_ideology in faction_ideologies else -0.2
        if float(s.get("party_opinion", 50.0)) >= 65 and profile.get("personality") == "Party loyalist":
            loyalty_delta += 0.2
        loyalty[department] = round(max(0.0, min(100.0, float(loyalty.get(department, 60.0)) + loyalty_delta)), 1)
        minister = minister_name
        appraisal_score = max(0.0, min(100.0, competence[department] * 0.45
                              + score * 0.40 + max(-10.0, min(10.0, change * 2.5))))
        if appraisal_score >= 80:
            grade = "Outstanding"
            recommendation = "Recognise strong delivery and maintain support"
        elif appraisal_score >= 65:
            grade = "Strong"
            recommendation = "Maintain current priorities"
        elif appraisal_score >= 52:
            grade = "Needs improvement"
            recommendation = "Agree a private improvement plan"
        else:
            grade = "At risk"
            recommendation = "Issue a formal warning and advise Number 10"
        poor_years = dict(s.get("ministerial_poor_review_years", {}))
        poor_years[department] = int(poor_years.get(department, 0)) + 1 if appraisal_score < 52 else 0
        warning = "No formal concern"
        if poor_years[department] == 1:
            warning = "Private warning"
        elif poor_years[department] >= 2:
            warning = "Recommend Prime Ministerial review"
            # Persistent failure has a modest effect; Number 10 still controls appointments.
            competence[department] = round(max(20.0, competence[department] - 1.0), 1)
            loyalty[department] = round(max(0.0, loyalty[department] - 0.5), 1)
        rows.append({"department": department, "minister": minister, "service": service,
                     "score": round(score, 1), "change": round(change, 1),
                     "competence": competence[department], "loyalty": loyalty[department],
                     "appraisal_score": round(appraisal_score, 1), "grade": grade,
                     "recommendation": recommendation, "warning": warning,
                     "poor_years": poor_years[department]})
    s.ministerial_competence = competence
    s.ministerial_loyalty = loyalty
    s.ministerial_poor_review_years = poor_years
    s.ministerial_latest_appraisals = rows
    s.ministerial_appraisal_history = (list(s.get("ministerial_appraisal_history", [])) + [{"year": tick, "rows": rows}])[-20:]
    s.ministerial_delivery_commitments = commitments
    s.ministerial_delivery_history = (list(s.get("ministerial_delivery_history", [])) + [{"year": tick, "rows": rows}])[-20:]
    update_rivalries(s)
    generate_relationship_issue(s, tick)



# Overlapping portfolios can develop rivalries over influence and scarce settlements.
RIVALRY_PAIRS = (
    ("health", "social_care", "Health and social care"),
    ("education", "skills", "Education and skills"),
    ("transport", "local_government", "Transport and local government"),
    ("housing", "local_government", "Housing and local government"),
    ("defence", "aid", "Defence and international development"),
)


def update_rivalries(s=None):
    """Update portfolio tensions once per annual review; ratings remain bounded."""
    s = s or st.session_state
    ensure(s)
    tensions = dict(s.get("ministerial_rivalries", {}))
    competence = s.get("ministerial_competence", {})
    loyalty = s.get("ministerial_loyalty", {})
    refusals = s.get("ministerial_refusals", {})
    cabinet = s.get("cabinet_ministers", {})
    rows = []
    for left, right, label in RIVALRY_PAIRS:
        left_name, right_name = str(cabinet.get(left, "")), str(cabinet.get(right, ""))
        if not left_name or not right_name or left_name.startswith(("Vacant", "New appointment")) or right_name.startswith(("Vacant", "New appointment")):
            continue
        key = f"{left}|{right}"
        gap_skill = abs(float(competence.get(left, 60.0)) - float(competence.get(right, 60.0)))
        gap_loyalty = abs(float(loyalty.get(left, 60.0)) - float(loyalty.get(right, 60.0)))
        refusal_gap = abs(int(refusals.get(left_name, 0)) - int(refusals.get(right_name, 0)))
        left_traits = PERSONALITIES.get(profile_for(s, left).get("personality"), {})
        right_traits = PERSONALITIES.get(profile_for(s, right).get("personality"), {})
        ambition_pressure = (float(left_traits.get("ambition", 0.0)) + float(right_traits.get("ambition", 0.0))) * 1.5
        pressure = max(0.0, gap_skill - 10.0) * 0.22 + max(0.0, gap_loyalty - 20.0) * 0.10 + min(4, refusal_gap) * 0.8 + ambition_pressure
        relief = 0.7 if gap_skill < 8 and gap_loyalty < 15 else 0.0
        tension = round(max(0.0, min(100.0, float(tensions.get(key, 24.0)) + pressure - relief)), 1)
        tensions[key] = tension
        rows.append({"key": key, "label": label, "ministers": f"{left_name} / {right_name}", "tension": tension})
    s.ministerial_rivalries = tensions
    history = list(s.get("ministerial_rivalry_history", []))
    tick = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    history.append({"year": tick, "rows": rows})
    s.ministerial_rivalry_history = history[-20:]
    serious = sum(1 for row in rows if row["tension"] >= 75)
    if serious:
        s.cab_opinion = round(max(0.0, float(s.get("cab_opinion", 50.0)) - min(1.0, serious * 0.25)), 1)
    return rows


REQUEST_PORTFOLIO = {
    "Health Secretary": "health", "Defence Secretary": "defence",
    "Education Secretary": "education", "Transport Secretary": "transport",
    "Home Secretary": "justice", "Foreign Secretary": "aid",
    "Science Secretary": "science", "Culture Secretary": "culture",
}


def record_resignation(s, minister, reason):
    """Record a departure and leave the affected portfolio vacant for Number 10 to fill."""
    cabinet = dict(s.get("cabinet_ministers", {}))
    department = next((key for key, name in cabinet.items() if str(name) == str(minister)), None)
    if department is None:
        department = REQUEST_PORTFOLIO.get(str(minister))
    departing_name = cabinet.get(department, str(minister)) if department else str(minister)
    if department is not None and department in cabinet:
        cabinet[department] = "Vacant — awaiting Prime Minister"
        s.cabinet_ministers = cabinet
        vacancies = dict(s.get("ministerial_vacancy_year", {}))
        vacancies[department] = int(s.get("year", 1))
        s.ministerial_vacancy_year = vacancies
        loyalty = dict(s.get("ministerial_loyalty", {}))
        loyalty[department] = 50.0
        s.ministerial_loyalty = loyalty
        competence = dict(s.get("ministerial_competence", {}))
        competence[department] = 60.0
        s.ministerial_competence = competence
    resignations = list(s.get("ministerial_resignations", []))
    resignations.append({
        "minister": str(departing_name), "portfolio": str(minister),
        "year": int(s.get("year", 1)), "term": int(s.get("term", 1)),
        "reason": str(reason), "department": department,
    })
    s.ministerial_resignations = resignations[-20:]
    return department



def reshuffle_assessment(s, department):
    """Estimate how receptive Number 10 is to a Chancellor's replacement request."""
    minister = str(s.get("cabinet_ministers", {}).get(department, ""))
    if not minister or minister.startswith(("Vacant", "New appointment")):
        return {"score": 0.0, "band": "Unavailable", "factors": {}}
    loyalty = float(s.get("ministerial_loyalty", {}).get(department, 55.0))
    competence = float(s.get("ministerial_competence", {}).get(department, 60.0))
    pm = float(s.get("pm_opinion", 50.0))
    cabinet = float(s.get("cab_opinion", 50.0))
    service = SERVICE_FOR_DEPARTMENT.get(department)
    service_score = float(s.get("public_service_scores", {}).get(service, 60.0)) if service else 60.0
    dispute = s.get("active_dispute") or {}
    dispute_pressure = 12.0 if dispute.get("minister") == minister else 0.0
    factors = {
        "Prime Minister confidence": round(0.45 * pm, 1),
        "Cabinet support": round(0.25 * cabinet, 1),
        "Ministerial disloyalty": round(0.30 * (100.0 - loyalty), 1),
        "Poor ministerial competence": round(0.15 * (60.0 - competence), 1),
        "Department performance": round(0.10 * (60.0 - service_score), 1),
        "Active dispute": round(dispute_pressure, 1),
    }
    score = max(0.0, min(100.0, sum(factors.values())))
    band = "High" if score >= 58.0 else ("Moderate" if score >= 48.0 else "Low")
    return {"score": round(score, 1), "band": band, "factors": factors,
            "minister": minister, "loyalty": loyalty, "competence": competence,
            "service_score": service_score}

def hold_private_meeting(department, approach):
    """One annual Chancellor-to-minister meeting; neither choice appoints or dismisses anyone."""
    s = st.session_state
    ensure(s)
    if department not in budget.DEPARTMENT_MINISTERS:
        return False
    tick = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    if s.get("ministerial_meeting_year") == tick:
        s.message = "You have already held your annual private Cabinet meeting."
        return False
    current = str(s.get("cabinet_ministers", {}).get(department, ""))
    if not current or current.startswith(("Vacant", "New appointment")):
        s.message = "Number 10 has not yet appointed an established minister to that post."
        return False
    import state
    state.checkpoint()
    before = state.values()
    state.snapshot()
    loyalty = dict(s.get("ministerial_loyalty", {}))
    if approach == "back":
        loyalty[department] = round(min(100.0, float(loyalty.get(department, 60.0)) + 6.0), 1)
        s.cab_opinion = round(min(100.0, float(s.get("cab_opinion", 50.0)) + 0.5), 1)
        outcome = f"You privately back {current} and agree to support the department's priorities. The minister's loyalty improves."
    elif approach == "challenge":
        loyalty[department] = round(max(0.0, float(loyalty.get(department, 60.0)) - 3.0), 1)
        s.ministerial_delivery_commitments = dict(s.get("ministerial_delivery_commitments", {}))
        s.ministerial_delivery_commitments[department] = tick
        outcome = f"You demand a measurable delivery plan from {current}. The minister is irritated, but commits to a performance review next year."
    else:
        return False
    s.ministerial_loyalty = loyalty
    s.ministerial_meeting_year = tick
    history = list(s.get("ministerial_review_history", []))
    history.append({"year": tick, "department": department, "minister": current,
                    "approach": approach, "outcome": outcome})
    s.ministerial_review_history = history[-20:]
    s.message = outcome
    s.humphrey_note = "A private ministerial conversation can improve cooperation, but departmental delivery still depends on resources, staff and demand."
    state.log("politics", f"Private meeting with {current}", choice=approach.title(), before=before, note=outcome)
    state.record()
    return True


def generate_relationship_issue(s=None, tick=None):
    """Generate at most one deterministic ministerial incident per game year."""
    s = s or st.session_state
    ensure(s)
    tick = tick or f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"
    if s.get("ministerial_relationship_issue_year") == tick:
        return s.get("ministerial_relationship_issue")
    s.ministerial_relationship_issue_year = tick
    if s.get("ministerial_relationship_issue"):
        return s.get("ministerial_relationship_issue")
    cabinet = s.get("cabinet_ministers", {})
    active = [(k, str(v)) for k, v in cabinet.items()
              if v and not str(v).startswith(("Vacant", "New appointment"))]
    if not active:
        return None
    rng = random.Random(f"{s.get('seed', 0)}:{tick}:cabinet-relationships")
    loyalty = s.get("ministerial_loyalty", {})
    vulnerable = [(k, n) for k, n in active if float(loyalty.get(k, 60)) <= 35]
    latest = list(s.get("ministerial_rivalry_history", []))
    rows = latest[-1].get("rows", []) if latest else []
    serious = [r for r in rows if float(r.get("tension", 0)) >= 55]
    if vulnerable:
        dept, minister = min(vulnerable, key=lambda x: float(loyalty.get(x[0], 60)))
        issue = {"kind": "resignation", "department": dept, "minister": minister,
                 "text": f"{minister} privately warns that continued Treasury opposition may leave them unable to remain in Cabinet."}
    elif serious and rng.random() < 0.62 + min(0.25, max(
            float(PERSONALITIES.get(profile_for(s, r.get("key", "").split("|")[0]).get("personality"), {}).get("ambition", 0.0))
            for r in serious) * 0.25):
        row = rng.choice(serious)
        pair = str(row.get("key", "")).split("|")
        if len(pair) != 2:
            return None
        dept, rival_dept = pair
        minister, rival = str(cabinet.get(dept, "")), str(cabinet.get(rival_dept, ""))
        issue = {"kind": "briefing", "department": dept, "minister": minister,
                 "rival_department": rival_dept, "rival": rival, "tension": float(row.get("tension", 55)),
                 "text": f"Reports suggest {minister} has been briefing privately against {rival} over overlapping responsibilities and influence with Number 10."}
    elif rng.random() < 0.58:
        weighted = []
        for dept_key, minister_name in active:
            profile = profile_for(s, dept_key)
            lobby_trait = float(PERSONALITIES.get(profile.get("personality"), {}).get("lobbying", 0.0))
            ideological_distance = 0.25 if str(s.get("last_ideology", "Centric")) not in FACTION_IDEOLOGIES.get(profile.get("faction"), ["Centric"]) else 0.0
            weighted.append((dept_key, minister_name, max(0.15, 1.0 + lobby_trait + ideological_distance)))
        dept, minister, _ = rng.choices(weighted, weights=[item[2] for item in weighted], k=1)[0]
        cost = round(rng.uniform(1.0, 3.5), 1)
        issue = {"kind": "lobbying", "department": dept, "minister": minister, "cost": cost,
                 "text": f"{minister} wants a private meeting and is pressing the Treasury for £{cost:.1f}bn of extra departmental support."}
    else:
        return None
    issue.update({"year": int(s.get("year", 1)), "term": int(s.get("term", 1)), "tick": tick})
    s.ministerial_relationship_issue = issue
    return issue


def resolve_relationship_issue(choice):
    """Resolve a ministerial approach without giving the Chancellor PM appointment powers."""
    s = st.session_state
    ensure(s)
    issue = s.get("ministerial_relationship_issue")
    if not issue:
        return False
    kind, dept = issue.get("kind"), issue.get("department")
    minister = str(issue.get("minister", "Cabinet minister"))
    loyalty = dict(s.get("ministerial_loyalty", {}))
    import state
    state.checkpoint()
    before = state.values()
    state.snapshot()
    if kind == "lobbying":
        cost = float(issue.get("cost", 1.0))
        if choice == "fund":
            s.headroom = round(float(s.get("headroom", 0)) - cost, 1)
            s.deficit = round(float(s.get("deficit", 0)) + cost, 1)
            loyalty[dept] = min(100.0, float(loyalty.get(dept, 60)) + 7)
            s.cab_opinion = min(100.0, float(s.get("cab_opinion", 50)) + 0.5)
            outcome = f"You agree £{cost:.1f}bn of extra support for {minister}. Relations improve, but borrowing rises."
        elif choice == "plan":
            loyalty[dept] = min(100.0, float(loyalty.get(dept, 60)) + 2)
            plans = dict(s.get("ministerial_delivery_commitments", {}))
            plans[dept] = issue.get("tick", "")
            s.ministerial_delivery_commitments = plans
            outcome = f"You ask {minister} for a costed delivery plan before agreeing extra money."
        elif choice == "refuse":
            loyalty[dept] = max(0.0, float(loyalty.get(dept, 60)) - 6)
            refusals = dict(s.get("ministerial_refusals", {}))
            refusals[minister] = int(refusals.get(minister, 0)) + 1
            s.ministerial_refusals = refusals
            outcome = f"You reject {minister}'s request. Their loyalty falls and they may take the argument to Cabinet."
        else:
            return False
    elif kind == "briefing":
        rival_dept, rival = issue.get("rival_department"), str(issue.get("rival", "the rival minister"))
        tensions = dict(s.get("ministerial_rivalries", {}))
        key = f"{dept}|{rival_dept}"
        tension = float(tensions.get(key, issue.get("tension", 55)))
        if choice == "mediate":
            tensions[key] = max(0.0, tension - 12)
            loyalty[dept] = min(100.0, float(loyalty.get(dept, 60)) + 2)
            loyalty[rival_dept] = min(100.0, float(loyalty.get(rival_dept, 60)) + 2)
            s.cab_opinion = min(100.0, float(s.get("cab_opinion", 50)) + 1)
            outcome = f"You bring {minister} and {rival} together and clarify their overlapping responsibilities."
        elif choice == "back":
            tensions[key] = min(100.0, tension + 8)
            loyalty[dept] = min(100.0, float(loyalty.get(dept, 60)) + 4)
            loyalty[rival_dept] = max(0.0, float(loyalty.get(rival_dept, 60)) - 5)
            s.cab_opinion = max(0.0, float(s.get("cab_opinion", 50)) - 1)
            outcome = f"You back {minister}'s account. They are grateful, but {rival} feels isolated and Cabinet tensions worsen."
        elif choice == "warn":
            tensions[key] = max(0.0, tension - 5)
            loyalty[dept] = max(0.0, float(loyalty.get(dept, 60)) - 1)
            loyalty[rival_dept] = max(0.0, float(loyalty.get(rival_dept, 60)) - 1)
            outcome = f"You warn both ministers that briefing against colleagues is unacceptable."
        else:
            return False
        s.ministerial_rivalries = tensions
    elif kind == "resignation":
        if choice == "compromise":
            cost = 1.5
            s.headroom = round(float(s.get("headroom", 0)) - cost, 1)
            s.deficit = round(float(s.get("deficit", 0)) + cost, 1)
            loyalty[dept] = min(100.0, float(loyalty.get(dept, 30)) + 18)
            s.pm_opinion = min(100.0, float(s.get("pm_opinion", 50)) + 1)
            outcome = f"You offer a £{cost:.1f}bn compromise to keep {minister} in Cabinet."
        elif choice == "stand":
            loyalty[dept] = max(0.0, float(loyalty.get(dept, 30)) - 12)
            outcome = f"You refuse to be pressured by {minister}. Their loyalty collapses."
            if loyalty[dept] <= 15:
                record_resignation(s, minister, "Resigned after an unresolved dispute with the Chancellor")
                loyalty[dept] = 50.0
                outcome += " They resign; the post is vacant pending a Prime Ministerial appointment."
        else:
            return False
    else:
        return False
    s.ministerial_loyalty = loyalty
    s.ministerial_relationship_issue = None
    history = list(s.get("ministerial_relationship_history", []))
    history.append({"year": issue.get("tick", ""), "kind": kind, "minister": minister,
                    "choice": choice, "outcome": outcome})
    s.ministerial_relationship_history = history[-20:]
    s.message = outcome
    s.humphrey_note = "You can negotiate funding and relationships as Chancellor; only the Prime Minister appoints or dismisses ministers."
    state.log("politics", f"Cabinet approach: {minister}", choice=choice.title(),
              before=before, note=outcome)
    state.record()
    return True
