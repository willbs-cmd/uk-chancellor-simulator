"""National investment portfolio: multi-year capital projects and delivery risks.

All commitments are explicit fiscal flows. Approved Budget tax/spending ledgers are
not rewritten; annual project costs enter the in-year fiscal position when delivered.
"""
import random
import streamlit as st

PROJECTS = {
    "housing": {"label": "Affordable homes and new towns", "sector": "Housing", "cost": 18.0, "years": 4, "gain": 1.15, "jobs": 85000, "region": 1.8, "description": "Expand housing supply, enabling infrastructure and serviced land."},
    "rail": {"label": "Rail and regional connectivity", "sector": "Transport", "cost": 26.0, "years": 5, "gain": 1.55, "jobs": 72000, "region": 2.2, "description": "Upgrade rail capacity, stations, freight links and regional connections."},
    "energy": {"label": "National clean energy and grid", "sector": "Energy", "cost": 32.0, "years": 5, "gain": 1.75, "jobs": 94000, "region": 1.4, "description": "Expand grid capacity, storage and low-carbon generation connections."},
    "science": {"label": "Science and advanced manufacturing", "sector": "Industry", "cost": 14.0, "years": 4, "gain": 1.9, "jobs": 51000, "region": 1.1, "description": "Support research facilities, industrial clusters and commercialisation."},
    "skills": {"label": "Technical skills and apprenticeships", "sector": "Skills", "cost": 9.0, "years": 3, "gain": 1.35, "jobs": 38000, "region": 1.0, "description": "Expand technical colleges, apprenticeships and employer-led training."},
    "hospitals": {"label": "Hospital and health infrastructure", "sector": "Public services", "cost": 21.0, "years": 5, "gain": 0.9, "jobs": 64000, "region": 0.9, "description": "Modernise hospitals, diagnostic facilities and community health estates."},
}
FINANCE = {
    "Public capital": {"public_share": 1.0, "label": "Government-funded capital spending"},
    "Infrastructure bonds": {"public_share": 1.0, "label": "Government borrowing through long-term infrastructure bonds"},
    "Private partnership": {"public_share": 0.35, "label": "Lower initial public capital, with long-term availability payments"},
}
MAX_ACTIVE = 8


def _period(s):
    return f"{int(s.get('term', 1))}:{int(s.get('year', 1))}"


def ensure(s=None):
    s = s if s is not None else st.session_state
    s.setdefault("national_investment_projects", [])
    s.setdefault("national_investment_history", [])
    s.setdefault("national_investment_sequence", 0)
    s.setdefault("national_investment_last_advance", "")
    s.setdefault("national_investment_spend_total", 0.0)
    s.setdefault("national_investment_productivity_stock", 0.0)
    s.setdefault("national_investment_jobs", 0)
    s["national_investment_projects"] = list(s.get("national_investment_projects", []))[-MAX_ACTIVE:]
    s["national_investment_history"] = list(s.get("national_investment_history", []))[-100:]
    return s


def create_project(s, project_key, finance="Public capital", region="North West"):
    """Approve a project. Annual cash costs and benefits are booked by advance()."""
    ensure(s)
    if project_key not in PROJECTS or finance not in FINANCE:
        return None, "Choose a valid project and financing route."
    active = [p for p in s["national_investment_projects"] if p.get("status") in ("Approved", "Under construction", "Delayed")]
    if len(active) >= MAX_ACTIVE:
        return None, f"The portfolio is limited to {MAX_ACTIVE} active projects."
    if any(p.get("project_key") == project_key and p.get("status") in ("Approved", "Under construction", "Delayed") for p in active):
        return None, "This project is already in the active portfolio."
    spec = PROJECTS[project_key]
    s["national_investment_sequence"] = int(s.get("national_investment_sequence", 0)) + 1
    project_id = f"NIP-{int(s.get('term', 1))}-{int(s.get('year', 1))}-{s['national_investment_sequence']}"
    finance_spec = FINANCE[finance]
    project = {
        "id": project_id, "project_key": project_key, "name": spec["label"], "sector": spec["sector"],
        "region": str(region), "finance": finance, "finance_label": finance_spec["label"],
        "approved_cost_bn": float(spec["cost"]), "public_share": float(finance_spec["public_share"]),
        "duration": int(spec["years"]), "progress": 0.0, "status": "Approved",
        "approved_period": _period(s), "years_elapsed": 0, "delay_years": 0,
        "overrun_bn": 0.0, "annual_cost_bn": round(float(spec["cost"]) * finance_spec["public_share"] / spec["years"], 2),
        "productivity_gain": float(spec["gain"]), "jobs_supported": int(spec["jobs"]),
        "regional_gain": float(spec["region"]), "last_review": None, "history": [],
        "availability_years": 8 if finance == "Private partnership" else 0,
        "availability_paid_years": 0,
    }
    s["national_investment_projects"] = list(s["national_investment_projects"]) + [project]
    s["message"] = f"National investment project approved: {spec['label']}. Annual delivery and fiscal costs begin at the next annual update."
    return project_id, None



