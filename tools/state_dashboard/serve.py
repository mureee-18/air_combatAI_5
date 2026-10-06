"""開発状況ダッシュボード（依存ゼロ / ローカル専用）.

このコンペの開発状態を1画面で可視化する:
    環境      Docker コンテナ、workspace 配置、repo とのドリフト
    提出      specialist、submit.zip、pre_submit_gate の判定
    評価      local_test/run_eval_paired.py の出力（workspace/paired/*.json）
    ログ      workspace/results*/ の世代と最新ログの挙動指標
    軌跡      自作エージェントのログから復元したレーダースコープ再生
    改善      analysis/agents/*/session_state.json
    git       ブランチ / 未コミット / 最新コミット
    コマンド  主要コマンドのコピーリスト

Usage:
    python tools/state_dashboard/serve.py              # http://127.0.0.1:8765
    python tools/state_dashboard/serve.py --open       # ブラウザを自動で開く
    python tools/state_dashboard/serve.py --once       # JSON を標準出力に吐いて終了（CI/テスト用）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import time
import webbrowser
import re
import zipfile
from pathlib import Path

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT / "workspace"
MYAGENT_DIR = WORKSPACE / "Agents" / "MyAgent"
INDEX_HTML = Path(__file__).resolve().parent / "index.html"
RULES_JSON = Path(__file__).resolve().parent / "rules.json"
TRAJECTORY_DIR = REPO_ROOT / "tools" / "battle_analyzer"
CACHE_EPOCH = REPO_ROOT / "analysis" / "ops" / "dashboard_cache_epoch.txt"
ALLOWED_SPECIALISTS = {"baseline"}
REQUIRED_ZIP_ENTRIES = ["__init__.py", "args.json", "config.json"]

COMMANDS = [
    {
        "group": "環境",
        "items": [
            {"title": "コンテナ起動（CPU）", "cmd": "docker compose up -d cpu"},
            {"title": "コンテナ停止", "cmd": "docker compose down"},
            {"title": "GPU コンテナで対戦", "cmd": "docker compose up -d gpu"},
            {"title": "依存関係の確認（コンテナ内）", "cmd": "python /repo/scripts/env_check.py"},
        ],
    },
    {
        "group": "評価",
        "items": [
            {
                "title": "通常の対戦（3戦）",
                "cmd": "python scripts/run_eval.py --games 3",
            },
            {
                "title": "パラメータ走査",
                "cmd": "python scripts/run_eval.py --games 3 --sweep fireRangeKm=25,35,50",
            },
            {
                "title": "seed 固定ペア評価（判定基準）",
                "cmd": 'docker exec atla5-cpu bash -lc "cd /workspace && python /repo/local_test/run_eval_paired.py '
                '--seeds 1,2,3 --colors both --label baseline --out /workspace/paired/baseline.json"',
            },
            {
                "title": "ログの挙動指標",
                "cmd": "python tools/battle_analyzer/battle_stats.py workspace/results/0/log_0.json",
            },
            {
                "title": "軌跡の復元（自作エージェントのログのみ）",
                "cmd": "python tools/battle_analyzer/trajectory.py workspace/results_tel/0/log_0.json",
            },
            {
                "title": "ログの整理（dry-run）",
                "cmd": "python tools/log_cleanup/cleanup.py --keep 3",
            },
        ],
    },
    {
        "group": "提出",
        "items": [
            {"title": "提出物のビルドと配置", "cmd": "python scripts/build_submission.py --deploy"},
            {
                "title": "zip の単体検証",
                "cmd": 'docker exec atla5-cpu bash -lc "python /repo/scripts/zip_check.py /repo/submission/submit.zip"',
            },
            {
                "title": "提出（ATLA5_SUBMIT_CONFIRM=1 必須）",
                "cmd": 'python tools/signate/cli.py submit submission/submit.zip --memo "..."',
            },
        ],
    },
    {
        "group": "改善セッション",
        "items": [
            {
                "title": "セッション開始",
                "cmd": "python analysis/tools/improvement_session.py start --specialist default",
            },
            {
                "title": "仮説の記録（変更前に必須）",
                "cmd": 'python analysis/tools/improvement_session.py hypothesis "..." --specialist default',
            },
            {
                "title": "検証（ペア評価）",
                "cmd": "python analysis/tools/improvement_session.py validate --specialist default --games 6",
            },
            {
                "title": "記録",
                "cmd": 'python analysis/tools/improvement_session.py record --specialist default --direction "..." '
                '--changes "..." --verification "..." --next-steps "..."',
            },
        ],
    },
    {
        "group": "品質",
        "items": [
            {"title": "テスト", "cmd": "pytest tests/ -q"},
            {"title": "lint", "cmd": "ruff check agent/ tools/ tests/ scripts/ analysis/ local_test/"},
            {
                "title": "提出前ゲート（ speciality 検査）",
                "cmd": "python tools/hooks/pre_submit_gate.py",
            },
        ],
    },
]

# 判定指標が「ダッシュボードのどこのデータから来るか」。仮説に書く --source もここから選ぶ。
METRIC_SOURCES = [
    {
        "metric": "avg_score / avg_our_alive / avg_enemy_alive / win-draw-loss / games",
        "label": "ペア評価（勝敗・スコアの唯一の判定基準）",
        "tab": "評価",
        "path": "workspace/paired/<label>.json",
        "source": "log",
        "source_label": "対戦ログ / 計測値",
        "command": (
            'docker exec atla5-cpu bash -lc "cd /workspace && '
            "python /repo/local_test/run_eval_paired.py "
            '--seeds 1,2,3 --colors both --label <label> --out /workspace/paired/<label>.json"'
        ),
        "note": "更新は 評価タブ の「seed 固定ペア評価（判定基準）」と同じコマンド。判定はこの値だけで行う。",
    },
    {
        "metric": "初探知 t / 初発射 t / 探知→初発の空白 / 総発射数 / 消費弾 / 敵方位の分散",
        "label": "軌跡（時系列・いつ撃ったか）",
        "tab": "軌跡",
        "path": "workspace/results*/**/log_*.json（自作エージェントのログのみ）",
        "source": "log",
        "source_label": "対戦ログ / 計測値",
        "command": "python tools/battle_analyzer/trajectory.py <log>",
        "note": "実測値（例: 初発 t=164 / 空白 147 秒）。戦っていない原因がここに出る。",
    },
    {
        "metric": "敵探知 回数 / 射撃指示 / 被弾警報 / 最近接距離 / 護衛対象機の発見",
        "label": "挙動指標（各機が何を見たか）",
        "tab": "ログ",
        "path": "workspace/results*/**/log_*.json",
        "source": "log",
        "source_label": "対戦ログ / 計測値",
        "command": "python tools/battle_analyzer/battle_stats.py <log>",
        "note": "射撃指示は発射を保証しない。発射数は軌跡タブの launch イベントで数える。",
    },
    {
        "metric": "推定敵位置の一致誤差・復元式の検証結果",
        "label": "復元・解析の検証値",
        "tab": "軌跡",
        "path": "tools/battle_analyzer/trajectory.py",
        "source": "analysis",
        "source_label": "解析結果・ダッシュボード",
        "command": "python tools/battle_analyzer/trajectory.py <log> --json",
        "note": "ログそのものの構造から導いた検証値。対戦ログ由来，但不是実測スコア。",
    },
    {
        "metric": "採点式（TIMEUP=0.5 / 0.6+ は撃墜時のみ）/ 初期配置 / 探知距離の制約",
        "label": "公式ルール",
        "tab": "ルール",
        "path": "workspace/src/fight.py, tools/state_dashboard/rules.json",
        "source": "official",
        "source_label": "公式ルール / シミュレータ実装",
        "command": "",
        "note": "推測で値を作らないこと。",
    },
    {
        "metric": "deploy() の制約（isLaunchableAt / _countFlyingMissiles / maxSimulShot）",
        "label": "自作コードの読み取り",
        "tab": "—",
        "path": "agent/strategy/agents/escort_hunter.py",
        "source": "code",
        "source_label": "自作コードの読み取り",
        "command": "",
        "note": "「発射できない」理由を切り分けるときに読む。",
    },
]

CUSTOM_METRICS_FILE = INDEX_HTML.parent / "custom_metrics.json"
CAUSE_BANK_FILE = INDEX_HTML.parent / "cause_bank.json"
METRIC_FROM_HINT = {
    "paired": "評価タブ / workspace/paired/<label>.json",
    "trajectory": "軌跡タブ / tools/battle_analyzer/trajectory.py",
    "logstats": "ログタブ / tools/battle_analyzer/battle_stats.py",
}
METRIC_FROM_TAB = {"paired": "評価", "trajectory": "軌跡", "logstats": "ログ"}


def _scalar(value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _min_of(value) -> float | None:
    """{機体名: 距離} や [距離] から最小値を取る."""

    if isinstance(value, dict):
        vals = [_scalar(v) for v in value.values()]
    elif isinstance(value, (list, tuple)):
        vals = [_scalar(v) for v in value]
    else:
        return _scalar(value)
    vals = [v for v in vals if v is not None]
    return min(vals) if vals else None


def _trajectory_values(traj: dict) -> dict:
    """軌跡の内部キーを『独自指標の ID と同じ名前』へ揃える."""

    if not traj:
        return {}
    out = {
        "first_detect": traj.get("first_detect"),
        "first_launch": traj.get("first_launch"),
        "first_launch_lag": traj.get("lag"),
        "launch_count": traj.get("launch_count"),
        "aircraft": traj.get("aircraft"),
        "bearing_spread": traj.get("spread_max"),
        "ammo_used": sum(
            max(0.0, (traj.get("ammo_start", {}).get(s) or 0) - (traj.get("ammo_end", {}).get(s) or 0))
            for s in traj.get("slots", [])
        ),
    }
    out["min_dist_km"] = _min_of(traj.get("min_dist"))
    out["lost_range_km"] = _scalar(traj.get("lost_max"))
    return out


def _logstats_values(stats: dict) -> dict:
    """挙動指標の agents 配列を『独自指標の ID』へ合計する."""

    if not stats or "error" in stats or not isinstance(stats.get("agents"), list):
        return {}
    out: dict = {}
    for key in ("fire_orders", "enemy_seen", "alerts"):
        vals = [_scalar(a.get(key)) for a in stats["agents"] if isinstance(a, dict)]
        vals = [v for v in vals if v is not None]
        if vals:
            out[key] = sum(vals)
    mins = [_scalar(a.get("min_dist")) for a in stats["agents"] if isinstance(a, dict)]
    mins = [v for v in mins if v is not None]
    if mins:
        out["min_dist_km"] = min(mins)
    return out


def _metric_snapshot(spec: dict, values: dict) -> dict:
    """定義 1 件に「今の値」と「どこで見たか」を付ける."""

    origin = spec.get("from", "paired")
    raw = values.get(spec.get("key") or spec.get("id"))
    value = _scalar(raw)
    target = _scalar(spec.get("target"))
    direction = spec.get("direction", "higher")
    status = "unknown"
    if value is not None and target is not None:
        reached = value >= target if direction == "higher" else value <= target
        status = "reached" if reached else "open"
    entry = dict(spec)
    entry.update(
        {
            "value": value,
            "target": target,
            "status": status,
            "direction": direction,
            "tab": METRIC_FROM_TAB.get(origin, "—"),
            "where": METRIC_FROM_HINT.get(origin, origin),
            "key": spec.get("key") or spec.get("id"),
        }
    )
    return entry


def collect_custom_metrics(paired: dict | None = None, target: str = "default") -> dict:
    """評価タブに出す『独自指標』。定義は custom_metrics.json に集約する."""

    defn = load_json(CUSTOM_METRICS_FILE) or {"version": 1, "metrics": []}
    rows = defn.get("metrics", [])
    paired = paired if paired is not None else collect_paired()
    try:
        newest_logs = collect_replays(limit=1)["entries"]
    except Exception:  # noqa: BLE001
        newest_logs = []
    traj = _trajectory_facts(newest_logs[0]["log"]) if newest_logs else {}
    stats = collect_logs().get("newest_stats") or {}

    paired_values: dict = {}
    files = [f for f in paired.get("files", []) if isinstance(f, dict)]
    pick = next((f for f in files if Path(str(f.get("name", ""))).stem == target), None)
    if pick is None:
        pick = next(
            (f for f in files if (f.get("metrics") or {}).get("label") == target), None
        )
    if pick is None:
        pick = files[-1] if files else None
    if pick:
        paired_values = {
            k: v for k, v in (pick.get("metrics") or {}).items() if _scalar(v) is not None
        }
    buckets = {
        "paired": paired_values,
        "trajectory": _trajectory_values(traj or {}),
        "logstats": _logstats_values(stats),
    }
    return {
        "store": str(CUSTOM_METRICS_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
        "note": defn.get("note", ""),
        "hints": [f"{k}: {v}" for k, v in METRIC_FROM_HINT.items()],
        "rows": [_metric_snapshot(r, buckets.get(r.get("from", "paired"), {})) for r in rows],
        "add_command": (
            'python tools/state_dashboard/add_metric.py --label "<指標名>" '
            "--from paired|trajectory|logstats --direction higher|lower "
            '--target <目標値> --source log|analysis|code|official --note "<見る理由>"'
        ),
        "list_command": "python tools/state_dashboard/add_metric.py --list",
    }


HYPOTHESIS_POLICY_FILE = INDEX_HTML.parent / "HYPOTHESIS_POLICY.md"


def collect_hypothesis_policy() -> dict:
    """仮説の立案方針（HYPOTHESIS_POLICY.md）と、指標一覧・記入ひな形を返す."""

    doc = HYPOTHESIS_POLICY_FILE
    text = doc.read_text(encoding="utf-8") if doc.exists() else ""
    sections: list[dict] = []
    current = None
    in_fence = False
    fence: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            in_fence = not in_fence
            if in_fence:
                fence = []
            elif current is not None:
                current["code"] = "\n".join(fence).strip()
            continue
        if in_fence:
            fence.append(line)
            continue
        if line.startswith("## "):
            current = {"title": line[3:].strip(), "items": [], "code": ""}
            sections.append(current)
        elif current is not None and line.strip().startswith("- "):
            current["items"].append(line.strip()[2:].strip())

    rules: list[dict] = []
    example = ""
    table: list[dict] = []
    for sec in sections:
        title = sec["title"]
        if "必ず守ること" in title:
            for item in sec["items"] or numbered_items(text, title):
                head, sep, rest = item.partition("。")
                if not sep:
                    head, rest = item, ""
                rules.append({"head": head.strip().strip("*"), "detail": rest.strip()})
        elif title.startswith("書き方の型"):
            for item in sec["items"]:
                key, _, rest = item.partition(":")
                if rest.strip():
                    rules.append({"head": key.strip(), "detail": rest.strip()})
        elif title.startswith("記入例"):
            example = sec["code"]
        elif "仮説が使う指標" in title:
            table = _policy_metric_rows(text)
    return {
        "file": str(HYPOTHESIS_POLICY_FILE.relative_to(REPO_ROOT)).replace("\\", "/"),
        "sections": sections,
        "rules": rules,
        "example": example,
        "metrics": table,
    }


def numbered_items(text: str, title: str) -> list[str]:
    """「## 必ず守ること」節の `1. ...` 行を取り出す."""

    out = []
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = title in line
            continue
        if not in_section:
            continue
        body = line.strip()
        if body[:1].isdigit() and ". " in body:
            out.append(body.split(". ", 1)[1].strip())
    return out


