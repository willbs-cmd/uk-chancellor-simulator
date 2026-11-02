"""OBR-style forecast revisions, Bank of England reaction and DMO debt strategy."""
import streamlit as st
import state

def ensure():
    s=st.session_state
    s.setdefault("obr_forecasts", []); s.setdefault("obr_latest", None)
    s.setdefault("boe_independence",75.0)
    s.setdefault("boe_last_statement","The Monetary Policy Committee is monitoring inflation and activity.")
    s.setdefault("boe_history",[])
    s.setdefault("dmo_strategy","Balanced issuance"); s.setdefault("dmo_maturity",10); s.setdefault("dmo_index_share",25)
    s.setdefault("dmo_last_action","No change to the issuance strategy yet.")
    s.setdefault("stress_test_result",None)

def annual_update():
    ensure(); s=st.session_state
    # Stable forecast noise for this in-game year; reloading does not change the forecast.
    import random
    rng=random.Random(int(s.get("seed",1))+int(s.get("term",1))*1000+int(s.get("year",1))*37)
    growth=float(s.get("growth",0)); inflation=float(s.get("inflation",2)); headroom=float(s.get("headroom",0)); market=float(s.get("market_conf",50))
    revision=rng.uniform(-0.22,0.22)
    receipts=round((growth-1.0)*1.8+revision*2.0,1)
    spending=round(max(0,inflation-2.0)*1.1+max(0,-growth)*1.4,1)
    forecast={"term":int(s.get("term",1)),"year":int(s.get("year",1)),"growth":round(growth+revision,2),
      "inflation":round(max(-1,inflation-0.25+rng.uniform(-0.12,0.12)),2),
      "receipts_revision":receipts,"spending_revision":spending,"headroom":round(headroom+receipts-spending,1),
      "market_conf":round(market,1),"note":"Illustrative OBR-style gameplay projection, not an official OBR forecast."}
    s.obr_forecasts=(list(s.get("obr_forecasts",[]))+[forecast])[-12:]; s.obr_latest=forecast
    s.headroom=round(float(s.headroom)+receipts-spending,1)
    s.deficit=round(max(0,float(s.deficit)-receipts+spending),1)
    # Independent MPC reaction function: Chancellor cannot set Bank Rate.
    before=float(s.get("interest_rate",4.5))
    change=max(-0.50,min(0.50,0.18*(inflation-2.0)-0.10*(growth-1.0)))
    after=round(max(0.1,before+change),2); s.interest_rate=after
    if inflation>3 and change>0.05: statement="The MPC has tightened policy to bring persistent inflation back towards target, despite risks to growth."
    elif inflation<1.5 and growth<0.5: statement="The MPC has eased policy as weak demand and subdued inflation increase the risk of stagnation."
    else: statement="The MPC has made a measured adjustment, balancing the inflation target against economic activity."
    s.boe_last_statement=statement
    if abs(after-before)>=0.05:
        s.boe_history=(list(s.get("boe_history",[]))+[{"year":f"Term {s.term}, Year {s.year}","before":before,"after":after,"inflation":inflation,"statement":statement}])[-12:]
    if float(s.get("boe_independence",75))<40:
        s.market_conf=round(max(0,min(100,float(s.market_conf)-1)),1); s.gilt_yield=round(float(s.gilt_yield)+0.05,2)
        s.message+=" Markets are questioning the perceived independence of the Bank of England."

def _stress_test():
    """Run illustrative macro-fiscal shocks against the current Budget draft."""
    s=st.session_state
    import budget
    approved=s.get("budget_applied",budget.read())
    draft=budget.read()
    baseline=budget.impact(approved,draft)
    headroom=float(s.get("headroom",0))+float(baseline.get("headroom",0))
    deficit=max(0.0,float(s.get("deficit",0))+float(baseline.get("deficit",0)))
    growth=float(s.get("growth",0))+float(baseline.get("growth",0))
    inflation=float(s.get("inflation",2))+float(baseline.get("inflation",0))
    gdp_bn=max(100.0,float(s.get("gdp_trillion",3.0))*1000.0)
    debt_bn=gdp_bn*float(s.get("debt",0))/100.0
    maturity=max(2.0,float(s.get("dmo_maturity",s.get("gilt_maturity_years",10))))
    refinancing_share=max(0.08,min(0.40,1.0/maturity+0.12))
    cases=[
        ("Mild slowdown",-1.0,0.0,0.0),
        ("Recession",-2.5,-0.5,0.5),
        ("Inflation returns",-0.5,2.0,1.5),
        ("Gilt-market shock",-1.0,0.5,2.0),
        ("Severe combined shock",-4.0,2.5,3.0),
    ]
    rows=[]
    for name,g_shock,i_shock,r_shock in cases:
        receipts_loss=max(0.0,-g_shock)*0.38*gdp_bn*0.010
        inflation_cost=max(0.0,i_shock)*0.44*gdp_bn*0.0025
        interest_cost=debt_bn*max(0.0,r_shock)/100.0*refinancing_share
        hit=receipts_loss+inflation_cost+interest_cost
        stressed_headroom=headroom-hit
        stressed_deficit=deficit+hit
        debt_after=(debt_bn+hit)/max(1.0,gdp_bn*(1+(growth+g_shock)/100.0))*100.0
        if stressed_headroom<0:
            status="Breach"
        elif stressed_headroom<3:
            status="Thin"
        else:
            status="Resilient"
        rows.append({
            "Scenario":name,
            "Assumptions":f"Growth {g_shock:+.1f}pp; inflation {i_shock:+.1f}pp; rates {r_shock:+.1f}pp",
            "Growth after shock (%)":round(growth+g_shock,2),
            "Inflation after shock (%)":round(inflation+i_shock,2),
            "Receipts loss (£bn)":round(receipts_loss,1),
            "Inflation cost (£bn)":round(inflation_cost,1),
            "Extra debt interest (£bn)":round(interest_cost,1),
            "Headroom after shock (£bn)":round(stressed_headroom,1),
            "Deficit after shock (£bn)":round(stressed_deficit,1),
            "Debt ratio after shock (%)":round(debt_after,1),
            "Fiscal position":status,
        })
    return rows

