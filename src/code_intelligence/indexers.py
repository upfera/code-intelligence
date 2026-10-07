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
        return json.loads(STATE_FILE.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict[str, str]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def repository_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def index_with_cbm(config: Config, path: Path, force: bool = False) -> bool:
    cbm = config.cbm
    if not cbm.get("enabled", False):
        return False

    head = repository_head(path)
    key = str(path)
    state = _load_state()

    if not force and state.get(key) == head:
        print(f"SKIP index unchanged: {path}")
        return False

    command = cbm.get("command", "codebase-memory-mcp")
    subprocess.run(
        [command, "cli", "index_repository", "--repo-path", str(path)],
        check=True,
        text=True,
    )

    state[key] = head
    _save_state(state)
    print(f"INDEXED {path} @ {head[:12]}")
    return True
