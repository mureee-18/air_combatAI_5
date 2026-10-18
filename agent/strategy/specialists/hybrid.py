"""hybrid: escort_hunt のアタッカー（IRST 識別・外回り）+ MA版の反撃/温存ロジックを組み合わせる実験 specialist.

defPolicy:
  "eh" : 従来の escort_hunt ディフェンダー（x=-60km 付近で哨戒・迎撃）
  "ma" : MA版 DefaultPolicy（前進して最寄りの敵戦闘機に反撃、護衛対象機用に N 発温存）
maArgs: MA版ポリシーへ渡す引数（既定は MA 提出版の args.json 相当、速度フィルタのみ無効）
defLeashXKm: ma ディフェンダーがこの x を越えたら自陣側へ戻る（None=制限なし）
"""
import copy
import math

from . import escort_hunt
from .escort_hunt import EscortHuntPolicy, get_agent_class, get_model_config, _slot  # noqa: F401
from .ma_default import DefaultPolicy

MA_ARGS = {
    "fireRangeKm": 50.0, "breakRangeKm": 35.0, "evadeCrankDeg": 0.0, "marginKm": 25.0,
    "trackConfirmFrames": 0, "targetSpread": 0, "escortSeekDistKm": 150, "escortForwardXKm": 110,
    "escortFireMode": 1, "escortMaxSpeedKmps": 0.0, "escortAmmoHold": 0, "escortNoBeam": 1,
    "escortIgnoreBreak": 1, "escortReserveMsls": 3, "beamHoldWhileArmed": 0, "beamHoldFrames": 0,
    "fireAlignDeg": 0, "launchIntervalFrames": 0,
}


def get_policy(args={}):
    return HybridPolicy(args)


class HybridPolicy(EscortHuntPolicy):
    def __init__(self, args={}):
        super().__init__(args)
        a = args if isinstance(args, dict) else {}
        self.defPolicy = str(a.get("defPolicy", "ma"))
        self.atkPolicy = str(a.get("atkPolicy", "eh"))
        ma = dict(MA_ARGS)
        ma.update(a.get("maArgs", {}) or {})
        self.ma = {}
        self.maArgs = ma
        lx = a.get("defLeashXKm", None)
        self.defLeashXKm = float(lx) if lx is not None else None

    def _maStep(self, observation, reward, done, info, agentFullName, observation_space, action_space):
        p = self.ma.get(agentFullName)
        if p is None:
            p = self.ma[agentFullName] = DefaultPolicy(copy.deepcopy(self.maArgs))
        obs = {"own": observation["own"], "enemy": observation["enemy"], "threat": observation["threat"]}
        return p.step(obs, reward, done, info, agentFullName, observation_space, action_space)

    def step(self, observation, reward, done, info, agentFullName, observation_space, action_space):
        slot = _slot(agentFullName)
        isAttacker = slot in self.attackerSlots
        mode = self.atkPolicy if isAttacker else self.defPolicy
        if mode != "ma":
            return super().step(observation, reward, done, info, agentFullName, observation_space, action_space)
        act = self._maStep(observation, reward, done, info, agentFullName, observation_space, action_space)
        own = observation["own"]
        if self.defLeashXKm is not None and float(own[0]) > self.defLeashXKm and observation["threat"][0] < 0.5:
            numTurn = int(action_space["turn"].n)
            az = math.degrees(math.atan2(self.defendY * (1 if own[1] >= 0 else -1) - float(own[1]), self.defendX - float(own[0])))
            act = dict(act)
            act["turn"] = self._turnIndex(self._bounds(own, az), numTurn)
        return act