def _policy_metric_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        parts = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(parts) != 3:
            continue
        name = parts[0].strip("`")
        if not name or set(name) <= set("- "):
            continue
        if name in {"指標", "仮説に使える指標"}:
            continue
        rows.append({"name": name, "meaning": parts[1], "where": parts[2]})
    return rows


_cache: dict = {"at": 0.0, "payload": None}
_trajectory_cache: dict = {}
# collect_evidence() が計算した実測値を collect_causes() が再利用するための中置き
_evidence_derived: dict = {}
TTL_SECONDS = 15.0


def decode_output(raw: bytes) -> str:
    for enc in ("utf-8", "cp932", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 15) -> str | None:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or REPO_ROOT),
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return decode_output(proc.stdout or b"") + decode_output(proc.stderr or b"")


def run_status(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int | None, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd or REPO_ROOT),
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    return proc.returncode, (decode_output(proc.stdout or b"") + decode_output(proc.stderr or b"")).strip()


def human(size: float) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024 or unit == "TB":
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}TB"


def dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())


def file_info(path: Path) -> dict:
    if not path.exists():
        return {"path": path.relative_to(REPO_ROOT).as_posix(), "exists": False}
    stat = path.stat()
    return {
        "path": path.relative_to(REPO_ROOT).as_posix(),
        "exists": True,
        "size": stat.st_size,
        "size_h": human(stat.st_size),
        "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
    }


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def collect_environment() -> dict:
    containers = []
    docker_ps = run_cmd(
        ["docker", "ps", "--format", "{{.Names}}|{{.Status}}|{{.Image}}"],
        timeout=8,
    )
    docker_ok = docker_ps is not None
    if docker_ok:
        for line in docker_ps.strip().splitlines():
            parts = line.split("|")
            if len(parts) >= 3:
                containers.append({"name": parts[0], "status": parts[1], "image": parts[2]})

    repo_args = load_json(REPO_ROOT / "agent" / "args.json") or {}
    deployed_args = load_json(MYAGENT_DIR / "args.json")
    drift = None
    if deployed_args is not None:
        drift = {
            "args_match": deployed_args == repo_args,
            "config_match": (MYAGENT_DIR / "config.json").exists()
            and (MYAGENT_DIR / "config.json").read_bytes() == (REPO_ROOT / "agent" / "config.json").read_bytes(),
        }

    agents_dir = WORKSPACE / "Agents"
    agents = sorted(p.name for p in agents_dir.iterdir() if p.is_dir()) if agents_dir.exists() else []

    return {
        "host": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "numpy": _has_numpy(),
        },
        "docker": {"available": docker_ok, "containers": containers},
        "workspace": {
            "exists": WORKSPACE.exists(),
            "simulator_ready": (WORKSPACE / "src" / "fight.py").exists(),
            "common_dir": (WORKSPACE / "common").exists(),
            "size_h": human(dir_size(WORKSPACE)),
            "agents": agents,
        },
        "deploy_drift": drift,
        "repo_specialist": repo_args.get("specialist"),
    }


