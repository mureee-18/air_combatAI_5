"""改善セッション支援ツール（kaggriculture の improvement_session.py を本コンペ用に移植）.

改善サイクルを強制・記録する。前提:
    - 対戦は Docker コンテナ (atla5-cpu) 内の validate.py で実行する
    - 記録は analysis/agents/<specialist>/improvement.md に追記する

記録は「事実（出所あり）」と「推論（仮説）」を型で分離する（kaggriculture の
records.py と同じ考え方）:
    kind    rule       大会ルール / 採点式に由来する制約（出所は official のみ）
            observation 実測ログ・計測値に基づく事実
            inference   仮説・因果推論・予測
    source  official 公式ルール / fight.py 等の実装
            code     自作コードの読み取り
            log      対戦ログ / 計測値
            analysis 解析結果・ダッシュボード

Usage:
    python analysis/tools/improvement_session.py start --specialist default
    python analysis/tools/improvement_session.py assumption "MWS は 10km 程度までしか効かない" --specialist default
    python analysis/tools/improvement_session.py hypothesis "射距離を 35km にすると命中率が上がる" \
        --specialist default --source log
    python analysis/tools/improvement_session.py verify --specialist default
    python analysis/tools/improvement_session.py validate --specialist default --games 3
    python analysis/tools/improvement_session.py record --specialist default \
        --kind observation --source log \
        --direction "..." --changes "..." --verification "..." --next-steps "..."
    python analysis/tools/improvement_session.py check --specialist default
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "analysis" / "agents"
FORMAT_MD = REPO_ROOT / "tools" / "battle_analyzer" / "BATTLELOG_FORMAT.md"
ACTIVE_PY = REPO_ROOT / "agent" / "strategy" / "active.py"
SPECIALISTS_DIR = REPO_ROOT / "agent" / "strategy" / "specialists"
ARGS_PATH = REPO_ROOT / "agent" / "args.json"
RESULT_DIR = "results_improve"

RECORD_KINDS = ("rule", "observation", "inference")
RECORD_SOURCES = ("official", "code", "log", "analysis")
KIND_PREFIX = {"rule": "R", "observation": "O", "inference": "N"}
KIND_LABEL = {
    "rule": "大会ルール由来の制約",
    "observation": "実測に基づく事実",
    "inference": "仮説・推論",
}
SOURCE_LABEL = {
    "official": "公式ルール / シミュレータ実装",
    "code": "自作コードの読み取り",
    "log": "対戦ログ / 計測値",
    "analysis": "解析結果・ダッシュボード",
}
# 種別ごとの許容出所。rule は公式に限る（推測でルールを作らない）。
KIND_ALLOWED_SOURCES = {
    "rule": ("official",),
    "observation": ("log", "analysis", "code"),
    "inference": ("log", "analysis", "code", "official"),
}


def state_path(name: str) -> Path:
    return AGENTS_DIR / name / "session_state.json"


def note_path(name: str) -> Path:
    return AGENTS_DIR / name / "improvement.md"


def load_state(name: str) -> dict:
    path = state_path(name)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(name: str, state: dict) -> None:
    path = state_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def require_specialist(name: str) -> None:
    if not (SPECIALISTS_DIR / f"{name}.py").exists():
        raise SystemExit(f"specialist が存在しません: {name}")


def validate_record(kind: str, source: str) -> None:
    """種別と出所の整合を検査する。不正なら SystemExit（ Clap 風の選択肢_help と対）."""

    if kind not in RECORD_KINDS:
        raise SystemExit(f"種別が不正です: {kind}（{'/'.join(RECORD_KINDS)}）")
    if source not in RECORD_SOURCES:
        raise SystemExit(f"出所が不正です: {source}（{'/'.join(RECORD_SOURCES)}）")
    allowed = KIND_ALLOWED_SOURCES[kind]
    if source not in allowed:
        raise SystemExit(
            f"種別の型制約違反: kind={kind} は source={'/'.join(allowed)} のみ。"
            f"（{KIND_LABEL[kind]} に {SOURCE_LABEL[source]} は使えない）"
        )


def normalize_text(text: str) -> str:
    """入力の貼り付けミスを正規化する。

    全体が「A A」と同じ文の2回繰り返しになっていれば A に畳む
    （コマンド例からのコピーで二重に貼り付いたケースの防止）。
    """

    text = text.strip()
    match = re.match(r"^(.+?)\s+\1[.。]?$", text, flags=re.DOTALL)
    if match:
        text = match.group(1).strip()
    return text


def next_record_id(path: Path, kind: str) -> str:
    """improvement.md に既にある同種別の記録数から次の ID を返す（O-001 / N-002 形式）."""

    prefix = KIND_PREFIX[kind]
    used = 0
    if path.exists():
        text = path.read_text(encoding="utf-8")
        used = text.count(f"\n## {prefix}-") + (1 if text.startswith(f"## {prefix}-") else 0)
    return f"{prefix}-{used + 1:03d}"


def next_hypothesis_id(state: dict) -> str:
    """session_state.json に既にある仮説から次の ID を返す（N-001 形式・重複しない）."""

    max_n = 0
    for hyp in state.get("hypotheses", []):
        match = re.fullmatch(r"N-(\d+)", str(hyp.get("id", "")))
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"N-{max_n + 1:03d}"


def run_games(games: int) -> dict:
    cmd = [
        "docker", "exec", "atla5-cpu", "bash", "-lc",
        f"cd /workspace && python validate.py --youth 1 --num-validation {games} "
        f"--result-dir /workspace/{RESULT_DIR} --visualize 0",
    ]
    subprocess.run(cmd, cwd=str(REPO_ROOT), check=False)
    path = REPO_ROOT / "workspace" / RESULT_DIR / "0" / "validation_results.json"
    if not path.exists():
        raise SystemExit(f"結果が見つかりません: {path}")
    return json.loads(path.read_text())


def summarize(label: str, data: dict) -> dict:
    own = data["own"]
    enemy = "Blue" if own == "Red" else "Red"
    n = max(1, len(data["details"]))
    score = 0.0
    our_alive = 0.0
    enemy_alive = 0.0
    print(f"--- {label} ---")
    for k, v in sorted(data["details"].items()):
        s = v["scores"][own]
        score += s
        our_alive += v["numAlives"][own]
        enemy_alive += v["numAlives"][enemy]
        print(
            f"  fight {k}: {v['endReason']:<12} steps={v['step_count']:<5} "
            f"alive {own}={v['numAlives'][own]:.0f} {enemy}={v['numAlives'][enemy]:.0f} score={s:.3f}"
        )
    metrics = {
        "avg_score": round(score / n, 3),
        "avg_our_alive": round(our_alive / n, 2),
        "avg_enemy_alive": round(enemy_alive / n, 2),
        "games": len(data["details"]),
    }
    print(f"  {metrics}")
    return metrics


def summarize_paired(path: Path) -> dict:
    """seed 固定ペア評価（local_test/run_eval_paired.py の出力）を判定指標として読む.

    判定基準はペア評価（CLAUDE.md）。validate.py を直接叩くとシナリオが毎回変わるため、
    記録は `--paired` で行う。
    """

    if not path.exists():
        raise SystemExit(f"ペア評価ファイルが見つかりません: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics = data.get("metrics") or {}
    if metrics.get("avg_score") is None:
        raise SystemExit(f"metrics.avg_score がありません（別ファイルの可能性）: {path}")
    print(f"--- ペア評価（seed 固定）: {metrics.get('label') or path.name} ---")
    for row in data.get("rows", []):
        print(
            f"  {str(row.get('color', '')):<5} seed={str(row.get('seed', '')):<4} "
            f"{str(row.get('result', '')):<5} {str(row.get('endReason', '')):<12} "
            f"steps={str(row.get('step_count', '')):<6} "
            f"alive {row.get('our_alive')} / {row.get('enemy_alive')} score={row.get('score')}"
        )
    picked = {
        "avg_score": metrics.get("avg_score"),
        "avg_our_alive": metrics.get("avg_our_alive"),
        "avg_enemy_alive": metrics.get("avg_enemy_alive"),
        "games": metrics.get("games"),
    }
    print(f"  {picked}")
    return picked


def cmd_start(args) -> None:
    require_specialist(args.specialist)
    if load_state(args.specialist):
        print(f"セッションは既に開始済み: {state_path(args.specialist)}")
    else:
        save_state(args.specialist, {
            "specialist": args.specialist,
            "started": datetime.now().isoformat(timespec="seconds"),
            "assumptions": [],
            "hypotheses": [],
            "cycles": [],
        })
    print("チェックリスト:")
    print(f"  1. {FORMAT_MD.relative_to(REPO_ROOT).as_posix()} を読んだか（ログ構造の再発見を避ける）")
    print(f"  2. 現在の active specialist を確認したか（{ARGS_PATH.relative_to(REPO_ROOT).as_posix()}）")
    print("  3. 直近の計測で敗因（生存数・スコア）を特定したか")
    print("  4. 変更は1変数か、予測を hypothesis で記録したか")


def cmd_assumption(args) -> None:
    state = load_state(args.specialist)
    text = normalize_text(args.text)
    assumptions = state.setdefault("assumptions", [])
    if assumptions and assumptions[-1]["text"] == text:
        print(f"前提は既に記録済み（重複スキップ）: {text}")
        return
    assumptions.append({
        "text": text,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(args.specialist, state)
    print(f"前提を記録: {text}")


TESTED_VARIABLES_PATH = Path(__file__).with_name("tested_variables.json")


def load_tested_variables() -> dict:
    return json.loads(TESTED_VARIABLES_PATH.read_text(encoding="utf-8"))


def add_tested_variable(variable: str, values: str, result: str, refs: list[str]) -> None:
    """試験済みの変数を登録簿へ追加・更新する（記録漏れ防止）."""
    data = load_tested_variables()
    variables = data.setdefault("variables", {})
    prev = variables.get(variable, {})
    merged_values = values or prev.get("values", "")
    if values and prev.get("values") and values not in prev.get("values", ""):
        merged_values = f"{prev['values']}/{values}"
    merged_refs = list(dict.fromkeys([*(prev.get("refs") or []), *refs]))
    variables[variable] = {
        "values": merged_values,
        "result": result or prev.get("result", ""),
        "refs": merged_refs,
    }
    TESTED_VARIABLES_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def variable_of_hypothesis(state: dict, hypothesis_id: str) -> str:
    """仮説 id から変数名を引く（無ければ空文字）."""
    for h in state.get("hypotheses", []):
        if h.get("id") == hypothesis_id:
            return h.get("variable", "") or ""
    return ""


def warn_untracked_variable(state: dict, hypothesis_id: str) -> None:
    """紐付いた仮説の変数が登録簿に無いとき、追加コマンドを促す（記録漏れ防止）."""
    variable = variable_of_hypothesis(state, hypothesis_id)
    if not variable:
        return
    if variable in load_tested_variables().get("variables", {}):
        return
    print(f"⚠ 変数 {variable} がまだ登録簿（tested_variables.json）にありません。")
    print("  試験した変数は仮説の重複を防ぐため登録すること:")
    print(
        "  python analysis/tools/improvement_session.py tested-variable "
        f'--variable {variable} --values "<試験値>" --result "<結果>" '
        f'--refs "{hypothesis_id}"'
    )


def _card_fill_open_direction_vars() -> set:
    """card_fill.json の open/direction カードが検証入口として立てる変数名。"""
    path = REPO_ROOT / "tools" / "state_dashboard" / "card_fill.json"
    try:
        with open(path, encoding="utf-8") as f:
            cards = (json.load(f) or {}).get("cards", {})
    except (OSError, ValueError):
        return set()
    return {
        (c.get("variable_name") or "").strip()
        for c in cards.values()
        if c.get("variable_status") in ("open", "direction") and (c.get("variable_name") or "").strip()
    }


def check_variable_untested(variable: str, retest: str) -> None:
    """登録簿に載っている変数は仮説にできない（重複・再試験の防止）。
    card_fill の open/direction カードが検証入口として立てた変数は再試験許可する
    （pending側も同じ変数を保護している）。"""
    data = load_tested_variables()
    entry = data.get("variables", {}).get(variable)
    if entry is None:
        return
    if variable in _card_fill_open_direction_vars():
        print(f"※ 事実カード(open/direction)の変数 {variable} は検証入口なので再試験許可します")
        return
    if retest.strip():
        print(f"※ 試験済みの変数 {variable} を再試験します（理由: {retest}）")
        return
    refs = " / ".join(entry.get("refs", []))
    values = entry.get("values")
    result = entry.get("result")
    print(f"登録拒否: 変数 {variable} は試験済み（値: {values}）")
    print(f"  結果: {result}")
    print(f"  根拠: {refs}")
    print("同じ変数の仮説は立てない。別の変数を選ぶか、--retest に再試験の理由を書く。")
    raise SystemExit(2)


def _pending_variables(state: dict) -> set:
    """未検証（pending）の仮説が持つ変数名。同一変数の再登録を止める判定に使う。"""
    validated = {
        c.get("hypothesis")
        for c in state.get("cycles", [])
        if c.get("kind") == "validate" and c.get("hypothesis")
    }
    validated |= {r.get("hypothesis") for r in state.get("records", []) if r.get("hypothesis")}
    return {
        (h.get("variable") or "").strip()
        for h in state.get("hypotheses", [])
        if h.get("id") not in validated and (h.get("variable") or "").strip()
    }


def cmd_hypothesis(args) -> None:
    validate_record("inference", args.source)
    variable = getattr(args, "variable", "") or ""
    retest = getattr(args, "retest", "") or ""
    check_variable_untested(variable, retest)
    state = load_state(args.specialist)
    if variable and variable in _pending_variables(state):
        print(f"登録拒否: 変数 {variable} の仮説が未検証で残っています。")
        print("  同一変数の再登録は累積の温床になるので、既存の仮説を検証して消化してください。")
        raise SystemExit(2)
    text = normalize_text(args.text)
    state.setdefault("hypotheses", []).append({
        "id": next_hypothesis_id(state),
        "kind": "inference",
        "source": args.source,
        "variable": variable,
        "text": text,
        "at": datetime.now().isoformat(timespec="seconds"),
    })
    save_state(args.specialist, state)
    print(f"仮説（推論）を記録: {text}")
    print(f"  出所: {args.source}（{SOURCE_LABEL[args.source]}）")
    print("変更前に数値で予測を書くこと。書けない場合は変更しない。")


def cmd_verify(args) -> None:
    metrics = summarize("1ゲーム検証", run_games(args.games))
    state = load_state(args.specialist)
    state.setdefault("cycles", []).append(
        {
            "kind": "verify",
            "hypothesis": getattr(args, "hypothesis", "") or "",
            "metrics": metrics,
            "at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_state(args.specialist, state)
    stats_log = f"workspace/{RESULT_DIR}/0/log_0.json"
    print("意図した挙動（接近・射撃・回避）が起きているかログで確認すること:")
    print(f"  python tools/battle_analyzer/battle_stats.py {stats_log}")
    print(f"  python tools/battle_analyzer/trajectory.py {stats_log}")


def cmd_validate(args) -> None:
    if args.paired:
        path = Path(args.paired)
        if not path.is_absolute():
            path = REPO_ROOT / path
        metrics = summarize_paired(path)
        paired = True
    else:
        metrics = summarize("バッチ検証", run_games(args.games))
        paired = False
    state = load_state(args.specialist)
    state.setdefault("cycles", []).append(
        {
            "kind": "validate",
            "hypothesis": getattr(args, "hypothesis", "") or "",
            "metrics": metrics,
            "paired": paired,
            "at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    save_state(args.specialist, state)
    print("勝率ではなく挙動指標（avg_our_alive / avg_enemy_alive / avg_score）で判定すること。")
    if not paired:
        print("※ 判定基準は seed 固定ペア評価。--paired workspace/paired/<label>.json を推奨。")
    warn_untracked_variable(state, getattr(args, "hypothesis", "") or "")


def cmd_record(args) -> None:
    validate_record(args.kind, args.source)
    path = note_path(args.specialist)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = load_state(args.specialist)
    latest = state.get("cycles", [])[-1]["metrics"] if state.get("cycles") else {}
    record_id = next_record_id(path, args.kind)
    materials = [m for m in (getattr(args, "materials", "") or "").split("|") if m.strip()]
    with path.open("a", encoding="utf-8") as f:
        f.write(f"\n## {record_id} [{args.kind}/{args.source}] {datetime.now().isoformat(timespec='seconds')}\n")
        f.write(f"- 種別: {args.kind}（{KIND_LABEL[args.kind]}）\n")
        f.write(f"- 出所: {args.source}（{SOURCE_LABEL[args.source]}）\n")
        f.write(f"- 方向性: {args.direction}\n")
        if getattr(args, "hypothesis", ""):
            f.write(f"- 仮説: {args.hypothesis}\n")
        if materials:
            f.write(f"- 材料: {len(materials)} 件を紐付け（ダッシュボードの処理済み判定用）\n")
        f.write(f"- 変更: {args.changes}\n")
        f.write(f"- 検証: {args.verification}\n")
        if latest:
            f.write(f"- 指標: {json.dumps(latest, ensure_ascii=False)}\n")
        if args.next_steps:
            f.write(f"- 次の一手: {args.next_steps}\n")
    state.setdefault("records", []).append({
        "id": record_id,
        "kind": args.kind,
        "source": args.source,
        "hypothesis": getattr(args, "hypothesis", "") or "",
        "at": datetime.now().isoformat(timespec="seconds"),
        "materials": materials,
        "next_steps": args.next_steps or "",
    })
    save_state(args.specialist, state)
    print(f"記録しました: {path}")
    print(f"  {record_id} [{args.kind}/{args.source}] materials={len(materials)}")
    warn_untracked_variable(state, getattr(args, "hypothesis", "") or "")


def cmd_tested_variable(args) -> None:
    """試験済みの変数を登録簿へ記録する（仮説の重複・再試験の防止）."""
    refs = [r for r in (args.refs or "").split(",") if r.strip()]
    add_tested_variable(args.variable, args.values, args.result, refs)
    entry = load_tested_variables()["variables"][args.variable]
    print(f"登録簿を更新: {args.variable}")
    print(f"  値: {entry['values']}")
    print(f"  結果: {entry['result']}")
    print(f"  根拠: {' / '.join(entry['refs'])}")


def cmd_link(args) -> None:
    state = load_state(args.specialist)
    if not state:
        raise SystemExit(f"セッション未開始: {args.specialist}")
    records = state.get("records", [])
    if not records:
        raise SystemExit("記録がありません")
    target = getattr(args, "record", "") or ""
    rec = next((r for r in records if r.get("id") == target), None) if target else records[-1]
    if rec is None:
        raise SystemExit(f"記録が見つかりません: {target}")
    materials = [m for m in (args.materials or "").split("|") if m.strip()]
    seen = set(rec.setdefault("materials", []))
    added = 0
    for m in materials:
        if m not in seen:
            rec["materials"].append(m)
            seen.add(m)
            added += 1
    save_state(args.specialist, state)
    print(f"{rec['id']} に材料 {added} 件を紐付け（計 {len(rec['materials'])} 件）")


def cmd_deepen(args) -> None:
    state = load_state(args.specialist)
    if not state:
        raise SystemExit(f"セッション未開始: {args.specialist}")
    card_id = (getattr(args, "card_id", "") or "").strip()
    phrase = normalize_text(args.phrase) if args.phrase else ""
    if not card_id and not phrase:
        raise SystemExit("phrase か --card-id のどちらかを指定すること")
    findings = normalize_text(args.findings)
    entry = {
        "findings": findings,
        "at": datetime.now().isoformat(timespec="seconds"),
    }
    if card_id:
        entry["card_id"] = card_id
    if phrase:
        entry["phrase"] = phrase
    state.setdefault("deepened_materials", []).append(entry)
    save_state(args.specialist, state)
    label = card_id or phrase[:60]
    print(f"深掘りを記録: {label}")
    print(f"  発見: {findings[:80]}")


def cmd_todo(args) -> None:
    state = load_state(args.specialist)
    if not state:
        raise SystemExit(f"セッション未開始: {args.specialist}")
    validated = {
        c.get("hypothesis")
        for c in state.get("cycles", [])
        if c.get("kind") == "validate" and c.get("hypothesis")
    }
    print(f"未処理の宿題（{args.specialist}）：")
    n = 0
    print("■ 未検証の仮説:")
    pending = [h for h in state.get("hypotheses", []) if h.get("id") not in validated]
    for h in pending[-12:]:
        n += 1
        print(f"  {h.get('id')}: {(h.get('text') or '')[:60]}")
    print("■ 記録の次の一手（直近8件）:")
    recs = [r for r in state.get("records", []) if (r.get("next_steps") or "").strip()]
    if not recs:
        recs = _next_steps_from_note(args.specialist)
    for r in recs[-8:]:
        n += 1
        print(f"  {r.get('id')}: {(r.get('next_steps') or '')[:80]}")
    if n == 0:
        print("  なし。停滞時は未見seed評価か指標見直しへ。")


def _next_steps_from_note(name: str) -> list[dict]:
    """improvement.md から「次の一手」を拾う（state に無い古い記録用）."""
    path = note_path(name)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for section in re.split(r"^##\s+", text, flags=re.M)[1:]:
        rid = (section.split(maxsplit=1) or ["?"])[0]
        found = re.findall(r"^-\s*次の一手:\s*(.+)$", section, flags=re.M)
        if found and found[-1].strip():
            out.append({"id": rid, "next_steps": found[-1].strip()})
    return out


def cmd_check(args) -> None:
    state = load_state(args.specialist)
    if not state:
        print(f"セッション未開始: {args.specialist}")
        return
    print(f"specialist: {state.get('specialist')} / started: {state.get('started')}")
    print(f"  前提: {len(state.get('assumptions', []))} 件")
    hypotheses = state.get("hypotheses", [])
    print(f"  仮説（推論）: {len(hypotheses)} 件")
    records = state.get("records", [])
    by_kind: dict[str, int] = {}
    for item in records:
        by_kind[item["kind"]] = by_kind.get(item["kind"], 0) + 1
    detail = " / ".join(f"{kind}={by_kind.get(kind, 0)}" for kind in RECORD_KINDS)
    print(f"  記録: {len(records)} 件（{detail}）")
    unsourced = [item["id"] for item in hypotheses if not item.get("source")]
    if unsourced:
        print(f"  出所未記録の仮説: {', '.join(unsourced)}")
    path = note_path(args.specialist)
    print(f"  improvement.md: {'あり' if path.exists() else 'なし'}")


def main() -> None:
    # Windows 標準出力(cp932)でもヘルプ出力が失敗しないよう、argparse より前に切り替える
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError):
            pass
    parser = argparse.ArgumentParser(description="改善セッション支援")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("assumption")
    p.add_argument("text")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_assumption)

    p = sub.add_parser("hypothesis")
    p.add_argument("text")
    p.add_argument(
        "--source",
        required=True,
        choices=RECORD_SOURCES,
        help="仮説の根拠出处（log=対戦ログ/計測値, analysis=解析, code=コード, official=ルール）",
    )
    p.add_argument(
        "--variable",
        required=True,
        help="仮説の変数名（例: fireRangeKm）。analysis/tools/tested_variables.json に載っていれば登録を拒否する",
    )
    p.add_argument("--retest", default="", help="試験済みの変数を再試験する理由（指定時のみ登録を許可）")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_hypothesis)

    p = sub.add_parser("verify")
    p.add_argument("--games", type=int, default=1)
    p.add_argument("--hypothesis", default="", help="紐付ける仮説の id（例: N-002）。省略可")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("validate")
    p.add_argument("--games", type=int, default=3)
    p.add_argument(
        "--paired",
        default="",
        help="判定基準となる seed 固定ペア評価の JSON（workspace/paired/<label>.json）。"
        "指定すると対戦を再開せず、その指標を validate サイクルとして記録する",
    )
    p.add_argument("--hypothesis", default="", help="紐付ける仮説の id（例: N-002）。省略可")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("record")
    p.add_argument("--specialist", required=True)
    p.add_argument(
        "--kind",
        required=True,
        choices=RECORD_KINDS,
        help="rule=大会ルール由来の制約 / observation=実測事実 / inference=推論",
    )
    p.add_argument(
        "--source",
        required=True,
        choices=RECORD_SOURCES,
        help="根拠の出所。kind=rule は official のみ許可",
    )
    p.add_argument("--direction", default="")
    p.add_argument("--changes", default="")
    p.add_argument("--verification", default="")
    p.add_argument("--next-steps", dest="next_steps", default="")
    p.add_argument("--hypothesis", default="", help="紐付ける仮説の id（例: N-002）。省略可")
    p.add_argument("--materials", default="",
                   help="処理した事実カードの phrase を | 区切りで記録（ダッシュボードの処理済み判定用）")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("link")
    p.add_argument("--specialist", required=True)
    p.add_argument("--materials", required=True,
                   help="事実カードの phrase を | 区切りで指定")
    p.add_argument("--record", default="",
                   help="紐付ける記録 id（例: O-059）。省略時は最新")
    p.set_defaults(func=cmd_link)

    p = sub.add_parser("tested-variable")
    p.add_argument("--variable", required=True, help="試験したコード上の変数名（例: launchIntervalFrames）")
    p.add_argument("--values", default="", help="試験した値（例: 0/30）")
    p.add_argument("--result", default="", help="結果（例: 命中改善なし。0 を維持）")
    p.add_argument("--refs", default="", help="根拠（仮説 id・結果ファイル名。カンマ区切り）")
    p.set_defaults(func=cmd_tested_variable)

    p = sub.add_parser("deepen")
    p.add_argument("phrase", nargs="?", default="", help="深掘り対象の事実カードの phrase（--card-id とどちらか必須）")
    p.add_argument("findings", help="深掘りで分かったこと（例: trajectory で射撃距離 40-50km の命中率が低い）")
    p.add_argument("--card-id", default="", help="事実カードの安定 ID（例: metric:hit_rate）。phrase より優先")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_deepen)

    p = sub.add_parser("todo")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_todo)

    p = sub.add_parser("check")
    p.add_argument("--specialist", required=True)
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
