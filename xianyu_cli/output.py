from __future__ import annotations

import json
from typing import Any, TextIO


def print_error(message: str, stream: TextIO) -> None:
    print(f"错误: {message}", file=stream)


def print_json(data: Any, stream: TextIO) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2), file=stream)


def print_publish_summary(report: dict[str, Any], stream: TextIO) -> None:
    summary = report.get("summary") or {}
    total = int(summary.get("total") or 0)
    success_count = int(summary.get("success") or 0)
    failed_count = int(summary.get("failed") or 0)

    print(
        f"发布完成: 总计 {total}，成功 {success_count}，失败 {failed_count}",
        file=stream,
    )

    for result in report.get("results") or []:
        status_label = "成功" if result.get("success") else "失败"
        parts = [
            f"[{status_label}] {result.get('cookie_id')}",
            str(result.get("message") or ""),
        ]

        product_id = result.get("product_id")
        if product_id:
            parts.append(f"product_id={product_id}")

        product_url = result.get("product_url")
        if product_url:
            parts.append(f"product_url={product_url}")

        existing_product = result.get("existing_product")
        if isinstance(existing_product, dict):
            existing_id = existing_product.get("product_id")
            existing_url = existing_product.get("product_url")
            if existing_id:
                parts.append(f"existing_product_id={existing_id}")
            if existing_url:
                parts.append(f"existing_product_url={existing_url}")

        print(" | ".join(part for part in parts if part), file=stream)


def print_card_list(cards: list[dict[str, Any]], stream: TextIO) -> None:
    print(f"卡片总数: {len(cards)}", file=stream)
    for card in cards:
        parts = [
            f"id={card.get('id')}",
            str(card.get("name") or "未命名卡片"),
            f"type={card.get('type') or 'unknown'}",
            f"状态={'启用' if card.get('enabled') else '禁用'}",
        ]
        delay_seconds = card.get("delay_seconds")
        if delay_seconds is not None:
            parts.append(f"delay={delay_seconds}s")

        spec_summary = _format_spec_summary(card)
        if spec_summary:
            parts.append(f"规格={spec_summary}")

        print(" | ".join(parts), file=stream)


def print_card_detail(card: dict[str, Any], stream: TextIO) -> None:
    lines = [
        f"id: {card.get('id')}",
        f"name: {card.get('name') or ''}",
        f"type: {card.get('type') or ''}",
        f"enabled: {bool(card.get('enabled'))}",
        f"delay_seconds: {card.get('delay_seconds') or 0}",
    ]

    description = card.get("description")
    if description not in (None, ""):
        lines.append(f"description: {description}")

    spec_summary = _format_spec_summary(card)
    if spec_summary:
        lines.append(f"spec: {spec_summary}")

    type_name = str(card.get("type") or "").strip()
    if type_name in {"api", "yifan_api"} and card.get("api_config") is not None:
        lines.append(f"api_config: {json.dumps(card['api_config'], ensure_ascii=False)}")
    if type_name == "text" and card.get("text_content") is not None:
        lines.append(f"text_content: {card.get('text_content')}")
    if type_name == "data" and card.get("data_content") is not None:
        lines.append(f"data_content: {card.get('data_content')}")
    if type_name == "image" and card.get("image_url") is not None:
        lines.append(f"image_url: {card.get('image_url')}")

    print("\n".join(lines), file=stream)


def print_delivery_rule_list(rules: list[dict[str, Any]], stream: TextIO) -> None:
    print(f"发货规则总数: {len(rules)}", file=stream)
    for rule in rules:
        parts = [
            f"id={rule.get('id')}",
            f"keyword={rule.get('keyword') or ''}",
            f"card_id={rule.get('card_id')}",
            f"card={rule.get('card_name') or '未知卡片'}",
            f"type={rule.get('card_type') or 'unknown'}",
            f"状态={'启用' if rule.get('enabled') else '禁用'}",
            f"count={rule.get('delivery_count') or 1}",
            f"times={rule.get('delivery_times') or 0}",
        ]

        spec_summary = _format_spec_summary(rule)
        if spec_summary:
            parts.append(f"规格={spec_summary}")

        print(" | ".join(parts), file=stream)


def print_delivery_rule_detail(rule: dict[str, Any], stream: TextIO) -> None:
    lines = [
        f"id: {rule.get('id')}",
        f"keyword: {rule.get('keyword') or ''}",
        f"card_id: {rule.get('card_id')}",
        f"card_name: {rule.get('card_name') or ''}",
        f"card_type: {rule.get('card_type') or ''}",
        f"enabled: {bool(rule.get('enabled'))}",
        f"delivery_count: {rule.get('delivery_count') or 1}",
        f"delivery_times: {rule.get('delivery_times') or 0}",
    ]

    description = rule.get("description")
    if description not in (None, ""):
        lines.append(f"description: {description}")

    spec_summary = _format_spec_summary(rule)
    if spec_summary:
        lines.append(f"spec: {spec_summary}")

    print("\n".join(lines), file=stream)


def print_stats(stats: dict[str, Any], stream: TextIO) -> None:
    print(f"today_delivery_count: {stats.get('today_delivery_count') or 0}", file=stream)


def print_message(message: str, stream: TextIO, *, item_id: Any = None, label: str = "id") -> None:
    parts = [message]
    if item_id is not None:
        parts.append(f"{label}={item_id}")
    print(" | ".join(parts), file=stream)


def _format_spec_summary(item: dict[str, Any]) -> str:
    if not item.get("is_multi_spec"):
        return ""

    spec_name = str(item.get("spec_name") or "").strip()
    spec_value = str(item.get("spec_value") or "").strip()
    if not spec_name or not spec_value:
        return ""

    parts = [f"{spec_name}:{spec_value}"]
    spec_name_2 = str(item.get("spec_name_2") or "").strip()
    spec_value_2 = str(item.get("spec_value_2") or "").strip()
    if spec_name_2 and spec_value_2:
        parts.append(f"{spec_name_2}:{spec_value_2}")
    return ", ".join(parts)
