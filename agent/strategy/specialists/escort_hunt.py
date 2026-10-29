"""escort_hunt: 敵護衛対象機を狙う役割分担型の方針（ローカル評価用の実験 specialist）.

- アタッカー（attackerSlots の2機）: 外側を回って IRST/レーダで識別した敵護衛対象機に
  先回りし、escortFireKm 以内で1発ずつ（escortShotIntervalS 間隔）撃ってから横に逃げる（ビーム）。
- ディフェンダー（残り2機）: 自陣側の哨戒点に留まり、近づく敵戦闘機を目標を分担して迎撃する。
  距離が詰まったら背を向けずにクランク／ビーム。
- 被弾警報中は全機が最高速で回避。既定は警報方位の真後ろ（evadeOffsetDeg=180）。
  ビーム回避（100° / 135°）は seed1-4×両面で生存が悪く（全滅が増えた）、真後ろ＋最高速が最良だった。
- 同時発射を抑える（config の maxSimulShot と、自機ごとの発射間隔）。
"""

import math

import numpy as np

from ASRCAISim1.policy import StandalonePolicy

from ..agents.escort_hunter import EscortHunterAgent
from ..observation import racetrack_intercept


def get_agent_class(args={}):
    return EscortHunterAgent


def get_policy(args={}):
    return EscortHuntPolicy(args)


def get_model_config(args={}):
    import json
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")
    with open(path) as f:
        configs = json.load(f)
    return configs.get("EscortHunt", configs.get("Fixed", {}))


def _wrap(az):
    return (az + 180.0) % 360.0 - 180.0


def _slot(agentFullName):
    try:
        return int(str(agentFullName).split(":")[0].split("_")[-1])
    except (ValueError, IndexError):
        return 1


