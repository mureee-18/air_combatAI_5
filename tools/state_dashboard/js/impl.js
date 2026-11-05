function renderImpl(d) {
  const a = d.agents || {};
  const args = a.args || {};
  const wiring = a.arg_wiring || {};
  // サーバー（serve.py の _arg_rows）が値・ベースライン・目的・配線状態をまとめて返す。
  // 旧ペイロード（arg_rows なし）でも壊れないように args から組み立てる。
  const rows = (a.arg_rows && a.arg_rows.length) ? a.arg_rows : Object.keys(args)
    .filter(k => k !== "type" && k !== "specialist")
    .sort()
    .map(k => ({
      key: k,
      current: args[k],
      baseline: undefined,
      changed: false,
      desc: "",
      wired: null,
      via: [],
      files: [],
    }));

  let h = '<h2>実装状態（agent/args.json → コードの配線）</h2>';
  h += '<p class="meta">現在の変数値と目的。この表は args.json のキー一覧ではなく、'
     + 'コード参照の監査結果（tools/arg_wiring.py）を正としています。'
     + '「未配線」の変数は値を変えても挙動が変わりません。</p>';

  const unwired = rows.filter(r => r.wired === false);
  if (wiring.total) {
    if (wiring.unwired && wiring.unwired.length) {
      h += `<p class="meta warn">未配線の変数: ${esc(wiring.unwired.join(", "))}`
         + `（${wiring.wired}/${wiring.total} 配線済み）</p>`;
    } else {
      h += `<p class="meta ok">全 ${wiring.total} 変数がコードに配線済みです`
         + '（policy / modelConfig / 直接参照のいずれか）。</p>';
    }
  }

  const wiredCell = (r) => {
    if (r.wired === true) {
      const via = (r.via && r.via.length) ? r.via.join("+") : "wired";
      const files = (r.files && r.files.length) ? r.files.join(", ") : "";
      return `<span class="ok" title="${esc(files)}">配線済み（${esc(via)}）</span>`;
    }
    if (r.wired === false) return '<span class="warn">未配線</span>';
    return "—";
  };

  h += table(
    [{label:"変数"},{label:"現在値"},{label:"ベースライン"},{label:"目的"},{label:"配線"}],
    rows.map(r => [
      esc(r.key),
      esc(String(r.current)),
      esc(r.baseline !== undefined && r.baseline !== null ? String(r.baseline) : "—"),
      esc(r.desc || "—"),
      wiredCell(r),
    ])
  );

  const changed = rows.filter(r => r.changed);
  if (changed.length) {
    h += `<p class="meta warn">ベースラインと異なる変数: `
       + `${esc(changed.map(r => r.key).join(", "))}（${changed.length} 個）</p>`;
  } else if (rows.length) {
    h += '<p class="meta ok">全変数がベースラインと一致しています。</p>';
  }

  if (unwired.length) {
    h += '<h2>未配線の変数（値を変えても挙動が変わらない）</h2>';
    h += '<p class="meta">args.json にキーを足しただけの状態です。'
       + 'policy.py に属性を作り、判断層から参照するまで効果はありません。</p>';
    h += '<ul>' + unwired.map(r => `<li><code>${esc(r.key)}</code></li>`).join("") + '</ul>';
  }

  h += '<h2>変数の追加・削除・仕様変更</h2>';
  h += '<p class="meta">変数を追加するときは次の4点をセットで変更します: '
     + '(1) agent/args.json にキーを追加、'
     + '(2) policy.py に self.xxx = args.get("xxx", default) を追加、'
     + '(3) judgment / execution で実際に参照、'
     + '(4) analysis/tools/baseline_args.json に同じ既定値を追加。'
     + '追加後は python tools/arg_wiring.py で「全変数が配線済み」を確認してください。</p>';
  h += cmdRow(
    '実装変更を依頼します。agent/args.json / policy.py / judgment.py を編集して変数を追加・削除・仕様変更してください。具体的な変更内容は私が指定します。',
    "実装変更の指示（OpenCode に貼り付け）", INTENT_IMPL);
  document.getElementById("impl").innerHTML = h;
  bindCopy(document.getElementById("impl"));
}
