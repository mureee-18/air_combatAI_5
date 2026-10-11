"""PR本文の公開＋往復照合。本文の文字化けを人間任せにしないための環境.

PowerShell 経由の `--body "..."` はバッククォート解釈で本文を破壊する
（`t → TAB 等）ため、本文は必ずファイル経由で書き、書いた後に読み返して
差分が無いことを確認する。差分があれば exit 1。

Usage:
    python tools/state_dashboard/pr_publish.py --pr 3 --body-file body.md
    python tools/state_dashboard/pr_publish.py --create --base master --head <branch> \\
        --title "..." --body-file body.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import text_review

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args: list[str], timeout: int = 60) -> tuple[int, str]:
    try:
        proc = subprocess.run(args, capture_output=True, timeout=timeout, cwd=REPO_ROOT)
    except Exception as exc:
        return 1, str(exc)
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace").strip()


def fetch_body(pr: str) -> str | None:
    code, out = _run(["gh", "pr", "view", pr, "--json", "body"])
    if code != 0:
        return None
    try:
        return json.loads(out or "{}").get("body") or ""
    except json.JSONDecodeError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="PR本文の公開＋往復照合")
    ap.add_argument("--pr", help="編集対象のPR番号")
    ap.add_argument("--create", action="store_true", help="新規作成する")
    ap.add_argument("--base", default="master")
    ap.add_argument("--head", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--body-file", required=True)
    args = ap.parse_args()

    try:
        source = Path(args.body_file).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"body-file が読めない: {exc}")
        return 1

    if args.create:
        cmd = ["gh", "pr", "create", "--base", args.base, "--title", args.title,
               "--body-file", args.body_file]
        if args.head:
            cmd += ["--head", args.head]
        target = "新規PR"
    elif args.pr:
        cmd = ["gh", "pr", "edit", args.pr, "--body-file", args.body_file]
        target = f"PR #{args.pr}"
    else:
        print("--pr か --create が必要")
        return 1

    code, out = _run(cmd)
    if code != 0:
        print(f"公開に失敗: {out[:300]}")
        return 1
    number = args.pr
    if args.create:
        try:
            number = out.rstrip("/").split("/")[-1]
        except IndexError:
            number = ""
    fetched = fetch_body(number) if number else None
    if fetched is None:
        print("読み返しに失敗（要目視確認）")
        return 1
    diff = text_review.body_matches(fetched, source)
    if diff:
        print(f"{target} の本文が化けている:")
        for line in diff[:10]:
            print(f"  {line}")
        return 1
    print(f"{target} の本文は一致（{len(source)} 文字）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
