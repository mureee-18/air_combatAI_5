import argparse
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
        shutil.copytree(src, staging / name, ignore=IGNORE)

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
