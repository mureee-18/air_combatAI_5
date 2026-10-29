import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run(cmd, cwd=None):
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd or ROOT, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--specialist", default="default")
    ap.add_argument("--label", default="hyp")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    args = ap.parse_args()

    if args.set:
        args_path = ROOT / "agent" / "args.json"
        current = json.loads(args_path.read_text(encoding="utf-8"))
        for item in args.set:
            key, value = item.split("=", 1)
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            current[key] = value
        args_path.write_text(json.dumps(current, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
        print("applied:", ", ".join(args.set))

    print("== baseline check ==")
    run([sys.executable, "analysis/tools/baseline_check.py", "--check", "--strict"])

    print("== build & deploy ==")
    run([sys.executable, "scripts/build_submission.py", "--deploy"])

    print("== 1-game gate ==")
    run(["docker", "exec", "atla5-cpu", "bash", "-lc",
         "cd /workspace && python validate.py --youth 1 --num-validation 1 --visualize 0"])

    print("== paired eval (seeds {}) ==".format(args.seeds))
    run(["docker", "exec", "atla5-cpu", "bash", "-lc",
         "cd /workspace && python /repo/local_test/run_eval_paired.py "
         f"--seeds {args.seeds} --colors both --label {args.label} "
         f"--out /workspace/paired/{args.label}.json"])

    if args.holdout:
        ho_label = f"{args.label}_ho"
        print("== paired eval (holdout seeds 4,5,6) ==")
        run(["docker", "exec", "atla5-cpu", "bash", "-lc",
             "cd /workspace && python /repo/local_test/run_eval_paired.py "
             f"--seeds 4,5,6 --colors both --label {ho_label} "
             f"--out /workspace/paired/{ho_label}.json"])

    print("done: baseline check -> build -> 1-game gate -> paired eval")


if __name__ == "__main__":
    raise SystemExit(main())
