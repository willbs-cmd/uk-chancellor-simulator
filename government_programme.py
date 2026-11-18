"""A connected annual government programme and policy-authorisation pipeline.

The Chancellor remains the player. Ministers provide Cabinet recommendations,
the Prime Minister controls final executive clearance, and the Commons retains
its existing vote model. Budget ledgers are deliberately not modified here.
"""
import streamlit as st


PRIORITIES = {
    "growth": {
        "label": "Growth, jobs & productivity",
        "description": "Raise investment, productivity, employment and sustainable output.",
        "keywords": ("growth", "productivity", "business", "investment", "jobs", "employment", "skills", "science", "research", "exports"),
        "department": "skills",
    },
    "living_standards": {
        "label": "Household living standards",
        "description": "Improve real incomes and reduce pressure from everyday costs.",
        "keywords": ("wage", "income", "household", "living standard", "cost of living", "benefit", "poverty", "rent", "mortgage", "bill"),
        "department": "welfare",
    },
    "public_services": {
        "label": "Public services & workforce",
        "description": "Improve the capacity, quality and resilience of essential services.",
        "keywords": ("nhs", "health", "hospital", "care", "school", "education", "teacher", "public service", "workforce", "pay", "justice", "prison"),
        "department": "health",
    },
    "fiscal_credibility": {
        "label": "Sound public finances",
        "description": "Protect fiscal headroom, control borrowing and maintain market confidence.",
        "keywords": ("tax", "deficit", "debt", "borrow", "fiscal", "spending", "headroom", "revenue", "treasury", "budget"),
        "department": "other",
    },
    "homes_transport": {
        "label": "Homes, infrastructure & transport",
        "description": "Expand housing supply and improve the country's physical infrastructure.",
        "keywords": ("housing", "housebuilding", "home", "planning", "transport", "rail", "road", "infrastructure", "construction"),
        "department": "housing",
    },
    "green_transition": {
        "label": "Energy security & the green transition",
        "description": "Strengthen energy security, clean power and climate resilience.",
        "keywords": ("energy", "climate", "carbon", "net zero", "renewable", "grid", "electricity", "environment"),
        "department": "climate",
    },
    "regional_balance": {
        "label": "Regional opportunity & local government",
        "description": "Spread investment and opportunity across the nations and regions.",
        "keywords": ("regional", "region", "local government", "council", "devolution", "north", "scotland", "wales", "community"),
        "department": "local_government",
    },
}

MISSION_DEFAULTS = {
    "growth_productivity": ["growth", "homes_transport", "regional_balance"],
    "living_standards": ["living_standards", "public_services", "growth"],
    "public_services": ["public_services", "living_standards", "fiscal_credibility"],
    "fiscal_repair": ["fiscal_credibility", "growth", "public_services"],
    "regional_renewal": ["regional_balance", "homes_transport", "growth"],
    "balanced_renewal": ["growth", "public_services", "fiscal_credibility"],
}


PORTFOLIO_RULES = {
    "health": {
        "keywords": ("nhs", "health", "hospital", "waiting list", "clinical", "care"),
        "effects": {"health": 1, "nhs_morale": 1, "social_care": 1, "nhs_waiting": -1},
    },
    "social_care": {
        "keywords": ("social care", "care home", "unpaid carer", "adult care", "care workforce"),
        "effects": {"social_care": 1, "nhs_waiting": -1},
    },
    "education": {
        "keywords": ("school", "education", "teacher", "college", "classroom", "pupil"),
        "effects": {"education": 1, "schools": 1, "teacher_retention": 1},
    },
    "skills": {
        "keywords": ("skills", "apprenticeship", "training", "productivity", "technical education"),
        "effects": {"skills": 1, "productivity": 1, "employment": 1, "unemployment": -1},
    },
    "housing": {
        "keywords": ("housing", "housebuilding", "homes", "planning", "rent", "homeless"),
        "effects": {"homes_built": 1, "housing": 1, "affordable_homes": 1, "rent_pressure": -1},
    },
    "transport": {
        "keywords": ("rail", "transport", "road", "bus", "connectivity", "infrastructure"),
        "effects": {"rail": 1, "transport": 1, "infrastructure": 1},
    },
    "local_government": {
        "keywords": ("council", "local government", "local services", "devolution", "regional"),
        "effects": {"local_grant": 1, "local_service_delivery": 1, "local_government": 1},
    },
    "climate": {
        "keywords": ("climate", "carbon", "net zero", "renewable", "clean energy", "grid"),
        "effects": {"climate": 1, "netzero": 1, "clean_energy": 1, "energy_security": 1},
    },
    "defence": {
        "keywords": ("defence", "military", "armed forces", "nato", "security"),
        "effects": {"defence": 1, "military": 1, "security": 1},
    },
    "welfare": {
        "keywords": ("welfare", "benefit", "poverty", "universal credit", "social security"),
        "effects": {"welfare": 1, "child_poverty": -1, "poverty": -1},
    },
    "justice": {
        "keywords": ("prison", "justice", "court", "police", "offender"),
        "effects": {"prisons": -1, "justice": 1, "court_backlog": -1, "crime": -1},
    },
    "public_sector_pay": {
        "keywords": ("public sector pay", "pay settlement", "nurse pay", "teacher pay", "workforce pay"),
        "effects": {"real_wages": 1, "nhs_morale": 1, "strikes": -1},
    },
    "science": {
        "keywords": ("science", "research", "innovation", "r&d", "technology"),
        "effects": {"science": 1, "research": 1, "productivity": 1},
    },
    "aid": {
        "keywords": ("aid", "development", "humanitarian", "foreign assistance", "international"),
        "effects": {"aid": 1, "international_development": 1},
    },
}


