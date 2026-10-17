"""IRST/レーダによる敵護衛対象機の運動学的識別（ユース部門専用・純 Python）.

ユース部門の敵護衛対象機は、自陣営座標系（x=+ が敵方向, km）で
x=115 / x=125 の2本の直線を半径5kmの半円でつなぐレーストラックを 250 m/s・右回りで周回する。
右回りなので「x=115 の辺は -y 方向」「x=125 の辺は +y 方向」に飛ぶ（10戦の真値で確認済み）。

IRST は距離が取れないが全周・距離無制限で方位が取れ、航跡 ID は探知が続く間は不変。
各 IRST 航跡について直近 window 秒の方位線と x=115/125 の交点 y(t) を一次式で当てはめ、
「速さ 200〜300 m/s・残差 RMS < rmsMaxKm・|y| ≤ yMaxKm・辺の向きが一致」なら1票。
票数が minVotes 以上かつ現存航跡の票の minShare 以上を占めたら護衛対象機として確定する（c2 方式）。
レーダ航跡が護衛対象機の運動学的特徴（速さ≈250 m/s、x≈115〜125 km）に一致した場合はそちらを優先する。

検証（/workspace/research/escort_id、Red/Blue×seed1-5 の10戦、BenchMark 相手）:
誤識別 0、初回正解 中央値 24 s、位置誤差 中央値 0.30 km。
"""

import math

LEGS = ((115.0, -1.0), (125.0, 1.0))  # (直線の x [km], その辺での vy の符号)


def _fit_line(hist, legX):
    ts = []
    ys = []
    for t, ox, oy, brg in hist:
        c = math.cos(math.radians(brg))
        if c < 0.05 or ox >= legX:
            continue
        ts.append(t)
        ys.append(oy + (legX - ox) * math.tan(math.radians(brg)))
    n = len(ts)
    if n < 2:
        return None
    mt = sum(ts) / n
    my = sum(ys) / n
    stt = sum((t - mt) ** 2 for t in ts)
    if stt <= 0.0:
        return None
    slope = sum((t - mt) * (y - my) for t, y in zip(ts, ys)) / stt
    icpt = my - slope * mt
    rms = math.sqrt(sum((icpt + slope * t - y) ** 2 for t, y in zip(ts, ys)) / n)
    return {"n": n, "vy": slope * 1000.0, "rms": rms, "y": icpt + slope * ts[-1], "t": ts[-1], "x": legX}


def best_leg_fit(hist, minSamples=15):
    fits = []
    for legX, sign in LEGS:
        f = _fit_line(hist, legX)
        if f is not None and f["n"] >= minSamples:
            f["consistent"] = (f["vy"] > 0) == (sign > 0)
            fits.append(f)
    if not fits:
        return None
    cons = [f for f in fits if f["consistent"]]
    return min(cons or fits, key=lambda f: f["rms"])


def radar_signature(x, y, vx, vy, speedTolMps=10.0):
    """レーダ航跡（自陣営座標系 km, m/s）が護衛対象機の特徴に合うか。"""
    v = math.hypot(vx, vy)
    return abs(v - 250.0) <= speedTolMps and 108.0 <= x <= 132.0 and abs(y) <= 112.0


class EscortIdentifier:
    def __init__(self, window=30, minSamples=15, minVotes=10, minShare=0.6,
                 vMin=200.0, vMax=300.0, rmsMaxKm=1.5, yMaxKm=110.0):
        self.window = int(window)
        self.minSamples = int(minSamples)
        self.minVotes = int(minVotes)
        self.minShare = float(minShare)
        self.vMin = float(vMin)
        self.vMax = float(vMax)
        self.rmsMaxKm = float(rmsMaxKm)
        self.yMaxKm = float(yMaxKm)
        self.hist = {}
        self.votes = {}
        self.estimate = None  # 最後に確定した推定 {t, x, y, vx, vy, src, irstId}

    def _passes(self, fit):
        return (fit is not None and self.vMin <= abs(fit["vy"]) <= self.vMax
                and fit["rms"] < self.rmsMaxKm and abs(fit["y"]) <= self.yMaxKm)

    def update(self, t, ownX, ownY, irst, radar=()):
        """1ステップ分を取り込み、現在の推定を返す（無ければ None）.

        irst: [(trackId, bearingDeg)]  （自陣営座標系、0=+x、反時計回り正）
        radar: [(x_km, y_km, vx_mps, vy_mps)]
        """
        current = set()
        for tid, brg in irst:
            current.add(tid)
            h = self.hist.setdefault(tid, [])
            h.append((float(t), float(ownX), float(ownY), float(brg)))
            if len(h) > self.window:
                del h[0]
            if self._passes(best_leg_fit(h, self.minSamples)):
                self.votes[tid] = self.votes.get(tid, 0) + 1
        for tid in list(self.hist):
            if tid not in current:
                del self.hist[tid]
        est = None
        live = {k: v for k, v in self.votes.items() if k in current}
        if live:
            tid = max(live, key=lambda k: live[k])
            v = live[tid]
            if v >= self.minVotes and v >= self.minShare * sum(live.values()):
                fit = best_leg_fit(self.hist[tid], self.minSamples)
                if fit is not None:
                    est = {"t": float(t), "x": fit["x"], "y": fit["y"], "vx": 0.0, "vy": fit["vy"],
                           "src": 1, "irstId": tid}
        for (x, y, vx, vy) in radar:
            if radar_signature(x, y, vx, vy):
                if est is None or math.hypot(est["x"] - x, est["y"] - y) <= 15.0:
                    est = {"t": float(t), "x": x, "y": y, "vx": vx, "vy": vy, "src": 2,
                           "irstId": est["irstId"] if est else None}
                    break
        if est is not None:
            self.estimate = est
        return est

    def predicted(self, t):
        """最後の推定をレーストラックに沿って t まで外挿（直線部分のみ近似）。"""
        e = self.estimate
        if e is None:
            return None
        dt = float(t) - e["t"]
        y = e["y"] + e["vy"] * dt / 1000.0
        y = max(-104.5, min(104.5, y))
        return {"x": e["x"], "y": y, "vy": e["vy"], "age": dt, "src": e["src"]}
