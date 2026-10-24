import importlib
import os

ACTIVE_SPECIALIST = "baseline"

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_CONFIG_PATH = os.path.join(_ROOT, "config.json")
_KINDS = ("specialists", "ideas")
_LOADED = {}


def _discover():
    """名前 -> [(kind, 相対パス)]。specialists/<name>.py と ideas/<name>/__init__.py をファイル名だけで集める。"""
    found = {}
    for kind in _KINDS:
        base = os.path.join(_HERE, kind)
        if not os.path.isdir(base):
            continue
        for entry in sorted(os.listdir(base)):
            if entry.startswith("_"):
                continue
            if kind == "specialists":
                if not entry.endswith(".py"):
                    continue
                name, rel = entry[:-3], f"strategy/{kind}/{entry}"
            else:
                if not os.path.isfile(os.path.join(base, entry, "__init__.py")):
                    continue
                name, rel = entry, f"strategy/{kind}/{entry}/__init__.py"
            found.setdefault(name, []).append((kind, rel))
    clashes = {name: [rel for _, rel in hits] for name, hits in found.items() if len(hits) > 1}
    if clashes:
        raise ImportError(f"specialist name clash: {clashes}")
    return {name: hits[0] for name, hits in found.items()}


_REGISTRY = _discover()


def available_specialists():
    return sorted(_REGISTRY)


def get_active_specialist(args={}):
    name = ACTIVE_SPECIALIST
    if isinstance(args, dict):
        name = args.get("specialist", ACTIVE_SPECIALIST)
    module = _LOADED.get(name)
    if module is None:
        kind, _ = _REGISTRY[name]
        module = _LOADED[name] = importlib.import_module(f".{kind}.{name}", __package__)
    return module


def get_agent_class(args={}):
    return get_active_specialist(args).get_agent_class(args)


def get_agent_model_config(args={}):
    return get_active_specialist(args).get_model_config(args)


def is_single_asset(args={}):
    return True


def get_policy(args={}):
    return get_active_specialist(args).get_policy(args)
