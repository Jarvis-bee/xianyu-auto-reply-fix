---
name: xianyu-cli
description: Work on the `xianyu_cli` package in this repository. Use when Codex needs to add or update `xianyu` subcommands such as `publish`, `card`, or `delivery-rule`, change the shared CLI API client or interactive selection flows, fix current CLI contracts, adjust packaging/install behavior for the local CLI, update CLI tests/docs, or validate the installed command/help flow.
---

# Xianyu CLI

## Overview

Build or extend the repository's local `xianyu` command without coupling the CLI to business modules. Keep the CLI as a thin, installable client over the existing FastAPI service, preserve existing command contracts unless the task explicitly changes them, and treat `publish`, `card`, and `delivery-rule` as peer subcommand groups under one root CLI.

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

## Command Rules

- Keep the root parser pluggable.
  Register subcommands from `xianyu_cli/commands/*.py` via `register(subparsers)`; avoid collapsing everything into one file.
- Keep `publish` as a thin client over `/health`, `/cookies/details`, and `/api/products/publish`.
- Keep `card` as a thin client over `/cards` and `/upload-image`.
- Keep `delivery-rule` as a thin client over `/delivery-rules` and `/delivery-rules/stats`.
- Preserve current UX unless the task explicitly changes it:
  `publish` uses optional repeatable `--cookie-id` with interactive cookie multi-select only when omitted; `delivery-rule create` uses optional `--card-id` with interactive card single-select only when omitted.
- Preserve scriptability:
  human-readable output by default, machine-readable JSON with `--json`, and no prompt text on `stdout` during JSON mode.

## Backend Coupling

- When a change touches publish semantics or cookie selection, inspect the matching FastAPI handlers in `reply_server.py` before editing the CLI.
- When a change touches card or delivery-rule updates, inspect the FastAPI update handlers and preserve backend-required fields instead of assuming PATCH semantics.
- Current backend quirk:
  `reply_server.update_card()` defaults missing `enabled` to `True`, and `reply_server.update_delivery_rule()` defaults missing `enabled` to `True` and missing `delivery_count` to `1`. The CLI must carry forward current values on partial updates.
- When a change touches validation, update the matching CLI tests first or alongside the code:
  `tests/test_publish_cli.py`, `tests/test_card_cli.py`, or `tests/test_delivery_rule_cli.py`.
- When a change touches output or error handling, keep scriptability in mind; avoid mixing human prose into `--json` mode.

## References

- Read [references/current-contract.md](references/current-contract.md) when you need the current file map, command contracts, endpoint dependencies, update semantics, or the exact validation commands.
