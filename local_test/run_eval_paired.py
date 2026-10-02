"""seed 固定のペア評価ハーネス（kaggriculture の local_test/run_battle.py + paired_eval.py 相当）.

配布の validate.py は seed を指定できないが、src/fight.py の Fight は
match_config["seed"] を読むため、同一 seed 群で A/B を比較できる。
side bias を消すため --colors both（Red と Blue の両面で対戦）を基本とする。

コンテナ内で実行する:
    docker exec atla5-cpu bash -lc "cd /workspace && python /repo/local_test/run_eval_paired.py \
        --myagent-module-path Agents/MyAgent --seeds 1,2,3 --colors both \
        --out /workspace/paired/default.json"
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/workspace")

from src.fight import Fight  # noqa: E402


def agent_info(agent_id: str, module_path: str) -> dict:
    with open(os.path.join(module_path, "args.json")) as f:
        args = json.load(f)
    return {
        "userModelID": agent_id,
        "userModuleID": ".".join(module_path.split(os.sep)),
        "args": args,
    }


def make_match_info(red: dict, blue: dict, seed: int, youth: bool) -> dict:
    return {
        "teams": {"Blue": blue, "Red": red},
        "youth": youth,
        "visualize": False,
        "replay": False,
        "time_out": 3.0,
        "common_dir": "common",
        "registered": {"Blue": False, "Red": False},
        "initial_state": "random",
        "make_log": False,
        "seed": seed,
    }


def run_fight(my_path: str, opp_path: str, seed: int, youth: bool, color: str) -> dict:
    my_info = agent_info("0", my_path)
    opp_info = agent_info("1", opp_path)
    if color == "Red":
        match_config = make_match_info(my_info, opp_info, seed, youth)
    else:
        match_config = make_match_info(opp_info, my_info, seed, youth)

    np.random.seed(seed)
    random.seed(seed)

    fight = Fight(match_config)
    fight.make_matchInfo()
    fight.set_match()
    winner, detail = fight.run(False)

    scores = detail.get("scores", {})
    alives = detail.get("numAlives", {})
    enemy = "Blue" if color == "Red" else "Red"
    return {
        "seed": seed,
        "color": color,
        "endReason": detail.get("endReason", ""),
        "step_count": detail.get("step_count", 0),
        "score": scores.get(color, 0.0),
        "our_alive": alives.get(color, 0.0),
        "enemy_alive": alives.get(enemy, 0.0),
        "result": "win" if winner == color else ("loss" if winner == enemy else "draw"),
        "error": bool(detail.get("error", False)),
    }


def summarize(label: str, rows: list[dict]) -> dict:
    n = max(1, len(rows))
    wins = sum(1 for r in rows if r["result"] == "win")
    draws = sum(1 for r in rows if r["result"] == "draw")
    metrics = {
        "label": label,
        "games": len(rows),
        "win": wins,
        "draw": draws,
        "loss": len(rows) - wins - draws,
        "avg_score": round(sum(r["score"] for r in rows) / n, 3),
        "avg_our_alive": round(sum(r["our_alive"] for r in rows) / n, 2),
        "avg_enemy_alive": round(sum(r["enemy_alive"] for r in rows) / n, 2),
    }
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="seed 固定ペア評価")
    parser.add_argument("--myagent-module-path", default="Agents/MyAgent")
    parser.add_argument("--opponent-module-path", default="Agents/BenchMark")
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("--colors", default="both", choices=["red", "blue", "both"])
    parser.add_argument("--youth", type=int, default=1)
    parser.add_argument("--label", default="current")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    seeds = [int(s) for s in args.seeds.split(",") if s.strip()]
    colors = ["Red", "Blue"] if args.colors == "both" else [args.colors.capitalize()]

    rows = []
    for color in colors:
        for seed in seeds:
            row = run_fight(args.myagent_module_path, args.opponent_module_path, seed, bool(args.youth), color)
            rows.append(row)
            print(
                f"  color={color} seed={seed}: {row['result']:<4} {row['endReason']:<12} "
                f"steps={row['step_count']:<5} alive our={row['our_alive']:.0f} enemy={row['enemy_alive']:.0f} "
                f"score={row['score']:.3f}"
            )

    metrics = summarize(args.label, rows)
    print("=== summary ===")
    print(json.dumps(metrics, ensure_ascii=False))

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"metrics": metrics, "rows": rows}, ensure_ascii=False, indent=2))
        print(f"saved: {out_path}")


if __name__ == "__main__":
    main()
