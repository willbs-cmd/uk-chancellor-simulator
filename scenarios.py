import random
import streamlit as st
import country

def C(title, humphrey, a, afx, b, bfx):
    """A crisis with two responses, each with its own effects, plus Humphrey's advice."""
    return dict(title=title, humphrey=humphrey, opts=[(a, afx), (b, bfx)])

CRISES = {
    'gilt_revolt': C('🚨 BREAKING: Severe Gilt Market Revolt! Foreign investors dump UK debt as yields surge past 5.5%.',
                     "Chancellor, the bond markets have taken a sudden and profound dislike to us. If we do not intervene, we may find ourselves in the rather novel position of national bankruptcy. A highly courageous moment.",
                     'Deploy emergency Bank of England intervention', dict(headroom=-7, market=8, gilt=-0.4),
                     'Refuse intervention and let bond vigilantes feast', dict(market=-18, debt=2.5, gilt=0.8)),
    
    'nhs_walkout': C('🚨 BREAKING: National Health Service Staff Walkout! Nurses and junior doctors launch coordinated strikes.',
                     "The medical practitioners have opted for a spontaneous cessation of labour, Chancellor. We could pay them, but that would set a terrifying precedent: rewarding people for complaining.",
                     'Meet pay demands in full to avoid collapse', dict(headroom=-6, approval=10, inflation=0.4, nhs_morale=8),
                     'Stand firm and invoke emergency service minimums', dict(approval=-12, growth=-0.3, nhs_morale=-10, nhs_waiting=0.4)),
    
    'energy_bankruptcy': C('🚨 BREAKING: Major Energy Retailer Bankruptcy! State bailout required to keep lights on.',
                           "An energy firm has carelessly misplaced its capital, Chancellor. We can bail them out, or we can let the free market freeze the electorate. I leave the optics entirely to you.",
                           'Absorb company liabilities into public balance sheet', dict(headroom=-5, approval=6, energy_bills=-40),
                           'Let customers scatter to higher tariffs', dict(approval=-9, inflation=0.5, energy_bills=120)),
    
    'pension_hole': C('🚨 BREAKING: Public Sector Pension Black Hole Discovered! OBR mandates immediate funding correction.',
                      "It appears there is a slight discrepancy in the pension fund. A 'black hole', the tabloids call it. I prefer to think of it as a deferred negative asset. Regrettably, the OBR insists we fill it.",
                      'Inject emergency cash reserves to plug shortfall', dict(headroom=-5.5, market=5),
                      'Cut departmental budgets across the board', dict(approval=-10, market=4, schools=-3, nhs_morale=-3)),

    'cyber_attack': C('🚨 BREAKING: Major Cyber Attack! HMRC and NHS systems are knocked offline by a hostile state actor.',
                      "Our computer systems have been compromised, Chancellor. Apparently 'Password123' was not as robust as the IT department claimed. We must throw money at the problem immediately so we appear to be doing something.",
                      'Fund an emergency national cyber-security overhaul', dict(headroom=-4, market=4, approval=2),
                      'Restore systems quietly and hope it does not recur', dict(approval=-6, market=-8, nhs_waiting=0.2)),
    
    'floods': C('🚨 BREAKING: Catastrophic Winter Floods! Thousands of homes and several northern towns are underwater.',
                "It is raining, Chancellor. And unfortunately, the water has decided to gather in places where people live. The Prime Minister will need wellington boots and a very large chequebook.",
                'Launch a national flood recovery and defence fund', dict(headroom=-5, approval=8, netzero=2),
                'Leave recovery to councils and insurers', dict(approval=-10, homeless=8)),
    
    'bank_run': C('🚨 BREAKING: Regional Bank Run! Depositors queue outside a mid-sized lender as confidence evaporates.',
                  "The public has decided to withdraw their money from the banks all at once. An annoying habit they have when panicked. If we don't guarantee the deposits, the contagion will be quite spectacular.",
                  'Guarantee all deposits to stop contagion', dict(headroom=-6, market=6, approval=3),
                  'Let it fail under the resolution regime', dict(market=-10, approval=-6, unemployment=0.1)),
    
    'steel_closure': C('🚨 BREAKING: Last Blast Furnace to Close! Thousands of jobs are at risk in a former industrial heartland.',
                       "Heavy industry is heavy, Chancellor. And expensive. Nationalising it would save jobs but ruin the balance sheet. Letting it collapse would ruin the jobs but save the balance sheet. A classic Treasury win-win.",
                       'Nationalise the plant to save the jobs', dict(headroom=-4, approval=7, market=-3),
                       'Let the market decide', dict(approval=-8, market=3, unemployment=0.2)),
    
    'border_surge': C('🚨 BREAKING: Border Crisis! Record Channel crossings overwhelm processing and hotel capacity.',
                      "The Home Office has miscalculated again, Chancellor. We are out of hotel rooms. They are asking for more money to process the backlog, which they will inevitably use to create a larger backlog.",
                      'Fund rapid processing and new returns deals', dict(headroom=-3.5, approval=5),
                      'Announce tougher deterrence with no extra funding', dict(approval=-4, homeless=3)),
    
    'student_loans': C('🚨 BREAKING: Student Loan Black Hole! The OBR warns a third of loans will never be repaid.',
                       "It turns out that lending billions of pounds to teenagers studying Media Studies was not a sound financial investment. We must either write the debt off or attempt to squeeze blood from a stone.",
                       'Write down loans and reform the system', dict(headroom=-4.5, approval=4, schools=2),
                       'Freeze the repayment threshold to claw money back', dict(headroom=3, approval=-7, real_wages=-0.2)),
    
    'water_collapse': C('🚨 BREAKING: Water Giant on the Brink! A major water company warns it cannot service its debts.',
                        "A privatised monopoly has managed to bankrupt itself while selling something that literally falls from the sky. It takes a special kind of genius. Shall we bail out the shareholders or face the public stench?",
                        'Place it into special administration', dict(headroom=-4, approval=6, market=-4),
                        'Back a rescue funded by higher customer bills', dict(approval=-8, market=3, energy_bills=60)),
    
    'winter_flu': C('🚨 BREAKING: Winter Flu Surge! A&E wards overflow and ambulances queue outside hospitals.',
                    "Winter has arrived, Chancellor. An entirely predictable annual event that catches the Department of Health completely by surprise every single year. They demand emergency funding. Again.",
                    'Fund emergency winter capacity', dict(headroom=-4, approval=5, nhs_waiting=-0.1, nhs_morale=3),
                    'Rely on existing winter plans', dict(approval=-9, nhs_waiting=0.3, nhs_morale=-5)),
    
    'rating_warning': C('🚨 BREAKING: Credit Rating Warning! A major agency puts the UK on negative watch over weak public finances.',
                        "A group of young men in New York with spreadsheets have decided they do not like your economic strategy, Chancellor. If they downgrade us, borrowing costs will soar. We must soothe them with austerity.",
                        'Publish a credible debt-reduction plan', dict(headroom=3, market=8, approval=-4),
                        'Dismiss the warning as politically motivated', dict(market=-10, gilt=0.5)),

    'capital_flight': C('🔗 LINKED REACTION (Capital Flight): Your aggressive socialist policies have sparked a sudden flight of millionaires and corporate HQs to Dublin and Frankfurt!',
                        "Chancellor, your policies have been deemed 'courageous' by the international elite. They are currently expressing their admiration by relocating their assets to Frankfurt. Shall we stop them, or tax the ones left behind?",
                        'Offer tax exemptions for multinational executives', dict(headroom=-4, market=10),
                        'Double down with emergency capital export controls', dict(market=-15, approval=6)),
    
    'utility_failure': C('🔗 LINKED REACTION (Private Utility Failure): Your recent deregulation has caused private water and energy providers to suffer major infrastructure leaks and sewage scandals!',
                         "It seems the 'invisible hand' of the market is currently covered in raw sewage, Chancellor. The utilities are failing. We can bail them out, or threaten them with nationalisation.",
                         'Bail out the private operators with state emergency grants', dict(headroom=-5, approval=-6),
                         'Threaten forcible public receivership', dict(market=-12, approval=8)),
    
    'service_collapse': C('🔗 LINKED REACTION (Public Service Collapse): Your deep departmental spending cuts have resulted in crumbling school roofs and prison overcrowding emergencies!',
                          "Chancellor, I did warn that cutting the maintenance budgets to zero might have physical consequences. Ceilings are falling in. Literally. We must patch them up before a minister is hit by debris.",
                          'Issue emergency capital grants to patch facilities', dict(headroom=-4.5, approval=5, schools=4, prisons=-3),
                          'Maintain strict budget caps and ride out the public backlash', dict(approval=-10, market=5, schools=-5, prisons=4)),

    'police_revolt': C('🔗 LINKED REACTION (Police Revolt): Your spending freeze has pushed officers to the brink, and the Police Federation is threatening industrial action!',
                       "The police are quite cross, Chancellor. It is generally considered poor form for a government to annoy the people holding the truncheons. Shall we find some spare change for them?",
                       'Fund a police pay settlement', dict(headroom=-3.5, approval=5, prisons=-2),
                       'Hold the line', dict(approval=-7, prisons=3)),
    
    'wage_spiral': C('🔗 LINKED REACTION (Wage-Price Spiral): Giant public pay deals have de-anchored inflation expectations across the economy!',
                     "We gave them the money, they spent it, and now everything costs more. It is a terrifying concept called 'economics', Chancellor. The Bank of England suggests we squeeze the life out of the economy to fix it.",
                     'Back the Bank of England with a tight fiscal squeeze', dict(headroom=3, approval=-6, inflation=-0.4, market=5),
                     'Let it ride and hope it fades', dict(inflation=0.6, market=-8, approval=-3)),
    
    'welfare_rebellion': C('🔗 LINKED REACTION (Welfare Rebellion): Your disability benefit cuts have sparked mass protests and a backbench revolt!',
                           "Taking money from the vulnerable was a bold move, Chancellor. Tragically, the public has noticed. Even your own MPs are developing a conscience. I suggest a strategic U-turn.",
                           'Reverse the harshest cuts', dict(headroom=-4, approval=8, child_poverty=-1),
                           'Press ahead regardless', dict(approval=-8, child_poverty=1.2)),
    
    'council_bankrupt': C('🔗 LINKED REACTION (Council Bankruptcy): Your council spending cuts have pushed a major city council to issue a Section 114 notice!',
                          "A rather large local authority has officially run out of money, Chancellor. They are blaming central government cuts. Outrageous, I know. Shall we send in the commissioners to slash the libraries?",
                          'Bail the council out with a rescue package', dict(headroom=-4, approval=4, homeless=-4, schools=2),
                          'Let government commissioners impose cuts', dict(approval=-8, homeless=5, schools=-3)),
    
    'rail_collapse': C('🔗 LINKED REACTION (Rail Franchise Collapse): A private rail consortium has walked away, leaving services in chaos!',
                       "The private sector has discovered that running trains is terribly hard work, so they have handed the keys back to the Department for Transport. Shall we run them ourselves, or bribe someone else to do it?",
                       'Take the lines back into public operation', dict(headroom=-4.5, approval=6, rail=5),
                       'Find another bidder with a subsidy', dict(headroom=-2, market=2, approval=-4, rail=-4)),
    
    'greenbelt_revolt': C('🔗 LINKED REACTION (Greenbelt Backlash): Rural MPs and councils are rebelling against mass development on protected land!',
                          "The shires are in revolt, Chancellor. The prospect of actual, physical houses being built near them has driven them to madness. We must either back down, or bulldoze their objections.",
                          'Offer communities a share of the gains', dict(headroom=-3, approval=3, homes_built=-5),
                          'Force the plans through', dict(approval=-8, homes_built=12, house_ratio=-0.1)),
    
    'retaliation': C('🔗 LINKED REACTION (Trade Retaliation): Your protectionist tariffs have triggered counter-tariffs on British exports!',
                     "It appears our trading partners did not appreciate our tariffs, Chancellor. They have retaliated. The Foreign Secretary is apoplectic. Shall we escalate to a full trade war?",
                     'Negotiate a rapid de-escalation deal', dict(headroom=-2, market=4, approval=-2, inflation=-0.1),
                     'Escalate and defend domestic industry', dict(approval=4, market=-8, inflation=0.4, real_wages=-0.3)),

    'school_crisis': C('📒 BUDGET FALLOUT: Dozens of schools close after safety warnings as education funding runs dry!',
                       "Chancellor, you slashed the education budget, and now the schools are structurally failing. I am shocked. If we don't fix them, the children will have to be educated in tents.",
                       'Fund emergency rebuilding', dict(headroom=-4.5, approval=5, schools=4),
                       'Move pupils into temporary units', dict(approval=-8, schools=-4)),
    
    'defence_scare': C('📒 BUDGET FALLOUT: A leaked report reveals critical defence shortfalls as tensions rise abroad!',
                       "Your defence cuts have been leaked to the press, Chancellor. Apparently we cannot afford bullets. The military top brass are demanding money. A very courageous budget, in hindsight.",
                       'Announce an emergency defence uplift', dict(headroom=-5, approval=3, market=3),
                       'Deny the report and defer spending', dict(approval=-6, market=-6)),
    
    'corp_exodus': C('📒 BUDGET FALLOUT: Firms announce plans to move their headquarters as high corporation tax bites!',
                     "The corporations are leaving, Chancellor. They have looked at your new tax rates and politely decided to incorporate in Ireland instead. A triumph for the Treasury's revenue projections, I'm sure.",
                     'Offer a targeted tax relief package', dict(headroom=-3, market=7, growth=0.1),
                     'Hold firm on the tax rate', dict(market=-8, growth=-0.2, unemployment=0.15)),
}

