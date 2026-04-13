from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, TextIO

from xianyu_cli.api.client import APIClient, APIClientError
from xianyu_cli.cli_common import (
    CLIUsageError,
    dumps_json,
    emit_fatal_error,
    optional_text,
    require_text,
    resolve_server,
    resolve_token,
    validate_non_negative_int,
    validate_positive_int,
    parse_json_object,
)
from xianyu_cli.output import print_card_detail, print_card_list, print_json, print_message

CARD_TYPES = {"api", "yifan_api", "text", "data", "image"}


def register(subparsers: Any) -> None:
    parser = subparsers.add_parser("card", help="管理自动发货卡片")
    parser.set_defaults(handler=_make_help_handler(parser))
    card_subparsers = parser.add_subparsers(dest="card_command", metavar="<subcommand>")

    list_parser = card_subparsers.add_parser("list", help="列出卡片")
    _add_runtime_args(list_parser)
    list_parser.set_defaults(handler=handle_list_cards)

    get_parser = card_subparsers.add_parser("get", help="查看卡片详情")
    get_parser.add_argument("card_id", type=int, help="卡片 ID")
    _add_runtime_args(get_parser)
    get_parser.set_defaults(handler=handle_get_card)

    create_parser = card_subparsers.add_parser("create", help="创建卡片")
    _add_card_arguments(create_parser, create_mode=True)
    _add_runtime_args(create_parser)
    create_parser.set_defaults(handler=handle_create_card)

    update_parser = card_subparsers.add_parser("update", help="更新卡片")
    update_parser.add_argument("card_id", type=int, help="卡片 ID")
    _add_card_arguments(update_parser, create_mode=False)
    _add_runtime_args(update_parser)
    update_parser.set_defaults(handler=handle_update_card)

    delete_parser = card_subparsers.add_parser("delete", help="删除卡片")
    delete_parser.add_argument("card_id", type=int, help="卡片 ID")
    _add_runtime_args(delete_parser)
    delete_parser.set_defaults(handler=handle_delete_card)


