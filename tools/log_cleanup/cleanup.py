"""対戦結果ログ (workspace/results*) の世代管理ツール.

1戦あたり数 MB の log_{n}.json が溜まるため、直近 N 世代だけを残す。
デフォルトは dry-run（一覧を出して消さない）。

Usage:
    python tools/log_cleanup/cleanup.py                 # dry-run
    python tools/log_cleanup/cleanup.py --keep 5        # 直近5世代を保持
    python tools/log_cleanup/cleanup.py --execute       # 実際に削除（確認プロンプトあり）
    python tools/log_cleanup/cleanup.py --execute --yes # 確認なしで削除
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT / "workspace"
PATTERNS = ["results*", "paired"]


def dir_size(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def human(size: int) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024 or unit == "GB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}GB"


def collect_targets() -> list[Path]:
    targets = []
    for pattern in PATTERNS:
        targets.extend(p for p in WORKSPACE.glob(pattern) if p.is_dir())
    return sorted(set(targets), key=lambda p: p.stat().st_mtime, reverse=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="対戦ログの整理")
    parser.add_argument("--keep", type=int, default=3, help="保持する世代数")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    targets = collect_targets()
    if not targets:
        print("対象ディレクトリはありません")
        return

    print(f"対象: {WORKSPACE} （{len(targets)} 件, 合計 {human(sum(dir_size(t) for t in targets))}）")
    keep = targets[: args.keep]
    drop = targets[args.keep :]

    for path in keep:
        print(f"  keep  : {path.name:<24} {human(dir_size(path))}")
    for path in drop:
        print(f"  delete: {path.name:<24} {human(dir_size(path))}")

    if not drop:
        print("削除対象はありません")
        return

    if not args.execute:
        print("dry-run のため削除しません（--execute で削除）")
        return

    if not args.yes:
        answer = input(f"{len(drop)} 件を削除しますか？ [y/N]: ").strip().lower()
        if answer != "y":
            print("中止しました")
            return

    for path in drop:
        shutil.rmtree(path)
        print(f"deleted: {path.name}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
