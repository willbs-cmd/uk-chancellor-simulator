import random

BLOCKS_PER_YEAR = 3   
BUDGET_BLOCK = 3
IDEOLOGIES = ['Hard Left', 'Social Democratic', 'Centric', 'Free-Market', 'Fiscal Austerity']

# --- Term 1 Narrative Arc ---
DECISIONS = {
    (1, 1): dict(
        title='The First Hundred Days',
        text='Your new government must make its first major legislative mark on the country.',
        humphrey="Welcome to the Treasury, Chancellor. The press are demanding a 'bold new vision'. I strongly advise against having one. Visions are expensive, and usually end in tears.",
        options=[
            '1. (Hard Left) Announce immediate nationalisation of key utilities and rail.',
            '2. (Social Democratic) Launch a massive state-funded green jobs guarantee.',
            '3. (Centric) Announce targeted, fully-costed infrastructure upgrades.',
            '4. (Free-Market) Immediately scrap EU-era employment regulations.',
            '5. (Fiscal Austerity) Announce an emergency freeze on all public sector hiring.',
        ],
        effects=[
            dict(headroom=-8.5, approval=6, market_conf=-18, gilt_yield=0.5, energy_bills=-200, rail=10, message='Nationalisation rattles the markets!'),
            dict(headroom=-5.0, approval=7, deficit=1.2, growth=0.2, unemployment=-0.3, netzero=5, message='Green jobs guarantee launched.'),
            dict(headroom=-2.5, approval=3, homes_built=15, rail=5, message='Pragmatic infrastructure pledged.'),
            dict(market_conf=10, approval=-6, growth=0.3, real_wages=-0.3, unemployment=-0.2, message='Employment regulations scrapped.'),
            dict(headroom=4.0, approval=-10, deficit=-0.7, nhs_morale=-10, schools=-5, message='Public sector hiring frozen.'),
        ],
    ),
    (1, 2): dict(
        title='Public Sector Pay Dispute',
        text='Public sector unions are threatening widespread winter strikes over pay freezes.',
        humphrey="The unions are threatening to bring the country to a standstill, Chancellor. A completely unforeseen consequence of not paying them enough, apparently. Shall we set up an interdepartmental committee?",
        options=[
            '1. (Hard Left) Meet all union pay demands in full, funded by borrowing.',
            '2. (Social Democratic) Negotiate a generous inflation-matching pay rise.',
            '3. (Centric) Offer a balanced compromise settlement.',
            '4. (Free-Market) De-unionize public sectors and introduce private contractors.',
            '5. (Fiscal Austerity) Enforce a strict statutory pay cap and invoke anti-strike laws.',
        ],
        effects=[
            dict(headroom=-8.0, approval=10, deficit=1.4, inflation=0.4, nhs_morale=15, message='Unions appeased, but inflation ticks upward.'),
            dict(headroom=-4.5, approval=6, nhs_morale=5, message='Fair pay settlement reached.'),
            dict(approval=-4, nhs_morale=0, message='Compromise struck with minor disruption.'),
            dict(market_conf=9, approval=-10, nhs_morale=-15, message='Private contracting introduced.'),
            dict(approval=-14, market_conf=10, inflation=-0.3, nhs_morale=-20, message='Pay cap enforced. Markets pleased, workforce furious.'),
        ],
    ),
    (2, 1): dict(
        title='Welfare & Long-Term Sickness Reform',
        text='Welfare expenditure is spiraling out of control due to rising health claims.',
        humphrey="Welfare costs are escalating, Chancellor. The public expects compassion, but the Treasury expects solvency. It is a classic dilemma. To act would be controversial. To do nothing would be merely disastrous.",
        options=[
            '1. (Hard Left) Expand universal credit and eliminate benefit sanctions.',
            '2. (Social Democratic) Increase wrap-around employment support and health coaching.',
            '3. (Centric) Streamline welfare administration with moderate criteria checks.',
            '4. (Free-Market) Privatize employment support services and enforce strict work search rules.',
            '5. (Fiscal Austerity) Severely restrict disability benefits to achieve immediate savings.',
        ],
        effects=[
            dict(headroom=-6.0, approval=7, child_poverty=-3.0, homeless=-20, message='Welfare expanded.'),
            dict(growth=0.3, headroom=-3.5, approval=5, unemployment=-0.2, message='Health coaching deployed.'),
            dict(headroom=2.0, child_poverty=0.5, message='Moderate welfare checks.'),
            dict(headroom=3.5, market_conf=4, approval=-7, unemployment=-0.3, child_poverty=1.5, message='Employment support outsourced.'),
            dict(headroom=7.5, approval=-16, deficit=-1.1, child_poverty=3.5, homeless=30, message='Benefits slashed. Massive public backlash.'),
        ],
    ),
    (2, 2): dict(
        title='Tech Giant Tax Loophole',
        text='A leak reveals major tech giants pay almost zero tax in the UK. The public is outraged.',
        humphrey="It appears the tech companies have been utilizing our tax code exactly as we designed it. The public are demanding we close the loopholes. The tech companies are threatening to move to Ireland.",
        options=[
            '1. (Hard Left) Impose a massive retroactive digital services tax.',
            '2. (Social Democratic) Lead a global OECD coalition to enforce a minimum tax floor.',
            '3. (Centric) Close the worst domestic loopholes but avoid a trade war.',
            '4. (Free-Market) Defend the tax code and offer them further R&D incentives.',
            '5. (Fiscal Austerity) Use the controversy to quietly raise VAT on digital goods instead.',
        ],
        effects=[
            dict(market_conf=-12, headroom=6.0, approval=8, message='Tech giants hit with massive tax!'),
            dict(market_conf=2, approval=5, message='OECD tax floor negotiated.'),
            dict(market_conf=-2, headroom=2.0, approval=3, message='Minor domestic loopholes closed.'),
            dict(market_conf=8, approval=-9, growth=0.2, message='Tech giants offered more incentives.'),
            dict(headroom=4.5, approval=-12, inflation=0.2, message='Digital VAT quietly raised.'),
        ],
    ),
    (3, 1): dict(
        title='Housing Supply & Planning Reform',
        text='A severe housing shortage is crippling affordability for younger voters.',
        humphrey="The public wants more houses, Chancellor, but they absolutely do not want them built anywhere near where they currently live. It is a geographical impossibility. A very courageous decision awaits.",
        options=[
            '1. (Hard Left) Implement rent controls and launch a state housebuilding blitz.',
            '2. (Social Democratic) Mandate high social housing quotas on all private developments.',
            '3. (Centric) Overhaul planning laws to streamline local housing approvals.',
            '4. (Free-Market) Abolish planning restrictions and greenbelt protections entirely.',
            '5. (Fiscal Austerity) Protect greenbelt land and offer no state housing intervention.',
        ],
        effects=[
            dict(approval=9, market_conf=-12, headroom=-5.5, homeless=-30, homes_built=20, message='Rent controls enacted.'),
            dict(approval=7, growth=0.2, homeless=-15, house_ratio=-0.2, message='Social housing quotas mandated.'),
            dict(growth=0.3, approval=5, homes_built=25, house_ratio=-0.1, message='Planning laws streamlined.'),
            dict(growth=0.5, approval=-9, homes_built=50, house_ratio=-0.5, netzero=-5, message='Greenbelt abolished.'),
            dict(approval=-6, homes_built=-20, house_ratio=0.3, message='Greenbelt protected.'),
        ],
    ),
    (3, 2): dict(
        title='Strategic Armed Forces Review',
        text='Global tensions are rising, and the Ministry of Defence claims the army is hollowed out.',
        humphrey="The generals are demanding more tanks, Chancellor. I reminded them that our chief strategic threat is the Treasury's deficit, not a land war in Europe. They were not amused.",
        options=[
            '1. (Hard Left) Slash defence spending entirely to fund domestic public services.',
            '2. (Social Democratic) Maintain current spending but shift focus to cyber warfare.',
            '3. (Centric) Modestly increase the defence budget to meet NATO 2.5% targets.',
            '4. (Free-Market) Privatise military logistics and procurement to cut costs.',
            '5. (Fiscal Austerity) Force the MoD to scrap a major aircraft carrier to save money.',
        ],
        effects=[
            dict(headroom=6.5, approval=2, market_conf=-5, message='Defence budget slashed!'),
            dict(approval=3, message='Military focus shifted to cyber.'),
            dict(headroom=-4.0, approval=4, market_conf=2, message='NATO 2.5% target met.'),
            dict(market_conf=6, approval=-6, headroom=2.0, message='Military logistics privatised.'),
            dict(headroom=5.0, approval=-8, market_conf=-4, message='Aircraft carrier scrapped.'),
        ],
    ),
    (4, 1): dict(
        title='Green Transition vs Energy Costs',
        text='Net Zero targets are clashing with a sudden spike in household energy bills.',
        humphrey="The environmentalists want us to ban gas, and the public wants us to make gas cheaper. Might I suggest we simply issue a target for 2050 and leave the actual problem to the next government?",
        options=[
            '1. (Hard Left) Nationalise the energy grid and mandate immediate renewable transition.',
            '2. (Social Democratic) Subsidise home insulation and cap green energy prices.',
            '3. (Centric) Delay minor green targets to ease immediate bill pressure.',
            '4. (Free-Market) Fast-track North Sea oil drilling and scrap all green levies.',
            '5. (Fiscal Austerity) Refuse all subsidies and let the market dictate energy prices.',
        ],
        effects=[
            dict(headroom=-9.0, approval=8, market_conf=-15, netzero=10, energy_bills=-150, message='Energy grid nationalised.'),
            dict(headroom=-5.5, approval=6, growth=0.2, netzero=5, energy_bills=-100, message='Insulation subsidies launched.'),
            dict(approval=2, market_conf=3, netzero=-5, energy_bills=-50, message='Green targets delayed.'),
            dict(market_conf=10, approval=-5, growth=0.3, netzero=-15, energy_bills=-100, message='North Sea drilling approved.'),
            dict(approval=-14, market_conf=-2, inflation=0.4, energy_bills=200, message='Energy prices left to soar.'),
        ],
    ),
    (4, 2): dict(
        title='Trade & International Tariffs',
        text='Major trading partners propose new tariff barriers affecting British exporters.',
        humphrey="Trade barriers, Chancellor. The diplomatic equivalent of shooting oneself in the foot to prove a point. The Foreign Office recommends a firmly worded memo. The Treasury recommends doing whatever costs the least.",
        options=[
            '1. (Hard Left) Retaliate with strict protectionist tariffs and import controls.',
            '2. (Social Democratic) Negotiate comprehensive digital and green trade alignment pacts.',
            '3. (Centric) Pursue standard diplomatic trade negotiations.',
            '4. (Free-Market) Unilateral free trade approach with zero tariffs on all imports.',
            '5. (Fiscal Austerity) Absorb trade friction without policy or budget changes.',
        ],
        effects=[
            dict(approval=4, market_conf=-12, inflation=0.5, message='Protectionist tariffs applied.'),
            dict(market_conf=7, growth=0.2, message='Trade pact secured.'),
            dict(growth=0.1, message='Diplomatic trade talks held.'),
            dict(market_conf=10, growth=0.3, approval=-6, message='Unilateral free trade adopted.'),
            dict(growth=-0.2, message='Trade friction ignored.'),
        ],
    ),
    (5, 1): dict(
        title='Pre-Election Healthcare Push',
        text='Waiting lists remain a major electoral vulnerability as the election approaches.',
        humphrey="The NHS, Chancellor. The great British religion. It is currently consuming more money than the Ministry of Defence, yet still generating endless bad press. Throwing money at it is futile, but politically compulsory.",
        options=[
            '1. (Hard Left) Rebuild NHS capacity strictly via state funding and ban private contractors.',
            '2. (Social Democratic) Launch a massive frontline staff recruitment drive.',
            '3. (Centric) Partner with private healthcare providers to clear backlogs quickly.',
            '4. (Free-Market) Introduce an insurance-based healthcare model with copays.',
            '5. (Fiscal Austerity) Rely on existing NHS efficiencies with no extra funding.',
        ],
        effects=[
            dict(approval=7, headroom=-5.5, nhs_waiting=-0.2, message='Private contractors banned.'),
            dict(approval=8, headroom=-4.5, nhs_waiting=-0.4, nhs_morale=5, message='Staff recruitment funded.'),
            dict(approval=5, headroom=-3.5, nhs_waiting=-0.5, message='Private capacity utilized.'),
            dict(market_conf=9, approval=-16, nhs_waiting=-0.8, nhs_morale=-15, message='Insurance model introduced. Major backlash.'),
            dict(approval=-7, nhs_waiting=0.3, message='No extra NHS funds.'),
        ],
    ),
    (5, 2): dict(
        title='Final Pre-Election Tax & Spend Pitch',
        text='Special interest groups lobby heavily ahead of your final manifesto commitments.',
        humphrey="Ah, the 'silly season'. Every lobby group in the land is demanding a slice of the pie. We must ensure we promise them everything whilst drafting the legislation so vaguely that we are committed to absolutely nothing.",
        options=[
            '1. (Hard Left) Implement a wealth tax to fund universal basic services.',
            '2. (Social Democratic) Deliver targeted cost-of-living cash support.',
            '3. (Centric) Increase defense spending to 2.5% and protect pensions.',
            '4. (Free-Market) Abolish stamp duty and inheritance tax.',
            '5. (Fiscal Austerity) Hold firm on spending caps and protect fiscal rules.',
        ],
        effects=[
            dict(approval=8, headroom=-4.5, child_poverty=-1.0, message='Wealth taxes pledged.'),
            dict(approval=9, headroom=-4.5, real_wages=0.3, message='Cost-of-living support delivered.'),
            dict(approval=5, headroom=-3.5, message='Defense and pensions secured.'),
            dict(approval=7, market_conf=7, headroom=-5.5, message='Taxes abolished.'),
            dict(market_conf=9, message='Spending caps held firm.'),
        ],
    ),
}

