r"""定期ヘルスチェック（kaggriculture の tools/ops/healthcheck.py を本コンペ用に移植）.

読み取り専用で以下を点検し、1行を analysis/ops/heartbeat.log へ追記する:
    - ダッシュボード HTTP（--port の既定 8765）の生存確認
    - Docker コンテナ atla5-cpu / atla5-gpu の状態
    - git のブランチ / 未コミット数 / upstream との差分
    - 主要 JSON が parse できるか
    - リポジトリのあるドライブの空き容量

注意:
    - 標準ライブラリのみ。docker / git が見つからない場合はその項目だけを「?」にする
    - 終了コードは常に 0（異常はログ内容で表現する）
    - `--restart` を明示したときだけダッシュボードを再起動する（既定は読み取り専用）

定期実行は Windows タスクスケジューラに手動で登録する（リポジトリのパスを <> で囲む）:
    schtasks /Create /TN "AirCombatAI5Health" /SC MINUTE /MO 10 /F /TR "<python> <repo>\tools\ops\healthcheck.py"

Usage:
    python tools/ops/healthcheck.py
    python tools/ops/healthcheck.py --port 8765 --no-log
    python tools/ops/healthcheck.py --restart
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HEARTBEAT_LOG = REPO_ROOT / "analysis" / "ops" / "heartbeat.log"
CONTAINERS = ["atla5-cpu", "atla5-gpu"]
WATCHED_JSON = [
    "agent/args.json",
    "agent/config.json",
    "tools/signate/config.json",
    "tools/state_dashboard/rules.json",
]


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def http_ok(url: str, timeout: float = 3.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as res:
            return res.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def run_cmd(cmd: list[str], timeout: int = 15) -> str | None:
    if shutil.which(cmd[0]) is None:
        return None
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace").strip()


def dashboard_state(port: int, restart: bool = False) -> str:
    url = f"http://127.0.0.1:{port}/api/health"
    if http_ok(url):
        return f"dashboard={port}:up"
    if not restart:
        return f"dashboard={port}:down"
    serve = REPO_ROOT / "tools" / "state_dashboard" / "serve.py"
    subprocess.Popen(
        [sys.executable, str(serve), "--port", str(port)],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    return f"dashboard={port}:{'restarted' if http_ok(url) else 'restart-failed'}"


def docker_state() -> str:
    if shutil.which("docker") is None:
        return "docker=?"
    out = run_cmd(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"], timeout=30)
    if out is None:
        return "docker=query-failed"
    running = {}
    for line in out.splitlines():
        parts = line.split("\t", 1)
        if len(parts) == 2:
            running[parts[0].strip()] = parts[1].strip()
    bits = []
    for name in CONTAINERS:
        bits.append(f"{name}={running.get(name, 'not-running')}")
    return " ".join(bits)


def git_state() -> str:
    branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch is None:
        return "git=?"
    status = run_cmd(["git", "status", "--porcelain"]) or ""
    changed = len([line for line in status.splitlines() if line.strip()])
    upstream = run_cmd(["git", "rev-list", "--left-right", "--count", "@{upstream}...HEAD"])
    return f"git={branch} dirty={changed}" + (f" ahead_behind={upstream.replace(chr(9), '/')}" if upstream else "")


def json_state() -> str:
    bad = []
    for rel in WATCHED_JSON:
        path = REPO_ROOT / rel
        if not path.exists():
            bad.append(f"{rel}:missing")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            bad.append(f"{rel}:broken")
    return "json=ok" if not bad else "json=bad(" + ",".join(bad) + ")"


def disk_state() -> str:
    usage = shutil.disk_usage(REPO_ROOT)
    return f"disk_free={usage.free / 1024**3:.1f}GB"


def collect(port: int, restart: bool = False) -> dict:
    return {
        "at": datetime.now().isoformat(timespec="seconds"),
        "dashboard": dashboard_state(port, restart=restart),
        "docker": docker_state(),
        "git": git_state(),
        "json": json_state(),
        "disk": disk_state(),
    }


def heartbeat_line(result: dict) -> str:
    return " ".join(
        [
            result["at"],
            result["dashboard"],
            result["docker"],
            result["git"],
            result["json"],
            result["disk"],
        ]
    )


def append_heartbeat(line: str) -> Path:
    HEARTBEAT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with HEARTBEAT_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return HEARTBEAT_LOG


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="開発環境の定期ヘルスチェック")
    parser.add_argument("--port", type=int, default=8765, help="ダッシュボードのポート")
    parser.add_argument("--restart", action="store_true", help="ダッシュボードが落ちていれば再起動する")
    parser.add_argument("--no-log", action="store_true", help="heartbeat.log に追記しない")
    parser.add_argument("--json", action="store_true", help="JSON で出力する")
    args = parser.parse_args()

    result = collect(args.port, restart=args.restart)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    if not args.no_log:
        append_heartbeat(heartbeat_line(result))
    sys.exit(0)


if __name__ == "__main__":
    main()