def _has_numpy() -> bool:
    try:
        import numpy  # noqa: F401

        return True
    except Exception:
        return False


def collect_submission() -> dict:
    args = load_json(REPO_ROOT / "agent" / "args.json") or {}
    specialist = args.get("specialist")
    zip_path = REPO_ROOT / "submission" / "submit.zip"

    entries = {}
    if zip_path.exists():
        try:
            with zipfile.ZipFile(zip_path) as zf:
                names = {Path(n).as_posix() for n in zf.namelist()}
            for required in REQUIRED_ZIP_ENTRIES:
                entries[required] = required in names
        except zipfile.BadZipFile:
            entries["__init__.py"] = False

    gate_code, gate = run_status([sys.executable, str(REPO_ROOT / "tools" / "hooks" / "pre_submit_gate.py")])

    return {
        "specialist": specialist,
        "specialist_allowed": specialist in ALLOWED_SPECIALISTS,
        "args": args,
        "zip": file_info(zip_path),
        "zip_entries": entries,
        "gate_ok": gate_code == 0,
        "gate_code": gate_code,
        "gate_output": (gate or "ゲートを実行できませんでした").splitlines()[-12:],
        "confirm_env": "ATLA5_SUBMIT_CONFIRM",
    }


def collect_paired() -> dict:
    paired_dir = WORKSPACE / "paired"
    files = []
    history = []
    if paired_dir.exists():
        for path in sorted(paired_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            data = load_json(path)
            if not isinstance(data, dict):
                continue
            metrics = data.get("metrics", {})
            stat = path.stat()
            mtime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
            files.append(
                {
                    "name": path.name,
                    "mtime": mtime,
                    "metrics": metrics,
                    "rows": data.get("rows", []),
                }
            )
            history.append(
                {
                    "name": path.name,
                    "mtime": mtime,
                    "metrics": metrics,
                }
            )
    best = None
    with_metrics = [f for f in files if f["metrics"].get("avg_score") is not None]
    if with_metrics:
        best = max(with_metrics, key=lambda f: f["metrics"]["avg_score"])
    history.sort(key=lambda x: (time.mktime(time.strptime(x["mtime"], "%Y-%m-%d %H:%M:%S")), x["name"]))
    return {"files": files, "best": best["name"] if best else None, "history": history}


def collect_logs() -> dict:
    generations = []
    candidates: list[Path] = []
    for path in sorted(WORKSPACE.glob("results*")):
        if not path.is_dir():
            continue
        logs = sorted(path.rglob("log_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        candidates.extend(logs)
        generations.append(
            {
                "name": path.name,
                "logs": len(logs),
                "size_h": human(dir_size(path)),
                "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime)),
                "newest": logs[0].relative_to(REPO_ROOT).as_posix() if logs else None,
            }
        )
    generations.sort(key=lambda g: g["mtime"], reverse=True)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    newest_stats = None
    fallback = None
    for log_path in candidates[:12]:
        stats = _log_stats(log_path)
        if stats is None or "error" in stats:
            continue
        if fallback is None:
            fallback = stats
        if any(a["enemy_seen"] or a["fire_orders"] for a in stats["agents"]):
            newest_stats = stats
            break
    newest_stats = newest_stats or fallback

    return {
        "generations": generations,
        "total_size_h": human(sum(dir_size(p) for p in WORKSPACE.glob("results*") if p.is_dir())),
        "newest_stats": newest_stats,
    }


def _log_stats(log_path: Path) -> dict | None:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "battle_analyzer"))
    try:
        import battle_stats

        steps, stats = battle_stats.collect(log_path)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}
    finally:
        sys.path.pop(0)
    agents = []
    for agent_id, s in sorted(stats.items()):
        agents.append(
            {
                "agent": agent_id,
                "enemy_seen": s["enemy"],
                "threat": s["threat"],
                "fire_orders": s["fire"],
                "escorted_seen": s["escorted"],
                "min_dist_km": round(s["minDist"], 1) if s["minDist"] is not None else None,
                "min_rmsls": s["mslsMin"],
            }
        )
    custom = any(a["enemy_seen"] or a["fire_orders"] for a in agents)
    return {
        "log": log_path.relative_to(REPO_ROOT).as_posix(),
        "steps": steps,
        "mode": "自作エージェント" if custom else "baseline / BenchMark",
        "agents": agents,
    }


def _trajectory_module():
    """tools/battle_analyzer/trajectory.py を import する（キャッシュ付き）."""

    cached = _trajectory_cache.get("module")
    if cached is not None:
        return cached
    sys.path.insert(0, str(TRAJECTORY_DIR))
    try:
        import trajectory
    finally:
        sys.path.pop(0)
    _trajectory_cache["module"] = trajectory
    return trajectory


def _log_candidates() -> list[Path]:
    paths: list[Path] = []
    for gen in sorted(WORKSPACE.glob("results*")):
        if gen.is_dir():
            paths.extend(gen.rglob("log_*.json"))
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)