class EscortHuntPolicy(StandalonePolicy):
    def __init__(self, args={}):
        super().__init__()
        a = args if isinstance(args, dict) else {}
        self.attackerSlots = [int(s) for s in a.get("attackerSlots", [1, 2])]
        self.escortFireKm = float(a.get("escortFireKm", 30.0))
        self.escortShotIntervalS = float(a.get("escortShotIntervalS", 30.0))
        self.attackerThreatKm = float(a.get("attackerThreatKm", 55.0))
        self.selfDefenseKm = float(a.get("selfDefenseKm", 50.0))
        self.flankYKm = float(a.get("flankYKm", 110.0))
        self.defendX = float(a.get("defendXKm", -60.0))
        self.defendY = float(a.get("defendYKm", 30.0))
        self.fighterFireKm = float(a.get("fighterFireKm", 50.0))
        self.fighterShotIntervalS = float(a.get("fighterShotIntervalS", 25.0))
        self.crankKm = float(a.get("crankKm", 40.0))
        self.beamKm = float(a.get("beamKm", 22.0))
        self.crankDeg = float(a.get("crankDeg", 50.0))
        self.evadeOffsetDeg = float(a.get("evadeOffsetDeg", 180.0))
        self.marginKm = float(a.get("marginKm", 25.0))
        self.marginAzDeg = float(a.get("marginAzDeg", 120.0))
        # 早期撃墜のための追加パラメータ（既定値は従来の挙動）
        self.interceptMode = str(a.get("interceptMode", "lead"))   # "lead" | "racetrack"
        self.flankRoute = bool(a.get("flankRoute", True))          # True: 側面の経由点を回る（False: 直行）
        self.routeMode = str(a.get("routeMode", "flank" if self.flankRoute else "direct"))  # flank | direct | edge
        self.edgeYKm = float(a.get("edgeYKm", 118.0))             # edge: 戦域の端（|y|=edgeYKm）沿いに進む
        self.edgeUntilXKm = float(a.get("edgeUntilXKm", 50.0))     # edge: この x を越えたら会合点へ直行
        self.edgeSide = str(a.get("edgeSide", "slot"))             # slot: 左右に分ける / escort: 会合点の側
        self.defenderMode = str(a.get("defenderMode", "engage"))   # engage | kite（一撃して距離を取り時間を稼ぐ）
        self.kiteKm = float(a.get("kiteKm", 55.0))
        self.attackerCruiseMps = float(a.get("attackerCruiseMps", 340.0))
        aeo = a.get("attackerEvadeOffsetDeg", None)
        self.attackerEvadeOffsetDeg = float(aeo) if aeo is not None else self.evadeOffsetDeg
        self.mem = {}

    # ------------------------------------------------------------------
    def step(self, observation, reward, done, info, agentFullName, observation_space, action_space):
        own = np.asarray(observation["own"], dtype=np.float64)
        enemy = np.asarray(observation["enemy"], dtype=np.float64)
        threat = np.asarray(observation["threat"], dtype=np.float64)
        escort = np.asarray(observation.get("escort", np.zeros(6)), dtype=np.float64)
        numTurn = int(action_space["turn"].n)
        numSpeed = int(action_space["speed"].n)

        slot = _slot(agentFullName)
        m = self.mem.setdefault(agentFullName, {"t": 0, "lastLaunch": -1e9, "prevMsl": own[8]})
        m["t"] += 1
        t = m["t"]
        if own[8] < m["prevMsl"]:
            m["lastLaunch"] = t
        m["prevMsl"] = own[8]

        ox, oy = own[0], own[1]
        rows = []
        for i in range(enemy.shape[0]):
            if enemy[i, 0] > 0.5:
                b = math.radians(enemy[i, 1])
                rows.append({"i": i, "brg": enemy[i, 1], "dist": enemy[i, 2], "esc": enemy[i, 4] > 0.5,
                             "x": ox + enemy[i, 2] * math.cos(b), "y": oy + enemy[i, 2] * math.sin(b)})
        fighters = sorted([r for r in rows if not r["esc"]], key=lambda r: r["dist"])

        isAttacker = slot in self.attackerSlots
        if isAttacker:
            side = 1.0 if self.attackerSlots.index(slot) == 0 else -1.0
            az, spd, tgt = self._attacker(own, rows, fighters, escort, side, t, m)
        else:
            idx = 0 if slot == min([s for s in (1, 2, 3, 4) if s not in self.attackerSlots] or [slot]) else 1
            az, spd, tgt = self._defender(own, fighters, idx, t, m)

        if threat[0] > 0.5:
            # 警報方位から evadeOffsetDeg ずらして最高速（180=真後ろ。滑空弾を失速させる）
            s = 1.0 if oy < 0.0 else -1.0
            az = threat[1] + s * (self.attackerEvadeOffsetDeg if isAttacker else self.evadeOffsetDeg)
            spd = numSpeed - 1
            tgt = 0

        az = self._bounds(own, az)
        return {"turn": self._turnIndex(az, numTurn), "speed": int(min(numSpeed - 1, spd)), "target": int(tgt)}

    # ------------------------------------------------------------------
    def _attacker(self, own, rows, fighters, escort, side, t, m):
        ox, oy = own[0], own[1]
        top = 2
        escRow = next((r for r in rows if r["esc"]), None)
        tgt = 0
        if escort[0] > 0.5:
            ex, ey, vy = escort[1], escort[2], escort[3]
            dist = math.hypot(ex - ox, ey - oy)
            if self.routeMode == "edge" and self.edgeSide == "escort":
                if "edgeSide" not in m:
                    _px, _py, _tau = racetrack_intercept(ox, oy, ex, ey, vy, self.attackerCruiseMps, ageS=escort[5])
                    m["edgeSide"] = 1.0 if _py >= 0.0 else -1.0
                side = m["edgeSide"]
            if self.interceptMode == "racetrack":
                # レーストラックに沿って予測し、最短で会合できる点へ直行
                axp, ay, _tau = racetrack_intercept(ox, oy, ex, ey, vy, self.attackerCruiseMps, ageS=escort[5])
            else:
                lead = min(240.0, dist / 0.3)
                axp, ay = ex, max(-104.0, min(104.0, ey + vy * lead / 1000.0))
            if self.routeMode == "edge" and ox < self.edgeUntilXKm:
                # 戦域の端に沿って敵戦闘機の主戦場（中央）を避けて進む
                wy = side * self.edgeYKm
                az = math.degrees(math.atan2(wy - oy, max(20.0, abs(wy - oy) * 0.5)))
            elif self.routeMode == "flank" and ox < ex - 60.0 and dist > 80.0:
                # 外側を回る: まず護衛対象機の側面（少し外側）へ
                wy = max(-115.0, min(115.0, ay + side * 25.0))
                az = math.degrees(math.atan2(wy - oy, (ex - 50.0) - ox))
            else:
                az = math.degrees(math.atan2(ay - oy, axp - ox))
        elif self.routeMode == "edge":
            wy = side * self.edgeYKm
            az = math.degrees(math.atan2(wy - oy, max(20.0, abs(wy - oy) * 0.5)))
        else:
            az = math.degrees(math.atan2(side * self.flankYKm - oy, 20.0 - ox))

        if escRow is not None:
            if escRow["dist"] <= self.escortFireKm and t - m["lastLaunch"] >= self.escortShotIntervalS and own[8] > 0:
                tgt = escRow["i"] + 1
            if t - m["lastLaunch"] < 12.0:
                az = escRow["brg"] + side * self.crankDeg  # 撃った後は覆域内に置いたまま横へ

        if fighters:
            f = fighters[0]
            if f["dist"] <= self.selfDefenseKm and tgt == 0 and own[8] > 3 and t - m["lastLaunch"] >= 25.0:
                tgt = f["i"] + 1
            if f["dist"] <= self.attackerThreatKm and not (escRow is not None and escRow["dist"] < f["dist"]):
                az = self._beamAway(f["brg"], az)
        return az, top, tgt

    def _defender(self, own, fighters, idx, t, m):
        ox, oy = own[0], own[1]
        side = 1.0 if idx == 0 else -1.0
        tgt = 0
        spd = 1
        px, py = self.defendX, side * self.defendY
        az = math.degrees(math.atan2(py - oy, px - ox))
        if math.hypot(px - ox, py - oy) < 10.0:
            az = 90.0 if (t // 60) % 2 == 0 else -90.0
        if fighters:
            leakers = [f for f in fighters if f["x"] < ox - 10.0]
            if leakers:
                f = leakers[0]
            else:
                f = fighters[min(idx, len(fighters) - 1)]
            spd = 2
            d = f["dist"]
            if self.defenderMode == "kite" and not leakers:
                # 一撃（fighterFireKm）したら、kiteKm 以内では背を向けて最高速で距離を取る（自陣側・戦域内）
                if d <= self.kiteKm and t - m["lastLaunch"] < self.fighterShotIntervalS * 4 or d <= self.beamKm:
                    az = f["brg"] + 180.0
                else:
                    az = f["brg"]
            elif leakers or d > self.crankKm:
                az = f["brg"]
            elif d > self.beamKm:
                az = f["brg"] + side * self.crankDeg
            else:
                az = self._beamAway(f["brg"], f["brg"] + side * 90.0)
            if d <= self.fighterFireKm and t - m["lastLaunch"] >= self.fighterShotIntervalS and own[8] > 0:
                tgt = f["i"] + 1
        return az, spd, tgt

    # ------------------------------------------------------------------
    def _beamAway(self, brg, preferAz):
        """敵方位から±90°のうち preferAz に近い側（真後ろには逃げない）。"""
        c1, c2 = brg + 90.0, brg - 90.0
        return c1 if abs(_wrap(c1 - preferAz)) <= abs(_wrap(c2 - preferAz)) else c2

    def _bounds(self, own, az):
        marginSide, marginFront, marginBack = own[5], own[6], own[7]
        if marginFront < self.marginKm:
            az = self.marginAzDeg if own[1] < 0.0 else -self.marginAzDeg
        elif marginBack < self.marginKm:
            az = 0.0
        if marginSide < self.marginKm:
            az = -60.0 if own[1] > 0.0 else 60.0
        return az

    def _turnIndex(self, az, numTurn):
        az = _wrap(az)
        step = 360.0 / numTurn
        return int(round((az + 180.0) / step)) % numTurn
