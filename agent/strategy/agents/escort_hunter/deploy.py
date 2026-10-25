import numpy as np
from ASRCAISim1.core import Track3D
from math import cos, radians, sin


class DeployMixin:
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
