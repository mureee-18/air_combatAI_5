import importlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_DIR = REPO_ROOT / "agent" / "strategy"
ARGS_PATH = REPO_ROOT / "agent" / "args.json"
CONFIG_PATH = REPO_ROOT / "agent" / "config.json"

SPECIALIST_CONFIG_KEYS = {"default": "Fixed", "baseline": "Baseline", "escort_hunt": "EscortHunt"}


def _load_active(strategy_dir: Path, package: str):
    """strategy_dir のコピーを package 名で読み込み、active モジュールを返す（ASRCAISim1 は読まない）。"""
    root = strategy_dir.parent
    sys.path.insert(0, str(root.parent))
    try:
        for name in [m for m in sys.modules if m == package or m.startswith(package + ".")]:
            del sys.modules[name]
        return importlib.import_module(f"{package}.strategy.active")
    finally:
        sys.path.remove(str(root.parent))


def _copy_agent(tmp_path: Path, package: str) -> Path:
    dest = tmp_path / package
    shutil.copytree(REPO_ROOT / "agent", dest, ignore=shutil.ignore_patterns("__pycache__", "presets"))
    return dest / "strategy"


def test_discovers_existing_specialists_without_simulator():
    from agent.strategy import active

    assert active.available_specialists() == ["baseline", "default", "escort_hunt", "hybrid", "ma_default"]
    assert "ASRCAISim1" not in sys.modules


def test_active_specialist_is_discovered():
    from agent.strategy import active

    args = json.loads(ARGS_PATH.read_text(encoding="utf-8"))
    assert args.get("specialist") in active.available_specialists()


def test_every_preset_names_a_discovered_specialist():
    from agent.strategy import active

    for preset in sorted((REPO_ROOT / "agent" / "presets").glob("*.json")):
        specialist = json.loads(preset.read_text(encoding="utf-8")).get("specialist")
        assert specialist in active.available_specialists(), preset.name


def test_idea_directory_is_discovered_and_underscore_skipped(tmp_path):
    strategy = _copy_agent(tmp_path, "agent_idea_probe")
    shutil.copytree(strategy / "ideas" / "_template", strategy / "ideas" / "hosyan_probe")
    (strategy / "specialists" / "_private.py").write_text("", encoding="utf-8")
    active = _load_active(strategy, "agent_idea_probe")
    names = active.available_specialists()
    assert "hosyan_probe" in names
    assert "_template" not in names and "_private" not in names
    assert active._REGISTRY["hosyan_probe"] == ("ideas", "strategy/ideas/hosyan_probe/__init__.py")


def test_name_clash_between_specialists_and_ideas_fails_with_both_paths(tmp_path):
    strategy = _copy_agent(tmp_path, "agent_clash_probe")
    shutil.copytree(strategy / "ideas" / "_template", strategy / "ideas" / "default")
    with pytest.raises(ImportError) as err:
        _load_active(strategy, "agent_clash_probe")
    assert "strategy/specialists/default.py" in str(err.value)
    assert "strategy/ideas/default/__init__.py" in str(err.value)


def test_config_has_section_for_active_specialist():
    args = json.loads(ARGS_PATH.read_text(encoding="utf-8"))
    configs = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    specialist = args["specialist"]
    section = SPECIALIST_CONFIG_KEYS[specialist]
    assert section in configs
