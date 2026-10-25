import numpy as np
from math import atan2, cos, sin, sqrt

from ASRCAISim1.core import MotionState


class ControlMixin:
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
