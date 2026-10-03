import pandas as pd
import streamlit as st
import country

# Expanded bounds (lo) so you can deeply cut taxes and spending
TAXES = {
    'income':   dict(label='Income tax, basic rate (p in the £)', short='Income tax', default=20, lo=5, hi=45, step=1, base=300.0, per=7.5, decay=0.02),
    'ni':       dict(label='National Insurance rate (%)', short='National Insurance', default=15, lo=0, hi=30, step=1, base=190.0, per=9.0, decay=0.04),
    'vat':      dict(label='VAT (%)', short='VAT', default=20, lo=5, hi=35, step=1, base=170.0, per=8.0, decay=0.04),
    'corp':     dict(label='Corporation tax (%)', short='Corporation tax', default=25, lo=5, hi=45, step=1, base=90.0, per=2.5, decay=0.04),
    'property': dict(label='Property & wealth taxes (% change in yield)', short='Property & wealth taxes', default=0, lo=-50, hi=100, step=5, base=110.0, per=1.1, decay=0.004),
}

OTHER_RECEIPTS = 290.0  

# Minimum limits (lo) set to 0 so you can slash budgets completely if desired
SPEND = {
    'welfare':   dict(label='Welfare & pensions (£bn)', short='Welfare & pensions', default=330, lo=0, hi=500),
    'health':    dict(label='NHS & health (£bn)', short='NHS & health', default=215, lo=0, hi=350),
    'education': dict(label='Education (£bn)', short='Education', default=125, lo=0, hi=200),
    'defence':   dict(label='Defence (£bn)', short='Defence', default=62, lo=0, hi=120),
    'transport': dict(label='Transport & infrastructure (£bn)', short='Transport & infrastructure', default=48, lo=0, hi=100),
    'justice':   dict(label='Policing, courts & prisons (£bn)', short='Policing, courts & prisons', default=45, lo=0, hi=90),
    'housing':   dict(label='Housing & local government (£bn)', short='Housing & local government', default=60, lo=0, hi=120),
    'climate':   dict(label='Climate, energy & industry (£bn)', short='Climate, energy & industry', default=35, lo=0, hi=100),
    'other':     dict(label='Other departments & admin (£bn)', short='Other departments & admin', default=130, lo=0, hi=200),
}

BASE_INTEREST = 105.4 

PALETTE = ['#c9a45c', '#6fbf8a', '#4f8fba', '#d6604f', '#9a7fc4', '#e0b0a0', '#7fb8b0', '#c4c46f', '#8aa0a0', '#d98cb3']

def defaults():
    return {'tax': {k: v['default'] for k, v in TAXES.items()},
            'spend': {k: v['default'] for k, v in SPEND.items()}}

def ensure():
    s = st.session_state
    if 'budget_applied' not in s:
        s.budget_applied = defaults()
        s.budget_interest = BASE_INTEREST
    for k, v in s.budget_applied['tax'].items():
        s.setdefault(f'bt_{k}', v)
    for k, v in s.budget_applied['spend'].items():
        s.setdefault(f'bs_{k}', v)

def read():
    s = st.session_state
    return {'tax': {k: s[f'bt_{k}'] for k in TAXES},
            'spend': {k: s[f'bs_{k}'] for k in SPEND}}

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
    data = {TAXES[k]['short']: v for k, v in r.items()}
    data['Fuel, alcohol & other'] = OTHER_RECEIPTS
    return data

def spending_pie(b):
    data = {SPEND[k]['short']: v for k, v in b['spend'].items()}
    data['Debt interest'] = interest()
    return data

def impact(old, new):
    ro, rn = revenues(old), revenues(new)
    d = {k: rn[k] - ro[k] for k in ro}
    ds = {k: new['spend'][k] - old['spend'][k] for k in SPEND}
    bal = sum(d.values()) - sum(ds.values())

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
    inflation = 0.12 * vat_pts + 0.003 * sum(ds.values())

    return dict(headroom=bal, deficit=-bal, approval=approval, market=market,
                growth=growth, inflation=inflation, real_wages=-0.010 * d['income'] - 0.006 * d['ni'],
                unemployment=0.010 * d['ni'] + 0.004 * d['corp'])

def _clip(v):
    return max(0, min(100, v))