def _portfolio_interest(department, decision, option):
    """Return a small, transparent ministerial stake in a proposal."""
    rule = PORTFOLIO_RULES.get(department)
    if not rule:
        return 0.0, "No direct portfolio impact identified"
    effect = option.get("effect", option.get("fx", {})) or {}
    text = " ".join(str(value or "") for value in (
        decision.get("title"), decision.get("text"), option.get("label"),
        option.get("description"), effect.get("message")
    )).lower()
    mentioned = any(word in text for word in rule["keywords"])
    signal = 0.0
    measured = False
    for key, direction in rule["effects"].items():
        try:
            value = float(effect.get(key, 0.0))
        except (TypeError, ValueError):
            continue
        if abs(value) > 0.0001:
            measured = True
            signal += value * direction
    if measured:
        # Scale actual effects gently; large numeric units cannot dominate a Cabinet vote.
        impact = max(-7.0, min(7.0, signal * 2.5))
        if impact > 0.3:
            reason = "Supports departmental outcomes"
        elif impact < -0.3:
            reason = "Undermines departmental outcomes"
        else:
            reason = "Mixed departmental consequences"
        return round(impact, 1), reason
    if mentioned:
        return 2.0, "Directly concerns this department"
    return 0.0, "No direct portfolio impact identified"


def _rivalry_penalty(s, department):
    """Unresolved overlapping-portfolio rivalry makes ministers less willing to endorse a common line."""
    import cabinet_management
    penalty = 0.0
    reasons = []
    for left, right, label in cabinet_management.RIVALRY_PAIRS:
        if department not in (left, right):
            continue
        tension = float(s.get("ministerial_rivalries", {}).get(f"{left}|{right}", 0.0))
        if tension > 45.0:
            loss = min(6.0, (tension - 45.0) * 0.11)
            penalty += loss
            reasons.append(f"{label} rivalry ({tension:.0f}/100)")
    issue = s.get("ministerial_relationship_issue") or {}
    if issue.get("kind") == "briefing" and department in (issue.get("department"), issue.get("rival_department")):
        penalty += 2.0
        reasons.append("Active ministerial briefing dispute")
    return round(min(8.0, penalty), 1), "; ".join(reasons)


_STANCE_EFFECTS = {
    "consensus": {"cab_opinion": 0.8, "pm_trust": 0.4},
    "compromise": {"cab_opinion": 1.4, "backbench_opinion": 0.8, "party_opinion": 0.3},
    "treasury": {"market_conf": 0.6, "cab_opinion": -1.0, "backbench_opinion": -0.4},
}


class _PreviewState(dict):
    """Mapping with Streamlit-session-style attribute access for read-only previews."""
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value

def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def _period(s):
    return f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"


def ensure(s=None):
    """Migrate an existing game safely and initialise a fictional working Cabinet."""
    if s is None:
        s = st.session_state
    s.setdefault("annual_government_programme", None)
    s.setdefault("annual_programme_history", [])
    s.setdefault("policy_proposals", [])
    s.setdefault("policy_deliveries", [])
    s.setdefault("policy_proposal_sequence", 0)

    # A newly formed government needs an actual ministerial team to negotiate with.
    # Names and portfolios come from the game's existing fictional departmental roster.
    ministers = s.get("cabinet_ministers")
    if not isinstance(ministers, dict) or not ministers:
        import budget
        s["cabinet_ministers"] = {
            department: details[0]
            for department, details in budget.DEPARTMENT_MINISTERS.items()
        }
    loyalty = dict(s.get("ministerial_loyalty", {}))
    for department in s.get("cabinet_ministers", {}):
        loyalty.setdefault(department, 60.0)
    s["ministerial_loyalty"] = loyalty
    import cabinet_management
    cabinet_management.ensure(s)

    current = s.get("annual_government_programme")
    if not isinstance(current, dict) or current.get("period") != _period(s):
        start_annual_programme(s, carry_forward=True)
    return s


def start_annual_programme(s, carry_forward=True):
    """Create the current year's priorities without erasing proposals or delivery records."""
    period = _period(s)
    current = s.get("annual_government_programme")
    if isinstance(current, dict) and current.get("period") == period:
        return current

    if isinstance(current, dict):
        archive = list(s.get("annual_programme_history", []))
        old = dict(current)
        if not any(item.get("period") == old.get("period") for item in archive):
            old["overall_progress"] = overall_progress(s, old)
            old["proposal_count"] = sum(
                1 for item in s.get("policy_proposals", [])
                if int(item.get("term", -1)) == int(old.get("term", -2))
                and int(item.get("year", -1)) == int(old.get("year", -2))
            )
            archive.append(old)
        s["annual_programme_history"] = archive[-25:]

    if carry_forward and isinstance(current, dict) and current.get("priorities"):
        priorities = list(current["priorities"])
        source = "Carried forward from the previous year"
    else:
        mission = str(s.get("government_mission", "balanced_renewal"))
        priorities = list(MISSION_DEFAULTS.get(mission, MISSION_DEFAULTS["balanced_renewal"]))
        source = "Suggested by the five-year government mandate"

    s["annual_government_programme"] = {
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "period": period,
        "priorities": priorities[:3],
        "declared": False,
        "source": source,
        "adopted_by": None,
    }
    return s["annual_government_programme"]


def current(s=None):
    if s is None:
        s = st.session_state
    ensure(s)
    return s["annual_government_programme"]


