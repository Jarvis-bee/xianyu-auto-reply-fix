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
