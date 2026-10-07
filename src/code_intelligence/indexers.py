from __future__ import annotations

import subprocess
from pathlib import Path

from .config import Config

def index_with_cbm(config: Config, path: Path) -> None:
    cbm = config.cbm
    if not cbm.get("enabled", False):
        return
    command = cbm.get("command", "codebase-memory-mcp")
    subprocess.run(
        [command, "cli", "index_repository", "--repo-path", str(path)],
        check=True,
        text=True,
    )
