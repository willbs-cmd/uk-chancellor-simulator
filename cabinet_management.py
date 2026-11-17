"""Cabinet performance and ministerial relationships for the Chancellor Simulator.

The player is Chancellor, not Prime Minister: they can review delivery, build
working relationships and recommend changes, but only Number 10 appoints or
removes Cabinet ministers.
"""
import streamlit as st
import budget

OPENING_COMPETENCE = {
    "health": 66.0, "education": 63.0, "welfare": 61.0, "justice": 58.0,
    "defence": 69.0, "transport": 62.0, "housing": 60.0, "science": 72.0,
    "climate": 64.0, "aid": 62.0, "culture": 65.0, "other": 60.0,
    "social_care": 61.0, "local_government": 59.0,
    "public_sector_pay": 63.0, "skills": 67.0,
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
    competence = dict(s.get("ministerial_competence", {}))
    for key in budget.DEPARTMENT_MINISTERS:
        competence.setdefault(key, OPENING_COMPETENCE.get(key, 60.0))
    s.ministerial_competence = competence


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
        if str(s.get("cabinet_ministers", {}).get(department, "")).startswith("Vacant"):
            continue
        score = float(scores.get(service, 60.0))
        old_score = float(previous.get(service, score))
        change = score - old_score
        delta = 0.25 if score >= 68 and change >= 0 else (-0.25 if score < 42 and change < 0 else 0.0)
        commitment = commitments.get(department)
        if commitment and commitment != tick:
            delta += 0.25 if change >= 0 else -0.25
            commitments.pop(department, None)
        competence[department] = round(max(20.0, min(95.0, float(competence.get(department, 60.0)) + delta)), 1)
        loyalty_delta = 1.0 if change >= 0.8 else (-1.0 if change <= -0.8 else 0.0)
        loyalty[department] = round(max(0.0, min(100.0, float(loyalty.get(department, 60.0)) + loyalty_delta)), 1)
        rows.append({"department": department, "service": service, "score": round(score, 1),
                     "change": round(change, 1), "competence": competence[department],
                     "loyalty": loyalty[department]})
    s.ministerial_competence = competence
    s.ministerial_loyalty = loyalty
    s.ministerial_delivery_commitments = commitments
    s.ministerial_delivery_history = (list(s.get("ministerial_delivery_history", [])) + [{"year": tick, "rows": rows}])[-20:]
    update_rivalries(s)



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
        pressure = max(0.0, gap_skill - 10.0) * 0.22 + max(0.0, gap_loyalty - 20.0) * 0.10 + min(4, refusal_gap) * 0.8
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


def record_resignation(s, minister, reason):
    """Record a departure and leave the affected portfolio vacant for Number 10 to fill."""
    cabinet = dict(s.get("cabinet_ministers", {}))
    department = next((key for key, name in cabinet.items() if str(name) == str(minister)), None)
    if department is not None:
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
        "minister": str(minister), "year": int(s.get("year", 1)),
        "term": int(s.get("term", 1)), "reason": str(reason),
        "department": department,
    })
    s.ministerial_resignations = resignations[-20:]
    return department


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
