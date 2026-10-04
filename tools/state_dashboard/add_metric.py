#!/usr/bin/env python3
"""評価タブの『独自指標』を追加・更新・削除する CLI.

ダッシュボードは読み取り専用なので、指標の定義はこのコマンドで作る。
定義の保存先は tools/state_dashboard/custom_metrics.json のみ。

    python tools/state_dashboard/add_metric.py --list
    python tools/state_dashboard/add_metric.py --label "初発までの空白" \
        --from trajectory --direction lower --target 60 --unit 秒 --source log
    python tools/state_dashboard/add_metric.py --id fire_orders --target 80
    python tools/state_dashboard/add_metric.py --remove first_launch_lag

--from は数値を取る場所（どのタブの値か）:
    paired      ペア評価（workspace/paired/<label>.json）: avg_score / avg_our_alive /
                avg_enemy_alive / win / draw / loss / games
    trajectory  軌跡（tools/battle_analyzer/trajectory.py）: first_detect /
                first_launch / first_launch_lag / launch_count / min_dist_km /
                bearing_spread / lost_range_km / aircraft / shots
    logstats    挙動指標（tools/battle_analyzer/battle_stats.py）: fire_orders /
                detections / alerts / min_dist_km / shots 等
"""

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

STORE = Path(__file__).resolve().parent / "custom_metrics.json"

SOURCES = {"paired", "trajectory", "logstats"}
SOURCES_HINT = "既定: log。ログ由来は log、復元式の検証値は analysis、規則は official、制約は code"
DIRECTIONS = {"higher", "lower"}


def slugify(label: str) -> str:
    out = []
    for ch in label.lower():
        if ch.isascii() and (ch.isalnum() or ch == "_"):
            out.append(ch)
        elif " " in "".join(out) or not out:
            out.append("_")
    slug = "".join(out).strip("_")
    return slug or "metric"


def load_store() -> dict:
    if not STORE.exists():
        return {"version": 1, "metrics": []}
    data = json.loads(STORE.read_text(encoding="utf-8"))
    data.setdefault("metrics", [])
    return data


def save_store(data: dict) -> None:
    STORE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def find(data: dict, mid: str) -> int:
    for i, m in enumerate(data["metrics"]):
        if m.get("id") == mid:
            return i
    return -1


def main() -> int:
    ap = argparse.ArgumentParser(
        description="独自指標の定義を追加・更新する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--id", help="指標 ID（省略時は label から自動生成）")
    ap.add_argument("--label", help="表示名")
    ap.add_argument("--unit", default="", help="単位（秒 / km / 発 など）")
    ap.add_argument(
        "--from",
        dest="origin",
        choices=sorted(SOURCES),
        help="数値の出所（paired / trajectory / logstats）",
    )
    ap.add_argument(
        "--source",
        choices=["log", "analysis", "code", "official"],
        help="improvement_session.py --source に渡す値",
    )
    ap.add_argument("--direction", choices=sorted(DIRECTIONS), help="目標が高いほど良いか")
    ap.add_argument("--target", type=float, help="目標値（付けない場合は参考値）")
    ap.add_argument("--note", default="", help="この指標の意味・見る理由")
    ap.add_argument("--digits", type=int, help="表示桁数")
    ap.add_argument("--remove", help="指定した ID を削除する")
    ap.add_argument("--list", action="store_true", help="定義の一覧を表示する")
    args = ap.parse_args()

    data = load_store()

    if args.list or not any(
        [args.id, args.label, args.remove, args.target is not None, args.note]
    ):
        if not data["metrics"]:
            print("（未定義）--label と --from を渡すと追加できる")
            return 0
        for m in data["metrics"]:
            tgt = m.get("target")
            tgt = "-" if tgt is None else f"{tgt}"
            print(
                f"{m['id']:20} {m.get('label', ''):16} from={m.get('from', '-'):10} "
                f"dir={m.get('direction', '-'):6} target={tgt} {m.get('unit', '')}"
            )
        return 0

    if args.remove:
        idx = find(data, args.remove)
        if idx < 0:
            print(f"not found: {args.remove}", file=sys.stderr)
            return 1
        removed = data["metrics"].pop(idx)
        save_store(data)
        print(f"removed: {removed['id']}")
        return 0

    mid = args.id or slugify(args.label or "")
    idx = find(data, mid)
    if idx < 0 and not args.label:
        print("--label が必要（新規追加のときは ID も省略できる）", file=sys.stderr)
        return 1

    entry = dict(data["metrics"][idx]) if idx >= 0 else {"id": mid}
    if args.label:
        entry["label"] = args.label
    entry.setdefault("label", mid)
    if args.origin:
        entry["from"] = args.origin
    if args.source:
        entry["source"] = args.source
    if args.direction:
        entry["direction"] = args.direction
    if args.target is not None:
        entry["target"] = args.target
    if args.digits is not None:
        entry["digits"] = args.digits
    if args.note:
        entry["note"] = args.note
    if args.unit:
        entry["unit"] = args.unit
    entry.setdefault("from", "paired")
    entry.setdefault("source", "log")
    entry.setdefault("direction", "higher")
    entry.setdefault("note", "")

    if idx < 0:
        data["metrics"].append(entry)
        action = "added"
    else:
        data["metrics"][idx] = entry
        action = "updated"
    save_store(data)
    print(f"{action}: {entry['id']} -> {STORE}")
    print("反映: python tools/state_dashboard/cache_bump.py のあとブラウザ F5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())