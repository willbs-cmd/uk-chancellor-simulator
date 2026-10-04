import pandas as pd
import streamlit as st
import altair as alt
import country
import state

TAXES = {
    'income':   dict(label='Income tax, basic rate (p in the £)', short='Income tax', default=20, lo=5, hi=45, step=1, base=300.0, per=7.5, decay=0.02),
    'ni':       dict(label='National Insurance rate (%)', short='National Insurance', default=15, lo=0, hi=30, step=1, base=190.0, per=9.0, decay=0.04),
    'vat':      dict(label='VAT (%)', short='VAT', default=20, lo=5, hi=35, step=1, base=170.0, per=8.0, decay=0.04),
    'corp':     dict(label='Corporation tax (%)', short='Corporation tax', default=25, lo=5, hi=45, step=1, base=90.0, per=2.5, decay=0.04),
    'property': dict(label='Property & wealth taxes (% change)', short='Property taxes', default=0, lo=-50, hi=100, step=5, base=110.0, per=1.1, decay=0.004),
}

TAX_POLICIES = {
    'vat_private': dict(label='Apply VAT to Private School Fees', yield_bn=1.5, app=1, mkt=-1, gro=0),
    'nondom':      dict(label='Scrap Non-Dom Tax Status', yield_bn=2.5, app=2, mkt=-2, gro=0),
    'windfall':    dict(label='Windfall Tax on Energy Firms', yield_bn=4.0, app=3, mkt=-3, gro=-0.1),
    'wealth':      dict(label='1% Wealth Tax on assets >£10m', yield_bn=9.0, app=4, mkt=-6, gro=-0.2),
}

OTHER_RECEIPTS = 290.0  

SPEND_DEFAULTS = {
    'welfare':   dict(label='Welfare & pensions', short='Welfare & pensions', default=330.0),
    'health':    dict(label='NHS & health', short='NHS & health', default=215.0),
    'education': dict(label='Education', short='Education', default=125.0),
    'defence':   dict(label='Defence', short='Defence', default=62.0),
    'transport': dict(label='Transport & infrastructure', short='Transport & infrastructure', default=48.0),
    'justice':   dict(label='Policing, courts & prisons', short='Policing, courts & prisons', default=45.0),
    'housing':   dict(label='Housing & local government', short='Housing & local government', default=60.0),
    'climate':   dict(label='Climate, energy & industry', short='Climate, energy & industry', default=35.0),
    'other':     dict(label='Other departments & admin', short='Other departments & admin', default=130.0),
}

SPEND_POLICIES = {
    'hs2':       dict(label='Revive Full HS2 Rail Project', cost_bn=8.0, app=2, mkt=0, gro=0.2),
    'meals':     dict(label='Universal Free School Meals', cost_bn=2.5, app=3, mkt=0, gro=0),
    'child_cap': dict(label='Scrap Two-Child Benefit Limit', cost_bn=3.0, app=2, mkt=-1, gro=0),
    'water':     dict(label='Nationalise Water Companies', cost_bn=10.0, app=5, mkt=-4, gro=0),
}

BASE_INTEREST = 105.4 

PALETTE = ['#c9a45c', '#6fbf8a', '#4f8fba', '#d6604f', '#9a7fc4', '#e0b0a0', '#7fb8b0', '#c4c46f', '#8aa0a0', '#d98cb3', '#444444', '#777777']

def defaults():
    return {
        'tax': {k: v['default'] for k, v in TAXES.items()},
        'spend': {k: 0.0 for k in SPEND_DEFAULTS},
        'tax_pol': {k: False for k in TAX_POLICIES},
        'spend_pol': {k: False for k in SPEND_POLICIES}
    }

def ensure():
    s = st.session_state
    if 'dept_spend' not in s:
        s.dept_spend = {k: v['default'] for k, v in SPEND_DEFAULTS.items()}

    if 'budget_applied' not in s or 'tax_pol' not in s.get('budget_applied', {}):
        s.budget_applied = defaults()
        s.budget_interest = BASE_INTEREST
        
    for k, v in s.budget_applied['tax'].items(): s.setdefault(f'bt_{k}', v)
    for k, v in s.budget_applied['spend'].items(): s.setdefault(f'bs_{k}', float(v))
    for k, v in s.budget_applied['tax_pol'].items(): s.setdefault(f'btp_{k}', v)
    for k, v in s.budget_applied['spend_pol'].items(): s.setdefault(f'bsp_{k}', v)

