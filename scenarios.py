import random
import streamlit as st
import budget
import country
import state

def C(title, humphrey, *args):
    opts = [(args[i], args[i+1]) for i in range(0, len(args), 2)]
    return dict(title=title, humphrey=humphrey, opts=opts)

CRISES = {
    # --- NEW POLITICAL CAPITAL CRISES ---
    'leadership_challenge': C('🚨 BREAKING: Leadership Challenge!',
                     "Chancellor, your backbenchers have decided the Prime Minister is a liability. You must intervene to save them, or wield the knife yourself.",
                     'Bribe the rebels with uncosted pet projects', dict(headroom=-3.5, approval=-2, pm_opinion=15, backbench_opinion=20),
                     'Unleash the whips to threaten and bully them', dict(market=2, pm_opinion=10, backbench_opinion=-10),
                     'Publicly support the PM but plot in secret', dict(approval=2, pm_opinion=20, cab_opinion=10)),
                     
    'tabloid_scandal': C('🚨 BREAKING: Major Tabloid Scandal!',
                     "Fleet Street has dug up some rather unedifying photographs of a senior Cabinet Minister, Chancellor. The press demands blood.",
                     'Force the Minister to resign immediately', dict(cab_opinion=-15, media_opinion=20, approval=3),
                     'Defend the Minister and attack the press', dict(media_opinion=-20, backbench_opinion=10, approval=-5),
                     'Distract them by leaking a popular new tax cut', dict(headroom=-2.0, approval=5, media_opinion=15)),

    # --- EXISTING CRISES ---
    'gilt_revolt': C('🚨 BREAKING: Severe Gilt Market Revolt! Foreign investors dump UK debt as yields surge past 5.5%.',
                     "Chancellor, the bond markets have taken a sudden and profound dislike to us. If we do not intervene, we may find ourselves in the rather novel position of national bankruptcy.",
                     'Deploy emergency Bank of England intervention', dict(headroom=-7, market=8, gilt=-0.4),
                     'Refuse intervention and let bond vigilantes feast', dict(market=-18, debt=2.5, gilt=0.8),
                     'Announce an emergency package of brutal spending cuts to restore confidence', dict(approval=-8, headroom=4, market=6, gilt=-0.2)),
    
    'nhs_walkout': C('🚨 BREAKING: National Health Service Staff Walkout! Nurses and junior doctors launch coordinated strikes.',
                     "The medical practitioners have opted for a spontaneous cessation of labour, Chancellor. We could pay them, but that would set a terrifying precedent.",
                     'Meet pay demands in full to avoid collapse', dict(headroom=-6, approval=10, inflation=0.4, nhs_morale=8),
                     'Stand firm and invoke emergency service minimums', dict(approval=-12, growth=-0.3, nhs_morale=-10, nhs_waiting=0.4),
                     'Offer a one-off non-consolidated bonus', dict(headroom=-2.5, approval=3, nhs_morale=2, inflation=0.1)),
    
    'energy_bankruptcy': C('🚨 BREAKING: Major Energy Retailer Bankruptcy! State bailout required to keep lights on.',
                           "An energy firm has carelessly misplaced its capital, Chancellor. We can bail them out, or we can let the free market freeze the electorate.",
                           'Absorb company liabilities into public balance sheet', dict(headroom=-5, approval=6, energy_bills=-40),
                           'Let customers scatter to higher tariffs', dict(approval=-9, inflation=0.5, energy_bills=120),
                           'Broker a rescue by a rival firm with temporary state loans', dict(headroom=-1.5, market=2, energy_bills=30)),
    
    'pension_hole': C('🚨 BREAKING: Public Sector Pension Black Hole Discovered! OBR mandates immediate funding correction.',
                      "It appears there is a slight discrepancy in the pension fund. A 'black hole', the tabloids call it.",
                      'Inject emergency cash reserves to plug shortfall', dict(headroom=-5.5, market=5),
                      'Cut departmental budgets across the board', dict(approval=-10, market=4, schools=-3, nhs_morale=-3),
                      'Increase employee contribution rates to share the pain', dict(approval=-6, real_wages=-0.2, market=2)),

    'cyber_attack': C('🚨 BREAKING: Major Cyber Attack! HMRC and NHS systems are knocked offline by a hostile state actor.',
                      "Our computer systems have been compromised, Chancellor. Apparently 'Password123' was not as robust as the IT department claimed.",
                      'Fund an emergency national cyber-security overhaul', dict(headroom=-4, market=4, approval=2),
                      'Restore systems quietly and hope it does not recur', dict(approval=-6, market=-8, nhs_waiting=0.2),
                      'Pay the ransom quietly through an untraceable proxy', dict(headroom=-1.0, approval=-4, market=-3)),
    
    'floods': C('🚨 BREAKING: Catastrophic Winter Floods! Thousands of homes and several northern towns are underwater.',
                "It is raining, Chancellor. And unfortunately, the water has decided to gather in places where people live.",
                'Launch a national flood recovery and defence fund', dict(headroom=-5, approval=8, netzero=2),
                'Leave recovery to councils and insurers', dict(approval=-10, homeless=8),
                'Deploy the army for logistics but provide no new cash', dict(approval=-2, homeless=4, market=1)),
    
    'bank_run': C('🚨 BREAKING: Regional Bank Run! Depositors queue outside a mid-sized lender as confidence evaporates.',
                  "The public has decided to withdraw their money from the banks all at once.",
                  'Guarantee all deposits to stop contagion', dict(headroom=-6, market=6, approval=3),
                  'Let it fail under the resolution regime', dict(market=-10, approval=-6, unemployment=0.1),
                  'Force a shotgun merger with a high street giant', dict(market=4, approval=-2, unemployment=0.1)),
    
    'steel_closure': C('🚨 BREAKING: Last Blast Furnace to Close! Thousands of jobs are at risk in a former industrial heartland.',
                       "Heavy industry is heavy, Chancellor. And expensive. Nationalising it would save jobs but ruin the balance sheet.",
                       'Nationalise the plant to save the jobs', dict(headroom=-4, approval=7, market=-3),
                       'Let the market decide', dict(approval=-8, market=3, unemployment=0.2),
                       'Provide heavy subsidies to transition to green steel', dict(headroom=-2.5, netzero=4, approval=4)),

    'prison_riot': C('🚨 BREAKING: Massive Prison Riot! Overcrowding has sparked a violent uprising in a major high-security facility.',
                     "The criminal classes are expressing their displeasure with the accommodation, Chancellor.",
                     'Approve emergency capital for new private prison contracts', dict(headroom=-3.0, approval=4, market=2, prisons=-5),
                     'Release non-violent offenders early to ease pressure', dict(approval=-12, prisons=-8, market=-1),
                     'Send in the military and suppress it without new funding', dict(approval=-4, prisons=2, market=-3)),
                     
    'ai_job_crisis': C('🚨 BREAKING: White-Collar AI Bloodbath! Major city firms announce 50,000 job cuts, replacing staff with AI.',
                       "The robots are taking over the City, Chancellor. It seems algorithms are far cheaper than accountants.",
                       'Implement an emergency "Robot Tax" to fund retraining', dict(headroom=2.0, market=-8, approval=6, unemployment=-0.1),
                       'Embrace the efficiency and let the market adjust naturally', dict(market=7, approval=-9, unemployment=0.4, growth=0.2),
                       'Ban AI from public sector procurement to protect state jobs', dict(approval=3, market=-4, growth=-0.1)),
                       
    'grid_blackout': C('🚨 BREAKING: Rolling Blackouts! The National Grid has failed to meet peak winter demand.',
                       "The lights have gone out, Chancellor. The public is sitting in the dark.",
                       'Bribe industrial users to shut down factories temporarily', dict(headroom=-2.5, approval=-3, growth=-0.3, market=-4),
                       'Fire up decommissioned coal plants at massive expense', dict(headroom=-1.5, approval=4, netzero=-8, market=2),
                       'Allow rolling domestic blackouts to continue', dict(approval=-16, market=-8, growth=-0.2)),
                       
    'farming_collapse': C('🚨 BREAKING: Agricultural Collapse! A horrible harvest and post-Brexit red tape threatens domestic food supplies.',
                          "The farmers are threatening to drive their tractors down Whitehall, Chancellor.",
                          'Inject emergency subsidies directly to farming businesses', dict(headroom=-3.0, approval=5, inflation=-0.2),
                          'Drop all food import tariffs to secure cheap foreign produce', dict(market=6, approval=-4, inflation=-0.4, real_wages=-0.2),
                          'Do nothing and allow food prices to naturally spike', dict(approval=-10, inflation=0.8, market=-2)),

    'flash_crash': C('🚨 BREAKING: Currency Flash Crash! A rogue algorithmic trade has sent Sterling plummeting 10% in minutes.',
                     "The Pound has fallen off a cliff, Chancellor. Importers are panicking, exporters are rejoicing.",
                     'Order the BoE to burn foreign reserves to prop up the Pound', dict(headroom=-4.0, market=5, inflation=-0.2),
                     'Let the currency find its new natural floor', dict(market=-8, approval=-5, inflation=0.6, growth=0.2),
                     'Suspend trading on the London Stock Exchange temporarily', dict(market=-15, approval=-2, gilt=0.5)),

    'border_surge': C('🚨 BREAKING: Border Crisis! Record Channel crossings overwhelm processing and hotel capacity.',
                      "The Home Office has miscalculated again, Chancellor. We are out of hotel rooms.",
                      'Fund rapid processing and new returns deals', dict(headroom=-3.5, approval=5),
                      'Announce tougher deterrence with no extra funding', dict(approval=-4, homeless=3),
                      'Requisition disused military bases for basic camps', dict(headroom=-1, approval=2, homeless=1)),
    
    'student_loans': C('🚨 BREAKING: Student Loan Black Hole! The OBR warns a third of loans will never be repaid.',
                       "It turns out that lending billions of pounds to teenagers studying Media Studies was not a sound financial investment.",
                       'Write down loans and reform the system', dict(headroom=-4.5, approval=4, schools=2),
                       'Freeze the repayment threshold to claw money back', dict(headroom=3, approval=-7, real_wages=-0.2),
                       'Convert the loans into a permanent graduate tax', dict(approval=2, headroom=1.5, real_wages=-0.1)),
    
    'water_collapse': C('🚨 BREAKING: Water Giant on the Brink! A major water company warns it cannot service its debts.',
                        "A privatised monopoly has managed to bankrupt itself while selling something that literally falls from the sky.",
                        'Place it into special administration', dict(headroom=-4, approval=6, market=-4),
                        'Back a rescue funded by higher customer bills', dict(approval=-8, market=3, energy_bills=60),
                        'Impose fines and strip assets from the parent company', dict(approval=8, market=-6, energy_bills=10)),
    
    'winter_flu': C('🚨 BREAKING: Winter Flu Surge! A&E wards overflow and ambulances queue outside hospitals.',
                    "Winter has arrived, Chancellor. An entirely predictable annual event.",
                    'Fund emergency winter capacity', dict(headroom=-4, approval=5, nhs_waiting=-0.1, nhs_morale=3),
                    'Rely on existing winter plans', dict(approval=-9, nhs_waiting=0.3, nhs_morale=-5),
                    'Cancel elective surgeries and bring in military medics', dict(approval=-5, nhs_waiting=0.8, nhs_morale=-2)),
    
    'rating_warning': C('🚨 BREAKING: Credit Rating Warning! A major agency puts the UK on negative watch over weak public finances.',
                        "A group of young men in New York with spreadsheets have decided they do not like your economic strategy.",
                        'Publish a credible debt-reduction plan', dict(headroom=3, market=8, approval=-4),
                        'Dismiss the warning as politically motivated', dict(market=-10, gilt=0.5),
                        'Lobby the agency privately and promise future reforms', dict(market=-4, gilt=0.2)),

    # --- LINKED CRISES ---
    'capital_flight': C('🔗 LINKED REACTION: Your aggressive socialist policies have sparked a sudden flight of millionaires to Dublin and Frankfurt!',
                        "Chancellor, your policies have been deemed 'courageous' by the international elite.",
                        'Offer tax exemptions for multinational executives', dict(headroom=-4, market=10),
                        'Double down with emergency capital export controls', dict(market=-15, approval=6),
                        'Launch a patriotic investment bond to retain domestic capital', dict(headroom=-1, market=3, approval=2)),
    
    'utility_failure': C('🔗 LINKED REACTION: Your recent deregulation has caused private water and energy providers to suffer major infrastructure leaks!',
                         "It seems the 'invisible hand' of the market is currently covered in raw sewage, Chancellor.",
                         'Bail out the private operators with state emergency grants', dict(headroom=-5, approval=-6),
                         'Threaten forcible public receivership', dict(market=-12, approval=8),
                         'Impose severe regulatory fines and force executive resignations', dict(approval=5, market=-4, energy_bills=20)),
    
    'service_collapse': C('🔗 LINKED REACTION: Your deep departmental spending cuts have resulted in crumbling school roofs and prison overcrowding!',
                          "Chancellor, I did warn that cutting the maintenance budgets to zero might have physical consequences. Ceilings are falling in.",
                          'Issue emergency capital grants to patch facilities', dict(headroom=-4.5, approval=5, schools=4, prisons=-3),
                          'Maintain strict budget caps and ride out the public backlash', dict(approval=-10, market=5, schools=-5, prisons=4),
                          'Launch a public-private partnership rebuilding scheme', dict(headroom=-1, market=3, schools=2, prisons=-1)),

    'police_revolt': C('🔗 LINKED REACTION: Your spending freeze has pushed officers to the brink, and the Police Federation is threatening action!',
                       "The police are quite cross, Chancellor. It is generally considered poor form for a government to annoy the people holding the truncheons.",
                       'Fund a police pay settlement', dict(headroom=-3.5, approval=5, prisons=-2),
                       'Hold the line', dict(approval=-7, prisons=3),
                       'Bring in the army to cover essential duties', dict(approval=-9, prisons=5, market=-2)),
    
    'wage_spiral': C('🔗 LINKED REACTION: Giant public pay deals have de-anchored inflation expectations across the economy!',
                     "We gave them the money, they spent it, and now everything costs more. It is a terrifying concept called 'economics'.",
                     'Back the Bank of England with a tight fiscal squeeze', dict(headroom=3, approval=-6, inflation=-0.4, market=5),
                     'Let it ride and hope it fades', dict(inflation=0.6, market=-8, approval=-3),
                     'Implement a temporary freeze on all prices and rents', dict(approval=8, market=-12, inflation=-0.8, growth=-0.4)),
    
    'welfare_rebellion': C('🔗 LINKED REACTION: Your disability benefit cuts have sparked mass protests and a backbench revolt!',
                           "Taking money from the vulnerable was a bold move, Chancellor. Tragically, the public has noticed.",
                           'Reverse the harshest cuts', dict(headroom=-4, approval=8, child_poverty=-1),
                           'Press ahead regardless', dict(approval=-8, child_poverty=1.2),
                           'Tweak the criteria to exempt the most severe cases', dict(headroom=-1.5, approval=3, child_poverty=-0.2)),
    
    'council_bankrupt': C('🔗 LINKED REACTION: Your council spending cuts have pushed a major city council to issue a Section 114 bankruptcy notice!',
                          "A rather large local authority has officially run out of money, Chancellor. They are blaming central government cuts.",
                          'Bail the council out with a rescue package', dict(headroom=-4, approval=4, homeless=-4, schools=2),
                          'Let government commissioners impose cuts', dict(approval=-8, homeless=5, schools=-3),
                          'Allow them to raise local council tax above the legal cap', dict(approval=-6, market=2, schools=1)),
    
    'rail_collapse': C('🔗 LINKED REACTION: A private rail consortium has walked away, leaving services in chaos!',
                       "The private sector has discovered that running trains is terribly hard work, so they have handed the keys back.",
                       'Take the lines back into public operation', dict(headroom=-4.5, approval=6, rail=5),
                       'Find another bidder with a subsidy', dict(headroom=-2, market=2, approval=-4, rail=-4),
                       'Run a skeleton service using emergency bus replacements', dict(approval=-8, rail=-8, headroom=-0.5)),
    
    'greenbelt_revolt': C('🔗 LINKED REACTION: Rural MPs and councils are rebelling against mass development on protected land!',
                          "The shires are in revolt, Chancellor. The prospect of actual, physical houses being built near them has driven them to madness.",
                          'Offer communities a share of the gains', dict(headroom=-3, approval=3, homes_built=-5),
                          'Force the plans through', dict(approval=-8, homes_built=12, house_ratio=-0.1),
                          'Rebrand them as "Eco-Towns" with strict green criteria', dict(approval=2, homes_built=6, netzero=1)),
    
    'retaliation': C('🔗 LINKED REACTION: Your protectionist tariffs have triggered counter-tariffs on British exports!',
                     "It appears our trading partners did not appreciate our tariffs, Chancellor. They have retaliated.",
                     'Negotiate a rapid de-escalation deal', dict(headroom=-2, market=4, approval=-2, inflation=-0.1),
                     'Escalate and defend domestic industry', dict(approval=4, market=-8, inflation=0.4, real_wages=-0.3),
                     'File a lengthy WTO dispute and ride it out', dict(approval=-1, market=-2, growth=-0.1)),

    'school_crisis': C('📒 BUDGET FALLOUT: Dozens of schools close after safety warnings as education funding runs dry!',
                       "Chancellor, you slashed the education budget, and now the schools are structurally failing. I am shocked.",
                       'Fund emergency rebuilding', dict(headroom=-4.5, approval=5, schools=4),
                       'Move pupils into temporary units', dict(approval=-8, schools=-4),
                       'Force schools to adopt remote learning indefinitely', dict(approval=-12, schools=-8, real_wages=-0.1)),
    
    'defence_scare': C('📒 BUDGET FALLOUT: A leaked report reveals critical defence shortfalls as tensions rise abroad!',
                       "Your defence cuts have been leaked to the press, Chancellor. Apparently we cannot afford bullets.",
                       'Announce an emergency defence uplift', dict(headroom=-5, approval=3, market=3),
                       'Deny the report and defer spending', dict(approval=-6, market=-6),
                       'Reallocate funds from international aid to cover the gap', dict(approval=2, market=1, schools=-1)),
    
    'corp_exodus': C('📒 BUDGET FALLOUT: Firms announce plans to move their headquarters as high corporation tax bites!',
                     "The corporations are leaving, Chancellor. They have looked at your new tax rates and politely decided to incorporate in Ireland instead.",
                     'Offer a targeted tax relief package', dict(headroom=-3, market=7, growth=0.1),
                     'Hold firm on the tax rate', dict(market=-8, growth=-0.2, unemployment=0.15),
                     'Threaten them with exclusion from all future government contracts', dict(approval=5, market=-10, growth=-0.3)),
}

