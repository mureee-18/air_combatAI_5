import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def run(args):
    exe = shutil.which("signate")
    if exe is None:
        print("signate が見つかりません。uv tool install signate を実行してください")
        raise SystemExit(1)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    result = subprocess.run([exe] + args, capture_output=True, env=env)
    if result.stdout:
        sys.stdout.write(result.stdout.decode("utf-8", errors="replace"))
    if result.stderr:
        sys.stdout.write(result.stderr.decode("utf-8", errors="replace"))
    return result.returncode


def main():
    parser = argparse.ArgumentParser(prog="signate-tools")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="ブラウザで Google サインイン")
    sub.add_parser("tasks", help="課題一覧を表示")
    sub.add_parser("files", help="配布ファイル一覧を表示")

    dl = sub.add_parser("download", help="ファイルをダウンロード")
    dl.add_argument("file_key")
    dl.add_argument("--path")

    sm = sub.add_parser("submit", help="提出する")
    sm.add_argument("path")
    sm.add_argument("--memo")

    args = parser.parse_args()
    cfg = load_config()

    if args.command == "login":
        raise SystemExit(run(["google-login"]))
    if args.command == "tasks":
        raise SystemExit(run(["task-list", f"--competition_key={cfg['competition_key']}"]))
    if args.command == "files":
        raise SystemExit(run(["file-list", f"--task_key={cfg['task_key']}"]))
    if args.command == "download":
        cmd = ["download", f"--task_key={cfg['task_key']}", f"--file_key={args.file_key}"]
        if args.path:
            cmd.append(f"--path={args.path}")
        raise SystemExit(run(cmd))
    if args.command == "submit":
        cmd = ["submit", f"--task_key={cfg['task_key']}", f"--path={args.path}"]
        if args.memo:
            cmd.append(f"--memo={args.memo}")
        raise SystemExit(run(cmd))


if __name__ == "__main__":
    main()
