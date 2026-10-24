import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "build_submission.py"
ZIP_PATH = REPO_ROOT / "submission" / "submit.zip"

REQUIRED_ENTRIES = ["__init__.py", "args.json", "config.json"]


def test_build_submission_creates_required_entries():
    result = subprocess.run([sys.executable, str(SCRIPT)], cwd=str(REPO_ROOT), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    assert ZIP_PATH.exists()
    with zipfile.ZipFile(ZIP_PATH) as z:
        names = z.namelist()

    for entry in REQUIRED_ENTRIES:
        assert entry in names, f"missing entry: {entry}"

    assert any(name.startswith("strategy/") for name in names)
    assert not any("__pycache__" in name for name in names)
    assert not any(name.endswith(".pyc") for name in names)


def test_built_args_json_declares_allowed_specialist():
    with zipfile.ZipFile(ZIP_PATH) as z:
        args = json.loads(z.read("args.json"))

    assert "specialist" in args
    assert args["specialist"] in {"baseline", "default", "hybrid"}


def test_build_with_hybrid_v6_preset_overrides_args_only_in_zip():
    preset = REPO_ROOT / "agent" / "presets" / "hybrid_v6.json"
    original_args = (REPO_ROOT / "agent" / "args.json").read_text(encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--args", "agent/presets/hybrid_v6.json"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        with zipfile.ZipFile(ZIP_PATH) as z:
            args = json.loads(z.read("args.json"))
            names = z.namelist()
        assert args == json.loads(preset.read_text(encoding="utf-8"))
        assert args["specialist"] == "hybrid"
        assert "strategy/specialists/hybrid.py" in names
        assert not any(name.startswith("presets/") for name in names)
        # 既定の agent/args.json は変更しない
        assert (REPO_ROOT / "agent" / "args.json").read_text(encoding="utf-8") == original_args
    finally:
        subprocess.run([sys.executable, str(SCRIPT)], cwd=str(REPO_ROOT), check=True, capture_output=True)


def _zip_entries(path):
    with zipfile.ZipFile(path) as z:
        return {name: z.read(name) for name in z.namelist()}


def test_build_with_out_leaves_submission_untouched(tmp_path):
    subprocess.run([sys.executable, str(SCRIPT)], cwd=str(REPO_ROOT), check=True, capture_output=True)
    before = ZIP_PATH.read_bytes()
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--preset", "hybrid_v6", "--out", str(tmp_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert f"built: {tmp_path / 'submit.zip'}" in result.stdout
    assert (tmp_path / "MyAgent" / "args.json").exists()
    assert ZIP_PATH.read_bytes() == before


def test_preset_name_matches_args_path(tmp_path):
    by_name, by_path = tmp_path / "name", tmp_path / "path"
    for out, flags in ((by_name, ["--preset", "hybrid_v6"]), (by_path, ["--args", "agent/presets/hybrid_v6.json"])):
        cmd = [sys.executable, str(SCRIPT), *flags, "--out", str(out)]
        subprocess.run(cmd, cwd=str(REPO_ROOT), check=True, capture_output=True)
    assert _zip_entries(by_name / "submit.zip") == _zip_entries(by_path / "submit.zip")


def test_unknown_preset_names_the_missing_file(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--preset", "does_not_exist", "--out", str(tmp_path)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "agent/presets/does_not_exist.json" in result.stderr


def _load_build_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_submission", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRESETS = sorted((REPO_ROOT / "agent" / "presets").glob("*.json"))


@pytest.mark.parametrize("preset", [None, *PRESETS], ids=lambda p: "default" if p is None else p.stem)
def test_zip_ships_only_the_import_closure(tmp_path, preset):
    build = _load_build_module()
    flags = ["--args", str(preset)] if preset else []
    subprocess.run([sys.executable, str(SCRIPT), *flags, "--out", str(tmp_path)], cwd=str(REPO_ROOT), check=True)
    args_file = preset or REPO_ROOT / "agent" / "args.json"
    specialist = json.loads(args_file.read_text(encoding="utf-8"))["specialist"]
    with zipfile.ZipFile(tmp_path / "submit.zip") as z:
        names = sorted(z.namelist())
    assert names == sorted(REQUIRED_ENTRIES + build.import_closure(specialist))


def test_default_zip_leaves_out_unused_specialists(tmp_path):
    subprocess.run([sys.executable, str(SCRIPT), "--out", str(tmp_path)], cwd=str(REPO_ROOT), check=True)
    with zipfile.ZipFile(tmp_path / "submit.zip") as z:
        names = set(z.namelist())
    needed = {"strategy/specialists/default.py", "strategy/agents/escort_hunter.py", "strategy/agents/escort_id.py"}
    assert needed <= names
    assert "strategy/specialists/hybrid.py" not in names


def test_idea_ships_its_sibling_module_and_data(tmp_path):
    build = _load_build_module()
    agent = tmp_path / "agent"
    shutil.copytree(REPO_ROOT / "agent", agent, ignore=shutil.ignore_patterns("__pycache__"))
    idea = agent / "strategy" / "ideas" / "hosyan_probe"
    idea.mkdir()
    (idea / "__init__.py").write_text("from .policy import get_policy  # noqa: F401\n", encoding="utf-8")
    sibling = "from ...agents.escort_id import EscortIdentifier  # noqa: F401\n"
    (idea / "policy.py").write_text(sibling, encoding="utf-8")
    (idea / "config.json").write_text("{}", encoding="utf-8")
    files = build.import_closure("hosyan_probe", agent)
    assert "strategy/ideas/__init__.py" in files
    assert "strategy/ideas/hosyan_probe/policy.py" in files
    assert "strategy/ideas/hosyan_probe/config.json" in files
    assert "strategy/agents/escort_id.py" in files
    assert "strategy/specialists/hybrid.py" not in files