def read():
    s = st.session_state
    return {
        'tax': {k: s[f'bt_{k}'] for k in TAXES},
        'spend': {k: float(s[f'bs_{k}']) for k in SPEND_DEFAULTS},
        'tax_pol': {k: s[f'btp_{k}'] for k in TAX_POLICIES},
        'spend_pol': {k: s[f'bsp_{k}'] for k in SPEND_POLICIES}
    }

def revenues(b):
    out = {}
    for k, t in TAXES.items():
        d = b['tax'][k] - t['default']
        out[k] = t['base'] + t['per'] * d - t['decay'] * t['per'] * max(d, 0) ** 2
    return out

def interest():
    s = st.session_state
    return BASE_INTEREST * (1 + 0.4 * (s.gilt_yield / 4.7 - 1) + (s.debt / 98.2 - 1))

def revenue_pie(b):
    r = revenues(b)
    data = {TAXES[k]['short']: round(v, 1) for k, v in r.items()}
    data['Fuel, alcohol & other'] = OTHER_RECEIPTS
    
    pol_rev = sum(TAX_POLICIES[k]['yield_bn'] for k, active in b['tax_pol'].items() if active)
    if pol_rev > 0: data['Special Tax Schemes'] = round(pol_rev, 1)
    return data

def spending_pie(b):
    s = st.session_state
    ensure()
    data = {SPEND_DEFAULTS[k]['short']: round(s.dept_spend[k] * (1.0 + b['spend'][k] / 100.0), 1) for k in SPEND_DEFAULTS}
    data['Debt interest'] = round(interest(), 1)
    
    pol_spend = sum(SPEND_POLICIES[k]['cost_bn'] for k, active in b['spend_pol'].items() if active)
    if pol_spend > 0: data['Special Spending Pledges'] = round(pol_spend, 1)
    return data

def impact(old, new):
    s = st.session_state
    ensure()
    ro, rn = revenues(old), revenues(new)
    d = {k: rn[k] - ro[k] for k in ro}
    ds = {k: s.dept_spend[k] * ((new['spend'][k] - old['spend'][k]) / 100.0) for k in SPEND_DEFAULTS}
    
    tax_pol_diff = sum(p['yield_bn'] for k, p in TAX_POLICIES.items() if new['tax_pol'][k]) - sum(p['yield_bn'] for k, p in TAX_POLICIES.items() if old['tax_pol'][k])
    spend_pol_diff = sum(p['cost_bn'] for k, p in SPEND_POLICIES.items() if new['spend_pol'][k]) - sum(p['cost_bn'] for k, p in SPEND_POLICIES.items() if old['spend_pol'][k])

    bal = sum(d.values()) - sum(ds.values()) + tax_pol_diff - spend_pol_diff

    household = d['income'] + d['ni'] + d['vat']
    vat_pts = new['tax']['vat'] - old['tax']['vat']

    approval = (-0.10 * household - 0.03 * d['property']
                + 0.05 * (ds['health'] + ds['education']) + 0.03 * ds['welfare']
                + 0.02 * (ds['justice'] + ds['housing'] + ds['transport']) + 0.01 * ds['defence'])
    market = max(-8, min(8, 0.10 * bal)) - 0.25 * d['corp'] - 0.12 * d['property']
    growth = (-0.012 * d['corp'] - 0.006 * d['ni'] - 0.004 * d['income']
              + 0.008 * (ds['transport'] + ds['housing'] + ds['climate'])
              + 0.002 * (ds['health'] + ds['education'] + ds['other'] + ds['welfare'])
              + 0.001 * ds['defence'])
    
    for k, p in TAX_POLICIES.items():
        if new['tax_pol'][k] and not old['tax_pol'][k]:
            approval += p['app']; market += p['mkt']; growth += p['gro']
        elif not new['tax_pol'][k] and old['tax_pol'][k]:
            approval -= p['app']; market -= p['mkt']; growth -= p['gro']

    for k, p in SPEND_POLICIES.items():
        if new['spend_pol'][k] and not old['spend_pol'][k]:
            approval += p['app']; market += p['mkt']; growth += p['gro']
        elif not new['spend_pol'][k] and old['spend_pol'][k]:
            approval -= p['app']; market -= p['mkt']; growth -= p['gro']

    inflation = 0.12 * vat_pts + 0.003 * sum(ds.values())

    return dict(headroom=bal, deficit=-bal, approval=approval, market=market,
                growth=growth, inflation=inflation, real_wages=-0.010 * d['income'] - 0.006 * d['ni'],
                unemployment=0.010 * d['ni'] + 0.004 * d['corp'])

