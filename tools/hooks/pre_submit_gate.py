"""SIGNATE 提出前ゲート (tools/hooks/pre_submit_gate.py).

`signate submit` を含むコマンドの実行前に hook-gates.ts から呼ばれる。
提出は**ユーザーの明示指示があった時のみ**許可し、エージェントの独断提出を
構造的に防ぐ。ユーザーが「提出して」と指示した場合は環境変数
ATLA5_SUBMIT_CONFIRM=1 を付けて実行する（付け忘れ時はこのゲートがブロックする）。

hook-gates.ts は execFile で node 側の env のみ継承するため、実行シェル側の
$env: で設定した env はゲートに届かない（kaggriculture 2026-09-28 実測）。
コマンド文字列中の `ATLA5_SUBMIT_CONFIRM=1` もフォールバックとして受け入れる。

加えて、提出物そのものの安全確認として次を検証する。
    1. 提出用 specialist であること（ローカル評価専用を誤提出しない）
    2. submission/submit.zip が必須3点を含むこと
    3. agent/ の fatal lint (ruff) が通ること
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ARGS_PATH = REPO_ROOT / "agent" / "args.json"
ZIP_PATH = REPO_ROOT / "submission" / "submit.zip"
CONFIRM_ENV = "ATLA5_SUBMIT_CONFIRM"

ALLOWED_SPECIALISTS = {"baseline"}
REQUIRED_ENTRIES = ["__init__.py", "args.json", "config.json"]


def _run(cmd: list[str]) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as e:
        return f"コマンドが見つかりません: {' '.join(cmd)} ({e})"
    if r.returncode != 0:
        out = (r.stdout or "")[-2000:]
        err = (r.stderr or "")[-2000:]
        return f"コマンド失敗: {' '.join(cmd)}\n{out}\n{err}".strip()
    return None


def _active_specialist() -> str:
    args = json.loads(ARGS_PATH.read_text(encoding="utf-8"))
    return str(args.get("specialist", ""))


def main() -> int:
    ap = argparse.ArgumentParser(description="SIGNATE 提出前ゲート")
    ap.add_argument("--command", default="", help="検証された提出コマンド（ログ用）")
    parsed = ap.parse_args()

    confirmed = os.environ.get(CONFIRM_ENV) == "1" or bool(
        re.search(rf"{CONFIRM_ENV}\s*=?\s*\"?1", parsed.command)
    )
    if not confirmed:
        print(
            "提出はユーザーの『提出して』の明示指示があった時のみ実行できます。\n"
            f"明示指示がある場合は環境変数 {CONFIRM_ENV}=1 を付けて再実行してください。\n"
            f"対象コマンド: {parsed.command}"
        )
        return 1

    specialist = _active_specialist()
    if specialist not in ALLOWED_SPECIALISTS:
        print(
            f"提出用ではない specialist が指定されています: {specialist}\n"
            f"提出可能な specialist: {sorted(ALLOWED_SPECIALISTS)}"
        )
        return 1

    if not ZIP_PATH.exists():
        print(f"提出物がありません: {ZIP_PATH}\npython scripts/build_submission.py を実行してください。")
        return 1

    with zipfile.ZipFile(ZIP_PATH) as z:
        names = set(z.namelist())
    missing = [entry for entry in REQUIRED_ENTRIES if entry not in names]
    if missing:
        print(f"提出物に必須ファイルがありません: {missing}")
        return 1

    # CI では uvx ruff、ローカルでは ruff どちらも通るよう試行
    detail = _run(["uvx", "ruff", "check", "agent/"])
    if detail is not None and "コマンドが見つかりません" in detail:
        detail = _run(["ruff", "check", "agent/"])
    if detail is not None:
        print("提出前チェック（fatal lint）に失敗しました:\n" + detail)
        return 1

    print(f"提出前ゲート OK: specialist={specialist} zip={ZIP_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
