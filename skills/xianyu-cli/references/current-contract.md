# Xianyu CLI Current Contract

## File Map

- `pyproject.toml`: exposes the installable `xianyu` entrypoint.
- `xianyu_build_backend.py`: local editable/wheel backend used to avoid external build-tool dependencies.
- `xianyu_cli/main.py`: root parser and subcommand registration.
- `xianyu_cli/commands/publish.py`: current `xianyu publish` implementation.
- `xianyu_cli/api/client.py`: shared HTTP client, Bearer token normalization, API error extraction.
- `xianyu_cli/interactive/cookies.py`: interactive cookie list rendering and space-separated multi-select parsing.
- `xianyu_cli/output.py`: human-readable and JSON-safe output helpers.
- `tests/test_publish_cli.py`: CLI unit coverage for help text, non-interactive failure, multi-select flow, and multi-account publish semantics.

## Current Publish Behavior

### Arguments

- Required: `--description`, `--price`, `--image` (repeatable)
- Optional: `--cookie-id` (repeatable), `--title`, `--category`, `--location`, `--original-price`, `--server`, `--token`, `--json`

### Resolution Rules

- Server precedence: `--server` -> `XIANYU_SERVER` -> `http://127.0.0.1:8090`
- Token precedence: `--token` -> `XIANYU_TOKEN`
- Token accepts raw token or `Bearer ...`, then normalizes to `Authorization: Bearer <token>`
- Image paths resolve to absolute local file paths and must exist before any request is sent

### Interactive Cookie Selection

- If `--cookie-id` is provided, use those IDs directly after trimming and de-duplicating.
- If `--cookie-id` is omitted and stdin is interactive:
  call `GET /cookies/details`, keep only `enabled=true`, render `id / remark / username / runtime status`, and let the user choose by space-separated indices.
- If `--cookie-id` is omitted and stdin is not interactive:
  fail before sending publish requests.

### API Dependencies

- `GET /health`
- `GET /cookies/details`
- `POST /api/products/publish`

When behavior changes, inspect the matching handlers in `reply_server.py`.

### Multi-Account Semantics

- One product payload is reused for every selected `cookie_id`
- Publish sequentially, not concurrently
- A failed account does not stop the next account
- Exit code is `0` only if every selected account succeeds

### Output Contract

- Default mode prints a human-readable summary per account
- `--json` prints a summary object:
  - `success`
  - `completed`
  - `summary.total`
  - `summary.success`
  - `summary.failed`
  - `results[]`
- Avoid mixing plain-text status lines into `--json` mode

## Validation Commands

Run all of these after CLI changes:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall xianyu_cli tests xianyu_build_backend.py
python3 -m pip install -e .
xianyu --help
xianyu publish --help
```

## Typical Change Patterns

- Add a subcommand:
  create `xianyu_cli/commands/<name>.py`, expose `register(subparsers)`, import and register it in `xianyu_cli/main.py`, then add tests and help verification.
- Change publish validation:
  edit `xianyu_cli/commands/publish.py` and extend `tests/test_publish_cli.py` in the same change.
- Change HTTP behavior:
  centralize reusable request/authorization/error logic in `xianyu_cli/api/client.py`.
- Change interactive account selection:
  keep the prompt logic in `xianyu_cli/interactive/cookies.py`; avoid duplicating selection parsing in subcommands.
