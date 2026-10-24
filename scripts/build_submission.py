import argparse
import ast
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT / "agent"
STAGING = ROOT / "submission" / "MyAgent"
OUTPUT_ZIP = ROOT / "submission" / "submit.zip"
DEPLOY_TARGET = ROOT / "workspace" / "Agents" / "MyAgent"
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc")

ENTRY_FILES = ["__init__.py", "args.json", "config.json"]
PACKAGE_DIRS = ["strategy"]
SWITCHBOARD = ["strategy/__init__.py", "strategy/active.py"]


def _module_file(agent_dir, parts):
    """agent ルートからのモジュール名 (tuple) を .py ファイルに解決する。無ければ None。"""
    base = agent_dir.joinpath(*parts)
    for path in (base.with_suffix(".py"), base / "__init__.py"):
        if parts and path.is_file():
            return path
    return None


def _package_inits(agent_dir, rel):
    """rel（agent ルートからの相対パス）を読み込むと実行される親パッケージの __init__.py。"""
    parts = rel.parts[:-1]
    if rel.name == "__init__.py":
        parts = parts[:-1]
    out = []
    for i in range(1, len(parts) + 1):
        init = agent_dir.joinpath(*parts[:i], "__init__.py")
        if init.is_file():
            out.append(init)
    return out


def _relative_imports(agent_dir, path):
    rel = path.relative_to(agent_dir)
    package = rel.parts[:-1]
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.ImportFrom) or node.level == 0:
            continue
        base = package[: len(package) - (node.level - 1)]
        target = base + tuple(node.module.split(".")) if node.module else base
        module = _module_file(agent_dir, target)
        if module is not None:
            found.append(module)
        for alias in node.names:
            sub = _module_file(agent_dir, target + (alias.name,))
            if sub is not None:
                found.append(sub)
    return found


def specialist_files(specialist, agent_dir=AGENT_DIR):
    """specialist 本体のファイル。ideas/<name>/ はディレクトリごと（データファイルも含む）。"""
    strategy = agent_dir / "strategy"
    single = strategy / "specialists" / f"{specialist}.py"
    idea = strategy / "ideas" / specialist
    if single.is_file():
        return [single]
    if (idea / "__init__.py").is_file():
        return [p for p in sorted(idea.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
    raise SystemExit(f"unknown specialist: {specialist}")


def import_closure(specialist, agent_dir=AGENT_DIR):
    """specialist が相対 import でたどるファイルと、その親パッケージの __init__.py（agent ルートからの相対パス）。"""
    todo = [agent_dir / name for name in SWITCHBOARD] + specialist_files(specialist, agent_dir)
    seen = set()
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        seen.add(path)
        rel = path.relative_to(agent_dir)
        todo.extend(_package_inits(agent_dir, rel))
        if path.suffix == ".py":
            todo.extend(_relative_imports(agent_dir, path))
    return sorted(p.relative_to(agent_dir).as_posix() for p in seen)


def build_staging(args_path=None, staging=STAGING):
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    for name in ENTRY_FILES:
        src = AGENT_DIR / name
        if not src.exists():
            raise SystemExit(f"missing required file: {src}")
        shutil.copy(src, staging / name)

    if args_path is not None:
        # 別解法のプリセット（例: agent/presets/hybrid_v6.json）で args.json を差し替える。agent/args.json は変更しない
        preset = Path(args_path)
        if not preset.is_absolute():
            preset = ROOT / preset
        if not preset.exists():
            raise SystemExit(f"missing args preset: {preset}")
        shutil.copy(preset, staging / "args.json")

    for name in PACKAGE_DIRS:
        src = AGENT_DIR / name
        if not src.exists():
            raise SystemExit(f"missing required directory: {src}")

    specialist = json.loads((staging / "args.json").read_text(encoding="utf-8")).get("specialist")
    if not specialist:
        raise SystemExit("args.json has no specialist")
    for rel in import_closure(specialist):
        dest = staging / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(AGENT_DIR / rel, dest)

    return staging


def make_zip(staging=STAGING, output_zip=OUTPUT_ZIP):
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(staging).as_posix())
    return output_zip


def deploy(staging=STAGING):
    if DEPLOY_TARGET.exists():
        shutil.rmtree(DEPLOY_TARGET)
    shutil.copytree(staging, DEPLOY_TARGET, ignore=IGNORE)
    return DEPLOY_TARGET


def main():
    parser = argparse.ArgumentParser(prog="build_submission")
    parser.add_argument("--deploy", action="store_true", help="workspace/Agents/MyAgent にも配置する")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument(
        "--args",
        default=None,
        help="args.json の代わりに使うプリセット（例: agent/presets/hybrid_v6.json）",
    )
    choice.add_argument("--preset", default=None, help="agent/presets/NAME.json を使う（--args の短縮）")
    parser.add_argument("--out", default=None, help="staging と submit.zip の出力先（省略時は submission/）")
    args = parser.parse_args()

    args_path = f"agent/presets/{args.preset}.json" if args.preset else args.args
    if args.out:
        out = Path(args.out).resolve()
        staging, output_zip = out / "MyAgent", out / "submit.zip"
    else:
        staging, output_zip = STAGING, OUTPUT_ZIP

    build_staging(args_path, staging)
    zip_path = make_zip(staging, output_zip)
    print(f"built: {zip_path} ({zip_path.stat().st_size} bytes)")
    for path in sorted(staging.rglob("*")):
        if path.is_file():
            print("  ", path.relative_to(staging).as_posix())

    if args.deploy:
        target = deploy(staging)
        print(f"deployed: {target}")


if __name__ == "__main__":
    main()
