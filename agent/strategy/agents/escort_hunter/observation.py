import numpy as np
from math import atan2, degrees

from ASRCAISim1.core import (
    MotionState,
    Track2D,
    Track3D,
)
from math import sqrt


class ObservationMixin:
    def makeObs(self):
        parent = self.parent
        own = np.zeros([10], dtype=np.float32)
        enemy = np.zeros([self.maxEnemyNum, 6], dtype=np.float32)
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
            enemy[row, 5] = float(np.linalg.norm(np.asarray(tracks[i].vel(), dtype=np.float64))) / 1000.0

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
