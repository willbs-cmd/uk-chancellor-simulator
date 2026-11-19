"""Five-year strategy and end-of-term Chancellor legacy."""
import streamlit as st
TARGETS={"growth":2.0,"debt":85.0,"productivity":1.5,"wages":2.0,"services":70.0}
LABELS={"growth":"GDP growth","debt":"Debt-to-GDP","productivity":"Productivity","wages":"Real wages","services":"Public services"}
def ensure(s=None):
 s=s or st.session_state
 defaults={"economic_strategy":{"title":"Productivity and living standards","targets":dict(TARGETS)},"economic_strategy_reviews":[],"economic_strategy_last_review":"","term_final_assessment":None,"term_legacy_archive":[]}
 for k,v in defaults.items():
  if k not in s:s[k]=dict(v) if isinstance(v,dict) else list(v) if isinstance(v,list) else v
 a=dict(s.economic_strategy);t=dict(TARGETS);t.update(a.get("targets") or {});a["targets"]=t;s.economic_strategy=a
 return s
def _clip(x):return max(0.,min(100.,float(x)))
def metrics(s):
 s=ensure(s);c=s.get("country") or {}
 try:
  import country
  service=country._overall(c)*100
 except Exception:service=50.
 return {"growth":float(s.get("growth",0)),"debt":float(s.get("debt",0)),"productivity":float(s.get("productivity_growth",s.get("longrun_productivity",0))),"wages":float(c.get("real_wages",s.get("real_wage_growth",0))),"services":float(service)}
def set_targets(s,targets,title):
 s=ensure(s)
 if int(s.get("year",1))!=1:return False
 clean={}
 for k,d in TARGETS.items():
  lo,hi=(0,5) if k in ("growth","productivity","wages") else ((50,120) if k=="debt" else (30,95))
  clean[k]=round(max(lo,min(hi,float(targets.get(k,d)))),1)
 s.economic_strategy={"title":str(title)[:80],"targets":clean};return True
def _score(k,a,t):
 return round(_clip(70+(-1 if k=="debt" else 1)*(float(a)-float(t))*(5 if k in ("growth","productivity","wages") else 12)))
def annual_review(s=None):
 s=ensure(s);period=f"{int(s.get('term',1))}:{int(s.get('year',1))}"
 if s.get("economic_strategy_last_review")==period:return None
 m=metrics(s);t=s.economic_strategy["targets"];goals={k:{"label":LABELS[k],"target":t[k],"actual":round(m[k],2),"score":_score(k,m[k],t[k])} for k in TARGETS}
 shocks=len(s.get("crisis_event_history",[]))+len(s.get("financial_crisis_history",[]));prev=list(s.get("economic_strategy_reviews",[]));old=int(prev[-1].get("shock_count",0)) if prev else 0
 row={"term":int(s.get("term",1)),"year":int(s.get("year",1)),"label":f"Year {s.get('year',1)}","metrics":m,"goals":goals,"score":round(sum(x["score"] for x in goals.values())/5),"shock_count":shocks,"shocks_this_year":max(0,shocks-old)}
 prev.append(row);s.economic_strategy_reviews=prev[-30:];s.economic_strategy_last_review=period;return row
def countdown(s=None):
 s=ensure(s);y=int(s.get("year",1));return max(0,6-y),min(5,max(0,y-1))