def collect_replays(limit: int = 30) -> dict:
    """再生可能なログ（自作エージェント形式）の一覧を返す."""

    module = _trajectory_module()
    entries = []
    skipped = 0
    for path in _log_candidates():
        if len(entries) >= limit:
            break
        try:
            stat = path.stat()
            log_data = module.load_log(path)
        except OSError:
            continue
        except ValueError:
            skipped += 1
            continue
        if module.first_payload(log_data) is None:
            skipped += 1
            continue
        payload = module.first_payload(log_data) or {}
        own = payload.get("own") or []
        entries.append(
            {
                "log": path.relative_to(REPO_ROOT).as_posix(),
                "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                "age_s": int(time.time() - stat.st_mtime),
                "size_h": human(stat.st_size),
                "frames": len(log_data.get("observations") or []),
                "own_length": len(own),
                "has_ammo": len(own) >= 10,
            }
        )
    return {"entries": entries, "scanned_skipped": skipped, "limit": limit}


def replay_payload(log_rel: str) -> dict:
    """ログ 1 本の軌跡 JSON を返す。パスは repo 配下のみ許可する."""

    module = _trajectory_module()
    if not log_rel or "\x00" in log_rel:
        raise ValueError("log パラメータが空です")
    candidate = (REPO_ROOT / log_rel).resolve()
    try:
        candidate.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("repo 外のパスは指定できません") from exc
    if not candidate.name.startswith("log_") or candidate.suffix != ".json" or not candidate.is_file():
        raise ValueError("log_*.json のみ指定できます")
    if not module.is_replayable(candidate):
        raise ValueError("このログは軌跡再現できません（自作エージェントのログのみ対象）")
    return module.build_trajectory(candidate)


def collect_session(paired: dict | None = None) -> dict:
    base = REPO_ROOT / "analysis" / "agents"
    sessions = []
    if base.exists():
        for path in sorted(base.glob("*/session_state.json")):
            state = load_json(path)
            if not isinstance(state, dict):
                continue
            sessions.append(
                {
                    "specialist": state.get("specialist", path.parent.name),
                    "started": state.get("started"),
                    "assumptions": state.get("assumptions", []),
                    "hypotheses": state.get("hypotheses", []),
                    "cycles": state.get("cycles", []),
                    "records": state.get("records", []),
                }
            )
    submitted = (load_json(REPO_ROOT / "agent" / "args.json") or {}).get("specialist")
    target = sessions[-1]["specialist"] if sessions else submitted
    paired = paired if paired is not None else collect_paired()
    started = bool(_session_state(target))
    steps = collect_steps(target, sessions)
    current = next((s for s in steps if s["state"] == "current"), None)
    cycle_done = False
    if current is None and steps:
        # 全ステップ完了 = 1サイクル終了。次のサイクルは仮説から。
        # 「次に打つコマンド」はステップ一覧の枠で示すので、枠を 1 つ目に移す。
        # 残りのステップは次サイクルの "todo" とする（単調順序保持のため）
        cycle_done = True
        current = steps[0]
        current["state"] = "current"
        for step in steps[1:]:
            step["state"] = "todo"
        last = _last_record_summary(target)
        base = "サイクル完了。次のサイクルはここから"
        current["detail"] = f"{base}／{last}" if last else base
    nxt = {}
    if current:
        nxt = {
            "index": steps.index(current) + 1,
            "total": len(steps),
            "key": current["key"],
            "label": current["label"],
            "hint": current["hint"],
            "detail": current["detail"],
            "where": current.get("where", "powershell"),
            "command": current.get("command", ""),
            "command_label": current.get("command_label", ""),
            "command2": current.get("command2", ""),
            "command2_label": current.get("command2_label", ""),
            "files": current.get("files", []),
            "finished": cycle_done or current["state"] == "done",
        }
    evidence = collect_evidence(target)
    target_session = next((s for s in sessions if s.get("specialist") == target), {})
    return {
        "sessions": sessions,
        "target": target,
        "submitted": submitted,
        "started": started,
        "steps": steps,
        "next": nxt,
        "hypotheses": target_session.get("hypotheses", []),
        "cycles": target_session.get("cycles", []),
        "paired": paired,
        "metric_sources": METRIC_SOURCES,
        "policy": collect_hypothesis_policy(),
        "evidence": evidence,
        "causes": collect_causes(
            target,
            facts=_evidence_derived.get("facts"),
            stats=_evidence_derived.get("stats"),
            paired=_evidence_derived.get("paired"),
        ),
    }


def _session_state(name: str) -> dict:
    path = REPO_ROOT / "analysis" / "agents" / name / "session_state.json"
    state = load_json(path)
    return state if isinstance(state, dict) else {}


def _agent_dirty() -> list[str]:
    status = run_cmd(["git", "status", "--porcelain", "--", "agent"], timeout=15)
    return [line[3:] for line in (status or "").splitlines() if line.strip()]


def _last_record_summary(name: str) -> str:
    md = REPO_ROOT / "analysis" / "agents" / name / "improvement.md"
    if not md.exists():
        return ""
    try:
        text = md.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return ""
    blocks = re.split(r"^## (O|N)-\d+", text, flags=re.M)
    if len(blocks) < 2:
        return ""
    last = blocks[-1]
    lines = []
    for line in last.splitlines():
        sline = line.strip()
        if not sline or sline.startswith("## "):
            continue
        if (
            sline.startswith("- 種別:")
            or sline.startswith("- 出所:")
            or sline.startswith("- 指標:")
            or sline.startswith("- at:")
        ):
            continue
        if sline.startswith("- 方向性:"):
            lines.append(f"前回: {sline[6:].strip()}")
        elif sline.startswith("- 検証:"):
            lines.append(f"実測: {sline[4:].strip()}")
        elif sline.startswith("- 次の一手:"):
            lines.append(f"次候補: {sline[7:].strip()}")
        elif sline.startswith("- 変更:"):
            lines.append(f"変更: {sline[4:].strip()}")
    out = " / ".join(lines)
    if len(out) > 160:
        out = out[:157] + "…"
    return out


