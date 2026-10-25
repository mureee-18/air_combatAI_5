import json
import subprocess
import sys
import zipfile
from pathlib import Path

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
