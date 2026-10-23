"""agent/args.json を変える PR の昇格ルールを確かめる。

新しい agent/args.json と、merge base の agent/args.json（現行の既定）の両方について、
results/runs/ に complete の run があり、seeds 1〜20 × 両色 × opponents/pool.json の pool 全部を覆うこと。
そのうえで次の2つを満たすときだけ通す。
  1. pool の最小値（相手ごとの平均スコアの最小）が現行以上
  2. pool 全体の対応差（同じ相手・seed・色の score 差）の平均が、その標準誤差より大きい

    python scripts/check_promotion.py --base origin/master
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEDS = list(range(1, 21))
COLORS = ["Red", "Blue"]

_spec = importlib.util.spec_from_file_location("results_report", ROOT / "scripts" / "results_report.py")
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)


def games_for_args(runs, args: dict) -> tuple[dict, list[str]]:
    """candidate.args が args と一致する complete run の試合を (相手, seed, 色) で集める。"""
    games, ids = {}, []
    for manifest, rows in sorted(runs, key=lambda r: (r[0].get("finished_at") or "", r[0]["run_id"]), reverse=True):
        if manifest.get("status") != "complete" or manifest["candidate"].get("args") != args:
            continue
        ids.append(manifest["run_id"])
        for row in rows:
            games.setdefault((row["opponent"], row["seed"], row["color"]), row)
    return games, ids


def missing(games: dict, pool: list[str], seeds=SEEDS) -> list[tuple]:
    return [(o, s, c) for o in pool for s in seeds for c in COLORS if (o, s, c) not in games]


def pool_stats(games: dict, pool: list[str], seeds=SEEDS) -> dict:
    means = {o: sum(games[(o, s, c)]["score"] for s in seeds for c in COLORS) / (len(seeds) * len(COLORS))
             for o in pool}
    return {"per_opponent": means, "min": min(means.values()), "mean": sum(means.values()) / len(means)}


def verdict(runs, new_args: dict, cur_args: dict, pool: list[str], seeds=SEEDS) -> tuple[bool, list[str]]:
    lines = []
    new, new_ids = games_for_args(runs, new_args)
    cur, cur_ids = games_for_args(runs, cur_args)
    ok = True
    for label, games, ids in (("new agent/args.json", new, new_ids), ("current default", cur, cur_ids)):
        gap = missing(games, pool, seeds)
        if gap:
            ok = False
            total = len(pool) * len(seeds) * len(COLORS)
            lines.append(f"FAIL {label}: complete runs with these args miss {len(gap)} of {total} games "
                         f"(first missing: {gap[0]}); runs with matching args: {ids or 'none'}")
        else:
            lines.append(f"ok   {label}: runs {ids}")
    if not ok:
        return False, lines
    ns, cs = pool_stats(new, pool, seeds), pool_stats(cur, pool, seeds)
    lines.append("pool per opponent (new / current): " + ", ".join(
        f"{o} {ns['per_opponent'][o]:.3f}/{cs['per_opponent'][o]:.3f}" for o in pool))
    if ns["min"] < cs["min"]:
        ok = False
        lines.append(f"FAIL pool min {ns['min']:.4f} < current {cs['min']:.4f}")
    else:
        lines.append(f"ok   pool min {ns['min']:.4f} >= current {cs['min']:.4f}")
    keys = {(o, s, c) for o in pool for s in seeds for c in COLORS}
    pd = rr.paired_diff({k: new[k] for k in keys}, {k: cur[k] for k in keys})
    if pd["se"] is None or not pd["diff"] > pd["se"]:
        ok = False
        lines.append(f"FAIL paired pool diff {pd['diff']:+.4f} is not larger than its SE {pd['se']} (n={pd['n']})")
    else:
        lines.append(f"ok   paired pool diff {pd['diff']:+.4f} > SE {pd['se']:.4f} (n={pd['n']})")
    return ok, lines


def _git_show(ref: str, path: str) -> str:
    return subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_promotion")
    ap.add_argument("--base", default="origin/master", help="比べる相手のブランチ（merge base を使う）")
    ap.add_argument("--results", default=str(ROOT / "results"))
    a = ap.parse_args(argv)
    merge_base = subprocess.run(["git", "merge-base", a.base, "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                check=True).stdout.strip()
    cur_args = json.loads(_git_show(merge_base, "agent/args.json"))
    new_args = json.loads((ROOT / "agent" / "args.json").read_text(encoding="utf-8"))
    if new_args == cur_args:
        print("agent/args.json is unchanged; no promotion to check")
        return 0
    pool = json.loads((ROOT / "opponents" / "pool.json").read_text(encoding="utf-8"))["pool"]
    ok, lines = verdict(rr.load_runs(Path(a.results)), new_args, cur_args, pool)
    print("\n".join(lines))
    print("promotion: PASS" if ok else "promotion: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
