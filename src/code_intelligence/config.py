from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os
import yaml

DEFAULT_CONFIG = Path("~/.config/code-intelligence/config.yaml").expanduser()

@dataclass
class Config:
    raw: dict[str, Any]

    @property
    def organization(self) -> str:
        return self.raw["github"]["organization"]

    @property
    def repository_root(self) -> Path:
        value = self.raw.get("repositories", {}).get("root", "~/code/github")
        return Path(os.path.expandvars(os.path.expanduser(value))).resolve()

    @property
    def include(self) -> list[str]:
        return self.raw.get("repositories", {}).get("include", ["*"])

    @property
    def exclude(self) -> list[str]:
        return self.raw.get("repositories", {}).get("exclude", [])

    @property
    def git_protocol(self) -> str:
        return self.raw.get("git", {}).get("protocol", "ssh")

    @property
    def cbm(self) -> dict[str, Any]:
        return self.raw.get("indexers", {}).get("cbm", {})

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG) -> "Config":
        if not path.exists():
            raise FileNotFoundError(
                f"Configuration not found: {path}. Run 'code-intelligence setup' first."
            )
        with path.open() as fh:
            raw = yaml.safe_load(fh) or {}
        return cls(raw)