def priority_label(priority):
    return PRIORITIES.get(priority, {}).get("label", "General government business")


def set_priorities(s, priorities):
    """Adopt two or three priorities for this financial year."""
    ensure(s)
    selected = []
    for item in priorities or []:
        if item in PRIORITIES and item not in selected:
            selected.append(item)
    if not 2 <= len(selected) <= 3:
        return False
    programme = dict(s["annual_government_programme"])
    programme.update({
        "priorities": selected,
        "declared": True,
        "source": "Adopted by the Chancellor",
        "adopted_by": "Chancellor",
    })
    s["annual_government_programme"] = programme
    s["message"] = "The annual Government Programme has been adopted. Departments will now be judged against these priorities."
    s["humphrey_note"] = "A programme is a useful thing, Chancellor. It gives the Cabinet something to agree with, the Opposition something to criticise, and the Treasury something to cost."
    return True


def classify_policy(decision, option):
    """Suggest the closest annual priority from the policy's own title and wording."""
    text = " ".join(str(value or "") for value in (
        decision.get("title"), decision.get("text"), option.get("label"),
        option.get("description"), option.get("effect", {}).get("message")
    )).lower()
    scores = {
        key: sum(1 for word in item["keywords"] if word in text)
        for key, item in PRIORITIES.items()
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "general"


def priority_options(s=None):
    programme = current(s)
    return list(programme.get("priorities", []))


def costing(s, decision, option):
    """Show only fiscal and macro effects actually present in the policy data."""
    effect = option.get("effect", {}) or {}
    headroom_delta = float(effect.get("headroom", 0.0) or 0.0)
    deficit_delta = float(effect.get("deficit", 0.0) or 0.0)
    post_headroom = float(s.get("headroom", 0.0)) + headroom_delta
    growth_delta = float(effect.get("growth", 0.0) or 0.0)
    inflation_delta = float(effect.get("inflation", 0.0) or 0.0)

    if headroom_delta < -0.01:
        funding = f"Uses approximately £{abs(headroom_delta):.1f}bn of modelled fiscal headroom."
    elif headroom_delta > 0.01:
        funding = f"Creates approximately £{headroom_delta:.1f}bn of modelled fiscal headroom."
    elif deficit_delta > 0.01:
        funding = f"Raises modelled annual borrowing by approximately £{deficit_delta:.1f}bn."
    elif deficit_delta < -0.01:
        funding = f"Reduces modelled annual borrowing by approximately £{abs(deficit_delta):.1f}bn."
    else:
        funding = "The policy data contains no separately quantified Budget or borrowing change."

    if post_headroom < 0:
        fiscal_risk = "Critical"
        risk_detail = "The modelled headroom position would move below zero."
    elif post_headroom < 3.0 or deficit_delta >= 2.0:
        fiscal_risk = "Elevated"
        risk_detail = "The policy leaves little fiscal room or adds material borrowing."
    else:
        fiscal_risk = "Manageable"
        risk_detail = "The modelled headroom remains positive after the stated effect."

    macro = []
    if abs(growth_delta) > 0.001:
        macro.append(("Real GDP growth", growth_delta, "pp"))
    if abs(inflation_delta) > 0.001:
        macro.append(("Inflation", inflation_delta, "pp"))
    for key, label, unit in (
        ("real_wages", "Real wages", "pp"),
        ("unemployment", "Unemployment", "pp"),
        ("nhs_waiting", "NHS waiting list", "million"),
        ("schools", "School standards", "points"),
        ("rail", "Rail performance", "points"),
        ("energy_security", "Energy security", "points"),
        ("homes_built", "New homes", "thousand"),
    ):
        value = float(effect.get(key, 0.0) or 0.0)
        if abs(value) > 0.001:
            macro.append((label, value, unit))

    return {
        "headroom_delta": round(headroom_delta, 2),
        "deficit_delta": round(deficit_delta, 2),
        "post_headroom": round(post_headroom, 2),
        "funding": funding,
        "fiscal_risk": fiscal_risk,
        "risk_detail": risk_detail,
        "macro": macro,
    }



def prepare_cabinet_amendments(s, decision, option):
    """Generate deterministic amendment demands from ministers' portfolio interests and rivalries."""
    import cabinet_management
    cabinet_management.ensure_profiles(s)
    ministers = s.get("cabinet_ministers", {}) or {}
    profiles = s.get("ministerial_profiles", {}) or {}
    loyalty = s.get("ministerial_loyalty", {}) or {}
    impact_rows = {}
    demands = []

    for department, minister in ministers.items():
        minister = str(minister or "")
        if not minister or minister.startswith(("Vacant", "New appointment")):
            continue
        impact, reason = _portfolio_interest(department, decision, option)
        penalty, rivalry_reason = _rivalry_penalty(s, department)
        rule = PORTFOLIO_RULES.get(department, {})
        effects = option.get("effect", option.get("fx", {})) or {}
        adverse_keys = []
        for key, direction in rule.get("effects", {}).items():
            try:
                value = float(effects.get(key, 0.0))
            except (TypeError, ValueError):
                continue
            if abs(value) > 0.0001 and value * float(direction) < 0:
                adverse_keys.append(key)
        impact_rows[department] = {
            "minister": minister, "impact": impact, "reason": reason,
            "penalty": penalty, "rivalry_reason": rivalry_reason,
            "keys": adverse_keys, "profile": profiles.get(department, {}),
            "loyalty": float(loyalty.get(department, 60.0)),
        }

    # Ministers in the same faction can coordinate one joint amendment.
    unassigned = set(impact_rows)
    while unassigned and len(demands) < 3:
        department = max(sorted(unassigned), key=lambda key: (
            max(0.0, -impact_rows[key]["impact"])
            + max(0.0, impact_rows[key]["penalty"] * 0.5)
            + max(0.0, 45.0 - impact_rows[key]["loyalty"]) * 0.08
        ))
        row = impact_rows[department]
        material_harm = row["impact"] <= -0.5 and bool(row["keys"])
        loyalty_concern = row["loyalty"] <= 32.0 and row["impact"] < 0
        rivalry_concern = row["penalty"] >= 5.0 and row["impact"] < 0
        if not (material_harm or loyalty_concern or rivalry_concern):
            unassigned.remove(department)
            continue

        faction = row["profile"].get("faction", "Government Mainstream")
        group = [department]
        for other in list(unassigned - {department}):
            other_row = impact_rows[other]
            other_faction = other_row["profile"].get("faction", "Government Mainstream")
            if other_faction == faction and other_row["impact"] <= -0.5 and other_row["keys"]:
                group.append(other)
        group.sort()
        for item in group:
            unassigned.discard(item)

        names = [impact_rows[item]["minister"] for item in group]
        keys_by_department = {item: list(impact_rows[item]["keys"]) for item in group}
        all_keys = sorted({key for values in keys_by_department.values() for key in values})
        loyalty_min = min(impact_rows[item]["loyalty"] for item in group)
        rival_departments = []
        import cabinet_management
        for left, right, _label in cabinet_management.RIVALRY_PAIRS:
            for member in group:
                if member not in (left, right):
                    continue
                rival = right if member == left else left
                rival_row = impact_rows.get(rival)
                if rival_row and rival_row["impact"] > 0.5:
                    rival_departments.append(rival)

        if all_keys:
            amendment = "Protect " + " / ".join(
                str(item).replace("_", " ").title() for item in group
            ) + " outcomes"
            description = (
                f"{', '.join(names)} request changes to reduce the harm to their portfolios. "
                f"The proposal currently works against {', '.join(all_keys)}."
            )
        else:
            amendment = "Add a departmental delivery safeguard"
            description = (
                f"{', '.join(names)} want a formal delivery safeguard before backing the proposal."
            )
        if rival_departments:
            rival_names = [impact_rows[item]["minister"] for item in rival_departments]
            description += (
                f" They also warn that the proposal favours rival portfolio(s): "
                f"{', '.join(rival_names)}."
            )
        if loyalty_min <= 32.0:
            description += f" {names[0]} warns that rejecting the request could trigger a resignation."
        supporters = []
        for other in impact_rows:
            if other in group:
                continue
            other_row = impact_rows[other]
            if other_row["profile"].get("faction") == faction and other_row["impact"] <= -0.5:
                supporters.append({"department": other, "minister": other_row["minister"]})
        demand_id = "+".join(group)
        demands.append({
            "id": demand_id,
            "departments": group,
            "ministers": names,
            "faction": faction,
            "amendment": amendment,
            "description": description,
            "effect_keys": keys_by_department,
            "rival_departments": sorted(set(rival_departments)),
            "allies": supporters,
            "loyalty_min": loyalty_min,
            "estimated_cost": 0.25,
            "kind": "portfolio" if all_keys else "safeguard",
        })

    return demands


def apply_cabinet_amendments(s, decision, option, accepted_amendments=None, commit=False):
    """Apply selected concessions to a copy of the option; commit ministerial reactions only at authorisation."""
    demands = prepare_cabinet_amendments(s, decision, option)
    accepted_ids = set(accepted_amendments or [])
    adjusted = dict(option)
    adjusted_effect = dict(option.get("effect", option.get("fx", {})) or {})
    outcomes = []
    accepted_cost = 0.0

    for demand in demands:
        accepted = demand["id"] in accepted_ids
        if accepted:
            for department, keys in demand["effect_keys"].items():
                for key in keys:
                    try:
                        adjusted_effect[key] = round(float(adjusted_effect.get(key, 0.0)) * 0.5, 4)
                    except (TypeError, ValueError):
                        pass
            accepted_cost += float(demand["estimated_cost"])
        outcomes.append({
            "id": demand["id"],
            "amendment": demand["amendment"],
            "ministers": list(demand["ministers"]),
            "departments": list(demand["departments"]),
            "accepted": accepted,
            "faction": demand["faction"],
            "rival_departments": list(demand["rival_departments"]),
            "allies": list(demand["allies"]),
            "description": demand["description"],
            "cost": float(demand["estimated_cost"]) if accepted else 0.0,
        })

    if accepted_cost > 0:
        adjusted_effect["headroom"] = round(float(adjusted_effect.get("headroom", 0.0)) - accepted_cost, 4)
        adjusted_effect["deficit"] = round(float(adjusted_effect.get("deficit", 0.0)) + accepted_cost, 4)
        old_message = str(adjusted_effect.get("message", ""))
        concession_note = f" Cabinet amendments add £{accepted_cost:.2f}bn to the policy's modelled cost."
        adjusted_effect["message"] = (old_message + concession_note).strip()

    adjusted["effect"] = adjusted_effect
    adjusted["_cabinet_amendments"] = outcomes

    if commit and outcomes:
        loyalty = dict(s.get("ministerial_loyalty", {}))
        refusals = dict(s.get("ministerial_refusals", {}))
        tensions = dict(s.get("ministerial_rivalries", {}))
        alliances = dict(s.get("ministerial_alliances", {}))
        resignation_candidate = None
        for outcome in outcomes:
            for department in outcome["departments"]:
                minister = str(s.get("cabinet_ministers", {}).get(department, ""))
                before_loyalty = float(loyalty.get(department, 60.0))
                if outcome["accepted"]:
                    loyalty[department] = round(_clip(before_loyalty + 4.0), 1)
                else:
                    loyalty[department] = round(_clip(before_loyalty - 3.5), 1)
                    refusals[minister] = int(refusals.get(minister, 0)) + 1
                    if before_loyalty <= 32.0 or (before_loyalty < 42.0 and refusals[minister] >= 2):
                        if resignation_candidate is None:
                            resignation_candidate = (department, minister)

                for ally in outcome["departments"]:
                    if ally == department or department > ally:
                        continue
                    pair = "|".join((department, ally))
                    change = 8.0 if outcome["accepted"] else 5.0
                    alliances[pair] = round(_clip(float(alliances.get(pair, 0.0)) + change), 1)

                for rival in outcome["rival_departments"]:
                    if department > rival:
                        continue
                    import cabinet_management
                    pair_key = next((
                        f"{left}|{right}" for left, right, _label in cabinet_management.RIVALRY_PAIRS
                        if {left, right} == {department, rival}
                    ), None)
                    if pair_key:
                        tension_change = -4.0 if outcome["accepted"] else 6.0
                        tensions[pair_key] = round(_clip(float(tensions.get(pair_key, 24.0)) + tension_change), 1)

        s.ministerial_loyalty = loyalty
        s.ministerial_refusals = refusals
        s.ministerial_rivalries = tensions
        s.ministerial_alliances = alliances
        history = list(s.get("ministerial_alliance_history", []))
        tick = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}:{int(s.get('block', 1))}"
        history.append({
            "tick": tick,
            "amendments": outcomes,
            "alliances": dict(alliances),
        })
        s.ministerial_alliance_history = history[-30:]

        if resignation_candidate and not s.get("ministerial_relationship_issue"):
            department, minister = resignation_candidate
            s.ministerial_relationship_issue = {
                "kind": "resignation",
                "department": department,
                "minister": minister,
                "text": (
                    f"{minister} has threatened to resign after you rejected their Cabinet amendment. "
                    "Number 10 is concerned that the dispute could destabilise the Government."
                ),
                "year": int(s.get("year", 1)),
                "term": int(s.get("term", 1)),
                "tick": tick,
            }
            s.ministerial_relationship_issue_year = f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"

    return adjusted, {
        "demands": demands,
        "outcomes": outcomes,
        "accepted": [item for item in outcomes if item["accepted"]],
        "rejected": [item for item in outcomes if not item["accepted"]],
        "cost": round(accepted_cost, 2),
    }