REGION_ALIASES = {
    "Yorkshire and the Humber": ["Yorkshire & Humber"],
    "Midlands": ["East Midlands", "West Midlands"],
}


def _apply_regional_impact(s, project, progress_delta):
    """Spread project benefits across the selected region as construction is delivered."""
    if progress_delta <= 0:
        return {}
    import regional_economy
    regional_economy.ensure(s)
    regions = s.get("regional_economies", {})
    targets = REGION_ALIASES.get(project.get("region"), [project.get("region")])
    targets = [name for name in targets if name in regions]
    if not targets:
        return {}
    gain = float(project.get("regional_gain", 1.0))
    jobs_total = int(project.get("jobs_supported", 0))
    delivered_share = min(1.0, progress_delta / 100.0)
    per_region_share = delivered_share / len(targets)
    effects = {}
    for name in targets:
        row = regions[name]
        priority_bonus = 1.15 if name in s.get("regional_strategy_regions", []) and s.get("regional_strategy_active") else 1.0
        productivity = gain * delivered_share * 0.85 * priority_bonus / len(targets)
        investment = gain * delivered_share * 1.20 * priority_bonus / len(targets)
        jobs_index = gain * delivered_share * 0.55 * priority_bonus / len(targets)
        growth = gain * delivered_share * 0.07 * priority_bonus / len(targets)
        row["productivity"] = round(max(70.0, min(145.0, float(row.get("productivity", 100.0)) + productivity)), 2)
        row["investment"] = round(max(20.0, min(100.0, float(row.get("investment", 50.0)) + investment)), 2)
        row["jobs"] = round(max(70.0, min(130.0, float(row.get("jobs", 100.0)) + jobs_index)), 2)
        row["growth"] = round(max(-4.0, min(5.0, float(row.get("growth", 0.8)) + growth)), 2)
        jobs = int(jobs_total * per_region_share)
        row["project_jobs_supported"] = int(row.get("project_jobs_supported", 0)) + jobs
        effects[name] = {
            "productivity": round(productivity, 3), "investment": round(investment, 3),
            "jobs_index": round(jobs_index, 3), "growth": round(growth, 3),
            "jobs_supported": jobs,
        }
    s["regional_economies"] = regions
    return effects


