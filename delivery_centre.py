"""National delivery command centre for the Chancellor Simulator.

Departmental contracts, in-year funding requests and policy delivery visibility.
Approved Budget ledgers are never mutated here: exceptional awards are recorded
as explicit one-off interventions against fiscal headroom.
"""
import streamlit as st


AMBITION = {
    "steady": {"label": "Steady improvement", "lift": 2.0},
    "stretch": {"label": "Stretch target", "lift": 5.0},
    "recovery": {"label": "Recovery plan", "lift": 3.0},
}
MAX_REQUEST_BN = 5.0
MAX_PENDING_PER_DEPARTMENT = 1


def _period(s):
    return f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"


def _next_period(s):
    year = int(s.get("year", 1)) + 1
    term = int(s.get("term", 1))
    if year > 5:
        return f"{term + 1}:1"
    return f"{term}:{year}"


def _department_data():
    import budget
    import cabinet_management
    output = {}
    service_map = cabinet_management.SERVICE_FOR_DEPARTMENT
    for key, details in budget.DEPARTMENT_MINISTERS.items():
        spend = budget.SPEND_DEFAULTS.get(key, {})
        output[key] = {
            "label": spend.get("label", key.replace("_", " ").title()),
            "opening_minister": details[0],
            "portfolio": details[1],
            "service": service_map.get(key),
        }
    return output


def _actual_score(s, department, spec=None):
    spec = spec or _department_data().get(department, {})
    service = spec.get("service")
    if service:
        scores = s.get("public_service_scores", {}) or {}
        if service in scores:
            return max(0.0, min(100.0, float(scores[service])))
    return max(0.0, min(100.0, float(s.get("ministerial_competence", {}).get(department, 60.0))))


def ensure(s=None):
    """Create and migrate departmental contracts without changing fiscal allocations."""
    if s is None:
        s = st.session_state
    s.setdefault("department_delivery_contracts", {})
    s.setdefault("delivery_contract_history", [])
    s.setdefault("delivery_last_review_period", "")
    s.setdefault("delivery_funding_requests", [])
    s.setdefault("delivery_funding_sequence", 0)
    s.setdefault("delivery_funding_spent", 0.0)
    contracts = dict(s.get("department_delivery_contracts", {}) or {})
    specs = _department_data()
    allocations = s.get("dept_spend", {}) or {}
    for department, spec in specs.items():
        score = _actual_score(s, department, spec)
        contract = dict(contracts.get(department, {}) or {})
        contract.setdefault("department", department)
        contract.setdefault("department_label", spec["label"])
        contract.setdefault("minister", s.get("cabinet_ministers", {}).get(department, spec["opening_minister"]))
        contract.setdefault("objective", spec["portfolio"])
        contract.setdefault("period", _period(s))
        contract.setdefault("ambition", "steady")
        contract.setdefault("baseline_score", score)
        contract.setdefault(
            "target_score",
            round(min(100.0, score + AMBITION["steady"]["lift"]), 1),
        )
        contract.setdefault("budget_ceiling_bn", float(allocations.get(department, 0.0) or 0.0))
        contract.setdefault("funding_support_bn", 0.0)
        contract.setdefault("status", "Contract agreed")
        contract.setdefault("last_review", None)
        contract.setdefault("history", [])
        contract["department_label"] = spec["label"]
        contract["minister"] = s.get("cabinet_ministers", {}).get(department, contract.get("minister", spec["opening_minister"]))
        # This is a read-only view of the approved departmental allocation. Refresh
        # after Budget roll-forwards without using it to alter the ledger.
        if department in allocations:
            contract["budget_ceiling_bn"] = round(float(allocations.get(department, 0.0)), 2)
        contracts[department] = contract
    s["department_delivery_contracts"] = contracts
    s["delivery_contract_history"] = list(s.get("delivery_contract_history", []))[-40:]
    s["delivery_funding_requests"] = list(s.get("delivery_funding_requests", []))[-100:]
    s["delivery_funding_sequence"] = int(s.get("delivery_funding_sequence", 0))
    s["delivery_funding_spent"] = float(s.get("delivery_funding_spent", 0.0))
    return s


