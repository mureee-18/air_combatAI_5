"""改善セッション支援ツール（kaggriculture の improvement_session.py を本コンペ用に移植）.

改善サイクルを強制・記録する。前提:
    - 対戦は Docker コンテナ (atla5-cpu) 内の validate.py で実行する
    - 記録は analysis/agents/<specialist>/improvement.md に追記する

記録は「事実（出所あり）」と「推論（仮説）」を型で分離する（kaggriculture の
records.py と同じ考え方）:
    kind    rule       大会ルール / 採点式に由来する制約（出所は official のみ）
            observation 実測ログ・計測値に基づく事実
            inference   仮説・因果推論・予測
    source  official 公式ルール / fight.py 等の実装
            code     自作コードの読み取り
            log      対戦ログ / 計測値
            analysis 解析結果・ダッシュボード

Usage:
    python analysis/tools/improvement_session.py start --specialist default
    python analysis/tools/improvement_session.py assumption "MWS は 10km 程度までしか効かない" --specialist default
    python analysis/tools/improvement_session.py hypothesis "射距離を 35km にすると命中率が上がる" \
        --specialist default --source log
    python analysis/tools/improvement_session.py verify --specialist default
    python analysis/tools/improvement_session.py validate --specialist default --games 3
    python analysis/tools/improvement_session.py record --specialist default \
        --kind observation --source log \
        --direction "..." --changes "..." --verification "..." --next-steps "..."
    python analysis/tools/improvement_session.py check --specialist default
"""

from __future__ import annotations

import argparse
import json
import re
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

RECORD_KINDS = ("rule", "observation", "inference")
RECORD_SOURCES = ("official", "code", "log", "analysis")
KIND_PREFIX = {"rule": "R", "observation": "O", "inference": "N"}
KIND_LABEL = {
    "rule": "大会ルール由来の制約",
    "observation": "実測に基づく事実",
    "inference": "仮説・推論",
}
SOURCE_LABEL = {
    "official": "公式ルール / シミュレータ実装",
    "code": "自作コードの読み取り",
    "log": "対戦ログ / 計測値",
    "analysis": "解析結果・ダッシュボード",
}
# 種別ごとの許容出所。rule は公式に限る（推測でルールを作らない）。
KIND_ALLOWED_SOURCES = {
    "rule": ("official",),
    "observation": ("log", "analysis", "code"),
    "inference": ("log", "analysis", "code", "official"),
}


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


def validate_record(kind: str, source: str) -> None:
    """種別と出所の整合を検査する。不正なら SystemExit（ Clap 風の選択肢_help と対）."""

    if kind not in RECORD_KINDS:
        raise SystemExit(f"種別が不正です: {kind}（{'/'.join(RECORD_KINDS)}）")
    if source not in RECORD_SOURCES:
        raise SystemExit(f"出所が不正です: {source}（{'/'.join(RECORD_SOURCES)}）")
    allowed = KIND_ALLOWED_SOURCES[kind]
    if source not in allowed:
        raise SystemExit(
            f"種別の型制約違反: kind={kind} は source={'/'.join(allowed)} のみ。"
            f"（{KIND_LABEL[kind]} に {SOURCE_LABEL[source]} は使えない）"
        )


def normalize_text(text: str) -> str:
    """入力の貼り付けミスを正規化する。

    全体が「A A」と同じ文の2回繰り返しになっていれば A に畳む
    （コマンド例からのコピーで二重に貼り付いたケースの防止）。
    """

    text = text.strip()
    match = re.match(r"^(.+?)\s+\1[.。]?$", text, flags=re.DOTALL)
    if match:
        text = match.group(1).strip()
    return text


def next_record_id(path: Path, kind: str) -> str:
    """improvement.md に既にある同種別の記録数から次の ID を返す（O-001 / N-002 形式）."""

    prefix = KIND_PREFIX[kind]
    used = 0
    if path.exists():
        text = path.read_text(encoding="utf-8")
        used = text.count(f"\n## {prefix}-") + (1 if text.startswith(f"## {prefix}-") else 0)
    return f"{prefix}-{used + 1:03d}"


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


