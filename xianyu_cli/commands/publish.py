from __future__ import annotations

import math
import os
import sys
from argparse import Namespace
from pathlib import Path
from typing import Any, Sequence, TextIO

from xianyu_cli.api.client import APIClient, APIClientError, normalize_bearer_token
from xianyu_cli.interactive.cookies import build_cookie_choices, prompt_cookie_selection
from xianyu_cli.output import print_error, print_json, print_publish_summary

DEFAULT_SERVER = "http://127.0.0.1:8090"


class CLIUsageError(ValueError):
    """Raised when the CLI input is invalid before an API request is sent."""


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser("publish", help="发布商品到一个或多个闲鱼账号")
    parser.add_argument("--cookie-id", action="append", dest="cookie_ids", help="目标账号 ID，可重复传入")
    parser.add_argument("--title", help="商品标题")
    parser.add_argument("--description", required=True, help="商品描述")
    parser.add_argument("--price", required=True, type=float, help="商品价格")
    parser.add_argument("--image", action="append", dest="images", required=True, help="商品图片路径，可重复传入")
    parser.add_argument("--category", help="商品分类路径，例如 数码产品/手机/苹果")
    parser.add_argument("--location", help="发货地，例如 北京市/朝阳区")
    parser.add_argument("--original-price", type=float, dest="original_price", help="商品原价")
    parser.add_argument("--quantity", type=int, help="无规格商品库存，必须大于 0")
    parser.add_argument("--server", help="服务地址，默认读取 XIANYU_SERVER 或 http://127.0.0.1:8090")
    parser.add_argument("--token", help="后台 Bearer token，默认读取 XIANYU_TOKEN")
    parser.add_argument("--json", action="store_true", dest="json_output", help="以 JSON 输出执行结果")
    parser.set_defaults(handler=handle_publish)


