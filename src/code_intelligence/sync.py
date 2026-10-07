from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

from .config import Config
from .github import Repository, list_repositories

def selected(repo: Repository, config: Config) -> bool:
    included = not config.include or any(fnmatch.fnmatch(repo.name, p) for p in config.include)
    excluded = any(fnmatch.fnmatch(repo.name, p) for p in config.exclude)
    return included and not excluded

def repo_path(config: Config, repo: Repository) -> Path:
    # repository_root is the parent directory for all GitHub organizations.
    return config.repository_root / config.organization / repo.name

def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        text=True,
        capture_output=True,
    )

def clone(config: Config, repo: Repository) -> Path:
    target = repo_path(config, repo)
    if not repo.default_branch:
        raise RuntimeError("repository has no default branch")
    target.parent.mkdir(parents=True, exist_ok=True)
    url = repo.ssh_url if config.git_protocol == "ssh" else repo.https_url
    subprocess.run(
        ["git", "clone", "--branch", repo.default_branch, url, str(target)],
        check=True,
        text=True,
    )
    return target

def update(config: Config, repo: Repository) -> tuple[Path, str]:
    target = repo_path(config, repo)
    if not target.exists():
        clone(config, repo)
        return target, "cloned"

    status = _git(target, "status", "--porcelain")
    if status.returncode:
        return target, "invalid"

    if status.stdout.strip():
        return target, "dirty"

    before = _git(target, "rev-parse", "HEAD")
    if before.returncode:
        return target, "invalid"
    old_head = before.stdout.strip()

    result = _git(target, "fetch", "--prune", "origin")
    if result.returncode:
        return target, "fetch-failed"

    result = _git(target, "pull", "--ff-only", "origin", repo.default_branch)
    if result.returncode:
        return target, "pull-failed"

    after = _git(target, "rev-parse", "HEAD")
    if after.returncode:
        return target, "invalid"
    return target, "updated" if after.stdout.strip() != old_head else "unchanged"

def sync(config: Config) -> list[tuple[Repository, Path, str]]:
    results = []
    for repo in list_repositories(config.organization):
        if repo.archived or repo.fork or not selected(repo, config):
            continue
        if not repo.default_branch:
            results.append((repo, repo_path(config, repo), "empty"))
            continue
        path, state = update(config, repo)
        results.append((repo, path, state))
    return results
