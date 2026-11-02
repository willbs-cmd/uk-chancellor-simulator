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
]

def pick(seed, steps, previous=None, chance=0.42):
    """Return one event or None. Seeded by the caller so saved games replay consistently."""
    rng = random.Random(f"{seed}:{steps}:weekly-event")
    if rng.random() >= chance:
        return None
    pool = [event for event in EVENTS if event["id"] != previous]
    return dict(rng.choice(pool))
