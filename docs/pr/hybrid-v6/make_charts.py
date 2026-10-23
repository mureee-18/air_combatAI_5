"""PR 用の図を生成（評価結果ディレクトリ /workspace/research/eval を読む）."""
import glob, json, statistics as st, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
B = "/workspace/research/eval/"; OUT = sys.argv[1] if len(sys.argv) > 1 else "."
OPPS = ["BenchMark", "MA", "EH", "O_RUSH", "O_GUARD", "O_BMAGG"]
OPPL = ["BenchMark", "MA版", "escort_hunt", "突撃型\n(O_RUSH)", "護衛型\n(O_GUARD)", "BM強化\n(O_BMAGG)"]
AG = ["MA", "EH", "H1", "V6"]; AGL = {"MA": "MA版", "EH": "escort_hunt", "H1": "H1", "V6": "V6 (本PR)"}
FIX = {("EH", "BenchMark"): "eh0", ("EH", "MA"): "eh_vs_ma", ("MA", "BenchMark"): "ma_vs_bm"}
def load(d):
    o = {}
    for f in glob.glob(B + d + "/*.json"):
        if not f.endswith("_log.json"):
            r = json.load(open(f)); o[(r["color"], r["seed"])] = r
    return o
def get(a, o):
    if (a, o) in FIX: return load(FIX[(a, o)])
    if a == "MA" and o == "EH":
        e = load("eh_vs_ma")
        return {(("Blue" if c == "Red" else "Red"), s): dict(r, score=1 - r["score"], result={"win": "loss", "loss": "win"}.get(r["result"], "draw")) for (c, s), r in e.items()}
    if a == "MA" and o == "MA": return None
    return load("pool/%s_vs_%s" % (a, o))
plt.rcParams["font.family"] = ["Noto Sans CJK JP", "DejaVu Sans"]
M = np.full((len(AG), len(OPPS)), np.nan); WDL = {}
for i, a in enumerate(AG):
    for j, o in enumerate(OPPS):
        D = get(a, o)
        if D is None: M[i, j] = 0.5; continue
        M[i, j] = st.mean(r["score"] for r in D.values())
        WDL[(a, o)] = [sum(r["result"] == k for r in D.values()) for k in ("win", "draw", "loss")]
# 1) pool avg bar
pm = M.mean(axis=1)
fig, ax = plt.subplots(figsize=(7, 3.6))
cols = ["#999", "#6baed6", "#9ecae1", "#e6550d"]
b = ax.bar([AGL[a] for a in AG], pm, color=cols)
for r, v in zip(b, pm): ax.text(r.get_x() + r.get_width() / 2, v + 0.005, "%.3f" % v, ha="center")
ax.axhline(0.5, ls="--", c="k", lw=0.8); ax.set_ylim(0.4, 0.7); ax.set_ylabel("6相手プールの平均スコア")
ax.set_title("プール平均スコア（各相手 40戦 = seed1-20×両色）"); fig.tight_layout(); fig.savefig(OUT + "/chart_pool_avg.png", dpi=130)
# 2) heatmap
fig, ax = plt.subplots(figsize=(8.5, 3.6))
im = ax.imshow(M, cmap="RdYlGn", vmin=0.2, vmax=0.8)
ax.set_xticks(range(len(OPPS)), OPPL, fontsize=8); ax.set_yticks(range(len(AG)), [AGL[a] for a in AG])
for i in range(len(AG)):
    for j in range(len(OPPS)):
        ax.text(j, i, ("%.3f" % M[i, j]) + (" (鏡像)" if AG[i] == "MA" and OPPS[j] == "MA" else ""), ha="center", va="center", fontsize=8)
ax.set_title("相手別の平均スコア（緑=有利、0.5=互角）"); fig.colorbar(im, ax=ax, shrink=0.8); fig.tight_layout(); fig.savefig(OUT + "/chart_heatmap.png", dpi=130)
# 3) W/D/L for V6 vs EH
fig, axs = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
for ax, a in zip(axs, ["EH", "V6"]):
    w = np.array([WDL.get((a, o), [0, 0, 0]) for o in OPPS])
    ax.bar(range(6), w[:, 0], color="#31a354", label="勝ち"); ax.bar(range(6), w[:, 1], bottom=w[:, 0], color="#bdbdbd", label="引分")
    ax.bar(range(6), w[:, 2], bottom=w[:, 0] + w[:, 1], color="#de2d26", label="負け")
    ax.set_xticks(range(6), OPPL, fontsize=7); ax.set_title(AGL[a] + " の勝敗（各40戦）")
axs[0].legend(fontsize=8); fig.tight_layout(); fig.savefig(OUT + "/chart_wdl.png", dpi=130)
# 4) V6 trajectory (win vs O_RUSH)
D = get("V6", "O_RUSH"); wins = sorted([r for r in D.values() if r["result"] == "win"], key=lambda r: r["step_count"])
r = wins[len(wins) // 2]
fig, ax = plt.subplots(figsize=(5.2, 6))
names = {"1": "アタッカー1", "2": "アタッカー2", "3": "ディフェンダー1", "4": "ディフェンダー2"}
cc = {"1": "#e6550d", "2": "#fd8d3c", "3": "#3182bd", "4": "#6baed6"}
for sl, tr in sorted(r["track"].items()):
    xs = [p[1] for p in tr]; ys = [p[2] for p in tr]
    ax.plot(ys, xs, c=cc[sl], label=names[sl]); ax.plot(ys[-1], xs[-1], "o", c=cc[sl])
for x0 in (115, 125): ax.axhline(x0, c="r", lw=0.6, ls=":")
ax.axhline(-120, c="g", lw=0.6, ls=":"); ax.axhline(0, c="k", lw=0.5)
ax.text(-110, 128, "敵の護衛対象機レーストラック", color="r", fontsize=7); ax.text(-110, -116, "自軍護衛対象機の周回域（推定）", color="g", fontsize=7)
ax.set_xlim(-130, 130); ax.set_ylim(-140, 140); ax.set_xlabel("y [km]"); ax.set_ylabel("x [km]（上が敵陣）")
ax.set_title("V6 の軌跡: 突撃型に勝った試合\n(%s seed%d, %d秒で撃破, score %.3f)" % (r["color"], r["seed"], r["step_count"], r["score"]), fontsize=9)
ax.legend(fontsize=7, loc="lower right"); fig.tight_layout(); fig.savefig(OUT + "/v6_track_vs_rush.png", dpi=130)
print("pool", dict(zip(AG, pm.round(3))))
