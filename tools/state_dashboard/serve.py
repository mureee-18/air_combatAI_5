"""開発状況ダッシュボード（依存ゼロ / ローカル専用）.

このコンペの開発状態を1画面で可視化する:
    環境      Docker コンテナ、workspace 配置、repo とのドリフト
    提出      specialist、submit.zip、pre_submit_gate の判定
    評価      local_test/run_eval_paired.py の出力（workspace/paired/*.json）
    ログ      workspace/results*/ の世代と最新ログの挙動指標
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
import json
import platform
import shutil
import subprocess
import sys
import time
import webbrowser
import zipfile
from pathlib import Path

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = REPO_ROOT / "workspace"
MYAGENT_DIR = WORKSPACE / "Agents" / "MyAgent"
INDEX_HTML = Path(__file__).resolve().parent / "index.html"
RULES_JSON = Path(__file__).resolve().parent / "rules.json"
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

_cache: dict = {"at": 0.0, "payload": None}
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
        return {"path": str(path.relative_to(REPO_ROOT)), "exists": False}
    stat = path.stat()
    return {
        "path": str(path.relative_to(REPO_ROOT)),
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
    if paired_dir.exists():
        for path in sorted(paired_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            data = load_json(path)
            if not isinstance(data, dict):
                continue
            metrics = data.get("metrics", {})
            stat = path.stat()
            files.append(
                {
                    "name": path.name,
                    "mtime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
                    "metrics": metrics,
                    "rows": data.get("rows", []),
                }
            )
    best = None
    with_metrics = [f for f in files if f["metrics"].get("avg_score") is not None]
    if with_metrics:
        best = max(with_metrics, key=lambda f: f["metrics"]["avg_score"])
    return {"files": files, "best": best["name"] if best else None}


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
                "newest": str(logs[0].relative_to(REPO_ROOT)) if logs else None,
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
                "min_dist_km": s["minDist"],
                "min_rmsls": s["mslsMin"],
            }
        )
    custom = any(a["enemy_seen"] or a["fire_orders"] for a in agents)
    return {
        "log": str(log_path.relative_to(REPO_ROOT)),
        "steps": steps,
        "mode": "自作エージェント" if custom else "baseline / BenchMark",
        "agents": agents,
    }


def collect_session() -> dict:
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
                }
            )
    return {"sessions": sessions}


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
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "repo_root": str(REPO_ROOT),
        "environment": collect_environment(),
        "submission": collect_submission(),
        "paired": collect_paired(),
        "logs": collect_logs(),
        "session": collect_session(),
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
                self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
            else:
                self._send(404, b"index.html not found", "text/plain; charset=utf-8")
            return
        if route == "/api/health":
            self._send(200, json.dumps({"ok": True}).encode(), "application/json; charset=utf-8")
            return
        if route == "/api/summary":
            force = "force=1" in self.path
            payload = get_summary(force=force)
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
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