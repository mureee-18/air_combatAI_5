import numpy as np
from gymnasium import spaces
from math import atan2, cos, sin, sqrt, degrees, radians

from ASRCAISim1.core import (
    AltitudeKeeper,
    MotionState,
    SingleAssetAgent,
    Track2D,
    Track3D,
    getValueFromJsonKRD,
)
from BasicAgentUtility.util import TeamOrigin

from .escort_id import EscortIdentifier


class EscortHunterAgent(SingleAssetAgent):
    def initialize(self):
        super().initialize()
        self.own = self.getTeam()
        mc = self.modelConfig

        defaultTurnTable = [-180.0 + 15.0 * i for i in range(24)]
        self.turnTable = np.array(
            getValueFromJsonKRD(mc, "turnTable", self.randomGen, defaultTurnTable),
            dtype=np.float64,
        )
        self.speedTable = np.array(
            getValueFromJsonKRD(mc, "speedTable", self.randomGen, [220.0, 280.0, 340.0]),
            dtype=np.float64,
        )
        self.maxEnemyNum = int(getValueFromJsonKRD(mc, "maxEnemyNum", self.randomGen, 5))
        self.maxSimulShot = int(getValueFromJsonKRD(mc, "maxSimulShot", self.randomGen, 2))
        self.altMin = getValueFromJsonKRD(mc, "altMin", self.randomGen, 2000.0)
        self.altMax = getValueFromJsonKRD(mc, "altMax", self.randomGen, 15000.0)
        self.altitudeKeeper = AltitudeKeeper(mc().get("altitudeKeeper", {}))
        # IRST/レーダによる敵護衛対象機の識別（既定 OFF。OFF のとき観測・挙動は従来と同一）
        self.useIrstEscortId = bool(getValueFromJsonKRD(mc, "useIrstEscortId", self.randomGen, False))
        self.escortId = EscortIdentifier() if self.useIrstEscortId else None
        self.escortMatchKm = float(getValueFromJsonKRD(mc, "escortMatchKm", self.randomGen, 6.0))

        self.lastTrackInfo = []
        self.dstDir = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        self.dstV = float(self.speedTable[len(self.speedTable) // 2])
        self.launchFlag = False
        self.target = Track3D()

    def validate(self):
        rulerObs = self.manager.getRuler()().observables()
        self.dOut = rulerObs["dOut"]
        self.dLine = rulerObs["dLine"]
        self.teamOrigin = TeamOrigin(self.own == rulerObs["eastSider"], self.dLine)
        self.dstDir = self.teamOrigin.relBtoP(np.array([1.0, 0.0, 0.0]))

        self.fuelCapacity = float(rulerObs.get("fuelMargin", 0.0))

    def makeObs(self):
        parent = self.parent
        own = np.zeros([10], dtype=np.float32)
        enemy = np.zeros([self.maxEnemyNum, 5], dtype=np.float32)
        threat = np.zeros([2], dtype=np.float32)
        self.lastTrackInfo = []

        escort = np.zeros([6], dtype=np.float32)

        if not parent.isAlive():
            return self._packObs(own, enemy, threat, escort)

        myMotion = MotionState(parent.observables["motion"]).transformTo(self.getLocalCRS())
        pos = self.teamOrigin.relPtoB(myMotion.pos())
        vel = self.teamOrigin.relPtoB(myMotion.vel())
        V = float(np.linalg.norm(vel))
        own[0] = pos[0] / 1000.0
        own[1] = pos[1] / 1000.0
        own[2] = -pos[2] / 1000.0
        own[3] = V
        own[4] = degrees(atan2(vel[1], vel[0])) if V > 1e-5 else 0.0
        own[5] = (self.dOut - abs(pos[1])) / 1000.0
        own[6] = (self.dLine - pos[0]) / 1000.0
        own[7] = (self.dLine + pos[0]) / 1000.0
        own[8] = float(parent.observables.at_p("/weapon/remMsls"))
        own[9] = float(parent.observables.at_p("/propulsion/fuelRemaining"))

        rawTracks = list(parent.observables.at_p("/sensor/track"))
        tracks = [Track3D(t).transformTo(self.getLocalCRS()) for t in rawTracks]
        order = sorted(
            range(len(tracks)),
            key=lambda i: float(np.linalg.norm(np.asarray(tracks[i].pos()) - np.asarray(myMotion.pos()))),
        )
        self.lastTrackInfo = [tracks[i] for i in order]

        for row, i in enumerate(order[: self.maxEnemyNum]):
            tPos = self.teamOrigin.relPtoB(tracks[i].pos())
            rel = tPos - pos
            enemy[row, 0] = 1.0
            enemy[row, 1] = degrees(atan2(rel[1], rel[0]))
            enemy[row, 2] = float(np.linalg.norm(rel[:2])) / 1000.0
            enemy[row, 3] = -tPos[2] / 1000.0
            enemy[row, 4] = 1.0 if self._isEscorted(rawTracks[i]) else 0.0

        if parent.observables.contains_p("/sensor/mws/track"):
            for mObs in parent.observables.at_p("/sensor/mws/track"):
                mwsTrack = Track2D(mObs).transformTo(self.getLocalCRS())
                d = self.teamOrigin.relPtoB(mwsTrack.dir())
                threat[0] = 1.0
                threat[1] = degrees(atan2(d[1], d[0]))
                break

        if self.useIrstEscortId:
            self._updateEscort(pos, enemy, escort, order[: self.maxEnemyNum], tracks)

        return self._packObs(own, enemy, threat, escort)

    def _packObs(self, own, enemy, threat, escort):
        obs = {"own": own, "enemy": enemy, "threat": threat}
        if self.useIrstEscortId:
            obs["escort"] = escort
        return obs

    def _updateEscort(self, pos, enemy, escort, rows, tracks):
        """IRST 方位列とレーダ航跡から敵護衛対象機を識別し、escort 観測と enemy[:,4] を埋める.

        escort = [有効, x km, y km, vy m/s, 出所(1=IRST, 2=レーダ), 推定からの経過秒]（自陣営座標系）
        """
        parent = self.parent
        crs = self.getLocalCRS()
        t = float(self.manager.getElapsedTime())
        irst = []
        if parent.observables.contains_p("/sensor/irst/track"):
            for tObs in parent.observables.at_p("/sensor/irst/track"):
                try:
                    d = self.teamOrigin.relPtoB(Track2D(tObs).transformTo(crs).dir())
                    irst.append((str(tObs["truth"]()), degrees(atan2(d[1], d[0]))))
                except Exception:
                    continue
        radar = []
        for i in rows:
            tp = self.teamOrigin.relPtoB(tracks[i].pos())
            tv = self.teamOrigin.relPtoB(tracks[i].vel())
            radar.append((tp[0] / 1000.0, tp[1] / 1000.0, float(tv[0]), float(tv[1])))
        self.escortId.update(t, pos[0] / 1000.0, pos[1] / 1000.0, irst, radar)
        pred = self.escortId.predicted(t)
        if pred is None or pred["age"] > 120.0:
            return
        escort[:] = [1.0, pred["x"], pred["y"], pred["vy"], pred["src"], pred["age"]]
        best = None
        for row, (x, y, _vx, _vy) in enumerate(radar):
            dd = sqrt((x - pred["x"]) ** 2 + (y - pred["y"]) ** 2)
            if dd <= self.escortMatchKm and (best is None or dd < best[0]):
                best = (dd, row)
        if best is not None:
            enemy[best[1], 4] = 1.0

    def observation_space(self):
        low = np.finfo(np.float32).min
        high = np.finfo(np.float32).max
        space = {
            "own": spaces.Box(low, high, shape=[10], dtype=np.float32),
            "enemy": spaces.Box(low, high, shape=[self.maxEnemyNum, 5], dtype=np.float32),
            "threat": spaces.Box(low, high, shape=[2], dtype=np.float32),
        }
        if self.useIrstEscortId:
            space["escort"] = spaces.Box(low, high, shape=[6], dtype=np.float32)
        return spaces.Dict(space)

    def action_space(self):
        return spaces.Dict({
            "turn": spaces.Discrete(len(self.turnTable)),
            "speed": spaces.Discrete(len(self.speedTable)),
            "target": spaces.Discrete(1 + self.maxEnemyNum),
        })

    def deploy(self, action):
        parent = self.parent
        if not parent.isAlive():
            return

        az = radians(float(self.turnTable[int(action["turn"])]))
        self.dstDir = self.teamOrigin.relBtoP(np.array([cos(az), sin(az), 0.0]))
        self.dstV = float(self.speedTable[int(action["speed"])])

        self.launchFlag = False
        self.target = Track3D()
        tIdx = int(action["target"]) - 1
        if 0 <= tIdx < len(self.lastTrackInfo):
            candidate = self.lastTrackInfo[tIdx]
            if parent.isLaunchableAt(candidate) and self._countFlyingMissiles() < self.maxSimulShot:
                self.launchFlag = True
                self.target = candidate

    def control(self):
        parent = self.parent
        if not parent.isAlive():
            return

        myMotion = MotionState(parent.observables["motion"]).transformTo(self.getLocalCRS())
        dstDir = np.array(self.dstDir, dtype=np.float64)
        n = sqrt(dstDir[0] * dstDir[0] + dstDir[1] * dstDir[1])
        if n < 1e-8:
            dstDir = self.teamOrigin.relBtoP(np.array([1.0, 0.0, 0.0]))
            n = sqrt(dstDir[0] * dstDir[0] + dstDir[1] * dstDir[1])
        dstPitch = atan2(-dstDir[2], n)
        bottom = self.altitudeKeeper(myMotion, dstDir, self.altMin)
        minPitch = atan2(-bottom[2], sqrt(bottom[0] * bottom[0] + bottom[1] * bottom[1]))
        top = self.altitudeKeeper(myMotion, dstDir, self.altMax)
        maxPitch = atan2(-top[2], sqrt(top[0] * top[0] + top[1] * top[1]))
        dstPitch = max(minPitch, min(maxPitch, dstPitch))
        cs = cos(dstPitch)
        sn = sin(dstPitch)
        dstDir = np.array([dstDir[0] / n * cs, dstDir[1] / n * cs, -sn])

        originalMyMotion = MotionState(parent.observables["motion"])
        self.commands[parent.getFullName()] = {
            "motion": {
                "dstDir": originalMyMotion.dirAtoP(dstDir, myMotion.pos(), self.getLocalCRS()),
                "dstV": self.dstV,
            },
            "weapon": {
                "launch": self.launchFlag,
                "target": self.target.to_json(),
            },
        }
        self.launchFlag = False

    def _isEscorted(self, rawTrack):
        try:
            if not rawTrack.contains("spec"):
                return False
            spec = rawTrack.at("spec")
            if not spec.contains("sensor"):
                return True
            return not spec.at("sensor").contains("radar")
        except Exception:
            return False

    def _countFlyingMissiles(self):
        count = 0
        if self.parent.observables.contains_p("/weapon/missiles"):
            for msl in self.parent.observables.at_p("/weapon/missiles"):
                if msl.at("isAlive")() and msl.at("hasLaunched")():
                    count += 1
        return count