def cabinet_review(s, decision, option, stance="consensus", amendment_outcomes=None):
    """Collect simulated individual ministerial positions on the proposal."""
    import cabinet_management
    ideology = str(option.get("ideology", "Centric"))
    cabinet_management.ensure_profiles(s)
    ministers = s.get("cabinet_ministers", {}) or {}
    profiles = s.get("ministerial_profiles", {}) or {}
    competence = s.get("ministerial_competence", {}) or {}
    loyalty = s.get("ministerial_loyalty", {}) or {}
    stance_bonus = {"consensus": 5.0, "compromise": 3.0, "treasury": -5.0}.get(stance, 0.0)
    rows = []

    for department, name in ministers.items():
        name = str(name or "")
        if not name or name.startswith(("Vacant", "New appointment")):
            continue
        profile = profiles.get(department, {})
        faction = profile.get("faction", "Government Mainstream")
        compatible = cabinet_management.FACTION_IDEOLOGIES.get(faction, ["Centric"])
        faction_effect = 10.0 if ideology in compatible else (-7.0 if ideology != "Centric" else 0.0)
        portfolio_effect, portfolio_reason = _portfolio_interest(department, decision, option)
        rivalry_penalty, rivalry_reason = _rivalry_penalty(s, department)
        amendment_effect = 0.0
        amendment_status = "No demand"
        for outcome in amendment_outcomes or []:
            if department not in outcome.get("departments", []):
                continue
            amendment_status = "Accepted" if outcome.get("accepted") else "Rejected"
            amendment_effect = 7.0 if outcome.get("accepted") else -7.0
        alliance_bonus = 0.0
        for pair, strength in (s.get("ministerial_alliances", {}) or {}).items():
            members = str(pair).split("|")
            if department in members:
                alliance_bonus += min(1.5, float(strength) * 0.015)
        alliance_bonus = min(3.0, alliance_bonus)
        score = (
            52.0
            + (float(loyalty.get(department, 60.0)) - 60.0) * 0.28
            + (float(competence.get(department, 60.0)) - 60.0) * 0.10
            + faction_effect + stance_bonus + portfolio_effect - rivalry_penalty
            + amendment_effect + alliance_bonus
            + (float(s.get("cab_opinion", 60.0)) - 60.0) * 0.10
        )
        score = round(_clip(score), 1)
        position = "Support" if score >= 55 else ("Seek amendments" if score >= 42 else "Oppose")
        rows.append({
            "department": department,
            "minister": name,
            "faction": faction,
            "score": score,
            "position": position,
            "portfolio_effect": portfolio_effect,
            "portfolio_reason": portfolio_reason,
            "rivalry_penalty": rivalry_penalty,
            "rivalry_reason": rivalry_reason,
            "amendment_status": amendment_status,
            "alliance_bonus": round(alliance_bonus, 1),
        })

    if rows:
        support = sum(1 for row in rows if row["position"] == "Support")
        amendments = sum(1 for row in rows if row["position"] == "Seek amendments")
        oppose = len(rows) - support - amendments
        support_pct = 100.0 * support / len(rows)
        amend_pct = 100.0 * amendments / len(rows)
    else:
        support_pct = _clip(56.0 + (float(s.get("cab_opinion", 60.0)) - 60.0) * 0.55 + stance_bonus * 0.5)
        support = int(round(support_pct))
        amendments = 0
        oppose = 0
        amend_pct = 0.0

    if support_pct >= 55:
        status = "Cabinet endorses"
        factor = 1.0
    elif support_pct >= 35 and support_pct + amend_pct >= 55:
        status = "Cabinet seeks amendments"
        factor = 0.90
    else:
        status = "Cabinet divided"
        factor = 0.78

    return {
        "status": status,
        "factor": factor,
        "support_pct": round(support_pct, 1),
        "support": support,
        "amendments": amendments,
        "oppose": oppose,
        "total": len(rows),
        "positions": rows,
    }


