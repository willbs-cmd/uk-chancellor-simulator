"""Policy decisions: 2 blocks per year, followed by the Budget.

Each decision lists five options in a fixed ideology order (see IDEOLOGIES). The game shuffles them and
hides the ideology tags unless the player turns them on. Some options also queue a DELAYED consequence."""
import random
import re

BLOCKS_PER_YEAR = 3   
BUDGET_BLOCK = 3
IDEOLOGIES = ['Hard Left', 'Social Democratic', 'Centric', 'Free-Market', 'Fiscal Austerity']

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
            dict(headroom=-9.77, approval=5.1, market_conf=-18, gilt_yield=0.5, energy_bills=-200, rail=10, message='Nationalisation rattles the markets!'),
            dict(headroom=-4.67, approval=7.56, deficit=1.2, growth=0.2, unemployment=-0.3, netzero=5, message='Green jobs guarantee launched.'),
            dict(headroom=-2.5, approval=1.35, homes_built=15, rail=5, message='Pragmatic infrastructure pledged.'),
            dict(market_conf=12, approval=-2.4, growth=0.36, real_wages=-0.3, unemployment=-0.2, headroom=1, message='Employment regulations scrapped.'),
            dict(headroom=4.4, approval=-4, deficit=-0.7, nhs_morale=-10, schools=-5, market_conf=4, message='Public sector hiring frozen.'),
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
            dict(headroom=-9.2, approval=8.5, deficit=1.4, inflation=0.4, nhs_morale=15, message='Unions appeased, but inflation ticks upward.'),
            dict(headroom=-5.47, approval=4.86, nhs_morale=5, message='Fair pay settlement reached.'),
            dict(approval=-2.4, nhs_morale=0, message='Compromise struck with minor disruption.'),
            dict(market_conf=10.8, approval=-4, nhs_morale=-15, headroom=1, message='Private contracting introduced.'),
            dict(approval=-5.6, market_conf=10, inflation=-0.3, nhs_morale=-20, message='Pay cap enforced. Markets pleased, workforce furious.'),
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
            dict(headroom=-6.9, approval=6, child_poverty=-3, homeless=-20, message='Welfare expanded.'),
            dict(growth=0.24, headroom=-4.25, approval=4.06, unemployment=-0.2, message='Health coaching deployed.'),
            dict(headroom=2, child_poverty=0.5, message='Moderate welfare checks.'),
            dict(headroom=3.5, market_conf=4.8, approval=-2.8, unemployment=-0.3, child_poverty=1.5, message='Employment support outsourced.'),
            dict(headroom=8.25, approval=-6.4, deficit=-1.1, child_poverty=3.5, homeless=30, market_conf=4, message='Benefits slashed. Massive public backlash.'),
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
            dict(market_conf=-12, headroom=6, approval=6.8, message='Tech giants hit with massive tax!'),
            dict(headroom=-1.7, market_conf=1, approval=4.06, message='OECD tax floor negotiated.'),
            dict(market_conf=-2, headroom=2, approval=1.35, message='Minor domestic loopholes closed.'),
            dict(market_conf=9.6, approval=-3.6, growth=0.24, headroom=1, message='Tech giants offered more incentives.'),
            dict(headroom=4.95, approval=-4.8, inflation=0.2, market_conf=4, message='Digital VAT quietly raised.'),
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
            dict(approval=7.7, market_conf=-12, headroom=-6.32, homeless=-30, homes_built=20, message='Rent controls enacted.'),
            dict(approval=5.66, growth=0.16, homeless=-15, house_ratio=-0.2, message='Social housing quotas mandated.'),
            dict(growth=0.3, approval=2.25, homes_built=25, house_ratio=-0.1, message='Planning laws streamlined.'),
            dict(growth=0.6, approval=-3.6, homes_built=50, house_ratio=-0.5, netzero=-5, headroom=1, message='Greenbelt abolished.'),
            dict(approval=-2.4, homes_built=-20, house_ratio=0.3, market_conf=4, message='Greenbelt protected.'),
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
            dict(headroom=6.5, approval=1.7, market_conf=-5, message='Defence budget slashed!'),
            dict(approval=2.44, message='Military focus shifted to cyber.'),
            dict(headroom=-4, approval=1.8, market_conf=2, message='NATO 2.5% target met.'),
            dict(market_conf=7.2, approval=-2.4, headroom=2, message='Military logistics privatised.'),
            dict(headroom=5.5, approval=-3.2, market_conf=-4, message='Aircraft carrier scrapped.'),
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
            dict(headroom=-10.35, approval=6.8, market_conf=-15, netzero=10, energy_bills=-150, message='Energy grid nationalised.'),
            dict(headroom=-6.69, approval=4.86, growth=0.16, netzero=5, energy_bills=-100, message='Insulation subsidies launched.'),
            dict(approval=0.9, market_conf=3, netzero=-5, energy_bills=-50, message='Green targets delayed.'),
            dict(market_conf=12, approval=-2, growth=0.36, netzero=-15, energy_bills=-100, headroom=1, message='North Sea drilling approved.'),
            dict(approval=-5.6, market_conf=-2, inflation=0.4, energy_bills=200, message='Energy prices left to soar.'),
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
            dict(approval=3.4, market_conf=-12, inflation=0.5, message='Protectionist tariffs applied.'),
            dict(market_conf=7, growth=0.16, message='Trade pact secured.'),
            dict(growth=0.1, message='Diplomatic trade talks held.'),
            dict(market_conf=12, growth=0.36, approval=-2.4, headroom=1, message='Unilateral free trade adopted.'),
            dict(growth=-0.2, market_conf=4, message='Trade friction ignored.'),
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
            dict(approval=6, headroom=-6.32, nhs_waiting=-0.2, message='Private contractors banned.'),
            dict(approval=6.48, headroom=-5.47, nhs_waiting=-0.4, nhs_morale=5, message='Staff recruitment funded.'),
            dict(approval=2.25, headroom=-3.5, nhs_waiting=-0.5, message='Private capacity utilized.'),
            dict(market_conf=10.8, approval=-6.4, nhs_waiting=-0.8, nhs_morale=-15, headroom=1, message='Insurance model introduced. Major backlash.'),
            dict(approval=-2.8, nhs_waiting=0.3, market_conf=4, message='No extra NHS funds.'),
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
            dict(approval=6.8, headroom=-5.17, child_poverty=-1, message='Wealth taxes pledged.'),
            dict(approval=7.28, headroom=-5.47, real_wages=0.24, message='Cost-of-living support delivered.'),
            dict(approval=2.25, headroom=-3.5, message='Defense and pensions secured.'),
            dict(approval=7, market_conf=8.4, headroom=-5.5, message='Taxes abolished.'),
            dict(market_conf=9, message='Spending caps held firm.'),
        ],
    ),
}


