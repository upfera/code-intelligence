from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path

from .config import DEFAULT_CONFIG, Config
from .github import check_auth, list_repositories
from .indexers import index_with_cbm
from .sync import repo_path, selected, sync
from .tools import install_all, update_all

EXAMPLE = Path(__file__).resolve().parents[2] / "config" / "example.yaml"
REPOSITORY_ALLOWLIST_HELP = "Comma-separated owner/repository allowlist"
SYNC_FAILURE_STATES = {"invalid", "fetch-failed", "pull-failed", "clone-failed"}


def setup() -> None:
    if DEFAULT_CONFIG.exists():
        print(DEFAULT_CONFIG)
        return
    print("Code Intelligence setup\n")
    organization = input("GitHub organization: ").strip()
    if not organization:
        raise SystemExit("GitHub organization is required")
    root_default = "~/code/github"
    root = input(f"Repository root [{root_default}]: ").strip() or root_default
    include = input('Repositories to include [*]: ').strip() or "*"
    exclude = input("Repositories to exclude []: ").strip()
    config = EXAMPLE.read_text()
    config = config.replace("organization: your-org", f"organization: {organization}")
    config = config.replace("root: ~/code/github", f"root: {root}")
    config = config.replace('    - "*"\n  exclude: []', f'    - "{include}"\n  exclude: [{exclude}]')
    DEFAULT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_CONFIG.write_text(config)
    print(f"Created {DEFAULT_CONFIG}")


def _check_indexer_tools(config: Config) -> int:
    failures = 0
    if config.cbm.get("enabled", False):
        command = config.cbm.get("command", "codebase-memory-mcp")
        if not shutil.which(command):
            print(f"FAIL {command}: not found")
            failures += 1
        else:
            result = subprocess.run([command, "--help"], capture_output=True, text=True, timeout=20)
            if result.returncode:
                print(f"FAIL {command}: --help exited {result.returncode}")
                failures += 1
            else:
                print(f"OK  {command} responds to --help")
    if config.raw.get("indexers", {}).get("serena", {}).get("enabled", False):
        if shutil.which("serena"):
            print("OK  serena")
        else:
            print("FAIL serena: not found")
            failures += 1
    return failures


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
        failures += _check_indexer_tools(config)
    except Exception as exc:
        print(f"FAIL {exc}")
        failures += 1
    return failures


def _parse_repos(value: str | None) -> set[str] | None:
    if not value:
        return None
    repos = {item.strip().casefold() for item in value.split(",") if item.strip()}
    if not repos:
        raise ValueError("--repos must contain at least one owner/repository")
    invalid = [item for item in repos if item.count("/") != 1]
    if invalid:
        raise ValueError("Repositories must use owner/repository format: " + ", ".join(sorted(invalid)))
    return repos


def sync_command(repositories: set[str] | None = None) -> int:
    config = Config.load()
    check_auth()
    results = sync(config, repositories=repositories)
    failures = 0
    for repo, path, state in results:
        print(f"{state:14} {repo.name_with_owner} -> {path}")
        if state.endswith("failed") or state == "invalid":
            failures += 1
    return 1 if failures else 0


def index_command(force: bool = False, repositories: set[str] | None = None) -> int:
    config = Config.load()
    check_auth()
    failures = 0
    for repo in list_repositories(config.organization):
        if repo.archived or repo.fork or not selected(repo, config):
            continue
        if repositories is not None and repo.name_with_owner.casefold() not in repositories:
            continue
        path = repo_path(config, repo)
        if not path.is_dir():
            print(f"SKIP missing: {repo.name_with_owner}")
            failures += 1
            continue
        try:
            indexed = index_with_cbm(config, path, repo.name_with_owner, force=force)
            print(f"{'INDEXED' if indexed else 'UNCHANGED'} {repo.name_with_owner}")
        except Exception as exc:
            print(f"ERROR index failed {repo.name_with_owner}: {exc}")
            failures += 1
    return 1 if failures else 0


