"""ローカル対戦ログに敵機の絶対座標を記録する（提出物とは無関係・可視化用）.

`workspace/src/fight.py` が「record_enemies」ON のとき引用し、各フレーム（観測が記録された
フレームに限定）の敵側戦闘機・護衛対象機の**自陣フレーム座標（km）**を集めて返す。

- 座標は予測ではなく、シミュレータの管理オブジェクトが保持する絶対座標の変換値。
- ワールド座標 (x, y) [m] -> 自陣フレーム (x, y) [km]:
  - Red 陣営 : (y_w, -x_w) / 1000   （x=+ が敵方向）
  - Blue 陣営: (-y_w, x_w) / 1000
- 方位は機首方位の記録が無いため、同一フレームの pos と pos_prev の差から進路方位を求める
  （2点の実測座標による微分であって、予測ではない）。
- `alive=False` の機体も行は返す（描画側で排除）。撃墜後の表示を出さないため。
"""

import math

import numpy as np

TEAM_TRANSFORM = {
    # ワールド(x,y)[m] -> 自陣フレーム(x,y)[km]
    "Red": lambda p: (p[1], -p[0]),
    "Blue": lambda p: (-p[1], p[0]),
}
COURSE_SHIFT_DEG = {"Red": -90.0, "Blue": 90.0}


def _vec(value, default=None):
    """Coordinate / np.ndarray / list から (x, y, z) の ndarray を取り出す。"""
    try:
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        try:
            return np.asarray(value.getValue(), dtype=float)
        except Exception:
            return default


def collect_enemy(manager, our_team):
    """自陣 our_team のフレームで見た敵側機体（F/F1..4 + E）の絶対位置一覧を返す。"""
    enemy_team = "Blue" if our_team == "Red" else "Red"
    transform = TEAM_TRANSFORM[our_team]
    shift = COURSE_SHIFT_DEG[our_team]
    rows = []
    for weak in manager.getAssets():
        asset = weak()
        name = asset.getFullName()
        if asset.getTeam() != enemy_team or name.count("/") != 1:
            continue
        pos = _vec(asset.pos)
        if pos is None:
            continue
        prev = _vec(getattr(asset, "pos_prev", None))
        x_km, y_km = transform(pos[:2])
        heading = None
        if prev is not None and (pos[:2] != prev[:2]).any():
            course_world = math.degrees(math.atan2(pos[1] - prev[1], pos[0] - prev[0]))
            heading = round((course_world + shift) % 360.0, 1)
        rows.append(
            {
                "id": name.split("/")[-1],
                "x": round(float(x_km) / 1000.0, 3),
                "y": round(float(y_km) / 1000.0, 3),
                "heading": heading,
                "alive": bool(asset.isAlive()),
            }
        )
    return rows