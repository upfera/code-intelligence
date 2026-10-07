from __future__ import annotations

import shutil
import subprocess


def run(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, check=True)


def install_serena() -> None:
    if shutil.which("serena"):
        print("OK  serena")
        return
    if not shutil.which("uv"):
        raise RuntimeError("uv is required to install Serena; install uv first")
    run(["uv", "tool", "install", "-p", "3.13", "serena-agent"])


def update_serena() -> None:
    if shutil.which("uv"):
        run(["uv", "tool", "upgrade", "serena-agent"])


def install_all() -> None:
    install_serena()
