"""hybrid: escort_hunt のアタッカー（IRST 識別・外回り）+ MA版の反撃/温存ロジックを組み合わせる実験 specialist.

defPolicy:
  "eh" : 従来の escort_hunt ディフェンダー（x=-60km 付近で哨戒・迎撃）
  "ma" : MA版 DefaultPolicy（前進して最寄りの敵戦闘機に反撃、護衛対象機用に N 発温存）
maArgs: MA版ポリシーへ渡す引数（既定は MA 提出版の args.json 相当、速度フィルタのみ無効）
defLeashXKm: ma ディフェンダーがこの x を越えたら自陣側へ戻る（None=制限なし）
guardCount: 側面突破機（flanker）を検知したら、ma ディフェンダーのうち guardCount 機を
  escort_hunt のディフェンダー（自陣哨戒・侵入機優先迎撃）に切り替える（0=無効）
  flanker = 自陣側 x < flankXKm かつ |y| > flankYKm、または x < deepXKm の敵戦闘機。guardHoldS 秒保持。
"""
import copy
import math

from .escort_hunt import EscortHuntPolicy, get_agent_class, get_model_config, _slot  # noqa: F401
from .ma_default import DefaultPolicy

MA_ARGS = {
    "fireRangeKm": 50.0, "breakRangeKm": 35.0, "evadeCrankDeg": 0.0, "marginKm": 25.0,
    "trackConfirmFrames": 0, "targetSpread": 0, "escortSeekDistKm": 150, "escortForwardXKm": 110,
    "escortFireEnable": 1, "escortFireMaxDistKm": 0.0, "escortMaxSpeedKmps": 0.0,
    "escortAmmoHold": 0, "escortNoBeam": 1,
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
        self.guardCount = int(a.get("guardCount", 0))
        self.flankXKm = float(a.get("flankXKm", -20.0))
        self.flankYKmDet = float(a.get("flankYKmDet", 60.0))
        self.deepXKm = float(a.get("deepXKm", -60.0))
        self.guardHoldS = float(a.get("guardHoldS", 120.0))
        # guardScale=1: 侵入機数に応じて guard 機数を増やす（1機侵入→1機、2機以上→guardCount 機）
        self.guardScale = int(a.get("guardScale", 0))
        self._guardUntil = {}
        self._tick = {}

    def _flankerSeen(self, observation):
        return self._flankerCount(observation) > 0

    def _flankerCount(self, observation):
        own = observation["own"]
        enemy = observation["enemy"]
        ox, oy = float(own[0]), float(own[1])
        n = 0
        for i in range(enemy.shape[0]):
            if enemy[i, 0] < 0.5 or enemy[i, 4] > 0.5:
                continue
            b = math.radians(float(enemy[i, 1]))
            x = ox + float(enemy[i, 2]) * math.cos(b)
            y = oy + float(enemy[i, 2]) * math.sin(b)
            if (x < self.flankXKm and abs(y) > self.flankYKmDet) or x < self.deepXKm:
                n += 1
        return n

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
        if not isAttacker and mode == "ma" and self.guardCount > 0:
            t = self._tick[agentFullName] = self._tick.get(agentFullName, 0) + 1
            defs = sorted(s_ for s_ in (1, 2, 3, 4) if s_ not in self.attackerSlots)
            nIntr = self._flankerCount(observation)
            if self.guardScale > 0:
                # 侵入機数は各機の観測で異なるため、直近の最大値を共有して使う
                self._lastIntr = max(nIntr, getattr(self, "_lastIntr", 0)) if nIntr else nIntr
                k = min(self.guardCount, max(1, self._lastIntr))
            else:
                k = self.guardCount
            guards = defs[::-1][:k]   # 後ろのスロットから guard 役
            if slot in guards:
                if nIntr > 0:
                    self._guardUntil[agentFullName] = t + self.guardHoldS
                if t < self._guardUntil.get(agentFullName, -1):
                    mode = "eh"
        if mode != "ma":
            return super().step(observation, reward, done, info, agentFullName, observation_space, action_space)
        act = self._maStep(observation, reward, done, info, agentFullName, observation_space, action_space)
        own = observation["own"]
        if self.defLeashXKm is not None and float(own[0]) > self.defLeashXKm and observation["threat"][0] < 0.5:
            numTurn = int(action_space["turn"].n)
            py = self.defendY * (1 if own[1] >= 0 else -1)
            az = math.degrees(math.atan2(py - float(own[1]), self.defendX - float(own[0])))
            act = dict(act)
            act["turn"] = self._turnIndex(self._bounds(own, az), numTurn)
        return act
