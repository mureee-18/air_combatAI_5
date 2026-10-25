#!/usr/bin/env bash
# GitHub Pages 用に開発状況ダッシュボードの静的スナップショットを作る。
# serve.py --once の JSON を api/summary.json に書き、JS の取得先を相対パスに置き換える。
# 生成物は _site/ のみ（ソースは書き換えない）。
set -euo pipefail
out="${1:-_site}"
src="tools/state_dashboard"
rm -rf "$out"
mkdir -p "$out/api"
cp "$src/index.html" "$out/index.html"
cp -r "$src/js" "$out/js"
python3 "$src/serve.py" --once > "$out/api/summary.json"
# サブパス（/air_combatAI_5/）で動くよう、絶対パスの API を相対パスへ。
# summary はスナップショットを読む。replay / decision など他の API はライブ専用なので静的版では読み込み失敗になる。
sed -i -e 's#fetch("/api/summary"#fetch("api/summary.json"#g' -e 's#fetch("/api/#fetch("api/#g' "$out"/js/*.js
touch "$out/.nojekyll"
echo "built $out: $(du -sh "$out" | cut -f1)"
