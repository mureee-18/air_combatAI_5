"""usage: compare2.py REF_DIR[,REF_DIR2] DIR ...  -> table + paired diffs vs first arg (keys: color,seed)"""
import json,glob,sys,statistics as st
def load(ds):
    out={}
    for d in ds.split(","):
        for f in glob.glob(d+"/*.json"):
            if f.endswith("_log.json"): continue
            r=json.load(open(f)); out[(r["color"],r["seed"])]=r
    return out
def stats(rows):
    n=len(rows); sc=[r["score"] for r in rows]; m=sum(sc)/n; se=st.stdev(sc)/n**.5
    L=sum(r["our_launched"] for r in rows); H=sum(r["our_hits"] for r in rows)
    kt=[r["step_count"] for r in rows if r["enemy_escort_killed"] and r["result"]=="win"]
    att=[]
    for r in rows:
        ds=r.get("death_step")
        if ds is None: continue
        for sl in ("1","2"): att.append(ds.get(sl, 9999))
    return {"n":n,"avg_score":round(m,3),"se":round(se,3),"W/D/L":"%d/%d/%d"%(sum(r["result"]=="win" for r in rows),sum(r["result"]=="draw" for r in rows),sum(r["result"]=="loss" for r in rows)),
      "kill_t_median":st.median(kt) if kt else None,"kill_t_mean":round(st.mean(kt)) if kt else None,"kills<=900":sum(k<=900 for k in kt),
      "hit_rate":round(H/L,3) if L else None,"launched/match":round(L/n,1),"our_escort_lost":sum(r["our_escort_killed"] for r in rows),
      "our_alive":round(sum(r["our_alive"] for r in rows)/n,2),"enemy_alive":round(sum(r["enemy_alive"] for r in rows)/n,2),
      "attacker_death_median":(st.median(att) if att else None),"errors":sum(r["error"] for r in rows)}
ref=load(sys.argv[1]); res={}
for d in sys.argv[1:]:
    D=load(d); keys=sorted(set(D)&set(ref)); s=stats([D[k] for k in keys])
    dd=[D[k]["score"]-ref[k]["score"] for k in keys]
    s["diff_vs_ref"]=round(st.mean(dd),3); s["diff_se"]=round(st.stdev(dd)/len(dd)**.5,3) if len(dd)>1 and d!=sys.argv[1] else 0
    s["sig_2SE"]=abs(s["diff_vs_ref"])>2*s["diff_se"] if s["diff_se"] else None
    res[d]=s; print(d.split("/")[-1][:24].ljust(24),json.dumps(s,ensure_ascii=False))
json.dump(res,open("cmp/compare2_last.json","w"),indent=1,ensure_ascii=False)