def handle_publish(
    args: Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        server = _resolve_server(args.server)
        token = _resolve_token(args.token)
        description = _require_text(args.description, field_name="商品描述")
        title = _optional_text(args.title)
        category = _optional_text(args.category)
        location = _optional_text(args.location)
        price = _validate_non_negative_number(args.price, field_name="商品价格")
        original_price = _validate_optional_non_negative_number(
            args.original_price,
            field_name="商品原价",
        )
        quantity = _validate_optional_positive_int(
            getattr(args, "quantity", None),
            field_name="商品库存",
        )

        with client_factory(server, token) as client:
            client.check_health()
            cookie_ids = _resolve_cookie_ids(
                args.cookie_ids,
                client,
                stdin=stdin,
                prompt_stream=stderr if args.json_output else stdout,
            )
            image_paths = _prepare_publish_images(client, args.images)
            report = _publish_to_cookies(
                client,
                cookie_ids=cookie_ids,
                title=title,
                description=description,
                price=price,
                image_paths=image_paths,
                category=category,
                location=location,
                original_price=original_price,
                quantity=quantity,
            )
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return _emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(report, stdout)
    else:
        print_publish_summary(report, stdout)

    return 0 if report.get("success") else 1


def _resolve_server(raw_server: str | None) -> str:
    return str(raw_server or os.getenv("XIANYU_SERVER") or DEFAULT_SERVER).strip()


def _resolve_token(raw_token: str | None) -> str:
    return normalize_bearer_token(raw_token or os.getenv("XIANYU_TOKEN") or "")


def _require_text(value: str | None, *, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned:
        raise CLIUsageError(f"{field_name}不能为空")
    return cleaned


def _optional_text(value: str | None) -> str | None:
    cleaned = str(value or "").strip()
    return cleaned or None


def _validate_non_negative_number(value: float, *, field_name: str) -> float:
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise CLIUsageError(f"{field_name}必须是有限数字")
    if numeric_value < 0:
        raise CLIUsageError(f"{field_name}不能小于 0")
    return numeric_value


def _validate_optional_non_negative_number(value: float | None, *, field_name: str) -> float | None:
    if value is None:
        return None
    return _validate_non_negative_number(value, field_name=field_name)


def _validate_optional_positive_int(value: int | None, *, field_name: str) -> int | None:
    if value is None:
        return None

    numeric_value = int(value)
    if numeric_value < 1:
        raise CLIUsageError(f"{field_name}必须大于 0")
    return numeric_value


def _prepare_publish_images(client: APIClient, raw_images: Sequence[str] | None) -> list[str]:
    if not raw_images:
        raise CLIUsageError("至少提供一个 --image")

    resolved_paths: list[str] = []
    for raw_image in raw_images:
        candidate = str(raw_image or "").strip()
        if not candidate:
            raise CLIUsageError("图片路径不能为空")

        if candidate.startswith(("http://", "https://")):
            raise CLIUsageError("暂不支持远程图片 URL，请使用本地文件路径或服务端 /static/... 路径")

        if _is_server_image_path(candidate):
            resolved_paths.append(candidate)
            continue

        resolved_paths.append(client.upload_image(_resolve_local_image_path(candidate)))

    return resolved_paths


def _is_server_image_path(candidate: str) -> bool:
    return candidate.startswith("/static/") or candidate.startswith("static/")


def _resolve_local_image_path(candidate: str) -> str:
    image_path = Path(candidate).expanduser()
    absolute_path = image_path if image_path.is_absolute() else image_path.resolve()
    if not absolute_path.exists():
        raise CLIUsageError(f"图片不存在: {candidate}")
    if not absolute_path.is_file():
        raise CLIUsageError(f"图片路径不是文件: {candidate}")
    return str(absolute_path)


def _resolve_cookie_ids(
    raw_cookie_ids: Sequence[str] | None,
    client: APIClient,
    *,
    stdin: TextIO,
    prompt_stream: TextIO,
) -> list[str]:
    explicit_cookie_ids = _normalize_cookie_ids(raw_cookie_ids)
    if explicit_cookie_ids:
        return explicit_cookie_ids

    if not _is_interactive_terminal(stdin):
        raise CLIUsageError("未提供 --cookie-id，且当前不是交互终端")

    choices = build_cookie_choices(client.get_cookie_details(), enabled_only=True)
    if not choices:
        raise CLIUsageError("当前没有可用的启用账号")

    return prompt_cookie_selection(choices, stdin=stdin, stdout=prompt_stream)


def _normalize_cookie_ids(raw_cookie_ids: Sequence[str] | None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()

    for raw_cookie_id in raw_cookie_ids or []:
        cookie_id = str(raw_cookie_id or "").strip()
        if not cookie_id:
            continue
        if cookie_id in seen:
            continue
        seen.add(cookie_id)
        normalized.append(cookie_id)

    return normalized


def _is_interactive_terminal(stream: TextIO) -> bool:
    isatty = getattr(stream, "isatty", None)
    if callable(isatty):
        return bool(isatty())
    return False


def _publish_to_cookies(
    client: APIClient,
    *,
    cookie_ids: Sequence[str],
    title: str | None,
    description: str,
    price: float,
    image_paths: Sequence[str],
    category: str | None,
    location: str | None,
    original_price: float | None,
    quantity: int | None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for cookie_id in cookie_ids:
        payload = {
            "cookie_id": cookie_id,
            "title": title,
            "description": description,
            "price": price,
            "images": list(image_paths),
            "category": category,
            "location": location,
            "original_price": original_price,
            "quantity": quantity,
        }

        try:
            response = client.publish_product(payload)
        except APIClientError as exc:
            results.append(
                {
                    "cookie_id": cookie_id,
                    "success": False,
                    "message": str(exc),
                    "status_code": exc.status_code,
                }
            )
            continue

        result = {
            "cookie_id": cookie_id,
            "success": bool(response.get("success")),
            "message": str(response.get("message") or ""),
        }

        if response.get("product_id"):
            result["product_id"] = response["product_id"]
        if response.get("product_url"):
            result["product_url"] = response["product_url"]
        if response.get("existing_product"):
            result["existing_product"] = response["existing_product"]

        results.append(result)

    success_count = sum(1 for item in results if item.get("success"))
    failed_count = len(results) - success_count

    return {
        "success": failed_count == 0,
        "completed": True,
        "summary": {
            "total": len(results),
            "success": success_count,
            "failed": failed_count,
        },
        "results": results,
    }


def _emit_fatal_error(
    message: str,
    *,
    json_output: bool,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    if json_output:
        print_json(
            {
                "success": False,
                "completed": False,
                "message": message,
            },
            stdout,
        )
        return 1

    print_error(message, stderr)
    return 1