def _clip(v): return max(0, min(100, v))

def _apply():
    s = st.session_state
    new, old = read(), s.budget_applied
    if new == old:
        s.message = 'Budget unchanged.'
        return
    imp = impact(old, new)
    
    state.snapshot()
    
    s.headroom = round(s.headroom + imp['headroom'], 1)
    s.deficit = round(s.deficit + imp['deficit'], 1)
    s.approval = round(_clip(s.approval + imp['approval']), 1)
    s.market_conf = round(_clip(s.market_conf + imp['market']), 1)
    s.growth = round(s.growth + imp['growth'], 2)
    s.inflation = round(s.inflation + imp['inflation'], 2)
    country.nudge({'real_wages': imp['real_wages'], 'unemployment': imp['unemployment']})
    s.budget_applied = new
    verb = 'improves' if imp['headroom'] >= 0 else 'worsens'
    s.message = f"Budget delivered. It {verb} public finances by £{abs(imp['headroom']):.1f}B a year."

def _reset():
    s = st.session_state
    for k, v in s.budget_applied['tax'].items(): s[f'bt_{k}'] = v
    for k, v in s.budget_applied['spend'].items(): s[f'bs_{k}'] = float(v)
    for k, v in s.budget_applied['tax_pol'].items(): s[f'btp_{k}'] = v
    for k, v in s.budget_applied['spend_pol'].items(): s[f'bsp_{k}'] = v

def apply_ongoing():
    s = st.session_state
    ensure()
    party = s.party

    # Capture ideological metrics before resetting the base
    corp_change = s.budget_applied['tax']['corp'] - TAXES['corp']['default']
    welfare_change = float(s.budget_applied['spend']['welfare'])
    climate_change = float(s.budget_applied['spend']['climate'])
    other_change = float(s.budget_applied['spend']['other'])
    
    # 1. Compound this year's % decisions into permanent baselines
    for k in SPEND_DEFAULTS:
        pct_change = s.budget_applied['spend'].get(k, 0.0)
        s.dept_spend[k] = round(s.dept_spend[k] * (1.0 + pct_change / 100.0), 1)
        s[f'bs_{k}'] = 0.0
        s.budget_applied['spend'][k] = 0.0

    # 2. Update country metrics
    sp_pol = s.budget_applied['spend_pol']
    dv = {k: s.dept_spend[k] - SPEND_DEFAULTS[k]['default'] for k in SPEND_DEFAULTS}
    
    country.nudge({
        'nhs_waiting': -0.004 * dv['health'],
        'nhs_morale': 0.05 * dv['health'],
        'schools': 0.04 * dv['education'] + (2 if sp_pol['meals'] else 0),
        'child_poverty': -0.012 * dv['welfare'] - (4 if sp_pol['child_cap'] else 0),
        'homeless': -0.03 * dv['welfare'] - 0.02 * dv['housing'],
        'homes_built': 0.6 * dv['housing'],
        'prisons': -0.05 * dv['justice'],
        'rail': 0.08 * dv['transport'] + (4 if sp_pol['hs2'] else 0),
        'netzero': 0.06 * dv['climate'],
        'energy_bills': -1.5 * dv['climate'],
    }, snapshot=False)

    # 3. IDEOLOGICAL BUDGETING LOOP
    if party in ['Conservative', 'Reform UK'] and corp_change > 0:
        s.backbench_opinion = max(0, s.backbench_opinion - 15)
        s.message += " Your backbenchers are furious about the Corporation Tax hike."
        
    if party in ['Labour', 'Green Party'] and welfare_change < 0:
        s.party_opinion = max(0, s.party_opinion - 15)
        s.message += " The left wing of your party is in open revolt over welfare cuts."
        
    if party == 'Liberal Democrats' and climate_change < 0:
        s.party_opinion = max(0, s.party_opinion - 15)
        s.message += " Your party base is angry about cuts to climate spending."
        
    if party in ['SNP', 'Plaid Cymru'] and other_change < 0:
        s.party_opinion = max(0, s.party_opinion - 15)
        s.message += " Your regional assembly is furious about cuts to devolved block grants."

    # 4. Interest Check
    new_interest = interest()
    drift = new_interest - s.get('budget_interest', BASE_INTEREST)
    if abs(drift) > 0.05:
        s.deficit = round(s.deficit + drift, 1)
        s.headroom = round(s.headroom - drift, 1)
        s.budget_interest = new_interest
    if s.headroom < 0:
        s.market_conf = round(_clip(s.market_conf - min(4, 0.15 * -s.headroom)), 1)
        s.message += " ⚠️ Negative OBR headroom: markets punish the breach of your fiscal rules."

