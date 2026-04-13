from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, TextIO


@dataclass(frozen=True)
class CardChoice:
    card_id: int
    name: str
    card_type: str
    enabled: bool
    is_multi_spec: bool
    spec_name: str
    spec_value: str
    spec_name_2: str
    spec_value_2: str


def build_card_choices(
    raw_cards: Iterable[dict[str, Any]],
    *,
    enabled_only: bool = True,
) -> list[CardChoice]:
    choices: list[CardChoice] = []
    for item in raw_cards:
        card_id = item.get("id")
        if not isinstance(card_id, int):
            continue

        enabled = bool(item.get("enabled"))
        if enabled_only and not enabled:
            continue

        choices.append(
            CardChoice(
                card_id=card_id,
                name=str(item.get("name") or "").strip(),
                card_type=str(item.get("type") or "").strip(),
                enabled=enabled,
                is_multi_spec=bool(item.get("is_multi_spec")),
                spec_name=str(item.get("spec_name") or "").strip(),
                spec_value=str(item.get("spec_value") or "").strip(),
                spec_name_2=str(item.get("spec_name_2") or "").strip(),
                spec_value_2=str(item.get("spec_value_2") or "").strip(),
            )
        )
    return choices


def prompt_card_selection(
    choices: list[CardChoice],
    *,
    stdin: TextIO,
    stdout: TextIO,
) -> int:
    if not choices:
        raise ValueError("当前没有可用的启用卡片")

    while True:
        _render_card_choices(choices, stdout)
        print("请输入要使用的卡片序号：", end="", file=stdout)
        stdout.flush()

        raw = stdin.readline()
        if raw == "":
            raise ValueError("未读取到卡片选择输入")

        try:
            selected_index = parse_card_selection(raw, len(choices))
        except ValueError as exc:
            print(f"输入无效: {exc}", file=stdout)
            continue

        return choices[selected_index - 1].card_id


def parse_card_selection(raw: str, max_index: int) -> int:
    token = str(raw).strip()
    if not token:
        raise ValueError("必须选择一个卡片")
    if not token.isdigit():
        raise ValueError(f"无效序号: {token}")

    index = int(token)
    if index < 1 or index > max_index:
        raise ValueError(f"序号超出范围: {index}")

    return index


def _render_card_choices(choices: list[CardChoice], stdout: TextIO) -> None:
    print("可用卡片：", file=stdout)
    for idx, choice in enumerate(choices, start=1):
        parts = [f"{idx}. {choice.card_id}", choice.name or "未命名卡片", choice.card_type or "unknown"]
        if choice.is_multi_spec and choice.spec_name and choice.spec_value:
            spec_summary = f"{choice.spec_name}:{choice.spec_value}"
            if choice.spec_name_2 and choice.spec_value_2:
                spec_summary = f"{spec_summary}, {choice.spec_name_2}:{choice.spec_value_2}"
            parts.append(f"规格: {spec_summary}")
        print(" | ".join(parts), file=stdout)
