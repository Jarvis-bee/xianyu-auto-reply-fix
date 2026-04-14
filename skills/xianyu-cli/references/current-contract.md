# Xianyu CLI Current Contract

## File Map

- `pyproject.toml`: exposes the installable `xianyu` entrypoint.
- `xianyu_build_backend.py`: local editable/wheel backend used to avoid external build-tool dependencies.
- `xianyu_cli/main.py`: root parser and subcommand registration.
- `xianyu_cli/cli_common.py`: shared CLI validation, env resolution, JSON-safe fatal error output.
- `xianyu_cli/commands/publish.py`: `xianyu publish` implementation.
- `xianyu_cli/commands/card.py`: `xianyu card list|get|create|update|delete`.
- `xianyu_cli/commands/delivery_rule.py`: `xianyu delivery-rule list|get|create|update|delete|stats`.
- `xianyu_cli/api/client.py`: shared HTTP client, Bearer token normalization, API error extraction.
- `xianyu_cli/interactive/cookies.py`: interactive cookie list rendering and space-separated multi-select parsing.
- `xianyu_cli/interactive/cards.py`: interactive card list rendering and single-select parsing for rule creation.
- `xianyu_cli/output.py`: human-readable and JSON-safe output helpers.
- `tests/test_publish_cli.py`: CLI unit coverage for help text, non-interactive failure, multi-select flow, and multi-account publish semantics.
- `tests/test_card_cli.py`: card create/update validation and state-preservation coverage.
- `tests/test_delivery_rule_cli.py`: delivery-rule create/update validation and state-preservation coverage.

## Current Command Surface

- `xianyu publish`
- `xianyu card list|get|create|update|delete`
- `xianyu delivery-rule list|get|create|update|delete|stats`

All subcommands support:

- `--server`
- `--token`
- `--json`

## Publish Behavior

### Arguments

- Required: `--description`, `--price`, `--image` (repeatable)
- Optional: `--cookie-id` (repeatable), `--title`, `--category`, `--location`, `--original-price`, `--quantity`, `--server`, `--token`, `--json`

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

### Publish Payload Notes

- `--quantity` is optional and is only intended for no-spec products
- CLI forwards `quantity` unchanged to `/api/products/publish`
- Backend rejects `quantity <= 0`

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

## Card Behavior

### Subcommands

- `xianyu card list`
- `xianyu card get <card_id>`
- `xianyu card create`
- `xianyu card update <card_id>`
- `xianyu card delete <card_id>`

### Card Types

- `api`
- `yifan_api`
- `text`
- `data`
- `image`

### Create and Update Notes

- `card create` requires `--name` and `--type`
- `card update` does not allow cross-type conversion
- `image` card local files upload through `POST /upload-image` before hitting `/cards`
- `api` card `method` must stay within `GET` or `POST`
- `api_config.headers` and `api_config.params` are stored as JSON strings to stay compatible with the existing frontend/editor flow

### Update Semantics

- The backend card update route is not true PATCH:
  missing `enabled` becomes `True`
- Because of that, CLI partial updates must preserve the current `enabled` state when the user did not explicitly pass `--enabled` or `--disabled`
- Multi-spec cards can now be disabled with `--no-multi-spec`; doing so must also clear `spec_*` fields
- `yifan_api` supports both `--yifan-require-account` and `--no-yifan-require-account`

### API Dependencies

- `GET /health`
- `GET /cards`
- `GET /cards/{card_id}`
- `POST /cards`
- `PUT /cards/{card_id}`
- `DELETE /cards/{card_id}`
- `POST /upload-image`

## Delivery Rule Behavior

### Subcommands

- `xianyu delivery-rule list`
- `xianyu delivery-rule get <rule_id>`
- `xianyu delivery-rule create`
- `xianyu delivery-rule update <rule_id>`
- `xianyu delivery-rule delete <rule_id>`
- `xianyu delivery-rule stats`

### Create and Update Notes

- `create` defaults `delivery_count=1` and `enabled=true`
- `delivery_count` must be an integer >= 1
- `create` interactively selects an enabled card when `--card-id` is omitted and stdin is interactive
- JSON mode must keep prompt text on `stderr`, never `stdout`

### Update Semantics

- The backend rule update route is not true PATCH:
  missing `enabled` becomes `True`, and missing `delivery_count` becomes `1`
- Because of that, CLI partial updates must preserve current `enabled` and `delivery_count` when omitted by the user

### API Dependencies

- `GET /health`
- `GET /cards`
- `GET /delivery-rules`
- `GET /delivery-rules/{rule_id}`
- `POST /delivery-rules`
- `PUT /delivery-rules/{rule_id}`
- `DELETE /delivery-rules/{rule_id}`
- `GET /delivery-rules/stats`

## Validation Commands

Run all of these after CLI changes:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall xianyu_cli tests xianyu_build_backend.py
python3 -m pip install -e .
xianyu --help
xianyu publish --help
xianyu card --help
xianyu delivery-rule --help
```

## Typical Change Patterns

- Add a subcommand:
  create `xianyu_cli/commands/<name>.py`, expose `register(subparsers)`, import and register it in `xianyu_cli/main.py`, then add tests and help verification.
- Change publish validation:
  edit `xianyu_cli/commands/publish.py` and extend `tests/test_publish_cli.py` in the same change.
- Change card behavior:
  edit `xianyu_cli/commands/card.py`, keep HTTP logic in `xianyu_cli/api/client.py`, and extend `tests/test_card_cli.py`.
- Change delivery-rule behavior:
  edit `xianyu_cli/commands/delivery_rule.py`, keep interactive card selection in `xianyu_cli/interactive/cards.py`, and extend `tests/test_delivery_rule_cli.py`.
- Change HTTP behavior:
  centralize reusable request/authorization/error logic in `xianyu_cli/api/client.py`.
- Change interactive account selection:
  keep the prompt logic in `xianyu_cli/interactive/cookies.py`; avoid duplicating selection parsing in subcommands.
- Change interactive card selection:
  keep the prompt logic in `xianyu_cli/interactive/cards.py`; avoid duplicating selection parsing in subcommands.