RANDOM_POOL = ['gilt_revolt', 'nhs_walkout', 'energy_bankruptcy', 'pension_hole', 'cyber_attack', 'floods', 'bank_run',
               'steel_closure', 'border_surge', 'student_loans', 'water_collapse', 'winter_flu', 'rating_warning']

IDEOLOGY_LINKS = {'Hard Left': 'capital_flight', 'Free-Market': 'utility_failure', 'Fiscal Austerity': 'service_collapse'}

DECISION_LINKS = {
    (1, 1, 'Hard Left'): ('gilt_revolt', 0.5), (1, 1, 'Fiscal Austerity'): ('police_revolt', 0.6),
    (1, 2, 'Hard Left'): ('wage_spiral', 0.6), (1, 2, 'Fiscal Austerity'): ('nhs_walkout', 0.7),
    (1, 3, 'Free-Market'): ('rating_warning', 0.5), (2, 1, 'Fiscal Austerity'): ('welfare_rebellion', 0.7),
    (2, 2, 'Free-Market'): ('bank_run', 0.5), (2, 3, 'Fiscal Austerity'): ('council_bankrupt', 0.7),
    (3, 1, 'Free-Market'): ('rail_collapse', 0.6), (3, 2, 'Free-Market'): ('greenbelt_revolt', 0.6),
    (4, 1, 'Fiscal Austerity'): ('energy_bankruptcy', 0.7), (4, 2, 'Hard Left'): ('retaliation', 0.6),
    (4, 3, 'Free-Market'): ('gilt_revolt', 0.6), (5, 1, 'Free-Market'): ('nhs_walkout', 0.7),
}

