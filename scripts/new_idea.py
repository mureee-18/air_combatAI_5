"""新しいアイデアの雛形を作る。PR のアイデア規則も確かめる。

    python scripts/new_idea.py hosyan rushguard      # ideas/hosyan_rushguard/ と presets/hosyan_rushguard.json
    python scripts/new_idea.py --check origin/master # CI 用: 足したアイデアの名前と results/ の run を確かめる
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDEAS = Path("agent/strategy/ideas")
PRESETS = Path("agent/presets")
PART = re.compile(r"^[a-z0-9]+$")
IDEA_NAME = re.compile(r"^[a-z0-9]+_[a-z0-9_]+$")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout


def remote_branches(root: Path = ROOT) -> list[str]:
    try:
        out = _git(root, "ls-remote", "--heads", "origin")
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.split("refs/heads/", 1)[1] for line in out.splitlines() if "refs/heads/" in line]


def create(author: str, name: str, root: Path = ROOT, branches: list[str] | None = None) -> str:
    if not PART.match(author) or not PART.match(name):
        raise SystemExit(f"author and name must be lowercase letters and digits: {author!r} {name!r}")
    idea = f"{author}_{name}"
    branch = f"idea/{author}/{name}"
    taken = [p for p in (root / IDEAS / idea, root / PRESETS / f"{idea}.json", root / "agent/strategy/specialists"
                         / f"{idea}.py") if p.exists()]
    if taken:
        raise SystemExit(f"{idea} already exists: {', '.join(str(p.relative_to(root)) for p in taken)}")
    branches = remote_branches(root) if branches is None else branches
    if branch in branches:
        raise SystemExit(f"{idea} is taken: remote branch {branch} exists")
    shutil.copytree(root / IDEAS / "_template", root / IDEAS / idea, ignore=shutil.ignore_patterns("__pycache__"))
    args = json.loads((root / "agent" / "args.json").read_text(encoding="utf-8"))
    args["specialist"] = idea
    (root / PRESETS / f"{idea}.json").write_text(json.dumps(args, ensure_ascii=False, indent=4) + "\n",
                                                 encoding="utf-8")
    return idea


def added_ideas(base: str, root: Path = ROOT) -> list[str]:
    """base から HEAD までに足したアイデア（ideas/<名前>/ か presets/<名前>.json）。"""
    out = _git(root, "diff", "--name-only", "--diff-filter=A", f"{base}...HEAD", "--", str(IDEAS), str(PRESETS))
    names = set()
    for path in out.splitlines():
        parts = Path(path).parts
        if path.startswith(str(IDEAS) + "/") and len(parts) > 4 and not parts[3].startswith("_"):
            names.add(parts[3])
        elif path.startswith(str(PRESETS) + "/") and path.endswith(".json"):
            names.add(Path(path).stem)
    return sorted(names)


def added_run_candidates(base: str, root: Path = ROOT) -> set[str]:
    out = _git(root, "diff", "--name-only", "--diff-filter=A", f"{base}...HEAD", "--", "results/runs")
    names = set()
    for path in out.splitlines():
        if path.endswith("/manifest.json"):
            manifest = json.loads((root / path).read_text(encoding="utf-8"))
            if manifest.get("status") == "complete":
                names.add(manifest["candidate"]["name"])
    return names


def check(base: str, root: Path = ROOT) -> list[str]:
    errors = []
    runs = added_run_candidates(base, root)
    for idea in added_ideas(base, root):
        if not IDEA_NAME.match(idea):
            errors.append(f"idea {idea!r} must be named <author>_<name> (lowercase letters, digits, underscores)")
        if idea not in runs:
            errors.append(f"idea {idea!r} has no complete run under results/runs/; "
                          f"run scripts/eval_pool.py --preset {idea} and commit the run in this PR")
    return errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="new_idea")
    ap.add_argument("author", nargs="?")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--check", metavar="BASE", help="BASE...HEAD で足したアイデアを確かめる（CI 用）")
    a = ap.parse_args(argv)
    if a.check:
        errors = check(a.check)
        for e in errors:
            print(f"error: {e}")
        print(f"{len(errors)} idea errors")
        return 1 if errors else 0
    if not (a.author and a.name):
        ap.error("author and name are required")
    idea = create(a.author, a.name)
    print(f"created {IDEAS / idea}/ and {PRESETS / idea}.json")
    print(f"next: git switch -c idea/{a.author}/{a.name}; edit {IDEAS / idea}/__init__.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