# --- Endless Replayability: Term 2+ Random Scenarios ---
RANDOM_POOL = [
    dict(
        title='Universal Basic Income Trial',
        text='Automation is accelerating, and pilot schemes for Universal Basic Income are gaining massive public traction.',
        humphrey="Giving people money for simply existing, Chancellor. It defies every principle of the Treasury. Next they will expect us to smile at them.",
        options=[
            '1. (Hard Left) Roll out full UBI funded by massive wealth taxes.',
            '2. (Social Democratic) Launch a generous targeted UBI for lower-income brackets.',
            '3. (Centric) Run a small, fully-costed regional trial.',
            '4. (Free-Market) Replace all existing welfare with a flat, meager UBI.',
            '5. (Fiscal Austerity) Cancel the trial and cut existing welfare to force people into work.',
        ],
        effects=[
            dict(approval=12, market_conf=-15, headroom=-10.0, child_poverty=-8.0, inflation=0.6, message='Full UBI enacted! Markets panic.'),
            dict(approval=8, headroom=-6.0, child_poverty=-4.0, message='Targeted UBI launched.'),
            dict(approval=3, headroom=-1.5, message='Regional UBI trial commences.'),
            dict(market_conf=6, approval=-8, child_poverty=3.0, headroom=4.0, message='Welfare replaced by flat UBI.'),
            dict(approval=-14, market_conf=8, headroom=5.5, child_poverty=4.0, message='Welfare slashed. Major protests erupt.'),
        ],
    ),
    dict(
        title='Nuclear Power & Energy Independence',
        text='The energy grid is vulnerable. A proposal is on your desk to rapidly expand nuclear power generation.',
        humphrey="Nuclear power, Chancellor. It guarantees energy independence in thirty years, which handily means the cost overruns will be the next government's problem.",
        options=[
            '1. (Hard Left) Fully nationalise the energy sector to build state-owned reactors.',
            '2. (Social Democratic) Co-fund reactors with unionised labor guarantees.',
            '3. (Centric) Offer moderate state subsidies for private SMR development.',
            '4. (Free-Market) Deregulate safety standards to speed up private construction.',
            '5. (Fiscal Austerity) Refuse state funding; rely entirely on foreign capital.',
        ],
        effects=[
            dict(approval=5, market_conf=-12, headroom=-8.0, netzero=5, energy_bills=-50, message='Energy sector nationalised.'),
            dict(approval=6, headroom=-5.0, growth=0.2, netzero=4, message='State co-funds nuclear plants.'),
            dict(approval=3, headroom=-2.0, netzero=2, message='Subsidies granted for private SMRs.'),
            dict(market_conf=8, approval=-6, netzero=4, message='Nuclear safety deregulated. Fast builds approved.'),
            dict(approval=-4, market_conf=-2, netzero=-2, message='State refuses to fund nuclear power.'),
        ],
    ),
    dict(
        title='The Four-Day Work Week',
        text='Trade unions and progressive think tanks are pushing hard for a mandated 4-day working week with no loss of pay.',
        humphrey="A four-day week, Chancellor? I assume the civil service is exempt. We barely manage to stretch our work across five days as it is.",
        options=[
            '1. (Hard Left) Mandate a 4-day week across all sectors by law.',
            '2. (Social Democratic) Subsidise public sector trials and encourage private adoption.',
            '3. (Centric) Issue voluntary guidelines for flexible working.',
            '4. (Free-Market) Ban 4-day mandates and scrap working time directives.',
            '5. (Fiscal Austerity) Force the public sector back to 5 days and cut holiday allowances.',
        ],
        effects=[
            dict(approval=15, market_conf=-18, growth=-0.5, inflation=0.8, message='4-Day Week mandated! Corporate chaos ensues.'),
            dict(approval=7, headroom=-3.0, growth=-0.1, message='Public sector 4-day trials begin.'),
            dict(approval=2, message='Voluntary flexible working guidelines issued.'),
            dict(market_conf=8, approval=-7, growth=0.3, real_wages=-0.2, message='Working time directives scrapped.'),
            dict(approval=-12, market_conf=5, nhs_morale=-10, message='Public sector holidays cut.'),
        ],
    ),
    dict(
        title='University Tuition Fee Crisis',
        text='Universities are going bankrupt, and student debt is suppressing the housing market for young adults.',
        humphrey="The universities have run out of money, Chancellor. They assumed they could infinitely charge students for degrees in Media Studies. A classic pyramid scheme.",
        options=[
            '1. (Hard Left) Abolish fees entirely and forgive all existing student debt.',
            '2. (Social Democratic) Halve fees and restore maintenance grants.',
            '3. (Centric) Link repayment thresholds to inflation.',
            '4. (Free-Market) Lift the fee cap entirely and let universities compete on price.',
            '5. (Fiscal Austerity) Raise fees and increase the interest rate on student loans.',
        ],
        effects=[
            dict(approval=12, market_conf=-14, headroom=-9.0, schools=5, message='Tuition fees abolished! Massive state cost.'),
            dict(approval=8, headroom=-5.0, schools=3, message='Fees halved and grants restored.'),
            dict(approval=3, headroom=-1.5, message='Repayment thresholds adjusted.'),
            dict(market_conf=6, approval=-10, schools=-2, message='Fee caps lifted. Education marketized.'),
            dict(approval=-15, headroom=4.0, schools=-4, message='Fees and interest rates hiked. Students riot.'),
        ],
    ),
    dict(
        title='The AI Automation Crisis',
        text='Artificial Intelligence is rapidly displacing white-collar jobs in the City, leading to a spike in sudden unemployment.',
        humphrey="The algorithms are writing reports faster than we are, Chancellor. If they learn how to leak them to the press, the civil service is doomed.",
        options=[
            '1. (Hard Left) Impose a crippling 50% "Robot Tax" to fund displaced workers.',
            '2. (Social Democratic) Create a state retraining fund paid for by a moderate tech levy.',
            '3. (Centric) Form a committee to study AI impacts.',
            '4. (Free-Market) Offer massive R&D tax credits to companies replacing staff with AI.',
            '5. (Fiscal Austerity) Do nothing; let displaced workers claim standard universal credit.',
        ],
        effects=[
            dict(approval=8, market_conf=-12, headroom=4.0, unemployment=-0.1, message='Robot Tax imposed! Tech sector furious.'),
            dict(approval=6, headroom=-1.0, growth=0.1, unemployment=-0.2, message='AI retraining fund established.'),
            dict(approval=1, message='AI Committee formed. Impact deferred.'),
            dict(market_conf=10, approval=-8, growth=0.4, unemployment=0.5, message='AI automation subsidized. Jobs lost, profits soar.'),
            dict(approval=-6, market_conf=2, unemployment=0.3, message='AI displacement ignored.'),
        ],
    ),
]

def get_decision(term, year, block):
    """Returns narrative decisions for Term 1, and randomized pool scenarios for Term 2+."""
    if term == 1:
        return DECISIONS.get((year, block))
    else:
        # Seed the random choice so it doesn't change every time a slider is moved
        random.seed(f"{term}-{year}-{block}")
        choice = random.choice(RANDOM_POOL)
        random.seed() # reset seed
        return choice