def collect_steps(target: str, sessions: list[dict]) -> list[dict]:
    """改善サイクルの現在位置と「次に打つコマンド」を、実データから判定する.

    `where` は実行場所（powershell=リポジトリ直下の PowerShell / editor=エディタ）。
    ダッシュボードは読み取り専用なので、コマンドは表示とコピーまでだけ。
    """

    if not target:
        return []
    state = _session_state(target)
    cmd_start = f"python analysis/tools/improvement_session.py start --specialist {target}"
    if not state:
        # セッション未開始なら start だけ案内する（他ステップはまだ意味を持たない）
        return [
            {
                "key": "start",
                "label": "セッションを開始する",
                "hint": "チェックリスト（ログ仕様の再発見防止・敗因の特定・1変数）が出力される",
                "state": "current",
                "detail": "未開始",
                "where": "powershell",
                "command": cmd_start,
                "command_label": "セッションを開始する",
                "files": [],
            }
        ]

    hypotheses = state.get("hypotheses", [])
    cycles = state.get("cycles", [])
    records = state.get("records", [])
    dirty = _agent_dirty()

    def cycle_kind(kind: str) -> bool:
        return any(c.get("kind") == kind for c in cycles)

    paired_out = f"workspace/paired/{target}.json"
    log_path = "workspace/results/0/log_0.json"

    def stamp(entries: list[dict], kind: str | None = None) -> str:
        picked = [e for e in entries if kind is None or e.get("kind") == kind]
        return max((e.get("at") or "" for e in picked), default="")

    last_validate = stamp(cycles, "validate")
    # record は「最後の validate より後」で才算する（前サイクルの記録で完了扱いにするのを防ぐ）
    record_done = bool(records) and (not last_validate or stamp(records) > last_validate)
    done = {
        "hypothesis": bool(hypotheses),
        # verify を記録しているなら変更済み。コミットで agent/ が clean になっても戻さない
        "change": bool(dirty) or cycle_kind("verify"),
        "verify": cycle_kind("verify"),
        "validate": cycle_kind("validate"),
        "record": record_done,
    }
    steps = [
        {
            "key": "hypothesis",
            "label": "仮説（出所つき）を登録",
            "hint": "下の「事実カード」を材料に、原因の当て推量と予測する指標の数値まで書く",
            "detail": f"{len(hypotheses)} 件" if hypotheses else "0 件（ここが最後の空白）",
            "where": "powershell",
            "command": (
                'python analysis/tools/improvement_session.py hypothesis '
                '"<事実に基づく因果と予測：指標を何から何に何倍にするか>" '
                f"--specialist {target} --source log"
            ),
            "command_label": "仮説を登録する（<…> を実際の文に置き換えて実行）",
            "files": [],
        },
        {
            "key": "change",
            "label": "1変数だけ変更",
            "hint": "同時に2つ変えると悪化時に原因が分からない。1ファイル1箇所だけ",
            "detail": f"変更中: {', '.join(dirty[:3])}" if dirty else "agent/ は未変更",
            "where": "editor",
            "command": "",
            "command_label": "",
            "files": [
                f"agent/strategy/specialists/{target}.py",
                "agent/args.json",
            ],
        },
        {
            "key": "verify",
            "label": "1戦で挙動確認",
            "hint": "1戦だけ回して、意図した行動（接近・射撃・回避）が起きたか見る",
            "detail": "検証済み（1戦）" if cycle_kind("verify") else "未実行",
            "where": "powershell",
            "command": f"python analysis/tools/improvement_session.py verify --specialist {target} --games 1",
            "command_label": "1戦を実行して検証結果を記録する",
            "command2": f"python tools/battle_analyzer/battle_stats.py {log_path}",
            "command2_label": "同じログの挙動指標を確認する",
            "hyp_arg": "command",
            "files": [],
        },
        {
            "key": "validate",
            "label": "seed 固定ペア評価",
            "hint": "勝率ではなく avg_score / avg_our_alive / avg_enemy_alive で判定",
            "detail": "検証済み（ペア評価）" if cycle_kind("validate") else "未実行",
            "where": "powershell",
            "command": (
                'docker exec atla5-cpu bash -lc "cd /workspace && '
                "python /repo/local_test/run_eval_paired.py "
                f'--seeds 1,2,3 --colors both --label {target} --out /workspace/paired/{target}.json"'
            ),
            "command_label": "ペア評価を実行する（同じ seed・両面）",
            "command2": (
                f"python analysis/tools/improvement_session.py validate "
                f"--specialist {target} --paired {paired_out}"
            ),
            "command2_label": "ペア評価の結果を記録する",
            "hyp_arg": "command2",
            "files": [],
        },
        {
            "key": "record",
            "label": "記録（kind/source つき）",
            "hint": "実測値と予測を improvement.md に残す",
            "detail": f"{len(records)} 件" if record_done else ("0 件（このサイクル分）" if records else "0 件"),
            "where": "powershell",
            "command": (
                f"python analysis/tools/improvement_session.py record --specialist {target} "
                '--kind observation --source log --direction "<やったこと>" '
                '--changes "<変更したファイルと変数>" --verification "<実測値>" '
                '--next-steps "<次で試す1変数>"'
            ),
            "command_label": "サイクルの結果を improvement.md に記録する（<…> を実測値に置き換えて実行）",
            "hyp_arg": "command",
            "files": [],
        },
    ]
    # 最初の未完了ステップだけを "current" にする（完了位置は常に先頭から連続する）
    state_of = {}
    reached = True
    for step in steps:
        if done.get(step["key"]):
            state_of[step["key"]] = "done"
        elif reached:
            state_of[step["key"]] = "current"
            reached = False
        else:
            state_of[step["key"]] = "todo"
    for step in steps:
        step["state"] = state_of[step["key"]]
    return steps


def _quote(text: str) -> str:
    """コマンド引数用にダブルクォートを除去する（Windows コマンドでも安全）。"""

    return " ".join(str(text).replace('"', "'").split())


def _known_constraints() -> list[dict]:
    """BATTLELOG_FORMAT.md の「既知の制約」節を構造化して読む（毎回調べ直さない）。

    `**太字**` で始まる行は前半がタイトル。それ以外は最初の文をタイトルにして、
    dropdown に空欄が出ないようにする。
    """

    doc = REPO_ROOT / "tools" / "battle_analyzer" / "BATTLELOG_FORMAT.md"
    if not doc.exists():
        return []
    text = doc.read_text(encoding="utf-8")
    if "## 4. 既知の制約" not in text:
        return []
    section = text.split("## 4. 既知の制約", 1)[1].split("\n## ", 1)[0]
    out = []
    for line in section.splitlines():
        line = line.strip()
        if not line.startswith("- "):
            continue
        body = line[2:].strip()
        if body.startswith("**") and "**" in body[2:]:
            title, detail = body[2:].split("**", 1)
            out.append({"title": title.strip(), "detail": detail.strip(" ：:")})
        else:
            # 太字タイトルが無い行は「最初の文」をタイトルにする（空 option を防ぐ）
            head, sep, tail = body.partition("。")
            title = head.strip() if head.strip() else body
            detail = (head + sep + tail).strip() if sep else body
            out.append({"title": title, "detail": detail})
    return out


def _trajectory_facts(log_rel: str) -> dict | None:
    """軌跡から「初探知/初発/被弾/包囲」の時系列を算出する."""

    try:
        payload = replay_payload(log_rel)
    except Exception:  # noqa: BLE001
        return None
    frames = payload["frames"]
    if not frames:
        return None

    events = payload["events"]
    first_detect = next((i for i, f in enumerate(frames) if f["enemy"]), None)
    first_launch = next((e["t"] for e in events if e["kind"] == "launch"), None)
    locks = [e["t"] for e in events if e["kind"] == "lock"]
    first_lock = locks[0] if locks else None
    lost = [e["t"] for e in events if e["kind"] == "lost"]
    launches = [e for e in events if e["kind"] == "launch"]

    warn_frames: dict[str, int] = {}
    min_dist: dict[str, float] = {}
    ammo_start: dict[str, float] = {}
    ammo_end: dict[str, float] = {}
    spread_max = 0.0
    spread_at = None
    for i, f in enumerate(frames):
        bearings = [e["bearing"] for e in f["enemy"]]
        if len(bearings) >= 2:
            spread = max(bearings) - min(bearings)
            if spread > spread_max:
                spread_max = spread
                spread_at = i
        for th in f["threat"]:
            warn_frames[th["slot"]] = warn_frames.get(th["slot"], 0) + 1
        for e in f["enemy"]:
            prev = min_dist.get(e["slot"])
            min_dist[e["slot"]] = e["dist"] if prev is None else min(prev, e["dist"])
        for slot, p in f["own"].items():
            if slot not in ammo_start:
                ammo_start[slot] = p["ammo"]
            ammo_end[slot] = p["ammo"]

    used = {e["slot"] for e in launches}
    lag = None
    if first_detect is not None and first_launch is not None:
        lag = first_launch - first_detect
    return {
        "log": log_rel,
        "frames": payload["frame_count"],
        "slots": payload["slots"],
        "first_detect": first_detect,
        "first_lock": first_lock,
        "first_launch": first_launch,
        "lag": lag,
        "launch_count": len(launches),
        "launched_slots": sorted(used),
        "ammo_start": ammo_start,
        "ammo_end": ammo_end,
        "warn_frames": warn_frames,
        "min_dist": min_dist,
        "spread_max": round(spread_max, 1),
        "spread_at": spread_at,
        "lost_t": lost,
        "result": payload.get("result") or {},
    }


def _paired_evidence() -> dict | None:
    paired = collect_paired()
    rows = []
    for f in paired["files"]:
        m = f.get("metrics") or {}
        if m.get("avg_score") is None:
            continue
        rows.append({"name": m.get("label") or f["name"], "file": f["name"], "metrics": m, "mtime": f["mtime"]})
    if len(rows) < 2:
        return None
    rows.sort(key=lambda r: r["metrics"]["avg_score"], reverse=True)
    best, worst = rows[0], rows[-1]
    gap = round(best["metrics"]["avg_score"] - worst["metrics"]["avg_score"], 3)
    return {"best": best, "worst": worst, "gap": gap, "rows": rows}


