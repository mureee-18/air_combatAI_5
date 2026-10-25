import numpy as np
from gymnasium import spaces

from ASRCAISim1.core import (
    AltitudeKeeper,
    SingleAssetAgent,
    Track3D,
    getValueFromJsonKRD,
)
from BasicAgentUtility.util import TeamOrigin

from .control import ControlMixin
from .deploy import DeployMixin
from .observation import ObservationMixin


class EscortHunterAgent(ObservationMixin, DeployMixin, ControlMixin, SingleAssetAgent):
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

    def observation_space(self):
        low = np.finfo(np.float32).min
        high = np.finfo(np.float32).max
        return spaces.Dict({
            "own": spaces.Box(low, high, shape=[10], dtype=np.float32),
            "enemy": spaces.Box(low, high, shape=[self.maxEnemyNum, 6], dtype=np.float32),
            "threat": spaces.Box(low, high, shape=[2], dtype=np.float32),
        })

    def action_space(self):
        return spaces.Dict({
            "turn": spaces.Discrete(len(self.turnTable)),
            "speed": spaces.Discrete(len(self.speedTable)),
            "target": spaces.Discrete(1 + self.maxEnemyNum),
        })