# Extra policy bank: each new term draws a fresh, non-repeating set of weekly topics.
# Effects deliberately use the same five-ideology order as the original decisions.
EXTRA_POLICY_DECISIONS = [
    dict(title='NHS Waiting Lists Emergency', text='Waiting lists remain politically toxic. The Health Secretary wants a plan before the next set of figures lands.', humphrey='The NHS would like more money, more staff and fewer patients, Chancellor. In the circumstances, I fear they may be asking for a miracle.', options=[
        '1. (Hard Left) Bring private hospitals into public ownership and fund a major staffing drive.',
        '2. (Social Democratic) Fund extra evening and weekend clinics and expand NHS recruitment.',
        '3. (Centric) Target the longest waits and publish monthly performance dashboards.',
        '4. (Free-Market) Expand independent-provider contracts for routine procedures.',
        '5. (Fiscal Austerity) Freeze administrative hiring and require productivity savings.',
    ], effects=[
        dict(headroom=-7.0, approval=5.0, nhs_waiting=-0.7, nhs_morale=7, market_conf=-3, message='A public-sector NHS expansion begins.'),
        dict(headroom=-5.0, approval=4.0, nhs_waiting=-0.9, nhs_morale=8, message='Extra clinics and recruitment funded.'),
        dict(headroom=-1.5, approval=1.5, nhs_waiting=-0.4, message='Targeted waiting-list plan launched.'),
        dict(headroom=-2.5, approval=-1.0, nhs_waiting=-0.6, market_conf=3, message='Independent-provider capacity contracted.'),
        dict(headroom=2.0, approval=-4.0, nhs_morale=-7, message='NHS savings drive announced.'),
    ]),
    dict(title='The Skills and Universities Settlement', text='Universities warn that finances are deteriorating while employers say they cannot find skilled workers.', humphrey='The universities say they are underfunded; the Treasury says they should diversify. Both sides have produced glossy reports. Neither has produced a cheaper solution.', options=[
        '1. (Hard Left) Make university tuition free and restore maintenance grants.',
        '2. (Social Democratic) Expand grants for disadvantaged students and technical colleges.',
        '3. (Centric) Reform student finance and fund courses tied to skills shortages.',
        '4. (Free-Market) Let universities set fees and compete for students.',
        '5. (Fiscal Austerity) Cut teaching grants and consolidate struggling institutions.',
    ], effects=[
        dict(headroom=-7.0, approval=5.5, growth=0.15, child_poverty=-0.5, message='Free tuition promised; the bill lands at the Treasury.'),
        dict(headroom=-4.0, approval=4.0, growth=0.2, unemployment=-0.1, message='Skills and student-support package announced.'),
        dict(headroom=-1.5, approval=1.0, growth=0.15, message='Student finance reform agreed.'),
        dict(headroom=1.0, market_conf=3, approval=-2.5, growth=0.1, message='Universities gain pricing freedom.'),
        dict(headroom=3.0, approval=-4.0, growth=-0.1, message='Higher education savings imposed.'),
    ]),
    dict(title='Rail Fares and Commuter Chaos', text='Commuters face rising fares and repeated disruption. Business groups say unreliable transport is holding back growth.', humphrey='The railways are currently too expensive, too unreliable and too complicated. Naturally, several departments have proposed adding a new regulator.', options=[
        '1. (Hard Left) Renationalise passenger rail and freeze fares.',
        '2. (Social Democratic) Cap fare rises and invest in reliable local services.',
        '3. (Centric) Tie fare rises to service standards and upgrade bottlenecks.',
        '4. (Free-Market) Open more routes to competition and dynamic pricing.',
        '5. (Fiscal Austerity) Allow fares to rise and cut low-use subsidies.',
    ], effects=[
        dict(headroom=-5.0, approval=4.5, rail=8, growth=0.1, market_conf=-3, message='Rail brought under public control.'),
        dict(headroom=-3.5, approval=4.0, rail=6, message='Fare cap and local-service investment announced.'),
        dict(headroom=-2.0, approval=1.5, rail=4, growth=0.1, message='Performance-linked rail reform begins.'),
        dict(headroom=0.5, approval=-1.5, rail=2, market_conf=3, message='Rail competition expanded.'),
        dict(headroom=2.5, approval=-4.0, rail=-3, message='Rail subsidies cut; fares rise.'),
    ]),
    dict(title='AI, Automation and British Jobs', text='Employers are adopting AI rapidly. Unions want protections, while firms warn against rules that could slow investment.', humphrey='Artificial intelligence promises to make work more efficient. The civil service is studying whether this means it can produce the same report in half the time.', options=[
        '1. (Hard Left) Introduce a robot tax and a public AI service.',
        '2. (Social Democratic) Fund retraining and require worker consultation on major automation.',
        '3. (Centric) Create a light-touch AI code with targeted retraining grants.',
        '4. (Free-Market) Keep regulation minimal and offer AI investment allowances.',
        '5. (Fiscal Austerity) End new grants and let firms fund their own transition.',
    ], effects=[
        dict(headroom=-3.5, approval=2.5, growth=-0.1, unemployment=0.2, message='AI levy and public technology programme proposed.'),
        dict(headroom=-3.0, approval=3.5, growth=0.2, unemployment=-0.2, message='Worker retraining package launched.'),
        dict(headroom=-1.0, approval=1.0, growth=0.2, message='Practical AI framework published.'),
        dict(headroom=-1.5, market_conf=4, growth=0.45, approval=0.5, message='AI investment incentives announced.'),
        dict(headroom=1.0, approval=-2.5, growth=0.05, message='Public support for AI transition withdrawn.'),
    ]),
    dict(title='Small Business Rates Revolt', text='High-street businesses say business rates and energy costs are making local shops unviable.', humphrey='The high street would like lower taxes, cheaper energy and more customers. The Treasury has discovered that the first two are expensive and the third is difficult to legislate for.', options=[
        '1. (Hard Left) Replace business rates with a tax on large commercial property owners.',
        '2. (Social Democratic) Expand small-business relief and provide targeted energy support.',
        '3. (Centric) Simplify rates and offer time-limited relief to struggling shops.',
        '4. (Free-Market) Permanently cut business rates and loosen trading rules.',
        '5. (Fiscal Austerity) Keep rates unchanged and remove temporary reliefs.',
    ], effects=[
        dict(headroom=-3.0, approval=3.5, growth=0.1, message='Business-rates overhaul targets large property owners.'),
        dict(headroom=-2.5, approval=4.0, growth=0.2, unemployment=-0.1, message='High-street support package launched.'),
        dict(headroom=-1.0, approval=1.5, growth=0.1, message='Temporary rates relief agreed.'),
        dict(headroom=-4.0, approval=2.0, market_conf=3, growth=0.35, message='Permanent rates cuts announced.'),
        dict(headroom=2.0, approval=-3.5, growth=-0.1, message='Business reliefs withdrawn.'),
    ]),
    dict(title='Flood Defences and Climate Resilience', text='Flooding has damaged homes and infrastructure. Local leaders demand long-term prevention rather than emergency clean-ups.', humphrey='The Environment Agency would like to prevent floods before they happen. The Treasury traditionally prefers to evaluate the value of prevention after the flooding has occurred.', options=[
        '1. (Hard Left) Launch a national public flood-defence and home-retrofit programme.',
        '2. (Social Democratic) Prioritise vulnerable communities and resilient infrastructure.',
        '3. (Centric) Co-fund local defences using risk-based assessments.',
        '4. (Free-Market) Incentivise private insurance and property-level protection.',
        '5. (Fiscal Austerity) Restrict new spending to emergency repairs only.',
    ], effects=[
        dict(headroom=-5.0, approval=3.5, netzero=3, growth=0.1, message='National resilience programme begins.'),
        dict(headroom=-3.5, approval=3.0, netzero=2, homeless=-5, message='Flood protection prioritised for high-risk communities.'),
        dict(headroom=-1.5, approval=1.0, netzero=1, message='Risk-based local flood funds allocated.'),
        dict(headroom=-0.5, approval=-1.0, market_conf=2, message='Private resilience incentives introduced.'),
        dict(headroom=1.5, approval=-3.0, netzero=-2, message='Only emergency flood repairs will be funded.'),
    ]),
    dict(title='Childcare and Parental Employment', text='Parents say childcare costs are keeping them out of work, while providers warn that funding does not cover their costs.', humphrey='Childcare is simultaneously an economic growth policy, a family policy and a very expensive invoice. The Treasury would prefer it to be just one of those things.', options=[
        '1. (Hard Left) Provide universal free childcare funded by the state.',
        '2. (Social Democratic) Expand funded hours and raise support for low-income families.',
        '3. (Centric) Target subsidies at working parents and childcare shortages.',
        '4. (Free-Market) Offer tax credits and encourage new private providers.',
        '5. (Fiscal Austerity) Tighten eligibility and reduce childcare subsidies.',
    ], effects=[
        dict(headroom=-7.0, approval=5.0, growth=0.3, unemployment=-0.3, message='Universal childcare pledge announced.'),
        dict(headroom=-4.0, approval=4.0, growth=0.3, unemployment=-0.25, message='Funded childcare hours expanded.'),
        dict(headroom=-2.0, approval=1.5, growth=0.2, unemployment=-0.15, message='Targeted childcare support launched.'),
        dict(headroom=-1.5, approval=1.0, growth=0.25, market_conf=2, message='Childcare tax credits introduced.'),
        dict(headroom=2.0, approval=-4.0, unemployment=0.2, child_poverty=1.0, message='Childcare support eligibility tightened.'),
    ]),
    dict(title='Local Councils on the Brink', text='Councils warn that social care, libraries and local roads are competing for an increasingly thin budget.', humphrey='Local government has reached the stage where it can no longer afford to empty the bins, let alone discuss the future of civilisation. The bins, regrettably, are not optional.', options=[
        '1. (Hard Left) Create a central grant to reverse years of council cuts.',
        '2. (Social Democratic) Stabilise council finances and protect social care.',
        '3. (Centric) Reward councils that share services and improve delivery.',
        '4. (Free-Market) Expand outsourcing and give councils greater tax flexibility.',
        '5. (Fiscal Austerity) Require deeper savings and allow service consolidation.',
    ], effects=[
        dict(headroom=-6.0, approval=4.0, homeless=-5, message='Emergency council grant announced.'),
        dict(headroom=-4.0, approval=3.0, homeless=-3, message='Social care and council finances stabilised.'),
        dict(headroom=-1.0, approval=1.0, growth=0.1, message='Shared-services programme launched.'),
        dict(headroom=0.5, approval=-1.5, market_conf=2, message='Outsourcing and local tax flexibility expanded.'),
        dict(headroom=3.0, approval=-4.0, schools=-2, message='Council savings targets imposed.'),
    ]),
    dict(title='A Fair Deal for Farmers', text='Farmers face volatile input costs, environmental rules and uncertainty over food security.', humphrey='Farmers would like certainty, fair prices and fewer forms. The department has prepared a consultation document on the forms.', options=[
        '1. (Hard Left) Establish a public food board and guarantee minimum farm prices.',
        '2. (Social Democratic) Fund sustainable farming and rural infrastructure.',
        '3. (Centric) Offer targeted resilience grants and simplify compliance.',
        '4. (Free-Market) Remove trade barriers and loosen agricultural regulation.',
        '5. (Fiscal Austerity) End most farm subsidies and prioritise market competition.',
    ], effects=[
        dict(headroom=-4.0, approval=2.5, growth=-0.05, message='Food board and price guarantees proposed.'),
        dict(headroom=-3.0, approval=3.0, netzero=2, growth=0.1, message='Sustainable farming support funded.'),
        dict(headroom=-1.5, approval=1.0, growth=0.1, message='Targeted farm resilience grants introduced.'),
        dict(headroom=0.5, approval=-1.0, growth=0.2, netzero=-1, message='Agricultural market rules loosened.'),
        dict(headroom=2.5, approval=-3.5, netzero=-2, message='Farm subsidy reductions announced.'),
    ]),
    dict(title='Energy Security After a Price Shock', text='Wholesale energy prices have jumped again. Ministers must balance household bills, energy security and the transition to cleaner power.', humphrey='Energy security is essential, Chancellor. Unfortunately, the cheapest energy, the cleanest energy and the energy available tomorrow are not always the same energy.', options=[
        '1. (Hard Left) Take major energy suppliers into public ownership and cap household bills.',
        '2. (Social Democratic) Expand renewables and provide targeted bill support.',
        '3. (Centric) Diversify supply and accelerate grid upgrades.',
        '4. (Free-Market) Offer tax incentives for private energy investment and new generation.',
        '5. (Fiscal Austerity) End bill support and let prices reduce demand.',
    ], effects=[
        dict(headroom=-6.0, approval=5.0, energy_bills=-250, market_conf=-4, netzero=2, message='Public energy intervention caps household bills.'),
        dict(headroom=-3.5, approval=3.5, energy_bills=-120, netzero=4, message='Renewables and targeted bill support expanded.'),
        dict(headroom=-2.0, approval=1.0, energy_bills=-50, netzero=2, message='Grid resilience and supply diversification funded.'),
        dict(headroom=-1.0, market_conf=4, growth=0.2, netzero=1, message='Private energy investment incentives announced.'),
        dict(headroom=2.0, approval=-4.5, energy_bills=150, inflation=0.2, message='Energy support withdrawn as bills rise.'),
    ]),
    dict(title='Productivity and Planning the Next Decade', text='Productivity growth is weak. The OBR wants credible measures that can raise output without permanently inflating public spending.', humphrey='Productivity is the art of producing more with less. Whitehall has generally specialised in producing more paperwork with more people.', options=[
        '1. (Hard Left) Launch a public investment bank for strategic industries.',
        '2. (Social Democratic) Invest in skills, R&D and regional growth partnerships.',
        '3. (Centric) Reform planning and focus investment on high-return projects.',
        '4. (Free-Market) Cut corporation tax and remove barriers to investment.',
        '5. (Fiscal Austerity) Prioritise debt reduction over new investment.',
    ], effects=[
        dict(headroom=-5.0, growth=0.35, approval=2.0, message='Public investment bank established.'),
        dict(headroom=-4.0, growth=0.4, unemployment=-0.1, approval=3.0, message='Skills and innovation package launched.'),
        dict(headroom=-1.5, growth=0.3, homes_built=8, message='Planning and high-return investment reforms agreed.'),
        dict(headroom=-3.0, growth=0.45, market_conf=5, approval=0.5, message='Business investment tax cuts announced.'),
        dict(headroom=3.0, growth=-0.1, approval=-2.0, message='Investment deferred in favour of debt reduction.'),
    ]),
    dict(title='Immigration, Skills and Public Services', text='Employers report shortages in key sectors while communities want confidence that public services can keep up.', humphrey='The country requires skilled workers, tighter controls, faster processing and a system that is both humane and inexpensive. The department assures me these aims are entirely compatible.', options=[
        '1. (Hard Left) Expand safe routes and fund local integration services.',
        '2. (Social Democratic) Link work visas to shortage sectors and invest in integration.',
        '3. (Centric) Reform processing, enforcement and skills planning together.',
        '4. (Free-Market) Expand employer-led visas and streamline recruitment.',
        '5. (Fiscal Austerity) Tighten eligibility and reduce migration-related service spending.',
    ], effects=[
        dict(headroom=-2.5, approval=2.0, growth=0.15, homeless=-2, message='Safe routes and local integration funding expanded.'),
        dict(headroom=-2.0, approval=2.5, growth=0.25, unemployment=-0.1, message='Shortage-sector visas and integration investment aligned.'),
        dict(headroom=-0.5, approval=1.0, market_conf=1, growth=0.1, message='Processing and workforce planning reforms launched.'),
        dict(headroom=-0.5, approval=-1.0, growth=0.3, market_conf=3, message='Employer-led migration route expanded.'),
        dict(headroom=1.5, approval=-3.0, growth=-0.15, message='Migration and related service spending tightened.'),
    ]),
    dict(title='The Cost of Living and Household Debt', text='Households are struggling with food, rent and borrowing costs. Ministers want visible help without reigniting inflation.', humphrey='The cost of living is the price of living, Chancellor. The public would prefer it to be lower. The Treasury has been asked to investigate whether this is feasible.', options=[
        '1. (Hard Left) Introduce a broad essentials price cap funded by borrowing.',
        '2. (Social Democratic) Provide targeted payments and expand social tariffs.',
        '3. (Centric) Focus help on low-income households and debt advice.',
        '4. (Free-Market) Cut selected indirect taxes and encourage competition.',
        '5. (Fiscal Austerity) End temporary support to limit borrowing and demand.',
    ], effects=[
        dict(headroom=-6.0, approval=5.0, inflation=0.3, child_poverty=-1.0, message='Essentials price cap announced; supply concerns emerge.'),
        dict(headroom=-3.5, approval=4.0, child_poverty=-1.0, message='Targeted household support extended.'),
        dict(headroom=-1.5, approval=1.5, child_poverty=-0.5, message='Debt advice and focused support funded.'),
        dict(headroom=-2.0, approval=1.0, inflation=-0.1, growth=0.1, message='Selected consumption taxes reduced.'),
        dict(headroom=2.5, approval=-4.5, child_poverty=1.0, message='Temporary cost-of-living support ends.'),
    ]),
    dict(title='Tourism, Culture and the Night-Time Economy', text='Tourism and cultural venues want support, but the Treasury questions which interventions generate lasting local growth.', humphrey='The arts sector says it contributes billions to the economy. The Treasury has asked whether it could contribute those billions while requiring slightly less Treasury money.', options=[
        '1. (Hard Left) Create a public culture fund and subsidise community venues.',
        '2. (Social Democratic) Support regional tourism, museums and creative apprenticeships.',
        '3. (Centric) Target grants at projects with measurable local economic returns.',
        '4. (Free-Market) Cut licensing red tape and promote private investment.',
        '5. (Fiscal Austerity) End cultural grants and require venues to become self-funding.',
    ], effects=[
        dict(headroom=-3.5, approval=2.5, growth=0.1, message='Community culture fund created.'),
        dict(headroom=-2.5, approval=2.5, growth=0.2, unemployment=-0.1, message='Regional tourism and creative skills supported.'),
        dict(headroom=-1.0, approval=1.0, growth=0.15, message='Local-impact grants targeted.'),
        dict(headroom=0.0, market_conf=2, growth=0.2, approval=0.5, message='Licensing rules simplified for venues.'),
        dict(headroom=1.5, approval=-3.0, message='Cultural grants withdrawn.'),
    ]),
    dict(title='Digital Government and Civil Service Reform', text='Public services still rely on fragmented systems and paper-heavy processes. Ministers want savings without a collapse in service quality.', humphrey='Digital transformation is proceeding well, Chancellor. We have formed a taskforce to consider whether the existing taskforce can be moved to a digital platform.', options=[
        '1. (Hard Left) Build shared public digital infrastructure in-house and protect public-service jobs.',
        '2. (Social Democratic) Fund secure digital services and retrain civil servants.',
        '3. (Centric) Consolidate legacy systems with staged delivery targets.',
        '4. (Free-Market) Outsource major platforms to competing technology firms.',
        '5. (Fiscal Austerity) Mandate rapid headcount reductions and freeze IT budgets.',
    ], effects=[
        dict(headroom=-3.5, approval=1.5, growth=0.1, message='Public digital infrastructure programme launched.'),
        dict(headroom=-2.5, approval=2.0, growth=0.2, message='Secure services and staff retraining funded.'),
        dict(headroom=-1.0, approval=1.0, market_conf=1, message='Legacy systems consolidation begins.'),
        dict(headroom=0.5, market_conf=2, approval=-1.0, message='Technology outsourcing expanded.'),
        dict(headroom=2.0, approval=-3.0, nhs_morale=-2, message='Rapid civil service savings imposed.'),
    ]),
    dict(title='Pensions and Intergenerational Fairness', text='Pension costs are rising as younger workers worry about housing, wages and whether the system will be there for them.', humphrey='Pensions are a promise made by politicians to people who vote reliably. Younger people are understandably curious about when they might receive a similar promise.', options=[
        '1. (Hard Left) Expand the state pension and restore universal winter payments.',
        '2. (Social Democratic) Protect the pension floor and improve support for low-income retirees.',
        '3. (Centric) Review pension uprating alongside targeted help for poorer pensioners.',
        '4. (Free-Market) Encourage private saving and gradually raise the retirement age.',
        '5. (Fiscal Austerity) Means-test more pensioner benefits and restrain uprating.',
    ], effects=[
        dict(headroom=-5.5, approval=4.0, child_poverty=-0.2, message='Pension entitlements expanded.'),
        dict(headroom=-3.5, approval=3.0, message='Pensioner poverty measures funded.'),
        dict(headroom=-1.0, approval=0.5, message='Pension review and targeted help announced.'),
        dict(headroom=1.0, approval=-2.0, growth=0.1, message='Private saving incentives and retirement-age review launched.'),
        dict(headroom=3.0, approval=-4.5, message='Pensioner benefits means-tested more tightly.'),
    ]),
]

