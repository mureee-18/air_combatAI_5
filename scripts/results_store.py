"""評価結果の置き場 results/ を読み書きする。

1回の評価 = results/runs/<run_id>/。試合ごとに games/<opponent>_<color>_<seed>.json を書き、
finish_run で games.jsonl にまとめて manifest.json の status を complete にする。complete の run は書き換えない。

    python scripts/results_store.py validate results/
    python scripts/results_store.py import-legacy /workspace/research/eval/pool --rename V6=hybrid_v6
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
RUNS = RESULTS / "runs"
SCHEMA_DIR = RESULTS / "schema"
SCHEMA_VERSION = 1
_ALPHABET = string.ascii_lowercase + string.digits
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


class CompleteRunError(RuntimeError):
    pass


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", text.lower()).strip("_") or "anon"


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_info() -> dict:
    status = _git("status", "--porcelain")
    return {"sha": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "dirty": None if status is None else bool(status)}


def new_run_id(worker: str, sha: str | None = None) -> str:
    """<UTC 時刻>-<worker>-<short sha>-<乱数6文字>。"""
    sha = sha or _git("rev-parse", "--short=7", "HEAD") or "nosha"
    rand = "".join(secrets.choice(_ALPHABET) for _ in range(6))
    return f"{_now():%Y%m%dT%H%M%SZ}-{_slug(worker)}-{sha[:7]}-{rand}"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def tree_sha256(directory: Path) -> str:
    """ディレクトリ内のファイル（__pycache__ を除く）のパスと中身から作るハッシュ。"""
    h = hashlib.sha256()
    for path in sorted(Path(directory).rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            h.update(path.relative_to(directory).as_posix().encode() + b"\0" + sha256_bytes(path.read_bytes()).encode())
    return h.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n"


def read_manifest(run_dir: Path) -> dict:
    return json.loads((Path(run_dir) / "manifest.json").read_text(encoding="utf-8"))


def _refuse_complete(run_dir: Path) -> None:
    if (Path(run_dir) / "manifest.json").exists() and read_manifest(run_dir).get("status") == "complete":
        raise CompleteRunError(f"run is complete and append-only: {run_dir}")


def start_run(worker: str, candidate: dict, opponents: list[dict], protocol: dict, *, runs_dir: Path = RUNS,
              run_id: str | None = None, notes: str | None = None, imported: bool = False,
              source: str | None = None, git: dict | None = None) -> Path:
    run_id = run_id or new_run_id(worker)
    run_dir = Path(runs_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    manifest = {"schema": SCHEMA_VERSION, "run_id": run_id, "status": "running", "created_at": _now().isoformat(),
                "finished_at": None, "worker": worker, "git": git or git_info(), "candidate": candidate,
                "opponents": opponents, "protocol": protocol, "imported": imported, "source": source,
                "n_games": None, "games_sha256": None, "notes": notes}
    _atomic_write(run_dir / "manifest.json", _dump(manifest))
    return run_dir


def game_key(row: dict) -> str:
    return f"{row['opponent']}_{row['color']}_{row['seed']}"


def write_game(run_dir: Path, row: dict) -> Path:
    """1試合 = 1ファイル。一時ファイルに書いてから rename するので、途中で落ちても壊れたファイルは残らない。"""
    _refuse_complete(run_dir)
    path = Path(run_dir) / "games" / f"{game_key(row)}.json"
    _atomic_write(path, json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def read_games(run_dir: Path) -> list[dict]:
    run_dir = Path(run_dir)
    jsonl = run_dir / "games.jsonl"
    if jsonl.exists():
        return [json.loads(line) for line in jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted((run_dir / "games").glob("*.json"))]


def _sort_key(row: dict):
    return (row["opponent"], row["color"], row["seed"])


def finish_run(run_dir: Path, status: str = "complete") -> dict:
    """games/*.json を games.jsonl にまとめ、manifest の status を確定する。"""
    run_dir = Path(run_dir)
    _refuse_complete(run_dir)
    rows = sorted(read_games(run_dir), key=_sort_key)
    text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows)
    _atomic_write(run_dir / "games.jsonl", text)
    manifest = read_manifest(run_dir)
    manifest.update(status=status, finished_at=_now().isoformat(), n_games=len(rows),
                    games_sha256=sha256_bytes(text.encode("utf-8")))
    _atomic_write(run_dir / "manifest.json", _dump(manifest))
    shutil.rmtree(run_dir / "games", ignore_errors=True)
    return manifest


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def _check(value, schema: dict, where: str) -> list[str]:
    errors = []
    types = schema.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        ok = any(
            (t == "integer" and isinstance(value, int) and not isinstance(value, bool))
            or (t == "number" and isinstance(value, (int, float)) and not isinstance(value, bool))
            or (t in _TYPES and isinstance(value, _TYPES[t]) and not (t != "boolean" and isinstance(value, bool)))
            for t in types
        )
        if not ok:
            return [f"{where}: expected {'/'.join(types)}, got {type(value).__name__}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{where}: {value!r} not in {schema['enum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{where}.{key}: missing")
        for key, sub in schema.get("properties", {}).items():
            if key in value:
                errors.extend(_check(value[key], sub, f"{where}.{key}"))
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            errors.extend(_check(item, schema["items"], f"{where}[{i}]"))
    return errors


def validate_run(run_dir: Path) -> list[str]:
    run_dir = Path(run_dir)
    mpath = run_dir / "manifest.json"
    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"{mpath}: {e}"]
    errors = [f"{mpath}: {e}" for e in _check(manifest, _schema("manifest"), "manifest")]
    if manifest.get("run_id") != run_dir.name:
        errors.append(f"{mpath}: run_id {manifest.get('run_id')!r} != directory name {run_dir.name!r}")
    game_schema = _schema("game")
    if manifest.get("status") == "complete":
        jsonl = run_dir / "games.jsonl"
        if not jsonl.exists():
            return errors + [f"{jsonl}: missing for a complete run"]
        data = jsonl.read_bytes()
        if sha256_bytes(data) != manifest.get("games_sha256"):
            errors.append(f"{jsonl}: edited after completion (games_sha256 mismatch)")
        lines = [line for line in data.decode("utf-8").splitlines() if line.strip()]
        if len(lines) != manifest.get("n_games"):
            errors.append(f"{jsonl}: {len(lines)} rows but n_games={manifest.get('n_games')}")
        rows = [(f"{jsonl}:{i + 1}", line) for i, line in enumerate(lines)]
        if (run_dir / "games").exists():
            errors.append(f"{run_dir / 'games'}: leftover game files in a complete run")
    else:
        rows = [(str(p), p.read_text(encoding="utf-8")) for p in sorted((run_dir / "games").glob("*.json"))]
        for p in (run_dir / "games").glob(".*.tmp"):
            errors.append(f"{p}: partial temporary file")
    for where, text in rows:
        try:
            row = json.loads(text)
        except ValueError as e:
            errors.append(f"{where}: {e}")
            continue
        errors.extend(f"{where}: {e}" for e in _check(row, game_schema, "game"))
    return errors


def iter_runs(path: Path):
    path = Path(path)
    if (path / "manifest.json").exists():
        yield path
        return
    base = path / "runs" if (path / "runs").is_dir() else path
    for run_dir in sorted(base.iterdir()):
        if run_dir.is_dir():
            yield run_dir


def validate(path: Path) -> list[str]:
    errors = []
    for run_dir in iter_runs(path):
        errors.extend(validate_run(run_dir))
    return errors


LEGACY_FIELDS = ["seed", "color", "result", "score", "endReason", "step_count", "our_alive", "enemy_alive",
                 "our_launched", "our_hits", "enemy_launched", "enemy_hits", "enemy_escort_killed",
                 "our_escort_killed", "error"]


def import_legacy(pool_dir: Path, runs_dir: Path = RUNS, rename: dict | None = None,
                  worker: str = "legacy") -> list[str]:
    """/workspace/research/eval/pool/<label>_vs_<opponent>/ を1組ごと1 run（imported: true）に変換する。"""
    rename = rename or {}
    ids = []
    for pair in sorted(Path(pool_dir).iterdir()):
        if not pair.is_dir() or "_vs_" not in pair.name:
            continue
        label, opponent = pair.name.split("_vs_", 1)
        files = sorted(p for p in pair.glob("*.json") if not p.name.endswith("_log.json"))
        if not files:
            continue
        rows = []
        for f in files:
            raw = json.loads(f.read_text(encoding="utf-8"))
            row = {k: raw[k] for k in LEGACY_FIELDS if k in raw}
            row["opponent"] = opponent
            rows.append(row)
        seeds = sorted({r["seed"] for r in rows})
        colors = [c for c in ("Red", "Blue") if any(r["color"] == c for r in rows)]
        name = rename.get(label, label)
        candidate = {"name": name, "specialist": None, "args": None, "args_sha256": None, "code_sha256": None}
        protocol = {"seeds": seeds, "colors": colors, "youth": True, "make_log": True}
        src = str(pair)
        run_dir = start_run(worker, candidate, [{"name": opponent, "commit": None, "args_sha256": None,
                                                 "code_sha256": None}], protocol, runs_dir=runs_dir,
                            imported=True, source=src, git={"sha": None, "branch": None, "dirty": None},
                            notes=f"imported from {src} (legacy label {label})")
        for row in rows:
            write_game(run_dir, row)
        complete = len(rows) == 40 and seeds == list(range(1, 21)) and colors == ["Red", "Blue"]
        finish_run(run_dir, "complete" if complete else "aborted")
        ids.append(run_dir.name)
    return ids


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="results_store")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("path", nargs="?", default=str(RESULTS))
    im = sub.add_parser("import-legacy")
    im.add_argument("pool_dir")
    im.add_argument("--runs-dir", default=str(RUNS))
    im.add_argument("--rename", default="", help="LABEL=NAME[,LABEL=NAME]（例: V6=hybrid_v6）")
    a = ap.parse_args(argv)
    if a.cmd == "validate":
        errors = validate(Path(a.path))
        for e in errors:
            print(e)
        print(f"{len(errors)} errors")
        return 1 if errors else 0
    rename = dict(pair.split("=", 1) for pair in a.rename.split(",") if pair)
    for run_id in import_legacy(Path(a.pool_dir), Path(a.runs_dir), rename):
        manifest = read_manifest(Path(a.runs_dir) / run_id)
        print(f"{run_id} {manifest['candidate']['name']} vs {manifest['opponents'][0]['name']} "
              f"{manifest['n_games']} games {manifest['status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