def advance(s):
    """Advance all projects once per in-game year; apply explicit costs and gradual benefits."""
    ensure(s)
    period = _period(s)
    if s.get("national_investment_last_advance") == period:
        return None
    rng = random.Random(int(s.get("seed", 1)) + int(s.get("term", 1)) * 65537 + int(s.get("year", 1)) * 8191)
    records = []
    annual_spend = 0.0
    annual_private_payments = 0.0
    productivity_delta = 0.0
    jobs = 0
    for project in s["national_investment_projects"]:
        status = project.get("status")
        if status in ("Completed", "Cancelled"):
            if status == "Completed" and project.get("availability_paid_years", 0) < project.get("availability_years", 0):
                payment = round(float(project.get("approved_cost_bn", 0.0)) * 0.65 * 0.07, 2)
                annual_private_payments += payment
                project["availability_paid_years"] = int(project.get("availability_paid_years", 0)) + 1
            continue
        before = float(project.get("progress", 0.0))
        spec = PROJECTS.get(project.get("project_key"), {})
        duration = max(1, int(project.get("duration", 1)))
        base_step = 100.0 / duration
        delay = rng.random() < 0.12
        step = base_step * (0.55 if delay else (1.0 + rng.uniform(-0.08, 0.10)))
        after = min(100.0, before + step)
        project["years_elapsed"] = int(project.get("years_elapsed", 0)) + 1
        if delay:
            project["delay_years"] = int(project.get("delay_years", 0)) + 1
            overrun = round(float(project.get("approved_cost_bn", 0.0)) * rng.uniform(0.015, 0.04), 2)
            project["overrun_bn"] = round(float(project.get("overrun_bn", 0.0)) + overrun, 2)
            project["status"] = "Delayed"
        else:
            project["status"] = "Completed" if after >= 99.9 else "Under construction"
        project["progress"] = round(after, 1)
        public_share = float(project.get("public_share", 1.0))
        cost = float(project.get("approved_cost_bn", 0.0)) * public_share / duration
        if delay:
            cost += overrun
        annual_spend += cost
        gain = float(project.get("productivity_gain", spec.get("gain", 0.0)))
        progress_delta = max(0.0, after - before)
        productivity_delta += progress_delta * gain / 1000.0
        jobs += int(float(project.get("jobs_supported", 0)) * min(1.0, after / 100.0) * 0.12)
        regional_effects = _apply_regional_impact(s, project, progress_delta)
        project["last_review"] = {
            "period": period, "progress_before": round(before, 1), "progress_after": round(after, 1),
            "delay": delay, "annual_capital_cost_bn": round(cost, 2),
            "overrun_bn": round(float(project.get("overrun_bn", 0.0)), 2),
            "regional_effects": regional_effects,
        }
        project["history"] = (list(project.get("history", [])) + [dict(project["last_review"])])[-10:]
        records.append({"project": project["name"], **project["last_review"], "status": project["status"]})
    fiscal_cost = round(annual_spend + annual_private_payments, 2)
    if fiscal_cost:
        s["headroom"] = round(float(s.get("headroom", 0.0)) - fiscal_cost, 1)
        s["deficit"] = round(max(0.0, float(s.get("deficit", 0.0)) + fiscal_cost), 1)
        s["national_investment_spend_total"] = round(float(s.get("national_investment_spend_total", 0.0)) + fiscal_cost, 2)
    if productivity_delta:
        growth_lift = min(0.18, productivity_delta)
        s["growth"] = round(float(s.get("growth", 0.0)) + growth_lift, 2)
        s["national_investment_productivity_stock"] = round(float(s.get("national_investment_productivity_stock", 0.0)) + productivity_delta, 3)
    s["national_investment_jobs"] = int(jobs)
    s["national_investment_history"] = (list(s["national_investment_history"]) + [{
        "period": period, "projects_reviewed": len(records), "capital_spend_bn": round(annual_spend, 2),
        "private_availability_bn": round(annual_private_payments, 2), "fiscal_cost_bn": fiscal_cost,
        "productivity_growth_pp": round(productivity_delta, 3), "jobs_supported": jobs, "projects": records,
    }])[-100:]
    s["national_investment_last_advance"] = period
    if records:
        s["message"] = str(s.get("message", "")) + f" National investment delivered £{annual_spend:.2f}bn of capital work; associated financing and availability costs were £{fiscal_cost:.2f}bn. Project progress added {min(0.18, productivity_delta):+.2f}pp to modeled growth."
    return s["national_investment_history"][-1]


def cancel_project(s, project_id):
    ensure(s)
    project = next((p for p in s["national_investment_projects"] if p.get("id") == project_id), None)
    if not project or project.get("status") in ("Completed", "Cancelled"):
        return False
    project["status"] = "Cancelled"
    project["cancelled_period"] = _period(s)
    project["cancellation_note"] = "Future capital allocations stop; costs already incurred remain in the fiscal record."
    return True