# Give the extra topics stable keys so existing option and delayed-effect code can be reused.
DECISIONS.update({(6 + i, 1): d for i, d in enumerate(EXTRA_POLICY_DECISIONS)})


def get_weekly_decision(seed, term, year, block):
    """Draw a varied, non-repeating set of 10 policy topics for each five-year term."""
    if block not in (1, 2) or year < 1:
        return None
    slot = (year - 1) * 2 + (block - 1)
    # Keep the opening policy as a reliable tutorial and preserve its delayed-consequence example.
    opening = DECISIONS[(1, 1)]
    if slot == 0:
        return opening
    pool = [d for d in DECISIONS.values() if d is not opening]
    random.Random(f'{seed}-{term}-weekly-policy-variety').shuffle(pool)
    if slot - 1 >= len(pool):
        return None
    return pool[slot - 1]


# ---------------------------------------------------------------------------------------------
# Delayed consequences: (year, block) -> {option index: spec}. 'after' counts player actions
# (decisions, crises, budgets) before it lands. Not every option has one; some are rewards.
# ---------------------------------------------------------------------------------------------
DELAYED = {
    (1, 1): {
        0: dict(after=2, title='Compensation bill arrives', text='Shareholders of the nationalised utilities are owed their compensation.',
                warn='Shareholders will, naturally, expect to be paid for what we have taken.',
                fx=dict(headroom=-4.0, gilt_yield=0.2, market_conf=-3)),
        3: dict(after=2, title='Tribunal chaos', text='Scrapping employment protections floods the tribunals and sours the mood at work.',
                warn='Workers tend to notice when their rights vanish.',
                fx=dict(approval=-3, unemployment=0.1)),
        4: dict(after=2, title='Staff exodus', text='Experienced public sector staff quietly leave and agency bills soar.',
                warn='A hiring freeze is rarely a free lunch.',
                fx=dict(nhs_waiting=0.3, nhs_morale=-5, schools=-2)),
    },
    (1, 2): {
        0: dict(after=2, title='Pay deal precedent', text='Every other sector now wants the same deal, and the Treasury is footing the bill.',
                warn='Precedents have a way of travelling.', fx=dict(inflation=0.3, headroom=-2.0)),
        3: dict(after=2, title='Contractor cost overruns', text='Private contractors turn out to cost rather more than the public sector did.',
                warn='Contractors do not work for free.', fx=dict(headroom=-3.0, approval=-2)),
        4: dict(after=2, title='Recruitment crisis', text='With pay capped, vacancies stack up across frontline services.',
                warn='Capped pay and vacant posts often go together.', fx=dict(nhs_waiting=0.3, nhs_morale=-5)),
    },
    (2, 1): {
        0: dict(after=2, title='Claimant numbers surge', text='Looser rules and no sanctions send claimant numbers climbing.',
                warn='Generosity is popular until the OBR publishes its forecast.', fx=dict(headroom=-3.0, deficit=0.5)),
        1: dict(after=2, title='Health coaching pays off', text='More people return to work and the savings start to show.',
                warn='Some investments take a little while to mature.', fx=dict(growth=0.2, headroom=2.0, unemployment=-0.2)),
        4: dict(after=2, title='Cuts hit local councils', text='Councils pick up the pieces of the benefit cuts, and temporary housing grows.',
                warn='Savings made in one place tend to appear as costs in another.',
                fx=dict(homeless=10, child_poverty=1.0, approval=-3)),
    },
    (2, 2): {
        0: dict(after=2, title='Tech firms relocate', text='The retroactive tax drives several firms to reconsider where they are headquartered.',
                warn='Mobile capital is rather good at leaving.', fx=dict(market_conf=-4, growth=-0.2)),
        1: dict(after=2, title='OECD floor yields revenue', text='The minimum tax floor starts to bring in money.',
                warn='Diplomacy is slow, but occasionally profitable.', fx=dict(headroom=3.0)),
    },
    (3, 1): {
        2: dict(after=2, title='Planning reform bears fruit', text='Streamlined approvals translate into cranes on the skyline.',
                warn='Planning reform takes time to turn into bricks.', fx=dict(homes_built=10, growth=0.1)),
        4: dict(after=2, title='Housing pressure builds', text='With supply frozen, younger voters feel the squeeze harder than ever.',
                warn='Doing nothing on housing has a way of showing up in polls.', fx=dict(house_ratio=0.2, approval=-2)),
    },
    (3, 2): {
        0: dict(after=2, title='Allies notice the gap', text='NATO partners publicly question Britain\'s commitment.',
                warn='Allies keep long memories about spending.', fx=dict(approval=-3, market_conf=-3)),
        4: dict(after=2, title='Carrier gap exposed', text='A crisis abroad exposes the hole where the carrier used to be.',
                warn='Capabilities are easier to scrap than to rebuild.', fx=dict(approval=-3, market_conf=-3)),
    },
    (4, 1): {
        0: dict(after=2, title='Grid takeover costs mount', text='Nationalising the grid is proving expensive to run.',
                warn='Ownership also means the bills are yours.', fx=dict(headroom=-3.0, gilt_yield=0.1)),
        3: dict(after=2, title='Drilling dividend', text='North Sea output and licence revenues arrive on schedule.',
                warn='Some policies pay back handsomely, in time.', fx=dict(headroom=3.0, energy_bills=-50)),
        4: dict(after=2, title='Winter price spike', text='Unsubsidised, bills surge when the cold arrives.',
                warn='Markets are not always gentle in winter.', fx=dict(energy_bills=80, approval=-4)),
    },
    (4, 2): {
        0: dict(after=2, title='Counter-tariffs bite', text='Partners retaliate and exporters feel it first.',
                warn='Tariffs are a two-way street.', fx=dict(approval=-3, growth=-0.2, market_conf=-5)),
        3: dict(after=2, title='Cheap imports hit manufacturers', text='Domestic producers struggle against unprotected competition.',
                warn='Free trade makes winners and losers; the losers vote.', fx=dict(unemployment=0.2, approval=-2)),
    },
    (5, 1): {
        1: dict(after=2, title='Recruitment drive delivers', text='New frontline staff start work and lists begin to shift.',
                warn='Recruitment takes a while, then it shows.', fx=dict(nhs_waiting=-0.2)),
        3: dict(after=2, title='Premium row', text='The first insurance premiums land and the public is unamused.',
                warn='Insurance models tend to meet resistance at the bill.', fx=dict(approval=-4)),
    },
    (5, 2): {
        0: dict(after=1, title='Avoidance schemes', text='The wealthy find ways around the new tax faster than HMRC can close them.',
                warn='Wealth is rather good at moving.', fx=dict(headroom=-2.0, market_conf=-4)),
        3: dict(after=1, title='Hole in the forecast', text='The OBR notes the abolished taxes leave a hole in the numbers.',
                warn='Tax cuts are fully costed until somebody checks.', fx=dict(headroom=-3.0)),
    },
}