RANDOM_POOL = ['gilt_revolt', 'nhs_walkout', 'energy_bankruptcy', 'pension_hole', 'cyber_attack', 'floods', 'bank_run',
               'steel_closure', 'border_surge', 'student_loans', 'water_collapse', 'winter_flu', 'rating_warning',
               'prison_riot', 'ai_job_crisis', 'grid_blackout', 'farming_collapse', 'flash_crash']

IDEOLOGY_LINKS = {'Hard Left': 'capital_flight', 'Free-Market': 'utility_failure', 'Fiscal Austerity': 'service_collapse'}

DECISION_LINKS = {
    (1, 1, 'Hard Left'): ('gilt_revolt', 0.5), (1, 1, 'Fiscal Austerity'): ('police_revolt', 0.6),
    (1, 2, 'Hard Left'): ('wage_spiral', 0.6), (1, 2, 'Fiscal Austerity'): ('nhs_walkout', 0.7),
    (2, 1, 'Free-Market'): ('rating_warning', 0.5), (2, 1, 'Fiscal Austerity'): ('welfare_rebellion', 0.7),
    (2, 2, 'Free-Market'): ('bank_run', 0.5), (3, 1, 'Fiscal Austerity'): ('council_bankrupt', 0.7),
    (3, 1, 'Free-Market'): ('greenbelt_revolt', 0.6), (3, 2, 'Free-Market'): ('rail_collapse', 0.6),
    (4, 1, 'Fiscal Austerity'): ('energy_bankruptcy', 0.7), (4, 2, 'Hard Left'): ('retaliation', 0.6),
    (5, 1, 'Free-Market'): ('gilt_revolt', 0.6), (5, 2, 'Hard Left'): ('nhs_walkout', 0.7),
}