def prime_minister_review(s, option, cabinet, fiscal):
    """Model Number 10's independent approval decision."""
    ideology_alignment = 1.0 if str(option.get("ideology", "Centric")) == "Centric" else 0.0
    headroom = float(fiscal["post_headroom"])
    score = (
        55.0
        + (float(s.get("pm_opinion", 50.0)) - 50.0) * 0.30
        + (float(s.get("pm_trust", 60.0)) - 60.0) * 0.22
        + (float(cabinet.get("support_pct", 50.0)) - 55.0) * 0.28
        + (min(3.0, max(0.0, headroom)) * 0.10)
        - (max(0.0, -headroom) * 0.80)
        - (min(5.0, max(0.0, float(fiscal["deficit_delta"])) * 0.40))
        + (2.0 if ideology_alignment else 0.0)
    )
    score = round(_clip(score, -25.0, 100.0), 1)
    if score >= 57:
        status, factor, message = "Approved", 1.0, "The Prime Minister authorises the proposal to proceed."
    elif score >= 39:
        status, factor, message = "Amendments required", 0.82, "Number 10 will only authorise the proposal with changes. Its impact will be reduced."
    else:
        status, factor, message = "Rejected by the Prime Minister", 0.0, "The Prime Minister refuses executive clearance. The proposal does not reach the Commons."
    return {"status": status, "score": score, "factor": factor, "message": message}