REACTIONS = {
    'Hard Left': ["Radical, Chancellor. I shall alert the gilt desk and the Bank's emergency line.",
                  "Bold, Chancellor. 'Bold' being the word we use in the Service when we mean 'unprecedented'.",
                  "The Cabinet Secretary asked me to convey his... interest, Chancellor."],
    'Social Democratic': ["A decent, sensible approach, Chancellor. The Treasury will merely ask who is paying for it.",
                          "I find this entirely defensible, Chancellor, provided nobody asks for the arithmetic.",
                          "The Opposition will call it tax and spend. The Treasury will call it 'investment'."],
    'Centric': ["A masterpiece of moderation, Chancellor. Nobody will love it and nobody will resign.",
                "Admirably cautious, Chancellor. The headline writers will be inconsolable.",
                "I could not have chosen better myself, Chancellor, and I have chosen precisely that for thirty years."],
    'Free-Market': ["The Treasury is reassured; the public less so. We shall brief that this was 'market-led'.",
                    "A confident move, Chancellor. I am told the City is delighted. The rest of the country has not yet been asked.",
                    "I shall prepare a note on 'managing expectations among the electorate', Chancellor."],
    'Fiscal Austerity': ["Firm, Chancellor. I shall have the Press Office describe it as 'responsible'.",
                         "The numbers look splendid, Chancellor. I will not ask how the people feel about them.",
                         "Prudent. Painfully prudent. Rather like a dentist, Chancellor."],
    'triumph': ["That went rather better than anyone expected, Chancellor. Do try to look surprised.",
                "A triumph, Chancellor. Enjoy it; they are very short-lived in Whitehall."],
    'disaster': ["That, Chancellor, was what we in the Service call 'a learning experience'.",
                 "I have seen worse. Admittedly, only once, and it ended an administration."],
}