BUDGET_LINKS = [
    ('nhs_walkout', 'spend', 'health', '<=', -2.0, 0.35), ('school_crisis', 'spend', 'education', '<=', -2.0, 0.35),
    ('defence_scare', 'spend', 'defence', '<=', -2.0, 0.35), ('corp_exodus', 'tax', 'corp', '>=', 30, 0.35),
]

def get(crisis_id):
    return CRISES.get(crisis_id) if isinstance(crisis_id, str) else None

def pick_next(year, block, ideology):
    s = st.session_state
    s.crisis_reason = ''
    last = s.get('last_crisis')

    # 1. NEW: Check Political Capital Crises FIRST
    if s.get('party_opinion', 100) < 40 and last != 'leadership_challenge':
        s.crisis_reason = "🚨 Your party has lost faith in the government's direction!"
        s.last_crisis = 'leadership_challenge'
        return 'leadership_challenge'
        
    if s.get('media_opinion', 100) < 30 and last != 'tabloid_scandal':
        s.crisis_reason = "🚨 Fleet Street has turned against you!"
        s.last_crisis = 'tabloid_scandal'
        return 'tabloid_scandal'

    if s.get('market_conf', 100) < 35 and last != 'gilt_revolt' and random.random() < 0.6:
        s.crisis_reason = '🚨 Investors have lost faith in your fiscal credibility!'
        s.last_crisis = 'gilt_revolt'
        return 'gilt_revolt'

    if s.get('headroom', 0) < -10 and last != 'rating_warning' and random.random() < 0.5:
        s.crisis_reason = '🚨 Your fiscal rules are in tatters and the agencies have noticed.'
        s.last_crisis = 'rating_warning'
        return 'rating_warning'

    link = DECISION_LINKS.get((year, block, ideology))
    if link and random.random() < link[1]:
        s.crisis_reason = f'🔗 This follows directly from your last decision ({ideology}).'
        s.last_crisis = link[0]
        return link[0]

    if ideology in IDEOLOGY_LINKS and random.random() < 0.30:
        s.crisis_reason = f'🔗 Your {ideology} approach is coming back to bite you.'
        s.last_crisis = IDEOLOGY_LINKS[ideology]
        return IDEOLOGY_LINKS[ideology]

    applied = s.get('budget_applied')
    done = s.setdefault('fallout_done', [])
    if applied and s.get('dept_spend'):
        for cid, section, item, op, limit, chance in BUDGET_LINKS:
            if cid in done:
                continue
            if section == 'spend':
                # cumulative change in this department's baseline since the start, in %
                value = (s.dept_spend[item] / budget.SPEND_DEFAULTS[item]['default'] - 1) * 100
            else:
                value = applied[section][item]
            hit = value <= limit if op == '<=' else value >= limit
            if hit and random.random() < chance:
                done.append(cid)
                s.crisis_reason = '📒 Your budget choices have consequences.'
                s.last_crisis = cid
                return cid

    if year < 5 and random.random() < state.diff()['crisis']:
        options = [c for c in RANDOM_POOL if c != last] or RANDOM_POOL
        s.last_crisis = random.choice(options)
        s.crisis_reason = "🚨 Events, dear boy, events. An unforeseen crisis has struck!"
        return s.last_crisis
        
    return None

