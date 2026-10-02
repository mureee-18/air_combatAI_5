import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKSPACE = ROOT / "workspace"
ARGS_PATH = WORKSPACE / "Agents" / "MyAgent" / "args.json"


def run_fights(num, result_dir):
    cmd = [
        "docker", "exec", "atla5-cpu", "bash", "-lc",
        f"cd /workspace && python validate.py --youth 1 --num-validation {num} "
        f"--result-dir /workspace/{result_dir} --visualize 0",
    ]
    subprocess.run(cmd, cwd=str(ROOT), check=False)
    path = WORKSPACE / result_dir / "0" / "validation_results.json"
    return json.loads(path.read_text())


def summarize(tag, data):
    own = data["own"]
    enemy_key = "Blue" if own == "Red" else "Red"
    total_score = 0.0
    our_alive = 0
    enemy_alive = 0
    print(f"=== {tag} ===")
    for k, v in data["details"].items():
        score = v["scores"][own]
        total_score += score
        our_alive += v["numAlives"][own]
        enemy_alive += v["numAlives"][enemy_key]
        print(
            f"  fight {k}: {v['endReason']:<12} steps={v['step_count']:<5} "
            f"alive {own}={v['numAlives'][own]:.0f} {enemy_key}={v['numAlives'][enemy_key]:.0f} "
            f"score={score:.3f}"
        )
    n = max(1, len(data["details"]))
    print(
        f"  avg_score={total_score / n:.3f} avg_our_alive={our_alive / n:.2f} "
        f"avg_enemy_alive={enemy_alive / n:.2f}"
    )
    return total_score / n


def main():
    parser = argparse.ArgumentParser(prog="run_eval")
    parser.add_argument("--games", type=int, default=3)
    parser.add_argument("--sweep", default="", help="key=value1,value2,... 形式。args.json を書き換えて走査")
    args = parser.parse_args()

    original = json.loads(ARGS_PATH.read_text())

    if not args.sweep:
        data = run_fights(args.games, "results_eval")
        summarize("current", data)
        return

    key, values = args.sweep.split("=", 1)
    results = {}
    for value in values.split(","):
        patched = dict(original)
        patched[key] = float(value) if value.replace(".", "").isdigit() else value
        ARGS_PATH.write_text(json.dumps(patched, ensure_ascii=False, indent=2))
        tag = f"{key}={value}"
        data = run_fights(args.games, "results_eval")
        results[tag] = summarize(tag, data)

    ARGS_PATH.write_text(json.dumps(original, ensure_ascii=False, indent=2))
    print("--- ranking ---")
    for tag, score in sorted(results.items(), key=lambda kv: -kv[1]):
        print(f"  {score:.3f}  {tag}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
