import ast
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ACTIVE_PY = REPO_ROOT / "agent" / "strategy" / "active.py"
SPECIALISTS_DIR = REPO_ROOT / "agent" / "strategy" / "specialists"
ARGS_PATH = REPO_ROOT / "agent" / "args.json"
CONFIG_PATH = REPO_ROOT / "agent" / "config.json"

SPECIALIST_CONFIG_KEYS = {"default": "Fixed", "baseline": "Baseline"}


def _specialist_registry():
    tree = ast.parse(ACTIVE_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "_SPECIALISTS" in targets and isinstance(node.value, ast.Dict):
                return {key.value: value.id for key, value in zip(node.value.keys, node.value.values)}
    raise AssertionError("_SPECIALISTS が見つかりません")


def test_registry_covers_existing_specialist_modules():
    registry = _specialist_registry()
    for name in registry:
        assert (SPECIALISTS_DIR / f"{name}.py").exists(), f"specialist module missing: {name}"


def test_active_specialist_is_registered():
    registry = _specialist_registry()
    args = json.loads(ARGS_PATH.read_text(encoding="utf-8"))
    assert args.get("specialist") in registry


def test_config_has_section_for_active_specialist():
    args = json.loads(ARGS_PATH.read_text(encoding="utf-8"))
    configs = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    specialist = args["specialist"]
    section = SPECIALIST_CONFIG_KEYS[specialist]
    assert section in configs