def finalise(s=None):
 s=ensure(s)
 if int(s.get("year",1))<5:return None
 term=int(s.get("term",1));old=s.get("term_final_assessment")
 if isinstance(old,dict) and int(old.get("term",-1))==term:return old
 rows=[r for r in s.economic_strategy_reviews if int(r.get("term",-1))==term]
 if not rows:
  r=annual_review(s)
  if r:rows=[r]
 t=s.economic_strategy["targets"];goals={}
 for k in TARGETS:
  vals=[float(r["metrics"][k]) for r in rows];avg=sum(vals)/len(vals) if vals else float(t[k]);goals[k]={"label":LABELS[k],"target":t[k],"average":round(avg,2),"score":_score(k,avg,t[k])}
 strategy=round(sum(g["score"] for g in goals.values())/5)
 try:
  import long_run_simulation
  legacy=long_run_simulation.legacy_assessment(s).get("overall",50)
 except Exception:legacy=50
 fiscal=_clip(55+float(s.get("headroom",0))*2.2-max(0,float(s.get("deficit",0))-80)*.1-max(0,float(s.get("debt",0))-90)*.12)
 politics=_clip(.35*float(s.get("approval",50))+.25*float(s.get("pm_opinion",50))+.2*float(s.get("party_opinion",50))+.2*float(s.get("cab_opinion",50))
 )
 result={"term":term,"years_completed":len(rows),"strategy_title":s.economic_strategy["title"],"strategy_score":strategy,"goals":goals,"fiscal_record":round(fiscal),"political_influence":round(politics),"structural_legacy":round(float(legacy)),"shocks_managed":sum(int(r.get("shocks_this_year",0)) for r in rows)}
 result["overall"]=round(.4*strategy+.25*fiscal+.2*politics+.15*float(legacy));result["grade"]="A" if result["overall"]>=85 else "B" if result["overall"]>=75 else "C" if result["overall"]>=65 else "D" if result["overall"]>=50 else "E"
 s.term_final_assessment=result;archive=list(s.get("term_legacy_archive",[]))
 if not any(int(x.get("term",-1))==term for x in archive):archive.append(result)
 s.term_legacy_archive=archive[-10:];return result
def render(s=None):
 s=ensure(s);left,done=countdown(s);t=s.economic_strategy["targets"];st.markdown("#### Five-year economic strategy");st.caption("Set targets for growth, debt, productivity, wages and public services. Delivery is reviewed every year.")
 a,b,c=st.columns(3);a.metric("Election countdown",f"{left} years");b.metric("Years completed",f"{done}/5");c.metric("Strategy",s.economic_strategy["title"])
 if int(s.get("year",1))==1 and not s.economic_strategy_reviews:
  with st.expander("Set five-year targets",expanded=True):
   title=st.text_input("Strategy title",s.economic_strategy["title"],key="fiveyear_title");x,y=st.columns(2)
   g=x.slider("GDP growth target (%)",0.,5.,float(t["growth"]),.1,key="fiveyear_growth");d=y.slider("Debt target (% GDP)",50.,120.,float(t["debt"]),1.,key="fiveyear_debt")
   p=x.slider("Productivity target (%)",0.,5.,float(t["productivity"]),.1,key="fiveyear_productivity");w=y.slider("Real wage target (%)",0.,5.,float(t["wages"]),.1,key="fiveyear_wages");v=st.slider("Public-service target",30.,95.,float(t["services"]),1.,key="fiveyear_services")
   if st.button("Adopt five-year strategy",type="primary",key="fiveyear_adopt"):
    set_targets(s,{"growth":g,"debt":d,"productivity":p,"wages":w,"services":v},title);st.success("Five-year economic strategy adopted.");st.rerun()
 m=metrics(s);cols=st.columns(5)
 for col,k in zip(cols,TARGETS):
  col.metric(LABELS[k],f"{m[k]:.1f}",f"Target {'≤' if k=='debt' else '≥'} {t[k]:.1f}")
 rows=[r for r in s.economic_strategy_reviews if int(r.get("term",-1))==int(s.get("term",1))]
 if rows:
  st.dataframe([{"Year":r["year"],"Strategy score":f"{r['score']}/100","Growth":f"{r['metrics']['growth']:+.2f}%","Debt":f"{r['metrics']['debt']:.1f}%","Services":f"{r['metrics']['services']:.1f}","Shocks":r["shocks_this_year"]} for r in rows],hide_index=True,use_container_width=True)
 final=s.get("term_final_assessment")
 if final and int(final.get("term",-1))==int(s.get("term",1)):
  st.markdown("#### Five-year Chancellor's legacy");st.metric("Overall term assessment",f"{final['grade']} · {final['overall']}/100");st.dataframe([{"Objective":v["label"],"Five-year average":v["average"],"Target":v["target"],"Score":v["score"]} for v in final["goals"].values()],hide_index=True,use_container_width=True)
