import json,glob,statistics as st,sys
B="/workspace/research/eval/"
OPPS=["BenchMark","MA","EH","O_RUSH","O_GUARD","O_BMAGG"]
AG=sys.argv[1].split(",") if len(sys.argv)>1 else ["EH","MA","H1","H3","V1","V2","V3","V4"]
def load(d):
    o={}
    for f in glob.glob(B+d+"/*.json"):
        if f.endswith("_log.json"): continue
        r=json.load(open(f)); o[(r["color"],r["seed"])]=r
    return o
FIX={("EH","BenchMark"):"eh0",("EH","MA"):"eh_vs_ma",("MA","BenchMark"):"ma_vs_bm"}
def get(a,o):
    if (a,o) in FIX: return load(FIX[(a,o)])
    if a=="MA" and o=="EH":
        e=load("eh_vs_ma"); return {(("Blue" if c=="Red" else "Red"),s):dict(r,score=1-r["score"],result={"win":"loss","loss":"win"}.get(r["result"],"draw")) for (c,s),r in e.items()}
    return load("pool/%s_vs_%s"%(a,o))
rows={}
print("agent | "+" | ".join(OPPS)+" | pool avg (ΔEH±SE) | min")
for a in AG:
    cells=[];means=[];diffs={}
    for o in OPPS:
        D=get(a,o)
        if a=="MA" and o=="MA": cells.append("0.500(mirror)"); means.append(0.5); continue
        if len(D)<40: cells.append("n=%d"%len(D)); continue
        R=get("EH",o); ks=sorted(D); sc=[D[k]["score"] for k in ks]; m=st.mean(sc)
        w=sum(D[k]["result"]=="win" for k in ks); dr=sum(D[k]["result"]=="draw" for k in ks)
        if len(R)==40:
            dd=[D[k]["score"]-R[k]["score"] for k in ks]; diffs[o]=dd
            dm=st.mean(dd); dse=st.stdev(dd)/40**.5 if a!="EH" else 0
            cells.append("%.3f %d/%d/%d Δ%+.3f%s"%(m,w,dr,40-w-dr,dm,"*" if dse and abs(dm)>2*dse else ""))
        else: cells.append("%.3f %d/%d/%d"%(m,w,dr,40-w-dr))
        means.append(m)
    tail=""
    if len(means)==6:
        pm=st.mean(means)
        if len(diffs)==6 and a!="EH":
            per=[st.mean(diffs[o][i] for o in OPPS) for i in range(40)]  # paired per seed/colour avg across opps
            tail="%.3f (Δ%+.3f±%.3f) | %.3f"%(pm,st.mean(per),st.stdev(per)/40**.5,min(means))
        else: tail="%.3f | %.3f"%(pm,min(means))
    print(a+" | "+" | ".join(cells)+" | "+tail)
