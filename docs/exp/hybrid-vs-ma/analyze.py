import json,glob,sys,collections,statistics as st
d=sys.argv[1]
rows=[json.load(open(f)) for f in sorted(glob.glob(d+"/*.json")) if not f.endswith("_log.json")]
c=collections.Counter(); 
for r in rows:
    k=(r["result"],r["endReason"],"ourEscLost" if r["our_escort_killed"] else "-","enEscKilled" if r["enemy_escort_killed"] else "-")
    c[k]+=1
for k,v in sorted(c.items()): print(v,k)
n=len(rows)
print("our_launched/m",round(sum(r["our_launched"] for r in rows)/n,1),"enemy_launched/m",round(sum(r["enemy_launched"] for r in rows)/n,1),
 "our_hits",sum(r["our_hits"] for r in rows),"enemy_hits",sum(r["enemy_hits"] for r in rows),"steps_med",st.median(r["step_count"] for r in rows))
for col in ("Red","Blue"):
    s=[r["score"] for r in rows if r["color"]==col]; print(col,round(sum(s)/len(s),3))
if "-v" in sys.argv:
    for r in sorted(rows,key=lambda r:(r["seed"],r["color"])):
        print(r["seed"],r["color"][0],r["result"][0],round(r["score"],3),r["endReason"],r["step_count"],"L",r["our_launched"],r["enemy_launched"],"H",r["our_hits"],r["enemy_hits"],"alive",r["our_alive"],r["enemy_alive"],"esc",int(r["enemy_escort_killed"]),int(r["our_escort_killed"]),"deaths",r["death_step"])
