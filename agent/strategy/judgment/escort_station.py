"""Judgment sub-task: escort station keeping (判断層 — 護衛候補との距離保持).

護衛候補（=敵の高価値機）との距離を、args.json の3つの距離ノブで制御する。
これらは以前 args.json に値だけ存在してコードから読まれていなかったため、
値を変えても挙動が変わらない「死んだ変数」だった。ここで判断層に配線する。

    escortFormationKm : 基本の保持距離 (km)。0=無効
    escortTrailDistKm : 接近フェーズ（ビーム射程外）の保持距離 (km)。0=無効（formation に従う）
    escortLeadDistKm  : 交戦フェーズ（ビーム射程内）の最小間隔 (km)。0=無効（formation に従う）

制御はデッドバンド方式。目標距離から一定以上内側に入ったときだけ
「離脱方向（目標方位 + 180°）」へ機首を向ける。外側にいるときは既定の
航法（目標へ向かう）に任せる。射撃解がある tick では上書きしない。
既定値はすべて 0（無効）なので、値を入れない限り従来の挙動と同一。
"""

BAND_RATIO = 0.15
BAND_MIN_KM = 5.0


def escort_station_heading(policy, enemy, escort_slot, beam_range_km):
    """護衛候補との距離を保つための望ましい機首方位を返す（不要なら None）."""

    if escort_slot is None:
        return None

    formation = float(getattr(policy, "escort_formation_km", 0.0))
    trail = float(getattr(policy, "escort_trail_dist_km", 0.0))
    lead = float(getattr(policy, "escort_lead_dist_km", 0.0))

    dist = float(enemy[escort_slot, 2])
    engage_range = max(float(beam_range_km), 0.0)

    if dist > engage_range and trail > 0.0:
        desired = trail
    elif dist <= engage_range and lead > 0.0:
        desired = lead
    elif formation > 0.0:
        desired = formation
    else:
        return None

    band = max(BAND_MIN_KM, abs(desired) * BAND_RATIO)
    if dist >= desired - band:
        # デッドバンド内または外側。既定の航法に任せる。
        return None

    return float(enemy[escort_slot, 1]) + 180.0
