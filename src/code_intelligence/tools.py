from __future__ import annotations

import shutil
import subprocess
import tempfile
import urllib.request

CBM_INSTALLER = "https://raw.githubusercontent.com/DeusData/codebase-memory-mcp/main/scripts/setup.sh"


def run(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, check=True)


def install_cbm() -> None:
    if shutil.which("codebase-memory-mcp"):
        print("OK  codebase-memory-mcp")
        return
    if not shutil.which("bash"):
        raise RuntimeError("bash is required to install Codebase Memory")
    with tempfile.NamedTemporaryFile(suffix=".sh") as script:
        urllib.request.urlretrieve(CBM_INSTALLER, script.name)
        run(["bash", script.name])


def update_cbm() -> None:
    install_cbm()


def install_serena() -> None:
    if shutil.which("serena"):
        print("OK  serena")
        return
    if not shutil.which("uv"):
        raise RuntimeError("uv is required to install Serena; install uv first")
    run(["uv", "tool", "install", "-p", "3.13", "serena-agent"])


def update_serena() -> None:
    if not shutil.which("uv"):
        raise RuntimeError("uv is required to update Serena")
    run(["uv", "tool", "upgrade", "serena-agent"])


def install_all() -> None:
    install_cbm()
    install_serena()


def update_all() -> None:
    update_cbm()
    update_serena()
