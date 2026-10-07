from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from .config import DEFAULT_CONFIG, Config
from .github import check_auth, list_repositories
from .indexers import index_with_cbm
from .sync import repo_path, selected, sync
from .tools import install_all, update_all

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
        if config.cbm.get("enabled", False):
            command = config.cbm.get("command", "codebase-memory-mcp")
            if shutil.which(command):
                print(f"OK  {command}")
            else:
                print(f"FAIL {command}: not found")
                failures += 1
        if config.raw.get("indexers", {}).get("serena", {}).get("enabled", False):
            if shutil.which("serena"):
                print("OK  serena")
            else:
                print("FAIL serena: not found")
                failures += 1
    except Exception as exc:
        print(f"FAIL {exc}")
        failures += 1
    return failures


def sync_command() -> int:
    config = Config.load()
    check_auth()
    for repo, path, state in sync(config):
        print(f"{state:12} {repo.name_with_owner} -> {path}")
    return 0


def index_command(force: bool = False) -> int:
    config = Config.load()
    check_auth()
    for repo in list_repositories(config.organization):
        if repo.archived or repo.fork or not selected(repo, config):
            continue
        path = repo_path(config, repo)
        if not path.is_dir():
            print(f"SKIP missing: {repo.name_with_owner}")
            continue
        try:
            index_with_cbm(config, path, force=force)
        except Exception as exc:
            print(f"WARN index failed {repo.name_with_owner}: {exc}")
    return 0


def bootstrap_command() -> int:
    setup()
    install_all()
    failures = doctor()
    if failures:
        return failures
    sync_command()
    return index_command(force=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="code-intelligence")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup")
    sub.add_parser("doctor")
    sub.add_parser("tools-install")
    sub.add_parser("tools-update")
    sub.add_parser("sync")
    index = sub.add_parser("index")
    index.add_argument("--force", action="store_true")
    sub.add_parser("bootstrap")
    args = parser.parse_args()

    if args.command == "setup":
        setup()
    elif args.command == "doctor":
        raise SystemExit(doctor())
    elif args.command == "tools-install":
        install_all()
    elif args.command == "tools-update":
        update_all()
    elif args.command == "sync":
        raise SystemExit(sync_command())
    elif args.command == "index":
        raise SystemExit(index_command(args.force))
    elif args.command == "bootstrap":
        raise SystemExit(bootstrap_command())


if __name__ == "__main__":
    main()