def collect_evidence(target: str) -> list[dict]:
    """仮説の材料になる『観測された事実』をカードで返す（すべて実データから算出）。

    読み取り専用。カードには「ここから立てられる仮説例」と、その仮説を
    improvement_session.py に登録するコマンドを添える。
    """

    cards: list[dict] = []
    specialist = target or "default"
    # collect_causes() が同じ実測値を再利用できるように残す（2 回計算しない）
    _evidence_derived.clear()
    _evidence_derived.update({"target": specialist})

    # 1) ペア評価の差分（最大の穴）
    paired = _paired_evidence()
    _evidence_derived["paired"] = paired
    if paired:
        worst, best = paired["worst"], paired["best"]
        wm, _ = worst["metrics"], best["metrics"]
        cards.append({
            "id": "paired",
            "kind": "observation",
            "source": "log",
            "title": f"{worst['name']} は {best['name']} に avg_score {paired['gap']} 差で劣る",
            "summary": (
                f"{worst['name']}: 自機生存 {wm.get('avg_our_alive')} / 敵生存 {wm.get('avg_enemy_alive')}。"
                "敵を1機も落とせず全滅しているなら、原因は『弾が少ない』ことではなく"
                "『有利な射撃機会を作れていない』ことにある。"
            ),
            "evidence": [
                {
                    "label": f"{entry['name']} avg_score",
                    "value": entry["metrics"].get("avg_score"),
                    "num": True,
                    "digits": 3,
                }
                for entry in paired["rows"]
            ] + [
                {"label": f"{worst['name']} 自機生存", "value": wm.get("avg_our_alive"), "num": True, "digits": 2},
                {"label": f"{worst['name']} 敵生存", "value": wm.get("avg_enemy_alive"), "num": True, "digits": 2},
                {"label": f"{worst['name']} 対戦数", "value": wm.get("games"), "num": True, "digits": 0},
            ],
            "hypothesis": (
                f"{worst['name']} の全滅は、初発タイミング・編隊の収束・回避のいずれかが主因。"
                "どれか1つを原因として1変数だけ変更して切り分ける。"
            ),
            "phrase": (
                f"{worst['name']} は avg_score {wm.get('avg_score')} / 自機生存 "
                f"{wm.get('avg_our_alive')} / 敵生存 {wm.get('avg_enemy_alive')}"
            ),
            "metric": "avg_score / avg_our_alive / avg_enemy_alive（ペア評価 6 戦）",
            "from_tab": "評価",
            "from_path": f"workspace/paired/{worst['file']}",
            "command": (
                'docker exec atla5-cpu bash -lc "cd /workspace && python /repo/local_test/run_eval_paired.py '
                f'--seeds 1,2,3 --colors both --label {worst["name"]} --out /workspace/paired/{worst["name"]}.json"'
            ),
            "command_label": f"{worst['name']} のペア評価を取り直す",
        })

    # 2) 軌跡の時系列（初探知 → 初発 → 被弾）
    try:
        newest = collect_replays(limit=1)["entries"]
    except Exception:  # noqa: BLE001
        newest = []
    facts = _trajectory_facts(newest[0]["log"]) if newest else None
    _evidence_derived["facts"] = facts
    if facts:
        lag_text = f"{facts['lag']} 秒" if facts["lag"] is not None else "—"
        ammo_used = sum(
            max(0.0, (facts["ammo_start"].get(s) or 0) - (facts["ammo_end"].get(s) or 0))
            for s in facts["slots"]
        )
        nearest = round(min(facts["min_dist"].values()), 1) if facts["min_dist"] else None
        cards.append({
            "id": "trajectory",
            "kind": "observation",
            "source": "log",
            "title": f"探知 t={facts['first_detect']} → 初発 t={facts['first_launch']}（空白 {lag_text}）",
            "summary": (
                f"敵の方位が最大 {facts['spread_max']}° まで散った（t={facts['spread_at']}）。"
                f"自機からの最短探知距離は {nearest} km。"
                f"被弾警報が出たのは各機 "
                f"{min(facts['warn_frames'].values()) if facts['warn_frames'] else 0}〜"
                f"{max(facts['warn_frames'].values()) if facts['warn_frames'] else 0} フレームのみで、"
                "応答が消えた直前に集中していた。"
            ),
            "evidence": [
                {"label": "初探知 t", "value": facts["first_detect"], "num": True, "digits": 0},
                {"label": "初射撃指示 t", "value": facts["first_lock"], "num": True, "digits": 0},
                {"label": "初発射 t", "value": facts["first_launch"], "num": True, "digits": 0},
                {"label": "探知→初発の空白", "value": facts["lag"], "num": True, "digits": 0},
                {"label": "総発射数", "value": facts["launch_count"], "num": True, "digits": 0},
                {"label": "発射した機体数", "value": len(facts["launched_slots"]), "num": True, "digits": 0},
                {"label": "消費した誘導弾", "value": ammo_used, "num": True, "digits": 0},
                {"label": "敵方位の最大分散", "value": facts["spread_max"], "num": True, "digits": 1},
                {"label": "最短探知距離[km]", "value": nearest, "num": True, "digits": 1},
                {"label": "応答終了 t", "value": max(facts["lost_t"]) if facts["lost_t"] else None,
                 "num": True, "digits": 0},
            ],
            "hypothesis": (
                f"探知から初発まで {lag_text}の空白が主因と仮説する。空白の原因が『射撃開始距離が遠い』"
                "（fireRangeKm）なのか『同時発射上限で次の発射を待っている』のか"
                "（maxSimulShot / 誘導弾の飛翔時間）なのかを、1変数だけ変えて切り分ける。"
            ),
            "phrase": (
                f"初探知 t={facts['first_detect']} に対し初発が t={facts['first_launch']}"
                f"（空白 {lag_text} / 総発射数 {facts['launch_count']}）"
            ),
            "metric": "初発 t / 総発射数 / 撃墜数（avg_enemy_alive の低下）",
            "from_tab": "軌跡",
            "from_path": facts["log"],
            "command": (
                f'python tools/battle_analyzer/trajectory.py {facts["log"]}'
            ),
            "command_label": "軌跡の要約をターミナルで確認",
        })

    # 3) 挙動指標（射撃指示 ≠ 発射 の切り分け）
    stats = collect_logs().get("newest_stats")
    _evidence_derived["stats"] = stats
    if stats and "error" not in stats and stats.get("mode") == "自作エージェント":
        agents = stats["agents"]
        cards.append({
            "id": "logstats",
            "kind": "observation",
            "source": "log",
            "title": f"最新ログの挙動指標（{stats['log']}）",
            "summary": (
                "射撃指示の回数は『発射した』ことを保証しない（isLaunchableAt が False の場合や、"
                "飛翔中の誘導弾で同時発射上限に達している場合は発射されない）。"
                "実際の発射は軌跡タブの launch イベント（残弾の減少）で確認する。"
            ),
            "evidence": [
                {
                    "label": f"{a['agent']} 号機",
                    "value": (
                        f"敵探知 {a['enemy_seen']} 回 / 射撃指示 {a['fire_orders']} 回"
                        f" / 最短 {a['min_dist_km']} km"
                    ),
                    "num": False,
                }
                for a in agents
            ],
            "hypothesis": (
                "射撃指示は出るのに発射イベントが少なければ、制約は方針（Policy）側ではなく "
                "deploy() の isLaunchableAt / _countFlyingMissiles 側にある。先にそこを疑う。"
            ),
            "metric": "fire_orders と launch イベント数の差",
            "phrase": (
                f"射撃指示 {sum(_scalar(a.get('fire_orders')) or 0 for a in agents)} 回に対して"
                f" 発射は {facts['launch_count'] if facts else '—'} 回"
            ),
            "from_tab": "ログ",
            "from_path": stats["log"],
            "command": f'python tools/battle_analyzer/battle_stats.py {stats["log"]}',
            "command_label": "挙動指標をターミナルで確認",
        })

    # 4) 前提（assumption）として登録すべき既知の制約
    constraints = _known_constraints()
    if constraints:
        cards.append({
            "id": "constraints",
            "kind": "assumption",
            "source": "code",
            "title": f"仮説の前提にすべき既知の制約 {len(constraints)} 件",
"summary": (
                "既知の制約を1行ずつ前提（assumption）として登録しておくと、"
                "『できないこと』を変更対象と誤って仮説に混ぜずに済む。"
            ),
            "items": [
                {
                    "title": c["title"],
                    "text": c["detail"],
                    "phrase": " ".join(x for x in (c["title"], c["detail"]) if x).strip(),
                    "command": (
                        'python analysis/tools/improvement_session.py assumption '
                        f'"{_quote(" ".join(x for x in (c["title"], c["detail"]) if x).strip())}" '
                        f"--specialist {specialist}"
                    ),
                }
                for c in constraints
            ],
            "phrase": f"既知の制約 {len(constraints)} 件は変更対象にしない",
        })

    # 5) 採点式が作る目標値（official）
    rules = collect_rules()
    scoring = next((g for g in rules.get("groups", []) if "採点" in g.get("title", "")), None)
    if scoring:
        cards.append({
            "id": "scoring",
            "kind": "rule",
            "source": "official",
            "title": "TIMEUP は必ず 0.5。0.6+ は撃墜（ELIMINATION）のときだけ",
            "summary": (
                "互角（TIMEUP）を保つだけではスコアは上がらない。順位を上げるには敵を1機以上倒すか、"
                "被弾で失点しないどちらか。採点式そのものはルールタブに記載。"
            ),
            "evidence": [
                {"label": "勝者のスコア", "value": "0.6 + 0.3 * hit_rate + time_bonus", "num": False},
                {"label": "敗者のスコア", "value": "1 - 勝者のスコア", "num": False},
                {"label": "TIMEUP", "value": "両者 0.5", "num": False},
            ],
            "hypothesis": None,
            "phrase": "TIMEUP はスコア 0.5、0.6 以上は撃墜時だけ",
            "metric": "avg_score が 0.5 を超えてるか（超えて初めて改善）",
            "from_tab": "ルール",
            "from_path": "workspace/src/fight.py, tools/state_dashboard/rules.json",
            "command": "",
            "command_label": "",
        })

    return cards


