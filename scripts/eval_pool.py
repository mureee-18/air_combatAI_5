"""相手プールとの決定論対戦を並列で回し、results/ に書く。ワーカー数に上限はない。

    python scripts/eval_pool.py --preset hybrid_v6 --opponents O_RUSH --seeds 1-20 --workers 8
    python scripts/eval_pool.py --default --opponents pool --seeds 1-20
    python scripts/eval_pool.py --preset hybrid_v6 --opponents O_RUSH --seeds 1-20 --resume <run_id>

1試合 = 1プロセス。候補と相手は <sim>/Agents/_runs/<run_id>/ に置き、終わったらその run の分だけ消す。
sim の場所は --sim-dir、環境変数 ATLA5_SIM_DIR、<repo>/workspace の順に探す。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import results_store as rs  # noqa: E402

POOL_JSON = ROOT / "opponents" / "pool.json"
BUILD = ROOT / "scripts" / "build_submission.py"
COLORS = {"both": ["Red", "Blue"], "red": ["Red"], "blue": ["Blue"]}


def parse_seeds(text: str) -> list[int]:
    """'1-20' や '1,3,5-7' を seed のリストにする。"""
    seeds = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.partition("-")
        seeds.extend(range(int(lo), int(hi or lo) + 1))
    if not seeds:
        raise ValueError(f"no seeds in {text!r}")
    return sorted(set(seeds))


def parse_shard(text: str | None) -> tuple[int, int] | None:
    if not text:
        return None
    i, n = (int(x) for x in text.split("/"))
    if not 1 <= i <= n:
        raise ValueError(f"bad shard {text!r}")
    return i, n


def job_key(job: tuple[str, int, str]) -> str:
    opponent, seed, color = job
    return f"{opponent}_{color}_{seed}"


def in_shard(job: tuple[str, int, str], shard: tuple[int, int] | None) -> bool:
    if shard is None:
        return True
    i, n = shard
    return int(hashlib.sha256(job_key(job).encode()).hexdigest(), 16) % n == i - 1


def plan_jobs(opponents, seeds, colors, shard=None) -> list[tuple[str, int, str]]:
    jobs = [(o, s, c) for o in opponents for c in colors for s in seeds]
    return [j for j in jobs if in_shard(j, shard)]


def pending_jobs(jobs, run_dir: Path) -> list[tuple[str, int, str]]:
    """resume 用。games/ に結果があるものを除く。"""
    done = {p.stem for p in (Path(run_dir) / "games").glob("*.json")}
    return [j for j in jobs if job_key(j) not in done]


def module_name(run_id: str) -> str:
    """run_id を Python のモジュール名に使える形にする（Agents._runs.<これ>.cand）。"""
    return "r_" + re.sub(r"\W", "_", run_id)


def resolve_sim(arg: str | None) -> Path:
    return Path(arg or os.environ.get("ATLA5_SIM_DIR") or ROOT / "workspace").resolve()


def load_pool(path: Path = POOL_JSON) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_opponents(text: str, pool: dict) -> list[str]:
    names = pool["pool"] if text == "pool" else [n.strip() for n in text.split(",") if n.strip()]
    unknown = [n for n in names if n not in pool["opponents"]]
    if unknown:
        raise SystemExit(f"unknown opponents {unknown}; see {POOL_JSON}")
    return names


def _copy_tree(src: Path, dest: Path) -> None:
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def build_candidate(args_file: str | None, dest: Path) -> None:
    out = Path(tempfile.mkdtemp(prefix="eval_pool_build_"))
    try:
        cmd = [sys.executable, str(BUILD), "--out", str(out)] + (["--args", args_file] if args_file else [])
        subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
        _copy_tree(out / "MyAgent", dest)
    finally:
        shutil.rmtree(out, ignore_errors=True)


def build_opponent(name: str, spec: dict, dest: Path, sim: Path) -> dict:
    if spec["kind"] == "sim":
        _copy_tree(sim / spec["path"], dest)
        if spec.get("config"):
            shutil.copy(ROOT / spec["config"], dest / "config.json")
    else:
        tmp = Path(tempfile.mkdtemp(prefix="eval_pool_opp_"))
        try:
            archive = subprocess.run(["git", "archive", spec["commit"], "agent"], cwd=ROOT, check=True,
                                     capture_output=True).stdout
            subprocess.run(["tar", "-x", "-C", str(tmp)], input=archive, check=True)
            dest.mkdir(parents=True)
            for f in ("__init__.py", "config.json", "args.json"):
                shutil.copy(tmp / "agent" / f, dest / f)
            _copy_tree(tmp / "agent" / "strategy", dest / "strategy")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        if spec.get("args"):
            shutil.copy(ROOT / spec["args"], dest / "args.json")
    return {"name": name, "commit": spec.get("commit"),
            "args_sha256": rs.sha256_bytes((dest / "args.json").read_bytes()), "code_sha256": rs.tree_sha256(dest)}


def play_game(sim: Path, cand: str, opp: str, seed: int, color: str, log_path: str | None) -> dict:
    """子プロセスで1試合。cwd は sim。local_test/run_eval_paired.py と同じ seed の決め方。"""
    import random

    import numpy as np

    os.chdir(sim)
    sys.path.insert(0, str(sim))
    from ASRCAISim1.core import Entity, Fighter
    from src.fight import Fight

    def info(i, p):
        args = json.loads((sim / p / "args.json").read_text(encoding="utf-8"))
        return {"userModelID": i, "userModuleID": ".".join(Path(p).parts), "args": args}

    me, op = info("0", cand), info("1", opp)
    red, blue = (me, op) if color == "Red" else (op, me)
    match = {"teams": {"Blue": blue, "Red": red}, "youth": True, "visualize": False, "replay": False,
             "time_out": 3.0, "common_dir": "common", "registered": {"Blue": False, "Red": False},
             "initial_state": "random", "make_log": bool(log_path), "seed": seed}
    np.random.seed(seed)
    random.seed(seed)
    fight = Fight(match)
    fight.make_matchInfo()
    fight.set_match()
    hits = {"Red": 0, "Blue": 0}
    env = fight.env
    step, registered = env.step, []

    def on_hit(event):
        hits[Entity.from_json(event["wpn"]).getTeam()] += 1

    def counted_step(action):
        if not registered:
            env.manager.getRuler()().manager.addEventHandler("Hit", on_hit)
            registered.append(True)
        return step(action)

    env.step = counted_step
    winner, detail = fight.run(False)
    enemy = "Blue" if color == "Red" else "Red"
    launched, escort_alive = {}, {}
    for w in env.manager.getAssets(lambda a: isinstance(a, Fighter)):
        x = w()
        launched[x.getTeam()] = launched.get(x.getTeam(), 0) + (x.numMsls - x.remMsls)
        if x.getFullName().endswith("E"):
            escort_alive[x.getTeam()] = bool(x.isAlive())
    alive = detail.get("numAlives", {})
    if log_path:
        Path(log_path).parent.mkdir(parents=True, exist_ok=True)
        Path(log_path).write_text(json.dumps(detail.get("logs", {}).get(color, {}), default=str), encoding="utf-8")
    return {"seed": seed, "color": color, "endReason": detail.get("endReason"), "step_count": detail.get("step_count"),
            "score": detail["scores"].get(color, 0.0),
            "result": "win" if winner == color else ("loss" if winner == enemy else "draw"),
            "our_alive": alive.get(color, 0.0), "enemy_alive": alive.get(enemy, 0.0),
            "our_launched": launched.get(color, 0), "our_hits": hits[color],
            "enemy_launched": launched.get(enemy, 0), "enemy_hits": hits[enemy],
            "enemy_escort_killed": not escort_alive.get(enemy, True),
            "our_escort_killed": not escort_alive.get(color, True), "error": bool(detail.get("error"))}


def _child(spec_json: str) -> int:
    spec = json.loads(spec_json)
    row = play_game(Path(spec["sim"]), spec["cand"], spec["opp"], spec["seed"], spec["color"], spec.get("log"))
    print("ROW " + json.dumps(row))
    return 0


def run_one(sim: Path, base: str, job, log_dir: Path | None) -> dict:
    opponent, seed, color = job
    spec = {"sim": str(sim), "cand": f"{base}/cand", "opp": f"{base}/opp_{opponent}", "seed": seed, "color": color,
            "log": str(log_dir / f"{job_key(job)}.json") if log_dir else None}
    t0 = time.time()
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), "_game", json.dumps(spec)], cwd=sim,
                       env=dict(os.environ, PYTHONPATH=str(sim)), capture_output=True, text=True)
    rows = [line[4:] for line in r.stdout.splitlines() if line.startswith("ROW ")]
    if r.returncode or not rows:
        raise RuntimeError(f"{job_key(job)} failed (exit {r.returncode}): {(r.stderr or r.stdout)[-600:]}")
    row = json.loads(rows[-1])
    row.update(opponent=opponent, wall_s=round(time.time() - t0, 2))
    return row


def main(argv=None) -> int:
    if argv is None and len(sys.argv) > 2 and sys.argv[1] == "_game":
        return _child(sys.argv[2])
    ap = argparse.ArgumentParser(prog="eval_pool", description=__doc__.split("\n\n")[0])
    who = ap.add_mutually_exclusive_group(required=True)
    who.add_argument("--preset", help="agent/presets/NAME.json")
    who.add_argument("--default", action="store_true", help="agent/args.json（既定ビルド）")
    who.add_argument("--args", help="任意の args.json")
    ap.add_argument("--opponents", default="pool", help="カンマ区切り、または pool（opponents/pool.json の pool）")
    ap.add_argument("--seeds", default="1-20")
    ap.add_argument("--colors", default="both", choices=sorted(COLORS))
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1, help="並列数（既定 CPU 数、上限なし）")
    ap.add_argument("--sim-dir", default=None)
    ap.add_argument("--shard", default=None, help="i/N。seed×色×相手の組をハッシュで N 分割した i 番目だけ回す")
    ap.add_argument("--resume", default=None, metavar="RUN_ID", help="running の run の残りだけ回す")
    ap.add_argument("--make-log", action="store_true", help="対戦ログを <sim>/artifacts/<run_id>/ に保存する")
    ap.add_argument("--keep", action="store_true", help="Agents/_runs/<run_id>/ を消さない")
    ap.add_argument("--runs-dir", default=str(rs.RUNS))
    ap.add_argument("--worker", default=os.environ.get("ATLA5_WORKER") or os.environ.get("USER") or "anon")
    ap.add_argument("--notes", default=None)
    ap.add_argument("--dry-run", action="store_true", help="試合の一覧だけ出して終わる")
    a = ap.parse_args(argv)
    if a.workers < 1:
        ap.error("--workers must be positive")

    pool = load_pool()
    opponents = resolve_opponents(a.opponents, pool)
    seeds, colors, shard = parse_seeds(a.seeds), COLORS[a.colors], parse_shard(a.shard)
    jobs = plan_jobs(opponents, seeds, colors, shard)
    if a.preset:
        name, args_file = a.preset, f"agent/presets/{a.preset}.json"
        if not (ROOT / args_file).exists():
            raise SystemExit(f"missing preset: {args_file}")
    elif a.args:
        path = Path(a.args)
        name, args_file = (path.parent.name if path.stem == "args" else path.stem), a.args
    else:
        name, args_file = "default", None
    if a.dry_run:
        print(f"{name}: {len(jobs)} games, workers={a.workers}")
        for job in jobs:
            print(" ", job_key(job))
        return 0

    sim = resolve_sim(a.sim_dir)
    if not (sim / "src" / "fight.py").exists():
        raise SystemExit(f"simulator not found in {sim}; pass --sim-dir or set ATLA5_SIM_DIR")
    runs_dir = Path(a.runs_dir)
    protocol = {"seeds": seeds, "colors": colors, "youth": True, "make_log": a.make_log,
                "shard": a.shard, "opponent_set": a.opponents}
    run_id = a.resume or rs.new_run_id(a.worker)
    base = f"Agents/_runs/{module_name(run_id)}"
    deploy = sim / base
    shutil.rmtree(deploy, ignore_errors=True)
    deploy.mkdir(parents=True)
    try:
        build_candidate(args_file, deploy / "cand")
        cand_args = json.loads((deploy / "cand" / "args.json").read_text(encoding="utf-8"))
        candidate = {"name": name, "specialist": cand_args.get("specialist"), "args": cand_args,
                     "args_sha256": rs.sha256_bytes((deploy / "cand" / "args.json").read_bytes()),
                     "code_sha256": rs.tree_sha256(deploy / "cand")}
        opp_meta = [build_opponent(o, pool["opponents"][o], deploy / f"opp_{o}", sim) for o in opponents]
        if a.resume:
            run_dir = runs_dir / run_id
            manifest = rs.read_manifest(run_dir)
            if manifest["status"] != "running":
                raise SystemExit(f"run {run_id} is {manifest['status']}, not running")
            if manifest["candidate"]["code_sha256"] != candidate["code_sha256"]:
                raise SystemExit(f"run {run_id} was made from different candidate code; refusing to resume")
            jobs = plan_jobs([o["name"] for o in manifest["opponents"]], manifest["protocol"]["seeds"],
                             manifest["protocol"]["colors"], parse_shard(manifest["protocol"].get("shard")))
        else:
            run_dir = rs.start_run(a.worker, candidate, opp_meta, protocol, runs_dir=runs_dir, run_id=run_id,
                                   notes=a.notes)
        todo = pending_jobs(jobs, run_dir)
        log_dir = sim / "artifacts" / run_id if a.make_log else None
        print(f"run {run_id}: {len(jobs) - len(todo)}/{len(jobs)} done, {len(todo)} to play, workers={a.workers}",
              flush=True)
        failures = []
        with ThreadPoolExecutor(max_workers=a.workers) as ex:
            futures = {ex.submit(run_one, sim, base, job, log_dir): job for job in todo}
            for fut in as_completed(futures):
                try:
                    rs.write_game(run_dir, fut.result())
                except Exception as e:  # noqa: BLE001
                    failures.append(str(e))
                    print(f"error: {e}", file=sys.stderr, flush=True)
        done = len(jobs) - len(pending_jobs(jobs, run_dir))
        if done == len(jobs):
            rs.finish_run(run_dir)
        print(f"{run_id} {done}/{len(jobs)} games{'' if done == len(jobs) else ' (running; rerun with --resume)'}")
        return 0 if not failures and done == len(jobs) else 1
    finally:
        if not a.keep:
            shutil.rmtree(deploy, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
