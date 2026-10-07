from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class Repository:
    name: str
    name_with_owner: str
    ssh_url: str
    https_url: str
    default_branch: str | None
    archived: bool
    fork: bool


def run_gh(*args: str) -> str:
    result = subprocess.run(
        ["gh", *args],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "gh command failed")
    return result.stdout


def check_auth() -> None:
    result = subprocess.run(["gh", "auth", "status"], text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("GitHub CLI is not authenticated. Run: gh auth login")


def list_repositories(organization: str) -> list[Repository]:
    output = run_gh(
        "repo",
        "list",
        organization,
        "--limit",
        "1000",
        "--json",
        "name,nameWithOwner,sshUrl,url,defaultBranchRef,isArchived,isFork",
    )
    rows = json.loads(output)
    return [
        Repository(
            name=row["name"],
            name_with_owner=row["nameWithOwner"],
            ssh_url=row["sshUrl"],
            https_url=row["url"],
            default_branch=(row["defaultBranchRef"] or {}).get("name"),
            archived=row["isArchived"],
            fork=row["isFork"],
        )
        for row in rows
    ]
