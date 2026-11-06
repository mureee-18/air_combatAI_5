"""agent/args.json の各変数が実際にエージェントコードで使われているかを監査する.

ダッシュボードの「実装状態」は長らく args.json のキー一覧をそのまま表示しており、
値だけ追加してコードに配線していない変数（=動かしても挙動が変わらない変数）も
「実装済み」に見えていた。このモジュールは args.json → コードの配線を機械的に判定し、
ダッシュボード・検証ツール・提出前ゲートが同じ判定を共有できるようにする。

判定ルール（いずれかを満たせば「配線済み」）
    1. policy 経由:
       policy.py の ``self.<attr> = ... args.get("<key>", ...)`` を key→attr に対応づけ、
       その attr が ``policy.<attr>`` または ``getattr(policy, "<attr>")`` として
       実際に参照されている。
    2. modelConfig 経由:
       ``getValueFromJsonKRD(mc, "<key>", ...)`` があり、config.py が args から
       そのキーを modelConfig へ転送している。
    3. 直接参照:
       policy.py 以外の .py が ``args.get("<key>")`` / ``args["<key>"]`` で読んでいる。

``type`` と ``specialist`` はメタ情報なので対象外。

Usage:
    python tools/arg_wiring.py            # 一覧表示（未配線があれば終了コード 1）
    python tools/arg_wiring.py --json     # JSON で出力
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

META_KEYS = ("type", "specialist")

_POLICY_ASSIGN = re.compile(
    r"self\.(\w+)\s*=\s*[^\n]*?args\.get\(\s*[\"']([\w]+)[\"']"
)
_POLICY_USE = re.compile(r"policy\.(\w+)\b")
_POLICY_GETATTR = re.compile(r"getattr\(\s*policy\s*,\s*[\"'](\w+)[\"']")
_MODEL_READ = re.compile(r"getValueFromJsonKRD\(\s*mc\s*,\s*[\"']([\w]+)[\"']")


def _read_agent_python(agent_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not agent_dir.is_dir():
        return out
    for path in sorted(agent_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            out[path.relative_to(agent_dir).as_posix()] = path.read_text(encoding="utf-8")
        except OSError:
            continue
    return out


def _policy_attr_of(files: dict[str, str]) -> dict[str, str]:
    """policy.py の ``self.<attr> = args.get("<key>")`` から key→attr を作る."""

    attr_of: dict[str, str] = {}
    for rel, text in files.items():
        if not rel.endswith("policy.py"):
            continue
        for m in _POLICY_ASSIGN.finditer(text):
            attr_of[m.group(2)] = m.group(1)
    return attr_of


def audit(repo_root: Path) -> dict[str, dict]:
    """args.json の全キーについて配線状態を返す."""

    repo_root = Path(repo_root)
    agent_dir = repo_root / "agent"
    args_path = agent_dir / "args.json"
    try:
        args = json.loads(args_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    files = _read_agent_python(agent_dir)
    attr_of = _policy_attr_of(files)

    used_attrs: set[str] = set()
    for text in files.values():
        used_attrs.update(_POLICY_USE.findall(text))
        used_attrs.update(_POLICY_GETATTR.findall(text))

    config_rel = "strategy/specialists/default/config.py"
    config_text = files.get(config_rel, "")
    model_keys: set[str] = set()
    for text in files.values():
        for key in _MODEL_READ.findall(text):
            # config.py が args から転送しているキーだけ modelConfig 経由と認める
            if re.search(rf"[\"']{re.escape(key)}[\"']", config_text):
                model_keys.add(key)

    direct_keys: dict[str, list[str]] = {}
    for rel, text in files.items():
        if rel.endswith("policy.py"):
            continue
        for key in set(
            re.findall(r"args\.get\(\s*[\"']([\w]+)[\"']", text)
            + re.findall(r"args\[\s*[\"']([\w]+)[\"']\s*\]", text)
        ):
            direct_keys.setdefault(key, []).append(rel)

    out: dict[str, dict] = {}
    for key in sorted(k for k in args if k not in META_KEYS):
        via: list[str] = []
        where: list[str] = []
        attr = attr_of.get(key)
        if attr and attr in used_attrs:
            via.append("policy")
            for rel, text in files.items():
                if rel.endswith("policy.py"):
                    continue
                if attr in _POLICY_USE.findall(text) or attr in _POLICY_GETATTR.findall(text):
                    where.append(f"agent/{rel}")
        if key in model_keys:
            via.append("modelConfig")
            for rel, text in files.items():
                if key in _MODEL_READ.findall(text):
                    where.append(f"agent/{rel}")
        if key in direct_keys:
            via.append("direct")
            where.extend(f"agent/{rel}" for rel in direct_keys[key])
        out[key] = {
            "key": key,
            "wired": bool(via),
            "via": via,
            "attr": attr,
            "files": sorted(set(where)),
        }
    return out


def unwired(repo_root: Path) -> list[str]:
    return [k for k, v in audit(repo_root).items() if not v["wired"]]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="args.json の配線監査")
    ap.add_argument("--json", action="store_true", help="JSON で出力")
    parsed = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    result = audit(repo_root)
    if parsed.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{'変数':32} {'状態':8} {'経路':20} 参照箇所")
        for key, item in result.items():
            state = "配線済み" if item["wired"] else "未配線"
            via = ",".join(item["via"]) or "-"
            files = ", ".join(item["files"]) or "-"
            print(f"{key:32} {state:8} {via:20} {files}")

    missing = [k for k, v in result.items() if not v["wired"]]
    if missing:
        print()
        print(f"未配線の変数が {len(missing)} 個あります: {', '.join(missing)}")
        print("args.json に値を足しただけでは挙動は変わりません（policy → 判断層まで配線してください）。")
        return 1
    print()
    print(f"全 {len(result)} 変数が配線済みです。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