def _apply_stance_to_copy(s, stance):
    preview = _PreviewState(dict(s))
    for key, delta in _STANCE_EFFECTS.get(stance, _STANCE_EFFECTS["consensus"]).items():
        preview[key] = round(_clip(float(preview.get(key, 50.0)) + delta), 1)
    return preview


def preflight(s, decision, option, stance="consensus", accepted_amendments=None):
    """Non-mutating Treasury, Cabinet and Number 10 forecast including selected concessions."""
    adjusted_option, negotiation = apply_cabinet_amendments(
        s, decision, option, accepted_amendments=accepted_amendments, commit=False
    )
    preview = _apply_stance_to_copy(s, stance)
    fiscal = costing(preview, decision, adjusted_option)
    cabinet = cabinet_review(preview, decision, adjusted_option, stance, amendment_outcomes=negotiation["outcomes"])
    prime_minister = prime_minister_review(preview, adjusted_option, cabinet, fiscal)
    return {
        "fiscal": fiscal, "cabinet": cabinet, "prime_minister": prime_minister,
        "option": adjusted_option, "negotiation": negotiation,
    }


def _department_for_policy(priority, decision):
    text = " ".join(str(decision.get(key, "")) for key in ("title", "text")).lower()
    if any(word in text for word in ("nhs", "hospital", "health", "care")):
        return "health"
    if any(word in text for word in ("school", "teacher", "education")):
        return "education"
    if any(word in text for word in ("house", "housing", "planning")):
        return "housing"
    if any(word in text for word in ("rail", "transport", "road")):
        return "transport"
    return PRIORITIES.get(priority, {}).get("department", "other")


