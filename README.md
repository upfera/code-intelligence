# code-intelligence

Local repository synchronization and code-intelligence orchestration for GitHub organizations.

The project keeps a configured set of GitHub repositories available locally and can maintain code-intelligence indexes such as Codebase Memory MCP. It is designed to run as a normal user process. Root access is only used when explicitly requested for system package installation.

## Goals

- Discover repositories from a GitHub organization.
- Select repositories with glob-style include/exclude patterns.
- Clone missing repositories and fast-forward existing clones.
- Keep repository layout deterministic.
- Install and update local developer tools.
- Index synchronized repositories with Codebase Memory MCP.
- Provide a small CLI now and an MCP interface for agents.
- Keep tool-specific logic behind adapters so additional indexers can be added later.

## Quick start

Requirements:

- Python 3.11+
- git
- GitHub CLI (gh) authenticated for the target organization
- uv for installing the project and managed Python tools

Install:

    git clone https://github.com/upfera/code-intelligence.git
    cd code-intelligence
    uv tool install .

Create a configuration:

    code-intelligence setup

Edit:

    ~/.config/code-intelligence/config.yaml

Then:

    code-intelligence doctor
    code-intelligence tools update
    code-intelligence sync

## Configuration

Example:

    github:
      organization: upfera

    repositories:
      root: ~/code/github

      include:
        - "*"

      exclude:
        - ".github"
        - ".private"
        - "archive-*"

    indexers:
      cbm:
        enabled: true

      serena:
        enabled: false

Patterns use standard shell-style wildcards (*, ?, [seq]) and are matched against repository names.

An empty include list means all repositories. Excludes always win.

## Repository lifecycle

For each selected GitHub repository:

1. Discover it through gh.
2. Clone it when it does not exist locally.
3. Fetch and fast-forward the default branch when it already exists.
4. Leave local changes untouched and report the repository as skipped.
5. Run enabled indexers.

The synchronizer does not delete local repositories when they disappear from GitHub or from the configuration.

## User vs root

The default installation is user-scoped:

- configuration: ~/.config/code-intelligence
- application state: ~/.local/share/code-intelligence
- logs/state: ~/.local/state/code-intelligence
- repositories: configured explicitly
- CBM data remains in CBM's own cache directory

The project never runs sudo implicitly.

## Codebase Memory MCP

When enabled, the CBM adapter invokes the installed codebase-memory-mcp CLI:

    codebase-memory-mcp cli index_repository --repo-path /absolute/path/to/repo

This makes the repository synchronizer independent from the CBM installation mechanism.

## MCP

The project also exposes an MCP server over stdio:

    code-intelligence mcp

Initial tools:

- list_repositories
- sync_repository
- sync_all
- get_repository_status
- index_repository

The MCP layer is intentionally thin. Core synchronization and indexing logic is shared with the CLI.

## Design

    code-intelligence
           |
      +----+----+
      |         |
     CLI       MCP
      |         |
      +----+----+
           |
       core services
      /      |       \
   GitHub   Git    indexers
                    /    \
                  CBM   Serena

Serena is an agent-facing semantic layer and is not started as one long-running process per repository. Its integration is therefore kept separate from the repository synchronization lifecycle.

## Status

Initial implementation. Future iterations can add scheduled synchronization via systemd timer, optional GitHub webhooks, richer tool version management, Serena project management, SCIP/LSP adapters, and cross-repository intelligence.
