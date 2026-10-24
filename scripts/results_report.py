"""results/runs/ から集計表（リーダーボード）、対応差、dashboard 用データを作る。

    python scripts/results_report.py --out /tmp/report
    python scripts/results_report.py --out /tmp/report --baseline hybrid_v6

出力は DIR/leaderboard.json、DIR/dashboard.json、DIR/index.html。生成物はコミットしない。
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
POOL_JSON = ROOT / "opponents" / "pool.json"


def load_runs(results: Path = RESULTS) -> list[tuple[dict, list[dict]]]:
    base = Path(results) / "runs" if (Path(results) / "runs").is_dir() else Path(results)
    runs = []
    for run_dir in sorted(p for p in base.iterdir() if (p / "manifest.json").exists()):
        manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
        jsonl = run_dir / "games.jsonl"
        if jsonl.exists():
            rows = [json.loads(x) for x in jsonl.read_text(encoding="utf-8").splitlines() if x.strip()]
        else:
            rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run_dir / "games").glob("*.json"))]
        runs.append((manifest, rows))
    return runs


def games_by_candidate(runs) -> dict[str, dict[tuple, dict]]:
    """候補名 -> {(相手, seed, 色): 行}。complete の新しい run を優先し、未完了の run は穴埋めにだけ使う。"""
    def order(item):
        manifest, _ = item
        return (manifest.get("status") == "complete", manifest.get("finished_at") or "", manifest["run_id"])

    out: dict[str, dict[tuple, dict]] = {}
    for manifest, rows in sorted(runs, key=order, reverse=True):
        games = out.setdefault(manifest["candidate"]["name"], {})
        partial = manifest.get("status") != "complete"
        for row in rows:
            key = (row["opponent"], row["seed"], row["color"])
            if key not in games:
                games[key] = dict(row, _run=manifest["run_id"], _partial=partial)
    return out


def _mean_se(values: list[float]) -> tuple[float | None, float | None]:
    n = len(values)
    if not n:
        return None, None
    mean = sum(values) / n
    if n == 1:
        return mean, None
    var = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, math.sqrt(var / n)


def cell(rows: list[dict]) -> dict:
    mean, se = _mean_se([r["score"] for r in rows])
    return {"n": len(rows), "mean": mean, "se": se,
            "win": sum(r["result"] == "win" for r in rows), "draw": sum(r["result"] == "draw" for r in rows),
            "loss": sum(r["result"] == "loss" for r in rows), "partial": any(r.get("_partial") for r in rows),
            "runs": sorted({r["_run"] for r in rows if "_run" in r})}


def paired_diff(cand: dict[tuple, dict], base: dict[tuple, dict], opponents=None) -> dict:
    """同じ (相手, seed, 色) の試合だけを突き合わせた score の差（候補 - 基準）と、その標準誤差。"""
    keys = sorted(k for k in cand.keys() & base.keys() if opponents is None or k[0] in opponents)
    mean, se = _mean_se([cand[k]["score"] - base[k]["score"] for k in keys])
    return {"n": len(keys), "diff": mean, "se": se}


def build(results: Path = RESULTS, pool: list[str] | None = None, baseline: str | None = None) -> dict:
    if pool is None:
        pool = json.loads(POOL_JSON.read_text(encoding="utf-8"))["pool"] if POOL_JSON.exists() else []
    runs = load_runs(results)
    by_cand = games_by_candidate(runs)
    opponents = sorted({k[0] for games in by_cand.values() for k in games},
                       key=lambda o: (o not in pool, pool.index(o) if o in pool else 0, o))
    candidates = []
    for name, games in sorted(by_cand.items()):
        cells = {}
        for opp in opponents:
            rows = [g for k, g in games.items() if k[0] == opp]
            if rows:
                cells[opp] = cell(rows)
        pool_means = [cells[o]["mean"] for o in pool if o in cells]
        entry = {"name": name, "cells": cells, "games": len(games),
                 "pool_mean": sum(pool_means) / len(pool_means) if pool_means else None,
                 "pool_min": min(pool_means) if pool_means else None,
                 "pool_complete": bool(pool) and all(o in cells and not cells[o]["partial"] for o in pool)}
        if baseline and baseline in by_cand and baseline != name:
            base = by_cand[baseline]
            entry["paired_vs_baseline"] = {
                "pool": paired_diff(games, base, set(pool) or None),
                **{o: paired_diff(games, base, {o}) for o in cells},
            }
        candidates.append(entry)
    candidates.sort(key=lambda c: (c["pool_mean"] is None, -(c["pool_mean"] or 0), c["name"]))
    return {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "pool": pool, "baseline": baseline,
            "opponents": opponents, "runs": len(runs), "candidates": candidates}


def _fmt(c: dict | None) -> str:
    if not c:
        return "-"
    flag = "*" if c["partial"] else ""
    return f"{c['mean']:.3f} {c['win']}/{c['draw']}/{c['loss']}{flag}"


def to_text(report: dict) -> str:
    cols = report["opponents"]
    lines = ["candidate | " + " | ".join(cols) + " | pool mean | pool min"]
    for c in report["candidates"]:
        pm = "-" if c["pool_mean"] is None else f"{c['pool_mean']:.3f}"
        pn = "-" if c["pool_min"] is None else f"{c['pool_min']:.3f}"
        lines.append(f"{c['name']} | " + " | ".join(_fmt(c["cells"].get(o)) for o in cols) + f" | {pm} | {pn}")
    return "\n".join(lines) + "\n"


def to_html(report: dict) -> str:
    cols = report["opponents"]
    head = "".join(f"<th>{html.escape(o)}{' (pool)' if o in report['pool'] else ''}</th>" for o in cols)
    body = []
    for c in report["candidates"]:
        cells = "".join(f"<td>{html.escape(_fmt(c['cells'].get(o)))}</td>" for o in cols)
        pm = "-" if c["pool_mean"] is None else f"{c['pool_mean']:.3f}"
        pn = "-" if c["pool_min"] is None else f"{c['pool_min']:.3f}"
        body.append(f"<tr><th>{html.escape(c['name'])}</th>{cells}<td>{pm}</td><td>{pn}</td></tr>")
    return ("<!doctype html><meta charset='utf-8'><title>air_combatAI_5 leaderboard</title>"
            "<style>body{font-family:sans-serif}td,th{border:1px solid #ccc;padding:4px 8px;text-align:right}"
            "table{border-collapse:collapse}</style>"
            f"<h1>リーダーボード</h1><p>results/ の {report['runs']} run から生成（{report['generated_at']}）。"
            "セルは平均スコアと 勝/分/敗。* は未完了の run を含む。pool mean はプールの相手ごとの平均の平均。</p>"
            f"<table><tr><th>候補</th>{head}<th>pool mean</th><th>pool min</th></tr>{''.join(body)}</table>")


def dashboard_data(report: dict) -> dict:
    return {"generated_at": report["generated_at"], "pool": report["pool"], "opponents": report["opponents"],
            "runs": report["runs"],
            "rows": [{"name": c["name"], "pool_mean": c["pool_mean"], "pool_min": c["pool_min"],
                      "pool_complete": c["pool_complete"], "games": c["games"],
                      "cells": {o: _fmt(v) for o, v in c["cells"].items()}} for c in report["candidates"]]}


def write(report: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "leaderboard.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "dashboard.json").write_text(json.dumps(dashboard_data(report), ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    (out / "index.html").write_text(to_html(report), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="results_report")
    ap.add_argument("--results", default=str(RESULTS))
    ap.add_argument("--out", default=None, help="leaderboard.json / dashboard.json / index.html の出力先")
    ap.add_argument("--baseline", default=None, help="対応差の基準にする候補名（例 hybrid_v6）")
    ap.add_argument("--candidate", default=None, help="この候補だけ表示する")
    a = ap.parse_args(argv)
    report = build(Path(a.results), baseline=a.baseline)
    if a.candidate:
        report["candidates"] = [c for c in report["candidates"] if c["name"] in (a.candidate, a.baseline)]
    if a.out:
        write(report, Path(a.out))
    sys.stdout.write(to_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
