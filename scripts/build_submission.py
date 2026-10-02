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


def build_staging():
    if STAGING.exists():
        shutil.rmtree(STAGING)
    STAGING.mkdir(parents=True)

    for name in ENTRY_FILES:
        src = AGENT_DIR / name
        if not src.exists():
            raise SystemExit(f"missing required file: {src}")
        shutil.copy(src, STAGING / name)

    for name in PACKAGE_DIRS:
        src = AGENT_DIR / name
        if not src.exists():
            raise SystemExit(f"missing required directory: {src}")
        shutil.copytree(src, STAGING / name, ignore=IGNORE)

    return STAGING


def make_zip():
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
    with zipfile.ZipFile(OUTPUT_ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(STAGING.rglob("*")):
            if path.is_file():
                z.write(path, path.relative_to(STAGING).as_posix())
    return OUTPUT_ZIP


def deploy():
    if DEPLOY_TARGET.exists():
        shutil.rmtree(DEPLOY_TARGET)
    shutil.copytree(STAGING, DEPLOY_TARGET, ignore=IGNORE)
    return DEPLOY_TARGET


def main():
    parser = argparse.ArgumentParser(prog="build_submission")
    parser.add_argument("--deploy", action="store_true", help="workspace/Agents/MyAgent にも配置する")
    args = parser.parse_args()

    build_staging()
    zip_path = make_zip()
    print(f"built: {zip_path} ({zip_path.stat().st_size} bytes)")
    for path in sorted(STAGING.rglob("*")):
        if path.is_file():
            print("  ", path.relative_to(STAGING).as_posix())

    if args.deploy:
        target = deploy()
        print(f"deployed: {target}")


if __name__ == "__main__":
    main()