BUDGET_LINKS = [
    ('nhs_walkout', 'spend', 'health', '<=', 195, 0.35), ('school_crisis', 'spend', 'education', '<=', 110, 0.35),
    ('defence_scare', 'spend', 'defence', '<=', 55, 0.35), ('corp_exodus', 'tax', 'corp', '>=', 30, 0.35),
]

def get(crisis_id):
    return CRISES.get(crisis_id) if isinstance(crisis_id, str) else None

def pick_next(year, block, ideology):
    s = st.session_state
    s.crisis_reason = ''
    last = s.get('last_crisis')

    link = DECISION_LINKS.get((year, block, ideology))
    if link and random.random() < link[1]:
        s.crisis_reason = f'🔗 This follows directly from your last decision ({ideology}).'
        s.last_crisis = link[0]
        return link[0]

    if ideology in IDEOLOGY_LINKS and random.random() < 0.30:
        s.crisis_reason = f'🔗 Your {ideology} approach is coming back to bite you.'
        s.last_crisis = IDEOLOGY_LINKS[ideology]
        return IDEOLOGY_LINKS[ideology]

    budget = s.get('budget_applied')
    if budget:
        for cid, section, item, op, limit, chance in BUDGET_LINKS:
            value = budget[section][item]
            hit = value <= limit if op == '<=' else value >= limit
            if hit and random.random() < chance:
                s.crisis_reason = '📒 Your budget choices have consequences.'
                s.last_crisis = cid
                return cid

    if year < 5 and random.random() < 0.35:
        options = [c for c in RANDOM_POOL if c != last] or RANDOM_POOL
        s.last_crisis = random.choice(options)
        return s.last_crisis
    return None