def set_contract(s, department, ambition):
    """Set an annual improvement target; this records a target, not a spending change."""
    ensure(s)
    if ambition not in AMBITION or department not in s["department_delivery_contracts"]:
        return False
    spec = _department_data()[department]
    contract = dict(s["department_delivery_contracts"][department])
    baseline = _actual_score(s, department, spec)
    lift = float(AMBITION[ambition]["lift"])
    if ambition == "recovery" and baseline < 45.0:
        lift = 5.0
    contract.update({
        "period": _period(s),
        "ambition": ambition,
        "baseline_score": round(baseline, 1),
        "target_score": round(min(100.0, baseline + lift), 1),
        "budget_ceiling_bn": round(float((s.get("dept_spend", {}) or {}).get(department, 0.0)), 2),
        "objective": spec["portfolio"],
        "status": "Contract agreed",
    })
    s["department_delivery_contracts"][department] = contract
    return True


def create_funding_request(s, department, title, rationale, amount_bn):
    """Create one exceptional in-year funding bid. No Budget ledger changes are made."""
    ensure(s)
    amount = round(float(amount_bn), 2)
    title = str(title or "").strip()
    rationale = str(rationale or "").strip()
    if department not in s["department_delivery_contracts"]:
        return None, "Select a valid department."
    if not title or len(title) > 90:
        return None, "Give the request a title of 1–90 characters."
    if len(rationale) < 12 or len(rationale) > 500:
        return None, "Explain the delivery case in 12–500 characters."
    if not 0.1 <= amount <= MAX_REQUEST_BN:
        return None, f"Requests must be between £0.1bn and £{MAX_REQUEST_BN:.1f}bn."
    period = _period(s)
    pending = [
        item for item in s.get("delivery_funding_requests", [])
        if item.get("department") == department
        and item.get("period") == period
        and item.get("status") == "Pending"
    ]
    if len(pending) >= MAX_PENDING_PER_DEPARTMENT:
        return None, "This department already has a funding request awaiting a Treasury decision."
    s["delivery_funding_sequence"] = int(s.get("delivery_funding_sequence", 0)) + 1
    request_id = f"DF-{int(s.get('term', 1))}-{int(s.get('year', 1))}-{s['delivery_funding_sequence']}"
    request = {
        "id": request_id,
        "period": period,
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "department": department,
        "department_label": s["department_delivery_contracts"][department]["department_label"],
        "minister": s.get("cabinet_ministers", {}).get(department, "Departmental team"),
        "title": title,
        "rationale": rationale,
        "requested_bn": amount,
        "approved_bn": 0.0,
        "status": "Pending",
        "decision": "",
        "decision_period": "",
    }
    s["delivery_funding_requests"] = (list(s.get("delivery_funding_requests", [])) + [request])[-100:]
    return request_id, None


def decide_funding_request(s, request_id, decision, approved_bn=0.0):
    """Approve/reject a one-off bid and book its full fiscal cost transparently."""
    ensure(s)
    request = next(
        (item for item in s.get("delivery_funding_requests", [])
         if item.get("id") == request_id),
        None,
    )
    if not request or request.get("status") != "Pending":
        return False, "This funding request is no longer awaiting a decision."
    decision = str(decision).lower()
    if decision == "reject":
        request["status"] = "Rejected"
        request["decision"] = "Rejected by the Chancellor"
        request["decision_period"] = _period(s)
        return True, None
    if decision != "approve":
        return False, "Choose approve or reject."
    amount = round(float(approved_bn), 2)
    requested = float(request.get("requested_bn", 0.0))
    available = max(0.0, float(s.get("headroom", 0.0)))
    if amount < 0.1 or amount > requested + 0.001:
        return False, "The award must be at least £0.1bn and cannot exceed the request."
    if amount > available + 0.001:
        return False, f"Only £{available:.1f}bn of fiscal headroom is currently available."
    # This is an explicit one-off in-year intervention. It does not rewrite
    # budget_applied, dept_spend, tax settings or any approved departmental ledger.
    s["headroom"] = round(float(s.get("headroom", 0.0)) - amount, 1)
    s["deficit"] = round(float(s.get("deficit", 0.0)) + amount, 1)
    s["delivery_funding_spent"] = round(float(s.get("delivery_funding_spent", 0.0)) + amount, 2)
    contract = s["department_delivery_contracts"].get(request["department"], {})
    contract["funding_support_bn"] = round(float(contract.get("funding_support_bn", 0.0)) + amount, 2)
    contract["status"] = "In-year support approved"
    request["approved_bn"] = amount
    request["status"] = "Approved" if amount >= requested - 0.001 else "Part-funded"
    request["decision"] = "Approved by the Chancellor"
    request["decision_period"] = _period(s)
    request["funding_source"] = "Fiscal headroom"
    request["fiscal_effect"] = f"Headroom −£{amount:.2f}bn; deficit +£{amount:.2f}bn"
    return True, None


