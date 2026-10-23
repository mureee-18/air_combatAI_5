"""H2b: hybrid V6 + 突撃を検知したときだけ MA ディフェンダーの対戦闘機射程を 45km にする（H2 r45 を条件付きにしたもの）。

突撃の判定（4機で共有するラッチ）:
  1. 自機の観測で見えている敵戦闘機（護衛対象機を除く）のうち、x < rushLineXKm のものを集める。
  2. どれか1機を中心に rushClusterKm 以内に rushMinCount 機以上いれば「固まって前進する集団」とみなす。
  3. これを試合開始から rushWindowS 秒以内に見たら突撃モードに入り、rushHoldS 秒（既定は試合終了まで）保持する。
O_RUSH（4機で直行）は最初に見えた時点で3〜4機が10km程度に固まっている。EH（2機が外回り）や
O_GUARD（1機攻撃・3機は自陣で哨戒）は序盤に固まった3機が見えないので、突撃と判定しない。
突撃モード中は MA ディフェンダーの fireRangeKm を rushRangeKm にする。
検知しない間は maArgs.fireRangeKm（V6 は 50）のままで、V6 と同じ動きになる。

args: rushMinCount (3), rushClusterKm (15), rushLineXKm (60), rushWindowS (300), rushRangeKm (45), rushHoldS (1e9)
環境変数 RUSH_LOG=<dir> があれば、ラッチした時刻を診断用に書き出す（挙動は変えない）。
"""
import copy
import json
import math
import os
import sys

from ...specialists.hybrid import HybridPolicy, get_agent_class, get_model_config  # noqa: F401
from ...specialists.ma_default import DefaultPolicy


def get_policy(args={}):
    return RushRangePolicy(args)


class RushRangePolicy(HybridPolicy):
    def __init__(self, args={}):
        super().__init__(args)
        a = args if isinstance(args, dict) else {}
        self.rushMinCount = int(a.get("rushMinCount", 3))
        self.rushClusterKm = float(a.get("rushClusterKm", 15.0))
        self.rushLineXKm = float(a.get("rushLineXKm", 60.0))
        self.rushWindowS = float(a.get("rushWindowS", 300.0))
        self.rushRangeKm = float(a.get("rushRangeKm", 45.0))
        self.rushHoldS = float(a.get("rushHoldS", 1e9))
        self.normalRangeKm = float(self.maArgs.get("fireRangeKm", 50.0))
        self._rt = {}
        self._rushUntil = -1.0
        self._log = os.environ.get("RUSH_LOG")

    def _now(self):
        return max(self._rt.values()) if self._rt else 0

    def _clusterCount(self, observation):
        """x < rushLineXKm の敵戦闘機について、1機を中心に rushClusterKm 以内にいる機数の最大。"""
        own = observation["own"]
        enemy = observation["enemy"]
        ox, oy = float(own[0]), float(own[1])
        pts = []
        for i in range(enemy.shape[0]):
            if enemy[i, 0] < 0.5 or enemy[i, 4] > 0.5:
                continue
            b = math.radians(float(enemy[i, 1]))
            x = ox + float(enemy[i, 2]) * math.cos(b)
            if x < self.rushLineXKm:
                pts.append((x, oy + float(enemy[i, 2]) * math.sin(b)))
        return max((sum(1 for q in pts if math.dist(p, q) <= self.rushClusterKm) for p in pts), default=0)

    def rushActive(self):
        return self._now() < self._rushUntil

    def step(self, observation, reward, done, info, agentFullName, observation_space, action_space):
        self._rt[agentFullName] = self._rt.get(agentFullName, 0) + 1
        if self._rushUntil < 0 and self._now() <= self.rushWindowS:
            n = self._clusterCount(observation)
            if n >= self.rushMinCount:
                self._rushUntil = self._now() + self.rushHoldS
                if self._log:
                    self._diag(n)
        return super().step(observation, reward, done, info, agentFullName, observation_space, action_space)

    def _maStep(self, observation, reward, done, info, agentFullName, observation_space, action_space):
        # 親（hybrid）の _maStep と同じ。違いは射程を毎回決めることだけ（未検知なら V6 の値のまま）
        p = self.ma.get(agentFullName)
        if p is None:
            p = self.ma[agentFullName] = DefaultPolicy(copy.deepcopy(self.maArgs))
        p.fireRangeKm = self.rushRangeKm if self.rushActive() else self.normalRangeKm
        obs = {"own": observation["own"], "enemy": observation["enemy"], "threat": observation["threat"]}
        return p.step(obs, reward, done, info, agentFullName, observation_space, action_space)

    def _diag(self, n):
        try:
            spec = json.loads(sys.argv[-1]) if len(sys.argv) > 2 and sys.argv[-2] == "_game" else {}
        except ValueError:
            spec = {}
        tag = f"{os.path.basename(str(spec.get('opp', '?')))[4:]}\t{spec.get('color', '?')}\t{spec.get('seed', '?')}"
        os.makedirs(self._log, exist_ok=True)
        with open(os.path.join(self._log, "latch.tsv"), "a") as f:
            f.write(f"{tag}\t{self._now()}\t{n}\t{self.rushMinCount}\t{self.rushClusterKm}\t{self.rushWindowS}\n")