def summarize_paired(path: Path) -> dict:
    """seed 固定ペア評価（local_test/run_eval_paired.py の出力）を判定指標として読む.

    判定基準はペア評価（CLAUDE.md）。validate.py を直接叩くとシナリオが毎回変わるため、
    記録は `--paired` で行う。
    """

    if not path.exists():
        raise SystemExit(f"ペア評価ファイルが見つかりません: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics = data.get("metrics") or {}
    if metrics.get("avg_score") is None:
        raise SystemExit(f"metrics.avg_score がありません（別ファイルの可能性）: {path}")
    print(f"--- ペア評価（seed 固定）: {metrics.get('label') or path.name} ---")
    for row in data.get("rows", []):
        print(
            f"  {str(row.get('color', '')):<5} seed={str(row.get('seed', '')):<4} "
            f"{str(row.get('result', '')):<5} {str(row.get('endReason', '')):<12} "
            f"steps={str(row.get('step_count', '')):<6} "
            f"alive {row.get('our_alive')} / {row.get('enemy_alive')} score={row.get('score')}"
        )
    picked = {
        "avg_score": metrics.get("avg_score"),
        "avg_our_alive": metrics.get("avg_our_alive"),
        "avg_enemy_alive": metrics.get("avg_enemy_alive"),
        "games": metrics.get("games"),
    }
    print(f"  {picked}")
    return picked


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
    text = normalize_text(args.text)
    assumptions = state.setdefault("assumptions", [])
    if assumptions and assumptions[-1]["text"] == text:
        print(f"前提は既に記録済み（重複スキップ）: {text}")
        return
    assumptions.append({
        "text": text,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(args.specialist, state)
    print(f"前提を記録: {text}")


def cmd_hypothesis(args) -> None:
    validate_record("inference", args.source)
    state = load_state(args.specialist)
    text = normalize_text(args.text)
    state.setdefault("hypotheses", []).append({
        "id": next_record_id(note_path(args.specialist), "inference"),
        "kind": "inference",
        "source": args.source,
        "text": text,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(args.specialist, state)
    print(f"仮説（推論）を記録: {text}")
    print(f"  出所: {args.source}（{SOURCE_LABEL[args.source]}）")
    print("変更前に数値で予測を書くこと。書けない場合は変更しない。")


def cmd_verify(args) -> None:
    metrics = summarize("1ゲーム検証", run_games(args.games))
    state = load_state(args.specialist)
    state.setdefault("cycles", []).append(
        {"kind": "verify", "metrics": metrics, "at": datetime.now().isoformat(timespec="seconds")}
    )
    save_state(args.specialist, state)
    stats_log = f"workspace/{RESULT_DIR}/0/log_0.json"
    print("意図した挙動（接近・射撃・回避）が起きているかログで確認すること:")
    print(f"  python tools/battle_analyzer/battle_stats.py {stats_log}")
    print(f"  python tools/battle_analyzer/trajectory.py {stats_log}")


def cmd_validate(args) -> None:
    if args.paired:
        path = Path(args.paired)
        if not path.is_absolute():
            path = REPO_ROOT / path
        metrics = summarize_paired(path)
        paired = True
    else:
        metrics = summarize("バッチ検証", run_games(args.games))
        paired = False
    state = load_state(args.specialist)
    state.setdefault("cycles", []).append(
        {
            "kind": "validate",
            "metrics": metrics,
            "paired": paired,
            "at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_state(args.specialist, state)
    print("勝率ではなく挙動指標（avg_our_alive / avg_enemy_alive / avg_score）で判定すること。")
    if not paired:
        print("※ 判定基準は seed 固定ペア評価。--paired workspace/paired/<label>.json を推奨。")


def cmd_record(args) -> None:
    validate_record(args.kind, args.source)
    path = note_path(args.specialist)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = load_state(args.specialist)
    latest = state.get("cycles", [])[-1]["metrics"] if state.get("cycles") else {}
    record_id = next_record_id(path, args.kind)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {record_id} [{args.kind}/{args.source}] {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"- 種別: {args.kind}（{KIND_LABEL[args.kind]}）\n")
        f.write(f"- 出所: {args.source}（{SOURCE_LABEL[args.source]}）\n")
        f.write(f"- 方向性: {args.direction}\n")
        f.write(f"- 変更: {args.changes}\n")
        f.write(f"- 検証: {args.verification}\n")
        if latest:
            f.write(f"- 指標: {json.dumps(latest, ensure_ascii=False)}\n")
        if args.next_steps:
            f.write(f"- 次の一手: {args.next_steps}\n")
    state.setdefault("records", []).append({
        "id": record_id,
        "kind": args.kind,
        "source": args.source,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(args.specialist, state)
    print(f"記録しました: {path}")
    print(f"  {record_id} [{args.kind}/{args.source}]")


def cmd_check(args) -> None:
    state = load_state(args.specialist)
    if not state:
        print(f"セッション未開始: {args.specialist}")
        return
    print(f"specialist: {state.get('specialist')} / started: {state.get('started')}")
    print(f"  前提: {len(state.get('assumptions', []))} 件")
    hypotheses = state.get("hypotheses", [])
    print(f"  仮説（推論）: {len(hypotheses)} 件")
    records = state.get("records", [])
    by_kind: dict[str, int] = {}
    for item in records:
        by_kind[item["kind"]] = by_kind.get(item["kind"], 0) + 1
    detail = " / ".join(f"{kind}={by_kind.get(kind, 0)}" for kind in RECORD_KINDS)
    print(f"  記録: {len(records)} 件（{detail}）")
    unsourced = [item["id"] for item in hypotheses if not item.get("source")]
    if unsourced:
        print(f"  出所未記録の仮説: {', '.join(unsourced)}")
    path = note_path(args.specialist)
    print(f"  improvement.md: {'あり' if path.exists() else 'なし'}")


def main() -> None:
    # Windows 標準出力(cp932)でもヘルプ出力が失敗しないよう、argparse より前に切り替える
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
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
    p.add_argument(
        "--source",
        required=True,
        choices=RECORD_SOURCES,
        help="仮説の根拠出处（log=対戦ログ/計測値, analysis=解析, code=コード, official=ルール）",
    )
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_hypothesis)

    p = sub.add_parser("verify")
    p.add_argument("--games", type=int, default=1)
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("validate")
    p.add_argument("--games", type=int, default=3)
    p.add_argument(
        "--paired",
        default="",
        help="判定基準となる seed 固定ペア評価の JSON（workspace/paired/<label>.json）。"
        "指定すると対戦を再開せず、その指標を validate サイクルとして記録する",
    )
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("record")
    p.add_argument("--specialist", required=True)
    p.add_argument(
        "--kind",
        required=True,
        choices=RECORD_KINDS,
        help="rule=大会ルール由来の制約 / observation=実測事実 / inference=推論",
    )
    p.add_argument(
        "--source",
        required=True,
        choices=RECORD_SOURCES,
        help="根拠の出所。kind=rule は official のみ許可",
    )
    p.add_argument("--direction", default="")
    p.add_argument("--changes", default="")
    p.add_argument("--verification", default="")
    p.add_argument("--next-steps", dest="next_steps", default="")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("check")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