_TAG = re.compile(r'^\d+\.\s*\(([^)]+)\)\s*')


def strip_tag(text):
    """Remove the leading '1. (Hard Left) ' from an option."""
    return _TAG.sub('', text)


def get_options(decision, shuffle_key, show_tags=False):
    """Return the decision's options as dicts, shuffled deterministically by ``shuffle_key``.

    Each dict has: label (what the player reads), ideology, effect, delayed (spec or None).
    """
    key = decision.get('_key')
    delayed = DELAYED.get(key, {})
    options = []
    for i, (text, fx) in enumerate(zip(decision['options'], decision['effects'])):
        body = strip_tag(text)
        ideology = IDEOLOGIES[i]
        options.append(dict(label=f'({ideology}) {body}' if show_tags else body, ideology=ideology,
                            effect=fx, delayed=delayed.get(i)))
    random.Random(shuffle_key).shuffle(options)
    return options


def reaction(ideology, d_approval, d_market, delayed=None):
    """Sir Humphrey's comment on what the player just did."""
    pool = REACTIONS.get(ideology, REACTIONS['Centric'])
    if d_approval + 0.5 * d_market >= 8:
        pool = REACTIONS['triumph']
    elif d_approval + 0.5 * d_market <= -10:
        pool = REACTIONS['disaster']
    text = random.choice(pool)
    if delayed:
        text += f" (A word of caution, Chancellor: {delayed['warn']})"
    return text


for _k, _d in DECISIONS.items():
    _d['_key'] = _k
