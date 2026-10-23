import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GATE = REPO_ROOT / "tools" / "hooks" / "pre_submit_gate.py"
BUILD = REPO_ROOT / "scripts" / "build_submission.py"


@pytest.fixture(scope="module", autouse=True)
def _built_package():
    subprocess.run([sys.executable, str(BUILD)], cwd=str(REPO_ROOT), check=True, capture_output=True)


def _run(command: str, env_confirm: bool):
    env = {"PATH": __import__("os").environ.get("PATH", "")}
    if env_confirm:
        env["ATLA5_SUBMIT_CONFIRM"] = "1"
    return subprocess.run(
        [sys.executable, str(GATE), "--command", command],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def test_blocks_without_confirmation():
    result = _run("signate submit --task_key=x --path=submission/submit.zip", env_confirm=False)
    assert result.returncode == 1
    assert "ATLA5_SUBMIT_CONFIRM" in result.stdout


def test_accepts_confirmation_in_command_string():
    result = _run("ATLA5_SUBMIT_CONFIRM=1 signate submit --path=submission/submit.zip", env_confirm=False)
    assert result.returncode == 0, result.stdout + result.stderr


def test_accepts_confirmation_via_env():
    result = _run("signate submit --path=submission/submit.zip", env_confirm=True)
    assert result.returncode == 0, result.stdout + result.stderr


def _build(*extra: str):
    subprocess.run([sys.executable, str(BUILD), *extra], cwd=str(REPO_ROOT), check=True, capture_output=True)


def test_accepts_hybrid_v6_preset_zip():
    try:
        _build("--args", "agent/presets/hybrid_v6.json")
        result = _run("signate submit --path=submission/submit.zip", env_confirm=True)
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        _build()


def test_blocks_zip_with_local_only_specialist(tmp_path):
    preset = tmp_path / "escort_hunt.json"
    preset.write_text('{"type": "Fixed", "specialist": "escort_hunt"}', encoding="utf-8")
    try:
        _build("--args", str(preset))
        result = _run("signate submit --path=submission/submit.zip", env_confirm=True)
        assert result.returncode == 1
        assert "escort_hunt" in result.stdout
    finally:
        _build()


def test_blocks_zip_whose_specialist_no_preset_names(tmp_path):
    preset = tmp_path / "unlisted.json"
    preset.write_text('{"type": "Fixed", "specialist": "ma_default"}', encoding="utf-8")
    try:
        _build("--args", str(preset))
        result = _run("signate submit --path=submission/submit.zip", env_confirm=True)
        assert result.returncode == 1
        assert "ma_default" in result.stdout
    finally:
        _build()


def test_submittable_specialists_come_from_args_and_presets():
    sys.path.insert(0, str(GATE.parent))
    try:
        import pre_submit_gate
    finally:
        sys.path.remove(str(GATE.parent))
    import json

    names = pre_submit_gate.submittable_specialists()
    named = [REPO_ROOT / "agent" / "args.json", *(REPO_ROOT / "agent" / "presets").glob("*.json")]
    assert {json.loads(p.read_text(encoding="utf-8"))["specialist"] for p in named} == names
    assert "escort_hunt" not in names
