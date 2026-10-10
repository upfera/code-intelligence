# code-intelligence

Local GitHub repository synchronization and code-intelligence orchestration.

- **Codebase Memory (CBM)** is the persistent index for selected repositories' default branches.
- **Serena** is task/workspace-scoped and is not globally pre-indexed.
- Synchronization is deterministic and never overwrites dirty checkouts.

## Quick start

Requirements: Python 3.11+, Git, GitHub CLI (gh) authenticated to the target organization, and CBM if indexing is enabled.

    python3 -m venv .venv
    .venv/bin/python -m pip install -e .
    .venv/bin/code-intelligence setup
    .venv/bin/code-intelligence doctor
    .venv/bin/code-intelligence bootstrap

Use the executable directly in scripts and automation; activating the virtual environment is not required:

    /path/to/code-intelligence/.venv/bin/code-intelligence reconcile --repos upfera/code-intelligence,upfera/junie-extensions

## Configuration

Default configuration: ~/.config/code-intelligence/config.yaml.

    github:
      organization: upfera
    repositories:
      # Parent of organization/repository directories, not the organization directory itself.
      root: ~/workspace/github
      include: ["*"]
      exclude: []
    git:
      protocol: ssh
    indexers:
      cbm:
        enabled: true
        command: codebase-memory-mcp
        timeout_seconds: 1800
      serena:
        enabled: true
    tools:
      auto_update: false

## Commands

- setup: create the user configuration.
- doctor: check Git, GitHub authentication, configuration and CBM CLI responsiveness.
- sync [--repos owner/repo,...]: synchronize selected repositories.
- index [--repos owner/repo,...] [--force]: index selected repositories.
- reconcile [--repos owner/repo,...] [--force]: synchronize and index in one process and print a JSON report.
- tools-install / tools-update: explicitly manage optional tools.
- bootstrap: initial setup, installation, sync and full indexing.

The --repos option is an exact allowlist of GitHub owner/repository identities. It is useful for automation and does not expand the configured scope. A repository excluded by the normal include/exclude filters is not synchronized or indexed.

## Incremental indexing

Each repository receives a stable CBM project name based on its canonical GitHub identity, e.g. github-upfera-code-intelligence. The local state file at ~/.local/state/code-intelligence/index-state.json stores the last HEAD whose CBM indexing command returned success.

A reconciliation run skips indexing when the recorded HEAD matches the checkout HEAD. Missing state, a changed HEAD or --force triggers indexing. The state file is only a local optimization: it is not independent proof that the CBM project still exists or that its index has not been removed. If CBM's project inventory is unavailable, that limitation must be treated explicitly rather than claiming an independently verified index.

Dirty repositories are skipped. Git synchronization uses fast-forward-only updates. Reconciliation does not delete local clones or CBM projects. A partial failure produces a non-zero exit status and a machine-readable report.

## Architecture

GitHub -> code-intelligence reconcile -> local default-branch clones -> CBM
Serena -> started separately for the active agent/task workspace
