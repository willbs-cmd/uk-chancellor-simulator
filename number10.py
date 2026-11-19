"""Number 10 and Treasury relationship: escalating tension and formal economic oversight."""
from __future__ import annotations


def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def ensure(s):
    """Migrate live sessions and older saves without resetting an existing game."""
    s.setdefault("pm_treasury_tension", 12.0)
    s.setdefault("pm_treasury_tension_history", [])
    s.setdefault("active_pm_intervention", None)
    s.setdefault("pm_committee_until_year", 0)
    s.setdefault("pm_committee_history", [])
    return s


def committee_active(s):
    ensure(s)
    until = int(s.get("pm_committee_until_year", 0))
    return until > 0 and int(s.get("year", 1)) <= until


def tension_status(value):
    value = float(value)
    if value >= 75: return "Critical"
    if value >= 58: return "Severe"
    if value >= 38: return "Strained"
    if value >= 22: return "Uneasy"
    return "Working relationship"


def adjust_tension(s, change, reason, source="government", allow_intervention=True):
    """Move the persistent dispute gauge and raise a Number 10 intervention when it boils over."""
    ensure(s)
    before = float(s.get("pm_treasury_tension", 12.0))
    after = round(_clip(before + float(change)), 1)
    actual = round(after - before, 1)
    s.pm_treasury_tension = after
    if actual:
        row = {
            "term": int(s.get("term", 1)), "year": int(s.get("year", 1)),
            "source": str(source), "reason": str(reason),
            "change": actual, "tension": after, "status": tension_status(after),
        }
        s.pm_treasury_tension_history = (list(s.get("pm_treasury_tension_history", [])) + [row])[-30:]
    can_intervene = (
        allow_intervention and after >= 68.0
        and not s.get("active_pm_intervention")
        and not s.get("active_pm_meeting")
        and not s.get("active_pm_ultimatum")
        and not s.get("game_over")
        and not committee_active(s)
    )
    if can_intervene:
        issue = {
            "term": int(s.get("term", 1)), "year": int(s.get("year", 1)),
            "tension": after, "source": str(source), "reason": str(reason),
            "pm": (
                "The Treasury and Number 10 cannot continue operating as competing centres of economic policy. "
                "I am establishing a Cabinet Economic Strategy Committee. The question is whether you will work with it."
            ),
        }
        s.active_pm_intervention = issue
        cards = list(s.get("event_cards", []))
        cards.append({
            "title": "Number 10 moves to take control of economic strategy",
            "text": "Repeated disputes have pushed the Chancellor–Prime Minister relationship to breaking point. The PM is establishing a Cabinet Economic Strategy Committee.",
            "summary": f"Treasury–Number 10 tension {after:.0f}/100 · formal intervention",
        })
        s.event_cards = cards[-12:]
    return {"before": before, "after": after, "change": actual, "intervention": s.get("active_pm_intervention")}


def review_relationship(s, trust_change):
    """Annual delivery affects the temperature between the Treasury and Number 10."""
    trust_change = float(trust_change)
    if trust_change < -0.05:
        adjust_tension(s, min(9.0, abs(trust_change) * 2.6),
                       "A poor annual relationship review", "annual_review")
    elif trust_change > 0.05:
        adjust_tension(s, -min(6.0, trust_change * 2.0),
                       "A stronger annual relationship review", "annual_review")


def review_budget(s, choice, met_count, total_count):
    """The Budget is a major test of whether the Chancellor accepts the Government's agreed direction."""
    ensure(s)
    choice = str(choice or "")
    met_count, total_count = int(met_count), max(1, int(total_count))
    active = committee_active(s)
    if choice == "Accept the Prime Minister’s priorities" and met_count == total_count:
        change, reason = -9.0, "The Budget fully delivered the Prime Minister's priorities"
        if active:
            s.pm_trust = round(_clip(float(s.get("pm_trust", 70.0)) + 3.0), 1)
            s.pm_opinion = round(_clip(float(s.get("pm_opinion", 50.0)) + 2.0), 1)
    elif choice == "Stand firm on the Treasury plan" and met_count < total_count:
        change, reason = 12.0, "The Chancellor rejected Number 10's Budget priorities"
        if active:
            s.pm_trust = round(_clip(float(s.get("pm_trust", 70.0)) - 4.0), 1)
            s.pm_opinion = round(_clip(float(s.get("pm_opinion", 50.0)) - 3.0), 1)
    elif met_count >= (total_count + 1) // 2:
        change, reason = -3.0, "A workable Budget compromise"
    else:
        change, reason = 4.0, "The Budget left most Number 10 priorities unmet"
    return adjust_tension(s, change, reason, "budget")


