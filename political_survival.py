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
        chance=min(85,max(20,int(pressure*.9)))
        if _roll(s,"leadership-challenge") < chance:
            previous=str(s.get("current_prime_minister","The Prime Minister"))
            new_pm=str(issue.get("challenger","A senior party figure"))
            styles={
                "Labour":("Public investment and service reform","Growth through skills, infrastructure and public services"),
                "Conservative":("Tax restraint and private-sector growth","Lower taxes, spending discipline and business investment"),
                "Liberal Democrats":("Public service renewal and constitutional reform","Local growth, public services and political reform"),
                "Reform UK":("Tax reduction and state reform","Smaller government, lower taxes and tighter spending"),
                "Green Party":("Green investment and redistribution","Climate investment, public ownership and inequality reduction"),
                "SNP":("Public investment and constitutional priorities","Scottish economic powers and public service investment"),
                "Plaid Cymru":("Welsh investment and regional renewal","Regional development, public services and devolution"),
            }
            priorities=styles.get(str(s.get("party","")),("A new political direction","Economic stability and party renewal"))
            s.current_prime_minister=new_pm
            s.pm_profile={"priority":priorities[0],"approach":priorities[1],"party":str(s.get("party",""))}
            s.pm_transition_issue={"year":int(s.get("year",1)),"term":int(s.get("term",1)),
                "previous_pm":previous,"new_pm":new_pm,"pressure":pressure,
                "priority":priorities[0],"approach":priorities[1]}
            s.pm_opinion=58.0
            s.pm_trust=48.0
            outcome=f"The leadership challenge succeeds. {new_pm} becomes Prime Minister and is reviewing the Treasury team. You must establish whether you have a place in the new administration."
        else:
            outcome="You privately back the challenger, but the leadership challenge fails. The Prime Minister survives and now knows where your loyalties lay."
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


def resolve_transition(s, choice):
    """The incoming Prime Minister decides whether the Chancellor stays in post."""
    issue=s.get("pm_transition_issue")
    if not issue or choice not in {"retain","dismiss"}:
        return False
    if choice=="retain":
        s.pm_trust=round(_clip(float(s.get("pm_trust",48))+17),1)
        s.pm_opinion=round(_clip(float(s.get("pm_opinion",58))+7),1)
        s.cab_opinion=round(_clip(float(s.get("cab_opinion",50))+2),1)
        s.chancellor_status="retained"
        outcome=f"{issue.get('new_pm','The new Prime Minister')} confirms that you will remain Chancellor. You have survived the transition, but must now deliver the new administration's priorities."
    else:
        s.chancellor_status="dismissed"
        s.sacked=True
        s.sacked_reason=f"{issue.get('new_pm','The new Prime Minister')} has appointed a different Chancellor as part of the new administration."
        s.game_over={"kind":"sacked","title":"Removed by the new Prime Minister","text":s.sacked_reason}
        outcome=s.sacked_reason
    s.pm_transition_issue=None
    record={"year":int(issue.get("year",s.get("year",1))),"term":int(issue.get("term",s.get("term",1))),
        "previous_pm":issue.get("previous_pm"),"new_pm":issue.get("new_pm"),
        "decision":choice,"outcome":outcome,"priority":issue.get("priority")}
    s.pm_history=(list(s.get("pm_history",[]))+[record])[-20:]
    s.chancellor_appointment_history=(list(s.get("chancellor_appointment_history",[]))+[record])[-20:]
    s.message=outcome
    s.humphrey_note="A new Prime Minister is entitled to a fresh team. It is customary to pretend this was always the plan."
    return True


def render(s):
    if s.get("game_over") or s.get("step")!="game": return
    transition=s.get("pm_transition_issue")
    if transition:
        st.markdown("### 🏛️ A new Prime Minister takes office")
        st.warning(f"{transition.get('new_pm')} has replaced {transition.get('previous_pm')} after a successful leadership challenge.")
        st.markdown(f"**New Prime Minister's priority:** {transition.get('priority')}  ")
        st.caption(transition.get("approach","The incoming administration is setting its economic direction."))
        st.write("The new Prime Minister is reviewing ministerial appointments. Your response to the leadership contest and your record in office will influence the decision.")
        left,right=st.columns(2)
        with left:
            if st.button("Accept the new PM's direction and remain Chancellor",key="pm_transition_retain",type="primary",use_container_width=True):
                resolve_transition(s,"retain")
                st.rerun()
        with right:
            if st.button("Offer to leave the Treasury",key="pm_transition_dismiss",use_container_width=True):
                resolve_transition(s,"dismiss")
                st.rerun()
        return
    issue=s.get("leadership_issue")
    if not issue: return
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
