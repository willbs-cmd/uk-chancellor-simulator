"""Dynamic weekly political and economic events for the Chancellor Simulator.

Events are deliberately separate from major COBRA crises: they create recurring
pressure, offer trade-offs, and can compound with the wider economic situation.
"""
import random

EVENTS = [
    {
        "id": "boe_dispute", "category": "Bank of England", "title": "The Governor challenges the Treasury",
        "text": "The Bank of England Governor has publicly questioned the Government's economic strategy, warning that political pressure for lower interest rates could undermine confidence in the Bank's independence.",
        "options": [
            ("Defend the Bank's independence", {"market_conf": 2, "approval": -0.5, "inflation": -0.05, "pm_opinion": -1}, "Markets welcome the constitutional restraint, but ministers complain."),
            ("Demand a public explanation", {"media_opinion": 1, "pm_opinion": 1, "market_conf": -2, "gilt_yield": 0.08}, "The confrontation attracts headlines and unsettles investors."),
            ("Privately agree a policy reset", {"growth": 0.05, "market_conf": -1, "cab_opinion": 1}, "Tensions ease, although questions remain about political interference."),
        ],
    },
    {
        "id": "tax_shortfall", "category": "Treasury receipts", "title": "Tax receipts miss the forecast",
        "text": "HMRC's latest figures show income tax, VAT and corporation tax receipts below the Treasury forecast. The shortfall is beginning to eat into your fiscal headroom.",
        "options": [
            ("Accept the £2.5B shortfall", {"headroom": -2.5, "deficit": 2.5, "approval": 0.2}, "You absorb the revenue miss and avoid immediate tax changes."),
            ("Bring forward compliance action", {"headroom": -0.8, "deficit": 0.8, "growth": -0.05, "media_opinion": 1}, "A targeted crackdown recovers some revenue, but takes time and administrative effort."),
            ("Prepare a targeted tax rise", {"headroom": 1.5, "approval": -1.5, "party_opinion": -1, "growth": -0.08}, "The markets like the extra revenue, while voters and MPs dislike the prospect of higher taxes."),
        ],
    },
    {
        "id": "nhs_strike", "category": "Public services", "title": "NHS unions announce strike action",
        "text": "Health unions have announced a 48-hour walkout over pay and staffing. Hospitals warn that waiting lists will rise unless a settlement is reached.",
        "options": [
            ("Make a funded pay offer", {"headroom": -2, "deficit": 2, "approval": 1.5, "cab_opinion": 1}, "The offer averts the worst disruption, but adds to departmental spending."),
            ("Open intensive negotiations", {"headroom": -0.5, "approval": 0.4, "cab_opinion": 0.5}, "Talks begin and the union pauses escalation, for now."),
            ("Hold the line on pay", {"approval": -2, "backbench_opinion": 1, "growth": -0.05}, "You protect the spending envelope, but disruption continues and public anger grows."),
        ],
    },
    {
        "id": "teacher_strike", "category": "Public services", "title": "Teachers vote for industrial action",
        "text": "Teaching unions have voted for strike action, citing pay, workload and recruitment. School leaders warn of further disruption to pupils and parents.",
        "options": [
            ("Fund a revised settlement", {"headroom": -1.5, "deficit": 1.5, "approval": 1, "cab_opinion": 0.5}, "A settlement reduces disruption but adds pressure to the public pay bill."),
            ("Offer workload concessions", {"headroom": -0.4, "approval": 0.5, "growth": 0.05}, "A non-pay package buys time, though unions remain cautious."),
            ("Refuse additional concessions", {"approval": -1.5, "media_opinion": -1, "headroom": 0.2}, "The Treasury holds its line while the dispute escalates."),
        ],
    },
    {
        "id": "global_credit_crunch", "category": "International markets", "title": "Overseas banking shock rattles markets",
        "text": "A major overseas lender has collapsed. Global banks are tightening credit, gilt investors are demanding a little more compensation for risk and exporters fear a downturn.",
        "options": [
            ("Coordinate with international partners", {"market_conf": 1, "growth": -0.12, "gilt_yield": 0.05, "media_opinion": 0.5}, "Coordination reassures markets, but the external shock still weighs on growth."),
            ("Announce a domestic stability package", {"headroom": -1.8, "deficit": 1.8, "market_conf": 1.5, "approval": 0.5}, "A limited backstop calms nerves at a fiscal cost."),
            ("Wait for the Bank and regulators", {"market_conf": -1.5, "growth": -0.18, "gilt_yield": 0.12}, "You avoid committing public money, but uncertainty persists."),
        ],
    },
    {
        "id": "energy_spike", "category": "International markets", "title": "A fresh international energy shock",
        "text": "Conflict and disruption abroad have pushed wholesale energy prices sharply higher. Businesses warn of rising costs and households fear another squeeze on living standards.",
        "options": [
            ("Target support at vulnerable households", {"headroom": -2, "deficit": 2, "approval": 1.5, "inflation": -0.05}, "Targeted help cushions the blow without a universal subsidy."),
            ("Back a temporary business relief scheme", {"headroom": -1.5, "deficit": 1.5, "growth": 0.08, "market_conf": -0.3}, "Some firms get breathing space, but the package costs money."),
            ("Avoid a new subsidy", {"headroom": 0.3, "approval": -1.5, "inflation": 0.15, "growth": -0.1}, "You protect the public finances while the price shock feeds through."),
        ],
    },
    {
        "id": "business_lobby", "category": "Business pressure", "title": "Business groups demand a growth package",
        "text": "The CBI and several sector groups are pressing for investment allowances, lower business taxes and faster planning decisions. They warn that investment is being delayed.",
        "options": [
            ("Offer targeted investment allowances", {"headroom": -1.2, "growth": 0.18, "market_conf": 0.5, "business_confidence": 1}, "A targeted incentive may lift investment, but reduces near-term receipts."),
            ("Convene a business and union summit", {"approval": 0.4, "cab_opinion": 0.5, "growth": 0.05, "media_opinion": 0.5}, "You bring employers and workers together, buying time for a broader deal."),
            ("Reject the lobbying campaign", {"headroom": 0.4, "business_confidence": -2, "growth": -0.08}, "You resist special treatment, but firms warn that investment may move elsewhere."),
        ],
    },
    {
        "id": "union_pay_pressure", "category": "Union pressure", "title": "Unions coordinate a public-sector pay campaign",
        "text": "A coalition of public-sector unions is preparing coordinated demonstrations and ballot campaigns. They say pay has fallen behind living costs.",
        "options": [
            ("Start talks on a multi-year deal", {"headroom": -0.8, "deficit": 0.8, "cab_opinion": 1, "approval": 0.6}, "A framework for talks lowers tensions, but creates future spending commitments."),
            ("Offer a one-off non-consolidated payment", {"headroom": -1.1, "deficit": 1.1, "approval": 0.8}, "A one-off payment eases immediate pressure without permanently raising salaries."),
            ("Ask departments to absorb the pressure", {"headroom": 0.2, "approval": -1, "cab_opinion": -1}, "The Treasury avoids new money, leaving ministers to manage the fallout."),
        ],
    },
    {
        "id": "cost_of_living_protest", "category": "Public pressure", "title": "Cost-of-living protests spread",
        "text": "Large demonstrations have taken place in several cities over rents, food prices and household bills. Opposition parties are demanding an urgent response.",
        "options": [
            ("Expand targeted household support", {"headroom": -1.5, "deficit": 1.5, "approval": 1.5, "inflation": -0.03}, "Support is focused on households under the greatest pressure."),
            ("Announce a cost-of-living review", {"approval": 0.3, "media_opinion": 0.5, "pm_opinion": 0.3}, "The review gives the Government time, but protesters want immediate action."),
            ("Argue that the economy is turning a corner", {"approval": -1.8, "media_opinion": -1.5, "party_opinion": 0.3}, "Your message is seen as out of touch by many demonstrators."),
        ],
    },
    {
        "id": "retail_tax_warning", "category": "Treasury receipts", "title": "Retail slowdown threatens VAT receipts",
        "text": "Retail sales have weakened unexpectedly. The Treasury's VAT forecast is now at risk, while retailers warn that consumer confidence is fragile.",
        "options": [
            ("Bring forward high-street investment", {"headroom": -1, "deficit": 1, "growth": 0.12, "approval": 0.5}, "A modest investment package supports town centres, at a cost to headroom."),
            ("Ask the OBR for a revised forecast", {"market_conf": 0.4, "media_opinion": 0.3, "headroom": -0.4}, "You acknowledge the numbers and prepare a more credible forecast."),
            ("Wait for next month's figures", {"growth": -0.08, "headroom": -1.2, "deficit": 1.2}, "You avoid premature action, but the weakness may deepen."),
        ],
    },
    {
        "id": "gilt_auction", "category": "Financial markets", "title": "A difficult gilt auction",
        "text": "Demand at the latest gilt auction is weaker than expected. The Debt Management Office warns that borrowing could become more expensive if confidence deteriorates.",
        "options": [
            ("Reaffirm the fiscal rules", {"market_conf": 1.5, "gilt_yield": -0.06, "pm_opinion": 0.5, "approval": -0.2}, "A credible statement steadies investors, although it limits room for manoeuvre."),
            ("Bring forward a borrowing review", {"market_conf": 0.5, "headroom": -0.3, "media_opinion": 0.3}, "You commission a review and avoid a dramatic intervention."),
            ("Criticise market speculation", {"market_conf": -2, "gilt_yield": 0.12, "media_opinion": -0.5}, "The rhetoric plays well with some MPs but does little to reassure bond buyers."),
        ],
    },
    {
        "id": "manufacturing_jobs", "category": "Business and unions", "title": "Major manufacturer threatens job cuts",
        "text": "A major manufacturer says high energy costs and weak demand may force it to close a UK site. Unions are demanding guarantees for workers.",
        "options": [
            ("Broker a worker and employer agreement", {"headroom": -0.8, "growth": 0.1, "approval": 0.7, "cab_opinion": 0.5}, "A negotiated plan may preserve jobs and retraining opportunities."),
            ("Offer a temporary investment incentive", {"headroom": -1.3, "deficit": 1.3, "growth": 0.15, "market_conf": -0.2}, "The company gets an incentive, but there is no guarantee the site will stay open."),
            ("Decline company-specific support", {"headroom": 0.2, "approval": -0.7, "growth": -0.12, "media_opinion": -0.5}, "You avoid a selective bailout, but redundancies remain possible."),
        ],
    },
    {
        "id": "council_funding_row", "category": "Local government", "title": "Council leaders warn of emergency service cuts",
        "text": "Council leaders from several regions say rising adult social-care, homelessness and temporary-accommodation costs are pushing local services towards insolvency. They want the Treasury to agree a rescue package.",
        "options": [
            ("Offer a targeted, conditional recovery grant", {"headroom": -1.8, "deficit": 1.8, "approval": 1.0, "cab_opinion": 0.5}, "Councils receive help in return for credible recovery plans and stronger financial oversight."),
            ("Allow councils more tax-raising flexibility", {"headroom": 0.4, "approval": -0.8, "party_opinion": -0.5}, "Local leaders welcome greater discretion, but households face the prospect of higher bills."),
            ("Require councils to absorb the shortfall", {"headroom": 0.5, "approval": -1.8, "cab_opinion": -1.0}, "The Treasury protects its settlement, but council leaders warn that visible service failures are now likely."),
        ],
    },
    {
        "id": "mortgage_reset_wave", "category": "Households", "title": "A wave of mortgage deals comes up for renewal",
        "text": "Millions of households are approaching the end of fixed-rate mortgage deals. Lenders report a sharp rise in refinancing costs, while MPs warn that repossessions and rent arrears could follow.",
        "options": [
            ("Expand targeted debt advice and hardship support", {"headroom": -1.0, "deficit": 1.0, "approval": 1.2, "household_confidence": 1.5}, "Targeted help gives the most exposed households time to adjust without subsidising every mortgage."),
            ("Bring forward planning and housing-supply reforms", {"headroom": -0.5, "growth": 0.1, "approval": 0.4}, "The Government focuses on long-term supply, though it offers little immediate relief to borrowers."),
            ("Leave the response to lenders and the Bank", {"approval": -1.6, "media_opinion": -0.8, "household_confidence": -1.5}, "You avoid a taxpayer-backed intervention, but household pressure continues to build."),
        ],
    },
    {
        "id": "water_company_failure", "category": "Infrastructure and regulation", "title": "A major water company faces financial collapse",
        "text": "A heavily indebted water company says it cannot meet its investment and environmental obligations. Regulators warn that service interruptions and pollution incidents could worsen without a credible plan.",
        "options": [
            ("Require shareholders to fund a restructuring", {"market_conf": 0.8, "approval": 0.6, "growth": 0.02}, "Investors are told that owners, rather than taxpayers, must carry the first losses."),
            ("Create a temporary public-interest administration", {"headroom": -1.2, "deficit": 1.2, "approval": 0.5, "market_conf": -0.2}, "Essential services are protected while the regulator oversees a longer-term rescue."),
            ("Allow the company to continue without intervention", {"approval": -1.8, "media_opinion": -1.0, "market_conf": -0.5}, "The Government avoids a rescue, but the regulator warns that failure could spread to customers and suppliers."),
        ],
    },
    {
        "id": "university_funding_row", "category": "Education and skills", "title": "Universities warn of a funding cliff-edge",
        "text": "Several universities report deep deficits after years of rising costs and weak international recruitment. They warn of course closures, job losses and reduced research capacity.",
        "options": [
            ("Fund a targeted research and skills compact", {"headroom": -1.1, "deficit": 1.1, "growth": 0.12, "approval": 0.5}, "Public support is tied to research partnerships, technical skills and regional access."),
            ("Reform the funding model before adding money", {"headroom": -0.2, "market_conf": 0.3, "growth": 0.04, "cab_opinion": -0.2}, "A review begins, but institutions warn that some decisions cannot wait."),
            ("Allow institutions to consolidate or close courses", {"headroom": 0.3, "approval": -1.2, "growth": -0.08, "media_opinion": -0.5}, "The Treasury avoids new spending while local employers fear losing skilled graduates."),
        ],
    },
    {
        "id": "defence_procurement_delay", "category": "Defence and industry", "title": "A flagship defence programme runs years late",
        "text": "The National Audit Office reports that a major equipment programme is over budget and several delivery milestones have slipped. Defence chiefs want certainty, while the Treasury demands accountability.",
        "options": [
            ("Commission an independent cost and delivery review", {"headroom": -0.2, "market_conf": 0.5, "cab_opinion": 0.4}, "The review may expose waste and reset the timetable, but it delays a final decision."),
            ("Protect the programme and pay to accelerate delivery", {"headroom": -1.6, "deficit": 1.6, "approval": 0.4}, "The contractor receives additional funding against strict milestones and penalties."),
            ("Pause the programme and renegotiate the contract", {"headroom": 0.8, "approval": -0.8, "growth": -0.04, "cab_opinion": -0.5}, "The Treasury regains leverage, but defence capability and suppliers face uncertainty."),
        ],
    },
    {
        "id": "export_contract_opportunity", "category": "Trade and industry", "title": "British firms secure a major overseas contract opportunity",
        "text": "A group of British engineering, technology and advanced-manufacturing firms has been shortlisted for a substantial overseas infrastructure contract. They are asking the Government to help coordinate export finance and trade diplomacy.",
        "options": [
            ("Coordinate export finance and trade support", {"headroom": -0.4, "growth": 0.16, "business_confidence": 1.0, "market_conf": 0.3}, "A coordinated offer improves the firms' chances and could support skilled jobs."),
            ("Bring the firms together with universities and suppliers", {"headroom": -0.2, "growth": 0.1, "approval": 0.4}, "The Government focuses on domestic supply chains and long-term capability."),
            ("Keep government at arm's length", {"headroom": 0.1, "growth": -0.04, "business_confidence": -0.5}, "The firms compete without additional public backing, avoiding the risk of picking winners."),
        ],
    },
    {
        "id": "farm_income_squeeze", "category": "Rural economy", "title": "Farmers warn that rising costs threaten food production",
        "text": "Farm groups report pressure from fertiliser, fuel and labour costs. Smaller farms say delayed payments and uncertain trade conditions are threatening investment ahead of the next growing season.",
        "options": [
            ("Bring forward targeted resilience payments", {"headroom": -0.9, "deficit": 0.9, "approval": 0.5, "growth": 0.04}, "Support is focused on smaller producers and improvements to productivity and resilience."),
            ("Simplify farm regulation and payment administration", {"headroom": -0.2, "growth": 0.06, "market_conf": 0.2}, "The administrative burden is reduced, although the immediate cash squeeze remains."),
            ("Hold the existing settlement", {"headroom": 0.2, "approval": -1.0, "media_opinion": -0.5}, "The Treasury avoids new spending, but rural MPs warn of further closures."),
        ],
    },
    {
        "id": "civil_service_leak", "category": "Government and Whitehall", "title": "A leaked Treasury paper undermines the Government's message",
        "text": "A confidential Treasury assessment appears in the newspapers, questioning whether several flagship policies can be delivered on time. The Prime Minister wants to know who authorised the analysis.",
        "options": [
            ("Publish the assessment and explain the risks", {"media_opinion": 0.8, "market_conf": 0.8, "pm_opinion": -0.5, "officials_confidence": 1.0}, "Transparency reassures some observers, although Number 10 dislikes the loss of message discipline."),
            ("Commission a rapid independent delivery review", {"headroom": -0.2, "approval": 0.3, "officials_confidence": 0.5}, "An independent review separates genuine delivery risks from internal disagreements."),
            ("Dispute the paper and discipline the officials", {"pm_opinion": 1.0, "officials_confidence": -2.0, "market_conf": -0.8}, "The Government appears united, but civil servants become more cautious about speaking frankly."),
        ],
    },
    {
        "id": "care_provider_failure", "category": "Social care", "title": "A large care provider threatens to hand back contracts",
        "text": "A major social-care provider says it can no longer deliver several local authority contracts at current prices. Councils warn that vulnerable residents could be left without reliable support.",
        "options": [
            ("Agree a short-term stability payment with safeguards", {"headroom": -1.0, "deficit": 1.0, "approval": 0.8, "cab_opinion": 0.5}, "A temporary settlement protects continuity while councils review commissioning arrangements."),
            ("Help councils bring services in-house or retender", {"headroom": -0.5, "growth": -0.02, "approval": 0.3}, "Local authorities receive help to arrange new provision, but disruption is likely."),
            ("Refuse extra support and let contracts end", {"headroom": 0.2, "approval": -1.8, "media_opinion": -0.8}, "The Treasury avoids a bailout, but councils warn of immediate gaps in care."),
        ],
    },
    {
        "id": "pension_fund_warning", "category": "Financial markets", "title": "Pension funds warn about long-term gilt-market volatility",
        "text": "Large pension schemes warn that volatile bond markets and changing collateral requirements are making long-term planning difficult. The Debt Management Office is asked to consider whether issuance patterns are adding to pressure.",
        "options": [
            ("Convene a joint DMO, regulator and pension-fund review", {"market_conf": 0.6, "gilt_yield": -0.03, "officials_confidence": 0.5}, "A coordinated review improves information-sharing without promising a bailout."),
            ("Adjust the gilt issuance programme", {"headroom": -0.1, "market_conf": 0.8, "gilt_yield": -0.05}, "The DMO changes the maturity mix to improve demand, accepting some refinancing trade-offs."),
            ("Leave issuance unchanged and explain the risks", {"market_conf": -0.8, "gilt_yield": 0.06, "approval": 0.1}, "The Treasury avoids reacting to short-term volatility, but investors remain watchful."),
        ],
    },
]