def render():
    ensure(); s=st.session_state
    st.markdown('### OBR forecasts and financial markets')
    st.caption("These are simplified gameplay models, not official OBR or Bank of England projections.")
    f=s.get("obr_latest")
    if f:
        st.markdown("#### Latest forecast revision")
        cols=st.columns(4)
        cols[0].metric("Growth forecast",f"{f['growth']:+.2f}%"); cols[1].metric("Inflation forecast",f"{f['inflation']:.2f}%")
        cols[2].metric("Receipts revision",f"£{f['receipts_revision']:+.1f}bn"); cols[3].metric("Headroom",f"£{f['headroom']:+.1f}bn")
        st.caption(f["note"])
    else: st.info("The first forecast revision arrives at the next annual Spring update.")
    with st.expander("Forecast history"):
        if s.get("obr_forecasts"): st.dataframe(s.obr_forecasts,hide_index=True,use_container_width=True)
        else: st.caption("No annual revisions yet.")
    st.divider(); st.markdown("#### Bank of England")
    st.metric("Bank Rate",f"{float(s.get('interest_rate',0)):.2f}%")
    st.write(s.get("boe_last_statement","The MPC is monitoring the economy."))
    st.caption(f"Perceived Bank independence: {float(s.get('boe_independence',75)):.0f}/100. The Chancellor cannot set Bank Rate.")
    if s.get("boe_history"): st.dataframe(s.boe_history[-6:],hide_index=True,use_container_width=True)
    st.info("The MPC sets interest rates independently. Political pressure on the Bank can damage confidence and increase gilt yields.")
    st.divider(); st.markdown('#### Debt Management Office · gilt issuance')
    st.caption("Choose the broad shape of new borrowing. This affects refinancing and inflation-linked exposure, not the existing debt stock.")
    strategies=["Balanced issuance","Long-term stability","Short-term flexibility","Limit index-linked exposure"]
    strategy=st.selectbox("Issuance strategy",strategies,index=strategies.index(s.get("dmo_strategy","Balanced issuance")),key="dmo_strategy_choice")
    maturity=st.slider("Average maturity of new conventional gilts (years)",2,30,int(s.get("dmo_maturity",10)),key="dmo_maturity_choice")
    share=st.slider("Index-linked share of new issuance (%)",0,50,int(s.get("dmo_index_share",25)),key="dmo_index_share_choice")
    if st.button("Submit issuance strategy",key="dmo_submit"):
        state.checkpoint(); s.dmo_strategy=strategy; s.dmo_maturity=maturity; s.dmo_index_share=share
        s.gilt_maturity_years=maturity; s.index_linked_share=share
        move=(10-maturity)*0.006+max(0,share-25)*0.0015
        s.gilt_yield=round(max(0.1,float(s.gilt_yield)+move),2)
        s.dmo_last_action=f"{strategy}: {maturity}-year average maturity and {share}% index-linked issuance."
        s.message="The DMO has adopted your revised issuance remit. "+s.dmo_last_action
        st.success(s.dmo_last_action)
    st.divider(); st.markdown("#### Fiscal stress testing")
    st.caption("Tests your live Budget draft against illustrative economic shocks. This is a forecast exercise only and does not alter your saved finances.")
    if st.button("Run fiscal stress tests",key="economic_stress_test",type="primary"):
        s.stress_test_result=_stress_test()
        s.stress_test_run_label="Term " + str(int(s.get("term",1))) + ", Year " + str(int(s.get("year",1)))
    if s.get("stress_test_result"):
        st.caption("Latest test: " + str(s.get("stress_test_run_label","Current game position")) + " · includes your uncommitted Budget draft.")
        st.dataframe(s.stress_test_result,hide_index=True,use_container_width=True)
        worst=min(s.stress_test_result,key=lambda x:x["Headroom after shock (£bn)"])
        cols=st.columns(3)
        cols[0].metric("Worst-case headroom","£" + str(worst["Headroom after shock (£bn)"]) + "bn")
        cols[1].metric("Worst-case deficit","£" + str(worst["Deficit after shock (£bn)"]) + "bn")
        cols[2].metric("Worst-case debt ratio",str(worst["Debt ratio after shock (%)"]) + "%")
        if worst["Headroom after shock (£bn)"]<0:
            st.error(str(worst["Scenario"]) + " would breach the fiscal rule by £" + str(abs(worst["Headroom after shock (£bn)"])) + "bn.")
        elif worst["Headroom after shock (£bn)"]<3:
            st.warning("The buffer is thin: the worst scenario leaves only £" + str(worst["Headroom after shock (£bn)"]) + "bn.")
        else:
            st.success("The fiscal position survives all tested shocks. Lowest remaining buffer: £" + str(worst["Headroom after shock (£bn)"]) + "bn.")
        st.caption("Debt-interest exposure reflects only the estimated share of debt refinanced during the year. Longer average gilt maturity cushions rate shocks.")
