"""文章レビュー（text_review.py）のテスト."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MOD_PATH = REPO_ROOT / "tools" / "state_dashboard" / "text_review.py"


def load_mod():
    spec = importlib.util.spec_from_file_location("text_review", MOD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mod = load_mod()


def test_scan_clean_text_has_no_issues():
    assert mod.scan_text("正常な日本語の文章です。\n2行目。") == []


def test_scan_finds_replacement_char():
    issues = mod.scan_text("正常です�ここが化け")
    assert len(issues) == 1
    assert issues[0]["kind"] == "replacement"
    assert issues[0]["line"] == 1


def test_scan_finds_control_char():
    issues = mod.scan_text("abc\x07def")
    assert any(i["kind"] == "control" for i in issues)


def test_scan_finds_halfwidth_run():
    issues = mod.scan_text("正常ｱｲｳｴｵｶｷｸｹｺｻです")
    assert any(i["kind"] == "halfwidth-run" for i in issues)


def test_scan_finds_midline_tab_but_not_indent():
    issues = mod.scan_text("spec に、\truth は UUID")
    assert any(i["kind"] == "tab-in-prose" for i in issues)
    assert mod.scan_text("\tindented code") == []


def test_scan_positions_are_1_based():
    issues = mod.scan_text("one\ntwo�x")
    assert issues[0]["line"] == 2
    assert issues[0]["col"] == 4


def test_card_phrases_fit_limit():
    cards = mod.review_cards()
    assert isinstance(cards, list)
    for card in cards:
        assert card.get("phrase"), f"{card.get('id')} に phrase がない"
        assert len(card["phrase"]) <= 120, f"{card.get('id')} の phrase が長すぎる"
        assert not card.get("command"), f"{card.get('id')} に command がある"


def test_review_summary_shape():
    summary = mod.review_summary()
    assert "docs" in summary
    assert "changelog" in summary
    assert "readme" in summary
    assert "prs" in summary
    assert "cards" in summary
    assert summary["changelog"]["last_entry"] is not None


def test_changelog_entry_date_parsed():
    fresh = mod.changelog_freshness()
    assert fresh["exists"] is True
    assert fresh["last_entry"] is not None
    assert isinstance(fresh["commits_since"], int)
