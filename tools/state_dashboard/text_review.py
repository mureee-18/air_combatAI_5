"""PR本文・README等の文章レビュー（文字化け・最新性）。gitタブ用.

仮説登録タブのコピー釦から貼られた材料が文字化けせず正しい文章か、
PR本文やREADMEが最新かを git タブで見直すためのもの。
チェック自体は読み取り専用。修正は人間（または材料を受け取ったAI）が行う。

Usage:
    python tools/state_dashboard/text_review.py
    python tools/state_dashboard/text_review.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

REVIEW_DOCS = [
    "README.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "tools/state_dashboard/HYPOTHESIS_POLICY.md",
    "tools/battle_analyzer/BATTLELOG_FORMAT.md",
    "tools/state_dashboard/custom_metrics.json",
]

MOJIBAKE_PATTERNS = [
    ("replacement", re.compile("\ufffd")),
    ("control", re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")),
    ("halfwidth-run", re.compile(r"[\uff61-\uff9f]{6,}")),
]

MAX_ISSUES_PER_FILE = 20
MAX_CARDS = 8


def review_doc_paths() -> list[Path]:
    paths = [REPO_ROOT / p for p in REVIEW_DOCS if (REPO_ROOT / p).is_file()]
    agents = REPO_ROOT / "analysis" / "agents"
    if agents.is_dir():
        paths += sorted(agents.glob("*/improvement.md"))
    return paths


def scan_text(text: str) -> list[dict]:
    """文字化けの疑い箇所を返す [{line, col, kind, snippet}]."""
    out: list[dict] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for kind, rx in MOJIBAKE_PATTERNS:
            for m in rx.finditer(line):
                start = max(0, m.start() - 12)
                out.append(
                    {
                        "line": lineno,
                        "col": m.start() + 1,
                        "kind": kind,
                        "snippet": line[start : m.end() + 12],
                    }
                )
                if len(out) >= MAX_ISSUES_PER_FILE:
                    return out
    return out


def review_docs() -> dict:
    files = []
    for path in review_doc_paths():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            files.append(
                {
                    "file": path.relative_to(REPO_ROOT).as_posix(),
                    "readable": False,
                    "count": 1,
                    "issues": [{"line": 0, "col": 0, "kind": "decode-error", "snippet": ""}],
                }
            )
            continue
        except OSError:
            continue
        issues = scan_text(text)
        files.append(
            {
                "file": path.relative_to(REPO_ROOT).as_posix(),
                "readable": True,
                "count": len(issues),
                "issues": issues[:6],
            }
        )
    return {"files": files, "bad": sum(1 for f in files if f["count"] > 0)}


def _run(args: list[str], timeout: int) -> str | None:
    """Windows の cp932 誤爆を避け、UTF-8 で読む（日本語の gh/git 出力用）."""
    try:
        proc = subprocess.run(
            args, capture_output=True, timeout=timeout, cwd=REPO_ROOT
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace").strip()


def _git(args: list[str], timeout: int = 15) -> str | None:
    return _run(["git", *args], timeout)


def changelog_freshness() -> dict:
    """CHANGELOG の最終日付と HEAD を比べ、追記が必要そうかを見る."""
    path = REPO_ROOT / "CHANGELOG.md"
    last = None
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        dates = re.findall(r"^##\s+(\d{4}-\d{2}-\d{2})", text, re.M)
        last = dates[0] if dates else None
    head = _git(["log", "-1", "--format=%ad", "--date=short"])
    since = 0
    if last and head:
        for line in (_git(["log", "--format=%ad", "--date=short"]) or "").splitlines():
            if line.strip() > last:
                since += 1
    return {
        "exists": path.is_file(),
        "last_entry": last,
        "head_date": head,
        "commits_since": since,
        "stale": bool(last and head and head > last and since > 0),
    }


def readme_specialist() -> dict:
    """README が specialist 名に触れていれば、現行と一致するかを見る."""
    args_path = REPO_ROOT / "agent" / "args.json"
    try:
        current = (json.loads(args_path.read_text(encoding="utf-8")) or {}).get("specialist")
    except (OSError, json.JSONDecodeError):
        current = None
    names = {"baseline", "default"}
    spec_dir = REPO_ROOT / "agent" / "strategy" / "specialists"
    if spec_dir.is_dir():
        names |= {p.stem for p in spec_dir.glob("*.py") if not p.stem.startswith("_")}
    path = REPO_ROOT / "README.md"
    mentions: list[str] = []
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = ""
        mentions = sorted({n for n in names if n in text})
    if not mentions:
        return {"current": current, "mentions": [], "match": None}
    return {"current": current, "mentions": mentions, "match": bool(current and current in mentions)}


def _epoch(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).replace(
            tzinfo=timezone.utc
        ).timestamp()
    except ValueError:
        return None


def pr_reviews() -> dict:
    """開いている PR の本文を文字化け・最新性で見る（gh が無ければ skip）."""
    if shutil.which("gh") is None:
        return {"available": False, "prs": []}
    out = _run(
        ["gh", "pr", "list", "--state", "open", "--json",
         "number,title,body,updatedAt,headRefName,url"],
        30,
    )
    if out is None:
        return {"available": False, "prs": []}
    try:
        items = json.loads(out or "[]")
    except json.JSONDecodeError:
        return {"available": False, "prs": []}
    prs = []
    for item in items:
        if not isinstance(item, dict):
            continue
        body = item.get("body") or ""
        issues = scan_text(body)
        ref = item.get("headRefName") or ""
        head_date = _git(["log", "-1", "--format=%ct", ref]) if ref else None
        try:
            head_epoch = float(head_date) if head_date else None
        except (TypeError, ValueError):
            head_epoch = None
        updated_epoch = _epoch(item.get("updatedAt"))
        stale = bool(
            head_epoch is not None
            and updated_epoch is not None
            and head_epoch > updated_epoch
        )
        prs.append(
            {
                "number": item.get("number"),
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "mojibake": len(issues),
                "issues": issues[:4],
                "stale": stale,
            }
        )
    return {"available": True, "prs": prs}


def _card(
    cid: str,
    title: str,
    summary: str,
    evidence: list[dict],
    phrase: str,
    hypothesis: str = "",
    from_path: str = "",
) -> dict:
    return {
        "id": cid,
        "kind": "observation",
        "source": "code",
        "title": title,
        "summary": summary,
        "evidence": evidence,
        "hypothesis": hypothesis,
        "metric": "",
        "from_tab": "git",
        "from_path": from_path,
        "command": "",
        "command_label": "",
        "phrase": phrase[:120],
    }


def review_cards() -> list[dict]:
    """git タブが renderFact で描く事実カード（コピー釦付き）."""
    cards: list[dict] = []
    docs = review_docs()
    total = sum(f["count"] for f in docs["files"])
    n_files = len(docs["files"])
    if total == 0:
        cards.append(
            _card(
                "textreview:docs-ok",
                f"文書レビュー: 対象 {n_files} 件・文字化け 0 件",
                "README・CHANGELOG・仕様書・改善記録に文字化けの疑いはない。",
                [
                    {"label": "対象文書", "value": n_files, "num": True, "digits": 0},
                    {"label": "文字化け", "value": 0, "num": True, "digits": 0},
                ],
                f"文書レビュー: 対象{n_files}件・文字化け0件",
            )
        )
    for f in docs["files"]:
        if f["count"] == 0 or len(cards) >= MAX_CARDS:
            continue
        first = f["issues"][0] if f["issues"] else {"line": 0, "kind": "?"}
        cards.append(
            _card(
                f"textreview:mojibake:{f['file']}",
                f"文字化けの疑い: {f['file']}（{f['count']} 件）",
                "該当行を UTF-8 で開き直し、正しい文章に修正する。直さないと貼った材料も化ける。",
                [
                    {"label": "ファイル", "value": f["file"], "num": False},
                    {"label": "件数", "value": f["count"], "num": True, "digits": 0},
                    {
                        "label": "先頭",
                        "value": f"{first.get('line')}行目・{first.get('kind')}",
                        "num": False,
                    },
                ],
                f"{f['file']}に文字化け{f['count']}件",
                hypothesis="該当行をUTF-8で開き直して修正する。",
                from_path=f["file"],
            )
        )
    fresh = changelog_freshness()
    if fresh["exists"]:
        if fresh["stale"]:
            cards.append(
            _card(
                "textreview:changelog-stale",
                f"CHANGELOG が古い（最終 {fresh['last_entry']}・{fresh['commits_since']} 件分）",
                    "最終日付より後にコミットがある。最新の変更を追記する。",
                    [
                        {"label": "最終記載", "value": fresh["last_entry"] or "—", "num": False},
                        {"label": "HEAD", "value": fresh["head_date"] or "—", "num": False},
                        {"label": "未記載", "value": fresh["commits_since"], "num": True, "digits": 0},
                    ],
                    f"CHANGELOGは{fresh['last_entry']}で止まり{int(fresh['commits_since'])}件未記載",
                    hypothesis="CHANGELOGに最新の変更を追記する。",
                    from_path="CHANGELOG.md",
                )
            )
        else:
            cards.append(
                _card(
                    "textreview:changelog-ok",
                    f"CHANGELOG は最新（最終 {fresh['last_entry'] or '—'}）",
                    "最終日付より後のコミットはない。",
                    [
                        {"label": "最終記載", "value": fresh["last_entry"] or "—", "num": False},
                    ],
                    f"CHANGELOGは最新（{fresh['last_entry'] or '—'}）",
                    from_path="CHANGELOG.md",
                )
            )
    spec = readme_specialist()
    if spec["mentions"] and not spec["match"]:
        cards.append(
            _card(
                "textreview:readme-specialist",
                f"README の specialist 記載: 不一致（現行 {spec['current']}）",
                "README が古い方針名を指している。現行に直す。",
                [
                    {"label": "現行", "value": spec["current"] or "—", "num": False},
                    {"label": "記載", "value": "・".join(spec["mentions"]), "num": False},
                ],
                "READMEのspecialist記載は不一致",
                hypothesis="READMEの方針名を現行に直す。",
                from_path="README.md",
            )
        )
    prs = pr_reviews()
    if prs["available"]:
        for pr in prs["prs"]:
            if len(cards) >= MAX_CARDS + 4:
                break
            num = pr.get("number")
            states = []
            if pr["mojibake"] > 0:
                states.append(f"文字化け{pr['mojibake']}件")
            if pr["stale"]:
                states.append("最新push未反映の可能性")
            ok = not states
            cards.append(
                _card(
                    f"textreview:pr-{num}",
                    f"PR #{num} 本文: {'OK' if ok else '・'.join(states)}",
                    "本文が化けず最新の内容かを PR ページで確認する。"
                    if not ok
                    else "本文に文字化けはなく、最新の push を反映している。",
                    [
                        {"label": "PR", "value": f"#{num}", "num": False},
                        {"label": "文字化け", "value": pr["mojibake"], "num": True, "digits": 0},
                        {"label": "鮮度", "value": "最新" if not pr["stale"] else "要確認", "num": False},
                    ],
                    f"PR #{num} 本文は{'OK' if ok else '要確認'}",
                    hypothesis="" if ok else "PR本文を最新の内容に更新する。",
                    from_path=pr.get("url") or "",
                )
            )
    return cards


def review_summary() -> dict:
    docs = review_docs()
    return {
        "docs": docs,
        "changelog": changelog_freshness(),
        "readme": readme_specialist(),
        "prs": pr_reviews(),
        "cards": review_cards(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="PR本文・README等の文章レビュー")
    ap.add_argument("--json", action="store_true", help="JSON を標準出力に吐く")
    args = ap.parse_args()
    summary = review_summary()
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
        return 0
    docs = summary["docs"]
    print(f"文書: {len(docs['files'])} 件・文字化け {sum(f['count'] for f in docs['files'])} 件")
    for f in docs["files"]:
        if f["count"]:
            print(f"  {f['file']}: {f['count']} 件")
    fresh = summary["changelog"]
    print(
        f"CHANGELOG: 最終 {fresh['last_entry']} / HEAD {fresh['head_date']} "
        f"/ 未記載 {fresh['commits_since']} 件"
    )
    spec = summary["readme"]
    print(f"README specialist: 記載 {spec['mentions']} / 現行 {spec['current']}")
    prs = summary["prs"]
    if not prs["available"]:
        print("PR: gh 不可のため skip")
    for pr in prs["prs"]:
        print(f"  PR #{pr['number']}: 文字化け {pr['mojibake']} 件・stale={pr['stale']}")
    print(f"カード: {len(summary['cards'])} 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
