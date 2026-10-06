"""improvement_session の型別記録（kind / source）の回帰テスト.

kaggriculture の records.py と同じ考え方:
「事実（出所あり）」と「推論（仮説）」を型で分離し、種別ごとに許容される出所を制限する。
"""

import argparse
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSION_PATH = REPO_ROOT / "analysis" / "tools" / "improvement_session.py"


def load_module():
    spec = importlib.util.spec_from_file_location("improvement_session", SESSION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def session(tmp_path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "AGENTS_DIR", tmp_path / "agents")
    (module.SPECIALISTS_DIR).mkdir(parents=True, exist_ok=True)
    return module


def make_args(**kwargs):
    base = {
        "specialist": "baseline",
        "text": "テスト",
        "source": "log",
        "kind": "observation",
        "direction": "方向",
        "changes": "変更",
        "verification": "検証",
        "next_steps": "",
        "hypothesis": "",
        "paired": "",
        "games": 1,
    }
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_validate_record_allows_expected_pairs(session):
    for kind, source in [
        ("rule", "official"),
        ("observation", "log"),
        ("observation", "analysis"),
        ("inference", "log"),
        ("inference", "code"),
    ]:
        session.validate_record(kind, source)


def test_validate_record_rejects_unknown_kind_and_source(session):
    with pytest.raises(SystemExit):
        session.validate_record("guess", "log")
    with pytest.raises(SystemExit):
        session.validate_record("observation", "rumor")


def test_validate_record_rejects_rule_without_official_source(session):
    with pytest.raises(SystemExit) as excinfo:
        session.validate_record("rule", "log")
    assert "型制約違反" in str(excinfo.value)


def test_next_record_id_increments_per_kind(session, tmp_path):
    note = tmp_path / "improvement.md"
    assert session.next_record_id(note, "observation") == "O-001"
    note.write_text("\n## O-001 [observation/log] 2026-01-01T00:00:00\n- 種別: observation\n", encoding="utf-8")
    assert session.next_record_id(note, "observation") == "O-002"
    assert session.next_record_id(note, "inference") == "N-001"


def test_record_writes_typed_heading(session):
    session.cmd_start(make_args())
    session.cmd_record(make_args(kind="observation", source="log"))
    session.cmd_record(make_args(kind="inference", source="analysis"))

    text = session.note_path("baseline").read_text(encoding="utf-8")
    assert "## O-001 [observation/log]" in text
    assert "## N-001 [inference/analysis]" in text
    assert "- 出所: log（対戦ログ / 計測値）" in text


def test_record_rejects_invalid_pair(session):
    session.cmd_start(make_args())
    with pytest.raises(SystemExit):
        session.cmd_record(make_args(kind="rule", source="log"))
    assert not session.note_path("baseline").exists()


def test_hypothesis_is_stored_as_inference_with_source(session):
    session.cmd_start(make_args())
    session.cmd_hypothesis(make_args(text="射距離を延ばすと命中率が上がる", source="log"))
    state = session.load_state("baseline")
    hypothesis = state["hypotheses"][-1]
    assert hypothesis["kind"] == "inference"
    assert hypothesis["source"] == "log"
    assert hypothesis["id"].startswith("N-")


def test_hypothesis_ids_are_unique(session):
    for _ in range(3):
        session.cmd_hypothesis(make_args(source="log"))
    ids = [h["id"] for h in session.load_state("baseline")["hypotheses"]]
    assert ids == ["N-001", "N-002", "N-003"]


def test_verify_records_linked_hypothesis(session, monkeypatch):
    monkeypatch.setattr(session, "run_games", lambda games: [])
    monkeypatch.setattr(session, "summarize", lambda label, results: {"avg_score": 0.1})
    session.cmd_verify(make_args(hypothesis="N-002"))
    cycle = session.load_state("baseline")["cycles"][-1]
    assert cycle["kind"] == "verify"
    assert cycle["hypothesis"] == "N-002"


def test_validate_records_linked_hypothesis(session, monkeypatch, tmp_path):
    monkeypatch.setattr(session, "summarize_paired", lambda path: {"avg_score": 0.5})
    paired = tmp_path / "paired.json"
    paired.write_text("{}", encoding="utf-8")
    session.cmd_validate(make_args(hypothesis="N-003", paired=str(paired)))
    cycle = session.load_state("baseline")["cycles"][-1]
    assert cycle["kind"] == "validate"
    assert cycle["hypothesis"] == "N-003"


def test_normalize_text_collapses_repeated_sentence(session):
    assert session.normalize_text("abc abc") == "abc"
    assert session.normalize_text("abc abc。") == "abc"
    assert session.normalize_text("  重複しない文  ") == "重複しない文"


def test_assumption_dedupes_repeat_and_consecutive(session, capsys):
    session.cmd_start(make_args())
    session.cmd_assumption(make_args(text="MWS は 10km までしか効かない MWS は 10km までしか効かない。"))
    session.cmd_assumption(make_args(text="MWS は 10km までしか効かない"))
    state = session.load_state("baseline")
    assert [a["text"] for a in state["assumptions"]] == ["MWS は 10km までしか効かない"]


def test_check_reports_records_by_kind(session, capsys):
    session.cmd_start(make_args())
    session.cmd_record(make_args(kind="observation", source="log"))
    capsys.readouterr()
    session.cmd_check(make_args())
    out = capsys.readouterr().out
    assert "記録: 1 件" in out
    assert "observation=1" in out
