import json,glob,sys,math
rows=[json.load(open(f)) for f in sorted(glob.glob(sys.argv[1]+"/*.json")) if not f.endswith("_log.json")]
n=len(rows)
if not n: print("no rows"); sys.exit()
sc=[r["score"] for r in rows]; m=sum(sc)/n; se=(sum((x-m)**2 for x in sc)/(n-1))**.5/n**.5 if n>1 else 0
L=sum(r["our_launched"] for r in rows); H=sum(r["our_hits"] for r in rows)
res={"label":sys.argv[1].split("/")[-1],"n":n,"avg_score":round(m,4),"se":round(se,4),"win":sum(r["result"]=="win" for r in rows),"draw":sum(r["result"]=="draw" for r in rows),"loss":sum(r["result"]=="loss" for r in rows),
 "avg_our_alive":round(sum(r["our_alive"] for r in rows)/n,2),"avg_enemy_alive":round(sum(r["enemy_alive"] for r in rows)/n,2),"launched":L,"hits":H,"hit_rate":round(H/L,3) if L else None,
 "escort_kills":sum(r["enemy_escort_killed"] for r in rows),"our_escort_lost":sum(r["our_escort_killed"] for r in rows),"errors":sum(r["error"] for r in rows)}
print(json.dumps(res,ensure_ascii=False))
json.dump(res,open(sys.argv[1]+".summary.json","w"),indent=1)
