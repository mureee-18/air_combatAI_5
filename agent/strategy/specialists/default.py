import numpy as np

from ASRCAISim1.policy import StandalonePolicy

from ..agents.escort_hunter import EscortHunterAgent


def get_agent_class(args={}):
    return EscortHunterAgent


def get_policy(args={}):
    return DefaultPolicy(args)


def get_model_config(args={}):
    import json
    import os

    path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")
    with open(path) as f:
        configs = json.load(f)
    return configs.get("Fixed", {})


class DefaultPolicy(StandalonePolicy):
    def __init__(self, args={}):
        super().__init__()
        args = args if args is not None else {}
        self.fireRangeKm = float(args.get("fireRangeKm", 50.0))
        self.engageRangeKm = float(args.get("engageRangeKm", 60.0))
        self.marginKm = float(args.get("marginKm", 25.0))
        self.beamRangeKm = float(args.get("beamRangeKm", 45.0))
        self.breakRangeKm = float(args.get("breakRangeKm", 35.0))
        self.marginAzDeg = float(args.get("marginAzDeg", 120.0))
        self.trackConfirmFrames = int(args.get("trackConfirmFrames", 0))
        self.trackPosToleranceKm = float(args.get("trackPosToleranceKm", 10.0))
        self.targetSpread = int(args.get("targetSpread", 0))
        self.escortSeekDistKm = float(args.get("escortSeekDistKm", 0.0))
        self._lastTargetXY = None
        self._trackCount = 0

    def step(self, observation, reward, done, info, agentFullName, observation_space, action_space):
        own = np.asarray(observation["own"], dtype=np.float64)
        enemy = np.asarray(observation["enemy"], dtype=np.float64)
        threat = np.asarray(observation["threat"], dtype=np.float64)

        numTurn = int(action_space["turn"].n)
        numSpeed = int(action_space["speed"].n)

        desiredAz = 0.0
        speedIndex = numSpeed - 1
        targetIndex = 0

        detected = list(np.where(enemy[:, 0] > 0.5)[0])
        escort_candidate = None
        if self.escortSeekDistKm > 0 and detected:
            far = [i for i in detected if enemy[i, 2] >= self.escortSeekDistKm]
            if far:
                escort_candidate = max(far, key=lambda i: enemy[i, 2])

        if len(detected) > 0:
            near = [i for i in detected if enemy[i, 2] <= self.engageRangeKm]
            escorted = [i for i in detected if enemy[i, 4] > 0.5]
            pool = near if len(near) > 0 else (escorted if len(escorted) > 0 else detected)
            pool_sorted = sorted(pool, key=lambda i: enemy[i, 2])

            if self.targetSpread > 0 and agentFullName:
                offset = sum(ord(c) for c in agentFullName) % self.targetSpread
                pick_idx = offset % len(pool_sorted)
            else:
                pick_idx = 0
            best = pool_sorted[pick_idx]
            bestDist = float(enemy[best, 2])

            bearing = enemy[best, 1]
            ex = own[0] + bestDist * np.cos(np.radians(bearing))
            ey = own[1] + bestDist * np.sin(np.radians(bearing))
            if self._lastTargetXY is not None:
                dx = ex - self._lastTargetXY[0]
                dy = ey - self._lastTargetXY[1]
                if np.hypot(dx, dy) <= self.trackPosToleranceKm:
                    self._trackCount += 1
                else:
                    self._trackCount = 1
            else:
                self._trackCount = 1
            self._lastTargetXY = (ex, ey)

            breaking = self.breakRangeKm > 0.0 and bestDist <= self.breakRangeKm
            if breaking:
                desiredAz = enemy[best, 1] + 180.0
            elif self.beamRangeKm > 0.0 and bestDist <= self.beamRangeKm:
                desiredAz = enemy[best, 1] + 80.0
            else:
                desiredAz = enemy[best, 1]

            speedIndex = numSpeed - 1
            track_ok = self.trackConfirmFrames <= 0 or self._trackCount >= self.trackConfirmFrames
            if not breaking and bestDist <= self.fireRangeKm and threat[0] < 0.5 and track_ok:
                targetIndex = int(best) + 1

            if (
                escort_candidate is not None
                and threat[0] < 0.5
                and not breaking
                and bestDist > self.beamRangeKm
            ):
                desiredAz = enemy[escort_candidate, 1]
        else:
            desiredAz = 0.0
            self._lastTargetXY = None
            self._trackCount = 0

        if threat[0] > 0.5:
            desiredAz = threat[1] + 180.0
            targetIndex = 0

        marginSide, marginFront, marginBack = own[5], own[6], own[7]
        if marginFront < self.marginKm:
            desiredAz = self.marginAzDeg if own[1] < 0.0 else -self.marginAzDeg
        elif marginBack < self.marginKm:
            desiredAz = 0.0
        if marginSide < self.marginKm:
            desiredAz = -60.0 if own[1] > 0.0 else 60.0

        return {
            "turn": self._nearestTurnIndex(desiredAz, numTurn),
            "speed": speedIndex,
            "target": targetIndex,
        }

    def _nearestTurnIndex(self, desiredAz, numTurn):
        az = (desiredAz + 180.0) % 360.0 - 180.0
        step = 360.0 / numTurn
        return int(round((az + 180.0) / step)) % numTurn