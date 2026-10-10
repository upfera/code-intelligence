from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .config import Config

STATE_FILE = Path("~/.local/state/code-intelligence/index-state.json").expanduser()


def _load_state() -> dict[str, str]:
    if not STATE_FILE.exists():
        return {}
    try:
        value = json.loads(STATE_FILE.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATE_FILE.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    temporary.replace(STATE_FILE)


def repository_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    )
    return result.stdout.strip()


def cbm_project_name(repository: str) -> str:
    """Return a stable CBM name derived from the GitHub owner/repository."""
    return f"github-{repository.replace('/', '-')}"


def index_with_cbm(config: Config, path: Path, repository: str, force: bool = False) -> bool:
    cbm = config.cbm
    if not cbm.get("enabled", False):
        raise RuntimeError("CBM indexing is disabled in configuration")
    head = repository_head(path)
    key = f"github.com/{repository.lower()}"
    state = _load_state()
    if not force and state.get(key) == head:
        print(f"SKIP index unchanged: {repository} ({head[:12]})")
        return False
    command = cbm.get("command", "codebase-memory-mcp")
    project_name = cbm_project_name(repository)
    subprocess.run(
        [command, "cli", "index_repository", "--repo-path", str(path), "--name", project_name],
        check=True, text=True, timeout=int(cbm.get("timeout_seconds", 1800)),
    )
    state[key] = head
    _save_state(state)
    print(f"INDEXED {project_name} @ {head[:12]}")
    return True
