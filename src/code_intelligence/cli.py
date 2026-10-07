from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .config import DEFAULT_CONFIG, Config
from .github import check_auth
from .indexers import index_with_cbm
from .sync import sync

EXAMPLE = Path(__file__).resolve().parents[2] / "config" / "example.yaml"

def setup() -> None:
    DEFAULT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if DEFAULT_CONFIG.exists():
        print(DEFAULT_CONFIG)
        return
    DEFAULT_CONFIG.write_text(EXAMPLE.read_text())
    print(f"Created {DEFAULT_CONFIG}")

def doctor() -> int:
    failures = 0
    for tool in ("git", "gh"):
        if shutil.which(tool):
            print(f"OK  {tool}")
        else:
            print(f"FAIL {tool}: not found")
            failures += 1
    try:
        check_auth()
        print("OK  gh authentication")
    except RuntimeError as exc:
        print(f"FAIL {exc}")
        failures += 1
    try:
        config = Config.load()
        print(f"OK  config: {DEFAULT_CONFIG}")
        print(f"OK  organization: {config.organization}")
        print(f"OK  repository root: {config.repository_root}")
    except Exception as exc:
        print(f"FAIL {exc}")
        failures += 1
    return failures

def sync_command() -> int:
    config = Config.load()
    check_auth()
    results = sync(config)
    for repo, path, state in results:
        print(f"{state:12} {repo.name_with_owner} -> {path}")
        if state in {"cloned", "updated"}:
            try:
                index_with_cbm(config, path)
            except FileNotFoundError:
                print("  WARN CBM command not found")
            except Exception as exc:
                print(f"  WARN CBM indexing failed: {exc}")
    return 0

def main() -> None:
    parser = argparse.ArgumentParser(prog="code-intelligence")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup")
    sub.add_parser("doctor")
    sub.add_parser("sync")
    args = parser.parse_args()

    if args.command == "setup":
        setup()
    elif args.command == "doctor":
        raise SystemExit(doctor())
    elif args.command == "sync":
        raise SystemExit(sync_command())

if __name__ == "__main__":
    main()