def close_year(s):
    """Review every departmental contract once, then roll its target into the next year."""
    ensure(s)
    period = _period(s)
    if s.get("delivery_last_review_period") == period:
        return list(s.get("delivery_contract_history", []))[-1] if s.get("delivery_contract_history") else None
    specs = _department_data()
    reviews = []
    for department, contract in s.get("department_delivery_contracts", {}).items():
        if contract.get("period") != period:
            continue
        spec = specs.get(department, {})
        actual = _actual_score(s, department, spec)
        target = float(contract.get("target_score", actual))
        support_bn = float(contract.get("funding_support_bn", 0.0))
        support_credit = min(3.0, support_bn * 0.6)
        assessed = min(100.0, actual + support_credit)
        gap = assessed - target
        if gap >= 0:
            outcome = "Met"
        elif gap >= -3.0:
            outcome = "Partly met"
        else:
            outcome = "Missed"
        review = {
            "period": period,
            "term": int(s.get("term", 1)),
            "year": int(s.get("year", 1)),
            "department": department,
            "department_label": contract.get("department_label", department.title()),
            "minister": s.get("cabinet_ministers", {}).get(department, contract.get("minister", "Departmental team")),
            "baseline_score": round(float(contract.get("baseline_score", actual)), 1),
            "target_score": round(target, 1),
            "actual_score": round(actual, 1),
            "support_credit": round(support_credit, 1),
            "support_bn": round(support_bn, 2),
            "outcome": outcome,
        }
        contract["last_review"] = review
        contract["history"] = (list(contract.get("history", [])) + [review])[-8:]
        contract["status"] = outcome
        contract["funding_support_bn"] = 0.0
        contract["baseline_score"] = round(actual, 1)
        contract["budget_ceiling_bn"] = round(float((s.get("dept_spend", {}) or {}).get(department, 0.0)), 2)
        next_ambition = contract.get("ambition", "steady")
        lift = float(AMBITION.get(next_ambition, AMBITION["steady"])["lift"])
        if next_ambition == "recovery" and actual < 45.0:
            lift = 5.0
        contract["target_score"] = round(min(100.0, actual + lift), 1)
        contract["period"] = _next_period(s)
        reviews.append(review)
    snapshot = {
        "period": period,
        "term": int(s.get("term", 1)),
        "year": int(s.get("year", 1)),
        "reviews": reviews,
        "met": sum(1 for row in reviews if row["outcome"] == "Met"),
        "partly_met": sum(1 for row in reviews if row["outcome"] == "Partly met"),
        "missed": sum(1 for row in reviews if row["outcome"] == "Missed"),
    }
    s["delivery_contract_history"] = (list(s.get("delivery_contract_history", [])) + [snapshot])[-40:]
    s["delivery_last_review_period"] = period
    return snapshot


