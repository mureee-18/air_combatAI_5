"""ダッシュボードのキャッシュ無効化ツール（kaggriculture から移植・簡略化）.

ブラウザに古い index.html / rules.json が残るのを防ぐ。build_id は serve.py の
build_id() が「index.html の mtime:サイズ | rules.json の mtime:サイズ | epoch ファイルの
中身」をハッシュして作る。このスクリプトは epoch ファイル
（analysis/ops/dashboard_cache_epoch.txt）を書き換えて build_id を変える。

serve.py は全レスポンスに `Cache-Control: no-store` を付けているので日常の「古い画面」は
起きない。本ツールは OS / ブラウザ側にキャッシュが残っている場合に手動で使う。

Usage:
    python tools/state_dashboard/cache_bump.py            # build_id を変える
    python tools/state_dashboard/cache_bump.py --status   # 現在の build_id を表示（変更なし）
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = Path(__file__).resolve().parent
INDEX_HTML = DASHBOARD_DIR / "index.html"
RULES_JSON = DASHBOARD_DIR / "rules.json"
EPOCH_FILE = REPO_ROOT / "analysis" / "ops" / "dashboard_cache_epoch.txt"


def asset_sig(path: Path) -> str:
    if not path.exists():
        return ""
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def build_id() -> str:
    epoch = EPOCH_FILE.read_text(encoding="utf-8").strip() if EPOCH_FILE.exists() else ""
    raw = "|".join([asset_sig(INDEX_HTML), asset_sig(RULES_JSON), epoch])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def bump() -> str:
    EPOCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    EPOCH_FILE.write_text(f"{time.time_ns()}\n", encoding="utf-8")
    return build_id()


def show_status() -> str:
    epoch = EPOCH_FILE.read_text(encoding="utf-8").strip() if EPOCH_FILE.exists() else "(未作成)"
    return "\n".join(
        [
            f"build_id: {build_id()}",
            f"epoch: {epoch}",
            f"index.html: {asset_sig(INDEX_HTML)}",
            f"rules.json: {asset_sig(RULES_JSON)}",
        ]
    )


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="ダッシュボードのキャッシュ無効化")
    parser.add_argument("--status", action="store_true", help="現在の build_id を表示して終了")
    args = parser.parse_args()

    if args.status:
        print(show_status())
        return

    before = build_id()
    after = bump()
    print(f"build_id: {before} -> {after}")
    print(f"epoch: {EPOCH_FILE.relative_to(REPO_ROOT).as_posix()}")
    if before == after:
        print("警告: build_id が変わりません（epoch ファイルの書き込みを確認してください）")


if __name__ == "__main__":
    main()