def _pie(data):
    df = pd.DataFrame([{'Category': str(k), 'Value': float(v)} for k, v in data.items() if float(v) > 0])
    if not df.empty:
        chart = alt.Chart(df).mark_arc(innerRadius=65, outerRadius=125, stroke='#0d1f17', strokeWidth=2).encode(
            theta=alt.Theta(field="Value", type="quantitative"),
            color=alt.Color(field="Category", type="nominal", scale=alt.Scale(range=PALETTE), 
                            legend=alt.Legend(title=None, orient='right', labelColor='#efe9da', labelFontSize=12, symbolType='square')),
            tooltip=[alt.Tooltip('Category:N', title='Item'), alt.Tooltip('Value:Q', title='Amount (£bn)', format=',.1f')]
        ).properties(height=300, background='transparent').configure_view(strokeWidth=0)
        st.altair_chart(chart, use_container_width=True)

def render():
    ensure()
    s = st.session_state
    applied, cur = s.budget_applied, read()
    changed = cur != applied

    pol_rev = sum(TAX_POLICIES[k]['yield_bn'] for k, active in cur['tax_pol'].items() if active)
    rev_now = sum(revenues(cur).values()) + OTHER_RECEIPTS + pol_rev
    
    pol_rev_app = sum(TAX_POLICIES[k]['yield_bn'] for k, active in applied['tax_pol'].items() if active)
    rev_app = sum(revenues(applied).values()) + OTHER_RECEIPTS + pol_rev_app
    
    pol_spend = sum(SPEND_POLICIES[k]['cost_bn'] for k, active in cur['spend_pol'].items() if active)
    spend_now = sum(s.dept_spend[k] * (1.0 + cur['spend'][k] / 100.0) for k in SPEND_DEFAULTS) + interest() + pol_spend
    
    pol_spend_app = sum(SPEND_POLICIES[k]['cost_bn'] for k, active in applied['spend_pol'].items() if active)
    spend_app = sum(s.dept_spend[k] * (1.0 + applied['spend'][k] / 100.0) for k in SPEND_DEFAULTS) + interest() + pol_spend_app
    
    bal_now, bal_app = rev_now - spend_now, rev_app - spend_app

    m1, m2, m3 = st.columns(3)
    m1.metric('Total income', f'£{rev_now:,.0f}bn', f'{rev_now - rev_app:+,.1f}bn' if changed else None)
    m2.metric('Total spending', f'£{spend_now:,.0f}bn', f'{spend_now - spend_app:+,.1f}bn' if changed else None, delta_color='inverse')
    label = 'Surplus' if bal_now >= 0 else 'Deficit'
    m3.metric(f'Budget {label.lower()}', f'£{abs(bal_now):,.1f}bn', f'{bal_now - bal_app:+,.1f}bn' if changed else None)

    left, right = st.columns(2)
    
    with left:
        st.markdown('#### Taxes')
        for k, t in TAXES.items():
            st.markdown(f"**{t['label']}**")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.slider(f"{t['label']} slider", t['lo'], t['hi'], value=int(s[f'bt_{k}']), step=t['step'], key=f'bt_{k}', label_visibility="collapsed")
            with c2:
                rate = s[f'bt_{k}']
                diff_rate = rate - t['default']
                new_rev = t['base'] + t['per'] * diff_rate - t['decay'] * t['per'] * max(diff_rate, 0) ** 2
                diff_rev = new_rev - t['base']
                color = '#6fbf8a' if diff_rev > 0 else '#e0705d' if diff_rev < 0 else '#9fb3a6'
                st.markdown(f"<div style='text-align:right; font-size:1.1rem; line-height:1.2;'><b>£{new_rev:,.1f}b</b><br><span style='color:{color}; font-size:0.85rem;'>{diff_rev:+,.1f}b</span></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown('#### Revenue Raising Schemes')
        for k, p in TAX_POLICIES.items(): st.checkbox(f"{p['label']} (+£{p['yield_bn']}bn)", key=f"btp_{k}")

    with right:
        st.markdown('#### Department Spending (Annual % Change)')
        st.caption('Set annual spending growth or cuts (-15% to +15%). Changes compound into baseline budgets each year.')
        for k, sp in SPEND_DEFAULTS.items():
            base = s.dept_spend[k]
            st.markdown(f"**{sp['label']}** (Current base: £{base:,.1f}bn)")
            c1, c2 = st.columns([3, 1])
            with c1:
                st.slider(f"{sp['label']} slider", -15.0, 15.0, value=float(s[f'bs_{k}']), step=0.5, key=f'bs_{k}', format="%+.1f%%", label_visibility="collapsed")
            with c2:
                pct = float(s[f'bs_{k}'])
                new_val = base * (1.0 + pct / 100.0)
                diff = new_val - base
                color = '#e0705d' if diff < 0 else '#6fbf8a' if diff > 0 else '#9fb3a6'
                st.markdown(f"<div style='text-align:right; font-size:1.1rem; line-height:1.2;'><b>£{new_val:,.1f}b</b><br><span style='color:{color}; font-size:0.85rem;'>{diff:+,.1f}b ({pct:+.1f}%)</span></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('#### Spending Pledges')
        for k, p in SPEND_POLICIES.items(): st.checkbox(f"{p['label']} (-£{p['cost_bn']}bn)", key=f"bsp_{k}")

    st.caption(f'Debt interest (£{interest():,.1f}bn) is set by gilt yields and total debt stock, not by departmental budgets.')

    imp = impact(applied, cur)
    st.markdown('#### Projected impact' if changed else '#### Impact of your current budget')
    c = st.columns(6)
    c[0].metric('Public Approval', f"{_clip(s.approval + imp['approval']):.1f}%", f"{imp['approval']:+.1f}")
    c[1].metric('Market Confidence', f"{_clip(s.market_conf + imp['market']):.1f}%", f"{imp['market']:+.1f}")
    c[2].metric('Economic Growth', f"{s.growth + imp['growth']:.1f}%", f"{imp['growth']:+.2f}")
    c[3].metric('Inflation', f"{s.inflation + imp['inflation']:.1f}%", f"{imp['inflation']:+.2f}", delta_color='inverse')
    c[4].metric('OBR Headroom', f"£{s.headroom + imp['headroom']:.1f}B", f"{imp['headroom']:+.1f}")
    c[5].metric('Annual Deficit', f"£{s.deficit + imp['deficit']:.1f}B", f"{imp['deficit']:+.1f}", delta_color='inverse')

    b1, b2, _ = st.columns([1, 1, 3])
    b1.button('Apply Budget', type='primary', on_click=_apply, disabled=not changed)
    b2.button('Reset sliders', on_click=_reset, disabled=not changed)

    st.caption('Departmental funding levels also nudge the State of the Nation indicators across turns.')

    p1, p2 = st.columns(2)
    with p1:
        st.markdown('#### Where the money comes from')
        _pie(revenue_pie(cur))
    with p2:
        st.markdown('#### Where the money goes')
        _pie(spending_pie(cur))