def _context_weight(event_id, context):
    """Give events a higher draw weight when their subject matches current pressures."""
    c = context or {}
    weight = 1.0
    if event_id in ("tax_shortfall", "retail_tax_warning") and float(c.get("headroom", 8.0)) < 4:
        weight += 1.3
    if event_id in ("boe_dispute", "energy_spike", "mortgage_reset_wave") and float(c.get("inflation", 2.0)) > 4:
        weight += 1.2
    if event_id in ("nhs_strike", "care_provider_failure") and float(c.get("nhs_waiting", 0.0)) > 0.5:
        weight += 1.2
    if event_id == "teacher_strike" and float(c.get("schools", 60.0)) < 55:
        weight += 1.2
    if event_id == "council_funding_row" and float(c.get("local_finance_pressure", 40.0)) > 60:
        weight += 1.8
    if event_id in ("mortgage_reset_wave", "cost_of_living_protest") and (
        float(c.get("mortgage_pressure", 45.0)) > 60 or float(c.get("household_bill_pressure", 45.0)) > 65
    ):
        weight += 1.4
    if event_id in ("business_lobby", "manufacturing_jobs") and (
        float(c.get("growth", 1.0)) < 0 or float(c.get("business_confidence", 50.0)) < 40
    ):
        weight += 1.2
    if event_id == "global_credit_crunch" and float(c.get("world_cycle", 0.0)) < -1:
        weight += 1.5
    if event_id == "water_company_failure" and float(c.get("local_finance_pressure", 40.0)) > 65:
        weight += 0.7
    if event_id == "pension_fund_warning" and float(c.get("debt", 80.0)) > 100:
        weight += 0.8
    if event_id == "export_contract_opportunity" and float(c.get("growth", 1.0)) > 1.2:
        weight += 0.5
    return weight


