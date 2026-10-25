"""H9 red tune: hybrid V6 の引数を、自分が Red 陣営のときだけ redArgs で上書きする。

V6 は Red で Blue より 0.07〜0.17 弱く（seeds 1-60: O_RUSH .508/.643, BM .554/.650, O_GUARD .623/.692）、
Red では自陣の護衛対象機を落とされる回数が約2倍。H7（回避角）や H8（目標分割）でも Red と Blue で
効き方が逆になることが多かったので、色ごとに別の引数を持たせる。
陣営は agentFullName の先頭（"Red" / "Blue"）で判定する。どちらでもない名前なら上書きしない。
redArgs が空（既定）なら V6 と同じ動き。blueArgs も同じ形で使える。
環境変数 H9_LOG=<file> があれば、判定した陣営を1行書き出す（挙動は変えない）。
"""
import os

from ...specialists.hybrid import HybridPolicy, _slot, get_agent_class, get_model_config  # noqa: F401


def get_policy(args={}):
    return ColorTunePolicy(args)


def _color(agentFullName):
    s = str(agentFullName)
    for c in ("Red", "Blue"):
        if s.startswith(c):
            return c
    return None


class ColorTunePolicy(HybridPolicy):
    def __init__(self, args={}):
        a = dict(args) if isinstance(args, dict) else {}
        over = {"Red": a.pop("redArgs", None) or {}, "Blue": a.pop("blueArgs", None) or {}}
        super().__init__(a)
        self._alt = {}
        for c, o in over.items():
            if o:
                b = dict(a)
                b.update(o)
                self._alt[c] = HybridPolicy(b)
        self._logged = False

    def step(self, observation, reward, done, info, agentFullName, observation_space, action_space):
        c = _color(agentFullName)
        log = os.environ.get("H9_LOG")
        if log and not self._logged:
            self._logged = True
            with open(log, "a") as f:
                f.write(f"{agentFullName}\t{c}\t{c in self._alt}\n")
        p = self._alt.get(c)
        if p is not None:
            return p.step(observation, reward, done, info, agentFullName, observation_space, action_space)
        return super().step(observation, reward, done, info, agentFullName, observation_space, action_space)
