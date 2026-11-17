"""Leadership speculation and parliamentary-party pressure on the Chancellor."""
import hashlib
import streamlit as st


def _clip(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def _roll(s, label):
    raw = f"{s.get('seed', 0)}:{s.get('term', 1)}:{s.get('year', 1)}:{label}"
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8], 16) % 100


def annual_review(s):
    """Assess leadership vulnerability once per financial year."""
    year = int(s.get("year", 1))
    if int(s.get("leadership_last_review", 0)) == year:
        return None
    s.leadership_last_review = year
    pm=float(s.get("pm_opinion",50)); approval=float(s.get("approval",50))
    party=float(s.get("party_opinion",50)); backbench=float(s.get("backbench_opinion",50))
    strikes=list(s.get("public_service_strikes",[]))
    strike_pressure=sum(float(x.get("severity",1.0))*min(1.6,1+0.2*max(0,int(x.get("duration_years",0))-1)) for x in strikes)
    raw=(max(0,50-pm)*.32+max(0,50-party)*.28+max(0,50-backbench)*.22
         +max(0,45-approval)*.12+min(8,strike_pressure*1.2))
    pressure=round(min(100,raw*.72+float(s.get("leadership_pressure",0))*.28),1)
    s.leadership_pressure=pressure
    if pressure<18 or s.get("leadership_issue") or s.get("game_over"): return None
    if _roll(s,"leadership-speculation")>=min(90,max(18,int(pressure*1.35))): return None
    profiles={
      "Labour":("the Deputy Leader","soft-left and parliamentary organisers"),
      "Conservative":("a senior former Cabinet minister","One Nation and fiscal conservative MPs"),
      "Liberal Democrats":("the party's deputy","social liberal MPs and local government voices"),
      "Reform UK":("a prominent party strategist","the party's campaigning and policy wing"),
      "Green Party":("a senior parliamentary spokesperson","eco-socialist and local movement activists"),
      "SNP":("a senior party figure","the party's parliamentary and independence wings"),
      "Plaid Cymru":("a senior Senedd and Westminster figure","regional and language campaigners")}
    challenger,faction=profiles.get(str(s.get("party","")) ,("a senior party figure","restless parliamentary colleagues"))
    issue={"year":year,"term":int(s.get("term",1)),"party":str(s.get("party","Government")),
      "pressure":pressure,"challenger":challenger,"faction":faction,"pm_opinion":round(pm,1),
      "party_opinion":round(party,1),"backbench_opinion":round(backbench,1),
      "text":f"Westminster is discussing whether {challenger} could replace the Prime Minister. {faction.capitalize()} are increasingly restless. The PM wants to know whether the Treasury is loyal."}
    s.leadership_issue=issue
    s.leadership_history=(list(s.get("leadership_history",[]))+[dict(issue)])[-20:]
    s.event_cards=(list(s.get("event_cards",[]))+[{"title":"Leadership speculation reaches Westminster",
      "text":issue["text"],"summary":f"Party pressure {pressure:.0f}/100 · Chancellor's position under scrutiny"}])[-12:]
    return issue


def resolve(s,choice):
    issue=s.get("leadership_issue")
    if not issue or choice not in {"back_pm","back_challenger","stay_neutral"}: return False
    pressure=float(issue.get("pressure",0))
    if choice=="back_pm":
        s.pm_trust=round(_clip(float(s.get("pm_trust",70))+6),1)
        s.pm_opinion=round(_clip(float(s.get("pm_opinion",50))+2.5),1)
        s.party_opinion=round(_clip(float(s.get("party_opinion",50))-(1.5 if pressure>=35 else .5)),1)
        s.backbench_opinion=round(_clip(float(s.get("backbench_opinion",50))-(2 if pressure>=35 else .5)),1)
        outcome="You publicly back the Prime Minister. Number 10 rewards your loyalty, although restless MPs see you as part of the embattled leadership."
    elif choice=="back_challenger":
        s.pm_trust=round(_clip(float(s.get("pm_trust",70))-7),1)
        s.pm_opinion=round(_clip(float(s.get("pm_opinion",50))-3),1)
        s.party_opinion=round(_clip(float(s.get("party_opinion",50))+(2.5 if pressure>=35 else 1)),1)
        s.backbench_opinion=round(_clip(float(s.get("backbench_opinion",50))+(2 if pressure>=35 else .5)),1)
        outcome="You privately signal that the party needs a change. Restless MPs welcome the signal, but the PM may regard you as disloyal."
    else:
        s.pm_trust=round(_clip(float(s.get("pm_trust",70))-1),1)
        s.party_opinion=round(_clip(float(s.get("party_opinion",50))+.5),1)
        outcome="You keep the Treasury out of the leadership argument. Neither camp is fully satisfied, but you avoid becoming the story."
    s.leadership_issue=None
    record={"term":int(issue.get("term",s.get("term",1))),"year":int(issue.get("year",s.get("year",1))),
      "challenger":issue.get("challenger","Potential challenger"),"pressure":pressure,
      "choice":choice,"outcome":outcome,"pm_trust":float(s.get("pm_trust",0)),
      "party_opinion":float(s.get("party_opinion",0))}
    s.leadership_history=(list(s.get("leadership_history",[]))+[record])[-20:]
    s.message=outcome
    s.humphrey_note="A Chancellor should never underestimate the speed with which a party discovers a new favourite."
    return True


def render(s):
    issue=s.get("leadership_issue")
    if not issue or s.get("game_over") or s.get("step")!="game": return
    st.markdown("### 🏛️ Party leadership under pressure")
    st.warning(issue.get("text","The Prime Minister's position is under scrutiny."))
    st.caption(f"Leadership pressure: {float(issue.get('pressure',0)):.0f}/100 · Potential challenger: {issue.get('challenger','Senior party figure')}")
    st.write("The Prime Minister has asked where the Chancellor stands. Your response will affect Number 10 and the parliamentary party.")
    a,b,c=st.columns(3)
    with a:
        if st.button("Back the PM",key="leadership_back_pm",use_container_width=True):
            resolve(s,"back_pm"); st.rerun()
    with b:
        if st.button("Back the challenger",key="leadership_back_challenger",use_container_width=True):
            resolve(s,"back_challenger"); st.rerun()
    with c:
        if st.button("Stay neutral",key="leadership_stay_neutral",use_container_width=True):
            resolve(s,"stay_neutral"); st.rerun()