def _apply():
    s = st.session_state
    new, old = read(), s.budget_applied
    if new == old:
        s.message = 'Budget unchanged.'
        return
    imp = impact(old, new)
    
    s.prev_approval, s.prev_market, s.prev_growth = s.approval, s.market_conf, s.growth
    s.prev_headroom, s.prev_debt = s.headroom, s.debt
    
    s.headroom = round(s.headroom + imp['headroom'], 1)
    s.deficit = round(s.deficit + imp['deficit'], 1)
    s.approval = round(_clip(s.approval + imp['approval']), 1)
    s.market_conf = round(_clip(s.market_conf + imp['market']), 1)
    s.growth = round(s.growth + imp['growth'], 2)
    s.inflation = round(s.inflation + imp['inflation'], 2)
    country.nudge({'real_wages': imp['real_wages'], 'unemployment': imp['unemployment']})
    s.budget_applied = new
    verb = 'improves' if imp['headroom'] >= 0 else 'worsens'
    s.message = f"Budget delivered. It {verb} the public finances by £{abs(imp['headroom']):.1f}B a year."

def _reset():
    s = st.session_state
    for k, v in s.budget_applied['tax'].items():
        s[f'bt_{k}'] = v
    for k, v in s.budget_applied['spend'].items():
        s[f'bs_{k}'] = v

def apply_ongoing():
    s = st.session_state
    ensure()
    sp = s.budget_applied['spend']
    dv = {k: sp[k] - SPEND[k]['default'] for k in SPEND}
    country.nudge({
        'nhs_waiting': -0.004 * dv['health'],
        'nhs_morale': 0.05 * dv['health'],
        'schools': 0.04 * dv['education'],
        'child_poverty': -0.012 * dv['welfare'],
        'homeless': -0.03 * dv['welfare'] - 0.02 * dv['housing'],
        'homes_built': 0.6 * dv['housing'],
        'prisons': -0.05 * dv['justice'],
        'rail': 0.08 * dv['transport'],
        'netzero': 0.06 * dv['climate'],
        'energy_bills': -1.5 * dv['climate'],
    }, snapshot=False)

    new_interest = interest()
    drift = new_interest - s.get('budget_interest', BASE_INTEREST)
    if abs(drift) > 0.05:
        s.deficit = round(s.deficit + drift, 1)
        s.headroom = round(s.headroom - drift, 1)
        s.budget_interest = new_interest
    if s.headroom < 0:
        s.market_conf = round(_clip(s.market_conf - min(4, 0.15 * -s.headroom)), 1)
        s.message = f"{s.message} ⚠️ Negative OBR headroom: markets punish the breach of your fiscal rules."

def _pie(data):
    import altair as alt
    total = sum(data.values())
    
    # Fixed invisible pie charts by casting values to float and defining an explicit outerRadius
    rows = [{'label': f'{k} · {v / total * 100:.1f}%', 'name': k, 'value': float(v), 'amount': f'£{v:,.0f}bn'}
            for k, v in data.items() if v > 0]
    df = pd.DataFrame(rows)
    domain = list(df['label'])
    
    chart = (alt.Chart(df)
             .mark_arc(innerRadius=70, outerRadius=130, stroke='#0d1f17', strokeWidth=2)
             .encode(
                 theta=alt.Theta('value:Q'),
                 color=alt.Color('label:N', scale=alt.Scale(domain=domain, range=PALETTE[:len(domain)]),
                                 legend=alt.Legend(title=None, orient='right', labelColor='#efe9da', labelFontSize=13, symbolType='square')),
                 tooltip=[alt.Tooltip('name:N', title='Item'), alt.Tooltip('amount:N', title='Amount'), alt.Tooltip('label:N', title='Share')],
             )
             .properties(height=300, background='transparent')
             .configure_view(strokeWidth=0)
             )
    st.altair_chart(chart, use_container_width=True)

def render():
    ensure()
    s = st.session_state
    applied, cur = s.budget_applied, read()
    changed = cur != applied

    rev_now, rev_app = sum(revenues(cur).values()) + OTHER_RECEIPTS, sum(revenues(applied).values()) + OTHER_RECEIPTS
    spend_now = sum(cur['spend'].values()) + interest()
    spend_app = sum(applied['spend'].values()) + interest()
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
            st.slider(t['label'], t['lo'], t['hi'], value=int(s[f'bt_{k}']), step=t['step'], key=f'bt_{k}')
    with right:
        st.markdown('#### Spending')
        for k, sp in SPEND.items():
            st.slider(sp['label'], sp['lo'], sp['hi'], value=int(s[f'bs_{k}']), step=1, key=f'bs_{k}')

    st.caption(f'Debt interest (£{interest():,.1f}bn) is set by gilt yields and the size of the debt, not by you.')

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

    st.caption('Spending levels also keep working on the State of the Nation every turn (NHS, schools, housing, rail and more), '
               'and very low or high settings can trigger budget fallout scenarios.')

    p1, p2 = st.columns(2)
    with p1:
        st.markdown('#### Where the money comes from')
        _pie(revenue_pie(cur))
    with p2:
        st.markdown('#### Where the money goes')
        _pie(spending_pie(cur))