def _fmt(fx):
    parts = []
    if 'headroom' in fx: parts.append(f"{'-' if fx['headroom'] < 0 else '+'}£{abs(fx['headroom']):g}B Headroom")
    for key, name in (('approval', 'Approval'), ('market', 'Market Conf'), ('growth', 'Growth'),
                      ('inflation', 'Inflation'), ('deficit', 'Deficit'), ('debt', 'Debt')):
        if key in fx: parts.append(f'{fx[key]:+g} {name}')
    return ', '.join(parts)

def option_labels(crisis):
    return [f'{label} ({_fmt(fx)})' if _fmt(fx) else label for label, fx in crisis['opts']]

def _clip(v):
    return max(0, min(100, v))

def apply_fx(fx):
    s = st.session_state
    if 'headroom' in fx: s.headroom = round(s.headroom + fx['headroom'], 1)
    if 'approval' in fx: s.approval = round(_clip(s.approval + fx['approval']), 1)
    if 'market' in fx: s.market_conf = round(_clip(s.market_conf + fx['market']), 1)
    if 'growth' in fx: s.growth = round(s.growth + fx['growth'], 2)
    if 'inflation' in fx: s.inflation = round(s.inflation + fx['inflation'], 2)
    if 'deficit' in fx: s.deficit = round(s.deficit + fx['deficit'], 1)
    if 'debt' in fx: s.debt = round(s.debt + fx['debt'], 1)
    if 'gilt' in fx: s.gilt_yield = round(s.gilt_yield + fx['gilt'], 2)
    country.nudge({k: v for k, v in fx.items() if k in country.STATS})

def resolve(crisis, index):
    label, fx = crisis['opts'][index]
    apply_fx(fx)
    
    # Initialize the memory for Humphrey so he never repeats himself back-to-back
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
        "An interesting approach. Usually, when one is in a hole, one stops digging. But you have asked for a larger shovel.",
        "We must be very careful not to let the electorate know we've done this. It might give them ideas.",
        "Quite, Chancellor. A decision that will echo through the corridors of power... mostly in whispers of disbelief.",
        "I shall ensure the implementation is sufficiently complex so that no one can ever trace the blame back to you."
    ]
    
    # Filter out the last used quote
    available_replies = [r for r in humphrey_replies if r != st.session_state.last_humphrey_quote]
    
    chosen_quote = random.choice(available_replies)
    st.session_state.last_humphrey_quote = chosen_quote
    
    return f"**Crisis handled: {label}**<br><br>*Sir Humphrey Appleby adds:* \"{chosen_quote}\""