def render(s=None):
    s = ensure(s)
    st.markdown("### National Investment Portfolio")
    st.caption("Commission long-term projects, choose their financing and monitor delivery. Figures are illustrative gameplay estimates, not official project appraisals.")
    projects = list(s.get("national_investment_projects", []))
    active = [p for p in projects if p.get("status") in ("Approved", "Under construction", "Delayed")]
    completed = [p for p in projects if p.get("status") == "Completed"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Active projects", len(active))
    c2.metric("Completed", len(completed))
    c3.metric("Capital & finance spent", f"£{float(s.get('national_investment_spend_total', 0.0)):.1f}bn")
    c4.metric("Jobs supported", f"{int(s.get('national_investment_jobs', 0)):,}")
    st.divider()
    with st.expander("Commission a national project", expanded=not bool(active)):
        available = [key for key in PROJECTS if not any(p.get("project_key") == key and p.get("status") in ("Approved", "Under construction", "Delayed") for p in projects)]
        if not available:
            st.info("All six project types are already represented in the active portfolio.")
        else:
            key = st.selectbox("Investment programme", available, format_func=lambda k: PROJECTS[k]["label"], key="nip_project")
            spec = PROJECTS[key]
            st.write(spec["description"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Estimated capital cost", f"£{spec['cost']:.1f}bn")
            c2.metric("Delivery period", f"{spec['years']} years")
            c3.metric("Productivity potential", f"{spec['gain']:.2f}")
            finance = st.selectbox("Financing route", list(FINANCE), key="nip_finance")
            region = st.selectbox("Primary region", ["North East", "North West", "Yorkshire and the Humber", "Midlands", "East of England", "London", "South East", "South West", "Scotland", "Wales", "Northern Ireland"], key="nip_region")
            st.caption(FINANCE[finance]["label"] + (". Long-term availability payments apply after completion." if finance == "Private partnership" else "."))
            if st.button("Approve national investment project", type="primary", use_container_width=True, disabled=len(active) >= MAX_ACTIVE):
                project_id, error = create_project(s, key, finance, region)
                if error:
                    st.error(error)
                else:
                    st.success(f"{project_id} approved. First annual delivery and costs are recognised at the next spring update.")
                    st.rerun()
    st.markdown("#### Active portfolio")
    if active:
        for project in active:
            with st.container(border=True):
                c1, c2, c3 = st.columns([2.2, 1, 1])
                with c1:
                    st.markdown(f"**{project['name']}**")
                    st.caption(f"{project['sector']} · {project['region']} · {project['finance']}")
                with c2:
                    st.metric("Progress", f"{float(project.get('progress', 0)):.0f}%")
                with c3:
                    st.metric("Estimated cost", f"£{float(project.get('approved_cost_bn', 0)) + float(project.get('overrun_bn', 0)):.1f}bn")
                st.progress(min(1.0, max(0.0, float(project.get("progress", 0)) / 100.0)))
                st.caption(f"Expected duration {project['duration']} years · {project.get('delay_years', 0)} delay year(s) · £{float(project.get('annual_cost_bn', 0)):.2f}bn annual public capital before overruns.")
                if st.button("Cancel future work", key=f"nip_cancel_{project['id']}"):
                    cancel_project(s, project["id"])
                    st.warning("Future allocations stopped. Costs already incurred remain recorded.")
                    st.rerun()
    else:
        st.info("No active projects. Commission a national investment programme above.")
    if completed:
        with st.expander("Completed projects"):
            for project in completed:
                st.write(f"**{project['name']}** — {project['region']} · £{float(project['approved_cost_bn']) + float(project.get('overrun_bn', 0)):.1f}bn total approved/overrun cost.")
    with st.expander("Annual investment record", expanded=False):
        history = s.get("national_investment_history", [])
        if history:
            rows = [{k: v for k, v in row.items() if k != "projects"} for row in history]
            st.dataframe(rows, hide_index=True, use_container_width=True)
        else:
            st.caption("The first annual investment review appears after the next spring update.")
    st.caption("Public capital spending and private-partnership availability payments reduce fiscal headroom and increase the deficit when incurred. Infrastructure bonds are still public borrowing; they do not make a project free. Productivity effects build gradually as work is delivered.")
