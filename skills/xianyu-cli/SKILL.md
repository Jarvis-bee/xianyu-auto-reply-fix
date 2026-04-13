---
name: xianyu-cli
description: Work on the `xianyu_cli` package in this repository. Use when Codex needs to add or update `xianyu` subcommands, change the shared CLI API client or interactive cookie selection flow, fix `xianyu publish`, adjust packaging/install behavior for the local CLI, update CLI tests/docs, or validate the installed command/help flow.
---

# Xianyu CLI

## Overview

Build or extend the repository's local `xianyu` command without coupling the CLI to business modules. Keep the CLI as a thin, installable client over the existing FastAPI service and preserve the current `publish` contract unless the task explicitly changes it.

## Workflow

1. Read the current command surface before editing.
   Start with `pyproject.toml`, `xianyu_cli/main.py`, and the target file under `xianyu_cli/`.
2. Keep subcommands pluggable.
   Register each subcommand from `xianyu_cli/commands/*.py` via `register(subparsers)` and keep shared logic in `xianyu_cli/api/`, `xianyu_cli/interactive/`, or `xianyu_cli/output.py`.
3. Prefer existing HTTP endpoints over direct business-module imports.
   If a CLI feature maps to an existing FastAPI route, call it through the shared API client instead of importing large runtime modules.
4. Preserve packaging and installability.
   Keep `pyproject.toml` and `xianyu_build_backend.py` working with `python3 -m pip install -e .`; do not reintroduce a backend that depends on network-installed build tooling unless the task explicitly requires it.
5. Validate after changes.
   Run the CLI-specific checks in [references/current-contract.md](references/current-contract.md).

## Publish Rules

- `xianyu publish` is the current only subcommand. Extend around it; do not hard-code the whole CLI as a one-command script.
- Keep `publish` as a thin client over `/health`, `/cookies/details`, and `/api/products/publish`.
- Preserve current UX unless the task explicitly changes it:
  `--cookie-id` is optional and repeatable, interactive selection only happens when `--cookie-id` is omitted, and non-interactive mode without `--cookie-id` must fail.
- Preserve multi-account semantics:
  one product payload is published sequentially to each selected `cookie_id`, failures do not stop later accounts, and the command exits non-zero if any account fails.
- Preserve result semantics:
  human-readable output by default, summary JSON with `--json`, and exit code `0` only when every selected account succeeds.

## Backend Coupling

- When a change touches publish semantics or cookie selection, inspect the matching FastAPI handlers in `reply_server.py` before editing the CLI.
- When a change touches validation, update `tests/test_publish_cli.py` first or alongside the code.
- When a change touches output or error handling, keep scriptability in mind; avoid mixing human prose into `--json` mode.

## References

- Read [references/current-contract.md](references/current-contract.md) when you need the current file map, publish contract, endpoint dependencies, or the exact validation commands.