def handle_list_cards(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            cards = client.list_cards()
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(cards, stdout)
    else:
        print_card_list(cards, stdout)
    return 0


def handle_get_card(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            card = client.get_card(args.card_id)
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(card, stdout)
    else:
        print_card_detail(card, stdout)
    return 0


def handle_create_card(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            payload = _build_create_payload(args, client)
            response = client.create_card(payload)
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(response, stdout)
    else:
        print_message(str(response.get("message") or "卡片创建成功"), stdout, item_id=response.get("id"))
    return 0


def handle_update_card(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            existing = client.get_card(args.card_id)
            payload = _build_update_payload(args, existing, client)
            response = client.update_card(args.card_id, payload)
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(response, stdout)
    else:
        print_message(str(response.get("message") or "卡片更新成功"), stdout, item_id=args.card_id)
    return 0


def handle_delete_card(
    args: argparse.Namespace,
    *,
    client_factory: type[APIClient] = APIClient,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    try:
        with client_factory(resolve_server(args.server), resolve_token(args.token)) as client:
            client.check_health()
            response = client.delete_card(args.card_id)
    except (CLIUsageError, APIClientError, ValueError) as exc:
        return emit_fatal_error(str(exc), json_output=bool(args.json_output), stdout=stdout, stderr=stderr)

    if args.json_output:
        print_json(response, stdout)
    else:
        print_message(str(response.get("message") or "卡片删除成功"), stdout, item_id=args.card_id)
    return 0


def _add_card_arguments(parser: argparse.ArgumentParser, *, create_mode: bool) -> None:
    parser.add_argument("--name", required=create_mode, help="卡片名称")
    parser.add_argument("--type", dest="card_type", required=create_mode, help="卡片类型")
    parser.add_argument("--description", help="卡片描述")
    parser.add_argument("--delay-seconds", help="延迟发货秒数")
    state_group = parser.add_mutually_exclusive_group()
    state_group.add_argument("--enabled", dest="enabled", action="store_true", help="启用卡片")
    state_group.add_argument("--disabled", dest="enabled", action="store_false", help="禁用卡片")
    parser.set_defaults(enabled=None)
    multi_spec_group = parser.add_mutually_exclusive_group()
    multi_spec_group.add_argument("--multi-spec", dest="is_multi_spec", action="store_const", const=True, default=None, help="启用多规格")
    multi_spec_group.add_argument("--no-multi-spec", dest="is_multi_spec", action="store_const", const=False, help="关闭多规格")
    parser.add_argument("--spec-name", help="规格 1 名称")
    parser.add_argument("--spec-value", help="规格 1 值")
    parser.add_argument("--spec-name-2", help="规格 2 名称")
    parser.add_argument("--spec-value-2", help="规格 2 值")

    parser.add_argument("--text-content", help="固定文字内容")
    parser.add_argument("--data-content", help="批量数据内容")
    parser.add_argument("--image", help="图片路径或服务端 /static/... 路径")

    parser.add_argument("--api-url", help="API 请求地址")
    parser.add_argument("--api-method", help="API 请求方法，默认 GET")
    parser.add_argument("--api-timeout", help="API 超时时间（秒）")
    parser.add_argument("--api-headers-json", help="API 请求头 JSON 对象")
    parser.add_argument("--api-params-json", help="API 请求参数 JSON 对象")

    parser.add_argument("--yifan-user-id", help="亦凡 API 商户 ID")
    parser.add_argument("--yifan-user-key", help="亦凡 API 商户 KEY")
    parser.add_argument("--yifan-goods-id", help="亦凡 API 商品 ID")
    parser.add_argument("--yifan-callback-url", help="亦凡 API 回调地址")
    yifan_require_account_group = parser.add_mutually_exclusive_group()
    yifan_require_account_group.add_argument(
        "--yifan-require-account",
        dest="yifan_require_account",
        action="store_const",
        const=True,
        default=None,
        help="亦凡 API 启用账号信息回传",
    )
    yifan_require_account_group.add_argument(
        "--no-yifan-require-account",
        dest="yifan_require_account",
        action="store_const",
        const=False,
        help="亦凡 API 关闭账号信息回传",
    )

    if create_mode:
        parser.add_argument("--generate-delivery-rule", action="store_true", help="创建卡片后自动生成对应发货规则")


def _add_runtime_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--server", help="服务地址，默认读取 XIANYU_SERVER 或 http://127.0.0.1:8090")
    parser.add_argument("--token", help="后台 Bearer token，默认读取 XIANYU_TOKEN")
    parser.add_argument("--json", action="store_true", dest="json_output", help="以 JSON 输出结果")


def _build_create_payload(args: argparse.Namespace, client: APIClient) -> dict[str, Any]:
    card_type = _normalize_card_type(args.card_type)
    payload: dict[str, Any] = {
        "name": require_text(args.name, field_name="卡片名称"),
        "type": card_type,
        "description": optional_text(args.description),
        "delay_seconds": validate_non_negative_int(args.delay_seconds or 0, field_name="延迟发货秒数"),
        "enabled": True if args.enabled is None else bool(args.enabled),
        "generate_delivery_rule": bool(getattr(args, "generate_delivery_rule", False)),
    }
    payload.update(_build_multi_spec_for_create(args))
    payload.update(_build_type_payload_for_create(args, card_type, client))
    return payload


def _build_update_payload(
    args: argparse.Namespace,
    existing: dict[str, Any],
    client: APIClient,
) -> dict[str, Any]:
    existing_type = _normalize_card_type(existing.get("type"))
    requested_type = optional_text(args.card_type)
    if requested_type is not None:
        normalized_requested_type = _normalize_card_type(requested_type)
        if normalized_requested_type != existing_type:
            raise CLIUsageError("首版 CLI 不支持卡片跨类型更新")

    payload: dict[str, Any] = {}
    if args.name is not None:
        payload["name"] = require_text(args.name, field_name="卡片名称")
    if args.description is not None:
        payload["description"] = optional_text(args.description)
    if args.delay_seconds is not None:
        payload["delay_seconds"] = validate_non_negative_int(args.delay_seconds, field_name="延迟发货秒数")
    if args.enabled is not None:
        payload["enabled"] = bool(args.enabled)

    payload.update(_build_multi_spec_for_update(args, existing))
    payload.update(_build_type_payload_for_update(args, existing_type, client, existing))

    if not payload:
        raise CLIUsageError("没有可更新的内容")

    if "enabled" not in payload:
        payload["enabled"] = bool(existing.get("enabled"))

    return payload


def _build_multi_spec_for_create(args: argparse.Namespace) -> dict[str, Any]:
    is_multi_spec = bool(args.is_multi_spec)
    spec_name = optional_text(args.spec_name)
    spec_value = optional_text(args.spec_value)
    spec_name_2 = optional_text(args.spec_name_2)
    spec_value_2 = optional_text(args.spec_value_2)

    if not is_multi_spec and any(value is not None for value in (spec_name, spec_value, spec_name_2, spec_value_2)):
        raise CLIUsageError("未启用 --multi-spec 时不能提供规格字段")

    if not is_multi_spec:
        return {"is_multi_spec": False}

    if not spec_name or not spec_value:
        raise CLIUsageError("多规格卡片必须提供 --spec-name 和 --spec-value")

    _validate_secondary_spec(spec_name_2, spec_value_2)
    return {
        "is_multi_spec": True,
        "spec_name": spec_name,
        "spec_value": spec_value,
        "spec_name_2": spec_name_2,
        "spec_value_2": spec_value_2,
    }


def _build_multi_spec_for_update(args: argparse.Namespace, existing: dict[str, Any]) -> dict[str, Any]:
    existing_is_multi_spec = bool(existing.get("is_multi_spec"))
    requested_multi_spec = args.is_multi_spec
    spec_fields_provided = any(
        value is not None
        for value in (args.spec_name, args.spec_value, args.spec_name_2, args.spec_value_2)
    )

    if requested_multi_spec is False:
        if spec_fields_provided:
            raise CLIUsageError("关闭多规格时不能同时提供规格字段")
        return {
            "is_multi_spec": False,
            "spec_name": "",
            "spec_value": "",
            "spec_name_2": "",
            "spec_value_2": "",
        }

    if not existing_is_multi_spec and requested_multi_spec is not True and spec_fields_provided:
        raise CLIUsageError("当前卡片不是多规格，更新规格字段时必须显式传入 --multi-spec")

    if not existing_is_multi_spec and requested_multi_spec is not True:
        return {}

    merged_spec_name = optional_text(args.spec_name) if args.spec_name is not None else optional_text(existing.get("spec_name"))
    merged_spec_value = optional_text(args.spec_value) if args.spec_value is not None else optional_text(existing.get("spec_value"))
    merged_spec_name_2 = optional_text(args.spec_name_2) if args.spec_name_2 is not None else optional_text(existing.get("spec_name_2"))
    merged_spec_value_2 = optional_text(args.spec_value_2) if args.spec_value_2 is not None else optional_text(existing.get("spec_value_2"))

    if not merged_spec_name or not merged_spec_value:
        raise CLIUsageError("多规格卡片必须提供完整的规格 1 信息")

    _validate_secondary_spec(merged_spec_name_2, merged_spec_value_2)

    payload: dict[str, Any] = {}
    if requested_multi_spec is True:
        payload["is_multi_spec"] = True
    if args.spec_name is not None:
        payload["spec_name"] = merged_spec_name
    if args.spec_value is not None:
        payload["spec_value"] = merged_spec_value
    if args.spec_name_2 is not None:
        payload["spec_name_2"] = merged_spec_name_2
    if args.spec_value_2 is not None:
        payload["spec_value_2"] = merged_spec_value_2
    return payload


def _build_type_payload_for_create(args: argparse.Namespace, card_type: str, client: APIClient) -> dict[str, Any]:
    if card_type == "text":
        return {"text_content": require_text(args.text_content, field_name="固定文字内容")}
    if card_type == "data":
        return {"data_content": require_text(args.data_content, field_name="批量数据内容")}
    if card_type == "image":
        return {"image_url": _prepare_card_image(client, args.image)}
    if card_type == "api":
        return {
            "api_config": {
                "url": require_text(args.api_url, field_name="API 请求地址"),
                "method": _normalize_api_method(args.api_method),
                "timeout": validate_positive_int(args.api_timeout or 10, field_name="API 超时时间"),
                "headers": dumps_json(parse_json_object(args.api_headers_json, field_name="API 请求头") or {}),
                "params": dumps_json(parse_json_object(args.api_params_json, field_name="API 请求参数") or {}),
            }
        }
    if card_type == "yifan_api":
        return {
            "api_config": {
                "user_id": require_text(args.yifan_user_id, field_name="亦凡 API 商户 ID"),
                "user_key": require_text(args.yifan_user_key, field_name="亦凡 API 商户 KEY"),
                "goods_id": require_text(args.yifan_goods_id, field_name="亦凡 API 商品 ID"),
                "callback_url": optional_text(args.yifan_callback_url) or "",
                "require_account": bool(args.yifan_require_account),
            }
        }

    raise CLIUsageError(f"不支持的卡片类型: {card_type}")


def _build_type_payload_for_update(
    args: argparse.Namespace,
    existing_type: str,
    client: APIClient,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    if args.text_content is not None:
        _assert_type(existing_type, "text", "--text-content")
        payload["text_content"] = require_text(args.text_content, field_name="固定文字内容")

    if args.data_content is not None:
        _assert_type(existing_type, "data", "--data-content")
        payload["data_content"] = require_text(args.data_content, field_name="批量数据内容")

    if args.image is not None:
        _assert_type(existing_type, "image", "--image")
        payload["image_url"] = _prepare_card_image(client, args.image)

    api_related = any(
        value is not None
        for value in (
            args.api_url,
            args.api_method,
            args.api_timeout,
            args.api_headers_json,
            args.api_params_json,
        )
    )
    if api_related:
        _assert_type(existing_type, "api", "API 参数")
        payload["api_config"] = _build_updated_api_config(args, existing)

    yifan_related = any(
        value is not None
        for value in (
            args.yifan_user_id,
            args.yifan_user_key,
            args.yifan_goods_id,
            args.yifan_callback_url,
        )
    ) or args.yifan_require_account is not None
    if yifan_related:
        _assert_type(existing_type, "yifan_api", "亦凡 API 参数")
        payload["api_config"] = _build_updated_yifan_config(args, existing)

    return payload


def _build_updated_api_config(args: argparse.Namespace, existing: dict[str, Any] | None) -> dict[str, Any]:
    existing_config = dict(existing.get("api_config") or {}) if existing else {}
    api_config: dict[str, Any] = dict(existing_config)
    if args.api_url is not None:
        api_config["url"] = require_text(args.api_url, field_name="API 请求地址")
    if args.api_method is not None:
        api_config["method"] = _normalize_api_method(args.api_method)
    if args.api_timeout is not None:
        api_config["timeout"] = validate_positive_int(args.api_timeout, field_name="API 超时时间")
    if args.api_headers_json is not None:
        api_config["headers"] = dumps_json(parse_json_object(args.api_headers_json, field_name="API 请求头") or {})
    if args.api_params_json is not None:
        api_config["params"] = dumps_json(parse_json_object(args.api_params_json, field_name="API 请求参数") or {})
    return api_config


def _build_updated_yifan_config(args: argparse.Namespace, existing: dict[str, Any] | None) -> dict[str, Any]:
    existing_config = dict(existing.get("api_config") or {}) if existing else {}
    api_config: dict[str, Any] = dict(existing_config)
    if args.yifan_user_id is not None:
        api_config["user_id"] = require_text(args.yifan_user_id, field_name="亦凡 API 商户 ID")
    if args.yifan_user_key is not None:
        api_config["user_key"] = require_text(args.yifan_user_key, field_name="亦凡 API 商户 KEY")
    if args.yifan_goods_id is not None:
        api_config["goods_id"] = require_text(args.yifan_goods_id, field_name="亦凡 API 商品 ID")
    if args.yifan_callback_url is not None:
        api_config["callback_url"] = optional_text(args.yifan_callback_url) or ""
    if args.yifan_require_account is not None:
        api_config["require_account"] = bool(args.yifan_require_account)
    return api_config


def _prepare_card_image(client: APIClient, raw_image: str | None) -> str:
    candidate = require_text(raw_image, field_name="图片路径")
    if candidate.startswith(("http://", "https://")):
        raise CLIUsageError("暂不支持远程图片 URL，请使用本地文件路径或服务端 /static/... 路径")
    if candidate.startswith("/static/") or candidate.startswith("static/"):
        return candidate
    return client.upload_image(_resolve_local_image_path(candidate))


def _resolve_local_image_path(candidate: str) -> str:
    image_path = Path(candidate).expanduser()
    absolute_path = image_path if image_path.is_absolute() else image_path.resolve()
    if not absolute_path.exists():
        raise CLIUsageError(f"图片不存在: {candidate}")
    if not absolute_path.is_file():
        raise CLIUsageError(f"图片路径不是文件: {candidate}")
    return str(absolute_path)


def _normalize_card_type(value: Any) -> str:
    card_type = str(value or "").strip()
    if card_type not in CARD_TYPES:
        raise CLIUsageError(f"不支持的卡片类型: {card_type}")
    return card_type


def _validate_secondary_spec(spec_name_2: str | None, spec_value_2: str | None) -> None:
    if bool(spec_name_2) != bool(spec_value_2):
        raise CLIUsageError("规格 2 必须同时提供名称和值")


def _assert_type(actual_type: str, expected_type: str, label: str) -> None:
    if actual_type != expected_type:
        raise CLIUsageError(f"{label}仅适用于 {expected_type} 类型卡片")


def _normalize_api_method(value: str | None) -> str:
    method = require_text(value, field_name="API 请求方法").upper() if value is not None else "GET"
    if method not in {"GET", "POST"}:
        raise CLIUsageError("API 请求方法仅支持 GET 或 POST")
    return method


def _make_help_handler(parser: argparse.ArgumentParser):
    def _handler(_: argparse.Namespace) -> int:
        parser.print_help()
        return 1

    return _handler