def _contract_rows(s):
    specs = _department_data()
    rows = []
    for department, contract in s.get("department_delivery_contracts", {}).items():
        spec = specs.get(department, {})
        actual = _actual_score(s, department, spec)
        baseline = float(contract.get("baseline_score", actual))
        target = float(contract.get("target_score", actual))
        competence = float(s.get("ministerial_competence", {}).get(department, 60.0))
        loyalty = float(s.get("ministerial_loyalty", {}).get(department, 60.0))
        confidence = max(0.0, min(100.0, competence * 0.65 + loyalty * 0.35))
        if actual > baseline + 0.5:
            direction = "Improving"
        elif actual < baseline - 0.5:
            direction = "Declining"
        else:
            direction = "Stable"
        if contract.get("last_review"):
            status = f"Last year: {contract['last_review'].get('outcome', 'Reviewed')}"
        elif actual < baseline - 1.0:
            status = "Recovery required"
        else:
            status = "On course"
        rows.append({
            "department": department,
            "Department": contract.get("department_label", department.title()),
            "Minister": s.get("cabinet_ministers", {}).get(department, contract.get("minister", "Departmental team")),
            "Baseline": round(baseline, 1),
            "Actual": round(actual, 1),
            "Target": round(target, 1),
            "Trend": direction,
            "Confidence": round(confidence),
            "Budget ceiling (£bn)": round(float(contract.get("budget_ceiling_bn", 0.0)), 2),
            "One-off support (£bn)": round(float(contract.get("funding_support_bn", 0.0)), 2),
            "Status": status,
        })
    return rows


def _next_milestone(delivery):
    """Derive a readable milestone and target year from the existing delivery progression."""
    progress = max(0.0, min(100.0, float(delivery.get("progress", 0.0))))
    start_year = int(delivery.get("start_year", 1))
    start_term = int(delivery.get("term", 1))
    milestones = (
        ("Mobilisation complete", 25.0, 0),
        ("Operational rollout", 55.0, 1),
        ("Full implementation", 85.0, 2),
        ("Benefits review", 100.0, 3),
    )
    next_item = next((item for item in milestones if progress < item[1]), None)
    if next_item is None:
        return "Benefits review complete", f"T{start_term} Y{start_year + 3}"
    title, threshold, offset = next_item
    year = start_year + offset
    term = start_term
    while year > 5:
        year -= 5
        term += 1
    return title, f"T{term} Y{year}"


def _adviser_notes(s, pending_count, programme_count):
    """Short, state-aware briefing from the core Treasury advisory roles."""
    log = list(s.get("officials_log", []))
    if log:
        latest = log[-1]
        permanent_secretary = f"{latest.get('view', 'Private advice')}: {latest.get('note', '')}"
    elif float(s.get("headroom", 0.0)) < 3.0:
        permanent_secretary = "Retain a margin against forecast revisions. Do not make permanent commitments from a narrow fiscal buffer."
    else:
        permanent_secretary = "Require transparent costings, named departmental ownership and a clear distinction between one-off and recurring expenditure."

    growth = float(s.get("growth", 0.0))
    inflation = float(s.get("inflation", 2.0))
    headroom = float(s.get("headroom", 0.0))
    if headroom < 0:
        chief_economist = "Fiscal headroom is negative. Reassess affordability before approving further interventions."
    elif inflation >= 4.5:
        chief_economist = "Inflation is elevated. Prefer supply-side improvements over broad demand stimulus."
    elif growth < 0:
        chief_economist = "Output is contracting. Protect high-value capacity and scrutinise the speed at which support can reach the economy."
    elif growth < 1:
        chief_economist = "Growth is subdued. Prioritise skills, productivity and projects with credible delivery capacity."
    else:
        chief_economist = "Growth is holding up. Protect fiscal resilience and concentrate on projects with durable productivity returns."

    spending_adviser = (
        f"{pending_count} bid(s) are awaiting a decision. Test whether each request is additional, time-limited and linked to measurable outcomes."
        if pending_count else
        "No bids are awaiting a decision. Ask departments to identify delivery bottlenecks before they request extra money."
    )
    investment_adviser = (
        f"{programme_count} approved programme(s) remain in delivery. Monitor milestones and cost overruns before expanding the project pipeline."
        if programme_count else
        "No approved policy programmes are currently in the implementation pipeline. Avoid creating projects without a named department and delivery plan."
    )
    return [
        ("Permanent Secretary", permanent_secretary),
        ("Chief Economic Adviser", chief_economist),
        ("Chief Spending Adviser", spending_adviser),
        ("Chief Investment Adviser", investment_adviser),
    ]