def resolve_intervention(s, choice):
    """The PM establishes the committee either way; the Chancellor decides how to respond."""
    ensure(s)
    issue = s.get("active_pm_intervention")
    if not issue or choice not in {"cooperate", "challenge"}:
        return False
    year = int(s.get("year", 1))
    until = max(int(s.get("pm_committee_until_year", 0)), year + 1)
    s.pm_committee_until_year = until
    if choice == "cooperate":
        s.pm_trust = round(_clip(float(s.get("pm_trust", 70.0)) + 8.0), 1)
        s.pm_opinion = round(_clip(float(s.get("pm_opinion", 50.0)) + 4.0), 1)
        s.cab_opinion = round(_clip(float(s.get("cab_opinion", 50.0)) + 2.0), 1)
        s.backbench_opinion = round(_clip(float(s.get("backbench_opinion", 50.0)) - 1.0), 1)
        adjust_tension(s, -32.0, "The Chancellor agreed to work with the committee",
                       "committee_response", allow_intervention=False)
        outcome = (
            f"You agree to work with the Cabinet Economic Strategy Committee. Number 10 restores some trust, "
            f"but major economic proposals face additional fiscal scrutiny through Year {until}."
        )
        label = "Cooperate with the committee"
    else:
        s.pm_trust = round(_clip(float(s.get("pm_trust", 70.0)) - 10.0), 1)
        s.pm_opinion = round(_clip(float(s.get("pm_opinion", 50.0)) - 7.0), 1)
        s.backbench_opinion = round(_clip(float(s.get("backbench_opinion", 50.0)) + 3.0), 1)
        s.party_opinion = round(_clip(float(s.get("party_opinion", 50.0)) + 1.0), 1)
        adjust_tension(s, 8.0, "The Chancellor publicly challenged Number 10's intervention",
                       "committee_response", allow_intervention=False)
        outcome = (
            f"You publicly challenge Number 10. The committee is established regardless, but your authority inside "
            f"Government is weakened and the PM may move against you. Oversight remains through Year {until}."
        )
        label = "Challenge Number 10 publicly"
    s.active_pm_intervention = None
    record = {
        "term": int(issue.get("term", s.get("term", 1))), "year": year,
        "decision": label, "tension_before": float(issue.get("tension", 0.0)),
        "tension_after": float(s.get("pm_treasury_tension", 0.0)),
        "committee_until_year": until, "outcome": outcome,
    }
    s.pm_committee_history = (list(s.get("pm_committee_history", [])) + [record])[-20:]
    s.message = outcome
    s.humphrey_note = "Number 10 has the authority to set up a Cabinet committee. The Chancellor's choice is whether to shape its work or openly resist it."
    cards = list(s.get("event_cards", []))
    cards.append({
        "title": "Cabinet Economic Strategy Committee established",
        "text": outcome, "summary": f"Number 10 oversight remains in force through Year {until}",
    })
    s.event_cards = cards[-12:]
    if choice == "challenge" and (
        float(s.get("pm_trust", 70.0)) < 38.0 or float(s.get("pm_opinion", 50.0)) < 30.0
    ) and not s.get("active_pm_ultimatum"):
        s.active_pm_ultimatum = {
            "year": year, "pm_opinion": round(float(s.get("pm_opinion", 50.0)), 1),
            "severity": "serious", "source": "committee_challenge",
        }
    return True


def annual_review(s):
    """Expire time-limited committee oversight once its final year has passed."""
    ensure(s)
    until = int(s.get("pm_committee_until_year", 0))
    if until and int(s.get("year", 1)) > until:
        s.pm_committee_until_year = 0
        adjust_tension(s, -14.0, "The Cabinet committee's temporary mandate expired",
                       "committee_expiry", allow_intervention=False)
        cards = list(s.get("event_cards", []))
        cards.append({
            "title": "Number 10 oversight ends",
            "text": "The temporary Cabinet Economic Strategy Committee mandate has expired. The Treasury regains its normal executive clearance position.",
            "summary": "Temporary economic oversight concluded",
        })
        s.event_cards = cards[-12:]
        return True
    return False