def _reconcile_repository(repo, path: Path, sync_status: str, config: Config, force: bool) -> dict:
    item = {"repository": repo.name_with_owner, "path": str(path), "sync": sync_status}
    if sync_status in {"dirty", "empty"}:
        item["index"] = "skipped"
        item["reason"] = "dirty checkout" if sync_status == "dirty" else "no default branch"
    elif sync_status in SYNC_FAILURE_STATES:
        item["index"] = "not_attempted"
        item["error"] = sync_status
    elif not path.is_dir():
        item["index"] = "not_attempted"
        item["error"] = "checkout missing after sync"
    else:
        try:
            did_index = index_with_cbm(config, path, repo.name_with_owner, force=force)
            item["index"] = "indexed" if did_index else "unchanged"
        except Exception as exc:
            item["index"] = "failed"
            item["error"] = f"{type(exc).__name__}: {exc}"
    return item


def _reconcile_summary(items: list[dict]) -> dict:
    return {
        "total": len(items),
        "indexed": sum(item.get("index") == "indexed" for item in items),
        "unchanged": sum(item.get("index") == "unchanged" for item in items),
        "skipped": sum(item.get("index") in {"skipped", "not_attempted"} for item in items),
        "failed": sum(
            item.get("index") == "failed"
            or item.get("sync") in SYNC_FAILURE_STATES
            or item.get("sync") == "not_found_or_filtered"
            or (item.get("index") == "not_attempted" and "error" in item)
            for item in items
        ),
    }


def reconcile_command(repositories: set[str] | None = None, force: bool = False) -> int:
    started = time.monotonic()
    config = Config.load()
    check_auth()
    report = {"command": "reconcile", "status": "success", "duration_seconds": None, "repositories": []}
    try:
        sync_results = sync(config, repositories=repositories)
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = f"sync inventory failed: {type(exc).__name__}: {exc}"
        report["duration_seconds"] = round(time.monotonic() - started, 3)
        print(json.dumps(report, sort_keys=True))
        return 1

    seen = set()
    for repo, path, sync_status in sync_results:
        seen.add(repo.name_with_owner.casefold())
        item = _reconcile_repository(repo, path, sync_status, config, force)
        report["repositories"].append(item)
        if "error" in item:
            report["status"] = "partial_failure"

    missing = repositories - seen if repositories is not None else set()
    for name in sorted(missing):
        report["repositories"].append({
            "repository": name,
            "sync": "not_found_or_filtered",
            "index": "not_attempted",
            "error": "Repository was not returned by GitHub or is excluded by configuration",
        })
    if missing:
        report["status"] = "partial_failure"

    report["duration_seconds"] = round(time.monotonic() - started, 3)
    report["summary"] = _reconcile_summary(report["repositories"])
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "success" else 1


def bootstrap_command() -> int:
    setup()
    install_all()
    failures = doctor()
    if failures:
        return failures
    if sync_command():
        return 1
    return index_command(force=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="code-intelligence")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup")
    sub.add_parser("doctor")
    sub.add_parser("tools-install")
    sub.add_parser("tools-update")
    sync_parser = sub.add_parser("sync")
    sync_parser.add_argument("--repos", help=REPOSITORY_ALLOWLIST_HELP)
    index = sub.add_parser("index")
    index.add_argument("--force", action="store_true")
    index.add_argument("--repos", help=REPOSITORY_ALLOWLIST_HELP)
    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--repos", help=REPOSITORY_ALLOWLIST_HELP)
    reconcile.add_argument("--force", action="store_true", help="Reindex even when the local manifest matches HEAD")
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
        raise SystemExit(sync_command(_parse_repos(args.repos)))
    elif args.command == "index":
        raise SystemExit(index_command(args.force, _parse_repos(args.repos)))
    elif args.command == "reconcile":
        raise SystemExit(reconcile_command(_parse_repos(args.repos), args.force))
    elif args.command == "bootstrap":
        raise SystemExit(bootstrap_command())


if __name__ == "__main__":
    main()
