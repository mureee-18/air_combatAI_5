import json,glob,statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"]="Noto Sans CJK JP"
E="/workspace/research/eval"; OUT="/workspace/pr_wt/docs/pr/escort-hunt-irst"
def load(ds):
    out={}
    for d in ds.split(","):
        for f in glob.glob(f"{E}/{d}/*.json"):
            if f.endswith("_log.json"): continue
            r=json.load(open(f)); out[(r["color"],r["seed"])]=r
    return out
V=[("baseline,baseline_11_20","従来\n(default)"),("eh0","escort_hunt\n(既定)"),("v1_rt","v1\n周回予測"),
   ("v4_edge","v4\n端ルート"),("v5_edge_rt","v5\n端+周回予測"),("v6_edgeEsc","v6\n端(護衛側)"),("v7_kite","v7\n端+kite")]
D={k:load(k) for k,_ in V}
for k in D: assert len(D[k])==40,(k,len(D[k]))
lab=[l for _,l in V]
col=["#9e9e9e","#1f77b4"]+["#ff9f43"]*5
# 1 avg score
m=[st.mean(r["score"] for r in D[k].values()) for k,_ in V]
se=[st.stdev([r["score"] for r in D[k].values()])/40**.5 for k,_ in V]
fig,ax=plt.subplots(figsize=(9,4.2),dpi=110)
b=ax.bar(lab,m,yerr=se,capsize=4,color=col)
for x,(mm,ss) in enumerate(zip(m,se)): ax.text(x,mm+ss+0.01,f"{mm:.3f}",ha="center",fontsize=9)
ax.axhline(0.5,ls="--",c="gray",lw=0.8); ax.text(6.45,0.505,"引き分け=0.5",ha="right",fontsize=8,color="gray")
ax.set_ylabel("平均スコア（±標準誤差）"); ax.set_ylim(0,0.7)
ax.set_title("BenchMark相手 40試合（seed1-20 × 赤/青）の平均スコア")
fig.tight_layout(); fig.savefig(f"{OUT}/chart_avg_score.png"); plt.close(fig)
# 2 WDL
W=[sum(r["result"]=="win" for r in D[k].values()) for k,_ in V]
Dr=[sum(r["result"]=="draw" for r in D[k].values()) for k,_ in V]
L=[sum(r["result"]=="loss" for r in D[k].values()) for k,_ in V]
fig,ax=plt.subplots(figsize=(9,4.2),dpi=110)
ax.bar(lab,W,color="#2ca02c",label="勝ち"); ax.bar(lab,Dr,bottom=W,color="#bdbdbd",label="引き分け")
ax.bar(lab,L,bottom=[a+b for a,b in zip(W,Dr)],color="#d62728",label="負け")
for x in range(len(V)):
    for y0,h in ((0,W[x]),(W[x],Dr[x]),(W[x]+Dr[x],L[x])):
        if h: ax.text(x,y0+h/2,str(h),ha="center",va="center",fontsize=9,color="white")
ax.set_ylabel("試合数（計40）"); ax.legend(loc="upper right",ncol=3,fontsize=9); ax.set_ylim(0,46)
ax.set_title("勝ち / 引き分け / 負け")
fig.tight_layout(); fig.savefig(f"{OUT}/chart_wdl.png"); plt.close(fig)
# 3 kill time
K=[("eh0","escort_hunt（既定）","#1f77b4"),("v1_rt","v1 周回予測","#9467bd"),("v5_edge_rt","v5 端+周回予測","#ff7f0e")]
fig,ax=plt.subplots(figsize=(9,4.2),dpi=110)
data=[]
for k,l,c in K:
    kt=sorted(r["step_count"] for r in D[k].values() if r["enemy_escort_killed"] and r["result"]=="win"); data.append(kt)
bp=ax.boxplot(data,vert=False,widths=0.5,patch_artist=True,showfliers=False)
for p,(_,_,c) in zip(bp["boxes"],K): p.set_facecolor(c); p.set_alpha(0.35)
import random; random.seed(0)
for i,(kt,(_,_,c)) in enumerate(zip(data,K)):
    ax.scatter(kt,[i+1+random.uniform(-0.15,0.15) for _ in kt],s=18,color=c,zorder=3)
    ax.text(1830,i+1,f"n={len(kt)}\n中央値 {st.median(kt):.0f}s\n≤900s: {sum(t<=900 for t in kt)}",va="center",fontsize=8)
ax.set_yticks([1,2,3],[l for _,l,_ in K]); ax.axvline(900,ls="--",c="green",lw=1); ax.axvline(1800,ls=":",c="gray",lw=1)
ax.set_ylim(0.5,3.7); ax.text(905,3.55,"900s：時間ボーナス満点",fontsize=8,color="green"); ax.set_xlim(0,2050)
ax.set_xlabel("敵護衛対象機を撃墜して勝った時刻 [s]（勝ち試合のみ）"); ax.set_title("敵護衛対象機の撃墜時刻の分布")
fig.tight_layout(); fig.savefig(f"{OUT}/chart_kill_time.png"); plt.close(fig)
print(m,se,W,Dr,L,[len(x) for x in data])