def context_from_state(s):
    """Extract only the live figures used to make weekly event selection feel situational."""
    country = s.get("country", {}) if isinstance(s.get("country", {}), dict) else {}
    return {
        "headroom": float(s.get("headroom", 8.0)),
        "inflation": float(s.get("inflation", 2.0)),
        "growth": float(s.get("growth", 1.0)),
        "debt": float(s.get("debt", 80.0)),
        "mortgage_pressure": float(s.get("mortgage_pressure", 45.0)),
        "household_bill_pressure": float(s.get("household_bill_pressure", 45.0)),
        "local_finance_pressure": float(s.get("local_finance_pressure", 40.0)),
        "nhs_waiting": float(country.get("nhs_waiting", 0.0)),
        "schools": float(country.get("schools", 60.0)),
        "business_confidence": float(country.get("business_confidence", 50.0)),
        "world_cycle": float(s.get("world_cycle", 0.0)),
    }


def pick(seed, steps, previous=None, chance=0.42, recent=None, context=None):
    """Draw an event without repeating recent briefings; favour issues visible in the current economy."""
    rng = random.Random(f"{seed}:{steps}:weekly-event")
    if rng.random() >= chance:
        return None

    recent_ids = list(recent or [])
    if previous:
        recent_ids.append(previous)
    blocked = set(recent_ids[-7:])
    pool = [event for event in EVENTS if event["id"] not in blocked]
    if not pool:
        # The event deck has been exhausted: start another cycle, but avoid the last card.
        pool = [event for event in EVENTS if event["id"] != (recent_ids[-1] if recent_ids else None)]
    if not pool:
        pool = list(EVENTS)

    recent_categories = {
        next((event["category"] for event in EVENTS if event["id"] == event_id), None)
        for event_id in recent_ids[-2:]
    }
    weights = []
    for event in pool:
        weight = _context_weight(event["id"], context)
        if event["category"] in recent_categories:
            weight *= 0.35
        weights.append(max(0.05, weight))
    chosen = rng.choices(pool, weights=weights, k=1)[0]
    return dict(chosen)
