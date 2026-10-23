import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ni = _load("new_idea")
cl = _load("changelog")


def _repo(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "agent" / "strategy" / "ideas" / "_template",
                    root / "agent" / "strategy" / "ideas" / "_template")
    (root / "agent" / "presets").mkdir(parents=True)
    shutil.copy(REPO_ROOT / "agent" / "args.json", root / "agent" / "args.json")
    return root


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _git_repo(tmp_path):
    root = _repo(tmp_path)
    _git(root, "init", "-q", "-b", "master")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "base")
    return root


def _commit(root, msg):
    _git(root, "add", "-A")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg)


def test_create_writes_idea_dir_and_preset(tmp_path):
    root = _repo(tmp_path)
    assert ni.create("hosyan", "rushguard", root, branches=[]) == "hosyan_rushguard"
    assert (root / "agent/strategy/ideas/hosyan_rushguard/__init__.py").exists()
    preset = json.loads((root / "agent/presets/hosyan_rushguard.json").read_text(encoding="utf-8"))
    args = json.loads((root / "agent/args.json").read_text(encoding="utf-8"))
    assert preset == {**args, "specialist": "hosyan_rushguard"}


@pytest.mark.parametrize("author,name", [("Hosyan", "x"), ("hosyan", "rush-guard"), ("", "x"), ("ho_syan", "x")])
def test_create_rejects_bad_names(tmp_path, author, name):
    with pytest.raises(SystemExit, match="lowercase letters and digits"):
        ni.create(author, name, _repo(tmp_path), branches=[])


def test_create_refuses_local_collision(tmp_path):
    root = _repo(tmp_path)
    ni.create("hosyan", "rushguard", root, branches=[])
    with pytest.raises(SystemExit, match="already exists"):
        ni.create("hosyan", "rushguard", root, branches=[])


def test_create_refuses_remote_branch_and_names_it(tmp_path):
    root = _repo(tmp_path)
    with pytest.raises(SystemExit, match="remote branch idea/hosyan/rushguard exists"):
        ni.create("hosyan", "rushguard", root, branches=["master", "idea/hosyan/rushguard"])
    assert not (root / "agent/strategy/ideas/hosyan_rushguard").exists()


def test_ci_rule_idea_without_prefix_fails(tmp_path):
    root = _git_repo(tmp_path)
    shutil.copytree(root / "agent/strategy/ideas/_template", root / "agent/strategy/ideas/rushguard")
    _commit(root, "idea")
    errors = ni.check("master~1", root)
    assert any("'rushguard' must be named <author>_<name>" in e for e in errors)


def test_ci_rule_idea_pr_must_add_a_run(tmp_path):
    root = _git_repo(tmp_path)
    ni.create("hosyan", "rushguard", root, branches=[])
    _commit(root, "idea")
    errors = ni.check("master~1", root)
    assert errors == ["idea 'hosyan_rushguard' has no complete run under results/runs/; "
                      "run scripts/eval_pool.py --preset hosyan_rushguard and commit the run in this PR"]
    run = root / "results/runs/r1"
    run.mkdir(parents=True)
    (run / "manifest.json").write_text(json.dumps({"status": "running", "candidate": {"name": "hosyan_rushguard"}}))
    _commit(root, "running run")
    assert ni.check("master~2", root) == errors
    (run / "manifest.json").write_text(json.dumps({"status": "complete", "candidate": {"name": "hosyan_rushguard"}}))
    _commit(root, "complete run")
    assert ni.check("master~3", root) == []


def test_ci_rule_ignores_prs_without_ideas(tmp_path):
    root = _git_repo(tmp_path)
    (root / "README.md").write_text("x")
    _commit(root, "docs")
    assert ni.check("master~1", root) == []


def test_changelog_keeps_every_existing_entry_and_is_stable(tmp_path):
    old = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(old, encoding="utf-8")
    frags = tmp_path / "changelog.d"
    frags.mkdir()
    (frags / "README.md").write_text("not a fragment")
    (frags / "2026-10-24-a-x.md").write_text("### A\n\n- a\n")
    (frags / "2026-10-24-b-y.md").write_text("### B\n\n- b\n")
    (frags / "2026-10-23-c-z.md").write_text("### C\n\n- c\n")
    assert cl.main(["--root", str(tmp_path)]) == 0
    new = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    body = old.split("\n", 1)[1].strip()
    assert body in new
    for heading in ("## 2026-10-24", "### A", "### B", "### C", "## 2026-10-23"):
        assert heading in new
    assert new.index("## 2026-10-24") < new.index("### A") < new.index("### B") < new.index("### C")
    assert "not a fragment" not in new
    assert cl.main(["--root", str(tmp_path), "--check"]) == 0
    assert cl.main(["--root", str(tmp_path)]) == 0
    assert (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8") == new
    (frags / "2026-10-25-d-w.md").write_text("### D\n")
    assert cl.main(["--root", str(tmp_path), "--check"]) == 1