def _fmt(fx):
    parts = []
    if 'headroom' in fx: parts.append(f"{'-' if fx['headroom'] < 0 else '+'}£{abs(fx['headroom']):g}B Headroom")
    for key, name in (('approval', 'Approval'), ('market', 'Market Conf'), ('growth', 'Growth'),
                      ('inflation', 'Inflation'), ('deficit', 'Deficit'), ('debt', 'Debt'),
                      ('pm_opinion', 'PM'), ('cab_opinion', 'Cabinet'), ('party_opinion', 'Party'),
                      ('backbench_opinion', 'Backbench'), ('media_opinion', 'Media')):
        if key in fx: parts.append(f'{fx[key]:+g} {name}')
    return ', '.join(parts)

def option_labels(crisis):
    return [f'{label} ({_fmt(fx)})' if _fmt(fx) else label for label, fx in crisis['opts']]

def _clip(v):
    return max(0, min(100, v))

def apply_fx(fx):
    s = st.session_state
    sc = state.scale
    if 'headroom' in fx: s.headroom = round(s.headroom + sc(fx['headroom']), 1)
    if 'approval' in fx: s.approval = round(_clip(s.approval + sc(fx['approval'])), 1)
    if 'market' in fx: s.market_conf = round(_clip(s.market_conf + sc(fx['market'])), 1)
    if 'growth' in fx: s.growth = round(s.growth + fx['growth'], 2)
    if 'inflation' in fx: s.inflation = round(s.inflation + fx['inflation'], 2)
    if 'deficit' in fx: s.deficit = round(s.deficit + fx['deficit'], 1)
    if 'debt' in fx: s.debt = round(s.debt + fx['debt'], 1)
    if 'gilt' in fx: s.gilt_yield = round(s.gilt_yield + fx['gilt'], 2)
    # political capital (these keys were previously ignored)
    for key in ('pm_opinion', 'cab_opinion', 'party_opinion', 'backbench_opinion', 'media_opinion'):
        if key in fx:
            s[key] = round(_clip(s[key] + fx[key]), 1)

    # Pass direct effects down to the country file too!
    country.nudge({k: v for k, v in fx.items() if k in country.STATS}, snapshot=False)


