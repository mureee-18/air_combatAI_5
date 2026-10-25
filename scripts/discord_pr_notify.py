"""PR のコメント・レビューを Discord Webhook に通知する（GitHub Actions 用）。

イベント本文は GITHUB_EVENT_PATH の JSON から読み、シェルには一切展開しない。
Webhook URL は環境変数 DISCORD_WEBHOOK_URL から読む。未設定なら通知を飛ばして正常終了する。

ローカル確認: python scripts/discord_pr_notify.py --event-name issue_comment --event-path sample.json --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

EXCERPT_CHARS = 300
DISCORD_CONTENT_LIMIT = 2000

REVIEW_VERBS = {
    "approved": ("✅", "を承認しました"),
    "changes_requested": ("📝", "に変更をリクエストしました"),
    "commented": ("💬", "をレビューしました"),
}


def _is_bot(user: dict | None) -> bool:
    if not user:
        return True
    return user.get("type") == "Bot" or str(user.get("login", "")).endswith("[bot]")


def _excerpt(body: str | None) -> str:
    text = (body or "").strip()
    if not text:
        return ""
    if len(text) > EXCERPT_CHARS:
        text = text[:EXCERPT_CHARS].rstrip() + "…"
    return "\n".join("> " + line for line in text.splitlines())


def _pr_label(number: int, title: str) -> str:
    return f"PR #{number}「{title}」"


def build_message(event_name: str, event: dict) -> str | None:
    """通知文を返す。通知しないイベントなら None。"""
    action = event.get("action")
    sender = event.get("sender")

    if event_name == "issue_comment":
        issue = event.get("issue") or {}
        if action != "created" or "pull_request" not in issue:
            return None
        comment = event.get("comment") or {}
        if _is_bot(comment.get("user")) or _is_bot(sender):
            return None
        head = f"💬 {comment['user']['login']} さんが {_pr_label(issue['number'], issue['title'])}にコメントしました"
        return _compose(head, comment.get("body"), comment.get("html_url"))

    if event_name == "pull_request_review":
        review = event.get("review") or {}
        pr = event.get("pull_request") or {}
        if action != "submitted" or _is_bot(review.get("user")) or _is_bot(sender):
            return None
        state = str(review.get("state", "")).lower()
        if state not in REVIEW_VERBS:
            return None
        body = (review.get("body") or "").strip()
        # 本文なしの「コメントのみ」レビューは、行コメントが pull_request_review_comment で個別に届くので省く。
        if state == "commented" and not body:
            return None
        emoji, verb = REVIEW_VERBS[state]
        head = f"{emoji} {review['user']['login']} さんが {_pr_label(pr['number'], pr['title'])}{verb}"
        return _compose(head, body, review.get("html_url"))

    if event_name == "pull_request_review_comment":
        comment = event.get("comment") or {}
        pr = event.get("pull_request") or {}
        if action != "created" or _is_bot(comment.get("user")) or _is_bot(sender):
            return None
        path = comment.get("path") or "ファイル"
        label = _pr_label(pr["number"], pr["title"])
        head = f"💬 {comment['user']['login']} さんが {label}の `{path}` にコメントしました"
        return _compose(head, comment.get("body"), comment.get("html_url"))

    return None


def _compose(head: str, body: str | None, url: str | None) -> str:
    parts = [head]
    quoted = _excerpt(body)
    if quoted:
        parts.append(quoted)
    if url:
        parts.append(f"<{url}>")  # <> でリンクのプレビュー展開を抑える
    message = "\n".join(parts)
    if len(message) > DISCORD_CONTENT_LIMIT:
        message = message[: DISCORD_CONTENT_LIMIT - 1] + "…"
    return message


def build_payload(message: str) -> dict:
    # allowed_mentions.parse を空にして @everyone / @here / ユーザー・ロールのメンションを無効化する。
    return {"content": message, "allowed_mentions": {"parse": []}}


def post(webhook_url: str, payload: dict) -> int:
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "air_combatAI_5-discord-notify"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as res:
        return res.status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--dry-run", action="store_true", help="送信せず payload を表示する")
    args = parser.parse_args(argv)

    with open(args.event_path, encoding="utf-8") as f:
        event = json.load(f)

    message = build_message(args.event_name, event)
    if message is None:
        print(f"skip: 通知対象外のイベントです（{args.event_name} / {event.get('action')}）")
        return 0

    payload = build_payload(message)
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook_url:
        print("::notice::DISCORD_WEBHOOK_URL が未設定のため Discord 通知を飛ばしました")
        return 0

    status = post(webhook_url, payload)
    print(f"Discord に送信しました（HTTP {status}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
