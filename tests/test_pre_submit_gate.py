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
