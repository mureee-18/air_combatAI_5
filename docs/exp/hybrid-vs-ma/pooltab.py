import json,glob,statistics as st,os
B="/workspace/research/eval/"
def load(d):
    o={}
    for f in glob.glob(B+d+"/*.json"):
        if f.endswith("_log.json"): continue
        r=json.load(open(f)); o[(r["color"],r["seed"])]=r
    return o
# reference dirs for EH and MA vs each opponent
REF={"EH":{"BenchMark":"eh0","MA":"eh_vs_ma","EH":"pool/EH_vs_EH"},"MA":{"BenchMark":"ma_vs_bm"}}
def get(agent,opp):
    if agent in REF and opp in REF[agent]: return load(REF[agent][opp])
    if agent=="MA" and opp=="EH":
        e=load("eh_vs_ma"); return {(("Blue" if c=="Red" else "Red"),s):dict(r,score=1-r["score"] if r["result"]!="draw" else 0.5,result={"win":"loss","loss":"win"}.get(r["result"],"draw")) for (c,s),r in e.items()}
    if agent=="MA" and opp=="MA": return None
    return load("pool/%s_vs_%s"%(agent,opp))
for ag in ["EH","MA","H1","H2","H3"]:
    line=[ag.ljust(4)]; means=[]
    for opp in ["BenchMark","MA","EH"]:
        D=get(ag,opp)
        if not D or len(D)<40: line.append("%s: n=%s"%(opp,len(D) if D else 0)); continue
        R=get("EH",opp); keys=sorted(D)
        sc=[D[k]["score"] for k in keys]; m=st.mean(sc); se=st.stdev(sc)/len(sc)**.5
        dd=[D[k]["score"]-R[k]["score"] for k in keys]; dm=st.mean(dd); dse=st.stdev(dd)/len(dd)**.5 if ag!="EH" else 0
        w=sum(D[k]["result"]=="win" for k in keys); dr=sum(D[k]["result"]=="draw" for k in keys)
        line.append("%s %.3f±%.3f %d/%d/%d ΔEH %+.3f±%.3f%s"%(opp,m,se,w,dr,40-w-dr,dm,dse,"*" if dse and abs(dm)>2*dse else ""))
        means.append(m)
    if len(means)==3: line.append("pool=%.3f"%st.mean(means))
    print(" | ".join(line))
