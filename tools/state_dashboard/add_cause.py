#!/usr/bin/env python3
"""仮説ビルダーの『原因』候補を追加・更新・削除する CLI.

ダッシュボードは読み取り専用なので、原因候補の追加はこのコマンドで行う。
定義の保存先は tools/state_dashboard/cause_bank.json のみ。

    python tools/state_dashboard/add_cause.py --list
    python tools/state_dashboard/add_cause.py --label "回避方位が固定" \
        --phrase "回避方位が被弾警報+180度で固定されているため、反転包囲を避けられない" \
        --group measured --source code
    python tools/state_dashboard/add_cause.py --id fire_ord_blocked --note "ログで裏が取れた"
    python tools/state_dashboard/add_cause.py --remove fire_ord_blocked

--group は dropdown のグループ:
    measured    この事実から出せそうな原因（実測から機械的に出たものと同じ枠）
    constraint  構造の制約（変えると壊れる。変更対象にしない）
    history     前回の検証で出た原因

同じ --label は上書きするので、一度決めた表現はそのまま使い回せる。
"""

import argparse
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

STORE = Path(__file__).resolve().parent / "cause_bank.json"

GROUPS = ("measured", "constraint", "history")
SOURCES = ("log", "analysis", "code", "official")


def load_store() -> dict:
    if not STORE.exists():
        return {"version": 1, "causes": []}
    data = json.loads(STORE.read_text(encoding="utf-8"))
    data.setdefault("causes", [])
    return data


def save_store(data: dict) -> None:
    STORE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def find(data: dict, key: str) -> int:
    for i, c in enumerate(data["causes"]):
        if c.get("id") == key or c.get("label") == key:
            return i
    return -1


def slugify(label: str) -> str:
    out = []
    for ch in label.lower():
        if ch.isascii() and (ch.isalnum() or ch == "_"):
            out.append(ch)
        elif " " in "".join(out) or not out:
            out.append("_")
    slug = "".join(out).strip("_")
    return slug or "cause"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="原因候補の定義を追加・更新する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument("--id", help="原因 ID（省略時は label から自動生成）")
    ap.add_argument("--label", help="dropdown に表示する短い名前")
    ap.add_argument("--phrase", help="仮説の文にそのまま入る一文")
    ap.add_argument("--group", choices=GROUPS, help="dropdown のグループ")
    ap.add_argument("--source", choices=SOURCES, help="improvement_session.py --source に渡す値")
    ap.add_argument("--note", default=None, help="補足（何を変えると切り分けられるか）")
    ap.add_argument("--remove", help="指定した ID / label を削除する")
    ap.add_argument("--list", action="store_true", help="定義の一覧を表示する")
    args = ap.parse_args()

    data = load_store()

    if args.list or not any([args.id, args.label, args.remove, args.phrase]):
        if not data["causes"]:
            print("（未定義）--label と --phrase を渡すと追加できる")
            return 0
        for c in data["causes"]:
            print(
                f"{c['id']:24} {c.get('group', '-'):11} {c.get('label', '')}"
            )
        return 0

    if args.remove:
        idx = find(data, args.remove)
        if idx < 0:
            print(f"not found: {args.remove}", file=sys.stderr)
            return 1
        removed = data["causes"].pop(idx)
        save_store(data)
        print(f"removed: {removed['id']}")
        return 0

    cid = args.id or slugify(args.label or "")
    idx = find(data, cid)
    if idx < 0 and not args.label:
        print("--label が必要（新規追加のときは ID も省略できる）", file=sys.stderr)
        return 1

    entry = dict(data["causes"][idx]) if idx >= 0 else {"id": cid}
    if args.label:
        entry["label"] = args.label
    entry.setdefault("label", cid)
    if args.phrase:
        entry["phrase"] = args.phrase
    if args.group:
        entry["group"] = args.group
    if args.source:
        entry["source"] = args.source
    if args.note is not None:
        entry["note"] = args.note
    entry.setdefault("phrase", entry["label"])
    entry.setdefault("group", "measured")
    entry.setdefault("source", "log")
    entry.setdefault("note", "")

    if idx < 0:
        data["causes"].append(entry)
        action = "added"
    else:
        data["causes"][idx] = entry
        action = "updated"
    save_store(data)
    print(f"{action}: {entry['id']} -> {STORE}")
    print("反映: python tools/state_dashboard/cache_bump.py のあとブラウザ F5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