def record_proposal(s, decision, option, priority, cabinet, prime_minister, vote, quality, fiscal=None, negotiation=None):
    """Log the complete authorisation journey and queue any approved delivery."""
    ensure(s)
    programme = s["annual_government_programme"]
    if priority not in programme.get("priorities", []):
        priority = "general"
    s.policy_proposal_sequence = int(s.get("policy_proposal_sequence", 0)) + 1
    proposal_id = f"{int(s.get('term', 1))}-{int(s.get('year', 1))}-{s.policy_proposal_sequence}"
    fiscal = fiscal or costing(s, decision, option)
    vote_status = str(vote.get("status", "Not submitted"))
    pm_status = prime_minister.get("status", "Rejected by the Prime Minister")
    cabinet_status = cabinet.get("status", "Cabinet review unavailable")

    if pm_status == "Rejected by the Prime Minister":
        outcome = "Stopped by Number 10"
        priority_weight = 0.0
    elif vote_status == "Rejected":
        outcome = "Commons rejected — limited pilot only"
        priority_weight = 0.18
    elif vote_status == "Passed with amendments" or pm_status == "Amendments required" or cabinet_status != "Cabinet endorses":
        outcome = "Approved with changes"
        priority_weight = 0.68
    else:
        outcome = "Approved for delivery"
        priority_weight = 1.0

    record = {
        "id": proposal_id,
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "block": int(s.get("block", 1)),
        "title": str(decision.get("title", "Policy proposal")),
        "choice": str(option.get("label", "Government proposal")),
        "ideology": str(option.get("ideology", "Centric")),
        "priority": priority,
        "priority_label": priority_label(priority),
        "cabinet_status": cabinet_status,
        "cabinet_support": float(cabinet.get("support_pct", 0.0)),
        "cabinet_positions": list(cabinet.get("positions", [])),
        "cabinet_amendments": list((negotiation or {}).get("outcomes", [])),
        "cabinet_amendment_cost": float((negotiation or {}).get("cost", 0.0)),
        "prime_minister_status": pm_status,
        "prime_minister_score": float(prime_minister.get("score", 0.0)),
        "commons_status": vote_status,
        "ayes": int(vote.get("ayes", 0)),
        "noes": int(vote.get("noes", 0)),
        "outcome": outcome,
        "priority_weight": priority_weight,
        "quality": round(max(0.0, min(1.0, float(quality))), 3),
        "fiscal_headroom_change": fiscal["headroom_delta"],
        "deficit_change": fiscal["deficit_delta"],
        "delivery_progress": 0.0,
        "delivery_id": None,
    }

    if pm_status != "Rejected by the Prime Minister" and float(quality) > 0.0:
        department = _department_for_policy(priority, decision)
        minister = str(s.get("cabinet_ministers", {}).get(department, ""))
        competence = float(s.get("ministerial_competence", {}).get(department, 60.0))
        initial_progress = 14.0 if vote_status != "Rejected" else 5.0
        delivery = {
            "id": proposal_id,
            "term": record["term"],
            "start_year": record["year"],
            "title": record["title"],
            "choice": record["choice"],
            "priority": priority,
            "priority_label": record["priority_label"],
            "department": department,
            "minister": minister or "Departmental team",
            "competence_at_authorisation": round(competence, 1),
            "quality": record["quality"],
            "progress": initial_progress,
            "status": "Mobilising" if vote_status != "Rejected" else "Limited pilot",
            "last_advanced_period": None,
            "years_in_delivery": 0,
        }
        s.policy_deliveries = (list(s.get("policy_deliveries", [])) + [delivery])[-100:]
        record["delivery_id"] = proposal_id
        record["delivery_progress"] = initial_progress

    s.policy_proposals = (list(s.get("policy_proposals", [])) + [record])[-120:]
    return record


def priority_progress(s, priority, programme=None):
    if programme is None:
        programme = current(s)
    proposals = [
        item for item in s.get("policy_proposals", [])
        if item.get("priority") == priority
        and int(item.get("term", -1)) == int(programme.get("term", -2))
        and int(item.get("year", -1)) == int(programme.get("year", -2))
    ]
    if not proposals:
        return 0.0
    contribution = 0.0
    for item in proposals:
        delivery = next((row for row in s.get("policy_deliveries", []) if row.get("id") == item.get("delivery_id")), None)
        delivery_progress = float(delivery.get("progress", 0.0)) if delivery else 0.0
        contribution += float(item.get("priority_weight", 0.0)) * 0.60 + delivery_progress / 100.0 * 0.40
    return round(min(100.0, contribution * 100.0), 1)


def overall_progress(s, programme=None):
    if programme is None:
        programme = current(s)
    priorities = list(programme.get("priorities", []))
    if not priorities:
        return 0.0
    return round(sum(priority_progress(s, key, programme) for key in priorities) / len(priorities), 1)


def close_annual_programme(s):
    """Advance delivery once and archive the annual scorecard before the year rolls over."""
    ensure(s)
    period = _period(s)
    for item in s.get("policy_deliveries", []):
        if item.get("status") == "Complete" or item.get("last_advanced_period") == period:
            continue
        department = item.get("department", "other")
        competence = float(s.get("ministerial_competence", {}).get(department, 60.0))
        quality = float(item.get("quality", 0.7))
        increment = 34.0 + (competence - 60.0) * 0.25 + (quality - 0.7) * 12.0
        increment = max(18.0, min(48.0, increment))
        item["progress"] = round(min(100.0, float(item.get("progress", 0.0)) + increment), 1)
        item["years_in_delivery"] = int(item.get("years_in_delivery", 0)) + 1
        item["last_advanced_period"] = period
        if item["progress"] >= 100.0:
            item["status"] = "Complete"
        elif competence < 38.0 and item["years_in_delivery"] >= 2:
            item["status"] = "At risk — departmental capacity"
        elif item["progress"] >= 70.0:
            item["status"] = "Final delivery stage"
        else:
            item["status"] = "In delivery"
        for proposal in s.get("policy_proposals", []):
            if proposal.get("id") == item.get("id"):
                proposal["delivery_progress"] = item["progress"]
                break

    programme = s["annual_government_programme"]
    snapshot = dict(programme)
    snapshot["priority_results"] = [
        {"priority": key, "label": priority_label(key), "progress": priority_progress(s, key, programme)}
        for key in programme.get("priorities", [])
    ]
    snapshot["overall_progress"] = overall_progress(s, programme)
    snapshot["proposal_count"] = sum(
        1 for item in s.get("policy_proposals", [])
        if int(item.get("term", -1)) == int(s.get("term", 1))
        and int(item.get("year", -1)) == int(s.get("year", 1))
    )
    archive = list(s.get("annual_programme_history", []))
    if not any(item.get("period") == period for item in archive):
        archive.append(snapshot)
    s["annual_programme_history"] = archive[-25:]
    return snapshot


