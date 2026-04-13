from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, TextIO


@dataclass(frozen=True)
class CookieChoice:
    cookie_id: str
    remark: str
    username: str
    runtime_status: dict[str, Any]


def build_cookie_choices(
    raw_cookies: Iterable[dict[str, Any]],
    *,
    enabled_only: bool = True,
) -> list[CookieChoice]:
    """Convert backend cookie details into selectable CLI entries."""
    choices: list[CookieChoice] = []
    for item in raw_cookies:
        cookie_id = str(item.get("id") or "").strip()
        if not cookie_id:
            continue

        if enabled_only and not bool(item.get("enabled")):
            continue

        choices.append(
            CookieChoice(
                cookie_id=cookie_id,
                remark=str(item.get("remark") or "").strip(),
                username=str(item.get("username") or "").strip(),
                runtime_status=item.get("runtime_status") or {},
            )
        )
    return choices


def summarize_runtime_status(runtime_status: dict[str, Any] | None) -> str:
    """Render a short runtime status label for interactive choice lists."""
    if not isinstance(runtime_status, dict):
        return "未知"

    connection_state = str(runtime_status.get("connection_state") or "").strip()
    if runtime_status.get("running"):
        return connection_state or "running"

    if connection_state and connection_state != "not_running":
        return connection_state

    if runtime_status.get("instance_exists"):
        return "已创建未连接"

    return "未运行"


def prompt_cookie_selection(
    choices: list[CookieChoice],
    *,
    stdin: TextIO,
    stdout: TextIO,
) -> list[str]:
    """Prompt the user to select one or more cookie IDs by index."""
    if not choices:
        raise ValueError("当前没有可用的启用账号")

    while True:
        _render_cookie_choices(choices, stdout)
        print("请输入要使用的账号序号，多个用空格分隔：", end="", file=stdout)
        stdout.flush()

        raw = stdin.readline()
        if raw == "":
            raise ValueError("未读取到账号选择输入")

        try:
            selected_indexes = parse_cookie_selection(raw, len(choices))
        except ValueError as exc:
            print(f"输入无效: {exc}", file=stdout)
            continue

        return [choices[index - 1].cookie_id for index in selected_indexes]


def parse_cookie_selection(raw: str, max_index: int) -> list[int]:
    """Parse space-separated menu indexes into unique ordered selections."""
    tokens = [token for token in re.split(r"[\s,]+", raw.strip()) if token]
    if not tokens:
        raise ValueError("至少选择一个账号")

    indexes: list[int] = []
    seen: set[int] = set()
    for token in tokens:
        if not token.isdigit():
            raise ValueError(f"无效序号: {token}")

        index = int(token)
        if index < 1 or index > max_index:
            raise ValueError(f"序号超出范围: {index}")

        if index in seen:
            continue
        seen.add(index)
        indexes.append(index)

    return indexes


def _render_cookie_choices(choices: list[CookieChoice], stdout: TextIO) -> None:
    print("可用账号：", file=stdout)
    for idx, choice in enumerate(choices, start=1):
        parts = [f"{idx}. {choice.cookie_id}"]
        if choice.remark:
            parts.append(f"备注: {choice.remark}")
        if choice.username:
            parts.append(f"用户名: {choice.username}")
        parts.append(f"状态: {summarize_runtime_status(choice.runtime_status)}")
        print(" | ".join(parts), file=stdout)