def proxy_ideology(fx):
    """Rough ideological flavour of a crisis response, judged by what it does."""
    head, app, mkt = fx.get('headroom', 0), fx.get('approval', 0), fx.get('market', 0)
    if head <= -3 and app > 0:
        return 'Social Democratic' if mkt >= -4 else 'Hard Left'
    if head > 0 and app < 0:
        return 'Fiscal Austerity'
    if mkt > 0 and app < 0:
        return 'Free-Market'
    return 'Centric'


def resolve(crisis, index):
    label, fx = crisis['opts'][index]
    apply_fx(fx)
    
    if 'last_humphrey_quote' not in st.session_state:
        st.session_state.last_humphrey_quote = ""
        
    humphrey_replies = [
        "A very courageous decision, Chancellor.",
        "Quite so, Chancellor. I shall draft a press release meaning absolutely nothing.",
        "I foresee immense administrative complications, but I shall execute your will, Chancellor.",
        "A bold strategy, Chancellor. The exact strategy, in fact, that ruined your predecessor.",
        "Yes, Chancellor. In the fullness of time, this may even prove to have been the right choice.",
        "If you insist, Chancellor. Though I must point out that in government, doing nothing is often the most productive course of action.",
        "Excellent, Chancellor. We shall set up an interdepartmental committee to monitor the implementation. That should delay it indefinitely.",
        "As you wish, Chancellor. I shall instruct the civil service to proceed with all deliberate lack of speed.",
        "A triumph of hope over experience, Chancellor.",
        "To be perfectly frank, Chancellor, the Treasury views this decision with a mixture of horror and profound amusement.",
        "I am fully seized of your instructions, Chancellor, and will implement them with the exact degree of enthusiasm they warrant.",
        "An interesting approach. Usually, when one is in a hole, one stops digging. But you have asked for a larger shovel."
    ]
    
    available_replies = [r for r in humphrey_replies if r != st.session_state.last_humphrey_quote]
    chosen_quote = random.choice(available_replies)
    st.session_state.last_humphrey_quote = chosen_quote
    
    return f"<b>Crisis handled: {label}</b><br><br><i>Sir Humphrey Appleby adds:</i> &ldquo;{chosen_quote}&rdquo;"
