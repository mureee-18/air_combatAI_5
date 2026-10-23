"""H2: hybrid V6 のまま、プリセットで maArgs.fireRangeKm（MA ディフェンダーの対戦闘機射程）だけを変える。"""
from ...specialists.hybrid import HybridPolicy, get_agent_class, get_model_config  # noqa: F401


def get_policy(args={}):
    return HybridPolicy(args)
