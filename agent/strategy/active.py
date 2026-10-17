import os

from .specialists import baseline, default, escort_hunt

ACTIVE_SPECIALIST = "baseline"

_SPECIALISTS = {
    "default": default,
    "baseline": baseline,
    "escort_hunt": escort_hunt,  # ローカル評価用の実験（提出ゲート対象外）
}

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_PATH = os.path.join(_ROOT, "config.json")


def get_active_specialist(args={}):
    name = ACTIVE_SPECIALIST
    if isinstance(args, dict):
        name = args.get("specialist", ACTIVE_SPECIALIST)
    return _SPECIALISTS[name]


def get_agent_class(args={}):
    return get_active_specialist(args).get_agent_class(args)


def get_agent_model_config(args={}):
    return get_active_specialist(args).get_model_config(args)


def is_single_asset(args={}):
    return True


def get_policy(args={}):
    return get_active_specialist(args).get_policy(args)
