### アイデア hosyan_h9redtune（Red 陣営のときだけ V6 の引数を上書き）

- 自分が Red のときだけ、ディフェンダーが護衛へ切り替わる判定を早める（deepXKm −20→0、flankXKm 10→30）。Blue は V6 と同じ動き
- 相手プール seeds 1〜60 × 両色 720 試合で対応差 +0.0063±0.0055、pool 最低値 0.602（V6 0.575）。O_RUSH の Red で +0.083±0.032
- このブランチの昇格ルール（差 > 1×SE）は PASS、P7 の規則（差 > 2×SE）は FAIL。`agent/args.json` と `hybrid_v6` は変えない
