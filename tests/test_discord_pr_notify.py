import importlib.util
import json
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "scripts" / "discord_pr_notify.py"
_spec = importlib.util.spec_from_file_location("discord_pr_notify", _PATH)
dpn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dpn)

HUMAN = {"login": "mureee-18", "type": "User"}
BOT = {"login": "github-actions[bot]", "type": "Bot"}
PR = {"number": 18, "title": "H9: Red 側チューニング"}


def _issue_comment(body="LGTM です", user=HUMAN, is_pr=True):
    issue = {"number": 18, "title": PR["title"]}
    if is_pr:
        issue["pull_request"] = {"url": "x"}
    return {
        "action": "created",
        "issue": issue,
        "sender": user,
        "comment": {"user": user, "body": body, "html_url": "https://github.com/o/r/pull/18#issuecomment-1"},
    }


def _review(state, body=""):
    return {
        "action": "submitted",
        "pull_request": PR,
        "sender": HUMAN,
        "review": {"user": HUMAN, "state": state, "body": body, "html_url": "https://github.com/o/r/pull/18#r1"},
    }


def test_issue_comment_on_pr():
    msg = dpn.build_message("issue_comment", _issue_comment())
    assert msg.splitlines() == [
        "💬 mureee-18 さんが PR #18「H9: Red 側チューニング」にコメントしました",
        "> LGTM です",
        "<https://github.com/o/r/pull/18#issuecomment-1>",
    ]


def test_issue_comment_on_plain_issue_is_skipped():
    assert dpn.build_message("issue_comment", _issue_comment(is_pr=False)) is None


def test_bot_is_skipped():
    assert dpn.build_message("issue_comment", _issue_comment(user=BOT)) is None


def test_review_states():
    assert dpn.build_message("pull_request_review", _review("APPROVED")).startswith(
        "✅ mureee-18 さんが PR #18「H9: Red 側チューニング」を承認しました"
    )
    changes = dpn.build_message("pull_request_review", _review("CHANGES_REQUESTED", "直して"))
    assert "に変更をリクエストしました" in changes
    assert "をレビューしました" in dpn.build_message("pull_request_review", _review("COMMENTED", "全体所感"))


def test_empty_commented_review_is_skipped():
    assert dpn.build_message("pull_request_review", _review("COMMENTED", "")) is None


def test_inline_review_comment_has_path():
    event = {
        "action": "created",
        "pull_request": PR,
        "sender": HUMAN,
        "comment": {"user": HUMAN, "path": "agent/default.py", "body": "ここ", "html_url": "u"},
    }
    msg = dpn.build_message("pull_request_review_comment", event)
    assert msg.startswith(
        "💬 mureee-18 さんが PR #18「H9: Red 側チューニング」の `agent/default.py` にコメントしました"
    )


def test_long_body_is_truncated_and_mentions_disabled():
    msg = dpn.build_message("issue_comment", _issue_comment(body="@everyone " + "あ" * 1000))
    assert len(msg) < 450
    assert "…" in msg
    payload = dpn.build_payload(msg)
    assert payload["allowed_mentions"] == {"parse": []}


def test_hostile_body_is_plain_data(tmp_path, capsys):
    body = '$(touch /tmp/pwned) `id` "; rm -rf / #'
    path = tmp_path / "event.json"
    path.write_text(json.dumps(_issue_comment(body=body)), encoding="utf-8")
    assert dpn.main(["--event-name", "issue_comment", "--event-path", str(path), "--dry-run"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert body in out["content"]


def test_missing_webhook_skips_without_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    path = tmp_path / "event.json"
    path.write_text(json.dumps(_issue_comment()), encoding="utf-8")
    assert dpn.main(["--event-name", "issue_comment", "--event-path", str(path)]) == 0
    assert "未設定" in capsys.readouterr().out
