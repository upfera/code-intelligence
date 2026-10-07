# code-intelligence

Local GitHub repository synchronization and code-intelligence orchestration.

The intended model is:

- **Codebase Memory (CBM)** is persistent and pre-indexes the default branch of every selected repository.
- **Serena** is installed once but started for the active OpenHands task/workspace. It sees the exact checkout and agent changes.
- Repository synchronization is deterministic and safe for normal user operation.

## Quick start

Requirements:

- Python 3.11+
- git
- GitHub CLI (`gh`) authenticated to the target organization

From a checkout of this repository:

    python3 -m venv .venv
    . .venv/bin/activate
    python -m pip install -e .

Then:

    code-intelligence bootstrap

The bootstrap installs the optional code-intelligence tools, creates the user configuration, synchronizes the selected repositories, and pre-indexes them with CBM.

## Configuration

Default configuration:

    ~/.config/code-intelligence/config.yaml

Example:

    github:
      organization: upfera

    repositories:
      root: ~/code/github/upfera
      include:
        - "*"
      exclude: []

    git:
      protocol: ssh

    indexers:
      cbm:
        enabled: true
        command: codebase-memory-mcp
      serena:
        enabled: true

## Commands

    code-intelligence setup
    code-intelligence doctor
    code-intelligence tools-install
    code-intelligence tools-update
    code-intelligence sync
    code-intelligence index
    code-intelligence bootstrap

`sync` only synchronizes repositories. `index` synchronizes first and then pre-indexes selected clean repositories with CBM.

## Indexing model

CBM indexes the repository's **default branch** in the canonical local checkout:

    ~/code/github/upfera/<repo>

This is the persistent organization-wide code intelligence corpus.

Serena is deliberately **not** pre-indexed for every repository. OpenHands should start Serena against the active task workspace, for example:

    ~/workspace/project/<conversation-id>

This gives the semantic layer the exact current workspace state, including uncommitted agent changes.

## Safety

- Runs as the normal user.
- Never implicitly uses sudo.
- Does not delete repositories that disappear from GitHub.
- Does not overwrite dirty local repositories.
- CBM is persistent; Serena is task-scoped.

## Architecture

    GitHub
       |
       v
    code-intelligence
       |
       +--> sync --> ~/code/github/upfera/*
       |
       +--> CBM --> persistent index of default branches
       |
       +--> Serena --> launched by the active agent/task for its workspace

The MCP interface remains intentionally thin and should call the same core services as the CLI.
