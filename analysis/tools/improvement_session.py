"""改善セッション支援ツール（kaggriculture の improvement_session.py を本コンペ用に移植）.

改善サイクルを強制・記録する。前提:
    - 対戦は Docker コンテナ (atla5-cpu) 内の validate.py で実行する
    - 記録は analysis/agents/<specialist>/improvement.md に追記する

Usage:
    python analysis/tools/improvement_session.py start --specialist default
    python analysis/tools/improvement_session.py assumption "MWS は 10km 程度までしか効かない" --specialist default
    python analysis/tools/improvement_session.py hypothesis "射距離を 35km にすると命中率が上がる" --specialist default
    python analysis/tools/improvement_session.py verify --specialist default
    python analysis/tools/improvement_session.py validate --specialist default --games 3
    python analysis/tools/improvement_session.py record --specialist default \
        --direction "..." --changes "..." --verification "..." --next-steps "..."
    python analysis/tools/improvement_session.py check --specialist default
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "analysis" / "agents"
FORMAT_MD = REPO_ROOT / "tools" / "battle_analyzer" / "BATTLELOG_FORMAT.md"
ACTIVE_PY = REPO_ROOT / "agent" / "strategy" / "active.py"
SPECIALISTS_DIR = REPO_ROOT / "agent" / "strategy" / "specialists"
ARGS_PATH = REPO_ROOT / "agent" / "args.json"
RESULT_DIR = "results_improve"


def state_path(name: str) -> Path:
    return AGENTS_DIR / name / "session_state.json"


def note_path(name: str) -> Path:
    return AGENTS_DIR / name / "improvement.md"


def load_state(name: str) -> dict:
    path = state_path(name)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(name: str, state: dict) -> None:
    path = state_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def require_specialist(name: str) -> None:
    if not (SPECIALISTS_DIR / f"{name}.py").exists():
        raise SystemExit(f"specialist が存在しません: {name}")


def run_games(games: int) -> dict:
    cmd = [
        "docker", "exec", "atla5-cpu", "bash", "-lc",
        f"cd /workspace && python validate.py --youth 1 --num-validation {games} "
        f"--result-dir /workspace/{RESULT_DIR} --visualize 0",
    ]
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
    path = REPO_ROOT / "workspace" / RESULT_DIR / "0" / "validation_results.json"
    if not path.exists():
        raise SystemExit(f"結果が見つかりません: {path}")
    return json.loads(path.read_text())


def summarize(label: str, data: dict) -> dict:
    own = data["own"]
    enemy = "Blue" if own == "Red" else "Red"
    n = max(1, len(data["details"]))
    score = 0.0
    our_alive = 0.0
    enemy_alive = 0.0
    print(f"--- {label} ---")
    for k, v in sorted(data["details"].items()):
        s = v["scores"][own]
        score += s
        our_alive += v["numAlives"][own]
        enemy_alive += v["numAlives"][enemy]
        print(
            f"  fight {k}: {v['endReason']:<12} steps={v['step_count']:<5} "
            f"alive {own}={v['numAlives'][own]:.0f} {enemy}={v['numAlives'][enemy]:.0f} score={s:.3f}"
        )
    metrics = {
        "avg_score": round(score / n, 3),
        "avg_our_alive": round(our_alive / n, 2),
        "avg_enemy_alive": round(enemy_alive / n, 2),
        "games": len(data["details"]),
    }
    print(f"  {metrics}")
    return metrics


def cmd_start(args) -> None:
    require_specialist(args.specialist)
    if load_state(args.specialist):
        print(f"セッションは既に開始済み: {state_path(args.specialist)}")
    else:
        save_state(args.specialist, {
            "specialist": args.specialist,
            "started": datetime.now().isoformat(timespec="seconds"),
            "assumptions": [],
            "hypotheses": [],
            "cycles": [],
        })
    print("チェックリスト:")
    print(f"  1. {FORMAT_MD.relative_to(REPO_ROOT).as_posix()} を読んだか（ログ構造の再発見を避ける）")
    print(f"  2. 現在の active specialist を確認したか（{ARGS_PATH.relative_to(REPO_ROOT).as_posix()}）")
    print("  3. 直近の計測で敗因（生存数・スコア）を特定したか")
    print("  4. 変更は1変数か、予測を hypothesis で記録したか")


def cmd_assumption(args) -> None:
    state = load_state(args.specialist)
    state.setdefault("assumptions", []).append({
        "text": args.text,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(args.specialist, state)
    print(f"前提を記録: {args.text}")


def cmd_hypothesis(args) -> None:
    state = load_state(args.specialist)
    state.setdefault("hypotheses", []).append({
        "text": args.text,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(args.specialist, state)
    print(f"仮説（予測）を記録: {args.text}")
    print("変更前に数値で予測を書くこと。書けない場合は変更しない。")


def cmd_verify(args) -> None:
    metrics = summarize("1ゲーム検証", run_games(args.games))
    state = load_state(args.specialist)
    state.setdefault("cycles", []).append({"kind": "verify", "metrics": metrics})
    save_state(args.specialist, state)
    print("意図した挙動（接近・射撃・回避）が起きているかログで確認すること:")
    print(f"  python tools/battle_analyzer/battle_stats.py workspace/{RESULT_DIR}/0/log_0.json")


def cmd_validate(args) -> None:
    metrics = summarize("バッチ検証", run_games(args.games))
    state = load_state(args.specialist)
    state.setdefault("cycles", []).append({"kind": "validate", "metrics": metrics})
    save_state(args.specialist, state)
    print("勝率ではなく挙動指標（avg_our_alive / avg_enemy_alive / avg_score）で判定すること。")


def cmd_record(args) -> None:
    path = note_path(args.specialist)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = load_state(args.specialist)
    latest = state.get("cycles", [])[-1]["metrics"] if state.get("cycles") else {}
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"- 方向性: {args.direction}\n")
        f.write(f"- 変更: {args.changes}\n")
        f.write(f"- 検証: {args.verification}\n")
        if latest:
            f.write(f"- 指標: {json.dumps(latest, ensure_ascii=False)}\n")
        if args.next_steps:
            f.write(f"- 次の一手: {args.next_steps}\n")
    print(f"記録しました: {path}")


def cmd_check(args) -> None:
    state = load_state(args.specialist)
    if not state:
        print(f"セッション未開始: {args.specialist}")
        return
    print(f"specialist: {state.get('specialist')} / started: {state.get('started')}")
    print(f"  前提: {len(state.get('assumptions', []))} 件")
    print(f"  仮説: {len(state.get('hypotheses', []))} 件")
    print(f"  検証: {len(state.get('cycles', []))} 回")
    path = note_path(args.specialist)
    print(f"  improvement.md: {'あり' if path.exists() else 'なし'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="改善セッション支援")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("assumption")
    p.add_argument("text")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_assumption)

    p = sub.add_parser("hypothesis")
    p.add_argument("text")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_hypothesis)

    p = sub.add_parser("verify")
    p.add_argument("--games", type=int, default=1)
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("validate")
    p.add_argument("--games", type=int, default=3)
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("record")
    p.add_argument("--specialist", required=True)
    p.add_argument("--direction", default="")
    p.add_argument("--changes", default="")
    p.add_argument("--verification", default="")
    p.add_argument("--next-steps", dest="next_steps", default="")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("check")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    args.func(args)


if __name__ == "__main__":
    main()
