from __future__ import annotations

import json
import os
import sys
from typing import Any, TextIO

from xianyu_cli.api.client import normalize_bearer_token
from xianyu_cli.output import print_error, print_json

DEFAULT_SERVER = "http://127.0.0.1:8090"


class CLIUsageError(ValueError):
    """Raised when the CLI input is invalid before an API request is sent."""


def resolve_server(raw_server: str | None) -> str:
    return str(raw_server or os.getenv("XIANYU_SERVER") or DEFAULT_SERVER).strip()


def resolve_token(raw_token: str | None) -> str:
    return normalize_bearer_token(raw_token or os.getenv("XIANYU_TOKEN") or "")


def require_text(value: str | None, *, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise CLIUsageError(f"{field_name}不能为空")
    return cleaned


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    return str(value).strip()


def optional_text_or_none(value: str | None) -> str | None:
    cleaned = optional_text(value)
    if cleaned is None:
        return None
    return cleaned or ""


def validate_non_negative_int(value: Any, *, field_name: str) -> int:
    try:
        numeric_value = int(value)
    except (TypeError, ValueError) as exc:
        raise CLIUsageError(f"{field_name}必须是整数") from exc

    if numeric_value < 0:
        raise CLIUsageError(f"{field_name}不能小于 0")

    return numeric_value


def validate_positive_int(value: Any, *, field_name: str) -> int:
    numeric_value = validate_non_negative_int(value, field_name=field_name)
    if numeric_value < 1:
        raise CLIUsageError(f"{field_name}必须大于等于 1")
    return numeric_value


def parse_json_object(value: str | None, *, field_name: str) -> dict[str, Any] | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    if not cleaned:
        return {}

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise CLIUsageError(f"{field_name}必须是合法的 JSON 对象") from exc

    if not isinstance(payload, dict):
        raise CLIUsageError(f"{field_name}必须是 JSON 对象")

    return payload


def dumps_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def is_interactive_terminal(stream: TextIO) -> bool:
    isatty = getattr(stream, "isatty", None)
    if callable(isatty):
        return bool(isatty())
    return False


def emit_fatal_error(
    message: str,
    *,
    json_output: bool,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    if json_output:
        print_json(
            {
                "success": False,
                "message": message,
            },
            stdout,
        )
        return 1

    print_error(message, stderr)
    return 1
