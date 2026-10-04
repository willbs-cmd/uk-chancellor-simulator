"""Endings and achievements. Checked when an election result (or a sacking) is reached."""
import streamlit as st

import country

ENDINGS = {
    'landslide': ('Landslide Triumph', 'The country has spoken, and it said yes. Emphatically.'),
    'majority': ('A Working Majority', 'Not a landslide, but a government that can actually govern.'),
    'coalition': ('Coalition of the Willing', 'Power is shared, and so is the blame.'),
    'minority': ('Minority Report', 'You cling to office on a wing, a prayer and a confidence-and-supply deal.'),
    'regional': ('Kingmaker', 'Your regional movement holds the keys to Westminster.'),
    'lost': ('Evicted from Downing Street', 'The electorate has shown you the door. The removal vans are already outside.'),
    'sacked': ('Sacked in Disgrace', 'The Prime Minister has decided your talents are best employed elsewhere. Anywhere else.'),
    'resigned': ('Resigned', 'You walked away from the Treasury. The memoirs write themselves.'),
}


def _counts():
    return st.session_state.get('ideology_counts', {})


# id: (name, description, check(state, result))
ACHIEVEMENTS = {
    'landslide': ('Landslide Victory', 'Win a majority of 100+ seats.',
                  lambda s, r: r['win'] and not r['sacked'] and r['kind'] == 'majority' and r['margin'] >= 100),
    'books': ('Balanced the Books', 'Reach election night with a surplus or £15B+ of headroom.',
              lambda s, r: s.headroom >= 15 or s.deficit <= 0),
    'city': ('Darling of the City', 'Finish a term with market confidence of 80+.',
             lambda s, r: s.market_conf >= 80),
    'peoples': ("The People's Chancellor", 'Child poverty under 27% and the NHS waiting list under 6.5m.',
                lambda s, r: s.country['child_poverty'] < 27 and s.country['nhs_waiting'] < 6.5),
    'purist': ('Ideological Purist', 'Make 7+ decisions from the same ideology in one term.',
               lambda s, r: max(_counts().values() or [0]) >= 7),
    'humphrey': ("Humphrey's Favourite", 'Pick the Centric option 6+ times in one term.',
                 lambda s, r: _counts().get('Centric', 0) >= 6),
    'crisis': ('Crisis Manager', 'Resolve 5+ crises in one term.',
               lambda s, r: s.crises_handled >= 5),
    'odds': ('Against the Odds', 'Win with public approval below 40%.',
             lambda s, r: r['win'] and not r['sacked'] and s.approval < 40),
    'dynasty': ('Dynasty', 'Win a second term.',
                lambda s, r: r['win'] and not r['sacked'] and s.term >= 2),
    'builder': ('Builder in Chief', 'Reach 300k+ new homes a year.',
                lambda s, r: s.country['homes_built'] >= 300),
    'green': ('Green Chancellor', 'Reach 60%+ net zero progress.',
              lambda s, r: s.country['netzero'] >= 60),
    'grade_a': ('State of Excellence', 'Finish a term with an A grade for the State of the Nation.',
                lambda s, r: country._overall(s.country) * 100 >= 70),
    'sacked': ('Persona Non Grata', 'Get sacked.', lambda s, r: r['sacked']),
}


def evaluate(result):
    """Return the ids of achievements earned by this result that weren't held before."""
    s = st.session_state
    held = set(s.get('achievements', []))
    new = []
    for aid, (_, _, check) in ACHIEVEMENTS.items():
        if aid not in held:
            try:
                if check(s, result):
                    new.append(aid)
            except (KeyError, AttributeError, TypeError):
                pass
    s.achievements = sorted(held | set(new))
    s.new_achievements = new
    return new


def ending_for(result):
    if result['sacked']:
        return ENDINGS['sacked']
    if not result['win']:
        return ENDINGS['lost']
    kind = result['kind']
    if kind == 'majority' and result['margin'] >= 100:
        return ENDINGS['landslide']
    return ENDINGS.get(kind, ENDINGS['majority'])