# ─────────────────────────────────────────────────────────────────────────
# 原因候補（仮説ビルダーの「原因」dropdown）
#
# 供給源が 1 つに固定されると、制約が増えるたびに選択肢が足りなくなる。
# そのため「その facts から機械的に出せそうな原因」「構造的な制約」
# 「前回の検証で外した・効いた原因」を別グループで束ねて返す。
# どれか 1 つが空でも、dropdown 自体は必ず埋まる。
# ─────────────────────────────────────────────────────────────────────────
CAUSE_GROUPS = (
    ("measured", "この事実から出せそうな原因"),
    ("constraint", "構造の制約（変えると壊れる）"),
    ("history", "前回の検証で出た原因"),
)
CAUSE_GROUP_KEYS = {k for k, _ in CAUSE_GROUPS}
RECORD_SOURCE_KEYS = {"log", "analysis", "code", "official"}


def _cause(label: str, phrase: str, group: str, source: str, note: str = "") -> dict:
    return {
        "label": label,
        "phrase": phrase,
        "group": group,
        "source": source,
        "note": note,
    }


def _measured_causes(facts: dict | None, stats: dict | None, paired: dict | None) -> list[dict]:
    """実測値から「ここが原因ならこう変わる」が言える原因候補 mechanically に作る。"""

    out: list[dict] = []

    # 空白（初探知→初発）が長い。射撃開始条件が高すぎるか、同時発射上限の可能性がある
    if facts and facts.get("lag") is not None and facts["lag"] >= 30:
        lag = facts["lag"]
        out.append(_cause(
            "射撃開始条件が高すぎて初発が遅い",
            f"敵を初めて探知してから {lag} 秒も発射していない。射撃開始距離や"
            "ロック解除条件が高すぎるため、射撃ループに入っていない",
            "measured", "log",
            "fireRangeKm など 1 変数だけ下げる",
        ))
        out.append(_cause(
            "同時発射上限で次の発射を待っている",
            f"探知から初発まで {lag} 秒空いている。誘導弾の飛翔中の数で"
            "同時発射数の上限に達し、次の射撃を待っている可能性がある",
            "measured", "log",
            "maxSimulShot / nMslSimul を 1 変数だけ変える",
        ))

    # 射撃指示 >> 発射 なら Policy 側ではなく deploy() の制約
    if stats and "error" not in stats and stats.get("mode") == "自作エージェント":
        orders = sum(_scalar(a.get("fire_orders")) or 0 for a in stats["agents"])
        launches = facts.get("launch_count") if facts else None
        if orders and launches is not None and orders > launches:
            out.append(_cause(
                "Policy は発射を指示しているが deploy() で止めている",
                f"射撃指示 {int(orders)} 回に対して発射は {int(launches)} 回。"
                "方針ではなく isLaunchableAt / _countFlyingMissiles の制約で止まっている",
                "measured", "code",
                "isLaunchableAt 側の条件を読む",
            ))

    # 自機全滅 かつ 敵生存も高い → 「倒せていない」
    if paired:
        m = paired["worst"]["metrics"]
        ours, theirs = m.get("avg_our_alive"), m.get("avg_enemy_alive")
        if ours is not None and ours == 0 and (theirs or 0) >= 3:
            out.append(_cause(
                "有利な射撃機会を作れていない（交戦距離・タイミング）",
                f"自機生存 {ours} / 敵生存 {theirs}。敵を1機も倒せないので、"
                "距離や迎撃タイミングの作り方に問題がある",
                "measured", "log",
                "最短交戦距離 min_dist_km を読む",
            ))
        # 敵を倒せているのに自機全滅 → 回避が効いていない
        if ours is not None and ours == 0 and (theirs or 4) < 3:
            out.append(_cause(
                "回避が間に合わず被弾で全滅している",
                f"敵生存 {theirs} に対して自機生存 {ours}。敵は倒せているのに"
                "被弾で全滅しており、被弾後の回避が効いていない",
                "measured", "code",
                "被弾警報の距離依存の扱いを見る",
            ))

    return out


def _history_causes(target: str) -> list[dict]:
    """前回までの記録（improvement.md）から原因候補を拾う。

    「検証」に書いた実測と「次の一手」に書いた候補は、次のサイクルでも
    そのまま原因候補として使えるので、毎回選び直す手間を省く。
    """

    md = REPO_ROOT / "analysis" / "agents" / (target or "default") / "improvement.md"
    if not md.exists():
        return []
    try:
        text = md.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return []
    blocks = re.split(r"^## (O|N)-\d+", text, flags=re.M)
    out: list[dict] = []
    seen: set[str] = set()
    for i in range(1, len(blocks) - 1, 2):
        body = blocks[i + 1]
        head = blocks[i].split("]")[0].strip()
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("- 次の一手:") or s.startswith("- 検証:"):
                payload = s.split(":", 1)[1].strip().rstrip("。")
                if len(payload) < 6 or payload in seen:
                    continue
                seen.add(payload)
                label = "前回候補" if s.startswith("- 次の一手") else "前回実測"
                out.append(_cause(
                    f"{label}: {payload[:28]}{'…' if len(payload) > 28 else ''}",
                    payload,
                    "history", "log",
                    f"{head} の記録",
                ))
    return out[:6]


