"""共有コアの変更が後方互換かを確かめる。既定ビルドと全プリセットを、merge base と HEAD で同じ決定論対戦にかけ、
1行でも結果が変われば失敗する。ファイルが1つも変わらない候補は対戦を省く。

    python scripts/check_core_compat.py --base origin/master --workers 8
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eval_pool as ep  # noqa: E402
import results_store as rs  # noqa: E402

KEYS = ["result", "score", "step_count", "endReason", "our_alive", "enemy_alive", "our_launched", "our_hits",
        "enemy_launched", "enemy_hits", "error"]


def build(tree: Path, preset_file: Path | None, dest: Path) -> None:
    """tree の build_submission.py で組み立てて dest に置く。--out が無い古いスクリプトにも対応する。"""
    script = tree / "scripts" / "build_submission.py"
    out = Path(tempfile.mkdtemp(prefix="compat_build_"))
    try:
        cmd = [sys.executable, str(script)] + (["--args", str(preset_file)] if preset_file else [])
        has_out = "--out" in script.read_text(encoding="utf-8")
        if has_out:
            cmd += ["--out", str(out)]
        subprocess.run(cmd, cwd=tree, check=True, capture_output=True, text=True)
        staging = out / "MyAgent" if has_out else tree / "submission" / "MyAgent"
        shutil.copytree(staging, dest, ignore=shutil.ignore_patterns("__pycache__"))
    finally:
        shutil.rmtree(out, ignore_errors=True)


def candidates(root: Path = ROOT) -> list[tuple[str, str | None]]:
    presets = sorted((root / "agent/presets").glob("*.json"))
    return [("default", None)] + [(p.stem, f"agent/presets/{p.name}") for p in presets]


def play(sim: Path, cand: str, opp: str, seed: int, color: str) -> dict:
    spec = {"sim": str(sim), "cand": cand, "opp": opp, "seed": seed, "color": color}
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "eval_pool.py"), "_game", json.dumps(spec)], cwd=sim,
                       env=dict(os.environ, PYTHONPATH=str(sim)), capture_output=True, text=True)
    rows = [line[4:] for line in r.stdout.splitlines() if line.startswith("ROW ")]
    if r.returncode or not rows:
        return {"error": True, "crash": (r.stderr or r.stdout)[-400:]}
    return json.loads(rows[-1])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="check_core_compat")
    ap.add_argument("--base", default="origin/master")
    ap.add_argument("--seeds", default="1-3")
    ap.add_argument("--colors", default="both", choices=sorted(ep.COLORS))
    ap.add_argument("--opponents", default="BenchMark")
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    ap.add_argument("--sim-dir", default=None)
    ap.add_argument("--out", default=None, help="結果の JSON を書く先")
    a = ap.parse_args(argv)
    sim = ep.resolve_sim(a.sim_dir)
    if not (sim / "src" / "fight.py").exists():
        raise SystemExit(f"simulator not found in {sim}; pass --sim-dir or set ATLA5_SIM_DIR")
    merge_base = subprocess.run(["git", "merge-base", a.base, "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                check=True).stdout.strip()
    pool = ep.load_pool()
    opponents = ep.resolve_opponents(a.opponents, pool)
    seeds, colors = ep.parse_seeds(a.seeds), ep.COLORS[a.colors]
    run_id = rs.new_run_id("compat")
    base_rel = f"Agents/_runs/{ep.module_name(run_id)}"
    deploy = sim / base_rel
    base_tree = Path(tempfile.mkdtemp(prefix="compat_base_"))
    t0 = time.time()
    jobs, games = [], []
    report = {"merge_base": merge_base, "candidates": {}, "changed": []}
    try:
        archive = subprocess.run(["git", "archive", merge_base], cwd=ROOT, check=True, capture_output=True).stdout
        subprocess.run(["tar", "-x", "-C", str(base_tree)], input=archive, check=True)
        deploy.mkdir(parents=True)
        for o in opponents:
            ep.build_opponent(o, pool["opponents"][o], deploy / f"opp_{o}", sim)
        for name, preset in candidates():
            head_dir, base_dir = deploy / f"head_{name}", deploy / f"base_{name}"
            build(ROOT, ROOT / preset if preset else None, head_dir)
            if preset and not (base_tree / preset).exists():
                report["candidates"][name] = "new at HEAD; nothing to compare"
                continue
            build(base_tree, base_tree / preset if preset else None, base_dir)
            if rs.tree_sha256(head_dir) == rs.tree_sha256(base_dir):
                report["candidates"][name] = "identical files; games skipped"
                continue
            report["candidates"][name] = "files differ; games compared"
            jobs += [(name, o, s, c) for o in opponents for c in colors for s in seeds]

        games = [(side, job) for job in jobs for side in ("base", "head")]

        def run(game):
            side, (name, o, s, c) = game
            return game, play(sim, f"{base_rel}/{side}_{name}", f"{base_rel}/opp_{o}", s, c)

        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            rows = dict(ex.map(run, games))
        for job in jobs:
            name, o, s, c = job
            old, new = rows[("base", job)], rows[("head", job)]
            diff = {k: (old.get(k), new.get(k)) for k in KEYS if old.get(k) != new.get(k)}
            if diff or old.get("crash") or new.get("crash"):
                report["changed"].append({"candidate": name, "opponent": o, "seed": s, "color": c, "diff": diff,
                                          "crash": old.get("crash") or new.get("crash")})
    finally:
        shutil.rmtree(deploy, ignore_errors=True)
        shutil.rmtree(base_tree, ignore_errors=True)
    report["games"] = len(games)
    report["wall_s"] = round(time.time() - t0, 1)
    for name, state in report["candidates"].items():
        print(f"{name}: {state}")
    for row in report["changed"]:
        print(f"CHANGED {row['candidate']} vs {row['opponent']} seed {row['seed']} {row['color']}: {row['diff']}")
    print(f"core compat: {'FAIL' if report['changed'] else 'PASS'} ({report['games']} games, {report['wall_s']} s, "
          f"merge base {merge_base[:7]})")
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    return 1 if report["changed"] else 0


if __name__ == "__main__":
    sys.exit(main())