def render_summary(s=None):
    """Compact Government Programme progress for the Chancellor's Office."""
    if s is None:
        s = st.session_state
    programme = current(s)
    st.markdown("#### Annual Government Programme")
    adopted = "Adopted" if programme.get("declared") else "Draft priorities — adopt them in Cabinet"
    st.caption(f"Year {programme.get('year', 1)} · {adopted}")
    for key in programme.get("priorities", []):
        progress = priority_progress(s, key, programme)
        st.write(f"**{priority_label(key)}** · {progress:.0f}%")
        st.progress(int(progress))
    active = sum(1 for item in s.get("policy_deliveries", []) if item.get("status") != "Complete")
    st.caption(f"{active} policy implementation(s) still in progress.")


def render(s=None):
    """Cabinet workspace: annual priorities, proposal outcomes and implementation tracking."""
    if s is None:
        s = st.session_state
    programme = current(s)
    st.markdown("### The annual Government Programme")
    st.caption("Choose two or three priorities for this financial year. Policies are assessed against the programme, and departments are tracked until delivery is complete.")
    status = "Adopted" if programme.get("declared") else "Draft — suggested by your five-year mandate"
    st.markdown(f"**Status:** {status} · **Term {programme.get('term', 1)}, Year {programme.get('year', 1)}**")
    current_priorities = list(programme.get("priorities", []))
    key = f"programme_editor_{programme.get('term', 1)}_{programme.get('year', 1)}"
    selected = st.multiselect(
        "Annual priorities",
        options=list(PRIORITIES),
        default=current_priorities,
        format_func=priority_label,
        max_selections=3,
        key=key,
        help="Choose the two or three outcomes the Government will concentrate on this year."
    )
    if st.button("Adopt annual Government Programme", key=f"adopt_programme_{programme.get('period')}", type="primary", use_container_width=True):
        if not set_priorities(s, selected):
            st.warning("Choose two or three priorities before adopting the programme.")
        else:
            st.rerun()

    st.divider()
    st.markdown("#### Progress against annual priorities")
    rows = []
    for priority in programme.get("priorities", []):
        progress = priority_progress(s, priority, programme)
        count = sum(
            1 for item in s.get("policy_proposals", [])
            if item.get("priority") == priority
            and int(item.get("term", -1)) == int(programme.get("term", -2))
            and int(item.get("year", -1)) == int(programme.get("year", -2))
        )
        rows.append({"Priority": priority_label(priority), "Progress": f"{progress:.0f}%", "Proposals": str(count)})
        st.write(f"**{priority_label(priority)}** · {progress:.0f}% · {count} proposal(s)")
        st.progress(int(progress))
        st.caption(PRIORITIES[priority]["description"])
    total = overall_progress(s, programme)
    c1, c2, c3 = st.columns(3)
    c1.metric("Programme progress", f"{total:.0f}%")
    c2.metric("Proposals this year", sum(int(row["Proposals"]) for row in rows))
    c3.metric("Departments delivering", len({x["department"] for x in s.get("policy_deliveries", []) if x.get("status") != "Complete"}))

    st.divider()
    st.markdown("#### Policy authorisation register")
    proposals = [
        item for item in s.get("policy_proposals", [])
        if int(item.get("term", -1)) == int(s.get("term", 1))
    ]
    if proposals:
        display = [{
            "Year": item["year"],
            "Proposal": item["title"],
            "Programme priority": item["priority_label"],
            "Cabinet": item["cabinet_status"],
            "Prime Minister": item["prime_minister_status"],
            "Commons": item["commons_status"],
            "Outcome": item["outcome"],
        } for item in proposals[-12:]]
        st.dataframe(display[::-1], hide_index=True, use_container_width=True)
    else:
        st.info("No proposals have entered the authorisation process yet.")

    latest = list(reversed(proposals[-5:]))
    if latest:
        with st.expander("Cabinet roll-call and ministerial positions"):
            for item in latest:
                st.markdown(f"**{item['title']}** · {item['cabinet_status']}")
                if item.get("cabinet_positions"):
                    st.dataframe([{
                        "Minister": row.get("minister", ""),
                        "Faction": row.get("faction", ""),
                        "Position": row.get("position", ""),
                        "Assessment": row.get("score", 0),
                    } for row in item["cabinet_positions"]], hide_index=True, use_container_width=True)
                else:
                    st.caption("Cabinet support was estimated from overall Cabinet confidence.")

    st.divider()
    st.markdown("#### Departmental implementation tracker")
    deliveries = list(s.get("policy_deliveries", []))
    if deliveries:
        display = [{
            "Policy": item["title"],
            "Department": str(item.get("department", "other")).replace("_", " ").title(),
            "Minister": item.get("minister", "Departmental team"),
            "Progress": round(float(item.get("progress", 0.0))),
            "Status": item.get("status", "Mobilising"),
        } for item in deliveries[-20:]]
        st.dataframe(display[::-1], hide_index=True, use_container_width=True,
                     column_config={"Progress": st.column_config.ProgressColumn("Progress", min_value=0, max_value=100, format="%d%%")})
    else:
        st.info("Approved policies will appear here as departments move from mobilisation to delivery.")
    history = list(s.get("annual_programme_history", []))
    if history:
        with st.expander("Previous annual programmes"):
            for item in reversed(history[-5:]):
                st.markdown(f"**Term {item.get('term', 1)}, Year {item.get('year', 1)}** · {item.get('overall_progress', 0):.0f}% delivered")
                for result in item.get("priority_results", []):
                    st.caption(f"{result.get('label', priority_label(result.get('priority')))}: {result.get('progress', 0):.0f}%")