def collect_causes(target: str, facts: dict | None = None,
                   stats: dict | None = None, paired: dict | None = None) -> dict:
    """原因候補をグループ付きで返す（dropdown 用）。読み取り専用。

    供給源は 4 つ。どれか 1 つが空でもdropdown は必ず埋まる:
      measured   - 実測値から機械的に生成（`_measured_causes`）
      constraint - BATTLELOG_FORMAT.md の既知の制約
      history    - 前回の記録（improvement.md）
      custom     - cause_bank.json（add_cause.py で追加）
    """

    measured = _measured_causes(facts, stats, paired)
    constraint = [
        _cause(c["title"], c["detail"], "constraint", "code")
        for c in _known_constraints()
        if c.get("title")
    ]
    history = _history_causes(target)

    custom: list[dict] = []
    bank = load_json(CAUSE_BANK_FILE)
    for c in (bank or {}).get("causes", []) if isinstance(bank, dict) else []:
        if not isinstance(c, dict) or not c.get("label"):
            continue
        group = c.get("group") if c.get("group") in CAUSE_GROUP_KEYS else "measured"
        custom.append(_cause(
            c["label"], c.get("phrase") or c["label"], group,
            c.get("source") if c.get("source") in RECORD_SOURCE_KEYS else "log",
            c.get("note", ""),
        ))

    by_group = {
        "measured": measured + [c for c in custom if c["group"] == "measured"],
        "constraint": constraint + [c for c in custom if c["group"] == "constraint"],
        "history": history + [c for c in custom if c["group"] == "history"],
    }
    return {
        "groups": [{"key": k, "label": v} for k, v in CAUSE_GROUPS],
        "by_group": by_group,
        "rows": [c for g in CAUSE_GROUPS for c in by_group[g[0]]],
        "counts": {k: len(v) for k, v in by_group.items()},
        "hint": (
            "候補に無い原因でも『手で書く』欄は常に使える。"
            "その場で定義を残すと次回から選べる（下の登録コマンド）。"
        ),
        "add_command": (
            'python tools/state_dashboard/add_cause.py --label "<短い名前>" '
            '--phrase "<仮説に入れる一文>" --group measured --source log'
        ),
    }


def collect_git() -> dict:
    branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], timeout=10)
    head = run_cmd(["git", "log", "-1", "--format=%h %s"], timeout=10)
    remote = run_cmd(["git", "remote", "get-url", "origin"], timeout=10)
    status = run_cmd(["git", "status", "--porcelain"], timeout=20)
    upstream = run_cmd(["git", "rev-parse", "--abbrev-ref", "@{u}"], timeout=10)
    ahead_behind = run_cmd(["git", "rev-list", "--left-right", "--count", "@{u}...HEAD"], timeout=10)
    recent = run_cmd(["git", "log", "-5", "--format=%h %ad %s", "--date=short"], timeout=10)

    entries = [line for line in (status or "").splitlines() if line.strip()]
    counts = {"modified": 0, "untracked": 0, "other": 0}
    for line in entries:
        if line.startswith("??"):
            counts["untracked"] += 1
        elif line[:2].strip() and "M" in line[:2]:
            counts["modified"] += 1
        else:
            counts["other"] += 1

    ab = None
    if ahead_behind:
        parts = ahead_behind.split()
        if len(parts) == 2:
            ab = {"behind": int(parts[0]), "ahead": int(parts[1])}

    return {
        "branch": (branch or "").strip(),
        "head": (head or "").strip(),
        "remote": (remote or "").strip(),
        "upstream": (upstream or "").strip(),
        "ahead_behind": ab,
        "dirty": counts,
        "recent": [line for line in (recent or "").splitlines() if line.strip()],
    }


def collect_rules() -> dict:
    data = load_json(RULES_JSON) or {}
    data.setdefault("meta", {})
    data.setdefault("groups", [])
    data["source_files"] = {
        "fight.py": (REPO_ROOT / "workspace" / "src" / "fight.py").exists(),
        "mission_config": (WORKSPACE / "common" / "R8_contest_youth_mission_config.json").exists(),
    }
    return data


def collect_summary() -> dict:
    session = collect_session()
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "repo_root": str(REPO_ROOT),
        "environment": collect_environment(),
        "submission": collect_submission(),
        "paired": session["paired"],
        "custom_metrics": collect_custom_metrics(session["paired"], session["target"]),
        "logs": collect_logs(),
        "session": session,
        "git": collect_git(),
        "rules": collect_rules(),
        "commands": COMMANDS,
    }


def get_summary(force: bool = False) -> dict:
    now = time.time()
    if not force and _cache["payload"] and now - _cache["at"] < TTL_SECONDS:
        return _cache["payload"]
    payload = collect_summary()
    _cache.update({"at": now, "payload": payload})
    return payload


def asset_sig(path: Path) -> str:
    """ファイル識別子（mtime + サイズ）。無いファイルは空文字."""

    if not path.exists():
        return ""
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def build_id() -> str:
    """ダッシュボードのビルド ID.

    index.html / rules.json の mtime と analysis/ops/dashboard_cache_epoch.txt を
    まとめてハッシュする。cache_bump.py が epoch を更新すると ID が変わる。
    """

    epoch = CACHE_EPOCH.read_text(encoding="utf-8").strip() if CACHE_EPOCH.exists() else ""
    raw = "|".join([asset_sig(INDEX_HTML), asset_sig(RULES_JSON), epoch])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def index_body(build: str) -> bytes:
    """index.html にビルド ID を注入して返す（/meta に埋め込む）."""

    html = INDEX_HTML.read_text(encoding="utf-8")
    tag = f'<meta name="x-build" content="{build}">'
    if '<meta name="x-build"' in html:
        return html.encode("utf-8")
    if "<head>" in html:
        return html.replace("<head>", f"<head>{tag}", 1).encode("utf-8")
    return (tag + html).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:  # noqa: A002
        return

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        route = self.path.split("?", 1)[0]
        if route in ("/", "/index.html"):
            if INDEX_HTML.exists():
                self._send(200, index_body(build_id()), "text/html; charset=utf-8")
            else:
                self._send(404, b"index.html not found", "text/plain; charset=utf-8")
            return
        if route == "/api/health":
            self._send(200, json.dumps({"ok": True}).encode(), "application/json; charset=utf-8")
            return
        if route == "/api/build":
            body = json.dumps({"build": build_id()}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        if route == "/api/summary":
            force = "force=1" in self.path
            payload = get_summary(force=force)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        if route == "/api/replays":
            try:
                payload = collect_replays()
                status = 200
            except Exception as exc:  # noqa: BLE001
                payload = {"error": str(exc)}
                status = 500
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(status, body, "application/json; charset=utf-8")
            return
        if route == "/api/replay":
            params = parse_qs(urlparse(self.path).query)
            log_rel = (params.get("log") or [""])[0]
            try:
                payload = replay_payload(log_rel)
                status = 200
            except ValueError as exc:
                payload = {"error": str(exc)}
                status = 400
            except Exception as exc:  # noqa: BLE001
                payload = {"error": str(exc)}
                status = 500
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send(status, body, "application/json; charset=utf-8")
            return
        if route == "/api/git":
            body = json.dumps({
                "branch": "main",
                "head": "",
                "remote": "",
                "upstream": "",
                "ahead_behind": None,
                "dirty": {"modified": 0, "untracked": 0, "other": 0},
                "recent": [],
            }, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        if route == "/api/commands":
            body = json.dumps({"groups": []}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        if route == "/api/rules":
            body = json.dumps([], ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        if route == "/api/policy":
            body = json.dumps({}, ensure_ascii=False).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        self._send(404, json.dumps({"error": "not found"}).encode(), "application/json; charset=utf-8")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="開発状況ダッシュボード")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="起動時にブラウザを開く")
    parser.add_argument("--once", action="store_true", help="JSON を標準出力に吐いて終了（CI/テスト用）")
    args = parser.parse_args()

    if args.once:
        print(json.dumps(collect_summary(), ensure_ascii=False, indent=2))
        return

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"state dashboard: {url}  (Ctrl+C で停止)")
    if args.open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    if shutil.which("git") is None:
        print("warning: git が見つかりません（git タブは空になります）", file=sys.stderr)
    main()