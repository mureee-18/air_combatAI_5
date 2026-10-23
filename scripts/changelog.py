"""changelog.d/*.md の断片から CHANGELOG.md を作る。手で書いた既存の項目はそのまま残す。

断片のファイル名は <YYYY-MM-DD>-<作者>-<話題>.md、中身は "### 見出し" と箇条書きです。
生成した部分は CHANGELOG.md の先頭のマーカーの間に入り、何度実行しても同じ結果になります。

    python scripts/changelog.py          # CHANGELOG.md を書き直す
    python scripts/changelog.py --check  # 書き直しが要るなら終了コード1
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
START = "<!-- changelog.d: generated from changelog.d/*.md by scripts/changelog.py; edit the fragments -->"
END = "<!-- changelog.d: end -->"
FRAGMENT = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$")


def fragments(directory: Path) -> list[tuple[str, str, str]]:
    out = []
    for path in sorted(directory.glob("*.md")):
        m = FRAGMENT.match(path.name)
        if m:
            out.append((m.group(1), m.group(2), path.read_text(encoding="utf-8").strip()))
    return out


def render(changelog: str, frags: list[tuple[str, str, str]]) -> str:
    if START in changelog and END in changelog:
        head, rest = changelog.split(START, 1)
        tail = rest.split(END, 1)[1].lstrip("\n")
    else:
        lines = changelog.splitlines(keepends=True)
        head = lines[0] + "\n" if lines and lines[0].startswith("# ") else "# CHANGELOG\n\n"
        tail = "".join(lines[1:]).lstrip("\n") if lines and lines[0].startswith("# ") else changelog
    blocks = []
    for date in sorted({d for d, _, _ in frags}, reverse=True):
        body = "\n\n".join(text for d, _, text in sorted(frags) if d == date)
        blocks.append(f"## {date}\n\n{body}\n")
    generated = "\n".join(blocks)
    return f"{head.rstrip()}\n\n{START}\n{generated}{END}\n\n{tail}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="changelog")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    root = Path(a.root)
    path = root / "CHANGELOG.md"
    old = path.read_text(encoding="utf-8") if path.exists() else "# CHANGELOG\n"
    new = render(old, fragments(root / "changelog.d"))
    if a.check:
        print("CHANGELOG.md is up to date" if new == old else "CHANGELOG.md is stale; run python scripts/changelog.py")
        return 0 if new == old else 1
    path.write_text(new, encoding="utf-8")
    print(f"wrote {path} from {len(fragments(root / 'changelog.d'))} fragments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
