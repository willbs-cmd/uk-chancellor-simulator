import streamlit as st
from theme import stat_card

STATS = {
    'nhs_waiting': {'label': 'NHS Waiting List', 'unit': 'm', 'default': 7.5, 'min': 2.0, 'max': 12.0, 'invert': True, 'desc': 'Total number of people waiting for routine hospital treatments.'},
    'nhs_morale': {'label': 'NHS Staff Morale', 'unit': '%', 'default': 45.0, 'min': 0.0, 'max': 100.0, 'invert': False, 'desc': 'Satisfaction and retention rates among frontline healthcare workers.'},
    'schools': {'label': 'School Attainment Gap', 'unit': 'pts', 'default': 30.0, 'min': 10.0, 'max': 60.0, 'invert': True, 'desc': 'The educational gap between disadvantaged pupils and their peers.'},
    'child_poverty': {'label': 'Child Poverty Rate', 'unit': '%', 'default': 29.0, 'min': 10.0, 'max': 50.0, 'invert': True, 'desc': 'Percentage of children living in relative poverty.'},
    'homeless': {'label': 'Homelessness', 'unit': 'k', 'default': 110.0, 'min': 30.0, 'max': 250.0, 'invert': True, 'desc': 'Number of households in temporary accommodation or sleeping rough.'},
    'homes_built': {'label': 'Annual Homes Built', 'unit': 'k', 'default': 180.0, 'min': 50.0, 'max': 400.0, 'invert': False, 'desc': 'Total new housing supply added this year.'},
    'prisons': {'label': 'Prison Capacity', 'unit': '%', 'default': 99.0, 'min': 70.0, 'max': 150.0, 'invert': True, 'desc': 'Current prison population as a percentage of safe capacity.'},
    'rail': {'label': 'Rail Reliability', 'unit': '%', 'default': 65.0, 'min': 30.0, 'max': 95.0, 'invert': False, 'desc': 'Percentage of national rail services arriving on time.'},
    'netzero': {'label': 'Net Zero Progress', 'unit': '%', 'default': 40.0, 'min': 0.0, 'max': 100.0, 'invert': False, 'desc': 'Pace of transition toward 2050 carbon neutrality targets.'},
    'energy_bills': {'label': 'Avg Energy Bill', 'unit': '£', 'default': 1900.0, 'min': 800.0, 'max': 5000.0, 'invert': True, 'desc': 'The average annual household gas and electricity bill.'},
}

def _overall(c_state):
    score = 0
    for k, v in STATS.items():
        val = c_state.get(k, v['default'])
        norm = (val - v['min']) / (v['max'] - v['min'])
        if v['invert']: norm = 1.0 - norm
        score += max(0.0, min(1.0, norm))
    return score / len(STATS)

def nudge(effects, snapshot=True):
    if 'country' not in st.session_state:
        st.session_state.country = {k: v['default'] for k, v in STATS.items()}
    if 'country_prev' not in st.session_state:
        st.session_state.country_prev = dict(st.session_state.country)
        
    if snapshot:
        st.session_state.country_prev = dict(st.session_state.country)
        
    for k, v in effects.items():
        if k in STATS:
            st.session_state.country[k] = max(STATS[k]['min'], min(STATS[k]['max'], st.session_state.country[k] + v))

def apply_decision(ideology):
    drift = {
        'Hard Left': {'nhs_morale': 2.0, 'child_poverty': -1.0, 'netzero': 1.0},
        'Social Democratic': {'nhs_waiting': -0.1, 'schools': -0.5, 'homeless': -2.0},
        'Centric': {'homes_built': 5.0, 'rail': 1.0},
        'Free-Market': {'homes_built': 10.0, 'energy_bills': -50.0, 'child_poverty': 1.0},
        'Fiscal Austerity': {'nhs_waiting': 0.2, 'prisons': 2.0, 'homeless': 5.0, 'nhs_morale': -2.0}
    }
    if ideology in drift:
        nudge(drift[ideology], snapshot=False)

def render():
    s = st.session_state
    if 'country' not in s:
        s.country = {k: v['default'] for k, v in STATS.items()}
    if 'country_prev' not in s:
        s.country_prev = dict(s.country)

    st.markdown("### 🇬🇧 State of the Nation")
    st.caption("Key domestic metrics. These shift dynamically based on your budget spending and policy decisions.")
    
    cols = st.columns(2)
    for i, (k, info) in enumerate(STATS.items()):
        val = s.country[k]
        prev = s.country_prev[k]
        diff = val - prev
        
        unit = info['unit']
        if unit == '£':
            v_str = f"£{val:,.0f}"
            d_str = f"{diff:+,.0f}"
        elif unit in ['m', '%', 'pts']:
            v_str = f"{val:.1f}{unit}"
            d_str = f"{diff:+.1f}{unit}"
        else: # 'k'
            v_str = f"{val:,.0f}k"
            d_str = f"{diff:+,.0f}k"
            
        if abs(diff) < 0.05:
            d_str = "0"
            
        card_html = stat_card(info['label'], v_str, d_str, info['desc'], diff, inverse=info['invert'])
        cols[i % 2].markdown(card_html, unsafe_allow_html=True)