def render(s=None):
    """National delivery board, departmental contracts and Treasury funding desk."""
    if s is None:
        s = st.session_state
    ensure(s)
    rows = _contract_rows(s)
    requests = list(s.get("delivery_funding_requests", []))
    pending = [item for item in requests if item.get("status") == "Pending"]
    history = list(s.get("delivery_contract_history", []))
    headroom = float(s.get("headroom", 0.0))
    deliveries = [item for item in s.get("policy_deliveries", []) if item.get("status") != "Complete"]
    met_last = history[-1]["met"] if history else 0
    reviewed_last = len(history[-1]["reviews"]) if history else 0
    confidence = round(sum(row["Confidence"] for row in rows) / len(rows)) if rows else 0

    st.markdown("#### National Delivery Board")
    st.caption("One view of departmental targets, approved programmes and exceptional funding requests.")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Departmental contracts", len(rows))
    k2.metric("Delivery confidence", f"{confidence}/100")
    k3.metric("Live programmes", len(deliveries))
    k4.metric("Funding bids pending", len(pending))
    if history:
        latest = history[-1]
        st.caption(
            f"Latest annual contract review · Term {latest.get('term', 1)}, Year {latest.get('year', 1)} · "
            f"{latest.get('met', 0)} met · {latest.get('partly_met', 0)} partly met · {latest.get('missed', 0)} missed"
        )
    else:
        st.caption("Contracts are newly established. The first full assessment will take place at the annual year-end review.")

    st.divider()
    st.markdown("#### Departmental delivery contracts")
    st.caption("Targets are set against the current service score or ministerial competence. A contract changes the performance target, not the approved spending allocation.")
    if rows:
        import pandas as pd
        frame = pd.DataFrame(rows)
        st.dataframe(
            frame.drop(columns=["department"]),
            hide_index=True,
            use_container_width=True,
            column_config={
                "Confidence": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=100),
                "Actual": st.column_config.NumberColumn("Actual", format="%.1f"),
                "Target": st.column_config.NumberColumn("Target", format="%.1f"),
                "Baseline": st.column_config.NumberColumn("Baseline", format="%.1f"),
            },
        )
    else:
        st.info("Departmental contracts will appear when the Cabinet is formed.")

    dept_options = _department_data()
    with st.form("delivery_contract_form"):
        st.markdown("**Set or renegotiate a contract**")
        contract_department = st.selectbox(
            "Department",
            list(dept_options),
            format_func=lambda key: dept_options[key]["label"],
        )
        ambition = st.selectbox(
            "Delivery ambition",
            options=list(AMBITION),
            format_func=lambda key: f"{AMBITION[key]['label']} (+{AMBITION[key]['lift']:.0f} points target)",
        )
        submitted = st.form_submit_button("Agree departmental contract", type="primary", use_container_width=True)
    if submitted:
        if set_contract(s, contract_department, ambition):
            st.success(f"New {AMBITION[ambition]['label'].lower()} contract agreed with {dept_options[contract_department]['label']}.")
            st.rerun()

    st.divider()
    st.markdown("#### Treasury funding control")
    st.caption(
        f"Available fiscal headroom: £{headroom:.1f}bn. These are exceptional one-off in-year awards, not a second Budget editor. "
        "Approval reduces headroom and increases the deficit; tax rates, departmental Budget percentages and the approved ledger remain unchanged."
    )
    with st.form("delivery_funding_request_form"):
        st.markdown("**Submit a departmental funding bid**")
        req_department = st.selectbox(
            "Requesting department",
            list(dept_options),
            format_func=lambda key: dept_options[key]["label"],
        )
        req_title = st.text_input("Programme or intervention")
        req_amount = st.number_input(
            "Amount requested (£bn)",
            min_value=0.1,
            max_value=MAX_REQUEST_BN,
            value=0.5,
            step=0.1,
        )
        req_rationale = st.text_area(
            "Why is additional funding required?",
            placeholder="Explain the delivery problem, what the money will pay for and what result it should achieve.",
            max_chars=500,
        )
        request_submitted = st.form_submit_button("Submit to the Treasury", use_container_width=True)
    if request_submitted:
        request_id, error = create_funding_request(s, req_department, req_title, req_rationale, req_amount)
        if error:
            st.error(error)
        else:
            st.success(f"Funding bid {request_id} submitted for Treasury review.")
            st.rerun()

    st.markdown(f"**Requests awaiting a decision · {len(pending)}**")
    if pending:
        for request in pending:
            with st.expander(
                f"{request['department_label']} · {request['title']} · £{float(request['requested_bn']):.1f}bn",
                expanded=True,
            ):
                st.caption(
                    f"{request['minister']} · {request['period']} · "
                    f"Requested £{float(request['requested_bn']):.1f}bn"
                )
                st.write(request["rationale"])
                max_award = min(float(request["requested_bn"]), max(0.0, float(s.get("headroom", 0.0))))
                if max_award >= 0.1:
                    award = st.number_input(
                        "Approved amount (£bn)",
                        min_value=0.1,
                        max_value=round(max_award, 2),
                        value=round(max_award, 2),
                        step=0.1,
                        key=f"delivery_award_{request['id']}",
                    )
                    left, right = st.columns(2)
                    with left:
                        if st.button("Approve award", key=f"delivery_approve_{request['id']}", type="primary", use_container_width=True):
                            ok, error = decide_funding_request(s, request["id"], "approve", award)
                            if ok:
                                st.success("Funding approved and charged against fiscal headroom.")
                                st.rerun()
                            else:
                                st.error(error)
                    with right:
                        if st.button("Reject bid", key=f"delivery_reject_{request['id']}", use_container_width=True):
                            decide_funding_request(s, request["id"], "reject")
                            st.rerun()
                else:
                    st.warning("There is insufficient positive headroom to approve even a £0.1bn award.")
                    if st.button("Reject bid", key=f"delivery_reject_{request['id']}", use_container_width=True):
                        decide_funding_request(s, request["id"], "reject")
                        st.rerun()
    else:
        st.info("No departmental funding bids are awaiting a decision.")

    decided = [item for item in requests if item.get("status") != "Pending"]
    if decided:
        with st.expander(f"Funding decision register · {len(decided)}", expanded=False):
            import pandas as pd
            display = [{
                "Period": item.get("period", ""),
                "Department": item.get("department_label", ""),
                "Request": item.get("title", ""),
                "Requested (£bn)": item.get("requested_bn", 0.0),
                "Approved (£bn)": item.get("approved_bn", 0.0),
                "Decision": item.get("status", ""),
                "Fiscal effect": item.get("fiscal_effect", "No spending approved"),
            } for item in reversed(decided[-20:])]
            st.dataframe(pd.DataFrame(display), hide_index=True, use_container_width=True)

    st.divider()
    st.markdown("#### Treasury advisory team")
    for adviser, note in _adviser_notes(s, len(pending), len(deliveries)):
        with st.expander(adviser, expanded=False):
            st.write(note)

    st.divider()
    st.markdown("#### Major policy implementation")
    if deliveries:
        import pandas as pd
        display = [{
            "Programme": item.get("title", "Approved policy"),
            "Department": dept_options.get(item.get("department"), {}).get("label", str(item.get("department", "other")).title()),
            "Lead minister": item.get("minister", "Departmental team"),
            "Progress": round(float(item.get("progress", 0.0))),
            "Stage": item.get("status", "Mobilising"),
            "Next milestone": _next_milestone(item)[0],
            "Target": _next_milestone(item)[1],
            "Years in delivery": int(item.get("years_in_delivery", 0)),
            "Funding award (£bn)": round(float(item.get("funding_award_bn", 0.0)), 2),
        } for item in deliveries[-30:]]
        st.dataframe(
            display[::-1],
            hide_index=True,
            use_container_width=True,
            column_config={"Progress": st.column_config.ProgressColumn("Progress", min_value=0, max_value=100, format="%d%%")},
        )
    else:
        st.info("Approved policies will appear here as they move from authorisation into departmental implementation.")

    if history:
        with st.expander("Annual delivery contract reviews", expanded=False):
            for review in reversed(history[-5:]):
                st.markdown(
                    f"**Term {review.get('term', 1)}, Year {review.get('year', 1)}** · "
                    f"{review.get('met', 0)} met · {review.get('partly_met', 0)} partly met · {review.get('missed', 0)} missed"
                )
                st.caption(
                    " · ".join(
                        f"{row.get('department_label', row.get('department', 'Department'))}: "
                        f"{row.get('actual_score', 0):.1f}/{row.get('target_score', 0):.1f} ({row.get('outcome', '')})"
                        for row in review.get("reviews", [])
                    )
                )
